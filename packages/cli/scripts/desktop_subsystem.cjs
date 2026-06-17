'use strict';

const { spawn, spawnSync } = require('node:child_process');
const fs = require('node:fs');
const http = require('node:http');
const net = require('node:net');
const os = require('node:os');
const path = require('node:path');

const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');
const DESKTOP_ROOT = path.join(REPO_ROOT, 'packages', 'polly-pad-os');
const ARTIFACT_ROOT = path.join(REPO_ROOT, 'artifacts', 'portable-desktop');
const ACTION_HISTORY_ROOT = path.join(REPO_ROOT, 'artifacts', 'scbe-actions');
const ACTION_RUNNER = path.join(REPO_ROOT, 'packages', 'cli', 'scripts', 'action_runner.cjs');
const CAPABILITY_BENCH = path.join(
  REPO_ROOT,
  'packages',
  'polly-pad-os',
  'scripts',
  'capability_benchmark.ts'
);
const DEFAULT_ZIP = path.join(
  os.homedir(),
  'Downloads',
  'Kimi_Agent_Build PowerShell CLI Shell.zip'
);

function hasFlag(args, name) {
  return args.includes(name);
}

function flagValue(args, name, fallback = '') {
  const index = args.indexOf(name);
  if (index < 0) return fallback;
  const value = args[index + 1];
  if (!value || value.startsWith('--')) return fallback;
  return value;
}

function firstPositionalArg(args, flagsWithValue = []) {
  const skip = new Set(flagsWithValue);
  for (let i = 0; i < args.length; i += 1) {
    const arg = String(args[i] || '');
    if (!arg) continue;
    if (skip.has(arg)) {
      i += 1;
      continue;
    }
    if (!arg.startsWith('--')) return arg;
  }
  return '';
}

function npmBin() {
  return process.platform === 'win32' ? 'npm.cmd' : 'npm';
}

function cmdToken(value) {
  const text = String(value);
  if (/^[A-Za-z0-9_.:/\\-]+$/.test(text)) return text;
  return JSON.stringify(text);
}

function firstLine(text) {
  return (
    String(text || '')
      .split(/\r?\n/)
      .find(Boolean) || ''
  );
}

function runNpm(script, extraArgs = []) {
  if (process.platform === 'win32') {
    const command = [
      'npm',
      '--prefix',
      cmdToken(DESKTOP_ROOT),
      'run',
      cmdToken(script),
      ...extraArgs.map(cmdToken),
    ].join(' ');
    return spawnSync('cmd.exe', ['/d', '/c', command], {
      cwd: REPO_ROOT,
      encoding: 'utf8',
      stdio: 'inherit',
    });
  }
  return spawnSync(npmBin(), ['--prefix', DESKTOP_ROOT, 'run', script, ...extraArgs], {
    cwd: REPO_ROOT,
    encoding: 'utf8',
    stdio: 'inherit',
  });
}

function countApps() {
  const registryPath = path.join(DESKTOP_ROOT, 'src', 'os', 'appRegistry.ts');
  if (!fs.existsSync(registryPath)) return null;
  const text = fs.readFileSync(registryPath, 'utf8');
  const ids = new Set();
  for (const match of text.matchAll(/\bid:\s*['"]([^'"]+)['"]/g)) {
    ids.add(match[1]);
  }
  return ids.size || null;
}

function inspectDesktop() {
  const pkgPath = path.join(DESKTOP_ROOT, 'package.json');
  const distIndex = path.join(DESKTOP_ROOT, 'dist', 'index.html');
  let packageName = null;
  let version = null;
  if (fs.existsSync(pkgPath)) {
    try {
      const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
      packageName = pkg.name || null;
      version = pkg.version || null;
    } catch (_err) {
      packageName = 'unreadable-package-json';
    }
  }
  return {
    schema_version: 'scbe_portable_desktop_status_v1',
    repo_root: REPO_ROOT,
    desktop_root: DESKTOP_ROOT,
    package_name: packageName,
    version,
    source_zip: DEFAULT_ZIP,
    source_zip_exists: fs.existsSync(DEFAULT_ZIP),
    package_exists: fs.existsSync(pkgPath),
    node_modules_exists: fs.existsSync(path.join(DESKTOP_ROOT, 'node_modules')),
    dist_exists: fs.existsSync(distIndex),
    dist_index: distIndex,
    app_count: countApps(),
    launcher_commands: {
      status: 'scbe desktop --json',
      open: 'scbe desktop open',
      browse: 'scbe desktop browse https://example.com --json',
      capture: 'scbe desktop capture --json',
      bridge: 'scbe desktop bridge',
      test: 'scbe desktop test',
      build: 'scbe desktop build',
      pack: 'scbe desktop pack',
    },
  };
}

function printHelp() {
  process.stdout.write(
    [
      'Usage:',
      '  scbe desktop                 Show portable desktop status',
      '  scbe desktop open            Start dev server and open browser',
      '  scbe desktop browse <url>    Open a real page headlessly and capture it',
      '  scbe desktop capture [url]   Capture the desktop/page surface to an artifact',
      '  scbe desktop bridge          Start the local action bridge only',
      '  scbe desktop bridge-smoke    Prove bridge health + PowerShell + browser capture',
      '  scbe desktop test            Run desktop runtime tests',
      '  scbe desktop app-bench       Benchmark app capability status and goals',
      '  scbe desktop build           Build the desktop app',
      '  scbe desktop pack            Build a portable static zip',
      '  scbe desktop --json          Machine-readable status',
      '',
      'Options:',
      '  --port <n>                   Preferred local dev port (default 3000)',
      '  --bridge-port <n>            Preferred action bridge port (default 3678)',
      '  --no-open                    Start server without opening browser',
      '  --dry-run                    For pack/open, show what would happen',
      '  --out <path>                 Portable zip destination',
      '',
      'Source:',
      `  ${DEFAULT_ZIP}`,
      '',
    ].join('\n')
  );
}

