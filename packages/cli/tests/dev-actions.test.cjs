'use strict';

const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const CLI = path.resolve(__dirname, '..', 'bin', 'scbe.js');

function runCli(args, options = {}) {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-dev-actions-home-'));
  const receiptDir = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-dev-actions-receipts-'));
  const env = {
    ...process.env,
    HOME: home,
    USERPROFILE: home,
    NO_COLOR: '1',
    SCBE_DEV_ACTION_DIR: receiptDir,
    ...(options.env || {}),
  };
  const result = spawnSync(process.execPath, [CLI, ...args], {
    cwd: path.resolve(__dirname, '..', '..', '..'),
    encoding: 'utf8',
    timeout: options.timeout || 120_000,
    env,
  });
  fs.rmSync(home, { recursive: true, force: true });
  fs.rmSync(receiptDir, { recursive: true, force: true });
  return result;
}

test('prepush dry-run emits governed action receipt', () => {
  const result = runCli(['prepush', '--dry-run', '--json', '--no-write'], {
    env: { SCBE_DEV_ACTION_FAST_GATE: '1' },
  });

  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_dev_action_receipt_v1');
  assert.equal(payload.action, 'prepush');
  assert.equal(payload.dry_run, true);
  assert.equal(payload.semantic_prime_syntax.action_coordinate.prime, 13);
  assert.equal(payload.semantic_prime_syntax.geoseal_coordinate.prime, 11);
  assert.equal(payload.summary.total_steps, 5);
  assert.equal(payload.summary.planned, 5);
  assert.equal(payload.summary.blocked, 0);
  assert.ok(payload.receipt_sha256);
  assert.ok(payload.steps.every((step) => step.geoseal));
  assert.ok(payload.steps.every((step) => step.geoseal.fast_gate));
  assert.ok(payload.steps.some((step) => step.id === 'desktop-capability-bench'));
});

test('format dry-run plans prettier without touching the workspace', () => {
  const result = runCli(['format', '--dry-run', '--json', '--no-write']);

  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.action, 'format');
  assert.equal(payload.summary.planned, 1);
  assert.match(payload.steps[0].command, /prettier --write/);
  assert.equal(payload.steps[0].semantic_operation.anchor_prime, 3);
  assert.equal(payload.steps[0].geoseal.allowed, true);
  assert.ok(payload.steps[0].geoseal.tier);
  assert.notEqual(payload.steps[0].geoseal.fast_gate, true);
});

test('push dry-run includes prepush gate before git push', () => {
  const result = runCli(
    ['push', '--dry-run', '--json', '--no-write', '--branch', 'feat/cli-ui-kit'],
    { env: { SCBE_DEV_ACTION_FAST_GATE: '1' } }
  );

  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.action, 'push');
  assert.equal(payload.dry_run, true);
  assert.equal(payload.steps.at(-1).id, 'git-push');
  assert.match(payload.steps.at(-1).command, /git push origin/);
  assert.ok(payload.steps.find((step) => step.id === 'diff-check'));
  assert.ok(payload.steps.find((step) => step.id === 'cli-tests'));
});

test('commit dry-run requires a message', () => {
  const result = runCli(['commit', '--dry-run', '--json', '--no-write']);

  assert.equal(result.status, 2);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_dev_action_error_v1');
  assert.match(payload.error, /commit requires a message/);
});
