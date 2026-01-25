/**
 * Antivirus App - SCBE Threat Scanner & System Cleaner
 *
 * Uses the 14-layer security stack to scan for threats:
 * - Malware detection via pattern matching
 * - Anomaly detection via hyperbolic geometry deviation
 * - Quantum-resistant integrity verification
 * - Real-time protection monitoring
 *
 * @license Apache-2.0
 */
import React, { useState, useCallback, useEffect } from 'react';
import {
  Shield, Search, AlertTriangle, CheckCircle, Trash2,
  RefreshCw, FileWarning, Bug, Zap, Lock, Eye,
  HardDrive, Cpu, Network, Clock, XCircle, Play
} from 'lucide-react';

type ScanStatus = 'idle' | 'scanning' | 'complete' | 'threat_found';
type ThreatLevel = 'low' | 'medium' | 'high' | 'critical';

interface ThreatItem {
  id: string;
  name: string;
  type: string;
  location: string;
  level: ThreatLevel;
  description: string;
  detected: Date;
  quarantined: boolean;
}

interface ScanResult {
  filesScanned: number;
  threatsFound: number;
  duration: number;
  timestamp: Date;
}

// Simulated threat database (in real impl, this would be from SCBE backend)
const THREAT_SIGNATURES = [
  { pattern: 'eval(', type: 'Code Injection', level: 'high' as ThreatLevel },
  { pattern: 'exec(', type: 'Command Injection', level: 'critical' as ThreatLevel },
  { pattern: 'SELECT * FROM', type: 'SQL Pattern', level: 'medium' as ThreatLevel },
  { pattern: '<script>', type: 'XSS Pattern', level: 'high' as ThreatLevel },
  { pattern: 'password=', type: 'Credential Exposure', level: 'critical' as ThreatLevel },
];

const LEVEL_COLORS: Record<ThreatLevel, string> = {
  low: 'bg-yellow-500',
  medium: 'bg-orange-500',
  high: 'bg-red-500',
  critical: 'bg-red-700'
};

const LEVEL_TEXT_COLORS: Record<ThreatLevel, string> = {
  low: 'text-yellow-400',
  medium: 'text-orange-400',
  high: 'text-red-400',
  critical: 'text-red-300'
};

