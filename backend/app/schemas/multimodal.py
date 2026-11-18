from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from uuid import UUID

class SignalAttribution(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    audio_contribution_pct: float = Field(..., ge=0.0, le=100.0)
    video_contribution_pct: float = Field(..., ge=0.0, le=100.0)
    sync_contribution_pct: float = Field(..., ge=0.0, le=100.0)
    asymmetry_penalty_pct: float = Field(..., ge=0.0, le=100.0)

class SyncMetrics(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lip_sync_correlation: float = Field(..., ge=-1.0, le=1.0)
    sync_drift_ms: float
    sync_error_score: float = Field(..., ge=0.0, le=1.0)
    is_synchronized: bool = True
    asynchronous_intervals: List[Dict[str, Any]] = []

class MultimodalBreakdown(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    audio_risk: float = Field(..., ge=0.0, le=1.0)
    video_risk: float = Field(..., ge=0.0, le=1.0)
    sync_error_score: float = Field(..., ge=0.0, le=1.0)
    cross_modal_inconsistency: float = Field(..., ge=0.0, le=1.0)
    evidence_status: str = "both_modalities_present"  # 'both_modalities_present', 'audio_missing', 'video_missing', 'insufficient_evidence'
    signal_attribution: SignalAttribution

class TimelineAnomaly(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    start_sec: float
    end_sec: float
    domain: str  # 'audio', 'video', 'cross_modal'
    severity: str  # 'low', 'medium', 'high', 'critical'
    description: str
    bounding_box: Optional[Dict[str, float]] = None

class MultimodalFusionRequest(BaseModel):
    audio_result: Optional[Dict[str, Any]] = None
    video_result: Optional[Dict[str, Any]] = None

class MultimodalAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: UUID
    media_type: str = "multimodal"
    verdict: str  # 'authentic', 'suspicious', 'manipulated', 'inconclusive'
    risk_category: str  # 'Low Risk', 'Medium Risk', 'High Risk', 'Inconclusive'
    composite_risk_score: float = Field(..., ge=0.0, le=100.0)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    summary_explanation: str
    breakdown: MultimodalBreakdown
    sync_metrics: Optional[SyncMetrics] = None
    suspicious_timestamps: List[float] = []
    timeline_anomalies: List[TimelineAnomaly] = []
    actionable_recommendations: List[str] = []
    model_limitations: List[str] = []
