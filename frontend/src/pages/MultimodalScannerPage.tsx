import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Layers,
  Video,
  Mic,
  Upload,
  AlertCircle,
  ArrowRight,
  Settings2,
  Cpu,
  CheckCircle2,
  Sparkles,
  Zap,
  Info,
  Clock,
  ShieldAlert,
  FileVideo,
  FileAudio,
} from 'lucide-react';
import { scansApi } from '../services/api';

type ScanMode = 'single_video' | 'dual_stream';

export const MultimodalScannerPage: React.FC = () => {
  const navigate = useNavigate();
  const videoInputRef = useRef<HTMLInputElement>(null);
  const audioInputRef = useRef<HTMLInputElement>(null);

  const [mode, setMode] = useState<ScanMode>('single_video');
  const [selectedVideo, setSelectedVideo] = useState<File | null>(null);
  const [selectedAudio, setSelectedAudio] = useState<File | null>(null);
  const [videoPreviewUrl, setVideoPreviewUrl] = useState<string | null>(null);
  const [audioPreviewUrl, setAudioPreviewUrl] = useState<string | null>(null);
  const [title, setTitle] = useState('');
  const [sampleFps, setSampleFps] = useState('3');
  const [enableSyncNet, setEnableSyncNet] = useState(true);
  const [asymmetryPenalty, setAsymmetryPenalty] = useState(true);

  // Scanning progress state machine
  const [isScanning, setIsScanning] = useState(false);
  const [scanStage, setScanStage] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);

  const stages = [
    { title: 'Cryptographic Ingestion', desc: 'Verifying file integrity and computing SHA-256 fingerprint' },
    { title: 'Stream Decomposition', desc: 'Decoding keyframes and extracting 16 kHz Float32 PCM audio' },
    { title: 'Neural Model Inference', desc: 'MediaPipe 468 mesh facial seams + Wav2Vec2 speech forensics' },
    { title: 'Audio-Visual SyncNet', desc: 'Lip aperture vs speech envelope cross-correlation & drift analysis' },
    { title: 'Bayesian Fusion & Audit Log', desc: 'Applying complementary authenticity fusion & signing dossier' },
  ];

  const handleVideoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedVideo(file);
      if (!title) {
        setTitle(file.name.replace(/\.[^/.]+$/, ''));
      }
      setVideoPreviewUrl(URL.createObjectURL(file));
      setError(null);
    }
  };

  const handleAudioChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedAudio(file);
      setAudioPreviewUrl(URL.createObjectURL(file));
      setError(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedVideo) {
      setError('Please select a video file for multimodal inspection.');
      return;
    }
    if (mode === 'dual_stream' && !selectedAudio) {
      setError('Please select an accompanying audio file for dual-stream conflict analysis.');
      return;
    }

    setIsScanning(true);
    setScanStage(0);
    setError(null);

    // Staged progress ticker
    const timer1 = setTimeout(() => setScanStage(1), 700);
    const timer2 = setTimeout(() => setScanStage(2), 1700);
    const timer3 = setTimeout(() => setScanStage(3), 2800);
    const timer4 = setTimeout(() => setScanStage(4), 4000);

    try {
      const formData = new FormData();
      formData.append('file', selectedVideo);
      formData.append('scan_type', 'multimodal');

      if (title.trim()) {
        formData.append('title', title.trim());
      }

      if (mode === 'dual_stream' && selectedAudio) {
        formData.append('audio_file', selectedAudio);
      }

      const scanResult = await scansApi.uploadAndScan(formData);
      navigate(`/scans/${scanResult.id}`);
    } catch (err: any) {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      clearTimeout(timer4);
      setError(err.message || 'Failed to complete multimodal deepfake scan.');
      setIsScanning(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center space-x-2 text-purple-400 text-xs font-semibold uppercase tracking-wider mb-1">
          <Layers className="w-4 h-4" />
          <span>Multimodal Audio-Visual Synchronization &amp; Risk Calibrator</span>
        </div>
        <h1 className="text-xl md:text-2xl font-bold text-gray-100">
          Multimodal Deepfake &amp; Dubbing Scanner
        </h1>
        <p className="text-xs text-gray-400 mt-1">
          Simultaneously inspect facial spatial boundaries, neural speech synthesis, and lip-sync temporal drift.
          Detect targeted voice dubbing over authentic footage and AI face swaps using complementary authenticity fusion.
        </p>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl bg-red-950/40 border border-red-800/50 flex items-start space-x-3 text-xs text-red-300">
          <AlertCircle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Mode Selection Tabs */}
      <div className="grid grid-cols-2 gap-3 p-1.5 bg-white border border-sky-200 rounded-xl shadow-sm">
        <button
          type="button"
          onClick={() => setMode('single_video')}
          disabled={isScanning}
          className={`py-3 px-4 rounded-lg text-xs font-semibold flex items-center justify-center space-x-2 transition ${mode === 'single_video'
            ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20'
            : 'text-slate-600 hover:text-slate-900 hover:bg-sky-50/70'
            }`}
        >
          <Video className="w-4 h-4" />
          <span>Single Video (Embedded Audio)</span>
        </button>
        <button
          type="button"
          onClick={() => setMode('dual_stream')}
          disabled={isScanning}
          className={`py-3 px-4 rounded-lg text-xs font-semibold flex items-center justify-center space-x-2 transition ${mode === 'dual_stream'
            ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20'
            : 'text-slate-600 hover:text-slate-900 hover:bg-sky-50/70'
            }`}
        >
          <div className="flex items-center space-x-1">
            <Video className="w-3.5 h-3.5" />
            <span>+</span>
            <Mic className="w-3.5 h-3.5" />
          </div>
          <span>Dual Stream (Video + Separate Audio)</span>
        </button>
      </div>

      {/* Main Upload Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Primary Video Upload Zone */}
          <div className="space-y-3">
            <label className="text-xs font-semibold text-gray-300 flex items-center space-x-1.5">
              <Video className="w-3.5 h-3.5 text-purple-400" />
              <span>Primary Video Recording *</span>
            </label>
            <input
              type="file"
              ref={videoInputRef}
              onChange={handleVideoChange}
              accept=".mp4,.avi,.mov,.mkv,.webm,.webp,.jpg,.jpeg,.png"
              disabled={isScanning}
              className="hidden"
            />
            <div
              onClick={() => videoInputRef.current?.click()}
              className={`p-6 border-2 border-dashed rounded-2xl text-center cursor-pointer transition flex flex-col items-center justify-center min-h-[200px] ${selectedVideo
                ? 'border-purple-500/50 bg-purple-950/10'
                : 'border-gray-700 hover:border-purple-500/50 hover:bg-gray-900/60 bg-[#111827]'
                }`}
            >
              {selectedVideo ? (
                <div className="space-y-2">
                  <div className="w-10 h-10 rounded-full bg-purple-500/20 text-purple-400 flex items-center justify-center mx-auto">
                    <FileVideo className="w-5 h-5" />
                  </div>
                  <p className="text-xs font-semibold text-gray-200 truncate max-w-xs">{selectedVideo.name}</p>
                  <p className="text-[10px] text-gray-400 font-mono">
                    {(selectedVideo.size / (1024 * 1024)).toFixed(2)} MB • Ready for Vision Decomposition
                  </p>
                  {videoPreviewUrl && (
                    selectedVideo && /\.(webp|jpg|jpeg|png)$/i.test(selectedVideo.name) ? (
                      <img
                        src={videoPreviewUrl}
                        alt="Preview"
                        className="w-full max-h-36 rounded-lg mt-2 bg-black object-contain"
                      />
                    ) : (
                      <video
                        src={videoPreviewUrl}
                        controls
                        className="w-full max-h-36 rounded-lg mt-2 bg-black object-contain"
                      />
                    )
                  )}
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="w-10 h-10 rounded-full bg-gray-800 text-gray-400 flex items-center justify-center mx-auto">
                    <Upload className="w-5 h-5" />
                  </div>
                  <p className="text-xs font-medium text-gray-300">Click or Drag Video/Image to Upload</p>
                  <p className="text-[10px] text-gray-500">MP4, WEBM, MOV, AVI, WEBP, JPG, PNG up to 100MB</p>
                </div>
              )}
            </div>
          </div>

          {/* Secondary Audio or Info Zone */}
          <div className="space-y-3">
            {mode === 'dual_stream' ? (
              <>
                <label className="text-xs font-semibold text-gray-300 flex items-center space-x-1.5">
                  <Mic className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Suspect Voice Track to Cross-Examine *</span>
                </label>
                <input
                  type="file"
                  ref={audioInputRef}
                  onChange={handleAudioChange}
                  accept=".wav,.mp3,.flac,.aac,.m4a,.ogg"
                  disabled={isScanning}
                  className="hidden"
                />
                <div
                  onClick={() => audioInputRef.current?.click()}
                  className={`p-6 border-2 border-dashed rounded-2xl text-center cursor-pointer transition flex flex-col items-center justify-center min-h-[200px] ${selectedAudio
                    ? 'border-cyan-500/50 bg-cyan-950/10'
                    : 'border-gray-700 hover:border-cyan-500/50 hover:bg-gray-900/60 bg-[#111827]'
                    }`}
                >
                  {selectedAudio ? (
                    <div className="space-y-2">
                      <div className="w-10 h-10 rounded-full bg-cyan-500/20 text-cyan-400 flex items-center justify-center mx-auto">
                        <FileAudio className="w-5 h-5" />
                      </div>
                      <p className="text-xs font-semibold text-gray-200 truncate max-w-xs">{selectedAudio.name}</p>
                      <p className="text-[10px] text-gray-400 font-mono">
                        {(selectedAudio.size / (1024 * 1024)).toFixed(2)} MB • Ready for Audio Pipeline
                      </p>
                      {audioPreviewUrl && (
                        <audio src={audioPreviewUrl} controls className="w-full mt-2 h-9" />
                      )}
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <div className="w-10 h-10 rounded-full bg-gray-800 text-gray-400 flex items-center justify-center mx-auto">
                        <Mic className="w-5 h-5" />
                      </div>
                      <p className="text-xs font-medium text-gray-300">Upload Suspect Audio Track</p>
                      <p className="text-[10px] text-gray-500">WAV, MP3, FLAC, M4A up to 100MB</p>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="p-5 rounded-2xl bg-[#111827] border border-gray-800 space-y-3.5 flex flex-col justify-center min-h-[200px]">
                <div className="flex items-center space-x-2 text-xs font-semibold text-gray-200">
                  <Info className="w-4 h-4 text-purple-400" />
                  <span>Single Video Mode Active</span>
                </div>
                <p className="text-[11px] text-gray-400 leading-relaxed">
                  The video container will be parsed by both the vision pipeline and audio preprocessor.
                  Lip movements in the visual frames will be correlated directly with the extracted acoustic speech track.
                </p>
                <div className="space-y-2 text-[10px] font-mono">
                  <div className="flex items-center justify-between text-gray-400 border-b border-gray-800 pb-1.5">
                    <span>Face Mesh Landmarker</span>
                    <span className="text-emerald-400">MediaPipe 3D</span>
                  </div>
                  <div className="flex items-center justify-between text-gray-400 border-b border-gray-800 pb-1.5">
                    <span>Speech RMS Envelope</span>
                    <span className="text-emerald-400">&plusmn;50ms Windows</span>
                  </div>
                  <div className="flex items-center justify-between text-gray-400">
                    <span>Lip Aperture Metric</span>
                    <span className="text-emerald-400">Sobel + Cavity Darkness</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Scan Details & Options */}
        <div className="p-5 rounded-2xl bg-[#111827] border border-gray-800 space-y-4">
          <div className="flex items-center space-x-2 text-xs font-semibold text-gray-300">
            <Settings2 className="w-4 h-4 text-purple-400" />
            <span>Forensic Parameters &amp; Scan Title</span>
          </div>

          <div>
            <label className="text-[11px] font-medium text-gray-400 block mb-1">
              Scan Title / Case Reference
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Executive Interview Dubbing Verification"
              disabled={isScanning}
              className="w-full bg-gray-900 border border-gray-700 rounded-xl px-3.5 py-2 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-purple-500"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
            <div>
              <label className="text-[11px] text-gray-400 block mb-1">Sampling Frequency</label>
              <select
                value={sampleFps}
                onChange={(e) => setSampleFps(e.target.value)}
                disabled={isScanning}
                className="w-full bg-gray-900 border border-gray-700 rounded-xl px-3 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-purple-500"
              >
                <option value="2">2.0 FPS (Fast Preview)</option>
                <option value="3">3.0 FPS (Standard Forensic)</option>
                <option value="5">5.0 FPS (High Resolution)</option>
              </select>
            </div>

            <div className="flex items-center space-x-2 sm:pt-5">
              <input
                type="checkbox"
                id="enableSync"
                checked={enableSyncNet}
                onChange={(e) => setEnableSyncNet(e.target.checked)}
                disabled={isScanning}
                className="rounded border-gray-700 text-purple-600 focus:ring-purple-500 bg-gray-900"
              />
              <label htmlFor="enableSync" className="text-xs text-gray-300 cursor-pointer">
                SyncNet Lip-Sync Cross-Corr
              </label>
            </div>

            <div className="flex items-center space-x-2 sm:pt-5">
              <input
                type="checkbox"
                id="asymPenalty"
                checked={asymmetryPenalty}
                onChange={(e) => setAsymmetryPenalty(e.target.checked)}
                disabled={isScanning}
                className="rounded border-gray-700 text-purple-600 focus:ring-purple-500 bg-gray-900"
              />
              <label htmlFor="asymPenalty" className="text-xs text-gray-300 cursor-pointer">
                Asymmetry Tension Penalty
              </label>
            </div>
          </div>
        </div>

        {/* Live Staged Progress State HUD */}
        {isScanning && (
          <div className="p-5 rounded-2xl bg-[#0F172A] border border-purple-500/30 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2 text-purple-400 text-xs font-semibold">
                <Clock className="w-4 h-4 animate-spin" />
                <span>Multimodal Deepfake Inspection in Progress...</span>
              </div>
              <span className="text-xs font-mono font-bold text-purple-300">
                {Math.round(((scanStage + 1) / stages.length) * 100)}%
              </span>
            </div>

            {/* Progress Bar */}
            <div className="w-full bg-gray-800 h-2 rounded-full overflow-hidden">
              <div
                className="bg-gradient-to-r from-purple-500 to-cyan-400 h-full transition-all duration-500"
                style={{ width: `${((scanStage + 1) / stages.length) * 100}%` }}
              />
            </div>

            {/* Step List */}
            <div className="grid grid-cols-1 sm:grid-cols-5 gap-2 pt-2">
              {stages.map((stg, idx) => (
                <div
                  key={idx}
                  className={`p-2.5 rounded-lg border text-left transition ${idx === scanStage
                    ? 'bg-purple-950/40 border-purple-500 text-purple-200'
                    : idx < scanStage
                      ? 'bg-emerald-950/20 border-emerald-500/30 text-emerald-300'
                      : 'bg-gray-900/50 border-gray-800 text-gray-500'
                    }`}
                >
                  <div className="flex items-center space-x-1 mb-1">
                    {idx < scanStage ? (
                      <CheckCircle2 className="w-3 h-3 text-emerald-400 flex-shrink-0" />
                    ) : idx === scanStage ? (
                      <div className="w-2 h-2 rounded-full bg-purple-400 animate-ping mr-1" />
                    ) : (
                      <span className="w-3 h-3 rounded-full border border-gray-600 inline-block text-[8px] text-center">
                        {idx + 1}
                      </span>
                    )}
                    <p className="text-[10px] font-bold truncate">{stg.title}</p>
                  </div>
                  <p className="text-[9px] line-clamp-2 leading-tight opacity-80">{stg.desc}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Submit Action */}
        <div className="flex items-center justify-end space-x-3">
          <button
            type="submit"
            disabled={isScanning || !selectedVideo}
            className="px-6 py-3 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold transition flex items-center space-x-2 shadow-lg shadow-purple-600/25 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span>{isScanning ? 'Executing Multimodal Inspection...' : 'Execute Multimodal Deepfake Scan'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  );
};

