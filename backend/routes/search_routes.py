"""Search API Router.

Exposes REST endpoints for Object Detection, Speech Transcription,
Multimodal Conversational Search, Interactive Constraint Chips, and Product Details.
"""

from __future__ import annotations

import io
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from PIL import Image

from backend.core.detector import ObjectDetector
from backend.core.embedder import MultimodalEmbedder
from backend.core.extractor import IntentExtractor
from backend.core.reranker import SoftReranker
from backend.core.retriever import CandidateRetriever
from backend.core.state_manager import StateManager
from backend.core.transcriber import SpeechTranscriber
from backend.db.connection import get_db_connection
from backend.schemas.api import (
    DeleteConstraintRequest,
    DetectResponse,
    ProductDetailResponse,
    TranscribeResponse,
)
from backend.schemas.state import QueryIntent, SearchResponse, SearchResultItem, SearchState

logger = logging.getLogger("search_routes")
router = APIRouter(prefix="/api", tags=["search"])

# In-memory session state storage for fast interactive updates
SESSION_STATES: Dict[str, SearchState] = {}
SESSION_PREVIOUS_RESULTS: Dict[str, List[str]] = {}
SESSION_QUERY_VECTORS: Dict[str, Any] = {}
SESSION_QUERY_TYPES: Dict[str, str] = {}

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
ALLOWED_AUDIO_TYPES = {"audio/webm", "audio/wav", "audio/mpeg", "audio/mp4", "audio/ogg", "audio/x-m4a"}
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/detect", response_model=DetectResponse)
async def detect_objects(file: UploadFile = File(...)) -> DetectResponse:
    """Detects garments in an uploaded outfit image using OWL-ViT."""
    if file.content_type not in ALLOWED_IMAGE_TYPES and not file.filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image type: {file.content_type}. Supported: JPEG, PNG, WebP.",
        )

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image file is empty.",
        )

    try:
        detector = ObjectDetector.get_instance()
        boxes = detector.detect(image_bytes)
        img_hash = detector.compute_image_hash(image_bytes)

        return DetectResponse(
            image_hash=img_hash,
            total_boxes=len(boxes),
            boxes=boxes,
        )
    except Exception as e:
        logger.error("Error during object detection: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Detection failure: {str(e)}",
        )


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(file: UploadFile = File(...)) -> TranscribeResponse:
    """Transcribes an audio blob query into Vietnamese text using Whisper."""
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file is empty.",
        )

    try:
        transcriber = SpeechTranscriber.get_instance()
        transcript = transcriber.transcribe(
            audio_input=audio_bytes,
            filename=file.filename or "recording.webm",
            language="vi",
        )
        return TranscribeResponse(text=transcript, language="vi")
    except Exception as e:
        logger.error("Error during speech transcription: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failure: {str(e)}",
        )


