#!/usr/bin/env node
'use strict';

const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');
const DEFAULT_ARTIFACT_DIR = path.join(REPO_ROOT, 'artifacts', 'benchmarks', 'scbe-task-corpus');
const DEFAULT_TARGETS = path.join(REPO_ROOT, 'config', 'eval', 'code_model_ranker_targets.v1.json');

function parseArgs(argv) {
  const opts = {
    json: false,
    category: 'codegen-hard',
    includeScaffold: false,
    limit: 12,
    probeOfficial: false,
  };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--json') opts.json = true;
    else if (arg === '--include-scaffold') opts.includeScaffold = true;
    else if (arg === '--probe-official') opts.probeOfficial = true;
    else if (arg === '--all-categories') opts.category = 'all';
    else if (arg === '--category') opts.category = argv[++i] || opts.category;
    else if (arg.startsWith('--category=')) opts.category = arg.slice('--category='.length);
    else if (arg === '--limit') opts.limit = Number(argv[++i] || opts.limit);
    else if (arg.startsWith('--limit=')) opts.limit = Number(arg.slice('--limit='.length));
    else if (arg === '--help' || arg === '-h') opts.help = true;
    else if (arg.trim()) opts.unknown = arg;
  }
  if (!Number.isFinite(opts.limit) || opts.limit < 1) opts.limit = 12;
  return opts;
}

function readJson(filePath, fallback = null) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch (_err) {
    return fallback;
  }
}

function rel(filePath) {
  return path.relative(REPO_ROOT, filePath).replace(/\\/g, '/');
}

function listJsonFiles(dir) {
  try {
    return fs
      .readdirSync(dir, { withFileTypes: true })
      .filter((entry) => entry.isFile() && entry.name.endsWith('.json'))
      .map((entry) => path.join(dir, entry.name));
  } catch (_err) {
    return [];
  }
}

function runKind(artifact) {
  if ((artifact.provider || '').toLowerCase() === 'offline') return 'scaffold';
  return 'model';
}

function harnessMode(artifact) {
  const advisor = artifact.advisor;
  if ((artifact.provider || '').toLowerCase() === 'offline') return 'offline-scaffold';
  if (advisor?.rescue_enabled)
    return `rescue-advisor:${advisor.rescue_mode || advisor.mode || 'retry'}`;
  if (advisor) return `advisor:${advisor.mode || 'retry'}`;
  return 'raw-primary';
}

function summarizeArtifact(filePath, category) {
  const artifact = readJson(filePath);
  if (!artifact || artifact.schema !== 'task-corpus/v2' || !Array.isArray(artifact.tasks)) {
    return null;
  }
  const selected =
    category === 'all'
      ? artifact.tasks
      : artifact.tasks.filter((task) => task.category === category);
  if (!selected.length) return null;

  const completed = selected.filter((task) => task.completed).length;
  const total = selected.length;
  const turns = selected.reduce((sum, task) => sum + Number(task.turns || 0), 0);
  const durationMs = selected.reduce((sum, task) => sum + Number(task.duration_ms || 0), 0);
  const falseDone = selected.reduce((sum, task) => sum + Number(task.false_done_count || 0), 0);
  const koBans = selected.reduce((sum, task) => sum + Number(task.ko_ban_count || 0), 0);
  const rescueCount = selected.filter((task) => task.rescued_by_advisor).length;
  const failedTasks = selected.filter((task) => !task.completed).map((task) => task.id);
  const categories = [...new Set(selected.map((task) => task.category))].sort();
  const verifierStrengths = [...new Set(selected.map((task) => task.verifier || 'unknown'))].sort();
  const kind = runKind(artifact);

  return {
    run_kind: kind,
    rankable: kind === 'model',
    provider: artifact.provider || 'unknown',
    model: artifact.model || 'unknown',
    harness_mode: harnessMode(artifact),
    advisor: artifact.advisor || null,
    category: category === 'all' ? categories.join(',') : category,
    categories,
    verifier_strengths: verifierStrengths,
    generated_at: artifact.generated_at || null,
    commit: artifact.commit || 'unknown',
    score: {
      completed,
      total,
      completion_rate: total ? completed / total : 0,
    },
    totals: {
      turns,
      false_done: falseDone,
      ko_bans: koBans,
      duration_ms: durationMs,
      rescued_by_advisor: rescueCount,
    },
    failed_tasks: failedTasks,
    artifact: rel(filePath),
  };
}

function sortRows(rows) {
  return rows.sort((a, b) => {
    const rateDelta = b.score.completion_rate - a.score.completion_rate;
    if (rateDelta) return rateDelta;
    const solvedDelta = b.score.completed - a.score.completed;
    if (solvedDelta) return solvedDelta;
    const turnDelta = a.totals.turns - b.totals.turns;
    if (turnDelta) return turnDelta;
    const durationDelta = a.totals.duration_ms - b.totals.duration_ms;
    if (durationDelta) return durationDelta;
    return String(b.generated_at || '').localeCompare(String(a.generated_at || ''));
  });
}

function pct(value) {
  return `${(Number(value || 0) * 100).toFixed(1)}%`;
}

function pad(value, width) {
  const text = String(value ?? '');
  return text.length >= width ? text : text + ' '.repeat(width - text.length);
}

function commandAvailable(command, args = ['--version'], timeoutMs = 10_000) {
  const result = spawnSync(command, args, {
    encoding: 'utf8',
    timeout: timeoutMs,
  });
  return {
    command: [command, ...args].join(' '),
    ok: result.status === 0,
    status: typeof result.status === 'number' ? result.status : null,
    stderr: (result.stderr || result.error?.message || '').trim().slice(0, 240),
    stdout: (result.stdout || '').trim().slice(0, 240),
  };
}

