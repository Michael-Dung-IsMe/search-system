"""Search State Manager.

Coordinates conversational search state merging across multi-turn queries,
handles interactive filter chip removals, and persists history into PostgreSQL.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

import psycopg

from backend.schemas.state import ConstraintChip, QueryIntent, SearchState

logger = logging.getLogger("state_manager")


class StateManager:
    """Manages SearchState lifecycle, constraint merging, and interactive chips."""

    @staticmethod
    def generate_chips(state: SearchState) -> List[ConstraintChip]:
        """Generates interactive UI chips reflecting all active state constraints."""
        chips: List[ConstraintChip] = []

        if state.gender:
            label = "Dành cho: Nữ" if state.gender == "Ladieswear" else "Dành cho: Nam"
            chips.append(ConstraintChip(
                chip_id=f"gender:{state.gender}",
                label=label,
                chip_type="gender",
                value=state.gender,
            ))

        if state.category:
            chips.append(ConstraintChip(
                chip_id=f"category:{state.category}",
                label=f"Loại: {state.category}",
                chip_type="category",
                value=state.category,
            ))

        if state.color:
            chips.append(ConstraintChip(
                chip_id=f"color:{state.color}",
                label=f"Màu: {state.color}",
                chip_type="color",
                value=state.color,
            ))

        if state.max_price is not None:
            formatted_price = f"{state.max_price / 1_000_000:.1f}M".replace(".0M", "M") if state.max_price >= 1_000_000 else f"{state.max_price // 1_000}k"
            chips.append(ConstraintChip(
                chip_id=f"max_price:{state.max_price}",
                label=f"Giá ≤ {formatted_price}",
                chip_type="price",
                value=state.max_price,
            ))

        if state.min_price is not None:
            formatted_price = f"{state.min_price / 1_000_000:.1f}M".replace(".0M", "M") if state.min_price >= 1_000_000 else f"{state.min_price // 1_000}k"
            chips.append(ConstraintChip(
                chip_id=f"min_price:{state.min_price}",
                label=f"Giá ≥ {formatted_price}",
                chip_type="price",
                value=state.min_price,
            ))

        if state.material:
            chips.append(ConstraintChip(
                chip_id=f"material:{state.material}",
                label=f"Chất liệu: {state.material}",
                chip_type="material",
                value=state.material,
            ))

        for exc_col in state.exclude_colors:
            chips.append(ConstraintChip(
                chip_id=f"exclude_color:{exc_col}",
                label=f"✕ Không màu {exc_col}",
                chip_type="exclude_color",
                value=exc_col,
            ))

        for exc_mat in state.exclude_materials:
            chips.append(ConstraintChip(
                chip_id=f"exclude_material:{exc_mat}",
                label=f"✕ Tránh chất liệu {exc_mat}",
                chip_type="exclude_material",
                value=exc_mat,
            ))

        if state.reference_article_id:
            chips.append(ConstraintChip(
                chip_id=f"ref:{state.reference_article_id}",
                label=f"Mẫu chuẩn #{state.reference_article_id[-4:]}",
                chip_type="reference",
                value=state.reference_article_id,
            ))

        return chips

    @classmethod
    def merge_intent(
        cls,
        current_state: SearchState,
        intent: QueryIntent,
        previous_results: Optional[List[str]] = None,
    ) -> SearchState:
        """Merges new extracted intent into existing conversational search state."""
        state = current_state.model_copy(deep=True)
        state.turn_index += 1

        # Direct overrides for positive attributes
        if intent.category:
            state.category = intent.category
        if intent.gender:
            state.gender = intent.gender
        if intent.color:
            state.color = intent.color
        if intent.max_price is not None:
            state.max_price = intent.max_price
        if intent.min_price is not None:
            state.min_price = intent.min_price
        if intent.material:
            state.material = intent.material
        if intent.style:
            state.style = intent.style
        if intent.purpose:
            state.purpose = intent.purpose

        # Cumulative aggregation for negative constraints
        for exc_col in intent.exclude_colors:
            if exc_col not in state.exclude_colors:
                state.exclude_colors.append(exc_col)
            # If user previously wanted this color, clear it
            if state.color and state.color.lower() == exc_col.lower():
                state.color = None

        for exc_mat in intent.exclude_materials:
            if exc_mat not in state.exclude_materials:
                state.exclude_materials.append(exc_mat)
            if state.material and state.material.lower() == exc_mat.lower():
                state.material = None

        # Resolve relative ordinal references (e.g. 'giống số 1', 'chiếc thứ 2')
        if intent.reference_ordinal and previous_results:
            idx = intent.reference_ordinal - 1
            if 0 <= idx < len(previous_results):
                state.reference_article_id = previous_results[idx]
                logger.info("Resolved reference ordinal %d to article %s", intent.reference_ordinal, state.reference_article_id)

        # Regenerate active chips
        state.active_chips = cls.generate_chips(state)
        return state

    @classmethod
    def remove_constraint(cls, current_state: SearchState, chip_id: str) -> SearchState:
        """Removes a specific constraint when user clicks [x] on an active chip."""
        state = current_state.model_copy(deep=True)

        if chip_id.startswith("gender:"):
            state.gender = None
        elif chip_id.startswith("category:"):
            state.category = None
        elif chip_id.startswith("color:"):
            state.color = None
        elif chip_id.startswith("max_price:"):
            state.max_price = None
        elif chip_id.startswith("min_price:"):
            state.min_price = None
        elif chip_id.startswith("material:"):
            state.material = None
        elif chip_id.startswith("exclude_color:"):
            val = chip_id.split(":", 1)[1]
            state.exclude_colors = [c for c in state.exclude_colors if c != val]
        elif chip_id.startswith("exclude_material:"):
            val = chip_id.split(":", 1)[1]
            state.exclude_materials = [m for m in state.exclude_materials if m != val]
        elif chip_id.startswith("ref:"):
            state.reference_article_id = None

        state.active_chips = cls.generate_chips(state)
        return state

    @staticmethod
    def persist_turn(
        conn: psycopg.Connection,
        state: SearchState,
        raw_query: Optional[str] = None,
        crop_image_path: Optional[str] = None,
        intent_json: Optional[Dict[str, Any]] = None,
        latency_ms: Optional[int] = None,
        query_type: str = "text",
        crop_box: Optional[str] = None,
        results: Optional[List[Any]] = None,
        query_id: Optional[str] = None,
    ) -> str:
        """Records search query event into 14-class TPT schema (search_query, text/image/voice_query, search_result)."""
        import json
        from uuid import uuid4

        qid = query_id or str(uuid4())
        search_crit = raw_query or (f"crop:{crop_box}" if crop_box else state.category or "")

        with conn.cursor() as cur:
            # 1. Insert parent search_query
            cur.execute(
                """
                INSERT INTO search_query (
                    query_id, query_type, search_criteria, reference_article_id, extracted_intent, latency_ms
                )
                VALUES (%s, %s, %s, %s, %s::jsonb, %s);
                """,
                (
                    qid,
                    query_type,
                    search_crit,
                    state.reference_article_id,
                    json.dumps(intent_json or {}),
                    latency_ms,
                ),
            )

            # 2. Insert child TPT query table
            if query_type == "image":
                cur.execute(
                    """
                    INSERT INTO image_query (query_id, image_reference, selected_region)
                    VALUES (%s, %s, %s);
                    """,
                    (qid, crop_image_path or "", crop_box),
                )
            elif query_type == "voice":
                cur.execute(
                    """
                    INSERT INTO voice_query (query_id, transcribe_text, audio_reference)
                    VALUES (%s, %s, %s);
                    """,
                    (qid, raw_query or "", crop_image_path),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO text_query (query_id, query_text)
                    VALUES (%s, %s);
                    """,
                    (qid, raw_query or ""),
                )

            # 3. Insert search_result items if provided
            if results:
                for rank_idx, item in enumerate(results[:50], start=1):
                    art_id = getattr(item, "article_id", None) or (item if isinstance(item, str) else str(item))
                    score = float(getattr(item, "final_score", 0.0) or getattr(item, "visual_similarity", 0.0) or 0.5)
                    cur.execute(
                        """
                        INSERT INTO search_result (query_id, article_id, rank, score)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (query_id, article_id) DO NOTHING;
                        """,
                        (qid, art_id, rank_idx, score),
                    )

        conn.commit()
        return qid
