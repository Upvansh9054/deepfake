import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Shield, Lock, Mail, User, ArrowRight, AlertCircle, Globe, Check, Settings } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { getRawBackendUrl, setCustomBackendUrl } from '../services/api';

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('user');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [customBackend, setCustomBackend] = useState(getRawBackendUrl());
  const [showBackendConfig, setShowBackendConfig] = useState(false);
  const [backendSavedMsg, setBackendSavedMsg] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password.length < 6) {
      setError('Password must be at least 6 characters long.');
      return;
    }

    setIsLoading(true);
    try {
      await register(email, password, fullName, role);
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0B0F17] flex flex-col justify-center items-center p-4">
      <div className="max-w-md w-full">
        {/* Brand Header */}
        <div className="text-center mb-8">
          <div className="inline-flex p-3 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 mb-4 shadow-lg shadow-cyan-500/10">
            <Shield className="w-10 h-10 animate-pulse" />
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight bg-gradient-to-r from-cyan-400 via-sky-300 to-indigo-400 bg-clip-text text-transparent">
            Deepfake Shield
          </h1>
          <p className="text-xs text-gray-400 mt-1">Get started with Deepfake Shield</p>
        </div>

        {/* Register Card */}
        <div className="bg-[#111827] border border-gray-800 rounded-2xl p-6 md:p-8 shadow-2xl backdrop-blur">
          <h2 className="text-lg font-bold text-gray-100 mb-1">Create Account</h2>
          <p className="text-xs text-gray-400 mb-6">Fill in your details to create an account.</p>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-950/40 border border-red-800/50 flex items-start space-x-2.5 text-xs text-red-300">
              <AlertCircle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {(error?.includes('405') || showBackendConfig || !customBackend) && (
            <div className="mb-5 p-3.5 rounded-xl bg-gray-900/90 border border-cyan-500/30 text-xs shadow-inner">
              <div className="flex items-center justify-between text-cyan-300 font-semibold mb-1.5">
                <span className="flex items-center gap-1.5">
                  <Globe className="w-3.5 h-3.5 text-cyan-400" />
                  Render Backend URL
                </span>
                {backendSavedMsg && (
                  <span className="text-emerald-400 text-[11px] font-medium flex items-center gap-1">
                    <Check className="w-3 h-3" /> Connected!
                  </span>
                )}
              </div>
              <p className="text-[11px] text-gray-400 mb-2 leading-relaxed">
                Paste your live Render backend URL (e.g. <span className="text-cyan-300">https://deepfake-xxxx.onrender.com</span>):
              </p>
              <div className="flex gap-2">
                <input
                  type="url"
                  value={customBackend}
                  onChange={(e) => setCustomBackend(e.target.value)}
                  placeholder="https://deepfake-xxxx.onrender.com"
                  className="flex-1 bg-gray-950 border border-gray-700 rounded-lg px-2.5 py-1.5 text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-cyan-500"
                />
                <button
                  type="button"
                  onClick={() => {
                    setCustomBackendUrl(customBackend);
                    setBackendSavedMsg(true);
                    setError(null);
                    setTimeout(() => setBackendSavedMsg(false), 3000);
                  }}
                  className="bg-cyan-600 hover:bg-cyan-500 text-white font-semibold px-3 py-1.5 rounded-lg text-xs transition whitespace-nowrap shadow"
                >
                  Save & Connect
                </button>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1.5">
                Full Name
              </label>
              <div className="relative">
                <User className="w-4 h-4 text-gray-500 absolute left-3 top-3 pointer-events-none" />
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Your Full Name"
                  className="w-full bg-gray-900 border border-gray-700/80 rounded-xl pl-9 pr-4 py-2.5 text-xs text-gray-100 placeholder-gray-600 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1.5">
                Email
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-gray-500 absolute left-3 top-3 pointer-events-none" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@example.com"
                  className="w-full bg-gray-900 border border-gray-700/80 rounded-xl pl-9 pr-4 py-2.5 text-xs text-gray-100 placeholder-gray-600 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-gray-500 absolute left-3 top-3 pointer-events-none" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Minimum 6 characters"
                  className="w-full bg-gray-900 border border-gray-700/80 rounded-xl pl-9 pr-4 py-2.5 text-xs text-gray-100 placeholder-gray-600 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full mt-2 py-2.5 px-4 rounded-xl bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white text-xs font-bold transition flex items-center justify-center space-x-2 shadow-lg shadow-cyan-600/20 disabled:opacity-50"
            >
              {isLoading ? (
                <span>Registering Account...</span>
              ) : (
                <>
                  <span>Create Account</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          <div className="mt-6 pt-5 border-t border-gray-800 text-center text-xs text-gray-400">
            Already have an account?{' '}
            <Link to="/login" className="text-cyan-400 hover:text-cyan-300 font-semibold">
              Sign In
            </Link>
          </div>

          <div className="mt-4 text-center">
            <button
              type="button"
              onClick={() => setShowBackendConfig(!showBackendConfig)}
              className="text-[11px] text-gray-500 hover:text-cyan-400 transition inline-flex items-center gap-1.5 mx-auto"
            >
              <Settings className="w-3 h-3" />
              <span>{customBackend ? `Server: ${customBackend}` : 'Configure Backend Server'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