function buildOfficialProbe() {
  const probes = [
    { id: 'git', ...commandAvailable('git', ['--version']) },
    { id: 'docker', ...commandAvailable('docker', ['--version']) },
    { id: 'harbor', ...commandAvailable('harbor', ['--help']) },
    {
      id: 'python',
      ...commandAvailable(process.platform === 'win32' ? 'python' : 'python3', ['--version']),
    },
  ];
  if (process.platform === 'win32') {
    probes.push({
      id: 'wsl_terminal_bench_surface',
      ...commandAvailable(
        'wsl',
        [
          'bash',
          '-lc',
          'command -v harbor || command -v tb; command -v podman || command -v docker; python3 --version',
        ],
        30_000
      ),
    });
  }
  return probes;
}

function buildPayload(opts) {
  const artifactDir = path.resolve(
    process.env.SCBE_CODE_RANKER_ARTIFACT_DIR ||
      process.env.SCBE_TASK_CORPUS_ARTIFACT_DIR ||
      DEFAULT_ARTIFACT_DIR
  );
  const targetsPath = path.resolve(process.env.SCBE_CODE_RANKER_TARGETS || DEFAULT_TARGETS);
  const targets = readJson(targetsPath, {
    schema_version: 'scbe_code_model_ranker_targets_v1',
    public_targets: [],
  });

  const allRows = listJsonFiles(artifactDir)
    .map((filePath) => summarizeArtifact(filePath, opts.category))
    .filter(Boolean);
  const modelRows = sortRows(allRows.filter((row) => row.run_kind === 'model')).map(
    (row, index) => ({
      rank: index + 1,
      ...row,
    })
  );
  const scaffoldRows = sortRows(allRows.filter((row) => row.run_kind === 'scaffold')).map(
    (row, index) => ({
      rank: index + 1,
      ...row,
    })
  );

  return {
    schema_version: 'scbe_code_model_ranker_v1',
    generated_at_utc: new Date().toISOString(),
    category: opts.category,
    artifact_dir: rel(artifactDir),
    targets_path: rel(targetsPath),
    claim_boundary:
      'SCBE private harness rows are local engineering evidence only. Official placement requires running the unchanged upstream benchmark harness and publishing the required artifacts/logs/traces.',
    public_reference_targets: targets.public_targets || [],
    private_model_rankings: modelRows.slice(0, opts.limit),
    private_model_run_count: modelRows.length,
    scaffold_calibration_runs: opts.includeScaffold ? scaffoldRows.slice(0, opts.limit) : [],
    scaffold_run_count: scaffoldRows.length,
    official_probe: opts.probeOfficial ? buildOfficialProbe() : null,
  };
}

function printPlain(payload) {
  const lines = [
    'SCBE code model ranker',
    '------------------------------------------------------------',
    `category: ${payload.category}`,
    `boundary: ${payload.claim_boundary}`,
    '',
    'Official public targets:',
  ];
  for (const target of payload.public_reference_targets) {
    const anchor = target.top_public_anchor
      ? `${target.top_public_anchor.name || 'live upstream'} ${target.top_public_anchor.score || ''}`.trim()
      : 'live upstream';
    lines.push(`  ${pad(target.id, 26)} ${pad(target.metric || 'metric', 18)} ${anchor}`);
  }
  lines.push('', 'Private SCBE model rankings:');
  if (!payload.private_model_rankings.length) {
    lines.push('  no model artifacts found for this category');
  } else {
    lines.push('  rank  score   turns  mode                         model');
    for (const row of payload.private_model_rankings) {
      lines.push(
        `  ${pad(row.rank, 4)}  ${pad(`${row.score.completed}/${row.score.total}`, 6)}  ${pad(
          row.totals.turns,
          5
        )}  ${pad(row.harness_mode, 28)} ${row.provider}:${row.model}`
      );
    }
  }
  lines.push('', `Scaffold calibration runs hidden: ${payload.scaffold_run_count}`);
  if (payload.official_probe) {
    lines.push('', 'Official harness readiness probe:');
    for (const probe of payload.official_probe) {
      lines.push(`  ${pad(probe.id, 28)} ${probe.ok ? 'ok' : 'missing/fail'}  ${probe.command}`);
    }
  }
  lines.push('', 'Next official lanes:');
  for (const target of payload.public_reference_targets) {
    if (target.official_run_command) {
      lines.push(`  ${target.id}: ${target.official_run_command}`);
    }
  }
  lines.push('');
  process.stdout.write(lines.join('\n'));
}

function printHelp() {
  process.stdout.write(
    [
      'Usage:',
      '  node packages/cli/scripts/bench_code_ranker.cjs [--json] [--category codegen-hard]',
      '  node packages/cli/scripts/bench_code_ranker.cjs --probe-official',
      '',
      'Options:',
      '  --json               Emit machine-readable board',
      '  --category <name>    Score only one task category (default: codegen-hard)',
      '  --all-categories     Score all task-corpus categories in each artifact',
      '  --include-scaffold   Show offline scaffold calibration rows',
      '  --probe-official     Check local readiness for official harnesses',
      '  --limit <n>          Number of rows per table (default: 12)',
      '',
      'Private SCBE rows are not public leaderboard claims.',
      '',
    ].join('\n')
  );
}

function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help) {
    printHelp();
    return;
  }
  if (opts.unknown) {
    process.stderr.write(`bench_code_ranker: unknown option ${opts.unknown}\n`);
    process.exit(2);
  }
  const payload = buildPayload(opts);
  if (opts.json) {
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
    return;
  }
  printPlain(payload);
}

main();
