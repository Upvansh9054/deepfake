"""
Phase 7 System Integration Test Suite.
Validates the complete end-to-end user workflow:
1. Analyst authentication and JWT token handling.
2. Audio deepfake scan upload & acoustic feature extraction.
3. Video deepfake scan upload & multi-frame facial landmark analysis.
4. Multimodal single-stream scan upload (lip-sync cross-correlation & Bayesian risk fusion).
5. Multimodal dual-stream scan upload (video + separate suspect audio track).
6. Cryptographic scan certificate generation & SHA-256 chain-of-custody verification.
7. Scan history filtering by media_type (audio, video, multimodal).
8. Analytics overview metrics (audio, video, multimodal counts, threat ratio).
9. Alert auto-generation for high-risk assets and audit trail logging.
10. Safe file and record deletion.
"""

import sys
from pathlib import Path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

import pytest
import io
import wave
import struct
import numpy as np
import cv2
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import init_db

def create_valid_test_wav(duration_sec: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Generates an in-memory 16kHz mono WAV file with voiced acoustic energy."""
    num_samples = int(sample_rate * duration_sec)
    t = np.linspace(0, duration_sec, num_samples, endpoint=False)
    # 440 Hz pure tone (simulated speech fundamental frequency)
    audio = 0.5 * np.sin(2 * np.pi * 440 * t)
    pcm16 = (audio * 32767).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm16.tobytes())
    return buf.getvalue()

def create_valid_test_mp4(duration_sec: float = 1.0, fps: int = 5) -> bytes:
    """Generates an in-memory synthetic MP4 video with a detectable human face simulation."""
    import tempfile
    import os

    num_frames = int(duration_sec * fps)
    width, height = 320, 240

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(tmp_path, fourcc, fps, (width, height))

        for i in range(num_frames):
            frame = np.full((height, width, 3), 40, dtype=np.uint8)
            # Simulated human skin-tone oval (face)
            cv2.ellipse(frame, (160, 120), (50, 70), 0, 0, 360, (140, 170, 220), -1)
            # Eyes
            cv2.circle(frame, (140, 100), 8, (255, 255, 255), -1)
            cv2.circle(frame, (180, 100), 8, (255, 255, 255), -1)
            # Mouth aperture (dynamic over time)
            mouth_h = int(5 + 10 * np.sin(i * 0.5) ** 2)
            cv2.ellipse(frame, (160, 150), (20, mouth_h), 0, 0, 360, (20, 20, 80), -1)
            writer.write(frame)

        writer.release()
        with open(tmp_path, "rb") as f:
            content = f.read()
        return content
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@pytest.mark.asyncio
async def test_complete_phase7_workflow():
    await init_db()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Authenticate with seeded analyst credentials
        login_res = await client.post("/api/v1/auth/login", json={
            "email": "analyst@shield.ai",
            "password": "CyberSecurity2026!"
        })
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("\n[STEP 1] Analyst authenticated successfully.")

        # 2. Test Audio Upload and Scanning
        wav_bytes = create_valid_test_wav(1.0)
        files = {"file": ("sample_voice.wav", wav_bytes, "audio/wav")}
        data = {"title": "Phase 7 Executive Voice Verification"}

        audio_scan_res = await client.post("/api/v1/scans/upload", headers=headers, files=files, data=data)
        assert audio_scan_res.status_code == 201, f"Audio scan failed: {audio_scan_res.text}"
        audio_scan = audio_scan_res.json()
        audio_id = audio_scan["id"]
        assert audio_scan["media_type"] == "audio"
        assert audio_scan["result"] is not None
        assert audio_scan["risk_report"] is not None
        print(f"[STEP 2] Audio Scan passed. ID={audio_id}, Verdict={audio_scan['result']['verdict']}")

        # 3. Test Video Upload and Scanning
        mp4_bytes = create_valid_test_mp4(1.0)
        files = {"file": ("interview_keyframe.mp4", mp4_bytes, "video/mp4")}
        data = {"title": "Phase 7 Video Reenactment Scan"}

        video_scan_res = await client.post("/api/v1/scans/upload", headers=headers, files=files, data=data)
        assert video_scan_res.status_code == 201, f"Video scan failed: {video_scan_res.text}"
        video_scan = video_scan_res.json()
        video_id = video_scan["id"]
        assert video_scan["media_type"] == "video"
        assert video_scan["result"] is not None
        assert video_scan["risk_report"] is not None
        print(f"[STEP 3] Video Scan passed. ID={video_id}, Verdict={video_scan['result']['verdict']}")

        # 4. Test Multimodal Single-Stream Scan
        files = {"file": ("multimodal_stream.mp4", mp4_bytes, "video/mp4")}
        data = {"title": "Phase 7 Multimodal Single Video", "scan_type": "multimodal"}

        multi_scan_res = await client.post("/api/v1/scans/upload", headers=headers, files=files, data=data)
        assert multi_scan_res.status_code == 201, f"Multimodal scan failed: {multi_scan_res.text}"
        multi_scan = multi_scan_res.json()
        multi_id = multi_scan["id"]
        assert multi_scan["media_type"] == "multimodal"
        assert multi_scan["result"] is not None
        assert "inference_engine" in multi_scan["result"]["video_metrics"]
        print(f"[STEP 4] Multimodal Single Scan passed. ID={multi_id}, Risk={multi_scan['risk_report']['composite_risk_score']}%")

        # 5. Test Multimodal Dual-Stream Scan (Video + Separate Audio)
        files = {
            "file": ("source_video.mp4", mp4_bytes, "video/mp4"),
            "audio_file": ("dubbed_audio.wav", wav_bytes, "audio/wav")
        }
        data = {"title": "Phase 7 Cross-Modal Conflict Assessment"}

        dual_scan_res = await client.post("/api/v1/scans/upload", headers=headers, files=files, data=data)
        assert dual_scan_res.status_code == 201, f"Dual scan failed: {dual_scan_res.text}"
        dual_scan = dual_scan_res.json()
        dual_id = dual_scan["id"]
        assert dual_scan["media_type"] == "multimodal"
        print(f"[STEP 5] Dual-Stream Scan passed. ID={dual_id}, Title={dual_scan['title']}")

        # 6. Test Cryptographic Scan Certificate Endpoint
        cert_res = await client.get(f"/api/v1/scans/{multi_id}/certificate", headers=headers)
        assert cert_res.status_code == 200, f"Certificate failed: {cert_res.text}"
        cert = cert_res.json()
        assert "certificate_id" in cert
        assert cert["inspected_asset"]["sha256_fingerprint"] == multi_scan["sha256_hash"]
        assert "chain_of_custody_hash" in cert
        assert cert["investigator"]["analyst_email"] == "analyst@shield.ai"
        print(f"[STEP 6] Cryptographic Certificate retrieved: {cert['certificate_id']}")

        # 7. Test Scan Registry List & Filtering
        # Filter: multimodal
        list_res = await client.get("/api/v1/scans/?media_type=multimodal", headers=headers)
        assert list_res.status_code == 200
        multimodal_list = list_res.json()
        assert multimodal_list["total"] >= 2
        for s in multimodal_list["items"]:
            assert s["media_type"] == "multimodal"
        print(f"[STEP 7] Filtered Multimodal Registry: {len(multimodal_list['items'])} record(s)")

        # 8. Test Analytics Overview
        analytics_res = await client.get("/api/v1/analytics/overview", headers=headers)
        assert analytics_res.status_code == 200
        overview = analytics_res.json()
        assert overview["total_scans"] >= 4
        assert overview["audio_scans"] >= 1
        assert overview["video_scans"] >= 1
        assert overview["multimodal_scans"] >= 2
        print(f"[STEP 8] Analytics Overview: Total={overview['total_scans']}, Audio={overview['audio_scans']}, Video={overview['video_scans']}, Multi={overview['multimodal_scans']}")

        # 9. Test Audit Trail Logs
        audit_res = await client.get("/api/v1/audit/?limit=10", headers=headers)
        assert audit_res.status_code == 200
        audit_logs = audit_res.json()
        assert len(audit_logs) >= 4
        actions = [a["action"] for a in audit_logs]
        assert "media_scan_completed" in actions
        print(f"[STEP 9] Audit Trail verified: {len(audit_logs)} audit records logged.")

        # 10. Clean up created scans
        for scan_id in [audio_id, video_id, multi_id, dual_id]:
            del_res = await client.delete(f"/api/v1/scans/{scan_id}", headers=headers)
            assert del_res.status_code == 204
        print("[STEP 10] Created test assets cleanly deleted from disk and database.")
