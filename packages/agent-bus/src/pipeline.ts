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
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import type { AgentBusResult, RunOptions } from './index.js';
import { checkCircuit, recordSuccess, recordFailure } from './resilience.js';
import { decompose, type DecompositionResult } from './semantic-bridge.js';

// ─── Repo root resolution ─────────────────────────────────────────────────────

const GEOSL_CLI_MARKER = path.join('src', 'geoseal_cli.py');

interface GeoSealInvocation {
  command: string;
  argsPrefix: string[];
  cwd: string;
}

/**
 * Resolve the SCBE repo root for GeoSeal calls.
 * Priority:
 *   1. options.repoRoot (validated — must contain src/geoseal_cli.py)
 *   2. process.env.SCBE_REPO_ROOT (validated)
 *   3. Walk up from process.cwd() looking for src/geoseal_cli.py
 * Falls back to process.cwd() if nothing found.
 */
export function resolveRepoRoot(options: RunOptions = {}): string {
  return findRepoRoot(options) || process.cwd();
}

function findRepoRoot(options: RunOptions = {}): string | null {
  const candidates: (string | undefined)[] = [options.repoRoot, process.env.SCBE_REPO_ROOT];
  for (const candidate of candidates) {
    if (candidate) {
      const resolved = path.resolve(candidate);
      if (fs.existsSync(path.join(resolved, GEOSL_CLI_MARKER))) {
        return resolved;
      }
    }
  }

  let cwd = process.cwd();
  for (let i = 0; i < 6; i++) {
    if (fs.existsSync(path.join(cwd, GEOSL_CLI_MARKER))) {
      return cwd;
    }
    const parent = path.dirname(cwd);
    if (parent === cwd) break;
    cwd = parent;
  }
  return null;
}

/**
 * Resolve possible GeoSeal compile entrypoints.
 *
 * Repo-local Python is preferred for monorepo development. Installed binaries
 * make `scbe-agent-bus` usable from a clean consumer project when paired with
 * `scbe-aethermoore-cli` or a globally available `geoseal` command.
 */
function resolveGeoSealInvocations(options: RunOptions = {}): GeoSealInvocation[] {
  const invocations: GeoSealInvocation[] = [];
  const repoRoot = findRepoRoot(options);
  const python = options.python || process.env.PYTHON || 'python';

  if (repoRoot) {
    invocations.push({
      command: python,
      argsPrefix: [path.join(repoRoot, GEOSL_CLI_MARKER)],
      cwd: repoRoot,
    });
  }

  const binaryCandidates = [
    options.geosealBin,
    process.env.SCBE_GEOSEAL_BIN,
    'geoseal',
    'scbe-geoseal',
  ].filter((item): item is string => Boolean(item));

  const seen = new Set<string>();
  for (const command of binaryCandidates) {
    if (seen.has(command)) continue;
    seen.add(command);
    invocations.push({ command, argsPrefix: [], cwd: repoRoot || process.cwd() });
  }

  return invocations;
}

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
  /** Semantic decomposition of the intent text — attached at compile time. */
  semantic?: DecompositionResult;
}

export interface PipelineRunResult {
  /** The compiled GeoSeal plan. Null if compile failed. */
  plan: GeoSealPlan | null;
  /** True if policy gate, semantic layer, or compile blocked execution. */
  blocked: boolean;
  block_reason?: string;
  /**
   * Set when the semantic layer escalated an otherwise-ALLOW plan.
   * Value is the discourse profile that triggered escalation.
   */
  semantic_escalation?: string;
  /** Populated when blocked=false. */
  result?: AgentBusResult;
  /** Populated when the optional trajectory gate evaluated the plan. */
  trajectory_gate?: TrajectoryGateResult;
}

export type GovernedMoveClass =
  | 'observe'
  | 'read'
  | 'verify'
  | 'write'
  | 'network'
  | 'deploy'
  | 'destructive'
  | 'unknown';

