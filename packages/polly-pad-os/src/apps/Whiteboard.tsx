import React, { useState, useRef, useCallback } from 'react';
import { Pencil, Minus, Square, Circle, Eraser, Trash2, Download, ImagePlus } from 'lucide-react';

type Tool = 'pencil' | 'line' | 'rect' | 'circle' | 'eraser';

export default function Whiteboard() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [tool, setTool] = useState<Tool>('pencil');
  const [color, setColor] = useState('#60a5fa');
  const [size, setSize] = useState(3);
  const drawingRef = useRef(false);
  const startRef = useRef({ x: 0, y: 0 });
  const snapshotRef = useRef<ImageData | null>(null);

  const getPos = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const c = canvasRef.current;
    if (!c) return { x: 0, y: 0 };
    const r = c.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  }, []);

  const start = (e: React.MouseEvent<HTMLCanvasElement>) => {
    drawingRef.current = true;
    const p = getPos(e);
    startRef.current = p;
    const ctx = canvasRef.current?.getContext('2d');
    if (!ctx) return;
    snapshotRef.current = ctx.getImageData(
      0,
      0,
      canvasRef.current!.width,
      canvasRef.current!.height
    );
    ctx.beginPath();
    ctx.moveTo(p.x, p.y);
    ctx.strokeStyle = tool === 'eraser' ? '#0d1926' : color;
    ctx.lineWidth = size;
    ctx.lineCap = 'round';
  };

  const draw = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!drawingRef.current) return;
    const p = getPos(e);
    const ctx = canvasRef.current?.getContext('2d');
    if (!ctx) return;
    if (tool === 'pencil' || tool === 'eraser') {
      ctx.lineTo(p.x, p.y);
      ctx.stroke();
    } else if (snapshotRef.current) {
      ctx.putImageData(snapshotRef.current, 0, 0);
      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.lineWidth = size;
      if (tool === 'line') {
        ctx.moveTo(startRef.current.x, startRef.current.y);
        ctx.lineTo(p.x, p.y);
        ctx.stroke();
      } else if (tool === 'rect')
        ctx.strokeRect(
          startRef.current.x,
          startRef.current.y,
          p.x - startRef.current.x,
          p.y - startRef.current.y
        );
      else if (tool === 'circle') {
        const r = Math.sqrt(
          Math.pow(p.x - startRef.current.x, 2) + Math.pow(p.y - startRef.current.y, 2)
        );
        ctx.arc(startRef.current.x, startRef.current.y, r, 0, Math.PI * 2);
        ctx.stroke();
      }
    }
  };

  const end = () => {
    drawingRef.current = false;
  };
  const clear = () => {
    const ctx = canvasRef.current?.getContext('2d');
    if (ctx && canvasRef.current) {
      ctx.fillStyle = '#0d1926';
      ctx.fillRect(0, 0, canvasRef.current.width, canvasRef.current.height);
    }
  };

  const exportCanvas = () => {
    const cvs = canvasRef.current;
    if (!cvs) return;
    const link = document.createElement('a');
    link.download = `whiteboard-${Date.now()}.png`;
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

  const colors = ['#60a5fa', '#ef4444', '#4ade80', '#fbbf24', '#a78bfa', '#f472b6', '#ffffff'];

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926]">
      <div className="flex items-center gap-1 px-2 py-1.5 border-b border-blue-500/10 bg-[#111d2e]">
        {[
          { t: 'pencil' as Tool, i: <Pencil size={14} /> },
          { t: 'line' as Tool, i: <Minus size={14} /> },
          { t: 'rect' as Tool, i: <Square size={14} /> },
          { t: 'circle' as Tool, i: <Circle size={14} /> },
          { t: 'eraser' as Tool, i: <Eraser size={14} /> },
        ].map(({ t, i }) => (
          <button
            key={t}
            onClick={() => setTool(t)}
            className={`p-1.5 rounded ${tool === t ? 'bg-blue-500/25 text-blue-200' : 'text-blue-300/40 hover:text-blue-200'}`}
          >
            {i}
          </button>
        ))}
        <div className="w-px h-5 bg-blue-500/10 mx-1" />
        {colors.map((c) => (
          <button
            key={c}
            onClick={() => setColor(c)}
            className={`w-5 h-5 rounded-full border-2 ${color === c ? 'border-white' : 'border-transparent'}`}
            style={{ background: c }}
          />
        ))}
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
        <button onClick={clear} className="p-1.5 rounded hover:bg-red-500/20 text-blue-300/40">
          <Trash2 size={14} />
        </button>
      </div>
      <canvas
        ref={canvasRef}
        width={800}
        height={600}
        className="flex-1 cursor-crosshair"
        onMouseDown={start}
        onMouseMove={draw}
        onMouseUp={end}
        onMouseLeave={end}
      />
    </div>
  );
}
