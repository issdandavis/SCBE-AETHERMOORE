'use strict';

const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const CLI = path.resolve(__dirname, '..', 'bin', 'scbe.js');

function runCli(args, options = {}) {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-cli-actions-'));
  const env = {
    ...process.env,
    HOME: home,
    USERPROFILE: home,
    NO_COLOR: '1',
    ...(options.env || {}),
  };
  const result = spawnSync(process.execPath, [CLI, ...args], {
    input: options.input || '',
    encoding: 'utf8',
    timeout: options.timeout || 30_000,
    env,
  });
  fs.rmSync(home, { recursive: true, force: true });
  return result;
}

test('actions --json lists true runnable bundles', () => {
  const result = runCli(['actions', '--json']);

  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_action_catalog_v1');
  assert.ok(payload.count >= 10);
  assert.ok(payload.actions.some((entry) => entry.id === 'terminal.panel'));
  assert.ok(payload.actions.some((entry) => entry.id === 'desktop.open'));
  assert.ok(payload.actions.every((entry) => entry.command));
});

test('action dry-run emits exact command without executing it', () => {
  const result = runCli(['action', 'desktop.open', '--dry-run', '--json']);

  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_action_result_v1');
  assert.equal(payload.action_id, 'desktop.open');
  assert.equal(payload.dry_run, true);
  assert.equal(payload.success, true);
  assert.equal(payload.command, 'scbe desktop open');
});

test('action alias resolves to the same bundle', () => {
  const result = runCli(['action', 'polly-status', '--dry-run', '--json']);

  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.action_id, 'desktop.status');
  assert.equal(payload.command, 'scbe desktop --json');
});

test('action can run a governed receipt smoke', () => {
  const result = runCli(['action', 'receipt.node-version', '--json'], { timeout: 45_000 });

  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_action_result_v1');
  assert.equal(payload.action_id, 'receipt.node-version');
  assert.equal(payload.success, true);
  assert.match(payload.stdout_preview, /scbe_terminal_run_v1/);
  assert.match(payload.stdout_preview, /node --version/);
});

test('unknown action returns a structured failure', () => {
  const result = runCli(['action', 'not.real', '--json']);

  assert.equal(result.status, 2);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_action_result_v1');
  assert.equal(payload.success, false);
  assert.equal(payload.error, 'unknown action bundle');
  assert.ok(payload.known_actions.includes('desktop.open'));
});
