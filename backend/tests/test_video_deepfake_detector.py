import os
import io
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

import cv2
import pytest
import numpy as np
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import init_db
from app.services.video_preprocessor import video_preprocessor, VideoValidationError
from app.services.video_deepfake_detector import video_deepfake_detector

def create_synthetic_mp4(filename: str, num_frames: int = 20, fps: float = 10.0, include_face: bool = True) -> str:
    """Helper to generate a lightweight MP4 container for forensic testing."""
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filename, fourcc, fps, (320, 240))
    for i in range(num_frames):
        frame = np.full((240, 320, 3), 30 + (i % 20), dtype=np.uint8)
        if include_face:
            # Draw an oval skin-tone face (YCrCb compatible) at center
            cv2.ellipse(frame, (160, 120), (45, 60), 0, 0, 360, (140, 170, 210), -1)
            # Add facial features (eyes and mouth)
            cv2.circle(frame, (145, 105), 6, (60, 60, 80), -1)
            cv2.circle(frame, (175, 105), 6, (60, 60, 80), -1)
            cv2.ellipse(frame, (160, 145), (15, 6), 0, 0, 360, (90, 90, 150), -1)
        out.write(frame)
    out.release()
    return filename

@pytest.mark.asyncio
async def test_video_preprocessor_and_face_localization():
    """Tests video metadata extraction, temporal frame sampling, and face crop localization."""
    test_video_path = "test_synth_face.mp4"
    try:
        create_synthetic_mp4(test_video_path, num_frames=25, fps=10.0, include_face=True)

        metadata, frames = video_preprocessor.extract_keyframes(test_video_path, max_frames=10, sample_fps=2.0)

        assert metadata["duration_seconds"] == 2.5
        assert metadata["fps"] == 10.0
        assert metadata["resolution"] == "320x240"
        assert len(frames) > 0
        assert len(frames) <= 10

        # Check face detection
        first_frame = frames[0]
        assert first_frame.face_detected is True
        assert first_frame.face_bbox is not None
        assert first_frame.normalized_bbox is not None
        assert first_frame.face_crop_rgb is not None
        assert first_frame.face_crop_rgb.shape == (224, 224, 3)

        # Check timestamp progression
        timestamps = [f.timestamp_sec for f in frames]
        assert timestamps == sorted(timestamps)

        # Test empty input handling
        with pytest.raises(VideoValidationError):
            video_preprocessor.extract_keyframes(b"")

    finally:
        if os.path.exists(test_video_path):
            os.remove(test_video_path)

@pytest.mark.asyncio
async def test_video_deepfake_detector_and_api():
    """Tests video deepfake multi-frame aggregation and FastAPI /api/v1/video/analyze endpoint."""
    await init_db()
    transport = ASGITransport(app=app)

    face_video_path = "test_synth_eval.mp4"
    noface_video_path = "test_synth_noface.mp4"

    try:
        create_synthetic_mp4(face_video_path, num_frames=20, fps=10.0, include_face=True)
        create_synthetic_mp4(noface_video_path, num_frames=15, fps=10.0, include_face=False)

        # 1. Direct detector analysis - Face present
        res_face = await video_deepfake_detector.analyze_video(face_video_path, max_frames=10, sample_fps=2.0)
        assert res_face["faces_detected"] > 0
        assert res_face["classification"] in ["genuine", "suspicious", "synthetic", "uncertain"]
        assert 0.0 <= res_face["calibrated_fraud_risk"] <= 100.0
        assert 0.0 <= res_face["model_confidence"] <= 1.0
        assert "video_metrics" in res_face
        assert res_face["video_metrics"]["faces_detected"] > 0
        assert "explainability_summary" in res_face
        assert len(res_face["actionable_recommendations"]) > 0

        # 2. Direct detector analysis - No face present (uncertain reporting)
        res_noface = await video_deepfake_detector.analyze_video(noface_video_path, max_frames=8, sample_fps=2.0)
        assert res_noface["faces_detected"] == 0
        assert res_noface["classification"] == "uncertain"
        assert res_noface["verdict"] == "inconclusive"
        assert res_noface["calibrated_fraud_risk"] == 0.0
        assert "No human facial regions were localized" in res_noface["explainability_summary"]

        # 3. Test FastAPI endpoint /api/v1/video/analyze
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Login as analyst
            login_res = await client.post("/api/v1/auth/login", json={
                "email": "analyst@shield.ai",
                "password": "CyberSecurity2026!"
            })
            assert login_res.status_code == 200
            token = login_res.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            with open(face_video_path, "rb") as f:
                video_bytes = f.read()

            files = {"file": ("test_interview.mp4", video_bytes, "video/mp4")}
            data = {"frame_sample_rate": "2", "extract_faces": "true"}

            api_res = await client.post("/api/v1/video/analyze", headers=headers, files=files, data=data)
            assert api_res.status_code == 200
            api_data = api_res.json()

            assert api_data["media_type"] == "video"
            assert api_data["faces_detected"] > 0
            assert api_data["status"] == "completed"
            assert "classification" in api_data
            assert "calibrated_fraud_risk" in api_data
            assert "facial_forensics" in api_data
            assert "flagged_intervals" in api_data
            assert "explainability_summary" in api_data

            # Test invalid file format rejection
            bad_files = {"file": ("corrupt.txt", b"plain text", "text/plain")}
            bad_res = await client.post("/api/v1/video/analyze", headers=headers, files=bad_files)
            assert bad_res.status_code == 400

    finally:
        for p in [face_video_path, noface_video_path]:
            if os.path.exists(p):
                os.remove(p)
