import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Mic,
  Video,
  Layers,
  Activity,
  History,
  Database,
  Zap,
  ChevronRight,
} from 'lucide-react';

interface SidebarProps {
  isOpen: boolean;
  onCloseMobile: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onCloseMobile }) => {
  const forensicNavItems = [
    { to: '/', label: 'Overview Dashboard', icon: LayoutDashboard },
    { to: '/audio-scanner', label: 'Audio Clone Scanner', icon: Mic },
    { to: '/video-scanner', label: 'Video Deepfake Scanner', icon: Video },
    { to: '/multimodal-scanner', label: 'Multimodal AI Scanner', icon: Layers },
    { to: '/realtime', label: 'Real-Time Monitor', icon: Activity },
  ];

  const registryNavItems = [
    { to: '/history', label: 'Forensic Scan History', icon: History },
    { to: '/datasets', label: 'HF Dataset Explorer', icon: Database },
  ];

  const sidebarClasses = `
    fixed md:static inset-y-0 left-0 z-30
    w-68 md:w-72 bg-[#0D131F] border-r border-gray-800/80
    flex flex-col justify-between
    transform transition-transform duration-300 ease-in-out
    shadow-xl md:shadow-none
    ${isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
  `;

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          onClick={onCloseMobile}
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-20 md:hidden"
        />
      )}

      <aside className={sidebarClasses}>
        <div className="flex-1 overflow-y-auto p-4 space-y-5">
          {/* Quick Threat Status Card */}
          <div className="p-4 rounded-2xl bg-gradient-to-br from-cyan-950/40 via-gray-900 to-indigo-950/30 border border-cyan-500/25 shadow-sm">
            <div className="flex items-center space-x-2 text-cyan-400 text-xs font-bold uppercase tracking-wider mb-1.5">
              <Zap className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
              <span>Shield Defense Active</span>
            </div>
            <p className="text-xs text-gray-400 leading-relaxed">
              Multimodal neural detectors monitoring for audio clones, face swaps & lip drift.
            </p>
          </div>

          {/* Forensic Detection Engines */}
          <nav className="space-y-1.5">
            <span className="px-3 text-xs font-mono uppercase tracking-wider text-gray-500 font-bold block mb-2">
              Forensic Engines
            </span>
            {forensicNavItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={onCloseMobile}
                  className={({ isActive }) =>
                    `group flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-medium transition-all duration-150 ${
                      isActive
                        ? 'sidebar-nav-active bg-cyan-500/15 text-cyan-400 border border-cyan-500/30 font-semibold shadow-sm'
                        : 'sidebar-nav-inactive text-gray-400 hover:text-cyan-300 hover:bg-cyan-500/10'
                    }`
                  }
                >
                  <div className="flex items-center space-x-3">
                    <Icon className="w-4 h-4 flex-shrink-0 transition-colors" />
                    <span>{item.label}</span>
                  </div>
                  <ChevronRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity text-cyan-400" />
                </NavLink>
              );
            })}
          </nav>

          {/* Intelligence & Configuration */}
          <nav className="space-y-1.5 pt-3 border-t border-gray-800/60">
            <span className="px-3 text-xs font-mono uppercase tracking-wider text-gray-500 font-bold block mb-2">
              Registry & Intel
            </span>
            {registryNavItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={onCloseMobile}
                  className={({ isActive }) =>
                    `group flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-medium transition-all duration-150 ${
                      isActive
                        ? 'sidebar-nav-active bg-cyan-500/15 text-cyan-400 border border-cyan-500/30 font-semibold shadow-sm'
                        : 'sidebar-nav-inactive text-gray-400 hover:text-cyan-300 hover:bg-cyan-500/10'
                    }`
                  }
                >
                  <div className="flex items-center space-x-3">
                    <Icon className="w-4 h-4 flex-shrink-0 transition-colors" />
                    <span>{item.label}</span>
                  </div>
                  <ChevronRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity text-cyan-400" />
                </NavLink>
              );
            })}
          </nav>
        </div>
      </aside>
    </>
  );
};
