import React, { useState } from 'react';
import { Play, Cpu, MemoryStick, Zap } from 'lucide-react';

export default function Benchmark() {
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState<{ cpu: number; mem: number; render: number } | null>(null);

  const start = () => {
    setRunning(true);
    setProgress(0);
    setResults(null);
    let p = 0;
    const interval = setInterval(() => {
      p += 5;
      setProgress(p);
      if (p >= 100) {
        clearInterval(interval);
        setRunning(false);
        setResults({
          cpu: 850 + Math.floor(Math.random() * 200),
          mem: 1200 + Math.floor(Math.random() * 300),
          render: 60 + Math.floor(Math.random() * 15),
        });
      }
    }, 150);
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 p-4 items-center">
      <h2 className="text-lg text-blue-200 font-semibold mb-4 flex items-center gap-2">
        <Zap size={18} className="text-yellow-400" />
        Benchmark
      </h2>
      {!running && !results && (
        <button
          onClick={start}
          className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-blue-500/20 hover:bg-blue-500/30 text-blue-200 text-sm transition-colors"
        >
          <Play size={16} /> Start Benchmark
        </button>
      )}
      {running && (
        <div className="w-full max-w-[300px]">
          <div className="text-xs text-blue-300/40 mb-2 text-center">Running tests...</div>
          <div className="w-full h-2 bg-blue-500/10 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="text-xs text-blue-300/30 mt-1 text-center">{progress}%</div>
        </div>
      )}
      {results && (
        <div className="w-full max-w-[300px] space-y-3">
          <div className="bg-[#162032] rounded-xl p-4 border border-blue-500/10">
            <div className="flex items-center gap-2 mb-1">
              <Cpu size={16} className="text-blue-400" />
              <span className="text-xs text-blue-300/40">CPU Score</span>
            </div>
            <div className="text-2xl text-blue-200">{results.cpu}</div>
          </div>
          <div className="bg-[#162032] rounded-xl p-4 border border-blue-500/10">
            <div className="flex items-center gap-2 mb-1">
              <MemoryStick size={16} className="text-green-400" />
              <span className="text-xs text-blue-300/40">Memory Score</span>
            </div>
            <div className="text-2xl text-blue-200">{results.mem}</div>
          </div>
          <div className="bg-[#162032] rounded-xl p-4 border border-blue-500/10">
            <div className="flex items-center gap-2 mb-1">
              <Zap size={16} className="text-yellow-400" />
              <span className="text-xs text-blue-300/40">FPS (render)</span>
            </div>
            <div className="text-2xl text-blue-200">{results.render}</div>
          </div>
          <button
            onClick={start}
            className="w-full py-2 rounded-lg bg-blue-500/20 text-blue-200 text-xs hover:bg-blue-500/30 transition-colors"
          >
            Run Again
          </button>
        </div>
      )}
    </div>
  );
}
