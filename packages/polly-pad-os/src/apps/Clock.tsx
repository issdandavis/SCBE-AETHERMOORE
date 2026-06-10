import React, { useState, useEffect } from 'react';
import { Clock as ClockIcon, Globe, Plus, X } from 'lucide-react';

const ZONES = [
  { city: 'New York', tz: 'America/New_York' },
  { city: 'London', tz: 'Europe/London' },
  { city: 'Tokyo', tz: 'Asia/Tokyo' },
  { city: 'Sydney', tz: 'Australia/Sydney' },
  { city: 'Paris', tz: 'Europe/Paris' },
  { city: 'Dubai', tz: 'Asia/Dubai' },
  { city: 'Singapore', tz: 'Asia/Singapore' },
  { city: 'Los Angeles', tz: 'America/Los_Angeles' },
];

export default function Clock() {
  const [time, setTime] = useState(new Date());
  const [activeClocks, setActiveClocks] = useState([
    'America/New_York',
    'Europe/London',
    'Asia/Tokyo',
  ]);
  const [showAdd, setShowAdd] = useState(false);
  const [activeTab, setActiveTab] = useState<'clock' | 'world'>('clock');
  const [stopwatchRunning, setStopwatchRunning] = useState(false);
  const [stopwatchTime, setStopwatchTime] = useState(0);
  const [laps, setLaps] = useState<number[]>([]);

  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!stopwatchRunning) return;
    const interval = setInterval(() => setStopwatchTime((t) => t + 10), 10);
    return () => clearInterval(interval);
  }, [stopwatchRunning]);

  const formatTime = (date: Date, tz?: string) => {
    return new Intl.DateTimeFormat('en', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
      timeZone: tz,
    }).format(date);
  };
  const formatDate = (date: Date) =>
    date.toLocaleDateString('en', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  const formatOffset = (tz: string) => {
    const now = new Date();
    const utc = now.getTime() + now.getTimezoneOffset() * 60000;
    const city = new Date(
      utc +
        3600000 *
          (tz.includes('New_York')
            ? -5
            : tz.includes('London')
              ? 0
              : tz.includes('Tokyo')
                ? 9
                : tz.includes('Sydney')
                  ? 11
                  : tz.includes('Paris')
                    ? 1
                    : tz.includes('Dubai')
                      ? 4
                      : tz.includes('Singapore')
                        ? 8
                        : -8)
    );
    const diff = Math.round((city.getTime() - now.getTime()) / 3600000);
    return diff >= 0 ? `+${diff}h` : `${diff}h`;
  };

  const addClock = (tz: string) => {
    if (!activeClocks.includes(tz)) setActiveClocks([...activeClocks, tz]);
    setShowAdd(false);
  };
  const removeClock = (tz: string) => setActiveClocks(activeClocks.filter((c) => c !== tz));

  const formatStopwatch = (ms: number) => {
    const m = Math.floor(ms / 60000);
    const s = Math.floor((ms % 60000) / 1000);
    const cs = Math.floor((ms % 1000) / 10);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${cs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80">
      <div className="flex border-b border-blue-500/10">
        {(['clock', 'world'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 py-2 text-xs transition-colors ${activeTab === tab ? 'text-blue-200 border-b-2 border-blue-500' : 'text-blue-300/30 hover:text-blue-200/60'}`}
          >
            {tab === 'clock' ? 'Clock' : 'World'}
          </button>
        ))}
      </div>

      {activeTab === 'clock' ? (
        <div className="flex-1 flex flex-col items-center justify-center p-6">
          <div className="w-40 h-40 rounded-full border-4 border-blue-500/20 relative mb-6 shadow-2xl">
            {Array.from({ length: 12 }).map((_, i) => (
              <div
                key={i}
                className="absolute text-[10px] text-blue-300/40 font-medium"
                style={{
                  left: '50%',
                  top: '50%',
                  transform: `rotate(${i * 30}deg) translateY(-68px) rotate(-${i * 30}deg)`,
                  transformOrigin: 'center',
                }}
              >
                {i === 0 ? 12 : i}
              </div>
            ))}
            <div className="absolute inset-0 flex items-center justify-center">
              <div
                className="w-1.5 h-16 bg-blue-400/60 rounded-full origin-bottom"
                style={{
                  transform: `rotate(${(time.getHours() % 12) * 30 + time.getMinutes() * 0.5}deg) translateY(-50%)`,
                }}
              />
              <div
                className="w-1 h-20 bg-blue-400/80 rounded-full origin-bottom absolute"
                style={{ transform: `rotate(${time.getMinutes() * 6}deg) translateY(-50%)` }}
              />
              <div
                className="w-0.5 h-24 bg-red-400/70 rounded-full origin-bottom absolute"
                style={{ transform: `rotate(${time.getSeconds() * 6}deg) translateY(-50%)` }}
              />
              <div className="w-3 h-3 rounded-full bg-blue-500/80" />
            </div>
          </div>
          <div className="text-4xl font-light tracking-wider mb-2">{formatTime(time)}</div>
          <div className="text-sm text-blue-400/40">{formatDate(time)}</div>

          {/* Stopwatch */}
          <div className="mt-6 pt-4 border-t border-blue-500/10 w-full max-w-xs">
            <div className="text-center text-2xl font-mono mb-3">
              {formatStopwatch(stopwatchTime)}
            </div>
            <div className="flex justify-center gap-2 mb-2">
              <button
                onClick={() => setStopwatchRunning(!stopwatchRunning)}
                className="px-4 py-1.5 rounded-lg text-xs bg-blue-500/20 hover:bg-blue-500/30 transition-colors"
              >
                {stopwatchRunning ? 'Stop' : 'Start'}
              </button>
              <button
                onClick={() => {
                  setStopwatchRunning(false);
                  setStopwatchTime(0);
                  setLaps([]);
                }}
                className="px-4 py-1.5 rounded-lg text-xs bg-blue-500/10 hover:bg-blue-500/20 transition-colors"
              >
                Reset
              </button>
              <button
                onClick={() => setLaps([...laps, stopwatchTime])}
                className="px-4 py-1.5 rounded-lg text-xs bg-blue-500/10 hover:bg-blue-500/20 transition-colors"
              >
                Lap
              </button>
            </div>
            {laps.length > 0 && (
              <div className="max-h-20 overflow-y-auto space-y-0.5">
                {laps.map((lap, i) => (
                  <div key={i} className="text-[10px] text-blue-300/40 text-center">
                    Lap {i + 1}: {formatStopwatch(lap)}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm text-blue-200">World Clocks</h3>
            <button
              onClick={() => setShowAdd(!showAdd)}
              className="p-1 rounded hover:bg-blue-500/20 text-blue-400 transition-colors"
            >
              <Plus size={16} />
            </button>
          </div>
          {showAdd && (
            <div className="mb-3 p-2 bg-[#162032] rounded-lg border border-blue-500/10 space-y-1">
              {ZONES.filter((z) => !activeClocks.includes(z.tz)).map((z) => (
                <button
                  key={z.tz}
                  onClick={() => addClock(z.tz)}
                  className="w-full text-left px-2 py-1 text-xs text-blue-200/60 hover:bg-blue-500/10 rounded transition-colors flex items-center gap-2"
                >
                  <Globe size={12} />
                  {z.city}
                </button>
              ))}
            </div>
          )}
          <div className="space-y-2">
            {activeClocks.map((tz) => {
              const zone = ZONES.find((z) => z.tz === tz);
              return (
                <div
                  key={tz}
                  className="flex items-center justify-between bg-[#162032] rounded-lg p-3 border border-blue-500/10"
                >
                  <div>
                    <div className="text-xs text-blue-200 font-medium">{zone?.city || tz}</div>
                    <div className="text-[10px] text-blue-400/30">{formatOffset(tz)}</div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-lg font-light">{formatTime(time, tz)}</span>
                    <button
                      onClick={() => removeClock(tz)}
                      className="p-1 rounded hover:bg-red-500/20 text-blue-300/30 hover:text-red-400 transition-colors"
                    >
                      <X size={12} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
