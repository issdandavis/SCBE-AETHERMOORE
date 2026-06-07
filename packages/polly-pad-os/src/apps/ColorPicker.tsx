import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

export default function ColorPicker() {
  const [color, setColor] = useState('#60a5fa');
  const [copied, setCopied] = useState(false);

  const hexToRgb = (hex: string) => {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return isNaN(r) ? '0, 0, 0' : `${r}, ${g}, ${b}`;
  };

  const hexToHsl = (hex: string) => {
    let r = parseInt(hex.slice(1, 3), 16) / 255;
    let g = parseInt(hex.slice(3, 5), 16) / 255;
    let b = parseInt(hex.slice(5, 7), 16) / 255;
    const max = Math.max(r, g, b),
      min = Math.min(r, g, b);
    let h = 0,
      s = 0,
      l = (max + min) / 2;
    if (max !== min) {
      const d = max - min;
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      h =
        max === r
          ? ((g - b) / d + (g < b ? 6 : 0)) / 6
          : max === g
            ? ((b - r) / d + 2) / 6
            : ((r - g) / d + 4) / 6;
    }
    return isNaN(r)
      ? '0, 0%, 0%'
      : `${Math.round(h * 360)}, ${Math.round(s * 100)}%, ${Math.round(l * 100)}%`;
  };

  const copy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const presets = [
    '#ef4444',
    '#f97316',
    '#f59e0b',
    '#84cc16',
    '#22c55e',
    '#06b6d4',
    '#3b82f6',
    '#6366f1',
    '#8b5cf6',
    '#a855f7',
    '#ec4899',
    '#f43f5e',
    '#1e293b',
    '#64748b',
    '#94a3b8',
  ];

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 p-4 items-center">
      <div
        className="w-32 h-32 rounded-2xl shadow-2xl mb-4 border-2 border-white/10"
        style={{ background: color }}
      />
      <div className="flex items-center gap-2 mb-4">
        <input
          type="color"
          value={color}
          onChange={(e) => setColor(e.target.value)}
          className="w-10 h-10 rounded-lg cursor-pointer"
        />
        <input
          value={color}
          onChange={(e) => setColor(e.target.value)}
          className="bg-[#162032] border border-blue-500/15 rounded-lg px-3 py-1.5 text-sm font-mono outline-none focus:border-blue-500/30 w-28"
        />
        <button
          onClick={() => copy(color)}
          className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/50"
        >
          {copied ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
        </button>
      </div>
      <div className="space-y-2 w-full max-w-[280px]">
        {[
          ['HEX', color],
          ['RGB', `rgb(${hexToRgb(color)})`],
          ['HSL', `hsl(${hexToHsl(color)})`],
        ].map(([label, value]) => (
          <button
            key={label}
            onClick={() => copy(value)}
            className="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-[#162032] border border-blue-500/10 hover:border-blue-500/25 transition-colors"
          >
            <span className="text-xs text-blue-300/40">{label}</span>
            <span className="text-xs font-mono text-blue-200/60">{value}</span>
          </button>
        ))}
      </div>
      <div className="flex gap-1.5 mt-4 flex-wrap justify-center max-w-[280px]">
        {presets.map((c) => (
          <button
            key={c}
            onClick={() => setColor(c)}
            className="w-7 h-7 rounded-full border-2 border-transparent hover:scale-110 transition-transform"
            style={{ background: c }}
          />
        ))}
      </div>
    </div>
  );
}
