import React, { useState, useEffect, useRef } from 'react';
import {
  Shield,
  ShieldCheck,
  ShieldAlert,
  Activity,
  Lock,
  Unlock,
  Eye,
  Radio,
  GitBranch,
  Atom,
  Orbit,
  Zap,
  Box,
  Layers,
} from 'lucide-react';

interface Agent {
  id: string;
  name: string;
  trustScore: number;
  driftScore: number;
  entropyLevel: number;
  capabilityScore: number;
  behaviorVector: [number, number, number];
  policyLevel: 'unrestricted' | 'supervised' | 'restricted' | 'quarantine';
  tokenUsage: number;
  identity: string;
  executions: number;
  lastAction: string;
  quorumState: 'active' | 'pending' | 'voting' | 'locked';
  capabilities: string[];
  restrictions: string[];
  axiomCompliance: Record<string, number>;
}

const AXIOMS = [
  {
    id: 'unitarity',
    name: 'Unitarity',
    icon: <Atom size={14} />,
    desc: 'Information conservation - no agent gains or loses capability without audit trail',
  },
  {
    id: 'locality',
    name: 'Locality',
    icon: <Box size={14} />,
    desc: 'Agents interact only through defined interfaces, no spooky action at a distance',
  },
  {
    id: 'causality',
    name: 'Causality',
    icon: <GitBranch size={14} />,
    desc: 'Every output has a traceable input; action chains form DAGs',
  },
  {
    id: 'symmetry',
    name: 'Symmetry',
    icon: <Layers size={14} />,
    desc: 'Equal agents have equal rights; policy applies uniformly across agent classes',
  },
  {
    id: 'composition',
    name: 'Composition',
    icon: <Orbit size={14} />,
    desc: 'Agent compositions must preserve individual accountability boundaries',
  },
];

const INITIAL_AGENTS: Agent[] = [
  {
    id: '1',
    name: 'explorer-alpha',
    trustScore: 92,
    driftScore: 3,
    entropyLevel: 12,
    capabilityScore: 78,
    behaviorVector: [0.8, 0.2, 0.1],
    policyLevel: 'unrestricted',
    tokenUsage: 145200,
    identity: '0x7a3f...e9d2',
    executions: 1240,
    lastAction: 'file_read /src/core',
    quorumState: 'active',
    capabilities: ['file_read', 'file_list', 'search', 'diff_view'],
    restrictions: [],
    axiomCompliance: { unitarity: 98, locality: 95, causality: 97, symmetry: 99, composition: 96 },
  },
  {
    id: '2',
    name: 'architect-beta',
    trustScore: 87,
    driftScore: 8,
    entropyLevel: 24,
    capabilityScore: 91,
    behaviorVector: [0.6, 0.7, 0.3],
    policyLevel: 'supervised',
    tokenUsage: 89200,
    identity: '0x4b8c...f1a5',
    executions: 856,
    lastAction: 'design_review api_gateway',
    quorumState: 'voting',
    capabilities: ['design', 'review', 'schema_gen', 'doc_gen'],
    restrictions: ['file_write'],
    axiomCompliance: { unitarity: 94, locality: 88, causality: 92, symmetry: 90, composition: 85 },
  },
  {
    id: '3',
    name: 'impl-gamma',
    trustScore: 78,
    driftScore: 15,
    entropyLevel: 38,
    capabilityScore: 85,
    behaviorVector: [0.4, 0.5, 0.8],
    policyLevel: 'restricted',
    tokenUsage: 234100,
    identity: '0x9e1d...c4b7',
    executions: 2345,
    lastAction: 'code_gen /src/modules/auth',
    quorumState: 'pending',
    capabilities: ['code_gen', 'test_gen', 'lint', 'refactor'],
    restrictions: ['deploy', 'prod_access', 'secret_read'],
    axiomCompliance: { unitarity: 82, locality: 75, causality: 80, symmetry: 85, composition: 78 },
  },
  {
    id: '4',
    name: 'review-delta',
    trustScore: 95,
    driftScore: 1,
    entropyLevel: 5,
    capabilityScore: 72,
    behaviorVector: [0.9, 0.1, 0.2],
    policyLevel: 'unrestricted',
    tokenUsage: 67800,
    identity: '0x2f5a...d8e3',
    executions: 567,
    lastAction: 'security_scan dependency_tree',
    quorumState: 'active',
    capabilities: ['review', 'security_scan', 'vuln_check', 'compliance'],
    restrictions: [],
    axiomCompliance: { unitarity: 99, locality: 98, causality: 99, symmetry: 97, composition: 98 },
  },
  {
    id: '5',
    name: 'security-epsilon',
    trustScore: 99,
    driftScore: 0,
    entropyLevel: 2,
    capabilityScore: 68,
    behaviorVector: [0.95, 0.05, 0.1],
    policyLevel: 'unrestricted',
    tokenUsage: 45600,
    identity: '0x8c4e...a2f1',
    executions: 890,
    lastAction: 'policy_enforce firewall_rule',
    quorumState: 'active',
    capabilities: ['security_scan', 'policy_enforce', 'audit', 'intrusion_detect'],
    restrictions: [],
    axiomCompliance: {
      unitarity: 100,
      locality: 100,
      causality: 100,
      symmetry: 100,
      composition: 100,
    },
  },
  {
    id: '6',
    name: 'debug-zeta',
    trustScore: 65,
    driftScore: 22,
    entropyLevel: 45,
    capabilityScore: 62,
    behaviorVector: [0.3, 0.4, 0.9],
    policyLevel: 'quarantine',
    tokenUsage: 123400,
    identity: '0x1a7b...e6c9',
    executions: 1567,
    lastAction: 'error_trace crash_dump_03',
    quorumState: 'locked',
    capabilities: ['debug', 'trace', 'profile'],
    restrictions: ['network_access', 'file_write', 'exec_cmd', 'secret_read'],
    axiomCompliance: { unitarity: 68, locality: 55, causality: 72, symmetry: 60, composition: 58 },
  },
];

