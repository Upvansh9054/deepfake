import React, { useState, useEffect } from 'react';
import {
  Database,
  ExternalLink,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Play,
  FileCode2,
  Layers,
  ShieldAlert,
  ShieldCheck,
  X,
  Copy,
  Info,
} from 'lucide-react';
import { huggingFaceApi } from '../services/api';

export const DatasetExplorerPage: React.FC = () => {
  const [status, setStatus] = useState<any>(null);
  const [metadata, setMetadata] = useState<any>(null);
  const [splits, setSplits] = useState<any[]>([]);
  const [parquetFiles, setParquetFiles] = useState<string[]>([]);
  const [rows, setRows] = useState<any[]>([]);
  const [totalRows, setTotalRows] = useState(0);

  const [activeTab, setActiveTab] = useState<'rows' | 'parquet' | 'splits' | 'architecture'>('rows');
  const [labelFilter, setLabelFilter] = useState<'all' | 'deepfake' | 'authentic'>('all');
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [previewVideo, setPreviewVideo] = useState<{ src: string; title: string; isDeepfake: boolean } | null>(null);
  const [copiedUrl, setCopiedUrl] = useState<string | null>(null);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [statusRes, metaRes, splitsRes, parquetRes, rowsRes] = await Promise.all([
        huggingFaceApi.getStatus(),
        huggingFaceApi.getMetadata(),
        huggingFaceApi.getSplits(),
        huggingFaceApi.getParquet(),
        huggingFaceApi.getRows({ offset: 0, length: 100 }),
      ]);

      setStatus(statusRes);
      setMetadata(metaRes);
      setSplits(splitsRes.splits || []);
      setParquetFiles(parquetRes.urls || []);
      setRows(rowsRes.rows || []);
      setTotalRows(rowsRes.num_rows_total || (rowsRes.rows ? rowsRes.rows.length : 0));
    } catch (err) {
      console.error('Failed to load Hugging Face dataset intelligence', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSync = async () => {
    setIsSyncing(true);
    try {
      const updated = await huggingFaceApi.syncMetadata();
      setMetadata(updated);
      await loadData();
    } catch (err: any) {
      alert(`Sync failed: ${err.message}`);
    } finally {
      setIsSyncing(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedUrl(text);
    setTimeout(() => setCopiedUrl(null), 2000);
  };

  const filteredRows = rows.filter((r) => {
    if (labelFilter === 'deepfake') return r.is_deepfake;
    if (labelFilter === 'authentic') return !r.is_deepfake;
    return true;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-2xl bg-gradient-to-r from-gray-900 via-[#111827] to-cyan-950/40 border border-gray-800 shadow-xl">
        <div>
          <div className="flex items-center space-x-2 text-cyan-400 text-xs font-semibold uppercase tracking-wider mb-1">
            <Database className="w-4 h-4" />
            <span>Hugging Face Dataset Intelligence Engine</span>
          </div>
          <h1 className="text-xl md:text-2xl font-bold text-gray-100">
            UniDataPro Deepfake Videos Dataset
          </h1>
          <p className="text-xs text-gray-400 mt-1">
            Live metadata and sample row inspection via Hugging Face Datasets Server API. Zero local storage overhead.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleSync}
            disabled={isSyncing}
            className="px-4 py-2 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs font-semibold transition flex items-center space-x-2 disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-cyan-400 ${isSyncing ? 'animate-spin' : ''}`} />
            <span>{isSyncing ? 'Syncing DB...' : 'Sync DB Cache'}</span>
          </button>
          <a
            href="https://huggingface.co/datasets/UniDataPro/deepfake-videos-dataset"
            target="_blank"
            rel="noreferrer"
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white text-xs font-semibold transition flex items-center space-x-2 shadow-lg shadow-cyan-600/20"
          >
            <span>Hugging Face Hub</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>

      {/* Top Telemetry / Status Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Connection Status */}
        <div className="p-5 rounded-xl bg-[#111827] border border-gray-800 shadow-lg">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">HF Server Status</span>
            <div className={`p-1.5 rounded-lg ${status?.status === 'connected' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'}`}>
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="text-xl font-extrabold font-mono text-gray-100 flex items-center space-x-2">
            <span className={`w-2.5 h-2.5 rounded-full ${status?.status === 'connected' ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`}></span>
            <span className="capitalize">{status?.status || 'Connecting'}</span>
          </div>
          <div className="text-[11px] text-gray-400 mt-2 font-mono">
            Latency: <span className="text-cyan-400 font-bold">{status?.latency_ms || 0} ms</span>
          </div>
        </div>

        {/* Dataset Identity */}
        <div className="p-5 rounded-xl bg-[#111827] border border-gray-800 shadow-lg">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Dataset Author</span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-gray-800 text-cyan-400">
              {metadata?.license || 'cc-by-nc-nd-4.0'}
            </span>
          </div>
          <div className="text-xl font-bold text-gray-100 truncate">
            {metadata?.author || 'UniDataPro'}
          </div>
          <div className="text-[11px] text-gray-400 mt-2">
            License: <span className="text-gray-300 font-mono">CC-BY-NC-ND 4.0</span>
          </div>
        </div>

        {/* Split & Partitioning */}
        <div className="p-5 rounded-xl bg-[#111827] border border-gray-800 shadow-lg">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Split / Config</span>
            <Layers className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-xl font-extrabold font-mono text-indigo-400">
            default / train
          </div>
          <div className="text-[11px] text-gray-400 mt-2 font-mono">
            Parquet partitions: <span className="text-gray-200 font-bold">{parquetFiles.length} file</span>
          </div>
        </div>

        {/* Total Sample Records */}
        <div className="p-5 rounded-xl bg-[#111827] border border-gray-800 shadow-lg">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Indexed Samples</span>
            <FileCode2 className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-xl font-extrabold font-mono text-purple-400">
            {totalRows} Videos
          </div>
          <div className="text-[11px] text-gray-400 mt-2">
            50% Deepfake • 50% Authentic
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-800 space-x-6 text-xs font-semibold">
        <button
          onClick={() => setActiveTab('rows')}
          className={`pb-3 transition flex items-center space-x-2 border-b-2 ${
            activeTab === 'rows'
              ? 'border-cyan-400 text-cyan-400'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          <Play className="w-4 h-4" />
          <span>Sample Records Explorer ({rows.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('parquet')}
          className={`pb-3 transition flex items-center space-x-2 border-b-2 ${
            activeTab === 'parquet'
              ? 'border-cyan-400 text-cyan-400'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          <FileCode2 className="w-4 h-4" />
          <span>Parquet Partitions ({parquetFiles.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('splits')}
          className={`pb-3 transition flex items-center space-x-2 border-b-2 ${
            activeTab === 'splits'
              ? 'border-cyan-400 text-cyan-400'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Splits & Features Schema</span>
        </button>

        <button
          onClick={() => setActiveTab('architecture')}
          className={`pb-3 transition flex items-center space-x-2 border-b-2 ${
            activeTab === 'architecture'
              ? 'border-cyan-400 text-cyan-400'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          <Info className="w-4 h-4" />
          <span>Integration Architecture</span>
        </button>
      </div>

      {/* Tab 1: Rows Explorer */}
      {activeTab === 'rows' && (
        <div className="bg-[#111827] border border-gray-800 rounded-2xl shadow-xl p-5 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-gray-800">
            <div>
              <h2 className="text-sm font-bold text-gray-200">
                Ground-Truth Labeled Media Records
              </h2>
              <p className="text-xs text-gray-400">
                Video clips retrieved directly from Hugging Face Datasets Server (Endpoint 2).
              </p>
            </div>

            {/* Filter pills */}
            <div className="flex bg-gray-900 p-1 rounded-lg border border-gray-800 text-xs">
              <button
                onClick={() => setLabelFilter('all')}
                className={`px-3 py-1 rounded-md transition ${labelFilter === 'all' ? 'bg-cyan-600 text-white font-medium' : 'text-gray-400 hover:text-gray-200'}`}
              >
                All ({rows.length})
              </button>
              <button
                onClick={() => setLabelFilter('deepfake')}
                className={`px-3 py-1 rounded-md transition text-red-400 ${labelFilter === 'deepfake' ? 'bg-red-600 text-white font-medium' : 'hover:text-red-300'}`}
              >
                Deepfakes (5)
              </button>
              <button
                onClick={() => setLabelFilter('authentic')}
                className={`px-3 py-1 rounded-md transition text-emerald-400 ${labelFilter === 'authentic' ? 'bg-emerald-600 text-white font-medium' : 'hover:text-emerald-300'}`}
              >
                Authentic (5)
              </button>
            </div>
          </div>

          {isLoading ? (
            <div className="py-16 text-center space-y-3">
              <div className="w-8 h-8 border-2 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin mx-auto" />
              <p className="text-xs text-gray-400 font-mono">Fetching rows from datasets-server.huggingface.co...</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-gray-800 text-gray-500 font-mono uppercase text-[10px]">
                    <th className="pb-3 px-3 font-semibold">Row #</th>
                    <th className="pb-3 px-3 font-semibold">File Path / Reference</th>
                    <th className="pb-3 px-3 font-semibold">Ground-Truth Label</th>
                    <th className="pb-3 px-3 font-semibold">Hugging Face CDN Reference</th>
                    <th className="pb-3 px-3 font-semibold text-right">Preview</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60 font-sans">
                  {filteredRows.map((row) => {
                    const videoSrc = row.video_src || '';
                    const filename = videoSrc.split('/').pop() || `video_${row.row_idx}.mp4`;
                    const subfolder = row.is_deepfake ? 'deepfake' : 'video';
                    return (
                      <tr key={row.row_idx} className="hover:bg-gray-900/40 transition">
                        <td className="py-3 px-3 font-mono text-cyan-400 font-bold">
                          #{row.row_idx}
                        </td>
                        <td className="py-3 px-3 font-mono text-gray-200">
                          <span className="text-gray-500">{subfolder}/</span>
                          <span className="font-semibold">{filename}</span>
                        </td>
                        <td className="py-3 px-3">
                          {row.is_deepfake ? (
                            <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-red-500/10 text-red-400 border border-red-500/30 uppercase tracking-wider">
                              <ShieldAlert className="w-3 h-3 text-red-400" />
                              <span>Deepfake [0]</span>
                            </span>
                          ) : (
                            <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 uppercase tracking-wider">
                              <ShieldCheck className="w-3 h-3 text-emerald-400" />
                              <span>Authentic [1]</span>
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-3">
                          <div className="flex items-center space-x-2">
                            <span className="text-[11px] font-mono text-gray-400 truncate max-w-[240px] select-all">
                              {videoSrc}
                            </span>
                            <button
                              onClick={() => copyToClipboard(videoSrc)}
                              className="p-1 rounded text-gray-500 hover:text-cyan-400 hover:bg-gray-800 transition"
                              title="Copy URL"
                            >
                              <Copy className="w-3 h-3" />
                            </button>
                          </div>
                        </td>
                        <td className="py-3 px-3 text-right">
                          <button
                            onClick={() =>
                              setPreviewVideo({
                                src: videoSrc,
                                title: `${subfolder}/${filename}`,
                                isDeepfake: row.is_deepfake,
                              })
                            }
                            className="px-3 py-1 rounded-lg bg-cyan-600/20 hover:bg-cyan-600 hover:text-white text-cyan-300 text-[11px] font-semibold transition inline-flex items-center space-x-1.5"
                          >
                            <Play className="w-3 h-3" />
                            <span>Preview</span>
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Parquet Partitions */}
      {activeTab === 'parquet' && (
        <div className="bg-[#111827] border border-gray-800 rounded-2xl shadow-xl p-6 space-y-4">
          <div>
            <h2 className="text-sm font-bold text-gray-200">
              Parquet File Partition Registry (Endpoint 3)
            </h2>
            <p className="text-xs text-gray-400">
              Available parquet URLs as exposed by <code className="text-cyan-400">/parquet/default/train</code>.
            </p>
          </div>

          <div className="space-y-3">
            {parquetFiles.map((url, idx) => (
              <div
                key={idx}
                className="p-4 rounded-xl bg-gray-900 border border-gray-800 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs font-mono"
              >
                <div>
                  <div className="flex items-center space-x-2 text-cyan-400 mb-1">
                    <FileCode2 className="w-4 h-4" />
                    <span className="font-bold">Partition #{idx} (0.parquet)</span>
                  </div>
                  <span className="text-gray-300 break-all select-all block text-[11px]">
                    {url}
                  </span>
                </div>

                <div className="flex items-center space-x-2 self-start md:self-auto">
                  <button
                    onClick={() => copyToClipboard(url)}
                    className="px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 font-medium transition flex items-center space-x-1.5"
                  >
                    <Copy className="w-3.5 h-3.5 text-cyan-400" />
                    <span>{copiedUrl === url ? 'Copied' : 'Copy URL'}</span>
                  </button>
                  <a
                    href={url}
                    target="_blank"
                    rel="noreferrer"
                    className="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-medium transition flex items-center space-x-1.5"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    <span>Inspect</span>
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 3: Splits & Schema */}
      {activeTab === 'splits' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Splits Card */}
          <div className="bg-[#111827] border border-gray-800 rounded-2xl shadow-xl p-6 space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-300 flex items-center space-x-2">
              <Layers className="w-4 h-4 text-cyan-400" />
              <span>Available Dataset Splits (Endpoint 1)</span>
            </h3>

            <div className="space-y-2">
              {splits.map((s, idx) => (
                <div key={idx} className="p-3.5 rounded-xl bg-gray-900 border border-gray-800 text-xs font-mono space-y-1">
                  <div className="flex justify-between items-center">
                    <span className="text-cyan-400 font-bold">Split: {s.split}</span>
                    <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[10px]">
                      READY
                    </span>
                  </div>
                  <p className="text-gray-400 text-[11px]">Dataset: {s.dataset}</p>
                  <p className="text-gray-500 text-[10px]">Configuration: {s.config}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Schema Card */}
          <div className="bg-[#111827] border border-gray-800 rounded-2xl shadow-xl p-6 space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-300 flex items-center space-x-2">
              <FileCode2 className="w-4 h-4 text-indigo-400" />
              <span>Feature Schema Representation</span>
            </h3>

            <div className="bg-gray-950 p-4 rounded-xl border border-gray-800 font-mono text-xs overflow-x-auto text-gray-300">
              <pre className="text-[11px] text-cyan-300">
{JSON.stringify(metadata?.features_schema || [
  { name: "video", type: { _type: "Video" } },
  { name: "label", type: { _type: "ClassLabel", names: ["deepfake", "video"] } }
], null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Architecture */}
      {activeTab === 'architecture' && (
        <div className="bg-[#111827] border border-gray-800 rounded-2xl shadow-xl p-6 space-y-4">
          <h2 className="text-sm font-bold text-gray-200">
            Phase 3 API Integration Architecture & Guardrails
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div className="p-4 rounded-xl bg-gray-900 border border-gray-800 space-y-2">
              <span className="text-cyan-400 font-bold uppercase text-[10px]">Zero Storage Overhead</span>
              <p className="text-gray-400">
                Data is consumed dynamically via Hugging Face REST APIs. No multi-gigabyte video datasets are downloaded or stored locally.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-gray-900 border border-gray-800 space-y-2">
              <span className="text-indigo-400 font-bold uppercase text-[10px]">Rate-Limit Caching</span>
              <p className="text-gray-400">
                In-memory TTL cache (300s) + PostgreSQL metadata persistence protects against Hugging Face rate limit saturation (HTTP 429).
              </p>
            </div>

            <div className="p-4 rounded-xl bg-gray-900 border border-gray-800 space-y-2">
              <span className="text-purple-400 font-bold uppercase text-[10px]">Phase 4 Readiness</span>
              <p className="text-gray-400">
                Benchmark ground-truth labels (0 for deepfake, 1 for authentic) provide clean evaluation targets for Phase 4 pretrained neural backbones.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Live Video Preview Modal */}
      {previewVideo && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-gray-800 rounded-2xl max-w-2xl w-full overflow-hidden shadow-2xl animate-in fade-in duration-200">
            <div className="p-4 border-b border-gray-800 flex items-center justify-between bg-gray-900/60">
              <div className="flex items-center space-x-2">
                {previewVideo.isDeepfake ? (
                  <ShieldAlert className="w-4 h-4 text-red-400" />
                ) : (
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                )}
                <span className="text-xs font-bold text-gray-200 font-mono">
                  {previewVideo.title}
                </span>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                  previewVideo.isDeepfake ? 'bg-red-500/20 text-red-300' : 'bg-emerald-500/20 text-emerald-300'
                }`}>
                  {previewVideo.isDeepfake ? 'Ground-Truth Deepfake' : 'Ground-Truth Authentic'}
                </span>
              </div>
              <button
                onClick={() => setPreviewVideo(null)}
                className="p-1 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-gray-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="relative aspect-video bg-black flex items-center justify-center">
              <video
                controls
                autoPlay
                src={previewVideo.src}
                className="w-full h-full object-contain"
              />
            </div>

            <div className="p-4 bg-gray-900/60 flex items-center justify-between text-xs font-mono">
              <span className="text-gray-500 truncate max-w-md">{previewVideo.src}</span>
              <button
                onClick={() => copyToClipboard(previewVideo.src)}
                className="text-cyan-400 hover:text-cyan-300 flex items-center space-x-1"
              >
                <Copy className="w-3.5 h-3.5" />
                <span>Copy CDN Link</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

