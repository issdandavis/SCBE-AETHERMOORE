'use strict';

/**
 * AetherDesk Operator Shell v0 — local server
 *
 * Binds to 127.0.0.1:5717 only. Exposes a small set of allowlisted
 * "known-good command" routes from docs/specs/AETHERDESK_OPERATOR_SHELL_v0.md.
 * Every command run writes a GeoSeal-shaped receipt to
 * artifacts/aetherdesk_receipts/ that the UI can list and re-open.
 *
 * Non-goals (v0):
 *   - No arbitrary command execution. The allowlist is the security boundary.
 *   - No remote access. The bind address is hardcoded to 127.0.0.1.
 *   - No secrets in receipts. stderr/stdout tails are truncated.
 */

const express = require('express');
const { spawn } = require('child_process');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const REPO_ROOT = path.resolve(__dirname, '..');
const RECEIPTS_DIR = path.join(REPO_ROOT, 'artifacts', 'aetherdesk_receipts');
const EMAIL_DRAFTS_DIR = path.join(REPO_ROOT, 'artifacts', 'aetherdesk_email_drafts');
const NOTEBOOKS_DIR = path.join(REPO_ROOT, 'artifacts', 'aetherdesk_notebooks');
const PORT = Number(process.env.AETHERDESK_PORT || 5717);
const HOST = '127.0.0.1';
const MAX_OUTPUT_TAIL_BYTES = 8192;
const COMMAND_TIMEOUT_MS = 10 * 60 * 1000;
const SHELL_TIMEOUT_MS = 45 * 1000;
const PLAYWRIGHT_TIMEOUT_MS = 15 * 1000;
const POWERSHELL_TIMEOUT_MS = 45 * 1000;
const TRANSCRIPT_TIMEOUT_MS = 45 * 1000;
const RUN_CONTROL_TIMEOUT_MS = 45 * 1000;
const WORKTREE_GARDEN_TIMEOUT_MS = 45 * 1000;
const MAX_TERMINAL_COMMAND_CHARS = 900;
const MAX_EMAIL_FIELD_CHARS = 4000;
const MAX_NOTEBOOK_CHARS = 200000;
const YOUTUBE_VIDEO_ID_RE = /^[A-Za-z0-9_-]{11}$/;
const BLOCKED_POWERSHELL_PATTERNS = Object.freeze([
  /\bRemove-Item\b/i,
  /\brm\b/i,
  /\bdel\b/i,
  /\berase\b/i,
  /\brmdir\b/i,
  /\bformat\b/i,
  /\bdiskpart\b/i,
  /\bshutdown\b/i,
  /\brestart-computer\b/i,
  /\bstop-computer\b/i,
  /\bSet-ExecutionPolicy\b/i,
  /\breg\s+(add|delete|import)\b/i,
  /\bgit\s+(reset|clean|push)\b/i,
  />\s*[^|]/,
  />>/,
  /\|\s*Out-File\b/i,
  /\|\s*Set-Content\b/i,
  /\|\s*Add-Content\b/i,
]);

// The allowlist is the security boundary. Every entry is a {npm, script}
// reference resolved against package.json scripts. Frontend cannot pass a
// raw shell string; it can only ask to run one of these IDs.
const COMMAND_ALLOWLIST = Object.freeze({
  typecheck: {
    label: 'Typecheck (TypeScript)',
    npmScript: 'typecheck',
    category: 'Checks',
    icon: 'check',
    risk_tier: 'read-only',
    description: 'tsc --noEmit — no files are written.',
  },
  ts_tests: {
    label: 'TS tests (vitest)',
    npmScript: 'test',
    category: 'Checks',
    icon: 'test',
    risk_tier: 'read-only',
    description: 'Run the full Vitest suite.',
  },
  benchmark_cli: {
    label: 'CLI benchmark',
    npmScript: 'benchmark:cli',
    category: 'Benchmarks',
    icon: 'chart',
    risk_tier: 'read-only',
    description: 'Run scripts/benchmark/cli_competitive_benchmark.py.',
  },
  research_aether_lattice: {
    label: 'Aether-Lattice sim',
    npmScript: 'research:aether-lattice',
    category: 'Research',
    icon: 'lattice',
    risk_tier: 'read-only',
    description: 'Run the Aether-Lattice containment simulator (deterministic seed=42).',
  },
  benchmark_coding_agents: {
    label: 'Coding-agent benchmark',
    npmScript: 'benchmark:coding-agents',
    category: 'Benchmarks',
    icon: 'agent',
    risk_tier: 'read-only',
    description:
      'Run scripts/eval/functional_coding_agent_benchmark.py. Note: TS scenario runner is missing per spec; see AETHERDESK_OPERATOR_SHELL_v0.md.',
  },
  chemistry_lookup: {
    label: 'Chemistry Lookup',
    npmScript: 'aetherdesk:chemistry',
    category: 'Tools',
    icon: 'atom',
    risk_tier: 'read-only',
    description: 'Formula dimensional analysis demo: atoms, protons, neutrons, electrons, and molar mass for glucose.',
  },
  token_lookup: {
    label: 'Token Lookup',
    npmScript: 'aetherdesk:token',
    category: 'Tools',
    icon: 'token',
    risk_tier: 'read-only',
    description: 'Atomic-style token lookup rows for build, H2O, and verify.',
  },
  instrument_play: {
    label: 'Instrument',
    npmScript: 'aetherdesk:instrument',
    category: 'Tools',
    icon: 'music',
    risk_tier: 'read-only',
    description: 'Play a short code-song through the Instrument and verify its Python face.',
  },
  forge_demo: {
    label: 'Forge Demo',
    npmScript: 'aetherdesk:forge',
    category: 'Build',
    icon: 'forge',
    risk_tier: 'sandbox-write',
    description: 'Run the Helm tool-forge demo in a temp workspace and emit its receipt.',
  },
  rosetta_demo: {
    label: 'Rosetta',
    npmScript: 'aetherdesk:rosetta',
    category: 'Tools',
    icon: 'faces',
    risk_tier: 'read-only',
    description: 'Show one code-song across proven-equal language faces.',
  },
  host_check: {
    label: 'Host Capability',
    npmScript: 'aetherdesk:hostcheck',
    category: 'System',
    icon: 'check',
    risk_tier: 'read-only',
    description: 'Boot check: certify what THIS box can run (toolchains, models, cross-face faces) before acting.',
  },
  coding_ladder: {
    label: 'Coding Ladder',
    npmScript: 'aetherdesk:curriculum',
    category: 'Measure',
    icon: 'chart',
    risk_tier: 'read-only',
    description: 'Graded coding ladder (elementary -> PhD+); answer-key climber validates it end to end.',
  },
  reasoning_ladder: {
    label: 'Reasoning Ladder',
    npmScript: 'aetherdesk:reasoning',
    category: 'Measure',
    icon: 'chart',
    risk_tier: 'read-only',
    description: 'Graded auto-gradable reasoning ladder (exact-match); answer-key climber validates the grader.',
  },
  stepwise: {
    label: 'Stepwise',
    npmScript: 'aetherdesk:stepwise',
    category: 'Tools',
    icon: 'forge',
    risk_tier: 'read-only',
    description: 'Guided step machine: calc in code, a misstep rewinds to before the bad step and retries.',
  },
  failure_map: {
    label: 'Failure Map',
    npmScript: 'aetherdesk:failuremap',
    category: 'Measure',
    icon: 'chart',
    risk_tier: 'read-only',
    description: 'Localize where a model drifts and map it across models (drift point, wall, universal-fail).',
  },
  pazaak_board: {
    label: 'Pazaak Board',
    npmScript: 'aetherdesk:pazaak',
    category: 'Tools',
    icon: 'agent',
    risk_tier: 'read-only',
    description: 'Score task lanes (value/risk/verified) and recommend the next card move.',
  },
  mahss_game_gym: {
    label: 'MAHSS Game Gym',
    npmScript: 'aetherdesk:mahss-game-gym',
    category: 'Research',
    icon: 'game',
    risk_tier: 'read-only',
    description: 'Pacman/Tetris-style closed-loop gym for routing free/local LLMs through tool stations.',
  },
});

