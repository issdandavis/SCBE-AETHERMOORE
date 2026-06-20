/**
 * Edge-case tests for shell_benchmark.cjs --last-artifact mode.
 *
 * Covers: missing/empty/corrupted dirs, score enforcement, stale-commit gate,
 * --allow-stale bypass, legacy artifacts without a commit field, multi-file
 * selection, and empty-bench authority disambiguation.
 *
 * Run with: node --test packages/cli/tests/bench_artifact_freshness.test.cjs
 * Or via:   npm test  (from packages/cli)
 */
'use strict';

const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const { test } = require('node:test');

const BENCH = path.resolve(__dirname, '..', 'scripts', 'shell_benchmark.cjs');
const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');

// ── helpers ───────────────────────────────────────────────────────────────────

function getHeadCommit() {
  return spawnSync('git', ['rev-parse', '--short', 'HEAD'], {
    cwd: REPO_ROOT,
    encoding: 'utf8',
  }).stdout.trim();
}

function run(extraArgs) {
  return spawnSync(process.execPath, [BENCH, '--last-artifact', ...extraArgs], {
    cwd: REPO_ROOT,
    encoding: 'utf8',
  });
}

function writeArtifact(dir, name, content) {
  fs.writeFileSync(path.join(dir, name), JSON.stringify(content));
}

