import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export default function AuthPage() {
  const { login, register, user } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<'login' | 'register'>('register');
  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [role, setRole] = useState<'coder' | 'investor'>('coder');
  const [error, setError] = useState('');

  if (user) {
    navigate('/dashboard');
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    let success: boolean;
    if (mode === 'register') {
      success = await register(email, displayName, role);
    } else {
      success = await login(email);
    }

    if (success) {
      navigate('/dashboard');
    } else {
      setError(mode === 'register' ? 'Registration failed (email may already exist)' : 'Login failed (user not found)');
    }
  };

  return (
    <div style={{ maxWidth: 440, margin: '40px auto' }}>
      <div className="card">
        <h2 style={{ fontFamily: 'var(--font-mono)', marginBottom: 24, color: 'var(--accent-cyan)' }}>
          {mode === 'register' ? 'Join vibe::conference' : 'Sign In'}
        </h2>

        <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
          <button
            className={mode === 'register' ? 'btn-primary' : 'btn-secondary'}
            onClick={() => setMode('register')}
            style={{ flex: 1 }}
          >
            Register
          </button>
          <button
            className={mode === 'login' ? 'btn-primary' : 'btn-secondary'}
            onClick={() => setMode('login')}
            style={{ flex: 1 }}
          >
            Sign In
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Email</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} required placeholder="you@example.com" />
          </div>

          {mode === 'register' && (
            <>
              <div className="form-group">
                <label>Display Name</label>
                <input value={displayName} onChange={e => setDisplayName(e.target.value)} required placeholder="Your name or handle" />
              </div>
              <div className="form-group">
                <label>I am a...</label>
                <div style={{ display: 'flex', gap: 12 }}>
                  <button
                    type="button"
                    className={role === 'coder' ? 'btn-primary' : 'btn-secondary'}
                    onClick={() => setRole('coder')}
                    style={{ flex: 1 }}
                  >
                    Vibe Coder
                  </button>
                  <button
                    type="button"
                    className={role === 'investor' ? 'btn-primary' : 'btn-secondary'}
                    onClick={() => setRole('investor')}
                    style={{ flex: 1 }}
                  >
                    Investor
                  </button>
                </div>
              </div>
            </>
          )}

          {error && <p style={{ color: 'var(--accent-red)', fontSize: '0.85rem', marginBottom: 16 }}>{error}</p>}

          <button type="submit" className="btn-primary" style={{ width: '100%' }}>
            {mode === 'register' ? 'Create Account' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}
