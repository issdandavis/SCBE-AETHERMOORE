#!/usr/bin/env node

const { spawnSync } = require('node:child_process');
const path = require('node:path');

const repoRoot = path.resolve(__dirname, '..');
const cliPath = path.join(repoRoot, 'scripts', 'scbe-system-cli.py');
const python = process.env.SCBE_PYTHON || process.env.PYTHON || 'python';

const result = spawnSync(python, [cliPath, '--repo-root', repoRoot, ...process.argv.slice(2)], {
  cwd: repoRoot,
  stdio: 'inherit',
});

if (result.error) {
  console.error(`[scbe-system] failed to launch Python CLI: ${result.error.message}`);
  process.exit(1);
}

process.exit(result.status ?? 0);
