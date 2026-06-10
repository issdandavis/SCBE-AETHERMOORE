import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Play, Pause, RotateCcw, Bell, Volume2, VolumeX } from 'lucide-react';

export default function Timer() {
  const [hours, setHours] = useState(0);
  const [minutes, setMinutes] = useState(5);
  const [seconds, setSeconds] = useState(0);
  const [remaining, setRemaining] = useState(300);
  const [running, setRunning] = useState(false);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [timeUp, setTimeUp] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);

  useEffect(() => {
    if (running && remaining > 0) {
      intervalRef.current = setInterval(() => setRemaining((r) => r - 1), 1000);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (remaining === 0 && running) {
        setRunning(false);
        setTimeUp(true);
        if (soundEnabled) playAlarm();
      }
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [running, remaining, soundEnabled]);

  const playAlarm = useCallback(() => {
    try {
      const ctx = new AudioContext();
      audioCtxRef.current = ctx;
      const playTone = (freq: number, duration: number, delay: number) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, ctx.currentTime + delay);
        gain.gain.setValueAtTime(0.3, ctx.currentTime + delay);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + delay + duration);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(ctx.currentTime + delay);
        osc.stop(ctx.currentTime + delay + duration);
      };
      // Alarm pattern: 3 beeps, repeated
      for (let repeat = 0; repeat < 3; repeat++) {
        const offset = repeat * 0.8;
        playTone(880, 0.2, offset);
        playTone(1100, 0.2, offset + 0.3);
        playTone(880, 0.2, offset + 0.6);
      }
    } catch {
      /* ignore audio errors */
    }
  }, []);

  const start = () => {
    if (!running && remaining === 0) {
      setRemaining(hours * 3600 + minutes * 60 + seconds);
      setTimeUp(false);
    }
    setRunning(!running);
  };

  const reset = () => {
    setRunning(false);
    setTimeUp(false);
    setRemaining(hours * 3600 + minutes * 60 + seconds);
  };

  const quickSet = (mins: number) => {
    setRunning(false);
    setTimeUp(false);
    setHours(0);
    setMinutes(mins);
    setSeconds(0);
    setRemaining(mins * 60);
  };

  const h = Math.floor(remaining / 3600);
  const m = Math.floor((remaining % 3600) / 60);
  const s = remaining % 60;
  const progress =
    hours * 3600 + minutes * 60 + seconds > 0
      ? 1 - remaining / (hours * 3600 + minutes * 60 + seconds || 1)
      : 0;

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 items-center justify-center p-4">
      {timeUp && (
        <div className="mb-4 px-4 py-2 rounded-xl bg-red-500/15 text-red-300 text-sm flex items-center gap-2 animate-pulse">
          <Bell size={16} /> Time's up!
        </div>
      )}

      <div className="relative mb-6">
        <svg width="180" height="180" viewBox="0 0 180 180">
          <circle cx="90" cy="90" r="80" fill="none" stroke="#162032" strokeWidth="8" />
          <circle
            cx="90"
            cy="90"
            r="80"
            fill="none"
            stroke={timeUp ? '#ef4444' : '#3b82f6'}
            strokeWidth="8"
            strokeDasharray={`${2 * Math.PI * 80}`}
            strokeDashoffset={`${2 * Math.PI * 80 * (1 - progress)}`}
            strokeLinecap="round"
            transform="rotate(-90 90 90)"
            className="transition-all duration-1000"
            style={{ opacity: running || timeUp ? 1 : 0.5 }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <div
            className={`text-4xl font-light tracking-wider font-mono ${timeUp ? 'text-red-300' : 'text-blue-100'}`}
          >
            {String(h).padStart(2, '0')}:{String(m).padStart(2, '0')}:{String(s).padStart(2, '0')}
          </div>
        </div>
      </div>

      {!running && !timeUp && (
        <div className="flex gap-2 mb-4">
          <div className="text-center">
            <div className="text-[10px] text-blue-300/30 mb-1">Hours</div>
            <input
              type="number"
              min={0}
              max={23}
              value={hours}
              onChange={(e) => setHours(Math.max(0, Math.min(23, Number(e.target.value))))}
              className="w-14 bg-[#162032] border border-blue-500/15 rounded-lg px-2 py-1 text-center text-sm outline-none"
            />
          </div>
          <div className="text-center">
            <div className="text-[10px] text-blue-300/30 mb-1">Minutes</div>
            <input
              type="number"
              min={0}
              max={59}
              value={minutes}
              onChange={(e) => setMinutes(Math.max(0, Math.min(59, Number(e.target.value))))}
              className="w-14 bg-[#162032] border border-blue-500/15 rounded-lg px-2 py-1 text-center text-sm outline-none"
            />
          </div>
          <div className="text-center">
            <div className="text-[10px] text-blue-300/30 mb-1">Seconds</div>
            <input
              type="number"
              min={0}
              max={59}
              value={seconds}
              onChange={(e) => setSeconds(Math.max(0, Math.min(59, Number(e.target.value))))}
              className="w-14 bg-[#162032] border border-blue-500/15 rounded-lg px-2 py-1 text-center text-sm outline-none"
            />
          </div>
        </div>
      )}

      <div className="flex gap-2 mb-4">
        {[1, 5, 10, 15, 25].map((mins) => (
          <button
            key={mins}
            onClick={() => quickSet(mins)}
            className="px-2 py-1 rounded-lg bg-[#162032] text-[10px] text-blue-300/40 hover:text-blue-200 hover:bg-blue-500/10 transition-colors"
          >
            {mins}m
          </button>
        ))}
      </div>

      <div className="flex gap-3 items-center">
        <button
          onClick={start}
          className="p-3 rounded-full bg-blue-500/20 hover:bg-blue-500/30 text-blue-200 transition-colors"
        >
          {running ? <Pause size={20} /> : <Play size={20} className="ml-0.5" />}
        </button>
        <button
          onClick={reset}
          className="p-3 rounded-full bg-blue-500/10 hover:bg-blue-500/20 text-blue-300 transition-colors"
        >
          <RotateCcw size={20} />
        </button>
        <button
          onClick={() => setSoundEnabled(!soundEnabled)}
          className="p-2 rounded-full bg-blue-500/5 hover:bg-blue-500/10 text-blue-300/40 hover:text-blue-300 transition-colors"
        >
          {soundEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
        </button>
      </div>
    </div>
  );
}