function printStatus(asJson) {
  const payload = inspectDesktop();
  if (asJson) {
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
    return;
  }
  process.stdout.write(
    [
      'SCBE Portable Desktop',
      '',
      `root:      ${payload.desktop_root}`,
      `apps:      ${payload.app_count ?? 'unknown'}`,
      `built:     ${payload.dist_exists ? 'yes' : 'no'}`,
      `deps:      ${payload.node_modules_exists ? 'installed' : 'missing'}`,
      `zip seed:  ${payload.source_zip_exists ? 'found' : 'missing'} (${payload.source_zip})`,
      '',
      'Commands:',
      '  scbe desktop open',
      '  scbe desktop browse <url>',
      '  scbe desktop capture [url]',
      '  scbe desktop bridge',
      '  scbe desktop test',
      '  scbe desktop build',
      '  scbe desktop pack',
      '',
    ].join('\n')
  );
}

function ensureDesktopRoot() {
  if (!fs.existsSync(path.join(DESKTOP_ROOT, 'package.json'))) {
    process.stderr.write(`Portable desktop package not found: ${DESKTOP_ROOT}\n`);
    process.stderr.write(`Expected seed zip: ${DEFAULT_ZIP}\n`);
    process.exit(2);
  }
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function isPortFree(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once('error', () => resolve(false));
    server.once('listening', () => {
      server.close(() => resolve(true));
    });
    server.listen(port, '127.0.0.1');
  });
}

async function findPort(preferred) {
  for (let port = preferred; port < preferred + 50; port += 1) {
    if (await isPortFree(port)) return port;
  }
  throw new Error(`No free local port found starting at ${preferred}`);
}

function waitForHttp(url, timeoutMs = 20000) {
  const started = Date.now();
  return new Promise((resolve) => {
    const tick = () => {
      const req = http.get(url, (res) => {
        res.resume();
        resolve(true);
      });
      req.on('error', () => {
        if (Date.now() - started > timeoutMs) {
          resolve(false);
        } else {
          setTimeout(tick, 400);
        }
      });
      req.setTimeout(1000, () => {
        req.destroy();
      });
    };
    tick();
  });
}

async function fetchJson(url, options = {}) {
  if (typeof fetch !== 'function') {
    throw new Error('global fetch is unavailable — requires Node 18+');
  }
  const method = options.method || 'GET';
  const headers = { 'content-type': 'application/json', ...(options.headers || {}) };
  const body = options.body ? JSON.stringify(options.body) : undefined;
  const res = await fetch(url, {
    method,
    headers,
    body,
    signal: AbortSignal.timeout(options.timeoutMs || 15000),
  });
  const text = await res.text();
  let payload = null;
  try {
    payload = text ? JSON.parse(text) : null;
  } catch (err) {
    throw new Error(`invalid JSON from ${url}: ${err.message}`);
  }
  return { status: res.status, payload };
}

function openUrl(url) {
  if (process.platform === 'win32') {
    spawn('powershell.exe', ['-NoProfile', '-Command', 'Start-Process', url], {
      detached: true,
      stdio: 'ignore',
    }).unref();
    return;
  }
  if (process.platform === 'darwin') {
    spawn('open', [url], { detached: true, stdio: 'ignore' }).unref();
    return;
  }
  spawn('xdg-open', [url], { detached: true, stdio: 'ignore' }).unref();
}

function commandPath(command) {
  try {
    const tool = process.platform === 'win32' ? 'where.exe' : 'which';
    const result = spawnSync(tool, [command], {
      encoding: 'utf8',
      timeout: 2000,
      stdio: ['ignore', 'pipe', 'ignore'],
    });
    if (result.status !== 0) return '';
    return firstLine(result.stdout || '').trim();
  } catch {
    return '';
  }
}

function resolveBrowserExecutable() {
  const envPath = String(process.env.SCBE_BROWSER_EXECUTABLE_PATH || '').trim();
  if (envPath && fs.existsSync(envPath)) return envPath;
  const windowsCandidates = [
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  ];
  if (process.platform === 'win32') {
    return windowsCandidates.find((candidate) => fs.existsSync(candidate)) || '';
  }
  const posixCandidates =
    process.platform === 'darwin'
      ? [
          '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
          '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
          commandPath('google-chrome'),
          commandPath('microsoft-edge'),
        ]
      : [
          commandPath('google-chrome'),
          commandPath('chromium-browser'),
          commandPath('chromium'),
          commandPath('microsoft-edge'),
        ];
  return posixCandidates.find((candidate) => candidate && fs.existsSync(candidate)) || '';
}

function loadPlaywrightChromium() {
  const tried = [];
  for (const id of ['playwright-core', '@playwright/test', 'playwright']) {
    try {
      const mod = require(id);
      const chromium = mod && mod.chromium;
      if (chromium) return { chromium, source: id };
      tried.push(`${id}: missing chromium export`);
    } catch (err) {
      tried.push(`${id}: ${err.message}`);
    }
  }
  return {
    chromium: null,
    source: null,
    error: `No Playwright runtime available. Tried ${tried.join(' | ')}`,
  };
}

