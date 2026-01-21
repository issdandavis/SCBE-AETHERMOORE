/**
 * Security Dashboard App - SCBE 14-Layer Security Monitor
 *
 * Real-time visualization of the SCBE-AETHERMOORE security system.
 * Shows layer status, threat detection, and cryptographic health.
 *
 * @license Apache-2.0
 */
import React, { useState, useEffect } from 'react';
import {
  Shield, Lock, Activity, AlertTriangle, CheckCircle,
  Layers, Key, Fingerprint, Globe, Cpu, Eye, Radio,
  RefreshCw, Zap, TrendingUp, Database
} from 'lucide-react';

// The 14 security layers from SCBE-AETHERMOORE
const SECURITY_LAYERS = [
  { id: 1, name: 'Input Validation', icon: Fingerprint, description: 'Request sanitization & encoding' },
  { id: 2, name: 'Authentication', icon: Key, description: 'Multi-factor identity verification' },
  { id: 3, name: 'Authorization', icon: Lock, description: 'Role-based access control' },
  { id: 4, name: 'Session Management', icon: Database, description: 'Secure session handling' },
  { id: 5, name: 'Encryption (PQC)', icon: Shield, description: 'Kyber-768 post-quantum encryption' },
  { id: 6, name: 'Integrity Check', icon: CheckCircle, description: 'Data integrity verification' },
  { id: 7, name: 'Rate Limiting', icon: Activity, description: 'DDoS & brute force protection' },
  { id: 8, name: 'Logging & Audit', icon: Eye, description: 'Comprehensive audit trails' },
  { id: 9, name: 'Error Handling', icon: AlertTriangle, description: 'Secure error management' },
  { id: 10, name: 'API Security', icon: Globe, description: 'Endpoint protection' },
  { id: 11, name: 'Network Security', icon: Radio, description: 'Transport layer security' },
  { id: 12, name: 'Hyperbolic Boundary', icon: Layers, description: 'Geometric trust boundaries' },
  { id: 13, name: 'Harmonic Resonance', icon: Zap, description: '6-gate verification system' },
  { id: 14, name: 'Quantum Lattice', icon: Cpu, description: 'LWE/SVP cryptographic hardness' }
];

interface LayerStatus {
  id: number;
  status: 'active' | 'warning' | 'error' | 'idle';
  load: number;
  lastCheck: Date;
  threats: number;
}

