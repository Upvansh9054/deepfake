import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mic, Upload, FileAudio, CheckCircle2, AlertCircle, ArrowRight, Settings2, Cpu, ShieldAlert, Info, Clock } from 'lucide-react';
import { scansApi } from '../services/api';

export const AudioScannerPage: React.FC = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [audioPreviewUrl, setAudioPreviewUrl] = useState<string | null>(null);
  const [title, setTitle] = useState('');
  const [checkVocoder, setCheckVocoder] = useState(true);
  const [checkCloning, setCheckCloning] = useState(true);

  const [isUploading, setIsUploading] = useState(false);
  const [scanStage, setScanStage] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const stages = [
    { title: 'Cryptographic Ingestion', desc: 'Verifying WAV/MP3 container and computing SHA-256 fingerprint' },
    { title: 'Linear PCM Normalization', desc: 'Gating silence at -50 dBFS, windowing to 30.0s, resample to 16 kHz' },
    { title: 'Acoustic Signal Forensics', desc: 'Measuring Spectral Flatness (SFM) and brickwall cutoffs (>4 kHz)' },
    { title: 'AI Model Inference', desc: 'Pretrained Wav2Vec 2.0 / ASVspoof AST synthetic speech detection' },
    { title: 'Risk Calibration & Audit', desc: 'Distinguishing confidence from fraud risk and logging audit trail' },
  ];

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setTitle(file.name.replace(/\.[^/.]+$/, ''));
      setAudioPreviewUrl(URL.createObjectURL(file));
      setError(null);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setSelectedFile(file);
      setTitle(file.name.replace(/\.[^/.]+$/, ''));
      setAudioPreviewUrl(URL.createObjectURL(file));
      setError(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError('Please select an audio file to scan.');
      return;
    }

    setIsUploading(true);
    setScanStage(0);
    setError(null);

    const timer1 = setTimeout(() => setScanStage(1), 600);
    const timer2 = setTimeout(() => setScanStage(2), 1400);
    const timer3 = setTimeout(() => setScanStage(3), 2400);
    const timer4 = setTimeout(() => setScanStage(4), 3400);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      if (title.trim()) {
        formData.append('title', title.trim());
      }

      const scanResult = await scansApi.uploadAndScan(formData);
      navigate(`/scans/${scanResult.id}`);
    } catch (err: any) {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      clearTimeout(timer4);
      setError(err.message || 'Failed to process audio scan.');
      setIsUploading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center space-x-2 text-cyan-400 text-xs font-semibold uppercase tracking-wider mb-1">
          <Mic className="w-4 h-4" />
          <span>Acoustic Signal Forensics & Pretrained AI Detection</span>
        </div>
        <h1 className="text-xl md:text-2xl font-bold text-gray-100">
          Audio Deepfake & Cloned Voice Scanner
        </h1>
        <p className="text-xs text-gray-400 mt-1">
          Detect neural speech synthesis (TTS), voice cloning, and vocoder phase anomalies using pretrained audio transformers and calibrated empirical signal descriptors.
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
        {/* Dropzone */}
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition ${
            selectedFile
              ? 'border-blue-400 bg-sky-50/70 shadow-sm'
              : 'border-sky-200 hover:border-blue-500 bg-white hover:bg-sky-50/40 shadow-sm'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".wav,.mp3,.ogg,.flac,.m4a,.aac"
            onChange={handleFileChange}
            className="hidden"
          />

          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-sky-50 border border-sky-200 flex items-center justify-center text-sky-600 shadow-sm">
            {selectedFile ? <FileAudio className="w-8 h-8" /> : <Upload className="w-8 h-8" />}
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
                Drop audio recording here, or browse files
              </p>
              <p className="text-xs text-slate-400 font-mono">
                Supports WAV, MP3, FLAC, OGG, M4A up to 250 MB (min 0.5s)
              </p>
            </div>
          )}
        </div>

        {/* Audio Player Preview */}
        {audioPreviewUrl && (
          <div className="p-4 rounded-xl bg-white border border-sky-200 shadow-sm space-y-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Audio Waveform Preview
            </span>
            <audio controls src={audioPreviewUrl} className="w-full h-10 accent-sky-600" />
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
              placeholder="e.g., Executive Voicemail Wire Request"
              className="w-full bg-slate-50 border border-sky-200 rounded-xl px-3.5 py-2.5 text-xs text-slate-800 placeholder-slate-400 focus:bg-white focus:outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100 transition"
            />
          </div>

          <div className="p-5 rounded-xl bg-white border border-sky-200 space-y-3 shadow-sm">
            <div className="flex items-center space-x-2 text-xs font-semibold uppercase tracking-wider text-slate-700">
              <Settings2 className="w-4 h-4 text-sky-600" />
              <span>Inspection Parameters</span>
            </div>
            <div className="space-y-2 text-xs">
              <label className="flex items-center space-x-2 text-slate-600 cursor-pointer">
                <input
                  type="checkbox"
                  checked={checkVocoder}
                  onChange={(e) => setCheckVocoder(e.target.checked)}
                  className="rounded bg-slate-50 border-sky-300 text-sky-600 focus:ring-0"
                />
                <span>Detect Vocoder Cutoffs &amp; Phase Anomalies</span>
              </label>
              <label className="flex items-center space-x-2 text-slate-600 cursor-pointer">
                <input
                  type="checkbox"
                  checked={checkCloning}
                  onChange={(e) => setCheckCloning(e.target.checked)}
                  className="rounded bg-slate-50 border-sky-300 text-sky-600 focus:ring-0"
                />
                <span>Spectral Flatness &amp; Energy Variance Analysis</span>
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
                <span>Forensic Audio Inspection in Progress...</span>
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
                  className={`p-2.5 rounded-lg border text-left transition ${
                    idx === scanStage
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
            <strong className="text-slate-800">Forensic Transparency:</strong> Empirical vocoder artifact analysis, spectral flatness, and ASVspoof neural weights evaluate probabilistic indicators of synthetic synthesis. Audio shorter than 0.5 seconds or containing pure silence cannot yield verified classifications.
          </p>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={!selectedFile || isUploading}
          className="w-full py-3.5 px-6 rounded-xl bg-gradient-to-r from-sky-600 via-blue-600 to-indigo-600 hover:from-sky-500 hover:to-indigo-500 text-white text-xs font-bold transition flex items-center justify-center space-x-2 shadow-lg shadow-blue-500/25 disabled:opacity-50"
        >
          {isUploading ? (
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>Running Pretrained Voice &amp; Signal Forensics...</span>
            </div>
          ) : (
            <>
              <span>Execute Deepfake Voice Analysis</span>
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>
      </form>
    </div>
  );
};

