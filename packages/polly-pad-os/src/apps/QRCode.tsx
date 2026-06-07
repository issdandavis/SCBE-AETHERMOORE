import React, { useState, useRef, useCallback, useEffect } from 'react';
import { QrCode, Copy, Check, Download, ExternalLink } from 'lucide-react';

// Simple QR code using Google Charts API (reliable, no library needed)
function generateQRUrl(text: string, size: number = 300): string {
  if (!text.trim()) return '';
  return `https://chart.googleapis.com/chart?cht=qr&chs=${size}x${size}&chld=H|0&chl=${encodeURIComponent(text)}`;
}

export default function QRCodeApp() {
  const [text, setText] = useState('https://linuxos.web');
  const [size, setSize] = useState(250);
  const [copied, setCopied] = useState(false);
  const [history, setHistory] = useState<string[]>(() => {
    try {
      const saved = localStorage.getItem('linuxos_qr_history');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    localStorage.setItem('linuxos_qr_history', JSON.stringify(history.slice(0, 10)));
  }, [history]);

  const qrUrl = generateQRUrl(text, size);

  const generate = useCallback(() => {
    if (text.trim()) {
      setHistory((prev) => [text.trim(), ...prev.filter((h) => h !== text.trim())].slice(0, 10));
    }
  }, [text]);

  useEffect(() => {
    generate();
  }, [generate]);

  const copyImage = async () => {
    if (!qrUrl) return;
    try {
      const res = await fetch(qrUrl);
      const blob = await res.blob();
      await navigator.clipboard.write([new ClipboardItem({ [blob.type]: blob })]);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Fallback
      navigator.clipboard.writeText(text);
    }
  };

  const download = async () => {
    if (!qrUrl) return;
    try {
      const res = await fetch(qrUrl);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `qrcode-${Date.now()}.png`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 p-4 items-center overflow-y-auto">
      <div className="flex items-center gap-2 mb-4">
        <QrCode size={18} className="text-blue-400" />
        <h2 className="text-lg text-blue-200 font-semibold">QR Code Generator</h2>
      </div>

      <div className="w-full max-w-[400px] mb-3">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Enter URL or text..."
          className="w-full h-20 bg-[#162032] border border-blue-500/15 rounded-xl p-3 text-xs resize-none outline-none focus:border-blue-500/30"
        />
      </div>

      <div className="flex items-center gap-3 mb-4">
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-blue-300/30">Size:</span>
          <input
            type="range"
            min={100}
            max={500}
            step={10}
            value={size}
            onChange={(e) => setSize(Number(e.target.value))}
            className="w-24 accent-blue-500"
          />
          <span className="text-[10px] text-blue-200/50 font-mono">{size}px</span>
        </div>
      </div>

      {qrUrl && (
        <div className="bg-white rounded-xl p-3 mb-4 shadow-lg">
          <img
            src={qrUrl}
            alt="QR Code"
            className="block"
            style={{ width: size, height: size, maxWidth: '100%' }}
          />
        </div>
      )}

      <div className="flex gap-2 mb-4">
        <button
          onClick={copyImage}
          className="px-3 py-1.5 rounded-lg bg-blue-500/15 text-blue-300 text-xs hover:bg-blue-500/25 transition-colors flex items-center gap-1.5"
        >
          {copied ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
          {copied ? 'Copied' : 'Copy'}
        </button>
        <button
          onClick={download}
          className="px-3 py-1.5 rounded-lg bg-blue-500/15 text-blue-300 text-xs hover:bg-blue-500/25 transition-colors flex items-center gap-1.5"
        >
          <Download size={12} /> Download
        </button>
        {/^https?:\/\//.test(text) && (
          <button
            onClick={() => window.open(text, '_blank')}
            className="px-3 py-1.5 rounded-lg bg-blue-500/15 text-blue-300 text-xs hover:bg-blue-500/25 transition-colors flex items-center gap-1.5"
          >
            <ExternalLink size={12} /> Open
          </button>
        )}
      </div>

      {history.length > 1 && (
        <div className="w-full max-w-[400px]">
          <div className="text-[10px] uppercase tracking-wider text-blue-400/30 mb-1">Recent</div>
          <div className="flex flex-wrap gap-1">
            {history.slice(1, 8).map((h, i) => (
              <button
                key={i}
                onClick={() => setText(h)}
                className="px-2 py-1 rounded bg-[#162032] text-[10px] text-blue-200/40 hover:text-blue-200/70 transition-colors truncate max-w-[150px]"
              >
                {h}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
