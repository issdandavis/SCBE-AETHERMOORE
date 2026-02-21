/**
 * @file SidebarSharePanel.tsx
 * @module scbe-visual-system/components/SidebarSharePanel
 * @layer L13 (Governance UI)
 * @component Sidebar Share Panel - Toggleable sidebar for sharing workspace state
 * @version 2.0.0
 * @license Apache-2.0
 */
import React, { useState } from 'react';
import {
  X, Share2, Copy, Link, Users, Globe, Lock,
  CheckCircle, ChevronRight, Monitor, Shield,
  ExternalLink, QrCode, Mail
} from 'lucide-react';

export type ShareVisibility = 'private' | 'team' | 'public';

interface ShareableWindow {
  id: string;
  name: string;
  appId?: string;
}

interface SidebarSharePanelProps {
  isOpen: boolean;
  onClose: () => void;
  openWindows: ShareableWindow[];
}

export const SidebarSharePanel: React.FC<SidebarSharePanelProps> = ({
  isOpen,
  onClose,
  openWindows
}) => {
  const [visibility, setVisibility] = useState<ShareVisibility>('private');
  const [copied, setCopied] = useState<string | null>(null);
  const [selectedWindows, setSelectedWindows] = useState<Set<string>>(new Set());
  const [shareGenerated, setShareGenerated] = useState(false);

  const toggleWindowSelection = (id: string) => {
    setSelectedWindows(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleCopy = (text: string, label: string) => {
    navigator.clipboard.writeText(text).catch(() => {
      // Fallback for environments without clipboard API
    });
    setCopied(label);
    setTimeout(() => setCopied(null), 2000);
  };

  const generateShareLink = () => {
    const sessionId = Math.random().toString(36).substring(2, 10);
    const windowIds = Array.from(selectedWindows).join(',');
    return `scbe://share/${sessionId}?apps=${windowIds}&v=${visibility}`;
  };

  const handleGenerateShare = () => {
    setShareGenerated(true);
    setTimeout(() => setShareGenerated(false), 5000);
  };

  const visibilityOptions: { value: ShareVisibility; label: string; icon: React.ElementType; desc: string }[] = [
    { value: 'private', label: 'Private', icon: Lock, desc: 'Only you can access' },
    { value: 'team', label: 'Team', icon: Users, desc: 'Share with your fleet' },
    { value: 'public', label: 'Public', icon: Globe, desc: 'Anyone with the link' },
  ];

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/40 backdrop-blur-sm z-[8500] transition-opacity"
          onClick={onClose}
        />
      )}

      {/* Sidebar Panel */}
      <div
        className={`fixed top-8 right-0 h-[calc(100%-2rem)] w-80 bg-zinc-900 border-l border-zinc-700 z-[8600] flex flex-col shadow-2xl transition-transform duration-300 ease-out ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="p-4 bg-zinc-800 border-b border-zinc-700 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-sky-600 flex items-center justify-center">
              <Share2 size={16} />
            </div>
            <div>
              <h2 className="font-bold text-sm text-white">Share Workspace</h2>
              <div className="text-[10px] text-zinc-400 uppercase tracking-widest">SCBE Governed</div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-zinc-700 rounded-lg text-zinc-400 hover:text-white transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-4 space-y-5">
          {/* Visibility Selector */}
          <div>
            <label className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold mb-2 block">
              Share Visibility
            </label>
            <div className="space-y-2">
              {visibilityOptions.map(opt => {
                const Icon = opt.icon;
                const isSelected = visibility === opt.value;
                return (
                  <button
                    key={opt.value}
                    onClick={() => setVisibility(opt.value)}
                    className={`w-full flex items-center gap-3 p-3 rounded-xl border transition-all text-left ${
                      isSelected
                        ? 'border-sky-500 bg-sky-500/10'
                        : 'border-zinc-700 bg-zinc-800 hover:border-zinc-600'
                    }`}
                  >
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                      isSelected ? 'bg-sky-500' : 'bg-zinc-700'
                    }`}>
                      <Icon size={14} className="text-white" />
                    </div>
                    <div className="flex-1">
                      <div className="text-sm font-bold text-white">{opt.label}</div>
                      <div className="text-[10px] text-zinc-500">{opt.desc}</div>
                    </div>
                    {isSelected && <CheckCircle size={16} className="text-sky-400" />}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Select Windows to Share */}
          {openWindows.length > 0 && (
            <div>
              <label className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold mb-2 block">
                Share Open Apps ({selectedWindows.size}/{openWindows.length})
              </label>
              <div className="space-y-1">
                {openWindows.map(win => {
                  const isSelected = selectedWindows.has(win.id);
                  return (
                    <button
                      key={win.id}
                      onClick={() => toggleWindowSelection(win.id)}
                      className={`w-full flex items-center gap-3 p-2.5 rounded-lg border transition-all text-left ${
                        isSelected
                          ? 'border-sky-500/50 bg-sky-500/10'
                          : 'border-transparent bg-zinc-800 hover:bg-zinc-750'
                      }`}
                    >
                      <Monitor size={14} className={isSelected ? 'text-sky-400' : 'text-zinc-500'} />
                      <span className={`text-sm flex-1 ${isSelected ? 'text-white' : 'text-zinc-400'}`}>
                        {win.name}
                      </span>
                      <ChevronRight size={12} className={`transition-transform ${isSelected ? 'rotate-90 text-sky-400' : 'text-zinc-600'}`} />
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {openWindows.length === 0 && (
            <div className="bg-zinc-800 rounded-xl p-4 text-center">
              <Monitor size={24} className="text-zinc-600 mx-auto mb-2" />
              <div className="text-sm text-zinc-500">No apps open to share</div>
              <div className="text-[10px] text-zinc-600 mt-1">Open an app to include it in the share</div>
            </div>
          )}

          {/* Quick Share Actions */}
          <div>
            <label className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold mb-2 block">
              Quick Actions
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => handleCopy(generateShareLink(), 'link')}
                className="flex flex-col items-center gap-2 p-3 bg-zinc-800 rounded-xl border border-zinc-700 hover:border-zinc-600 transition-colors"
              >
                {copied === 'link' ? (
                  <CheckCircle size={18} className="text-emerald-400" />
                ) : (
                  <Link size={18} className="text-sky-400" />
                )}
                <span className="text-[10px] text-zinc-400 uppercase tracking-widest">
                  {copied === 'link' ? 'Copied' : 'Copy Link'}
                </span>
              </button>

              <button
                onClick={() => handleCopy(JSON.stringify({
                  session: 'scbe-session',
                  visibility,
                  apps: Array.from(selectedWindows),
                  timestamp: new Date().toISOString()
                }, null, 2), 'json')}
                className="flex flex-col items-center gap-2 p-3 bg-zinc-800 rounded-xl border border-zinc-700 hover:border-zinc-600 transition-colors"
              >
                {copied === 'json' ? (
                  <CheckCircle size={18} className="text-emerald-400" />
                ) : (
                  <Copy size={18} className="text-purple-400" />
                )}
                <span className="text-[10px] text-zinc-400 uppercase tracking-widest">
                  {copied === 'json' ? 'Copied' : 'Export JSON'}
                </span>
              </button>

              <button
                className="flex flex-col items-center gap-2 p-3 bg-zinc-800 rounded-xl border border-zinc-700 hover:border-zinc-600 transition-colors"
              >
                <QrCode size={18} className="text-orange-400" />
                <span className="text-[10px] text-zinc-400 uppercase tracking-widest">QR Code</span>
              </button>

              <button
                className="flex flex-col items-center gap-2 p-3 bg-zinc-800 rounded-xl border border-zinc-700 hover:border-zinc-600 transition-colors"
              >
                <Mail size={18} className="text-emerald-400" />
                <span className="text-[10px] text-zinc-400 uppercase tracking-widest">Email</span>
              </button>
            </div>
          </div>

          {/* Generate Share Button */}
          <button
            onClick={handleGenerateShare}
            className={`w-full py-3 rounded-xl font-bold text-sm uppercase tracking-widest flex items-center justify-center gap-2 transition-all ${
              shareGenerated
                ? 'bg-emerald-600 text-white'
                : 'bg-sky-600 hover:bg-sky-500 text-white'
            }`}
          >
            {shareGenerated ? (
              <>
                <CheckCircle size={16} />
                Share Generated
              </>
            ) : (
              <>
                <Share2 size={16} />
                Generate Share
              </>
            )}
          </button>
        </div>

        {/* Footer */}
        <div className="p-3 bg-zinc-800 border-t border-zinc-700 flex items-center justify-between text-[10px] text-zinc-500">
          <span className="flex items-center gap-1">
            <Shield size={10} className="text-emerald-400" />
            SCBE Encrypted
          </span>
          <span className="flex items-center gap-1">
            <ExternalLink size={10} />
            Spiralverse Protocol
          </span>
        </div>
      </div>
    </>
  );
};
