#!/usr/bin/env node
/**
 * @file scbe_mcp_terminal.mjs
 * @module scripts/scbe_mcp_terminal
 * @description Cross-platform Docker MCP terminal wrapper.
 *              Replaces scbe_mcp_terminal.ps1 for Linux/macOS/Windows.
 */

import { execSync, spawnSync } from 'child_process';

// ── Logging helpers ──────────────────────────────────────────────────────────

function info(msg) { console.log(`\x1b[36m[INFO] ${msg}\x1b[0m`); }
function ok(msg) { console.log(`\x1b[32m[OK]   ${msg}\x1b[0m`); }
function err(msg) { console.log(`\x1b[31m[ERR]  ${msg}\x1b[0m`); }

// ── Argument parsing ─────────────────────────────────────────────────────────

function parseArgs() {
  const args = process.argv.slice(2);
  const opts = { action: 'doctor', name: '', argsJson: '{}', verbose: false };

  for (let i = 0; i < args.length; i++) {
    const a = args[i].replace(/^-+/, '').toLowerCase();
    switch (a) {
      case 'action': opts.action = args[++i]; break;
      case 'name': opts.name = args[++i]; break;
      case 'argsjson': opts.argsJson = args[++i]; break;
      case 'verboseoutput': case 'verbose': opts.verbose = true; break;
      default: break;
    }
  }
  return opts;
}

// ── Docker MCP helpers ───────────────────────────────────────────────────────

function assertDockerMcpReady() {
  try {
    execSync("docker version --format '{{.Server.Version}}'", { stdio: 'pipe' });
    execSync('docker mcp --version', { stdio: 'pipe' });
    ok('Docker + MCP CLI are available.');
  } catch {
    err('Docker MCP CLI not available. Install/update Docker Desktop MCP Toolkit.');
    process.exit(1);
  }
}

function dockerMcp(args, opts = {}) {
  return spawnSync('docker', ['mcp', ...args], { stdio: 'inherit', ...opts });
}

function requireName(name, label) {
  if (!name) {
    err(`Provide --Name for ${label}.`);
    process.exit(1);
  }
}

// ── Actions ──────────────────────────────────────────────────────────────────

function runDoctor() {
  assertDockerMcpReady();

  info('MCP version');
  dockerMcp(['version']);

  info('Enabled servers');
  dockerMcp(['server', 'ls']);

  info('Tool count');
  dockerMcp(['tools', 'count']);

  info('First tools');
  const result = spawnSync('docker', ['mcp', 'tools', 'ls'], { encoding: 'utf8' });
  if (result.stdout) {
    const lines = result.stdout.split('\n').slice(0, 40);
    console.log(lines.join('\n'));
  }
}

function runGateway() {
  assertDockerMcpReady();
  info('Starting Docker MCP gateway (Ctrl+C to stop)');
  dockerMcp(['gateway', 'run']);
}

function runTools(verbose) {
  assertDockerMcpReady();
  const args = ['tools', 'ls'];
  if (verbose) args.push('--verbose');
  dockerMcp(args);
}

function runServers() {
  assertDockerMcpReady();
  dockerMcp(['server', 'ls']);
}

function runToolCount() {
  assertDockerMcpReady();
  dockerMcp(['tools', 'count']);
}

function runToolInspect(name) {
  assertDockerMcpReady();
  requireName(name, 'tool inspection (example: browser_navigate)');
  dockerMcp(['tools', 'inspect', name]);
}

function runToolCall(name, argsJson) {
  assertDockerMcpReady();
  requireName(name, 'tool call (example: browser_navigate)');

  let payload;
  try {
    payload = JSON.parse(argsJson);
  } catch {
    err(`ArgsJson must be valid JSON. Received: ${argsJson}`);
    process.exit(1);
  }

  const compact = JSON.stringify(payload);
  info(`Calling tool '${name}' with payload: ${compact}`);
  dockerMcp(['tools', 'call', name, compact]);
}

function runServerEnable(name) {
  assertDockerMcpReady();
  requireName(name, 'server enable (example: github)');
  dockerMcp(['server', 'enable', name]);
}

function runServerDisable(name) {
  assertDockerMcpReady();
  requireName(name, 'server disable (example: github)');
  dockerMcp(['server', 'disable', name]);
}

// ── Entry point ──────────────────────────────────────────────────────────────

const opts = parseArgs();

switch (opts.action) {
  case 'doctor': runDoctor(); break;
  case 'gateway': runGateway(); break;
  case 'tools': runTools(opts.verbose); break;
  case 'servers': runServers(); break;
  case 'tool-count': runToolCount(); break;
  case 'tool-inspect': runToolInspect(opts.name); break;
  case 'tool-call': runToolCall(opts.name, opts.argsJson); break;
  case 'server-enable': runServerEnable(opts.name); break;
  case 'server-disable': runServerDisable(opts.name); break;
  default: err(`Unsupported action '${opts.action}'.`); process.exit(1);
}
