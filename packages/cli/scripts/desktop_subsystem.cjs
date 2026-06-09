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
      '  scbe desktop test            Run desktop runtime tests',
      '  scbe desktop build           Build the desktop app',
      '  scbe desktop pack            Build a portable static zip',
      '  scbe desktop --json          Machine-readable status',
      '',
      'Options:',
      '  --port <n>                   Preferred local dev port (default 3000)',
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

function psSingle(value) {
  return `'${String(value).replace(/'/g, "''")}'`;
}

function startDevServer(port, logPath) {
  const errPath = logPath.replace(/\.log$/i, '.err.log');
  if (process.platform === 'win32') {
    const launcherPath = path.join(ARTIFACT_ROOT, `run-dev-${port}.cmd`);
    fs.writeFileSync(
      launcherPath,
      [
        '@echo off',
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
    }
  );
  child.unref();
  return { pid: child.pid, err_path: logPath };
}

async function runOpen(args) {
  ensureDesktopRoot();
  const asJson = hasFlag(args, '--json');
  const dryRun = hasFlag(args, '--dry-run');
  const preferredPort = Number.parseInt(flagValue(args, '--port', '3000'), 10) || 3000;
  const port = dryRun ? preferredPort : await findPort(preferredPort);
  const url = `http://127.0.0.1:${port}/`;
  const logPath = path.join(ARTIFACT_ROOT, `dev-server-${port}.log`);
  ensureDir(ARTIFACT_ROOT);
  const payload = {
    schema_version: 'scbe_portable_desktop_open_v1',
    desktop_root: DESKTOP_ROOT,
    url,
    log_path: logPath,
    command: `npm --prefix ${DESKTOP_ROOT} run dev -- --host 127.0.0.1 --port ${port}`,
    dry_run: dryRun,
  };

  if (dryRun) {
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
    return;
  }

  const server = startDevServer(port, logPath);
  payload.pid = server.pid;
  payload.stderr_path = server.err_path;
  payload.ready = await waitForHttp(url);
  if (!hasFlag(args, '--no-open')) openUrl(url);

  if (asJson) {
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
  } else {
    process.stdout.write(
      [
        'SCBE portable desktop is running.',
        '',
        `url: ${url}`,
        `pid: ${child.pid}`,
        `log: ${logPath}`,
        '',
      ].join('\n')
    );
  }
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
  if (sub === 'test') {
    ensureDesktopRoot();
    const child = runNpm('test');
    process.exit(typeof child.status === 'number' ? child.status : 1);
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
