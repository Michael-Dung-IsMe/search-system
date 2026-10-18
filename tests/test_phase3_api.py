"""Integration and Contract-based Test Suite for Phase 3 API Gateway.

Verifies:
1. System endpoints (Health check, Static file mounts, Structured error handlers).
2. /api/detect (Valid image upload, normalized boxes, MD5 caching, empty/invalid file rejection).
3. /api/transcribe (Audio upload, speech-to-text transcript, empty file handling).
4. /api/search Lifecycle (Text search, Image search, Crop-box integration, Multi-turn session).
5. /api/search/{session_id}/constraint (Interactive chip removal, 404 handling).
6. /api/products/{id} (Product detail lookup, 404 handling).
7. Detector and Embedder helpers (Bounding box cropping, Unit normalization).
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.core.detector import ObjectDetector
from backend.core.embedder import MultimodalEmbedder
from backend.core.transcriber import SpeechTranscriber
from backend.main import app
from backend.schemas.state import SearchResultItem


@pytest.fixture(scope="module")
def client():
    """FastAPI test client fixture."""
    ObjectDetector.get_instance(use_mock=True)
    MultimodalEmbedder.get_instance(use_mock=True)
    SpeechTranscriber.get_instance(use_mock=True)
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Helper fixture providing correctly configured context-managed db connection and cursor."""
    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    return mock_conn, mock_cur


@pytest.fixture
def sample_image_bytes():
    """Creates in-memory JPEG image bytes."""
    img = Image.new("RGB", (200, 300), color=(120, 150, 180))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestSystemEndpoints:
    """Verifies health check, static file hosting, and error handling."""

    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "Interactive Multimodal" in data["service"]

    def test_static_image_serving(self, client):
        img_path = Path("data/images/test_mock_serving.jpg")
        img = Image.new("RGB", (50, 50), color="red")
        img.save(img_path)

        try:
            response = client.get("/images/test_mock_serving.jpg")
            assert response.status_code == 200
            assert response.headers["content-type"] in ["image/jpeg", "application/octet-stream"]
        finally:
            if img_path.exists():
                img_path.unlink()

    def test_global_exception_handler(self, client):
        with patch("backend.routes.search_routes.ObjectDetector.get_instance") as mock_det:
            mock_det.side_effect = RuntimeError("Simulated unexpected crash")
            response = client.post(
                "/api/detect",
                files={"file": ("test.jpg", b"fake_bytes", "image/jpeg")},
            )
            assert response.status_code == 500
            data = response.json()
            assert data["error_type"] in ["RuntimeError", "HTTPException"]


class TestDetectEndpoint:
    """Verifies garment detection, bounding boxes, MD5 caching, and input validation."""

    def test_detect_valid_image(self, client, sample_image_bytes):
        response = client.post(
            "/api/detect",
            files={"file": ("outfit.jpg", sample_image_bytes, "image/jpeg")},
        )
        assert response.status_code == 200
        data = response.json()

        assert "image_hash" in data
        assert data["total_boxes"] > 0
        assert len(data["boxes"]) == data["total_boxes"]

        for box in data["boxes"]:
            assert "box_id" in box
            assert "label" in box
            assert 0.0 <= box["score"] <= 1.0
            coords = box["box_2d"]
            assert len(coords) == 4
            for c in coords:
                assert 0.0 <= c <= 1.0

    def test_detect_caching(self, client, sample_image_bytes):
        res_1 = client.post("/api/detect", files={"file": ("outfit.jpg", sample_image_bytes, "image/jpeg")})
        res_2 = client.post("/api/detect", files={"file": ("outfit.jpg", sample_image_bytes, "image/jpeg")})

        assert res_1.status_code == 200
        assert res_2.status_code == 200
        assert res_1.json()["image_hash"] == res_2.json()["image_hash"]
        assert len(res_1.json()["boxes"]) == len(res_2.json()["boxes"])

    def test_detect_unsupported_file_type(self, client):
        response = client.post(
            "/api/detect",
            files={"file": ("document.pdf", b"%PDF-1.4...", "application/pdf")},
        )
        assert response.status_code == 400
        assert "Unsupported image type" in response.json()["message"]

    def test_detect_empty_file(self, client):
        response = client.post(
            "/api/detect",
            files={"file": ("empty.jpg", b"", "image/jpeg")},
        )
        assert response.status_code == 400
        assert "empty" in response.json()["message"].lower()