async function launchBrowserRuntime(chromium) {
  const executablePath = resolveBrowserExecutable();
  const attempts = [];
  const options = [];
  if (executablePath) options.push({ headless: true, executablePath });
  options.push({ headless: true });
  let lastError = null;
  for (const launchOptions of options) {
    try {
      const browser = await chromium.launch(launchOptions);
      return { browser, executablePath: launchOptions.executablePath || null };
    } catch (err) {
      lastError = err;
      attempts.push(
        launchOptions.executablePath
          ? `executablePath=${launchOptions.executablePath}: ${err.message}`
          : `bundled: ${err.message}`
      );
    }
  }
  throw new Error(
    attempts.join(' | ') || (lastError ? lastError.message : 'browser launch failed')
  );
}

function psSingle(value) {
  return `'${String(value).replace(/'/g, "''")}'`;
}

function startDevServer(port, logPath, bridgeUrl = '') {
  const errPath = logPath.replace(/\.log$/i, '.err.log');
  if (process.platform === 'win32') {
    const launcherPath = path.join(ARTIFACT_ROOT, `run-dev-${port}.cmd`);
    fs.writeFileSync(
      launcherPath,
      [
        '@echo off',
        bridgeUrl ? `set VITE_SCBE_ACTION_BRIDGE=${bridgeUrl}` : '',
        `cd /d ${JSON.stringify(REPO_ROOT)}`,
        `${cmdToken(npmBin())} --prefix ${JSON.stringify(DESKTOP_ROOT)} run dev -- --host 127.0.0.1 --port ${port} > ${JSON.stringify(logPath)} 2> ${JSON.stringify(errPath)}`,
        '',
      ].join('\r\n'),
      'utf8'
    );
    const command = [
      "$p = Start-Process -FilePath 'cmd.exe'",
      `-ArgumentList @('/d', '/c', ${psSingle(launcherPath)})`,
      '-WindowStyle Hidden',
      '-PassThru;',
      '$p.Id',
    ].join(' ');
    const child = spawnSync('powershell.exe', ['-NoProfile', '-Command', command], {
      encoding: 'utf8',
    });
    if (child.status !== 0) {
      throw new Error(firstLine((child.stdout || '') + (child.stderr || 'Start-Process failed')));
    }
    return { pid: Number.parseInt(child.stdout.trim(), 10) || null, err_path: errPath };
  }

  const out = fs.openSync(logPath, 'a');
  const child = spawn(
    npmBin(),
    ['--prefix', DESKTOP_ROOT, 'run', 'dev', '--', '--host', '127.0.0.1', '--port', String(port)],
    {
      cwd: REPO_ROOT,
      detached: true,
      stdio: ['ignore', out, out],
      env: {
        ...process.env,
        ...(bridgeUrl ? { VITE_SCBE_ACTION_BRIDGE: bridgeUrl } : {}),
      },
    }
  );
  child.unref();
  return { pid: child.pid, err_path: logPath };
}

function startActionBridgeProcess(port, logPath, desktopUrl = '') {
  const errPath = logPath.replace(/\.log$/i, '.err.log');
  if (process.platform === 'win32') {
    const launcherPath = path.join(ARTIFACT_ROOT, `run-bridge-${port}.cmd`);
    fs.writeFileSync(
      launcherPath,
      [
        '@echo off',
        desktopUrl ? `set SCBE_DESKTOP_URL=${desktopUrl}` : '',
        `cd /d ${JSON.stringify(REPO_ROOT)}`,
        `${cmdToken(process.execPath)} ${JSON.stringify(__filename)} bridge --port ${port} > ${JSON.stringify(logPath)} 2> ${JSON.stringify(errPath)}`,
        '',
      ].join('\r\n'),
      'utf8'
    );
    const command = [
      "$p = Start-Process -FilePath 'cmd.exe'",
      `-ArgumentList @('/d', '/c', ${psSingle(launcherPath)})`,
      '-WindowStyle Hidden',
      '-PassThru;',
      '$p.Id',
    ].join(' ');
    const child = spawnSync('powershell.exe', ['-NoProfile', '-Command', command], {
      encoding: 'utf8',
    });
    if (child.status !== 0) {
      throw new Error(firstLine((child.stdout || '') + (child.stderr || 'Start-Process failed')));
    }
    return { pid: Number.parseInt(child.stdout.trim(), 10) || null, err_path: errPath };
  }

  const out = fs.openSync(logPath, 'a');
  const child = spawn(process.execPath, [__filename, 'bridge', '--port', String(port)], {
    cwd: REPO_ROOT,
    detached: true,
    stdio: ['ignore', out, out],
    env: {
      ...process.env,
      ...(desktopUrl ? { SCBE_DESKTOP_URL: desktopUrl } : {}),
    },
  });
  child.unref();
  return { pid: child.pid, err_path: logPath };
}

