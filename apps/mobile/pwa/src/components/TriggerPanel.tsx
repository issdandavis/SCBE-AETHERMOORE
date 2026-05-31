import { useEffect, useState } from 'react';
import { authedFetch } from '../state/auth';
import { Verdict } from './Verdict';

type AgentSummary = {
  id: string;
  name: string;
  role: string;
  available: boolean;
  seat: string | null;
};

type DispatchResult = {
  agent?: string;
  seat?: string;
  model?: string;
  verdict?: { verdict?: 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY' };
  text?: string;
  blocked?: boolean;
  reason?: string;
  error?: string;
};

export function TriggerPanel() {
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [agent, setAgent] = useState('free');
  const [prompt, setPrompt] = useState('');
  const [result, setResult] = useState<DispatchResult | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await authedFetch('/v1/agents');
        const data = (await r.json()) as { agents?: AgentSummary[] };
        if (!cancelled && data.agents) {
          setAgents(data.agents);
          const firstAvailable = data.agents.find((a) => a.available) ?? data.agents[0];
          if (firstAvailable) setAgent(firstAvailable.id);
        }
      } catch {
        // backend not reachable — fall back to default agent slugs
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const submit = async () => {
    setBusy(true);
    setResult(null);
    try {
      const r = await authedFetch('/v1/agents/dispatch', {
        method: 'POST',
        body: JSON.stringify({ agent, prompt }),
      });
      const data = (await r.json()) as DispatchResult;
      setResult(r.ok ? data : { error: data.error ?? `HTTP ${r.status}` });
    } catch (e: unknown) {
      setResult({ error: e instanceof Error ? e.message : String(e) });
    } finally {
      setBusy(false);
    }
  };

  const fallbackAgents: AgentSummary[] = [
    { id: 'free', name: 'Free Tier', role: 'auto-route', available: false, seat: null },
    { id: 'polly', name: 'Polly', role: 'governance', available: false, seat: null },
    { id: 'zara', name: 'Zara', role: 'student', available: false, seat: null },
    { id: 'scribe', name: 'Scribe', role: 'lore', available: false, seat: null },
  ];
  const optionList = agents.length ? agents : fallbackAgents;

  return (
    <div>
      <div className="card">
        <label>
          <div style={{ marginBottom: 6 }}>Agent</div>
          <select className="select" value={agent} onChange={(e) => setAgent(e.target.value)}>
            {optionList.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name} — {a.role}
                {a.available ? ` · ${a.seat}` : ' · offline'}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="card">
        <label>
          <div style={{ marginBottom: 6 }}>Prompt</div>
          <textarea
            className="textarea"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="What do you want this agent to do?"
          />
        </label>
      </div>
      <button className="btn" disabled={busy || !prompt.trim()} onClick={submit}>
        {busy ? 'Dispatching…' : 'Trigger agent'}
      </button>
      {result && (
        <div className="card" style={{ marginTop: 16 }}>
          {result.error && (
            <div>
              <strong>Failed:</strong> <span className="muted">{result.error}</span>
            </div>
          )}
          {!result.error && (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div className="muted" style={{ fontSize: 12 }}>
                  {result.seat ?? ''} {result.model ? `· ${result.model}` : ''}
                </div>
                {result.verdict?.verdict && <Verdict v={result.verdict.verdict} />}
              </div>
              {result.blocked && (
                <div className="muted" style={{ marginTop: 10 }}>
                  Blocked by SCBE governance: {result.reason ?? 'unknown'}
                </div>
              )}
              {result.text && <pre style={{ whiteSpace: 'pre-wrap', marginTop: 10 }}>{result.text}</pre>}
            </>
          )}
        </div>
      )}
    </div>
  );
}
