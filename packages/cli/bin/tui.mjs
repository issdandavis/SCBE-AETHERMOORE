/**
 * @file tui.mjs
 * @description SCBE governed shell — Ink TUI (scbe shell --tui)
 *
 * ESM module: loaded via dynamic import() from scbe.js (CJS).
 * No build step required — written in plain ESM using React.createElement.
 * Ink 4 (ESM-only) + React 18.
 */

import React, { useState, useRef, useEffect } from 'react';
import { render, Box, Text, Static, useInput, useApp } from 'ink';
import { spawnSync } from 'node:child_process';

// ─── Message helpers ──────────────────────────────────────────────────────────

let _mid = 0;
const mkMsg = (kind, text) => ({ id: String(++_mid), kind, text });

const MSG_COLOR = {
  user: 'cyan', ai: 'white', command: 'gray', info: 'gray',
  system: 'yellow', error: 'red', search: 'blue', governance: 'green',
};
const MSG_PREFIX = {
  user: 'you  ', ai: 'ai   ', command: '$    ', info: '     ',
  system: 'sys  ', error: 'err  ', search: 'web  ', governance: 'gov  ',
};
const h = React.createElement;

// ─── Components ───────────────────────────────────────────────────────────────

function MsgLine({ msg }) {
  const color = MSG_COLOR[msg.kind] || 'white';
  const prefix = MSG_PREFIX[msg.kind] || '     ';
  const lines = String(msg.text || '').split('\n');
  return h(Box, { flexDirection: 'column' },
    ...lines.map((line, i) =>
      h(Box, { key: String(i) },
        h(Text, { dimColor: true }, i === 0 ? prefix + ' ' : '       '),
        h(Text, { color }, line)
      )
    )
  );
}

function StatusBar({ provider, model, branch }) {
  const parts = ['SCBE', `${provider}:${model}`, branch ? `git:${branch}` : ''].filter(Boolean);
  return h(Box, { paddingX: 1, marginBottom: 1 },
    h(Text, { dimColor: true }, parts.join(' │ '))
  );
}

