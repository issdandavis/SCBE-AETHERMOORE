'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
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
  return fs.mkdtempSync(path.join(os.tmpdir(), 'polly-test-'));
}

function cleanup(dir) {
  try {
    fs.rmSync(dir, { recursive: true, force: true });
  } catch (_) {}
}

// ---------------------------------------------------------------------------
// Test 1: polly init creates .polly/pad.json
// ---------------------------------------------------------------------------
test('polly init creates .polly/pad.json', () => {
  const dir = mktemp();
  try {
    const result = run(dir, ['init', 'TestPad']);
    assert.strictEqual(result.status, 0, 'exit code should be 0\nstdout: ' + result.stdout + '\nstderr: ' + result.stderr);
    const padPath = path.join(dir, '.polly', 'pad.json');
    assert.ok(fs.existsSync(padPath), '.polly/pad.json should exist');
    const pad = JSON.parse(fs.readFileSync(padPath, 'utf8'));
    assert.strictEqual(pad.name, 'TestPad', 'pad.name should be TestPad');
    assert.strictEqual(pad.schema_version, 'polly_pad_v1', 'schema_version should be polly_pad_v1');
  } finally {
    cleanup(dir);
  }
});

// ---------------------------------------------------------------------------
// Test 2: polly status outputs JSON with --json
// ---------------------------------------------------------------------------
test('polly status outputs JSON with --json', () => {
  const dir = mktemp();
  try {
    const initResult = run(dir, ['init', 'StatusTest']);
    assert.strictEqual(initResult.status, 0, 'init should succeed');

    const statusResult = run(dir, ['status', '--json']);
    assert.strictEqual(statusResult.status, 0, 'status exit code should be 0\nstdout: ' + statusResult.stdout + '\nstderr: ' + statusResult.stderr);
    let parsed;
    assert.doesNotThrow(() => {
      parsed = JSON.parse(statusResult.stdout);
    }, 'status --json output should be valid JSON');
    assert.ok(parsed.schema_version, 'should have schema_version');
    assert.strictEqual(parsed.name, 'StatusTest');
  } finally {
    cleanup(dir);
  }
});

// ---------------------------------------------------------------------------
// Test 3: polly task add then list
// ---------------------------------------------------------------------------
test('polly task add then list', () => {
  const dir = mktemp();
  try {
    run(dir, ['init', 'TaskTest']);
    const addResult = run(dir, ['task', 'add', 'hello', 'world']);
    assert.strictEqual(addResult.status, 0, 'task add should succeed\nstdout: ' + addResult.stdout + '\nstderr: ' + addResult.stderr);

    const statusResult = run(dir, ['status', '--json']);
    assert.strictEqual(statusResult.status, 0, 'status should succeed');
    const pad = JSON.parse(statusResult.stdout);
    assert.ok(Array.isArray(pad.tasks), 'tasks should be an array');
    const task = pad.tasks.find((t) => t.text === 'hello world');
    assert.ok(task, 'should find task with text "hello world"');
    assert.strictEqual(task.state, 'pending');
  } finally {
    cleanup(dir);
  }
});

// ---------------------------------------------------------------------------
// Test 4: polly task done marks completed
// ---------------------------------------------------------------------------
test('polly task done marks completed', () => {
  const dir = mktemp();
  try {
    run(dir, ['init', 'DoneTest']);
    run(dir, ['task', 'add', 'finish this task']);

    // Get the task id
    const statusBefore = run(dir, ['status', '--json']);
    const padBefore = JSON.parse(statusBefore.stdout);
    const taskId = padBefore.tasks[0].id;
    assert.ok(taskId, 'task id should exist');

    const doneResult = run(dir, ['task', 'done', taskId]);
    assert.strictEqual(doneResult.status, 0, 'task done should succeed\nstdout: ' + doneResult.stdout + '\nstderr: ' + doneResult.stderr);

    const statusAfter = run(dir, ['status', '--json']);
    const padAfter = JSON.parse(statusAfter.stdout);
    const task = padAfter.tasks.find((t) => t.id === taskId);
    assert.strictEqual(task.state, 'done', 'task state should be done');
  } finally {
    cleanup(dir);
  }
});

// ---------------------------------------------------------------------------
// Test 5: polly runs returns empty list initially
// ---------------------------------------------------------------------------
test('polly runs returns empty list initially', () => {
  const dir = mktemp();
  try {
    run(dir, ['init', 'RunsTest']);
    const runsResult = run(dir, ['runs', '--json']);
    assert.strictEqual(runsResult.status, 0, 'runs should succeed\nstdout: ' + runsResult.stdout + '\nstderr: ' + runsResult.stderr);
    let parsed;
    assert.doesNotThrow(() => {
      parsed = JSON.parse(runsResult.stdout);
    }, 'runs --json should be valid JSON');
    assert.ok(Array.isArray(parsed), 'runs output should be an array');
    assert.strictEqual(parsed.length, 0, 'runs should be empty initially');
  } finally {
    cleanup(dir);
  }
});

// ---------------------------------------------------------------------------
// Test 6: polly doctor exits 0
// ---------------------------------------------------------------------------
test('polly doctor exits 0', () => {
  const dir = mktemp();
  try {
    const result = run(dir, ['doctor']);
    assert.strictEqual(result.status, 0, 'doctor should exit 0\nstdout: ' + result.stdout + '\nstderr: ' + result.stderr);
  } finally {
    cleanup(dir);
  }
});

// ---------------------------------------------------------------------------
// Test 7: polly --version prints version
// ---------------------------------------------------------------------------
test('polly --version prints version', () => {
  const dir = mktemp();
  try {
    const result = run(dir, ['--version']);
    assert.strictEqual(result.status, 0, '--version should exit 0');
    assert.ok(result.stdout.includes('polly v'), 'output should include "polly v"');
  } finally {
    cleanup(dir);
  }
});

// ---------------------------------------------------------------------------
// Test 8: polly snapshot creates snapshot file
// ---------------------------------------------------------------------------
test('polly snapshot creates snapshot file', () => {
  const dir = mktemp();
  try {
    run(dir, ['init', 'SnapTest']);
    const snapResult = run(dir, ['snapshot']);
    assert.strictEqual(snapResult.status, 0, 'snapshot should exit 0\nstdout: ' + snapResult.stdout + '\nstderr: ' + snapResult.stderr);

    const snapsDir = path.join(dir, '.polly', 'snapshots');
    assert.ok(fs.existsSync(snapsDir), '.polly/snapshots should exist');
    const files = fs.readdirSync(snapsDir).filter((f) => f.endsWith('.json'));
    assert.ok(files.length > 0, 'should have at least one snapshot file');
  } finally {
    cleanup(dir);
  }
});