// Shell profiles are real host commands, but still bounded. The UI can request
// only these IDs; it cannot pass arbitrary PowerShell or command text.
const SHELL_ALLOWLIST = Object.freeze({
  pwd: {
    label: 'Working Directory',
    shell: 'powershell',
    args: ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', 'Get-Location | Select-Object -ExpandProperty Path'],
    risk_tier: 'read-only',
    description: 'Show the AetherDesk server working directory.',
  },
  git_status: {
    label: 'Git Status',
    shell: 'git',
    args: ['status', '--short', '--branch'],
    risk_tier: 'read-only',
    description: 'Show the current repo branch and pending local changes.',
  },
  powershell_probe: {
    label: 'PowerShell Probe',
    shell: 'powershell',
    args: [
      '-NoProfile',
      '-ExecutionPolicy',
      'Bypass',
      '-Command',
      '$PSVersionTable.PSVersion.ToString(); Get-Command powershell | Select-Object -ExpandProperty Source',
    ],
    risk_tier: 'read-only',
    description: 'Verify that the PowerShell lane is callable.',
  },
  agent_shell_probe: {
    label: 'Agent Shell Probe',
    shell: 'python',
    args: ['scripts/system/agent_shell.py', 'probe', '--model', 'qwen2.5-coder:3b'],
    risk_tier: 'read-only',
    description: 'List supervised Ollama launch integrations and the Agent Shell receipt root.',
  },
  agent_shell_codex_brief: {
    label: 'Agent Shell Codex Brief',
    shell: 'python',
    args: [
      'scripts/system/agent_shell.py',
      'run',
      'codex',
      '--model',
      'qwen2.5-coder:3b',
      '--timeout',
      '30',
      '--readonly-worktree',
      '--task',
      'AetherDesk bounded handoff: inspect context only, propose one safe next improvement, do not edit files.',
    ],
    risk_tier: 'read-only-agent',
    description: 'Launch Codex through the supervised Agent Shell with a no-edit proposal task.',
  },
});

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function utcStamp() {
  return new Date().toISOString().replace(/[-:]/g, '').replace(/\..*/, 'Z');
}

function sha256(buf) {
  return crypto.createHash('sha256').update(buf).digest('hex');
}

function tailBytes(str, max) {
  if (str.length <= max) return str;
  return '...[truncated]...\n' + str.slice(str.length - max);
}

function buildReceipt({
  commandId,
  exitCode,
  stdoutTail,
  stderrTail,
  startedAt,
  finishedAt,
  artifactPath,
}) {
  const entry = COMMAND_ALLOWLIST[commandId];
  const result = exitCode === 0 ? 'pass' : 'fail';
  const commandStr = `npm run ${entry.npmScript}`;
  return {
    schema: 'aetherdesk_receipt_v0',
    task_id: `${utcStamp()}_${commandId}`,
    command_id: commandId,
    command_label: entry.label,
    command: commandStr,
    command_digest: sha256(Buffer.from(commandStr, 'utf8')),
    risk_tier: entry.risk_tier,
    allowed_paths: ['<repo-readonly>'],
    started_at: startedAt,
    finished_at: finishedAt,
    duration_ms: new Date(finishedAt).getTime() - new Date(startedAt).getTime(),
    exit_code: exitCode,
    result,
    stdout_tail: stdoutTail,
    stderr_tail: stderrTail,
    artifact_path: artifactPath,
  };
}

function receiptFilename(receipt) {
  return `${receipt.task_id}.json`;
}

function writeReceipt(receipt) {
  ensureDir(RECEIPTS_DIR);
  const filePath = path.join(RECEIPTS_DIR, receiptFilename(receipt));
  fs.writeFileSync(filePath, JSON.stringify(receipt, null, 2) + '\n');
  return filePath;
}

function listReceipts(limit = 50) {
  if (!fs.existsSync(RECEIPTS_DIR)) return [];
  const files = fs
    .readdirSync(RECEIPTS_DIR)
    .filter((f) => f.endsWith('.json'))
    .sort()
    .reverse()
    .slice(0, limit);
  return files.map((f) => {
    const full = path.join(RECEIPTS_DIR, f);
    try {
      const r = JSON.parse(fs.readFileSync(full, 'utf8'));
      return {
        task_id: r.task_id,
        command_id: r.command_id,
        command_label: r.command_label,
        result: r.result,
        exit_code: r.exit_code,
        started_at: r.started_at,
        duration_ms: r.duration_ms,
        file: f,
      };
    } catch (_err) {
      return { task_id: f, command_id: 'unknown', result: 'unreadable', file: f };
    }
  });
}

function readReceipt(file) {
  // Strict: only allow simple filenames — no path separators, no traversal.
  if (!/^[A-Za-z0-9_.-]+\.json$/.test(file)) return null;
  const full = path.join(RECEIPTS_DIR, file);
  if (!fs.existsSync(full)) return null;
  return JSON.parse(fs.readFileSync(full, 'utf8'));
}

function runCommand(commandId) {
  return new Promise((resolve) => {
    const entry = COMMAND_ALLOWLIST[commandId];
    if (!entry) {
      return resolve({ ok: false, error: 'command not allowlisted' });
    }
    const startedAt = new Date().toISOString();
    const stdoutChunks = [];
    const stderrChunks = [];
    const child = spawn('npm', ['run', entry.npmScript], {
      cwd: REPO_ROOT,
      env: process.env,
      shell: process.platform === 'win32',
    });
    const timer = setTimeout(() => {
      try {
        child.kill('SIGTERM');
      } catch (_err) {
        /* swallow */
      }
    }, COMMAND_TIMEOUT_MS);
    child.stdout.on('data', (d) => stdoutChunks.push(d.toString('utf8')));
    child.stderr.on('data', (d) => stderrChunks.push(d.toString('utf8')));
    child.on('close', (code) => {
      clearTimeout(timer);
      const finishedAt = new Date().toISOString();
      const stdout = stdoutChunks.join('');
      const stderr = stderrChunks.join('');
      const receipt = buildReceipt({
        commandId,
        exitCode: code,
        stdoutTail: tailBytes(stdout, MAX_OUTPUT_TAIL_BYTES),
        stderrTail: tailBytes(stderr, MAX_OUTPUT_TAIL_BYTES),
        startedAt,
        finishedAt,
        artifactPath: null,
      });
      const filePath = writeReceipt(receipt);
      receipt.artifact_path = path.relative(REPO_ROOT, filePath).replace(/\\/g, '/');
      resolve({ ok: true, receipt });
    });
    child.on('error', (err) => {
      clearTimeout(timer);
      const finishedAt = new Date().toISOString();
      const receipt = buildReceipt({
        commandId,
        exitCode: -1,
        stdoutTail: '',
        stderrTail: `[spawn error] ${String(err && err.message ? err.message : err)}`,
        startedAt,
        finishedAt,
        artifactPath: null,
      });
      const filePath = writeReceipt(receipt);
      receipt.artifact_path = path.relative(REPO_ROOT, filePath).replace(/\\/g, '/');
      resolve({ ok: true, receipt });
    });
  });
}

