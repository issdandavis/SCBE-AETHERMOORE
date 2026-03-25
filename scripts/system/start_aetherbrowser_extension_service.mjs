#!/usr/bin/env node
/**
 * @file start_aetherbrowser_extension_service.mjs
 * @module scripts/system/start_aetherbrowser_extension_service
 * @description Cross-platform AetherBrowser extension service launcher.
 *              Starts the Python backend (uvicorn) and Chrome with debugging port.
 *              Replaces start_aetherbrowser_extension_service.ps1.
 */

import { spawn, execSync } from 'child_process';
import { existsSync, mkdirSync, writeFileSync } from 'fs';
import { resolve, join } from 'path';
import { createConnection } from 'net';
import { platform, homedir } from 'os';

const ROOT = resolve(import.meta.dirname, '..', '..');

// ── Argument parsing ─────────────────────────────────────────────────────────

function parseArgs() {
  const args = process.argv.slice(2);
  const opts = {
    backendHost: '127.0.0.1',
    backendPort: 8002,
    chromeDebugPort: 9222,
    chromePath: '',
    pythonExe: 'python',
    userDataDir: '',
    extensionDir: '',
    startUrl: '',
    killOnPortInUse: false,
    runVerify: false,
  };

  for (let i = 0; i < args.length; i++) {
    const a = args[i].replace(/^-+/, '').toLowerCase();
    switch (a) {
      case 'backendhost': opts.backendHost = args[++i]; break;
      case 'backendport': opts.backendPort = parseInt(args[++i], 10); break;
      case 'chromedebugport': opts.chromeDebugPort = parseInt(args[++i], 10); break;
      case 'chromepath': opts.chromePath = args[++i]; break;
      case 'pythonexe': opts.pythonExe = args[++i]; break;
      case 'userdatadir': opts.userDataDir = args[++i]; break;
      case 'extensiondir': opts.extensionDir = args[++i]; break;
      case 'starturl': opts.startUrl = args[++i]; break;
      case 'killonportinuse': opts.killOnPortInUse = true; break;
      case 'runverify': opts.runVerify = true; break;
      default: break;
    }
  }
  return opts;
}

// ── Cross-platform Chrome detection ──────────────────────────────────────────

function detectChromePath() {
  const os = platform();
  const candidates = [];

  if (os === 'win32') {
    candidates.push(
      'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
      'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
      join(homedir(), 'AppData', 'Local', 'Google', 'Chrome', 'Application', 'chrome.exe'),
    );
  } else if (os === 'darwin') {
    candidates.push(
      '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
      join(homedir(), 'Applications', 'Google Chrome.app', 'Contents', 'MacOS', 'Google Chrome'),
    );
  } else {
    // Linux
    candidates.push(
      '/usr/bin/google-chrome',
      '/usr/bin/google-chrome-stable',
      '/usr/bin/chromium-browser',
      '/usr/bin/chromium',
      '/snap/bin/chromium',
    );
  }

  for (const c of candidates) {
    if (existsSync(c)) return c;
  }

  // Fallback: try PATH
  try {
    const cmd = os === 'win32' ? 'where chrome' : 'which google-chrome || which chromium-browser || which chromium';
    return execSync(cmd, { encoding: 'utf8' }).trim().split('\n')[0];
  } catch {
    return null;
  }
}

function defaultUserDataDir() {
  return join(homedir(), '.scbe-aetherbrowser', 'profiles', 'service-main');
}

// ── Port utilities ───────────────────────────────────────────────────────────

function isPortListening(port) {
  return new Promise((res) => {
    const sock = createConnection({ port, host: '127.0.0.1' });
    sock.once('connect', () => { sock.destroy(); res(true); });
    sock.once('error', () => res(false));
    sock.setTimeout(500, () => { sock.destroy(); res(false); });
  });
}

function killPortProcess(port) {
  const os = platform();
  try {
    if (os === 'win32') {
      const out = execSync(`netstat -ano | findstr :${port} | findstr LISTENING`, { encoding: 'utf8' });
      const pids = new Set(out.split('\n').map((l) => l.trim().split(/\s+/).pop()).filter(Boolean));
      for (const pid of pids) {
        try { execSync(`taskkill /F /PID ${pid}`, { stdio: 'pipe' }); } catch { /* already gone */ }
      }
    } else {
      execSync(`lsof -ti :${port} | xargs -r kill -9 2>/dev/null || fuser -k ${port}/tcp 2>/dev/null || true`, { stdio: 'pipe' });
    }
  } catch { /* best effort */ }
}

// ── HTTP readiness polling ───────────────────────────────────────────────────

async function waitHttpReady(name, url, retries = 60, sleepMs = 500) {
  for (let i = 0; i < retries; i++) {
    await new Promise((r) => setTimeout(r, sleepMs));
    try {
      const resp = await fetch(url, { signal: AbortSignal.timeout(3000) });
      if (resp.ok) return;
    } catch { /* not ready yet */ }
  }
  throw new Error(`${name} did not become ready at ${url}`);
}

async function waitCdpReady(port, retries = 60, sleepMs = 500) {
  const url = `http://127.0.0.1:${port}/json/list`;
  for (let i = 0; i < retries; i++) {
    await new Promise((r) => setTimeout(r, sleepMs));
    try {
      const resp = await fetch(url, { signal: AbortSignal.timeout(3000) });
      if (resp.ok) return;
    } catch { /* not ready yet */ }
  }
  throw new Error(`Chrome CDP did not become ready at ${url}`);
}

// ── Main ─────────────────────────────────────────────────────────────────────

