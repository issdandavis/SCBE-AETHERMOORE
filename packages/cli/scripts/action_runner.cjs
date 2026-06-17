#!/usr/bin/env node
'use strict';

const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const {
  actionCard,
  findActionBundle,
  listActionBundles,
  REPO_ROOT,
} = require('../lib/action-bundles');
const { ui } = require('../lib/ui');

const CLI = path.resolve(__dirname, '..', 'bin', 'scbe.js');
const HISTORY_PATH = path.join(REPO_ROOT, 'artifacts', 'scbe-actions', 'history.jsonl');

function hasFlag(args, name) {
  return args.includes(name);
}

function removeFlags(args, flags) {
  const out = [];
  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (flags.has(arg)) continue;
    out.push(arg);
  }
  return out;
}

function resolveBin(bin) {
  if (process.platform !== 'win32') return bin;
  if (bin === 'npm') return 'npm.cmd';
  return bin;
}

function preview(text, max = 2200) {
  const value = String(text || '').trim();
  if (value.length <= max) return value;
  return value.slice(-max);
}

function ensureHistoryDir() {
  fs.mkdirSync(path.dirname(HISTORY_PATH), { recursive: true });
}

function writeHistory(payload) {
  try {
    ensureHistoryDir();
    fs.appendFileSync(HISTORY_PATH, `${JSON.stringify(payload)}\n`, 'utf8');
  } catch (_err) {
    // Action execution must never fail because local history is unavailable.
  }
}

function parseJsonOutput(text) {
  const value = String(text || '').trim();
  if (!value) return null;
  try {
    return JSON.parse(value);
  } catch (_err) {
    return null;
  }
}

function actionCommand(bundle) {
  const spec = bundle.command || {};
  if (spec.runner === 'scbe') {
    return {
      command: process.execPath,
      args: [CLI, ...(spec.argv || [])],
      display: bundle.command_text,
      timeout: spec.timeout_ms || 120000,
    };
  }
  if (spec.runner === 'bin') {
    return {
      command: resolveBin(spec.bin),
      args: spec.argv || [],
      display: bundle.command_text,
      timeout: spec.timeout_ms || 120000,
    };
  }
  throw new Error(`Unsupported action runner: ${spec.runner || 'missing'}`);
}

function printHelp() {
  process.stdout.write(
    [
      'Usage:',
      '  scbe actions                         List runnable action bundles',
      '  scbe actions --json                  List action bundles as JSON',
      '  scbe actions run <id> [--json]       Execute one action',
      '  scbe actions run <id> --dry-run      Show the exact command only',
      '  scbe action <id>                    Short form for run',
      '',
      'Examples:',
      '  scbe actions run terminal.panel',
      '  scbe action desktop.status --json',
      '  scbe action desktop.open',
      '  scbe action cli.test',
      '',
    ].join('\n')
  );
}

function listActions(asJson) {
  const actions = listActionBundles().map(actionCard);
  const payload = {
    schema_version: 'scbe_action_catalog_v1',
    generated_at: new Date().toISOString(),
    history_path: HISTORY_PATH,
    count: actions.length,
    actions,
  };
  if (asJson) {
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
    return;
  }

  const u = ui({ color: undefined });
  const rows = actions.map((entry) => [
    u.badge(entry.risk || 'low', entry.risk === 'medium' ? 'warn' : 'allow'),
    u.bold(entry.id),
    entry.command,
    u.dim(entry.feedback),
  ]);
  process.stdout.write(
    [
      u.box(
        [
          `${u.bold('SCBE Actions')} ${u.dim('single-command bundles for humans and agents')}`,
          `${u.dim('run')} ${u.cyan('scbe action <id>')} ${u.dim('| json')} ${u.cyan('scbe actions --json')}`,
        ],
        { title: 'ACTIONS', color: u.cyan }
      ),
      '',
      u.table(rows, { head: ['risk', 'id', 'command', 'feedback'] }),
      '',
    ].join('\n')
  );
}