function buildShellReceipt({
  profileId,
  exitCode,
  stdoutTail,
  stderrTail,
  startedAt,
  finishedAt,
  artifactPath,
}) {
  const entry = SHELL_ALLOWLIST[profileId];
  const commandStr = [entry.shell, ...entry.args].join(' ');
  const result = exitCode === 0 ? 'pass' : 'fail';
  return {
    schema: 'aetherdesk_receipt_v0',
    task_id: `${utcStamp()}_shell_${profileId}`,
    command_id: `shell:${profileId}`,
    command_label: `Shell: ${entry.label}`,
    command: commandStr,
    command_digest: sha256(Buffer.from(commandStr, 'utf8')),
    risk_tier: entry.risk_tier,
    allowed_paths: ['<repo-readonly>'],
    started_at: startedAt,
    finished_at: finishedAt,
    duration_ms: new Date(finishedAt).getTime() - new Date(startedAt).getTime(),
    exit_code: exitCode,
    result,
    stdout_tail: stdoutTail,
    stderr_tail: stderrTail,
    artifact_path: artifactPath,
  };
}

function runShellProfile(profileId) {
  return new Promise((resolve) => {
    const entry = SHELL_ALLOWLIST[profileId];
    if (!entry) {
      return resolve({ ok: false, error: 'shell profile not allowlisted' });
    }
    const startedAt = new Date().toISOString();
    const stdoutChunks = [];
    const stderrChunks = [];
    const child = spawn(entry.shell, entry.args, {
      cwd: REPO_ROOT,
      env: process.env,
      shell: false,
    });
    const timer = setTimeout(() => {
      try {
        child.kill('SIGTERM');
      } catch (_err) {
        /* swallow */
      }
    }, SHELL_TIMEOUT_MS);
    child.stdout.on('data', (d) => stdoutChunks.push(d.toString('utf8')));
    child.stderr.on('data', (d) => stderrChunks.push(d.toString('utf8')));
    child.on('close', (code) => {
      clearTimeout(timer);
      const finishedAt = new Date().toISOString();
      const receipt = buildShellReceipt({
        profileId,
        exitCode: code,
        stdoutTail: tailBytes(stdoutChunks.join(''), MAX_OUTPUT_TAIL_BYTES),
        stderrTail: tailBytes(stderrChunks.join(''), MAX_OUTPUT_TAIL_BYTES),
        startedAt,
        finishedAt,
        artifactPath: null,
      });
      const filePath = writeReceipt(receipt);
      receipt.artifact_path = path.relative(REPO_ROOT, filePath).replace(/\\/g, '/');
      resolve({ ok: true, receipt });
    });
    child.on('error', (err) => {
      clearTimeout(timer);
      const finishedAt = new Date().toISOString();
      const receipt = buildShellReceipt({
        profileId,
        exitCode: -1,
        stdoutTail: '',
        stderrTail: `[spawn error] ${String(err && err.message ? err.message : err)}`,
        startedAt,
        finishedAt,
        artifactPath: null,
      });
      const filePath = writeReceipt(receipt);
      receipt.artifact_path = path.relative(REPO_ROOT, filePath).replace(/\\/g, '/');
      resolve({ ok: true, receipt });
    });
  });
}

function validatePowerShellCommand(command) {
  const text = String(command || '').trim();
  if (!text) return { ok: false, error: 'empty PowerShell command' };
  if (text.length > MAX_TERMINAL_COMMAND_CHARS) {
    return { ok: false, error: `PowerShell command too long (${text.length} chars)` };
  }
  for (const pattern of BLOCKED_POWERSHELL_PATTERNS) {
    if (pattern.test(text)) {
      return { ok: false, error: `PowerShell command blocked by safety pattern: ${pattern}` };
    }
  }
  return { ok: true, command: text };
}

function buildPowerShellReceipt({
  command,
  exitCode,
  stdoutTail,
  stderrTail,
  startedAt,
  finishedAt,
  artifactPath,
  blocked,
  geosealPayload,
  riskTier,
  commandLabel,
}) {
  const commandStr = `powershell -NoProfile -ExecutionPolicy Bypass -Command ${command}`;
  const result = exitCode === 0 ? 'pass' : 'fail';
  return {
    schema: 'aetherdesk_receipt_v0',
    task_id: `${utcStamp()}_powershell`,
    command_id: 'powershell:command',
    command_label: commandLabel || (blocked ? 'PowerShell blocked' : 'PowerShell command'),
    command: commandStr,
    command_digest: sha256(Buffer.from(commandStr, 'utf8')),
    risk_tier: riskTier || (blocked ? 'blocked' : 'bounded-host-read'),
    allowed_paths: [REPO_ROOT],
    started_at: startedAt,
    finished_at: finishedAt,
    duration_ms: new Date(finishedAt).getTime() - new Date(startedAt).getTime(),
    exit_code: exitCode,
    result,
    stdout_tail: stdoutTail,
    stderr_tail: stderrTail,
    artifact_path: artifactPath,
    executor: blocked ? 'aetherdesk:preflight' : 'geoseal:powershell',
    upstream_schema: geosealPayload && geosealPayload.schema_version ? geosealPayload.schema_version : null,
    upstream_command_id: geosealPayload && geosealPayload.command_id ? geosealPayload.command_id : null,
    upstream_receipt_path: geosealPayload && geosealPayload.receipt_path ? geosealPayload.receipt_path : null,
    upstream_decision: geosealPayload && geosealPayload.decision ? geosealPayload.decision : null,
    upstream_safety: geosealPayload && geosealPayload.safety ? geosealPayload.safety : null,
  };
}

