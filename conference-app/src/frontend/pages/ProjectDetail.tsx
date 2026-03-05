import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { useAuth } from '../hooks/useAuth';
import GovernanceBadge from '../components/GovernanceBadge';
import GovernanceLayers from '../components/GovernanceLayers';
import HydraAudit from '../components/HydraAudit';
import type { ProjectCapsule } from '../../shared/types/index.js';

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const { get } = useApi();
  const { user } = useAuth();
  const [project, setProject] = useState<ProjectCapsule | null>(null);

  useEffect(() => {
    if (id) {
      get<ProjectCapsule>(`/projects/${id}`).then(res => {
        if (res.success && res.data) setProject(res.data);
      });
    }
  }, [id]);

  if (!project) return <div style={{ color: 'var(--text-muted)' }}>Loading...</div>;

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <div className="card" style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h2 style={{ fontFamily: 'var(--font-mono)', marginBottom: 4 }}>{project.title}</h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>{project.tagline}</p>
          </div>
          {project.governance && <GovernanceBadge decision={project.governance.decision} />}
        </div>

        <p style={{ marginTop: 16, color: 'var(--text-primary)', fontSize: '0.9rem', lineHeight: 1.7 }}>
          {project.description}
        </p>

        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 16 }}>
          {project.techStack.map(t => (
            <span key={t} style={{
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border)',
              borderRadius: 4,
              padding: '3px 10px',
              fontSize: '0.78rem',
              color: 'var(--text-secondary)',
            }}>
              {t}
            </span>
          ))}
        </div>

        <div style={{ display: 'flex', gap: 16, marginTop: 20, flexWrap: 'wrap' }}>
          {project.repoUrl && <a href={project.repoUrl} target="_blank" rel="noopener noreferrer">Repository</a>}
          {project.demoUrl && <a href={project.demoUrl} target="_blank" rel="noopener noreferrer">Live Demo</a>}
          {project.videoUrl && <a href={project.videoUrl} target="_blank" rel="noopener noreferrer">Video</a>}
          {project.pitchDeckUrl && <a href={project.pitchDeckUrl} target="_blank" rel="noopener noreferrer">Pitch Deck</a>}
        </div>

        <div style={{ marginTop: 20, padding: '12px 16px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius)' }}>
          <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Funding Ask:</span>{' '}
          <span style={{ color: 'var(--accent-green)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
            ${project.fundingAsk.amount.toLocaleString()}
          </span>
          <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginLeft: 12 }}>
            {project.fundingAsk.stage}
          </span>
        </div>
      </div>

      {project.governance && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h3 style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)', marginBottom: 16 }}>
            SCBE Governance Scores (L1-L14)
          </h3>

          <div className="governance-ribbon" style={{ marginBottom: 20 }}>
            <span className="governance-stat">coherence: <span className="value">{project.governance.coherence.toFixed(3)}</span></span>
            <span className="governance-stat">d_H: <span className="value">{project.governance.hyperbolicDistance.toFixed(3)}</span></span>
            <span className="governance-stat">H(d,pd): <span className="value">{project.governance.harmonicScore.toFixed(3)}</span></span>
            <span className="governance-stat">novelty: <span className="value">{project.governance.noveltyScore.toFixed(3)}</span></span>
          </div>

          <GovernanceLayers layers={project.governance.layerSummary} />
        </div>
      )}

      {project.hydraAudit && (
        <div className="card">
          <h3 style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-purple)', marginBottom: 16 }}>
            HYDRA Swarm Audit
          </h3>
          <HydraAudit audit={project.hydraAudit} />
        </div>
      )}
    </div>
  );
}
