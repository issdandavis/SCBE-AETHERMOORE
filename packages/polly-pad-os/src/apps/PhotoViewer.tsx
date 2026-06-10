import React, { useState } from 'react';
import { ZoomIn, ZoomOut, RotateCcw, ChevronLeft, ChevronRight, Image } from 'lucide-react';

const DEMO_IMAGES = [
  { name: 'Landscape', color: 'from-blue-500/30 to-green-500/30' },
  { name: 'Sunset', color: 'from-orange-500/30 to-red-500/30' },
  { name: 'Ocean', color: 'from-cyan-500/30 to-blue-500/30' },
  { name: 'Forest', color: 'from-green-500/30 to-emerald-500/30' },
  { name: 'Night Sky', color: 'from-purple-500/30 to-indigo-500/30' },
  { name: 'Abstract', color: 'from-pink-500/30 to-purple-500/30' },
];

export default function PhotoViewer() {
  const [current, setCurrent] = useState(0);
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);

  const img = DEMO_IMAGES[current];

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-blue-500/10 bg-[#111d2e]">
        <button
          onClick={() => setCurrent((c) => (c - 1 + DEMO_IMAGES.length) % DEMO_IMAGES.length)}
          className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/50"
        >
          <ChevronLeft size={16} />
        </button>
        <span className="text-xs text-blue-200/60 flex-1 text-center">
          {img.name} ({current + 1}/{DEMO_IMAGES.length})
        </span>
        <button
          onClick={() => setCurrent((c) => (c + 1) % DEMO_IMAGES.length)}
          className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/50"
        >
          <ChevronRight size={16} />
        </button>
      </div>
      <div className="flex-1 flex items-center justify-center overflow-hidden p-4">
        <div
          className={`w-full h-full rounded-xl bg-gradient-to-br ${img.color} border border-blue-500/10 flex items-center justify-center transition-transform`}
          style={{ transform: `scale(${zoom}) rotate(${rotation}deg)` }}
        >
          <Image size={80} className="text-blue-400/20" />
          <div className="absolute text-xl text-blue-200/40 font-light">{img.name}</div>
        </div>
      </div>
      <div className="flex items-center justify-center gap-2 px-3 py-2 border-t border-blue-500/10 bg-[#111d2e]">
        <button
          onClick={() => setZoom((z) => Math.max(0.5, z - 0.25))}
          className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/50"
        >
          <ZoomOut size={16} />
        </button>
        <span className="text-xs text-blue-300/30 w-10 text-center">{Math.round(zoom * 100)}%</span>
        <button
          onClick={() => setZoom((z) => Math.min(3, z + 0.25))}
          className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/50"
        >
          <ZoomIn size={16} />
        </button>
        <div className="w-px h-4 bg-blue-500/10 mx-2" />
        <button
          onClick={() => setRotation((r) => r + 90)}
          className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/50"
        >
          <RotateCcw size={16} />
        </button>
        <button
          onClick={() => {
            setZoom(1);
            setRotation(0);
          }}
          className="px-2 py-1 rounded text-xs text-blue-300/40 hover:text-blue-200"
        >
          Reset
        </button>
      </div>
    </div>
  );
}
