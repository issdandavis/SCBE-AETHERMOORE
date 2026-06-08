const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const CLI = path.resolve(__dirname, '..', 'bin', 'scbe.js');
const TASK_CORPUS = path.resolve(__dirname, '..', 'scripts', 'bench_task_corpus.cjs');
const EXPECTED_BENCH_LANES = 12;

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

function runTaskCorpus(args, options = {}) {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-task-corpus-'));
  const env = {
    ...process.env,
    HOME: home,
    USERPROFILE: home,
    NO_COLOR: '1',
    SCBE_PROVIDER: 'offline',
    ...(options.env || {}),
  };
  return spawnSync(process.execPath, [TASK_CORPUS, ...args], {
    encoding: 'utf8',
    timeout: options.timeout || 120_000,
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
  assert.ok(payload.lanes.some((lane) => lane.id === 'kaggle-api'));
});

test('bench list has all registered lanes', () => {
  const result = runCli(['bench', 'list', '--json']);
  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.lanes.length, EXPECTED_BENCH_LANES);
  assert.ok(payload.lanes.some((lane) => lane.id === 'providers'));
  assert.ok(payload.lanes.some((lane) => lane.id === 'compound-decompose'));
});

test('task corpus category filter runs codegen subset', () => {
  const result = runTaskCorpus(['--category', 'codegen', '--max-corpus-turns=8', '--no-artifact']);

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /Tasks: 5\b/);
  assert.match(result.stdout, /codegen-js-clamp-module/);
  assert.match(result.stdout, /codegen-python-prime-coordinate/);
  assert.match(result.stdout, /codegen-js-intent-router/);
  assert.match(result.stdout, /codegen-python-prime-abacus/);
  assert.match(result.stdout, /codegen-python-chunk-worksheet/);
  assert.match(result.stdout, /Summary: 5\/5 tasks completed/);
});

test('task corpus runs a hard codegen repair task', () => {
  const result = runTaskCorpus(
    [
      '--task',
      'codegen-hard-js-safe-shell-filter',
      '--max-corpus-turns=4',
      '--no-artifact',
      '--fail-on-incomplete',
    ],
    { timeout: 120_000 }
  );

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /codegen-hard-js-safe-shell-filter/);
  assert.match(result.stdout, /Summary: 1\/1 tasks completed/);
});

test('task corpus can fail when selected tasks do not verify', () => {
  const result = runTaskCorpus(
    [
      '--task',
      'run-freshness-tests',
      '--max-corpus-turns=1',
      '--no-artifact',
      '--fail-on-incomplete',
    ],
    {
      env: {
        SCBE_PROVIDER: 'ollama',
        SCBE_URL: 'http://127.0.0.1:9',
        SCBE_DISABLE_AGENT_JSON_FALLBACK: '1',
      },
    }
  );

  assert.equal(result.status, 1, result.stdout);
  assert.match(result.stdout, /Summary: 0\/1 tasks completed/);
});

test('bench compound-decompose forwards JSON flag', () => {
  const outDir = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-compound-json-'));
  const result = runCli(['bench', 'compound-decompose', '--out-dir', outDir, '--json'], {
    timeout: 90_000,
  });

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

test('tourney emits local/public benchmark circuit as JSON', () => {
  const result = runCli(['tourney', '--json']);
  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_cli_tourney_v1');
  assert.ok(payload.local_evidence.ready_lanes >= 0);
  assert.ok(payload.local_evidence.private_scores.some((score) => score.id === 'cli-competitive'));
  assert.ok(payload.public_targets.some((target) => target.id === 'terminal-bench-2'));
  assert.match(payload.claim_boundary, /Public claims require/);
});

test('tourney plain output shows scorecards and next routes', () => {
  const result = runCli(['tourney']);
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /SCBE CLI tourney board/);
  assert.match(result.stdout, /Private\/local scorecards:/);
  assert.match(result.stdout, /Public arenas:/);
  assert.match(result.stdout, /Next routes:/);
});

test('bench latest with no args returns all lanes', () => {
  const result = runCli(['bench', 'latest', '--json']);
  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_bench_latest_v1');
  assert.equal(payload.lanes.length, EXPECTED_BENCH_LANES);
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

test('bench prove all-lanes proof packet has all registered lanes', () => {
  const result = runCli(['bench', 'prove', '--json']);
  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.lanes.length, EXPECTED_BENCH_LANES);
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
  assert.equal(payload.evidence_total, EXPECTED_BENCH_LANES);
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

test('bench dashboard emits website-ready JSON summary', () => {
  const result = runCli(['bench', 'dashboard', '--json']);
  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_bench_dashboard_v1');
  assert.equal(payload.evidence_total, EXPECTED_BENCH_LANES);
  assert.ok(payload.summary.website_claim_boundary.includes('command'));
  assert.ok(payload.lanes.every((lane) => typeof lane.claim_boundary === 'string'));
  assert.ok(
    payload.lanes.every((lane) => ['evidence-ready', 'missing-artifact'].includes(lane.status))
  );
});

test('bench dashboard can write HTML artifact', () => {
  const outDir = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-bench-dashboard-'));
  const outPath = path.join(outDir, 'dashboard.html');
  const result = runCli(['bench', 'dashboard', '--write', outPath]);
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /wrote /);
  const html = fs.readFileSync(outPath, 'utf8');
  assert.match(html, /SCBE Benchmark Evidence Dashboard/);
  assert.match(html, /Proof rule/);
  assert.match(html, /<table>/);
});

test('bench dashboard can write JSON artifact and still print JSON', () => {
  const outDir = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-bench-dashboard-json-'));
  const outPath = path.join(outDir, 'dashboard.json');
  const result = runCli(['bench', 'dashboard', '--json', '--write', outPath]);
  assert.equal(result.status, 0, result.stderr);
  const stdoutPayload = JSON.parse(result.stdout);
  const filePayload = JSON.parse(fs.readFileSync(outPath, 'utf8'));
  assert.equal(stdoutPayload.schema_version, 'scbe_bench_dashboard_v1');
  assert.equal(filePayload.schema_version, 'scbe_bench_dashboard_v1');
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
