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
const PORT = Number(process.env.AETHERDESK_PORT || 5717);
const HOST = '127.0.0.1';
const MAX_OUTPUT_TAIL_BYTES = 8192;
const COMMAND_TIMEOUT_MS = 10 * 60 * 1000;

// The allowlist is the security boundary. Every entry is a {npm, script}
// reference resolved against package.json scripts. Frontend cannot pass a
// raw shell string; it can only ask to run one of these IDs.
const COMMAND_ALLOWLIST = Object.freeze({
  typecheck: {
    label: 'Typecheck (TypeScript)',
    npmScript: 'typecheck',
    risk_tier: 'read-only',
    description: 'tsc --noEmit — no files are written.',
  },
  ts_tests: {
    label: 'TS tests (vitest)',
    npmScript: 'test',
    risk_tier: 'read-only',
    description: 'Run the full Vitest suite.',
  },
  benchmark_cli: {
    label: 'CLI benchmark',
    npmScript: 'benchmark:cli',
    risk_tier: 'read-only',
    description: 'Run scripts/benchmark/cli_competitive_benchmark.py.',
  },
  research_aether_lattice: {
    label: 'Aether-Lattice sim',
    npmScript: 'research:aether-lattice',
    risk_tier: 'read-only',
    description: 'Run the Aether-Lattice containment simulator (deterministic seed=42).',
  },
  benchmark_coding_agents: {
    label: 'Coding-agent benchmark',
    npmScript: 'benchmark:coding-agents',
    risk_tier: 'read-only',
    description:
      'Run scripts/eval/functional_coding_agent_benchmark.py. Note: TS scenario runner is missing per spec; see AETHERDESK_OPERATOR_SHELL_v0.md.',
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

// Provider status checks — read-only. Never expose secret values, only
// their presence as booleans. HTTP probes use a hard 1.5s timeout so a
// single slow provider can't block the whole panel.
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

function buildApp() {
  const app = express();
  app.use(express.json({ limit: '64kb' }));
  app.use(express.static(path.join(__dirname, 'public')));

  app.get('/api/health', (_req, res) => {
    res.json({ ok: true, schema: 'aetherdesk_health_v0', port: PORT, host: HOST });
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
      risk_tier: entry.risk_tier,
      description: entry.description,
    }));
    res.json({ ok: true, schema: 'aetherdesk_commands_v0', commands: items });
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
  PROVIDER_DEFS,
  buildReceipt,
  listReceipts,
  readReceipt,
  writeReceipt,
  checkAllProviders,
  probeEnv,
  RECEIPTS_DIR,
  HOST,
  PORT,
  _private: { tailBytes, sha256, runCommand, probeHttp },
};
