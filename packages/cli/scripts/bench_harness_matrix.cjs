#!/usr/bin/env node
/**
 * bench_harness_matrix.cjs — compare SCBE agent harness modes.
 *
 * This is a control harness, not a leaderboard. It records what the scaffold,
 * missing-model path, and optional live model path do under the same repo state.
 */

'use strict';

const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');
const ARTIFACT_DIR = path.join(REPO_ROOT, 'artifacts', 'benchmarks', 'scbe-harness-matrix');

function runNode(script, args = [], env = {}, timeoutMs = 180000) {
  const started = Date.now();
  const r = spawnSync(process.execPath, [script, ...args], {
    cwd: REPO_ROOT,
    encoding: 'utf8',
    timeout: timeoutMs,
    env: { ...process.env, NO_COLOR: '1', ...env },
    maxBuffer: 1024 * 1024 * 16,
  });
  return {
    status: r.status ?? 1,
    ok: r.status === 0,
    duration_ms: Date.now() - started,
    stdout: r.stdout || '',
    stderr: r.stderr || '',
    error: r.error ? r.error.message : null,
  };
}

function latestJson(dir) {
  if (!fs.existsSync(dir)) return null;
  const files = fs
    .readdirSync(dir)
    .filter((f) => f.endsWith('.json'))
    .map((f) => path.join(dir, f))
    .sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);
  if (!files[0]) return null;
  try {
    return { path: files[0], data: JSON.parse(fs.readFileSync(files[0], 'utf8')) };
  } catch {
    return { path: files[0], data: null };
  }
}

function corpusSummary(run) {
  const artifact = latestJson(path.join(REPO_ROOT, 'artifacts', 'benchmarks', 'scbe-task-corpus'));
  const score = artifact?.data?.score || artifact?.data?.summary || null;
  return {
    ok: run.ok,
    exit_code: run.status,
    completed: score?.completed ?? null,
    total: score?.total ?? null,
    completion_rate: score?.completion_rate ?? null,
    artifact: artifact?.path || null,
    stderr_tail: run.stderr.slice(-500),
  };
}

function shellSummary(run) {
  const artifact = latestJson(path.join(REPO_ROOT, 'artifacts', 'benchmarks', 'scbe-shell'));
  const score = artifact?.data?.score || null;
  return {
    ok: run.ok,
    exit_code: run.status,
    earned: score?.earned ?? null,
    total: score?.total ?? null,
    percent: score?.percent ?? null,
    artifact: artifact?.path || null,
    stderr_tail: run.stderr.slice(-500),
  };
}

function printRow(name, summary) {
  const score =
    summary.percent != null
      ? `${summary.earned}/${summary.total} (${summary.percent}%)`
      : summary.total
        ? `${summary.completed}/${summary.total}`
        : summary.ok
          ? 'ok'
          : 'failed';
  console.log(`${name.padEnd(34)} ${String(summary.exit_code).padEnd(5)} ${score}`);
}

function main() {
  const shellBench = path.join('packages', 'cli', 'scripts', 'shell_benchmark.cjs');
  const corpusBench = path.join('packages', 'cli', 'scripts', 'bench_task_corpus.cjs');
  const generatedAt = new Date().toISOString();

  const results = [];

  console.log('SCBE harness benchmark matrix\n');

  const protocol = runNode(shellBench, [], {}, 180000);
  results.push({
    name: 'protocol_harness',
    description: 'model-independent agent-json protocol checks',
    ...shellSummary(protocol),
  });

  const offlineCorpus = runNode(
    corpusBench,
    ['--max-corpus-turns=40'],
    { SCBE_PROVIDER: 'offline' },
    180000
  );
  results.push({
    name: 'offline_scaffold_corpus',
    description: 'deterministic scaffold path for missing or tiny models',
    ...corpusSummary(offlineCorpus),
  });

  const noFallback = runNode(
    corpusBench,
    ['--task', 'run-freshness-tests', '--max-corpus-turns=2', '--no-artifact'],
    {
      SCBE_PROVIDER: 'ollama',
      SCBE_URL: 'http://127.0.0.1:9',
      SCBE_DISABLE_AGENT_JSON_FALLBACK: '1',
    },
    60000
  );
  results.push({
    name: 'missing_model_no_fallback_control',
    description: 'negative control: unreachable model with fallback disabled should fail',
    ok:
      !noFallback.ok ||
      /agent error|fetch failed|ECONNREFUSED/i.test(noFallback.stdout + noFallback.stderr),
    exit_code: noFallback.status,
    expected_failure: true,
    stdout_tail: noFallback.stdout.slice(-500),
    stderr_tail: noFallback.stderr.slice(-500),
  });

  if (process.env.SCBE_RUN_LIVE_BENCH === '1') {
    const live = runNode(corpusBench, ['--max-corpus-turns=40'], {}, 300000);
    results.push({
      name: 'live_provider_corpus',
      description: 'live provider from current SCBE_PROVIDER/SCBE_MODEL config',
      ...corpusSummary(live),
    });
  }

  console.log('mode                               exit  score');
  console.log('─'.repeat(56));
  for (const result of results) printRow(result.name, result);

  const payload = {
    schema: 'scbe_harness_benchmark_matrix_v1',
    generated_at: generatedAt,
    branch: spawnSync('git', ['branch', '--show-current'], {
      cwd: REPO_ROOT,
      encoding: 'utf8',
    }).stdout.trim(),
    commit: spawnSync('git', ['rev-parse', '--short', 'HEAD'], {
      cwd: REPO_ROOT,
      encoding: 'utf8',
    }).stdout.trim(),
    live_provider_included: process.env.SCBE_RUN_LIVE_BENCH === '1',
    results,
  };

  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
  const out = path.join(ARTIFACT_DIR, `${generatedAt.replace(/[:.]/g, '-')}-harness-matrix.json`);
  fs.writeFileSync(out, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
  console.log(`\nartifact: ${out}`);

  const failedRequired = results.some(
    (r) => r.name !== 'missing_model_no_fallback_control' && !r.ok
  );
  process.exit(failedRequired ? 1 : 0);
}

main();
