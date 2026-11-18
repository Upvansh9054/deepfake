import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Video, Upload, FileVideo, AlertCircle, ArrowRight, Settings2, Eye, Cpu, Info, CheckCircle2, Clock, Layers, Link2, Globe } from 'lucide-react';
import { scansApi } from '../services/api';

export const VideoScannerPage: React.FC = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [inputMode, setInputMode] = useState<'file' | 'url'>('file');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [videoUrl, setVideoUrl] = useState('');
  const [videoPreviewUrl, setVideoPreviewUrl] = useState<string | null>(null);
  const [title, setTitle] = useState('');
  const [sampleFps, setSampleFps] = useState('3');
  const [checkBlink, setCheckBlink] = useState(true);
  const [checkBoundarySeam, setCheckBoundarySeam] = useState(true);
  const [enableMultimodal, setEnableMultimodal] = useState(true);

  const [isUploading, setIsUploading] = useState(false);
  const [scanStage, setScanStage] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const stages = [
    { title: 'Cryptographic Ingestion', desc: inputMode === 'url' ? 'Fetching media stream from URL and computing SHA-256 fingerprint' : 'Verifying file integrity and computing SHA-256 fingerprint' },
    { title: 'Keyframe Sampling', desc: `Extracting video keyframes at ${sampleFps} FPS with 15% face boundary padding` },
    { title: 'Facial Landmark Forensics', desc: 'MediaPipe 468 mesh landmark jitter, EAR blink dynamics, seam disparity' },
    { title: 'Spectral Residual Analysis', desc: 'Computing 2D FFT spectral residuals and frequency grid artifacts' },
    { title: 'Risk Calibration & Audit', desc: 'Aggregating multi-frame verdicts into calibrated fraud report' },
  ];

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setTitle(file.name.replace(/\.[^/.]+$/, ''));
      setVideoPreviewUrl(URL.createObjectURL(file));
      setError(null);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setSelectedFile(file);
      setTitle(file.name.replace(/\.[^/.]+$/, ''));
      setVideoPreviewUrl(URL.createObjectURL(file));
      setError(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (inputMode === 'file' && !selectedFile) {
      setError('Please select or drop a video file to scan.');
      return;
    }
    if (inputMode === 'url' && !videoUrl.trim()) {
      setError('Please paste a YouTube, Instagram, or video link to scan.');
      return;
    }

    setIsUploading(true);
    setScanStage(0);
    setError(null);

    const timer1 = setTimeout(() => setScanStage(1), inputMode === 'url' ? 1800 : 800);
    const timer2 = setTimeout(() => setScanStage(2), inputMode === 'url' ? 3400 : 1800);
    const timer3 = setTimeout(() => setScanStage(3), inputMode === 'url' ? 5000 : 3000);
    const timer4 = setTimeout(() => setScanStage(4), inputMode === 'url' ? 6600 : 4200);

    try {
      let scanResult;
      if (inputMode === 'url') {
        scanResult = await scansApi.scanFromUrl({
          url: videoUrl.trim(),
          title: title.trim() || undefined,
          scan_type: enableMultimodal ? 'multimodal' : 'video'
        });
      } else {
        const formData = new FormData();
        formData.append('file', selectedFile!);
        if (title.trim()) {
          formData.append('title', title.trim());
        }
        if (enableMultimodal) {
          formData.append('scan_type', 'multimodal');
        }
        scanResult = await scansApi.uploadAndScan(formData);
      }
      navigate(`/scans/${scanResult.id}`);
    } catch (err: any) {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      clearTimeout(timer4);
      setError(err.message || 'Failed to process video scan.');
      setIsUploading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center space-x-2 text-indigo-400 text-xs font-semibold uppercase tracking-wider mb-1">
          <Video className="w-4 h-4" />
          <span>Visual &amp; Facial Forensics • Pretrained AI Vision Pipeline</span>
        </div>
        <h1 className="text-xl md:text-2xl font-bold text-gray-100">
          Video Deepfake &amp; Face-Swap Scanner
        </h1>
        <p className="text-xs text-gray-400 mt-1">
          Perform multi-frame facial manipulation detection, spatial boundary seam inspection, and 2D FFT spectral residual analysis across sampled video intervals.
        </p>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl bg-red-950/40 border border-red-800/50 flex items-start space-x-3 text-xs text-red-300">
          <AlertCircle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Form Section */}
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Source Mode Switcher Tabs */}
        <div className="flex flex-wrap items-center gap-2.5 pb-2">
          <button
            type="button"
            onClick={() => { setInputMode('file'); setError(null); }}
            className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl text-xs font-semibold transition-all ${
              inputMode === 'file'
                ? 'bg-blue-600 text-white shadow-md shadow-blue-500/25 border border-blue-500'
                : 'bg-white text-slate-600 hover:text-slate-900 hover:bg-sky-50/80 border border-sky-200/80 shadow-sm'
            }`}
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Upload Visual or Video File</span>
          </button>

          <button
            type="button"
            onClick={() => { setInputMode('url'); setError(null); }}
            className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl text-xs font-semibold transition-all ${
              inputMode === 'url'
                ? 'bg-gradient-to-r from-sky-600 via-blue-600 to-indigo-600 text-white shadow-md shadow-blue-500/30 border border-sky-500'
                : 'bg-white text-slate-600 hover:text-slate-900 hover:bg-sky-50/80 border border-sky-200/80 shadow-sm'
            }`}
          >
            <Link2 className="w-3.5 h-3.5" />
            <span>Paste Video Link (YouTube / Instagram)</span>
            <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ml-1 ${
              inputMode === 'url' ? 'bg-white/20 text-white' : 'bg-sky-100 text-sky-700'
            }`}>
              YouTube &amp; Instagram
            </span>
          </button>
        </div>

        {/* Input Mode: Video Link Ingestion Card */}
        {inputMode === 'url' ? (
          <div className="p-6 rounded-2xl bg-white border border-sky-200/90 space-y-4 shadow-sm shadow-sky-100">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-xl bg-sky-50 border border-sky-200 flex items-center justify-center text-sky-600 shadow-sm">
                  <Globe className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
                    <span>Web Video Ingestion</span>
                    <span className="text-[10px] px-2.5 py-0.5 rounded-md bg-sky-100 text-sky-800 border border-sky-200 font-medium">
                      Stream Forensic Extractor
                    </span>
                  </h3>
                  <p className="text-[11px] text-slate-500">
                    Paste public links from YouTube, Instagram Reels, TikTok, or direct video streams
                  </p>
                </div>
              </div>

              {/* Supported Platform Badges */}
              <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
                <span className="px-2.5 py-1 rounded-md bg-rose-50 border border-rose-200 text-rose-700 font-semibold">
                  YouTube &amp; Shorts
                </span>
                <span className="px-2.5 py-1 rounded-md bg-fuchsia-50 border border-fuchsia-200 text-fuchsia-700 font-semibold">
                  Instagram Reels
                </span>
                <span className="px-2.5 py-1 rounded-md bg-sky-50 border border-sky-200 text-sky-700 font-semibold">
                  TikTok / Web MP4
                </span>
              </div>
            </div>

            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Link2 className="w-4 h-4 text-sky-600" />
              </div>
              <input
                type="url"
                value={videoUrl}
                onChange={(e) => {
                  setVideoUrl(e.target.value);
                  setError(null);
                  if (e.target.value && !title) {
                    try {
                      const u = new URL(e.target.value);
                      if (u.hostname.includes('youtube') || u.hostname.includes('youtu.be')) {
                        setTitle('YouTube Video Forensic Scan');
                      } else if (u.hostname.includes('instagram')) {
                        setTitle('Instagram Reel Forensic Scan');
                      } else if (u.hostname.includes('tiktok')) {
                        setTitle('TikTok Video Forensic Scan');
                      }
                    } catch { }
                  }
                }}
                placeholder="Paste video link: https://www.youtube.com/watch?v=... or https://www.instagram.com/reel/..."
                className="w-full bg-slate-50 border border-sky-200 focus:bg-white focus:border-sky-500 focus:ring-4 focus:ring-sky-100 rounded-xl pl-10 pr-16 py-3.5 text-xs text-slate-800 placeholder-slate-400 font-mono transition shadow-inner"
              />
              {videoUrl && (
                <button
                  type="button"
                  onClick={() => setVideoUrl('')}
                  className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-700 text-xs font-semibold"
                >
                  Clear
                </button>
              )}
            </div>

            {/* Source indicator pill */}
            {videoUrl && (
              <div className="flex items-center space-x-2 text-[11px] bg-sky-50/70 border border-sky-200/70 rounded-lg px-3 py-2">
                <span className="text-slate-500 font-mono">Recognized Source:</span>
                {videoUrl.includes('youtube.com') || videoUrl.includes('youtu.be') ? (
                  <span className="text-rose-600 font-bold flex items-center space-x-1">
                    <span>YouTube Video / Short</span>
                  </span>
                ) : videoUrl.includes('instagram.com') ? (
                  <span className="text-fuchsia-600 font-bold flex items-center space-x-1">
                    <span>Instagram Reel / Post Clip</span>
                  </span>
                ) : videoUrl.includes('tiktok.com') ? (
                  <span className="text-sky-600 font-bold flex items-center space-x-1">
                    <span>TikTok Video</span>
                  </span>
                ) : (
                  <span className="text-blue-600 font-bold flex items-center space-x-1">
                    <span>Direct Web Video Source</span>
                  </span>
                )}
              </div>
            )}
          </div>
        ) : (
          /* File Dropzone */
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition ${selectedFile
              ? 'border-blue-400 bg-sky-50/70 shadow-sm'
              : 'border-sky-200 hover:border-blue-500 bg-white hover:bg-sky-50/40 shadow-sm'
              }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".mp4,.avi,.mov,.mkv,.webm,.webp,.jpg,.jpeg,.png"
              onChange={handleFileChange}
              className="hidden"
            />

            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-sky-50 border border-sky-200 flex items-center justify-center text-sky-600 shadow-sm">
              {selectedFile ? <FileVideo className="w-8 h-8" /> : <Upload className="w-8 h-8" />}
            </div>

            {selectedFile ? (
              <div>
                <p className="text-sm font-semibold text-slate-800 mb-1">{selectedFile.name}</p>
                <p className="text-xs text-slate-500 font-mono">
                  {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • Click or drag to replace
                </p>
              </div>
            ) : (
              <div>
                <p className="text-sm font-semibold text-slate-700 mb-1">
                  Drop visual or video file here, or browse files
                </p>
                <p className="text-xs text-slate-400 font-mono mb-2">
                  Supports MP4, AVI, MOV, MKV, WEBM, WEBP, JPG, PNG up to 250 MB
                </p>
                <span
                  onClick={(e) => { e.stopPropagation(); setInputMode('url'); }}
                  className="text-xs text-sky-600 hover:text-sky-700 underline font-medium cursor-pointer"
                >
                  Or paste a YouTube / Instagram video link &rarr;
                </span>
              </div>
            )}
          </div>
        )}

        {/* Video / Visual Stream Preview */}
        {inputMode === 'file' && videoPreviewUrl && (
          <div className="p-4 rounded-xl bg-white border border-sky-200 shadow-sm space-y-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Visual Stream Preview
            </span>
            <div className="relative aspect-video max-h-96 mx-auto bg-black rounded-lg overflow-hidden flex items-center justify-center">
              {selectedFile && /\.(webp|jpg|jpeg|png)$/i.test(selectedFile.name) ? (
                <img src={videoPreviewUrl} alt="Visual Stream Preview" className="w-full h-full object-contain" />
              ) : (
                <video controls src={videoPreviewUrl} className="w-full h-full object-contain" />
              )}
            </div>
          </div>
        )}

        {/* Options & Metadata */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-5 rounded-xl bg-white border border-sky-200 space-y-3 shadow-sm">
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700">
              Scan Title / Case Reference
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., Video Conference Candidate Verification"
              className="w-full bg-slate-50 border border-sky-200 rounded-xl px-3.5 py-2.5 text-xs text-slate-800 placeholder-slate-400 focus:bg-white focus:outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100 transition"
            />
            <div className="pt-2">
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                Forensic Frame Sampling Rate
              </label>
              <select
                value={sampleFps}
                onChange={(e) => setSampleFps(e.target.value)}
                className="w-full bg-slate-50 border border-sky-200 rounded-xl px-3 py-2 text-xs text-slate-800 focus:bg-white focus:outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100 transition"
              >
                <option value="3">3 FPS (Standard Forensic Depth)</option>
                <option value="5">5 FPS (High Precision)</option>
                <option value="10">10 FPS (Micro-expression Detail)</option>
              </select>
            </div>
          </div>

          <div className="p-5 rounded-xl bg-white border border-sky-200 space-y-3 shadow-sm">
            <div className="flex items-center space-x-2 text-xs font-semibold uppercase tracking-wider text-slate-700">
              <Settings2 className="w-4 h-4 text-sky-600" />
              <span>Vision Forensic Parameters</span>
            </div>
            <div className="space-y-2 text-xs">
              <label className="flex items-center space-x-2 text-slate-600 cursor-pointer">
                <input
                  type="checkbox"
                  checked={checkBoundarySeam}
                  onChange={(e) => setCheckBoundarySeam(e.target.checked)}
                  className="rounded bg-slate-50 border-sky-300 text-sky-600 focus:ring-0"
                />
                <span>Spatial Facial Boundary Seam Gradient Inspection</span>
              </label>
              <label className="flex items-center space-x-2 text-slate-600 cursor-pointer">
                <input
                  type="checkbox"
                  checked={checkBlink}
                  onChange={(e) => setCheckBlink(e.target.checked)}
                  className="rounded bg-slate-50 border-sky-300 text-sky-600 focus:ring-0"
                />
                <span>Eye Aspect Ratio (EAR) Blink Suppression Analysis</span>
              </label>
              <label className="flex items-center space-x-2 text-sky-900 cursor-pointer">
                <input
                  type="checkbox"
                  checked={enableMultimodal}
                  onChange={(e) => setEnableMultimodal(e.target.checked)}
                  className="rounded bg-slate-50 border-sky-300 text-sky-600 focus:ring-0"
                />
                <span className="font-semibold flex items-center space-x-1">
                  <Layers className="w-3.5 h-3.5 text-sky-600 inline" />
                  <span>Enable Multimodal Audio-Visual Lip-Sync &amp; Speech Inspection</span>
                </span>
              </label>
              <label className="flex items-center space-x-2 text-slate-400 cursor-pointer">
                <input
                  type="checkbox"
                  defaultChecked
                  disabled
                  className="rounded bg-slate-50 border-sky-200 text-sky-400 focus:ring-0"
                />
                <span className="text-slate-400">MediaPipe 468 3D Facial Landmark Tracking (Always On)</span>
              </label>
            </div>
          </div>
        </div>

        {/* Live Staged Progress State HUD */}
        {isUploading && (
          <div className="p-5 rounded-2xl bg-white border border-sky-200 space-y-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2 text-sky-700 text-xs font-semibold">
                <Clock className="w-4 h-4 animate-spin text-sky-600" />
                <span>Forensic Video Inspection in Progress...</span>
              </div>
              <span className="text-xs font-mono font-bold text-sky-800">
                {Math.round(((scanStage + 1) / stages.length) * 100)}%
              </span>
            </div>

            {/* Progress Bar */}
            <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden border border-sky-100">
              <div
                className="bg-gradient-to-r from-sky-500 via-blue-600 to-indigo-600 h-full transition-all duration-500 rounded-full"
                style={{ width: `${((scanStage + 1) / stages.length) * 100}%` }}
              />
            </div>

            {/* Step List */}
            <div className="grid grid-cols-1 sm:grid-cols-5 gap-2 pt-2">
              {stages.map((stg, idx) => (
                <div
                  key={idx}
                  className={`p-2.5 rounded-lg border text-left transition ${idx === scanStage
                    ? 'bg-sky-50 border-sky-400 text-sky-900 shadow-sm'
                    : idx < scanStage
                      ? 'bg-emerald-50 border-emerald-300 text-emerald-800'
                      : 'bg-slate-50 border-slate-200 text-slate-400'
                    }`}
                >
                  <div className="flex items-center space-x-1 mb-1">
                    {idx < scanStage ? (
                      <CheckCircle2 className="w-3 h-3 text-emerald-600 flex-shrink-0" />
                    ) : idx === scanStage ? (
                      <div className="w-2 h-2 rounded-full bg-sky-500 animate-ping mr-1" />
                    ) : (
                      <span className="w-3 h-3 rounded-full border border-slate-300 inline-block text-[8px] text-center text-slate-400">
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

        {/* Transparent AI Disclaimer */}
        <div className="p-4 rounded-xl bg-white border border-sky-200 flex items-start space-x-3 text-xs text-slate-500 shadow-sm">
          <Info className="w-4 h-4 text-sky-600 mt-0.5 flex-shrink-0" />
          <p className="text-[11px] leading-relaxed">
            <strong className="text-slate-800">Forensic Transparency:</strong> Video deepfake detection analyzes multi-frame temporal consistency and facial boundary transitions. A complete video is never classified based on one frame alone. Videos with no detectable human face or severe motion blur are reported as uncertain.
          </p>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={(inputMode === 'file' ? !selectedFile : !videoUrl.trim()) || isUploading}
          className="w-full py-3.5 px-6 rounded-xl bg-gradient-to-r from-sky-600 via-blue-600 to-indigo-600 hover:from-sky-500 hover:to-indigo-500 text-white text-xs font-bold transition flex items-center justify-center space-x-2 shadow-lg shadow-blue-500/25 disabled:opacity-50"
        >
          {isUploading ? (
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>
                {inputMode === 'url' ? 'Fetching Video Stream & Running Forensic Analysis...' : 'Analyzing Spatial Frames & Facial Landmarks...'}
              </span>
            </div>
          ) : (
            <>
              <span>
                {inputMode === 'url' ? 'Download & Execute Deepfake Analysis' : 'Execute Deepfake Video Analysis'}
              </span>
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>
      </form>
    </div>
  );
};

