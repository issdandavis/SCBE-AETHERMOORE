#!/usr/bin/env node
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const mode = process.argv.includes('--write') ? '--write' : '--check';
const prettierBin = path.resolve('node_modules', 'prettier', 'bin', 'prettier.cjs');
const extensions = /\.(?:ts|tsx|js|jsx|cjs|mjs|json|md|ya?ml)$/i;
const rootCodeExtensions = /\.(?:ts|tsx)$/i;
const excluded = [
  /^artifacts\//,
  /^build\//,
  /^coverage\//,
  /^dist\//,
  /^node_modules\//,
  /^package-lock\.json$/,
];

function isManagedPath(file) {
  if (/^packages\/agent-bus\//.test(file)) return true;
  if (/^scripts\/dev\/run_prettier_tracked\.mjs$/.test(file)) return true;
  if (/^package\.json$/.test(file)) return true;
  if (/^(?:src|tests)\//.test(file)) return rootCodeExtensions.test(file);
  return false;
}

const listed = spawnSync('git', ['ls-files', '-z'], { encoding: 'utf8' });
if (listed.status !== 0) {
  process.stderr.write(listed.stderr || 'git ls-files failed\n');
  process.exit(listed.status ?? 1);
}

const files = listed.stdout
  .split('\0')
  .filter(Boolean)
  .filter((file) => extensions.test(file))
  .map((file) => file.replace(/\\/g, '/'))
  .filter((file) => isManagedPath(file))
  .filter((file) => !excluded.some((pattern) => pattern.test(file)));

if (!fs.existsSync(prettierBin)) {
  process.stderr.write(`Prettier binary not found at ${prettierBin}; run npm install first.\n`);
  process.exit(1);
}

if (files.length === 0) {
  process.stdout.write('No tracked Prettier-managed files found.\n');
  process.exit(0);
}

let exitCode = 0;
const chunkSize = 100;
for (let index = 0; index < files.length; index += chunkSize) {
  const chunk = files.slice(index, index + chunkSize);
  const result = spawnSync(process.execPath, [prettierBin, mode, ...chunk], {
    stdio: 'inherit',
    shell: false,
  });
  if (result.status !== 0) {
    exitCode = result.status ?? 1;
    if (mode === '--check') break;
  }
}

process.exit(exitCode);
