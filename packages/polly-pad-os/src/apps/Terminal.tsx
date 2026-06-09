// @ts-nocheck
import React, { useEffect, useRef, useState } from 'react';

type TerminalLine = {
  kind: 'input' | 'output' | 'error' | 'system';
  text: string;
  prompt?: string;
};

type CommandResult = {
  schema_version: string;
  command?: string;
  cwd?: string;
  next_cwd?: string;
  shell?: string;
  success?: boolean;
  exit_code?: number;
  duration_ms?: number;
  stdout?: string;
  stderr?: string;
  error?: string;
};

const DEFAULT_BRIDGE = 'http://127.0.0.1:3678';

function configuredBridgeUrl() {
  const viteBridge = import.meta.env.VITE_SCBE_ACTION_BRIDGE;
  if (viteBridge) return viteBridge;
  try {
    return localStorage.getItem('scbe_action_bridge') || DEFAULT_BRIDGE;
  } catch {
    return DEFAULT_BRIDGE;
  }
}

function compactPath(path: string) {
  if (!path) return 'repo';
  return path.replace(/^C:\\Users\\issda\\SCBE-AETHERMOORE/i, 'SCBE');
}

function promptFor(cwd: string) {
  return `PS ${compactPath(cwd)}>`;
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

export default function Terminal() {
  const [bridgeUrl, setBridgeUrl] = useState(configuredBridgeUrl());
  const [cwd, setCwd] = useState('C:\\Users\\issda\\SCBE-AETHERMOORE');
  const [shell, setShell] = useState('powershell.exe');
  const [input, setInput] = useState('');
  const [running, setRunning] = useState(false);
  const [history, setHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [lines, setLines] = useState<TerminalLine[]>([
    {
      kind: 'system',
      text: 'SCBE PowerShell bridge. Type help, /actions, /action repo.status, or any PowerShell command.',
    },
  ]);
  const inputRef = useRef<HTMLInputElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [lines, running]);

  useEffect(() => {
    fetch(`${bridgeUrl}/terminal/session`)
      .then((response) => response.json())
      .then((session) => {
        if (session?.cwd) setCwd(session.cwd);
        if (session?.shell) setShell(session.shell);
        setLines((prev) => [
          ...prev,
          { kind: 'system', text: `bridge ready: ${bridgeUrl} (${session.shell || shell})` },
        ]);
      })
      .catch(() => {
        setLines((prev) => [
          ...prev,
          {
            kind: 'error',
            text: `bridge offline: ${bridgeUrl}. Start it with scbe desktop open or scbe desktop bridge.`,
          },
        ]);
      });
  }, [bridgeUrl]);

  const push = (items: TerminalLine[]) => setLines((prev) => [...prev, ...items]);

  const runAction = async (id: string) => {
    const result = await postJson(`${bridgeUrl}/actions/run`, { id });
    const payload = result.data;
    push([
      {
        kind: payload.success ? 'output' : 'error',
        text: `${payload.action_id || id}: ${payload.success ? 'PASS' : 'FAIL'} exit ${payload.exit_code ?? '?'}\n${payload.stdout_preview || payload.stderr_preview || payload.error || ''}`,
      },
    ]);
  };

  const runCommand = async (raw: string) => {
    const command = raw.trim();
    if (!command) return;
    const prompt = promptFor(cwd);
    setHistory((prev) => [...prev, command]);
    setHistoryIndex(-1);
    push([{ kind: 'input', text: command, prompt }]);

    if (command === 'clear') {
      setLines([]);
      return;
    }
    if (command === 'help') {
      push([
        {
          kind: 'system',
          text: [
            'Built-ins:',
            '  help',
            '  clear',
            '  bridge <url>',
            '  /actions',
            '  /action <id>',
            '  /open <url or search>',
            '',
            'Everything else is sent to real PowerShell through the bridge.',
          ].join('\n'),
        },
      ]);
      return;
    }
    if (command.startsWith('bridge ')) {
      const next = command.slice('bridge '.length).trim();
      setBridgeUrl(next);
      try {
        localStorage.setItem('scbe_action_bridge', next);
      } catch {
        // ignored
      }
      push([{ kind: 'system', text: `bridge set: ${next}` }]);
      return;
    }
    if (command === '/actions') {
      const response = await fetch(`${bridgeUrl}/actions`);
      const payload = await response.json();
      push([
        {
          kind: 'output',
          text: payload.actions
            .map(
              (action: { id: string; label: string }) => `${action.id.padEnd(24)} ${action.label}`
            )
            .join('\n'),
        },
      ]);
      return;
    }
    if (command.startsWith('/action ')) {
      await runAction(command.slice('/action '.length).trim());
      return;
    }
    if (command.startsWith('/open ')) {
      const result = await postJson(`${bridgeUrl}/internet/open`, {
        url: command.slice('/open '.length).trim(),
      });
      push([
        {
          kind: result.ok ? 'output' : 'error',
          text: result.ok
            ? `opened in system browser: ${result.data.url}`
            : result.data.error || 'internet open failed',
        },
      ]);
      return;
    }

    setRunning(true);
    try {
      const result = await postJson(`${bridgeUrl}/terminal/run`, { command, cwd });
      const payload = result.data as CommandResult;
      if (payload.next_cwd) setCwd(payload.next_cwd);
      const out: TerminalLine[] = [];
      if (payload.stdout) out.push({ kind: 'output', text: payload.stdout });
      if (payload.stderr) out.push({ kind: 'error', text: payload.stderr });
      if (!payload.stdout && !payload.stderr) {
        out.push({
          kind: payload.success ? 'system' : 'error',
          text: `exit ${payload.exit_code ?? '?'} in ${payload.duration_ms ?? '?'}ms`,
        });
      } else {
        out.push({
          kind: 'system',
          text: `exit ${payload.exit_code ?? '?'} in ${payload.duration_ms ?? '?'}ms`,
        });
      }
      push(out);
    } catch (err) {
      push([{ kind: 'error', text: err instanceof Error ? err.message : 'command failed' }]);
    } finally {
      setRunning(false);
    }
  };

  const onKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter' && !running) {
      const next = input;
      setInput('');
      void runCommand(next);
      return;
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      if (historyIndex < history.length - 1) {
        const nextIndex = historyIndex + 1;
        setHistoryIndex(nextIndex);
        setInput(history[history.length - 1 - nextIndex] || '');
      }
      return;
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      if (historyIndex > 0) {
        const nextIndex = historyIndex - 1;
        setHistoryIndex(nextIndex);
        setInput(history[history.length - 1 - nextIndex] || '');
      } else {
        setHistoryIndex(-1);
        setInput('');
      }
    }
  };

  return (
    <div
      className="h-full w-full bg-[#080b0f] text-zinc-100 font-mono text-xs flex flex-col"
      onClick={() => inputRef.current?.focus()}
    >
      <div className="flex items-center justify-between border-b border-zinc-700/60 bg-[#11151b] px-3 py-2">
        <div>
          <div className="text-[11px] uppercase tracking-[0.16em] text-cyan-300">
            SCBE PowerShell
          </div>
          <div className="text-[10px] text-zinc-400">{bridgeUrl}</div>
        </div>
        <div className="text-[10px] text-zinc-400">{shell}</div>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 py-3 space-y-1">
        {lines.map((line, index) => (
          <div key={index} className="whitespace-pre-wrap break-words">
            {line.kind === 'input' && <span className="text-cyan-300">{line.prompt} </span>}
            <span
              className={
                line.kind === 'error'
                  ? 'text-red-300'
                  : line.kind === 'system'
                    ? 'text-amber-200'
                    : line.kind === 'input'
                      ? 'text-zinc-100'
                      : 'text-emerald-200'
              }
            >
              {line.text}
            </span>
          </div>
        ))}
        {running && <div className="text-cyan-300">running...</div>}
      </div>

      <div className="border-t border-zinc-700/60 bg-[#0d1117] px-3 py-2">
        <div className="flex items-center gap-2">
          <span className="shrink-0 text-cyan-300">{promptFor(cwd)}</span>
          <input
            ref={inputRef}
            data-testid="powershell-input"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={onKeyDown}
            disabled={running}
            spellCheck={false}
            autoComplete="off"
            style={{ color: '#f8fafc', caretColor: '#67e8f9' }}
            className="min-w-0 flex-1 bg-transparent text-zinc-50 outline-none disabled:opacity-50"
          />
        </div>
      </div>
    </div>
  );
}
