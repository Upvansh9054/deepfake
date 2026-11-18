# Deepfake Shield 🛡️
### Real-Time Deepfake and Voice Clone Detection Platform

Deepfake Shield is an enterprise-grade AI security platform engineered to detect manipulated audio, cloned synthetic voices, deepfake videos, and unsynchronized audiovisual streams in real-time (< 300ms latency) and via high-precision batch forensics.

---

## 📌 Table of Contents
1. [Core Capabilities](#core-capabilities)
2. [Technology Stack](#technology-stack)
3. [System Architecture](#system-architecture)
4. [Communication & Data Flow](#communication--data-flow)
5. [AI Detection Modules](#ai-detection-modules)
6. [Hardware & Environment Requirements](#hardware--environment-requirements)
7. [Installation & Setup](#installation--setup)
8. [API & WebSocket Specification](#api--websocket-specification)
9. [Project Directory Layout](#project-directory-layout)
10. [Implementation Roadmap](#implementation-roadmap)

---

## 🚀 Core Capabilities

- **Real-Time Stream Protection**: Live sub-300ms monitoring of camera and microphone feeds for Zoom/Teams meetings and video calls.
- **Audio Voice Clone & Synthetic Speech Detection**: Analyzes linear frequency cepstral coefficients (LFCC), spectral flatness, and neural vocoder (HiFi-GAN, WaveGlow) phase artifacts.
- **Video Facial Tamper Forensics**: Employs MediaPipe FaceMesh (468 landmarks), Eye Aspect Ratio (EAR) blink frequency modeling, and edge boundary gradient discontinuity detection.
- **Multimodal Audio-Visual Synchronization**: Evaluates lip-sync alignment and viseme-phoneme cross-correlation (SyncNet principles) to identify mismatched dubs or reenactments.
- **Calibrated Bayesian Composite Risk Scoring**: Transparent, explainable risk ratings (0–100%) backed by second-by-second anomaly timelines.

---

## 🛠️ Technology Stack

| Domain | Technology |
| :--- | :--- |
| **Frontend** | React 18, TypeScript, Tailwind CSS, Lucide React, Vite |
| **Backend & Ingestion** | Python, FastAPI, Uvicorn, Pydantic v2, WebSockets |
| **Deep Learning & Audio** | PyTorch, Hugging Face Transformers, Librosa, Torchaudio |
| **Vision & Video** | OpenCV, MediaPipe Face Landmarker, FFmpeg |
| **Database & Caching** | PostgreSQL 16 (Relational Metadata & Audit), Redis 7 (Pub/Sub & Queues) |
| **Containerization** | Docker, Docker Compose |

---

## 📐 System Architecture

```mermaid
flowchart TD
    subgraph Client ["Client Interface (React + TypeScript + Tailwind)"]
        UI["Web Dashboard & Forensic Player"]
        LiveHUD["Real-Time Threat HUD"]
        Capture["WebRTC / AudioContext Streamer"]
    end

    subgraph Gateway ["API Gateway (FastAPI)"]
        Router["REST Endpoints (/api/v1)"]
        WSHandler["WebSocket Stream Manager (/api/v1/stream)"]
    end

    subgraph Broker ["Message Broker & Ring Buffer (Redis)"]
        TaskQ["Celery / Redis Job Queue"]
        RingBuffer["Audio/Video Sliding Window Buffer"]
    end

    subgraph AI ["AI Forensics Engine"]
        AudioM["Audio Forensics (Librosa + AASIST/Wav2Vec2)"]
        VideoM["Video Forensics (MediaPipe + EfficientNet)"]
        MultiM["Multimodal Sync & Risk Calibrator (SyncNet)"]
        StreamProc["Sub-300ms Stream Processor"]
    end

    subgraph Storage ["Persistence Tier"]
        PG[("PostgreSQL 16")]
        MediaDisk[("Local Storage / S3 MinIO")]
    end

    Capture -->|WebSockets (16kHz PCM + Keyframes)| WSHandler
    UI -->|REST Uploads (MP4, WAV)| Router
    Router --> MediaDisk
    Router --> TaskQ
    WSHandler <--> RingBuffer
    RingBuffer --> StreamProc
    StreamProc --> WSHandler
    WSHandler --> LiveHUD

    TaskQ --> AudioM
    TaskQ --> VideoM
    AudioM --> MultiM
    VideoM --> MultiM
    MultiM --> PG
    Router --> PG
```

---

## 🔄 Communication & Data Flow

### 1. Real-Time Streaming Flow (Low Latency)
1. **Capture**: Client captures 16 kHz Float32 PCM audio chunks every 250ms via Web Audio API, and JPEG keyframes at 10 FPS via HTML5 Canvas.
2. **WebSocket Ingestion**: Sent over `ws://localhost:8000/api/v1/stream/live/{session_id}`.
3. **Ring Buffer**: Audio buffer maintains a rolling 2.0-second sliding window.
4. **Fast-Path Inference**: Real-time spectral flatness and facial edge boundary gradients are computed.
5. **Telemetry Push**: Evaluated threat score and bounding box coordinates pushed back to client in < 250ms.

### 2. Batch Forensic Analysis Flow (Deep Inspection)
1. **Upload**: User uploads media file via `POST /api/v1/multimodal/analyze`.
2. **Persistence**: File hash is verified (SHA-256) and stored in local object storage.
3. **Audio Demuxing**: FFmpeg demuxes audio track into 16 kHz WAV.
4. **Frame Extraction**: Sampled keyframes extracted for facial detection and landmark tracking.
5. **Inference Workers**: Audio, Video, and Lip-Sync engines compute forensic probabilities.
6. **Report Generation**: PostgreSQL stores comprehensive verdict, explainability summary, and second-by-second anomaly markers.

---

## 🧠 AI Detection Modules

1. **Audio Detection (`app/ml/audio_detector.py`)**:
   - Computes spectral flatness, spectral centroid, and zero-crossing rate (ZCR).
   - Identifies high-frequency energy cutoffs characteristic of neural vocoders.
   - Cosine similarity matching against enrolled speaker embeddings for voice clone verification.
2. **Video Detection (`app/ml/video_detector.py`)**:
   - MediaPipe 468 3D landmark mesh extraction.
   - Eye Aspect Ratio (EAR) temporal tracking to detect suppressed or unnatural blinking.
   - Boundary seam edge gradient disparity analysis.
3. **Multimodal Fusion (`app/ml/multimodal_fusion.py`)**:
   - Cross-correlates audio acoustic energy (RMS) with mouth aspect ratio (MAR) dynamics.
   - Bayesian multi-evidence ensemble score ($R \in [0, 100]$) with temperature calibration.
4. **Stream Processor (`app/ml/stream_processor.py`)**:
   - Circular ring buffer memory management preventing memory leaks during continuous streaming sessions.

---

## ⚠️ Hardware & Environment Requirements

> [!IMPORTANT]
> **Python Version Compatibility Note:**
> PyTorch, Torchaudio, Librosa (via Numba), and MediaPipe require prebuilt binary wheels that are officially validated for **Python 3.10** and **Python 3.11**.
> System environments running Python 3.14+ will encounter wheel build failures for Numba and MediaPipe. Always use a dedicated **Python 3.11 virtual environment** or Docker.

- **FFmpeg**: Required on host system or container for media transcoding and demuxing.
- **Node.js**: v18.0.0 or higher (v24.x tested).
- **GPU Acceleration (Optional)**: NVIDIA CUDA 11.8 / 12.1 supported with automatic CPU fallback.

---

## 📦 Installation & Setup

### Option A: Running via Docker Compose (Recommended)

1. Clone or navigate to the project directory:
   ```bash
   cd D:\DeepFake
   ```
2. Copy the environment variables:
   ```bash
   copy .env.example .env
   ```
3. Start the entire platform (PostgreSQL, Redis, Backend, Frontend):
   ```bash
   docker compose up --build
   ```
4. Access the applications:
   - Frontend Dashboard: `http://localhost:3000`
   - FastAPI Interactive Swagger Docs: `http://localhost:8000/api/v1/docs`

---

### Option B: Local Development Setup

#### 1. System Prerequisites
- Install FFmpeg:
  ```powershell
  winget install Gyan.FFmpeg
  ```
- Install Python 3.11 (if host default is 3.14):
  ```powershell
  winget install Python.Python.3.11
  ```

#### 2. Backend Setup
```powershell
cd D:\DeepFake\backend

# Create virtual environment using Python 3.11
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1

# Install core and ML dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-ml.txt

# Run FastAPI backend server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 3. Frontend Setup
From the root directory:
```powershell
# Run directly from D:\DeepFake
npm run dev

# Or build for production
npm run build
```

Or navigate into the `frontend` folder:
```powershell
cd D:\DeepFake\frontend

# Install node dependencies
npm install

# Start Vite development server
npm run dev

# Build for production
npm run build
```

---

## 📁 Project Directory Layout

```
D:\DeepFake/
├── README.md                          # Platform documentation
├── docker-compose.yml                 # PostgreSQL, Redis, Backend, Frontend orchestrator
├── .gitignore                         # Git exclusion rules
├── .env.example                       # Environment configuration template
├── docs/                              # Formal architectural documentation
│   ├── ARCHITECTURE.md                # System topology and component design
│   ├── API_SPECIFICATION.md           # REST & WebSocket endpoint contracts
│   ├── DATABASE_SCHEMA.sql            # PostgreSQL DDL schema & indexes
│   └── MODULES_SPECIFICATION.md       # AI mathematical formulations and pipelines
├── backend/                           # FastAPI Application & AI Engines
│   ├── Dockerfile
│   ├── requirements.txt               # API Gateway dependencies
│   ├── requirements-ml.txt            # ML/Inference dependencies
│   └── app/
│       ├── main.py                    # Application entrypoint & middleware
│       ├── core/                      # Config, DB connection, security
│       ├── models/                    # SQLAlchemy ORM models
│       ├── schemas/                   # Pydantic v2 schemas
│       ├── api/v1/                    # REST routes & WebSocket handler
│       └── ml/                        # AI Detection Engine
│           ├── audio_detector.py      # Audio spectral & voice clone analysis
│           ├── video_detector.py      # Facial landmark & edge seam forensics
│           ├── multimodal_fusion.py   # Lip-sync sync & Bayesian risk calibrator
│           └── stream_processor.py    # Sub-300ms ring buffer streaming worker
└── frontend/                          # React + TypeScript + Tailwind CSS
    ├── Dockerfile
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.js
    └── src/
        ├── App.tsx                    # Main security HUD & dashboard
        ├── main.tsx
        ├── index.css
        └── types/                     # TypeScript schema declarations
```

---

## 🗺️ Implementation Roadmap

- [x] **Phase 1: Architecture & Development Scaffolding**
  - Project structure inspection and dependency audit.
  - Complete technical architecture, communication protocols, and data flow design.
  - PostgreSQL schema and OpenAPI specifications.
  - AI Detection Module interfaces with empirical feature extractors.
  - Verified development environment scaffolding.
- [x] **Phase 2: Full-Stack Security Application & Forensic Storage**
  - Modern cybersecurity SaaS dashboard with responsive sidebar and top navigation.
  - Authentication & Authorization system (JWT + bcrypt password encryption).
  - Relational Database ORM supporting PostgreSQL 16 & SQLite (`users`, `scans`, `scan_results`, `risk_reports`, `alerts`, `audit_logs`).
  - Audio Deepfake Scanner page with drag-and-drop ingestion & audio preview.
  - Video Deepfake Scanner page with drag-and-drop ingestion & video preview.
  - Forensic Detection Results page with SHA-256 cryptographic hash verification & risk meter.
  - Scan History Registry with search, multi-modality filtering, and CSV export.
  - Real-Time Live Camera & Mic Monitoring HUD foundation.
  - System Settings console for profile, API keys, and sensitivity thresholds.
  - Automated integration test suite (`python -m pytest backend/tests/test_phase2_endpoints.py`).
- [x] **Phase 3: Hugging Face Dataset API Integration**
  - Connected to `UniDataPro/deepfake-videos-dataset` via Hugging Face Datasets Server API.
  - Endpoints integrated: `/splits`, `/rows` (paginated), and `/parquet`.
  - In-memory TTL caching (300s) + PostgreSQL metadata persistence (`dataset_metadata` table).
  - Ground-truth label inspection (Class 0: `deepfake`, Class 1: `video`).
  - Interactive Dataset Explorer UI page (`/datasets`) with preview video modal and filter controls.
  - Live API connection status and latency widget on Overview Dashboard.
  - Comprehensive automated test suite (`python -m pytest backend/tests/test_huggingface_service.py`).
- [x] **Phase 4: AI Voice Deepfake & Pretrained Audio Detection**
  - Evaluated AASIST, RawNet2, AST (`MattyB95/AST-ASVspoof2019-Synthetic-Voice-Detection`), and Wav2Vec 2.0 (`mo-thecreator/Deepfake-audio-detection`).
  - Implemented robust `AudioPreprocessor` with RIFF/WAV validation, linear PCM conversion (16,000 Hz mono), silence detection (-50 dBFS RMS gate), sub-second duration rejection (<0.5s), and 30.0s high-res windowing.
  - Implemented `AudioDeepfakeDetector` connecting to Hugging Face Serverless Router (`mo-thecreator/Deepfake-audio-detection`) and deterministic ASVspoof spectral signal extraction (SFM, vocoder cutoffs, ZCR, RMS variance).
  - Mathematical decoupling of Model Confidence ($C \in [0.0, 1.0]$) from Calibrated Fraud Risk ($R \in [0, 100]\%$).
  - Explainable classification taxonomy: `genuine`, `suspicious`, `synthetic`, `uncertain`.
  - Forensic persistence in PostgreSQL/SQLite `scans`, `scan_results`, and `risk_reports` tables.
  - Enhanced Frontend Audio Scanner & Detection Results pages with dual gauges, acoustic warnings, signal metric breakdown, and transparent model limitation disclosures.
  - Comprehensive documentation in `docs/AUDIO_DEEPFAKE_MODEL_EVALUATION.md`.
  - Automated test suite (`python -m pytest backend/tests/test_audio_deepfake_detector.py`).
- [x] **Phase 5: AI Video Deepfake Detection & Multi-Frame Facial Forensics**
  - Evaluated Xception (FaceForensics++ benchmark), EfficientNet-B4/B7 (DFDC winning architectures), and Vision Transformer (ViT) face classifiers (`dima806/deepfake_vs_real_image_detection`, `prithivMLmods/Deep-Fake-Detector-v2-Model`).
  - Implemented `VideoPreprocessor` using OpenCV for uniform temporal keyframe extraction (2–10 FPS), container validation, and illumination-invariant face localization in YCrCb color space with 15% padding margin.
  - Implemented `VideoDeepfakeDetector` integrating pretrained Hugging Face Router inference with empirical visual forensics: spatial boundary seam disparity, 2D FFT spectral high-frequency residuals, YCrCb color divergence, and temporal landmark stability.
  - Enforced multi-frame aggregation: videos are never classified based on one frame alone; robust trimmed mean and peak frame analysis are combined.
  - Transparent handling of videos without faces: `faces_detected = 0`, `classification = "uncertain"`, `verdict = "inconclusive"`.
  - Timestamp and interval grouping for suspicious video segments.
  - Updated FastAPI endpoint `POST /api/v1/video/analyze` and asynchronous forensics pipeline.
  - Enhanced frontend Video Scanner and Detection Results pages with suspicious interval cards, timestamp pills, 6-metric video breakdown, and no-face warning banners.
  - Comprehensive documentation in `docs/VIDEO_DEEPFAKE_MODEL_EVALUATION.md`.
  - Automated test suite (`python -m pytest backend/tests/test_video_deepfake_detector.py`).
- [x] **Phase 6: Multimodal Risk Assessment & Audio-Visual Lip-Sync Synchronization**
  - Implemented `MultimodalAnalysisService` using transparent Bayesian Maximum Margin evidence fusion with cross-modal conflict penalties (strictly avoiding naive arithmetic averaging).
  - Audio-Visual Lip-Sync Synchronization engine (SyncNet principles): cross-correlates mouth opening aperture envelope ($\text{MOR}$) with speech acoustic energy envelope ($\text{RMS}$), calculating temporal drift in milliseconds and identifying speech-lip conflict intervals.
  - Standardized Risk Categories: `Low Risk` ($R < 35\%$), `Medium Risk` ($35\% \le R < 65\%$), `High Risk` ($R \ge 65\%$), and `Inconclusive`.
  - Transparent Signal Contribution Attribution (% Audio Voice Synthesis, % Video Facial Seams, % Lip-Sync Drift, % Cross-Modal Tension).
  - Explicit handling of missing modalities: `audio_missing`, `video_missing`, `insufficient_evidence` with epistemic confidence bounding penalties (never assuming missing media is genuine).
  - Forensic Governance Notice: explicit policy enforcing that model scores represent probabilistic indicators and must never be used to label a person a scammer without secondary out-of-band verification.
  - Endpoints created: `POST /api/v1/multimodal/analyze` and `POST /api/v1/multimodal/fuse`.
  - Frontend Detection Results page updated with Risk Category badges, Signal Attribution progress bars, Lip-Sync Metrics card, and Missing Modality notice banners.
  - Comprehensive documentation in `docs/MULTIMODAL_RISK_ASSESSMENT.md`.
  - Automated test suite (`python -m pytest backend/tests/test_multimodal_service.py`).
- [x] **Phase 7: Complete System Integration**
  - Unified ingestion pipeline supporting single-stream audio/video and dual-stream cross-modal input.
  - Dedicated Multimodal Deepfake Scanner UI (`/multimodal-scanner`) with single and dual-stream inspection modes.
  - Interactive multi-stage scanning state machines with live progress HUD across Audio, Video, and Multimodal scanners.
  - Complete Scan History Registry with `multimodal` filtering, SHA-256 search, and CSV export.
  - Cryptographic Forensic Certificate API endpoint (`GET /api/v1/scans/{scan_id}/certificate`) and downloadable JSON dossier.
  - Print-optimized `@media print` styling for downloadable/printable NIST/ISO-compliant Forensic Dossiers.
  - Overview Dashboard integration: live Hugging Face latency & split counts, multi-modality ingest counters, and threat monitoring.
  - Upstream resilience: offline benchmark caching prevents UI failures during external Hugging Face server timeouts.
  - Comprehensive documentation in `docs/SYSTEM_INTEGRATION.md`.
  - Automated integration test suite (`python -m pytest backend/tests/test_phase7_integration.py`).
- [x] **Phase 8: Real-Time Deepfake Monitoring & Browser WebRTC Calling Platform**
  - Dedicated browser-based WebRTC calling platform with peer-to-peer audio/video calling (`RTCPeerConnection` + `RoomSignalingManager`).
  - Strict privacy & ethical safeguards: Interactive pre-call Consent Modal requiring user agreement prior to media track capture and analysis.
  - Sub-300ms Fast-Path Stream Processor (`backend/app/ml/stream_processor.py`):
    - Circular 16kHz Float32 PCM audio ring buffer with spectral flux & pitch stability tracking.
    - Uniform 4 FPS keyframe extraction with fast YCrCb skin-color face localization and normalized bounding boxes.
    - 2D FFT spectral residual analysis on face crops to detect high-frequency diffusion & GAN artifacts.
    - Facial boundary seam disparity and oral cavity aperture tracking.
    - Real-time audio-visual lip-sync cross-correlation tracking phoneme-viseme temporal drift.
  - Measured latency verification: Millisecond-precision execution profiling via `time.perf_counter()`, asserting sub-300ms real-time SLA (averaging 15–40ms in practice).
  - Unified WebSocket Signaling and Telemetry route (`WS /api/v1/stream/call/{room_id}`) supporting room joins, SDP offer/answer exchanges, trickle ICE candidates, and real-time inference streaming.
  - Dynamic Threat HUD with alert tiers: Protected (<35% risk, emerald), Warning (35–64%, amber), Critical Alert (>=65%, pulsing red).
  - Real-time SVG/HTML5 canvas facial bounding box overlay rendering threat bounding boxes directly on remote video frames.
  - In-call controls: mic mute, camera toggle, screen sharing (`getDisplayMedia`), AI Deepfake Shield on/off toggle, and room invite URL sharing.
  - Comprehensive documentation in `docs/REALTIME_DEEPFAKE_MONITORING.md`.
  - Automated test suite (`python -m pytest backend/tests/test_stream_monitoring.py`).
- [x] **Phase 9: Security, Testing and Optimisation**
  - **Authentication & RBAC**: Rigorous JWT validation, bcrypt password encryption, and Role-Based Access Control (`require_roles`: `admin`, `analyst`, `auditor`) with deactivated account guards (`is_active=False`).
  - **Upload Security & Magic Bytes Defense**: Content-based magic bytes inspection blocking executable headers (Windows PE `MZ`, Linux ELF, Mach-O, shell scripts `#!`), enforcing genuine media containers (WAV, MP3, FLAC, OGG, MP4, WebM, AVI), sanitizing filenames against path traversal attacks, and enforcing 0-byte and 250MB size limits.
  - **Sliding-Window Rate Limiting**: In-memory rate limiting with `Retry-After` headers on `/auth/login` (10 req/min), neural inference (`/upload`, `/audio/analyze`, `/video/analyze`, `/multimodal/analyze`: 30 req/min), and general endpoints (120 req/min).
  - **Secure Storage & Data Retention Lifecycle**: Authenticated media streaming via `GET /api/v1/scans/{scan_id}/media` enforcing tenant ownership, retention status reporting (`GET /api/v1/retention/status`), and admin-only compliance purge (`POST /api/v1/retention/purge`).
  - **Empirical Model Benchmark & Evaluation**: Ground-truth evaluation harness (`backend/app/services/evaluator.py` & `GET /api/v1/analytics/evaluation-metrics`) computing Precision, Recall, Specificity, F1-Score, False Positive Rate (FPR), False Negative Rate (FNR), and latency distributions.
  - **Edge Case & Failure Resilience**: Robust handling of silent audio (< -50 dBFS), sub-second audio (< 0.5s), corrupted media headers, videos lacking detectable faces (`verdict="inconclusive"`), and upstream API timeout fallback.
  - **CPU/GPU Optimizations & Defense-in-Depth**: HTTP security headers middleware (HSTS, nosniff, DENY, CSP), explicit OpenCV handle cleanup in `finally` blocks, and downsampled 2D FFT spectral analysis.
  - **Comprehensive Test Coverage**: All 23 backend tests passed (`23 passed in 17.27s`), verifying auth, RBAC, magic bytes rejection, rate limiting, media isolation, retention purges, evaluation metrics, and failure recovery.
  - **Frontend UI Expansion**: Settings page updated with Data Retention Lifecycle controls, administrative purge actions, and interactive Empirical Forensic Benchmark runner.
  - Comprehensive documentation in `docs/SECURITY_TESTING_AND_OPTIMISATION.md`.