function runPowerShellCommand(command) {
  return new Promise((resolve) => {
    const startedAt = new Date().toISOString();
    const validation = validatePowerShellCommand(command);
    if (!validation.ok) {
      const finishedAt = new Date().toISOString();
      const receipt = buildPowerShellReceipt({
        command: String(command || ''),
        exitCode: 126,
        stdoutTail: '',
        stderrTail: validation.error,
        startedAt,
        finishedAt,
        artifactPath: null,
        blocked: true,
        geosealPayload: null,
        riskTier: 'blocked',
        commandLabel: 'PowerShell blocked',
      });
      const filePath = writeReceipt(receipt);
      receipt.artifact_path = path.relative(REPO_ROOT, filePath).replace(/\\/g, '/');
      return resolve({ ok: false, error: validation.error, receipt });
    }

    const stdoutChunks = [];
    const stderrChunks = [];
    const child = spawn(
      process.execPath,
      [
        'bin/geoseal.cjs',
        'powershell',
        'run',
        '--command',
        validation.command,
        '--write-receipt',
        '--json',
        '--timeout',
        String(POWERSHELL_TIMEOUT_MS),
      ],
      {
        cwd: REPO_ROOT,
        env: process.env,
        shell: false,
      }
    );
    const timer = setTimeout(() => {
      try {
        child.kill('SIGTERM');
      } catch (_err) {
        /* swallow */
      }
    }, POWERSHELL_TIMEOUT_MS);
    child.stdout.on('data', (d) => stdoutChunks.push(d.toString('utf8')));
    child.stderr.on('data', (d) => stderrChunks.push(d.toString('utf8')));
    child.on('close', (code) => {
      clearTimeout(timer);
      const finishedAt = new Date().toISOString();
      const stdout = stdoutChunks.join('');
      const stderr = stderrChunks.join('');
      let geosealPayload = null;
      let exitCode = code;
      let stdoutTail = tailBytes(stdout, MAX_OUTPUT_TAIL_BYTES);
      let stderrTail = tailBytes(stderr, MAX_OUTPUT_TAIL_BYTES);
      try {
        geosealPayload = parseJsonFromStdout(stdout);
        exitCode = Number.isInteger(geosealPayload.exit_code) ? geosealPayload.exit_code : code;
        stdoutTail = geosealPayload.stdout_tail || '';
        stderrTail = geosealPayload.stderr_tail || geosealPayload.error || '';
      } catch (err) {
        stderrTail = tailBytes(
          `${stderrTail}\n[geoseal parse error] ${String(err && err.message ? err.message : err)}`.trim(),
          MAX_OUTPUT_TAIL_BYTES
        );
      }
      const receipt = buildPowerShellReceipt({
        command: validation.command,
        exitCode,
        stdoutTail,
        stderrTail,
        startedAt,
        finishedAt,
        artifactPath: null,
        blocked: false,
        geosealPayload,
        riskTier: geosealPayload && geosealPayload.risk_tier ? geosealPayload.risk_tier : 'bounded-host-read',
        commandLabel: geosealPayload && geosealPayload.risk_tier === 'blocked'
          ? 'PowerShell blocked by GeoSeal'
          : 'PowerShell command',
      });
      const filePath = writeReceipt(receipt);
      receipt.artifact_path = path.relative(REPO_ROOT, filePath).replace(/\\/g, '/');
      const blockedByGeoSeal = geosealPayload && geosealPayload.risk_tier === 'blocked';
      resolve({
        ok: !blockedByGeoSeal && exitCode !== 127,
        error: blockedByGeoSeal ? stderrTail || 'PowerShell command blocked by GeoSeal' : undefined,
        receipt,
      });
    });
    child.on('error', (err) => {
      clearTimeout(timer);
      const finishedAt = new Date().toISOString();
      const receipt = buildPowerShellReceipt({
        command: validation.command,
        exitCode: -1,
        stdoutTail: '',
        stderrTail: `[spawn error] ${String(err && err.message ? err.message : err)}`,
        startedAt,
        finishedAt,
        artifactPath: null,
        blocked: false,
        geosealPayload: null,
        riskTier: 'bounded-host-read',
        commandLabel: 'PowerShell command',
      });
      const filePath = writeReceipt(receipt);
      receipt.artifact_path = path.relative(REPO_ROOT, filePath).replace(/\\/g, '/');
      resolve({ ok: false, error: receipt.stderr_tail, receipt });
    });
  });
}

function parseJsonFromStdout(stdout) {
  const text = String(stdout || '').replace(/^\uFEFF/, '');
  const start = text.indexOf('{');
  const end = text.lastIndexOf('}');
  if (start < 0 || end < start) throw new Error('run-control emitted no JSON object');
  return JSON.parse(text.slice(start, end + 1));
}

function runControlCommand(args, timeoutMs = RUN_CONTROL_TIMEOUT_MS) {
  return new Promise((resolve) => {
    const startedAt = new Date().toISOString();
    const stdoutChunks = [];
    const stderrChunks = [];
    const child = spawn('node', ['scripts/system/aetherdesk_run_control.mjs', ...args], {
      cwd: REPO_ROOT,
      env: process.env,
      shell: false,
    });
    const timer = setTimeout(() => {
      try {
        child.kill('SIGTERM');
      } catch (_err) {
        /* swallow */
      }
    }, timeoutMs);
    child.stdout.on('data', (d) => stdoutChunks.push(d.toString('utf8')));
    child.stderr.on('data', (d) => stderrChunks.push(d.toString('utf8')));
    child.on('close', (code) => {
      clearTimeout(timer);
      const stdout = stdoutChunks.join('');
      const stderr = stderrChunks.join('');
      try {
        const payload = parseJsonFromStdout(stdout);
        resolve({
          ok: code === 0 && payload.ok !== false,
          exit_code: code,
          started_at: startedAt,
          finished_at: new Date().toISOString(),
          payload,
          stderr_tail: tailBytes(stderr, MAX_OUTPUT_TAIL_BYTES),
        });
      } catch (err) {
        resolve({
          ok: false,
          exit_code: code,
          started_at: startedAt,
          finished_at: new Date().toISOString(),
          error: String(err && err.message ? err.message : err),
          stdout_tail: tailBytes(stdout, MAX_OUTPUT_TAIL_BYTES),
          stderr_tail: tailBytes(stderr, MAX_OUTPUT_TAIL_BYTES),
        });
      }
    });
    child.on('error', (err) => {
      clearTimeout(timer);
      resolve({
        ok: false,
        exit_code: -1,
        started_at: startedAt,
        finished_at: new Date().toISOString(),
        error: `[spawn error] ${String(err && err.message ? err.message : err)}`,
      });
    });
  });
}

// Provider status checks — read-only. Never expose secret values, only
// their presence as booleans. HTTP probes use a hard 1.5s timeout so a
// single slow provider can't block the whole panel.
function normalizeGardenToken(raw, label, fallback = '') {
  const value = String(raw || fallback).trim();
  if (!/^[A-Za-z0-9_.-]{1,80}$/.test(value)) {
    throw new Error(`invalid ${label}`);
  }
  return value;
}

function normalizeGardenMode(raw) {
  const mode = String(raw || 'work').trim();
  if (!['observe', 'work', 'review'].includes(mode)) {
    throw new Error('invalid garden mode');
  }
  return mode;
}

function normalizeGardenTask(raw) {
  return String(raw || '').replace(/\s+/g, ' ').trim().slice(0, 240);
}

function normalizeGardenTtlHours(raw) {
  const value = Number(raw || 12);
  if (!Number.isFinite(value)) return 12;
  return Math.max(0.25, Math.min(72, value));
}

function runWorktreeGardenCommand(args, timeoutMs = WORKTREE_GARDEN_TIMEOUT_MS) {
  return new Promise((resolve) => {
    const startedAt = new Date().toISOString();
    const stdoutChunks = [];
    const stderrChunks = [];
    const child = spawn('python', ['scripts/system/worktree_garden.py', ...args], {
      cwd: REPO_ROOT,
      env: process.env,
      shell: false,
    });
    const timer = setTimeout(() => {
      try {
        child.kill('SIGTERM');
      } catch (_err) {
        /* swallow */
      }
    }, timeoutMs);
    child.stdout.on('data', (d) => stdoutChunks.push(d.toString('utf8')));
    child.stderr.on('data', (d) => stderrChunks.push(d.toString('utf8')));
    child.on('close', (code) => {
      clearTimeout(timer);
      const stdout = stdoutChunks.join('');
      const stderr = stderrChunks.join('');
      try {
        const payload = parseJsonFromStdout(stdout);
        resolve({
          ok: code === 0 && payload.ok !== false,
          schema: 'aetherdesk_worktree_garden_v0',
          exit_code: code,
          started_at: startedAt,
          finished_at: new Date().toISOString(),
          payload,
          stderr_tail: tailBytes(stderr, MAX_OUTPUT_TAIL_BYTES),
        });
      } catch (err) {
        resolve({
          ok: false,
          schema: 'aetherdesk_worktree_garden_v0',
          exit_code: code,
          started_at: startedAt,
          finished_at: new Date().toISOString(),
          error: String(err && err.message ? err.message : err),
          stdout_tail: tailBytes(stdout, MAX_OUTPUT_TAIL_BYTES),
          stderr_tail: tailBytes(stderr, MAX_OUTPUT_TAIL_BYTES),
        });
      }
    });
    child.on('error', (err) => {
      clearTimeout(timer);
      resolve({
        ok: false,
        schema: 'aetherdesk_worktree_garden_v0',
        exit_code: -1,
        started_at: startedAt,
        finished_at: new Date().toISOString(),
        error: `[spawn error] ${String(err && err.message ? err.message : err)}`,
      });
    });
  });
}

