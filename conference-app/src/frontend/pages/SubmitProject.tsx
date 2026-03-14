import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useApi } from '../hooks/useApi';

export default function SubmitProject() {
  const { user } = useAuth();
  const { post, loading, error } = useApi();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    title: '',
    tagline: '',
    description: '',
    techStack: '',
    repoUrl: '',
    demoUrl: '',
    videoUrl: '',
    pitchDeckUrl: '',
    fundingAmount: 50000,
    fundingStage: 'pre-seed' as const,
    useOfFunds: '',
  });

  if (!user || user.role !== 'coder') {
    navigate('/auth');
    return null;
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Create the project
    const createRes = await post<{ id: string }>('/projects', {
      title: form.title,
      tagline: form.tagline,
      description: form.description,
      techStack: form.techStack.split(',').map(s => s.trim()).filter(Boolean),
      repoUrl: form.repoUrl || undefined,
      demoUrl: form.demoUrl || undefined,
      videoUrl: form.videoUrl || undefined,
      pitchDeckUrl: form.pitchDeckUrl || undefined,
      fundingAsk: {
        amount: Number(form.fundingAmount),
        stage: form.fundingStage,
        useOfFunds: form.useOfFunds,
      },
    });

    if (createRes.success && createRes.data) {
      const projectId = (createRes.data as any).id;
      // Auto-submit for governance scoring
      await post(`/projects/${projectId}/submit`, {});
      navigate(`/projects/${projectId}`);
    }
  };

  return (
    <div style={{ maxWidth: 640, margin: '0 auto' }}>
      <h2 style={{ fontFamily: 'var(--font-mono)', marginBottom: 8 }}>Submit Your Project</h2>
      <p style={{ color: 'var(--text-secondary)', marginBottom: 32 }}>
        Fill in your project details. After submission, the SCBE 14-layer pipeline
        and HYDRA swarm browser will score and audit your project.
      </p>

      <form onSubmit={handleSubmit} className="card">
        <div className="form-group">
          <label>Project Title *</label>
          <input name="title" value={form.title} onChange={handleChange} required placeholder="e.g., VibeDB — a database for vibes" />
        </div>

        <div className="form-group">
          <label>Tagline *</label>
          <input name="tagline" value={form.tagline} onChange={handleChange} required placeholder="One line that captures your project" />
        </div>

        <div className="form-group">
          <label>Description *</label>
          <textarea name="description" value={form.description} onChange={handleChange} required rows={5} placeholder="What does your project do? What problem does it solve? Why now?" />
        </div>

        <div className="form-group">
          <label>Tech Stack * (comma-separated)</label>
          <input name="techStack" value={form.techStack} onChange={handleChange} required placeholder="e.g., React, TypeScript, Rust, WebGPU" />
        </div>

        <div className="form-group">
          <label>Repository URL</label>
          <input name="repoUrl" value={form.repoUrl} onChange={handleChange} placeholder="https://github.com/..." />
        </div>

        <div className="form-group">
          <label>Live Demo URL</label>
          <input name="demoUrl" value={form.demoUrl} onChange={handleChange} placeholder="https://..." />
        </div>

        <div className="form-group">
          <label>Video (Loom/YouTube)</label>
          <input name="videoUrl" value={form.videoUrl} onChange={handleChange} placeholder="3-5 minute walkthrough" />
        </div>

        <div className="form-group">
          <label>Pitch Deck URL</label>
          <input name="pitchDeckUrl" value={form.pitchDeckUrl} onChange={handleChange} placeholder="Google Slides, Notion, PDF link..." />
        </div>

        <h3 style={{ fontFamily: 'var(--font-mono)', fontSize: '0.95rem', color: 'var(--accent-green)', margin: '24px 0 16px' }}>
          Funding Ask
        </h3>

        <div className="form-group">
          <label>Amount (USD)</label>
          <input name="fundingAmount" type="number" value={form.fundingAmount} onChange={handleChange} min={1000} />
        </div>

        <div className="form-group">
          <label>Stage</label>
          <select name="fundingStage" value={form.fundingStage} onChange={handleChange}>
            <option value="pre-seed">Pre-Seed</option>
            <option value="seed">Seed</option>
            <option value="series-a">Series A</option>
            <option value="grant">Grant</option>
            <option value="other">Other</option>
          </select>
        </div>

        <div className="form-group">
          <label>Use of Funds</label>
          <textarea name="useOfFunds" value={form.useOfFunds} onChange={handleChange} rows={3} placeholder="How will you use the money?" />
        </div>

        {error && <p style={{ color: 'var(--accent-red)', fontSize: '0.85rem', marginBottom: 16 }}>{error}</p>}

        <button type="submit" className="btn-success" disabled={loading} style={{ width: '100%' }}>
          {loading ? 'Submitting...' : 'Submit & Score via SCBE Pipeline'}
        </button>
      </form>
    </div>
  );
}