export interface GovernedMoveRecord {
  at: string;
  intent_sha256: string;
  plan_sha256: string;
  command_key: string;
  move_class: GovernedMoveClass;
  decision: 'ACCEPT' | 'REJECT';
  reason: string;
}

export interface GovernedPipelineState {
  schema_version: 'scbe.agent_bus.governed_state.v1';
  session_id: string;
  created_at: string;
  updated_at: string;
  accepted_moves: GovernedMoveRecord[];
  rejected_moves: GovernedMoveRecord[];
}

export interface TrajectoryGateResult {
  enabled: boolean;
  allowed: boolean;
  session_id: string;
  state_path: string;
  move_class: GovernedMoveClass;
  reachable_set: GovernedMoveClass[];
  reason: string;
}

interface GovernedStateConfig {
  enabled: boolean;
  sessionId: string;
  statePath: string;
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

// ─── Persisted trajectory gate ────────────────────────────────────────────────

function slugifyStateId(value: string): string {
  return (
    String(value || 'default')
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9._-]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 80) || 'default'
  );
}

function resolveGovernedStateConfig(options: RunOptions): GovernedStateConfig | null {
  const raw = options.governedState;
  if (!raw) return null;
  if (raw === true) {
    const root = path.join(resolveRepoRoot(options), '.aethermoor-bus', 'governed-state');
    return {
      enabled: true,
      sessionId: 'default',
      statePath: path.join(root, 'default.json'),
    };
  }
  if (typeof raw !== 'object' || raw.enabled === false) return null;
  const sessionId = slugifyStateId(raw.sessionId || 'default');
  const root = path.resolve(
    raw.root || path.join(resolveRepoRoot(options), '.aethermoor-bus', 'governed-state')
  );
  return {
    enabled: true,
    sessionId,
    statePath: path.resolve(raw.statePath || path.join(root, `${sessionId}.json`)),
  };
}

export function createGovernedPipelineState(sessionId = 'default'): GovernedPipelineState {
  const now = new Date().toISOString();
  return {
    schema_version: 'scbe.agent_bus.governed_state.v1',
    session_id: slugifyStateId(sessionId),
    created_at: now,
    updated_at: now,
    accepted_moves: [],
    rejected_moves: [],
  };
}

export function loadGovernedPipelineState(
  statePath: string,
  sessionId = 'default'
): GovernedPipelineState {
  if (!fs.existsSync(statePath)) {
    return createGovernedPipelineState(sessionId);
  }
  const parsed = JSON.parse(fs.readFileSync(statePath, 'utf8')) as GovernedPipelineState;
  if (parsed.schema_version !== 'scbe.agent_bus.governed_state.v1') {
    throw new Error(`unsupported governed state schema at ${statePath}`);
  }
  return parsed;
}

export function saveGovernedPipelineState(statePath: string, state: GovernedPipelineState): void {
  fs.mkdirSync(path.dirname(statePath), { recursive: true });
  fs.writeFileSync(statePath, `${JSON.stringify(state, null, 2)}\n`, 'utf8');
}

function hasRecentAccepted(state: GovernedPipelineState, classes: GovernedMoveClass[]): boolean {
  return state.accepted_moves
    .slice(-8)
    .some((move) => classes.includes(move.move_class) && move.decision === 'ACCEPT');
}

