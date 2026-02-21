import express from 'express';
import { spawn } from 'child_process';
import fs from 'fs/promises';
import os from 'os';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const publicDir = path.join(__dirname, 'public');

const MAX_FILE_BYTES = 512 * 1024;
const MAX_TOTAL_BYTES = 2 * 1024 * 1024;
const MAX_OUTPUT_BYTES = 300 * 1024;
const DOCKER_IMAGE = process.env.KERNEL_RUNNER_IMAGE || 'node:20-bookworm';
const PORT = Number(process.env.KERNEL_RUNNER_PORT || 4242);

const SECRET_PATTERNS = [
  /\bghp_[A-Za-z0-9]{20,}\b/gi,
  /\bhf_[A-Za-z0-9]{20,}\b/gi,
  /\bsk-[A-Za-z0-9]{16,}\b/gi,
  /\bAKIA[0-9A-Z]{16}\b/gi,
  /BEGIN\s+PRIVATE\s+KEY/gi,
];

const MALICIOUS_PATTERNS = [
  /(curl|wget).{0,32}\|\s*(bash|sh)/gi,
  /\brm\s+-rf\s+\/\b/gi,
  /\bpowershell\s+-enc(odedcommand)?\b/gi,
  /\bcredential\s+stuffing\b/gi,
  /\bkeylogger\b/gi,
  /\bexfiltrat(e|ion)\b/gi,
];

const HIGH_RISK_SCRIPT_PATTERNS = [
  /\bpostinstall\b/gi,
  /\bpreinstall\b/gi,
  /\bnpm\s+publish\b/gi,
  /\bdocker\s+run\b/gi,
];

function nowIso() {
  return new Date().toISOString();
}

function clamp01(value) {
  return Math.max(0, Math.min(1, value));
}

function clipText(value, maxBytes = MAX_OUTPUT_BYTES) {
  const text = String(value ?? '');
  const buf = Buffer.from(text, 'utf8');
  if (buf.length <= maxBytes) return text;
  return buf.subarray(0, maxBytes).toString('utf8') + '\n...[truncated]';
}

function asObject(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {};
  return value;
}

function normalizeFiles(input) {
  const filesIn = asObject(input);
  const filesOut = {};
  let totalBytes = 0;
  for (const [rawName, rawContent] of Object.entries(filesIn)) {
    const name = String(rawName || '').replace(/\\/g, '/').trim();
    if (!name || name.startsWith('/') || name.includes('..')) continue;
    const content = String(rawContent ?? '');
    const bytes = Buffer.byteLength(content, 'utf8');
    if (bytes > MAX_FILE_BYTES) {
      throw new Error(`File too large: ${name}`);
    }
    totalBytes += bytes;
    if (totalBytes > MAX_TOTAL_BYTES) {
      throw new Error('Total file payload too large');
    }
    filesOut[name] = content;
  }
  if (Object.keys(filesOut).length === 0) {
    filesOut['index.js'] = "console.log('hello from sandbox');\n";
  }
  return filesOut;
}

function normalizePackageJson(input) {
  if (typeof input === 'string') {
    try {
      const parsed = JSON.parse(input);
      return JSON.stringify(parsed, null, 2) + '\n';
    } catch {
      throw new Error('packageJson must be valid JSON');
    }
  }
  if (input && typeof input === 'object') {
    return JSON.stringify(input, null, 2) + '\n';
  }
  return JSON.stringify(
    {
      name: 'kernel-runner-playground',
      version: '0.0.1',
      private: true,
      scripts: { test: 'node index.js' },
    },
    null,
    2,
  ) + '\n';
}

function safeRunCommand(input) {
  const raw = String(input || 'npm test').trim();
  if (/^npm\s+test(\s+.*)?$/i.test(raw)) return raw;
  if (/^npm\s+run\s+[a-zA-Z0-9:_-]+(\s+.*)?$/i.test(raw)) return raw;
  throw new Error('runCommand is restricted to `npm test` or `npm run <script>`');
}

function extractScriptText(pkgObj) {
  const scripts = asObject(pkgObj.scripts);
  return Object.entries(scripts)
    .map(([k, v]) => `${k}: ${String(v ?? '')}`)
    .join('\n');
}

