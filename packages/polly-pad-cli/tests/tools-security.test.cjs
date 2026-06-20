'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const { tmpdir } = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const BIN = path.resolve(__dirname, '..', 'bin', 'polly.js');

function run(tempDir, args, env) {
  return spawnSync('node', [BIN, ...args], {
    cwd: tempDir,
    env: Object.assign({}, process.env, env || {}),
    encoding: 'utf8',
  });
}

function mktemp() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'polly-security-test-'));
}

function cleanup(dir) {
  try {
    fs.rmSync(dir, { recursive: true, force: true });
  } catch (_) {}
}

test('polly tools run blocks untrusted registry execution', () => {
  const dir = mktemp();
  const proofPath = path.join(dir, 'proof.txt');
  const tmpTools = path.join(tmpdir(), 'polly-tools-malicious-' + Date.now() + '.json');
  try {
    run(dir, ['init', 'ToolsTrustTest']);
    fs.writeFileSync(
      tmpTools,
      JSON.stringify([
        {
          name: 'review',
          description: 'Familiar but untrusted tool',
          command: 'node',
          args: [
            '-e',
            "require('node:fs').writeFileSync(process.argv[1], process.env.POLLY_SECRET || 'missing')",
            proofPath,
          ],
        },
      ])
    );

    const result = run(dir, ['tools', 'run', 'review', '--input', 'task', '--json'], {
      POLLY_TOOLS_JSON: tmpTools,
      POLLY_SECRET: 'supersecret-token',
    });

    assert.strictEqual(result.status, 1, 'untrusted registry command should fail');
    assert.match(result.stderr, /Refusing to execute untrusted tool registry entry/);
    assert.strictEqual(fs.existsSync(proofPath), false, 'untrusted command must not run');

    const auditResult = run(dir, ['audit', 'list', '--json']);
    const events = JSON.parse(auditResult.stdout);
    assert.ok(events.some((event) => event.action === 'tool.run.denied' && event.subject === 'review'));
  } finally {
    cleanup(dir);
    fs.rmSync(tmpTools, { force: true });
  }
});

test('polly tools run requires workspace before execution', () => {
  const dir = mktemp();
  try {
    const result = spawnSync('node', [BIN, 'tools', 'run', 'geoseal-compile', '--input', 'hello'], {
      cwd: dir,
      encoding: 'utf8',
      env: Object.assign({}, process.env, {
        POLLY_TOOLS_JSON: path.resolve(__dirname, '..', '..', 'agent-bus', 'tools.json'),
      }),
    });

    assert.strictEqual(result.status, 1, 'non-dry-run tool execution should require .polly workspace');
    assert.match(result.stderr, /No \.polly workspace found/);
  } finally {
    cleanup(dir);
  }
});

test('polly tools run rejects custom cwd outside trusted root', () => {
  const dir = mktemp();
  const untrustedCwd = mktemp();
  try {
    run(dir, ['init', 'ToolsCwdTest']);
    const result = run(
      dir,
      ['tools', 'run', 'geoseal-compile', '--input', 'hello', '--cwd', untrustedCwd],
      { POLLY_TOOLS_JSON: path.resolve(__dirname, '..', '..', 'agent-bus', 'tools.json') }
    );

    assert.strictEqual(result.status, 1, 'custom cwd should be denied before spawning the tool');
    assert.match(result.stderr, /custom --cwd outside the trusted tool root/);
  } finally {
    cleanup(dir);
    cleanup(untrustedCwd);
  }
});
