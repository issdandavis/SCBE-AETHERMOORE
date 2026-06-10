#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');
const DEFAULT_DATASET = 'terminal-bench-core==0.1.1';
const DEFAULT_TASK = 'vim-terminal-task';
const DEFAULT_OUTPUT = path.join(REPO_ROOT, 'artifacts', 'benchmarks', 'nonlocal-terminal-bench');
const DEFAULT_MODEL = 'ollama:qwen2.5-coder:1.5b';

function usage() {
  return [
    'Usage:',
    '  scbe bench tb-smoke --oracle [--task <id>] [--json]',
    '  scbe bench tb-smoke --scbe [--task <id>] [--model ollama:qwen2.5-coder:1.5b] [--json]',
    '  scbe bench tb-smoke --scbe-model [--task <id>] [--model ollama:qwen2.5-coder:1.5b]',
    '',
    'Defaults:',
    `  dataset: ${DEFAULT_DATASET}`,
    `  task:    ${DEFAULT_TASK}`,
    '',
    'SCBE mode defaults to choice-script scaffolding: the harness picks legal',
    'moves and blocks dead moves. Use --scbe-model to test raw model command',
    'generation instead.',
    '',
    'This runs Terminal-Bench from WSL when called on Windows. It is a real',
    'external harness smoke, not a public leaderboard submission.',
    '',
  ].join('\n');
}

function parseArgs(argv) {
  const options = {
    agent: 'oracle',
    choiceScript: true,
    dataset: DEFAULT_DATASET,
    download: true,
    dryRun: false,
    json: false,
    model: process.env.SCBE_MODEL || DEFAULT_MODEL,
    nAttempts: 1,
    nConcurrent: 1,
    outputPath: DEFAULT_OUTPUT,
    task: DEFAULT_TASK,
    timeoutAgent: 180,
    timeoutTest: 120,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--help' || arg === '-h') {
      options.help = true;
    } else if (arg === '--oracle') {
      options.agent = 'oracle';
      options.choiceScript = false;
    } else if (arg === '--scbe') {
      options.agent = 'scbe';
      options.choiceScript = true;
    } else if (arg === '--scbe-choice' || arg === '--choice-script') {
      options.agent = 'scbe';
      options.choiceScript = true;
    } else if (arg === '--scbe-model' || arg === '--raw-model') {
      options.agent = 'scbe';
      options.choiceScript = false;
    } else if (arg === '--json') {
      options.json = true;
    } else if (arg === '--dry-run') {
      options.dryRun = true;
    } else if (arg === '--no-download') {
      options.download = false;
    } else if (arg === '--dataset') {
      options.dataset = requireValue(argv, ++i, arg);
    } else if (arg === '--task') {
      options.task = requireValue(argv, ++i, arg);
    } else if (arg === '--model') {
      options.model = requireValue(argv, ++i, arg);
    } else if (arg === '--run-id') {
      options.runId = requireValue(argv, ++i, arg);
    } else if (arg === '--out' || arg === '--output-path') {
      options.outputPath = path.resolve(requireValue(argv, ++i, arg));
    } else if (arg === '--agent-timeout') {
      options.timeoutAgent = Number(requireValue(argv, ++i, arg));
    } else if (arg === '--test-timeout') {
      options.timeoutTest = Number(requireValue(argv, ++i, arg));
    } else if (arg === '--attempts') {
      options.nAttempts = Number(requireValue(argv, ++i, arg));
    } else if (arg === '--concurrent') {
      options.nConcurrent = Number(requireValue(argv, ++i, arg));
    } else {
      throw new Error(`unknown argument: ${arg}`);
    }
  }

  for (const [key, value] of [
    ['agent-timeout', options.timeoutAgent],
    ['test-timeout', options.timeoutTest],
    ['attempts', options.nAttempts],
    ['concurrent', options.nConcurrent],
  ]) {
    if (!Number.isFinite(value) || value <= 0) {
      throw new Error(`${key} must be a positive number`);
    }
  }

  options.runId =
    options.runId ||
    `${options.agent}-smoke-${new Date()
      .toISOString()
      .replace(/[-:.TZ]/g, '')
      .slice(0, 14)}`;
  return options;
}

function requireValue(argv, index, flag) {
  const value = argv[index];
  if (!value || value.startsWith('--')) throw new Error(`${flag} requires a value`);
  return value;
}

