import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useApi } from '../hooks/useApi';
import GovernanceBadge from '../components/GovernanceBadge';
import NDASigningCeremony from '../components/NDASigningCeremony';
import type { ProjectCapsule } from '../../shared/types/index.js';

export default function Dashboard() {
  const { user } = useAuth();
  const { get, post } = useApi();
  const navigate = useNavigate();
  const [projects, setProjects] = useState<ProjectCapsule[]>([]);
  const [ndaStatus, setNdaStatus] = useState<{ platformNdaSigned: boolean }>({ platformNdaSigned: false });

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }

    get<ProjectCapsule[]>('/projects').then(res => {
      if (res.success && res.data) setProjects(res.data);
    });

    if (user.role === 'investor') {
      get<{ platformNdaSigned: boolean }>('/ndas/status').then(res => {
        if (res.success && res.data) setNdaStatus(res.data);
      });
    }
  }, [user]);

  if (!user) return null;

  const [showNdaCeremony, setShowNdaCeremony] = useState(false);

  return (
    <div>
      <h2 style={{ fontFamily: 'var(--font-mono)', marginBottom: 8 }}>
        {user.role === 'coder' ? 'My Projects' : user.role === 'investor' ? 'Deal Flow' : 'Admin Dashboard'}
      </h2>
      <p style={{ color: 'var(--text-secondary)', marginBottom: 24 }}>
        {user.role === 'coder'
          ? 'Submit projects, track governance scores, and get scheduled for demo days.'
          : user.role === 'investor'
          ? 'Browse governance-scored projects, sign NDAs, and register interest during live events.'
          : 'Manage conferences, curate projects, and open deal rooms.'}
      </p>

      {user.role === 'investor' && !ndaStatus.platformNdaSigned && !showNdaCeremony && (
        <div className="card" style={{ marginBottom: 24, borderColor: 'var(--accent-amber)' }}>
          <h3 style={{ color: 'var(--accent-amber)', fontFamily: 'var(--font-mono)', marginBottom: 8 }}>
            Platform NDA Required
          </h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: 16 }}>
            Sign the platform NDA to access project details, join live Q&A, and register soft-commits.
            All access is recorded to the HYDRA governance ledger.
          </p>
          <button className="btn-primary" onClick={() => setShowNdaCeremony(true)}>Begin NDA Signing</button>
        </div>
      )}

      {user.role === 'investor' && showNdaCeremony && !ndaStatus.platformNdaSigned && (
        <div style={{ marginBottom: 24 }}>
          <NDASigningCeremony onSigned={() => { setNdaStatus({ platformNdaSigned: true }); setShowNdaCeremony(false); }} />
        </div>
      )}

      {user.role === 'investor' && ndaStatus.platformNdaSigned && (
        <div style={{ marginBottom: 24 }}>
          <span className="badge badge-allow">NDA Active</span>
        </div>
      )}

      {user.role === 'coder' && (
        <div style={{ marginBottom: 24 }}>
          <Link to="/submit">
            <button className="btn-primary">Submit New Project</button>
          </Link>
        </div>
      )}

      <div className="card-grid">
        {projects.map(project => (
          <Link to={`/projects/${project.id}`} key={project.id} style={{ textDecoration: 'none' }}>
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                <h3 style={{ fontFamily: 'var(--font-mono)', fontSize: '1rem' }}>{project.title}</h3>
                {project.governance && <GovernanceBadge decision={project.governance.decision} />}
              </div>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: 12 }}>
                {project.tagline}
              </p>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {project.techStack.slice(0, 4).map(t => (
                  <span key={t} style={{
                    background: 'var(--bg-secondary)',
                    border: '1px solid var(--border)',
                    borderRadius: 4,
                    padding: '2px 8px',
                    fontSize: '0.72rem',
                    color: 'var(--text-muted)',
                  }}>
                    {t}
                  </span>
                ))}
              </div>
              {project.governance && (
                <div className="governance-ribbon">
                  <span className="governance-stat">coherence: <span className="value">{project.governance.coherence.toFixed(2)}</span></span>
                  <span className="governance-stat">novelty: <span className="value">{project.governance.noveltyScore.toFixed(2)}</span></span>
                  <span className="governance-stat">risk: <span className="value">{project.governance.riskLabel}</span></span>
                </div>
              )}
            </div>
          </Link>
        ))}
        {projects.length === 0 && (
          <div className="card" style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
            {user.role === 'coder' ? 'No projects yet. Submit your first project!' : 'No projects available yet.'}
          </div>
        )}
      </div>
    </div>
  );
}
