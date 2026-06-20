/**
 * @file reaction-chain.ts
 * @module agent-bus/reaction-chain
 * @layer Cross-layer workflow orchestration
 * @component ReactionChain — chemical-reaction-style verified workflow chains
 *
 * Each "reaction" is one governed AgentBusEvent step. When a step completes,
 * downstream steps whose deps are now satisfied are automatically enqueued.
 * Small AI can execute long verified chains at low cost because each step is
 * independently minimal and the chain state is fully serializable.
 *
 * Security: task_template supports ${step.<id>.result|status|ok} interpolation
 * for passing prior outputs forward as NL context. operationCommand is NEVER
 * interpolated — it flows verbatim to shell execution to prevent injection.
 *
 * Cost routing: model_tier ('local'|'free'|'paid') maps to dispatchProvider
 * on each enqueued event, enabling the free-first routing policy per step.
 */

import crypto from 'node:crypto';
import type { AgentBusEvent, RunOptions } from './index.js';
import { enqueueEvent, processOneEvent, getEventStatus } from './queue.js';

// ─── Spec types (workflow definition) ────────────────────────────────────────

/**
 * One reaction step in a chain.
 *
 * id             — unique within the chain; used as the dependency key.
 * task_template  — NL prompt. Supports ${step.<id>.result|status|ok}.
 * operation_command — static shell stub. Never interpolated.
 * model_tier     — cost-routing hint: 'local' → Ollama, 'free' → Cerebras/Groq, 'paid' → Anthropic.
 * depends_on     — IDs that must be 'done' before this step fires.
 */
export interface ReactionSpec {
  id: string;
  task_template: string;
  task_type?: string;
  operation_command?: string;
  model_tier?: 'local' | 'free' | 'paid';
  depends_on?: string[];
}

/** Versioned, named workflow spec. */
export interface ReactionChain {
  schema_version: 'scbe_reaction_chain_v1';
  chain_id: string;
  reactions: ReactionSpec[];
}

// ─── Runtime state types ──────────────────────────────────────────────────────

export type ReactionStepStatus = 'pending' | 'running' | 'done' | 'blocked';
export type ChainRunStatus = 'running' | 'complete' | 'blocked';

export interface ReactionStepState {
  id: string;
  status: ReactionStepStatus;
  queue_run_id?: string;
  result?: unknown;
  started_at?: string;
  finished_at?: string;
  error?: string;
}

export interface ReactionChainState {
  schema_version: 'scbe_reaction_chain_state_v1';
  chain_id: string;
  run_id: string;
  started_at: string;
  status: ChainRunStatus;
  steps: Record<string, ReactionStepState>;
}

// ─── Pure state machine ───────────────────────────────────────────────────────

export interface ChainStartResult {
  state: ReactionChainState;
  /** IDs of reactions that are immediately ready to fire. */
  ready: string[];
}

export interface ChainAdvanceResult {
  state: ReactionChainState;
  /** IDs that became ready after this step completed (empty if step was blocked). */
  newly_ready: string[];
  done: boolean;
}

/**
 * Initialize a chain run. Empty chains start with status 'complete' and ready=[].
 * All steps start as 'pending'; reactions with no deps are immediately ready.
 */
export function startChain(chain: ReactionChain): ChainStartResult {
  const now = new Date().toISOString();
  const steps: Record<string, ReactionStepState> = {};
  for (const r of chain.reactions) {
    steps[r.id] = { id: r.id, status: 'pending' };
  }
  const status: ChainRunStatus = chain.reactions.length === 0 ? 'complete' : 'running';
  const state: ReactionChainState = {
    schema_version: 'scbe_reaction_chain_state_v1',
    chain_id: chain.chain_id,
    run_id: crypto.randomBytes(6).toString('hex'),
    started_at: now,
    status,
    steps,
  };
  return { state, ready: getReadyReactions(state, chain) };
}

/**
 * Return IDs of pending reactions whose every dependency is 'done'.
 * Pure — no mutations, safe to call repeatedly.
 */
export function getReadyReactions(state: ReactionChainState, chain: ReactionChain): string[] {
  return chain.reactions
    .filter((r) => {
      const step = state.steps[r.id];
      if (!step || step.status !== 'pending') return false;
      return (r.depends_on ?? []).every((dep) => state.steps[dep]?.status === 'done');
    })
    .map((r) => r.id);
}

/**
 * Record that a step completed and return the updated state + newly ready IDs.
 *
 * ok=false marks the step 'blocked'. Any step whose deps include a blocked
 * step can never become ready. When no pending or running steps remain
 * reachable, the chain transitions to 'blocked'.
 */
export function advanceChain(
  state: ReactionChainState,
  chain: ReactionChain,
  completedId: string,
  result: unknown,
  ok: boolean
): ChainAdvanceResult {
  const now = new Date().toISOString();
  const updated: ReactionChainState = {
    ...state,
    steps: {
      ...state.steps,
      [completedId]: {
        ...state.steps[completedId]!,
        status: ok ? 'done' : 'blocked',
        result,
        finished_at: now,
        ...(ok ? {} : { error: 'step completed with ok=false' }),
      },
    },
  };

  const newly_ready = ok ? getReadyReactions(updated, chain) : [];

  // Determine overall chain status
  const allDone = chain.reactions.every((r) => updated.steps[r.id]?.status === 'done');
  if (allDone) {
    updated.status = 'complete';
  } else {
    const anyBlocked = Object.values(updated.steps).some((s) => s.status === 'blocked');
    if (anyBlocked) {
      const stillReachable = getReadyReactions(updated, chain).length > 0;
      const stillRunning = Object.values(updated.steps).some((s) => s.status === 'running');
      if (!stillReachable && !stillRunning && newly_ready.length === 0) {
        updated.status = 'blocked';
      }
    }
  }

  return { state: updated, newly_ready, done: updated.status === 'complete' };
}

