import React, { useState } from 'react';
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  Clock,
  FileEdit,
  GitCommit,
  Shield,
  UserCheck,
} from 'lucide-react';

interface Approval {
  id: string;
  agent: string;
  identity: string;
  action: string;
  target: string;
  risk: 'low' | 'medium' | 'high' | 'critical';
  status: 'pending' | 'approved' | 'rejected';
  requestedAt: string;
  description: string;
  estimatedTokens: number;
}

const INITIAL: Approval[] = [
  {
    id: 'AP-001',
    agent: 'impl-gamma',
    identity: '0x9e1d...c4b7',
    action: 'file_write',
    target: '/src/modules/auth.ts',
    risk: 'high',
    status: 'pending',
    requestedAt: '2 min ago',
    description:
      'Agent requests permission to modify authentication module. Changes include token validation logic and session management. Drift score: 15.',
    estimatedTokens: 4200,
  },
  {
    id: 'AP-002',
    agent: 'impl-gamma',
    identity: '0x9e1d...c4b7',
    action: 'secret_read',
    target: '.env (DATABASE_URL)',
    risk: 'critical',
    status: 'pending',
    requestedAt: '5 min ago',
    description:
      'Agent requests access to database credentials. This is a RESTRICTED action per security policy §4.2. Auto-denied, awaiting override.',
    estimatedTokens: 150,
  },
  {
    id: 'AP-003',
    agent: 'architect-beta',
    identity: '0x4b8c...f1a5',
    action: 'deploy_preview',
    target: 'staging-env',
    risk: 'medium',
    status: 'approved',
    requestedAt: '8 min ago',
    description:
      'Deploy current branch to staging environment for integration testing. No production impact.',
    estimatedTokens: 800,
  },
  {
    id: 'AP-004',
    agent: 'debug-zeta',
    identity: '0x1a7b...e6c9',
    action: 'network_access',
    target: 'external-api (logs)',
    risk: 'high',
    status: 'rejected',
    requestedAt: '12 min ago',
    description:
      'Agent in quarantine requested external network access. Denied per isolation protocol.',
    estimatedTokens: 0,
  },
  {
    id: 'AP-005',
    agent: 'impl-gamma',
    identity: '0x9e1d...c4b7',
    action: 'code_gen',
    target: '/src/modules/auth.ts',
    risk: 'medium',
    status: 'pending',
    requestedAt: '1 min ago',
    description:
      'Generate unit tests for authentication module. Covers edge cases for token expiry and replay attacks.',
    estimatedTokens: 3200,
  },
];

const RISK_COLORS: Record<string, string> = {
  low: 'text-green-400 bg-green-500/10 border-green-500/20',
  medium: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20',
  high: 'text-orange-400 bg-orange-500/10 border-orange-500/20',
  critical: 'text-red-400 bg-red-500/10 border-red-500/20',
};