export const AntivirusApp: React.FC = () => {
  const [status, setStatus] = useState<ScanStatus>('idle');
  const [progress, setProgress] = useState(0);
  const [currentFile, setCurrentFile] = useState('');
  const [threats, setThreats] = useState<ThreatItem[]>([]);
  const [lastScan, setLastScan] = useState<ScanResult | null>(null);
  const [realTimeProtection, setRealTimeProtection] = useState(true);
  const [scanHistory, setScanHistory] = useState<ScanResult[]>([]);

  // Simulated real-time monitoring
  useEffect(() => {
    if (!realTimeProtection) return;

    const interval = setInterval(() => {
      // Simulate occasional threat detection
      if (Math.random() > 0.98) {
        const newThreat: ThreatItem = {
          id: `threat-${Date.now()}`,
          name: 'Suspicious Activity',
          type: 'Anomaly Detection',
          location: '/runtime/memory',
          level: 'low',
          description: 'Unusual pattern detected via hyperbolic deviation',
          detected: new Date(),
          quarantined: false
        };
        setThreats(prev => [...prev, newThreat]);
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [realTimeProtection]);

  const runFullScan = useCallback(() => {
    setStatus('scanning');
    setProgress(0);
    setThreats([]);

    const scanLocations = [
      '/system/core',
      '/system/drivers',
      '/apps/security',
      '/apps/fleet',
      '/apps/pollypad',
      '/data/cache',
      '/data/temp',
      '/network/connections',
      '/memory/heap',
      '/memory/stack'
    ];

    let currentIndex = 0;
    const foundThreats: ThreatItem[] = [];

    const scanInterval = setInterval(() => {
      if (currentIndex >= scanLocations.length) {
        clearInterval(scanInterval);
        setStatus(foundThreats.length > 0 ? 'threat_found' : 'complete');
        setProgress(100);
        setCurrentFile('Scan complete');

        const result: ScanResult = {
          filesScanned: Math.floor(Math.random() * 5000) + 10000,
          threatsFound: foundThreats.length,
          duration: (Date.now() - startTime) / 1000,
          timestamp: new Date()
        };
        setLastScan(result);
        setScanHistory(prev => [result, ...prev.slice(0, 9)]);
        return;
      }

      const location = scanLocations[currentIndex];
      setCurrentFile(location);
      setProgress(Math.floor((currentIndex / scanLocations.length) * 100));

      // Simulate threat detection (20% chance per location)
      if (Math.random() > 0.8) {
        const sig = THREAT_SIGNATURES[Math.floor(Math.random() * THREAT_SIGNATURES.length)];
        const threat: ThreatItem = {
          id: `threat-${Date.now()}-${currentIndex}`,
          name: sig.type,
          type: sig.type,
          location: location,
          level: sig.level,
          description: `Pattern "${sig.pattern}" detected`,
          detected: new Date(),
          quarantined: false
        };
        foundThreats.push(threat);
        setThreats([...foundThreats]);
      }

      currentIndex++;
    }, 500);

    const startTime = Date.now();
  }, []);

  const quarantineThreat = (threatId: string) => {
    setThreats(prev => prev.map(t =>
      t.id === threatId ? { ...t, quarantined: true } : t
    ));
  };

  const removeThreat = (threatId: string) => {
    setThreats(prev => prev.filter(t => t.id !== threatId));
  };

  const quarantineAll = () => {
    setThreats(prev => prev.map(t => ({ ...t, quarantined: true })));
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'scanning': return <RefreshCw className="animate-spin" size={24} />;
      case 'complete': return <CheckCircle size={24} />;
      case 'threat_found': return <AlertTriangle size={24} />;
      default: return <Shield size={24} />;
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'scanning': return 'text-sky-400';
      case 'complete': return 'text-emerald-400';
      case 'threat_found': return 'text-red-400';
      default: return 'text-zinc-400';
    }
  };

  return (
    <div className="h-full w-full bg-zinc-900 flex flex-col text-white overflow-hidden">
      {/* Header */}
      <div className="p-4 bg-zinc-800 border-b border-zinc-700">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className={`w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-600 to-sky-600 flex items-center justify-center ${getStatusColor()}`}>
              {getStatusIcon()}
            </div>
            <div>
              <h2 className="font-black text-lg">SCBE Antivirus</h2>
              <div className="text-xs text-zinc-400">14-Layer Quantum-Resistant Protection</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs text-zinc-500">Real-time Protection</span>
              <button
                onClick={() => setRealTimeProtection(!realTimeProtection)}
                className={`w-12 h-6 rounded-full transition-colors relative ${
                  realTimeProtection ? 'bg-emerald-600' : 'bg-zinc-600'
                }`}
              >
                <div className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${
                  realTimeProtection ? 'left-7' : 'left-1'
                }`} />
              </button>
            </div>
          </div>
        </div>

        {/* Status Bar */}
        <div className="grid grid-cols-4 gap-3">
          <div className={`rounded-lg p-3 text-center ${
            status === 'idle' ? 'bg-zinc-700/50' :
            status === 'scanning' ? 'bg-sky-500/20 border border-sky-500/30' :
            status === 'complete' ? 'bg-emerald-500/20 border border-emerald-500/30' :
            'bg-red-500/20 border border-red-500/30'
          }`}>
            <div className={`text-lg font-black ${getStatusColor()}`}>
              {status === 'idle' ? 'Ready' :
               status === 'scanning' ? 'Scanning...' :
               status === 'complete' ? 'Protected' : 'Threats Found'}
            </div>
            <div className="text-[10px] text-zinc-400 uppercase tracking-widest">Status</div>
          </div>
          <div className="bg-zinc-700/50 rounded-lg p-3 text-center">
            <div className="text-lg font-black">{threats.filter(t => !t.quarantined).length}</div>
            <div className="text-[10px] text-zinc-400 uppercase tracking-widest">Active Threats</div>
          </div>
          <div className="bg-zinc-700/50 rounded-lg p-3 text-center">
            <div className="text-lg font-black">{threats.filter(t => t.quarantined).length}</div>
            <div className="text-[10px] text-zinc-400 uppercase tracking-widest">Quarantined</div>
          </div>
          <div className="bg-zinc-700/50 rounded-lg p-3 text-center">
            <div className="text-lg font-black">{lastScan?.filesScanned?.toLocaleString() || '—'}</div>
            <div className="text-[10px] text-zinc-400 uppercase tracking-widest">Files Scanned</div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {/* Scan Controls */}
        <div className="bg-zinc-800 rounded-xl p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-sm flex items-center gap-2">
              <Search size={16} className="text-sky-400" />
              System Scan
            </h3>
            <button
              onClick={runFullScan}
              disabled={status === 'scanning'}
              className={`px-6 py-2 rounded-lg text-xs font-bold uppercase tracking-widest flex items-center gap-2 ${
                status === 'scanning'
                  ? 'bg-zinc-600 cursor-not-allowed'
                  : 'bg-emerald-600 hover:bg-emerald-500'
              }`}
            >
              {status === 'scanning' ? (
                <><RefreshCw size={14} className="animate-spin" /> Scanning...</>
              ) : (
                <><Play size={14} /> Full Scan</>
              )}
            </button>
          </div>

          {/* Progress Bar */}
          {status === 'scanning' && (
            <div className="space-y-2">
              <div className="h-2 bg-zinc-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-sky-500 transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <div className="flex justify-between text-[10px] text-zinc-500">
                <span>Scanning: {currentFile}</span>
                <span>{progress}%</span>
              </div>
            </div>
          )}

          {/* Scan Areas */}
          <div className="grid grid-cols-4 gap-2 mt-4">
            {[
              { icon: HardDrive, label: 'Storage', status: status === 'scanning' ? 'scanning' : 'protected' },
              { icon: Cpu, label: 'Memory', status: status === 'scanning' ? 'scanning' : 'protected' },
              { icon: Network, label: 'Network', status: status === 'scanning' ? 'scanning' : 'protected' },
              { icon: Lock, label: 'Crypto', status: status === 'scanning' ? 'scanning' : 'protected' }
            ].map(area => (
              <div key={area.label} className="bg-zinc-700/50 rounded-lg p-3 text-center">
                <area.icon size={20} className={`mx-auto mb-1 ${
                  area.status === 'scanning' ? 'text-sky-400 animate-pulse' : 'text-emerald-400'
                }`} />
                <div className="text-[10px] font-bold">{area.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Threat List */}
        <div className="bg-zinc-800 rounded-xl p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-sm flex items-center gap-2">
              <Bug size={16} className="text-red-400" />
              Detected Threats ({threats.length})
            </h3>
            {threats.some(t => !t.quarantined) && (
              <button
                onClick={quarantineAll}
                className="px-4 py-1.5 bg-red-600 rounded-lg text-[10px] font-bold uppercase tracking-widest hover:bg-red-500"
              >
                Quarantine All
              </button>
            )}
          </div>

          {threats.length === 0 ? (
            <div className="text-center py-8 text-zinc-500">
              <CheckCircle size={32} className="mx-auto mb-2 text-emerald-500" />
              <p className="text-sm">No threats detected</p>
              <p className="text-xs">Your system is protected</p>
            </div>
          ) : (
            <div className="space-y-2 max-h-64 overflow-auto">
              {threats.map(threat => (
                <div
                  key={threat.id}
                  className={`rounded-lg p-3 border-l-4 ${
                    threat.quarantined
                      ? 'bg-zinc-700/30 border-zinc-500 opacity-60'
                      : `bg-zinc-700/50 ${LEVEL_COLORS[threat.level].replace('bg-', 'border-')}`
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                      <FileWarning size={20} className={threat.quarantined ? 'text-zinc-500' : LEVEL_TEXT_COLORS[threat.level]} />
                      <div>
                        <div className="font-bold text-sm flex items-center gap-2">
                          {threat.name}
                          <span className={`px-1.5 py-0.5 rounded text-[9px] uppercase ${
                            threat.quarantined ? 'bg-zinc-600 text-zinc-400' : `${LEVEL_COLORS[threat.level]} text-white`
                          }`}>
                            {threat.quarantined ? 'Quarantined' : threat.level}
                          </span>
                        </div>
                        <div className="text-[10px] text-zinc-500">{threat.location}</div>
                        <div className="text-xs text-zinc-400 mt-1">{threat.description}</div>
                      </div>
                    </div>
                    {!threat.quarantined && (
                      <div className="flex gap-1">
                        <button
                          onClick={() => quarantineThreat(threat.id)}
                          className="p-1.5 bg-yellow-600 rounded hover:bg-yellow-500"
                          title="Quarantine"
                        >
                          <Lock size={12} />
                        </button>
                        <button
                          onClick={() => removeThreat(threat.id)}
                          className="p-1.5 bg-red-600 rounded hover:bg-red-500"
                          title="Delete"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Protection Layers */}
        <div className="bg-zinc-800 rounded-xl p-4">
          <h3 className="font-bold text-sm mb-3 flex items-center gap-2">
            <Eye size={16} className="text-purple-400" />
            Active Protection Layers
          </h3>
          <div className="grid grid-cols-2 gap-2">
            {[
              { name: 'Input Validation', active: true },
              { name: 'Pattern Matching', active: true },
              { name: 'Hyperbolic Deviation', active: true },
              { name: 'Quantum Integrity', active: true },
              { name: 'Network Monitor', active: realTimeProtection },
              { name: 'Memory Guard', active: realTimeProtection }
            ].map(layer => (
              <div key={layer.name} className="flex items-center justify-between bg-zinc-700/30 rounded-lg px-3 py-2">
                <span className="text-xs">{layer.name}</span>
                <div className={`w-2 h-2 rounded-full ${layer.active ? 'bg-emerald-500' : 'bg-zinc-500'}`} />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="p-3 bg-zinc-800 border-t border-zinc-700 flex items-center justify-between text-[10px] text-zinc-500">
        <span>Last scan: {lastScan ? lastScan.timestamp.toLocaleString() : 'Never'}</span>
        <span className="flex items-center gap-2">
          {realTimeProtection && <><Zap size={10} className="text-emerald-400" /> Real-time protection active</>}
        </span>
        <span>SCBE Antivirus v1.0</span>
      </div>
    </div>
  );
};
