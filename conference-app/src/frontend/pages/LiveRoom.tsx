import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { useAuth } from '../hooks/useAuth';
import GovernanceBadge from '../components/GovernanceBadge';
import type { Conference, ProjectCapsule, SoftCommit } from '../../shared/types/index.js';

const COMMIT_TIERS: Array<{ tier: SoftCommit['tier']; label: string; amount: number }> = [
  { tier: '10k', label: '$10K', amount: 10_000 },
  { tier: '25k', label: '$25K', amount: 25_000 },
  { tier: '50k', label: '$50K', amount: 50_000 },
  { tier: '100k', label: '$100K', amount: 100_000 },
];

export default function LiveRoom() {
  const { id } = useParams<{ id: string }>();
  const { get, post } = useApi();
  const { user } = useAuth();
  const [conference, setConference] = useState<(Conference & { slots: Array<any> }) | null>(null);
  const [ticker, setTicker] = useState<Array<{ projectId: string; totalAmount: number; commitCount: number }>>([]);
  const [committedProjectIds, setCommittedProjectIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!id) return;
    get<Conference & { slots: Array<any> }>(`/conferences/${id}`).then(res => {
      if (res.success && res.data) setConference(res.data);
    });
    // Poll ticker
    const interval = setInterval(() => {
      get<Array<any>>(`/funding/ticker/${id}`).then(res => {
        if (res.success && res.data) setTicker(res.data);
      });
    }, 3000);
    return () => clearInterval(interval);
  }, [id]);

  const handleCommit = async (projectId: string, tier: SoftCommit['tier'], amount: number) => {
    if (!id) return;
    const res = await post('/funding/soft-commit', {
      projectId,
      conferenceId: id,
      amount,
      tier,
      interestLevel: 'interested',
    });
    if (res.success) {
      setCommittedProjectIds(prev => new Set([...prev, projectId]));
    }
  };

  if (!conference) return <div style={{ color: 'var(--text-muted)' }}>Loading live room...</div>;

  const currentSlot = conference.slots.find((s: any) => s.status === 'live') ?? conference.slots[0];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2 style={{ fontFamily: 'var(--font-mono)' }}>
          {conference.title}
          <span className="badge badge-live" style={{ marginLeft: 12, verticalAlign: 'middle' }}>LIVE</span>
        </h2>
      </div>

      {/* Ticker bar */}
      {ticker.length > 0 && (
        <div className="ticker-bar" style={{ marginBottom: 20 }}>
          {ticker.map(t => {
            const project = conference.slots.find((s: any) => s.projectId === t.projectId)?.project;
            return (
              <div key={t.projectId} className="ticker-item">
                <span style={{ color: 'var(--text-secondary)' }}>{project?.title ?? t.projectId.slice(0, 8)}</span>
                <span className="ticker-amount">${t.totalAmount.toLocaleString()}</span>
                <span style={{ color: 'var(--text-muted)' }}>({t.commitCount})</span>
              </div>
            );
          })}
        </div>
      )}

      <div className="live-layout">
        {/* Main stage */}
        <div className="live-stage">
          {currentSlot?.project ? (
            <div style={{ padding: 40, textAlign: 'center' }}>
              <h2 style={{ fontFamily: 'var(--font-mono)', fontSize: '1.8rem', marginBottom: 8 }}>
                {currentSlot.project.title}
              </h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '1.1rem', marginBottom: 16 }}>
                {currentSlot.project.tagline}
              </p>
              {currentSlot.project.governance && (
                <div style={{ display: 'flex', gap: 16, justifyContent: 'center', alignItems: 'center', flexWrap: 'wrap' }}>
                  <GovernanceBadge decision={currentSlot.project.governance.decision} />
                  <span className="governance-stat">coherence: <span className="value">{currentSlot.project.governance.coherence.toFixed(2)}</span></span>
                  <span className="governance-stat">novelty: <span className="value">{currentSlot.project.governance.noveltyScore.toFixed(2)}</span></span>
                </div>
              )}
              <p style={{ color: 'var(--text-muted)', marginTop: 32, fontSize: '0.85rem' }}>
                Stream view would appear here (WebRTC/RTMP via Mux/Twilio)
              </p>
            </div>
          ) : (
            <span>Waiting for presentations to begin...</span>
          )}
        </div>

        {/* Side panel */}
        <div className="live-sidebar">
          {/* Commit panel (investors) */}
          {user?.role === 'investor' && currentSlot?.project && (
            <div className="commit-panel">
              <h3>Soft-Commit Interest</h3>
              {committedProjectIds.has(currentSlot.projectId) ? (
                <p style={{ color: 'var(--accent-green)', fontSize: '0.9rem' }}>Interest registered! The project creator will see your commitment.</p>
              ) : (
                <div className="commit-tiers">
                  {COMMIT_TIERS.map(ct => (
                    <button
                      key={ct.tier}
                      className="commit-tier-btn"
                      onClick={() => handleCommit(currentSlot.projectId, ct.tier, ct.amount)}
                    >
                      {ct.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Lineup */}
          <div className="commit-panel">
            <h3>Lineup</h3>
            {conference.slots.map((slot: any, i: number) => (
              <div key={slot.id} style={{
                padding: '10px 12px',
                background: slot.status === 'live' ? 'rgba(255, 68, 102, 0.1)' : 'transparent',
                borderRadius: 'var(--radius)',
                marginBottom: 6,
                borderLeft: slot.status === 'live' ? '3px solid var(--accent-red)' : '3px solid var(--border)',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', fontWeight: 600 }}>
                    {String(i + 1).padStart(2, '0')}. {slot.project?.title ?? 'TBD'}
                  </span>
                  {slot.status === 'live' && <span className="badge badge-live" style={{ fontSize: '0.65rem' }}>NOW</span>}
                </div>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                  {slot.pitchMinutes}min pitch + {slot.qaMinutes}min Q&A
                </span>
              </div>
            ))}
          </div>

          {/* HYDRA view (simplified) */}
          <div className="commit-panel">
            <h3>HYDRA Governance View</h3>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              {['KO-SCOUT', 'AV-VISION', 'RU-READER', 'CA-CLICKER', 'UM-TYPER', 'DR-JUDGE'].map((agent, i) => (
                <div key={agent} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderBottom: '1px solid var(--border)' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>{agent}</span>
                  <span style={{ color: 'var(--accent-green)' }}>{(0.7 + Math.random() * 0.3).toFixed(2)}</span>
                </div>
              ))}
              <div style={{ marginTop: 8, fontFamily: 'var(--font-mono)', color: 'var(--accent-purple)' }}>
                Quorum: 5/6 (threshold: 4/6)
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
