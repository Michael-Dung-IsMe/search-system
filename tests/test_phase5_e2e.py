"""End-to-End Walkthrough and Scenario Integration Test Suite (Phase 5).

Verifies the complete 6-step conversational multimodal user scenario:
1. Step 1: Upload outfit image & OWL-ViT detection.
2. Step 2: Initial visual search using cropped garment.
3. Step 3: Multi-turn conversational refinement with hard filters (color, price).
4. Step 4: Reference ordinal resolution & negative constraints ("không phải da").
5. Step 5: Interactive constraint chip removal ([X] button) and dynamic re-ranking.
6. Step 6: Voice transcription via Whisper and unified search execution.
7. Resilience & CSV fallback verification under missing database conditions.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.core.detector import ObjectDetector
from backend.core.embedder import MultimodalEmbedder
from backend.core.retriever import CandidateRetriever
from backend.core.transcriber import SpeechTranscriber
from backend.main import app
from backend.schemas.state import ConstraintChip, SearchState
from scripts.benchmark_e2e import create_sample_outfit_image, get_gpu_memory_mb, run_benchmark


@pytest.fixture(scope="module")
def client():
    """FastAPI test client with mock inference models for rapid automated testing."""
    ObjectDetector.get_instance(use_mock=True)
    MultimodalEmbedder.get_instance(use_mock=True)
    SpeechTranscriber.get_instance(use_mock=True)
    return TestClient(app)


class TestPhase5EndToEndScenario:
    """Verifies the complete 6-step multi-turn shopping search scenario."""

    def test_complete_six_step_multimodal_scenario(self, client):
        outfit_bytes = create_sample_outfit_image()

        # Step 1: Detect objects from uploaded outfit
        resp_detect = client.post(
            "/api/detect",
            files={"file": ("outfit.jpg", outfit_bytes, "image/jpeg")},
        )
        assert resp_detect.status_code == 200
        detect_json = resp_detect.json()
        assert detect_json["total_boxes"] >= 1
        box = detect_json["boxes"][0]
        crop_coords = box["box_2d"]
        assert len(crop_coords) == 4

        # Step 2: Initial search with selected garment box
        resp_turn1 = client.post(
            "/api/search",
            data={
                "query_text": "Tìm đôi giống thế này",
                "crop_box": json.dumps(crop_coords),
            },
            files={"image": ("outfit.jpg", outfit_bytes, "image/jpeg")},
        )
        assert resp_turn1.status_code == 200
        turn1_json = resp_turn1.json()
        session_id = turn1_json["session_id"]
        assert session_id is not None
        assert turn1_json["turn_index"] == 1
        assert len(turn1_json["items"]) > 0
        top1_id = turn1_json["items"][0]["article_id"]

        # Step 3: Conversational refinement: "Màu trắng, dưới 1 triệu"
        resp_turn2 = client.post(
            "/api/search",
            data={
                "session_id": session_id,
                "query_text": "Màu trắng, dưới 1 triệu",
            },
        )
        assert resp_turn2.status_code == 200
        turn2_json = resp_turn2.json()
        state2 = turn2_json["search_state"]
        assert turn2_json["turn_index"] == 2
        assert state2["color"] == "White"
        assert state2["max_price"] == 1000000

        # Step 4: Negative constraint + reference: "Giống số 1 nhưng thể thao hơn, không phải da"
        resp_turn3 = client.post(
            "/api/search",
            data={
                "session_id": session_id,
                "query_text": "Giống số 1 nhưng thể thao hơn, không phải da",
            },
        )
        assert resp_turn3.status_code == 200
        turn3_json = resp_turn3.json()
        state3 = turn3_json["search_state"]
        assert state3["reference_article_id"] == turn2_json["items"][0]["article_id"]
        assert "leather" in state3["exclude_materials"]

        # Check negative constraint chip is generated
        chips = state3.get("active_chips", [])
        exclude_chips = [c for c in chips if c["chip_type"] == "exclude_material"]
        assert len(exclude_chips) >= 1
        chip_to_remove = exclude_chips[0]["chip_id"]

        # Step 5: Interactive chip deletion: Remove negative constraint chip
        resp_delete = client.delete(
            f"/api/search/{session_id}/constraint",
            params={"chip_id": chip_to_remove},
        )
        assert resp_delete.status_code == 200
        delete_json = resp_delete.json()
        state5 = delete_json["search_state"]
        assert chip_to_remove not in [c["chip_id"] for c in state5.get("active_chips", [])]
        assert "leather" not in state5["exclude_materials"]

        # Step 6: Audio recording -> transcribe -> search
        audio_dummy = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
        resp_audio = client.post(
            "/api/transcribe",
            files={"file": ("speech.wav", audio_dummy, "audio/wav")},
        )
        assert resp_audio.status_code == 200
        transcript = resp_audio.json().get("text")
        assert transcript is not None

        resp_turn6 = client.post(
            "/api/search",
            data={
                "session_id": session_id,
                "query_text": transcript or "quần jeans xanh",
            },
        )
        assert resp_turn6.status_code == 200
        turn6_json = resp_turn6.json()
        assert turn6_json["turn_index"] == 4
        assert len(turn6_json["items"]) > 0


class TestCandidateRetrieverFallback:
    """Verifies in-memory CSV candidate retrieval fallback."""

    def test_retrieve_from_csv_filtering_rules(self):
        state = SearchState(
            session_id="test-csv",
            turn_index=1,
            gender="Menswear",
            color="White",
            max_price=1500000,
            category="Trousers",
            exclude_colors=["Black"],
        )

        candidates = CandidateRetriever.retrieve_from_csv(state, limit=10)
        assert isinstance(candidates, list)
        for c in candidates:
            assert c.gender == "Menswear"
            assert "white" in c.color_name.lower()
            assert c.price_vnd <= 1500000
            assert "black" not in c.color_name.lower()

    def test_retrieve_from_csv_empty_when_no_match(self):
        state = SearchState(
            session_id="test-empty",
            turn_index=1,
            category="NonexistentCategoryXYZ",
            color="NonexistentColorXYZ",
        )
        candidates = CandidateRetriever.retrieve_from_csv(state, limit=10)
        assert len(candidates) == 0

    def test_retrieve_from_csv_nonexistent_file(self):
        state = SearchState(session_id="test-none")
        candidates = CandidateRetriever.retrieve_from_csv(
            state, csv_path="nonexistent_sample.csv"
        )
        assert candidates == []


class TestBenchmarkScriptHelpers:
    """Verifies the standalone benchmark helper functions."""

    def test_gpu_memory_structure(self):
        gpu_info = get_gpu_memory_mb()
        assert "device" in gpu_info
        assert "allocated_mb" in gpu_info
        assert "reserved_mb" in gpu_info
        assert isinstance(gpu_info["allocated_mb"], float)

    def test_create_sample_outfit_image_format(self):
        img_bytes = create_sample_outfit_image()
        assert len(img_bytes) > 500
        pil_img = Image.open(io.BytesIO(img_bytes))
        assert pil_img.size == (640, 800)
        assert pil_img.format == "JPEG"

    def test_run_benchmark_mocked_execution(self):
        with patch("scripts.benchmark_e2e.create_sample_outfit_image", return_value=create_sample_outfit_image()):
            summary = run_benchmark(use_mock=True)
            assert "hardware" in summary
            assert "performance" in summary
            assert summary["performance"]["total_steps"] == 6
            assert Path("docs/benchmark_results.json").exists()
