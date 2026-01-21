/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Point, Stroke } from '../types';

interface InkLayerProps {
    active: boolean;
    strokes: Stroke[];
    onStrokeComplete: (stroke: Stroke) => void;
    isProcessing: boolean;
}

export const InkLayer: React.FC<InkLayerProps> = ({ active, strokes, onStrokeComplete, isProcessing }) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const [isDrawing, setIsDrawing] = useState(false);
    const currentStroke = useRef<Stroke>([]);

    // Function to draw a single stroke with the new volumetric style
    const drawSingleStroke = (ctx: CanvasRenderingContext2D, stroke: Stroke) => {
        if (stroke.length < 2) return;

        const path = new Path2D();
        // Move to the first point
        path.moveTo(stroke[0].x, stroke[0].y);
        
        // Use simple line segments for responsiveness. 
        for (let i = 1; i < stroke.length; i++) {
            path.lineTo(stroke[i].x, stroke[i].y);
        }

        ctx.globalCompositeOperation = 'source-over';
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';

        // --- Pass 1: Contrast Shadow (helps visibility on white backgrounds) ---
        // A very faint, wide dark stroke underneath to act as a shadow/contrast booster
        ctx.lineWidth = 14;
        ctx.strokeStyle = 'rgba(0, 0, 0, 0.15)'; 
        ctx.stroke(path);

        // --- Pass 2: Wide White Glow ---
        ctx.lineWidth = 12;
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
        ctx.stroke(path);

        // --- Pass 3: Core Solid White Stroke ---
        ctx.lineWidth = 7;
        ctx.strokeStyle = '#ffffff';
        ctx.stroke(path);
    };

    // Main render function that clears and redraws everything
    const renderCanvas = useCallback(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        // Clear
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Draw all committed strokes
        strokes.forEach(stroke => drawSingleStroke(ctx, stroke));

        // Draw the active stroke being drawn right now
        if (isDrawing && currentStroke.current.length > 0) {
            drawSingleStroke(ctx, currentStroke.current);
        }
    }, [strokes, isDrawing]);

    // Resize handler
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const resize = () => {
            const parent = canvas.parentElement;
            if (parent) {
                const rect = parent.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    canvas.width = rect.width;
                    canvas.height = rect.height;
                    renderCanvas();
                }
            }
        };

        resize();
        window.addEventListener('resize', resize);
        return () => window.removeEventListener('resize', resize);
    }, [renderCanvas]);

    // Trigger render when strokes change externally
    useEffect(() => {
        if (!isProcessing) {
            renderCanvas();
        }
    }, [strokes, renderCanvas, isProcessing]);

    // Pulsating animation loop when processing
    useEffect(() => {
        if (!isProcessing) return;

        let animationFrameId: number;
        const start = Date.now();

        const animate = () => {
            const canvas = canvasRef.current;
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            if (!ctx) return;

            const now = Date.now();
            // Create a smooth sine wave for opacity between 0.4 and 1.0
            const pulse = (Math.sin((now - start) / 250) + 1) / 3.33 + 0.4;

            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.save();
            ctx.globalAlpha = pulse;
            strokes.forEach(stroke => drawSingleStroke(ctx, stroke));
            ctx.restore();

            animationFrameId = requestAnimationFrame(animate);
        };

        animate();

        return () => {
            cancelAnimationFrame(animationFrameId);
            // Ensure we do one final clean render when stopping
            renderCanvas();
        };
    }, [isProcessing, strokes, renderCanvas]);

    const getPoint = (e: React.PointerEvent<HTMLCanvasElement>): Point => {
        const rect = canvasRef.current!.getBoundingClientRect();
        return {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };
    };

    const handlePointerDown = (e: React.PointerEvent<HTMLCanvasElement>) => {
        if (!active || isProcessing) return;
        e.currentTarget.setPointerCapture(e.pointerId);
        setIsDrawing(true);
        const point = getPoint(e);
        currentStroke.current = [point];
        renderCanvas();
    };

    const handlePointerMove = (e: React.PointerEvent<HTMLCanvasElement>) => {
        if (!active || !isDrawing || isProcessing) return;
        
        const getCoalescedEvents = (e: React.PointerEvent<HTMLCanvasElement>) => {
             // @ts-ignore 
             if (typeof e.getCoalescedEvents === 'function') {
                 // @ts-ignore
                 return e.getCoalescedEvents();
             }
             return [e];
        };

        const events = getCoalescedEvents(e);
        const rect = canvasRef.current!.getBoundingClientRect();

        for (let i = 0; i < events.length; i++) {
             currentStroke.current.push({
                x: events[i].clientX - rect.left,
                y: events[i].clientY - rect.top
            });
        }

        renderCanvas();
    };

    const handlePointerUp = (e: React.PointerEvent<HTMLCanvasElement>) => {
        if (!active || !isDrawing || isProcessing) return;
        setIsDrawing(false);
        e.currentTarget.releasePointerCapture(e.pointerId);
        
        if (currentStroke.current.length > 0) {
            onStrokeComplete([...currentStroke.current]);
        }
        currentStroke.current = [];
    };

    return (
        <canvas
            ref={canvasRef}
            className={`absolute inset-0 z-[2000] touch-none ${active && !isProcessing ? 'cursor-crosshair' : 'pointer-events-none'}`}
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            onPointerCancel={handlePointerUp}
        />
    );
};