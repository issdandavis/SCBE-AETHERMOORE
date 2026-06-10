import React, { useRef, useEffect, useState, useCallback } from 'react';
import { useOS } from './OSStore';
import type { WindowState } from '@/types';
import { Minus, Square, X, GripVertical } from 'lucide-react';

interface WindowProps {
  window: WindowState;
  children: React.ReactNode;
}

export default function WindowComponent({ window: win, children }: WindowProps) {
  const {
    focusWindow,
    closeWindow,
    minimizeWindow,
    maximizeWindow,
    restoreWindow,
    setWindowPos,
    setWindowSize,
  } = useOS();
  const windowRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const dragStart = useRef({ x: 0, y: 0, winX: 0, winY: 0 });
  const resizeStart = useRef({ x: 0, y: 0, w: 0, h: 0 });
  const [prevSize, setPrevSize] = useState({ x: win.x, y: win.y, w: win.width, h: win.height });

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if ((e.target as HTMLElement).closest('.window-control')) return;
      focusWindow(win.id);
    },
    [focusWindow, win.id]
  );

  const handleTitleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (win.isMaximized) return;
      setIsDragging(true);
      dragStart.current = { x: e.clientX, y: e.clientY, winX: win.x, winY: win.y };
    },
    [win.isMaximized, win.x, win.y]
  );

  const handleResizeMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (win.isMaximized) return;
      e.stopPropagation();
      e.preventDefault();
      setIsResizing(true);
      resizeStart.current = { x: e.clientX, y: e.clientY, w: win.width, h: win.height };
    },
    [win.isMaximized, win.width, win.height]
  );

  useEffect(() => {
    if (!isDragging && !isResizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (isDragging) {
        const dx = e.clientX - dragStart.current.x;
        const dy = e.clientY - dragStart.current.y;
        let newX = dragStart.current.winX + dx;
        let newY = dragStart.current.winY + dy;
        newX = Math.max(-win.width + 100, Math.min(newX, window.innerWidth - 50));
        newY = Math.max(0, Math.min(newY, window.innerHeight - 60));
        setWindowPos(win.id, newX, newY);
      }
      if (isResizing) {
        const dx = e.clientX - resizeStart.current.x;
        const dy = e.clientY - resizeStart.current.y;
        const newW = Math.max(300, resizeStart.current.w + dx);
        const newH = Math.max(200, resizeStart.current.h + dy);
        setWindowSize(win.id, newW, newH);
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      setIsResizing(false);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, isResizing, win.id, setWindowPos, setWindowSize]);

  const handleMaximize = useCallback(() => {
    if (win.isMaximized) {
      restoreWindow(win.id);
    } else {
      setPrevSize({ x: win.x, y: win.y, w: win.width, h: win.height });
      maximizeWindow(win.id);
    }
  }, [win.isMaximized, win.id, win.x, win.y, win.width, win.height, restoreWindow, maximizeWindow]);

  return (
    <div
      ref={windowRef}
      id={`window-${win.id}`}
      className={`absolute flex flex-col rounded-xl shadow-2xl overflow-hidden transition-shadow ${
        win.isFocused ? 'shadow-blue-500/20 ring-1 ring-blue-500/30' : 'shadow-black/40'
      }`}
      style={{
        left: win.x,
        top: win.y,
        width: win.width,
        height: win.height,
        zIndex: win.zIndex,
        background: '#111d2e',
      }}
      onMouseDown={handleMouseDown}
    >
      {/* Title Bar */}
      <div
        className={`h-9 flex items-center justify-between px-2 select-none ${
          isDragging ? 'cursor-grabbing' : win.isMaximized ? 'cursor-default' : 'cursor-grab'
        } ${win.isFocused ? 'bg-[#1a2d45]' : 'bg-[#131f33]'}`}
        onMouseDown={handleTitleMouseDown}
      >
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <GripVertical size={12} className="text-blue-400/20" />
          <span
            className={`text-xs truncate ${win.isFocused ? 'text-blue-100' : 'text-blue-300/40'}`}
          >
            {win.title}
          </span>
        </div>
        <div className="flex items-center gap-0.5 window-control">
          <button
            onClick={(e) => {
              e.stopPropagation();
              minimizeWindow(win.id);
            }}
            className="p-1 rounded-md hover:bg-blue-500/20 text-blue-300/50 hover:text-blue-200 transition-colors"
          >
            <Minus size={13} />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleMaximize();
            }}
            className="p-1 rounded-md hover:bg-blue-500/20 text-blue-300/50 hover:text-blue-200 transition-colors"
          >
            <Square size={11} />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              closeWindow(win.id);
            }}
            className="p-1 rounded-md hover:bg-red-500/30 text-blue-300/50 hover:text-red-400 transition-colors"
          >
            <X size={13} />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden relative" style={{ background: '#0d1926' }}>
        {children}
      </div>

      {/* Resize Handle */}
      {!win.isMaximized && (
        <div
          className="absolute bottom-0 right-0 w-4 h-4 cursor-se-resize z-10"
          onMouseDown={handleResizeMouseDown}
          style={{
            background: 'linear-gradient(135deg, transparent 50%, rgba(59,130,246,0.2) 50%)',
            borderBottomRightRadius: '12px',
          }}
        />
      )}
    </div>
  );
}
