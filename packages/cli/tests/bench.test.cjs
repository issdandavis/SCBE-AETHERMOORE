const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const CLI = path.resolve(__dirname, '..', 'bin', 'scbe.js');

function runCli(args, options = {}) {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-cli-bench-'));
  const env = {
    ...process.env,
    HOME: home,
    USERPROFILE: home,
    NO_COLOR: '1',
  };
  return spawnSync(process.execPath, [CLI, ...args], {
    input: options.input || '',
    encoding: 'utf8',
    timeout: options.timeout || 30_000,
    env,
  });
}

test('help documents benchmark evidence lanes', () => {
  const result = runCli(['--help']);

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /bench hard-agentic/);
  assert.match(result.stdout, /bench research/);
  assert.match(result.stdout, /bench rubix-browser/);
});

test('bench help prints local evidence boundary', () => {
  const result = runCli(['bench', 'help']);

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /local executable evidence lanes/);
});

test('bench rubix-browser forwards to Python fixture and emits JSON', () => {
  const outDir = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-rubix-bench-'));
  const result = runCli(['bench', 'rubix-browser', '--out-dir', outDir, '--json'], { timeout: 60_000 });

  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_rubix_browser_hypercube_benchmark_v1');
  assert.equal(payload.summary.decision, 'PASS');
  assert.equal(payload.summary.baseline_completed, 0);
  assert.equal(payload.summary.hypercube_completed, payload.summary.task_count);
  assert.ok(fs.existsSync(path.join(outDir, 'latest_report.json')));
});