const PROVIDER_PROBE_TIMEOUT_MS = 1500;

const PROVIDER_DEFS = Object.freeze([
  { id: 'ollama', label: 'Ollama', kind: 'local-http', url: 'http://127.0.0.1:11434/api/tags' },
  {
    id: 'lmstudio',
    label: 'LM Studio',
    kind: 'local-http',
    url: 'http://127.0.0.1:1234/v1/models',
  },
  {
    id: 'huggingface',
    label: 'HuggingFace',
    kind: 'env-var',
    env: ['HF_TOKEN', 'HUGGING_FACE_HUB_TOKEN'],
  },
  { id: 'anthropic', label: 'Anthropic', kind: 'env-var', env: ['ANTHROPIC_API_KEY'] },
  { id: 'openai', label: 'OpenAI', kind: 'env-var', env: ['OPENAI_API_KEY'] },
  { id: 'xai', label: 'xAI (Grok)', kind: 'env-var', env: ['XAI_API_KEY', 'GROK_API_KEY'] },
  { id: 'groq', label: 'Groq', kind: 'env-var', env: ['GROQ_API_KEY'] },
]);

async function probeHttp(url, timeoutMs) {
  const t0 = Date.now();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const resp = await fetch(url, { signal: controller.signal });
    return {
      reachable: resp.ok,
      latency_ms: Date.now() - t0,
      error: resp.ok ? null : `HTTP ${resp.status}`,
    };
  } catch (err) {
    const msg = err && err.name === 'AbortError' ? 'timeout' : String((err && err.message) || err);
    return { reachable: false, latency_ms: Date.now() - t0, error: msg };
  } finally {
    clearTimeout(timer);
  }
}

function probeEnv(envNames) {
  const found = envNames.find((n) => {
    const v = process.env[n];
    return typeof v === 'string' && v.length > 0;
  });
  return { has_secret: Boolean(found), secret_env_var: found || null };
}

function normalizePlaywrightUrl(raw) {
  const s = String(raw || '').trim();
  if (!s) return 'https://example.com';
  if (s === 'about:blank') return s;
  const withScheme = /^[a-z][a-z0-9+.-]*:/i.test(s) ? s : `https://${s}`;
  let parsed;
  try {
    parsed = new URL(withScheme);
  } catch (_err) {
    throw new Error('invalid URL');
  }
  if (!['http:', 'https:', 'about:'].includes(parsed.protocol)) {
    throw new Error('only http, https, and about URLs are allowed');
  }
  if (parsed.username || parsed.password) {
    throw new Error('URLs with embedded credentials are not allowed');
  }
  return parsed.toString();
}

function extractYouTubeVideoId(target) {
  const raw = String(target || '').trim();
  if (!raw) throw new Error('YouTube URL or video ID is required');
  if (YOUTUBE_VIDEO_ID_RE.test(raw)) return raw;

  let parsed;
  try {
    parsed = new URL(raw);
  } catch (_err) {
    throw new Error('invalid YouTube URL or video ID');
  }

  const host = parsed.hostname.toLowerCase();
  const pathParts = parsed.pathname.split('/').filter(Boolean);
  let candidate = '';
  if (host === 'youtu.be' || host === 'www.youtu.be') {
    candidate = pathParts[0] || '';
  } else if (['youtube.com', 'www.youtube.com', 'm.youtube.com'].includes(host)) {
    if (parsed.pathname === '/watch') {
      candidate = parsed.searchParams.get('v') || '';
    } else if (['shorts', 'live', 'embed'].includes(pathParts[0])) {
      candidate = pathParts[1] || '';
    }
  }

  if (YOUTUBE_VIDEO_ID_RE.test(candidate)) return candidate;
  throw new Error('could not extract a YouTube video ID');
}

function normalizeTranscriptLanguages(raw) {
  const list = Array.isArray(raw) ? raw : String(raw || 'en').split(',');
  const languages = list
    .map((v) => String(v || '').trim().toLowerCase())
    .filter(Boolean)
    .filter((v) => /^[a-z]{2,3}(-[a-z0-9]{2,8})?$/i.test(v))
    .slice(0, 6);
  return languages.length ? languages : ['en'];
}

function runYouTubeTranscript(target, languages) {
  return new Promise((resolve) => {
    let videoId;
    try {
      videoId = extractYouTubeVideoId(target);
    } catch (err) {
      return resolve({ ok: false, error: String(err && err.message ? err.message : err), status: 400 });
    }

    const startedAt = new Date().toISOString();
    const args = ['scripts/system/youtube_transcript_pull.py', videoId, '--json'];
    for (const lang of normalizeTranscriptLanguages(languages)) {
      args.push('--language', lang);
    }

    const stdoutChunks = [];
    const stderrChunks = [];
    const child = spawn('python', args, {
      cwd: REPO_ROOT,
      env: process.env,
      shell: false,
    });
    const timer = setTimeout(() => {
      try {
        child.kill('SIGTERM');
      } catch (_err) {
        /* swallow */
      }
    }, TRANSCRIPT_TIMEOUT_MS);

    child.stdout.on('data', (d) => stdoutChunks.push(d.toString('utf8')));
    child.stderr.on('data', (d) => stderrChunks.push(d.toString('utf8')));
    child.on('close', (code) => {
      clearTimeout(timer);
      const finishedAt = new Date().toISOString();
      const stdout = stdoutChunks.join('');
      const stderr = stderrChunks.join('');
      if (code !== 0) {
        return resolve({
          ok: false,
          schema: 'aetherdesk_youtube_transcript_v0',
          video_id: videoId,
          exit_code: code,
          error: tailBytes(stderr || stdout || 'transcript pull failed', MAX_OUTPUT_TAIL_BYTES),
          duration_ms: new Date(finishedAt).getTime() - new Date(startedAt).getTime(),
          status: 502,
        });
      }
      try {
        const payload = JSON.parse(stdout);
        return resolve({
          ok: true,
          schema: 'aetherdesk_youtube_transcript_v0',
          video_id: videoId,
          fetched_at: finishedAt,
          duration_ms: new Date(finishedAt).getTime() - new Date(startedAt).getTime(),
          ...payload,
          text: tailBytes(payload.text || '', 60000),
        });
      } catch (err) {
        return resolve({
          ok: false,
          schema: 'aetherdesk_youtube_transcript_v0',
          video_id: videoId,
          error: `transcript JSON parse failed: ${String(err && err.message ? err.message : err)}`,
          status: 502,
        });
      }
    });
    child.on('error', (err) => {
      clearTimeout(timer);
      resolve({
        ok: false,
        schema: 'aetherdesk_youtube_transcript_v0',
        video_id: videoId,
        error: `[spawn error] ${String(err && err.message ? err.message : err)}`,
        status: 502,
      });
    });
  });
}

function defaultPlaywrightExecutable() {
  if (process.env.AETHERDESK_PLAYWRIGHT_EXECUTABLE) return process.env.AETHERDESK_PLAYWRIGHT_EXECUTABLE;
  const edge = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
  if (process.platform === 'win32' && fs.existsSync(edge)) return edge;
  return null;
}

