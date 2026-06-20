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
    axis_scores: artifact?.data?.axis_scores || null,
    artifact: artifact?.path || null,
    stderr_tail: run.stderr.slice(-500),
  };
}

function parseModelMatrix(raw) {
  if (!raw || !raw.trim()) return [];
  const text = raw.trim();
  if (text.startsWith('[')) {
    const rows = JSON.parse(text);
    if (!Array.isArray(rows)) throw new Error('SCBE_CODEGEN_MODEL_MATRIX JSON must be an array');
    return rows.map((row, index) => ({
      name: String(row.name || `${row.provider || 'model'}-${index + 1}`),
      provider: String(row.provider || ''),
      model: String(row.model || ''),
      baseUrl: row.baseUrl || row.base_url || row.url || '',
      apiKeyEnv: row.apiKeyEnv || row.api_key_env || '',
    }));
  }
  return text
    .split(';')
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part, index) => {
      const fields = part.split('|').map((value) => value.trim());
      if (fields.length < 3) {
        throw new Error(
          `model matrix row ${index + 1} must be name|provider|model[|baseUrl][|apiKeyEnv]`
        );
      }
      return {
        name: fields[0],
        provider: fields[1],
        model: fields[2],
        baseUrl: fields[3] || '',
        apiKeyEnv: fields[4] || '',
      };
    });
}

function envForModelRow(row) {
  const env = {
    SCBE_PROVIDER: row.provider,
    SCBE_MODEL: row.model,
    SCBE_DISABLE_AGENT_JSON_FALLBACK: row.provider === 'offline' ? '' : '1',
  };
  if (row.baseUrl) {
    env.SCBE_BASE_URL = row.baseUrl;
    env.SCBE_URL = row.baseUrl;
  }
  if (row.apiKeyEnv && process.env[row.apiKeyEnv]) env.SCBE_API_KEY = process.env[row.apiKeyEnv];
  return Object.fromEntries(
    Object.entries(env).filter(([, value]) => value != null && value !== '')
  );
}

function advisorEnv() {
  const env = {};
  if (process.env.SCBE_ADVISOR_PROVIDER)
    env.SCBE_ADVISOR_PROVIDER = process.env.SCBE_ADVISOR_PROVIDER;
  if (process.env.SCBE_ADVISOR_MODEL) env.SCBE_ADVISOR_MODEL = process.env.SCBE_ADVISOR_MODEL;
  if (process.env.SCBE_ADVISOR_MAX_CHARS)
    env.SCBE_ADVISOR_MAX_CHARS = process.env.SCBE_ADVISOR_MAX_CHARS;
  if (process.env.SCBE_ADVISOR_MODE) env.SCBE_ADVISOR_MODE = process.env.SCBE_ADVISOR_MODE;
  if (process.env.SCBE_ADVISOR_WEB) env.SCBE_ADVISOR_WEB = process.env.SCBE_ADVISOR_WEB;
  if (process.env.SCBE_ADVISOR_WEB_QUERY)
    env.SCBE_ADVISOR_WEB_QUERY = process.env.SCBE_ADVISOR_WEB_QUERY;
  if (process.env.SCBE_ADVISOR_WEB_DOMAINS)
    env.SCBE_ADVISOR_WEB_DOMAINS = process.env.SCBE_ADVISOR_WEB_DOMAINS;
  if (process.env.SCBE_ADVISOR_WEB_MAX) env.SCBE_ADVISOR_WEB_MAX = process.env.SCBE_ADVISOR_WEB_MAX;
  return env;
}

