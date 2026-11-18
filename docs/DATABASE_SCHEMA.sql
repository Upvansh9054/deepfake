-- Deepfake Shield Database Schema (PostgreSQL 15+)
-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enum Types
CREATE TYPE user_role AS ENUM ('analyst', 'admin', 'auditor', 'api_client');
CREATE TYPE media_type AS ENUM ('audio', 'video', 'stream');
CREATE TYPE job_status AS ENUM ('queued', 'preprocessing', 'inferencing', 'completed', 'failed');
CREATE TYPE verdict_type AS ENUM ('authentic', 'suspicious', 'manipulated', 'inconclusive');
CREATE TYPE stream_session_status AS ENUM ('active', 'paused', 'closed', 'terminated');

-- 1. Users & API Keys
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(150),
    role user_role DEFAULT 'analyst',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    key_prefix VARCHAR(16) NOT NULL,
    hashed_key VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    rate_limit_per_min INT DEFAULT 60,
    expires_at TIMESTAMP WITH TIME ZONE,
    is_revoked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Media Ingestion & Uploads
CREATE TABLE media_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    file_name VARCHAR(255) NOT NULL,
    original_path VARCHAR(500) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    media_type media_type NOT NULL,
    sha256_hash VARCHAR(64) UNIQUE NOT NULL,
    duration_seconds FLOAT,
    audio_sample_rate INT,
    video_fps FLOAT,
    video_resolution VARCHAR(32),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Batch Detection Jobs
CREATE TABLE detection_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    media_file_id UUID REFERENCES media_files(id) ON DELETE CASCADE,
    status job_status DEFAULT 'queued',
    priority INT DEFAULT 1,
    progress_percentage INT DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Audio Forensics Results
CREATE TABLE audio_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    detection_job_id UUID REFERENCES detection_jobs(id) ON DELETE CASCADE,
    synthetic_speech_probability FLOAT NOT NULL, -- 0.0 to 1.0 (AASIST / Wav2Vec2)
    voice_clone_probability FLOAT NOT NULL,      -- Speaker embedding anomaly score
    spectral_flatness_mean FLOAT,
    zero_crossing_rate_mean FLOAT,
    vocoder_artifact_detected BOOLEAN DEFAULT FALSE,
    spectral_inconsistencies JSONB,              -- Timestamped frequency cutoffs / artifacts
    detected_model_signatures TEXT[],            -- e.g., ['ElevenLabs-V2', 'Bark', 'VITS']
    verdict verdict_type NOT NULL,
    confidence_score FLOAT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Video Forensics Results
CREATE TABLE video_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    detection_job_id UUID REFERENCES detection_jobs(id) ON DELETE CASCADE,
    spatial_manipulation_score FLOAT NOT NULL,   -- EfficientNet / Swin-T face artifact score
    temporal_inconsistency_score FLOAT NOT NULL, -- Frame-to-frame jitter & landmark stability
    blink_rate_anomaly BOOLEAN DEFAULT FALSE,
    eye_aspect_ratio_history JSONB,              -- Array of [{timestamp: 1.2, ear: 0.18}]
    face_warping_detected BOOLEAN DEFAULT FALSE,
    boundary_artifacts_detected BOOLEAN DEFAULT FALSE,
    flagged_frame_intervals JSONB,               -- [{start_sec: 2.1, end_sec: 4.8, confidence: 0.92, type: 'deepfake_face_swap'}]
    extracted_faces_count INT DEFAULT 0,
    verdict verdict_type NOT NULL,
    confidence_score FLOAT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. Multimodal Fusion Reports
CREATE TABLE multimodal_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    detection_job_id UUID UNIQUE REFERENCES detection_jobs(id) ON DELETE CASCADE,
    audio_analysis_id UUID REFERENCES audio_analyses(id) ON DELETE CASCADE,
    video_analysis_id UUID REFERENCES video_analyses(id) ON DELETE CASCADE,
    lip_sync_error_score FLOAT NOT NULL,         -- SyncNet AV confidence offset
    cross_modal_inconsistency FLOAT NOT NULL,    -- Discrepancy between visual emotion & vocal acoustics
    composite_risk_score FLOAT NOT NULL,         -- Calibrated Bayesian combined score [0 - 100]
    final_verdict verdict_type NOT NULL,
    summary_explanation TEXT NOT NULL,           -- Explainable reasoning for human analysts
    anomaly_timeline JSONB NOT NULL,             -- Merged audio-video second-by-second anomaly markers
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. Real-Time Streaming Sessions & Live Events
CREATE TABLE stream_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    session_title VARCHAR(200) NOT NULL,
    protocol VARCHAR(32) DEFAULT 'websocket',     -- 'websocket' or 'webrtc'
    status stream_session_status DEFAULT 'active',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP WITH TIME ZONE,
    total_frames_processed INT DEFAULT 0,
    total_audio_chunks_processed INT DEFAULT 0,
    peak_risk_score FLOAT DEFAULT 0.0,
    average_risk_score FLOAT DEFAULT 0.0
);

CREATE TABLE stream_event_telemetry (
    id BIGSERIAL PRIMARY KEY,
    stream_session_id UUID REFERENCES stream_sessions(id) ON DELETE CASCADE,
    timestamp_offset_ms BIGINT NOT NULL,
    audio_synthetic_prob FLOAT NOT NULL,
    video_spatial_prob FLOAT NOT NULL,
    sync_discrepancy_prob FLOAT NOT NULL,
    instantaneous_risk_score FLOAT NOT NULL,
    flagged_alert BOOLEAN DEFAULT FALSE,
    alert_details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 8. Audit Logs & Forensic Evidence Chain of Custody
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id UUID NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 9. Hugging Face Dataset Metadata & Benchmark Cache
CREATE TABLE dataset_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id VARCHAR(255) UNIQUE NOT NULL,
    author VARCHAR(100),
    description TEXT,
    license VARCHAR(100),
    tags JSONB DEFAULT '[]',
    splits JSONB DEFAULT '[]',
    total_rows INT DEFAULT 0,
    parquet_urls JSONB DEFAULT '[]',
    features_schema JSONB DEFAULT '[]',
    last_synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for high-performance querying
CREATE INDEX idx_media_files_hash ON media_files(sha256_hash);
CREATE INDEX idx_detection_jobs_status ON detection_jobs(status);
CREATE INDEX idx_multimodal_composite_risk ON multimodal_reports(composite_risk_score);
CREATE INDEX idx_stream_telemetry_session_time ON stream_event_telemetry(stream_session_id, timestamp_offset_ms);
CREATE INDEX idx_audit_logs_user_action ON audit_logs(user_id, action);
CREATE INDEX idx_dataset_metadata_id ON dataset_metadata(dataset_id);

