import React, { useState, useEffect, useRef } from 'react';
import { Play, Pause, RotateCcw, Flag } from 'lucide-react';

export default function Stopwatch() {
  const [time, setTime] = useState(0);
  const [running, setRunning] = useState(false);
  const [laps, setLaps] = useState<number[]>([]);
  const intervalRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined);

  useEffect(() => {
    if (running) intervalRef.current = setInterval(() => setTime((t) => t + 10), 10);
    else clearInterval(intervalRef.current);
    return () => clearInterval(intervalRef.current);
  }, [running]);

  const format = (ms: number) => {
    const m = Math.floor(ms / 60000);
    const s = Math.floor((ms % 60000) / 1000);
    const cs = Math.floor((ms % 1000) / 10);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${cs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 items-center justify-center p-4">
      <div className="text-5xl font-light tracking-wider mb-6 text-blue-100">{format(time)}</div>
      <div className="flex gap-3 mb-6">
        <button
          onClick={() => setRunning(!running)}
          className="p-3 rounded-full bg-blue-500/20 hover:bg-blue-500/30 text-blue-200 transition-colors"
        >
          {running ? <Pause size={20} /> : <Play size={20} className="ml-0.5" />}
        </button>
        <button
          onClick={() => {
            setRunning(false);
            setTime(0);
            setLaps([]);
          }}
          className="p-3 rounded-full bg-blue-500/10 hover:bg-blue-500/20 text-blue-300 transition-colors"
        >
          <RotateCcw size={20} />
        </button>
        <button
          onClick={() => setLaps((prev) => [time, ...prev].slice(0, 20))}
          className="p-3 rounded-full bg-blue-500/10 hover:bg-blue-500/20 text-blue-300 transition-colors"
        >
          <Flag size={20} />
        </button>
      </div>
      {laps.length > 0 && (
        <div className="w-full max-w-[200px] max-h-32 overflow-y-auto space-y-1">
          {laps.map((lap, i) => (
            <div
              key={i}
              className="flex justify-between text-xs text-blue-300/40 px-2 py-0.5 rounded bg-[#162032]"
            >
              <span>Lap {laps.length - i}</span>
              <span className="font-mono">{format(lap)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
