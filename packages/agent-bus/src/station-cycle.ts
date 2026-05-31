/**
 * @file station-cycle.ts
 * @module agent-bus/station-cycle
 * @layer Fleet coordination
 * @component StationCycle — integration layer that runs one operational cycle
 *
 * Wires station-manifest + keeper-agent + polly-operator + handoff-packet into
 * a single atomic tick:
 *   1. Keeper sweep   — apply safe repairs, collect escalations
 *   2. Polly brief    — narrate the post-sweep state for the operator
 *   3. Handoff queue  — mint HandoffPackets for every auto-dispatchable action
 *
 * All state is immutable. Every call returns new objects; inputs are not mutated.
 * The result is JSON-serializable so it can be persisted, forwarded, or diffed.
 */

import { runSweep } from './keeper-agent.js';
import type { KeeperAgent, KeeperRunResult } from './keeper-agent.js';
import { buildPollyOperatorBrief } from './polly-operator.js';
import type {
  PollyOperatorBrief,
  PollyOperatorBriefOptions,
  PollyOperatorAction,
} from './polly-operator.js';
import { createHandoff } from './handoff-packet.js';
import type { HandoffPacket, HandoffPriority } from './handoff-packet.js';
import type { StationManifest } from './station-manifest.js';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface StationCycleOptions {
  now?: string;
  briefOpts?: Omit<PollyOperatorBriefOptions, 'now' | 'keeperRun'>;
  /** When true, keeper repairs are planned but not applied to the manifest. */
  dryRun?: boolean;
  /** Deadline offset in ms added to now for each suggested handoff. Default: none. */
  handoffDeadlineMs?: number;
}

export interface StationCycleResult {
  readonly schema_version: 'scbe_station_cycle_v1';
  readonly cycle_id: string;
  readonly cycle_at: string;
  /** Manifest after keeper repairs were applied (same ref when dry_run). */
  readonly manifest: StationManifest;
  /** Keeper state after this cycle (updated sweep counters). */
  readonly keeper: KeeperAgent;
  /** Full keeper run record including sweep + repair results. */
  readonly keeperRun: KeeperRunResult;
  /** Polly operator brief rendered from post-sweep state. */
  readonly brief: PollyOperatorBrief;
  /**
   * HandoffPackets (all in HELD state) generated from Polly actions where
   * requires_human === false. Ready to be thrown to an executor or queued.
   */
  readonly suggestedHandoffs: HandoffPacket[];
}

// ─── Internals ────────────────────────────────────────────────────────────────

let _cycleCounter = 0;

function nextCycleId(now: string): string {
  _cycleCounter = (_cycleCounter + 1) % 1_000_000;
  const ts = now.replace(/[-:.TZ]/g, '').slice(0, 14);
  return `cycle-${ts}-${String(_cycleCounter).padStart(6, '0')}`;
}

const POLLY_PRIORITY_TO_HANDOFF: Record<string, HandoffPriority> = {
  info: 'routine',
  notice: 'routine',
  warning: 'elevated',
  critical: 'urgent',
};

function actionToHandoff(
  action: PollyOperatorAction,
  keeperId: string,
  now: string,
  deadlineAt?: string
): HandoffPacket {
  return createHandoff(
    keeperId,
    {
      task: action.command,
      payload: {
        action_id: action.id,
        reason: action.reason,
        priority: action.priority,
      },
    },
    {
      now,
      priority: POLLY_PRIORITY_TO_HANDOFF[action.priority] ?? 'routine',
      authority: 'auto',
      ...(deadlineAt ? { deadlineAt } : {}),
    }
  );
}

// ─── Public API ───────────────────────────────────────────────────────────────

/**
 * Run one operational cycle: keeper sweep → Polly brief → suggested handoffs.
 *
 * @param manifest  Current station manifest (read-only input).
 * @param keeper    Current keeper agent state (read-only input).
 * @param opts      Optional cycle parameters.
 * @returns         Immutable StationCycleResult with updated manifest, keeper,
 *                  brief, and suggested handoffs.
 */
export function runStationCycle(
  manifest: StationManifest,
  keeper: KeeperAgent,
  opts: StationCycleOptions = {}
): StationCycleResult {
  const now = opts.now ?? new Date().toISOString();
  const cycleId = nextCycleId(now);

  // Step 1 — keeper sweep (note: runSweep signature is keeper, manifest, opts)
  const {
    manifest: sweptManifest,
    keeper: updatedKeeper,
    result: keeperRun,
  } = runSweep(keeper, manifest, { now, dry_run: opts.dryRun });

  // Step 2 — Polly brief over the post-sweep manifest
  const brief = buildPollyOperatorBrief(sweptManifest, {
    ...opts.briefOpts,
    now,
    keeperRun,
  });

  // Step 3 — mint handoffs for every auto-dispatchable action
  const deadlineAt = opts.handoffDeadlineMs
    ? new Date(new Date(now).getTime() + opts.handoffDeadlineMs).toISOString()
    : undefined;

  const suggestedHandoffs: HandoffPacket[] = brief.actions
    .filter((a) => !a.requires_human)
    .map((a) => actionToHandoff(a, keeper.keeper_id, now, deadlineAt));

  return {
    schema_version: 'scbe_station_cycle_v1',
    cycle_id: cycleId,
    cycle_at: now,
    manifest: sweptManifest,
    keeper: updatedKeeper,
    keeperRun,
    brief,
    suggestedHandoffs,
  };
}
