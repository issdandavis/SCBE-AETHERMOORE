import { useState } from 'react';
import type { ToolBus, ToolDef } from '../toolBus';

interface Props {
  bus: ToolBus;
}

const PANEL: React.CSSProperties = {
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
  fontFamily: 'monospace',
  fontSize: 13,
};

const ROW: React.CSSProperties = {
  display: 'flex',
  gap: 8,
  padding: '8px 12px',
  borderBottom: '1px solid #ddd',
  alignItems: 'center',
};

export function ToolConsole({ bus }: Props) {
  const tools = bus.listTools();
  const [selected, setSelected] = useState<ToolDef>(tools[0]);
  const [argsJson, setArgsJson] = useState('{}');
  const [output, setOutput] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  function pickTool(name: string) {
    const def = tools.find((t) => t.name === name);
    if (!def) return;
    setSelected(def);
    setArgsJson('{}');
    setOutput(null);
    setErr(null);
  }

  function scaffold() {
    const obj: Record<string, string> = {};
    for (const p of selected.params) obj[p.name] = '';
    setArgsJson(JSON.stringify(obj, null, 2));
  }

  async function run() {
    setRunning(true);
    setOutput(null);
    setErr(null);
    try {
      const args = JSON.parse(argsJson) as Record<string, unknown>;
      const result = await bus.callTool(selected.name, args);
      setOutput(JSON.stringify(result, null, 2));
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div style={PANEL}>
      {/* Tool selector */}
      <div style={ROW}>
        <label htmlFor="tool-select">Tool</label>
        <select
          id="tool-select"
          value={selected.name}
          onChange={(e) => pickTool(e.target.value)}
          style={{ flex: 1 }}
        >
          {tools.map((t) => (
            <option key={t.name} value={t.name}>
              {t.name}
            </option>
          ))}
        </select>
        <span style={{ color: '#666', fontSize: 11 }}>{selected.description}</span>
      </div>

      {/* Param hints */}
      {selected.params.length > 0 && (
        <div style={{ padding: '4px 12px 0', fontSize: 11, color: '#888' }}>
          {selected.params.map((p) => (
            <span key={p.name} style={{ marginRight: 12 }}>
              <b>{p.name}</b>
              {p.required ? '*' : ''} — {p.description}
            </span>
          ))}
        </div>
      )}

      {/* Args */}
      <div style={{ padding: '8px 12px', borderBottom: '1px solid #ddd' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <label>Args (JSON)</label>
          <button onClick={scaffold} style={{ fontSize: 11 }}>
            scaffold
          </button>
        </div>
        <textarea
          value={argsJson}
          onChange={(e) => setArgsJson(e.target.value)}
          rows={4}
          style={{ width: '100%', boxSizing: 'border-box', fontFamily: 'monospace', fontSize: 12 }}
          spellCheck={false}
        />
        <button onClick={run} disabled={running} style={{ marginTop: 4 }}>
          {running ? 'Running…' : '▶ Run'}
        </button>
      </div>

      {/* Output */}
      <div style={{ flex: 1, padding: '8px 12px', overflow: 'auto' }}>
        {err && <pre style={{ color: 'red', margin: 0 }}>{err}</pre>}
        {output !== null && (
          <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{output}</pre>
        )}
        {output === null && !err && !running && (
          <span style={{ color: '#aaa' }}>— output appears here —</span>
        )}
      </div>
    </div>
  );
}
