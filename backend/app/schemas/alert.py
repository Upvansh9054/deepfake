from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime

class AlertResponse(BaseModel):
    id: str
    user_id: str
    scan_id: Optional[str] = None
    alert_type: str
    severity: str
    title: str
    message: str
    is_read: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AuditLogResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    action: str
    resource_type: str
    resource_id: str
    ip_address: Optional[str] = None
    details: Dict[str, Any] = {}
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AnalyticsOverview(BaseModel):
    total_scans: int
    audio_scans: int
    video_scans: int
    multimodal_scans: int = 0
    threats_detected: int
    clean_scans: int
    average_risk_score: float
    active_threat_level: str
    recent_activity: List[Dict[str, Any]]
