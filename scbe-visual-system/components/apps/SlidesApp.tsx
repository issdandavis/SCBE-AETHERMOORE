/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
import React, { useState } from 'react';

const MOCK_SLIDES = [
    { id: 1, src: 'https://picsum.photos/300/200?random=1', x: 50, y: 50, title: 'Q1 Growth' },
    { id: 2, src: 'https://picsum.photos/300/200?random=2', x: 320, y: 80, title: 'Team Photo' },
    { id: 3, src: 'https://picsum.photos/300/200?random=3', x: 150, y: 250, title: 'Product Roadmap' },
];

export const SlidesApp: React.FC = () => {
    const [slides, setSlides] = useState(MOCK_SLIDES);
    const [dragId, setDragId] = useState<number | null>(null);
    const [offset, setOffset] = useState({ x: 0, y: 0 });

    const handleMouseDown = (e: React.MouseEvent, id: number) => {
        e.stopPropagation(); // Prevent window drag
        const slide = slides.find(s => s.id === id);
        if (!slide) return;
        setDragId(id);
        setOffset({
            x: e.clientX - slide.x,
            y: e.clientY - slide.y
        });
    };

    const handleMouseMove = (e: React.MouseEvent) => {
        if (dragId === null) return;
        setSlides(prev => prev.map(slide =>
            slide.id === dragId
                ? { ...slide, x: e.clientX - offset.x, y: e.clientY - offset.y }
                : slide
        ));
    };

    const handleMouseUp = () => {
        setDragId(null);
    };

    return (
        <div
            className="h-full w-full bg-zinc-100 relative overflow-hidden flex flex-col"
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
        >
            <div className="bg-white border-b border-zinc-200 px-4 py-2 flex items-center shrink-0">
                <h2 className="font-semibold text-zinc-800">Gemini Slides Editor</h2>
            </div>
            <div className="flex-1 relative bg-[radial-gradient(#e5e7eb_1px,transparent_1px)] [background-size:16px_16px] p-4 overflow-hidden">
                 <p className="text-zinc-400 text-sm absolute top-4 left-4 pointer-events-none select-none">Drag images to arrange slides on the canvas</p>
                {slides.map((slide) => (
                    <div
                        key={slide.id}
                        style={{ left: slide.x, top: slide.y }}
                        className={`absolute w-52 bg-white shadow-md hover:shadow-xl transition-shadow p-2 rounded cursor-move border ${dragId === slide.id ? 'border-blue-400' : 'border-zinc-200'}`}
                        onMouseDown={(e) => handleMouseDown(e, slide.id)}
                    >
                        <img src={slide.src} alt={slide.title} className="w-full h-28 object-cover rounded-sm pointer-events-none bg-zinc-200" />
                        <p className="text-center text-zinc-700 mt-2 text-xs font-medium">{slide.title}</p>
                    </div>
                ))}
            </div>
        </div>
    );
};