export default function ApprovalGates() {
  const [approvals, setApprovals] = useState<Approval[]>(INITIAL);
  const [selected, setSelected] = useState<string>('AP-001');

  const approve = (id: string) =>
    setApprovals((prev) =>
      prev.map((a) => (a.id === id ? { ...a, status: 'approved' as const } : a))
    );
  const reject = (id: string) =>
    setApprovals((prev) =>
      prev.map((a) => (a.id === id ? { ...a, status: 'rejected' as const } : a))
    );

  const pending = approvals.filter((a) => a.status === 'pending');
  const active = approvals.find((a) => a.id === selected);

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80">
      <div className="flex items-center justify-between px-4 py-3 border-b border-blue-500/10 bg-[#111d2e]">
        <div className="flex items-center gap-2">
          <Shield size={18} className="text-blue-400" />
          <h2 className="text-sm font-semibold text-blue-200">Approval Gates</h2>
          {pending.length > 0 && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/15 text-red-300 animate-pulse">
              {pending.length} pending
            </span>
          )}
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* List */}
        <div className="w-64 border-r border-blue-500/10 overflow-y-auto">
          {approvals.map((a) => (
            <button
              key={a.id}
              onClick={() => setSelected(a.id)}
              className={`w-full text-left px-3 py-2.5 border-b border-blue-500/5 transition-colors ${selected === a.id ? 'bg-blue-500/10' : 'hover:bg-blue-500/5'}`}
            >
              <div className="flex items-center gap-2 mb-1">
                {a.status === 'pending' ? (
                  <AlertTriangle size={12} className="text-yellow-400" />
                ) : a.status === 'approved' ? (
                  <CheckCircle size={12} className="text-green-400" />
                ) : (
                  <XCircle size={12} className="text-red-400" />
                )}
                <span className="text-xs text-blue-200/70 font-mono">{a.id}</span>
                <span className={`text-[9px] px-1 rounded ml-auto ${RISK_COLORS[a.risk]}`}>
                  {a.risk}
                </span>
              </div>
              <div className="text-[10px] text-blue-300/30">
                {a.action} on {a.target}
              </div>
            </button>
          ))}
        </div>

        {/* Detail */}
        {active && (
          <div className="flex-1 p-4 overflow-y-auto">
            <div className="bg-[#162032] rounded-xl p-4 border border-blue-500/10 mb-4">
              <div className="flex items-center gap-2 mb-3">
                <FileEdit size={14} className="text-blue-400" />
                <span className="text-sm text-blue-200 font-semibold font-mono">
                  {active.action}
                </span>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] ml-auto ${RISK_COLORS[active.risk]}`}
                >
                  {active.risk}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3 mb-3 text-xs">
                <div className="bg-[#0d1926] rounded-lg p-2">
                  <div className="text-blue-300/20 text-[10px] mb-0.5">Agent</div>
                  <div className="text-blue-200/70">{active.agent}</div>
                  <div className="text-[9px] text-blue-300/20 font-mono">{active.identity}</div>
                </div>
                <div className="bg-[#0d1926] rounded-lg p-2">
                  <div className="text-blue-300/20 text-[10px] mb-0.5">Target</div>
                  <div className="text-blue-200/70 font-mono">{active.target}</div>
                </div>
                <div className="bg-[#0d1926] rounded-lg p-2">
                  <div className="text-blue-300/20 text-[10px] mb-0.5">Requested</div>
                  <div className="text-blue-200/70">{active.requestedAt}</div>
                </div>
                <div className="bg-[#0d1926] rounded-lg p-2">
                  <div className="text-blue-300/20 text-[10px] mb-0.5">Est. Tokens</div>
                  <div className="text-blue-200/70">{active.estimatedTokens.toLocaleString()}</div>
                </div>
              </div>

              <div className="bg-[#0d1926] rounded-lg p-3 text-xs text-blue-200/50 mb-4">
                {active.description}
              </div>

              {active.status === 'pending' && (
                <div className="flex gap-2">
                  <button
                    onClick={() => approve(active.id)}
                    className="flex-1 flex items-center justify-center gap-2 py-2 rounded-lg bg-green-500/15 text-green-400 hover:bg-green-500/25 transition-colors text-xs"
                  >
                    <UserCheck size={14} /> Approve
                  </button>
                  <button
                    onClick={() => reject(active.id)}
                    className="flex-1 flex items-center justify-center gap-2 py-2 rounded-lg bg-red-500/15 text-red-400 hover:bg-red-500/25 transition-colors text-xs"
                  >
                    <XCircle size={14} /> Reject
                  </button>
                </div>
              )}

              {active.status === 'approved' && (
                <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-green-500/10 text-green-400 text-xs">
                  <CheckCircle size={14} /> Approved - Action executed successfully
                </div>
              )}

              {active.status === 'rejected' && (
                <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-500/10 text-red-400 text-xs">
                  <XCircle size={14} /> Rejected - Action blocked by policy
                </div>
              )}
            </div>

            {/* Policy Reference */}
            <div className="bg-[#162032] rounded-xl p-3 border border-blue-500/10">
              <div className="text-[10px] uppercase tracking-wider text-blue-400/30 mb-2 flex items-center gap-1">
                <GitCommit size={10} /> Policy Reference
              </div>
              <div className="space-y-1.5 text-[10px]">
                {[
                  { rule: '§2.1', desc: 'Read-only agents cannot write files' },
                  { rule: '§3.4', desc: 'Drift score > 20 triggers quarantine' },
                  { rule: '§4.2', desc: 'Secret access requires human approval' },
                  { rule: '§5.1', desc: 'High-risk actions need two-party approval' },
                  { rule: '§6.3', desc: 'All actions logged with cryptographic identity' },
                ].map((p) => (
                  <div key={p.rule} className="flex items-center gap-2 py-0.5">
                    <span className="text-blue-400/30 font-mono">{p.rule}</span>
                    <span className="text-blue-200/40">{p.desc}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
