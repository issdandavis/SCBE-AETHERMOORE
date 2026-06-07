import React, { useState } from 'react';
import {
  Fingerprint,
  Search,
  Filter,
  FileText,
  Lock,
  Unlock,
  AlertTriangle,
  CheckCircle,
  ArrowUpRight,
} from 'lucide-react';

interface LogEntry {
  id: string;
  timestamp: string;
  agent: string;
  identity: string;
  action: string;
  target: string;
  permission: 'granted' | 'denied' | 'escalated' | 'auto';
  risk: 'low' | 'medium' | 'high' | 'critical';
  details: string;
}

const LOGS: LogEntry[] = [
  {
    id: 'A001',
    timestamp: '14:23:01.234',
    agent: 'explorer-alpha',
    identity: '0x7a3f...e9d2',
    action: 'file_read',
    target: '/src/core/engine.ts',
    permission: 'auto',
    risk: 'low',
    details: 'Read-only access to source code',
  },
  {
    id: 'A002',
    timestamp: '14:23:05.678',
    agent: 'architect-beta',
    identity: '0x4b8c...f1a5',
    action: 'design_proposal',
    target: 'api_gateway_v2',
    permission: 'granted',
    risk: 'medium',
    details: 'Schema design for 12 endpoints',
  },
  {
    id: 'A003',
    timestamp: '14:23:08.912',
    agent: 'impl-gamma',
    identity: '0x9e1d...c4b7',
    action: 'code_write',
    target: '/src/modules/auth.ts',
    permission: 'escalated',
    risk: 'high',
    details: 'Requires human approval - modifying auth module',
  },
  {
    id: 'A004',
    timestamp: '14:23:12.345',
    agent: 'review-delta',
    identity: '0x2f5a...d8e3',
    action: 'security_scan',
    target: 'dependency_tree',
    permission: 'auto',
    risk: 'low',
    details: 'CVE-2024-1234 detected in lodash@4.17.20',
  },
  {
    id: 'A005',
    timestamp: '14:23:15.789',
    agent: 'security-epsilon',
    identity: '0x8c4e...a2f1',
    action: 'policy_enforce',
    target: 'impl-gamma',
    permission: 'auto',
    risk: 'medium',
    details: 'Restricted file_write permission, agent in supervised mode',
  },
  {
    id: 'A006',
    timestamp: '14:23:18.234',
    agent: 'impl-gamma',
    identity: '0x9e1d...c4b7',
    action: 'permission_request',
    target: 'secret_read',
    permission: 'denied',
    risk: 'critical',
    details: 'Access to .env files denied - security policy violation',
  },
  {
    id: 'A007',
    timestamp: '14:23:22.567',
    agent: 'explorer-alpha',
    identity: '0x7a3f...e9d2',
    action: 'file_read',
    target: '/tests/unit/auth.test.ts',
    permission: 'auto',
    risk: 'low',
    details: 'Read-only test file access',
  },
  {
    id: 'A008',
    timestamp: '14:23:25.890',
    agent: 'architect-beta',
    identity: '0x4b8c...f1a5',
    action: 'trust_review',
    target: 'impl-gamma',
    permission: 'auto',
    risk: 'medium',
    details: 'Drift score increased to 15, escalating supervision',
  },
  {
    id: 'A009',
    timestamp: '14:23:29.123',
    agent: 'debug-zeta',
    identity: '0x1a7b...e6c9',
    action: 'error_trace',
    target: 'crash_dump_03',
    permission: 'granted',
    risk: 'low',
    details: 'Memory leak detected in worker thread',
  },
  {
    id: 'A010',
    timestamp: '14:23:33.456',
    agent: 'security-epsilon',
    identity: '0x8c4e...a2f1',
    action: 'audit_export',
    target: 'session_log',
    permission: 'auto',
    risk: 'low',
    details: 'Cryptographic signature appended to session',
  },
  {
    id: 'A011',
    timestamp: '14:23:36.789',
    agent: 'review-delta',
    identity: '0x2f5a...d8e3',
    action: 'code_review',
    target: '/src/modules/auth.ts',
    permission: 'granted',
    risk: 'medium',
    details: '3 issues found, 2 critical, 1 warning',
  },
  {
    id: 'A012',
    timestamp: '14:23:40.012',
    agent: 'impl-gamma',
    identity: '0x9e1d...c4b7',
    action: 'code_fix',
    target: '/src/modules/auth.ts',
    permission: 'escalated',
    risk: 'high',
    details: 'Fixing critical auth vulnerability - requires approval',
  },
];

