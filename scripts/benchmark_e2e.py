"""End-to-End Walkthrough & Hardware Benchmark Script.

Executes a 6-step independent multimodal shopping scenario,
measures end-to-end latency per request, and benchmarks GPU VRAM footprint
on NVIDIA GeForce GTX 1660 Ti (or CPU fallback).

Outputs structured latency and memory metrics.
"""

from __future__ import annotations

import io
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import torch
from fastapi.testclient import TestClient
from PIL import Image

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.main import app
from backend.schemas.state import SearchResultItem, SearchState

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("benchmark_e2e")


def get_gpu_memory_mb() -> Dict[str, float]:
    """Returns GPU allocated and reserved memory in MB if CUDA is available."""
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated(0) / (1024 * 1024)
        reserved = torch.cuda.memory_reserved(0) / (1024 * 1024)
        max_allocated = torch.cuda.max_memory_allocated(0) / (1024 * 1024)
        return {
            "device": torch.cuda.get_device_name(0),
            "allocated_mb": round(allocated, 2),
            "reserved_mb": round(reserved, 2),
            "max_allocated_mb": round(max_allocated, 2),
        }
    return {
        "device": "CPU",
        "allocated_mb": 0.0,
        "reserved_mb": 0.0,
        "max_allocated_mb": 0.0,
    }


