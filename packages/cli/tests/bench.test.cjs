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
  assert.match(result.stdout, /bench terminal-adapter/);
  assert.match(result.stdout, /bench chemistry/);
  assert.match(result.stdout, /bench compound-decompose/);
  assert.match(result.stdout, /bench full/);
  assert.match(result.stdout, /bench circuit/);
  assert.match(result.stdout, /bench list/);
  assert.match(result.stdout, /bench status/);
  assert.match(result.stdout, /bench latest/);
  assert.match(result.stdout, /bench prove/);
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

test('bench list emits registered evidence lanes as JSON', () => {
  const result = runCli(['bench', 'list', '--json']);

  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_bench_lane_list_v1');
  assert.ok(payload.lanes.some((lane) => lane.id === 'hard-agentic'));
  assert.ok(payload.lanes.some((lane) => lane.id === 'research'));
  assert.ok(payload.lanes.some((lane) => lane.id === 'rubix-browser'));
  assert.ok(payload.lanes.some((lane) => lane.id === 'terminal-adapter'));
  assert.ok(payload.lanes.some((lane) => lane.id === 'chemistry'));
  assert.ok(payload.lanes.some((lane) => lane.id === 'compound-decompose'));
  assert.ok(payload.lanes.some((lane) => lane.id === 'full'));
  assert.ok(payload.lanes.some((lane) => lane.id === 'circuit'));
});

test('bench latest reads latest lane artifact summary', () => {
  const outDir = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-rubix-latest-'));
  const warmup = runCli(['bench', 'rubix-browser', '--out-dir', outDir, '--json'], { timeout: 60_000 });
  assert.equal(warmup.status, 0, warmup.stderr);

  const result = runCli(['bench', 'latest', 'rubix-browser', '--json']);
  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_bench_latest_v1');
  assert.equal(payload.lanes.length, 1);
  assert.equal(payload.lanes[0].id, 'rubix-browser');
  assert.equal(payload.lanes[0].report.schema_version, 'scbe_rubix_browser_hypercube_benchmark_v1');
});

test('bench status emits compact utility view', () => {
  const result = runCli(['bench', 'status', '--json']);

  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_bench_status_v1');
  assert.ok(payload.evidence_total >= 3);
  assert.ok(Array.isArray(payload.lanes));
  assert.ok(payload.lanes.some((lane) => lane.id === 'rubix-browser'));
});

test('bench prove emits claim-safe proof packet', () => {
  const result = runCli(['bench', 'prove', 'rubix-browser', '--json']);

  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_bench_proof_packet_v1');
  assert.match(payload.proof_rule, /command, artifact, commit, and claim boundary/);
  assert.equal(payload.lanes.length, 1);
  assert.equal(payload.lanes[0].id, 'rubix-browser');
  assert.match(payload.lanes[0].claim_boundary, /not WebArena/);
});

test('bench prove can write a portable proof packet', () => {
  const outDir = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-bench-proof-'));
  const outPath = path.join(outDir, 'proof.json');
  const result = runCli(['bench', 'prove', 'rubix-browser', '--write', outPath]);

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /wrote /);
  const payload = JSON.parse(fs.readFileSync(outPath, 'utf8'));
  assert.equal(payload.schema_version, 'scbe_bench_proof_packet_v1');
  assert.equal(payload.lanes[0].id, 'rubix-browser');
});
