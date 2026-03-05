import React from 'react';
import { Link } from 'react-router-dom';

export default function Landing() {
  return (
    <div>
      <section className="hero">
        <h1>vibe::conference</h1>
        <p>
          Live demo days for vibe coders. Show investors what you built.
          Every project is scored by the SCBE-AETHERMOORE governance pipeline.
          Investors sign NDAs. Funding flows through.
        </p>
        <div className="hero-actions">
          <Link to="/auth"><button className="btn-primary">I'm a Vibe Coder</button></Link>
          <Link to="/auth"><button className="btn-secondary">I'm an Investor</button></Link>
        </div>
      </section>

      <div className="card-grid">
        <div className="card">
          <h3 style={{ color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)', marginBottom: 12 }}>
            Submit Your Project
          </h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Drop your repo, demo, and pitch video. The SCBE 14-layer pipeline
            scores your project across coherence, novelty, and risk. HYDRA's
            six-tongue swarm browser audits your code.
          </p>
        </div>

        <div className="card">
          <h3 style={{ color: 'var(--accent-green)', fontFamily: 'var(--font-mono)', marginBottom: 12 }}>
            Governance-Gated Demo Days
          </h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Only ALLOW-status projects make it to the main stage. Investors
            see governance badges, HYDRA audit results, and coherence scores.
            No black boxes — transparent safety.
          </p>
        </div>

        <div className="card">
          <h3 style={{ color: 'var(--accent-purple)', fontFamily: 'var(--font-mono)', marginBottom: 12 }}>
            NDA-First Investment
          </h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Investors sign NDAs before accessing sensitive materials.
            Soft-commit during live pitches. Follow up in structured
            deal rooms with full SCBE audit trails.
          </p>
        </div>
      </div>

      <div style={{ marginTop: 48, textAlign: 'center' }}>
        <h2 style={{ fontFamily: 'var(--font-mono)', marginBottom: 16, color: 'var(--accent-cyan)' }}>
          How It Works
        </h2>
        <div style={{ display: 'flex', gap: 40, justifyContent: 'center', flexWrap: 'wrap', marginTop: 24 }}>
          {[
            { step: '01', label: 'Intake', desc: 'Submit project capsule with code, demo, and pitch' },
            { step: '02', label: 'Governance', desc: 'SCBE L1-L14 pipeline scores + HYDRA swarm audit' },
            { step: '03', label: 'Conference', desc: 'Live demo day with investor soft-commits' },
            { step: '04', label: 'Funding', desc: 'Deal rooms, follow-ups, and term sheets' },
          ].map(s => (
            <div key={s.step} style={{ textAlign: 'center', maxWidth: 200 }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '2rem', color: 'var(--accent-purple)', fontWeight: 800 }}>
                {s.step}
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, margin: '8px 0' }}>{s.label}</div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>{s.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
