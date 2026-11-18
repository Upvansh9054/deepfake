from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from uuid import UUID

class AudioMetricSummary(BaseModel):
    spectral_flatness_mean: float
    spectral_centroid_mean: float
    zero_crossing_rate_mean: float
    high_frequency_energy_ratio: float
    dynamic_energy_variance: Optional[float] = 0.0
    rms_energy_dbfs: Optional[float] = 0.0
    model_config = ConfigDict(from_attributes=True)

class AudioAnomalySegment(BaseModel):
    start_time: float
    end_time: float
    synthetic_score: float
    reason: str
    model_config = ConfigDict(from_attributes=True)

class AudioAnalysisResponse(BaseModel):
    job_id: UUID
    status: str
    media_type: str = "audio"
    duration_seconds: float
    sample_rate: int
    classification: str = "genuine"  # 'genuine', 'suspicious', 'synthetic', 'uncertain'
    verdict: str  # 'authentic', 'suspicious', 'manipulated', 'inconclusive'
    model_confidence: float = Field(..., ge=0.0, le=1.0)
    synthetic_speech_probability: float = Field(..., ge=0.0, le=1.0)
    voice_clone_probability: float = Field(..., ge=0.0, le=1.0)
    calibrated_fraud_risk: float = Field(..., ge=0.0, le=100.0)
    risk_level: str = "LOW"
    inference_engine: str = "pretrained_asvspoof"
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    vocoder_artifacts_detected: bool
    acoustic_metrics: AudioMetricSummary
    explainability_summary: str
    actionable_recommendations: List[str] = []
    anomalous_segments: List[AudioAnomalySegment] = []
    potential_generator_signatures: List[str] = []
    model_limitations: List[str] = []
    model_config = ConfigDict(from_attributes=True)
