import os
import io
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

import cv2
import wave
import pytest
import numpy as np
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import init_db
from app.services.multimodal_service import multimodal_service
from app.services.video_preprocessor import ExtractedFrame

def create_synthetic_mp4(filename: str, num_frames: int = 15, fps: float = 10.0) -> str:
    """Helper to generate a lightweight MP4 container for multimodal testing."""
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filename, fourcc, fps, (320, 240))
    for i in range(num_frames):
        frame = np.full((240, 320, 3), 40, dtype=np.uint8)
        # Face ellipse
        cv2.ellipse(frame, (160, 120), (45, 60), 0, 0, 360, (140, 170, 210), -1)
        # Mouth with varying aperture
        aperture_h = 4 + (i % 8) * 2
        cv2.ellipse(frame, (160, 145), (16, aperture_h), 0, 0, 360, (40, 40, 90), -1)
        out.write(frame)
    out.release()
    return filename

def create_synthetic_wav(filename: str, duration_sec: float = 1.5, sample_rate: int = 16000) -> str:
    """Helper to generate a linear PCM WAV file for multimodal testing."""
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    # 440Hz sine wave speech tone
    audio_data = (np.sin(2 * np.pi * 440 * t) * 16384).astype(np.int16)
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data.tobytes())
    return filename

@pytest.mark.asyncio
async def test_multimodal_evidence_fusion_all_modalities():
    """Tests Bayesian multi-evidence fusion when both audio and video streams are present."""
    # Scenario A: Organic audio + Organic video + Synchronized lip movement
    audio_clean = {
        "synthetic_probability": 0.08,
        "model_confidence": 0.94,
        "classification": "genuine",
        "flagged_intervals": []
    }
    video_clean = {
        "spatial_manipulation_score": 0.12,
        "model_confidence": 0.88,
        "classification": "genuine",
        "faces_detected": 4,
        "flagged_intervals": []
    }
    sync_clean = {
        "lip_sync_correlation": 0.72,
        "sync_drift_ms": 20.0,
        "sync_error_score": 0.08,
        "is_synchronized": True,
        "asynchronous_intervals": []
    }

    report_clean = multimodal_service.fuse_evidence(audio_clean, video_clean, sync_clean)
    assert report_clean["risk_category"] == "Low Risk"
    assert report_clean["verdict"] == "authentic"
    assert report_clean["composite_risk_score"] < 35.0
    assert report_clean["breakdown"]["evidence_status"] == "both_modalities_present"
    assert "signal_attribution" in report_clean["breakdown"]

    # Scenario B: High synthetic audio + Organic video + Lip sync lag (Audio Dubbing attack)
    audio_fake = {
        "synthetic_probability": 0.91,
        "model_confidence": 0.95,
        "classification": "synthetic",
        "flagged_intervals": [{"start_sec": 0.0, "end_sec": 2.0, "manipulation_type": "vocoder_speech"}]
    }
    sync_lag = {
        "lip_sync_correlation": 0.15,
        "sync_drift_ms": 240.0,
        "sync_error_score": 0.82,
        "is_synchronized": False,
        "asynchronous_intervals": [{"start_sec": 0.5, "end_sec": 1.5, "reason": "Vocal energy without mouth movement"}]
    }

    report_dub = multimodal_service.fuse_evidence(audio_fake, video_clean, sync_lag)
    # Cross-modal asymmetry and sync lag elevate threat
    assert report_dub["risk_category"] in ["Medium Risk", "High Risk"]
    assert report_dub["breakdown"]["cross_modal_inconsistency"] > 0.40
    assert report_dub["breakdown"]["signal_attribution"]["asymmetry_penalty_pct"] > 0.0
    assert len(report_dub["timeline_anomalies"]) >= 2
    assert "Non-Defamation" not in report_dub["summary_explanation"]

@pytest.mark.asyncio
async def test_missing_modalities_and_uncertainty():
    """Tests that missing streams are never presumed authentic and confidence is calibrated."""
    video_evidence = {
        "spatial_manipulation_score": 0.78,
        "model_confidence": 0.85,
        "classification": "synthetic",
        "faces_detected": 3,
        "flagged_intervals": []
    }
    audio_evidence = {
        "synthetic_probability": 0.15,
        "model_confidence": 0.90,
        "classification": "genuine",
        "flagged_intervals": []
    }

    # 1. Audio missing
    res_no_audio = multimodal_service.fuse_evidence(audio_result=None, video_result=video_evidence)
    assert res_no_audio["breakdown"]["evidence_status"] == "audio_missing"
    assert res_no_audio["risk_category"] == "High Risk"
    assert "missing audio track does not imply authentic voice" in res_no_audio["summary_explanation"].lower()
    assert res_no_audio["confidence_score"] <= 0.70  # Penalized for missing modality

    # 2. Video missing
    res_no_video = multimodal_service.fuse_evidence(audio_result=audio_evidence, video_result=None)
    assert res_no_video["breakdown"]["evidence_status"] == "video_missing"
    assert res_no_video["risk_category"] == "Low Risk"
    assert "Visual stream unavailable" in res_no_video["summary_explanation"]

    # 3. Both missing
    res_empty = multimodal_service.fuse_evidence(audio_result=None, video_result=None)
    assert res_empty["breakdown"]["evidence_status"] == "insufficient_evidence"
    assert res_empty["risk_category"] == "Inconclusive"
    assert res_empty["composite_risk_score"] == 0.0