async function capturePlaywrightView(rawUrl) {
  const url = normalizePlaywrightUrl(rawUrl);
  const { chromium } = await import('playwright');
  const executablePath = defaultPlaywrightExecutable();
  const browser = await chromium.launch({
    headless: true,
    ...(executablePath ? { executablePath } : {}),
  });
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
    const startedAt = Date.now();
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: PLAYWRIGHT_TIMEOUT_MS });
    const title = await page.title().catch(() => '');
    const screenshot = await page.screenshot({ type: 'png', fullPage: false, timeout: PLAYWRIGHT_TIMEOUT_MS });
    return {
      ok: true,
      schema: 'aetherdesk_playwright_view_v0',
      url: page.url(),
      title,
      captured_at: new Date().toISOString(),
      duration_ms: Date.now() - startedAt,
      viewport: { width: 1280, height: 720 },
      screenshot_data_url: `data:image/png;base64,${screenshot.toString('base64')}`,
    };
  } finally {
    await browser.close();
  }
}

const browserSessions = new Map();

function normalizeBrowserAction(rawAction) {
  const action = String(rawAction || 'screenshot').trim().toLowerCase();
  if (!['goto', 'screenshot', 'text', 'aria', 'guide', 'click', 'type', 'close'].includes(action)) {
    throw new Error('unsupported browser action');
  }
  return action;
}

function normalizeSessionId(raw) {
  const s = String(raw || 'main').trim() || 'main';
  if (!/^[A-Za-z0-9_.-]{1,40}$/.test(s)) throw new Error('invalid browser session id');
  return s;
}

function normalizeSelector(raw) {
  const s = String(raw || '').trim();
  if (!s) throw new Error('selector is required');
  if (s.length > 220) throw new Error('selector too long');
  return s;
}

async function browserAriaSnapshot(page) {
  const body = page.locator('body');
  if (typeof body.ariaSnapshot === 'function') {
    return body.ariaSnapshot({ timeout: PLAYWRIGHT_TIMEOUT_MS }).catch(() => '');
  }
  return page
    .locator('body')
    .innerText({ timeout: PLAYWRIGHT_TIMEOUT_MS })
    .then((text) => `- document: ${tailBytes(text, MAX_OUTPUT_TAIL_BYTES)}`)
    .catch(() => '');
}

async function browserGuidedMoves(page) {
  return page.evaluate(() => {
    function cssEscapeLocal(value) {
      if (window.CSS && typeof window.CSS.escape === 'function') return window.CSS.escape(value);
      return String(value).replace(/[^A-Za-z0-9_-]/g, '\\$&');
    }
    function selectorFor(el) {
      if (el.id) return `#${cssEscapeLocal(el.id)}`;
      const name = el.getAttribute('name');
      if (name) return `${el.tagName.toLowerCase()}[name="${String(name).replace(/"/g, '\\"')}"]`;
      const aria = el.getAttribute('aria-label');
      if (aria) return `${el.tagName.toLowerCase()}[aria-label="${String(aria).replace(/"/g, '\\"')}"]`;
      const parent = el.parentElement;
      if (!parent) return el.tagName.toLowerCase();
      const siblings = Array.from(parent.children).filter((x) => x.tagName === el.tagName);
      const idx = siblings.indexOf(el) + 1;
      return `${el.tagName.toLowerCase()}:nth-of-type(${Math.max(1, idx)})`;
    }
    const nodes = Array.from(
      document.querySelectorAll('a,button,input,textarea,select,[role="button"],[role="link"],[contenteditable="true"]')
    );
    return nodes
      .filter((el) => {
        const style = window.getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        return style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0;
      })
      .slice(0, 60)
      .map((el, index) => {
        const text = (el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('title') || '').trim();
        const tag = el.tagName.toLowerCase();
        const role = el.getAttribute('role') || tag;
        const canType = ['input', 'textarea'].includes(tag) || el.getAttribute('contenteditable') === 'true';
        return {
          index,
          role,
          tag,
          label: text.slice(0, 120),
          selector: selectorFor(el),
          href: el.href || '',
          disabled: Boolean(el.disabled || el.getAttribute('aria-disabled') === 'true'),
          move: canType ? 'type' : 'click',
        };
      });
  });
}

async function getBrowserSession(sessionId) {
  const existing = browserSessions.get(sessionId);
  if (existing) return existing;
  const { chromium } = await import('playwright');
  const executablePath = defaultPlaywrightExecutable();
  const browser = await chromium.launch({
    headless: true,
    ...(executablePath ? { executablePath } : {}),
  });
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  const session = { browser, page, id: sessionId, created_at: new Date().toISOString() };
  browserSessions.set(sessionId, session);
  return session;
}

async function browserAction(payload = {}) {
  const action = normalizeBrowserAction(payload.action);
  const sessionId = normalizeSessionId(payload.session_id);
  if (action === 'close') {
    const existing = browserSessions.get(sessionId);
    if (existing) {
      await existing.browser.close();
      browserSessions.delete(sessionId);
    }
    return {
      ok: true,
      schema: 'aetherdesk_browser_action_v0',
      session_id: sessionId,
      action,
      closed: Boolean(existing),
    };
  }

  const session = await getBrowserSession(sessionId);
  const { page } = session;
  const startedAt = Date.now();

  if (action === 'goto') {
    const url = normalizePlaywrightUrl(payload.url);
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: PLAYWRIGHT_TIMEOUT_MS });
  } else if (action === 'click') {
    await page.click(normalizeSelector(payload.selector), { timeout: PLAYWRIGHT_TIMEOUT_MS });
  } else if (action === 'type') {
    await page.fill(normalizeSelector(payload.selector), String(payload.text || ''), {
      timeout: PLAYWRIGHT_TIMEOUT_MS,
    });
  }

  const title = await page.title().catch(() => '');
  const text = action === 'text' ? await page.locator('body').innerText({ timeout: PLAYWRIGHT_TIMEOUT_MS }).catch(() => '') : '';
  const aria = action === 'aria' ? await browserAriaSnapshot(page) : '';
  const guide = action === 'guide' ? await browserGuidedMoves(page) : null;
  const screenshot =
    action === 'screenshot' || action === 'goto' || action === 'click' || action === 'type'
      ? await page.screenshot({ type: 'png', fullPage: false, timeout: PLAYWRIGHT_TIMEOUT_MS })
      : null;
  return {
    ok: true,
    schema: 'aetherdesk_browser_action_v0',
    session_id: sessionId,
    action,
    url: page.url(),
    title,
    captured_at: new Date().toISOString(),
    duration_ms: Date.now() - startedAt,
    viewport: { width: 1280, height: 720 },
    text_tail: text ? tailBytes(text, MAX_OUTPUT_TAIL_BYTES) : '',
    aria_tail: aria ? tailBytes(aria, MAX_OUTPUT_TAIL_BYTES) : '',
    guide,
    screenshot_data_url: screenshot ? `data:image/png;base64,${screenshot.toString('base64')}` : null,
  };
}

async function checkAllProviders() {
  const results = await Promise.all(
    PROVIDER_DEFS.map(async (p) => {
      const base = { id: p.id, label: p.label, kind: p.kind };
      if (p.kind === 'local-http') {
        const r = await probeHttp(p.url, PROVIDER_PROBE_TIMEOUT_MS);
        return { ...base, url: p.url, ...r };
      }
      // env-var kind
      return { ...base, env_vars_checked: p.env, ...probeEnv(p.env) };
    })
  );
  return results;
}

