import React, { useState, useEffect } from 'react';
import { Cpu, HardDrive, Wifi, Shield, CheckCircle } from 'lucide-react';

interface BootScreenProps {
  onComplete: () => void;
}

const bootMessages = [
  { icon: <Cpu size={14} />, text: 'Preparing tool bridge...', delay: 200 },
  { icon: <HardDrive size={14} />, text: 'Loading local desktop state...', delay: 400 },
  { icon: <Shield size={14} />, text: 'Checking governed action surfaces...', delay: 200 },
  { icon: <Wifi size={14} />, text: 'Connecting local bridge endpoints...', delay: 300 },
  { icon: <CheckCircle size={14} />, text: 'Opening real tool surfaces...', delay: 600 },
  { icon: <CheckCircle size={14} />, text: 'Starting SCBE desktop...', delay: 400 },
];

export default function BootScreen({ onComplete }: BootScreenProps) {
  const [progress, setProgress] = useState(0);
  const [visibleMessages, setVisibleMessages] = useState<number[]>([]);

  useEffect(() => {
    let totalDelay = 0;
    bootMessages.forEach((msg, idx) => {
      totalDelay += msg.delay;
      setTimeout(() => {
        setVisibleMessages((prev) => [...prev, idx]);
        setProgress(((idx + 1) / bootMessages.length) * 100);
      }, totalDelay);
    });

    setTimeout(() => {
      onComplete();
    }, totalDelay + 500);

    return () => {
      /* cleanup */
    };
  }, [onComplete]);

  return (
    <div className="fixed inset-0 z-[100000] bg-[#060e18] flex flex-col items-center justify-center">
      {/* Logo */}
      <div className="mb-12 flex flex-col items-center">
        <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-600 via-blue-500 to-cyan-400 flex items-center justify-center shadow-2xl shadow-blue-500/20 mb-6">
          <svg
            width="40"
            height="40"
            viewBox="0 0 24 24"
            fill="none"
            stroke="white"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <rect x="3" y="3" width="7" height="7" rx="1" />
            <rect x="14" y="3" width="7" height="7" rx="1" />
            <rect x="3" y="14" width="7" height="7" rx="1" />
            <rect x="14" y="14" width="7" height="7" rx="1" />
          </svg>
        </div>
        <h1 className="text-3xl font-bold text-blue-100 tracking-tight">SCBE Tool Desktop</h1>
        <p className="text-sm text-blue-400/50 mt-1">
          Local bridge for tools, receipts, and screens
        </p>
      </div>

      {/* Boot Messages */}
      <div className="w-80 space-y-2 mb-8">
        {bootMessages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex items-center gap-3 text-sm transition-all duration-300 ${
              visibleMessages.includes(idx)
                ? 'opacity-100 translate-x-0'
                : 'opacity-0 -translate-x-4'
            }`}
          >
            <span className={visibleMessages.includes(idx) ? 'text-blue-400' : 'text-transparent'}>
              {visibleMessages.includes(idx) ? msg.icon : <CheckCircle size={14} />}
            </span>
            <span
              className={visibleMessages.includes(idx) ? 'text-blue-200/70' : 'text-transparent'}
            >
              {msg.text}
            </span>
          </div>
        ))}
      </div>

      {/* Progress Bar */}
      <div className="w-80 h-1 bg-blue-500/10 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-blue-600 to-cyan-400 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>
      <div className="text-xs text-blue-400/30 mt-3">{Math.round(progress)}%</div>
    </div>
  );
}