@router.post("/search", response_model=SearchResponse)
async def search_products(
    query_text: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    reference_article_id: Optional[str] = Form(None),
    crop_box: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    query_type: Optional[str] = Form(None),
) -> SearchResponse:
    """Unified Multimodal Conversational Search endpoint."""
    start_time = time.time()

    # 1. Resolve or create SearchState session
    sid = session_id or str(uuid4())
    state = SESSION_STATES.get(sid, SearchState(session_id=sid))
    previous_results = SESSION_PREVIOUS_RESULTS.get(sid, [])

    active_query_type = query_type or SESSION_QUERY_TYPES.get(sid, "text")
    query_vector = SESSION_QUERY_VECTORS.get(sid)
    crop_image_path = None

    # 2. Process uploaded image or crop box
    if image is not None:
        img_bytes = await image.read()
        if img_bytes:
            try:
                pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                
                # Check if specific object bounding box is requested
                if crop_box:
                    try:
                        box_coords = json.loads(crop_box)
                        if isinstance(box_coords, list) and len(box_coords) == 4:
                            pil_img = ObjectDetector.crop_bounding_box(pil_img, box_coords)
                    except json.JSONDecodeError:
                        logger.warning("Invalid crop_box JSON format: %s", crop_box)

                # Save uploaded crop
                crop_filename = f"{sid}_turn_{state.turn_index + 1}.jpg"
                crop_file_path = UPLOAD_DIR / crop_filename
                pil_img.save(crop_file_path, format="JPEG")
                crop_image_path = str(crop_file_path)

                # Compute SigLIP visual embedding
                embedder = MultimodalEmbedder.get_instance()
                query_vector = embedder.encode_image(pil_img)
                active_query_type = "image"
                SESSION_QUERY_VECTORS[sid] = query_vector
                SESSION_QUERY_TYPES[sid] = active_query_type

            except Exception as e:
                logger.error("Failed to process uploaded image: %s", e)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid image content: {str(e)}",
                )

    # 3. Process direct reference article
    if reference_article_id:
        state.reference_article_id = reference_article_id
        # Try fetching article visual embedding from database
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT image_embedding FROM product WHERE article_id = %s;",
                        (reference_article_id,),
                    )
                    row = cur.fetchone()
                    if row and row[0]:
                        import numpy as np
                        raw_vec = row[0]
                        if isinstance(raw_vec, str):
                            raw_vec = json.loads(raw_vec)
                        query_vector = np.array(raw_vec, dtype=np.float32)
                        active_query_type = "image"
                        SESSION_QUERY_VECTORS[sid] = query_vector
                        SESSION_QUERY_TYPES[sid] = active_query_type
        except Exception as e:
            logger.warning("Could not fetch reference embedding from DB (%s), using embedder fallback.", e)

    # 4. Process natural text query through Intent Extractor & State Manager
    extracted_intent = None
    if query_text and query_text.strip():
        extractor = IntentExtractor()
        extracted_intent = extractor.extract(query_text)
        state = StateManager.merge_intent(state, extracted_intent, previous_results)

        # If no visual vector yet, compute text query vector
        if query_vector is None or image is None:
            embedder = MultimodalEmbedder.get_instance()
            query_vector = embedder.encode_text(extracted_intent.normalized_query or query_text)
            if not query_type:
                active_query_type = "text"
            SESSION_QUERY_VECTORS[sid] = query_vector
            SESSION_QUERY_TYPES[sid] = active_query_type

    # 5. Retrieve partitioned candidates (Exact Matches vs Similar Recommendations)
    exact_candidates: List[SearchResultItem] = []
    similar_candidates: List[SearchResultItem] = []
    query_id = None

    try:
        with get_db_connection() as conn:
            exact_candidates, similar_candidates = CandidateRetriever.retrieve_partitioned(
                conn=conn,
                state=state,
                query_vector=query_vector,
                query_type=active_query_type,
                limit=50,
            )

            # 6. Apply multi-signal soft reranker to both partitions
            reranked_exact = SoftReranker.rerank(exact_candidates, state)
            reranked_similar = SoftReranker.rerank(similar_candidates, state)

            has_exact_match = len(reranked_exact) > 0
            message = None
            if not has_exact_match:
                message = "Không tìm thấy sản phẩm khớp chính xác với tiêu chí của bạn. Dưới đây là các sản phẩm tương tự."

            # Combined items for persistence and backwards compatibility
            all_displayed = reranked_exact if has_exact_match else reranked_similar

            # 7. Persist turn audit log and search_result records
            latency = int((time.time() - start_time) * 1000)
            query_id = StateManager.persist_turn(
                conn=conn,
                state=state,
                raw_query=query_text,
                crop_image_path=crop_image_path,
                intent_json=extracted_intent.model_dump() if extracted_intent else {},
                latency_ms=latency,
                query_type=active_query_type,
                crop_box=crop_box,
                results=all_displayed,
            )
    except Exception as e:
        logger.warning("Database unavailable (%s), using sample dataset fallback.", e)
        exact_candidates, similar_candidates = CandidateRetriever.retrieve_from_csv_partitioned(
            state=state, limit=50
        )
        reranked_exact = SoftReranker.rerank(exact_candidates, state)
        reranked_similar = SoftReranker.rerank(similar_candidates, state)
        has_exact_match = len(reranked_exact) > 0
        message = None
        if not has_exact_match:
            message = "Không tìm thấy sản phẩm khớp chính xác với tiêu chí của bạn. Dưới đây là các sản phẩm tương tự."
        all_displayed = reranked_exact if has_exact_match else reranked_similar
        latency = int((time.time() - start_time) * 1000)
        query_id = None

    # 8. Update in-memory session tracking
    SESSION_STATES[sid] = state
    SESSION_PREVIOUS_RESULTS[sid] = [item.article_id for item in all_displayed]

    return SearchResponse(
        session_id=sid,
        turn_index=state.turn_index,
        total_results=len(reranked_exact) + len(reranked_similar),
        search_state=state,
        items=all_displayed,
        has_exact_match=has_exact_match,
        exact_items=reranked_exact,
        similar_items=reranked_similar,
        message=message,
        latency_ms=latency,
        query_id=query_id,
    )


