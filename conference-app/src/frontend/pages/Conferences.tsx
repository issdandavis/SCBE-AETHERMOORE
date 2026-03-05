import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { useAuth } from '../hooks/useAuth';
import type { Conference } from '../../shared/types/index.js';

export default function Conferences() {
  const { get, post } = useApi();
  const { user } = useAuth();
  const [conferences, setConferences] = useState<Conference[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ title: '', theme: '', description: '', scheduledAt: '', duration: 120 });

  useEffect(() => {
    get<Conference[]>('/conferences').then(res => {
      if (res.success && res.data) setConferences(res.data);
    });
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    const res = await post<Conference>('/conferences', form);
    if (res.success && res.data) {
      setConferences(prev => [res.data!, ...prev]);
      setShowCreate(false);
      setForm({ title: '', theme: '', description: '', scheduledAt: '', duration: 120 });
    }
  };

  const statusStyle = (status: string) => {
    switch (status) {
      case 'live': return 'badge-live';
      case 'scheduled': return 'badge-allow';
      case 'ended': return 'badge-quarantine';
      default: return '';
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2 style={{ fontFamily: 'var(--font-mono)' }}>Demo Days</h2>
        {user?.role === 'curator' && (
          <button className="btn-primary" onClick={() => setShowCreate(!showCreate)}>
            {showCreate ? 'Cancel' : 'Create Conference'}
          </button>
        )}
      </div>

      {showCreate && (
        <form className="card" onSubmit={handleCreate} style={{ marginBottom: 24 }}>
          <div className="form-group">
            <label>Title</label>
            <input value={form.title} onChange={e => setForm(p => ({ ...p, title: e.target.value }))} required placeholder="e.g., Agents & Browsers Week" />
          </div>
          <div className="form-group">
            <label>Theme</label>
            <input value={form.theme} onChange={e => setForm(p => ({ ...p, theme: e.target.value }))} required placeholder="e.g., AI Agents" />
          </div>
          <div className="form-group">
            <label>Description</label>
            <textarea value={form.description} onChange={e => setForm(p => ({ ...p, description: e.target.value }))} required rows={3} />
          </div>
          <div className="form-group">
            <label>Scheduled At</label>
            <input type="datetime-local" value={form.scheduledAt} onChange={e => setForm(p => ({ ...p, scheduledAt: e.target.value }))} required />
          </div>
          <div className="form-group">
            <label>Duration (minutes)</label>
            <input type="number" value={form.duration} onChange={e => setForm(p => ({ ...p, duration: Number(e.target.value) }))} min={30} />
          </div>
          <button type="submit" className="btn-success">Create Demo Day</button>
        </form>
      )}

      <div className="card-grid">
        {conferences.map(conf => (
          <Link to={conf.status === 'live' ? `/live/${conf.id}` : `/conferences`} key={conf.id} style={{ textDecoration: 'none' }}>
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                <h3 style={{ fontFamily: 'var(--font-mono)', fontSize: '1rem' }}>{conf.title}</h3>
                <span className={`badge ${statusStyle(conf.status)}`}>{conf.status}</span>
              </div>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: 8 }}>{conf.theme}</p>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                {new Date(conf.scheduledAt).toLocaleDateString('en-US', {
                  weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                })}
                {' '}&middot;{' '}{conf.duration}min{' '}&middot;{' '}{conf.slots.length} projects
              </p>
            </div>
          </Link>
        ))}
        {conferences.length === 0 && (
          <div className="card" style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
            No demo days scheduled yet.
          </div>
        )}
      </div>
    </div>
  );
}
