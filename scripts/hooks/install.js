#!/usr/bin/env node
/**
 * Installs project git hooks from scripts/hooks/ into .git/hooks/.
 * Run via: npm run hooks:install
 * Also runs automatically on: npm install (prepare script)
 */

const fs = require('fs');
const path = require('path');

const HOOKS_SRC = path.join(__dirname);
const HOOKS_DST = path.join(__dirname, '..', '..', '.git', 'hooks');

if (!fs.existsSync(HOOKS_DST)) {
    console.log('[hooks] .git/hooks not found — skipping (not a git repo or hooks dir missing)');
    process.exit(0);
}

const hooks = fs.readdirSync(HOOKS_SRC).filter(
    (f) =>
        !f.endsWith('.js') &&
        !f.endsWith('.md') &&
        fs.statSync(path.join(HOOKS_SRC, f)).isFile() // skip dirs like __pycache__
);

for (const hook of hooks) {
    const src = path.join(HOOKS_SRC, hook);
    const dst = path.join(HOOKS_DST, hook);
    fs.copyFileSync(src, dst);
    fs.chmodSync(dst, 0o755);
    console.log(`[hooks] installed ${hook}`);
}

console.log('[hooks] done');
