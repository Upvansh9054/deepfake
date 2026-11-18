# Deepfake Shield – System Architecture

## 1. System Overview
Deepfake Shield is an enterprise-grade, real-time AI security platform engineered to detect synthetic speech, cloned voices, deepfake videos, and manipulated audiovisual streams.

```mermaid
flowchart TD
    subgraph ClientLayer ["Client Layer (React + TS + Tailwind)"]
        UI["Web Dashboard & Forensic Player"]
        LiveHUD["Real-Time Stream HUD"]
        Capture["WebRTC / AudioContext Streamer"]
    end

    subgraph GatewayLayer ["API Gateway & Ingestion Tier (FastAPI)"]
        Router["REST API Router (FastAPI)"]
        WSHandler["WebSocket Stream Manager"]
        Auth["JWT / API Key Guard"]
    end

    subgraph QueueLayer ["Async Queue & Ephemeral State (Redis)"]
        TaskQ["Celery / Redis Job Queue"]
        StreamPubSub["Pub/Sub Telemetry Broker"]
        RingBuffer["Stream Sliding Window Buffer"]
    end

    subgraph AIEngine ["AI Forensics Engine"]
        AudioM["Audio Detection Module (Librosa + AASIST/Wav2Vec2)"]
        VideoM["Video Detection Module (MediaPipe + EfficientNet)"]
        MultiM["Multimodal Sync & Risk Calibrator (SyncNet)"]
        StreamProc["Low-Latency Stream Processor"]
    end

    subgraph StorageLayer ["Persistence & Storage Tier"]
        PG[("PostgreSQL 16 (Relational Metadata & Audit)")]
        Blob[("Local Storage / S3 MinIO (Media Artifacts)")]
    end

    Capture -->|WebSockets (PCM + Frames)| WSHandler
    UI -->|REST Uploads (MP4/WAV)| Router
    Router --> Auth
    Auth --> Blob
    Router --> TaskQ
    WSHandler <--> RingBuffer
    RingBuffer --> StreamProc
    StreamProc --> StreamPubSub
    StreamPubSub --> WSHandler
    WSHandler --> LiveHUD

    TaskQ --> AudioM
    TaskQ --> VideoM
    TaskQ --> MultiM
    AudioM --> MultiM
    VideoM --> MultiM
    MultiM --> PG
    Router --> PG
```

---

## 2. Component Breakdown

### 2.1 Client Layer
- **Tech Stack**: React 18, TypeScript, Tailwind CSS, Lucide React, Chart.js / Recharts.
- **Key Modules**:
  - `ForensicViewer`: Frame-by-frame scrubbing, visual bounding box overlays, spectrogram visualization, and audio anomaly timeline.
  - `LiveCameraHUD`: WebRTC and WebSocket media streamer that captures live camera/microphone input and displays real-time threat meters.
  - `AuditLogViewer`: Forensic chain-of-custody exportable as PDF/JSON.

### 2.2 API Gateway & Ingestion Tier
- **Tech Stack**: Python 3.10/3.11, FastAPI, Uvicorn, Pydantic v2.
- **Responsibilities**:
  - Request validation, authentication, rate-limiting, and CORS management.
  - Chunked file upload streaming for large multi-gigabyte video files.
  - WebSocket connection pooling and connection heartbeat monitoring.

### 2.3 Message Broker & Cache Tier
- **Tech Stack**: Redis 7.
- **Responsibilities**:
  - Acts as an asynchronous task queue for deep batch forensics.
  - Maintains low-latency ephemeral ring buffers for live WebSocket streams.
  - Pub/Sub mechanism to broadcast detection alerts across distributed gateway instances.

### 2.4 AI Forensics Engine Tier
- **Tech Stack**: PyTorch, TorchAudio, Hugging Face Transformers, Librosa, OpenCV, MediaPipe, FFmpeg.
- **Execution Mode**:
  - **Fast-path (Stream Mode)**: Lightweight models (MobileNetV3, quantized ONNX spectral CNN, MediaPipe FaceMesh) running within a 150-250ms latency budget.
  - **Forensic-path (Batch Mode)**: Multi-stage deep ensembles (AASIST graph neural networks, Wav2Vec 2.0 embeddings, EfficientNet-B4 spatial artifact detectors, SyncNet lip-audio correlation).

### 2.5 Storage Tier
- **PostgreSQL 16**: Relational storage for users, detection records, job statuses, temporal anomaly sequences, and audit logs.
- **Media Object Store**: Storage for raw media files, extracted face chips, and spectrogram heatmaps.

---

## 3. Communication Patterns

| Flow | Protocol | Payload Format | Latency Target |
| :--- | :--- | :--- | :--- |
| Batch Upload | HTTPS POST (Multipart) | Binary Video / Audio | Dependent on network (Async polling) |
| Live Stream Audio | WebSocket Binary/JSON | 16kHz Float32 PCM (250ms chunks) | < 100ms |
| Live Stream Video | WebSocket Binary/JSON | Base64 JPEG/WebP keyframes (5-10 fps) | < 200ms |
| Telemetry Stream | WebSocket JSON | Instantaneous Risk & Bounding Boxes | < 250ms |
| Internal Tasks | Redis Streams / AMQP | Job IDs & S3 File URIs | < 10ms |
| Database Queries | Asyncpg / SQLAlchemy | SQL over TCP pool | < 5ms |