function withTmp(fn) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-bench-test-'));
  try {
    return fn(dir);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

const HEAD = getHeadCommit();
// Guarantee a value different from HEAD by flipping the first hex character.
const STALE = HEAD.length
  ? HEAD[0] === 'a'
    ? 'b' + HEAD.slice(1)
    : 'a' + HEAD.slice(1)
  : 'aaaaaaa';

function freshArtifact(overrides) {
  return Object.assign(
    {
      schema: 'bench/v1',
      generated_at: '2026-05-26T00:00:00Z',
      commit: HEAD,
      score: { earned: 26, total: 26, percent: 100 },
      ready: true,
    },
    overrides
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

test('no artifact dir → exit 1, stderr "No bench artifacts found", stdout empty', () => {
  const dir = path.join(os.tmpdir(), `scbe-bench-nonexistent-${Date.now()}`);
  const r = run([`--artifact-dir=${dir}`]);
  assert.equal(r.status, 1, 'exit code');
  assert.ok(r.stderr.includes('No bench artifacts found'), `stderr: ${r.stderr}`);
  assert.equal(r.stdout, '', 'stdout must be empty');
});

test('empty artifact dir (dir exists, no .json files) → exit 1', () => {
  withTmp((dir) => {
    fs.writeFileSync(path.join(dir, 'readme.txt'), 'not a json');
    const r = run([`--artifact-dir=${dir}`]);
    assert.equal(r.status, 1, 'exit code');
    assert.ok(r.stderr.includes('No bench artifacts found'), `stderr: ${r.stderr}`);
    assert.equal(r.stdout, '', 'stdout must be empty');
  });
});

test('corrupted JSON → exit 1, stderr "Corrupted artifact"', () => {
  withTmp((dir) => {
    fs.writeFileSync(path.join(dir, '2026-05-26T00-00-00Z.json'), '{not valid json at all');
    const r = run([`--artifact-dir=${dir}`]);
    assert.equal(r.status, 1, 'exit code');
    assert.ok(r.stderr.includes('Corrupted artifact'), `stderr: ${r.stderr}`);
    assert.equal(r.stdout, '', 'stdout must be empty on parse error');
  });
});

test('fresh artifact, 100% → exit 0, score on stdout, stderr empty', () => {
  withTmp((dir) => {
    writeArtifact(dir, '2026-05-26T00-00-00Z.json', freshArtifact());
    const r = run([`--artifact-dir=${dir}`]);
    assert.equal(r.status, 0, `exit code (stderr: ${r.stderr})`);
    assert.ok(r.stdout.includes('26/26'), `stdout: ${r.stdout}`);
    assert.ok(r.stdout.includes('100%'), `stdout: ${r.stdout}`);
    assert.equal(r.stderr, '', 'stderr must be empty on clean pass');
  });
});

test('fresh artifact, 96% → exit 1, score on stdout', () => {
  withTmp((dir) => {
    writeArtifact(
      dir,
      '2026-05-26T00-00-00Z.json',
      freshArtifact({ score: { earned: 25, total: 26, percent: 96 }, ready: false })
    );
    const r = run([`--artifact-dir=${dir}`]);
    assert.equal(r.status, 1, 'exit code');
    assert.ok(r.stdout.includes('25/26'), `stdout: ${r.stdout}`);
    assert.ok(r.stdout.includes('96%'), `stdout: ${r.stdout}`);
  });
});

// Authority is percent === 100, NOT ready. ready:true must not override a 0% score.
test('empty-bench (0/0, ready:true) → exit 1 — authority is percent, not ready', () => {
  withTmp((dir) => {
    writeArtifact(
      dir,
      '2026-05-26T00-00-00Z.json',
      freshArtifact({ score: { earned: 0, total: 0, percent: 0 }, ready: true })
    );
    const r = run([`--artifact-dir=${dir}`]);
    assert.equal(r.status, 1, 'exit code — ready:true must not override percent check');
    assert.ok(r.stdout.includes('0/0'), `stdout: ${r.stdout}`);
  });
});

test('artifact missing score field → defaults to 0%, exit 1', () => {
  withTmp((dir) => {
    writeArtifact(dir, '2026-05-26T00-00-00Z.json', {
      schema: 'bench/v1',
      generated_at: '2026-05-26T00:00:00Z',
      commit: HEAD,
    });
    const r = run([`--artifact-dir=${dir}`]);
    assert.equal(r.status, 1, 'exit code');
    assert.ok(r.stdout.includes('0/0'), `stdout: ${r.stdout}`);
  });
});

test('stale artifact → exit 1, stale on stderr, stdout must be empty', () => {
  withTmp((dir) => {
    writeArtifact(dir, '2026-05-26T00-00-00Z.json', freshArtifact({ commit: STALE }));
    const r = run([`--artifact-dir=${dir}`]);
    if (!HEAD) return; // git unavailable — stale check would be skipped; skip assertion
    assert.equal(r.status, 1, 'exit code');
    assert.ok(r.stderr.includes('Stale artifact'), `stderr: ${r.stderr}`);
    assert.ok(r.stderr.includes(STALE), `stderr contains artifact commit: ${r.stderr}`);
    assert.equal(r.stdout, '', 'stdout must be empty when stale');
  });
});

test('--allow-stale + stale commit + 100% → exit 0', () => {
  withTmp((dir) => {
    writeArtifact(dir, '2026-05-26T00-00-00Z.json', freshArtifact({ commit: STALE }));
    const r = run(['--allow-stale', `--artifact-dir=${dir}`]);
    assert.equal(r.status, 0, `exit code (stderr: ${r.stderr}, stdout: ${r.stdout})`);
    assert.ok(r.stdout.includes('26/26'), `stdout: ${r.stdout}`);
  });
});

test('--allow-stale + stale commit + 90% → exit 1 (score still enforced)', () => {
  withTmp((dir) => {
    writeArtifact(
      dir,
      '2026-05-26T00-00-00Z.json',
      freshArtifact({ commit: STALE, score: { earned: 23, total: 26, percent: 90 }, ready: false })
    );
    const r = run(['--allow-stale', `--artifact-dir=${dir}`]);
    assert.equal(r.status, 1, 'exit code');
    assert.ok(r.stdout.includes('23/26'), `stdout: ${r.stdout}`);
  });
});

// Artifact with no commit field: the condition `headCommit && artifactCommit` is false
// because artifactCommit resolves to ''. Freshness check must be skipped, not treated as stale.
test('no commit field in artifact → freshness check skipped, score decides', () => {
  withTmp((dir) => {
    writeArtifact(dir, '2026-05-26T00-00-00Z.json', {
      schema: 'bench/v1',
      generated_at: '2026-05-26T00:00:00Z',
      score: { earned: 26, total: 26, percent: 100 },
      ready: true,
    });
    const r = run([`--artifact-dir=${dir}`]);
    assert.equal(r.status, 0, `exit code — missing commit must not be treated as stale (stderr: ${r.stderr})`);
    assert.ok(r.stdout.includes('unknown'), `stdout should say 'unknown': ${r.stdout}`);
    assert.ok(!r.stderr.includes('Stale artifact'), `no stale message: ${r.stderr}`);
  });
});

test('empty-string commit field → freshness check skipped', () => {
  withTmp((dir) => {
    writeArtifact(dir, '2026-05-26T00-00-00Z.json', freshArtifact({ commit: '' }));
    const r = run([`--artifact-dir=${dir}`]);
    assert.equal(r.status, 0, `exit code (stderr: ${r.stderr})`);
    assert.ok(!r.stderr.includes('Stale artifact'), `no stale message: ${r.stderr}`);
  });
});

test('multiple artifacts in dir → alphabetically last (most recent) selected', () => {
  withTmp((dir) => {
    writeArtifact(
      dir,
      '2026-05-24T00-00-00Z.json',
      freshArtifact({ generated_at: '2026-05-24T00:00:00Z', score: { earned: 0, total: 26, percent: 0 }, ready: false })
    );
    writeArtifact(
      dir,
      '2026-05-25T00-00-00Z.json',
      freshArtifact({ generated_at: '2026-05-25T00:00:00Z', score: { earned: 13, total: 26, percent: 50 }, ready: false })
    );
    writeArtifact(
      dir,
      '2026-05-26T00-00-00Z.json',
      freshArtifact({ generated_at: '2026-05-26T00:00:00Z', score: { earned: 26, total: 26, percent: 100 }, ready: true })
    );
    const r = run([`--artifact-dir=${dir}`]);
    assert.equal(r.status, 0, `exit code (stdout: ${r.stdout})`);
    assert.ok(r.stdout.includes('26/26'), `picks newest artifact: ${r.stdout}`);
    assert.ok(!r.stdout.includes('0/26'), `must not pick oldest artifact: ${r.stdout}`);
  });
});

test('non-.json files in dir are ignored', () => {
  withTmp((dir) => {
    fs.writeFileSync(path.join(dir, 'bench-result.txt'), '{"score":{"percent":100}}');
    const r = run([`--artifact-dir=${dir}`]);
    assert.equal(r.status, 1, 'exit code');
    assert.ok(r.stderr.includes('No bench artifacts found'), `stderr: ${r.stderr}`);
  });
});

test('score line format includes earned/total, %, generated_at, commit token', () => {
  withTmp((dir) => {
    writeArtifact(
      dir,
      '2026-05-26T00-00-00Z.json',
      freshArtifact({ generated_at: '2026-05-26T12:34:56Z', commit: HEAD || 'abc1234' })
    );
    const r = run([`--artifact-dir=${dir}`]);
    assert.equal(r.status, 0, `exit code (stderr: ${r.stderr})`);
    assert.ok(r.stdout.includes('26/26'), `earned/total: ${r.stdout}`);
    assert.ok(r.stdout.includes('100%'), `percent: ${r.stdout}`);
    assert.ok(r.stdout.includes('2026-05-26T12:34:56Z'), `generated_at: ${r.stdout}`);
    assert.ok(r.stdout.includes('commit'), `commit token: ${r.stdout}`);
  });
});
