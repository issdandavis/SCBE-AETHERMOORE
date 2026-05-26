/**
 * @file pipeline.ts
 * @module agent-bus/pipeline
 *
 * GeoSeal-backed intent pipeline.
 *
 * Turns a natural-language intent into a governed, auditable execution:
 *   compilePlan(intent) → GeoSealPlan (policy-checked command plan)
 *   execPlan(plan)      → AgentBusResult (run through geoseal exec gate)
 *   runPipeline(intent) → PipelineRunResult (compile + gate + exec in one call)
 *
 * The compiled plan's policy.decision controls execution:
 *   ALLOW     → run
 *   anything else → block, return blocked=true with the reason
 */

import { spawnSync } from 'node:child_process';
import path from 'node:path';
import type { AgentBusResult, RunOptions } from './index.js';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface GeoSealPlanIntent {
  text: string;
  permission_mode: string;
  preferred_language?: string;
  requested_tool?: string | null;
}

export interface GeoSealPlanTool {
  class: string;
  contract: {
    tool: string;
    risk: string;
    approval: string;
    purpose?: string;
    routes?: string[];
  };
}

export interface GeoSealPlanPolicy {
  schema_version?: string;
  permission_mode?: string;
  tool_class?: string;
  ok: boolean;
  decision: 'ALLOW' | 'DENY' | 'QUARANTINE' | 'ESCALATE';
  reason: string;
}

export interface GeoSealPlanCommand {
  key: string;
  template: string;
  runnable: boolean;
}

export interface GeoSealPlanHashes {
  intent_sha256: string;
  tool_sha256?: string;
  command_sha256?: string;
  plan_sha256: string;
}

export interface GeoSealPlan {
  schema_version: 'scbe_command_plan_v1';
  intent: GeoSealPlanIntent;
  tool: GeoSealPlanTool;
  policy: GeoSealPlanPolicy;
  command: GeoSealPlanCommand;
  strands?: { forward: string; reverse: string; converged: boolean };
  hashes: GeoSealPlanHashes;
}

export interface PipelineRunResult {
  /** The compiled GeoSeal plan. Null if compile failed. */
  plan: GeoSealPlan | null;
  /** True if policy gate or compile blocked execution. */
  blocked: boolean;
  block_reason?: string;
  /** Populated when blocked=false. */
  result?: AgentBusResult;
}

// ─── Shell template parser ────────────────────────────────────────────────────

/**
 * Parse a shell-style command template string into an argv array.
 * Handles single-quoted and double-quoted segments.
 * Works for the output format produced by `geoseal compile --json`.
 */
export function parseShellTemplate(template: string): string[] {
  const args: string[] = [];
  let current = '';
  let inSingle = false;
  let inDouble = false;

  for (let i = 0; i < template.length; i++) {
    const ch = template[i];
    if (ch === "'" && !inDouble) {
      inSingle = !inSingle;
      continue;
    }
    if (ch === '"' && !inSingle) {
      inDouble = !inDouble;
      continue;
    }
    if (ch === ' ' && !inSingle && !inDouble) {
      if (current.length > 0) {
        args.push(current);
        current = '';
      }
      continue;
    }
    current += ch;
  }
  if (current.length > 0) args.push(current);
  return args;
}

// ─── Core functions ───────────────────────────────────────────────────────────

/**
 * Call `geoseal compile --json <intent>` and return the parsed plan.
 * Returns null if geoseal is unavailable or the output cannot be parsed.
 */
export function compilePlan(intent: string, options: RunOptions = {}): GeoSealPlan | null {
  const repoRoot = path.resolve(options.repoRoot || process.cwd());
  const python = options.python || process.env.PYTHON || 'python';

  const r = spawnSync(
    python,
    [path.join(repoRoot, 'src', 'geoseal_cli.py'), 'compile', '--json', intent],
    {
      encoding: 'utf-8',
      cwd: repoRoot,
      maxBuffer: 1024 * 1024 * 4,
    }
  );

  if (r.status !== 0 || !r.stdout) {
    return null;
  }
  try {
    const parsed = JSON.parse(r.stdout) as unknown;
    if (typeof parsed === 'object' && parsed !== null && 'schema_version' in parsed) {
      return parsed as GeoSealPlan;
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * Execute a compiled plan by spawning the command from plan.command.template.
 * The plan must already be policy-checked (policy.decision === 'ALLOW') before
 * calling this — gate enforcement is the caller's responsibility.
 */
export function execPlan(plan: GeoSealPlan, options: RunOptions = {}): AgentBusResult {
  const repoRoot = path.resolve(options.repoRoot || process.cwd());
  const startedAt = new Date().toISOString();

  const argv = parseShellTemplate(plan.command.template);
  if (argv.length === 0) {
    return {
      schema_version: 'scbe-agentbus-node-result-v1',
      event_index: 1,
      started_at: startedAt,
      finished_at: new Date().toISOString(),
      ok: false,
      exit_code: null,
      stderr_tail: 'empty command template after parsing',
      event: {
        task_sha256: plan.hashes.intent_sha256,
        task_chars: plan.intent.text.length,
        series_id: plan.hashes.plan_sha256.slice(0, 12),
        operation_command_chars: plan.command.template.length,
      },
      result: null,
    };
  }

  const [cmd, ...args] = argv;
  const r = spawnSync(cmd, args, {
    encoding: 'utf-8',
    cwd: repoRoot,
    maxBuffer: 1024 * 1024 * 8,
  });

  let payload: unknown = null;
  try {
    if (r.stdout) payload = JSON.parse(r.stdout) as unknown;
  } catch {
    payload = r.stdout ? { raw_output: r.stdout } : null;
  }

  return {
    schema_version: 'scbe-agentbus-node-result-v1',
    event_index: 1,
    started_at: startedAt,
    finished_at: new Date().toISOString(),
    ok: r.status === 0,
    exit_code: r.status,
    stderr_tail: String(r.stderr || '').slice(-1000),
    event: {
      task_sha256: plan.hashes.intent_sha256,
      task_chars: plan.intent.text.length,
      series_id: plan.hashes.plan_sha256.slice(0, 12),
      operation_command_chars: plan.command.template.length,
    },
    result: payload,
  };
}

/**
 * Full pipeline: compile intent → check policy → execute plan.
 *
 * @example
 * const result = await runPipeline("analyze changed files for security", {
 *   repoRoot: process.cwd(),
 * });
 * if (result.blocked) console.error(result.block_reason);
 * else console.log(result.result);
 */
export async function runPipeline(
  intent: string,
  options: RunOptions = {}
): Promise<PipelineRunResult> {
  const plan = compilePlan(intent, options);

  if (!plan) {
    return {
      plan: null,
      blocked: true,
      block_reason: `geoseal compile failed for intent: "${intent.slice(0, 60)}"`,
    };
  }

  if (plan.policy.decision !== 'ALLOW') {
    return {
      plan,
      blocked: true,
      block_reason: `policy ${plan.policy.decision}: ${plan.policy.reason}`,
    };
  }

  if (!plan.command.runnable) {
    return {
      plan,
      blocked: true,
      block_reason: `plan is not runnable (key=${plan.command.key}, check permission_mode)`,
    };
  }

  const result = execPlan(plan, options);
  return { plan, blocked: false, result };
}
