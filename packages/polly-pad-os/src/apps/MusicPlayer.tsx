import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Play, Pause, SkipBack, SkipForward, Volume2, Shuffle, Repeat } from 'lucide-react';

interface Track {
  title: string;
  artist: string;
  bpm: number;
  notes: number[];
  type: 'ambient' | 'drums' | 'bass' | 'melody';
}

const TRACKS: Track[] = [
  {
    title: 'Ambient Dreams',
    artist: 'SynthWave',
    bpm: 80,
    type: 'ambient',
    notes: [261.63, 329.63, 392.0, 523.25, 392.0, 329.63, 293.66, 349.23],
  },
  {
    title: 'Digital Pulse',
    artist: 'Neon Lab',
    bpm: 120,
    type: 'drums',
    notes: [440, 0, 440, 0, 523.25, 0, 659.25, 0, 440, 0, 392, 0, 523.25, 0, 440, 0],
  },
  {
    title: 'Neon Horizon',
    artist: 'CyberDrift',
    bpm: 100,
    type: 'melody',
    notes: [
      329.63, 392.0, 440.0, 523.25, 440.0, 392.0, 349.23, 293.66, 261.63, 329.63, 392.0, 440.0,
    ],
  },
  {
    title: 'Deep Space',
    artist: 'Cosmic Flow',
    bpm: 65,
    type: 'ambient',
    notes: [174.61, 220.0, 261.63, 220.0, 196.0, 246.94, 293.66, 349.23],
  },
  {
    title: 'Rainy City',
    artist: 'Chill Lab',
    bpm: 90,
    type: 'bass',
    notes: [
      130.81, 146.83, 164.81, 174.61, 196.0, 174.61, 164.81, 146.83, 130.81, 110.0, 123.47, 130.81,
    ],
  },
  {
    title: 'Starlight',
    artist: 'Night Crawler',
    bpm: 110,
    type: 'melody',
    notes: [
      523.25, 587.33, 659.25, 783.99, 659.25, 587.33, 523.25, 493.88, 440.0, 523.25, 587.33, 659.25,
    ],
  },
];

