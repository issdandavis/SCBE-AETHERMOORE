import React, { useState, useRef, useCallback } from 'react';
import { Minus, Square, Circle, Pencil, Trash2, Eraser, Download } from 'lucide-react';

type Tool = 'brush' | 'eraser' | 'line' | 'rect' | 'circle';

export default function Paint() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [color, setColor] = useState('#60a5fa');
  const [size, setSize] = useState(3);
  const [tool, setTool] = useState<Tool>('brush');
  const [drawing, setDrawing] = useState(false);
  const [start, setStart] = useState({ x: 0, y: 0 });
  const [snapshot, setSnapshot] = useState<ImageData | null>(null);

  const colors = [
    '#000000',
    '#ffffff',
    '#ef4444',
    '#f97316',
    '#f59e0b',
    '#84cc16',
    '#22c55e',
    '#06b6d4',
    '#3b82f6',
    '#6366f1',
    '#8b5cf6',
    '#ec4899',
    '#f43f5e',
    '#64748b',
  ];

  const getPos = useCallback((e: React.MouseEvent) => {
    const c = canvasRef.current;
    if (!c) return { x: 0, y: 0 };
    const r = c.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  }, []);

  const startDraw = (e: React.MouseEvent) => {
    setDrawing(true);
    const p = getPos(e);
    setStart(p);
    const cvs = canvasRef.current;
    if (!cvs) return;
    const ctx = cvs.getContext('2d');
    if (!ctx) return;
    setSnapshot(ctx.getImageData(0, 0, cvs.width, cvs.height));
    ctx.beginPath();
    ctx.moveTo(p.x, p.y);
    ctx.strokeStyle = tool === 'eraser' ? '#ffffff' : color;
    ctx.lineWidth = size;
    ctx.lineCap = 'round';
    if (tool === 'brush' || tool === 'eraser') {
      ctx.lineTo(p.x, p.y);
      ctx.stroke();
    }
  };

  const draw = (e: React.MouseEvent) => {
    if (!drawing) return;
    const p = getPos(e);
    const cvs = canvasRef.current;
    if (!cvs) return;
    const ctx = cvs.getContext('2d');
    if (!ctx) return;

    if (tool === 'brush' || tool === 'eraser') {
      ctx.lineTo(p.x, p.y);
      ctx.stroke();
    } else if (snapshot) {
      ctx.putImageData(snapshot, 0, 0);
      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.lineWidth = size;
      if (tool === 'line') {
        ctx.moveTo(start.x, start.y);
        ctx.lineTo(p.x, p.y);
        ctx.stroke();
      } else if (tool === 'rect') {
        ctx.strokeRect(start.x, start.y, p.x - start.x, p.y - start.y);
      } else if (tool === 'circle') {
        const r = Math.sqrt(Math.pow(p.x - start.x, 2) + Math.pow(p.y - start.y, 2));
        ctx.arc(start.x, start.y, r, 0, Math.PI * 2);
        ctx.stroke();
      }
    }
  };

  const endDraw = () => setDrawing(false);

  const clear = () => {
    const cvs = canvasRef.current;
    if (!cvs) return;
    const ctx = cvs.getContext('2d');
    if (!ctx) return;
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, cvs.width, cvs.height);
  };

  const download = () => {
    const cvs = canvasRef.current;
    if (!cvs) return;
    const link = document.createElement('a');
    link.download = 'paint.png';
    link.href = cvs.toDataURL();
    link.click();
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#f0f0f0]">
      <div className="flex items-center gap-1 px-2 py-1 bg-[#e0e0e0] border-b border-gray-300">
        {[
          { t: 'brush' as Tool, i: <Pencil size={14} /> },
          { t: 'eraser' as Tool, i: <Eraser size={14} /> },
          { t: 'line' as Tool, i: <Minus size={14} /> },
          { t: 'rect' as Tool, i: <Square size={14} /> },
          { t: 'circle' as Tool, i: <Circle size={14} /> },
        ].map(({ t, i }) => (
          <button
            key={t}
            onClick={() => setTool(t)}
            className={`p-1.5 rounded ${tool === t ? 'bg-blue-500 text-white' : 'hover:bg-gray-300'}`}
          >
            {i}
          </button>
        ))}
        <div className="w-px h-5 bg-gray-300 mx-1" />
        {colors.map((c) => (
          <button
            key={c}
            onClick={() => {
              setColor(c);
              setTool('brush');
            }}
            className="w-5 h-5 rounded border border-gray-300"
            style={{ background: c }}
          />
        ))}
        <div className="flex-1" />
        <button onClick={clear} className="p-1.5 rounded hover:bg-red-200 text-red-600">
          <Trash2 size={14} />
        </button>
        <button onClick={download} className="p-1.5 rounded hover:bg-gray-300">
          <Download size={14} />
        </button>
      </div>
      <canvas
        ref={canvasRef}
        width={800}
        height={600}
        className="flex-1 bg-white cursor-crosshair"
        onMouseDown={startDraw}
        onMouseMove={draw}
        onMouseUp={endDraw}
        onMouseLeave={endDraw}
      />
    </div>
  );
}
