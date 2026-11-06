#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

function packageRootFromEntry(entry) {
  let current = path.dirname(entry);
  for (let depth = 0; depth < 8; depth += 1) {
    const packageJson = path.join(current, 'package.json');
    try {
      const parsed = JSON.parse(fs.readFileSync(packageJson, 'utf8'));
      if (parsed.name === 'scbe-aethermoore') return current;
    } catch (_error) {
      // Continue walking toward the package root.
    }
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }
  return null;
}

function resolveCoreGeoSeal() {
  try {
    const root = packageRootFromEntry(require.resolve('scbe-aethermoore'));
    const target = root ? path.join(root, 'bin', 'geoseal.cjs') : '';
    if (target && fs.existsSync(target)) return target;
  } catch (_error) {
    // Try the monorepo fallback below.
  }
  const fallback = path.resolve(__dirname, '..', '..', '..', 'bin', 'geoseal.cjs');
  if (fs.existsSync(fallback)) return fallback;
  throw new Error('could not find the scbe-aethermoore GeoSeal executable');
}

const args = process.argv.slice(2);
try {
  const nativeShell = !args.length || (args[0] === 'shell' &&
    !args.some((arg) => arg === '--api-base' || arg.startsWith('--api-base=') || arg === '--command'));
  const target = nativeShell ? path.join(__dirname, 'scbe.js') : resolveCoreGeoSeal();
  const forwarded = nativeShell ? ['shell', '--command-session', ...args.slice(1)] : args;
  const child = spawnSync(process.execPath, [target, ...forwarded], { stdio: 'inherit', windowsHide: true });
  process.exit(typeof child.status === 'number' ? child.status : 1);
} catch (error) {
  process.stderr.write(`geoseal: ${error.message || error}\n`);
  process.exit(1);
}
