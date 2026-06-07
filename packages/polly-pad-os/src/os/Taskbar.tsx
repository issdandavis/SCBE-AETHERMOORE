import React, { useState, useEffect } from 'react';
import { useOS } from './OSStore';
import { AppWindow, Wifi, Volume2, Battery, ChevronUp, Bell, Power } from 'lucide-react';

export default function Taskbar() {
  const { windows, focusWindow, startMenuOpen, setStartMenuOpen, activeWindowId } = useOS();
  const [time, setTime] = useState(new Date());
  const [showSysTray, setShowSysTray] = useState(false);

  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  const visibleWindows = windows.filter((w) => !w.isMinimized);
  const taskbarWindows = windows;

  return (
    <div className="fixed bottom-0 left-0 right-0 h-12 bg-[#0a1625]/90 border-t border-blue-500/10 backdrop-blur-xl z-[9999] flex items-center px-2 gap-1">
      {/* Start Button */}
      <button
        onClick={() => setStartMenuOpen(!startMenuOpen)}
        className={`flex items-center gap-2 px-4 h-9 rounded-lg transition-all duration-200 ${
          startMenuOpen
            ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/25'
            : 'text-blue-200/70 hover:bg-blue-500/20 hover:text-blue-100'
        }`}
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <rect x="3" y="3" width="7" height="7" rx="1" />
          <rect x="14" y="3" width="7" height="7" rx="1" />
          <rect x="3" y="14" width="7" height="7" rx="1" />
          <rect x="14" y="14" width="7" height="7" rx="1" />
        </svg>
        <span className="text-sm font-medium">Start</span>
      </button>

      <div className="w-px h-6 bg-blue-500/10 mx-1" />

      {/* Taskbar Items */}
      <div className="flex-1 flex items-center gap-0.5 min-w-0 overflow-x-auto scrollbar-hide">
        {taskbarWindows.map((w) => {
          const isFocused = w.id === activeWindowId && !w.isMinimized;
          return (
            <button
              key={w.id}
              onClick={() => {
                if (w.isMinimized || !isFocused) {
                  focusWindow(w.id);
                } else {
                  // minimize if already focused
                }
              }}
              className={`flex items-center gap-2 px-3 h-9 rounded-lg transition-all duration-200 min-w-0 max-w-[180px] ${
                isFocused
                  ? 'bg-blue-500/25 text-blue-100 border border-blue-400/30'
                  : 'text-blue-200/60 hover:bg-blue-500/15 hover:text-blue-200 border border-transparent'
              }`}
            >
              <AppWindow size={16} className="flex-shrink-0 opacity-70" />
              <span className="text-xs truncate">{w.title}</span>
            </button>
          );
        })}
      </div>

      <div className="w-px h-6 bg-blue-500/10 mx-1" />

      {/* System Tray */}
      <div className="flex items-center gap-1 relative">
        <button
          onClick={() => setShowSysTray(!showSysTray)}
          className="p-1.5 rounded-lg text-blue-200/50 hover:bg-blue-500/20 hover:text-blue-200 transition-colors"
        >
          <ChevronUp size={14} />
        </button>

        <button className="p-1.5 rounded-lg text-blue-200/50 hover:bg-blue-500/20 hover:text-blue-200 transition-colors relative">
          <Bell size={16} />
          <span className="absolute top-0.5 right-0.5 w-2 h-2 bg-blue-500 rounded-full" />
        </button>

        <div className="flex items-center gap-2 px-2 h-9 rounded-lg text-blue-200/60 hover:bg-blue-500/10 transition-colors cursor-pointer">
          <Wifi size={14} />
          <Volume2 size={14} />
          <Battery size={14} />
          <div className="flex flex-col items-end ml-1">
            <span className="text-[11px] leading-tight">
              {time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
            <span className="text-[9px] leading-tight opacity-60">
              {time.toLocaleDateString([], { month: 'short', day: 'numeric' })}
            </span>
          </div>
        </div>

        <button className="p-1.5 rounded-lg text-red-400/50 hover:bg-red-500/20 hover:text-red-400 transition-colors ml-1">
          <Power size={14} />
        </button>

        {showSysTray && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setShowSysTray(false)} />
            <div className="absolute bottom-12 right-0 bg-[#162032]/95 border border-blue-500/20 rounded-lg shadow-2xl p-3 min-w-[200px] z-50 backdrop-blur-xl">
              <div className="text-sm text-blue-200/80 mb-2">System Tray</div>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs text-blue-200/60">
                  <span>Wi-Fi</span>
                  <span className="text-blue-400">Connected</span>
                </div>
                <div className="flex items-center justify-between text-xs text-blue-200/60">
                  <span>Volume</span>
                  <span className="text-blue-400">75%</span>
                </div>
                <div className="flex items-center justify-between text-xs text-blue-200/60">
                  <span>Battery</span>
                  <span className="text-green-400">92%</span>
                </div>
                <div className="flex items-center justify-between text-xs text-blue-200/60">
                  <span>CPU</span>
                  <span className="text-blue-400">12%</span>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