// ─── Task template rendering ──────────────────────────────────────────────────

const STEP_REF_RE = /\$\{step\.([a-zA-Z0-9_-]+)\.(result|status|ok)\}/g;

/**
 * Render a task_template by substituting ${step.<id>.result|status|ok} from state.
 *
 * Only task_template is ever passed to this function.
 * operation_command MUST NOT be rendered here — it flows to shell argv.
 */
export function renderTask(template: string, state: ReactionChainState): string {
  return template.replace(STEP_REF_RE, (_match, stepId, field) => {
    const step = state.steps[stepId];
    if (!step) return _match;
    if (field === 'result') {
      const v = step.result;
      return v === undefined ? _match : typeof v === 'string' ? v : JSON.stringify(v);
    }
    if (field === 'status') return step.status;
    // field === 'ok'
    return step.status === 'done' ? 'true' : 'false';
  });
}

// ─── Event builder ────────────────────────────────────────────────────────────

const TIER_MAP: Record<string, string> = {
  local: 'ollama',
  free: 'cerebras',
  paid: 'anthropic',
};

/**
 * Build an AgentBusEvent from a ReactionSpec and current chain state.
 *
 * seriesId encodes the chain run and reaction ID so completion can be
 * traced back to the right step.
 *
 * task_template is rendered (NL interpolation allowed).
 * operation_command is passed verbatim (no interpolation, no exceptions).
 */
export function buildReactionEvent(
  spec: ReactionSpec,
  state: ReactionChainState,
  chainRunId: string
): AgentBusEvent {
  return {
    task: renderTask(spec.task_template, state),
    seriesId: `${chainRunId}-${spec.id}`,
    ...(spec.task_type ? { taskType: spec.task_type } : {}),
    ...(spec.operation_command ? { operationCommand: spec.operation_command } : {}),
    ...(spec.model_tier ? { dispatchProvider: TIER_MAP[spec.model_tier] ?? 'offline' } : {}),
  };
}

// ─── Queue runner ─────────────────────────────────────────────────────────────

/** Signature for an injectable event runner (primarily for testing). */
export type ReactionRunnerFn = (event: AgentBusEvent) => Promise<{ ok: boolean; result: unknown }>;

export interface ReactionChainRunOptions extends RunOptions {
  /**
   * Override the event runner. When omitted, events route through the
   * filesystem queue: enqueueEvent → processOneEvent → getEventStatus.
   *
   * Note: the default queue runner assumes the queue is idle before the
   * chain starts. For a shared queue, inject a custom runEvent that
   * dispatches to a specific handler.
   */
  runEvent?: ReactionRunnerFn;
}

export interface ReactionChainRunResult {
  schema_version: 'scbe_reaction_chain_run_v1';
  chain_id: string;
  run_id: string;
  state: ReactionChainState;
  ok: boolean;
  steps_completed: number;
  steps_blocked: number;
}

function defaultQueueRunner(options: RunOptions): ReactionRunnerFn {
  return async (event: AgentBusEvent) => {
    const runId = enqueueEvent(event, options);
    await processOneEvent();
    const queued = getEventStatus(runId);
    return {
      ok: queued?.result?.ok ?? false,
      result: queued?.result?.result ?? null,
    };
  };
}

/**
 * Execute a ReactionChain, returning the final run state and summary.
 *
 * Steps are processed in dependency order. A batch of ready steps (all with
 * no unmet deps) runs sequentially; after the batch completes, the next
 * batch of newly-ready steps runs, and so on.
 *
 * When a step fails (ok=false), all steps that depend on it (directly or
 * transitively) become permanently unreachable and the chain terminates as
 * 'blocked'.
 */
export async function runReactionChain(
  chain: ReactionChain,
  options: ReactionChainRunOptions = {}
): Promise<ReactionChainRunResult> {
  const runner = options.runEvent ?? defaultQueueRunner(options);
  let { state, ready } = startChain(chain);

  while (ready.length > 0 && state.status === 'running') {
    const batch = [...ready];

    for (const id of batch) {
      const spec = chain.reactions.find((r) => r.id === id);
      if (!spec) continue;

      state = {
        ...state,
        steps: {
          ...state.steps,
          [id]: {
            ...state.steps[id]!,
            status: 'running',
            started_at: new Date().toISOString(),
          },
        },
      };

      const event = buildReactionEvent(spec, state, state.run_id);
      const { ok, result } = await runner(event);

      const { state: next } = advanceChain(state, chain, id, result, ok);
      state = next;
    }

    ready = state.status === 'running' ? getReadyReactions(state, chain) : [];
  }

  const completed = Object.values(state.steps).filter((s) => s.status === 'done').length;
  const blocked = Object.values(state.steps).filter((s) => s.status === 'blocked').length;

  return {
    schema_version: 'scbe_reaction_chain_run_v1',
    chain_id: chain.chain_id,
    run_id: state.run_id,
    state,
    ok: state.status === 'complete',
    steps_completed: completed,
    steps_blocked: blocked,
  };
}