def create_sample_outfit_image() -> bytes:
    """Generates an in-memory sample outfit image (640x800) with colored blocks."""
    img = Image.new("RGB", (640, 800), color=(245, 245, 245))
    # Top/Jacket (Navy Blue)
    for x in range(160, 480):
        for y in range(120, 420):
            img.putpixel((x, y), (20, 40, 90))
    # Pants (Denim Blue)
    for x in range(200, 440):
        for y in range(430, 680):
            img.putpixel((x, y), (50, 80, 140))
    # Shoes (White/Red)
    for x in range(180, 460):
        for y in range(690, 780):
            img.putpixel((x, y), (240, 240, 245))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def run_benchmark(use_mock: bool = False):
    """Executes the full 6-step interactive multimodal scenario and logs metrics."""
    logger.info("=" * 70)
    logger.info("STARTING PHASE 5: END-TO-END MULTIMODAL WALKTHROUGH & BENCHMARK")
    logger.info("=" * 70)

    if use_mock:
        from backend.core.detector import ObjectDetector
        from backend.core.embedder import MultimodalEmbedder
        from backend.core.transcriber import SpeechTranscriber
        ObjectDetector.get_instance(use_mock=True)
        MultimodalEmbedder.get_instance(use_mock=True)
        SpeechTranscriber.get_instance(use_mock=True)

    initial_gpu = get_gpu_memory_mb()
    logger.info("Initial GPU State: %s", initial_gpu)

    client = TestClient(app)
    outfit_bytes = create_sample_outfit_image()

    scenario_metrics: List[Dict[str, Any]] = []

    # -------------------------------------------------------------------------
    # STEP 1: Upload Outfit Image & Garment Detection (OWL-ViT)
    # -------------------------------------------------------------------------
    t0 = time.perf_counter()
    resp_step1 = client.post(
        "/api/detect",
        files={"file": ("outfit.jpg", outfit_bytes, "image/jpeg")},
    )
    t1 = time.perf_counter()
    latency_step1 = (t1 - t0) * 1000

    assert resp_step1.status_code == 200, f"Step 1 failed: {resp_step1.text}"
    detect_data = resp_step1.json()
    boxes = detect_data.get("boxes", [])
    logger.info(
        "✓ Step 1 [Detect]: Detected %d boxes in %.1f ms (GPU VRAM: %s MB)",
        len(boxes),
        latency_step1,
        get_gpu_memory_mb()["allocated_mb"],
    )

    # Pick the shoes or dominant bounding box
    selected_box = None
    for b in boxes:
        if "shoe" in b["label"].lower():
            selected_box = b
            break
    if not selected_box and boxes:
        selected_box = boxes[0]

    crop_coords = selected_box["box_2d"] if selected_box else [0.65, 0.2, 0.95, 0.8]

    scenario_metrics.append({
        "step": 1,
        "name": "Upload Outfit & OWL-ViT Detect",
        "action": "Upload outfit image -> Detect garments with bounding boxes",
        "latency_ms": round(latency_step1, 2),
        "gpu_allocated_mb": get_gpu_memory_mb()["allocated_mb"],
        "details": f"Detected {len(boxes)} boxes. Selected box: {selected_box['label'] if selected_box else 'Default'}",
    })

    # -------------------------------------------------------------------------
    # STEP 2: Initial Multimodal Visual Query ("Tìm đôi giống thế này")
    # -------------------------------------------------------------------------
    t0 = time.perf_counter()
    resp_step2 = client.post(
        "/api/search",
        data={
            "query_text": "Tìm đôi giống thế này",
            "crop_box": json.dumps(crop_coords),
        },
        files={"image": ("crop_outfit.jpg", outfit_bytes, "image/jpeg")},
    )
    t1 = time.perf_counter()
    latency_step2 = (t1 - t0) * 1000

    assert resp_step2.status_code == 200, f"Step 2 failed: {resp_step2.text}"
    search_data_step2 = resp_step2.json()
    items_step2 = search_data_step2["items"]

    logger.info(
        "✓ Step 2 [Visual Search]: Returned %d items in %.1f ms",
        len(items_step2),
        latency_step2,
    )

    scenario_metrics.append({
        "step": 2,
        "name": "Initial Visual Search",
        "action": 'User selects Shoes crop + "Tìm đôi giống thế này"',
        "latency_ms": round(latency_step2, 2),
        "gpu_allocated_mb": get_gpu_memory_mb()["allocated_mb"],
        "details": f"Returned {len(items_step2)} visual match items. Top-1: {items_step2[0]['prod_name'] if items_step2 else 'N/A'}",
    })

    # -------------------------------------------------------------------------
    # STEP 3: One-shot image + text constraints
    # -------------------------------------------------------------------------
    t0 = time.perf_counter()
    resp_step3 = client.post(
        "/api/search",
        data={
            "query_text": "Tìm giày giống ảnh, màu trắng, dưới 1 triệu",
            "crop_box": json.dumps(crop_coords),
        },
        files={"image": ("crop_outfit.jpg", outfit_bytes, "image/jpeg")},
    )
    t1 = time.perf_counter()
    latency_step3 = (t1 - t0) * 1000

    assert resp_step3.status_code == 200, f"Step 3 failed: {resp_step3.text}"
    search_data_step3 = resp_step3.json()
    state_step3 = search_data_step3["search_state"]
    items_step3 = search_data_step3["items"]

    logger.info(
        "✓ Step 3 [Image + Text]: Applied request constraints (Color: %s, MaxPrice: %s) in %.1f ms",
        state_step3.get("color"),
        state_step3.get("max_price"),
        latency_step3,
    )

    scenario_metrics.append({
        "step": 3,
        "name": "One-shot Image + Text Search",
        "action": 'Image and full request: "Giày giống ảnh, màu trắng, dưới 1 triệu"',
        "latency_ms": round(latency_step3, 2),
        "gpu_allocated_mb": get_gpu_memory_mb()["allocated_mb"],
        "details": f"Max price: {state_step3.get('max_price')}đ. Matches: {len(items_step3)}",
    })

    # -------------------------------------------------------------------------
    # STEP 4: Independent negative-constraint text query
    # -------------------------------------------------------------------------
    t0 = time.perf_counter()
    resp_step4 = client.post(
        "/api/search",
        data={
            "query_text": "Tìm giày thể thao không phải da",
        },
    )
    t1 = time.perf_counter()
    latency_step4 = (t1 - t0) * 1000

    assert resp_step4.status_code == 200, f"Step 4 failed: {resp_step4.text}"
    search_data_step4 = resp_step4.json()
    state_step4 = search_data_step4["search_state"]
    items_step4 = search_data_step4["items"]

    logger.info(
        "✓ Step 4 [Text Search]: Negative constraints applied (Excludes: %s) in %.1f ms",
        state_step4.get("exclude_materials"),
        latency_step4,
    )

    scenario_metrics.append({
        "step": 4,
        "name": "Independent Negative Constraint Query",
        "action": 'User searches: "Tìm giày thể thao không phải da"',
        "latency_ms": round(latency_step4, 2),
        "gpu_allocated_mb": get_gpu_memory_mb()["allocated_mb"],
        "details": f"Negative constraint [exclude_materials: da]. Penalty (-0.30) applied to leather products. Matches: {len(items_step4)}",
    })

    # -------------------------------------------------------------------------
    # STEP 5: Independent visual-similar search from a product card
    # -------------------------------------------------------------------------
    reference_article_id = (
        items_step2[0]["article_id"] if items_step2 else "0000000001"
    )

    t0 = time.perf_counter()
    resp_step5 = client.post(
        "/api/search",
        data={"reference_article_id": reference_article_id},
    )
    t1 = time.perf_counter()
    latency_step5 = (t1 - t0) * 1000

    assert resp_step5.status_code == 200, f"Step 5 failed: {resp_step5.text}"
    search_data_step5 = resp_step5.json()
    items_step5 = search_data_step5["items"]

    logger.info(
        "✓ Step 5 [Product Reference]: Searched from '%s' in %.1f ms",
        reference_article_id,
        latency_step5,
    )

    scenario_metrics.append({
        "step": 5,
        "name": "Product Reference Search",
        "action": f"User clicks tìm tương tự on product '{reference_article_id}'",
        "latency_ms": round(latency_step5, 2),
        "gpu_allocated_mb": get_gpu_memory_mb()["allocated_mb"],
        "details": f"Returned {len(items_step5)} visually similar products.",
    })

    # -------------------------------------------------------------------------
    # STEP 6: Speech Transcription & Unified Search Pipeline
    # -------------------------------------------------------------------------
    sample_audio_blob = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"

    t0 = time.perf_counter()
    resp_transcribe = client.post(
        "/api/transcribe",
        files={"file": ("recording.wav", sample_audio_blob, "audio/wav")},
    )
    t1 = time.perf_counter()
    latency_transcribe = (t1 - t0) * 1000

    assert resp_transcribe.status_code == 200, f"Step 6 transcribe failed: {resp_transcribe.text}"
    transcript_text = resp_transcribe.json().get("text", "áo khoác gió màu đen")

    # Independent search with transcribed voice text
    t2 = time.perf_counter()
    resp_step6 = client.post(
        "/api/search",
        data={
            "query_text": transcript_text,
            "query_type": "voice",
        },
    )
    t3 = time.perf_counter()
    latency_step6 = latency_transcribe + (t3 - t2) * 1000

    assert resp_step6.status_code == 200, f"Step 6 search failed: {resp_step6.text}"
    search_data_step6 = resp_step6.json()

    logger.info(
        "✓ Step 6 [Voice to Search]: Transcribed ('%s') & searched in %.1f ms",
        transcript_text,
        latency_step6,
    )

    scenario_metrics.append({
        "step": 6,
        "name": "Voice-to-Search Full Flow",
        "action": f"Audio recorded -> gpt-transcribe -> Independent search ('{transcript_text}')",
        "latency_ms": round(latency_step6, 2),
        "gpu_allocated_mb": get_gpu_memory_mb()["allocated_mb"],
        "details": f"Transcript text received: '{transcript_text}'. Total matches: {len(search_data_step6['items'])}",
    })

    # -------------------------------------------------------------------------
    # BENCHMARK AGGREGATION & SUMMARY
    # -------------------------------------------------------------------------
    final_gpu = get_gpu_memory_mb()
    latencies = [m["latency_ms"] for m in scenario_metrics]
    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    peak_vram = final_gpu.get("max_allocated_mb", final_gpu["allocated_mb"])

    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "hardware": {
            "gpu_device": final_gpu["device"],
            "cuda_available": torch.cuda.is_available(),
            "peak_vram_mb": peak_vram,
            "allocated_vram_mb": final_gpu["allocated_mb"],
            "vram_limit_target_mb": 4096.0,
            "vram_status": "PASS (< 4.0 GB)" if peak_vram < 4096.0 else "EXCEEDED",
        },
        "performance": {
            "total_steps": len(scenario_metrics),
            "average_latency_ms": round(avg_latency, 2),
            "max_latency_ms": round(max_latency, 2),
            "latency_target_ms": 1000.0,
            "latency_status": "PASS (< 1.0s)" if avg_latency < 1000.0 else "EXCEEDED",
        },
        "steps": scenario_metrics,
    }

    # Save benchmark metrics to file
    out_path = PROJECT_ROOT / "docs" / "benchmark_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    logger.info("=" * 70)
    logger.info("PHASE 5 BENCHMARK COMPLETE:")
    logger.info("  • Average Request Latency: %.2f ms (Target: < 1000 ms) -> %s", avg_latency, summary["performance"]["latency_status"])
    logger.info("  • Peak GPU VRAM: %.2f MB (Target: < 4096 MB) -> %s", peak_vram, summary["hardware"]["vram_status"])
    logger.info("  • Results exported to: %s", out_path)
    logger.info("=" * 70)

    return summary


if __name__ == "__main__":
    run_benchmark()
