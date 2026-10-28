"""Unit and Contract-based Test Suite for Phase 2 Core Engine.

Verifies:
1. EntityNormalizer (Phonetic & dialect corrections, colors, categories, materials, prices).
2. IntentExtractor (LLM mocking, rule-based extraction, negative constraints, resilience).
3. Search audit persistence for independent requests.
4. CandidateRetriever (Parameterized SQL generation, pgvector HNSW integration).
5. SoftReranker & ResultExplainer (Scoring math, penalty deduction, bonus awards, badge generation).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from backend.core.extractor import IntentExtractor, build_canonical_query
from backend.core.normalizer import EntityNormalizer
from backend.core.reranker import ResultExplainer, SoftReranker
from backend.core.retriever import CandidateRetriever
from backend.core.search_audit import persist_search
from backend.schemas.state import QueryIntent, SearchResultItem, SearchState


class TestEntityNormalizer:
    """Verifies phonetic correction, dialect rules, and regex entity parsers."""

    def test_normalize_phonetics_dialects(self):
        assert EntityNormalizer.normalize_phonetics("dày da nam") == "giày da nam"
        assert EntityNormalizer.normalize_phonetics("bận áo thun") == "mặc áo thun"
        assert EntityNormalizer.normalize_phonetics("dưới 1 chiệu") == "dưới 1 triệu"
        assert EntityNormalizer.normalize_phonetics("dưới 2 chẹo") == "dưới 2 triệu"
        assert EntityNormalizer.normalize_phonetics("quờn tây") == "quần tây"
        assert EntityNormalizer.normalize_phonetics("") == ""

    def test_extract_color(self):
        # Direct English and Vietnamese
        assert EntityNormalizer.extract_color("áo màu đen") == ("09", "Black")
        assert EntityNormalizer.extract_color("white shirt") == ("10", "White")
        # Composite color takes precedence over single color
        assert EntityNormalizer.extract_color("áo thun xanh navy") == ("73", "Dark Blue")
        assert EntityNormalizer.extract_color("quần màu hồng") == ("52", "Pink")
        assert EntityNormalizer.get_color_name("51") == "Light Pink"
        assert EntityNormalizer.get_color_name("52") == "Pink"
        assert EntityNormalizer.extract_color("áo màu đồng") == ("04", "Bronze/Copper")
        assert EntityNormalizer.extract_color("giá 199.000 đồng") is None
        # Non-existent color
        assert EntityNormalizer.extract_color("áo màu cầu vồng") is None

    def test_extract_category(self):
        assert EntityNormalizer.extract_category("áo thun cổ tròn") == ("Garment Upper body", "T-shirt")
        assert EntityNormalizer.extract_category("quần jean ống rộng") == ("Garment Lower body", "Trousers")
        assert EntityNormalizer.extract_category("quần đùi ngắn") == ("Garment Lower body", "Shorts")
        assert EntityNormalizer.extract_category("quần ngắn") == ("Garment Lower body", "Shorts")
        assert EntityNormalizer.extract_category("quần soóc") == ("Garment Lower body", "Shorts")
        assert EntityNormalizer.extract_category("short pants") == ("Garment Lower body", "Shorts")
        assert EntityNormalizer.extract_category("quần này") == ("Garment Lower body", "Pants")
        assert EntityNormalizer.extract_category("áo blazer nữ") == ("Garment Upper body", "Blazer")
        assert EntityNormalizer.extract_category("giày nữ") == ("Shoes", "Shoes")
        assert EntityNormalizer.extract_category("giày sneaker thể thao") == ("Shoes", "Sneakers")
        assert EntityNormalizer.extract_category("váy dạ hội") == ("Garment Full body", "Dress")
        # Bags are not present in the current 1,000-product catalog.
        assert EntityNormalizer.extract_category("balo du lịch") is None
        assert EntityNormalizer.extract_category("đồng hồ đeo tay") is None

    def test_normalize_material(self):
        assert EntityNormalizer.normalize_material("áo da") == "leather"
        assert EntityNormalizer.normalize_material("quần bò") == "denim"
        assert EntityNormalizer.normalize_material("vải cotton mát mẻ") == "cotton"
        assert EntityNormalizer.normalize_material("túi vải bố") == "canvas"
        assert EntityNormalizer.normalize_material("chất liệu kim loại") is None

    def test_parse_vnd_price(self):
        assert EntityNormalizer.parse_vnd_price("dưới 1 triệu") == 1_000_000
        assert EntityNormalizer.parse_vnd_price("khoảng 1.5tr") == 1_500_000
        assert EntityNormalizer.parse_vnd_price("tầm 500k") == 500_000
        assert EntityNormalizer.parse_vnd_price("800 nghìn") == 800_000
        assert EntityNormalizer.parse_vnd_price("giá 499000") == 499_000
        assert EntityNormalizer.parse_vnd_price("không có giá") is None


class TestIntentExtractor:
    """Verifies intent extraction, negative constraints, and LLM fallbacks."""

    def test_empty_query(self):
        extractor = IntentExtractor(use_mock=True)
        intent = extractor.extract("")
        assert intent.raw_query == ""
        assert intent.category is None

    def test_rule_based_negative_and_positive_constraints(self):
        extractor = IntentExtractor(use_mock=True)
        # Query with negative color and negative material
        query = "tìm giày sneaker màu trắng không phải da không màu đen dưới 1 triệu"
        intent = extractor.extract(query)

        assert intent.category == "Sneakers"
        assert intent.color == "White"
        assert "Black" in intent.exclude_colors
        assert "leather" in intent.exclude_materials
        assert intent.max_price == 1_000_000

    def test_rule_based_gender_and_category(self):
        extractor = IntentExtractor(use_mock=True)
        query = "tìm áo thun nam giống số 2"
        intent = extractor.extract(query)

        assert intent.gender == "Menswear"
        assert intent.category == "T-shirt"

    def test_rule_based_chitchat_is_not_a_product_search(self):
        intent = IntentExtractor(use_mock=True).extract("Xin chào, bạn có khỏe không?")
        assert intent.intent_type == "conversation"
        assert intent.category is None

    def test_generic_pants_query_keeps_a_pants_family_constraint(self):
        intent = IntentExtractor(use_mock=True).extract("tìm quần màu hồng")
        assert intent.intent_type == "product_search"
        assert intent.category == "Pants"
        assert intent.color == "Pink"

    def test_reconcile_drops_provider_color_inferred_from_currency(self):
        intent = QueryIntent(
            raw_query="Tìm áo sơ mi có giá 199.000 đồng",
            normalized_query="Tìm áo sơ mi có giá 199.000 đồng",
            category="Shirt",
            color="Bronze/Copper",
            min_price=199_000,
            max_price=199_000,
        )

        resolved = IntentExtractor._reconcile_intent(
            intent,
            intent.normalized_query,
        )

        assert resolved.category == "Shirt"
        assert resolved.color is None
        assert resolved.min_price == 199_000
        assert resolved.max_price == 199_000

    def test_build_canonical_query_uses_structured_semantic_fields_only(self):
        intent = QueryIntent(
            raw_query="Tìm cho tôi quần màu hồng dưới 1 triệu",
            normalized_query="Tìm cho tôi quần màu hồng dưới 1 triệu",
            category="Pants",
            color="Pink",
            max_price=1_000_000,
            exclude_colors=["Black"],
        )

        assert build_canonical_query(intent) == "pants trousers shorts, pink"

    @patch("openai.OpenAI")
    def test_openai_conversation_intent_is_preserved(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.parsed = QueryIntent(intent_type="conversation")
        mock_response.choices = [mock_choice]
        mock_client.beta.chat.completions.parse.return_value = mock_response

        intent = IntentExtractor(
            openai_api_key="mock_key",
            use_mock=False,
        ).extract("Xin chào, bạn có khỏe không?")

        assert intent.intent_type == "conversation"

    @patch("openai.OpenAI")
    def test_openai_extraction_success(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_parsed = QueryIntent(
            raw_query="áo blazer nữ",
            normalized_query="áo blazer nữ",
            category="Jacket",
            gender="Ladieswear",
        )
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.parsed = mock_parsed
        mock_response.choices = [mock_choice]
        mock_client.beta.chat.completions.parse.return_value = mock_response

        extractor = IntentExtractor(openai_api_key="mock_key", use_mock=False)
        intent = extractor.extract("áo blazer nữ")

        assert intent.category == "Blazer"
        assert intent.gender == "Ladieswear"

    @patch("openai.OpenAI")
    def test_openai_output_is_reconciled_with_explicit_short_category(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.parsed = QueryIntent(
            category="Trousers",
            gender="Unisex",
            color="White",
            max_price=1_000_000,
        )
        mock_response.choices = [mock_choice]
        mock_client.beta.chat.completions.parse.return_value = mock_response

        intent = IntentExtractor(
            openai_api_key="mock_key",
            use_mock=False,
        ).extract("quần short màu trắng dưới 1 triệu")

        assert intent.category == "Shorts"
        assert intent.gender is None
        assert intent.color == "White"
        assert intent.max_price == 1_000_000

    @patch("openai.OpenAI")
    def test_openai_failure_fallback_to_rule_based(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.beta.chat.completions.parse.side_effect = RuntimeError("OpenAI API timeout")

        extractor = IntentExtractor(openai_api_key="mock_key", use_mock=False)
        # Should gracefully fallback to rule-based without raising
        intent = extractor.extract("áo thun màu trắng dưới 500k")
        assert intent.color == "White"
        assert intent.max_price == 500_000


class TestSearchAudit:
    """Verifies audit persistence without conversational session state."""

    def test_persist_search_db(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        state = SearchState(category="Sneakers")
        persist_search(
            conn=mock_conn,
            state=state,
            raw_query="giày sneaker",
            latency_ms=120,
        )
        assert mock_cur.execute.call_count == 2
        assert mock_conn.commit.called


class TestCandidateRetriever:
    """Verifies SQL generation with hard constraints and vector similarity order."""

    def test_build_sql_with_all_hard_filters(self):
        state = SearchState(
            gender="Ladieswear",
            category="Dress",
            color="Red",
            max_price=1_000_000,
            min_price=200_000,
            exclude_colors=["Black", "Grey"],
        )
        # Test default text query type
        sql_text, params = CandidateRetriever.build_sql(state, has_vector=True, query_type="text", limit=20)
        assert "p.gender = %(gender)s" in sql_text
        assert "p.price_vnd <= %(max_price)s" in sql_text
        assert "p.price_vnd >= %(min_price)s" in sql_text
        assert "ORDER BY p.text_embedding <=> %(query_vec)s::vector ASC" in sql_text
        assert "1 - (p.text_embedding <=> %(query_vec)s::vector) AS raw_sim" in sql_text
        assert params["gender"] == "Ladieswear"
        assert params["max_price"] == 1_000_000
        assert "exc_col_0" in params
        assert "exc_col_1" in params

        # Test image query type
        sql_img, _ = CandidateRetriever.build_sql(state, has_vector=True, query_type="image", limit=20)
        assert "ORDER BY p.image_embedding <=> %(query_vec)s::vector ASC" in sql_img
        assert "1 - (p.image_embedding <=> %(query_vec)s::vector) AS raw_sim" in sql_img

    def test_build_sql_generic_pants_excludes_shoes_and_skirts(self):
        sql, params = CandidateRetriever.build_sql(
            SearchState(category="Pants", color="Pink"),
            has_vector=False,
        )

        assert "c.sub_category IN" in sql
        assert params["pants_trousers"] == "Trousers"
        assert params["pants_shorts"] == "Shorts"
        assert params["color_code"] == EntityNormalizer.get_color_code("Pink")

    def test_build_sql_uses_exact_catalog_category_matching(self):
        shirt_sql, shirt_params = CandidateRetriever.build_sql(
            SearchState(category="Shirt"),
            has_vector=False,
        )
        shoes_sql, shoes_params = CandidateRetriever.build_sql(
            SearchState(category="Shoes"),
            has_vector=False,
        )

        assert "c.sub_category = %(category)s" in shirt_sql
        assert "ILIKE" not in shirt_sql
        assert shirt_params["category"] == "Shirt"
        assert "c.group_name = %(category)s" in shoes_sql
        assert shoes_params["category"] == "Shoes"

    def test_retrieve_candidates_mock_db(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchall.return_value = [
            (
                "0123456789", "Cotton T-shirt", 299000, "Ladieswear",
                "10", "White", "Garment Upper body", "T-shirt",
                "images/0123456789.jpg", "100% cotton fabric", 0.88,
            )
        ]

        state = SearchState(category="T-shirt")
        dummy_vec = np.ones(768, dtype=np.float32)

        items = CandidateRetriever.retrieve_candidates(mock_conn, state, query_vector=dummy_vec, limit=10)
        assert len(items) == 1
        assert items[0].article_id == "0123456789"
        assert items[0].price_vnd == 299000
        assert items[0].visual_similarity == 0.88

    def test_infer_category_from_image_neighbor_vote(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchall.return_value = [
            ("Trousers", 16, 0.81),
            ("Shorts", 3, 0.73),
            ("Skirt", 1, 0.68),
        ]

        category, confidence = CandidateRetriever.infer_category_from_image(
            mock_conn,
            np.ones(768, dtype=np.float32),
        )

        assert category == "Trousers"
        assert confidence == 0.8

    def test_infer_category_from_image_rejects_ambiguous_vote(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchall.return_value = [
            ("Trousers", 10, 0.81),
            ("Shorts", 9, 0.80),
            ("Skirt", 1, 0.70),
        ]

        category, confidence = CandidateRetriever.infer_category_from_image(
            mock_conn,
            np.ones(768, dtype=np.float32),
        )

        assert category is None
        assert confidence == 0.5


class TestSoftRerankerAndExplainer:
    """Verifies math scoring formula, penalty logic, and badge creation."""

    def create_dummy_item(self, desc: str, price: int = 400_000, sim: float = 0.9) -> SearchResultItem:
        return SearchResultItem(
            article_id="001",
            prod_name="Test Product",
            price_vnd=price,
            gender="Ladieswear",
            color_code="10",
            color_name="White",
            category_group="Garment Upper body",
            category_sub="T-shirt",
            image_path="images/001.jpg",
            detail_desc=desc,
            visual_similarity=sim,
        )

    def test_reranker_penalty_violation(self):
        # Item contains leather
        item = self.create_dummy_item("Genuine leather jacket with zipper")
        state = SearchState(exclude_materials=["leather"])

        score, penalty_applied = SoftReranker.calculate_item_score(item, state)
        assert penalty_applied is True
        badges = ResultExplainer.generate_badges(item, state, penalty_applied)
        assert any("Dính chất liệu loại trừ" in b for b in badges)

    def test_reranker_bonus_material(self):
        item = self.create_dummy_item("Premium 100% cotton t-shirt")
        state = SearchState(material="cotton", color="White", max_price=500_000)

        score, penalty_applied = SoftReranker.calculate_item_score(item, state)
        assert penalty_applied is False
        badges = ResultExplainer.generate_badges(item, state, penalty_applied)

        assert any("Màu White" in b for b in badges)
        assert any("Dưới 500k" in b for b in badges)
        assert any("Chất liệu Cotton" in b for b in badges)

    def test_rerank_sorts_descending(self):
        item_bad = self.create_dummy_item("Heavy leather coat", price=900_000, sim=0.7)
        item_good = self.create_dummy_item("Cool soft cotton shirt", price=300_000, sim=0.85)

        state = SearchState(material="cotton", exclude_materials=["leather"])
        reranked = SoftReranker.rerank([item_bad, item_good], state)

        assert reranked[0].article_id == item_good.article_id
        assert reranked[0].final_score > reranked[1].final_score


class TestPhase2MultimodalLogicAdditions:
    """Verifies contour polygon extraction, color family map, and partitioned retrieval with threshold cutoff."""

    def test_extract_contour_polygon_structure(self):
        from backend.core.detector import ObjectDetector
        from PIL import Image

        # Create dummy image
        img = Image.new("RGB", (200, 200), color=(255, 255, 255))
        box_2d = [0.1, 0.1, 0.9, 0.9]

        polygon = ObjectDetector.extract_contour_polygon(img, box_2d, num_rays=16)
        assert isinstance(polygon, list)
        assert len(polygon) == 16
        for pt in polygon:
            assert len(pt) == 2
            x, y = pt
            assert 0.0 <= x <= 1.0
            assert 0.0 <= y <= 1.0

    def test_color_family_expansion_in_normalizer(self):
        from backend.core.normalizer import EntityNormalizer

        # Relaxation stays inside the light/regular/dark dataset family.
        beige_family = EntityNormalizer.get_color_family("Beige")
        assert beige_family == ["12", "13", "14", "15"]

        pink_family = EntityNormalizer.get_color_family("Pink")
        assert pink_family == ["51", "52", "53"]

        black_family = EntityNormalizer.get_color_family("Black")
        assert "09" in black_family

    def test_retrieve_from_csv_partitioned_logic(self):
        # Case A: Exact search where matching items exist
        state_exact = SearchState(
            category="Trousers",
            color="White",
        )
        exact_items, similar_items = CandidateRetriever.retrieve_from_csv_partitioned(state_exact, limit=20)
        assert len(exact_items) > 0
        for item in exact_items:
            assert item.match_type == "exact"
            assert "white" in item.color_name.lower()
            assert "trouser" in item.category_sub.lower() or "trouser" in item.prod_name.lower()

        # Case B: Category invariant: if category does not exist, both must be empty (stops cleanly)
        state_nonexistent = SearchState(
            category="NonExistentCategory999",
            color="Beige",
        )
        exact_empty, similar_empty = CandidateRetriever.retrieve_from_csv_partitioned(state_nonexistent, limit=20)
        assert len(exact_empty) == 0
        assert len(similar_empty) == 0

    def test_retrieve_partitioned_sql_generation(self):
        state = SearchState(
            category="Trousers",
            color="Beige",
        )
        # Phase 1 SQL: strict color
        sql_exact, params_exact = CandidateRetriever.build_sql(
            state, has_vector=True, query_type="text", min_similarity=0.58
        )
        assert "p.color_code = %(color_code)s" in sql_exact
        assert params_exact["color_code"] == "13"
        assert f"(1 - (p.text_embedding <=> %(query_vec)s::vector)) >= %(min_sim)s" in sql_exact
        assert params_exact["min_sim"] == 0.58

        # Phase 2 SQL: relaxed colors
        sql_relaxed, params_relaxed = CandidateRetriever.build_sql(
            state,
            has_vector=True,
            query_type="text",
            min_similarity=0.58,
            relaxed_colors=EntityNormalizer.get_color_family("Beige"),
        )
        assert "rel_col_0" in params_relaxed
        assert "rel_col_1" in params_relaxed
        assert params_relaxed["rel_col_0"] == "12"
        assert params_relaxed["rel_col_1"] == "13"
        assert f"(1 - (p.text_embedding <=> %(query_vec)s::vector)) >= %(min_sim)s" in sql_relaxed

