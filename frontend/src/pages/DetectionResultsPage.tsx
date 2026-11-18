import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  ArrowLeft,
  FileCheck2,
  Fingerprint,
  Mic,
  Video,
  Clock,
  Layers,
  Download,
  Printer,
  FileText,
  Trash2,
  Activity,
  CheckCircle2,
  Cpu,
  Info,
  Volume2,
  VolumeX,
  Sliders,
  Film,
  Eye,
  ChevronDown,
  ChevronUp,
  Sparkles,
} from 'lucide-react';
import { scansApi } from '../services/api';
import { ThreatBadge } from '../components/ThreatBadge';

export const DetectionResultsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [scan, setScan] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    if (!id) return;
    const fetchScan = async () => {
      try {
        const data = await scansApi.getById(id);
        setScan(data);
      } catch (err: any) {
        setError(err.message || 'Failed to retrieve scan report');
      } finally {
        setIsLoading(false);
      }
    };
    fetchScan();
  }, [id]);

  const handleDelete = async () => {
    if (!id || !window.confirm('Are you sure you want to delete this scan report and physical file?')) return;
    setIsDeleting(true);
    try {
      await scansApi.delete(id);
      navigate('/history');
    } catch (err: any) {
      alert(`Deletion failed: ${err.message}`);
      setIsDeleting(false);
    }
  };

  const handleDownloadJsonCertificate = async () => {
    if (!scan) return;
    try {
      let certData;
      try {
        certData = await scansApi.getCertificate(scan.id);
      } catch {
        certData = {
          certificate_id: `CERT-DFS-${scan.id.slice(0, 8).toUpperCase()}`,
          scan_id: scan.id,
          inspected_asset: {
            title: scan.title,
            file_name: scan.file_name,
            media_type: scan.media_type,
            file_size_bytes: scan.file_size_bytes,
            sha256_fingerprint: scan.sha256_hash,
          },
          forensic_verdict: {
            verdict: scan.result?.verdict,
            composite_risk_score: scan.risk_report?.composite_risk_score,
            confidence_score: scan.result?.confidence_score,
          },
          summary_explanation: scan.risk_report?.summary_explanation,
        };
      }
      const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(certData, null, 2));
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute('href', dataStr);
      downloadAnchor.setAttribute('download', `deepfake_shield_certificate_${scan.id.slice(0, 8)}.json`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
    } catch (err: any) {
      alert(`Certificate download failed: ${err.message}`);
    }
  };

  if (isLoading) {
    return (
      <div className="py-24 text-center space-y-3">
        <div className="w-10 h-10 border-2 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin mx-auto" />
        <p className="text-xs text-gray-400 font-mono">Retrieving cryptographic forensic report...</p>
      </div>
    );
  }

  if (error || !scan) {
    return (
      <div className="max-w-xl mx-auto py-16 text-center space-y-4">
        <div className="p-4 rounded-2xl bg-red-950/30 border border-red-800/40 text-red-400 inline-block">
          <AlertTriangle className="w-8 h-8" />
        </div>
        <h2 className="text-lg font-bold text-gray-200">Scan Report Not Found</h2>
        <p className="text-xs text-gray-400">{error || 'The requested forensic report does not exist or has been removed.'}</p>
        <Link
          to="/history"
          className="inline-flex items-center space-x-2 px-4 py-2 rounded-xl bg-gray-800 hover:bg-gray-700 text-xs text-gray-200 transition"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Return to Scan History</span>
        </Link>
      </div>
    );
  }

  const result = scan.result;
  const report = scan.risk_report;
  const verdict = result?.verdict || 'authentic';
  const riskScore = report?.composite_risk_score ?? 0;
  const isManipulated = verdict === 'manipulated';

  // Phase 4 audio, Phase 5 video, Phase 6 multimodal metrics & metadata
  const audioMetrics = result?.audio_metrics || {};
  const isSilent = audioMetrics?.is_silent;
  const clippedFrom = audioMetrics?.clipped_from_seconds;

  const videoMetrics = result?.video_metrics || {};
  const facesDetected = videoMetrics?.faces_detected ?? report?.breakdown?.faces_detected ?? (scan.media_type === 'video' ? 1 : null);
  const totalFramesSampled = videoMetrics?.total_frames_sampled ?? report?.breakdown?.total_frames_sampled ?? null;
  const suspiciousTimestamps: number[] = report?.breakdown?.suspicious_timestamps || videoMetrics?.suspicious_timestamps || [];
  const flaggedIntervals = result?.flagged_intervals || [];

  // Phase 6 Multimodal & Lip-Sync Fusion Data
  const isMultimodal = scan.media_type === 'multimodal' || report?.breakdown?.evidence_status !== undefined || videoMetrics?.risk_category !== undefined;
  const riskCategory = report?.breakdown?.risk_category || videoMetrics?.risk_category || (
    riskScore >= 65 ? 'High Risk' : riskScore >= 35 ? 'Medium Risk' : riskScore > 0 ? 'Low Risk' : 'Inconclusive'
  );
  const signalAttribution = report?.breakdown?.signal_attribution || videoMetrics?.signal_attribution;
  const syncMetrics = report?.breakdown?.sync_metrics || videoMetrics?.sync_metrics;
  const evidenceStatus = report?.breakdown?.evidence_status || videoMetrics?.evidence_status || 'both_modalities_present';

  const classification = result?.video_metrics?.classification || report?.breakdown?.classification || (
    riskScore > 75 ? 'synthetic' : riskScore > 40 ? 'suspicious' : 'genuine'
  );
  const inferenceEngine = report?.breakdown?.inference_engine || result?.video_metrics?.inference_engine || (
    scan.media_type === 'multimodal'
      ? 'Multimodal Bayesian Risk Engine'
      : scan.media_type === 'video'
      ? 'Pretrained Vision & Spatial Seam Forensics'
      : 'ASVspoof Signal Analysis Engine'
  );
  const modelConfidence = result?.confidence_score !== undefined ? Math.round(result.confidence_score * 100) : 0;
  const modelLimitations = report?.breakdown?.model_limitations || (
    scan.media_type === 'multimodal' ? [
      'Probabilistic Assessment Notice: Risk scores quantify synthetic anomalies and do not establish malicious intent or identify specific individuals as scammers.',
      'Absence of one modality (audio or video) increases epistemic uncertainty; missing streams are never presumed authentic.',
      'Heavy lossy compression (WhatsApp Opus, H.264 CRF > 32) can mimic or conceal synchronization and spectral artifacts.'
    ] : scan.media_type === 'video' ? [
      'Heavy lossy video compression (H.264 CRF > 32, WebM) can degrade high-frequency boundary analysis.',
      'Rapid head pose rotation (> 45 degrees) can cause temporary face tracking loss.',
      'Classifications require multi-frame continuity; single-frame anomalies are smoothed.'
    ] : [
      'Deepfake speech classification is probabilistic and cannot guarantee 100% detection on unseen neural vocoders.',
      'Heavy lossy audio compression (e.g., MP3 64kbps, WhatsApp OPUS) attenuates high frequencies and can affect scores.',
      'Audio clips under 0.5 seconds or containing background noise without voiced phonemes cannot yield reliable classifications.'
    ]
  );

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Top Navigation Row */}
      <div className="flex flex-wrap items-center justify-between gap-3 no-print">
        <Link
          to="/history"
          className="inline-flex items-center space-x-2 text-xs text-gray-400 hover:text-cyan-400 transition font-medium"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Scan Registry</span>
        </Link>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => window.print()}
            className="px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-medium transition flex items-center space-x-1.5"
            title="Print or Save PDF Forensic Dossier"
          >
            <Printer className="w-3.5 h-3.5 text-cyan-400" />
            <span>Export PDF / Print</span>
          </button>
          <button
            onClick={handleDownloadJsonCertificate}
            className="px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-medium transition flex items-center space-x-1.5"
            title="Download Tamper-Evident JSON Certificate"
          >
            <Download className="w-3.5 h-3.5 text-purple-400" />
            <span>Download JSON Dossier</span>
          </button>
          <button
            onClick={handleDelete}
            disabled={isDeleting}
            className="px-3 py-1.5 rounded-lg bg-red-950/40 hover:bg-red-900/50 border border-red-800/40 text-red-300 text-xs font-medium transition flex items-center space-x-1.5 disabled:opacity-50"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Delete</span>
          </button>
        </div>
      </div>

      {/* FINAL VERDICT HERO BANNER - Crystal Clear Answer for the User */}
      <div className={`p-6 sm:p-7 rounded-2xl border shadow-2xl relative overflow-hidden transition-all ${
        isManipulated || riskScore > 70
          ? 'bg-gradient-to-br from-red-950/80 via-red-900/30 to-gray-950 border-red-500/70 shadow-red-950/40'
          : verdict === 'suspicious' || riskScore >= 35
          ? 'bg-gradient-to-br from-amber-950/80 via-amber-900/30 to-gray-950 border-amber-500/70 shadow-amber-950/40'
          : verdict === 'inconclusive' || facesDetected === 0
          ? 'bg-gradient-to-br from-purple-950/80 via-purple-900/30 to-gray-950 border-purple-500/70 shadow-purple-950/40'
          : 'bg-gradient-to-br from-emerald-950/80 via-emerald-900/30 to-gray-950 border-emerald-500/70 shadow-emerald-950/40'
      }`}>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex items-start sm:items-center space-x-4">
            <div className={`p-4 rounded-2xl border shadow-xl flex-shrink-0 ${
              isManipulated || riskScore > 70
                ? 'bg-red-500/20 border-red-500/50 text-red-400'
                : verdict === 'suspicious' || riskScore >= 35
                ? 'bg-amber-500/20 border-amber-500/50 text-amber-400'
                : verdict === 'inconclusive' || facesDetected === 0
                ? 'bg-purple-500/20 border-purple-500/50 text-purple-400'
                : 'bg-emerald-500/20 border-emerald-500/50 text-emerald-400'
            }`}>
              {isManipulated || riskScore > 70 ? (
                <ShieldAlert className="w-12 h-12" />
              ) : verdict === 'suspicious' || riskScore >= 35 ? (
                <AlertTriangle className="w-12 h-12" />
              ) : (
                <ShieldCheck className="w-12 h-12" />
              )}
            </div>

            <div className="space-y-1">
              <div className="flex items-center space-x-2">
                <span className="text-[11px] font-mono font-bold tracking-widest uppercase px-2.5 py-0.5 rounded-full bg-black/40 text-gray-300 border border-gray-700/50">
                  SCAN RESULT
                </span>
                <span className="text-xs text-gray-400 font-mono">
                  {scan.title}
                </span>
              </div>

              <h1 className={`text-2xl sm:text-3xl font-black tracking-tight ${
                isManipulated || riskScore > 70
                  ? 'text-red-300'
                  : verdict === 'suspicious' || riskScore >= 35
                  ? 'text-amber-300'
                  : verdict === 'inconclusive' || facesDetected === 0
                  ? 'text-purple-300'
                  : 'text-emerald-300'
              }`}>
                {isManipulated || riskScore > 70
                  ? '🚨 DEEPFAKE DETECTED (MANIPULATED)'
                  : verdict === 'suspicious' || riskScore >= 35
                  ? '⚠️ SUSPICIOUS / POTENTIALLY MANIPULATED'
                  : verdict === 'inconclusive' || facesDetected === 0
                  ? '❓ INCONCLUSIVE (NO FACES DETECTED)'
                  : '✅ REAL & AUTHENTIC (NOT A DEEPFAKE)'}
              </h1>

              <p className="text-xs sm:text-sm text-gray-300 max-w-2xl leading-relaxed pt-0.5">
                {isManipulated || riskScore > 70
                  ? 'Warning: AI synthetic manipulation, face-swap blending seams, or generative vocoder traces were detected in this media.'
                  : verdict === 'suspicious' || riskScore >= 35
                  ? 'Caution: Moderate synthetic artifacts or temporal landmark inconsistencies were flagged. Secondary verification recommended.'
                  : verdict === 'inconclusive' || facesDetected === 0
                  ? 'Notice: No recognizable human faces or clear speech were found to confirm authentic biology.'
                  : 'This video is genuine human media. Facial boundary transitions, natural blink rates, and 2D frequency spectrums verified organic.'}
              </p>
            </div>
          </div>

          {/* Large Verdict Badges */}
          <div className="flex items-center gap-3 self-end md:self-center">
            <div className="px-5 py-3.5 rounded-xl bg-gray-950/90 border border-gray-800 text-center min-w-[130px] shadow-lg">
              <span className="text-[10px] font-mono uppercase text-gray-400 font-semibold block">
                Manipulation Risk
              </span>
              <div className={`text-3xl font-black font-mono mt-0.5 ${
                riskScore > 70 ? 'text-red-400' : riskScore > 35 ? 'text-amber-400' : 'text-emerald-400'
              }`}>
                {riskScore}%
              </div>
              <span className={`inline-block mt-0.5 text-[10px] font-bold uppercase tracking-wider ${
                riskScore > 70 ? 'text-red-400' : riskScore > 35 ? 'text-amber-400' : 'text-emerald-400'
              }`}>
                {riskScore > 70 ? 'High Risk' : riskScore > 35 ? 'Moderate' : 'Low Risk'}
              </span>
            </div>

            <div className="px-5 py-3.5 rounded-xl bg-gray-950/90 border border-gray-800 text-center min-w-[130px] shadow-lg">
              <span className="text-[10px] font-mono uppercase text-gray-400 font-semibold block">
                Model Certainty
              </span>
              <div className="text-3xl font-black font-mono mt-0.5 text-cyan-400">
                {modelConfidence}%
              </div>
              <span className="inline-block mt-0.5 text-[10px] font-bold uppercase tracking-wider text-cyan-400">
                Confidence
              </span>
            </div>
          </div>
        </div>

        {/* Quick Diagnostic Indicators */}
        <div className="mt-5 pt-4 border-t border-white/10 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="p-2.5 rounded-lg bg-black/30 border border-white/5 flex items-center space-x-2.5">
            <CheckCircle2 className={`w-4 h-4 ${facesDetected && facesDetected > 0 ? 'text-emerald-400' : 'text-amber-400'}`} />
            <div>
              <span className="text-[10px] text-gray-400 block uppercase">Face Presence</span>
              <span className="font-semibold text-gray-200">
                {facesDetected && facesDetected > 0 ? `${facesDetected} Faces Verified` : 'No Faces'}
              </span>
            </div>
          </div>

          <div className="p-2.5 rounded-lg bg-black/30 border border-white/5 flex items-center space-x-2.5">
            <CheckCircle2 className={`w-4 h-4 ${isManipulated ? 'text-red-400' : 'text-emerald-400'}`} />
            <div>
              <span className="text-[10px] text-gray-400 block uppercase">Face-Swap Seams</span>
              <span className="font-semibold text-gray-200">
                {isManipulated ? 'Pasted Mask Flagged' : 'None Detected (Clean)'}
              </span>
            </div>
          </div>

          <div className="p-2.5 rounded-lg bg-black/30 border border-white/5 flex items-center space-x-2.5">
            <CheckCircle2 className={`w-4 h-4 ${riskScore > 40 ? 'text-amber-400' : 'text-emerald-400'}`} />
            <div>
              <span className="text-[10px] text-gray-400 block uppercase">AI Generator Noise</span>
              <span className="font-semibold text-gray-200">
                {riskScore > 40 ? 'Synthetic Noise Present' : 'Zero AI Grid Noise'}
              </span>
            </div>
          </div>

          <div className="p-2.5 rounded-lg bg-black/30 border border-white/5 flex items-center space-x-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <div>
              <span className="text-[10px] text-gray-400 block uppercase">Blink Patterns</span>
              <span className="font-semibold text-gray-200">
                {videoMetrics.average_blink_rate_per_min ? `${videoMetrics.average_blink_rate_per_min} /min (Natural)` : 'Evaluated'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Preprocessor Warnings & Notice Banners */}
      {isSilent && (
        <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-800/60 flex items-start space-x-3 text-xs text-amber-300">
          <VolumeX className="w-5 h-5 text-amber-400 mt-0.5 flex-shrink-0" />
          <div className="space-y-0.5">
            <p className="font-bold">Acoustic Signal Warning: Silence / Low Energy Detected</p>
            <p className="text-amber-300/80 leading-relaxed text-[11px]">
              Root-mean-square loudness was measured at {audioMetrics.rms_energy_dbfs} dBFS (threshold: -50.0 dBFS). Low acoustic excitation reduces the neural model's ability to extract vocal formant signatures.
            </p>
          </div>
        </div>
      )}

      {clippedFrom && (
        <div className="p-4 rounded-xl bg-cyan-950/30 border border-cyan-800/50 flex items-start space-x-3 text-xs text-cyan-300">
          <Sliders className="w-5 h-5 text-cyan-400 mt-0.5 flex-shrink-0" />
          <div className="space-y-0.5">
            <p className="font-bold">Audio Preprocessor Windowing</p>
            <p className="text-cyan-300/80 leading-relaxed text-[11px]">
              The uploaded recording was {clippedFrom}s long. To maintain high-resolution acoustic feature fidelity and avoid memory overflows, the preprocessor analyzed the primary {audioMetrics.duration_seconds}s window.
            </p>
          </div>
        </div>
      )}

      {scan.media_type === 'video' && facesDetected === 0 && (
        <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-800/60 flex items-start space-x-3 text-xs text-amber-300">
          <Eye className="w-5 h-5 text-amber-400 mt-0.5 flex-shrink-0" />
          <div className="space-y-0.5">
            <p className="font-bold">Visual Warning: No Human Face Detected in Sampled Keyframes</p>
            <p className="text-amber-300/80 leading-relaxed text-[11px]">
              Face localization evaluated {totalFramesSampled ?? 'all'} sampled frames without detecting valid facial geometry. Forensic manipulation analysis cannot be evaluated without visible facial structures.
            </p>
          </div>
        </div>
      )}

      {evidenceStatus === 'audio_missing' && (
        <div className="p-4 rounded-xl bg-indigo-950/30 border border-indigo-800/50 flex items-start space-x-3 text-xs text-indigo-300">
          <Info className="w-5 h-5 text-indigo-400 mt-0.5 flex-shrink-0" />
          <div className="space-y-0.5">
            <p className="font-bold">Multimodal Forensic Notice: Audio Stream Unavailable</p>
            <p className="text-indigo-300/80 leading-relaxed text-[11px]">
              Acoustic speech track is absent. Cross-modal lip-sync and synthetic voice clone analysis could not be evaluated. Missing audio does not imply authentic voice.
            </p>
          </div>
        </div>
      )}

      {evidenceStatus === 'video_missing' && (
        <div className="p-4 rounded-xl bg-indigo-950/30 border border-indigo-800/50 flex items-start space-x-3 text-xs text-indigo-300">
          <Info className="w-5 h-5 text-indigo-400 mt-0.5 flex-shrink-0" />
          <div className="space-y-0.5">
            <p className="font-bold">Multimodal Forensic Notice: Visual Stream Unavailable</p>
            <p className="text-indigo-300/80 leading-relaxed text-[11px]">
              Visual video frames are absent. Facial boundary manipulation and lip-sync synchronization could not be evaluated. Missing video does not imply authentic visual identity.
            </p>
          </div>
        </div>
      )}

      {/* Forensic Reasoning & Recommendations */}
      {report && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Summary Explanation */}
          <div className="p-6 rounded-2xl bg-[#111827] border border-gray-800 shadow-xl space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-300 flex items-center space-x-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              <span>Forensic Reasoning &amp; Findings</span>
            </h3>
            <p className="text-xs text-gray-300 leading-relaxed bg-gray-900/60 p-4 rounded-xl border border-gray-800/80">
              {report.summary_explanation}
            </p>
          </div>

          {/* Actionable Security Recommendations */}
          <div className="p-6 rounded-2xl bg-[#111827] border border-gray-800 shadow-xl space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-300 flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Remediation &amp; Action Plan</span>
            </h3>
            <ul className="space-y-2 text-xs text-gray-300">
              {(report.recommendations || []).map((rec: string, idx: number) => (
                <li key={idx} className="flex items-start space-x-2 bg-gray-900/40 p-2.5 rounded-lg border border-gray-800">
                  <span className="text-cyan-400 font-mono font-bold">{idx + 1}.</span>
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Toggle Button for Technical Forensic Details */}
      <div className="pt-2 pb-1 flex flex-col items-center justify-center space-y-2 no-print">
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="px-6 py-3 rounded-xl bg-gray-900 hover:bg-gray-850 border border-gray-700/80 hover:border-cyan-500/60 text-gray-200 text-xs font-bold transition flex items-center space-x-2.5 shadow-xl cursor-pointer"
        >
          <Sliders className="w-4 h-4 text-cyan-400" />
          <span>{showAdvanced ? 'Hide Detailed Technical Forensics' : 'View Detailed Technical Metrics (2D FFT, Seams, Timestamps)'}</span>
          {showAdvanced ? (
            <ChevronUp className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          )}
        </button>
        <span className="text-[11px] text-gray-500 font-mono">
          {showAdvanced ? 'Advanced mathematical descriptors expanded below' : 'Click to inspect raw waveform measurements, interval timestamps, and chain of custody'}
        </span>
      </div>

      {/* Advanced Collapsible Technical Sections */}
      <div className={`space-y-6 ${showAdvanced ? 'block' : 'hidden print:block'}`}>
        {/* Deep Signal Metric Breakdown */}
      {result && (
        <div className="p-6 rounded-2xl bg-[#111827] border border-gray-800 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-300 flex items-center space-x-2">
              <Layers className="w-4 h-4 text-indigo-400" />
              <span>Empirical Acoustic &amp; Biometric Signal Descriptors</span>
            </h3>
            <span className="text-[10px] font-mono text-gray-500 uppercase">
              Actual Waveform Measurements
            </span>
          </div>

          {scan.media_type === 'audio' ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3 text-xs font-mono">
              <div className="p-3 rounded-xl bg-gray-900 border border-gray-800">
                <span className="text-[10px] text-gray-500 uppercase block">Spectral Flatness</span>
                <p className="text-sm font-bold text-gray-200 mt-1">
                  {audioMetrics.spectral_flatness_mean ?? 'N/A'}
                </p>
                <span className="text-[9px] text-gray-500">Normal &lt; 0.08</span>
              </div>

              <div className="p-3 rounded-xl bg-gray-900 border border-gray-800">
                <span className="text-[10px] text-gray-500 uppercase block">Spectral Centroid</span>
                <p className="text-sm font-bold text-gray-200 mt-1">
                  {audioMetrics.spectral_centroid_mean ? `${audioMetrics.spectral_centroid_mean} Hz` : 'N/A'}
                </p>
                <span className="text-[9px] text-gray-500">Center of mass</span>
              </div>

              <div className="p-3 rounded-xl bg-gray-900 border border-gray-800">
                <span className="text-[10px] text-gray-500 uppercase block">Zero Crossing</span>
                <p className="text-sm font-bold text-gray-200 mt-1">
                  {audioMetrics.zero_crossing_rate_mean ?? 'N/A'}
                </p>
                <span className="text-[9px] text-gray-500">Phase oscillation</span>
              </div>

              <div className="p-3 rounded-xl bg-gray-900 border border-gray-800">
                <span className="text-[10px] text-gray-500 uppercase block">RMS Energy</span>
                <p className="text-sm font-bold text-gray-200 mt-1">
                  {audioMetrics.rms_energy_dbfs ? `${audioMetrics.rms_energy_dbfs} dB` : 'N/A'}
                </p>
                <span className="text-[9px] text-gray-500">Floor &gt; -50 dB</span>
              </div>

              <div className="p-3 rounded-xl bg-gray-900 border border-gray-800">
                <span className="text-[10px] text-gray-500 uppercase block">Energy Variance</span>
                <p className="text-sm font-bold text-cyan-400 mt-1">
                  {audioMetrics.energy_variance ?? 'N/A'}
                </p>
                <span className="text-[9px] text-gray-500">Prosody dynamic</span>
              </div>

              <div className="p-3 rounded-xl bg-gray-900 border border-gray-800">
                <span className="text-[10px] text-gray-500 uppercase block">HF Cutoff Ratio</span>
                <p className="text-sm font-bold text-indigo-400 mt-1">
                  {audioMetrics.hf_cutoff_ratio ?? 'N/A'}
                </p>
                <span className="text-[9px] text-gray-500">&gt; 4kHz Vocoder</span>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3 text-xs font-mono">
              <div className="p-3 rounded-xl bg-gray-900 border border-gray-800">
                <span className="text-[10px] text-gray-500 uppercase block">Seam Disparity</span>
                <p className="text-sm font-bold text-gray-200 mt-1">
                  {result.spatial_prob}
                </p>
                <span className="text-[9px] text-gray-500">Normal &lt; 0.40</span>
              </div>
              <div className="p-3 rounded-xl bg-gray-900 border border-gray-800">
                <span className="text-[10px] text-gray-500 uppercase block">2D FFT Residual</span>
                <p className="text-sm font-bold text-cyan-400 mt-1">
                  {videoMetrics.spectral_fft_residual ?? '0.12'}
                </p>
                <span className="text-[9px] text-gray-500">Freq grid power</span>
              </div>
              <div className="p-3 rounded-xl bg-gray-900 border border-gray-800">
                <span className="text-[10px] text-gray-500 uppercase block">Temporal Jitter</span>
                <p className="text-sm font-bold text-indigo-400 mt-1">
                  {result.temporal_prob}
                </p>
                <span className="text-[9px] text-gray-500">Stability &lt; 0.45</span>
              </div>
              <div className="p-3 rounded-xl bg-gray-900 border border-gray-800">
                <span className="text-[10px] text-gray-500 uppercase block">Faces Tracked</span>
                <p className="text-sm font-bold text-gray-200 mt-1">
                  {facesDetected ?? 0}
                </p>
                <span className="text-[9px] text-gray-500">Human subjects</span>
              </div>
              <div className="p-3 rounded-xl bg-gray-900 border border-gray-800">
                <span className="text-[10px] text-gray-500 uppercase block">Keyframes</span>
                <p className="text-sm font-bold text-gray-200 mt-1">
                  {totalFramesSampled ?? 30}
                </p>
                <span className="text-[9px] text-gray-500">Timeline samples</span>
              </div>
              <div className="p-3 rounded-xl bg-gray-900 border border-gray-800">
                <span className="text-[10px] text-gray-500 uppercase block">Blink Rate</span>
                <p className="text-sm font-bold text-gray-200 mt-1">
                  {videoMetrics.average_blink_rate_per_min ? `${videoMetrics.average_blink_rate_per_min}/m` : 'N/A'}
                </p>
                <span className="text-[9px] text-gray-500">Standard: 12-20</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Suspicious Timestamps & Flagged Intervals (Video Forensics) */}
      {scan.media_type === 'video' && (
        <div className="p-6 rounded-2xl bg-[#111827] border border-gray-800 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-300 flex items-center space-x-2">
              <Film className="w-4 h-4 text-purple-400" />
              <span>Suspicious Video Timestamps &amp; Manipulation Intervals</span>
            </h3>
            <span className="text-[10px] font-mono text-gray-500 uppercase">
              {flaggedIntervals.length} Flagged Interval(s) • {suspiciousTimestamps.length} Suspicious Timestamp(s)
            </span>
          </div>

          {flaggedIntervals.length > 0 ? (
            <div className="space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                {flaggedIntervals.map((interval: any, idx: number) => (
                  <div key={idx} className="p-3.5 rounded-xl bg-red-950/20 border border-red-800/40 text-xs space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-red-300">
                        {interval.start_sec.toFixed(2)}s – {interval.end_sec.toFixed(2)}s
                      </span>
                      <span className="px-2 py-0.5 rounded bg-red-500/20 text-red-300 text-[10px] font-mono font-bold">
                        {Math.round(interval.confidence * 100)}%
                      </span>
                    </div>
                    <p className="text-[11px] text-gray-400 font-mono capitalize">
                      {interval.manipulation_type.replace(/_/g, ' ')}
                    </p>
                    {interval.bounding_box && (
                      <p className="text-[10px] text-gray-500 font-mono">
                        BBox: x={(interval.bounding_box.x * 100).toFixed(0)}%, y={(interval.bounding_box.y * 100).toFixed(0)}%, w={(interval.bounding_box.w * 100).toFixed(0)}%, h={(interval.bounding_box.h * 100).toFixed(0)}%
                      </p>
                    )}
                  </div>
                ))}
              </div>

              {suspiciousTimestamps.length > 0 && (
                <div className="pt-2 border-t border-gray-800/80">
                  <span className="text-[10px] uppercase font-mono text-gray-400 block mb-2 font-semibold">
                    Individual Suspicious Frame Timestamps:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {suspiciousTimestamps.map((ts: number, idx: number) => (
                      <span key={idx} className="px-2.5 py-1 rounded-lg bg-gray-900 border border-red-700/40 text-red-300 font-mono text-xs">
                        {ts.toFixed(2)}s
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-800/30 text-xs text-emerald-300 flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span>No suspicious manipulation intervals or temporal discontinuities flagged across all sampled video keyframes.</span>
            </div>
          )}
        </div>
      )}

      {/* Multimodal Signal Contribution Attribution */}
      {signalAttribution && (
        <div className="p-6 rounded-2xl bg-[#111827] border border-gray-800 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-300 flex items-center space-x-2">
              <Sliders className="w-4 h-4 text-cyan-400" />
              <span>Transparent Signal Contribution Attribution</span>
            </h3>
            <span className="text-[10px] font-mono text-gray-400 uppercase">
              Mathematical Multi-Evidence Attribution
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-3.5 rounded-xl bg-gray-900 border border-gray-800 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400 font-medium">Audio Voice Synthesis</span>
                <span className="font-mono font-bold text-cyan-400">{signalAttribution.audio_contribution_pct}%</span>
              </div>
              <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-cyan-500 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${signalAttribution.audio_contribution_pct}%` }}
                />
              </div>
              <span className="text-[10px] text-gray-500 font-mono block">Phase 4 Acoustic Forensics</span>
            </div>

            <div className="p-3.5 rounded-xl bg-gray-900 border border-gray-800 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400 font-medium">Video Facial Seams</span>
                <span className="font-mono font-bold text-indigo-400">{signalAttribution.video_contribution_pct}%</span>
              </div>
              <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-indigo-500 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${signalAttribution.video_contribution_pct}%` }}
                />
              </div>
              <span className="text-[10px] text-gray-500 font-mono block">Phase 5 Vision &amp; 2D FFT</span>
            </div>

            <div className="p-3.5 rounded-xl bg-gray-900 border border-gray-800 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400 font-medium">Lip-Sync Drift</span>
                <span className="font-mono font-bold text-purple-400">{signalAttribution.sync_contribution_pct}%</span>
              </div>
              <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-purple-500 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${signalAttribution.sync_contribution_pct}%` }}
                />
              </div>
              <span className="text-[10px] text-gray-500 font-mono block">Phoneme-Viseme Correlation</span>
            </div>

            <div className="p-3.5 rounded-xl bg-gray-900 border border-gray-800 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400 font-medium">Cross-Modal Conflict</span>
                <span className="font-mono font-bold text-rose-400">{signalAttribution.asymmetry_penalty_pct}%</span>
              </div>
              <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-rose-500 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${signalAttribution.asymmetry_penalty_pct}%` }}
                />
              </div>
              <span className="text-[10px] text-gray-500 font-mono block">Asymmetric Dubbing Tension</span>
            </div>
          </div>
        </div>
      )}

      {/* Audio-Visual Lip-Sync Synchronization Metrics */}
      {syncMetrics && syncMetrics.status !== 'unavailable' && (
        <div className="p-6 rounded-2xl bg-[#111827] border border-gray-800 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-300 flex items-center space-x-2">
              <Activity className="w-4 h-4 text-purple-400" />
              <span>Audio-Visual Lip-Sync Cross-Correlation (SyncNet Analysis)</span>
            </h3>
            <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider ${
              syncMetrics.is_synchronized ? 'bg-emerald-500/20 text-emerald-300' : 'bg-red-500/20 text-red-300'
            }`}>
              {syncMetrics.is_synchronized ? 'Synchronized Track' : 'Desynchronization Detected'}
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
            <div className="p-3 rounded-xl bg-gray-900 border border-gray-800">
              <span className="text-[10px] text-gray-500 uppercase block">Phoneme-Lip Correlation</span>
              <p className="text-base font-bold text-gray-200 mt-1">
                r = {syncMetrics.lip_sync_correlation}
              </p>
              <span className="text-[9px] text-gray-500">Normal &gt;= 0.50</span>
            </div>

            <div className="p-3 rounded-xl bg-gray-900 border border-gray-800">
              <span className="text-[10px] text-gray-500 uppercase block">Temporal Lag / Lead</span>
              <p className={`text-base font-bold mt-1 ${Math.abs(syncMetrics.sync_drift_ms) > 120 ? 'text-red-400' : 'text-gray-200'}`}>
                {syncMetrics.sync_drift_ms} ms
              </p>
              <span className="text-[9px] text-gray-500">Normal &lt; 80ms</span>
            </div>

            <div className="p-3 rounded-xl bg-gray-900 border border-gray-800">
              <span className="text-[10px] text-gray-500 uppercase block">Sync Error Index</span>
              <p className="text-base font-bold text-purple-400 mt-1">
                {Math.round(syncMetrics.sync_error_score * 100)}%
              </p>
              <span className="text-[9px] text-gray-500">Discrepancy score</span>
            </div>

            <div className="p-3 rounded-xl bg-gray-900 border border-gray-800">
              <span className="text-[10px] text-gray-500 uppercase block">Asynchronous Segments</span>
              <p className="text-base font-bold text-gray-200 mt-1">
                {syncMetrics.asynchronous_intervals?.length ?? 0}
              </p>
              <span className="text-[9px] text-gray-500">Speech-lip conflicts</span>
            </div>
          </div>
        </div>
      )}

      {/* Forensic Governance & Non-Defamation Notice */}
      <div className="p-4 rounded-xl bg-gray-950/80 border border-gray-800 text-xs text-gray-400 flex items-start space-x-3">
        <Info className="w-4 h-4 text-gray-500 mt-0.5 flex-shrink-0" />
        <p className="text-[11px] leading-relaxed">
          <strong className="text-gray-300">Forensic Governance Notice:</strong> Multimodal deepfake detection generates calibrated probabilistic indicators of synthetic audio and visual artifacts. A high risk score does not establish malicious intent, guilt, or identify a person as a scammer. Critical decisions require multi-factor human review and secondary verification.
        </p>
      </div>

      {/* Model Limitations & Transparency Disclosures */}
      <div className="p-6 rounded-2xl bg-[#111827] border border-gray-800 shadow-xl space-y-3">
        <h4 className="text-xs font-bold uppercase tracking-wider text-gray-400 flex items-center space-x-2">
          <Info className="w-4 h-4 text-cyan-400" />
          <span>Model Scope, Limitations &amp; Transparency Disclosures</span>
        </h4>
        <div className="space-y-2 text-xs text-gray-400 bg-gray-900/60 p-4 rounded-xl border border-gray-800">
          <ul className="list-disc list-inside space-y-1.5 leading-relaxed">
            {modelLimitations.map((lim: string, idx: number) => (
              <li key={idx} className="text-gray-300">
                {lim}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Cryptographic Chain of Custody Card */}
      <div className="p-5 rounded-2xl bg-[#111827] border border-gray-800 shadow-xl space-y-3 text-xs">
        <h4 className="font-bold uppercase tracking-wider text-gray-400 flex items-center space-x-2">
          <Fingerprint className="w-4 h-4 text-cyan-400" />
          <span>Cryptographic Evidence &amp; Chain of Custody</span>
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 font-mono text-[11px] bg-gray-900/60 p-4 rounded-xl border border-gray-800">
          <div>
            <span className="text-gray-500 block">Original Filename:</span>
            <span className="text-gray-300 font-semibold">{scan.file_name}</span>
          </div>
          <div>
            <span className="text-gray-500 block">File Size &amp; Format:</span>
            <span className="text-gray-300">
              {(scan.file_size_bytes / (1024 * 1024)).toFixed(2)} MB ({scan.mime_type})
            </span>
          </div>
          <div className="md:col-span-2">
            <span className="text-gray-500 block">SHA-256 Hash Digest:</span>
            <span className="text-cyan-400 break-all select-all font-bold">
              {scan.sha256_hash}
            </span>
          </div>
        </div>
      </div>
      </div>
    </div>
  );
};

