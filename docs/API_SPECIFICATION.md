# Deepfake Shield API Specification (v1)

## Overview
Deepfake Shield provides a dual-interface architecture:
1. **REST API**: For file uploads, asynchronous batch forensic analysis, reporting, user management, and session control.
2. **WebSocket & WebRTC Stream API**: For real-time, ultra-low-latency (< 300ms) continuous deepfake and synthetic voice detection from live camera and microphone streams.

Base URL: `http://localhost:8000/api/v1`
WebSocket Base URL: `ws://localhost:8000/api/v1/stream`

---

## 1. Authentication & Security
All authenticated endpoints require an `Authorization` header with a Bearer JWT or an API Key:
```http
Authorization: Bearer <access_token>
X-API-Key: dfs_<prefix>_<secret_hash>
```

---

## 2. Audio Detection Endpoints

### 2.1 Analyze Audio File
- **POST** `/audio/analyze`
- **Content-Type**: `multipart/form-data`
- **Request Body**:
  - `file`: Binary audio file (`wav`, `mp3`, `flac`, `m4a`, `ogg`)
  - `enable_voice_cloning_check`: boolean (default: `true`)
  - `reference_speaker_file`: Optional reference speaker audio for cloning distance measurement
- **Response** `(200 OK)`:
```json
{
  "job_id": "8fa8430b-d0e5-4f40-8b17-73d8e52dbbfa",
  "status": "completed",
  "media_type": "audio",
  "duration_seconds": 12.4,
  "sample_rate": 16000,
  "results": {
    "synthetic_speech_probability": 0.884,
    "voice_clone_probability": 0.792,
    "verdict": "manipulated",
    "confidence_score": 0.89,
    "vocoder_artifacts_detected": true,
    "acoustic_metrics": {
      "spectral_flatness_mean": 0.041,
      "spectral_centroid_mean": 2150.3,
      "zero_crossing_rate_mean": 0.078
    },
    "anomalous_segments": [
      {
        "start_time": 3.2,
        "end_time": 7.4,
        "synthetic_score": 0.94,
        "reason": "High frequency vocoder phase cutoff and robotic formant distortion"
      }
    ],
    "potential_generator_signatures": ["ElevenLabs-V2", "HiFi-GAN"]
  }
}
```

---

## 3. Video Detection Endpoints

### 3.1 Analyze Video File
- **POST** `/video/analyze`
- **Content-Type**: `multipart/form-data`
- **Request Body**:
  - `file`: Binary video file (`mp4`, `mkv`, `mov`, `avi`, `webm`)
  - `frame_sample_rate`: integer (default: `3` frames per second for forensics)
  - `extract_faces`: boolean (default: `true`)
- **Response** `(200 OK)`:
```json
{
  "job_id": "c138d672-887e-4008-8f15-776263884e92",
  "status": "completed",
  "media_type": "video",
  "video_metadata": {
    "duration_seconds": 24.0,
    "fps": 30.0,
    "resolution": "1920x1080",
    "total_frames_sampled": 72
  },
  "results": {
    "spatial_manipulation_score": 0.912,
    "temporal_inconsistency_score": 0.835,
    "verdict": "manipulated",
    "confidence_score": 0.91,
    "facial_forensics": {
      "faces_detected": 1,
      "eye_blinking_anomaly": true,
      "average_blink_rate_per_min": 2.1,
      "boundary_warping_detected": true
    },
    "flagged_intervals": [
      {
        "start_sec": 4.0,
        "end_sec": 11.2,
        "confidence": 0.94,
        "manipulation_type": "face_swap_synthetic_skin_smoothing",
        "bounding_box": {"x": 340, "y": 180, "w": 280, "h": 320}
      }
    ]
  }
}
```

---

## 4. Multimodal Fusion Endpoints

### 4.1 Comprehensive Media Forensics
- **POST** `/multimodal/analyze`
- **Content-Type**: `multipart/form-data`
- **Request Body**:
  - `file`: Binary video file with audio
  - `analysis_depth`: string (`"fast"` | `"standard"` | `"deep_forensic"`)
- **Response** `(200 OK)`:
```json
{
  "job_id": "0384a56c-17e9-4e78-a006-218f2762ce3b",
  "verdict": "manipulated",
  "composite_risk_score": 93.4,
  "confidence_rating": "high",
  "summary": "High-confidence deepfake detected. Visual analysis identified synthetic face swapping and warping artifacts between 00:04 and 00:11. Audio analysis identified high-frequency synthetic speech vocoder artifacts. Multimodal lip-sync alignment shows a 140ms desynchronization.",
  "breakdown": {
    "audio_risk": 0.88,
    "video_risk": 0.91,
    "lip_sync_error_score": 0.89,
    "cross_modal_inconsistency": 0.78
  },
  "timeline_anomalies": [
    {
      "timestamp_start": 4.0,
      "timestamp_end": 11.2,
      "domain": "cross_modal",
      "severity": "critical",
      "description": "Visual face swap coupled with synthetic speech phoneme-viseme mismatch"
    }
  ]
}
```

---

## 5. Real-Time Streaming (WebSocket)

### 5.1 Real-Time Streaming Session
- **WebSocket Endpoint**: `ws://localhost:8000/api/v1/stream/live/{session_id}`
- **Query Params**: `token=<jwt_token>`

#### Client -> Server Frames:
Client streams interleaved audio buffers and video keyframes.

1. **Init Handshake**:
```json
{
  "type": "init",
  "config": {
    "audio_sample_rate": 16000,
    "video_fps": 10,
    "sensitivity": "balanced"
  }
}
```

2. **Audio Chunk**:
```json
{
  "type": "audio_chunk",
  "timestamp_ms": 1500,
  "audio_base64_pcm": "UklGRi..."
}
```

3. **Video Keyframe**:
```json
{
  "type": "video_frame",
  "timestamp_ms": 1500,
  "frame_base64_jpeg": "/9j/4AAQSkZJRg..."
}
```

#### Server -> Client Live Telemetry (< 250ms interval):
```json
{
  "type": "telemetry",
  "session_id": "f5e92c4e-fcf6-407a-9a99-b1d55e81d113",
  "timestamp_ms": 1500,
  "composite_risk_score": 87.5,
  "verdict": "suspicious",
  "metrics": {
    "audio_synthetic_prob": 0.84,
    "video_manipulation_prob": 0.79,
    "lip_sync_drift_ms": 120
  },
  "anomalies": [
    {
      "type": "synthetic_voice_frequency_artifact",
      "severity": "high"
    }
  ],
  "face_bbox": {
    "x": 0.35,
    "y": 0.22,
    "w": 0.28,
    "h": 0.34
  }
}
```