function matchAny(patterns, text) {
  const hits = [];
  for (const pattern of patterns) {
    pattern.lastIndex = 0;
    if (pattern.test(text)) hits.push(pattern.source);
  }
  return hits;
}

function buildVerification({ packageJsonText, packageJsonObj, files, runCommand }) {
  const allText = [packageJsonText, extractScriptText(packageJsonObj), ...Object.values(files)].join('\n');
  const scriptText = extractScriptText(packageJsonObj);

  let truth = 0;
  let useful = 0;
  let harmful = 0;
  const reasons = [];

  if (packageJsonObj && typeof packageJsonObj === 'object') {
    truth += 0.3;
    reasons.push('package_json_parsed');
  }
  if (Object.keys(files).length > 0) {
    truth += 0.2;
    reasons.push('files_present');
  }
  if (Buffer.byteLength(allText, 'utf8') >= 120) {
    truth += 0.2;
    useful += 0.25;
    reasons.push('content_size_ok');
  }
  if (scriptText.includes('test')) {
    useful += 0.25;
    reasons.push('test_script_present');
  }
  if (/npm\s+(test|run)/i.test(runCommand)) {
    useful += 0.2;
    reasons.push('run_command_valid');
  }
  if (/TODO|TBD|placeholder/i.test(allText)) {
    truth -= 0.1;
    reasons.push('uncertainty_marker_found');
  } else {
    truth += 0.15;
    reasons.push('no_uncertainty_markers');
  }

  const secretHits = matchAny(SECRET_PATTERNS, allText);
  if (secretHits.length > 0) {
    harmful += 0.65;
    reasons.push('secret_pattern_detected');
  }
  const maliciousHits = matchAny(MALICIOUS_PATTERNS, allText);
  if (maliciousHits.length > 0) {
    harmful += 0.45;
    reasons.push('malicious_pattern_detected');
  }
  const riskyScriptHits = matchAny(HIGH_RISK_SCRIPT_PATTERNS, scriptText);
  if (riskyScriptHits.length > 0) {
    harmful += 0.25;
    reasons.push('high_risk_script_found');
  }

  const verification = {
    truth_score: Number(clamp01(truth).toFixed(4)),
    useful_score: Number(clamp01(useful).toFixed(4)),
    harmful_score: Number(clamp01(harmful).toFixed(4)),
    secret_hits: secretHits,
    malicious_hits: maliciousHits,
    risky_script_hits: riskyScriptHits,
    reasons,
  };

  let action = 'ALLOW';
  let reason = 'Verification scores passed policy.';
  let confidence = 0.92;
  if (verification.harmful_score > 0.35) {
    action = 'DENY';
    reason = 'High harmful score.';
    confidence = 0.98;
  } else if (verification.truth_score < 0.55 || verification.useful_score < 0.45) {
    action = 'QUARANTINE';
    reason = 'Low truth/useful score.';
    confidence = 0.86;
  }

  return {
    verification,
    state_vector: {
      coherence: verification.truth_score,
      energy: verification.useful_score,
      drift: verification.harmful_score,
    },
    decision_record: {
      action,
      signature: `kernel-runner:${action.toLowerCase()}:${Date.now()}`,
      timestamp: nowIso(),
      reason,
      confidence,
    },
  };
}

function runProcess(command, args, timeoutMs) {
  return new Promise((resolve) => {
    const child = spawn(command, args, { windowsHide: true });
    let stdout = '';
    let stderr = '';
    let timedOut = false;
    const start = Date.now();

    const timer = setTimeout(() => {
      timedOut = true;
      child.kill('SIGKILL');
    }, timeoutMs);

    child.stdout.on('data', (chunk) => {
      stdout += chunk.toString('utf8');
    });
    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString('utf8');
    });
    child.on('error', (error) => {
      clearTimeout(timer);
      resolve({
        ok: false,
        exit_code: -1,
        timed_out: false,
        duration_ms: Date.now() - start,
        stdout: '',
        stderr: String(error?.message || error),
      });
    });
    child.on('close', (code) => {
      clearTimeout(timer);
      resolve({
        ok: !timedOut && code === 0,
        exit_code: code ?? -1,
        timed_out: timedOut,
        duration_ms: Date.now() - start,
        stdout: clipText(stdout),
        stderr: clipText(stderr),
      });
    });
  });
}

