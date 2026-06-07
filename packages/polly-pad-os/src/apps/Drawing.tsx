import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Trash2, Download, Circle, Square, Minus, Undo, ImagePlus } from 'lucide-react';

export default function Drawing() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [color, setColor] = useState('#60a5fa');
  const [brushSize, setBrushSize] = useState(3);
  const [tool, setTool] = useState<'brush' | 'eraser' | 'line' | 'rect' | 'circle'>('brush');
  const [isDrawing, setIsDrawing] = useState(false);
  const [startPos, setStartPos] = useState({ x: 0, y: 0 });
  const [snapshot, setSnapshot] = useState<ImageData | null>(null);
  const historyRef = useState<ImageData[]>([])[0];

  const colors = [
    '#60a5fa',
    '#f87171',
    '#4ade80',
    '#fbbf24',
    '#a78bfa',
    '#f472b6',
    '#94a3b8',
    '#ffffff',
    '#000000',
  ];

  const getPos = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const cvs = canvasRef.current;
    if (!cvs) return { x: 0, y: 0 };
    const rect = cvs.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }, []);

  const startDraw = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDrawing(true);
    const pos = getPos(e);
    setStartPos(pos);
    const cvs = canvasRef.current;
    if (!cvs) return;
    const ctx = cvs.getContext('2d');
    if (!ctx) return;
    setSnapshot(ctx.getImageData(0, 0, cvs.width, cvs.height));
    ctx.beginPath();
    ctx.moveTo(pos.x, pos.y);
    ctx.strokeStyle = tool === 'eraser' ? '#0d1926' : color;
    ctx.lineWidth = brushSize;
    ctx.lineCap = 'round';
  };

  const draw = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing) return;
    const pos = getPos(e);
    const cvs = canvasRef.current;
    if (!cvs) return;
    const ctx = cvs.getContext('2d');
    if (!ctx) return;

    if (tool === 'brush' || tool === 'eraser') {
      ctx.lineTo(pos.x, pos.y);
      ctx.stroke();
    } else if (snapshot) {
      ctx.putImageData(snapshot, 0, 0);
      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.lineWidth = brushSize;
      if (tool === 'line') {
        ctx.moveTo(startPos.x, startPos.y);
        ctx.lineTo(pos.x, pos.y);
        ctx.stroke();
      } else if (tool === 'rect') {
        ctx.strokeRect(startPos.x, startPos.y, pos.x - startPos.x, pos.y - startPos.y);
      } else if (tool === 'circle') {
        const r = Math.sqrt(Math.pow(pos.x - startPos.x, 2) + Math.pow(pos.y - startPos.y, 2));
        ctx.arc(startPos.x, startPos.y, r, 0, Math.PI * 2);
        ctx.stroke();
      }
    }
  };

  const endDraw = () => setIsDrawing(false);

  const clear = () => {
    const cvs = canvasRef.current;
    if (!cvs) return;
    const ctx = cvs.getContext('2d');
    if (!ctx) return;
    ctx.fillStyle = '#0d1926';
    ctx.fillRect(0, 0, cvs.width, cvs.height);
  };

  const exportCanvas = () => {
    const cvs = canvasRef.current;
    if (!cvs) return;
    const link = document.createElement('a');
    link.download = `drawing-${Date.now()}.png`;
    link.href = cvs.toDataURL('image/png');
    link.click();
  };

  const importImage = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (ev) => {
        const img = new Image();
        img.onload = () => {
          const cvs = canvasRef.current;
          if (!cvs) return;
          const ctx = cvs.getContext('2d');
          if (!ctx) return;
          ctx.drawImage(img, 0, 0, cvs.width, cvs.height);
        };
        img.src = ev.target?.result as string;
      };
      reader.readAsDataURL(file);
    };
    input.click();
  };

  useEffect(() => {
    const cvs = canvasRef.current;
    if (!cvs) return;
    cvs.width = cvs.offsetWidth;
    cvs.height = cvs.offsetHeight;
    clear();
  }, []);

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926]">
      <div className="flex items-center gap-1 px-2 py-1.5 border-b border-blue-500/10 bg-[#111d2e]">
        {(['brush', 'eraser', 'line', 'rect', 'circle'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTool(t)}
            className={`p-1.5 rounded transition-colors ${tool === t ? 'bg-blue-500/25 text-blue-200' : 'text-blue-300/40 hover:text-blue-200 hover:bg-blue-500/10'}`}
          >
            {t === 'brush' ? (
              <Circle size={14} />
            ) : t === 'eraser' ? (
              <Trash2 size={14} />
            ) : t === 'line' ? (
              <Minus size={14} />
            ) : t === 'rect' ? (
              <Square size={14} />
            ) : (
              <Circle size={14} />
            )}
          </button>
        ))}
        <div className="w-px h-5 bg-blue-500/10 mx-1" />
        {colors.map((c) => (
          <button
            key={c}
            onClick={() => {
              setColor(c);
              setTool('brush');
            }}
            className={`w-5 h-5 rounded-full border-2 transition-transform hover:scale-110 ${color === c ? 'border-white' : 'border-transparent'}`}
            style={{ background: c }}
          />
        ))}
        <div className="w-px h-5 bg-blue-500/10 mx-1" />
        <input
          type="range"
          min={1}
          max={20}
          value={brushSize}
          onChange={(e) => setBrushSize(Number(e.target.value))}
          className="w-16 accent-blue-500"
        />
        <div className="w-px h-5 bg-blue-500/10 mx-1" />
        <button
          onClick={importImage}
          className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/40 hover:text-blue-300"
          title="Import Image"
        >
          <ImagePlus size={14} />
        </button>
        <button
          onClick={exportCanvas}
          className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/40 hover:text-blue-300"
          title="Export PNG"
        >
          <Download size={14} />
        </button>
        <div className="flex-1" />
        <button
          onClick={clear}
          className="p-1.5 rounded hover:bg-red-500/20 text-blue-300/40 hover:text-red-400"
        >
          <Trash2 size={14} />
        </button>
      </div>
      <canvas
        ref={canvasRef}
        className="flex-1 cursor-crosshair"
        onMouseDown={startDraw}
        onMouseMove={draw}
        onMouseUp={endDraw}
        onMouseLeave={endDraw}
      />
    </div>
  );
}
