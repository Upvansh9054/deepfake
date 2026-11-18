from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from uuid import UUID

class BoundingBox(BaseModel):
    x: float
    y: float
    w: float
    h: float

class FlaggedInterval(BaseModel):
    start_sec: float
    end_sec: float
    confidence: float
    manipulation_type: str
    bounding_box: Optional[BoundingBox] = None

class FacialForensicSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    faces_detected: int
    eye_blinking_anomaly: bool = False
    average_blink_rate_per_min: float = 0.0
    boundary_warping_detected: bool = False
    landmark_jitter_score: float = 0.0
    spectral_fft_residual: Optional[float] = None
    facial_boundary_disparity: Optional[float] = None

class VideoAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: UUID
    status: str = "completed"
    media_type: str = "video"
    duration_seconds: float
    fps: float
    resolution: str
    total_frames_sampled: int
    faces_detected: int = 0
    spatial_manipulation_score: float = Field(..., ge=0.0, le=1.0)
    temporal_inconsistency_score: float = Field(..., ge=0.0, le=1.0)
    verdict: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    classification: str = "uncertain"
    calibrated_fraud_risk: float = 0.0
    risk_level: str = "LOW"
    inference_engine: str = "Pretrained Vision & Spatial Seam Forensics"
    facial_forensics: FacialForensicSummary
    suspicious_timestamps: List[float] = []
    flagged_intervals: List[FlaggedInterval] = []
    explainability_summary: Optional[str] = None
    actionable_recommendations: List[str] = []
    model_limitations: List[str] = []
