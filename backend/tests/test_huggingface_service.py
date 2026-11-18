"""
Unit & Integration tests for Hugging Face Dataset API Service in Deepfake Shield.
"""

import sys
from pathlib import Path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import init_db

@pytest.mark.asyncio
async def test_huggingface_api_integration():
    await init_db()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Login with demo user
        res = await client.post("/api/v1/auth/login", json={
            "email": "analyst@shield.ai",
            "password": "CyberSecurity2026!"
        })
        assert res.status_code == 200
        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("\n[PASS] Authenticated with Demo Analyst Token")

        # 2. Test HF Connection Status
        res = await client.get("/api/v1/huggingface/status", headers=headers)
        assert res.status_code == 200
        status_data = res.json()
        assert status_data["status"] in ["connected", "degraded", "error"]
        print(f"[PASS] Hugging Face Status: {status_data['status']}, Latency: {status_data['latency_ms']}ms")

        # 3. Test Splits Endpoint
        res = await client.get("/api/v1/huggingface/splits", headers=headers)
        assert res.status_code == 200
        splits_data = res.json()
        assert "splits" in splits_data
        assert len(splits_data["splits"]) > 0
        first_split = splits_data["splits"][0]
        assert first_split["dataset"] == "UniDataPro/deepfake-videos-dataset"
        assert first_split["config"] == "default"
        assert first_split["split"] == "train"
        print(f"[PASS] HF Splits Retrieved: config={first_split['config']}, split={first_split['split']}")

        # 4. Test Parquet Endpoint
        res = await client.get("/api/v1/huggingface/parquet", headers=headers)
        assert res.status_code == 200
        parquet_data = res.json()
        assert parquet_data["total_files"] >= 1
        assert "urls" in parquet_data
        print(f"[PASS] HF Parquet Metadata Retrieved: {parquet_data['total_files']} partition file(s)")

        # 5. Test Rows Endpoint (Offset 0, Length 5)
        res = await client.get("/api/v1/huggingface/rows?offset=0&length=5", headers=headers)
        if res.status_code == 200:
            rows_data = res.json()
            assert "rows" in rows_data
            assert len(rows_data["rows"]) == 5
            sample_row = rows_data["rows"][0]
            assert sample_row["row_idx"] == 0
            assert sample_row["label_idx"] == 0
            assert sample_row["label_name"] == "deepfake"
            assert sample_row["is_deepfake"] is True
            assert "video_src" in sample_row
            print(f"[PASS] HF Rows Retrieved: Row 0 is_deepfake={sample_row['is_deepfake']}, Label={sample_row['label_name']}")
        else:
            # Handle upstream Hugging Face datasets-server temporary maintenance / 502/503 outage
            assert res.status_code in [502, 503, 504]
            print(f"[WARN] HF Datasets-Server upstream returned {res.status_code}; handled gracefully with proper HTTP error code.")

        # 6. Test Metadata & Sync
        res = await client.post("/api/v1/huggingface/sync", headers=headers)
        assert res.status_code == 200
        synced_meta = res.json()
        assert synced_meta["dataset_id"] == "UniDataPro/deepfake-videos-dataset"
        assert synced_meta["total_rows"] == 10
        assert synced_meta["license"] == "cc-by-nc-nd-4.0"
        print(f"[PASS] HF Metadata Synced to DB: License={synced_meta['license']}, Rows={synced_meta['total_rows']}")

        # 7. Test Cached Metadata Retrieval
        res = await client.get("/api/v1/huggingface/metadata", headers=headers)
        assert res.status_code == 200
        cached_meta = res.json()
        assert cached_meta["dataset_id"] == "UniDataPro/deepfake-videos-dataset"
        assert cached_meta["last_synced_at"] is not None
        print("[PASS] HF Cached Metadata Retrieved from DB")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_huggingface_api_integration())

