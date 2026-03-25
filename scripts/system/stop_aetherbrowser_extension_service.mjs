#!/usr/bin/env node
/**
 * @file stop_aetherbrowser_extension_service.mjs
 * @module scripts/system/stop_aetherbrowser_extension_service
 * @description Cross-platform AetherBrowser extension service shutdown.
 *              Reads PID snapshot and stops managed processes.
 *              Replaces stop_aetherbrowser_extension_service.ps1.
 */

import { readFileSync, existsSync } from 'fs';
import { resolve, join } from 'path';

const ROOT = resolve(import.meta.dirname, '..', '..');

// ── Argument parsing ─────────────────────────────────────────────────────────

function parseArgs() {
  const args = process.argv.slice(2);
  let pidFile = '';
  for (let i = 0; i < args.length; i++) {
    const a = args[i].replace(/^-+/, '').toLowerCase();
    if (a === 'pidfile') pidFile = args[++i];
  }
  return { pidFile };
}

// ── Process management ───────────────────────────────────────────────────────

function isProcessAlive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

function stopProcess(pid) {
  try {
    process.kill(pid, 'SIGTERM');
  } catch { /* already gone */ }
}

// ── Main ─────────────────────────────────────────────────────────────────────

function main() {
  const opts = parseArgs();
  const pidFile = opts.pidFile || join(ROOT, 'artifacts', 'system', 'aetherbrowser_extension_service_pids.json');

  if (!existsSync(pidFile)) {
    console.log(`\x1b[33mPID snapshot not found: ${pidFile}\x1b[0m`);
    return;
  }

  let json;
  try {
    json = JSON.parse(readFileSync(pidFile, 'utf8'));
  } catch (e) {
    console.error(`\x1b[31mFailed to parse PID file: ${e.message}\x1b[0m`);
    process.exit(1);
  }

  const processes = json.processes || [];
  if (processes.length === 0) {
    console.log(`\x1b[33mNo processes listed in ${pidFile}\x1b[0m`);
    return;
  }

  for (const entry of processes) {
    if (entry.reused) {
      console.log(`\x1b[90mSkipping reused process: ${entry.name}\x1b[0m`);
      continue;
    }
    const pid = entry.pid;
    if (pid && isProcessAlive(pid)) {
      console.log(`\x1b[33mStopping ${entry.name} PID ${pid}\x1b[0m`);
      stopProcess(pid);
    } else {
      console.log(`\x1b[90mAlready stopped: ${entry.name} PID ${pid}\x1b[0m`);
    }
  }

  console.log('\x1b[32mAetherBrowser extension service stop complete.\x1b[0m');
}

main();
