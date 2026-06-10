import React from 'react';
import { HardDrive, Folder, FileText, Image, Music, Film } from 'lucide-react';

const DATA = [
  {
    name: 'Documents',
    size: 12.4,
    files: 1240,
    icon: <FileText size={16} />,
    color: 'bg-blue-500',
  },
  { name: 'Images', size: 28.6, files: 8430, icon: <Image size={16} />, color: 'bg-green-500' },
  { name: 'Music', size: 15.2, files: 3200, icon: <Music size={16} />, color: 'bg-purple-500' },
  { name: 'Videos', size: 45.8, files: 520, icon: <Film size={16} />, color: 'bg-red-500' },
  { name: 'System', size: 18.3, files: 45000, icon: <Folder size={16} />, color: 'bg-yellow-500' },
  { name: 'Other', size: 4.7, files: 890, icon: <HardDrive size={16} />, color: 'bg-cyan-500' },
];

const TOTAL = 125;

export default function DiskUsage() {
  const used = DATA.reduce((a, d) => a + d.size, 0);
  const free = TOTAL - used;

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 p-4">
      <h2 className="text-lg text-blue-200 font-semibold mb-4 flex items-center gap-2">
        <HardDrive size={18} className="text-blue-400" />
        Disk Usage
      </h2>
      <div className="bg-[#162032] rounded-xl p-4 border border-blue-500/10 mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-blue-300/40">Storage</span>
          <span className="text-xs text-blue-200/60">
            {used.toFixed(1)} GB / {TOTAL} GB
          </span>
        </div>
        <div className="w-full h-3 bg-blue-500/10 rounded-full overflow-hidden flex">
          {DATA.map((d) => (
            <div
              key={d.name}
              className={`h-full ${d.color}`}
              style={{ width: `${(d.size / TOTAL) * 100}%` }}
            />
          ))}
        </div>
        <div className="flex justify-between mt-2">
          <span className="text-xs text-green-400">{free.toFixed(1)} GB free</span>
          <span className="text-xs text-blue-300/40">
            {((used / TOTAL) * 100).toFixed(1)}% used
          </span>
        </div>
      </div>
      <div className="space-y-2 flex-1 overflow-y-auto">
        {DATA.map((d) => (
          <div
            key={d.name}
            className="flex items-center gap-3 px-3 py-2 rounded-lg bg-[#162032] border border-blue-500/5"
          >
            <span className={d.color.replace('bg-', 'text-')}>{d.icon}</span>
            <div className="flex-1">
              <div className="flex justify-between">
                <span className="text-xs text-blue-200/60">{d.name}</span>
                <span className="text-xs text-blue-200/60">{d.size} GB</span>
              </div>
              <div className="w-full h-1 bg-blue-500/10 rounded-full mt-1">
                <div
                  className={`h-full ${d.color} rounded-full`}
                  style={{ width: `${(d.size / used) * 100}%` }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
