from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class ScanBase(BaseModel):
    title: str
    media_type: str  # 'audio', 'video', 'stream'

class ScanCreate(ScanBase):
    pass

class UrlScanRequest(BaseModel):
    url: str
    title: Optional[str] = None
    scan_type: Optional[str] = "video"

class ScanResultSchema(BaseModel):
    id: str
    synthetic_prob: float
    spatial_prob: float
    temporal_prob: float
    audio_metrics: Dict[str, Any]
    video_metrics: Dict[str, Any]
    verdict: str
    confidence_score: float
    flagged_intervals: List[Dict[str, Any]]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class RiskReportSchema(BaseModel):
    id: str
    composite_risk_score: float
    risk_level: str
    summary_explanation: str
    recommendations: List[str]
    breakdown: Dict[str, Any]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ScanResponse(BaseModel):
    id: str
    user_id: str
    title: str
    media_type: str
    file_name: str
    file_size_bytes: int
    mime_type: str
    sha256_hash: str
    status: str
    progress_percentage: int
    duration_seconds: float
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ScanDetailResponse(ScanResponse):
    result: Optional[ScanResultSchema] = None
    risk_report: Optional[RiskReportSchema] = None

class ScanListResponse(BaseModel):
    total: int
    page: int
    limit: int
    items: List[ScanDetailResponse]
