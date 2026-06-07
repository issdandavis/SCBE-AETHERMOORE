import React, { useState } from 'react';
import {
  Monitor,
  Moon,
  Sun,
  Palette,
  Volume2,
  Wifi,
  Shield,
  Info,
  Trash2,
  RotateCcw,
} from 'lucide-react';

export default function Settings() {
  const [activeTab, setActiveTab] = useState('appearance');
  const [theme, setTheme] = useState('dark');
  const [wallpaper, setWallpaper] = useState('default');
  const [volume, setVolume] = useState(75);
  const [brightness, setBrightness] = useState(100);

  const tabs = [
    { id: 'appearance', label: 'Appearance', icon: <Palette size={16} /> },
    { id: 'display', label: 'Display', icon: <Monitor size={16} /> },
    { id: 'sound', label: 'Sound', icon: <Volume2 size={16} /> },
    { id: 'network', label: 'Network', icon: <Wifi size={16} /> },
    { id: 'privacy', label: 'Privacy', icon: <Shield size={16} /> },
    { id: 'system', label: 'System', icon: <Info size={16} /> },
  ];

  const renderContent = () => {
    switch (activeTab) {
      case 'appearance':
        return (
          <div className="space-y-5">
            <div>
              <h3 className="text-sm text-blue-200 mb-3">Theme</h3>
              <div className="grid grid-cols-3 gap-3">
                {['dark', 'light', 'blue'].map((t) => (
                  <button
                    key={t}
                    onClick={() => setTheme(t)}
                    className={`p-3 rounded-xl border transition-all ${theme === t ? 'border-blue-500 bg-blue-500/15' : 'border-blue-500/10 hover:border-blue-500/25 bg-[#162032]'}`}
                  >
                    <div className="text-2xl mb-1">
                      {t === 'dark' ? (
                        <Moon size={20} className="mx-auto" />
                      ) : t === 'light' ? (
                        <Sun size={20} className="mx-auto" />
                      ) : (
                        <Palette size={20} className="mx-auto" />
                      )}
                    </div>
                    <span className="text-xs text-blue-200/60 capitalize">{t}</span>
                  </button>
                ))}
              </div>
            </div>
            <div>
              <h3 className="text-sm text-blue-200 mb-3">Wallpaper</h3>
              <div className="grid grid-cols-4 gap-2">
                {[
                  'default',
                  'ocean',
                  'forest',
                  'space',
                  'minimal',
                  'cyber',
                  'sunset',
                  'mountain',
                ].map((wp) => (
                  <button
                    key={wp}
                    onClick={() => setWallpaper(wp)}
                    className={`h-16 rounded-lg border transition-all ${wallpaper === wp ? 'border-blue-500 ring-1 ring-blue-500' : 'border-blue-500/10 hover:border-blue-500/30'}`}
                    style={{
                      background:
                        wp === 'default'
                          ? 'linear-gradient(135deg, #0c1929, #132744)'
                          : wp === 'ocean'
                            ? 'linear-gradient(135deg, #001a33, #004d7a)'
                            : wp === 'forest'
                              ? 'linear-gradient(135deg, #0a1f0a, #1a3a1a)'
                              : wp === 'space'
                                ? 'linear-gradient(135deg, #0a001a, #1a0033)'
                                : wp === 'minimal'
                                  ? '#0d1926'
                                  : wp === 'cyber'
                                    ? 'linear-gradient(135deg, #1a001a, #330066)'
                                    : wp === 'sunset'
                                      ? 'linear-gradient(135deg, #331a00, #663300)'
                                      : 'linear-gradient(135deg, #1a2332, #2d3a4a)',
                    }}
                  />
                ))}
              </div>
            </div>
          </div>
        );
      case 'display':
        return (
          <div className="space-y-5">
            <div>
              <h3 className="text-sm text-blue-200 mb-2">Brightness</h3>
              <input
                type="range"
                min="20"
                max="100"
                value={brightness}
                onChange={(e) => setBrightness(Number(e.target.value))}
                className="w-full accent-blue-500"
              />
              <div className="text-xs text-blue-400/40 mt-1">{brightness}%</div>
            </div>
            <div>
              <h3 className="text-sm text-blue-200 mb-2">Resolution</h3>
              <div className="flex gap-2">
                {['1920x1080', '2560x1440', '3840x2160'].map((r) => (
                  <button
                    key={r}
                    className="px-3 py-1.5 rounded-lg text-xs bg-[#162032] border border-blue-500/10 text-blue-200/60 hover:border-blue-500/30 transition-colors"
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>
          </div>
        );
      case 'sound':
        return (
          <div className="space-y-5">
            <div>
              <h3 className="text-sm text-blue-200 mb-2">System Volume</h3>
              <input
                type="range"
                min="0"
                max="100"
                value={volume}
                onChange={(e) => setVolume(Number(e.target.value))}
                className="w-full accent-blue-500"
              />
              <div className="text-xs text-blue-400/40 mt-1">{volume}%</div>
            </div>
            <div className="space-y-2">
              {['Startup Sound', 'Notification Sound', 'Window Sound'].map((s) => (
                <div
                  key={s}
                  className="flex items-center justify-between py-2 border-b border-blue-500/5"
                >
                  <span className="text-xs text-blue-200/60">{s}</span>
                  <button className="w-10 h-5 rounded-full bg-blue-500/30 relative transition-colors">
                    <div className="absolute right-0.5 top-0.5 w-4 h-4 rounded-full bg-blue-400 shadow-sm" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        );
      case 'network':
        return (
          <div className="space-y-4">
            <div className="bg-[#162032] rounded-xl p-4 border border-blue-500/10">
              <div className="flex items-center gap-3 mb-3">
                <Wifi size={18} className="text-green-400" />
                <div>
                  <div className="text-sm text-blue-200">Wi-Fi Connected</div>
                  <div className="text-xs text-blue-400/40">LinuxOS-Network</div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <span className="text-blue-400/40">IP:</span>{' '}
                  <span className="text-blue-200/60">192.168.1.100</span>
                </div>
                <div>
                  <span className="text-blue-400/40">MAC:</span>{' '}
                  <span className="text-blue-200/60">00:1A:2B:3C:4D:5E</span>
                </div>
                <div>
                  <span className="text-blue-400/40">Speed:</span>{' '}
                  <span className="text-blue-200/60">1 Gbps</span>
                </div>
                <div>
                  <span className="text-blue-400/40">Signal:</span>{' '}
                  <span className="text-blue-200/60">Excellent</span>
                </div>
              </div>
            </div>
          </div>
        );
      case 'privacy':
        return (
          <div className="space-y-4">
            {['Location Services', 'Usage Analytics', 'Crash Reports', 'Automatic Updates'].map(
              (s) => (
                <div
                  key={s}
                  className="flex items-center justify-between py-3 border-b border-blue-500/5"
                >
                  <span className="text-xs text-blue-200/60">{s}</span>
                  <button className="w-10 h-5 rounded-full bg-blue-500/30 relative transition-colors">
                    <div className="absolute right-0.5 top-0.5 w-4 h-4 rounded-full bg-blue-400 shadow-sm" />
                  </button>
                </div>
              )
            )}
          </div>
        );
      case 'system':
        return (
          <div className="space-y-4">
            <div className="bg-[#162032] rounded-xl p-4 border border-blue-500/10">
              <h3 className="text-sm text-blue-200 mb-3">System Information</h3>
              <div className="space-y-2 text-xs">
                {[
                  ['OS', 'LinuxOS Web 1.0'],
                  ['Kernel', '5.15.0-generic'],
                  ['Architecture', 'x86_64'],
                  ['CPU', 'Virtual 8-Core Processor'],
                  ['Memory', '4 GB / 16 GB'],
                  ['Storage', '125 GB / 1 TB'],
                  ['Uptime', '3d 7h 22m'],
                ].map(([label, value]) => (
                  <div key={label} className="flex justify-between">
                    <span className="text-blue-400/40">{label}</span>
                    <span className="text-blue-200/60">{value}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="flex gap-2">
              <button className="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 text-xs transition-colors">
                <RotateCcw size={14} /> Restart
              </button>
              <button className="flex items-center gap-2 px-3 py-2 rounded-lg bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 text-xs transition-colors">
                <Trash2 size={14} /> Clear Data
              </button>
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="w-full h-full flex bg-[#0d1926]">
      <div className="w-44 border-r border-blue-500/10 bg-[#111d2e] p-2">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs transition-all ${activeTab === tab.id ? 'bg-blue-500/15 text-blue-200' : 'text-blue-300/40 hover:text-blue-200/70 hover:bg-blue-500/5'}`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>
      <div className="flex-1 p-5 overflow-y-auto">{renderContent()}</div>
    </div>
  );
}