// Reap a spawned bridge AND its descendants. On Windows the bridge is launched
// through a `Start-Process cmd.exe` wrapper (for output redirection), so the
// recorded pid is the cmd.exe wrapper, not the node bridge grandchild — killing
// just that pid orphans the node server (it keeps answering and holds its log
// file open). `taskkill /T` kills the whole tree. On POSIX the bridge is a
// detached process-group leader, so a negative-pid signal kills the group.
function stopProcessTree(pid) {
  if (!pid) return;
  if (process.platform === 'win32') {
    spawnSync('taskkill', ['/PID', String(pid), '/T', '/F'], { stdio: 'ignore' });
    return;
  }
  try {
    process.kill(-pid, 'SIGTERM');
  } catch {
    /* group may already be gone */
  }
  try {
    process.kill(pid, 'SIGTERM');
  } catch {
    /* process may already be gone */
  }
}

function sendJson(res, status, payload) {
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  });
  res.end(`${JSON.stringify(payload, null, 2)}\n`);
}

function isPathInside(root, target) {
  const relative = path.relative(path.resolve(root), path.resolve(target));
  return relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative));
}

function artifactUrlFor(filePath) {
  const resolved = path.resolve(filePath);
  if (!isPathInside(ARTIFACT_ROOT, resolved)) return null;
  return `/artifact?path=${encodeURIComponent(resolved)}`;
}

function sendArtifact(res, filePath) {
  const resolved = path.resolve(String(filePath || ''));
  if (!isPathInside(ARTIFACT_ROOT, resolved)) {
    sendJson(res, 403, { error: 'artifact path outside bridge artifact root' });
    return;
  }
  if (!fs.existsSync(resolved) || !fs.statSync(resolved).isFile()) {
    sendJson(res, 404, { error: 'artifact not found' });
    return;
  }
  const ext = path.extname(resolved).toLowerCase();
  const contentType =
    ext === '.png'
      ? 'image/png'
      : ext === '.jpg' || ext === '.jpeg'
        ? 'image/jpeg'
        : 'application/octet-stream';
  res.writeHead(200, {
    'Content-Type': contentType,
    'Access-Control-Allow-Origin': '*',
  });
  fs.createReadStream(resolved).pipe(res);
}

function readRequestJson(req, maxBytes = 1024 * 1024) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.setEncoding('utf8');
    req.on('data', (chunk) => {
      body += chunk;
      if (body.length > maxBytes) reject(new Error('request body too large'));
    });
    req.on('end', () => {
      if (!body.trim()) {
        resolve({});
        return;
      }
      try {
        resolve(JSON.parse(body));
      } catch (_err) {
        reject(new Error('invalid JSON body'));
      }
    });
    req.on('error', reject);
  });
}

function actionCatalogJson() {
  const result = spawnSync(process.execPath, [ACTION_RUNNER, 'list', '--json'], {
    cwd: REPO_ROOT,
    encoding: 'utf8',
    timeout: 30_000,
    maxBuffer: 4 * 1024 * 1024,
  });
  if (result.status !== 0) {
    return {
      schema_version: 'scbe_action_catalog_v1',
      count: 0,
      actions: [],
      error: firstLine(result.stderr || result.stdout || 'action catalog failed'),
    };
  }
  return JSON.parse(result.stdout);
}

function runActionJson(id, { dryRun = false } = {}) {
  const args = ['run', String(id || ''), '--json'];
  if (dryRun) args.push('--dry-run');
  const result = spawnSync(process.execPath, [ACTION_RUNNER, ...args], {
    cwd: REPO_ROOT,
    encoding: 'utf8',
    timeout: 180_000,
    maxBuffer: 12 * 1024 * 1024,
  });
  let payload;
  try {
    payload = JSON.parse(result.stdout || '{}');
  } catch (_err) {
    payload = {
      schema_version: 'scbe_action_result_v1',
      action_id: id || null,
      success: false,
      exit_code: typeof result.status === 'number' ? result.status : 1,
      error: 'action runner returned non-JSON',
      stdout_preview: firstLine(result.stdout || ''),
      stderr_preview: firstLine(result.stderr || ''),
    };
  }
  return { status: result.status === 0 ? 200 : 500, payload };
}

