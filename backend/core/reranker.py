"""Soft Reranker and Explanation Badges Engine.

Implements the multi-signal scoring formula:
FinalScore = 0.45 * S_visual + 0.25 * S_text_desc + 0.15 * S_color + 0.15 * S_price - Penalty
and generates transparent explanation badges for end-user trust.
"""

from __future__ import annotations

import logging
import re
from typing import List, Tuple

from backend.schemas.state import SearchResultItem, SearchState

logger = logging.getLogger("reranker")


class ResultExplainer:
    """Generates human-readable explanation badges based on matched attributes."""

    @staticmethod
    def generate_badges(item: SearchResultItem, state: SearchState, penalty_applied: bool) -> List[str]:
        """Creates transparent badges explaining why this item was ranked here."""
        badges: List[str] = []

        # 1. Visual match percentage badge
        vis_pct = int(round(item.visual_similarity * 100))
        if vis_pct > 0:
            badges.append(f"{vis_pct}% tương đồng ảnh")

        # 2. Color badge
        if state.color and (state.color.lower() in item.color_name.lower()):
            badges.append(f"✓ Màu {item.color_name}")

        # 3. Price fit badge
        if state.max_price is not None and item.price_vnd <= state.max_price:
            price_m = f"{state.max_price / 1_000_000:.1f}M".replace(".0M", "M") if state.max_price >= 1_000_000 else f"{state.max_price // 1_000}k"
            badges.append(f"✓ Dưới {price_m}")

        # 4. Material bonus badge
        if state.material and re.search(r"\b" + re.escape(state.material.lower()) + r"\b", item.detail_desc.lower()):
            badges.append(f"✓ Chất liệu {state.material.title()}")

        # 5. Penalty warning badge
        if penalty_applied:
            badges.append("⚠️ Dính chất liệu loại trừ (-30%)")

        return badges


class SoftReranker:
    """Constraint-aware soft reranking engine."""

    PENALTY_VIOLATION = 0.30
    BONUS_MATERIAL = 0.15

    @classmethod
    def calculate_item_score(
        cls,
        item: SearchResultItem,
        state: SearchState,
    ) -> Tuple[float, bool]:
        """Calculates multi-signal score and checks penalty violation."""
        desc_lower = (item.detail_desc + " " + item.prod_name).lower()

        # 1. S_visual (0.45 weight)
        s_visual = item.visual_similarity

        # 2. S_text_desc (0.25 weight)
        s_text = 0.5
        if state.material and re.search(r"\b" + re.escape(state.material.lower()) + r"\b", desc_lower):
            s_text += 0.4
        if state.style and re.search(r"\b" + re.escape(state.style.lower()) + r"\b", desc_lower):
            s_text += 0.1
        s_text = min(1.0, s_text)

        # 3. S_color (0.15 weight)
        s_color = 0.5
        if state.color and state.color.lower() in item.color_name.lower():
            s_color = 1.0

        # 4. S_price (0.15 weight)
        s_price = 0.7
        if state.max_price is not None and state.max_price > 0:
            if item.price_vnd <= state.max_price:
                # Cheaper items get slightly higher preference within budget
                ratio = item.price_vnd / state.max_price
                s_price = 1.0 - 0.2 * ratio
            else:
                s_price = 0.2

        # 5. Penalty check for negative constraints (exclude_materials)
        penalty = 0.0
        penalty_applied = False
        for exc_mat in state.exclude_materials:
            if re.search(r"\b" + re.escape(exc_mat.lower()) + r"\b", desc_lower):
                penalty += cls.PENALTY_VIOLATION
                penalty_applied = True
                break

        # Calculate final composite score
        base_score = 0.45 * s_visual + 0.25 * s_text + 0.15 * s_color + 0.15 * s_price
        
        # Apply material bonus if specifically matched
        if state.material and re.search(r"\b" + re.escape(state.material.lower()) + r"\b", desc_lower):
            base_score += cls.BONUS_MATERIAL

        final_score = max(0.0, round(base_score - penalty, 4))
        return final_score, penalty_applied

    @classmethod
    def rerank(
        cls,
        candidates: List[SearchResultItem],
        state: SearchState,
    ) -> List[SearchResultItem]:
        """Reranks candidates and attaches explanation badges."""
        reranked_items: List[SearchResultItem] = []

        for item in candidates:
            score, penalty_applied = cls.calculate_item_score(item, state)
            item.final_score = score
            item.explanation_badges = ResultExplainer.generate_badges(item, state, penalty_applied)
            reranked_items.append(item)

        # Sort descending by final_score
        reranked_items.sort(key=lambda x: x.final_score, reverse=True)
        return reranked_items
