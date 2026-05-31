import { useState } from 'react';
import { useAuth } from '../state/auth';

export function LoginGate() {
  const { signIn } = useAuth();
  const [token, setToken] = useState('');
  const [backend, setBackend] = useState('https://');
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  return (
    <div className="content">
      <div className="card">
        <h2 style={{ marginTop: 0 }}>Connect to your SCBE backend</h2>
        <p className="muted tight">
          The token and backend URL stay on this device (localStorage). The app calls your
          backend directly — no third-party servers in between.
        </p>
      </div>
      <div className="card">
        <label>
          <div style={{ marginBottom: 6 }}>Backend URL</div>
          <input
            className="input"
            type="url"
            value={backend}
            onChange={(e) => setBackend(e.target.value)}
            placeholder="https://your-scbe-bridge.example.com"
            autoComplete="off"
            spellCheck={false}
          />
        </label>
        <p className="muted" style={{ fontSize: 12, marginTop: 4 }}>
          Points at the FastAPI bridge from <code>workflows/n8n/scbe_n8n_bridge.py</code>.
          For local dev, <code>http://10.0.2.2:8001</code> reaches the host machine from the
          Android emulator.
        </p>
      </div>
      <div className="card">
        <label>
          <div style={{ marginBottom: 6 }}>Hugging Face token (or your bridge auth token)</div>
          <input
            className="input"
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="hf_…"
            autoComplete="current-password"
          />
        </label>
        <p className="muted" style={{ fontSize: 12, marginTop: 4 }}>
          Used as a bearer token for backend calls. Generate at{' '}
          <a href="https://huggingface.co/settings/tokens">huggingface.co/settings/tokens</a>.
        </p>
      </div>
      {err && (
        <div className="card" style={{ borderColor: '#7a3030' }}>
          <strong>Sign-in failed:</strong> {err}
        </div>
      )}
      <button
        className="btn"
        disabled={submitting || !token || !/^https?:\/\//.test(backend)}
        onClick={async () => {
          setErr(null);
          setSubmitting(true);
          try {
            // Don't trust the user's input until we ping the backend.
            const r = await fetch(`${backend.replace(/\/+$/, '')}/health`, {
              headers: { Authorization: `Bearer ${token}` },
            });
            if (!r.ok) throw new Error(`Health check returned ${r.status}`);
            signIn(token, backend);
          } catch (e: unknown) {
            setErr(e instanceof Error ? e.message : String(e));
          } finally {
            setSubmitting(false);
          }
        }}
      >
        {submitting ? 'Connecting…' : 'Sign in'}
      </button>
    </div>
  );
}
