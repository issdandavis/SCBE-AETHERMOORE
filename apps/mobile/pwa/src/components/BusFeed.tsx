import { useEffect, useRef, useState } from 'react';
import { authedFetch } from '../state/auth';
import { Verdict } from './Verdict';

type BusEvent = {
  id: string;
  ts: string;
  agent_id: string;
  verdict?: 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY';
  summary?: string;
};

export function BusFeed() {
  const [events, setEvents] = useState<BusEvent[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const seen = useRef<Set<string>>(new Set());

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const tick = async () => {
      try {
        const r = await authedFetch('/v1/bus/events?limit=50');
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const data = (await r.json()) as { events?: BusEvent[] };
        if (cancelled) return;
        const fresh = (data.events ?? []).filter((e) => !seen.current.has(e.id));
        for (const e of fresh) seen.current.add(e.id);
        if (fresh.length) setEvents((prev) => [...fresh, ...prev].slice(0, 200));
        setErr(null);
      } catch (e: unknown) {
        if (!cancelled) setErr(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) timer = setTimeout(tick, 4000);
      }
    };
    tick();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, []);

  return (
    <div>
      {err && (
        <div className="card" style={{ borderColor: '#7a3030' }}>
          <strong>Stream offline.</strong>
          <p className="muted">{err}</p>
          <p className="muted" style={{ fontSize: 12 }}>
            Expects <code>GET /v1/bus/events?limit=N</code> returning <code>{'{ events: [...] }'}</code>.
          </p>
        </div>
      )}
      {events.length === 0 && !err && <p className="muted">Listening for bus events…</p>}
      <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {events.map((ev) => (
          <li key={ev.id} className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div className="muted" style={{ fontSize: 12 }}>{new Date(ev.ts).toLocaleTimeString()}</div>
              {ev.verdict && <Verdict v={ev.verdict} />}
            </div>
            <div style={{ fontWeight: 600, marginTop: 4 }}>{ev.agent_id}</div>
            {ev.summary && <div className="muted" style={{ marginTop: 2 }}>{ev.summary}</div>}
          </li>
        ))}
      </ul>
    </div>
  );
}
