import React, { useEffect, useMemo, useState } from 'react';
import { Bot, CheckCircle, ChevronUp, Loader2, MessageCircle, Play, XCircle } from 'lucide-react';
import { useOS } from './OSStore';

interface ActionCard {
  id: string;
  label: string;
  surface: string;
  intent: string;
  command: string;
  risk: 'low' | 'medium' | 'high' | string;
  feedback: string;
  agent_use: string;
}

interface ActionResult {
  action_id?: string;
  label?: string;
  command?: string;
  success?: boolean;
  exit_code?: number;
  duration_ms?: number;
  stdout_preview?: string;
  stderr_preview?: string;
  stdout_json?: unknown;
  error?: string | null;
}

type Message = {
  role: 'operator' | 'assistant' | 'system';
  text: string;
};

const DEFAULT_BRIDGE = 'http://127.0.0.1:3678';

function bridgeUrl() {
  const env = import.meta.env.VITE_SCBE_ACTION_BRIDGE;
  return env || window.localStorage.getItem('SCBE_ACTION_BRIDGE') || DEFAULT_BRIDGE;
}

function summarizeResult(result: ActionResult) {
  const status = result.success ? 'PASS' : 'FAIL';
  const time = result.duration_ms == null ? '' : ` in ${Math.round(result.duration_ms)}ms`;
  const exit = result.exit_code == null ? '' : ` exit ${result.exit_code}`;
  const line = `${status}${time}${exit}`;
  if (result.stdout_json && typeof result.stdout_json === 'object') {
    const schema = (result.stdout_json as { schema_version?: string }).schema_version;
    return schema ? `${line} · ${schema}` : line;
  }
  const preview = result.stdout_preview || result.stderr_preview || result.error || '';
  return preview ? `${line} · ${preview.split(/\r?\n/).find(Boolean)}` : line;
}

function chooseAction(input: string, actions: ActionCard[]) {
  const text = input.trim().toLowerCase();
  if (!text) return null;
  const direct = actions.find((action) => action.id.toLowerCase() === text);
  if (direct) return direct;
  const tokens = text.split(/[^a-z0-9.]+/).filter(Boolean);
  let best: { action: ActionCard; score: number } | null = null;
  for (const action of actions) {
    const haystack = [
      action.id,
      action.label,
      action.surface,
      action.intent,
      action.feedback,
      action.agent_use,
    ]
      .join(' ')
      .toLowerCase();
    const score = tokens.reduce((acc, token) => acc + (haystack.includes(token) ? 1 : 0), 0);
    if (!best || score > best.score) best = { action, score };
  }
  return best && best.score > 0 ? best.action : null;
}

