/**
 * @file LiveRoom.tsx
 * @module conference/frontend/pages
 *
 * Live conference room with:
 * - Zoom meeting embed (join link) or stream placeholder
 * - Real-time soft-commit ticker via SSE
 * - Live chat + emoji reactions
 * - Investor soft-commit panel ($10K/$25K/$50K/$100K tiers)
 * - HYDRA governance view with agent scores
 * - Lineup sidebar with slot status
 */

import React, { useEffect, useState, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { useAuth } from '../hooks/useAuth';
import { useLiveEvents } from '../hooks/useLiveEvents';
import GovernanceBadge from '../components/GovernanceBadge';
import type { Conference, SoftCommit } from '../../shared/types/index.js';

const COMMIT_TIERS: Array<{ tier: SoftCommit['tier']; label: string; amount: number }> = [
  { tier: '10k', label: '$10K', amount: 10_000 },
  { tier: '25k', label: '$25K', amount: 25_000 },
  { tier: '50k', label: '$50K', amount: 50_000 },
  { tier: '100k', label: '$100K', amount: 100_000 },
];

const REACTION_EMOJIS = [
  { id: 'fire', display: 'FIRE' },
  { id: 'rocket', display: 'ROCKET' },
  { id: 'money', display: 'MONEY' },
  { id: 'clap', display: 'CLAP' },
  { id: 'think', display: 'THINK' },
  { id: 'heart', display: 'HEART' },
];

export default function LiveRoom() {
  const { id } = useParams<{ id: string }>();
  const { get, post } = useApi();
  const { user, token } = useAuth();
  const live = useLiveEvents(id, token);
  const [conference, setConference] = useState<(Conference & { slots: Array<any> }) | null>(null);
  const [committedProjectIds, setCommittedProjectIds] = useState<Set<string>>(new Set());
  const [zoomJoinUrl, setZoomJoinUrl] = useState<string | null>(null);
  const [chatInput, setChatInput] = useState('');
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!id) return;
    get<Conference & { slots: Array<any> }>(`/conferences/${id}`).then(res => {
      if (res.success && res.data) setConference(res.data);
    });
    // Get Zoom join link
    get<{ url: string; role: string }>(`/zoom/conferences/${id}/join`).then(res => {
      if (res.success && res.data) setZoomJoinUrl((res.data as any).url);
    });
  }, [id]);

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [live.chatMessages]);

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

  const handleChat = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || !id) return;
    await post(`/zoom/conferences/${id}/chat`, { message: chatInput });
    setChatInput('');
  };

  const handleReaction = async (emoji: string) => {
    if (!id) return;
    await post(`/zoom/conferences/${id}/reaction`, { emoji });
  };

  if (!conference) return <div style={{ color: 'var(--text-muted)' }}>Loading live room...</div>;

  const currentSlot = conference.slots.find((s: any) => s.status === 'live') ?? conference.slots[0];
  const ticker = live.ticker.length > 0 ? live.ticker : [];

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2 style={{ fontFamily: 'var(--font-mono)' }}>
          {conference.title}
          <span className="badge badge-live" style={{ marginLeft: 12, verticalAlign: 'middle' }}>LIVE</span>
          {live.connected && (
            <span style={{ marginLeft: 12, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {live.viewerCount} viewer{live.viewerCount !== 1 ? 's' : ''}
            </span>
          )}
        </h2>
        {zoomJoinUrl && (
          <a href={zoomJoinUrl} target="_blank" rel="noopener noreferrer">
            <button className="btn-primary">Join Zoom Meeting</button>
          </a>
        )}
      </div>

      {/* Latest commit toast */}
      {live.latestCommit && (
        <div style={{
          background: 'rgba(68, 204, 136, 0.1)',
          border: '1px solid rgba(68, 204, 136, 0.3)',
          borderRadius: 'var(--radius)',
          padding: '10px 16px',
          marginBottom: 16,
          fontFamily: 'var(--font-mono)',
          fontSize: '0.85rem',
          display: 'flex',
          gap: 12,
          alignItems: 'center',
        }}>
          <span style={{ color: 'var(--accent-green)', fontWeight: 700 }}>NEW COMMIT</span>
          <span style={{ color: 'var(--text-secondary)' }}>{live.latestCommit.investorName}</span>
          <span className="ticker-amount">${live.latestCommit.amount.toLocaleString()}</span>
          <span style={{ color: 'var(--text-muted)' }}>on {live.latestCommit.projectTitle}</span>
        </div>
      )}

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
            <div style={{ padding: 40, textAlign: 'center', width: '100%' }}>
              <h2 style={{ fontFamily: 'var(--font-mono)', fontSize: '1.8rem', marginBottom: 8 }}>
                {currentSlot.project.title}
              </h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '1.1rem', marginBottom: 16 }}>
                {currentSlot.project.tagline}
              </p>
              {currentSlot.project.governance && (
                <div style={{ display: 'flex', gap: 16, justifyContent: 'center', alignItems: 'center', flexWrap: 'wrap', marginBottom: 24 }}>
                  <GovernanceBadge decision={currentSlot.project.governance.decision} />
                  <span className="governance-stat">coherence: <span className="value">{currentSlot.project.governance.coherence.toFixed(2)}</span></span>
                  <span className="governance-stat">novelty: <span className="value">{currentSlot.project.governance.noveltyScore.toFixed(2)}</span></span>
                  <span className="governance-stat">risk: <span className="value">{currentSlot.project.governance.riskLabel}</span></span>
                </div>
              )}

              {/* Zoom status */}
              {zoomJoinUrl ? (
                <div style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius)',
                  padding: 32,
                  marginTop: 16,
                }}>
                  <p style={{ color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)', marginBottom: 12 }}>
                    Zoom Meeting Active
                  </p>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                    Click "Join Zoom Meeting" above to watch the live presentation.
                    Use the side panel for soft-commits, chat, and governance data.
                  </p>
                </div>
              ) : (
                <p style={{ color: 'var(--text-muted)', marginTop: 32, fontSize: '0.85rem' }}>
                  No Zoom meeting configured. Curator can create one from conference settings.
                </p>
              )}

              {/* Reactions */}
              <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 24 }}>
                {REACTION_EMOJIS.map(r => (
                  <button
                    key={r.id}
                    onClick={() => handleReaction(r.id)}
                    style={{
                      background: 'var(--bg-secondary)',
                      border: '1px solid var(--border)',
                      color: 'var(--text-secondary)',
                      padding: '6px 12px',
                      borderRadius: 20,
                      fontSize: '0.75rem',
                      fontFamily: 'var(--font-mono)',
                      cursor: 'pointer',
                    }}
                  >
                    {r.display}
                  </button>
                ))}
              </div>
              {live.reactions.length > 0 && (
                <div style={{ marginTop: 8, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  {live.reactions.slice(-5).map((r, i) => (
                    <span key={i} style={{ marginRight: 6 }}>[{r.emoji}]</span>
                  ))}
                </div>
              )}
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
                <p style={{ color: 'var(--accent-green)', fontSize: '0.9rem' }}>
                  Interest registered! The project creator will see your commitment.
                </p>
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

          {/* Live Chat */}
          <div className="commit-panel" style={{ display: 'flex', flexDirection: 'column', maxHeight: 240 }}>
            <h3>Live Chat</h3>
            <div style={{ flex: 1, overflowY: 'auto', marginBottom: 8, minHeight: 100 }}>
              {live.chatMessages.map((msg, i) => (
                <div key={i} style={{ marginBottom: 6, fontSize: '0.8rem' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)', fontWeight: 600 }}>
                    {msg.displayName}:
                  </span>{' '}
                  <span style={{ color: 'var(--text-secondary)' }}>{msg.message}</span>
                </div>
              ))}
              {live.chatMessages.length === 0 && (
                <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>No messages yet.</p>
              )}
              <div ref={chatEndRef} />
            </div>
            <form onSubmit={handleChat} style={{ display: 'flex', gap: 6 }}>
              <input
                value={chatInput}
                onChange={e => setChatInput(e.target.value)}
                placeholder="Type a message..."
                style={{ flex: 1, padding: '6px 10px', fontSize: '0.8rem' }}
              />
              <button type="submit" className="btn-primary" style={{ padding: '6px 12px', fontSize: '0.8rem' }}>
                Send
              </button>
            </form>
          </div>

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

          {/* HYDRA Governance View */}
          <div className="commit-panel">
            <h3>HYDRA Governance</h3>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              {currentSlot?.project?.hydraAudit ? (
                <>
                  {currentSlot.project.hydraAudit.agents.map((agent: any) => (
                    <div key={agent.tongue} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderBottom: '1px solid var(--border)' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>
                        {agent.tongue}-{agent.role}
                      </span>
                      <span style={{ color: agent.score >= 0.7 ? 'var(--accent-green)' : 'var(--accent-amber)' }}>
                        {agent.score.toFixed(2)}
                      </span>
                    </div>
                  ))}
                  <div style={{ marginTop: 8, fontFamily: 'var(--font-mono)' }}>
                    <span style={{ color: currentSlot.project.hydraAudit.quorumMet ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                      Quorum: {currentSlot.project.hydraAudit.quorumMet ? 'MET' : 'NOT MET'}
                    </span>
                    <span style={{ color: 'var(--accent-purple)', marginLeft: 12 }}>
                      Phase-lock: {currentSlot.project.hydraAudit.phaseLockScore.toFixed(2)}
                    </span>
                  </div>
                </>
              ) : (
                <p style={{ color: 'var(--text-muted)' }}>No HYDRA audit data for current project.</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