const POLICY_COLORS: Record<string, string> = {
  unrestricted: 'text-green-400 bg-green-500/10 border-green-500/20',
  supervised: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20',
  restricted: 'text-orange-400 bg-orange-500/10 border-orange-500/20',
  quarantine: 'text-red-400 bg-red-500/10 border-red-500/20',
};

const QUORUM_ICONS: Record<string, React.ReactNode> = {
  active: <ShieldCheck size={14} className="text-green-400" />,
  pending: <Shield size={14} className="text-yellow-400" />,
  voting: <Activity size={14} className="text-blue-400 animate-pulse" />,
  locked: <Lock size={14} className="text-red-400" />,
};

// Poincare ball: map (x,y) to disk point
function poincareMap(x: number, y: number): [number, number] {
  const r = Math.sqrt(x * x + y * y);
  if (r === 0) return [0, 0];
  const scale = Math.tanh(r * 0.8) / r;
  return [x * scale, y * scale];
}

export default function GovernanceConsole() {
  const [agents, setAgents] = useState(INITIAL_AGENTS);
  const [selected, setSelected] = useState<string>('1');
  const [activeTab, setActiveTab] = useState<'agents' | 'axioms' | 'poincare'>('agents');
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const active = agents.find((a) => a.id === selected);

  // Update agent metrics periodically
  useEffect(() => {
    const interval = setInterval(() => {
      setAgents((prev) =>
        prev.map((a) => ({
          ...a,
          trustScore: Math.min(100, Math.max(0, a.trustScore + (Math.random() - 0.5) * 1.5)),
          driftScore: Math.max(0, a.driftScore + (Math.random() > 0.8 ? 0.5 : 0)),
          entropyLevel: Math.min(100, Math.max(0, a.entropyLevel + (Math.random() - 0.5) * 3)),
        }))
      );
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  // Poincare Ball Visualization
  useEffect(() => {
    if (activeTab !== 'poincare' || !canvasRef.current) return;
    const cvs = canvasRef.current;
    const ctx = cvs.getContext('2d');
    if (!ctx) return;

    const W = cvs.width;
    const H = cvs.height;
    const cx = W / 2;
    const cy = H / 2;
    const radius = Math.min(W, H) * 0.42;

    const draw = () => {
      ctx.clearRect(0, 0, W, H);

      // Background grid (hyperbolic)
      ctx.strokeStyle = 'rgba(59,130,246,0.08)';
      ctx.lineWidth = 0.5;
      for (let i = 1; i <= 4; i++) {
        ctx.beginPath();
        ctx.arc(cx, cy, (radius * i) / 4, 0, Math.PI * 2);
        ctx.stroke();
      }
      // Radial lines
      for (let a = 0; a < 12; a++) {
        const angle = (a * Math.PI) / 6;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(cx + Math.cos(angle) * radius, cy + Math.sin(angle) * radius);
        ctx.stroke();
      }

      // Outer boundary
      ctx.strokeStyle = 'rgba(59,130,246,0.25)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.stroke();

      // Label
      ctx.fillStyle = 'rgba(59,130,246,0.4)';
      ctx.font = '10px monospace';
      ctx.textAlign = 'center';
      ctx.fillText('Poincare Ball Model', cx, 14);
      ctx.fillStyle = 'rgba(148,163,184,0.3)';
      ctx.font = '9px monospace';
      ctx.fillText('SCBE Operator State Space', cx, 26);

      // Draw agents as points
      agents.forEach((a) => {
        const [px, py] = poincareMap(a.behaviorVector[0] - 0.5, a.behaviorVector[1] - 0.3);
        const screenX = cx + px * radius * 1.8;
        const screenY = cy + py * radius * 1.8;

        // Glow
        const gradient = ctx.createRadialGradient(screenX, screenY, 0, screenX, screenY, 12);
        const color =
          a.policyLevel === 'unrestricted'
            ? '74,222,128'
            : a.policyLevel === 'supervised'
              ? '250,204,21'
              : a.policyLevel === 'restricted'
                ? '251,146,60'
                : '248,113,113';
        gradient.addColorStop(0, `rgba(${color},0.3)`);
        gradient.addColorStop(1, `rgba(${color},0)`);
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(screenX, screenY, 12, 0, Math.PI * 2);
        ctx.fill();

        // Dot
        ctx.fillStyle = `rgba(${color},0.9)`;
        ctx.beginPath();
        ctx.arc(screenX, screenY, a.id === selected ? 5 : 3.5, 0, Math.PI * 2);
        ctx.fill();

        // Label
        ctx.fillStyle = 'rgba(148,163,184,0.5)';
        ctx.font = '8px monospace';
        ctx.textAlign = 'left';
        ctx.fillText(a.name.split('-')[0], screenX + 7, screenY + 2);
      });

      // Center reference
      ctx.fillStyle = 'rgba(59,130,246,0.15)';
      ctx.beginPath();
      ctx.arc(cx, cy, 3, 0, Math.PI * 2);
      ctx.fill();
    };

    draw();
  }, [activeTab, agents, selected]);

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-blue-500/10 bg-[#111d2e]">
        <div className="flex items-center gap-2">
          <Shield size={18} className="text-blue-400" />
          <div>
            <h2 className="text-sm font-semibold text-blue-200">SCBE Governance Console</h2>
            <div className="text-[9px] text-blue-400/30">
              Poincare-Ball Operator | 5 Physical Axioms
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-blue-500/10">
            <Zap size={12} className="text-green-400" />
            <span className="text-xs text-blue-300">
              {Math.round(agents.reduce((s, a) => s + a.trustScore, 0) / agents.length)}% T
            </span>
          </div>
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-blue-500/10">
            <Radio size={12} className="text-blue-400" />
            <span className="text-xs text-blue-300">
              {agents.filter((a) => a.quorumState === 'active').length}A
            </span>
          </div>
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-red-500/10">
            <ShieldAlert size={12} className="text-red-400" />
            <span className="text-xs text-red-300">
              {agents.filter((a) => a.policyLevel === 'quarantine').length}Q
            </span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-blue-500/10 bg-[#111d2e]">
        {(['agents', 'axioms', 'poincare'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-xs transition-colors ${activeTab === tab ? 'text-blue-200 border-b-2 border-blue-500 bg-blue-500/5' : 'text-blue-300/30 hover:text-blue-200/60'}`}
          >
            {tab === 'agents'
              ? 'Agent Registry'
              : tab === 'axioms'
                ? 'Physical Axioms'
                : 'Poincare Ball'}
          </button>
        ))}
      </div>

      {/* Content */}
      {activeTab === 'agents' && (
        <div className="flex flex-1 overflow-hidden">
          <div className="w-56 border-r border-blue-500/10 overflow-y-auto">
            <div className="px-3 py-2 text-[10px] uppercase tracking-wider text-blue-400/30">
              Agents ({agents.length})
            </div>
            {agents.map((a) => (
              <button
                key={a.id}
                onClick={() => setSelected(a.id)}
                className={`w-full text-left px-3 py-2.5 border-b border-blue-500/5 transition-colors ${selected === a.id ? 'bg-blue-500/10' : 'hover:bg-blue-500/5'}`}
              >
                <div className="flex items-center gap-2">
                  {QUORUM_ICONS[a.quorumState]}
                  <span className="text-xs text-blue-200/70">{a.name}</span>
                  <span
                    className={`ml-auto text-[9px] px-1 rounded ${POLICY_COLORS[a.policyLevel]}`}
                  >
                    {a.policyLevel[0].toUpperCase()}
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-1.5">
                  <div className="flex-1 h-1 bg-blue-500/10 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${a.trustScore}%`,
                        background:
                          a.trustScore > 80 ? '#4ade80' : a.trustScore > 50 ? '#facc15' : '#ef4444',
                      }}
                    />
                  </div>
                  <span className="text-[9px] text-blue-300/30 w-6 text-right">
                    {Math.round(a.trustScore)}
                  </span>
                </div>
                <div className="flex gap-2 mt-1">
                  <span className="text-[9px] text-blue-300/20">D:{a.driftScore}</span>
                  <span className="text-[9px] text-blue-300/20">E:{a.entropyLevel}</span>
                  <span className="text-[9px] text-blue-300/20">C:{a.capabilityScore}</span>
                </div>
              </button>
            ))}
          </div>

          {active && (
            <div className="flex-1 overflow-y-auto p-4">
              {/* Identity Card */}
              <div className="bg-[#162032] rounded-xl p-4 border border-blue-500/10 mb-4">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <div className="text-sm text-blue-200 font-semibold">{active.name}</div>
                    <div className="text-[10px] text-blue-300/30 font-mono">{active.identity}</div>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] ${POLICY_COLORS[active.policyLevel]}`}
                  >
                    {active.policyLevel}
                  </span>
                </div>

                {/* SCBE Metrics */}
                <div className="grid grid-cols-4 gap-2 mb-3">
                  {[
                    {
                      label: 'Trust',
                      value: Math.round(active.trustScore),
                      color:
                        active.trustScore > 80
                          ? 'text-green-400'
                          : active.trustScore > 50
                            ? 'text-yellow-400'
                            : 'text-red-400',
                    },
                    {
                      label: 'Drift',
                      value: active.driftScore,
                      color:
                        active.driftScore < 10
                          ? 'text-green-400'
                          : active.driftScore < 20
                            ? 'text-yellow-400'
                            : 'text-red-400',
                    },
                    {
                      label: 'Entropy',
                      value: active.entropyLevel,
                      color:
                        active.entropyLevel < 20
                          ? 'text-green-400'
                          : active.entropyLevel < 40
                            ? 'text-yellow-400'
                            : 'text-red-400',
                    },
                    { label: 'Capability', value: active.capabilityScore, color: 'text-blue-400' },
                  ].map((m) => (
                    <div key={m.label} className="bg-[#0d1926] rounded-lg p-2 text-center">
                      <div className="text-[10px] text-blue-300/30">{m.label}</div>
                      <div className={`text-lg font-light ${m.color}`}>{m.value}</div>
                    </div>
                  ))}
                </div>

                {/* Axiom Compliance Bars */}
                <div className="mb-3">
                  <div className="text-[10px] text-blue-300/30 mb-2">Axiom Compliance</div>
                  <div className="space-y-1.5">
                    {AXIOMS.map((ax) => {
                      const score = active.axiomCompliance[ax.id] || 0;
                      return (
                        <div key={ax.id} className="flex items-center gap-2">
                          <span className="text-blue-400/50">{ax.icon}</span>
                          <span className="text-[10px] text-blue-300/40 w-20">{ax.name}</span>
                          <div className="flex-1 h-1.5 bg-blue-500/10 rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all"
                              style={{
                                width: `${score}%`,
                                background:
                                  score > 90 ? '#4ade80' : score > 70 ? '#facc15' : '#ef4444',
                              }}
                            />
                          </div>
                          <span className="text-[10px] text-blue-300/30 w-8 text-right">
                            {score}%
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Behavior Vector */}
                <div className="bg-[#0d1926] rounded-lg p-2">
                  <div className="text-[10px] text-blue-300/30 mb-1">
                    Behavior Vector (b1, b2, b3)
                  </div>
                  <div className="flex gap-1">
                    {active.behaviorVector.map((v, i) => (
                      <div key={i} className="flex-1 bg-[#162032] rounded p-1.5 text-center">
                        <div className="text-[9px] text-blue-300/20">b{i + 1}</div>
                        <div className="text-xs text-blue-200 font-mono">{v.toFixed(2)}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Capabilities & Restrictions */}
              <div className="grid grid-cols-2 gap-3 mb-4">
                <div className="bg-[#162032] rounded-xl p-3 border border-blue-500/10">
                  <div className="text-[10px] uppercase tracking-wider text-green-400/40 mb-2 flex items-center gap-1">
                    <Unlock size={10} /> Capabilities
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {active.capabilities.map((c) => (
                      <span
                        key={c}
                        className="px-2 py-0.5 rounded text-[10px] bg-green-500/10 text-green-300/70"
                      >
                        {c}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="bg-[#162032] rounded-xl p-3 border border-blue-500/10">
                  <div className="text-[10px] uppercase tracking-wider text-red-400/40 mb-2 flex items-center gap-1">
                    <Lock size={10} /> Restrictions
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {active.restrictions.length === 0 ? (
                      <span className="text-[10px] text-blue-300/20">None</span>
                    ) : (
                      active.restrictions.map((r) => (
                        <span
                          key={r}
                          className="px-2 py-0.5 rounded text-[10px] bg-red-500/10 text-red-300/70"
                        >
                          {r}
                        </span>
                      ))
                    )}
                  </div>
                </div>
              </div>

              {/* Activity */}
              <div className="bg-[#162032] rounded-xl p-3 border border-blue-500/10">
                <div className="text-[10px] uppercase tracking-wider text-blue-400/30 mb-2">
                  Recent Activity
                </div>
                <div className="space-y-1.5">
                  {[
                    { action: active.lastAction, time: 'now', status: 'success' },
                    { action: 'axiom_check five_axioms_pass', time: '2m ago', status: 'success' },
                    { action: 'poincare_update state_vector', time: '5m ago', status: 'success' },
                    { action: 'trust_eval scbe_compute', time: '8m ago', status: 'success' },
                    {
                      action: 'entropy_measure behavior_drift',
                      time: '12m ago',
                      status: active.driftScore > 15 ? 'warning' : 'success',
                    },
                  ].map((log, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs">
                      <div
                        className={`w-1.5 h-1.5 rounded-full ${log.status === 'success' ? 'bg-green-400' : 'bg-yellow-400'}`}
                      />
                      <span className="text-blue-200/50 flex-1 font-mono">{log.action}</span>
                      <span className="text-[10px] text-blue-300/20">{log.time}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Physical Axioms Tab */}
      {activeTab === 'axioms' && (
        <div className="flex-1 overflow-y-auto p-4">
          <div className="mb-4">
            <h3 className="text-sm text-blue-200 font-semibold mb-1">
              Five Physical Axioms of Multi-Agent Governance
            </h3>
            <p className="text-xs text-blue-300/40">
              Composed Poincare-ball operator constraints derived from DARPA SCBE-AETHERMOORE
              research (Agreement HR0011-XX-3-XXXX)
            </p>
          </div>
          <div className="grid grid-cols-1 gap-3">
            {AXIOMS.map((ax, idx) => (
              <div key={ax.id} className="bg-[#162032] rounded-xl p-4 border border-blue-500/10">
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-400">
                    {ax.icon}
                  </div>
                  <div>
                    <div className="text-sm text-blue-200 font-medium">
                      Axiom {idx + 1}: {ax.name}
                    </div>
                    <div className="text-[10px] text-blue-400/30 font-mono">ID: {ax.id}</div>
                  </div>
                </div>
                <p className="text-xs text-blue-200/50 mb-3">{ax.desc}</p>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-blue-300/30">Enforcement:</span>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-green-500/10 text-green-400">
                    active
                  </span>
                  <span className="text-[10px] text-blue-300/30">Violation handling:</span>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-yellow-500/10 text-yellow-400">
                    escalate
                  </span>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-4 bg-[#162032] rounded-xl p-4 border border-blue-500/10">
            <h4 className="text-xs text-blue-200 font-semibold mb-2">SCBE Operator Formalism</h4>
            <div className="text-xs text-blue-200/40 font-mono space-y-1">
              <div>G(agent) = (Trust, Capability, Behavior, Entropy) in H^n</div>
              <div>Operator: O = U compose L compose C compose S compose Co</div>
              <div>State evolution: agent(t+1) = PoincareExp(agent(t), -grad(Loss))</div>
              <div>where Loss = alpha*T + beta*D + gamma*E + delta*V</div>
              <div className="text-blue-400/30 mt-2">
                // Poincare exponential map on hyperbolic manifold
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Poincare Ball Tab */}
      {activeTab === 'poincare' && (
        <div className="flex-1 flex flex-col items-center justify-center p-4">
          <canvas
            ref={canvasRef}
            width={500}
            height={400}
            className="rounded-xl border border-blue-500/10 bg-[#0a1420]"
          />
          <div className="mt-3 text-center">
            <div className="text-xs text-blue-200/60 mb-1">
              Agent State Space in Poincare Ball Model
            </div>
            <div className="text-[10px] text-blue-300/30">
              Hyperbolic geometry: tanh(r) boundary | agents near edge = high drift risk
            </div>
          </div>
          <div className="flex gap-4 mt-2">
            {agents.slice(0, 4).map((a) => (
              <button
                key={a.id}
                onClick={() => setSelected(a.id)}
                className={`flex items-center gap-1 px-2 py-1 rounded text-[10px] transition-colors ${selected === a.id ? 'bg-blue-500/20 text-blue-200' : 'text-blue-300/30 hover:text-blue-200/60'}`}
              >
                <div
                  className={`w-2 h-2 rounded-full ${a.policyLevel === 'unrestricted' ? 'bg-green-400' : a.policyLevel === 'supervised' ? 'bg-yellow-400' : a.policyLevel === 'restricted' ? 'bg-orange-400' : 'bg-red-400'}`}
                />
                {a.name}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
