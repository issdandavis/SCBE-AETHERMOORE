import React, { useState, useEffect } from 'react';

export default function BinaryClock() {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  const toBinary = (n: number, bits: number) => n.toString(2).padStart(bits, '0').split('');
  const h = toBinary(time.getHours(), 5);
  const m = toBinary(time.getMinutes(), 6);
  const s = toBinary(time.getSeconds(), 6);

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 items-center justify-center p-4">
      <h2 className="text-lg text-blue-200 font-semibold mb-6">Binary Clock</h2>
      <div className="space-y-4">
        {[
          { label: 'Hours', bits: h },
          { label: 'Minutes', bits: m },
          { label: 'Seconds', bits: s },
        ].map((row) => (
          <div key={row.label} className="flex items-center gap-3">
            <span className="text-xs text-blue-300/30 w-14 text-right">{row.label}</span>
            <div className="flex gap-1.5">
              {row.bits.map((bit, i) => (
                <div
                  key={i}
                  className={`w-6 h-6 rounded transition-all ${bit === '1' ? 'bg-blue-500 shadow-lg shadow-blue-500/30' : 'bg-blue-500/10'}`}
                />
              ))}
            </div>
            <span className="text-xs text-blue-300/30 w-6">
              {row.label === 'Hours'
                ? time.getHours()
                : row.label === 'Minutes'
                  ? time.getMinutes()
                  : time.getSeconds()}
            </span>
          </div>
        ))}
      </div>
      <div className="mt-6 text-xs text-blue-300/20">Each column represents a binary digit</div>
    </div>
  );
}
