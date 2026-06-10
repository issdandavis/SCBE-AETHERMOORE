import React, { useState, useEffect } from 'react';
import { Wifi, Globe, Shield, Activity } from 'lucide-react';

export default function Network() {
  const [ping, setPing] = useState(12);
  const [download, setDownload] = useState(85);
  const [upload, setUpload] = useState(42);
  const [scanning, setScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setPing(Math.floor(Math.random() * 20 + 5));
      setDownload(Math.floor(Math.random() * 30 + 70));
      setUpload(Math.floor(Math.random() * 20 + 30));
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const scan = () => {
    setScanning(true);
    setScanProgress(0);
    let p = 0;
    const interval = setInterval(() => {
      p += 10;
      setScanProgress(p);
      if (p >= 100) {
        clearInterval(interval);
        setScanning(false);
      }
    }, 200);
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 p-4">
      <h2 className="text-lg text-blue-200 font-semibold mb-4 flex items-center gap-2">
        <Globe size={18} className="text-blue-400" />
        Network Tools
      </h2>
      <div className="grid grid-cols-3 gap-3 mb-4">
        {[
          {
            label: 'Ping',
            value: `${ping} ms`,
            icon: <Activity size={16} />,
            color: 'text-green-400',
          },
          {
            label: 'Download',
            value: `${download} Mbps`,
            icon: <Wifi size={16} />,
            color: 'text-blue-400',
          },
          {
            label: 'Upload',
            value: `${upload} Mbps`,
            icon: <Wifi size={16} />,
            color: 'text-purple-400',
          },
        ].map((item) => (
          <div
            key={item.label}
            className="bg-[#162032] rounded-xl p-3 border border-blue-500/10 text-center"
          >
            <div className={`${item.color} mb-1 flex justify-center`}>{item.icon}</div>
            <div className="text-lg font-light">{item.value}</div>
            <div className="text-[10px] text-blue-300/30">{item.label}</div>
          </div>
        ))}
      </div>
      <div className="bg-[#162032] rounded-xl p-4 border border-blue-500/10 mb-4">
        <div className="flex items-center gap-2 mb-3">
          <Shield size={14} className="text-green-400" />
          <span className="text-xs text-blue-200">Port Scanner</span>
        </div>
        <button
          onClick={scan}
          disabled={scanning}
          className="px-4 py-2 rounded-lg bg-blue-500/20 text-blue-200 text-xs hover:bg-blue-500/30 transition-colors disabled:opacity-50"
        >
          {scanning ? `Scanning... ${scanProgress}%` : 'Scan Common Ports'}
        </button>
        <div className="mt-3 space-y-1">
          {[
            { port: 80, name: 'HTTP', status: 'open' },
            { port: 443, name: 'HTTPS', status: 'open' },
            { port: 22, name: 'SSH', status: 'open' },
            { port: 21, name: 'FTP', status: 'closed' },
            { port: 3306, name: 'MySQL', status: 'closed' },
          ].map((s) => (
            <div key={s.port} className="flex items-center justify-between text-xs py-0.5">
              <span className="text-blue-200/50">
                {s.name} ({s.port})
              </span>
              <span
                className={`text-[10px] px-1.5 py-0.5 rounded ${s.status === 'open' ? 'bg-green-500/15 text-green-400' : 'bg-red-500/15 text-red-400'}`}
              >
                {s.status}
              </span>
            </div>
          ))}
        </div>
      </div>
      <div className="flex-1 bg-[#162032] rounded-xl p-4 border border-blue-500/10">
        <div className="text-xs text-blue-300/40 mb-2">Network Info</div>
        <div className="space-y-1.5 text-xs">
          {[
            ['IP Address', '192.168.1.100'],
            ['Subnet Mask', '255.255.255.0'],
            ['Gateway', '192.168.1.1'],
            ['DNS', '8.8.8.8'],
            ['MAC Address', '00:1A:2B:3C:4D:5E'],
          ].map(([label, value]) => (
            <div key={label} className="flex justify-between">
              <span className="text-blue-300/30">{label}</span>
              <span className="text-blue-200/60 font-mono">{value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