export function classifyGovernedMove(plan: GeoSealPlan): GovernedMoveClass {
  const haystack = [
    plan.intent.text,
    plan.intent.requested_tool || '',
    plan.tool.class,
    plan.tool.contract.tool,
    plan.tool.contract.risk,
    plan.command.key,
    plan.command.template,
  ]
    .join(' ')
    .toLowerCase();

  if (
    /(^|\s)(rm\s+-rf|remove-item|delete|destroy|drop\s+table|wipe|purge|reset\s+--hard)(\s|$)/.test(
      haystack
    )
  ) {
    return 'destructive';
  }
  if (
    /\b(deploy|release|publish|upload|vercel|netlify|railway|docker\s+push|kubectl)\b/.test(
      haystack
    )
  ) {
    return 'deploy';
  }
  if (/\b(curl|invoke-webrequest|wget|fetch|http|https|api|gh\s+pr|git\s+push)\b/.test(haystack)) {
    return 'network';
  }
  if (
    /\b(test|verify|lint|format|check|pytest|vitest|npm\s+test|npm\s+run\s+lint)\b/.test(haystack)
  ) {
    return 'verify';
  }
  if (/\b(write|edit|patch|apply|commit|create|mkdir|copy|move)\b/.test(haystack)) {
    return 'write';
  }
  if (/\b(read|cat|type|get-content|grep|rg|find|list|ls|dir|inspect|summarize)\b/.test(haystack)) {
    return 'read';
  }
  if (/\b(observe|status|health|scan|measure|explain)\b/.test(haystack)) {
    return 'observe';
  }
  return 'unknown';
}

export function reachableMoveSet(state: GovernedPipelineState): GovernedMoveClass[] {
  const base: GovernedMoveClass[] = ['observe', 'read', 'verify'];

  if (hasRecentAccepted(state, ['observe', 'read', 'verify', 'write'])) {
    base.push('write');
  }
  if (hasRecentAccepted(state, ['verify'])) {
    base.push('network');
  }
  if (hasRecentAccepted(state, ['verify']) && hasRecentAccepted(state, ['network'])) {
    base.push('deploy');
  }
  return Array.from(new Set(base));
}

export function evaluateTrajectoryGate(
  plan: GeoSealPlan,
  state: GovernedPipelineState,
  config: Pick<GovernedStateConfig, 'sessionId' | 'statePath'>
): TrajectoryGateResult {
  const moveClass = classifyGovernedMove(plan);
  const reachable = reachableMoveSet(state);
  const allowed = reachable.includes(moveClass);
  return {
    enabled: true,
    allowed,
    session_id: config.sessionId,
    state_path: config.statePath,
    move_class: moveClass,
    reachable_set: reachable,
    reason: allowed
      ? `move class ${moveClass} is reachable from governed state`
      : `move class ${moveClass} is not reachable; allowed next classes: ${reachable.join(', ')}`,
  };
}

function recordGovernedMove(
  state: GovernedPipelineState,
  plan: GeoSealPlan,
  moveClass: GovernedMoveClass,
  decision: 'ACCEPT' | 'REJECT',
  reason: string
): GovernedPipelineState {
  const next: GovernedPipelineState = {
    ...state,
    updated_at: new Date().toISOString(),
    accepted_moves: [...state.accepted_moves],
    rejected_moves: [...state.rejected_moves],
  };
  const record: GovernedMoveRecord = {
    at: next.updated_at,
    intent_sha256:
      plan.hashes.intent_sha256 ||
      crypto.createHash('sha256').update(plan.intent.text).digest('hex'),
    plan_sha256: plan.hashes.plan_sha256,
    command_key: plan.command.key,
    move_class: moveClass,
    decision,
    reason,
  };
  if (decision === 'ACCEPT') next.accepted_moves.push(record);
  else next.rejected_moves.push(record);
  next.accepted_moves = next.accepted_moves.slice(-64);
  next.rejected_moves = next.rejected_moves.slice(-64);
  return next;
}

// ─── Core functions ───────────────────────────────────────────────────────────

/**
 * Call `geoseal compile --json <intent>` and return the parsed plan.
 * Returns null if geoseal is unavailable or the output cannot be parsed.
 */