function shellQuote(value) {
  return `'${String(value).replace(/'/g, `'\\''`)}'`;
}

function toWslPath(value) {
  const absolute = path.resolve(value);
  const match = absolute.match(/^([A-Za-z]):\\(.*)$/);
  if (!match) return absolute.replace(/\\/g, '/');
  const drive = match[1].toLowerCase();
  const rest = match[2].replace(/\\/g, '/');
  return `/mnt/${drive}/${rest}`;
}

function toTbModel(model) {
  const slash = model.indexOf('/');
  if (slash !== -1) return model;
  const providerModel = splitProviderModel(model);
  if (providerModel) return `${providerModel.provider}/${providerModel.model}`;
  return `ollama/${model}`;
}

function toScbeModelEnv(model) {
  const slash = model.indexOf('/');
  if (slash !== -1) return model;
  const providerModel = splitProviderModel(model);
  if (providerModel) return `${providerModel.provider}/${providerModel.model}`;
  return model;
}

function splitProviderModel(model) {
  const match = String(model || '').match(/^([a-z][\w-]*):(.+)$/i);
  if (!match) return null;
  const provider = match[1].toLowerCase();
  const knownProviders = new Set(['ollama', 'openai', 'anthropic', 'fireworks', 'gemini']);
  if (!knownProviders.has(provider)) return null;
  return { provider, model: match[2] };
}

function toDisplayModel(model) {
  const providerModel = splitProviderModel(model);
  if (providerModel) return `${providerModel.provider}:${providerModel.model}`;
  if (model.includes('/')) return model.replace('/', ':');
  return `ollama:${model}`;
}

function writeScbeWrapper() {
  const tempRoot = path.join('C:\\SCBE_CACHE', 'temp');
  fs.mkdirSync(tempRoot, { recursive: true });
  const wrapper = path.join(tempRoot, 'scbe-win-node.sh');
  const cliPath = path.join(REPO_ROOT, 'packages', 'cli', 'bin', 'scbe.js').replace(/\\/g, '/');
  fs.writeFileSync(wrapper, `#!/usr/bin/env bash\nexec node.exe ${cliPath} "$@"\n`, 'ascii');
  return wrapper;
}

function buildBashScript(options) {
  const lines = ['#!/usr/bin/env bash', 'set -euo pipefail'];
  lines.push(`cd ${shellQuote(toWslPath(REPO_ROOT))}`);
  lines.push(`mkdir -p ${shellQuote(toWslPath(options.outputPath))}`);
  lines.push('command -v tb >/dev/null');
  lines.push('command -v podman >/dev/null || command -v docker >/dev/null');

  if (options.download) {
    lines.push(`tb datasets download -d ${shellQuote(options.dataset)}`);
  }

  const common = [
    'tb',
    'runs',
    'create',
    '-d',
    shellQuote(options.dataset),
    '--task-id',
    shellQuote(options.task),
    '--n-concurrent',
    String(options.nConcurrent),
    '--n-attempts',
    String(options.nAttempts),
    '--global-agent-timeout-sec',
    String(options.timeoutAgent),
    '--global-test-timeout-sec',
    String(options.timeoutTest),
    '--output-path',
    shellQuote(toWslPath(options.outputPath)),
    '--run-id',
    shellQuote(options.runId),
  ];

  if (options.agent === 'oracle') {
    lines.push([...common, '--agent', 'oracle'].join(' '));
  } else {
    const wrapper = writeScbeWrapper();
    lines.push(`chmod +x ${shellQuote(toWslPath(wrapper))}`);
    lines.push(`export SCBE_CLI=${shellQuote(toWslPath(wrapper))}`);
    lines.push(`export SCBE_MODEL=${shellQuote(toScbeModelEnv(options.model))}`);
    if (options.choiceScript) {
      lines.push('export SCBE_AGENT_JSON_SCAFFOLD=1');
    }
    lines.push(
      'export WSLENV="SCBE_MODEL/u:SCBE_AGENT_JSON_SCAFFOLD/u:SCBE_AGENT_JSON_SKIP_GOVERNANCE/u:${WSLENV:-}"'
    );
    lines.push(
      `export PYTHONPATH=${shellQuote(toWslPath(path.join(REPO_ROOT, 'packages', 'cli', 'scripts')))}:\${PYTHONPATH:-}`
    );
    lines.push(
      [
        ...common,
        '--agent-import-path',
        'scbe_tb_agent:ScbeAgent',
        '--model',
        shellQuote(toTbModel(options.model)),
      ].join(' ')
    );
  }

  return `${lines.join('\n')}\n`;
}

