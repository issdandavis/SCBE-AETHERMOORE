/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
import React, { useState, useRef, useEffect } from 'react';
import { X, Minus, Square, Grip } from 'lucide-react';

interface DraggableWindowProps {
    id: string;
    title: string;
    icon?: React.ElementType;
    onClose: () => void;
    children: React.ReactNode;
    initialPos?: { x: number; y: number };
    initialSize?: { width: number; height: number };
    zIndex: number;
    onFocus?: () => void;
    isActive?: boolean;
}

export const DraggableWindow: React.FC<DraggableWindowProps> = ({
    id,
    title,
    icon: Icon,
    onClose,
    children,
    initialPos = { x: 50, y: 50 },
    initialSize = { width: 640, height: 480 },
    zIndex,
    onFocus,
    isActive = false
}) => {
    // Determine if we should start maximized based on screen size
    const isSmallScreen = typeof window !== 'undefined' && window.innerWidth < 768;
    
    const [pos, setPos] = useState(isSmallScreen ? { x: 0, y: 0 } : initialPos);
    const [size, setSize] = useState(isSmallScreen ? { width: window.innerWidth, height: window.innerHeight } : initialSize);
    const [isDragging, setIsDragging] = useState(false);
    const [isResizing, setIsResizing] = useState(false);
    const [isMaximized, setIsMaximized] = useState(isSmallScreen);
    const preMaximizeState = useRef({ pos, size });
    
    const dragStartPos = useRef({ x: 0, y: 0 });
    const resizeStart = useRef({ x: 0, y: 0, width: 0, height: 0 });
    const windowRef = useRef<HTMLDivElement>(null);

    const handleHeaderPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
        if (e.target instanceof Element && e.target.closest('button')) return;
        if (onFocus) onFocus();
        if (isMaximized) return;
        
        e.preventDefault();
        e.stopPropagation();
        e.currentTarget.setPointerCapture(e.pointerId);
        
        setIsDragging(true);
        dragStartPos.current = {
            x: e.clientX - pos.x,
            y: e.clientY - pos.y
        };
    };

    const handleResizePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
        e.preventDefault();
        e.stopPropagation();
        e.currentTarget.setPointerCapture(e.pointerId);

        if (onFocus) onFocus();
        setIsResizing(true);
        resizeStart.current = {
            x: e.clientX,
            y: e.clientY,
            width: size.width,
            height: size.height
        };
    };

    const toggleMaximize = () => {
        if (isMaximized) {
            setPos(preMaximizeState.current.pos);
            setSize(preMaximizeState.current.size);
        } else {
            preMaximizeState.current = { pos, size };
            setPos({ x: 0, y: 0 });
            setSize({ width: window.innerWidth, height: window.innerHeight });
        }
        setIsMaximized(!isMaximized);
        if (onFocus) onFocus();
    };

    useEffect(() => {
        const handleGlobalPointerMove = (e: PointerEvent) => {
            if (!isDragging && !isResizing) return;
            e.preventDefault(); 

            if (isDragging) {
                // Constrain drag to screen boundaries
                const newX = Math.max(-size.width + 100, Math.min(window.innerWidth - 100, e.clientX - dragStartPos.current.x));
                const newY = Math.max(0, Math.min(window.innerHeight - 40, e.clientY - dragStartPos.current.y));
                setPos({ x: newX, y: newY });
            }
            if (isResizing) {
                setSize({
                    width: Math.max(300, Math.min(window.innerWidth, resizeStart.current.width + (e.clientX - resizeStart.current.x))),
                    height: Math.max(200, Math.min(window.innerHeight - 40, resizeStart.current.height + (e.clientY - resizeStart.current.y)))
                });
            }
        };

        const handleGlobalPointerUp = (e: PointerEvent) => {
             if (isDragging || isResizing) {
                 setIsDragging(false);
                 setIsResizing(false);
             }
        };

        if (isDragging || isResizing) {
            window.addEventListener('pointermove', handleGlobalPointerMove, { passive: false });
            window.addEventListener('pointerup', handleGlobalPointerUp);
            window.addEventListener('pointercancel', handleGlobalPointerUp);
        }
        return () => {
            window.removeEventListener('pointermove', handleGlobalPointerMove);
            window.removeEventListener('pointerup', handleGlobalPointerUp);
            window.removeEventListener('pointercancel', handleGlobalPointerUp);
        };
    }, [isDragging, isResizing, size]);

    // Update window size on browser resize if maximized
    useEffect(() => {
        if (isMaximized) {
            setSize({ width: window.innerWidth, height: window.innerHeight });
        }
    }, [isMaximized]);

    return (
        <div
            ref={windowRef}
            style={!isMaximized ? {
                left: pos.x,
                top: pos.y,
                width: size.width,
                height: size.height,
                zIndex: zIndex
            } : {
                zIndex: zIndex,
                left: 0,
                top: 0,
                width: '100%',
                height: '100%'
            }}
            className={`absolute flex flex-col bg-zinc-900 shadow-2xl border ${isActive ? 'border-zinc-600 ring-1 ring-zinc-700/50' : 'border-zinc-800'} overflow-hidden ${isMaximized ? 'rounded-none m-0' : 'rounded-2xl'} transition-[left,top,width,height,border-radius] duration-200 ease-out touch-none`}
            onPointerDown={() => { if (onFocus) onFocus(); }}
        >
            {/* Window Header */}
            <div
                onDoubleClick={toggleMaximize}
                onPointerDown={handleHeaderPointerDown}
                className={`bg-zinc-800/80 backdrop-blur-md border-b border-zinc-700 px-4 py-3 flex items-center justify-between select-none touch-none ${!isMaximized ? 'cursor-grab active:cursor-grabbing' : ''}`}
            >
                <div className="flex items-center gap-2.5 text-zinc-300 font-bold pointer-events-none">
                    {Icon && <div className="p-1 rounded bg-white/5 border border-white/10"><Icon size={14} className="text-white opacity-90" /></div>}
                    <span className="text-[11px] uppercase tracking-wider">{title}</span>
                </div>
                <div className="flex items-center gap-1">
                     <button className="p-2 hover:bg-zinc-700 rounded-lg text-zinc-400 hover:text-zinc-200 transition-colors">
                        <Minus size={16} />
                    </button>
                    {!isSmallScreen && (
                        <button onClick={toggleMaximize} className="p-2 hover:bg-zinc-700 rounded-lg text-zinc-400 hover:text-zinc-200 transition-colors">
                            <Square size={14} />
                        </button>
                    )}
                    <button
                        onClick={(e) => { e.stopPropagation(); onClose(); }}
                        onPointerDown={(e) => e.stopPropagation()}
                        className="p-2 hover:bg-red-500 rounded-lg text-zinc-400 hover:text-white transition-colors"
                    >
                        <X size={18} />
                    </button>
                </div>
            </div>

            {/* Window Content */}
            <div className="flex-1 overflow-hidden relative bg-zinc-950">
                {children}
                {!isActive && <div className="absolute inset-0 bg-black/0 z-40" />}
            </div>

            {/* Resize Handle */}
            {!isMaximized && !isSmallScreen && (
                <div
                    className="absolute bottom-0 right-0 w-10 h-10 cursor-nwse-resize flex items-center justify-center z-50 text-zinc-600 touch-none"
                    onPointerDown={handleResizePointerDown}
                >
                    <Grip size={18} className="-rotate-45 translate-x-1.5 translate-y-1.5 opacity-50"/>
                </div>
            )}
        </div>
    );
};