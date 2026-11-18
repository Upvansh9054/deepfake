import React from 'react';
import { ShieldCheck, ShieldAlert, AlertTriangle, HelpCircle } from 'lucide-react';

interface ThreatBadgeProps {
  verdict: string;
  size?: 'sm' | 'md' | 'lg';
}

export const ThreatBadge: React.FC<ThreatBadgeProps> = ({ verdict, size = 'md' }) => {
  const v = verdict.toLowerCase();

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5 space-x-1',
    md: 'text-xs px-2.5 py-1 space-x-1.5',
    lg: 'text-sm px-3.5 py-1.5 space-x-2 font-semibold',
  };

  const iconSizes = {
    sm: 'w-3 h-3',
    md: 'w-3.5 h-3.5',
    lg: 'w-4 h-4',
  };

  if (v === 'manipulated') {
    return (
      <span className={`inline-flex items-center rounded-md font-medium bg-red-500/10 text-red-400 border border-red-500/30 uppercase tracking-wider ${sizeClasses[size]}`}>
        <ShieldAlert className={`${iconSizes[size]} text-red-400`} />
        <span>Manipulated (Deepfake)</span>
      </span>
    );
  }

  if (v === 'suspicious') {
    return (
      <span className={`inline-flex items-center rounded-md font-medium bg-amber-500/10 text-amber-400 border border-amber-500/30 uppercase tracking-wider ${sizeClasses[size]}`}>
        <AlertTriangle className={`${iconSizes[size]} text-amber-400`} />
        <span>Suspicious Anomaly</span>
      </span>
    );
  }

  if (v === 'authentic') {
    return (
      <span className={`inline-flex items-center rounded-md font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 uppercase tracking-wider ${sizeClasses[size]}`}>
        <ShieldCheck className={`${iconSizes[size]} text-emerald-400`} />
        <span>Authentic Organic</span>
      </span>
    );
  }

  return (
    <span className={`inline-flex items-center rounded-md font-medium bg-gray-800 text-gray-400 border border-gray-700 uppercase tracking-wider ${sizeClasses[size]}`}>
      <HelpCircle className={`${iconSizes[size]} text-gray-400`} />
      <span>{verdict}</span>
    </span>
  );
};