async function main() {
  const opts = parseArgs();

  // Resolve defaults
  if (!opts.chromePath) opts.chromePath = detectChromePath();
  if (!opts.chromePath) {
    console.error('[ERR] Could not detect Chrome/Chromium. Provide --ChromePath.');
    process.exit(1);
  }
  if (!opts.userDataDir) opts.userDataDir = defaultUserDataDir();
  if (!opts.extensionDir) opts.extensionDir = join(ROOT, 'src', 'extension');
  if (!opts.startUrl) opts.startUrl = `http://${opts.backendHost}:${opts.backendPort}/health`;

  // Ensure directories
  mkdirSync(opts.userDataDir, { recursive: true });
  const artifactsDir = join(ROOT, 'artifacts', 'system');
  const smokeDir = join(ROOT, 'artifacts', 'smokes');
  mkdirSync(artifactsDir, { recursive: true });
  mkdirSync(smokeDir, { recursive: true });

  const pidFile = join(artifactsDir, 'aetherbrowser_extension_service_pids.json');

  // Kill port occupants if requested
  if (opts.killOnPortInUse) {
    killPortProcess(opts.backendPort);
    if (opts.chromeDebugPort !== opts.backendPort) {
      killPortProcess(opts.chromeDebugPort);
    }
    await new Promise((r) => setTimeout(r, 800));
  }

  const started = [];
  let backendReused = false;
  let chromeReused = false;
  const childProcesses = [];

  try {
    // ── Backend ──────────────────────────────────────────────────────────
    const backendListening = await isPortListening(opts.backendPort);
    if (backendListening) {
      await waitHttpReady('Backend', `http://${opts.backendHost}:${opts.backendPort}/health`, 4, 300);
      backendReused = true;
      started.push({ name: 'backend', pid: null, reused: true, url: `http://${opts.backendHost}:${opts.backendPort}` });
    } else {
      const backendProc = spawn(opts.pythonExe, [
        '-m', 'uvicorn', 'src.aetherbrowser.serve:app',
        '--host', opts.backendHost,
        '--port', String(opts.backendPort),
      ], {
        cwd: ROOT,
        stdio: ['ignore', 'pipe', 'pipe'],
        detached: true,
      });
      backendProc.unref();
      childProcesses.push(backendProc);

      await waitHttpReady('Backend', `http://${opts.backendHost}:${opts.backendPort}/health`);
      started.push({ name: 'backend', pid: backendProc.pid, reused: false, url: `http://${opts.backendHost}:${opts.backendPort}` });
    }

    // ── Chrome ───────────────────────────────────────────────────────────
    const chromeListening = await isPortListening(opts.chromeDebugPort);
    if (chromeListening) {
      await waitCdpReady(opts.chromeDebugPort, 4, 300);
      chromeReused = true;
      started.push({ name: 'chrome', pid: null, reused: true, url: `http://127.0.0.1:${opts.chromeDebugPort}/json/list` });
    } else {
      const chromeArgs = [
        `--remote-debugging-port=${opts.chromeDebugPort}`,
        `--user-data-dir=${opts.userDataDir}`,
        '--no-first-run',
        '--no-default-browser-check',
        '--new-window',
        '--disable-sync',
        `--load-extension=${opts.extensionDir}`,
        `--disable-extensions-except=${opts.extensionDir}`,
        opts.startUrl,
      ];
      const chromeProc = spawn(opts.chromePath, chromeArgs, {
        cwd: ROOT,
        stdio: 'ignore',
        detached: true,
      });
      chromeProc.unref();
      childProcesses.push(chromeProc);

      await waitCdpReady(opts.chromeDebugPort);
      started.push({ name: 'chrome', pid: chromeProc.pid, reused: false, url: `http://127.0.0.1:${opts.chromeDebugPort}/json/list` });
    }

    // ── PID snapshot ─────────────────────────────────────────────────────
    const snapshot = {
      started_at_utc: new Date().toISOString(),
      repo_root: ROOT,
      backend: `http://${opts.backendHost}:${opts.backendPort}`,
      chrome_debug: `http://127.0.0.1:${opts.chromeDebugPort}/json/list`,
      chrome_path: opts.chromePath,
      extension_dir: opts.extensionDir,
      user_data_dir: opts.userDataDir,
      start_url: opts.startUrl,
      backend_reused: backendReused,
      chrome_reused: chromeReused,
      processes: started,
    };
    writeFileSync(pidFile, JSON.stringify(snapshot, null, 2), 'utf8');

    console.log('\x1b[32mAetherBrowser extension service started.\x1b[0m');
    for (const item of started) {
      const pidDisplay = item.pid == null ? 'reused' : `PID ${item.pid}`;
      console.log(`\x1b[36m - ${item.name}: ${pidDisplay} (${item.url})\x1b[0m`);
    }
    console.log(`PID snapshot: ${pidFile}`);

    // ── Optional verification ────────────────────────────────────────────
    if (opts.runVerify) {
      const verifyScript = join(ROOT, 'scripts', 'verify_aetherbrowser_extension_service.py');
      const { spawnSync: spawnSyncLocal } = await import('child_process');
      spawnSyncLocal(opts.pythonExe, [
        verifyScript,
        '--host', opts.backendHost,
        '--port', String(opts.backendPort),
        '--chrome-port', String(opts.chromeDebugPort),
        '--run-backend-smoke',
        '--json',
      ], { stdio: 'inherit', cwd: ROOT });
    }
  } catch (e) {
    // Cleanup on failure
    for (const entry of started) {
      if (entry.pid) {
        try { process.kill(entry.pid, 'SIGTERM'); } catch { /* already gone */ }
      }
    }
    throw e;
  }
}

main().catch((e) => {
  console.error(`\x1b[31m[ERR] ${e.message}\x1b[0m`);
  process.exit(1);
});
