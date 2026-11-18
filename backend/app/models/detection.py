import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(150))
    role = Column(String(50), default="analyst")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class MediaFile(Base):
    __tablename__ = "media_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    file_name = Column(String(255), nullable=False)
    original_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    media_type = Column(String(50), nullable=False)
    sha256_hash = Column(String(64), unique=True, index=True, nullable=False)
    duration_seconds = Column(Float, nullable=True)
    audio_sample_rate = Column(Integer, nullable=True)
    video_fps = Column(Float, nullable=True)
    video_resolution = Column(String(32), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class DetectionJob(Base):
    __tablename__ = "detection_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_file_id = Column(UUID(as_uuid=True), ForeignKey("media_files.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), default="queued", index=True)
    progress_percentage = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    audio_analysis = relationship("AudioAnalysis", back_populates="job", uselist=False)
    video_analysis = relationship("VideoAnalysis", back_populates="job", uselist=False)
    multimodal_report = relationship("MultimodalReport", back_populates="job", uselist=False)

class AudioAnalysis(Base):
    __tablename__ = "audio_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    detection_job_id = Column(UUID(as_uuid=True), ForeignKey("detection_jobs.id", ondelete="CASCADE"), nullable=False)
    synthetic_speech_probability = Column(Float, nullable=False)
    voice_clone_probability = Column(Float, nullable=False)
    spectral_flatness_mean = Column(Float, nullable=True)
    zero_crossing_rate_mean = Column(Float, nullable=True)
    vocoder_artifact_detected = Column(Boolean, default=False)
    spectral_inconsistencies = Column(JSONB, nullable=True)
    detected_model_signatures = Column(JSONB, nullable=True)
    verdict = Column(String(50), nullable=False)
    confidence_score = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    job = relationship("DetectionJob", back_populates="audio_analysis")

class VideoAnalysis(Base):
    __tablename__ = "video_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    detection_job_id = Column(UUID(as_uuid=True), ForeignKey("detection_jobs.id", ondelete="CASCADE"), nullable=False)
    spatial_manipulation_score = Column(Float, nullable=False)
    temporal_inconsistency_score = Column(Float, nullable=False)
    blink_rate_anomaly = Column(Boolean, default=False)
    eye_aspect_ratio_history = Column(JSONB, nullable=True)
    face_warping_detected = Column(Boolean, default=False)
    boundary_artifacts_detected = Column(Boolean, default=False)
    flagged_frame_intervals = Column(JSONB, nullable=True)
    extracted_faces_count = Column(Integer, default=0)
    verdict = Column(String(50), nullable=False)
    confidence_score = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    job = relationship("DetectionJob", back_populates="video_analysis")

class MultimodalReport(Base):
    __tablename__ = "multimodal_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    detection_job_id = Column(UUID(as_uuid=True), ForeignKey("detection_jobs.id", ondelete="CASCADE"), nullable=False)
    audio_analysis_id = Column(UUID(as_uuid=True), ForeignKey("audio_analyses.id", ondelete="CASCADE"), nullable=True)
    video_analysis_id = Column(UUID(as_uuid=True), ForeignKey("video_analyses.id", ondelete="CASCADE"), nullable=True)
    lip_sync_error_score = Column(Float, nullable=False)
    cross_modal_inconsistency = Column(Float, nullable=False)
    composite_risk_score = Column(Float, nullable=False, index=True)
    final_verdict = Column(String(50), nullable=False)
    summary_explanation = Column(Text, nullable=False)
    anomaly_timeline = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    job = relationship("DetectionJob", back_populates="multimodal_report")

class StreamSession(Base):
    __tablename__ = "stream_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    session_title = Column(String(200), nullable=False)
    protocol = Column(String(32), default="websocket")
    status = Column(String(50), default="active")
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    total_frames_processed = Column(Integer, default=0)
    total_audio_chunks_processed = Column(Integer, default=0)
    peak_risk_score = Column(Float, default=0.0)
    average_risk_score = Column(Float, default=0.0)