function normalizeUrl(input) {
  const raw = String(input || '').trim();
  if (!raw) return '';
  if (/^https?:\/\//i.test(raw)) return raw;
  if (/^(localhost|127\.0\.0\.1)(:\d+)?(\/.*)?$/i.test(raw)) return `http://${raw}`;
  if (raw.includes(' ') || !raw.includes('.')) {
    return `https://www.google.com/search?q=${encodeURIComponent(raw)}`;
  }
  return `https://${raw}`;
}

function runPowerShellCommand({ command, cwd } = {}) {
  const text = String(command || '').trim();
  const started = Date.now();
  if (!text) {
    return {
      status: 400,
      payload: {
        schema_version: 'scbe_terminal_command_result_v1',
        success: false,
        exit_code: 2,
        error: 'missing command',
        duration_ms: 0,
      },
    };
  }
  if (text.length > 8000) {
    return {
      status: 400,
      payload: {
        schema_version: 'scbe_terminal_command_result_v1',
        command: text.slice(0, 120),
        success: false,
        exit_code: 2,
        error: 'command too long',
        duration_ms: 0,
      },
    };
  }

  const requestedCwd = cwd ? path.resolve(String(cwd)) : REPO_ROOT;
  const runCwd = fs.existsSync(requestedCwd) ? requestedCwd : REPO_ROOT;
  const shell = process.platform === 'win32' ? 'powershell.exe' : 'pwsh';
  const marker = `__SCBE_CWD_${Date.now()}_${Math.random().toString(36).slice(2)}__=`;
  const wrappedCommand = [
    `$ErrorActionPreference = 'Continue'`,
    `Set-Location -LiteralPath ${psSingle(runCwd)}`,
    text,
    `Write-Output (${psSingle(marker)} + (Get-Location).Path)`,
  ].join('; ');
  const args =
    process.platform === 'win32'
      ? ['-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', wrappedCommand]
      : ['-NoLogo', '-NoProfile', '-Command', wrappedCommand];
  const result = spawnSync(shell, args, {
    cwd: runCwd,
    encoding: 'utf8',
    timeout: 60_000,
    maxBuffer: 8 * 1024 * 1024,
  });
  const rawStdout = result.stdout || '';
  let nextCwd = runCwd;
  const stdoutLines = rawStdout.split(/\r?\n/);
  const filteredStdout = [];
  for (const line of stdoutLines) {
    if (line.startsWith(marker)) {
      nextCwd = line.slice(marker.length).trim() || nextCwd;
    } else {
      filteredStdout.push(line);
    }
  }
  const stdout = filteredStdout.join('\n').replace(/\n+$/g, '');
  const stderr = result.stderr || '';
  const exitCode = typeof result.status === 'number' ? result.status : result.error ? 1 : 0;
  return {
    status: exitCode === 0 ? 200 : 500,
    payload: {
      schema_version: 'scbe_terminal_command_result_v1',
      command: text,
      cwd: runCwd,
      next_cwd: nextCwd,
      shell,
      success: exitCode === 0,
      exit_code: exitCode,
      duration_ms: Date.now() - started,
      stdout,
      stderr,
      stdout_preview: firstLine(stdout),
      stderr_preview: firstLine(stderr),
      error: result.error ? result.error.message : undefined,
    },
  };
}

async function captureScreen({ url, out } = {}) {
  const targetUrl = normalizeUrl(url || process.env.SCBE_DESKTOP_URL || 'http://127.0.0.1:3000/');
  const outPath = path.resolve(
    REPO_ROOT,
    out ||
      path.join(
        ARTIFACT_ROOT,
        'screens',
        `desktop-${new Date().toISOString().replace(/[:.]/g, '-')}.png`
      )
  );
  ensureDir(path.dirname(outPath));
  const runtime = loadPlaywrightChromium();
  if (!runtime.chromium) {
    return {
      status: 500,
      payload: {
        schema_version: 'scbe_screen_capture_v1',
        success: false,
        url: targetUrl,
        out_path: outPath,
        error: runtime.error,
      },
    };
  }

  const launched = await launchBrowserRuntime(runtime.chromium);
  const browser = launched.browser;
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 20_000 });
    await page.screenshot({ path: outPath, fullPage: true });
    return {
      status: 200,
      payload: {
        schema_version: 'scbe_screen_capture_v1',
        success: true,
        url: targetUrl,
        out_path: outPath,
        bytes: fs.statSync(outPath).size,
        runtime: runtime.source,
        browser_path: launched.executablePath,
      },
    };
  } finally {
    await browser.close();
  }
}

async function openBrowserPage({ url, out } = {}) {
  const targetUrl = normalizeUrl(url || 'https://example.com');
  const outPath = path.resolve(
    REPO_ROOT,
    out ||
      path.join(
        ARTIFACT_ROOT,
        'browser',
        `page-${new Date().toISOString().replace(/[:.]/g, '-')}.png`
      )
  );
  ensureDir(path.dirname(outPath));
  const runtime = loadPlaywrightChromium();
  if (!runtime.chromium) {
    return {
      status: 500,
      payload: {
        schema_version: 'scbe_browser_page_v1',
        success: false,
        requested_url: targetUrl,
        out_path: outPath,
        error: runtime.error,
      },
    };
  }

  const launched = await launchBrowserRuntime(runtime.chromium);
  const browser = launched.browser;
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    const response = await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 30_000 });
    const title = await page.title();
    await page.screenshot({ path: outPath, fullPage: true });
    const bytes = fs.statSync(outPath).size;
    return {
      status: 200,
      payload: {
        schema_version: 'scbe_browser_page_v1',
        success: true,
        requested_url: targetUrl,
        final_url: page.url(),
        title,
        status_code: response ? response.status() : null,
        out_path: outPath,
        screenshot_url: artifactUrlFor(outPath),
        bytes,
        runtime: runtime.source,
        browser_path: launched.executablePath,
      },
    };
  } finally {
    await browser.close();
  }
}