@pytest.mark.asyncio
async def test_lip_sync_cross_correlation_analysis():
    """Tests lip aperture to speech energy cross-correlation."""
    # Synthesize dummy frames with mouth aperture
    frames = []
    for i in range(10):
        dummy_crop = np.full((224, 224, 3), 160, dtype=np.uint8)
        # Open mouth on odd frames
        if i % 2 == 1:
            cv2.ellipse(dummy_crop, (112, 175), (25, 15), 0, 0, 360, (20, 20, 20), -1)
        else:
            cv2.line(dummy_crop, (90, 175), (135, 175), (50, 50, 50), 2)

        frames.append(ExtractedFrame(
            frame_index=i,
            timestamp_sec=i * 0.1,
            frame_rgb=dummy_crop,
            face_detected=True,
            face_bbox=(30, 20, 160, 180),
            normalized_bbox={"x": 0.1, "y": 0.1, "w": 0.8, "h": 0.8},
            face_crop_rgb=dummy_crop
        ))

    # Synchronized audio: energy matches odd frame openings
    pcm = np.zeros(16000, dtype=np.float32)
    for i in range(10):
        if i % 2 == 1:
            start = int(i * 0.1 * 16000)
            end = min(len(pcm), start + 800)
            pcm[start:end] = 0.5

    sync_eval = multimodal_service.analyze_audio_visual_sync(frames, pcm, sample_rate=16000)
    assert "lip_sync_correlation" in sync_eval
    assert "sync_drift_ms" in sync_eval
    assert "is_synchronized" in sync_eval
    assert 0.0 <= sync_eval["sync_error_score"] <= 1.0

@pytest.mark.asyncio
async def test_multimodal_api_endpoints():
    """Tests FastAPI /api/v1/multimodal/fuse and /api/v1/multimodal/analyze endpoints."""
    await init_db()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Test /multimodal/fuse JSON endpoint
        fuse_payload = {
            "audio_result": {
                "synthetic_probability": 0.85,
                "model_confidence": 0.90,
                "classification": "synthetic"
            },
            "video_result": {
                "spatial_manipulation_score": 0.15,
                "model_confidence": 0.85,
                "classification": "genuine",
                "faces_detected": 2
            }
        }
        res_fuse = await client.post("/api/v1/multimodal/fuse", json=fuse_payload)
        assert res_fuse.status_code == 200
        fuse_data = res_fuse.json()
        assert fuse_data["media_type"] == "multimodal"
        assert fuse_data["risk_category"] in ["Low Risk", "Medium Risk", "High Risk"]
        assert "breakdown" in fuse_data
        assert "signal_attribution" in fuse_data["breakdown"]
        assert len(fuse_data["actionable_recommendations"]) > 0
        assert len(fuse_data["model_limitations"]) > 0

        # 2. Test /multimodal/analyze with synthetic media files
        vid_path = "test_mm_video.mp4"
        aud_path = "test_mm_audio.wav"
        try:
            create_synthetic_mp4(vid_path, num_frames=12, fps=10.0)
            create_synthetic_wav(aud_path, duration_sec=1.2)

            with open(vid_path, "rb") as vf, open(aud_path, "rb") as af:
                files = {
                    "video_file": ("test_clip.mp4", vf.read(), "video/mp4"),
                    "audio_file": ("test_speech.wav", af.read(), "audio/wav")
                }

            res_ana = await client.post("/api/v1/multimodal/analyze", files=files)
            assert res_ana.status_code == 200
            ana_data = res_ana.json()
            assert ana_data["media_type"] == "multimodal"
            assert ana_data["risk_category"] in ["Low Risk", "Medium Risk", "High Risk", "Inconclusive"]
            assert ana_data["breakdown"]["evidence_status"] == "both_modalities_present"
            assert ana_data["sync_metrics"] is not None

            # 3. Test invalid request (no files)
            res_bad = await client.post("/api/v1/multimodal/analyze")
            assert res_bad.status_code == 400

        finally:
            for p in [vid_path, aud_path]:
                if os.path.exists(p):
                    os.remove(p)
