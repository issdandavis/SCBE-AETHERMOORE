#!/usr/bin/env node
/**
 * @file scbe_docker_status.mjs
 * @module scripts/scbe_docker_status
 * @description Cross-platform Docker Compose orchestration utility.
 *              Replaces scbe_docker_status.ps1 for Linux/macOS/Windows.
 */

import { execSync, spawnSync } from 'child_process';
import { existsSync } from 'fs';
import { createConnection } from 'net';
import { resolve, join } from 'path';

const ROOT = resolve(import.meta.dirname, '..');

// ── Configuration ────────────────────────────────────────────────────────────

const STACK_FILES = {
  default: 'docker-compose.yml',
  api: 'docker-compose.api.yml',
  unified: 'docker-compose.unified.yml',
  research: 'docker-compose.research.yml',
  'hydra-remote': 'docker-compose.hydra-remote.yml',
};

const STACK_PROJECTS = {
  default: 'scbe-default',
  api: 'scbe-api',
  unified: 'scbe-unified',
  research: 'scbe-research',
  'hydra-remote': 'scbe-hydra-remote',
};

const STACK_PORTS = {
  default: [8000, 8080],
  api: [8080],
  unified: [8000, 8080, 8081, 9090, 3000, 6379],
  research: [8000],
  'hydra-remote': [],
};

const STACK_HEALTH = {
  default: ['http://localhost:8000/health'],
  api: ['http://localhost:8080/v1/health'],
  unified: [
    'http://localhost:8000/v1/health',
    'http://localhost:8080/health',
    'http://localhost:9090/-/healthy',
    'http://localhost:8081/health',
  ],
  research: ['http://localhost:8000/v1/health'],
  'hydra-remote': [],
};

// ── Logging helpers ──────────────────────────────────────────────────────────

function info(msg) { console.log(`\x1b[36m[INFO] ${msg}\x1b[0m`); }
function ok(msg) { console.log(`\x1b[32m[OK]   ${msg}\x1b[0m`); }
function warn(msg) { console.log(`\x1b[33m[WARN] ${msg}\x1b[0m`); }
function err(msg) { console.log(`\x1b[31m[ERR]  ${msg}\x1b[0m`); }

// ── Argument parsing ─────────────────────────────────────────────────────────

function parseArgs() {
  const args = process.argv.slice(2);
  const opts = {
    action: 'doctor',
    stack: 'api',
    containerName: '',
    logTail: 120,
    follow: false,
    noBuild: false,
    cleanVolumes: false,
    inspectStacks: false,
    showLogs: false,
  };

  for (let i = 0; i < args.length; i++) {
    const a = args[i].replace(/^-+/, '').toLowerCase();
    switch (a) {
      case 'action': opts.action = args[++i]; break;
      case 'stack': opts.stack = args[++i]; break;
      case 'containername': opts.containerName = args[++i]; break;
      case 'logtail': opts.logTail = parseInt(args[++i], 10); break;
      case 'follow': opts.follow = true; break;
      case 'nobuild': opts.noBuild = true; break;
      case 'cleanvolumes': opts.cleanVolumes = true; break;
      case 'inspectstacks': opts.inspectStacks = true; break;
      case 'showlogs': opts.showLogs = true; break;
      default: break;
    }
  }
  return opts;
}

// ── Docker helpers ───────────────────────────────────────────────────────────

function assertDockerReady() {
  try {
    execSync("docker version --format '{{.Server.Version}}'", { stdio: 'pipe' });
    ok('Docker daemon reachable.');
  } catch {
    err('Docker daemon is not reachable. Start Docker Desktop/Engine first.');
    process.exit(1);
  }
}

function assertComposeReady() {
  try {
    execSync('docker compose version', { stdio: 'pipe' });
    ok('Docker Compose plugin available.');
  } catch {
    err('Docker Compose plugin is unavailable.');
    process.exit(1);
  }
}

function getComposeFilePath(stack) {
  const file = STACK_FILES[stack];
  if (!file) { throw new Error(`Unknown stack '${stack}'.`); }
  const p = join(ROOT, file);
  if (!existsSync(p)) { throw new Error(`Compose file not found: ${p}`); }
  return p;
}

function getProjectName(stack) {
  const name = STACK_PROJECTS[stack];
  if (!name) { throw new Error(`Project name missing for stack '${stack}'.`); }
  return name;
}

function invokeCompose(stack, composeArgs) {
  const composeFile = getComposeFilePath(stack);
  const projectName = getProjectName(stack);
  const full = ['compose', '-p', projectName, '-f', composeFile, ...composeArgs];
  spawnSync('docker', full, { stdio: 'inherit', cwd: ROOT });
}

// ── Port checking (cross-platform) ──────────────────────────────────────────

function isPortInUse(port) {
  return new Promise((resolve) => {
    const sock = createConnection({ port, host: '127.0.0.1' });
    sock.once('connect', () => { sock.destroy(); resolve(true); });
    sock.once('error', () => resolve(false));
    sock.setTimeout(500, () => { sock.destroy(); resolve(false); });
  });
}

