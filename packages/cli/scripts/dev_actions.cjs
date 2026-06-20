#!/usr/bin/env node
'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');
const DEFAULT_RECEIPT_DIR = path.join(REPO_ROOT, 'artifacts', 'scbe-dev-actions');

const ACTION_ALIASES = {
  check: 'prepush',
  ci: 'prepush',
  fmt: 'format',
  hygiene: 'format',
  repair: 'fix',
  ship: 'prepush',
  verify: 'test',
};

const ACTION_COORDINATES = {
  run: { prime: 2, tongue: 'KO', depth: 1, role: 'execute a single concrete operation' },
  format: { prime: 3, tongue: 'RU', depth: 2, role: 'normalize source layout' },
  test: { prime: 5, tongue: 'CA', depth: 3, role: 'verify behavior' },
  fix: { prime: 7, tongue: 'RU', depth: 4, role: 'repair by format plus verification' },
  geoseal: { prime: 11, tongue: 'CA', depth: 5, role: 'govern tool execution' },
  prepush: { prime: 13, tongue: 'DR', depth: 6, role: 'prove the branch is ready to push' },
  commit: { prime: 17, tongue: 'AV', depth: 7, role: 'seal local staged changes' },
  push: { prime: 19, tongue: 'AV', depth: 8, role: 'publish a verified branch' },
};

function nowIso() {
  return new Date().toISOString();
}

function stamp() {
  return nowIso().replace(/[:.]/g, '-');
}

function hash(value) {
  return crypto.createHash('sha256').update(String(value)).digest('hex');
}

function pythonCommand() {
  return process.env.PYTHON || (process.platform === 'win32' ? 'py' : 'python3');
}

function parseJsonFromText(raw) {
  const text = String(raw || '').trim();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch (_err) {
    const lines = text.split(/\r?\n/);
    for (let index = 0; index < lines.length; index += 1) {
      const candidate = lines.slice(index).join('\n').trim();
      if (!candidate.startsWith('{') && !candidate.startsWith('[')) continue;
      try {
        return JSON.parse(candidate);
      } catch (_innerErr) {
        // keep scanning
      }
    }
  }
  return null;
}