export default function AgentActionBubble() {
  const { openApp, addNotification, isAppOpen } = useOS();
  const [open, setOpen] = useState(false);
  const [actions, setActions] = useState<ActionCard[]>([]);
  const [status, setStatus] = useState<'offline' | 'ready' | 'running'>('offline');
  const [selected, setSelected] = useState('terminal.state-json');
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'system',
      text: 'Headed agent bridge. Type a goal or click an action.',
    },
  ]);
  const [input, setInput] = useState('');
  const bridge = useMemo(() => bridgeUrl(), []);

  useEffect(() => {
    let cancelled = false;
    fetch(`${bridge}/actions`)
      .then((res) => res.json())
      .then((payload) => {
        if (cancelled) return;
        const loaded = Array.isArray(payload.actions) ? payload.actions : [];
        setActions(loaded);
        setStatus(loaded.length > 0 ? 'ready' : 'offline');
        if (loaded.some((action: ActionCard) => action.id === selected)) return;
        setSelected(loaded[0]?.id || '');
      })
      .catch(() => {
        if (!cancelled) setStatus('offline');
      });
    return () => {
      cancelled = true;
    };
  }, [bridge, selected]);

  const runAction = async (id: string) => {
    const action = actions.find((entry) => entry.id === id);
    if (!action) return;
    setStatus('running');
    setMessages((prev) => [
      ...prev,
      { role: 'operator', text: action.command },
      { role: 'assistant', text: `Running ${action.id} through ${bridge}` },
    ]);
    try {
      const res = await fetch(`${bridge}/actions/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: action.id }),
      });
      const result = (await res.json()) as ActionResult;
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: `${action.id}: ${summarizeResult(result)}`,
        },
      ]);
      addNotification({
        title: action.label,
        message: summarizeResult(result),
        type: result.success ? 'success' : 'warning',
      });
    } catch (err) {
      const text = err instanceof Error ? err.message : 'bridge request failed';
      setMessages((prev) => [...prev, { role: 'assistant', text: `Bridge failed: ${text}` }]);
      addNotification({ title: 'SCBE bridge offline', message: text, type: 'error' });
    } finally {
      setStatus('ready');
    }
  };

  const submit = () => {
    const action = chooseAction(input, actions);
    setMessages((prev) => [...prev, { role: 'operator', text: input }]);
    setInput('');
    if (!action) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: 'No action matched. Try: status, test desktop, terminal json, receipt smoke.',
        },
      ]);
      return;
    }
    setSelected(action.id);
    void runAction(action.id);
  };

  return (
    <div className="fixed bottom-16 right-4 z-[1000] flex flex-col items-end gap-2">
      {open && (
        <div
          data-testid="agent-action-panel"
          className="w-[380px] max-w-[calc(100vw-2rem)] overflow-hidden rounded-xl border border-cyan-300/20 bg-[#07111f]/95 shadow-2xl shadow-cyan-500/10 backdrop-blur-xl"
        >
          <div className="flex items-center justify-between border-b border-cyan-300/10 px-3 py-2">
            <div className="flex items-center gap-2">
              <Bot size={16} className="text-cyan-300" />
              <div>
                <div className="text-xs font-semibold text-cyan-100">SCBE action bridge</div>
                <div className="text-[10px] text-cyan-200/45">{bridge}</div>
              </div>
            </div>
            <div className="flex items-center gap-2 text-[10px]">
              {status === 'running' ? (
                <Loader2 size={13} className="animate-spin text-yellow-300" />
              ) : status === 'ready' ? (
                <CheckCircle size={13} className="text-emerald-300" />
              ) : (
                <XCircle size={13} className="text-red-300" />
              )}
              <span className={status === 'ready' ? 'text-emerald-200' : 'text-yellow-200'}>
                {status}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-[150px_1fr] gap-0">
            <div className="max-h-[310px] overflow-y-auto border-r border-cyan-300/10 p-2">
              {actions.slice(0, 11).map((action) => (
                <button
                  key={action.id}
                  onClick={() => setSelected(action.id)}
                  className={`mb-1 w-full rounded-md px-2 py-1.5 text-left text-[11px] transition ${
                    selected === action.id
                      ? 'bg-cyan-400/15 text-cyan-50 ring-1 ring-cyan-300/25'
                      : 'text-cyan-100/65 hover:bg-cyan-400/10'
                  }`}
                >
                  <div className="truncate font-medium">{action.label}</div>
                  <div className="truncate text-[9px] text-cyan-200/35">{action.surface}</div>
                </button>
              ))}
            </div>

            <div className="flex min-h-[310px] flex-col">
              <div className="border-b border-cyan-300/10 p-3">
                {actions
                  .filter((action) => action.id === selected)
                  .map((action) => (
                    <div key={action.id} className="space-y-2">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="text-sm font-semibold text-cyan-50">{action.label}</div>
                          <div className="text-[10px] text-cyan-200/40">{action.id}</div>
                        </div>
                        <span className="rounded bg-cyan-300/10 px-1.5 py-0.5 text-[9px] uppercase text-cyan-100/70">
                          {action.risk}
                        </span>
                      </div>
                      <div className="text-[11px] leading-snug text-cyan-100/65">
                        {action.feedback}
                      </div>
                      <button
                        data-testid={`run-action-${action.id}`}
                        onClick={() => void runAction(action.id)}
                        disabled={status === 'running'}
                        className="flex w-full items-center justify-center gap-1.5 rounded-md bg-emerald-400/15 px-3 py-2 text-xs font-semibold text-emerald-100 transition hover:bg-emerald-400/25 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        <Play size={13} />
                        Run true action
                      </button>
                    </div>
                  ))}
              </div>

              <div className="flex-1 space-y-2 overflow-y-auto p-3">
                {messages.slice(-6).map((message, index) => (
                  <div
                    key={`${message.role}-${index}`}
                    className={`rounded-lg px-2 py-1.5 text-[11px] leading-snug ${
                      message.role === 'operator'
                        ? 'ml-8 bg-blue-400/10 text-blue-100'
                        : message.role === 'system'
                          ? 'bg-white/5 text-cyan-100/50'
                          : 'mr-8 bg-cyan-300/10 text-cyan-50'
                    }`}
                  >
                    {message.text}
                  </div>
                ))}
              </div>

              <div className="flex gap-2 border-t border-cyan-300/10 p-2">
                <input
                  data-testid="agent-action-input"
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') submit();
                  }}
                  className="min-w-0 flex-1 rounded-md border border-cyan-300/10 bg-black/20 px-2 py-1.5 text-xs text-cyan-50 outline-none placeholder:text-cyan-100/25"
                  placeholder="say: run receipt smoke"
                />
                <button
                  onClick={submit}
                  className="rounded-md bg-cyan-300/15 px-2.5 text-xs font-semibold text-cyan-50 hover:bg-cyan-300/25"
                >
                  Send
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <button
        data-testid="agent-action-bubble"
        onClick={() => {
          setOpen((value) => !value);
          if (!open && !isAppOpen('multiagent')) openApp('multiagent');
        }}
        className="flex items-center gap-2 rounded-full border border-cyan-300/20 bg-[#07111f]/95 px-4 py-3 text-sm font-semibold text-cyan-50 shadow-xl shadow-cyan-500/10 backdrop-blur-xl transition hover:border-cyan-300/40 hover:bg-[#0a1a2f]"
      >
        <MessageCircle size={17} />
        Agent actions
        <ChevronUp size={15} className={open ? 'rotate-180 transition' : 'transition'} />
      </button>
    </div>
  );
}
