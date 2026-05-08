import { useState } from 'react';
import { authedFetch } from '../state/auth';
import { Verdict } from './Verdict';

type Result = {
  task_id?: string;
  verdict?: 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY';
  output?: string;
  error?: string;
};

export function TriggerPanel() {
  const [agent, setAgent] = useState('research');
  const [prompt, setPrompt] = useState('');
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    setResult(null);
    try {
      const r = await authedFetch('/v1/agent/task', {
        method: 'POST',
        body: JSON.stringify({ agent, prompt }),
      });
      const data = (await r.json()) as Result;
      setResult(r.ok ? data : { error: data.error ?? `HTTP ${r.status}` });
    } catch (e: unknown) {
      setResult({ error: e instanceof Error ? e.message : String(e) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <div className="card">
        <label>
          <div style={{ marginBottom: 6 }}>Agent</div>
          <select className="select" value={agent} onChange={(e) => setAgent(e.target.value)}>
            <option value="research">research</option>
            <option value="coding">coding</option>
            <option value="chemistry">chemistry</option>
            <option value="governance">governance</option>
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
                <div className="muted" style={{ fontSize: 12 }}>{result.task_id}</div>
                {result.verdict && <Verdict v={result.verdict} />}
              </div>
              {result.output && <pre style={{ whiteSpace: 'pre-wrap', marginTop: 10 }}>{result.output}</pre>}
            </>
          )}
        </div>
      )}
    </div>
  );
}