async function runDockerStage({
  workspace,
  command,
  timeoutMs,
  network = 'none',
}) {
  const args = [
    'run',
    '--rm',
    '--cpus',
    '1.0',
    '--memory',
    '1024m',
    '--pids-limit',
    '256',
    '--user',
    'node',
    '--workdir',
    '/workspace',
    '--volume',
    `${workspace}:/workspace`,
  ];

  if (network === 'none') {
    args.push('--network', 'none');
  }

  args.push(DOCKER_IMAGE, 'sh', '-lc', command);
  return runProcess('docker', args, timeoutMs);
}

async function checkDocker() {
  const result = await runProcess('docker', ['--version'], 8000);
  return {
    available: result.ok,
    detail: result.ok ? result.stdout.trim() : (result.stderr || result.stdout).trim(),
  };
}

function parsePayload(body) {
  const packageJsonText = normalizePackageJson(body.packageJson);
  const packageJsonObj = JSON.parse(packageJsonText);
  const files = normalizeFiles(body.files || {});
  const runCommand = safeRunCommand(body.runCommand);
  return { packageJsonText, packageJsonObj, files, runCommand };
}

const app = express();
app.use(express.json({ limit: '3mb' }));
app.use(express.static(publicDir));

app.get('/api/health', async (_req, res) => {
  const docker = await checkDocker();
  res.json({
    status: 'ok',
    service: 'kernel-runner',
    docker,
    image: DOCKER_IMAGE,
    timestamp: nowIso(),
  });
});

app.post('/api/preflight', (req, res) => {
  try {
    const payload = parsePayload(req.body || {});
    const result = buildVerification(payload);
    res.json({
      ok: true,
      ...result,
      file_count: Object.keys(payload.files).length,
    });
  } catch (error) {
    res.status(400).json({
      ok: false,
      error: String(error?.message || error),
    });
  }
});

app.post('/api/run', async (req, res) => {
  let workspace = '';
  try {
    const payload = parsePayload(req.body || {});
    const preflight = buildVerification(payload);
    if (preflight.decision_record.action !== 'ALLOW') {
      return res.status(403).json({
        ok: false,
        blocked: true,
        ...preflight,
      });
    }

    const docker = await checkDocker();
    if (!docker.available) {
      return res.status(503).json({
        ok: false,
        error: 'Docker is not available.',
        docker,
      });
    }

    workspace = await fs.mkdtemp(path.join(os.tmpdir(), 'scbe-kernel-run-'));
    await fs.writeFile(path.join(workspace, 'package.json'), payload.packageJsonText, 'utf8');

    for (const [name, content] of Object.entries(payload.files)) {
      const full = path.join(workspace, name);
      await fs.mkdir(path.dirname(full), { recursive: true });
      await fs.writeFile(full, content, 'utf8');
    }

    const installNetwork = req.body?.allowNetworkInstall === false ? 'none' : 'bridge';
    const installResult = await runDockerStage({
      workspace,
      network: installNetwork,
      timeoutMs: Number(req.body?.installTimeoutMs || 120000),
      command: 'npm install --ignore-scripts --no-audit --fund=false',
    });

    if (!installResult.ok) {
      return res.status(422).json({
        ok: false,
        stage: 'install',
        preflight,
        install: installResult,
      });
    }

    const executeResult = await runDockerStage({
      workspace,
      network: 'none',
      timeoutMs: Number(req.body?.runTimeoutMs || 120000),
      command: payload.runCommand,
    });

    return res.status(executeResult.ok ? 200 : 422).json({
      ok: executeResult.ok,
      preflight,
      install: installResult,
      execute: executeResult,
    });
  } catch (error) {
    return res.status(500).json({
      ok: false,
      error: String(error?.message || error),
    });
  } finally {
    if (workspace) {
      await fs.rm(workspace, { recursive: true, force: true });
    }
  }
});

app.use((_req, res) => {
  res.sendFile(path.join(publicDir, 'index.html'));
});

app.listen(PORT, () => {
  process.stdout.write(`kernel-runner listening on http://localhost:${PORT}\n`);
});