async function runBridge(args) {
  const port = Number.parseInt(flagValue(args, '--port', '3678'), 10) || 3678;
  ensureDir(ACTION_HISTORY_ROOT);
  const server = http.createServer(async (req, res) => {
    if (req.method === 'OPTIONS') {
      sendJson(res, 200, { ok: true });
      return;
    }
    const url = new URL(req.url || '/', `http://127.0.0.1:${port}`);
    try {
      if (req.method === 'GET' && url.pathname === '/health') {
        sendJson(res, 200, {
          schema_version: 'scbe_action_bridge_health_v1',
          ok: true,
          pid: process.pid,
          repo_root: REPO_ROOT,
          action_history_root: ACTION_HISTORY_ROOT,
          terminal: {
            shell: process.platform === 'win32' ? 'powershell.exe' : 'pwsh',
            endpoint: '/terminal/run',
            cwd: REPO_ROOT,
          },
          internet: {
            endpoint: '/internet/open',
          },
          screen: {
            endpoint: '/screen/capture',
          },
          browser: {
            endpoint: '/browser/open',
            artifact_endpoint: '/artifact',
          },
        });
        return;
      }
      if (req.method === 'GET' && url.pathname === '/artifact') {
        sendArtifact(res, url.searchParams.get('path'));
        return;
      }
      if (req.method === 'GET' && url.pathname === '/terminal/session') {
        sendJson(res, 200, {
          schema_version: 'scbe_terminal_session_v1',
          ok: true,
          shell: process.platform === 'win32' ? 'powershell.exe' : 'pwsh',
          cwd: REPO_ROOT,
          repo_root: REPO_ROOT,
          pid: process.pid,
          endpoints: {
            run: '/terminal/run',
            actions: '/actions/run',
            internet: '/internet/open',
            capture: '/screen/capture',
            browser: '/browser/open',
            artifact: '/artifact',
          },
        });
        return;
      }
      if (req.method === 'GET' && url.pathname === '/actions') {
        sendJson(res, 200, actionCatalogJson());
        return;
      }
      if (req.method === 'POST' && url.pathname === '/actions/run') {
        const body = await readRequestJson(req);
        const result = runActionJson(body.id, { dryRun: Boolean(body.dry_run) });
        sendJson(res, result.status, result.payload);
        return;
      }
      if (req.method === 'POST' && url.pathname === '/terminal/run') {
        const body = await readRequestJson(req);
        const result = runPowerShellCommand({ command: body.command, cwd: body.cwd });
        sendJson(res, result.status, result.payload);
        return;
      }
      if (req.method === 'POST' && url.pathname === '/internet/open') {
        const body = await readRequestJson(req);
        const target = normalizeUrl(body.url || body.query);
        if (!target) {
          sendJson(res, 400, {
            schema_version: 'scbe_internet_open_v1',
            success: false,
            error: 'missing url',
          });
          return;
        }
        openUrl(target);
        sendJson(res, 200, {
          schema_version: 'scbe_internet_open_v1',
          success: true,
          url: target,
          opened: 'system-browser',
        });
        return;
      }
      if (req.method === 'POST' && url.pathname === '/screen/capture') {
        const body = await readRequestJson(req);
        const result = await captureScreen({ url: body.url, out: body.out });
        sendJson(res, result.status, result.payload);
        return;
      }
      if (req.method === 'POST' && url.pathname === '/browser/open') {
        const body = await readRequestJson(req);
        const result = await openBrowserPage({ url: body.url || body.query, out: body.out });
        sendJson(res, result.status, result.payload);
        return;
      }
      sendJson(res, 404, { error: 'not found', path: url.pathname });
    } catch (err) {
      sendJson(res, 500, { error: err.message || 'bridge error' });
    }
  });
  server.listen(port, '127.0.0.1', () => {
    process.stdout.write(`SCBE action bridge listening on http://127.0.0.1:${port}\n`);
  });
  // Close the listener on a termination signal so the process exits promptly
  // instead of lingering on an open socket (POSIX group-kill / Ctrl-C path).
  const shutdown = () => {
    try {
      server.close();
    } catch {
      /* already closing */
    }
    process.exit(0);
  };
  process.once('SIGTERM', shutdown);
  process.once('SIGINT', shutdown);
}

async function runOpen(args) {
  ensureDesktopRoot();
  const asJson = hasFlag(args, '--json');
  const dryRun = hasFlag(args, '--dry-run');
  const preferredPort = Number.parseInt(flagValue(args, '--port', '3000'), 10) || 3000;
  const preferredBridgePort = Number.parseInt(flagValue(args, '--bridge-port', '3678'), 10) || 3678;
  const port = dryRun ? preferredPort : await findPort(preferredPort);
  const bridgePort = dryRun ? preferredBridgePort : await findPort(preferredBridgePort);
  const url = `http://127.0.0.1:${port}/`;
  const bridgeUrl = `http://127.0.0.1:${bridgePort}`;
  const logPath = path.join(ARTIFACT_ROOT, `dev-server-${port}.log`);
  const bridgeLogPath = path.join(ARTIFACT_ROOT, `action-bridge-${bridgePort}.log`);
  ensureDir(ARTIFACT_ROOT);
  const payload = {
    schema_version: 'scbe_portable_desktop_open_v1',
    desktop_root: DESKTOP_ROOT,
    url,
    bridge_url: bridgeUrl,
    log_path: logPath,
    bridge_log_path: bridgeLogPath,
    command: `npm --prefix ${DESKTOP_ROOT} run dev -- --host 127.0.0.1 --port ${port}`,
    bridge_command: `node ${__filename} bridge --port ${bridgePort}`,
    dry_run: dryRun,
  };

  if (dryRun) {
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
    return;
  }

  const bridge = startActionBridgeProcess(bridgePort, bridgeLogPath, url);
  const server = startDevServer(port, logPath, bridgeUrl);
  payload.pid = server.pid;
  payload.stderr_path = server.err_path;
  payload.bridge_pid = bridge.pid;
  payload.bridge_stderr_path = bridge.err_path;
  payload.ready = await waitForHttp(url);
  payload.bridge_ready = await waitForHttp(`${bridgeUrl}/health`);
  if (!hasFlag(args, '--no-open')) openUrl(url);

  if (asJson) {
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
  } else {
    process.stdout.write(
      [
        'SCBE portable desktop is running.',
        '',
        `url: ${url}`,
        `bridge: ${bridgeUrl}`,
        `pid: ${server.pid}`,
        `bridge pid: ${bridge.pid}`,
        `log: ${logPath}`,
        `bridge log: ${bridgeLogPath}`,
        '',
      ].join('\n')
    );
  }
}