async function testPorts(stack) {
  const ports = STACK_PORTS[stack] || [];
  if (ports.length === 0) {
    info(`No host port checks defined for stack '${stack}'.`);
    return;
  }
  for (const port of ports) {
    const inUse = await isPortInUse(port);
    if (inUse) { warn(`Port ${port} is already in use.`); }
    else { ok(`Port ${port} is free.`); }
  }
}

// ── Health checking ──────────────────────────────────────────────────────────

async function testHealth(stack) {
  const urls = STACK_HEALTH[stack] || [];
  if (urls.length === 0) {
    info(`No HTTP health endpoints configured for stack '${stack}'.`);
    return;
  }
  for (const url of urls) {
    try {
      const resp = await fetch(url, { signal: AbortSignal.timeout(4000) });
      if (resp.ok) { ok(`${url} -> ${resp.status}`); }
      else { warn(`${url} -> ${resp.status}`); }
    } catch {
      warn(`${url} -> unreachable`);
    }
  }
}

// ── Actions ──────────────────────────────────────────────────────────────────

async function runDoctor(opts) {
  info(`Running Docker doctor for stack '${opts.stack}'`);
  assertDockerReady();
  assertComposeReady();

  const composePath = getComposeFilePath(opts.stack);
  ok(`Compose file found: ${composePath}`);

  try {
    execSync(`docker compose -f "${composePath}" config`, { stdio: 'pipe', cwd: ROOT });
    ok('Compose config is valid.');
  } catch {
    warn('Compose config validation failed.');
  }

  if (existsSync(join(ROOT, '.env'))) { ok('.env file present.'); }
  else { warn('.env file missing. Copy from .env.example for predictable runtime settings.'); }

  await testPorts(opts.stack);
  invokeCompose(opts.stack, ['ps']);
  await testHealth(opts.stack);

  if (opts.showLogs) {
    invokeCompose(opts.stack, ['logs', '--tail', String(opts.logTail)]);
  }
}

async function runStatus(opts) {
  assertDockerReady();
  assertComposeReady();
  info(`Status for stack '${opts.stack}'`);
  invokeCompose(opts.stack, ['ps']);
  await testHealth(opts.stack);
}

async function runUp(opts) {
  assertDockerReady();
  assertComposeReady();
  await testPorts(opts.stack);
  info(`Starting stack '${opts.stack}'`);
  const args = ['up', '-d'];
  if (!opts.noBuild) args.push('--build');
  invokeCompose(opts.stack, args);
  await runStatus(opts);
}

function runDown(opts) {
  assertDockerReady();
  assertComposeReady();
  info(`Stopping stack '${opts.stack}'`);
  const args = ['down'];
  if (opts.cleanVolumes) args.push('--volumes');
  invokeCompose(opts.stack, args);
}

async function runRestart(opts) {
  runDown(opts);
  await runUp(opts);
}

function runLogs(opts) {
  assertDockerReady();
  if (opts.containerName) {
    const args = ['logs', '--tail', String(opts.logTail)];
    if (opts.follow) args.push('-f');
    args.push(opts.containerName);
    spawnSync('docker', args, { stdio: 'inherit' });
    return;
  }
  assertComposeReady();
  const composeArgs = ['logs', '--tail', String(opts.logTail)];
  if (opts.follow) composeArgs.push('-f');
  invokeCompose(opts.stack, composeArgs);
}

function runBuild(opts) {
  assertDockerReady();
  assertComposeReady();
  info(`Building stack '${opts.stack}'`);
  invokeCompose(opts.stack, ['build']);
}

function runClean() {
  assertDockerReady();
  warn('Pruning stopped containers and dangling images...');
  spawnSync('docker', ['system', 'prune', '-f'], { stdio: 'inherit' });
}

// ── Entry point ──────────────────────────────────────────────────────────────

async function main() {
  const opts = parseArgs();

  if (opts.inspectStacks) {
    assertDockerReady();
    assertComposeReady();
    for (const stack of Object.keys(STACK_FILES)) {
      console.log(`\n\x1b[35m==== STACK: ${stack} ====\x1b[0m`);
      try { await runStatus({ ...opts, stack }); }
      catch (e) { warn(`Failed to inspect stack '${stack}': ${e.message}`); }
    }
    process.exit(0);
  }

  switch (opts.action) {
    case 'doctor': await runDoctor(opts); break;
    case 'up': await runUp(opts); break;
    case 'down': runDown(opts); break;
    case 'restart': await runRestart(opts); break;
    case 'status': await runStatus(opts); break;
    case 'logs': runLogs(opts); break;
    case 'health': await testHealth(opts.stack); break;
    case 'build': runBuild(opts); break;
    case 'clean': runClean(); break;
    default: err(`Unsupported action '${opts.action}'.`); process.exit(1);
  }
}

main().catch((e) => { err(e.message); process.exit(1); });
