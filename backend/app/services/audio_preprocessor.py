"""
Audio Preprocessing and Validation Service.
Handles audio ingestion, format validation, silence detection, duration clipping,
and feature normalization for deepfake voice detection models.
"""

import io
import wave
import struct
import numpy as np
from typing import Dict, Any, Tuple, Optional
from fastapi import HTTPException, status
from app.core.config import settings
import logging

logger = logging.getLogger("deepfake_shield.audio_preprocessor")

class AudioValidationError(Exception):
    """Custom exception raised when audio input fails forensic validation."""
    pass

class NormalizedAudioValidation:
    def __init__(self, pcm_samples: np.ndarray, sample_rate: int, duration_sec: float, metadata: Dict[str, Any]):
        self.pcm_samples = pcm_samples
        self.sample_rate = sample_rate
        self.duration_sec = duration_sec
        self.metadata = metadata

class AudioPreprocessor:
    def __init__(self, target_sample_rate: int = 16000, max_duration_seconds: float = 30.0):
        self.target_sample_rate = target_sample_rate
        self.max_duration_seconds = max_duration_seconds
        self.max_samples = int(target_sample_rate * max_duration_seconds)
        self.silence_threshold_dbfs = -50.0  # Signals below -50 dBFS are flagged as silent
        self.min_speech_duration_seconds = 0.5  # Sub-second audio cannot be reliably classified

    def read_audio_bytes(self, content: bytes, filename: str = "audio.wav") -> Tuple[np.ndarray, int, float, Dict[str, Any]]:
        """
        Reads raw audio file bytes, validates integrity, extracts 16kHz float32 PCM samples,
        and returns (pcm_data, sample_rate, duration_seconds, metadata).
        """
        if not content or len(content) < 44:
            raise AudioValidationError("Corrupted audio file: File is empty or smaller than standard audio header (44 bytes).")

        # 1. Inspect RIFF / WAV header
        is_wav = content.startswith(b"RIFF") and b"WAVE" in content[:16]

        pcm_data: Optional[np.ndarray] = None
        sample_rate: int = self.target_sample_rate
        channels: int = 1

        if is_wav:
            try:
                with wave.open(io.BytesIO(content), "rb") as wf:
                    channels = wf.getnchannels()
                    sampwidth = wf.getsampwidth()
                    sample_rate = wf.getframerate()
                    nframes = wf.getnframes()
                    raw_frames = wf.readframes(nframes)

                    if sampwidth == 2:  # 16-bit PCM
                        pcm_int = np.frombuffer(raw_frames, dtype=np.int16)
                        pcm_float = pcm_int.astype(np.float32) / 32768.0
                    elif sampwidth == 1:  # 8-bit unsigned PCM
                        pcm_uint = np.frombuffer(raw_frames, dtype=np.uint8)
                        pcm_float = (pcm_uint.astype(np.float32) - 128.0) / 128.0
                    elif sampwidth == 4:  # 32-bit float or 32-bit int
                        pcm_float = np.frombuffer(raw_frames, dtype=np.float32)
                    else:
                        pcm_int = np.frombuffer(raw_frames[:len(raw_frames) - (len(raw_frames) % 2)], dtype=np.int16)
                        pcm_float = pcm_int.astype(np.float32) / 32768.0

                    # Convert multi-channel to mono
                    if channels > 1:
                        pcm_float = pcm_float.reshape(-1, channels).mean(axis=1)

                    pcm_data = pcm_float
            except Exception as e:
                logger.warning(f"Wave module failed to parse WAV: {e}. Falling back to raw byte stream parsing.")

        # Fallback for non-standard WAV, MP3, or raw audio
        if pcm_data is None:
            # Skip header bytes if present
            header_offset = 44 if is_wav else 0
            trimmed = content[header_offset:]
            valid_len = len(trimmed) - (len(trimmed) % 2)
            if valid_len == 0:
                raise AudioValidationError("Corrupted audio data: Unable to parse linear audio frames.")
            pcm_int = np.frombuffer(trimmed[:valid_len], dtype=np.int16)
            pcm_data = pcm_int.astype(np.float32) / 32768.0
            sample_rate = 16000

        # Simple linear resample to 16kHz if different
        if sample_rate != self.target_sample_rate and sample_rate > 0:
            target_len = int(len(pcm_data) * (self.target_sample_rate / sample_rate))
            if target_len > 0 and len(pcm_data) > 1:
                indices = np.linspace(0, len(pcm_data) - 1, target_len)
                pcm_data = np.interp(indices, np.arange(len(pcm_data)), pcm_data)
            sample_rate = self.target_sample_rate

        total_samples = len(pcm_data)
        if total_samples == 0:
            raise AudioValidationError("Audio stream contains no readable PCM samples.")
        original_duration = float(total_samples / max(1, sample_rate))

        # 2. Check for Silence
        rms = float(np.sqrt(np.mean(pcm_data ** 2)))
        dbfs = float(20 * np.log10(rms + 1e-9))
        is_silent = (dbfs < self.silence_threshold_dbfs) or (float(np.var(pcm_data)) < 1e-7)

        # 3. Check for Excessively Short Audio
        is_too_short = (original_duration < self.min_speech_duration_seconds)

        # 4. Check for Excessively Long Audio & Clip to max window (30s)
        was_clipped = False
        clipped_duration = original_duration
        if original_duration > self.max_duration_seconds:
            pcm_data = pcm_data[:self.max_samples]
            clipped_duration = self.max_duration_seconds
            was_clipped = True

        metadata = {
            "original_duration_seconds": round(original_duration, 2),
            "processed_duration_seconds": round(clipped_duration, 2),
            "sample_rate": sample_rate,
            "channels": channels,
            "rms_energy_dbfs": round(dbfs, 2),
            "is_silent": is_silent,
            "is_too_short": is_too_short,
            "was_clipped": was_clipped,
        }

        return pcm_data, sample_rate, clipped_duration, metadata

    def validate_and_normalize(self, content: bytes, filename: str = "audio.wav") -> NormalizedAudioValidation:
        """Convenience method returning NormalizedAudioValidation object with pcm_samples attribute."""
        pcm_data, sample_rate, duration_sec, metadata = self.read_audio_bytes(content, filename)
        return NormalizedAudioValidation(pcm_data, sample_rate, duration_sec, metadata)

audio_preprocessor = AudioPreprocessor()

