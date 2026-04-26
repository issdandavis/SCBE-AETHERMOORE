#!/usr/bin/env node
/*
Pipeable SCBE agent-bus runner.

Reads one JSON object or JSONL objects from stdin/input file and runs the
user-facing `scbe-system-cli.py agentbus run` endpoint for each event. This is
the Zapier/Grok-fleet style surface: event in, shaped bus result out.
*/

import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

function parseArgs(argv) {
  const args = {
    repoRoot: process.cwd(),
    input: '',
    output: '',
    python: process.env.PYTHON || 'python',
    continueOnError: false,
  };
  for (let i = 2; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--repo-root' && argv[i + 1]) {
      args.repoRoot = argv[++i];
    } else if (arg === '--input' && argv[i + 1]) {
      args.input = argv[++i];
    } else if (arg === '--output' && argv[i + 1]) {
      args.output = argv[++i];
    } else if (arg === '--python' && argv[i + 1]) {
      args.python = argv[++i];
    } else if (arg === '--continue-on-error') {
      args.continueOnError = true;
    }
  }
  return args;
}

function readStdin() {
  try {
    return fs.readFileSync(0, 'utf-8');
  } catch {
    return '';
  }
}

function parseEvents(raw) {
  const text = String(raw || '').trim();
  if (!text) return [];
  const parsed = JSON.parse(text);
  if (Array.isArray(parsed)) return parsed;
  if (Array.isArray(parsed.items)) return parsed.items;
  return [parsed];
}

function normalizeEvent(event, index) {
  if (!event || typeof event !== 'object') {
    throw new Error(`event ${index} must be an object`);
  }
  const task = String(event.task || event.text || '').trim();
  if (!task) {
    throw new Error(`event ${index} missing task/text`);
  }
  return {
    task,
    operationCommand: String(event.operation_command || event.operationCommand || '').trim(),
    taskType: String(event.task_type || event.taskType || 'general').trim(),
    seriesId: String(event.series_id || event.seriesId || `pipe-event-${index}`).trim(),
    privacy: String(event.privacy || 'local_only').trim(),
    budgetCents: Number(event.budget_cents ?? event.budgetCents ?? 0),
    dispatch: event.dispatch !== false,
    dispatchProvider: String(event.dispatch_provider || event.dispatchProvider || 'offline').trim(),
  };
}

function runOne(args, event, index) {
  const normalized = normalizeEvent(event, index);
  const cli = path.join(path.resolve(args.repoRoot), 'scripts', 'scbe-system-cli.py');
  const argv = [
    cli,
    '--repo-root',
    path.resolve(args.repoRoot),
    'agentbus',
    'run',
    '--task',
    normalized.task,
    '--task-type',
    normalized.taskType,
    '--series-id',
    normalized.seriesId,
    '--privacy',
    normalized.privacy,
    '--budget-cents',
    String(normalized.budgetCents),
    '--dispatch-provider',
    normalized.dispatchProvider,
    '--json',
  ];
  if (normalized.operationCommand) {
    argv.push('--operation-command', normalized.operationCommand);
  }
  if (normalized.dispatch) {
    argv.push('--dispatch');
  }

  const startedAt = new Date().toISOString();
  const result = spawnSync(args.python, argv, {
    cwd: path.resolve(args.repoRoot),
    encoding: 'utf-8',
    maxBuffer: 1024 * 1024 * 8,
  });
  let payload = null;
  try {
    payload = JSON.parse(result.stdout || '{}');
  } catch {
    payload = null;
  }
  return {
    schema_version: 'scbe-agentbus-pipe-result-v1',
    event_index: index,
    started_at: startedAt,
    finished_at: new Date().toISOString(),
    ok: result.status === 0 && Boolean(payload),
    exit_code: result.status,
    stderr_tail: String(result.stderr || '').slice(-1000),
    event: {
      task_sha256: payload?.task?.sha256 || null,
      task_chars: normalized.task.length,
      series_id: normalized.seriesId,
      operation_command_chars: normalized.operationCommand.length,
    },
    result: payload,
  };
}

function main() {
  const args = parseArgs(process.argv);
  const raw = args.input ? fs.readFileSync(args.input, 'utf-8') : readStdin();
  const events = parseEvents(raw);
  if (!events.length) {
    throw new Error('no events provided');
  }

  const rows = [];
  for (let i = 0; i < events.length; i += 1) {
    const row = runOne(args, events[i], i + 1);
    rows.push(row);
    if (!row.ok && !args.continueOnError) {
      break;
    }
  }

  const output = rows.map((row) => JSON.stringify(row)).join('\n') + '\n';
  if (args.output) {
    const outPath = path.resolve(args.output);
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    fs.writeFileSync(outPath, output, 'utf-8');
  } else {
    process.stdout.write(output);
  }
  if (rows.some((row) => !row.ok)) {
    process.exitCode = 1;
  }
}

main();