function InputBox({ value, busy, awaitingApproval }) {
  if (awaitingApproval !== null) {
    return h(Box, { borderStyle: 'round', paddingX: 1, marginTop: 1 },
      h(Text, { color: 'yellow' }, 'execute? '),
      h(Text, { color: 'gray' }, '[y/N] '),
      h(Text, { color: 'white' }, value),
      h(Text, { color: 'cyan' }, '▌')
    );
  }
  return h(Box, { borderStyle: 'round', paddingX: 1, marginTop: 1 },
    h(Text, { color: 'cyan', bold: true }, 'scbe '),
    h(Text, { color: 'cyan' }, '› '),
    busy
      ? h(Text, { dimColor: true }, 'thinking…')
      : h(React.Fragment, null,
          h(Text, { color: 'white' }, value),
          h(Text, { color: 'cyan' }, '▌')
        )
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────

function App({ engine }) {
  const { exit } = useApp();
  const cfg = engine.readShellConfig();

  let branch = '';
  try {
    const g = engine.gitPosture(engine.repoRoot());
    if (g.branch && g.branch !== 'unknown') branch = `${g.branch}${g.dirty ? '*' : ''}`;
  } catch { /* no git */ }

  const [completedMsgs, setCompletedMsgs] = useState([
    mkMsg('info', 'Type a command, plain English, or :help'),
    mkMsg('info', '!cmd or ps:cmd → PowerShell  │  :search <query>  │  :exit'),
  ]);
  const [streamingMsg, setStreamingMsg] = useState(null);
  const [inputValue, setInputValue] = useState('');
  const [busy, setBusy] = useState(false);
  const [awaitingApproval, setAwaitingApproval] = useState(null);

  // Refs: keep latest values accessible inside useInput callback (avoids stale closure)
  const inputRef = useRef('');
  const busyRef = useRef(false);
  const approvalRef = useRef(null);
  const convHistory = useRef([]);

  useEffect(() => { inputRef.current = inputValue; }, [inputValue]);
  useEffect(() => { busyRef.current = busy; }, [busy]);
  useEffect(() => { approvalRef.current = awaitingApproval; }, [awaitingApproval]);

  const pushMsg = (kind, text) => setCompletedMsgs(prev => [...prev, mkMsg(kind, text)]);

  async function handleLine(line) {
    // ── Approval flow ────────────────────────────────────────────────────────
    if (approvalRef.current !== null) {
      const proposed = approvalRef.current;
      setAwaitingApproval(null);
      approvalRef.current = null;
      if (line.trim().toLowerCase() === 'y' || line.trim().toLowerCase() === 'yes') {
        pushMsg('command', '$ ' + proposed);
        const row = engine.runShellCommand(proposed, { quiet: true, capture: true, json: true });
        if (row.stdout_preview?.trim()) pushMsg('command', row.stdout_preview.trim().slice(0, 600));
        if (!row.success && row.failure) {
          pushMsg('error', row.failure.summary);
          pushMsg('info', '→ ' + row.failure.next_step);
        }
      } else {
        pushMsg('info', 'skipped.');
      }
      return;
    }

    pushMsg('user', line);
    const kind = engine.classifyShellInput(line);

    // ── Meta commands (:help, :config, :search, …) ───────────────────────────
    if (kind === 'meta') {
      const parts = line.slice(1).split(/\s+/);
      const meta = parts[0];
      const margs = parts.slice(1);

      if (meta === 'exit' || meta === 'quit') { exit(); return; }
      if (meta === 'help') {
        pushMsg('info', 'Commands: ' + engine.KNOWN_COMMANDS.slice(0, 12).join(' ') + ' …');
        pushMsg('info', ':help :status :config [:set key val] :search <q> :history :clear :exit');
        return;
      }
      if (meta === 'clear') { process.stdout.write('\x1b[2J\x1b[H'); setCompletedMsgs([]); return; }
      if (meta === 'status') {
        pushMsg('info', `${cfg.provider}:${cfg.model} │ git:${branch || '(none)'}`);
        return;
      }
      if (meta === 'config') {
        if (margs[0] === 'set' && margs[1]) {
          cfg[margs[1]] = margs.slice(2).join(' ');
          engine.saveShellConfig(cfg);
          pushMsg('governance', `config.${margs[1]} = ${cfg[margs[1]]}`);
        } else {
          const d = { ...cfg };
          if (d.openai_api_key) d.openai_api_key = '***';
          if (d.api_key) d.api_key = '***';
          if (d.groq_api_key) d.groq_api_key = '***';
          pushMsg('info', JSON.stringify(d, null, 2));
        }
        return;
      }
      if (meta === 'history') {
        pushMsg('info', ':history is not available in TUI mode — check artifacts/scbe-terminal/history.jsonl');
        return;
      }
      if (meta === 'search') {
        const q = margs.join(' ');
        if (!q) { pushMsg('system', 'Usage: :search <query>'); return; }
        setBusy(true);
        busyRef.current = true;
        pushMsg('info', `searching: ${q}…`);
        engine.searchWeb(q).then(r => {
          if (r.error) {
            pushMsg('error', r.error);
          } else if (!r.results?.length) {
            pushMsg('info', 'no results found.');
          } else {
            for (const res of r.results) {
              pushMsg('search', `${res.title}\n  ${(res.snippet || '').slice(0, 140)}\n  ${res.url}`);
            }
          }
          setBusy(false);
          busyRef.current = false;
        }).catch(err => {
          pushMsg('error', 'search failed: ' + err.message);
          setBusy(false);
          busyRef.current = false;
        });
        return;
      }
      pushMsg('system', `:${meta} unknown — try :help`);
      return;
    }

    // ── PowerShell passthrough  (!cmd or ps:cmd) ─────────────────────────────
    if (kind === 'powershell') {
      const cmd = line.replace(/^(!|ps:)\s*/, '').trim();
      if (!cmd) return;
      pushMsg('command', '$ ' + cmd);
      const row = engine.runShellCommand(cmd, { quiet: true, capture: true, json: true });
      if (row.stdout_preview?.trim()) pushMsg('command', row.stdout_preview.trim().slice(0, 600));
      if (!row.success && row.failure) {
        pushMsg('error', row.failure.summary);
        pushMsg('info', '→ ' + row.failure.next_step);
      }
      return;
    }

    // ── Known scbe subcommand ─────────────────────────────────────────────────
    if (kind === 'command') {
      const r = spawnSync(process.execPath, [engine.scbeBin, ...line.split(/\s+/)], {
        encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], timeout: 30000,
      });
      const out = (r.stdout || '').trim();
      const err = (r.stderr || '').trim();
      if (out) pushMsg('command', out.slice(0, 1000));
      if (err) pushMsg('error', err.slice(0, 400));
      return;
    }

    // ── Natural language intent → LLM → GeoSeal → approve/execute ────────────
    setBusy(true);
    busyRef.current = true;
    const liveMsg = mkMsg('ai', '');
    setStreamingMsg(liveMsg);
    let accumulated = '';

    try {
      const full = await engine.streamLLM(line, cfg, convHistory.current, (token) => {
        accumulated += token;
        setStreamingMsg(prev => prev ? { ...prev, text: accumulated } : null);
      });

      setStreamingMsg(null);
      setCompletedMsgs(prev => [...prev, { ...liveMsg, text: full || '(no response)' }]);

      convHistory.current.push(
        { role: 'user', content: line },
        { role: 'assistant', content: full }
      );
      if (convHistory.current.length > 20) convHistory.current.splice(0, 2);

      const cmdMatch = full.match(/<cmd>([\s\S]*?)<\/cmd>/);
      if (!cmdMatch) return;

      const proposed = cmdMatch[1].trim();
      pushMsg('governance', 'proposed: ' + proposed);

      const busBin = engine.resolveAgentBusBin();
      if (!busBin) return;

      pushMsg('info', 'checking governance…');
      let blocked = true;
      let blockReason = 'compile failed';
      try {
        const r = spawnSync(
          process.execPath,
          [busBin, 'pipeline', 'compile', '--intent', proposed, '--json'],
          { encoding: 'utf8', timeout: 15000, maxBuffer: 1024 * 512 }
        );
        if (r.status === 0 && r.stdout) {
          const plan = JSON.parse(r.stdout);
          blocked = !!(plan.policy && plan.policy.decision !== 'ALLOW');
          if (!blocked) {
            pushMsg('governance', `✓ GeoSeal: ${plan.policy.decision} (${plan.policy.reason})`);
            if (plan.semantic?.discourseProfile) {
              pushMsg('info', `semantic: ${plan.semantic.dominant} → ${plan.semantic.discourseProfile}`);
            }
          } else {
            blockReason = `policy ${plan.policy.decision}: ${plan.policy.reason}`;
            pushMsg('error', '✗ blocked: ' + blockReason);
          }
        }
      } catch {
        pushMsg('error', '✗ blocked: ' + blockReason);
      }

      if (!blocked) {
        setAwaitingApproval(proposed);
        approvalRef.current = proposed;
        pushMsg('system', 'execute? [y/N]');
      }
    } catch (err) {
      setStreamingMsg(null);
      pushMsg('error', 'LLM error: ' + err.message);
      pushMsg('info', `Is ${cfg.provider} running? Try: :config set provider offline`);
    } finally {
      setBusy(false);
      busyRef.current = false;
    }
  }

  useInput((char, key) => {
    if (key.ctrl && char === 'c') { exit(); return; }
    if (busyRef.current) return;

    if (key.return) {
      const line = inputRef.current;
      setInputValue('');
      inputRef.current = '';
      if (line.trim()) handleLine(line);
      return;
    }
    if (key.backspace || key.delete) {
      setInputValue(p => p.slice(0, -1));
      return;
    }
    if (!key.ctrl && !key.meta && char) {
      setInputValue(p => p + char);
    }
  });

  // ── Render ────────────────────────────────────────────────────────────────
  return h(Box, { flexDirection: 'column' },
    h(StatusBar, { provider: cfg.provider || 'ollama', model: cfg.model || 'llama3.2', branch }),
    h(Static, { items: completedMsgs },
      (msg) => h(MsgLine, { key: msg.id, msg })
    ),
    streamingMsg && h(MsgLine, { msg: streamingMsg }),
    h(InputBox, { value: inputValue, busy, awaitingApproval })
  );
}

// ─── Public entry point ───────────────────────────────────────────────────────

/**
 * Launch the Ink TUI. Called from scbe.js via dynamic import().
 *
 * @param {object} engine - Shell engine injected from scbe.js:
 *   scbeBin, resolveAgentBusBin, runShellCommand, streamLLM, searchWeb,
 *   classifyShellInput, readShellConfig, saveShellConfig, KNOWN_COMMANDS,
 *   gitPosture, repoRoot
 */
export function launchTui(engine) {
  render(h(App, { engine }));
}
