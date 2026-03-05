import React from 'react';
import type { HydraAuditResult } from '../../shared/types/index.js';

interface Props {
  audit: HydraAuditResult;
}

const TONGUE_COLORS: Record<string, string> = {
  KO: '#4488ff',
  AV: '#44ccdd',
  RU: '#8844ff',
  CA: '#ff8844',
  UM: '#44cc88',
  DR: '#ffaa44',
};

export default function HydraAudit({ audit }: Props) {
  return (
    <div>
      <div style={{ display: 'flex', gap: 16, marginBottom: 20, flexWrap: 'wrap' }}>
        <span className="governance-stat">quality: <span className="value">{audit.qualityScore.toFixed(2)}</span></span>
        <span className="governance-stat">phase-lock: <span className="value">{audit.phaseLockScore.toFixed(2)}</span></span>
        <span className="governance-stat">quorum: <span className="value">{audit.quorumMet ? 'MET' : 'NOT MET'}</span></span>
      </div>

      <div style={{ display: 'grid', gap: 8 }}>
        {audit.agents.map(agent => (
          <div
            key={agent.tongue}
            style={{
              display: 'grid',
              gridTemplateColumns: '100px 1fr 60px',
              gap: 12,
              alignItems: 'center',
              padding: '8px 12px',
              background: 'var(--bg-secondary)',
              borderRadius: 'var(--radius)',
              borderLeft: `3px solid ${TONGUE_COLORS[agent.tongue] ?? 'var(--border)'}`,
            }}
          >
            <div>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: TONGUE_COLORS[agent.tongue] }}>
                {agent.tongue}
              </span>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginLeft: 4 }}>
                {agent.role}
              </span>
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
              {agent.findings.join(' | ')}
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--accent-green)', textAlign: 'right' }}>
              {agent.score.toFixed(2)}
            </div>
          </div>
        ))}
      </div>

      {audit.securityFlags.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--accent-amber)' }}>Security flags: </span>
          {audit.securityFlags.map(f => (
            <span key={f} className="badge badge-quarantine" style={{ marginRight: 4 }}>{f}</span>
          ))}
        </div>
      )}
    </div>
  );
}
