#!/usr/bin/env node
/**
 * Installs project git hooks from scripts/hooks/ into .git/hooks/.
 * Run via: npm run hooks:install
 * Also runs automatically on: npm install (prepare script)
 */

// All diagnostics go to STDERR, never stdout. This script runs as npm's `prepare`
// lifecycle hook, and `prepare` fires during `npm pack` -- including, on some npm
// versions, when `--ignore-scripts` was passed. `publish:pack:json` redirects pack's
// stdout into artifacts/npm-pack/pack.json, so a single console.log here corrupts that
// JSON and every `npm publish` dies in npm_pack_guard.js. It did: run 30244227191,
// `SyntaxError: Unexpected token 'h', "[hooks] ins"...`.
const fs = require('fs');
const path = require('path');

const HOOKS_SRC = path.join(__dirname);
const HOOKS_DST = path.join(__dirname, '..', '..', '.git', 'hooks');

if (!fs.existsSync(HOOKS_DST)) {
    console.error('[hooks] .git/hooks not found — skipping (not a git repo or hooks dir missing)');
    process.exit(0);
}

const hooks = fs.readdirSync(HOOKS_SRC).filter((f) => !f.endsWith('.js') && !f.endsWith('.md'));

for (const hook of hooks) {
    const src = path.join(HOOKS_SRC, hook);
    const dst = path.join(HOOKS_DST, hook);
    fs.copyFileSync(src, dst);
    fs.chmodSync(dst, 0o755);
    console.error(`[hooks] installed ${hook}`);
}

console.error('[hooks] done');
