#!/usr/bin/env node

const { spawnSync } = require('node:child_process');
const crypto = require('node:crypto');
const path = require('node:path');

const pkgRoot = path.resolve(__dirname, '..');

const BENCHMARKS = [
  {
    id: 'roll-stack-maze',
    command: ['node', ['scripts/bench_roll_stack_maze.cjs']],
    summary(report) {
      return {
        evidence_passed: report.summary.passed,
        evidence_failed: report.summary.failed,
        primary_score: report.summary.passed / report.summary.case_count,
        p95_ms: report.summary.p95_ms,
      };
    },
  },
  {
    id: 'worm-environment-adapter',
    command: ['node', ['scripts/bench_worm_environment_adapter.cjs']],
    summary(report) {
      return {
        evidence_passed: report.summary.evidence_passed,
        evidence_failed: report.summary.evidence_failed,
        primary_score: report.summary.worm_advantage_cases / report.summary.case_count,
        solved_rate: report.summary.worm_solved / report.summary.case_count,
        p95_ms: report.summary.p95_ms,
      };
    },
  },
  {
    id: 'projection-board',
    command: ['node', ['scripts/bench_projection_board_pathfinding.cjs']],
    summary(report) {
      return {
        evidence_passed: report.summary.evidence_passed,
        evidence_failed: report.summary.evidence_failed,
        primary_score: report.summary.projection_advantage_cases / report.summary.case_count,
        solved_rate: report.summary.projection_solved / report.summary.case_count,
        p95_ms: report.summary.p95_ms,
      };
    },
  },
  {
    id: 'vector-field-nav',
    command: ['node', ['scripts/vector_field_bench.cjs', '--skip-ablation']],
    summary(report) {
      return {
        evidence_passed: report.runs.filter((run) => run.receipt_completeness === 1).length,
        evidence_failed: report.runs.filter((run) => run.receipt_completeness !== 1).length,
        primary_score: report.summary.ensemble_beam_solve_rate,
        solved_rate: report.summary.ensemble_beam_solve_rate,
        multi_lattice_baseline_solve_rate: report.summary.multi_lattice_solve_rate,
        ensemble_beam_solve_rate: report.summary.ensemble_beam_solve_rate,
        ensemble_beam_avg_efficiency: report.summary.ensemble_beam_avg_efficiency,
        random_solve_rate: report.summary.random_solve_rate,
        p95_ms: Math.max(...report.runs.map((run) => run.total_ms || 0)),
      };
    },
  },
];

function sha256(value) {
  return crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex');
}

function runBenchmark(spec) {
  const [cmd, args] = spec.command;
  const started = Date.now();
  const result = spawnSync(cmd, args, {
    cwd: pkgRoot,
    encoding: 'utf8',
    maxBuffer: 1024 * 1024 * 16,
  });
  const durationMs = Date.now() - started;
  let report = null;
  let parseError = null;
  try {
    report = JSON.parse(result.stdout);
  } catch (error) {
    parseError = error instanceof Error ? error.message : String(error);
  }
  const ok = result.status === 0 && report !== null;
  return {
    id: spec.id,
    ok,
    exit_code: result.status,
    duration_ms: durationMs,
    stderr_tail: result.stderr.slice(-1200),
    parse_error: parseError,
    summary: report ? spec.summary(report) : null,
    schema_version: report?.schema_version || null,
    receipt_hash: sha256({
      id: spec.id,
      exit_code: result.status,
      stdout: result.stdout,
      stderr_tail: result.stderr.slice(-1200),
    }),
  };
}

function main() {
  const results = BENCHMARKS.map(runBenchmark);
  const evidenceFailed = results.reduce(
    (total, result) => total + (result.summary?.evidence_failed ?? 1),
    0
  );
  const report = {
    schema_version: 'scbe.agent_bus.pathfinding_suite_benchmark.v1',
    generated_at: new Date().toISOString(),
    suite: 'roll-stack + worm environmental adapter + projection board + vector field nav',
    benchmark_count: results.length,
    ok: results.every((result) => result.ok) && evidenceFailed === 0,
    summary: {
      evidence_failed: evidenceFailed,
      benchmark_process_failures: results.filter((result) => !result.ok).length,
      avg_primary_score: Number(
        (
          results.reduce((total, result) => total + (result.summary?.primary_score || 0), 0) /
          results.length
        ).toFixed(4)
      ),
      max_p95_ms: Math.max(...results.map((result) => result.summary?.p95_ms || 0)),
    },
    results,
    receipt_hash: sha256(results),
    note: 'This suite runs all current agent-bus pathfinding benchmarks and distinguishes execution evidence from pathfinding advantage.',
  };
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  process.exitCode = report.ok ? 0 : 1;
}

main();
