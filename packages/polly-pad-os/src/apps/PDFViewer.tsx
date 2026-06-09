import React, { useState } from 'react';
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, FileText } from 'lucide-react';

const PAGES = [
  {
    title: 'SCBE Tool Desktop - Notes',
    content:
      'This is a demo document viewer. The production-use surfaces are PowerShell, Tool Console, Internet routing, and Layered Abacus.\n\nGetting Started:\n- Click the Start button to open the app menu\n- Double-click desktop icons to open apps\n- Drag windows by their title bar\n- Resize windows from the bottom-right corner',
  },
  {
    title: 'Desktop Environment',
    content:
      'The SCBE Tool Desktop provides a browser-based workbench:\n\n- Desktop icons for real tool surfaces\n- Taskbar with system tray and clock\n- Start menu with search functionality\n- Window management (minimize, maximize, close)\n- Right-click context menus\n\nDemo apps are available only when explicitly toggled on.',
  },
  {
    title: 'Surface Truth',
    content:
      'Real surfaces are bridge-backed or tested local tools. Demo apps are visual/source material from the imported desktop build and should not be treated as production capability until wired to a real endpoint.',
  },
];

export default function PDFViewer() {
  const [page, setPage] = useState(0);
  const [zoom, setZoom] = useState(1);

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80">
      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-blue-500/10 bg-[#111d2e]">
        <FileText size={14} className="text-red-400/60" />
        <span className="text-xs text-blue-200/60 flex-1 truncate">
          SCBE_Tool_Desktop_Notes.pdf
        </span>
        <button
          onClick={() => setZoom((z) => Math.max(0.5, z - 0.1))}
          className="p-1 rounded hover:bg-blue-500/20 text-blue-300/50"
        >
          <ZoomOut size={14} />
        </button>
        <span className="text-[10px] text-blue-300/30">{Math.round(zoom * 100)}%</span>
        <button
          onClick={() => setZoom((z) => Math.min(2, z + 0.1))}
          className="p-1 rounded hover:bg-blue-500/20 text-blue-300/50"
        >
          <ZoomIn size={14} />
        </button>
        <div className="w-px h-4 bg-blue-500/10 mx-1" />
        <button
          onClick={() => setPage((p) => Math.max(0, p - 1))}
          className="p-1 rounded hover:bg-blue-500/20 text-blue-300/50"
          disabled={page === 0}
        >
          <ChevronLeft size={14} />
        </button>
        <span className="text-[10px] text-blue-300/30">
          {page + 1}/{PAGES.length}
        </span>
        <button
          onClick={() => setPage((p) => Math.min(PAGES.length - 1, p + 1))}
          className="p-1 rounded hover:bg-blue-500/20 text-blue-300/50"
          disabled={page === PAGES.length - 1}
        >
          <ChevronRight size={14} />
        </button>
      </div>
      <div className="flex-1 overflow-auto p-6 flex justify-center">
        <div
          className="bg-white rounded-lg shadow-xl p-8 max-w-[600px] w-full"
          style={{ transform: `scale(${zoom})`, transformOrigin: 'top center' }}
        >
          <h1 className="text-xl font-bold text-gray-800 mb-4">{PAGES[page].title}</h1>
          <div className="text-sm text-gray-600 whitespace-pre-line leading-relaxed">
            {PAGES[page].content}
          </div>
        </div>
      </div>
    </div>
  );
}