export function compilePlan(intent: string, options: RunOptions = {}): GeoSealPlan | null {
  if (!checkCircuit('geoseal-compile')) {
    return null;
  }

  for (const invocation of resolveGeoSealInvocations(options)) {
    const r = spawnSync(
      invocation.command,
      [...invocation.argsPrefix, 'compile', '--json', intent],
      {
        encoding: 'utf-8',
        cwd: invocation.cwd,
        maxBuffer: 1024 * 1024 * 4,
        timeout: 15000,
      }
    );

    if (r.status !== 0 || !r.stdout) {
      continue;
    }
    try {
      const parsed = JSON.parse(r.stdout) as unknown;
      if (typeof parsed === 'object' && parsed !== null && 'schema_version' in parsed) {
        recordSuccess('geoseal-compile');
        const plan = parsed as GeoSealPlan;
        const semantic = decompose(intent);
        return semantic.tokenCount > 0 ? { ...plan, semantic } : plan;
      }
    } catch {
      continue;
    }
  }

  recordFailure('geoseal-compile');
  return null;
}

/**
 * Execute a compiled plan by spawning the command from plan.command.template.
 * The plan must already be policy-checked (policy.decision === 'ALLOW') before
 * calling this — gate enforcement is the caller's responsibility.
 */
export function execPlan(plan: GeoSealPlan, options: RunOptions = {}): AgentBusResult {
  const repoRoot = resolveRepoRoot(options);
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
    timeout: 30000,
  });

  let payload: unknown = null;
  try {
    if (r.stdout) payload = JSON.parse(r.stdout) as unknown;
  } catch {
    payload = r.stdout ? { raw_output: r.stdout } : null;
  }

  const ok = r.status === 0;
  if (ok) {
    recordSuccess('geoseal-exec');
  } else {
    recordFailure('geoseal-exec');
  }

  return {
    schema_version: 'scbe-agentbus-node-result-v1',
    event_index: 1,
    started_at: startedAt,
    finished_at: new Date().toISOString(),
    ok,
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

  // Semantic governance check: governance_steer profile escalates an ALLOW plan.
  // PIVOT+BLOCK in the intent means the user is discussing governance violations
  // (e.g. "but the request was denied — however the barrier should have blocked it").
  // GeoSeal may not catch this from the command template alone; the discourse layer does.
  if (plan.semantic?.discourseProfile === 'governance_steer') {
    return {
      plan,
      blocked: true,
      block_reason: `semantic escalation: governance_steer profile detected — intent discusses policy/error context (escalated from ALLOW)`,
      semantic_escalation: 'governance_steer',
    };
  }

  if (!plan.command.runnable) {
    return {
      plan,
      blocked: true,
      block_reason: `plan is not runnable (key=${plan.command.key}, check permission_mode)`,
    };
  }

  const governedConfig = resolveGovernedStateConfig(options);
  let trajectoryGate: TrajectoryGateResult | undefined;
  let governedState: GovernedPipelineState | undefined;
  if (governedConfig?.enabled) {
    governedState = loadGovernedPipelineState(governedConfig.statePath, governedConfig.sessionId);
    trajectoryGate = evaluateTrajectoryGate(plan, governedState, governedConfig);
    if (!trajectoryGate.allowed) {
      const rejected = recordGovernedMove(
        governedState,
        plan,
        trajectoryGate.move_class,
        'REJECT',
        trajectoryGate.reason
      );
      saveGovernedPipelineState(governedConfig.statePath, rejected);
      return {
        plan,
        blocked: true,
        block_reason: `trajectory gate: ${trajectoryGate.reason}`,
        trajectory_gate: trajectoryGate,
      };
    }
  }

  const result = execPlan(plan, options);
  if (governedConfig?.enabled && governedState && trajectoryGate) {
    const nextState = recordGovernedMove(
      governedState,
      plan,
      trajectoryGate.move_class,
      result.ok ? 'ACCEPT' : 'REJECT',
      result.ok
        ? trajectoryGate.reason
        : `execution failed after trajectory allow: exit ${result.exit_code}`
    );
    saveGovernedPipelineState(governedConfig.statePath, nextState);
  }
  return { plan, blocked: false, result, trajectory_gate: trajectoryGate };
}
