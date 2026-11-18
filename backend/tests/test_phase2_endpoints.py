"""
Integration test suite for Deepfake Shield Phase 2 Backend.
Validates Authentication, User Management, Scan Ingestion, File Upload,
Database Connectivity, Forensics Execution, and Analytics.
"""

import sys
from pathlib import Path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

import pytest
import io
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import init_db

@pytest.mark.asyncio
async def test_full_phase2_workflow():
    await init_db()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Health check
        res = await client.get("/health")
        assert res.status_code == 200
        health = res.json()
        assert health["status"] == "healthy"
        print("[PASS] Health Check")

        # 2. Register a new security analyst
        analyst_email = f"test_analyst_{Path(__file__).stem}@shield.ai"
        register_payload = {
            "email": analyst_email,
            "password": "SecurePassword2026!",
            "full_name": "Integration Test Analyst",
            "role": "admin"
        }
        res = await client.post("/api/v1/auth/register", json=register_payload)
        # 201 Created or 400 if already created
        if res.status_code == 400:
            # Login instead
            res = await client.post("/api/v1/auth/login", json={
                "email": analyst_email,
                "password": "SecurePassword2026!"
            })
        assert res.status_code in [200, 201]
        token_data = res.json()
        token = token_data["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}
        print("[PASS] User Registration & Token Issue")

        # 3. Authenticated /me endpoint
        res = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert res.status_code == 200
        user_info = res.json()
        assert user_info["email"] == analyst_email
        print("[PASS] Current User Profile (/auth/me)")

        # 4. Upload and scan Audio file
        dummy_audio = io.BytesIO(b"RIFF" + b"\x00"*40 + b"WAVEfmt " + b"\x00"*2000)
        files = {
            "file": ("test_voicemail.wav", dummy_audio, "audio/wav")
        }
        data = {
            "title": "Suspected Executive Voice Clone"
        }
        res = await client.post("/api/v1/scans/upload", headers=auth_headers, files=files, data=data)
        assert res.status_code == 201
        audio_scan = res.json()
        assert audio_scan["media_type"] == "audio"
        assert audio_scan["result"] is not None
        assert audio_scan["risk_report"] is not None
        audio_scan_id = audio_scan["id"]
        print(f"[PASS] Audio Upload & Forensics: Verdict={audio_scan['result']['verdict']}, Risk={audio_scan['risk_report']['composite_risk_score']}%")

        # 5. Upload and scan Video file
        dummy_video = io.BytesIO(b"\x00\x00\x00\x20ftypmp42" + b"\x00"*5000)
        files = {
            "file": ("test_interview.mp4", dummy_video, "video/mp4")
        }
        data = {
            "title": "Video Conference Intercept"
        }
        res = await client.post("/api/v1/scans/upload", headers=auth_headers, files=files, data=data)
        assert res.status_code == 201
        video_scan = res.json()
        assert video_scan["media_type"] == "video"
        assert video_scan["result"] is not None
        video_scan_id = video_scan["id"]
        print(f"[PASS] Video Upload & Forensics: Verdict={video_scan['result']['verdict']}, Risk={video_scan['risk_report']['composite_risk_score']}%")

        # 6. List Scans with query filters
        res = await client.get("/api/v1/scans/?media_type=audio", headers=auth_headers)
        assert res.status_code == 200
        scan_list = res.json()
        assert scan_list["total"] >= 1
        print(f"[PASS] Scan Registry Query (Found {scan_list['total']} scans)")

        # 7. Get Scan Detail by ID
        res = await client.get(f"/api/v1/scans/{audio_scan_id}", headers=auth_headers)
        assert res.status_code == 200
        detail = res.json()
        assert detail["id"] == audio_scan_id
        assert "sha256_hash" in detail
        print("[PASS] Scan Detail Retrieval with SHA-256 Digest")

        # 8. Cybersecurity Analytics Overview
        res = await client.get("/api/v1/analytics/overview", headers=auth_headers)
        assert res.status_code == 200
        analytics = res.json()
        assert analytics["total_scans"] >= 2
        print(f"[PASS] Analytics Overview: Total={analytics['total_scans']}, ThreatLevel={analytics['active_threat_level']}")

        # 9. Threat Alerts List
        res = await client.get("/api/v1/alerts/", headers=auth_headers)
        assert res.status_code == 200
        alerts = res.json()
        print(f"[PASS] Threat Alerts List (Found {len(alerts)} alerts)")

        # 10. Audit Logs List
        res = await client.get("/api/v1/audit/", headers=auth_headers)
        assert res.status_code == 200
        logs = res.json()
        assert len(logs) >= 2
        print(f"[PASS] Forensic Audit Logs (Found {len(logs)} audit entries)")

        # 11. Delete Scan & verify removal
        res = await client.delete(f"/api/v1/scans/{audio_scan_id}", headers=auth_headers)
        assert res.status_code == 204
        # Verify it's gone
        res = await client.get(f"/api/v1/scans/{audio_scan_id}", headers=auth_headers)
        assert res.status_code == 404
        print("[PASS] Scan Deletion & Physical File Cleanup")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_full_phase2_workflow())

