export type VerdictType = 'authentic' | 'suspicious' | 'manipulated' | 'inconclusive';

export interface BoundingBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface AcousticMetrics {
  spectral_flatness_mean: number;
  spectral_centroid_mean: number;
  zero_crossing_rate_mean: number;
  high_frequency_energy_ratio: number;
}

export interface AudioAnalysisResult {
  job_id: string;
  duration_seconds: number;
  sample_rate: number;
  synthetic_speech_probability: number;
  voice_clone_probability: number;
  verdict: VerdictType;
  confidence_score: number;
  vocoder_artifacts_detected: boolean;
  acoustic_metrics: AcousticMetrics;
}

export interface FacialForensics {
  faces_detected: number;
  eye_blinking_anomaly: boolean;
  average_blink_rate_per_min: number;
  boundary_warping_detected: boolean;
  landmark_jitter_score: number;
}

export interface VideoAnalysisResult {
  job_id: string;
  duration_seconds: number;
  fps: number;
  resolution: string;
  spatial_manipulation_score: number;
  temporal_inconsistency_score: number;
  verdict: VerdictType;
  confidence_score: number;
  facial_forensics: FacialForensics;
}

export interface StreamTelemetry {
  type: string;
  session_id: string;
  timestamp_ms: number;
  latency_ms?: number;
  fps?: number;
  composite_risk_score: number;
  verdict: VerdictType;
  risk_category?: string;
  metrics: {
    audio_synthetic_prob: number;
    video_manipulation_prob: number;
    lip_sync_drift_ms: number;
    spectral_flatness?: number;
    high_frequency_ratio?: number;
    fft_spectral_residual?: number;
    faces_detected?: number;
    average_blink_rate?: number;
  };
  anomalies: Array<{ type: string; severity: string; message?: string }>;
  face_bbox?: BoundingBox;
  governance_notice?: string;
}