async function runBridgeSmoke(args) {
  const asJson = hasFlag(args, '--json');
  const preferredPort = Number.parseInt(flagValue(args, '--port', '3678'), 10) || 3678;
  const browserUrl = flagValue(args, '--url', 'https://example.com');
  const command = flagValue(args, '--command', 'Write-Output "SCBE_BRIDGE_SMOKE_OK"');
  const port = await findPort(preferredPort);
  ensureDir(ARTIFACT_ROOT);
  const bridgeLogPath = path.join(ARTIFACT_ROOT, `action-bridge-smoke-${port}.log`);
  const bridge = startActionBridgeProcess(port, bridgeLogPath);
  const baseUrl = `http://127.0.0.1:${port}`;
  const payload = {
    schema_version: 'scbe_action_bridge_smoke_v1',
    success: false,
    bridge_url: baseUrl,
    bridge_pid: bridge.pid,
    bridge_log_path: bridgeLogPath,
    terminal_command: command,
    browser_url: browserUrl,
    health: null,
    terminal: null,
    browser: null,
    error: null,
  };
  try {
    const ready = await waitForHttp(`${baseUrl}/health`, 20000);
    if (!ready) {
      payload.error = 'bridge did not become healthy';
    } else {
      const health = await fetchJson(`${baseUrl}/health`);
      const terminal = await fetchJson(`${baseUrl}/terminal/run`, {
        method: 'POST',
        body: { command },
        timeoutMs: 20000,
      });
      const browser = await fetchJson(`${baseUrl}/browser/open`, {
        method: 'POST',
        body: { url: browserUrl },
        timeoutMs: 45000,
      });
      payload.health = health.payload;
      payload.terminal = terminal.payload;
      payload.browser = browser.payload;
      payload.success =
        health.status === 200 &&
        health.payload &&
        health.payload.ok === true &&
        terminal.status === 200 &&
        terminal.payload &&
        terminal.payload.success === true &&
        browser.status === 200 &&
        browser.payload &&
        browser.payload.success === true;
    }
  } catch (err) {
    payload.error = err && err.message ? err.message : String(err);
  } finally {
    stopProcessTree(bridge.pid);
  }
  if (asJson) {
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
  } else if (payload.success) {
    process.stdout.write(
      [
        'SCBE bridge smoke passed.',
        `bridge:   ${payload.bridge_url}`,
        `shell:    ${payload.terminal.shell}`,
        `stdout:   ${payload.terminal.stdout_preview || payload.terminal.stdout || ''}`,
        `browser:  ${payload.browser.title} (${payload.browser.final_url || payload.browser.requested_url})`,
        `artifact: ${payload.browser.screenshot_url || '<none>'}`,
        '',
      ].join('\n')
    );
  } else {
    process.stdout.write(
      `SCBE bridge smoke failed: ${payload.error || 'surface returned failure'}\n`
    );
  }
  process.exit(payload.success ? 0 : 1);
}

async function runBrowse(args) {
  const asJson = hasFlag(args, '--json');
  const url =
    flagValue(args, '--url') ||
    firstPositionalArg(args, ['--url', '--out']) ||
    'https://example.com';
  const out = flagValue(args, '--out', '');
  const result = await openBrowserPage({ url, out });
  if (asJson) {
    process.stdout.write(`${JSON.stringify(result.payload, null, 2)}\n`);
  } else if (result.payload && result.payload.success) {
    process.stdout.write(
      [
        'SCBE browser open passed.',
        `title:    ${result.payload.title}`,
        `url:      ${result.payload.final_url || result.payload.requested_url}`,
        `artifact: ${result.payload.screenshot_url || result.payload.out_path}`,
        `runtime:  ${result.payload.runtime || 'unknown'}`,
        '',
      ].join('\n')
    );
  } else {
    process.stdout.write(`SCBE browser open failed: ${result.payload?.error || 'unknown error'}\n`);
  }
  process.exit(result.status === 200 && result.payload?.success ? 0 : 1);
}

async function runCapture(args) {
  const asJson = hasFlag(args, '--json');
  const url =
    flagValue(args, '--url') ||
    firstPositionalArg(args, ['--url', '--out']) ||
    process.env.SCBE_DESKTOP_URL ||
    'http://127.0.0.1:3000/';
  const out = flagValue(args, '--out', '');
  const result = await captureScreen({ url, out });
  if (asJson) {
    process.stdout.write(`${JSON.stringify(result.payload, null, 2)}\n`);
  } else if (result.payload && result.payload.success) {
    process.stdout.write(
      [
        'SCBE screen capture passed.',
        `url:      ${result.payload.url}`,
        `artifact: ${result.payload.out_path}`,
        `bytes:    ${result.payload.bytes}`,
        `runtime:  ${result.payload.runtime || 'unknown'}`,
        '',
      ].join('\n')
    );
  } else {
    process.stdout.write(
      `SCBE screen capture failed: ${result.payload?.error || 'unknown error'}\n`
    );
  }
  process.exit(result.status === 200 && result.payload?.success ? 0 : 1);
}