export default function MusicPlayer() {
  const [currentTrack, setCurrentTrack] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [volume, setVolume] = useState(0.3);
  const [shuffle, setShuffle] = useState(false);
  const [repeat, setRepeat] = useState(false);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const noteIdxRef = useRef(0);
  const oscillatorsRef = useRef<OscillatorNode[]>([]);

  const getAudioCtx = () => {
    if (!audioCtxRef.current) {
      audioCtxRef.current = new AudioContext();
    }
    return audioCtxRef.current;
  };

  const stopOscillators = () => {
    oscillatorsRef.current.forEach((osc) => {
      try {
        osc.stop();
      } catch {
        /* already stopped */
      }
    });
    oscillatorsRef.current = [];
  };

  const playNote = useCallback(
    (freq: number, duration: number) => {
      if (freq <= 0) return;
      const ctx = getAudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      const track = TRACKS[currentTrack];

      osc.type =
        track.type === 'drums'
          ? 'square'
          : track.type === 'bass'
            ? 'sawtooth'
            : track.type === 'ambient'
              ? 'sine'
              : 'triangle';
      osc.frequency.setValueAtTime(freq, ctx.currentTime);

      gain.gain.setValueAtTime(volume * 0.15, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);

      // Add reverb-like effect for ambient
      if (track.type === 'ambient') {
        const delay = ctx.createDelay();
        delay.delayTime.value = 0.3;
        const delayGain = ctx.createGain();
        delayGain.gain.value = 0.3;
        osc.connect(delay);
        delay.connect(delayGain);
        delayGain.connect(ctx.destination);
      }

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + duration);
      oscillatorsRef.current.push(osc);
    },
    [currentTrack, volume]
  );

  const startPlayback = useCallback(() => {
    stopOscillators();
    const track = TRACKS[currentTrack];
    const beatDuration = 60 / track.bpm;
    const noteDuration = beatDuration * 0.8;

    noteIdxRef.current = 0;

    intervalRef.current = setInterval(() => {
      const idx = noteIdxRef.current % track.notes.length;
      playNote(track.notes[idx], noteDuration);
      noteIdxRef.current++;
      setProgress((p) => (p + 100 / track.notes.length) % 100);

      if (noteIdxRef.current >= track.notes.length && !repeat) {
        if (shuffle) setCurrentTrack(Math.floor(Math.random() * TRACKS.length));
        else setCurrentTrack((t) => (t + 1) % TRACKS.length);
        noteIdxRef.current = 0;
        setProgress(0);
      } else if (noteIdxRef.current >= track.notes.length && repeat) {
        noteIdxRef.current = 0;
        setProgress(0);
      }
    }, beatDuration * 1000);
  }, [currentTrack, playNote, repeat, shuffle]);

  useEffect(() => {
    if (isPlaying) startPlayback();
    else {
      if (intervalRef.current) clearInterval(intervalRef.current);
      stopOscillators();
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      stopOscillators();
    };
  }, [isPlaying, startPlayback]);

  useEffect(() => {
    if (isPlaying) {
      if (intervalRef.current) clearInterval(intervalRef.current);
      startPlayback();
    }
  }, [currentTrack]);

  const track = TRACKS[currentTrack];
  const formatTime = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}`;
  const elapsed = Math.floor((progress / 100) * ((track.notes.length * 60) / track.bpm));
  const total = Math.floor((track.notes.length * 60) / track.bpm);

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80">
      <div className="flex-1 flex flex-col items-center justify-center p-6">
        <div className="w-48 h-48 rounded-2xl bg-gradient-to-br from-blue-600/30 to-purple-600/30 border border-blue-500/15 flex items-center justify-center mb-6 shadow-2xl relative overflow-hidden">
          <div
            className={`absolute inset-0 flex items-center justify-center transition-all duration-300 ${isPlaying ? 'scale-110' : 'scale-100'}`}
          >
            <div
              className={`w-32 h-32 rounded-full border-4 border-blue-400/20 flex items-center justify-center ${isPlaying ? 'animate-spin' : ''}`}
              style={{ animationDuration: `${(60 / track.bpm) * 4}s` }}
            >
              <div className="w-20 h-20 rounded-full border-2 border-blue-400/30 flex items-center justify-center">
                <div className="w-4 h-4 rounded-full bg-blue-400/60" />
              </div>
            </div>
          </div>
          <div className="absolute bottom-3 text-center">
            <div className="text-[10px] text-blue-300/40 uppercase tracking-wider">
              {track.type}
            </div>
            <div className="text-xs text-blue-200/60">{track.bpm} BPM</div>
          </div>
        </div>
        <h3 className="text-lg font-semibold text-blue-100">{track.title}</h3>
        <p className="text-sm text-blue-300/40">{track.artist}</p>
      </div>

      <div className="px-6 pb-2">
        <input
          type="range"
          min={0}
          max={100}
          value={progress}
          onChange={(e) => setProgress(Number(e.target.value))}
          className="w-full accent-blue-500 h-1"
        />
        <div className="flex justify-between text-[10px] text-blue-300/30 mt-1">
          <span>{formatTime(elapsed)}</span>
          <span>{formatTime(total)}</span>
        </div>
      </div>

      <div className="flex items-center justify-center gap-4 pb-3">
        <button
          onClick={() => setShuffle(!shuffle)}
          className={`p-2 rounded-lg transition-colors ${shuffle ? 'text-blue-400 bg-blue-500/15' : 'text-blue-300/30 hover:text-blue-200'}`}
        >
          <Shuffle size={16} />
        </button>
        <button
          onClick={() => setCurrentTrack((t) => (t - 1 + TRACKS.length) % TRACKS.length)}
          className="p-2 rounded-lg text-blue-300/50 hover:text-blue-200 hover:bg-blue-500/10 transition-colors"
        >
          <SkipBack size={20} />
        </button>
        <button
          onClick={() => setIsPlaying(!isPlaying)}
          className="p-3 rounded-full bg-blue-500/25 text-blue-200 hover:bg-blue-500/35 transition-colors"
        >
          {isPlaying ? <Pause size={24} /> : <Play size={24} />}
        </button>
        <button
          onClick={() => setCurrentTrack((t) => (t + 1) % TRACKS.length)}
          className="p-2 rounded-lg text-blue-300/50 hover:text-blue-200 hover:bg-blue-500/10 transition-colors"
        >
          <SkipForward size={20} />
        </button>
        <button
          onClick={() => setRepeat(!repeat)}
          className={`p-2 rounded-lg transition-colors ${repeat ? 'text-blue-400 bg-blue-500/15' : 'text-blue-300/30 hover:text-blue-200'}`}
        >
          <Repeat size={16} />
        </button>
      </div>

      <div className="flex items-center gap-2 px-6 pb-3">
        <Volume2 size={14} className="text-blue-300/30" />
        <input
          type="range"
          min={0}
          max={100}
          value={volume * 100}
          onChange={(e) => setVolume(Number(e.target.value) / 100)}
          className="flex-1 accent-blue-500 h-1"
        />
        <span className="text-[10px] text-blue-300/30 w-6">{Math.round(volume * 100)}</span>
      </div>

      <div className="border-t border-blue-500/10 max-h-36 overflow-y-auto">
        {TRACKS.map((t, i) => (
          <button
            key={i}
            onClick={() => {
              setCurrentTrack(i);
              setProgress(0);
              setIsPlaying(true);
            }}
            className={`w-full flex items-center gap-3 px-4 py-2 text-left transition-colors ${i === currentTrack ? 'bg-blue-500/10' : 'hover:bg-blue-500/5'}`}
          >
            <span className="text-xs text-blue-300/30 w-4">{i + 1}</span>
            <div className="flex-1 min-w-0">
              <div
                className={`text-xs truncate ${i === currentTrack ? 'text-blue-200' : 'text-blue-200/60'}`}
              >
                {t.title}
              </div>
              <div className="text-[10px] text-blue-300/30">
                {t.artist} · {t.bpm} BPM · {t.type}
              </div>
            </div>
            <span className="text-[10px] text-blue-300/30">
              {formatTime(Math.floor((t.notes.length * 60) / t.bpm))}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
