"""Candidate Retriever for PostgreSQL + pgvector.

Executes dynamically constructed SQL queries combining strict relational WHERE clauses
(Hard Constraints) and HNSW cosine distance vector similarity ordering.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import psycopg

from backend.core.normalizer import EntityNormalizer
from backend.schemas.state import SearchResultItem, SearchState

logger = logging.getLogger("retriever")


class CandidateRetriever:
    """Retrieves top candidate products from PostgreSQL + pgvector based on SearchState."""

    @staticmethod
    def infer_category_from_image(
        conn: psycopg.Connection,
        query_vector: np.ndarray,
        top_k: int = 20,
        min_confidence: float = 0.55,
    ) -> Tuple[Optional[str], float]:
        """Infers the base product category by voting among nearest image neighbors."""
        sql = """
            WITH nearest AS (
                SELECT
                    c.sub_category,
                    1 - (p.image_embedding <=> %(query_vec)s::vector) AS similarity
                FROM product p
                JOIN category c ON p.category_id = c.id
                WHERE p.image_embedding IS NOT NULL
                ORDER BY p.image_embedding <=> %(query_vec)s::vector ASC
                LIMIT %(top_k)s
            )
            SELECT
                sub_category,
                COUNT(*)::int AS votes,
                AVG(similarity)::float AS avg_similarity
            FROM nearest
            GROUP BY sub_category
            ORDER BY votes DESC, avg_similarity DESC;
        """
        with conn.cursor() as cur:
            cur.execute(
                sql,
                {"query_vec": query_vector.tolist(), "top_k": top_k},
            )
            rows = cur.fetchall()

        if not rows:
            return None, 0.0

        # Defensive validation also keeps test/mocked product rows from being
        # mistaken for the aggregate rows returned by this query.
        valid_rows = [
            row for row in rows
            if len(row) >= 3
            and isinstance(row[0], str)
            and isinstance(row[1], (int, np.integer))
            and 0 < int(row[1]) <= top_k
            and isinstance(row[2], (int, float, np.integer, np.floating))
            and -1.0 <= float(row[2]) <= 1.0
        ]
        if not valid_rows:
            return None, 0.0

        total_votes = sum(int(row[1]) for row in valid_rows)
        winner = valid_rows[0]
        confidence = int(winner[1]) / total_votes if total_votes else 0.0
        if confidence < min_confidence:
            return None, round(confidence, 4)
        return str(winner[0]), round(confidence, 4)

    @staticmethod
    def build_sql(
        state: SearchState,
        has_vector: bool = True,
        query_type: str = "text",
        limit: int = 50,
        relaxed_colors: Optional[List[str]] = None,
        min_similarity: Optional[float] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """Constructs safe parameterized SQL with dynamic hard constraints and optional relaxation."""
        where_clauses: List[str] = []
        params: Dict[str, Any] = {"limit": limit}

        # 1. Gender constraint
        if state.gender and state.gender != "Unisex":
            where_clauses.append("p.gender = %(gender)s")
            params["gender"] = state.gender

        # 2. Price constraints
        if state.max_price is not None:
            where_clauses.append("p.price_vnd <= %(max_price)s")
            params["max_price"] = state.max_price
        if state.min_price is not None:
            where_clauses.append("p.price_vnd >= %(min_price)s")
            params["min_price"] = state.min_price

        # 3. Category constraint (P0 - Non-negotiable)
        if state.category == "Pants":
            where_clauses.append(
                "c.sub_category IN (%(pants_trousers)s, %(pants_shorts)s)"
            )
            params["pants_trousers"] = "Trousers"
            params["pants_shorts"] = "Shorts"
        elif state.category:
            where_clauses.append("(c.sub_category ILIKE %(category)s OR c.group_name ILIKE %(category)s)")
            params["category"] = f"%{state.category}%"

        # 4. Color positive constraint (P1 - Strict or Relaxed Family)
        if relaxed_colors:
            color_clauses = []
            for idx, c_val in enumerate(relaxed_colors):
                ckey = f"rel_col_{idx}"
                color_code = EntityNormalizer.get_color_code(c_val)
                if not color_code:
                    continue
                color_clauses.append(f"p.color_code = %({ckey})s")
                params[ckey] = color_code
            if color_clauses:
                where_clauses.append("(" + " OR ".join(color_clauses) + ")")
        elif state.color:
            color_code = EntityNormalizer.get_color_code(state.color)
            if color_code:
                where_clauses.append("p.color_code = %(color_code)s")
                params["color_code"] = color_code
            else:
                # An unknown requested color must not silently return unrelated colors.
                where_clauses.append("1 = 0")

        # 5. Exclude colors negative constraints
        if state.exclude_colors:
            for idx, exc_col in enumerate(state.exclude_colors):
                exc_code = EntityNormalizer.get_color_code(exc_col)
                if not exc_code:
                    continue
                param_key = f"exc_col_{idx}"
                where_clauses.append(f"p.color_code <> %({param_key})s")
                params[param_key] = exc_code

        col_target = "p.text_embedding" if query_type in ("text", "voice") else "p.image_embedding"

        # 6. Minimum Similarity Threshold Cutoff (P2 - Zero results safety)
        if min_similarity is not None and has_vector:
            where_clauses.append(f"(1 - ({col_target} <=> %(query_vec)s::vector)) >= %(min_sim)s")
            params["min_sim"] = min_similarity

        where_stmt = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        if has_vector:
            order_stmt = f"ORDER BY {col_target} <=> %(query_vec)s::vector ASC"
            select_dist = f"1 - ({col_target} <=> %(query_vec)s::vector) AS raw_sim"
        else:
            order_stmt = "ORDER BY p.price_vnd ASC"
            select_dist = "0.5 AS raw_sim"

        query = f"""
            SELECT 
                p.article_id,
                p.prod_name,
                p.price_vnd,
                p.gender,
                COALESCE(p.color_code, '') AS color_code,
                COALESCE(p.color_code, '') AS color_name,
                c.group_name,
                c.sub_category,
                p.image_path,
                COALESCE(p.detail_desc, '') AS detail_desc,
                {select_dist}
            FROM product p
            JOIN category c ON p.category_id = c.id
            {where_stmt}
            {order_stmt}
            LIMIT %(limit)s;
        """
        return query, params

    @classmethod
    def _execute_query(
        cls,
        conn: psycopg.Connection,
        sql: str,
        params: Dict[str, Any],
        match_type: str = "exact",
        similarity_reason: Optional[str] = None,
    ) -> List[SearchResultItem]:
        """Executes prepared SQL query and transforms rows into SearchResultItem candidates."""
        items: List[SearchResultItem] = []
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

            for row in rows:
                raw_sim = float(row[10]) if row[10] is not None else 0.5
                norm_sim = max(0.0, min(1.0, (raw_sim + 1.0) / 2.0 if raw_sim < 0 else raw_sim))

                items.append(
                    SearchResultItem(
                        article_id=str(row[0]),
                        prod_name=str(row[1]),
                        price_vnd=int(row[2]),
                        gender=str(row[3]),
                        color_code=str(row[4]),
                        color_name=EntityNormalizer.get_color_name(str(row[4])),
                        category_group=str(row[6]),
                        category_sub=str(row[7]),
                        image_path=str(row[8]),
                        detail_desc=str(row[9]),
                        visual_similarity=round(norm_sim, 4),
                        final_score=round(norm_sim, 4),
                        match_type=match_type,
                        similarity_reason=similarity_reason,
                    )
                )
        return items

    @classmethod
    def retrieve_partitioned(
        cls,
        conn: psycopg.Connection,
        state: SearchState,
        query_vector: Optional[np.ndarray] = None,
        query_type: str = "text",
        limit: int = 50,
        threshold_image: float = 0.65,
        threshold_text: float = 0.58,
    ) -> Tuple[List[SearchResultItem], List[SearchResultItem]]:
        """Executes 2-phase retrieval: Exact Match first; if empty, runs Controlled Relaxation."""
        has_vector = query_vector is not None

        # Phase 1: Strict Exact Query (P0 Category + P1 Exact Color/Price)
        sql_exact, params_exact = cls.build_sql(state, has_vector=has_vector, query_type=query_type, limit=limit)
        if has_vector and query_vector is not None:
            params_exact["query_vec"] = query_vector.tolist()

        exact_items = cls._execute_query(conn, sql_exact, params_exact, match_type="exact")

        if exact_items:
            logger.info("Phase 1: Found %d exact match products.", len(exact_items))
            return exact_items, []

        # Phase 2: Controlled Relaxation (Keep P0 Category invariant, relax P1 Color Family)
        logger.info("Phase 1 yielded 0 exact results. Initiating Phase 2 Controlled Relaxation...")
        relaxed_family = None
        sim_reason = None
        if state.color:
            relaxed_family = EntityNormalizer.get_color_family(state.color)
            sim_reason = f"Cùng loại sản phẩm {state.category or ''}, gợi ý màu sắc tương đồng"
        elif state.category:
            sim_reason = f"Cùng loại sản phẩm {state.category}, gợi ý theo độ tương đồng"

        # Adaptive Threshold based on Modality
        tau = threshold_image if query_type == "image" else threshold_text

        sql_similar, params_similar = cls.build_sql(
            state,
            has_vector=has_vector,
            query_type=query_type,
            limit=limit,
            relaxed_colors=relaxed_family,
            min_similarity=tau if has_vector else None,
        )
        if has_vector and query_vector is not None:
            params_similar["query_vec"] = query_vector.tolist()

        similar_items = cls._execute_query(
            conn,
            sql_similar,
            params_similar,
            match_type="similar",
            similarity_reason=sim_reason,
        )

        logger.info("Phase 2: Retrieved %d similar candidate products (Threshold >= %.2f).", len(similar_items), tau)
        return [], similar_items

    @classmethod
    def retrieve_candidates(
        cls,
        conn: psycopg.Connection,
        state: SearchState,
        query_vector: Optional[np.ndarray] = None,
        query_type: str = "text",
        limit: int = 50,
    ) -> List[SearchResultItem]:
        """Backward-compatible helper returning exact items or similar fallback."""
        exact_items, similar_items = cls.retrieve_partitioned(
            conn=conn,
            state=state,
            query_vector=query_vector,
            query_type=query_type,
            limit=limit,
        )
        return exact_items if exact_items else similar_items

    @classmethod
    def retrieve_from_csv_partitioned(
        cls,
        state: SearchState,
        csv_path: Optional[str] = None,
        limit: int = 50,
    ) -> Tuple[List[SearchResultItem], List[SearchResultItem]]:
        """In-memory fallback returning (exact_items, similar_items) from sample CSV."""
        import csv
        from pathlib import Path

        if csv_path:
            path = Path(csv_path)
            if not path.exists():
                return [], []
        else:
            path = Path("data/sample_articles.csv")
            if not path.exists():
                alt_path = Path(__file__).resolve().parent.parent.parent / "data" / "sample_articles.csv"
                if alt_path.exists():
                    path = alt_path
                else:
                    return [], []

        exact_candidates: List[SearchResultItem] = []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                gender = row.get("index_group_name", "Unisex")
                price = int(row.get("price_vnd", 499000))
                color = row.get("colour_group_name", "White")
                category_sub = row.get("product_type_name", "")
                category_group = row.get("product_group_name", "")
                desc = row.get("detail_desc", "")

                # 1. Gender filter
                if state.gender and state.gender != "Unisex" and gender != state.gender:
                    continue
                # 2. Price filter
                if state.max_price is not None and price > state.max_price:
                    continue
                if state.min_price is not None and price < state.min_price:
                    continue
                # 3. Category filter
                if state.category:
                    if state.category == "Pants":
                        if category_sub not in {"Trousers", "Shorts"}:
                            continue
                    else:
                        cat_lower = state.category.lower()
                        if cat_lower not in category_sub.lower() and cat_lower not in category_group.lower():
                            continue
                # 4. Color filter
                if state.color:
                    requested_code = EntityNormalizer.get_color_code(state.color)
                    row_code = str(row.get("colour_group_code", "")).zfill(2)
                    if not requested_code or row_code != requested_code:
                        continue
                # 5. Exclude colors
                if state.exclude_colors:
                    row_code = str(row.get("colour_group_code", "")).zfill(2)
                    excluded_codes = {
                        code for code in (
                            EntityNormalizer.get_color_code(exc) for exc in state.exclude_colors
                        ) if code
                    }
                    if row_code in excluded_codes:
                        continue

                exact_candidates.append(
                    SearchResultItem(
                        article_id=row.get("article_id", "0000000001"),
                        prod_name=row.get("prod_name", "Fashion Item"),
                        price_vnd=price,
                        gender=gender,
                        color_code=row.get("colour_group_code", "10"),
                        color_name=color,
                        category_group=category_group,
                        category_sub=category_sub,
                        image_path=row.get("image_path", ""),
                        detail_desc=desc,
                        visual_similarity=0.88,
                        final_score=0.88,
                        match_type="exact",
                    )
                )
                if len(exact_candidates) >= limit:
                    break

        if exact_candidates:
            return exact_candidates, []

        # If strict multi-filter yielded no candidates, search similar candidates (keep category, relax color)
        similar_candidates: List[SearchResultItem] = []
        color_family = EntityNormalizer.get_color_family(state.color) if state.color else []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                gender = row.get("index_group_name", "Unisex")
                category_sub = row.get("product_type_name", "")
                category_group = row.get("product_group_name", "")
                color = row.get("colour_group_name", "White")
                color_code = str(row.get("colour_group_code", "")).zfill(2)
                desc = row.get("detail_desc", "")

                # Keep P0 Category invariant
                if state.category:
                    if state.category == "Pants":
                        if category_sub not in {"Trousers", "Shorts"}:
                            continue
                    else:
                        cat_lower = state.category.lower()
                        if cat_lower not in category_sub.lower() and cat_lower not in category_group.lower():
                            continue

                # Check color family or general category match
                match = False
                if color_family:
                    if color_code in color_family:
                        match = True
                else:
                    match = True

                if match:
                    similar_candidates.append(
                        SearchResultItem(
                            article_id=row.get("article_id", "0000000001"),
                            prod_name=row.get("prod_name", "Fashion Item"),
                            price_vnd=int(row.get("price_vnd", 499000)),
                            gender=gender,
                            color_code=row.get("colour_group_code", "10"),
                            color_name=color,
                            category_group=category_group,
                            category_sub=category_sub,
                            image_path=row.get("image_path", ""),
                            detail_desc=desc,
                            visual_similarity=0.75,
                            final_score=0.75,
                            match_type="similar",
                            similarity_reason=f"Cùng danh mục {state.category or ''}, gợi ý màu sắc tương đồng",
                        )
                    )
                    if len(similar_candidates) >= limit:
                        break

        return [], similar_candidates

    @classmethod
    def retrieve_from_csv(
        cls,
        state: SearchState,
        csv_path: Optional[str] = None,
        limit: int = 50,
    ) -> List[SearchResultItem]:
        """In-memory fallback retrieving candidates from sample dataset."""
        exact, similar = cls.retrieve_from_csv_partitioned(state=state, csv_path=csv_path, limit=limit)
        return exact if exact else similar
