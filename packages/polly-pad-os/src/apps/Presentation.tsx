import React, { useState } from 'react';
import { ChevronLeft, ChevronRight, Play, Square } from 'lucide-react';

const SLIDES = [
  {
    title: 'Welcome to LinuxOS',
    content: 'A web-based Linux replica with 60+ fully functional apps.',
    color: 'from-blue-600/30 to-purple-600/30',
  },
  {
    title: 'Desktop Environment',
    content: 'Features draggable icons, a window manager, and a fully functional taskbar.',
    color: 'from-green-600/30 to-teal-600/30',
  },
  {
    title: '60+ Applications',
    content: 'Includes games, productivity tools, media players, dev tools, and utilities.',
    color: 'from-orange-600/30 to-red-600/30',
  },
  {
    title: 'Fully Functional',
    content: 'Every app is interactive and works - not just placeholders.',
    color: 'from-purple-600/30 to-pink-600/30',
  },
  {
    title: 'Open Source',
    content: 'Built with React, TypeScript, and Tailwind CSS.',
    color: 'from-cyan-600/30 to-blue-600/30',
  },
];

export default function Presentation() {
  const [current, setCurrent] = useState(0);
  const [presenting, setPresenting] = useState(false);

  const next = () => setCurrent((c) => (c + 1) % SLIDES.length);
  const prev = () => setCurrent((c) => (c - 1 + SLIDES.length) % SLIDES.length);

  const slide = SLIDES[current];

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80">
      {!presenting ? (
        <>
          <div className="flex items-center justify-between px-3 py-2 border-b border-blue-500/10 bg-[#111d2e]">
            <span className="text-xs text-blue-300/40">
              Slide {current + 1}/{SLIDES.length}
            </span>
            <button
              onClick={() => setPresenting(true)}
              className="p-1.5 rounded bg-blue-500/20 text-blue-200 hover:bg-blue-500/30"
            >
              <Play size={14} />
            </button>
          </div>
          <div className="flex-1 flex items-center justify-center p-8">
            <div
              className={`w-full max-w-[600px] aspect-video rounded-2xl bg-gradient-to-br ${slide.color} border border-blue-500/15 flex flex-col items-center justify-center p-8 shadow-2xl`}
            >
              <h2 className="text-2xl text-blue-100 font-semibold mb-3 text-center">
                {slide.title}
              </h2>
              <p className="text-sm text-blue-200/60 text-center">{slide.content}</p>
            </div>
          </div>
          <div className="flex items-center justify-center gap-4 px-3 py-2 border-t border-blue-500/10">
            <button onClick={prev} className="p-2 rounded-lg hover:bg-blue-500/20 text-blue-300">
              <ChevronLeft size={18} />
            </button>
            <div className="flex gap-1">
              {SLIDES.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setCurrent(i)}
                  className={`w-2 h-2 rounded-full transition-colors ${i === current ? 'bg-blue-500' : 'bg-blue-500/20'}`}
                />
              ))}
            </div>
            <button onClick={next} className="p-2 rounded-lg hover:bg-blue-500/20 text-blue-300">
              <ChevronRight size={18} />
            </button>
          </div>
        </>
      ) : (
        <div
          className="fixed inset-0 z-[100000] bg-[#0d1926] flex flex-col items-center justify-center"
          onClick={next}
        >
          <button
            onClick={(e) => {
              e.stopPropagation();
              setPresenting(false);
            }}
            className="absolute top-4 right-4 p-2 rounded-lg bg-blue-500/20 text-blue-200 hover:bg-blue-500/30 z-10"
          >
            <Square size={16} />
          </button>
          <div
            className={`w-full h-full flex flex-col items-center justify-center p-16 bg-gradient-to-br ${slide.color}`}
          >
            <h2 className="text-4xl text-blue-100 font-semibold mb-4 text-center">{slide.title}</h2>
            <p className="text-lg text-blue-200/60 text-center">{slide.content}</p>
          </div>
        </div>
      )}
    </div>
  );
}
