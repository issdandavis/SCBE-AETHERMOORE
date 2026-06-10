import React, { useState, useRef, useEffect } from 'react';
import { Mic, Square, Play, Trash2, Download, Pause } from 'lucide-react';

interface Recording {
  id: string;
  url: string;
  duration: number;
  date: number;
}

const STORAGE_KEY = 'linuxos_recordings_meta';

export default function VoiceRecorder() {
  const [recording, setRecording] = useState(false);
  const [time, setTime] = useState(0);
  const [recordings, setRecordings] = useState<Recording[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) return JSON.parse(saved);
    } catch {
      /* ignore */
    }
    return [];
  });
  const [playingId, setPlayingId] = useState<string | null>(null);
  const [audioLevel, setAudioLevel] = useState<number[]>(Array(30).fill(0));
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const animationRef = useRef<number | null>(null);

  useEffect(() => {
    const meta = recordings.map((r) => ({ id: r.id, duration: r.duration, date: r.date }));
    localStorage.setItem(STORAGE_KEY, JSON.stringify(meta));
  }, [recordings]);

  useEffect(() => {
    if (!recording) return;
    intervalRef.current = setInterval(() => setTime((t) => t + 1), 1000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [recording]);

  const animateWaveform = () => {
    if (!analyserRef.current) return;
    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    analyserRef.current.getByteFrequencyData(dataArray);
    const bars = Array.from({ length: 30 }, (_, i) => {
      const idx = Math.floor((i * dataArray.length) / 30);
      return dataArray[idx] / 255;
    });
    setAudioLevel(bars);
    animationRef.current = requestAnimationFrame(animateWaveform);
  };

  const start = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioContextRef.current = new AudioContext();
      const source = audioContextRef.current.createMediaStreamSource(stream);
      analyserRef.current = audioContextRef.current.createAnalyser();
      analyserRef.current.fftSize = 64;
      source.connect(analyserRef.current);

      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';
      const recorder = new MediaRecorder(stream, { mimeType });
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mimeType });
        const url = URL.createObjectURL(blob);
        const id = Date.now().toString();
        setRecordings((prev) => [{ id, url, duration: time, date: Date.now() }, ...prev]);
        stream.getTracks().forEach((t) => t.stop());
        if (audioContextRef.current?.state !== 'closed') audioContextRef.current?.close();
      };

      recorder.start(100);
      mediaRecorderRef.current = recorder;
      setRecording(true);
      setTime(0);
      animationRef.current = requestAnimationFrame(animateWaveform);
    } catch {
      // Fallback to timer-only mode
      setRecording(true);
      setTime(0);
      const bars = Array(30).fill(0);
      const interval = setInterval(() => {
        for (let i = 0; i < 30; i++) bars[i] = Math.random() * 0.5 + (recording ? 0.3 : 0);
        setAudioLevel([...bars]);
      }, 100);
      intervalRef.current = interval;
    }
  };

  const stop = () => {
    setRecording(false);
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    if (animationRef.current) cancelAnimationFrame(animationRef.current);
    setAudioLevel(Array(30).fill(0));
  };

  const playRecording = (rec: Recording) => {
    const audio = new Audio(rec.url);
    audio.play();
    setPlayingId(rec.id);
    audio.onended = () => setPlayingId(null);
  };

  const downloadRecording = (rec: Recording) => {
    const a = document.createElement('a');
    a.href = rec.url;
    a.download = `recording-${new Date(rec.date).toISOString().slice(0, 19).replace(/:/g, '-')}.webm`;
    a.click();
  };

  const deleteRecording = (id: string) => {
    setRecordings((prev) => {
      const rec = prev.find((r) => r.id === id);
      if (rec) URL.revokeObjectURL(rec.url);
      return prev.filter((r) => r.id !== id);
    });
  };

  const formatTime = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}`;

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 p-4 items-center">
      <h2 className="text-lg text-blue-200 font-semibold mb-4">Voice Recorder</h2>
      <div className="w-[300px] h-[80px] bg-[#162032] rounded-xl mb-4 border border-blue-500/10 flex items-end justify-center gap-0.5 px-2 pb-2 overflow-hidden">
        {audioLevel.map((level, i) => (
          <div
            key={i}
            className="w-2 rounded-full transition-all duration-75"
            style={{
              height: `${Math.max(4, level * 64)}px`,
              background: recording ? `hsl(${200 + level * 60}, 70%, 60%)` : '#1e3a5f',
            }}
          />
        ))}
      </div>
      <div className="text-3xl font-light mb-4 font-mono">{formatTime(time)}</div>
      <div className="flex gap-3 mb-6">
        {!recording ? (
          <button
            onClick={start}
            className="p-4 rounded-full bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors"
          >
            <Mic size={24} />
          </button>
        ) : (
          <button
            onClick={stop}
            className="p-4 rounded-full bg-red-500 text-white hover:bg-red-600 transition-colors animate-pulse"
          >
            <Square size={24} />
          </button>
        )}
      </div>
      {recordings.length > 0 && (
        <div className="w-full max-w-[340px]">
          <div className="text-[10px] uppercase tracking-wider text-blue-400/30 mb-2">
            Recordings ({recordings.length})
          </div>
          <div className="space-y-1.5 max-h-40 overflow-y-auto">
            {recordings.map((r) => (
              <div
                key={r.id}
                className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[#162032] border border-blue-500/5"
              >
                <button
                  onClick={() => playRecording(r)}
                  className="p-1.5 rounded-full bg-blue-500/20 text-blue-300 hover:bg-blue-500/30 transition-colors"
                >
                  {playingId === r.id ? <Pause size={10} /> : <Play size={10} />}
                </button>
                <span className="text-xs text-blue-200/60 flex-1">
                  Recording {recordings.length - recordings.indexOf(r)}
                </span>
                <span className="text-[10px] text-blue-300/30 font-mono">
                  {formatTime(r.duration)}
                </span>
                <button
                  onClick={() => downloadRecording(r)}
                  className="p-1 rounded hover:bg-blue-500/20 text-blue-300/30 hover:text-blue-300 transition-colors"
                >
                  <Download size={10} />
                </button>
                <button
                  onClick={() => deleteRecording(r.id)}
                  className="p-1 rounded hover:bg-red-500/20 text-blue-300/20 hover:text-red-400 transition-colors"
                >
                  <Trash2 size={10} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
