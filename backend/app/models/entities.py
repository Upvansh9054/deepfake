import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    role = Column(String(50), default="analyst")  # 'analyst', 'admin', 'auditor'
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    scans = relationship("Scan", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")

class Scan(Base):
    __tablename__ = "scans"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    media_type = Column(String(50), nullable=False)  # 'audio', 'video', 'stream'
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    sha256_hash = Column(String(64), nullable=False, index=True)
    status = Column(String(50), default="completed", index=True)  # 'queued', 'processing', 'completed', 'failed'
    progress_percentage = Column(Integer, default=100)
    duration_seconds = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    user = relationship("User", back_populates="scans")
    result = relationship("ScanResult", back_populates="scan", uselist=False, cascade="all, delete-orphan")
    risk_report = relationship("RiskReport", back_populates="scan", uselist=False, cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="scan", cascade="all, delete-orphan")

class ScanResult(Base):
    __tablename__ = "scan_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    scan_id = Column(String(36), ForeignKey("scans.id", ondelete="CASCADE"), unique=True, nullable=False)
    synthetic_prob = Column(Float, nullable=False, default=0.0)  # Audio synthetic speech probability
    spatial_prob = Column(Float, nullable=False, default=0.0)    # Video spatial boundary manipulation
    temporal_prob = Column(Float, nullable=False, default=0.0)   # Temporal blinking/landmark jitter
    audio_metrics = Column(JSON, default=dict)                   # Flatness, ZCR, vocoder flags
    video_metrics = Column(JSON, default=dict)                   # Face landmarks, EAR, seam gradients
    verdict = Column(String(50), nullable=False, default="authentic")  # 'authentic', 'suspicious', 'manipulated', 'inconclusive'
    confidence_score = Column(Float, nullable=False, default=0.0)
    flagged_intervals = Column(JSON, default=list)               # [{start, end, reason, confidence}]
    created_at = Column(DateTime(timezone=True), default=utc_now)

    scan = relationship("Scan", back_populates="result")

class RiskReport(Base):
    __tablename__ = "risk_reports"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    scan_id = Column(String(36), ForeignKey("scans.id", ondelete="CASCADE"), unique=True, nullable=False)
    composite_risk_score = Column(Float, nullable=False, default=0.0)  # 0.0 - 100.0
    risk_level = Column(String(20), nullable=False, default="LOW")     # 'LOW', 'MODERATE', 'HIGH', 'CRITICAL'
    summary_explanation = Column(Text, nullable=False)
    recommendations = Column(JSON, default=list)
    breakdown = Column(JSON, default=dict)                             # Audio, video, sync weights
    created_at = Column(DateTime(timezone=True), default=utc_now)

    scan = relationship("Scan", back_populates="risk_report")

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    scan_id = Column(String(36), ForeignKey("scans.id", ondelete="CASCADE"), nullable=True)
    alert_type = Column(String(50), nullable=False)                    # 'threat_detected', 'system_event', 'threshold_breach'
    severity = Column(String(20), nullable=False, default="INFO")      # 'INFO', 'WARNING', 'CRITICAL'
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)

    user = relationship("User", back_populates="alerts")
    scan = relationship("Scan", back_populates="alerts")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False)                       # 'user_registered', 'file_uploaded', 'scan_executed'
    resource_type = Column(String(100), nullable=False)                # 'scan', 'user', 'session'
    resource_id = Column(String(36), nullable=False)
    ip_address = Column(String(45), nullable=True)
    details = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)

    user = relationship("User", back_populates="audit_logs")

class DatasetMetadata(Base):
    __tablename__ = "dataset_metadata"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    dataset_id = Column(String(255), unique=True, nullable=False, index=True)
    author = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    license = Column(String(100), nullable=True)
    tags = Column(JSON, default=list)
    splits = Column(JSON, default=list)
    total_rows = Column(Integer, default=0)
    parquet_urls = Column(JSON, default=list)
    features_schema = Column(JSON, default=list)
    last_synced_at = Column(DateTime(timezone=True), default=utc_now)
    created_at = Column(DateTime(timezone=True), default=utc_now)

