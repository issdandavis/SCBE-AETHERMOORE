#!/usr/bin/env node
'use strict';

const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const repoRoot = path.resolve(__dirname, '..');
const outputDir = path.join(repoRoot, 'artifacts', 'npm-pack');
const outputPath = path.join(outputDir, 'pack.json');
const cacheDir = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-npm-pack-cache-'));
const npmCli =
  process.env.npm_execpath ||
  path.join(path.dirname(process.execPath), 'node_modules', 'npm', 'bin', 'npm-cli.js');

try {
  fs.mkdirSync(outputDir, { recursive: true });
  const result = spawnSync(
    process.execPath,
    [npmCli, 'pack', '--dry-run', '--json', '--ignore-scripts', '--cache', cacheDir],
    {
      cwd: repoRoot,
      encoding: 'utf8',
      windowsHide: true,
      timeout: 300000,
    }
  );
  if (result.status !== 0) {
    process.stderr.write(
      result.stderr || result.stdout || String(result.error || 'npm pack failed')
    );
    process.exitCode = result.status || 1;
  } else {
    const receipt = JSON.parse(result.stdout);
    fs.writeFileSync(outputPath, `${JSON.stringify(receipt, null, 2)}\n`, 'utf8');
    process.stdout.write(`${outputPath}\n`);
  }
} finally {
  fs.rmSync(cacheDir, { recursive: true, force: true });
}
