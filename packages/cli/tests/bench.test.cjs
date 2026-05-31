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

test('bench help prints local evidence boundary', () => {
  const result = runCli(['bench', 'help']);
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /local executable evidence lanes/);
});

test('bench list emits registered evidence lanes as JSON', () => {
  const result = runCli(['bench', 'list', '--json']);
  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_bench_lane_list_v1');
  assert.ok(payload.lanes.some((lane) => lane.id === 'hard-agentic'));
  assert.ok(payload.lanes.some((lane) => lane.id === 'research'));
  assert.ok(payload.lanes.some((lane) => lane.id === 'rubix-browser'));
  assert.ok(payload.lanes.some((lane) => lane.id === 'arc-agi2'));
  assert.ok(payload.lanes.some((lane) => lane.id === 'arc-style-grid'));
  assert.ok(payload.lanes.some((lane) => lane.id === 'longform'));
  assert.ok(payload.lanes.some((lane) => lane.id === 'swe-local'));
  assert.ok(payload.lanes.some((lane) => lane.id === 'cli-competitive'));
});

test('bench list has 10 lanes', () => {
  const result = runCli(['bench', 'list', '--json']);
  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.lanes.length, 10);
  assert.ok(payload.lanes.some((lane) => lane.id === 'providers'));
  assert.ok(payload.lanes.some((lane) => lane.id === 'compound-decompose'));
});

test('bench compound-decompose forwards JSON flag', () => {
  const outDir = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-compound-json-'));
  const result = runCli(['bench', 'compound-decompose', '--out-dir', outDir, '--json'], { timeout: 90_000 });

  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_compound_decomposition_recomposition_v1');
  assert.equal(payload.summary.decision, 'PASS');
  assert.equal(payload.summary.case_count, 30);
});

test('bench list plain text shows artifact status', () => {
  const result = runCli(['bench', 'list']);
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /SCBE benchmark evidence lanes/);
  assert.match(result.stdout, /artifact:/);
});

test('bench status emits compact utility view', () => {
  const result = runCli(['bench', 'status', '--json']);
  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_bench_status_v1');
  assert.ok(payload.evidence_total >= 7);
  assert.ok(Array.isArray(payload.lanes));
});

test('bench latest with no args returns all lanes', () => {
  const result = runCli(['bench', 'latest', '--json']);
  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_bench_latest_v1');
  assert.equal(payload.lanes.length, 10);
});

test('bench prove emits claim-safe proof packet with overclaim check', () => {
  const result = runCli(['bench', 'prove', 'rubix-browser', '--json']);
  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_bench_proof_packet_v1');
  assert.match(payload.proof_rule, /command, artifact, commit, and claim boundary/);
  assert.ok(typeof payload.overclaim_check === 'object');
  assert.ok(typeof payload.overclaim_check.clean === 'boolean');
  assert.ok(Array.isArray(payload.overclaim_check.warnings));
  assert.equal(payload.lanes.length, 1);
  assert.equal(payload.lanes[0].id, 'rubix-browser');
});

test('bench prove all-lanes proof packet has 10 lanes', () => {
  const result = runCli(['bench', 'prove', '--json']);
  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.lanes.length, 10);
});

test('bench prove can write a portable proof packet', () => {
  const outDir = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-bench-proof-'));
  const outPath = path.join(outDir, 'proof.json');
  const result = runCli(['bench', 'prove', 'rubix-browser', '--write', outPath]);
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /wrote /);
  const payload = JSON.parse(fs.readFileSync(outPath, 'utf8'));
  assert.equal(payload.schema_version, 'scbe_bench_proof_packet_v1');
  assert.ok(payload.overclaim_check);
});

test('bench index emits public artifact catalog with commit hash', () => {
  const result = runCli(['bench', 'index', '--json']);
  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_bench_index_v1');
  assert.ok(typeof payload.commit === 'string');
  assert.ok(typeof payload.evidence_ready === 'number');
  assert.equal(payload.evidence_total, 10);
  assert.match(payload.proof_rule, /claim/);
  assert.ok(payload.lanes.every((l) => typeof l.claim_boundary === 'string'));
});

test('bench index can write to a file', () => {
  const outDir = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-bench-index-'));
  const outPath = path.join(outDir, 'INDEX.json');
  const result = runCli(['bench', 'index', '--write', outPath]);
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /wrote /);
  const payload = JSON.parse(fs.readFileSync(outPath, 'utf8'));
  assert.equal(payload.schema_version, 'scbe_bench_index_v1');
});

test('bench index plain text shows commit and lane status', () => {
  const result = runCli(['bench', 'index']);
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /SCBE bench index/);
  assert.match(result.stdout, /evidence:/);
});

test('bench unknown lane exits with code 2', () => {
  const result = runCli(['bench', 'notexist']);
  assert.equal(result.status, 2, result.stdout);
  assert.match(result.stderr, /unknown lane/);
});

test('bench is recognized as known command (no typo suggestion)', () => {
  // bench should not trigger the typo guard
  const result = runCli(['bench', 'list']);
  assert.notEqual(result.status, 2, 'should not trigger typo guard');
  assert.doesNotMatch(result.stderr || '', /Did you mean/);
});
