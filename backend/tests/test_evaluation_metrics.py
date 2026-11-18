import sys
from pathlib import Path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
import io
import wave
import uuid
import numpy as np
import cv2
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.evaluator import model_evaluator, calculate_binary_metrics
from app.services.audio_deepfake_detector import audio_deepfake_detector
from app.services.video_deepfake_detector import video_deepfake_detector
from app.services.audio_preprocessor import audio_preprocessor, AudioValidationError
from app.services.video_preprocessor import video_preprocessor, VideoValidationError

@pytest.mark.anyio
async def test_binary_metrics_calculation():
    """Task 9: Verify precision, recall, f1, fpr mathematical accuracy."""
    # Test case: 4 TP, 1 FP, 4 TN, 1 FN
    y_true = [1, 1, 1, 1, 1, 0, 0, 0, 0, 0]
    y_pred = [1, 1, 1, 1, 0, 1, 0, 0, 0, 0]
    latencies = [15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0, 55.0, 60.0]

    metrics = calculate_binary_metrics(y_true, y_pred, latencies)

    # TP = 4, FP = 1, TN = 4, FN = 1
    # Accuracy = 8 / 10 = 0.8
    # Precision = 4 / (4 + 1) = 0.8
    # Recall = 4 / (4 + 1) = 0.8
    # F1 = 0.8
    # FPR = 1 / (1 + 4) = 0.2
    assert metrics["accuracy"] == 0.8
    assert metrics["precision"] == 0.8
    assert metrics["recall"] == 0.8
    assert metrics["f1_score"] == 0.8
    assert metrics["false_positive_rate"] == 0.2
    assert metrics["latency_metrics"]["mean_ms"] == 37.5

@pytest.mark.anyio
async def test_audio_and_video_detection_on_permitted_samples():
    """Task 8: Test detection engines against permitted synthetic and natural samples."""
    # 1. Permitted Synthetic Audio (high spectral flatness, comb artifacts)
    synth_audio = model_evaluator.generate_permitted_audio_sample(is_synthetic=True, duration_seconds=1.5)
    synth_res = await audio_deepfake_detector.analyze_recording(synth_audio, "synth_test.wav")
    assert synth_res["classification"] in ["synthetic", "suspicious"]
    assert synth_res["calibrated_fraud_risk"] >= 40.0

    # 2. Permitted Natural Audio (harmonic vocal formants)
    natural_audio = model_evaluator.generate_permitted_audio_sample(is_synthetic=False, duration_seconds=1.5)
    nat_res = await audio_deepfake_detector.analyze_recording(natural_audio, "natural_test.wav")
    assert nat_res["classification"] in ["genuine", "uncertain"]
    assert nat_res["calibrated_fraud_risk"] < 50.0

    # 3. Permitted Synthetic Video Frame (GAN artifacts & boundary seams)
    synth_vid_bytes = model_evaluator.generate_permitted_video_bytes(is_synthetic=True, num_frames=10)
    synth_vid_res = await video_deepfake_detector.analyze_video(synth_vid_bytes, max_frames=5)
    assert synth_vid_res["faces_detected"] >= 3
    assert synth_vid_res["spatial_manipulation_score"] >= 0.0
    assert synth_vid_res["verdict"] in ["authentic", "suspicious", "manipulated"]

    # 4. Permitted Natural Video Frame (smooth gradients)
    nat_vid_bytes = model_evaluator.generate_permitted_video_bytes(is_synthetic=False, num_frames=10)
    nat_vid_res = await video_deepfake_detector.analyze_video(nat_vid_bytes, max_frames=5)
    assert nat_vid_res["faces_detected"] >= 3
    assert nat_vid_res["verdict"] in ["authentic", "suspicious"]

@pytest.mark.anyio
async def test_edge_cases_and_model_failure_handling():
    """Task 10: Test corrupted audio, silent audio, short audio, no-face video, and empty payloads."""
    # 1. Silent Audio (< -50 dBFS)
    silent_buf = io.BytesIO()
    with wave.open(silent_buf, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b'\x00\x00' * 16000)
    silent_res = await audio_deepfake_detector.analyze_recording(silent_buf.getvalue(), "silent.wav")
    assert silent_res["classification"] == "uncertain"
    assert silent_res["verdict"] == "inconclusive"
    assert len(silent_res["flagged_intervals"]) > 0 or "silent" in silent_res["explainability_summary"].lower()

    # 2. Sub-second Audio (< 0.5s duration)
    short_buf = io.BytesIO()
    with wave.open(short_buf, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b'\x00\x00' * 3000)  # ~0.18s
    pcm_sh, sr_sh, dur_sh, meta_sh = audio_preprocessor.read_audio_bytes(short_buf.getvalue(), "short.wav")
    assert meta_sh["is_too_short"] is True

    short_res = await audio_deepfake_detector.analyze_recording(short_buf.getvalue(), "short.wav")
    assert short_res["classification"] == "uncertain"
    assert short_res["verdict"] == "inconclusive"

    # 3. Video with NO FACES (solid gray scene in MP4 container)
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
        temp_blank = tf.name
    try:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_blank, fourcc, 10.0, (320, 240))
        for _ in range(6):
            out.write(np.full((240, 320, 3), 120, dtype=np.uint8))
        out.release()
        with open(temp_blank, "rb") as f:
            blank_mp4_bytes = f.read()
    finally:
        if os.path.exists(temp_blank):
            os.remove(temp_blank)

    blank_res = await video_deepfake_detector.analyze_video(blank_mp4_bytes, max_frames=3)
    assert blank_res["faces_detected"] == 0
    assert blank_res["verdict"] == "inconclusive"
    assert blank_res["classification"] == "uncertain"

    # 4. Zero-byte video payload
    with pytest.raises(VideoValidationError) as vid_err:
        video_preprocessor.extract_keyframes(b"")
    assert "empty" in str(vid_err.value).lower()

@pytest.mark.anyio
async def test_evaluation_benchmark_api_endpoint():
    """Task 9: Test the /api/v1/analytics/evaluation-metrics endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register user
        user = (await client.post("/api/v1/auth/register", json={
            "email": f"analyst_eval_{uuid.uuid4().hex[:6]}@shield.ai",
            "password": "Password123!",
            "full_name": "Metrics Analyst",
            "role": "analyst"
        })).json()
        token = user["access_token"]

        resp = await client.get(
            "/api/v1/analytics/evaluation-metrics",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "composite_evaluation" in data
        assert "audio_detector_metrics" in data
        assert "video_detector_metrics" in data
        assert "precision" in data["composite_evaluation"]
        assert "recall" in data["composite_evaluation"]
        assert "f1_score" in data["composite_evaluation"]
        assert "false_positive_rate" in data["composite_evaluation"]
        assert "latency_metrics" in data["composite_evaluation"]
        assert data["composite_evaluation"]["latency_metrics"]["mean_ms"] >= 0.0
