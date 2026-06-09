import React, { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  Bot,
  Camera,
  CheckCircle,
  Play,
  RefreshCw,
  Terminal,
  XCircle,
} from 'lucide-react';

type ActionEntry = {
  id: string;
  label: string;
  description?: string;
  risk?: string;
  command?: string;
};

type ConsoleLine = {
  kind: 'ok' | 'error' | 'system';
  text: string;
};

const DEFAULT_BRIDGE = 'http://127.0.0.1:3678';

function bridgeUrl() {
  return import.meta.env.VITE_SCBE_ACTION_BRIDGE || DEFAULT_BRIDGE;
}

async function postJson(url: string, payload: unknown) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  return { ok: response.ok, data };
}

export default function MultiAgentTerminal() {
  const [health, setHealth] = useState<any>(null);
  const [actions, setActions] = useState<ActionEntry[]>([]);
  const [selectedId, setSelectedId] = useState('repo.status');
  const [query, setQuery] = useState('');
  const [command, setCommand] = useState('git status --short');
  const [running, setRunning] = useState(false);
  const [lines, setLines] = useState<ConsoleLine[]>([
    {
      kind: 'system',
      text: 'Tool Console is a bridge surface. It only reports commands that actually ran.',
    },
  ]);

  const bridge = bridgeUrl();
  const selectedAction = actions.find((action) => action.id === selectedId) || actions[0];
  const filteredActions = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return actions;
    return actions.filter((action) =>
      `${action.id} ${action.label} ${action.description || ''}`.toLowerCase().includes(needle)
    );
  }, [actions, query]);

  const push = (line: ConsoleLine) => setLines((prev) => [...prev.slice(-80), line]);

  const refresh = async () => {
    try {
      const [healthResponse, actionsResponse] = await Promise.all([
        fetch(`${bridge}/health`).then((response) => response.json()),
        fetch(`${bridge}/actions`).then((response) => response.json()),
      ]);
      setHealth(healthResponse);
      setActions(actionsResponse.actions || []);
      if (!selectedId && actionsResponse.actions?.[0]?.id)
        setSelectedId(actionsResponse.actions[0].id);
      push({ kind: 'system', text: `bridge ready: ${bridge}` });
    } catch (err) {
      push({
        kind: 'error',
        text: `bridge offline: ${err instanceof Error ? err.message : 'connection failed'}`,
      });
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const runAction = async (id: string) => {
    setRunning(true);
    try {
      const result = await postJson(`${bridge}/actions/run`, { id });
      const payload = result.data;
      push({
        kind: payload.success ? 'ok' : 'error',
        text: [
          `${payload.action_id || id}: ${payload.success ? 'PASS' : 'FAIL'} exit ${payload.exit_code ?? '?'}`,
          payload.stdout_preview || payload.stderr_preview || payload.error || '',
        ]
          .filter(Boolean)
          .join('\n'),
      });
    } catch (err) {
      push({ kind: 'error', text: err instanceof Error ? err.message : 'action failed' });
    } finally {
      setRunning(false);
    }
  };

  const runCommand = async () => {
    const text = command.trim();
    if (!text) return;
    setRunning(true);
    try {
      const result = await postJson(`${bridge}/terminal/run`, { command: text });
      const payload = result.data;
      push({
        kind: payload.success ? 'ok' : 'error',
        text: [
          `PS: ${text}`,
          payload.stdout || payload.stderr || payload.error || `exit ${payload.exit_code ?? '?'}`,
        ]
          .filter(Boolean)
          .join('\n'),
      });
    } catch (err) {
      push({ kind: 'error', text: err instanceof Error ? err.message : 'command failed' });
    } finally {
      setRunning(false);
    }
  };

  const capture = async () => {
    setRunning(true);
    try {
      const result = await postJson(`${bridge}/screen/capture`, {});
      push({
        kind: result.ok ? 'ok' : 'error',
        text: result.ok
          ? `screen captured: ${result.data.out_path}`
          : result.data.error || 'screen capture failed',
      });
    } catch (err) {
      push({ kind: 'error', text: err instanceof Error ? err.message : 'screen capture failed' });
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#090d12] text-zinc-100">
      <div className="flex items-center justify-between border-b border-zinc-700/60 bg-[#111820] px-3 py-2">
        <div className="flex items-center gap-2">
          <Bot size={16} className="text-cyan-300" />
          <div>
            <div className="text-sm font-semibold text-zinc-100">Tool Console</div>
            <div className="text-[10px] text-zinc-400">{bridge}</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`rounded px-2 py-1 text-[10px] ${
              health?.ok ? 'bg-emerald-500/15 text-emerald-200' : 'bg-red-500/15 text-red-200'
            }`}
          >
            {health?.ok ? 'bridge online' : 'bridge unknown'}
          </span>
          <button
            onClick={refresh}
            className="rounded border border-zinc-700/80 px-2 py-1 text-xs text-zinc-300 hover:bg-zinc-800"
          >
            <RefreshCw size={12} />
          </button>
        </div>
      </div>

      <div className="grid flex-1 min-h-0 grid-cols-[260px_1fr]">
        <aside className="min-h-0 border-r border-zinc-700/60 bg-[#0d1218] p-3">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Filter true actions"
            className="mb-3 w-full rounded border border-zinc-700 bg-[#080b0f] px-2 py-2 text-xs text-zinc-100 outline-none"
            style={{ color: '#f8fafc', caretColor: '#67e8f9' }}
          />
          <div
            className="space-y-1 overflow-y-auto pr-1"
            style={{ maxHeight: 'calc(100% - 44px)' }}
          >
            {filteredActions.map((action) => (
              <button
                key={action.id}
                onClick={() => setSelectedId(action.id)}
                className={`w-full rounded border px-2 py-2 text-left text-xs ${
                  selectedId === action.id
                    ? 'border-cyan-400/50 bg-cyan-500/10'
                    : 'border-zinc-800 bg-zinc-950/40 hover:bg-zinc-900'
                }`}
              >
                <div className="font-semibold text-zinc-100">{action.label}</div>
                <div className="mt-0.5 text-[10px] text-zinc-500">{action.id}</div>
              </button>
            ))}
          </div>
        </aside>

        <main className="flex min-h-0 flex-col">
          <section className="border-b border-zinc-700/60 p-3">
            {selectedAction ? (
              <div className="grid grid-cols-[1fr_auto] gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <Activity size={14} className="text-cyan-300" />
                    <span className="text-sm font-semibold">{selectedAction.label}</span>
                    <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-400">
                      {selectedAction.risk || 'unknown risk'}
                    </span>
                  </div>
                  <div className="mt-1 text-xs text-zinc-400">{selectedAction.description}</div>
                  <div className="mt-2 rounded bg-black/40 px-2 py-1 font-mono text-[11px] text-zinc-400">
                    {selectedAction.command}
                  </div>
                </div>
                <button
                  onClick={() => runAction(selectedAction.id)}
                  disabled={running}
                  className="h-9 rounded bg-cyan-400 px-3 text-xs font-semibold text-black hover:bg-cyan-300 disabled:opacity-50"
                >
                  <Play size={13} className="mr-1 inline" />
                  Run
                </button>
              </div>
            ) : (
              <div className="text-xs text-zinc-500">No bridge actions loaded.</div>
            )}
          </section>

          <section className="border-b border-zinc-700/60 p-3">
            <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-zinc-300">
              <Terminal size={14} className="text-cyan-300" />
              Real PowerShell command
            </div>
            <div className="flex gap-2">
              <input
                value={command}
                onChange={(event) => setCommand(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !running) void runCommand();
                }}
                className="min-w-0 flex-1 rounded border border-zinc-700 bg-[#080b0f] px-2 py-2 font-mono text-xs text-zinc-100 outline-none"
                style={{ color: '#f8fafc', caretColor: '#67e8f9' }}
              />
              <button
                onClick={runCommand}
                disabled={running}
                className="rounded border border-cyan-400/50 px-3 text-xs text-cyan-200 hover:bg-cyan-500/10 disabled:opacity-50"
              >
                Run PS
              </button>
              <button
                onClick={capture}
                disabled={running}
                className="rounded border border-zinc-700 px-3 text-xs text-zinc-300 hover:bg-zinc-800 disabled:opacity-50"
              >
                <Camera size={13} className="mr-1 inline" />
                Capture
              </button>
            </div>
          </section>

          <section className="min-h-0 flex-1 overflow-y-auto p-3 font-mono text-xs">
            {lines.map((line, index) => (
              <div key={index} className="mb-2 flex gap-2 whitespace-pre-wrap break-words">
                {line.kind === 'ok' ? (
                  <CheckCircle size={13} className="mt-0.5 shrink-0 text-emerald-300" />
                ) : line.kind === 'error' ? (
                  <XCircle size={13} className="mt-0.5 shrink-0 text-red-300" />
                ) : (
                  <Activity size={13} className="mt-0.5 shrink-0 text-zinc-500" />
                )}
                <span
                  className={
                    line.kind === 'ok'
                      ? 'text-emerald-100'
                      : line.kind === 'error'
                        ? 'text-red-200'
                        : 'text-zinc-400'
                  }
                >
                  {line.text}
                </span>
              </div>
            ))}
          </section>
        </main>
      </div>
    </div>
  );
}
