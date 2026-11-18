# Deepfake Shield – AI Detection Modules Specification

## 1. Architectural Philosophy
Deepfake Shield is designed to use **real, empirical feature extraction and state-of-the-art neural architectures**. It strictly avoids heuristic randomizations or artificial mocked scores.

Each module exposes:
1. **Algorithmic Feature Extractor**: Deterministic signal-processing and geometric feature computations.
2. **Pretrained Neural Network Backbone**: Deep representations trained on forensic datasets (ASVspoof, DFDC, FaceForensics++, FakeAVCeleb).
3. **Calibrated Probability Estimator**: Temperature-scaled sigmoid or softmax outputs reflecting calibrated confidence intervals.

---

## 2. Audio Detection Module (`backend/app/ml/audio_detector.py`)

### 2.1 Objectives
- Identify AI-generated voices (Text-to-Speech: VITS, Bark, ElevenLabs, Tortoise).
- Detect Voice Cloning (neural voice conversion like OpenVoice, retrieval-based voice conversion RVC).
- Spot vocoder phase artifacts and unnatural high-frequency spectral cutoffs.

### 2.2 Feature Pipeline
1. **Linear Frequency Cepstral Coefficients (LFCC) & CQCC**:
   - Audio resampled to 16 kHz mono.
   - Filterbanks capture linear high frequencies where vocoders (HiFi-GAN, WaveGlow) exhibit periodic phase inconsistencies.
2. **Spectral Descriptors via Librosa**:
   - **Spectral Flatness**: Measures tone-likeness vs noise; synthetic speech frequently produces unnaturally uniform high-frequency bands.
   - **Spectral Centroid & Rolloff**: Identifies steep brick-wall lowpass filters characteristic of compressed neural audio decoders.
   - **Zero Crossing Rate (ZCR)**: Detects phase cancellation and unvoiced sound irregularities.
3. **Deep Representation**:
   - Wav2Vec 2.0 / HuBERT / AASIST (Audio Anti-Spoofing using Integrated Spectro-Temporal Graph Attention Networks) embeddings.

### 2.3 Mathematical Formulation
Given audio signal $x(t)$, short-time Fourier transform $X(f, t)$:
$$\text{Spectral Flatness}(t) = \frac{\exp\left(\frac{1}{N}\sum_{k=0}^{N-1}\ln |X(k, t)|^2\right)}{\frac{1}{N}\sum_{k=0}^{N-1}|X(k, t)|^2}$$
Voice cloning anomaly is calculated via Cosine Distance between enrollment speaker embedding $e_{ref}$ and query embedding $e_{query}$ extracted via ECAPA-TDNN:
$$d_{clone}(e_{ref}, e_{query}) = 1 - \frac{e_{ref} \cdot e_{query}}{\|e_{ref}\|_2 \|e_{query}\|_2}$$

---

## 3. Video Detection Module (`backend/app/ml/video_detector.py`)

### 3.1 Objectives
- Detect face-swapping (Roop, SimSwap, DeepFaceLab, FaceFusion).
- Detect face-reenactment (LivePortrait, Thin-Plate Spline, FOMM).
- Identify spatial blending artifacts, pixel boundary seams, and temporal eye-blink anomalies.

### 3.2 Feature Pipeline
1. **Face & Landmark Extraction**:
   - MediaPipe FaceMesh (468 3D facial landmarks) + OpenCV Haar/SSD cascade fallback.
   - Extract tight normalized face bounding boxes and affine-aligned face crops ($256 \times 256$).
2. **Spatial Anomaly Analysis**:
   - High-pass frequency filtering (FFT / Laplacian variance) to detect unnatural boundary smoothing along face margins.
   - Color distribution disparity between facial mask and surrounding neck/hair skin tones.
3. **Temporal Inconsistency & Eye Blinking (EAR)**:
   - Eye Aspect Ratio (EAR) tracked across frames:
     $$\text{EAR} = \frac{\|p_2 - p_6\| + \|p_3 - p_5\|}{2 \|p_1 - p_4\|}$$
   - Healthy human blinks occur 12-20 times per minute with a characteristic 100-300ms curve. Zero blinks over 10 seconds or asymmetric EAR curves flag automated synthesis.
4. **Deep Spatial Backbone**:
   - Pretrained EfficientNet-B4 / ConvNeXt trained on FaceForensics++ (c23/c40 compressed).

---

## 4. Multimodal Fusion Module (`backend/app/ml/multimodal_fusion.py`)

### 4.1 Objectives
- Detect audio-video mismatch (e.g. real video overlaid with cloned synthetic voice, or real audio driving a deepfake video avatar).
- Quantify viseme-phoneme synchronization (lip-sync alignment).

### 4.2 Feature Pipeline & SyncNet Principles
1. Visual stream: mouth region-of-interest (ROI) crops extracted at 25 fps.
2. Audio stream: MFCCs/Mel-spectrogram chunks synchronized to 0.2s windows.
3. Joint cross-attention embedding:
   - Compute the temporal offset $\Delta t$ maximizing cross-correlation between audio acoustics and lip aperture dynamics.
   - Offsets exceeding threshold $\tau_{sync} > 80\text{ms}$ indicate manipulation.

### 4.3 Calibrated Bayesian Composite Risk Scoring
The final risk score $R \in [0, 100]$ is computed using a weighted Bayesian ensemble:
$$R = 100 \times \left(1 - \prod_{m \in \{A, V, S\}} (1 - w_m \cdot P_m)\right)$$
Where:
- $P_A$: Audio synthetic probability
- $P_V$: Video spatial/temporal manipulation probability
- $P_S$: Cross-modal lip-sync discrepancy probability
- $w_m$: Empirical weight coefficients ($\sum w_m = 1.0$) calibrated against validation priors.

---

## 5. Real-Time Monitoring Module (`backend/app/ml/stream_processor.py`)

### 5.1 Objectives
- Sub-300ms round-trip latency for live Zoom, Teams, WebRTC, or camera/mic input.
- Memory-bounded circular ring buffers preventing memory leaks during indefinite streaming.

### 5.2 Stream Architecture
- **Audio Pipeline**:
  - Web Audio API streams 16kHz Float32 PCM chunks every 250ms (4000 samples).
  - Ring buffer maintains a sliding 2.0-second window.
  - Fast-path Librosa spectral flatness + quantized ONNX inference executed every 500ms.
- **Video Pipeline**:
  - HTML5 Canvas grabs keyframes at 5-10 fps (resolution 640x480).
  - MediaPipe Landmarker runs directly on the active keyframe.
  - Fast-path blink/head pose variance and lightweight MobileNetV3 face artifact classifier execute in < 45ms.
- **Real-Time Telemetry Aggregator**:
  - Emits telemetry message back through WebSocket to update client HUD dials and alert toasts.

