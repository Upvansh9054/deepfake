import React, { useState, useEffect } from 'react';
import { Shield, Bell, LogOut, CheckCircle2, AlertTriangle, ShieldAlert, Menu, X, Sun, Moon } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { alertsApi } from '../services/api';

interface NavbarProps {
  onToggleMobileMenu: () => void;
  isMobileMenuOpen: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({ onToggleMobileMenu, isMobileMenuOpen }) => {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [alerts, setAlerts] = useState<any[]>([]);
  const [showAlertDropdown, setShowAlertDropdown] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  const fetchAlerts = async () => {
    try {
      const data = await alertsApi.list();
      setAlerts(data);
      setUnreadCount(data.filter((a) => !a.is_read).length);
    } catch {
      // Silently handle if not logged in
    }
  };

  useEffect(() => {
    if (user) {
      fetchAlerts();
      const interval = setInterval(fetchAlerts, 15000);
      return () => clearInterval(interval);
    }
  }, [user]);

  const handleMarkAllRead = async () => {
    try {
      await alertsApi.markAllRead();
      setUnreadCount(0);
      setAlerts((prev) => prev.map((a) => ({ ...a, is_read: true })));
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <header className="border-b border-gray-800 bg-[#0F172A]/90 backdrop-blur px-4 md:px-6 py-3.5 flex items-center justify-between sticky top-0 z-40">
      <div className="flex items-center space-x-3">
        {/* Mobile menu toggle */}
        <button
          onClick={onToggleMobileMenu}
          className="md:hidden p-2 text-gray-400 hover:text-gray-200 rounded-lg hover:bg-gray-800"
        >
          {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>

        <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
          <Shield className="w-5 h-5 animate-pulse" />
        </div>
        <div>
          <span className="text-base font-bold tracking-tight bg-gradient-to-r from-cyan-400 via-sky-300 to-indigo-400 bg-clip-text text-transparent">
            Deepfake Shield
          </span>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        {/* Threat Alerts Dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowAlertDropdown(!showAlertDropdown)}
            className="relative p-2 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-gray-800 transition"
            title="Threat Notifications"
          >
            <Bell className="w-5 h-5" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 w-4 h-4 bg-red-500 text-white rounded-full text-[10px] font-bold flex items-center justify-center animate-pulse">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {showAlertDropdown && (
            <div className="absolute right-0 mt-2 w-80 md:w-96 bg-[#111827] border border-gray-800 rounded-xl shadow-2xl z-50 overflow-hidden">
              <div className="p-3.5 border-b border-gray-800 flex items-center justify-between bg-gray-900/50">
                <div className="flex items-center space-x-2">
                  <ShieldAlert className="w-4 h-4 text-cyan-400" />
                  <span className="text-xs font-bold uppercase tracking-wider text-gray-200">
                    Security Alerts
                  </span>
                </div>
                {unreadCount > 0 && (
                  <button
                    onClick={handleMarkAllRead}
                    className="text-[11px] text-cyan-400 hover:text-cyan-300 font-medium"
                  >
                    Mark all read
                  </button>
                )}
              </div>

              <div className="max-h-80 overflow-y-auto divide-y divide-gray-800/60">
                {alerts.length === 0 ? (
                  <div className="p-6 text-center text-gray-500 text-xs">
                    <CheckCircle2 className="w-8 h-8 mx-auto mb-2 text-gray-600" />
                    No active threat alerts
                  </div>
                ) : (
                  alerts.map((alert) => (
                    <div
                      key={alert.id}
                      className={`p-3 text-xs transition ${
                        alert.is_read ? 'bg-transparent text-gray-400' : 'bg-cyan-950/20 text-gray-200'
                      }`}
                    >
                      <div className="flex items-start space-x-2">
                        {alert.severity === 'CRITICAL' ? (
                          <ShieldAlert className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
                        )}
                        <div className="flex-1">
                          <p className="font-semibold text-gray-200">{alert.title}</p>
                          <p className="text-gray-400 text-[11px] mt-0.5 line-clamp-2">{alert.message}</p>
                          <span className="text-[10px] text-gray-500 mt-1 block font-mono">
                            {new Date(alert.created_at).toLocaleTimeString()}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* Light Blue / Dark Theme Switcher */}
        <button
          onClick={toggleTheme}
          className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all shadow-sm ${
            theme === 'light'
              ? 'bg-sky-50 text-sky-800 border-sky-300 hover:bg-sky-100 shadow-sky-100'
              : 'bg-gray-850 text-gray-200 border-gray-700 hover:bg-gray-800'
          }`}
          title={`Currently on ${theme === 'light' ? 'Light Blue' : 'Dark'} theme. Click to switch.`}
        >
          {theme === 'light' ? (
            <>
              <Sun className="w-4 h-4 text-amber-500 animate-spin-slow" />
              <span className="font-semibold tracking-wide">Light Blue</span>
            </>
          ) : (
            <>
              <Moon className="w-4 h-4 text-cyan-400" />
              <span className="font-semibold tracking-wide">Dark Mode</span>
            </>
          )}
        </button>

        {/* User Profile & Logout */}
        {user ? (
          <div className="flex items-center space-x-3 pl-3 border-l border-gray-800">
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-cyan-600 to-indigo-600 flex items-center justify-center text-xs font-bold text-white shadow">
              {user.full_name?.charAt(0) || 'U'}
            </div>
            <div className="hidden sm:block text-left text-xs">
              <p className="font-semibold text-gray-200 truncate max-w-[120px]">{user.full_name}</p>
            </div>
            <button
              onClick={logout}
              className="p-1.5 rounded-lg text-gray-400 hover:text-red-400 hover:bg-red-500/10 transition"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : null}
      </div>
    </header>
  );
};

