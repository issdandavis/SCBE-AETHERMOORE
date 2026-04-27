/**
 * @file index.ts
 * @module agent-bus
 *
 * Typed Node surface over the existing scripts/system/agentbus_pipe.mjs runner.
 * The Python CLI (scbe-system-cli.py agentbus run) is the source of truth;
 * this module exists so TypeScript callers do not each reimplement the spawn glue.
 *
 * Status: pre-publish. The package is `private: true` in package.json until the
 * readiness gate documented in README.md clears.
 */

import { spawn } from 'node:child_process';
import * as path from 'node:path';

export type Privacy = 'local_only' | 'remote_ok';
export type TaskType = 'coding' | 'review' | 'research' | 'governance' | 'training' | 'general';

export interface AgentBusEvent {
  task: string;
  operationCommand?: string;
  taskType?: TaskType;
  seriesId?: string;
  privacy?: Privacy;
  budgetCents?: number;
  dispatch?: boolean;
  dispatchProvider?: string;
}

export interface AgentBusResult {
  schema_version: 'scbe-agentbus-pipe-result-v1';
  event_index: number;
  started_at: string;
  finished_at: string;
  ok: boolean;
  exit_code: number | null;
  stderr_tail: string;
  event: {
    task_sha256: string | null;
    task_chars: number;
    series_id: string;
    operation_command_chars: number;
  };
  result: unknown;
}

export interface RunnerOptions {
  repoRoot?: string;
  python?: string;
  continueOnError?: boolean;
}

const DEFAULT_REPO_ROOT = path.resolve(__dirname, '..', '..', '..');

function resolveRunner(repoRoot: string): string {
  return path.join(repoRoot, 'scripts', 'system', 'agentbus_pipe.mjs');
}

export async function runEvent(
  event: AgentBusEvent,
  options: RunnerOptions = {},
): Promise<AgentBusResult> {
  const rows = await runBatch([event], options);
  if (!rows.length) {
    throw new Error('agent-bus runner returned no rows');
  }
  return rows[0];
}

export async function runBatch(
  events: AgentBusEvent[],
  options: RunnerOptions = {},
): Promise<AgentBusResult[]> {
  if (!events.length) {
    throw new Error('agent-bus: events array is empty');
  }
  const repoRoot = path.resolve(options.repoRoot ?? DEFAULT_REPO_ROOT);
  const runner = resolveRunner(repoRoot);
  const args = ['--repo-root', repoRoot];
  if (options.python) {
    args.push('--python', options.python);
  }
  if (options.continueOnError) {
    args.push('--continue-on-error');
  }

  return new Promise<AgentBusResult[]>((resolve, reject) => {
    const child = spawn(process.execPath, [runner, ...args], {
      cwd: repoRoot,
      stdio: ['pipe', 'pipe', 'pipe'],
    });

    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => {
      stdout += String(chunk);
    });
    child.stderr.on('data', (chunk) => {
      stderr += String(chunk);
    });

    child.on('error', reject);
    child.on('close', (code) => {
      if (!stdout.trim()) {
        const err = new Error(`agent-bus runner produced no stdout (exit ${code})`);
        (err as Error & { stderr: string }).stderr = stderr.slice(-2000);
        reject(err);
        return;
      }
      try {
        const rows: AgentBusResult[] = stdout
          .split('\n')
          .map((line) => line.trim())
          .filter((line) => line.length > 0)
          .map((line) => JSON.parse(line) as AgentBusResult);
        resolve(rows);
      } catch (parseErr) {
        reject(parseErr);
      }
    });

    const payload = JSON.stringify(events);
    child.stdin.write(payload);
    child.stdin.end();
  });
}

export const SCHEMA_VERSION = 'scbe-agentbus-pipe-result-v1' as const;
