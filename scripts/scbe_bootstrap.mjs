#!/usr/bin/env node
/**
 * @file scbe_bootstrap.mjs
 * @module scripts/scbe_bootstrap
 * @description Cross-platform SCBE project bootstrap — installs dependencies,
 *              verifies Python/Node versions, and runs initial build.
 */

import { execSync } from 'child_process';
import { existsSync } from 'fs';
import { resolve } from 'path';

const ROOT = resolve(import.meta.dirname, '..');

function run(cmd, opts = {}) {
  console.log(`[bootstrap] ${cmd}`);
  try {
    execSync(cmd, { stdio: 'inherit', cwd: ROOT, ...opts });
  } catch (e) {
    if (!opts.ignoreError) {
      console.error(`[bootstrap] FAILED: ${cmd}`);
      process.exit(1);
    }
  }
}

function checkVersion(cmd, minMajor, label) {
  try {
    const out = execSync(cmd, { encoding: 'utf8' }).trim();
    const major = parseInt(out.replace(/^v/, '').split('.')[0], 10);
    if (major < minMajor) {
      console.warn(`[bootstrap] WARNING: ${label} version ${out} found, >= ${minMajor} recommended`);
    } else {
      console.log(`[bootstrap] ${label} ${out} OK`);
    }
  } catch {
    console.warn(`[bootstrap] ${label} not found — some features may be unavailable`);
  }
}

console.log('=== SCBE-AETHERMOORE Bootstrap ===\n');

// 1. Check prerequisites
checkVersion('node --version', 18, 'Node.js');
checkVersion('python3 --version 2>&1 || python --version 2>&1', 3, 'Python');

// 2. Install npm dependencies
if (!existsSync(resolve(ROOT, 'node_modules'))) {
  run('npm install');
} else {
  console.log('[bootstrap] node_modules exists, skipping npm install');
}

// 3. Install Python dependencies (best-effort)
if (existsSync(resolve(ROOT, 'requirements.txt'))) {
  run('pip install -r requirements.txt', { ignoreError: true });
}

// 4. Build TypeScript
run('npm run build');

console.log('\n=== Bootstrap complete ===');
