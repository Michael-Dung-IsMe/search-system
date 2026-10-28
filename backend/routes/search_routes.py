"""Search API Router.

Exposes REST endpoints for object detection, speech transcription,
independent multimodal searches, and product details.
"""

from __future__ import annotations

import io
import json
import logging
import os
import time
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from PIL import Image

from backend.core.detector import ObjectDetector
from backend.core.embedder import MultimodalEmbedder
from backend.core.extractor import IntentExtractor, build_canonical_query
from backend.core.normalizer import EntityNormalizer
from backend.core.reranker import SoftReranker
from backend.core.retriever import CandidateRetriever
from backend.core.search_audit import persist_search
from backend.core.transcriber import SpeechTranscriber
from backend.db.connection import get_db_connection
from backend.schemas.api import (
    DetectResponse,
    ProductDetailResponse,
    TranscribeResponse,
)
from backend.schemas.state import SearchResponse, SearchResultItem, SearchState

logger = logging.getLogger("search_routes")
router = APIRouter(prefix="/api", tags=["search"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
ALLOWED_AUDIO_TYPES = {
    "audio/webm",
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mpga",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
}
ALLOWED_AUDIO_EXTENSIONS = (".webm", ".wav", ".mp3", ".mp4", ".mpeg", ".mpga", ".m4a")
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
    """Transcribes a completed audio query into Vietnamese text."""
    filename = file.filename or "recording.webm"
    if (
        file.content_type not in ALLOWED_AUDIO_TYPES
        and not filename.lower().endswith(ALLOWED_AUDIO_EXTENSIONS)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio type: {file.content_type}.",
        )

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
            filename=filename,
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
    reference_article_id: Optional[str] = Form(None),
    crop_box: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    query_type: Optional[str] = Form(None),
) -> SearchResponse:
    """Execute one self-contained text, image, voice, or image+text search."""
    start_time = time.time()
    state = SearchState(reference_article_id=reference_article_id)
    active_query_type = query_type or "text"
    query_vector = None
    crop_image_path = None
    image_was_uploaded = False
    explicit_category_override: Optional[str] = None

    # 1. Process an uploaded image or selected crop.
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
                crop_filename = f"{uuid4()}.jpg"
                crop_file_path = UPLOAD_DIR / crop_filename
                pil_img.save(crop_file_path, format="JPEG")
                crop_image_path = str(crop_file_path)

                # Compute SigLIP visual embedding
                embedder = MultimodalEmbedder.get_instance()
                query_vector = embedder.encode_image(pil_img)
                active_query_type = "image"
                image_was_uploaded = True

            except Exception as e:
                logger.error("Failed to process uploaded image: %s", e)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid image content: {str(e)}",
                )

    # 2. A product-reference search reuses that product's image embedding.
    if reference_article_id:
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
        except Exception as e:
            logger.warning("Could not fetch reference embedding from DB (%s), using embedder fallback.", e)

    # 3. Extract all constraints for this request. Nothing is inherited from
    # an earlier request.
    extracted_intent = None
    if query_text and query_text.strip():
        extractor = IntentExtractor()
        extracted_intent = extractor.extract(query_text)

        # For image + text search, the image supplies the base product category.
        # Text overrides it only when the user names a specific catalog type.
        if image_was_uploaded:
            normalized_text = EntityNormalizer.normalize_phonetics(query_text)
            explicit_category = EntityNormalizer.extract_category(normalized_text)
            if explicit_category and explicit_category[1] != "Pants":
                explicit_category_override = explicit_category[1]
                extracted_intent.category = explicit_category_override
                logger.info(
                    "Multimodal category | source=text_override | category=%s",
                    explicit_category_override,
                )
            else:
                extracted_intent.category = None
                logger.info(
                    "Multimodal category | source=image_pending | ignored_llm_guess=true"
                )

        if image_was_uploaded or reference_article_id:
            extracted_intent.intent_type = "product_search"

        state = SearchState(
            category=extracted_intent.category,
            gender=extracted_intent.gender,
            color=extracted_intent.color,
            min_price=extracted_intent.min_price,
            max_price=extracted_intent.max_price,
            material=extracted_intent.material,
            style=extracted_intent.style,
            purpose=extracted_intent.purpose,
            exclude_colors=list(extracted_intent.exclude_colors),
            exclude_materials=list(extracted_intent.exclude_materials),
            reference_article_id=reference_article_id,
        )

        if extracted_intent.intent_type == "conversation":
            latency = int((time.time() - start_time) * 1000)
            message = (
                "Xin chào! Tôi là trợ lý tìm kiếm thời trang. "
                "Bạn có thể mô tả loại áo, quần, váy hoặc giày mà bạn muốn tìm."
            )
            logger.info(
                "Conversation-only query skipped product retrieval | query=%r",
                query_text,
            )
            return SearchResponse(
                total_results=0,
                search_state=state,
                items=[],
                has_exact_match=False,
                exact_items=[],
                similar_items=[],
                message=message,
                response_type="conversation",
                query_type=active_query_type,
                latency_ms=latency,
            )

        # Keep an image/reference vector for multimodal search. Text embedding
        # is only needed when the request has no visual input.
        if query_vector is None:
            embedder = MultimodalEmbedder.get_instance()
            query_vector = embedder.encode_text(extracted_intent.normalized_query or query_text)
            active_query_type = query_type or "text"

    # 4. Retrieve exact matches and controlled-relaxation recommendations.
    exact_candidates: List[SearchResultItem] = []
    similar_candidates: List[SearchResultItem] = []
    query_id = None

    try:
        with get_db_connection() as conn:
            if (
                image_was_uploaded
                and explicit_category_override is None
                and query_vector is not None
            ):
                try:
                    inferred_category, category_confidence = (
                        CandidateRetriever.infer_category_from_image(
                            conn=conn,
                            query_vector=query_vector,
                        )
                    )
                    if inferred_category:
                        state.category = inferred_category
                        logger.info(
                            "Multimodal category | source=image_neighbors | category=%s | confidence=%.2f",
                            inferred_category,
                            category_confidence,
                        )
                    else:
                        logger.info(
                            "Multimodal category | source=image_neighbors | category=none | confidence=%.2f",
                            category_confidence,
                        )
                except Exception as e:
                    conn.rollback()
                    logger.warning("Could not infer category from image neighbors: %s", e)

            exact_candidates, similar_candidates = CandidateRetriever.retrieve_partitioned(
                conn=conn,
                state=state,
                query_vector=query_vector,
                query_type=active_query_type,
                limit=50,
            )

            # Try the user's normalized wording first. Only an empty text/voice
            # result triggers a second retrieval using stable catalog terms
            # assembled from the structured LLM intent.
            if (
                not exact_candidates
                and not similar_candidates
                and extracted_intent is not None
                and active_query_type in ("text", "voice")
                and not image_was_uploaded
                and not reference_article_id
            ):
                canonical_query = build_canonical_query(extracted_intent)
                raw_embedding_query = (
                    extracted_intent.normalized_query or query_text or ""
                ).strip()
                if (
                    canonical_query
                    and canonical_query.casefold() != raw_embedding_query.casefold()
                ):
                    logger.info(
                        "Raw text retrieval returned no candidates; retrying canonical query | raw=%r | canonical=%r",
                        raw_embedding_query,
                        canonical_query,
                    )
                    embedder = MultimodalEmbedder.get_instance()
                    query_vector = embedder.encode_text(canonical_query)
                    exact_candidates, similar_candidates = (
                        CandidateRetriever.retrieve_partitioned(
                            conn=conn,
                            state=state,
                            query_vector=query_vector,
                            query_type=active_query_type,
                            limit=50,
                        )
                    )

            # 5. Apply the multi-signal soft reranker to both partitions.
            reranked_exact = SoftReranker.rerank(exact_candidates, state)
            reranked_similar = SoftReranker.rerank(similar_candidates, state)

            has_exact_match = len(reranked_exact) > 0
            message = None
            if not has_exact_match:
                message = "Không tìm thấy sản phẩm khớp chính xác với tiêu chí của bạn. Dưới đây là các sản phẩm tương tự."

            all_displayed = reranked_exact if has_exact_match else reranked_similar

            # 6. Persist this independent search for audit/analytics.
            latency = int((time.time() - start_time) * 1000)
            query_id = persist_search(
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

    return SearchResponse(
        total_results=len(reranked_exact) + len(reranked_similar),
        search_state=state,
        items=all_displayed,
        has_exact_match=has_exact_match,
        exact_items=reranked_exact,
        similar_items=reranked_similar,
        message=message,
        query_type=active_query_type,
        latency_ms=latency,
        query_id=query_id,
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
                    color_name=EntityNormalizer.get_color_name(str(row[5])),
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