function runWslScript(script) {
  const tempRoot = path.join('C:\\SCBE_CACHE', 'temp');
  fs.mkdirSync(tempRoot, { recursive: true });
  const scriptPath = path.join(tempRoot, `scbe-tb-smoke-${process.pid}-${Date.now()}.sh`);
  fs.writeFileSync(scriptPath, script, 'ascii');
  const result = spawnSync('wsl', ['bash', toWslPath(scriptPath)], {
    cwd: REPO_ROOT,
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
    timeout: 15 * 60 * 1000,
  });
  try {
    fs.rmSync(scriptPath, { force: true });
  } catch {
    // temp cleanup only
  }
  return result;
}

function readSummary(options) {
  const resultPath = path.join(options.outputPath, options.runId, 'results.json');
  if (!fs.existsSync(resultPath)) return { result_path: resultPath, result_exists: false };
  const payload = JSON.parse(fs.readFileSync(resultPath, 'utf8'));
  const first = Array.isArray(payload.results) ? payload.results[0] : null;
  return {
    result_path: resultPath,
    result_exists: true,
    accuracy: payload.accuracy,
    n_resolved: payload.n_resolved,
    n_unresolved: payload.n_unresolved,
    task_id: first ? first.task_id : options.task,
    is_resolved: first ? first.is_resolved : null,
    failure_mode: first ? first.failure_mode : null,
  };
}

function payloadFor(options, script, runResult) {
  const summary = options.dryRun ? null : readSummary(options);
  return {
    schema_version: 'scbe_tb_smoke_v1',
    generated_at_utc: new Date().toISOString(),
    claim_boundary:
      'External Terminal-Bench harness smoke only. Public leaderboard placement requires full unchanged upstream run and published artifacts.',
    command: `scbe bench tb-smoke --${options.agent} --task ${options.task}`,
    options: {
      agent: options.agent,
      dataset: options.dataset,
      task: options.task,
      model: options.agent === 'scbe' ? toDisplayModel(options.model) : null,
      choice_script: options.agent === 'scbe' ? options.choiceScript : false,
      run_id: options.runId,
      output_path: options.outputPath,
    },
    dry_run: options.dryRun,
    bash_script: script,
    run_status: runResult
      ? {
          status: runResult.status,
          signal: runResult.signal,
          error: runResult.error ? runResult.error.message : null,
        }
      : null,
    summary,
  };
}

function printPlain(payload, stdout, stderr) {
  process.stdout.write('SCBE Terminal-Bench smoke\n');
  process.stdout.write(`agent: ${payload.options.agent}\n`);
  process.stdout.write(`task:  ${payload.options.task}\n`);
  process.stdout.write(`run:   ${payload.options.run_id}\n`);
  process.stdout.write(`rule:  ${payload.claim_boundary}\n`);
  if (payload.dry_run) {
    process.stdout.write('\nDry run command script:\n');
    process.stdout.write(payload.bash_script);
    return;
  }
  if (stdout) process.stdout.write(`\n${stdout.trim()}\n`);
  if (stderr) process.stderr.write(`${stderr.trim()}\n`);
  if (payload.summary?.result_exists) {
    process.stdout.write('\nSummary:\n');
    process.stdout.write(`  accuracy: ${payload.summary.accuracy}\n`);
    process.stdout.write(`  resolved: ${payload.summary.n_resolved}\n`);
    process.stdout.write(`  unresolved: ${payload.summary.n_unresolved}\n`);
    process.stdout.write(`  failure: ${payload.summary.failure_mode || 'none'}\n`);
    process.stdout.write(`  results: ${payload.summary.result_path}\n`);
  }
}

function main() {
  let options;
  try {
    options = parseArgs(process.argv.slice(2));
  } catch (error) {
    process.stderr.write(`scbe tb-smoke: ${error.message}\n\n${usage()}`);
    process.exit(2);
  }

  if (options.help) {
    process.stdout.write(usage());
    process.exit(0);
  }

  const script = buildBashScript(options);
  if (options.dryRun) {
    const payload = payloadFor(options, script, null);
    if (options.json) process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
    else printPlain(payload);
    process.exit(0);
  }

  const result = runWslScript(script);
  const payload = payloadFor(options, script, result);
  if (options.json) {
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
    if (result.stderr) process.stderr.write(result.stderr);
  } else {
    printPlain(payload, result.stdout, result.stderr);
  }
  process.exit(typeof result.status === 'number' ? result.status : 1);
}

main();