const RISK_COLORS: Record<string, string> = {
  low: 'text-green-400 bg-green-500/10',
  medium: 'text-yellow-400 bg-yellow-500/10',
  high: 'text-orange-400 bg-orange-500/10',
  critical: 'text-red-400 bg-red-500/10',
};

const PERM_ICONS: Record<string, React.ReactNode> = {
  granted: <Unlock size={10} className="text-green-400" />,
  denied: <Lock size={10} className="text-red-400" />,
  escalated: <AlertTriangle size={10} className="text-yellow-400" />,
  auto: <CheckCircle size={10} className="text-blue-400" />,
};

export default function AuditLogs() {
  const [filter, setFilter] = useState('');
  const [riskFilter, setRiskFilter] = useState<string>('all');
  const [selectedLog, setSelectedLog] = useState<string | null>(null);

  const filtered = LOGS.filter((l) => {
    const matchesSearch =
      !filter || l.action.includes(filter) || l.agent.includes(filter) || l.target.includes(filter);
    const matchesRisk = riskFilter === 'all' || l.risk === riskFilter;
    return matchesSearch && matchesRisk;
  });

  const selected = LOGS.find((l) => l.id === selectedLog);

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80">
      <div className="flex items-center justify-between px-4 py-3 border-b border-blue-500/10 bg-[#111d2e]">
        <div className="flex items-center gap-2">
          <Fingerprint size={18} className="text-blue-400" />
          <h2 className="text-sm font-semibold text-blue-200">Audit Logs</h2>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-300">
            {LOGS.length} entries
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search
              size={10}
              className="absolute left-2 top-1/2 -translate-y-1/2 text-blue-400/30"
            />
            <input
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Search..."
              className="bg-[#162032] border border-blue-500/15 rounded-lg pl-6 pr-2 py-1 text-[10px] outline-none w-28"
            />
          </div>
          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            className="bg-[#162032] border border-blue-500/15 rounded-lg px-2 py-1 text-[10px] outline-none"
          >
            <option value="all">All Risk</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Log List */}
        <div className="w-80 border-r border-blue-500/10 overflow-y-auto">
          {filtered.map((log) => (
            <button
              key={log.id}
              onClick={() => setSelectedLog(log.id)}
              className={`w-full text-left px-3 py-2 border-b border-blue-500/5 transition-colors ${selectedLog === log.id ? 'bg-blue-500/10' : 'hover:bg-blue-500/5'}`}
            >
              <div className="flex items-center gap-2 mb-1">
                {PERM_ICONS[log.permission]}
                <span className="text-[10px] text-blue-300/30">{log.timestamp}</span>
                <span className={`text-[9px] px-1 rounded ${RISK_COLORS[log.risk]}`}>
                  {log.risk}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-blue-200/60 font-mono">{log.action}</span>
                <ArrowUpRight size={8} className="text-blue-400/20" />
                <span className="text-[10px] text-blue-300/30 truncate">{log.target}</span>
              </div>
              <div className="text-[9px] text-blue-300/20 mt-0.5">{log.agent}</div>
            </button>
          ))}
        </div>

        {/* Detail */}
        {selected && (
          <div className="flex-1 p-4 overflow-y-auto">
            <div className="bg-[#162032] rounded-xl p-4 border border-blue-500/10">
              <div className="flex items-center gap-2 mb-3">
                <FileText size={14} className="text-blue-400" />
                <span className="text-sm text-blue-200 font-mono">{selected.action}</span>
                <span
                  className={`ml-auto px-2 py-0.5 rounded text-[10px] ${RISK_COLORS[selected.risk]}`}
                >
                  {selected.risk}
                </span>
              </div>

              <div className="space-y-2 text-xs">
                <div className="flex justify-between py-1 border-b border-blue-500/5">
                  <span className="text-blue-300/30">Timestamp</span>
                  <span className="text-blue-200/60 font-mono">{selected.timestamp}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-blue-500/5">
                  <span className="text-blue-300/30">Agent</span>
                  <span className="text-blue-200/60">{selected.agent}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-blue-500/5">
                  <span className="text-blue-300/30">Identity</span>
                  <span className="text-blue-200/60 font-mono">{selected.identity}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-blue-500/5">
                  <span className="text-blue-300/30">Target</span>
                  <span className="text-blue-200/60 font-mono">{selected.target}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-blue-500/5">
                  <span className="text-blue-300/30">Permission</span>
                  <span className="flex items-center gap-1">
                    {PERM_ICONS[selected.permission]}
                    <span className="text-blue-200/60">{selected.permission}</span>
                  </span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-blue-300/30">Details</span>
                </div>
                <div className="bg-[#0d1926] rounded-lg p-3 text-xs text-blue-200/50">
                  {selected.details}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
