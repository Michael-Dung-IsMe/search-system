"""End-to-end tests for independent multimodal searches and fallbacks."""

from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.core.detector import ObjectDetector
from backend.core.embedder import MultimodalEmbedder
from backend.core.retriever import CandidateRetriever
from backend.core.transcriber import SpeechTranscriber
from backend.main import app
from backend.schemas.state import SearchState
from scripts.benchmark_e2e import create_sample_outfit_image, get_gpu_memory_mb, run_benchmark


@pytest.fixture(scope="module")
def client():
    """FastAPI client with mock inference models for deterministic tests."""
    ObjectDetector.get_instance(use_mock=True)
    MultimodalEmbedder.get_instance(use_mock=True)
    SpeechTranscriber.get_instance(use_mock=True)
    return TestClient(app)


class TestPhase5EndToEndScenario:
    """Verify one-shot image+text and voice search flows."""

    def test_independent_multimodal_scenario(self, client):
        outfit_bytes = create_sample_outfit_image()

        detection = client.post(
            "/api/detect",
            files={"file": ("outfit.jpg", outfit_bytes, "image/jpeg")},
        )
        assert detection.status_code == 200
        detection_json = detection.json()
        assert detection_json["total_boxes"] >= 1
        crop_coords = detection_json["boxes"][0]["box_2d"]

        search = client.post(
            "/api/search",
            data={
                "query_text": "Tìm quần màu trắng dưới 1 triệu",
                "crop_box": json.dumps(crop_coords),
            },
            files={"image": ("outfit.jpg", outfit_bytes, "image/jpeg")},
        )
        assert search.status_code == 200
        search_json = search.json()
        assert "session_id" not in search_json
        assert "turn_index" not in search_json
        assert search_json["query_type"] == "image"
        assert search_json["search_state"]["color"] == "White"
        assert search_json["search_state"]["max_price"] == 1_000_000

        audio_dummy = (
            b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
            b"\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
        )
        transcription = client.post(
            "/api/transcribe",
            files={"file": ("speech.wav", audio_dummy, "audio/wav")},
        )
        assert transcription.status_code == 200
        transcript = transcription.json()["text"]

        voice_search = client.post(
            "/api/search",
            data={"query_text": transcript, "query_type": "voice"},
        )
        assert voice_search.status_code == 200
        voice_json = voice_search.json()
        assert voice_json["query_type"] == "voice"

        fresh_search = client.post(
            "/api/search",
            data={"query_text": "Tìm áo màu đen"},
        )
        assert fresh_search.status_code == 200
        fresh_state = fresh_search.json()["search_state"]
        assert fresh_state["color"] == "Black"
        assert fresh_state["max_price"] is None


class TestCandidateRetrieverFallback:
    """Verify in-memory CSV candidate retrieval fallback."""

    def test_retrieve_from_csv_filtering_rules(self):
        state = SearchState(
            gender="Menswear",
            color="White",
            max_price=1_500_000,
            category="Trousers",
            exclude_colors=["Black"],
        )

        candidates = CandidateRetriever.retrieve_from_csv(state, limit=10)
        assert isinstance(candidates, list)
        for candidate in candidates:
            assert candidate.gender == "Menswear"
            assert "white" in candidate.color_name.lower()
            assert candidate.price_vnd <= 1_500_000
            assert "black" not in candidate.color_name.lower()

    def test_retrieve_from_csv_empty_when_no_match(self):
        state = SearchState(
            category="NonexistentCategoryXYZ",
            color="NonexistentColorXYZ",
        )
        candidates = CandidateRetriever.retrieve_from_csv(state, limit=10)
        assert candidates == []

    def test_retrieve_from_csv_nonexistent_file(self):
        candidates = CandidateRetriever.retrieve_from_csv(
            SearchState(), csv_path="nonexistent_sample.csv"
        )
        assert candidates == []


class TestBenchmarkScriptHelpers:
    """Verify standalone benchmark helper functions."""

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
        with patch(
            "scripts.benchmark_e2e.create_sample_outfit_image",
            return_value=create_sample_outfit_image(),
        ):
            summary = run_benchmark(use_mock=True)
            assert "hardware" in summary
            assert "performance" in summary
            assert summary["performance"]["total_steps"] == 6
            assert Path("docs/benchmark_results.json").exists()
