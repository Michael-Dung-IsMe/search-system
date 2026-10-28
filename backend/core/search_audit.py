"""Persistence helper for independent search requests."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from uuid import uuid4

import psycopg

from backend.schemas.state import SearchState


def persist_search(
    conn: psycopg.Connection,
    state: SearchState,
    raw_query: Optional[str] = None,
    crop_image_path: Optional[str] = None,
    intent_json: Optional[Dict[str, Any]] = None,
    latency_ms: Optional[int] = None,
    query_type: str = "text",
    crop_box: Optional[str] = None,
    results: Optional[List[Any]] = None,
) -> str:
    """Record one search and its displayed results in the TPT audit tables."""
    query_id = str(uuid4())
    search_criteria = raw_query or (
        f"crop:{crop_box}" if crop_box else state.category or ""
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO search_query (
                query_id, query_type, search_criteria, reference_article_id,
                extracted_intent, latency_ms
            )
            VALUES (%s, %s, %s, %s, %s::jsonb, %s);
            """,
            (
                query_id,
                query_type,
                search_criteria,
                state.reference_article_id,
                json.dumps(intent_json or {}),
                latency_ms,
            ),
        )

        if query_type == "image":
            cur.execute(
                """
                INSERT INTO image_query (query_id, image_reference, selected_region)
                VALUES (%s, %s, %s);
                """,
                (query_id, crop_image_path or "", crop_box),
            )
        elif query_type == "voice":
            cur.execute(
                """
                INSERT INTO voice_query (query_id, transcribe_text, audio_reference)
                VALUES (%s, %s, %s);
                """,
                (query_id, raw_query or "", crop_image_path),
            )
        else:
            cur.execute(
                """
                INSERT INTO text_query (query_id, query_text)
                VALUES (%s, %s);
                """,
                (query_id, raw_query or ""),
            )

        for rank, item in enumerate(results or [], start=1):
            if rank > 50:
                break
            article_id = getattr(item, "article_id", None) or str(item)
            score = float(
                getattr(item, "final_score", 0.0)
                or getattr(item, "visual_similarity", 0.0)
                or 0.5
            )
            cur.execute(
                """
                INSERT INTO search_result (query_id, article_id, rank, score)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (query_id, article_id) DO NOTHING;
                """,
                (query_id, article_id, rank, score),
            )

    conn.commit()
    return query_id

