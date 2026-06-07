import React, { useState, useEffect } from 'react';
import { Activity, Cpu, HardDrive, MemoryStick, Thermometer } from 'lucide-react';

export default function SystemMonitor() {
  const [stats, setStats] = useState({ cpu: 12, mem: 34, disk: 52, temp: 42, uptime: 0 });

  useEffect(() => {
    const interval = setInterval(() => {
      setStats((s) => ({
        cpu: Math.max(5, Math.min(95, s.cpu + (Math.random() - 0.5) * 10)),
        mem: Math.max(20, Math.min(80, s.mem + (Math.random() - 0.5) * 4)),
        disk: 52,
        temp: Math.max(35, Math.min(70, s.temp + (Math.random() - 0.5) * 3)),
        uptime: s.uptime + 1,
      }));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const formatUptime = (s: number) => `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`;

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 p-4">
      <h2 className="text-lg text-blue-200 font-semibold mb-4 flex items-center gap-2">
        <Activity size={18} className="text-blue-400" />
        System Monitor
      </h2>
      <div className="grid grid-cols-2 gap-3 mb-4">
        {[
          {
            icon: <Cpu size={20} />,
            label: 'CPU',
            value: stats.cpu.toFixed(1) + '%',
            color: 'text-blue-400',
            bar: 'bg-blue-500',
          },
          {
            icon: <MemoryStick size={20} />,
            label: 'Memory',
            value: stats.mem.toFixed(1) + '%',
            color: 'text-green-400',
            bar: 'bg-green-500',
          },
          {
            icon: <HardDrive size={20} />,
            label: 'Disk',
            value: stats.disk + '%',
            color: 'text-purple-400',
            bar: 'bg-purple-500',
          },
          {
            icon: <Thermometer size={20} />,
            label: 'Temp',
            value: stats.temp.toFixed(1) + '°C',
            color: 'text-red-400',
            bar: 'bg-red-500',
          },
        ].map((item) => (
          <div key={item.label} className="bg-[#162032] rounded-xl p-4 border border-blue-500/10">
            <div className="flex items-center gap-2 mb-2">
              <span className={item.color}>{item.icon}</span>
              <span className="text-xs text-blue-300/40">{item.label}</span>
            </div>
            <div className="text-2xl font-light mb-2">{item.value}</div>
            <div className="w-full h-1.5 bg-blue-500/10 rounded-full overflow-hidden">
              <div
                className={`h-full ${item.bar} rounded-full transition-all`}
                style={{ width: item.value }}
              />
            </div>
          </div>
        ))}
      </div>
      <div className="flex-1 bg-[#162032] rounded-xl border border-blue-500/10 p-3 overflow-auto">
        <div className="text-[10px] uppercase tracking-wider text-blue-400/30 mb-2">
          Process Table
        </div>
        <div className="space-y-1">
          {[
            'init',
            'kernel',
            'desktop',
            'terminal',
            'browser',
            'file-manager',
            'audio-server',
            'network-daemon',
            'window-manager',
            'app-launcher',
          ].map((proc, i) => (
            <div
              key={proc}
              className="flex items-center justify-between text-xs py-1 border-b border-blue-500/5"
            >
              <span className="text-blue-200/50">{proc}</span>
              <span className="text-blue-300/30">{(Math.random() * 5 + 0.1).toFixed(1)}%</span>
            </div>
          ))}
        </div>
      </div>
      <div className="text-xs text-blue-300/30 mt-2 text-right">
        Uptime: {formatUptime(stats.uptime)}
      </div>
    </div>
  );
}