function writePortableLaunchers(staging) {
  fs.writeFileSync(
    path.join(staging, 'open-desktop.ps1'),
    [
      '$here = Split-Path -Parent $MyInvocation.MyCommand.Path',
      '$index = Join-Path $here "dist/index.html"',
      'Start-Process $index',
      '',
    ].join('\r\n'),
    'utf8'
  );
  fs.writeFileSync(
    path.join(staging, 'open-desktop.cmd'),
    ['@echo off', 'start "" "%~dp0dist\\index.html"', ''].join('\r\n'),
    'utf8'
  );
  fs.writeFileSync(
    path.join(staging, 'README.txt'),
    [
      'SCBE Portable Desktop',
      '',
      'Open with:',
      '  open-desktop.cmd',
      '  powershell -ExecutionPolicy Bypass -File open-desktop.ps1',
      '',
      'This bundle is static Vite output from packages/polly-pad-os.',
      `Seed zip: ${DEFAULT_ZIP}`,
      '',
    ].join('\r\n'),
    'utf8'
  );
}

function compressDirectory(staging, outPath) {
  ensureDir(path.dirname(outPath));
  if (fs.existsSync(outPath)) fs.rmSync(outPath, { force: true });
  if (process.platform === 'win32') {
    const ps = spawnSync(
      'powershell.exe',
      [
        '-NoProfile',
        '-Command',
        `$items = Get-ChildItem -LiteralPath ${JSON.stringify(staging)}; Compress-Archive -Path $items.FullName -DestinationPath ${JSON.stringify(outPath)} -Force`,
      ],
      { encoding: 'utf8' }
    );
    if (ps.status !== 0) {
      process.stderr.write((ps.stdout || '') + (ps.stderr || 'Compress-Archive failed'));
      process.exit(ps.status || 1);
    }
    return;
  }
  const tar = spawnSync('tar', ['-a', '-cf', outPath, '-C', staging, '.'], {
    encoding: 'utf8',
  });
  if (tar.status !== 0) {
    process.stderr.write((tar.stdout || '') + (tar.stderr || 'tar compression failed'));
    process.exit(tar.status || 1);
  }
}

function runPack(args) {
  ensureDesktopRoot();
  const asJson = hasFlag(args, '--json');
  const dryRun = hasFlag(args, '--dry-run');
  const outPath = path.resolve(
    REPO_ROOT,
    flagValue(args, '--out', path.join(ARTIFACT_ROOT, 'scbe-portable-desktop.zip'))
  );
  const payload = {
    schema_version: 'scbe_portable_desktop_pack_v1',
    desktop_root: DESKTOP_ROOT,
    out_path: outPath,
    dry_run: dryRun,
    source_zip: DEFAULT_ZIP,
  };

  if (dryRun) {
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
    return;
  }

  if (!hasFlag(args, '--no-build')) {
    const build = runNpm('build');
    if (typeof build.status === 'number' && build.status !== 0) process.exit(build.status);
    if (typeof build.status !== 'number') process.exit(1);
  }

  const dist = path.join(DESKTOP_ROOT, 'dist');
  const staging = path.join(ARTIFACT_ROOT, 'staging', 'scbe-portable-desktop');
  fs.rmSync(staging, { recursive: true, force: true });
  ensureDir(staging);
  fs.cpSync(dist, path.join(staging, 'dist'), { recursive: true });
  writePortableLaunchers(staging);
  compressDirectory(staging, outPath);

  payload.bytes = fs.statSync(outPath).size;
  if (asJson) {
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
  } else {
    process.stdout.write(`Portable desktop bundle: ${outPath}\n`);
  }
}

function runAppBench(args) {
  ensureDesktopRoot();
  const child = spawnSync(
    process.execPath,
    ['--experimental-strip-types', CAPABILITY_BENCH, ...args],
    {
      cwd: REPO_ROOT,
      encoding: 'utf8',
      stdio: 'inherit',
    }
  );
  process.exit(typeof child.status === 'number' ? child.status : 1);
}

async function main() {
  const args = process.argv.slice(2);
  const sub = args[0] && !args[0].startsWith('--') ? args[0] : 'status';
  const rest = sub === 'status' ? args : args.slice(1);

  if (sub === 'help' || hasFlag(args, '--help') || hasFlag(args, '-h')) {
    printHelp();
    return;
  }
  if (sub === 'status') {
    printStatus(hasFlag(args, '--json'));
    return;
  }
  if (sub === 'bridge') {
    await runBridge(rest);
    return;
  }
  if (sub === 'browse' || sub === 'browser') {
    await runBrowse(rest);
    return;
  }
  if (sub === 'capture' || sub === 'screenshot') {
    await runCapture(rest);
    return;
  }
  if (sub === 'bridge-smoke' || sub === 'smoke') {
    await runBridgeSmoke(rest);
    return;
  }
  if (sub === 'test') {
    ensureDesktopRoot();
    const child = runNpm('test');
    process.exit(typeof child.status === 'number' ? child.status : 1);
  }
  if (sub === 'app-bench' || sub === 'apps' || sub === 'capabilities') {
    runAppBench(rest);
    return;
  }
  if (sub === 'build') {
    ensureDesktopRoot();
    const child = runNpm('build');
    process.exit(typeof child.status === 'number' ? child.status : 1);
  }
  if (sub === 'open' || sub === 'dev') {
    await runOpen(rest);
    return;
  }
  if (sub === 'pack' || sub === 'bundle') {
    runPack(rest);
    return;
  }

  process.stderr.write(`Unknown desktop command: ${sub}\n\n`);
  printHelp();
  process.exit(2);
}

main().catch((err) => {
  process.stderr.write(`${err.stack || err.message}\n`);
  process.exit(1);
});
