"""
Unit & Integration tests for Phase 4 AI Voice Deepfake Detection.
Validates AudioPreprocessor, AudioDeepfakeDetector, Silent/Corrupted handling,
Model confidence vs Calibrated Risk separation, and FastAPI endpoints.
"""

import sys
from pathlib import Path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

import pytest
import numpy as np
import wave
import io
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import init_db
from app.services.audio_preprocessor import audio_preprocessor, AudioValidationError
from app.services.audio_deepfake_detector import audio_deepfake_detector

def generate_wav_bytes(duration_sec: float = 2.0, freq_hz: float = 440.0, sample_rate: int = 16000, is_silent: bool = False) -> bytes:
    """Helper to synthesize valid WAV byte streams in memory."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        total_samples = int(duration_sec * sample_rate)
        if is_silent:
            data = np.zeros(total_samples, dtype=np.int16)
        else:
            t = np.linspace(0, duration_sec, total_samples, False)
            # Mixed frequencies mimicking speech formants
            signal = (0.5 * np.sin(2 * np.pi * freq_hz * t) + 0.3 * np.sin(2 * np.pi * (freq_hz * 2.2) * t))
            data = (signal * 30000).astype(np.int16)
        wf.writeframes(data.tobytes())
    return buf.getvalue()

@pytest.mark.asyncio
async def test_audio_preprocessing_and_validations():
    # 1. Normal Audio
    normal_wav = generate_wav_bytes(duration_sec=3.0, freq_hz=300.0)
    pcm, sr, dur, meta = audio_preprocessor.read_audio_bytes(normal_wav, "normal.wav")
    assert sr == 16000
    assert dur == 3.0
    assert meta["is_silent"] is False
    assert meta["is_too_short"] is False
    assert meta["was_clipped"] is False
    print("\n[PASS] Normal audio correctly parsed & validated")

    # 2. Silent Audio
    silent_wav = generate_wav_bytes(duration_sec=2.0, is_silent=True)
    pcm_s, sr_s, dur_s, meta_s = audio_preprocessor.read_audio_bytes(silent_wav, "silent.wav")
    assert meta_s["is_silent"] is True
    print("[PASS] Silent audio detected (< -50 dBFS)")

    # 3. Excessively Long Audio (> 30s)
    long_wav = generate_wav_bytes(duration_sec=35.0, freq_hz=400.0)
    pcm_l, sr_l, dur_l, meta_l = audio_preprocessor.read_audio_bytes(long_wav, "long.wav")
    assert meta_l["original_duration_seconds"] == 35.0
    assert meta_l["processed_duration_seconds"] == 30.0
    assert meta_l["was_clipped"] is True
    assert len(pcm_l) == 16000 * 30
    print("[PASS] Excessively long audio automatically windowed to 30.0s")

    # 4. Too Short Audio (< 0.5s)
    short_wav = generate_wav_bytes(duration_sec=0.3, freq_hz=500.0)
    pcm_sh, sr_sh, dur_sh, meta_sh = audio_preprocessor.read_audio_bytes(short_wav, "short.wav")
    assert meta_sh["is_too_short"] is True
    print("[PASS] Too short audio (< 0.5s) flagged")

    # 5. Corrupted Audio
    with pytest.raises(AudioValidationError):
        audio_preprocessor.read_audio_bytes(b"NOT_A_VALID_WAV_HEADER", "corrupted.wav")
    print("[PASS] Corrupted audio properly caught and rejected")

@pytest.mark.asyncio
async def test_deepfake_detector_and_api():
    await init_db()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Login with demo analyst
        login_res = await client.post("/api/v1/auth/login", json={
            "email": "analyst@shield.ai",
            "password": "CyberSecurity2026!"
        })
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Analyze Normal Speech Audio via API
        valid_wav = generate_wav_bytes(duration_sec=2.5, freq_hz=350.0)
        files = {"file": ("speech_sample.wav", io.BytesIO(valid_wav), "audio/wav")}
        res = await client.post("/api/v1/audio/analyze", headers=headers, files=files)
        assert res.status_code == 200
        analysis = res.json()
        assert analysis["classification"] in ["genuine", "suspicious", "synthetic"]
        assert analysis["duration_seconds"] == 2.5
        assert "model_confidence" in analysis
        assert "calibrated_fraud_risk" in analysis
        assert "explainability_summary" in analysis
        assert len(analysis["actionable_recommendations"]) > 0
        assert len(analysis["model_limitations"]) > 0
        print(f"[PASS] Audio Analyzed: Classification={analysis['classification']}, Conf={analysis['model_confidence']}, Risk={analysis['calibrated_fraud_risk']}%")

        # 3. Analyze Silent Audio via API
        silent_wav = generate_wav_bytes(duration_sec=2.0, is_silent=True)
        files_s = {"file": ("silent_room.wav", io.BytesIO(silent_wav), "audio/wav")}
        res_s = await client.post("/api/v1/audio/analyze", headers=headers, files=files_s)
        assert res_s.status_code == 200
        analysis_s = res_s.json()
        assert analysis_s["classification"] == "uncertain"
        assert analysis_s["verdict"] == "inconclusive"
        assert analysis_s["calibrated_fraud_risk"] == 0.0
        print("[PASS] Silent Audio returned 'uncertain' classification with 0.0% fraud risk")

        # 4. Analyze Corrupted Audio via API (Expect 400 Bad Request)
        corrupted_bytes = b"CORRUPTED_GARBAGE_PAYLOAD_WITHOUT_HEADER"
        files_c = {"file": ("corrupted.wav", io.BytesIO(corrupted_bytes), "audio/wav")}
        res_c = await client.post("/api/v1/audio/analyze", headers=headers, files=files_c)
        assert res_c.status_code == 400
        assert "Invalid WAV file" in res_c.json()["detail"] or "Corrupted audio file" in res_c.json()["detail"]
        print("[PASS] Corrupted Audio cleanly rejected with HTTP 400")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_audio_preprocessing_and_validations())
    asyncio.run(test_deepfake_detector_and_api())