@router.delete("/search/{session_id}/constraint", response_model=SearchResponse)
async def delete_constraint(
    session_id: str,
    chip_id: str = Query(..., description="The chip_id to remove, e.g. 'color:Black'"),
) -> SearchResponse:
    """Removes an active constraint chip and re-evaluates ranking immediately."""
    if session_id not in SESSION_STATES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    start_time = time.time()
    state = SESSION_STATES[session_id]
    state = StateManager.remove_constraint(state, chip_id)

    query_vector = SESSION_QUERY_VECTORS.get(session_id)
    query_type = SESSION_QUERY_TYPES.get(session_id, "text")

    # Re-query partitioned candidates
    exact_candidates: List[SearchResultItem] = []
    similar_candidates: List[SearchResultItem] = []

    try:
        with get_db_connection() as conn:
            exact_candidates, similar_candidates = CandidateRetriever.retrieve_partitioned(
                conn=conn,
                state=state,
                query_vector=query_vector,
                query_type=query_type,
                limit=50,
            )
            reranked_exact = SoftReranker.rerank(exact_candidates, state)
            reranked_similar = SoftReranker.rerank(similar_candidates, state)
    except Exception as e:
        logger.warning("DB query during constraint removal failed (%s), using sample dataset fallback.", e)
        exact_candidates, similar_candidates = CandidateRetriever.retrieve_from_csv_partitioned(
            state=state, limit=50
        )
        reranked_exact = SoftReranker.rerank(exact_candidates, state)
        reranked_similar = SoftReranker.rerank(similar_candidates, state)

    has_exact_match = len(reranked_exact) > 0
    message = None
    if not has_exact_match:
        message = "Không tìm thấy sản phẩm khớp chính xác với tiêu chí của bạn. Dưới đây là các sản phẩm tương tự."
    all_displayed = reranked_exact if has_exact_match else reranked_similar

    SESSION_STATES[session_id] = state
    SESSION_PREVIOUS_RESULTS[session_id] = [item.article_id for item in all_displayed]
    latency = int((time.time() - start_time) * 1000)

    return SearchResponse(
        session_id=session_id,
        turn_index=state.turn_index,
        total_results=len(reranked_exact) + len(reranked_similar),
        search_state=state,
        items=all_displayed,
        has_exact_match=has_exact_match,
        exact_items=reranked_exact,
        similar_items=reranked_similar,
        message=message,
        latency_ms=latency,
    )


@router.get("/products/{product_id}", response_model=ProductDetailResponse)
async def get_product_detail(product_id: str) -> ProductDetailResponse:
    """Fetches complete product detail by article_id."""
    clean_id = product_id.strip().zfill(10)

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 
                        p.article_id,
                        p.product_code,
                        p.prod_name,
                        p.price_vnd,
                        p.gender,
                        COALESCE(p.color_code, '') AS color_code,
                        COALESCE(p.color_code, '') AS color_name,
                        c.group_name,
                        c.sub_category,
                        COALESCE(p.detail_desc, ''),
                        p.image_path
                    FROM product p
                    JOIN category c ON p.category_id = c.id
                    WHERE p.article_id = %s;
                    """,
                    (clean_id,),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Product with article_id '{clean_id}' does not exist.",
                    )

                return ProductDetailResponse(
                    article_id=str(row[0]),
                    product_code=str(row[1]),
                    prod_name=str(row[2]),
                    price_vnd=int(row[3]),
                    gender=str(row[4]),
                    color_code=str(row[5]),
                    color_name=str(row[6]),
                    category_group=str(row[7]),
                    category_sub=str(row[8]),
                    detail_desc=str(row[9]),
                    image_path=str(row[10]),
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to query product %s: %s", clean_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal database query error: {str(e)}",
        )