function runAction(id, options = {}) {
  const bundle = findActionBundle(id);
  const asJson = Boolean(options.json);
  const dryRun = Boolean(options.dryRun);
  const startedAt = new Date().toISOString();
  if (!bundle) {
    const payload = {
      schema_version: 'scbe_action_result_v1',
      started_at: startedAt,
      action_id: id || null,
      success: false,
      exit_code: 2,
      error: 'unknown action bundle',
      known_actions: listActionBundles().map((entry) => entry.id),
    };
    if (asJson) process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
    else process.stderr.write(`Unknown SCBE action: ${id || '(missing)'}\nRun: scbe actions\n`);
    process.exit(2);
  }

  let command;
  try {
    command = actionCommand(bundle);
  } catch (err) {
    const payload = {
      schema_version: 'scbe_action_result_v1',
      started_at: startedAt,
      action_id: bundle.id,
      success: false,
      exit_code: 2,
      command: bundle.command_text,
      error: err.message,
    };
    if (asJson) process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
    else process.stderr.write(`${err.message}\n`);
    process.exit(2);
  }

  if (dryRun) {
    const payload = {
      schema_version: 'scbe_action_result_v1',
      started_at: startedAt,
      action_id: bundle.id,
      label: bundle.label,
      surface: bundle.surface,
      command: command.display,
      cwd: REPO_ROOT,
      dry_run: true,
      success: true,
      exit_code: 0,
      feedback: bundle.feedback,
      agent_use: bundle.agent_use,
    };
    if (asJson) {
      process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
    } else {
      const u = ui({});
      process.stdout.write(
        `${u.info(`would run ${u.bold(bundle.id)}`)}\n  ${u.cyan(command.display)}\n`
      );
    }
    return;
  }

  const start = process.hrtime.bigint();
  const child = spawnSync(command.command, command.args, {
    cwd: REPO_ROOT,
    encoding: 'utf8',
    timeout: command.timeout,
    maxBuffer: 12 * 1024 * 1024,
    env: { ...process.env },
  });
  const durationMs = Number(process.hrtime.bigint() - start) / 1_000_000;
  const exitCode = typeof child.status === 'number' ? child.status : 1;
  const payload = {
    schema_version: 'scbe_action_result_v1',
    started_at: startedAt,
    action_id: bundle.id,
    label: bundle.label,
    surface: bundle.surface,
    command: command.display,
    cwd: REPO_ROOT,
    success: exitCode === 0,
    exit_code: exitCode,
    duration_ms: Number(durationMs.toFixed(2)),
    feedback: bundle.feedback,
    agent_use: bundle.agent_use,
    stdout_preview: preview(child.stdout),
    stderr_preview: preview(child.stderr),
    error: child.error ? child.error.message : null,
    history_path: HISTORY_PATH,
  };
  const stdoutJson = parseJsonOutput(child.stdout);
  if (stdoutJson) payload.stdout_json = stdoutJson;
  writeHistory(payload);

  if (asJson) {
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
  } else {
    const u = ui({});
    process.stdout.write(
      [
        u.box(
          [
            `${u.badge(payload.success ? 'pass' : 'fail', payload.success ? 'allow' : 'deny')} ${u.bold(bundle.label)} ${u.dim(bundle.id)}`,
            `${u.dim('command')} ${u.cyan(command.display)}`,
            `${u.dim('time')} ${payload.duration_ms}ms ${u.dim('exit')} ${payload.exit_code}`,
          ],
          { title: 'ACTION', color: payload.success ? u.cyan : u.yellow }
        ),
        payload.stdout_preview ? `\n${u.dim('stdout')}\n${payload.stdout_preview}` : '',
        payload.stderr_preview ? `\n${u.dim('stderr')}\n${payload.stderr_preview}` : '',
        '',
      ].join('\n')
    );
  }

  process.exit(exitCode);
}

function main(argv) {
  const asJson = hasFlag(argv, '--json');
  const dryRun = hasFlag(argv, '--dry-run');
  const filtered = removeFlags(argv, new Set(['--json', '--dry-run', '--no-color']));
  const sub = filtered[0] || 'list';
  if (sub === 'help' || sub === '--help' || sub === '-h') {
    printHelp();
    return;
  }
  if (sub === 'list' || sub === 'ls') {
    listActions(asJson);
    return;
  }
  if (sub === 'run') {
    runAction(filtered[1], { json: asJson, dryRun });
    return;
  }
  runAction(sub, { json: asJson, dryRun });
}

main(process.argv.slice(2));
