import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  History,
  Search,
  Filter,
  Mic,
  Video,
  Layers,
  FileCheck2,
  Trash2,
  ArrowRight,
  Download,
  AlertTriangle,
} from 'lucide-react';
import { scansApi } from '../services/api';
import { ThreatBadge } from '../components/ThreatBadge';

export const ScanHistoryPage: React.FC = () => {
  const [scans, setScans] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [mediaFilter, setMediaFilter] = useState<'all' | 'audio' | 'video' | 'multimodal'>('all');
  const [verdictFilter, setVerdictFilter] = useState<'all' | 'manipulated' | 'authentic'>('all');
  const [isLoading, setIsLoading] = useState(true);

  const fetchScans = async () => {
    setIsLoading(true);
    try {
      const params: any = { limit: 50 };
      if (search.trim()) params.search = search.trim();
      if (mediaFilter !== 'all') params.media_type = mediaFilter;
      if (verdictFilter !== 'all') params.verdict = verdictFilter;

      const data = await scansApi.list(params);
      setScans(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      console.error('Failed to load scan history', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchScans();
  }, [mediaFilter, verdictFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchScans();
  };

  const handleDelete = async (id: string, title: string) => {
    if (!window.confirm(`Are you sure you want to delete scan record "${title}"?`)) return;
    try {
      await scansApi.delete(id);
      setScans((prev) => prev.filter((s) => s.id !== id));
      setTotal((prev) => Math.max(0, prev - 1));
    } catch (err: any) {
      alert(`Deletion failed: ${err.message}`);
    }
  };

  const exportCSV = () => {
    if (scans.length === 0) return;
    const headers = ['ID', 'Title', 'File Name', 'Media Type', 'SHA256', 'Verdict', 'Risk Score', 'Created At'];
    const rows = scans.map((s) => [
      s.id,
      `"${s.title.replace(/"/g, '""')}"`,
      `"${s.file_name.replace(/"/g, '""')}"`,
      s.media_type,
      s.sha256_hash,
      s.result?.verdict || 'N/A',
      s.risk_report?.composite_risk_score ?? 0,
      s.created_at,
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `deepfake_shield_registry_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-cyan-400 text-xs font-semibold uppercase tracking-wider mb-1">
            <History className="w-4 h-4" />
            <span>Forensic Evidence Registry</span>
          </div>
          <h1 className="text-xl md:text-2xl font-bold text-gray-100">
            Forensic Scan History & Audit Trail
          </h1>
          <p className="text-xs text-gray-400 mt-1">
            Browse, inspect, and export cryptographically indexed audio and video deepfake scans.
          </p>
        </div>

        <button
          onClick={exportCSV}
          disabled={scans.length === 0}
          className="px-4 py-2 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs font-semibold transition flex items-center space-x-2 disabled:opacity-50"
        >
          <Download className="w-3.5 h-3.5 text-cyan-400" />
          <span>Export Registry CSV</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-xl bg-[#111827] border border-gray-800 flex flex-col md:flex-row gap-4 justify-between items-center shadow-lg">
        {/* Search */}
        <form onSubmit={handleSearchSubmit} className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-gray-500 absolute left-3 top-3 pointer-events-none" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search title, filename, SHA-256..."
            className="w-full bg-gray-900 border border-gray-700 rounded-xl pl-9 pr-4 py-2 text-xs text-gray-100 placeholder-gray-500 focus:outline-none focus:border-cyan-500"
          />
        </form>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto text-xs">
          {/* Media Type Tabs */}
          <div className="flex bg-gray-900 p-1 rounded-lg border border-gray-800">
            <button
              onClick={() => setMediaFilter('all')}
              className={`px-3 py-1 rounded-md transition ${mediaFilter === 'all' ? 'bg-cyan-600 text-white font-medium' : 'text-gray-400 hover:text-gray-200'}`}
            >
              All Types
            </button>
            <button
              onClick={() => setMediaFilter('audio')}
              className={`px-3 py-1 rounded-md transition flex items-center space-x-1 ${mediaFilter === 'audio' ? 'bg-cyan-600 text-white font-medium' : 'text-gray-400 hover:text-gray-200'}`}
            >
              <Mic className="w-3 h-3" />
              <span>Audio</span>
            </button>
            <button
              onClick={() => setMediaFilter('video')}
              className={`px-3 py-1 rounded-md transition flex items-center space-x-1 ${mediaFilter === 'video' ? 'bg-cyan-600 text-white font-medium' : 'text-gray-400 hover:text-gray-200'}`}
            >
              <Video className="w-3 h-3" />
              <span>Video</span>
            </button>
            <button
              onClick={() => setMediaFilter('multimodal')}
              className={`px-3 py-1 rounded-md transition flex items-center space-x-1 ${mediaFilter === 'multimodal' ? 'bg-purple-600 text-white font-medium' : 'text-gray-400 hover:text-gray-200'}`}
            >
              <Layers className="w-3 h-3" />
              <span>Multimodal</span>
            </button>
          </div>

          {/* Verdict Filter */}
          <div className="flex bg-gray-900 p-1 rounded-lg border border-gray-800">
            <button
              onClick={() => setVerdictFilter('all')}
              className={`px-3 py-1 rounded-md transition ${verdictFilter === 'all' ? 'bg-indigo-600 text-white font-medium' : 'text-gray-400 hover:text-gray-200'}`}
            >
              All Verdicts
            </button>
            <button
              onClick={() => setVerdictFilter('manipulated')}
              className={`px-3 py-1 rounded-md transition text-red-400 ${verdictFilter === 'manipulated' ? 'bg-red-600 text-white font-medium' : 'hover:text-red-300'}`}
            >
              Manipulated
            </button>
            <button
              onClick={() => setVerdictFilter('authentic')}
              className={`px-3 py-1 rounded-md transition text-emerald-400 ${verdictFilter === 'authentic' ? 'bg-emerald-600 text-white font-medium' : 'hover:text-emerald-300'}`}
            >
              Authentic
            </button>
          </div>
        </div>
      </div>

      {/* Main Scans Table */}
      <div className="bg-[#111827] border border-gray-800 rounded-2xl shadow-xl overflow-hidden">
        {isLoading ? (
          <div className="py-20 text-center space-y-3">
            <div className="w-8 h-8 border-2 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin mx-auto" />
            <p className="text-xs text-gray-500 font-mono">Loading forensic registry...</p>
          </div>
        ) : scans.length === 0 ? (
          <div className="py-20 text-center space-y-3 text-xs text-gray-500">
            <FileCheck2 className="w-10 h-10 mx-auto text-gray-600" />
            <p className="text-gray-300 font-semibold">No scans match your criteria</p>
            <p className="text-gray-500 max-w-sm mx-auto">
              Try adjusting your search query or upload a new audio or video file to analyze.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-gray-900/60 border-b border-gray-800 text-[10px] uppercase font-mono text-gray-400">
                <tr>
                  <th className="py-3.5 px-4 font-semibold">Scan Title & File</th>
                  <th className="py-3.5 px-4 font-semibold">Type</th>
                  <th className="py-3.5 px-4 font-semibold">Verdict</th>
                  <th className="py-3.5 px-4 font-semibold">Composite Risk</th>
                  <th className="py-3.5 px-4 font-semibold">Date Registered</th>
                  <th className="py-3.5 px-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60">
                {scans.map((scan) => {
                  const verdict = scan.result?.verdict || 'authentic';
                  const risk = scan.risk_report?.composite_risk_score ?? 0;
                  return (
                    <tr key={scan.id} className="hover:bg-gray-900/40 transition">
                      <td className="py-3.5 px-4">
                        <Link
                          to={`/scans/${scan.id}`}
                          className="font-semibold text-gray-200 hover:text-cyan-400 transition block truncate max-w-xs"
                        >
                          {scan.title}
                        </Link>
                        <span className="text-[10px] text-gray-500 font-mono truncate max-w-xs block mt-0.5">
                          {scan.file_name} • {(scan.file_size_bytes / (1024 * 1024)).toFixed(2)} MB
                        </span>
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="inline-flex items-center space-x-1 uppercase font-mono text-[10px] text-gray-400">
                          {scan.media_type === 'audio' ? (
                            <Mic className="w-3.5 h-3.5 text-cyan-400" />
                          ) : scan.media_type === 'multimodal' ? (
                            <Layers className="w-3.5 h-3.5 text-purple-400" />
                          ) : (
                            <Video className="w-3.5 h-3.5 text-indigo-400" />
                          )}
                          <span className={scan.media_type === 'multimodal' ? 'text-purple-400 font-semibold' : ''}>
                            {scan.media_type}
                          </span>
                        </span>
                      </td>
                      <td className="py-3.5 px-4">
                        <ThreatBadge verdict={verdict} size="sm" />
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="flex items-center space-x-2">
                          <span
                            className={`font-mono font-bold ${
                              risk > 70
                                ? 'text-red-400'
                                : risk > 40
                                ? 'text-amber-400'
                                : 'text-emerald-400'
                            }`}
                          >
                            {risk}%
                          </span>
                          <div className="w-20 bg-gray-800 h-1.5 rounded-full overflow-hidden">
                            <div
                              className={`h-full ${
                                risk > 70
                                  ? 'bg-red-500'
                                  : risk > 40
                                  ? 'bg-amber-500'
                                  : 'bg-emerald-500'
                              }`}
                              style={{ width: `${risk}%` }}
                            ></div>
                          </div>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-gray-400 font-mono text-[11px]">
                        {new Date(scan.created_at).toLocaleDateString()} {new Date(scan.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <div className="inline-flex items-center space-x-2">
                          <Link
                            to={`/scans/${scan.id}`}
                            className="px-2.5 py-1 rounded-lg bg-gray-800 hover:bg-cyan-600 hover:text-white text-cyan-400 text-[11px] font-medium transition"
                          >
                            View Report
                          </Link>
                          <button
                            onClick={() => handleDelete(scan.id, scan.title)}
                            className="p-1 rounded text-gray-500 hover:text-red-400 hover:bg-red-500/10 transition"
                            title="Delete Record"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

