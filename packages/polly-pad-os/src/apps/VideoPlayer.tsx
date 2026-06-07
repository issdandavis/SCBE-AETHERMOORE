import React, { useState, useRef, useEffect } from 'react';
import { Play, Pause, SkipForward, Volume2, Maximize } from 'lucide-react';

export default function VideoPlayer() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [volume, setVolume] = useState(75);
  const [currentVideo, setCurrentVideo] = useState(0);

  const videos = [
    { title: 'Demo Video 1', duration: 120 },
    { title: 'Demo Video 2', duration: 180 },
    { title: 'Demo Video 3', duration: 90 },
  ];

  useEffect(() => {
    if (!isPlaying) return;
    const interval = setInterval(
      () =>
        setProgress((p) => {
          if (p >= videos[currentVideo].duration) {
            setIsPlaying(false);
            return 0;
          }
          return p + 1;
        }),
      1000
    );
    return () => clearInterval(interval);
  }, [isPlaying, currentVideo]);

  const formatTime = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}`;

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80">
      <div className="flex-1 relative bg-[#0a1420] flex items-center justify-center border-b border-blue-500/10">
        <div className="text-center">
          <div className="w-20 h-20 rounded-full bg-blue-500/10 flex items-center justify-center mx-auto mb-3">
            <Play size={32} className="text-blue-400/40 ml-1" />
          </div>
          <p className="text-sm text-blue-200/60">{videos[currentVideo].title}</p>
          <p className="text-xs text-blue-300/30">Video Player (Demo)</p>
        </div>
      </div>
      <div className="px-4 py-2">
        <input
          type="range"
          min={0}
          max={videos[currentVideo].duration}
          value={progress}
          onChange={(e) => setProgress(Number(e.target.value))}
          className="w-full accent-blue-500 h-1"
        />
        <div className="flex justify-between text-[10px] text-blue-300/30 mt-1">
          <span>{formatTime(progress)}</span>
          <span>{formatTime(videos[currentVideo].duration)}</span>
        </div>
      </div>
      <div className="flex items-center justify-center gap-3 px-4 pb-2">
        <button
          onClick={() => setIsPlaying(!isPlaying)}
          className="p-2.5 rounded-full bg-blue-500/20 text-blue-200 hover:bg-blue-500/30 transition-colors"
        >
          {isPlaying ? <Pause size={18} /> : <Play size={18} className="ml-0.5" />}
        </button>
        <button
          onClick={() => {
            setCurrentVideo((i) => (i + 1) % videos.length);
            setProgress(0);
          }}
          className="p-2 rounded-lg text-blue-300/40 hover:text-blue-200"
        >
          <SkipForward size={16} />
        </button>
        <Volume2 size={14} className="text-blue-300/30" />
        <input
          type="range"
          min={0}
          max={100}
          value={volume}
          onChange={(e) => setVolume(Number(e.target.value))}
          className="w-16 accent-blue-500 h-1"
        />
      </div>
      <div className="border-t border-blue-500/10 max-h-28 overflow-y-auto">
        {videos.map((v, i) => (
          <button
            key={i}
            onClick={() => {
              setCurrentVideo(i);
              setProgress(0);
            }}
            className={`w-full flex items-center gap-3 px-4 py-2 text-left transition-colors ${i === currentVideo ? 'bg-blue-500/10' : 'hover:bg-blue-500/5'}`}
          >
            <span
              className={`text-xs ${i === currentVideo ? 'text-blue-200' : 'text-blue-200/50'}`}
            >
              {v.title}
            </span>
            <span className="text-[10px] text-blue-300/30 ml-auto">{formatTime(v.duration)}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
