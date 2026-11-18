import sys
from pathlib import Path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
import io
import wave
import uuid
import time
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy.future import select
from app.main import app
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.core.rate_limiter import login_rate_limiter
from app.core.database import AsyncSessionLocal
from app.models.entities import User, Scan, ScanResult, RiskReport

@pytest.fixture(autouse=True)
def reset_rate_limiters():
    """Reset rate limiter state before each test."""
    login_rate_limiter.reset()
    yield
    login_rate_limiter.reset()

def create_valid_test_wav_bytes(duration_sec: float = 1.0) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b'\x00\x00' * int(16000 * duration_sec))
    return buf.getvalue()

@pytest.mark.anyio
async def test_authentication_and_jwt_validation():
    """Task 1: Test valid login, bad password, missing token, tampered token, and deactivated user."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        test_email = f"analyst_sec_{uuid.uuid4().hex[:6]}@shield.ai"
        test_pw = "SecureP@ssw0rd2026!"

        # 1. Register analyst
        reg_resp = await client.post("/api/v1/auth/register", json={
            "email": test_email,
            "password": test_pw,
            "full_name": "Security Analyst",
            "role": "analyst"
        })
        assert reg_resp.status_code == 201
        token = reg_resp.json()["access_token"]
        user_id = reg_resp.json()["user"]["id"]

        # 2. Authenticated /me request
        me_resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == test_email
        assert me_resp.json()["role"] == "analyst"

        # 3. Missing authentication credentials
        no_auth = await client.get("/api/v1/auth/me")
        assert no_auth.status_code == 401

        # 4. Tampered JWT token
        tampered_token = token[:-5] + "XXXXX"
        bad_token = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
        assert bad_token.status_code == 401

        # 5. Expired JWT token
        expired_jwt = create_access_token(
            data={"sub": user_id, "email": test_email, "role": "analyst"},
            expires_delta=timedelta(seconds=-60)
        )
        exp_resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_jwt}"})
        assert exp_resp.status_code == 401

        # 6. Invalid credentials on login
        bad_login = await client.post("/api/v1/auth/login", json={
            "email": test_email,
            "password": "WrongPassword!"
        })
        assert bad_login.status_code == 401

        # 7. Deactivated user
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.id == user_id)
            user_db = (await session.execute(stmt)).scalars().first()
            user_db.is_active = False
            await session.commit()

        deact_resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert deact_resp.status_code == 403
        assert "deactivated" in deact_resp.json()["detail"].lower()

@pytest.mark.anyio
async def test_role_based_authorization():
    """Task 1: Verify Role-Based Access Control (RBAC)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create an analyst user
        analyst_email = f"analyst_rbac_{uuid.uuid4().hex[:6]}@shield.ai"
        analyst_resp = await client.post("/api/v1/auth/register", json={
            "email": analyst_email,
            "password": "Password123!",
            "full_name": "Standard Analyst",
            "role": "analyst"
        })
        analyst_token = analyst_resp.json()["access_token"]

        # Create an admin user
        admin_email = f"admin_rbac_{uuid.uuid4().hex[:6]}@shield.ai"
        admin_resp = await client.post("/api/v1/auth/register", json={
            "email": admin_email,
            "password": "AdminPassword123!",
            "full_name": "Security Admin",
            "role": "admin"
        })
        admin_token = admin_resp.json()["access_token"]

        # Analyst attempts to call admin-only purge endpoint -> Expect 403 Forbidden
        analyst_purge = await client.post(
            "/api/v1/retention/purge?retention_days=90",
            headers={"Authorization": f"Bearer {analyst_token}"}
        )
        assert analyst_purge.status_code == 403
        assert "Access forbidden" in analyst_purge.json()["detail"]

        # Admin calls purge endpoint -> Expect 200 OK
        admin_purge = await client.post(
            "/api/v1/retention/purge?retention_days=90",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert admin_purge.status_code == 200
        assert "purged_records_count" in admin_purge.json()

@pytest.mark.anyio
async def test_upload_security_and_magic_bytes_inspection():
    """Task 2 & 3: Test file validation, size, magic bytes, and path traversal protection."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register user
        user_resp = await client.post("/api/v1/auth/register", json={
            "email": f"upload_sec_{uuid.uuid4().hex[:6]}@shield.ai",
            "password": "Password123!",
            "full_name": "Uploader",
            "role": "analyst"
        })
        token = user_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Reject 0-byte file
        empty_upload = await client.post(
            "/api/v1/scans/upload",
            files={"file": ("empty.wav", b"", "audio/wav")},
            headers=headers
        )
        assert empty_upload.status_code == 400
        assert "empty" in empty_upload.json()["detail"].lower()

        # 2. Reject executable disguised as .wav (Windows PE 'MZ' header)
        fake_wav_exe = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00malicious_payload"
        exe_upload = await client.post(
            "/api/v1/scans/upload",
            files={"file": ("speech.wav", fake_wav_exe, "audio/wav")},
            headers=headers
        )
        assert exe_upload.status_code == 400
        assert "blocked executable or script" in exe_upload.json()["detail"].lower()

        # 3. Reject bash script disguised as .mp4
        fake_mp4_script = b"#!/bin/bash\nrm -rf /"
        script_upload = await client.post(
            "/api/v1/scans/upload",
            files={"file": ("video.mp4", fake_mp4_script, "video/mp4")},
            headers=headers
        )
        assert script_upload.status_code == 400
        assert "blocked executable or script" in script_upload.json()["detail"].lower()

        # 4. Reject unsupported extension
        unsupported = await client.post(
            "/api/v1/scans/upload",
            files={"file": ("trojan.exe", b"MZtest", "application/octet-stream")},
            headers=headers
        )
        assert unsupported.status_code == 400
        assert "unsupported file format" in unsupported.json()["detail"].lower()

        # 5. Path traversal attempt in filename sanitized safely
        valid_wav = create_valid_test_wav_bytes(1.0)
        traversal_upload = await client.post(
            "/api/v1/scans/upload",
            files={"file": ("../../../../etc/passwd.wav", valid_wav, "audio/wav")},
            headers=headers
        )
        assert traversal_upload.status_code == 201
        data = traversal_upload.json()
        assert ".." not in data["file_name"]

@pytest.mark.anyio
async def test_rate_limiting():
    """Task 5: Test rate limiting on sensitive endpoints."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Rapid login requests to trigger login rate limit (limit is 10/min)
        triggered_429 = False
        for i in range(15):
            res = await client.post("/api/v1/auth/login", json={
                "email": "nonexistent@shield.ai",
                "password": "wrong"
            })
            if res.status_code == 429:
                triggered_429 = True
                assert "Retry-After" in res.headers
                assert "Rate limit exceeded" in res.json()["detail"]
                break

        assert triggered_429, "Rate limiter should have triggered HTTP 429"

@pytest.mark.anyio
async def test_secure_stored_media_and_tenant_isolation():
    """Task 6: Test secure media streaming and ownership isolation."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create User A
        user_a = (await client.post("/api/v1/auth/register", json={
            "email": f"tenant_a_{uuid.uuid4().hex[:6]}@shield.ai",
            "password": "Password123!",
            "full_name": "Tenant A",
            "role": "analyst"
        })).json()
        token_a = user_a["access_token"]

        # Create User B
        user_b = (await client.post("/api/v1/auth/register", json={
            "email": f"tenant_b_{uuid.uuid4().hex[:6]}@shield.ai",
            "password": "Password123!",
            "full_name": "Tenant B",
            "role": "analyst"
        })).json()
        token_b = user_b["access_token"]

        # User A uploads a scan
        valid_wav = create_valid_test_wav_bytes(1.0)
        upload_resp = await client.post(
            "/api/v1/scans/upload",
            files={"file": ("tenant_a_audio.wav", valid_wav, "audio/wav")},
            headers={"Authorization": f"Bearer {token_a}"}
        )
        assert upload_resp.status_code == 201
        scan_id = upload_resp.json()["id"]

        # User A can securely stream their media
        stream_a = await client.get(
            f"/api/v1/scans/{scan_id}/media",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        assert stream_a.status_code == 200
        assert stream_a.headers["X-Content-Type-Options"] == "nosniff"

        # User B cannot access User A's media stream -> Expect 403 Forbidden
        stream_b = await client.get(
            f"/api/v1/scans/{scan_id}/media",
            headers={"Authorization": f"Bearer {token_b}"}
        )
        assert stream_b.status_code == 403
        assert "Access denied" in stream_b.json()["detail"]

@pytest.mark.anyio
async def test_data_retention_and_purge_lifecycle():
    """Task 7: Test data retention query and purge execution."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register Admin
        admin = (await client.post("/api/v1/auth/register", json={
            "email": f"admin_ret_{uuid.uuid4().hex[:6]}@shield.ai",
            "password": "AdminPassword123!",
            "full_name": "Admin Officer",
            "role": "admin"
        })).json()
        admin_token = admin["access_token"]

        # 1. Query status
        status_resp = await client.get(
            "/api/v1/retention/status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert "retention_policy_days" in data
        assert "storage_disk_usage_mb" in data

        # 2. Execute purge with 365 days window
        purge_resp = await client.post(
            "/api/v1/retention/purge?retention_days=365",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert purge_resp.status_code == 200
        assert purge_resp.json()["status"] == "success"