class TestTranscribeEndpoint:
    """Verifies speech-to-text audio processing and error handling."""

    def test_transcribe_audio_success(self, client):
        dummy_audio = b"FAKE_WEBM_AUDIO_STREAM_DATA"
        response = client.post(
            "/api/transcribe",
            files={"file": ("voice.webm", dummy_audio, "audio/webm")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "text" in data
        assert len(data["text"]) > 0
        assert data["language"] == "vi"

    def test_transcribe_empty_file(self, client):
        response = client.post(
            "/api/transcribe",
            files={"file": ("empty.webm", b"", "audio/webm")},
        )
        assert response.status_code == 400
        assert "empty" in response.json()["message"].lower()


class TestSearchLifecycleAndConstraints:
    """Verifies end-to-end multi-turn search sessions, crop boxes, and chip removal."""

    def test_search_turn1_text_only(self, client, mock_db):
        mock_conn, mock_cur = mock_db
        mock_cur.fetchall.return_value = [
            (
                "0123456789", "White Cotton T-Shirt", 299000, "Ladieswear",
                "10", "White", "Garment Upper body", "T-shirt",
                "images/0123456789.jpg", "100% pure cotton", 0.92,
            )
        ]

        with patch("backend.routes.search_routes.get_db_connection", return_value=mock_conn):
            response = client.post(
                "/api/search",
                data={"query_text": "tìm áo thun màu trắng dưới 500k"},
            )
            assert response.status_code == 200
            data = response.json()

            assert "session_id" in data
            assert data["turn_index"] == 1
            assert data["total_results"] == 1
            assert len(data["search_state"]["active_chips"]) >= 2
            assert data["items"][0]["article_id"] == "0123456789"

    def test_search_turn2_with_image_and_crop(self, client, sample_image_bytes, mock_db):
        sid = "test_session_turn2"
        crop_box_json = json.dumps([0.1, 0.2, 0.8, 0.9])

        mock_conn, mock_cur = mock_db
        mock_cur.fetchall.return_value = [
            (
                "0987654321", "White Sneakers", 899000, "Unisex",
                "10", "White", "Shoes", "Sneakers",
                "images/0987654321.jpg", "Canvas casual sneaker", 0.89,
            )
        ]

        with patch("backend.routes.search_routes.get_db_connection", return_value=mock_conn):
            response = client.post(
                "/api/search",
                data={
                    "session_id": sid,
                    "query_text": "tìm đôi giày sneaker giống vùng này",
                    "crop_box": crop_box_json,
                },
                files={"image": ("outfit.jpg", sample_image_bytes, "image/jpeg")},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == sid
            assert data["turn_index"] == 1
            assert data["total_results"] == 1

    def test_search_turn3_reference_article(self, client, mock_db):
        sid = "test_session_turn3"
        mock_conn, mock_cur = mock_db
        mock_cur.fetchone.return_value = ([0.01] * 768,)
        mock_cur.fetchall.return_value = []

        with patch("backend.routes.search_routes.get_db_connection", return_value=mock_conn):
            response = client.post(
                "/api/search",
                data={
                    "session_id": sid,
                    "reference_article_id": "0123456789",
                    "query_text": "nhưng không phải da",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["search_state"]["reference_article_id"] == "0123456789"
            assert "leather" in data["search_state"]["exclude_materials"]

    def test_delete_constraint_chip_success(self, client, mock_db):
        from backend.core.state_manager import StateManager
        from backend.routes.search_routes import SESSION_STATES
        from backend.schemas.state import SearchState

        sid = "session_for_delete_chip"
        state = SearchState(session_id=sid, color="White", max_price=500000)
        state.active_chips = StateManager.generate_chips(state)
        SESSION_STATES[sid] = state

        mock_conn, mock_cur = mock_db
        mock_cur.fetchall.return_value = []

        with patch("backend.routes.search_routes.get_db_connection", return_value=mock_conn):
            response = client.delete(
                f"/api/search/{sid}/constraint",
                params={"chip_id": "color:White"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["search_state"]["color"] is None

    def test_delete_constraint_unknown_session(self, client):
        response = client.delete(
            "/api/search/unknown_session_uuid/constraint",
            params={"chip_id": "color:White"},
        )
        assert response.status_code == 404
        assert "not found" in response.json()["message"].lower()


    def test_search_corrupt_image_upload(self, client):
        response = client.post(
            "/api/search",
            data={"query_text": "tìm áo"},
            files={"image": ("corrupted.jpg", b"THIS_IS_NOT_AN_IMAGE", "image/jpeg")},
        )
        assert response.status_code == 400
        assert "Invalid image content" in response.json()["message"]

    def test_search_invalid_crop_box_json(self, client, sample_image_bytes, mock_db):
        mock_conn, mock_cur = mock_db
        mock_cur.fetchall.return_value = []

        with patch("backend.routes.search_routes.get_db_connection", return_value=mock_conn):
            response = client.post(
                "/api/search",
                data={
                    "query_text": "tìm áo",
                    "crop_box": "{broken_json_not_array",
                },
                files={"image": ("outfit.jpg", sample_image_bytes, "image/jpeg")},
            )
            assert response.status_code == 200


class TestProductDetailEndpoint:
    """Verifies single product lookup and 404 behavior."""

    def test_get_product_detail_success(self, client, mock_db):
        mock_conn, mock_cur = mock_db
        mock_cur.fetchone.return_value = (
            "0123456789", "P001", "Slim Fit Denim Jeans", 799000, "Menswear",
            "14", "Dark Blue", "Garment Lower body", "Trousers",
            "100% cotton denim fabric", "images/0123456789.jpg"
        )

        with patch("backend.routes.search_routes.get_db_connection", return_value=mock_conn):
            response = client.get("/api/products/0123456789")
            assert response.status_code == 200
            data = response.json()
            assert data["article_id"] == "0123456789"
            assert data["prod_name"] == "Slim Fit Denim Jeans"
            assert data["price_vnd"] == 799000
            assert data["color_name"] == "Dark Blue"

    def test_get_product_detail_not_found(self, client, mock_db):
        mock_conn, mock_cur = mock_db
        mock_cur.fetchone.return_value = None

        with patch("backend.routes.search_routes.get_db_connection", return_value=mock_conn):
            response = client.get("/api/products/9999999999")
            assert response.status_code == 404
            assert "does not exist" in response.json()["message"]


class TestDetectorAndEmbedderHelpers:
    """Verifies cropping math, detector caching, and embedding extraction utilities."""

    def test_crop_bounding_box(self):
        img = Image.new("RGB", (100, 200), color="blue")
        cropped = ObjectDetector.crop_bounding_box(img, [0.1, 0.2, 0.8, 0.9])
        assert isinstance(cropped, Image.Image)
        assert cropped.size[0] > 0
        assert cropped.size[1] > 0

    def test_crop_bounding_box_boundary_clamps(self):
        img = Image.new("RGB", (100, 100), color="green")
        cropped = ObjectDetector.crop_bounding_box(img, [-0.5, -0.5, 1.5, 1.5])
        assert cropped.size == (100, 100)

    def test_detector_with_pil_image_and_hash(self):
        detector = ObjectDetector(use_mock=True)
        img = Image.new("RGB", (64, 64), color="red")
        boxes = detector.detect(img)
        assert len(boxes) > 0

        # Verify MD5 hash calculation returns 32 hex chars
        md5_hash = detector.compute_image_hash(b"test_image_bytes")
        assert len(md5_hash) == 32
        assert all(c in "0123456789abcdef" for c in md5_hash)

    def test_embedder_text_and_image_vector_properties(self, tmp_path):
        embedder = MultimodalEmbedder.get_instance(use_mock=True)

        vec_text = embedder.encode_text("áo sơ mi trắng")
        assert isinstance(vec_text, np.ndarray)
        assert vec_text.shape == (768,)
        assert pytest.approx(np.linalg.norm(vec_text), rel=1e-4) == 1.0

        vec_empty = embedder.encode_text("")
        assert vec_empty.shape == (768,)

        # Test with PIL image
        img = Image.new("RGB", (100, 100), color="yellow")
        vec_img = embedder.encode_image(img)
        assert vec_img.shape == (768,)
        assert pytest.approx(np.linalg.norm(vec_img), rel=1e-4) == 1.0

        # Test with Image Path
        dummy_file = tmp_path / "test_item.jpg"
        img.save(dummy_file)
        vec_file = embedder.encode_image(dummy_file)
        assert vec_file.shape == (768,)
        assert pytest.approx(np.linalg.norm(vec_file), rel=1e-4) == 1.0


class TestTranscriberUnitMethods:
    """Verifies SpeechTranscriber integration branches."""

    @patch("openai.OpenAI")
    def test_transcribe_openai_branch(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_transcription = MagicMock()
        mock_transcription.text = "tìm áo blazer màu be"
        mock_client.audio.transcriptions.create.return_value = mock_transcription

        transcriber = SpeechTranscriber(openai_api_key="mock_key", use_mock=False)
        result = transcriber.transcribe(b"fake_audio_bytes", filename="audio.webm")
        assert result == "tìm áo blazer màu be"
        assert mock_client.audio.transcriptions.create.called

    def test_transcribe_file_path_input(self, tmp_path):
        audio_file = tmp_path / "voice_sample.webm"
        audio_file.write_bytes(b"FAKE_AUDIO_SAMPLE")

        transcriber = SpeechTranscriber(use_mock=True)
        res = transcriber.transcribe(audio_file)
        assert len(res) > 0


class TestDatabaseConnectionHelper:
    """Verifies get_db_connection handling."""

    def test_get_db_connection_custom_string(self):
        from backend.db.connection import get_db_connection

        with patch("psycopg.connect") as mock_connect:
            get_db_connection("postgresql://user:pass@remote:5432/db")
            mock_connect.assert_called_with("postgresql://user:pass@remote:5432/db")

    def test_get_db_connection_env_vars(self):
        from backend.db.connection import get_db_connection

        with patch("psycopg.connect") as mock_connect, patch.dict("os.environ", {"POSTGRES_PORT": "5433"}):
            get_db_connection()
            assert mock_connect.called


class TestPhase3MultimodalLogicEndpoints:
    """Verifies polygon return in /api/detect and partitioned response in /api/search."""

    def test_detect_endpoint_returns_polygon(self, client, sample_image_bytes):
        resp = client.post(
            "/api/detect",
            files={"file": ("test.jpg", sample_image_bytes, "image/jpeg")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_boxes"] > 0
        box = data["boxes"][0]
        assert "polygon" in box
        assert box["polygon"] is not None
        assert len(box["polygon"]) >= 4
        for vertex in box["polygon"]:
            assert len(vertex) == 2
            x, y = vertex
            assert 0.0 <= x <= 1.0
            assert 0.0 <= y <= 1.0

    def test_search_endpoint_returns_partitioned_fields(self, client):
        resp = client.post(
            "/api/search",
            data={"query_text": "áo sơ mi trắng"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "has_exact_match" in data
        assert "exact_items" in data
        assert "similar_items" in data
        assert isinstance(data["exact_items"], list)
        assert isinstance(data["similar_items"], list)
        assert isinstance(data["has_exact_match"], bool)

    def test_constraint_deletion_preserves_partitions(self, client):
        # Initial search to establish session
        resp1 = client.post("/api/search", data={"query_text": "quần đen"})
        session_id = resp1.json()["session_id"]

        # Delete constraint
        resp2 = client.delete(f"/api/search/{session_id}/constraint?chip_id=color:Black")
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert "has_exact_match" in data2
        assert "exact_items" in data2
        assert "similar_items" in data2

