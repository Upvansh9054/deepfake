from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID

class StreamInitConfig(BaseModel):
    audio_sample_rate: int = 16000
    video_fps: int = 10
    sensitivity: str = "balanced"  # 'conservative', 'balanced', 'aggressive'

class StreamMetrics(BaseModel):
    audio_synthetic_prob: float = Field(..., ge=0.0, le=1.0)
    video_manipulation_prob: float = Field(..., ge=0.0, le=1.0)
    lip_sync_drift_ms: float
    spectral_flatness: Optional[float] = 0.0
    high_frequency_ratio: Optional[float] = 0.0
    fft_spectral_residual: Optional[float] = 0.0
    faces_detected: Optional[int] = 0
    average_blink_rate: Optional[float] = 14.5

class StreamAnomaly(BaseModel):
    type: str
    severity: str
    message: Optional[str] = None

class NormalizedBBox(BaseModel):
    x: float
    y: float
    w: float
    h: float

class StreamTelemetry(BaseModel):
    type: str = "telemetry"
    session_id: str
    timestamp_ms: int
    latency_ms: float = 0.0
    fps: float = 0.0
    composite_risk_score: float = Field(..., ge=0.0, le=100.0)
    verdict: str
    risk_category: str = "Low Risk"
    metrics: StreamMetrics
    anomalies: List[StreamAnomaly] = []
    face_bbox: Optional[NormalizedBBox] = None
    governance_notice: Optional[str] = None