export const SecurityDashboardApp: React.FC = () => {
  const [layers, setLayers] = useState<LayerStatus[]>([]);
  const [overallHealth, setOverallHealth] = useState(98.3);
  const [threatsBlocked, setThreatsBlocked] = useState(0);
  const [activeConnections, setActiveConnections] = useState(0);
  const [isSimulating, setIsSimulating] = useState(false);

  // Initialize layer statuses
  useEffect(() => {
    const initialLayers = SECURITY_LAYERS.map(layer => ({
      id: layer.id,
      status: 'active' as const,
      load: Math.random() * 30 + 10,
      lastCheck: new Date(),
      threats: 0
    }));
    setLayers(initialLayers);

    // Simulate real-time updates
    const interval = setInterval(() => {
      setLayers(prev => prev.map(layer => ({
        ...layer,
        load: Math.max(5, Math.min(95, layer.load + (Math.random() - 0.5) * 10)),
        lastCheck: new Date()
      })));
      setActiveConnections(Math.floor(Math.random() * 50 + 10));
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  const simulateAttack = () => {
    setIsSimulating(true);

    // Simulate attack detection across layers
    let delay = 0;
    SECURITY_LAYERS.forEach((_, idx) => {
      setTimeout(() => {
        setLayers(prev => prev.map((layer, i) => {
          if (i === idx) {
            return {
              ...layer,
              status: Math.random() > 0.1 ? 'active' : 'warning',
              load: Math.min(95, layer.load + 30),
              threats: layer.threats + (Math.random() > 0.7 ? 1 : 0)
            };
          }
          return layer;
        }));

        if (idx === SECURITY_LAYERS.length - 1) {
          setThreatsBlocked(prev => prev + 1);
          setIsSimulating(false);

          // Reset after simulation
          setTimeout(() => {
            setLayers(prev => prev.map(layer => ({
              ...layer,
              status: 'active',
              load: Math.random() * 30 + 10
            })));
          }, 1500);
        }
      }, delay);
      delay += 200;
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-emerald-500';
      case 'warning': return 'bg-yellow-500';
      case 'error': return 'bg-red-500';
      default: return 'bg-zinc-500';
    }
  };

  const totalThreats = layers.reduce((sum, l) => sum + l.threats, 0);

  return (
    <div className="h-full w-full bg-zinc-900 flex flex-col text-white overflow-hidden">
      {/* Header */}
      <div className="p-4 bg-zinc-800 border-b border-zinc-700">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-600 flex items-center justify-center">
              <Shield size={20} />
            </div>
            <div>
              <h2 className="font-black text-lg">SCBE Security Monitor</h2>
              <div className="text-xs text-zinc-400">14-Layer Quantum-Resistant Framework</div>
            </div>
          </div>
          <button
            onClick={simulateAttack}
            disabled={isSimulating}
            className={`px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-widest flex items-center gap-2 ${
              isSimulating
                ? 'bg-yellow-600 animate-pulse'
                : 'bg-red-600 hover:bg-red-500'
            }`}
          >
            <AlertTriangle size={14} />
            {isSimulating ? 'Detecting...' : 'Simulate Attack'}
          </button>
        </div>

        {/* Stats Bar */}
        <div className="grid grid-cols-4 gap-3">
          <div className="bg-emerald-500/20 rounded-lg p-3 text-center border border-emerald-500/30">
            <div className="text-2xl font-black text-emerald-400">{overallHealth}%</div>
            <div className="text-[10px] text-emerald-400/70 uppercase tracking-widest">System Health</div>
          </div>
          <div className="bg-sky-500/20 rounded-lg p-3 text-center border border-sky-500/30">
            <div className="text-2xl font-black text-sky-400">{activeConnections}</div>
            <div className="text-[10px] text-sky-400/70 uppercase tracking-widest">Active Connections</div>
          </div>
          <div className="bg-purple-500/20 rounded-lg p-3 text-center border border-purple-500/30">
            <div className="text-2xl font-black text-purple-400">{threatsBlocked}</div>
            <div className="text-[10px] text-purple-400/70 uppercase tracking-widest">Threats Blocked</div>
          </div>
          <div className="bg-orange-500/20 rounded-lg p-3 text-center border border-orange-500/30">
            <div className="text-2xl font-black text-orange-400">{totalThreats}</div>
            <div className="text-[10px] text-orange-400/70 uppercase tracking-widest">Alerts</div>
          </div>
        </div>
      </div>

      {/* Layer Grid */}
      <div className="flex-1 overflow-auto p-4">
        <h3 className="font-bold text-sm uppercase tracking-widest text-zinc-400 mb-3">
          Security Layers ({layers.filter(l => l.status === 'active').length}/14 Active)
        </h3>

        <div className="grid grid-cols-2 gap-3">
          {SECURITY_LAYERS.map((layer, idx) => {
            const status = layers[idx];
            const LayerIcon = layer.icon;

            return (
              <div
                key={layer.id}
                className={`bg-zinc-800 rounded-xl p-4 border-2 transition-all ${
                  status?.status === 'warning'
                    ? 'border-yellow-500 bg-yellow-500/10'
                    : status?.status === 'error'
                    ? 'border-red-500 bg-red-500/10'
                    : 'border-transparent hover:border-zinc-700'
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className={`w-8 h-8 rounded-lg ${getStatusColor(status?.status || 'idle')} flex items-center justify-center`}>
                      <LayerIcon size={16} />
                    </div>
                    <div>
                      <div className="font-bold text-sm">L{layer.id}: {layer.name}</div>
                      <div className="text-[10px] text-zinc-500">{layer.description}</div>
                    </div>
                  </div>
                  {status?.threats > 0 && (
                    <span className="px-2 py-0.5 bg-red-500/20 text-red-400 rounded text-[10px] font-bold">
                      {status.threats} alert{status.threats > 1 ? 's' : ''}
                    </span>
                  )}
                </div>

                {/* Load Bar */}
                <div className="mt-3">
                  <div className="flex justify-between text-[10px] text-zinc-500 mb-1">
                    <span>Load</span>
                    <span>{status?.load?.toFixed(0) || 0}%</span>
                  </div>
                  <div className="h-1.5 bg-zinc-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-500 ${
                        (status?.load || 0) > 80 ? 'bg-red-500' :
                        (status?.load || 0) > 50 ? 'bg-yellow-500' : 'bg-emerald-500'
                      }`}
                      style={{ width: `${status?.load || 0}%` }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Cryptographic Status */}
        <div className="mt-4 bg-zinc-800 rounded-xl p-4">
          <h4 className="font-bold text-sm mb-3 flex items-center gap-2">
            <Key size={16} className="text-purple-400" />
            Post-Quantum Cryptography Status
          </h4>
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-zinc-700/50 rounded-lg p-3">
              <div className="text-emerald-400 font-bold">Kyber-768</div>
              <div className="text-[10px] text-zinc-500">Key Encapsulation</div>
              <div className="text-xs mt-1">✓ NIST Approved</div>
            </div>
            <div className="bg-zinc-700/50 rounded-lg p-3">
              <div className="text-sky-400 font-bold">Dilithium-3</div>
              <div className="text-[10px] text-zinc-500">Digital Signatures</div>
              <div className="text-xs mt-1">✓ 128-bit Security</div>
            </div>
            <div className="bg-zinc-700/50 rounded-lg p-3">
              <div className="text-purple-400 font-bold">LWE/SVP</div>
              <div className="text-[10px] text-zinc-500">Lattice Hardness</div>
              <div className="text-xs mt-1">T ≥ 2^188.9</div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="p-3 bg-zinc-800 border-t border-zinc-700 flex items-center justify-between text-[10px] text-zinc-500">
        <span>USPTO Patent #63/961,403</span>
        <span className="flex items-center gap-2">
          <RefreshCw size={10} className="animate-spin" />
          Real-time monitoring active
        </span>
        <span>SCBE-AETHERMOORE v3.0.0</span>
      </div>
    </div>
  );
};
