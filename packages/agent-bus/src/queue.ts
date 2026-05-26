/**
 * @file queue.ts
 * @module agent-bus/queue
 *
 * Zero-dependency persistent event queue for the SCBE Agent Bus.
 *
 * Uses a filesystem-based queue (JSON receipt files in staged directories)
 * so that events survive process crashes and remain auditable without
 * adding database dependencies.
 *
 * Queue lifecycle:
 *   pending/  →  running/  →  completed/
 *
 * Each event is a JSON file named `<utc-ts>-<run-id>.json`.
 */

import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import type { AgentBusEvent, AgentBusResult, RunOptions } from './index.js';
import { runBeforeRunPlugins, runAfterRunPlugins } from './plugins.js';

export interface QueuedEvent {
  run_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  event: AgentBusEvent;
  options: RunOptions;
  created_at: string;
  started_at?: string;
  finished_at?: string;
  result?: AgentBusResult;
  retry_count: number;
  max_retries: number;
  error_message?: string;
}

export interface QueueStatus {
  pending: number;
  running: number;
  completed: number;
  failed: number;
}

const DEFAULT_QUEUE_ROOT = '.aethermoor-bus/queue';
const DEFAULT_MAX_RETRIES = 2;

function queueRoot(): string {
  return process.env.SCBE_BUS_QUEUE_ROOT || DEFAULT_QUEUE_ROOT;
}

function dirs() {
  const root = path.resolve(queueRoot());
  return {
    root,
    pending: path.join(root, 'pending'),
    running: path.join(root, 'running'),
    completed: path.join(root, 'completed'),
  };
}

function ensureDirs(): void {
  const d = dirs();
  fs.mkdirSync(d.pending, { recursive: true });
  fs.mkdirSync(d.running, { recursive: true });
  fs.mkdirSync(d.completed, { recursive: true });
}

function receiptPath(dir: string, runId: string, ts?: string): string {
  const safeTs = (ts || new Date().toISOString()).replace(/[:.]/g, '-');
  return path.join(dir, `${safeTs}-${runId}.json`);
}

function writeReceipt(filePath: string, receipt: QueuedEvent): void {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, `${JSON.stringify(receipt, null, 2)}\n`, 'utf8');
}

function readReceipt(filePath: string): QueuedEvent {
  return JSON.parse(fs.readFileSync(filePath, 'utf8')) as QueuedEvent;
}

function moveReceipt(src: string, destDir: string): string {
  const dest = path.join(destDir, path.basename(src));
  fs.mkdirSync(destDir, { recursive: true });
  fs.renameSync(src, dest);
  return dest;
}

/** List receipt files in a directory, oldest first. */
function listReceipts(dir: string): string[] {
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => f.endsWith('.json'))
    .sort()
    .map((f) => path.join(dir, f));
}

function generateRunId(): string {
  return `${Date.now().toString(36)}-${crypto.randomBytes(4).toString('hex')}`;
}

// =============================================================================
// PUBLIC API
// =============================================================================

/**
 * Enqueue an event for async execution.
 * Returns the run_id so callers can poll status.
 */
export function enqueueEvent(
  event: AgentBusEvent,
  options: RunOptions = {},
  maxRetries = DEFAULT_MAX_RETRIES
): string {
  ensureDirs();
  const runId = generateRunId();
  const receipt: QueuedEvent = {
    run_id: runId,
    status: 'pending',
    event,
    options,
    created_at: new Date().toISOString(),
    retry_count: 0,
    max_retries: maxRetries,
  };
  const filePath = receiptPath(dirs().pending, runId, receipt.created_at);
  writeReceipt(filePath, receipt);
  return runId;
}

/**
 * Get the current state of a queued event by run_id.
 * Searches pending, running, and completed directories.
 */
