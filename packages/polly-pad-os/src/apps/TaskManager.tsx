import React, { useState, useEffect } from 'react';
import { Activity, Cpu, HardDrive, MemoryStick, XCircle } from 'lucide-react';

interface Process {
  pid: number;
  name: string;
  cpu: number;
  mem: number;
  status: 'running' | 'sleeping';
}

const PROCESS_NAMES = [
  'init',
  'desktop',
  'terminal',
  'browser',
  'file-manager',
  'text-editor',
  'calculator',
  'calendar',
  'settings',
  'audio-daemon',
  'network-manager',
  'display-server',
  'window-manager',
  'notification-daemon',
  'system-daemon',
  'app-launcher',
  'file-watcher',
  'input-handler',
];

export default function TaskManager() {
  const [processes, setProcesses] = useState<Process[]>([]);
  const [sortBy, setSortBy] = useState<'cpu' | 'mem' | 'pid'>('cpu');
  const [search, setSearch] = useState('');
  const [cpuUsage, setCpuUsage] = useState(12);
  const [memUsage, setMemUsage] = useState(34);
  const [uptime, setUptime] = useState(0);

  useEffect(() => {
    const generate = () => {
      const procs: Process[] = PROCESS_NAMES.map((name, i) => ({
        pid: (i + 1) * 123,
        name,
        cpu: Math.random() * 8 + (name === 'desktop' ? 5 : 0),
        mem: Math.random() * 50 + 10,
        status: Math.random() > 0.3 ? 'running' : 'sleeping',
      }));
      setProcesses(procs);
      setCpuUsage(Math.round(8 + Math.random() * 15));
      setMemUsage(Math.round(30 + Math.random() * 10));
    };
    generate();
    const interval = setInterval(generate, 2000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const interval = setInterval(() => setUptime((u) => u + 1), 1000);
    return () => clearInterval(interval);
  }, []);

  const killProcess = (pid: number) => setProcesses((prev) => prev.filter((p) => p.pid !== pid));

  const sorted = [...processes]
    .filter((p) => p.name.includes(search.toLowerCase()))
    .sort((a, b) => b[sortBy] - a[sortBy]);

  const formatUptime = (s: number) =>
    `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m ${s % 60}s`;

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80">
      {/* Stats */}
      <div className="grid grid-cols-3 gap-3 p-3 border-b border-blue-500/10">
        <div className="bg-[#162032] rounded-xl p-3 border border-blue-500/10">
          <div className="flex items-center gap-2 mb-2">
            <Cpu size={14} className="text-blue-400" />
            <span className="text-xs text-blue-300/40">CPU</span>
          </div>
          <div className="text-2xl font-light">{cpuUsage}%</div>
          <div className="w-full h-1.5 bg-blue-500/10 rounded-full mt-2 overflow-hidden">
            <div
              className="h-full bg-blue-500/60 rounded-full transition-all"
              style={{ width: `${cpuUsage}%` }}
            />
          </div>
        </div>
        <div className="bg-[#162032] rounded-xl p-3 border border-blue-500/10">
          <div className="flex items-center gap-2 mb-2">
            <MemoryStick size={14} className="text-green-400" />
            <span className="text-xs text-blue-300/40">Memory</span>
          </div>
          <div className="text-2xl font-light">{memUsage}%</div>
          <div className="w-full h-1.5 bg-green-500/10 rounded-full mt-2 overflow-hidden">
            <div
              className="h-full bg-green-500/60 rounded-full transition-all"
              style={{ width: `${memUsage}%` }}
            />
          </div>
        </div>
        <div className="bg-[#162032] rounded-xl p-3 border border-blue-500/10">
          <div className="flex items-center gap-2 mb-2">
            <HardDrive size={14} className="text-purple-400" />
            <span className="text-xs text-blue-300/40">Uptime</span>
          </div>
          <div className="text-lg font-light">{formatUptime(uptime)}</div>
          <div className="text-[10px] text-blue-300/30 mt-1">{processes.length} processes</div>
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-blue-500/10">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search processes..."
          className="flex-1 bg-[#162032] border border-blue-500/10 rounded-lg px-2.5 py-1 text-xs outline-none focus:border-blue-500/30"
        />
        <button
          onClick={() => setSortBy('cpu')}
          className={`px-2.5 py-1 rounded-lg text-xs transition-colors ${sortBy === 'cpu' ? 'bg-blue-500/20 text-blue-200' : 'bg-[#162032] text-blue-300/40 hover:text-blue-200'}`}
        >
          CPU
        </button>
        <button
          onClick={() => setSortBy('mem')}
          className={`px-2.5 py-1 rounded-lg text-xs transition-colors ${sortBy === 'mem' ? 'bg-blue-500/20 text-blue-200' : 'bg-[#162032] text-blue-300/40 hover:text-blue-200'}`}
        >
          Mem
        </button>
        <button
          onClick={() => setSortBy('pid')}
          className={`px-2.5 py-1 rounded-lg text-xs transition-colors ${sortBy === 'pid' ? 'bg-blue-500/20 text-blue-200' : 'bg-[#162032] text-blue-300/40 hover:text-blue-200'}`}
        >
          PID
        </button>
      </div>

      {/* Process List */}
      <div className="flex-1 overflow-y-auto">
        <div className="grid grid-cols-[60px_1fr_60px_60px_60px_30px] gap-2 px-3 py-1.5 text-[10px] uppercase text-blue-400/30 border-b border-blue-500/5">
          <span>PID</span>
          <span>Name</span>
          <span>CPU</span>
          <span>Mem</span>
          <span>Status</span>
          <span></span>
        </div>
        {sorted.map((p) => (
          <div
            key={p.pid}
            className="grid grid-cols-[60px_1fr_60px_60px_60px_30px] gap-2 px-3 py-1.5 text-xs items-center hover:bg-blue-500/5 transition-colors border-b border-blue-500/5"
          >
            <span className="text-blue-300/40">{p.pid}</span>
            <span className="text-blue-200/70">{p.name}</span>
            <span className="text-blue-300/40">{p.cpu.toFixed(1)}%</span>
            <span className="text-blue-300/40">{p.mem.toFixed(0)}MB</span>
            <span
              className={`text-[10px] ${p.status === 'running' ? 'text-green-400/60' : 'text-blue-400/40'}`}
            >
              {p.status}
            </span>
            <button
              onClick={() => killProcess(p.pid)}
              className="p-0.5 rounded hover:bg-red-500/20 text-blue-300/20 hover:text-red-400 transition-colors"
            >
              <XCircle size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
