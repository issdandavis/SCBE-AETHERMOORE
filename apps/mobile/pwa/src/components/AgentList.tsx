import { useEffect, useState } from 'react';
import { authedFetch } from '../state/auth';
import { Verdict } from './Verdict';

type Agent = {
  id: string;
  name: string;
  last_verdict?: 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY';
  last_seen_iso?: string;
  task_count_24h?: number;
};

export function AgentList() {
  const [agents, setAgents] = useState<Agent[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await authedFetch('/v1/agents');
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const data = (await r.json()) as { agents?: Agent[] };
        if (!cancelled) setAgents(data.agents ?? []);
      } catch (e: unknown) {
        if (!cancelled) setErr(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (err) {
    return (
      <div className="card">
        <strong>Failed to load agents.</strong>
        <p className="muted">{err}</p>
        <p className="muted" style={{ fontSize: 12 }}>
          The bridge needs a <code>GET /v1/agents</code> route returning <code>{'{ agents: [...] }'}</code>.
          Until that ships, this tab will stay empty.
        </p>
      </div>
    );
  }

  if (agents === null) {
    return <p className="muted">Loading agents…</p>;
  }

  if (agents.length === 0) {
    return (
      <div className="card">
        <strong>No agents reporting yet.</strong>
        <p className="muted">
          Start an agent on your machine that pushes its heartbeat to the bus and it'll appear
          here.
        </p>
      </div>
    );
  }

  return (
    <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
      {agents.map((a) => (
        <li key={a.id} className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontWeight: 600 }}>{a.name}</div>
              <div className="muted" style={{ fontSize: 12 }}>
                {a.id} · {a.task_count_24h ?? 0} tasks / 24h
              </div>
            </div>
            {a.last_verdict && <Verdict v={a.last_verdict} />}
          </div>
          {a.last_seen_iso && (
            <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>
              last seen {new Date(a.last_seen_iso).toLocaleString()}
            </div>
          )}
        </li>
      ))}
    </ul>
  );
}