function validateEmailDraft(payload = {}) {
  const to = String(payload.to || '').trim();
  const subject = String(payload.subject || '').trim();
  const body = String(payload.body || '').trim();
  if (!to) throw new Error('email draft requires a recipient');
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(to)) throw new Error('recipient must be an email address');
  if (!subject) throw new Error('email draft requires a subject');
  if (!body) throw new Error('email draft requires a body');
  if (to.length > 320 || subject.length > 300 || body.length > MAX_EMAIL_FIELD_CHARS) {
    throw new Error('email draft exceeds length limits');
  }
  return { to, subject, body };
}

function createEmailDraft(payload = {}) {
  const draft = validateEmailDraft(payload);
  ensureDir(EMAIL_DRAFTS_DIR);
  const savedAt = new Date().toISOString();
  const id = `${utcStamp()}_${sha256(Buffer.from(`${draft.to}\n${draft.subject}\n${draft.body}`, 'utf8')).slice(0, 12)}`;
  const record = {
    schema: 'aetherdesk_email_draft_v0',
    id,
    saved_at: savedAt,
    status: 'draft_only_not_sent',
    to: draft.to,
    subject: draft.subject,
    body: draft.body,
  };
  const filePath = path.join(EMAIL_DRAFTS_DIR, `${id}.json`);
  fs.writeFileSync(filePath, JSON.stringify(record, null, 2) + '\n', 'utf8');
  return {
    ok: true,
    ...record,
    artifact_path: path.relative(REPO_ROOT, filePath).replace(/\\/g, '/'),
  };
}

function normalizeNotebookId(raw) {
  const id = String(raw || 'default').trim() || 'default';
  if (!/^[A-Za-z0-9_.-]{1,64}$/.test(id)) throw new Error('invalid notebook id');
  return id;
}

function notebookPath(id) {
  return path.join(NOTEBOOKS_DIR, `${normalizeNotebookId(id)}.json`);
}

function saveNotebook(payload = {}) {
  const id = normalizeNotebookId(payload.id);
  const title = String(payload.title || id).trim().slice(0, 180) || id;
  const body = String(payload.body || '');
  if (body.length > MAX_NOTEBOOK_CHARS) throw new Error('notebook exceeds length limit');
  ensureDir(NOTEBOOKS_DIR);
  const savedAt = new Date().toISOString();
  const record = {
    schema: 'aetherdesk_notebook_v0',
    id,
    title,
    body,
    saved_at: savedAt,
  };
  const filePath = notebookPath(id);
  fs.writeFileSync(filePath, JSON.stringify(record, null, 2) + '\n', 'utf8');
  return {
    ok: true,
    ...record,
    artifact_path: path.relative(REPO_ROOT, filePath).replace(/\\/g, '/'),
  };
}

function loadNotebook(id) {
  const filePath = notebookPath(id);
  if (!fs.existsSync(filePath)) {
    return {
      ok: true,
      schema: 'aetherdesk_notebook_v0',
      id: normalizeNotebookId(id),
      title: normalizeNotebookId(id),
      body: '',
      saved_at: null,
      artifact_path: null,
    };
  }
  const record = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  return {
    ok: true,
    ...record,
    artifact_path: path.relative(REPO_ROOT, filePath).replace(/\\/g, '/'),
  };
}