function safeName(value) {
  return String(value || 'model')
    .replace(/[^a-zA-Z0-9_.-]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 48);
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

  const offlineCodegen = runNode(
    corpusBench,
    ['--category', 'codegen', '--max-corpus-turns=20', '--fail-on-incomplete'],
    { SCBE_PROVIDER: 'offline' },
    120000
  );
  results.push({
    name: 'offline_codegen_corpus',
    description: 'deterministic code-generation scaffold with runnable verifiers',
    ...corpusSummary(offlineCodegen),
  });

  const offlineHardCodegen = runNode(
    corpusBench,
    ['--category', 'codegen-hard', '--max-corpus-turns=40', '--fail-on-incomplete'],
    { SCBE_PROVIDER: 'offline' },
    300000
  );
  results.push({
    name: 'offline_hard_codegen_corpus',
    description: 'deterministic hard code-generation and repair tasks with runnable verifiers',
    ...corpusSummary(offlineHardCodegen),
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
      optional: true,
      ...corpusSummary(live),
    });
  }

  if (process.env.SCBE_RUN_LIVE_CODEGEN_BENCH === '1') {
    const liveCodegen = runNode(
      corpusBench,
      ['--category', 'codegen', '--max-corpus-turns=8', '--fail-on-incomplete'],
      { SCBE_DISABLE_AGENT_JSON_FALLBACK: '1' },
      180000
    );
    results.push({
      name: 'live_provider_codegen_corpus',
      description: 'live provider codegen tasks with deterministic scaffold fallback disabled',
      optional: true,
      ...corpusSummary(liveCodegen),
    });
  }

  const modelMatrix = parseModelMatrix(process.env.SCBE_CODEGEN_MODEL_MATRIX || '');
  const runHardModelMatrix = process.env.SCBE_RUN_HARD_CODEGEN_MODELS === '1';
  const runAdvisorModelMatrix =
    process.env.SCBE_RUN_ADVISOR_CODEGEN_MODELS === '1' &&
    Boolean(process.env.SCBE_ADVISOR_MODEL || process.env.SCBE_ADVISOR_PROVIDER);
  const runRescueModelMatrix =
    process.env.SCBE_RUN_RESCUE_CODEGEN_MODELS === '1' &&
    Boolean(process.env.SCBE_ADVISOR_MODEL || process.env.SCBE_ADVISOR_PROVIDER);
  for (const row of modelMatrix) {
    const modelRun = runNode(
      corpusBench,
      ['--category', 'codegen', '--max-corpus-turns=20', '--fail-on-incomplete'],
      envForModelRow(row),
      300000
    );
    results.push({
      name: `model_codegen_${safeName(row.name)}`,
      description: 'code-generation corpus against one configured provider/model row',
      optional: true,
      provider: row.provider,
      model: row.model,
      ...corpusSummary(modelRun),
    });

    if (runHardModelMatrix) {
      const hardModelRun = runNode(
        corpusBench,
        ['--category', 'codegen-hard', '--max-corpus-turns=40', '--fail-on-incomplete'],
        envForModelRow(row),
        600000
      );
      results.push({
        name: `model_hard_codegen_${safeName(row.name)}`,
        description:
          'hard code-generation and repair corpus against one configured provider/model row',
        optional: true,
        provider: row.provider,
        model: row.model,
        ...corpusSummary(hardModelRun),
      });
    }

    if (runAdvisorModelMatrix) {
      const hardAdvisorRun = runNode(
        corpusBench,
        ['--category', 'codegen-hard', '--max-corpus-turns=40', '--fail-on-incomplete'],
        { ...envForModelRow(row), ...advisorEnv() },
        900000
      );
      results.push({
        name: `advisor_hard_codegen_${safeName(row.name)}`,
        description:
          'hard code-generation corpus with a secondary advisor worksheet in the configured advisor mode',
        optional: true,
        provider: row.provider,
        model: row.model,
        advisor_provider: process.env.SCBE_ADVISOR_PROVIDER || 'ollama',
        advisor_model: process.env.SCBE_ADVISOR_MODEL || '',
        advisor_mode: process.env.SCBE_ADVISOR_MODE || 'retry',
        ...corpusSummary(hardAdvisorRun),
      });
    }

    if (runRescueModelMatrix) {
      const hardRescueRun = runNode(
        corpusBench,
        [
          '--category',
          'codegen-hard',
          '--max-corpus-turns=80',
          '--fail-on-incomplete',
          '--rescue-advisor',
        ],
        { ...envForModelRow(row), ...advisorEnv() },
        1200000
      );
      results.push({
        name: `rescue_hard_codegen_${safeName(row.name)}`,
        description:
          'hard code-generation corpus; plain primary first, advisor retries verifier failures',
        optional: true,
        provider: row.provider,
        model: row.model,
        advisor_provider: process.env.SCBE_ADVISOR_PROVIDER || 'ollama',
        advisor_model: process.env.SCBE_ADVISOR_MODEL || '',
        advisor_mode: process.env.SCBE_ADVISOR_MODE || 'retry',
        ...corpusSummary(hardRescueRun),
      });
    }
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
    live_codegen_included: process.env.SCBE_RUN_LIVE_CODEGEN_BENCH === '1',
    codegen_model_matrix_included: modelMatrix.length > 0,
    codegen_model_matrix_count: modelMatrix.length,
    hard_codegen_model_matrix_included: runHardModelMatrix && modelMatrix.length > 0,
    advisor_codegen_model_matrix_included: runAdvisorModelMatrix && modelMatrix.length > 0,
    rescue_codegen_model_matrix_included: runRescueModelMatrix && modelMatrix.length > 0,
    optional_failure_required: process.env.SCBE_REQUIRE_OPTIONAL_BENCH === '1',
    results,
  };

  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
  const out = path.join(ARTIFACT_DIR, `${generatedAt.replace(/[:.]/g, '-')}-harness-matrix.json`);
  fs.writeFileSync(out, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
  console.log(`\nartifact: ${out}`);

  const failedRequired = results.some(
    (r) =>
      r.name !== 'missing_model_no_fallback_control' &&
      !r.ok &&
      (process.env.SCBE_REQUIRE_OPTIONAL_BENCH === '1' || !r.optional)
  );
  process.exit(failedRequired ? 1 : 0);
}

main();
