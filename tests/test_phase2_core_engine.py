"""Unit and Contract-based Test Suite for Phase 2 Core Engine.

Verifies:
1. EntityNormalizer (Phonetic & dialect corrections, colors, categories, materials, prices).
2. IntentExtractor (LLM mocking, rule-based extraction, negative constraints, resilience).
3. StateManager (Multi-turn merging, cumulative excludes, chip generation & removal, DB audit).
4. CandidateRetriever (Parameterized SQL generation, pgvector HNSW integration).
5. SoftReranker & ResultExplainer (Scoring math, penalty deduction, bonus awards, badge generation).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from backend.core.extractor import IntentExtractor
from backend.core.normalizer import EntityNormalizer
from backend.core.reranker import ResultExplainer, SoftReranker
from backend.core.retriever import CandidateRetriever
from backend.core.state_manager import StateManager
from backend.schemas.state import ConstraintChip, QueryIntent, SearchResultItem, SearchState


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
        assert EntityNormalizer.extract_color("áo thun xanh navy") == ("14", "Dark Blue")
        # Non-existent color
        assert EntityNormalizer.extract_color("áo màu cầu vồng") is None

    def test_extract_category(self):
        assert EntityNormalizer.extract_category("áo thun cổ tròn") == ("Garment Upper body", "T-shirt")
        assert EntityNormalizer.extract_category("quần jean ống rộng") == ("Garment Lower body", "Trousers")
        assert EntityNormalizer.extract_category("giày sneaker thể thao") == ("Shoes", "Sneakers")
        assert EntityNormalizer.extract_category("váy dạ hội") == ("Garment Full body", "Dress")
        assert EntityNormalizer.extract_category("balo du lịch") == ("Bags", "Backpack")
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

    def test_rule_based_gender_and_reference_ordinal(self):
        extractor = IntentExtractor(use_mock=True)
        query = "tìm áo thun nam giống số 2"
        intent = extractor.extract(query)

        assert intent.gender == "Menswear"
        assert intent.category == "T-shirt"
        assert intent.reference_ordinal == 2

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

        assert intent.category == "Jacket"
        assert intent.gender == "Ladieswear"

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


class TestStateManager:
    """Verifies conversational multi-turn state transitions, chip handling, and audit logs."""

    def test_multi_turn_state_merging(self):
        state = SearchState()

        # Turn 1: Search for white t-shirt
        intent_1 = QueryIntent(
            raw_query="áo thun màu trắng",
            category="T-shirt",
            color="White",
        )
        state_1 = StateManager.merge_intent(state, intent_1)
        assert state_1.turn_index == 1
        assert state_1.category == "T-shirt"
        assert state_1.color == "White"
        assert len(state_1.active_chips) >= 2

        # Turn 2: Add price constraint and negative material
        intent_2 = QueryIntent(
            raw_query="dưới 500k không phải da",
            max_price=500_000,
            exclude_materials=["leather"],
        )
        state_2 = StateManager.merge_intent(state_1, intent_2)
        assert state_2.turn_index == 2
        # Previous attributes are preserved
        assert state_2.category == "T-shirt"
        assert state_2.color == "White"
        assert state_2.max_price == 500_000
        assert "leather" in state_2.exclude_materials

        # Turn 3: User says 'không màu trắng' -> should clear color and append to exclude_colors
        intent_3 = QueryIntent(
            raw_query="đổi sang không màu trắng",
            exclude_colors=["White"],
        )
        state_3 = StateManager.merge_intent(state_2, intent_3)
        assert state_3.color is None
        assert "White" in state_3.exclude_colors

    def test_reference_ordinal_resolution(self):
        state = SearchState()
        previous_articles = ["0123456789", "0987654321", "0112233445"]

        intent = QueryIntent(
            raw_query="tìm giống số 2",
            reference_ordinal=2,
        )
        updated = StateManager.merge_intent(state, intent, previous_results=previous_articles)
        assert updated.reference_article_id == "0987654321"

    def test_remove_constraint_chips(self):
        state = SearchState(
            category="T-shirt",
            color="Black",
            max_price=1_000_000,
            exclude_materials=["leather"],
            gender="Menswear",
        )
        state.active_chips = StateManager.generate_chips(state)

        # Remove color chip
        state_after_color = StateManager.remove_constraint(state, "color:Black")
        assert state_after_color.color is None
        assert state_after_color.category == "T-shirt"

        # Remove max_price chip
        state_after_price = StateManager.remove_constraint(state_after_color, "max_price:1000000")
        assert state_after_price.max_price is None

        # Remove exclude_material chip
        state_after_exc = StateManager.remove_constraint(state_after_price, "exclude_material:leather")
        assert len(state_after_exc.exclude_materials) == 0

    def test_persist_turn_db(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        state = SearchState(turn_index=1, category="Sneakers")
        StateManager.persist_turn(
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

        # Beige family contains Cream, Khaki, Off White
        beige_family = EntityNormalizer.get_color_family("Beige")
        assert "Beige" in beige_family
        assert any(c in beige_family for c in ["Cream", "Khaki", "Off White"])

        # Black family
        black_family = EntityNormalizer.get_color_family("Black")
        assert "Black" in black_family

    def test_retrieve_from_csv_partitioned_logic(self):
        # Case A: Exact search where matching items exist
        state_exact = SearchState(
            session_id="test-partition-1",
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
            session_id="test-partition-2",
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
        assert "p.color_code ILIKE %(color)s" in sql_exact
        assert f"(1 - (p.text_embedding <=> %(query_vec)s::vector)) >= %(min_sim)s" in sql_exact
        assert params_exact["min_sim"] == 0.58

        # Phase 2 SQL: relaxed colors
        sql_relaxed, params_relaxed = CandidateRetriever.build_sql(
            state, has_vector=True, query_type="text", min_similarity=0.58, relaxed_colors=["Beige", "Cream", "Khaki"]
        )
        assert "rel_col_0" in params_relaxed
        assert "rel_col_1" in params_relaxed
        assert f"(1 - (p.text_embedding <=> %(query_vec)s::vector)) >= %(min_sim)s" in sql_relaxed