export function getEventStatus(runId: string): QueuedEvent | null {
  const d = dirs();
  for (const dir of [d.pending, d.running, d.completed]) {
    for (const filePath of listReceipts(dir)) {
      if (path.basename(filePath).includes(runId)) {
        return readReceipt(filePath);
      }
    }
  }
  return null;
}

/**
 * Get aggregate queue statistics.
 */
export function getQueueStatus(): QueueStatus {
  const d = dirs();
  return {
    pending: listReceipts(d.pending).length,
    running: listReceipts(d.running).length,
    completed: listReceipts(d.completed).length,
    failed: listReceipts(d.completed).filter((fp) => {
      const r = readReceipt(fp);
      return r.status === 'failed';
    }).length,
  };
}

// =============================================================================
// WORKER
// =============================================================================

/**
 * Execute a single event asynchronously.
 * Replaces the old spawnSync with non-blocking spawn + Promise.
 * Runs plugin hooks before and after execution.
 */
function executeEventAsync(
  receipt: QueuedEvent,
  repoRoot: string,
  python: string
): Promise<AgentBusResult> {
  return new Promise((resolve) => {
    const normalized = receipt.event;
    const cli = path.join(repoRoot, 'scripts', 'scbe-system-cli.py');
    const argv: string[] = [
      cli,
      '--repo-root',
      repoRoot,
      'agentbus',
      'run',
      '--task',
      normalized.task,
      '--task-type',
      normalized.taskType || 'general',
      '--series-id',
      normalized.seriesId || receipt.run_id,
      '--privacy',
      normalized.privacy || 'local_only',
      '--budget-cents',
      String(normalized.budgetCents || 0),
      '--dispatch-provider',
      normalized.dispatchProvider || 'offline',
      '--json',
    ];
    if (normalized.operationCommand) {
      argv.push('--operation-command', normalized.operationCommand);
    }
    if (normalized.dispatch !== false) {
      argv.push('--dispatch');
    }

    const startedAt = new Date().toISOString();
    let stdout = '';
    let stderr = '';

    const child = spawn(python, argv, {
      cwd: repoRoot,
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    child.stdout.setEncoding('utf-8');
    child.stderr.setEncoding('utf-8');
    child.stdout.on('data', (chunk) => {
      stdout += chunk;
    });
    child.stderr.on('data', (chunk) => {
      stderr += chunk;
    });

    child.on('close', (code) => {
      let payload: Record<string, unknown> | null = null;
      try {
        payload = JSON.parse(stdout || '{}') as Record<string, unknown>;
      } catch {
        payload = null;
      }
      const taskPayload =
        payload && typeof payload.task === 'object'
          ? (payload.task as Record<string, unknown>)
          : null;

      const result: AgentBusResult = {
        schema_version: 'scbe-agentbus-node-result-v1',
        event_index: 1,
        started_at: startedAt,
        finished_at: new Date().toISOString(),
        ok: code === 0 && payload !== null,
        exit_code: code,
        stderr_tail: String(stderr || '').slice(-1000),
        event: {
          task_sha256: typeof taskPayload?.sha256 === 'string' ? taskPayload.sha256 : null,
          task_chars: normalized.task.length,
          series_id: normalized.seriesId || receipt.run_id,
          operation_command_chars: (normalized.operationCommand || '').length,
        },
        result: payload,
      };
      resolve(result);
    });

    child.on('error', (err) => {
      const result: AgentBusResult = {
        schema_version: 'scbe-agentbus-node-result-v1',
        event_index: 1,
        started_at: startedAt,
        finished_at: new Date().toISOString(),
        ok: false,
        exit_code: null,
        stderr_tail: `spawn error: ${err.message}`,
        event: {
          task_sha256: null,
          task_chars: normalized.task.length,
          series_id: normalized.seriesId || receipt.run_id,
          operation_command_chars: (normalized.operationCommand || '').length,
        },
        result: null,
      };
      resolve(result);
    });
  });
}

/**
 * Process one pending event.
 * Returns true if an event was processed, false if queue is empty.
 */
export async function processOneEvent(): Promise<boolean> {
  ensureDirs();
  const d = dirs();
  const pendingFiles = listReceipts(d.pending);
  if (pendingFiles.length === 0) return false;

  const filePath = pendingFiles[0];
  let receipt: QueuedEvent;
  try {
    receipt = readReceipt(filePath);
  } catch {
    // Corrupt receipt — move to completed as failed
    const bad = path.join(d.completed, `corrupt-${path.basename(filePath)}`);
    fs.renameSync(filePath, bad);
    return true;
  }

  const runningPath = moveReceipt(filePath, d.running);
  receipt.status = 'running';
  receipt.started_at = new Date().toISOString();
  writeReceipt(runningPath, receipt);

  // Plugin: beforeRun
  const pluginCtx = {
    event: receipt.event,
    runId: receipt.run_id,
    startedAt: receipt.started_at,
  };
  const allowedEvent = await runBeforeRunPlugins(pluginCtx);

  let result: AgentBusResult;
  if (allowedEvent === null) {
    result = {
      schema_version: 'scbe-agentbus-node-result-v1',
      event_index: 1,
      started_at: receipt.started_at,
      finished_at: new Date().toISOString(),
      ok: false,
      exit_code: 403,
      stderr_tail: 'Event denied by plugin gate',
      event: {
        task_sha256: null,
        task_chars: receipt.event.task.length,
        series_id: receipt.event.seriesId || receipt.run_id,
        operation_command_chars: (receipt.event.operationCommand || '').length,
      },
      result: { denied: true, reason: 'plugin_gate' },
    };
  } else {
    receipt.event = allowedEvent;
    const repoRoot = path.resolve(receipt.options.repoRoot || process.cwd());
    const python = receipt.options.python || process.env.PYTHON || 'python';
    result = await executeEventAsync(receipt, repoRoot, python);
  }

  receipt.result = result;
  receipt.finished_at = new Date().toISOString();

  // Plugin: afterRun
  await runAfterRunPlugins({
    event: receipt.event,
    result,
    runId: receipt.run_id,
    startedAt: receipt.started_at || receipt.created_at,
  });

  // Retry logic
  if (!result.ok && receipt.retry_count < receipt.max_retries) {
    receipt.retry_count += 1;
    receipt.status = 'pending';
    receipt.error_message = `retry ${receipt.retry_count}/${receipt.max_retries}: ${result.stderr_tail}`;
    delete receipt.started_at;
    delete receipt.finished_at;
    delete receipt.result;
    const retryPath = receiptPath(d.pending, receipt.run_id, new Date().toISOString());
    writeReceipt(retryPath, receipt);
    fs.unlinkSync(runningPath);
    return true;
  }

  receipt.status = result.ok ? 'completed' : 'failed';
  if (!result.ok && !receipt.error_message) {
    receipt.error_message = result.stderr_tail;
  }
  const completedPath = receiptPath(d.completed, receipt.run_id, receipt.finished_at);
  writeReceipt(completedPath, receipt);
  fs.unlinkSync(runningPath);
  return true;
}

/**
 * Continuously process pending events.
 * Runs until the queue is empty, then resolves.
 * Call this from a setInterval or cron for persistent workers.
 */
export async function drainQueue(): Promise<void> {
  while (await processOneEvent()) {
    // continue draining
  }
}

/**
 * Start a background worker that polls the queue every `intervalMs`.
 * Returns a handle with `stop()` to shut down gracefully.
 */
export function startQueueWorker(intervalMs = 5000): { stop: () => void } {
  let running = true;
  async function tick() {
    if (!running) return;
    try {
      await processOneEvent();
    } catch (err) {
      process.stderr.write(
        `[agent-bus] queue worker error: ${err instanceof Error ? err.message : String(err)}\n`
      );
    }
    if (running) {
      setTimeout(tick, intervalMs);
    }
  }
  tick();
  return {
    stop: () => {
      running = false;
    },
  };
}