function buildApp() {
  const app = express();
  app.use(express.json({ limit: '64kb' }));
  app.use(express.static(path.join(__dirname, 'public'), {
    etag: false,
    maxAge: 0,
    setHeaders(res) {
      res.setHeader('Cache-Control', 'no-store');
    }
  }));

  app.get('/api/health', (_req, res) => {
    res.json({ ok: true, schema: 'aetherdesk_health_v0', port: PORT, host: HOST });
  });

  app.get('/favicon.ico', (_req, res) => {
    res.status(204).end();
  });

  app.get('/api/providers', async (_req, res) => {
    const providers = await checkAllProviders();
    res.json({
      ok: true,
      schema: 'aetherdesk_providers_v0',
      generated_at: new Date().toISOString(),
      providers,
    });
  });

  app.get('/api/commands', (_req, res) => {
    const items = Object.entries(COMMAND_ALLOWLIST).map(([id, entry]) => ({
      id,
      label: entry.label,
      npm_script: entry.npmScript,
      category: entry.category || 'Commands',
      icon: entry.icon || 'terminal',
      risk_tier: entry.risk_tier,
      description: entry.description,
    }));
    res.json({ ok: true, schema: 'aetherdesk_commands_v0', commands: items });
  });

  app.post('/api/playwright/view', async (req, res) => {
    try {
      const result = await capturePlaywrightView(req.body && req.body.url);
      res.json(result);
    } catch (err) {
      res.status(400).json({
        ok: false,
        schema: 'aetherdesk_playwright_view_v0',
        error: String(err && err.message ? err.message : err),
      });
    }
  });

  app.get('/api/aetherdesk/runs/status', async (_req, res) => {
    const result = await runControlCommand(['status'], RUN_CONTROL_TIMEOUT_MS);
    res.status(result.ok ? 200 : 502).json({
      ok: result.ok,
      schema: 'aetherdesk_run_control_status_v0',
      ...result,
    });
  });

  app.get('/api/worktree-garden', async (_req, res) => {
    const result = await runWorktreeGardenCommand(['status', '--json']);
    res.status(result.ok ? 200 : 502).json({
      ok: result.ok,
      ...result,
    });
  });

  app.post('/api/worktree-garden/attach', async (req, res) => {
    try {
      const body = req.body || {};
      const result = await runWorktreeGardenCommand([
        'attach',
        '--agent',
        normalizeGardenToken(body.agent, 'agent', 'codex'),
        '--plot',
        normalizeGardenToken(body.plot, 'plot'),
        '--task',
        normalizeGardenTask(body.task),
        '--mode',
        normalizeGardenMode(body.mode),
        '--ttl-hours',
        String(normalizeGardenTtlHours(body.ttl_hours)),
        '--json',
      ]);
      res.status(result.ok ? 200 : 400).json({ ok: result.ok, ...result });
    } catch (err) {
      res.status(400).json({
        ok: false,
        schema: 'aetherdesk_worktree_garden_v0',
        error: String(err && err.message ? err.message : err),
      });
    }
  });

  app.post('/api/worktree-garden/release', async (req, res) => {
    try {
      const body = req.body || {};
      const args = ['release'];
      if (body.agent) args.push('--agent', normalizeGardenToken(body.agent, 'agent'));
      if (body.plot) args.push('--plot', normalizeGardenToken(body.plot, 'plot'));
      if (body.lease_id) args.push('--lease-id', normalizeGardenToken(body.lease_id, 'lease_id'));
      args.push('--json');
      const result = await runWorktreeGardenCommand(args);
      res.status(result.ok ? 200 : 400).json({ ok: result.ok, ...result });
    } catch (err) {
      res.status(400).json({
        ok: false,
        schema: 'aetherdesk_worktree_garden_v0',
        error: String(err && err.message ? err.message : err),
      });
    }
  });

  app.get('/api/aetherdesk/runs/inventory', async (_req, res) => {
    const result = await runControlCommand(['inventory', '--json'], RUN_CONTROL_TIMEOUT_MS);
    res.status(result.ok ? 200 : 502).json({
      ok: result.ok,
      schema: 'aetherdesk_run_control_inventory_v0',
      ...result,
    });
  });

  app.get('/api/aetherdesk/runs/queue', async (_req, res) => {
    const result = await runControlCommand(['queue-list', '--json'], RUN_CONTROL_TIMEOUT_MS);
    res.status(result.ok ? 200 : 502).json({
      ok: result.ok,
      schema: 'aetherdesk_run_control_queue_v0',
      ...result,
    });
  });

  app.post('/api/aetherdesk/runs/queue/colab-fast', async (req, res) => {
    const watchFor = String((req.body && req.body.watch_for) || 'SCBE_FAST_FULL_DONE');
    const timeoutMs = Math.max(15000, Math.min(24 * 60 * 60 * 1000, Number((req.body && req.body.timeout_ms) || 1800000)));
    const result = await runControlCommand(
      ['queue-add-colab-fast', '--watch-for', watchFor, '--timeout-ms', String(timeoutMs)],
      RUN_CONTROL_TIMEOUT_MS
    );
    res.status(result.ok ? 200 : 502).json({
      ok: result.ok,
      schema: 'aetherdesk_run_control_queue_add_v0',
      ...result,
    });
  });

  app.post('/api/aetherdesk/runs/queue/colab-rescue', async (req, res) => {
    const timeoutMs = Math.max(15000, Math.min(30 * 60 * 1000, Number((req.body && req.body.timeout_ms) || 600000)));
    const result = await runControlCommand(
      ['queue-add-colab-rescue', '--timeout-ms', String(timeoutMs)],
      RUN_CONTROL_TIMEOUT_MS
    );
    res.status(result.ok ? 200 : 502).json({
      ok: result.ok,
      schema: 'aetherdesk_run_control_queue_rescue_v0',
      ...result,
    });
  });

  app.post('/api/aetherdesk/runs/queue/monitor', async (req, res) => {
    const watchFor = String((req.body && req.body.watch_for) || 'SCBE_FAST_FULL_DONE');
    const match = String((req.body && req.body.match) || 'train_qlora');
    const timeoutMs = Math.max(15000, Math.min(24 * 60 * 60 * 1000, Number((req.body && req.body.timeout_ms) || 1800000)));
    const result = await runControlCommand(
      ['queue-add-monitor', '--watch-for', watchFor, '--match', match, '--timeout-ms', String(timeoutMs)],
      RUN_CONTROL_TIMEOUT_MS
    );
    res.status(result.ok ? 200 : 502).json({
      ok: result.ok,
      schema: 'aetherdesk_run_control_queue_add_v0',
      ...result,
    });
  });

  app.post('/api/aetherdesk/runs/run-next', async (_req, res) => {
    const result = await runControlCommand(['run-next'], 24 * 60 * 60 * 1000);
    res.status(result.ok ? 200 : 502).json({
      ok: result.ok,
      schema: 'aetherdesk_run_control_run_next_v0',
      ...result,
    });
  });

  app.post('/api/browser/action', async (req, res) => {
    try {
      const result = await browserAction(req.body || {});
      res.json(result);
    } catch (err) {
      res.status(400).json({
        ok: false,
        schema: 'aetherdesk_browser_action_v0',
        error: String(err && err.message ? err.message : err),
      });
    }
  });

  app.post('/api/youtube/transcript', async (req, res) => {
    const result = await runYouTubeTranscript(req.body && req.body.target, req.body && req.body.languages);
    res.status(result.ok ? 200 : result.status || 400).json(result);
  });

  app.post('/api/email/draft', (req, res) => {
    try {
      res.json(createEmailDraft(req.body || {}));
    } catch (err) {
      res.status(400).json({
        ok: false,
        schema: 'aetherdesk_email_draft_v0',
        error: String(err && err.message ? err.message : err),
      });
    }
  });

  app.get('/api/notebook/:id', (req, res) => {
    try {
      res.json(loadNotebook(req.params.id));
    } catch (err) {
      res.status(400).json({
        ok: false,
        schema: 'aetherdesk_notebook_v0',
        error: String(err && err.message ? err.message : err),
      });
    }
  });

  app.post('/api/notebook/:id', (req, res) => {
    try {
      res.json(saveNotebook({ ...(req.body || {}), id: req.params.id }));
    } catch (err) {
      res.status(400).json({
        ok: false,
        schema: 'aetherdesk_notebook_v0',
        error: String(err && err.message ? err.message : err),
      });
    }
  });

  app.get('/api/shell/profiles', (_req, res) => {
    const profiles = Object.entries(SHELL_ALLOWLIST).map(([id, entry]) => ({
      id,
      label: entry.label,
      shell: entry.shell,
      risk_tier: entry.risk_tier,
      description: entry.description,
    }));
    res.json({ ok: true, schema: 'aetherdesk_shell_profiles_v0', profiles });
  });

  app.get('/api/receipts', (req, res) => {
    const limit = Math.max(1, Math.min(200, Number(req.query.limit || 50)));
    res.json({ ok: true, schema: 'aetherdesk_receipt_list_v0', receipts: listReceipts(limit) });
  });

  app.get('/api/receipts/:file', (req, res) => {
    const r = readReceipt(req.params.file);
    if (!r) return res.status(404).json({ ok: false, error: 'receipt not found' });
    res.json({ ok: true, receipt: r });
  });

  app.post('/api/run/:command_id', async (req, res) => {
    const id = String(req.params.command_id || '');
    if (!Object.prototype.hasOwnProperty.call(COMMAND_ALLOWLIST, id)) {
      return res.status(400).json({ ok: false, error: 'command not allowlisted', command_id: id });
    }
    const result = await runCommand(id);
    if (!result.ok) return res.status(500).json(result);
    res.json(result);
  });

  app.post('/api/shell/run', async (req, res) => {
    const id = String((req.body && req.body.id) || '');
    if (!Object.prototype.hasOwnProperty.call(SHELL_ALLOWLIST, id)) {
      return res.status(400).json({ ok: false, error: 'shell profile not allowlisted', profile_id: id });
    }
    const result = await runShellProfile(id);
    if (!result.ok) return res.status(500).json(result);
    res.json(result);
  });

  app.post('/api/powershell/run', async (req, res) => {
    const result = await runPowerShellCommand(req.body && req.body.command);
    res.status(result.ok ? 200 : 400).json(result);
  });

  return app;
}

function main() {
  const app = buildApp();
  const server = app.listen(PORT, HOST, () => {
    // eslint-disable-next-line no-console
    console.log(`AetherDesk Operator Shell v0 — http://${HOST}:${PORT}`);
    // eslint-disable-next-line no-console
    console.log(`Receipts: ${path.relative(REPO_ROOT, RECEIPTS_DIR)}`);
  });
  return server;
}

if (require.main === module) {
  main();
}

module.exports = {
  buildApp,
  COMMAND_ALLOWLIST,
  SHELL_ALLOWLIST,
  PROVIDER_DEFS,
  buildReceipt,
  listReceipts,
  readReceipt,
  writeReceipt,
  checkAllProviders,
  probeEnv,
  normalizePlaywrightUrl,
  extractYouTubeVideoId,
  normalizeTranscriptLanguages,
  normalizeBrowserAction,
  normalizeSessionId,
  normalizeSelector,
  capturePlaywrightView,
  browserAction,
  validateEmailDraft,
  createEmailDraft,
  normalizeNotebookId,
  saveNotebook,
  loadNotebook,
  normalizeGardenToken,
  normalizeGardenMode,
  normalizeGardenTask,
  normalizeGardenTtlHours,
  validatePowerShellCommand,
  RECEIPTS_DIR,
  EMAIL_DRAFTS_DIR,
  NOTEBOOKS_DIR,
  HOST,
  PORT,
  _private: {
    tailBytes,
    sha256,
    runCommand,
    runShellProfile,
    runPowerShellCommand,
    runWorktreeGardenCommand,
    runYouTubeTranscript,
    probeHttp,
    defaultPlaywrightExecutable,
    browserAriaSnapshot,
    browserGuidedMoves,
  },
};