function gateCommand(command) {
  if (process.env.SCBE_DEV_ACTION_FAST_GATE === '1') {
    return {
      allowed: true,
      tier: 'ALLOW',
      parser_ok: true,
      fast_gate: true,
      command_sha256: hash(command),
      findings: [],
    };
  }
  const code = [
    'import json, sys',
    'from src.crypto.geoseal_execution_gate import scan_command',
    'print(json.dumps(scan_command(sys.argv[1]).to_dict()))',
  ].join('\n');
  const child = spawnSync(pythonCommand(), ['-c', code, command], {
    cwd: REPO_ROOT,
    encoding: 'utf8',
    timeout: 8000,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  if (child.status !== 0) {
    return {
      allowed: true,
      tier: 'WARN',
      parser_ok: false,
      findings: ['GeoSeal execution gate unavailable; action step allowed with warning'],
      stderr_preview: String(child.stderr || '').slice(0, 500),
    };
  }
  const parsed = parseJsonFromText(child.stdout);
  if (parsed) return parsed;
  return {
    allowed: true,
    tier: 'WARN',
    parser_ok: false,
    findings: ['GeoSeal execution gate returned non-JSON; action step allowed with warning'],
    stdout_preview: String(child.stdout || '').slice(0, 500),
  };
}

function quoteArg(arg) {
  const text = String(arg ?? '');
  if (text === '') return '""';
  if (/^[A-Za-z0-9_@%+=:,./\\-]+$/.test(text)) return text;
  if (process.platform === 'win32') return `'${text.replace(/'/g, "''")}'`;
  return `'${text.replace(/'/g, "'\\''")}'`;
}

function shell(command, options = {}) {
  const started = Date.now();
  const child = spawnSync(command, {
    cwd: REPO_ROOT,
    shell: true,
    encoding: 'utf8',
    timeout: options.timeoutMs || 120000,
    maxBuffer: 1024 * 1024 * 20,
  });
  return {
    exit_code: typeof child.status === 'number' ? child.status : 1,
    duration_ms: Date.now() - started,
    stdout_preview: String(child.stdout || '').slice(-2000),
    stderr_preview: String(child.stderr || '').slice(-2000),
  };
}

function gitBranch() {
  const out = shell('git branch --show-current', { timeoutMs: 10000 });
  return out.exit_code === 0 ? out.stdout_preview.trim() || 'HEAD' : 'HEAD';
}

function step(id, action, command, options = {}) {
  const actionCoord = ACTION_COORDINATES[action] || ACTION_COORDINATES.run;
  const gateCoord = ACTION_COORDINATES.geoseal;
  return {
    id,
    action,
    command,
    timeout_ms: options.timeoutMs || 120000,
    semantic_operation: {
      syntax: `p${actionCoord.prime}:${action}`,
      anchor_prime: actionCoord.prime,
      tongue: actionCoord.tongue,
      depth: actionCoord.depth,
      role: actionCoord.role,
      geoseal_gate: `p${gateCoord.prime}:geoseal`,
      relationships: [
        `p${gateCoord.prime}->p${actionCoord.prime}`,
        `${gateCoord.tongue}->${actionCoord.tongue}`,
      ],
    },
  };
}

function baseTestSteps() {
  return [
    step('cli-tests', 'test', 'npm --prefix packages\\cli test', { timeoutMs: 240000 }),
    step('desktop-runtime-tests', 'test', 'npm --prefix packages\\polly-pad-os run test', {
      timeoutMs: 120000,
    }),
  ];
}

function prepushSteps() {
  return [
    step('diff-check', 'test', 'git diff --check', { timeoutMs: 120000 }),
    step(
      'desktop-capability-bench',
      'test',
      `${quoteArg(process.execPath)} packages\\cli\\bin\\scbe.js desktop app-bench --json`,
      { timeoutMs: 120000 }
    ),
    step('desktop-runtime-tests', 'test', 'npm --prefix packages\\polly-pad-os run test', {
      timeoutMs: 120000,
    }),
    step('desktop-build', 'test', 'npm --prefix packages\\polly-pad-os run build', {
      timeoutMs: 240000,
    }),
    step('cli-tests', 'test', 'npm --prefix packages\\cli test', { timeoutMs: 300000 }),
  ];
}

function buildPlan(action, args) {
  const message = readOption(args, '--message') || readOption(args, '-m') || args.join(' ').trim();
  const cleanAction = ACTION_ALIASES[action] || action;
  if (cleanAction === 'run') {
    const command = args.join(' ').trim();
    if (!command) throw new Error('run requires a command');
    return [step('run-command', 'run', command)];
  }
  if (cleanAction === 'format') {
    return [
      step(
        'prettier-cli-surfaces',
        'format',
        [
          'npx prettier --write',
          'packages/cli/bin/scbe.js',
          'packages/cli/scripts',
          'packages/cli/tests',
          'packages/polly-pad-os/src',
          'packages/polly-pad-os/tests',
        ].join(' '),
        { timeoutMs: 180000 }
      ),
    ];
  }
  if (cleanAction === 'test') return baseTestSteps();
  if (cleanAction === 'fix') return [...buildPlan('format', []), ...baseTestSteps()];
  if (cleanAction === 'prepush') return prepushSteps();
  if (cleanAction === 'commit') {
    if (!message) throw new Error('commit requires a message: scbe commit -m "feat: ..."');
    return [
      ...prepushSteps(),
      step(
        'staged-diff-present',
        'commit',
        [
          `${quoteArg(process.execPath)} -e`,
          quoteArg(
            [
              "const cp=require('child_process');",
              "const r=cp.spawnSync('git',['diff','--cached','--quiet']);",
              "if(r.status===0){console.error('No staged changes to commit');process.exit(1)}",
              'if(r.status===1)process.exit(0);',
              'process.exit(r.status||1);',
            ].join('')
          ),
        ].join(' '),
        { timeoutMs: 10000 }
      ),
      step('git-commit', 'commit', `git commit -m ${quoteArg(message)}`, { timeoutMs: 120000 }),
    ];
  }
  if (cleanAction === 'push') {
    const branch =
      readOption(args, '--branch') || args.find((arg) => !arg.startsWith('--')) || gitBranch();
    return [
      ...prepushSteps(),
      step('git-push', 'push', `git push origin ${quoteArg(branch)}`, { timeoutMs: 180000 }),
    ];
  }
  throw new Error(`unknown dev action '${action}'`);
}

function readOption(args, name) {
  const exact = args.indexOf(name);
  if (exact >= 0)
    return args[exact + 1] && !args[exact + 1].startsWith('--') ? args[exact + 1] : '';
  const prefix = `${name}=`;
  const hit = args.find((arg) => arg.startsWith(prefix));
  return hit ? hit.slice(prefix.length) : '';
}

function normalizeArgs(args) {
  const out = {
    action: ACTION_ALIASES[args[0]] || args[0] || 'help',
    dryRun: args.includes('--dry-run'),
    json: args.includes('--json'),
    noWrite: args.includes('--no-write') || process.env.SCBE_DEV_ACTION_NO_WRITE === '1',
    rest: args.slice(1).filter((arg) => !['--dry-run', '--json', '--no-write'].includes(arg)),
  };
  return out;
}

function canRunGate(gate) {
  const tier = String(gate.tier || 'ALLOW').toUpperCase();
  return gate.allowed !== false && !['DENY', 'QUARANTINE', 'ESCALATE'].includes(tier);
}

function executePlan(options) {
  const plannedSteps = buildPlan(options.action, options.rest);
  const startedAt = nowIso();
  const steps = [];
  let exitCode = 0;
  for (const planned of plannedSteps) {
    const geoseal = gateCommand(planned.command);
    const row = {
      ...planned,
      command_sha256: hash(planned.command),
      geoseal,
      status: options.dryRun ? 'planned' : 'pending',
    };
    if (!canRunGate(geoseal)) {
      row.status = 'blocked';
      row.exit_code = 126;
      exitCode = 126;
      steps.push(row);
      break;
    }
    if (!options.dryRun) {
      const result = shell(planned.command, { timeoutMs: planned.timeout_ms });
      row.status = result.exit_code === 0 ? 'passed' : 'failed';
      row.exit_code = result.exit_code;
      row.duration_ms = result.duration_ms;
      row.stdout_preview = result.stdout_preview;
      row.stderr_preview = result.stderr_preview;
      if (result.exit_code !== 0) {
        exitCode = result.exit_code;
        steps.push(row);
        break;
      }
    }
    steps.push(row);
  }
  const receipt = {
    schema_version: 'scbe_dev_action_receipt_v1',
    generated_at: nowIso(),
    started_at: startedAt,
    action: options.action,
    dry_run: options.dryRun,
    repo_root: REPO_ROOT,
    branch: gitBranch(),
    semantic_prime_syntax: {
      description:
        'Prime anchors label operation roles only; they are a compact semantic coordinate, not a primality claim.',
      action_coordinate: ACTION_COORDINATES[options.action] || null,
      geoseal_coordinate: ACTION_COORDINATES.geoseal,
      line: steps.map((row) => row.semantic_operation.syntax),
    },
    goals: [
      'Collapse common repo hygiene into one safe command.',
      'GeoSeal-scan every executable step before it runs.',
      'Emit a receipt that small agents and humans can both inspect.',
    ],
    summary: {
      total_steps: steps.length,
      planned: steps.filter((row) => row.status === 'planned').length,
      passed: steps.filter((row) => row.status === 'passed').length,
      failed: steps.filter((row) => row.status === 'failed').length,
      blocked: steps.filter((row) => row.status === 'blocked').length,
      exit_code: exitCode,
    },
    steps,
  };
  receipt.receipt_sha256 = hash(JSON.stringify(receipt));
  return { receipt, exitCode };
}

function writeReceipt(receipt) {
  const dir = process.env.SCBE_DEV_ACTION_DIR || DEFAULT_RECEIPT_DIR;
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, `${stamp()}-${receipt.action}.json`);
  fs.writeFileSync(file, `${JSON.stringify(receipt, null, 2)}\n`);
  return file;
}

function printHelp() {
  console.log(
    [
      'Usage:',
      '  scbe format [--dry-run] [--json]',
      '  scbe test [--dry-run] [--json]',
      '  scbe fix [--dry-run] [--json]',
      '  scbe prepush [--dry-run] [--json]',
      '  scbe commit -m "feat: message" [--dry-run] [--json]',
      '  scbe push [branch] [--dry-run] [--json]',
      '',
      'Every step is GeoSeal-scanned before execution and written to an action receipt.',
    ].join(os.EOL)
  );
}

function printText(receipt, receiptPath) {
  console.log(`SCBE ${receipt.action}${receipt.dry_run ? ' dry-run' : ''}`);
  console.log(`branch: ${receipt.branch}`);
  console.log(`steps: ${receipt.summary.total_steps}`);
  console.log(`semantic: ${receipt.semantic_prime_syntax.line.join(' -> ')}`);
  for (const row of receipt.steps) {
    const tier = row.geoseal?.tier || 'UNKNOWN';
    console.log(`  ${row.status.padEnd(7)} ${row.id.padEnd(26)} GeoSeal ${tier}  ${row.command}`);
  }
  if (receiptPath) console.log(`receipt: ${receiptPath}`);
}

function main() {
  const options = normalizeArgs(process.argv.slice(2));
  if (options.action === 'help' || options.action === '--help' || options.action === '-h') {
    printHelp();
    return;
  }
  try {
    const { receipt, exitCode } = executePlan(options);
    let receiptPath = '';
    if (!options.noWrite) {
      try {
        receiptPath = writeReceipt(receipt);
      } catch (err) {
        receipt.receipt_write_error = err && err.message ? err.message : String(err);
      }
    }
    if (receiptPath) receipt.receipt_path = receiptPath;
    if (options.json) console.log(JSON.stringify(receipt, null, 2));
    else printText(receipt, receiptPath);
    process.exit(exitCode);
  } catch (err) {
    const payload = {
      schema_version: 'scbe_dev_action_error_v1',
      action: options.action,
      error: err && err.message ? err.message : String(err),
    };
    if (options.json) console.log(JSON.stringify(payload, null, 2));
    else {
      console.error(payload.error);
      printHelp();
    }
    process.exit(2);
  }
}

main();
