/**
 * @file keeper-agent.ts
 * @module agent-bus/keeper-agent
 * @layer Cross-layer maintenance
 * @component KeeperAgent — low-permission background daemon for station upkeep
 *
 * Keepers run periodic sweeps of the StationManifest, apply safe repairs
 * autonomously, and escalate anything requiring higher authority. They
 * operate in the 'keeper' architecture lane — repair authority only, no
 * creative or governance decisions.
 *
 * Repair authority matrix:
 *   schedule_audit          → AUTO: stamp zone with generated receipt ID
 *   evict_excess_occupants  → AUTO: trim occupants to zone.capacity
 *   review_quarantine       → ESCALATE: requires governance clearance
 *   add_transit_link        → ESCALATE: keeper cannot determine topology
 *
 * All state is immutable — every function returns new objects.
 * KeeperAgent and all result types are JSON-serializable.
 */

import { sweepKeepers, updateZone, getZone } from './station-manifest.js';
import type {
  StationManifest,
  StationZone,
  KeeperRepairAction,
  KeeperSweepResult,
} from './station-manifest.js';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface KeeperConfig {
  /** Sweep interval hint in milliseconds (informational; callers drive timing). */
  sweep_interval_ms: number;
  /** Max repairs applied per sweep before the remainder stays queued. */
  max_repairs_per_sweep: number;
  /** Zone staleness threshold forwarded to sweepKeepers. */
  stale_threshold_ms: number;
  /** When true, repairs are planned but the manifest is not modified. */
  dry_run: boolean;
}

export interface KeeperEscalation {
  zone_id: string;
  action: string;
  reason: string;
  escalated_at: string;
  resolved: boolean;
}

export interface KeeperAgent {
  schema_version: 'scbe_keeper_agent_v1';
  keeper_id: string;
  config: KeeperConfig;
  /** Pending repairs queued for the next drain. */
  repair_queue: KeeperRepairAction[];
  /** Accumulated escalations (resolved + unresolved). */
  escalation_log: KeeperEscalation[];
  /** ISO timestamp of most recent sweep. */
  last_sweep?: string;
  total_sweeps: number;
  total_repairs_applied: number;
  total_escalations: number;
}

export interface KeeperRepairResult {
  action: KeeperRepairAction;
  applied: boolean;
  skipped: boolean;
  skip_reason?: string;
  dry_run: boolean;
}

export interface KeeperRunResult {
  schema_version: 'scbe_keeper_run_v1';
  keeper_id: string;
  run_at: string;
  sweep: KeeperSweepResult;
  repairs: KeeperRepairResult[];
  new_escalations: KeeperEscalation[];
  zones_repaired: number;
  zones_escalated: number;
  dry_run: boolean;
}

// ─── Repair classification ────────────────────────────────────────────────────

/** Actions the keeper can apply automatically without escalation. */
const AUTO_REPAIRABLE = new Set<string>(['schedule_audit', 'evict_excess_occupants']);

/** Actions that require escalation — keeper cannot safely resolve alone. */
const MUST_ESCALATE = new Set<string>(['review_quarantine', 'add_transit_link']);

function escalationReason(action: string): string {
  if (action === 'review_quarantine') return 'quarantine_review_requires_governance_clearance';
  if (action === 'add_transit_link') return 'transit_topology_change_requires_station_authority';
  return 'unknown_action';
}

// ─── Lifecycle ────────────────────────────────────────────────────────────────

export function createKeeper(keeperId: string, opts: Partial<KeeperConfig> = {}): KeeperAgent {
  return {
    schema_version: 'scbe_keeper_agent_v1',
    keeper_id: keeperId,
    config: {
      sweep_interval_ms: opts.sweep_interval_ms ?? 300_000, // 5 min default
      max_repairs_per_sweep: opts.max_repairs_per_sweep ?? 20,
      stale_threshold_ms: opts.stale_threshold_ms ?? 86_400_000, // 24 h
      dry_run: opts.dry_run ?? false,
    },
    repair_queue: [],
    escalation_log: [],
    total_sweeps: 0,
    total_repairs_applied: 0,
    total_escalations: 0,
  };
}

// ─── Repair queue ─────────────────────────────────────────────────────────────

/** Enqueue a repair action. Returns new KeeperAgent (immutable). */
export function queueRepair(keeper: KeeperAgent, action: KeeperRepairAction): KeeperAgent {
  return { ...keeper, repair_queue: [...keeper.repair_queue, action] };
}

/** Clear all queued repairs without applying them. */
export function clearRepairQueue(keeper: KeeperAgent): KeeperAgent {
  return { ...keeper, repair_queue: [] };
}

// ─── Escalation ───────────────────────────────────────────────────────────────

export function escalate(
  keeper: KeeperAgent,
  zoneId: string,
  action: string,
  reason: string,
  opts: { now?: string } = {}
): KeeperAgent {
  const now = opts.now ?? new Date().toISOString();
  const entry: KeeperEscalation = {
    zone_id: zoneId,
    action,
    reason,
    escalated_at: now,
    resolved: false,
  };
  return {
    ...keeper,
    escalation_log: [...keeper.escalation_log, entry],
    total_escalations: keeper.total_escalations + 1,
  };
}

export function resolveEscalation(
  keeper: KeeperAgent,
  zoneId: string,
  action: string
): KeeperAgent {
  const escalation_log = keeper.escalation_log.map((e) =>
    e.zone_id === zoneId && e.action === action && !e.resolved ? { ...e, resolved: true } : e
  );
  return { ...keeper, escalation_log };
}

// ─── Single repair application ────────────────────────────────────────────────

function generateReceiptId(keeperId: string, zoneId: string, now: string): string {
  const ts = new Date(now).getTime().toString(36);
  return `rcpt-${keeperId.slice(0, 8)}-${zoneId.slice(0, 8)}-${ts}`;
}

/**
 * Apply one repair action to the manifest.
 *
 * Returns updated keeper, manifest, and a result record.
 * If dry_run (from action override or keeper config), manifest is unchanged.
 */
export function applyRepair(
  keeper: KeeperAgent,
  manifest: StationManifest,
  action: KeeperRepairAction,
  opts: { now?: string; dry_run?: boolean } = {}
): { keeper: KeeperAgent; manifest: StationManifest; result: KeeperRepairResult } {
  const now = opts.now ?? new Date().toISOString();
  const isDryRun = opts.dry_run ?? keeper.config.dry_run;

  // Actions requiring escalation are never applied
  if (MUST_ESCALATE.has(action.action)) {
    const reason = escalationReason(action.action);
    const updatedKeeper = escalate(keeper, action.zone_id, action.action, reason, { now });
    return {
      keeper: updatedKeeper,
      manifest,
      result: { action, applied: false, skipped: true, skip_reason: reason, dry_run: isDryRun },
    };
  }

  // Unknown actions are skipped with a note
  if (!AUTO_REPAIRABLE.has(action.action)) {
    return {
      keeper,
      manifest,
      result: {
        action,
        applied: false,
        skipped: true,
        skip_reason: 'unknown_repair_action',
        dry_run: isDryRun,
      },
    };
  }

  // Dry run: plan the repair but don't mutate
  if (isDryRun) {
    return {
      keeper,
      manifest,
      result: { action, applied: false, skipped: false, dry_run: true },
    };
  }

  // Apply the repair
  let updatedManifest = manifest;
  let applied = false;

  if (action.action === 'schedule_audit') {
    const zone = getZone(manifest, action.zone_id);
    if (zone) {
      const receiptId = generateReceiptId(keeper.keeper_id, action.zone_id, now);
      const updatedZone: StationZone = {
        ...zone,
        audit_receipt: receiptId,
        updated_at: now,
      };
      updatedManifest = updateZone(manifest, updatedZone, { now });
      applied = true;
    }
  } else if (action.action === 'evict_excess_occupants') {
    const zone = getZone(manifest, action.zone_id);
    if (zone && zone.occupants.length > zone.capacity) {
      const updatedZone: StationZone = {
        ...zone,
        // Evict from the tail — oldest occupants first (FIFO assumption)
        occupants: zone.occupants.slice(0, zone.capacity),
        updated_at: now,
      };
      updatedManifest = updateZone(manifest, updatedZone, { now });
      applied = true;
    }
  }

  const updatedKeeper: KeeperAgent = applied
    ? { ...keeper, total_repairs_applied: keeper.total_repairs_applied + 1 }
    : keeper;

  return {
    keeper: updatedKeeper,
    manifest: updatedManifest,
    result: { action, applied, skipped: !applied, dry_run: false },
  };
}

// ─── Drain repair queue ───────────────────────────────────────────────────────

/**
 * Apply all queued repairs in order, up to config.max_repairs_per_sweep.
 * Returns updated keeper (queue drained), updated manifest, and results.
 */
export function drainRepairQueue(
  keeper: KeeperAgent,
  manifest: StationManifest,
  opts: { now?: string; dry_run?: boolean } = {}
): { keeper: KeeperAgent; manifest: StationManifest; results: KeeperRepairResult[] } {
  const now = opts.now ?? new Date().toISOString();
  const isDryRun = opts.dry_run ?? keeper.config.dry_run;
  const limit = keeper.config.max_repairs_per_sweep;

  let currentKeeper = keeper;
  let currentManifest = manifest;
  const results: KeeperRepairResult[] = [];

  const toApply = keeper.repair_queue.slice(0, limit);
  const remaining = keeper.repair_queue.slice(limit);

  for (const action of toApply) {
    const out = applyRepair(currentKeeper, currentManifest, action, { now, dry_run: isDryRun });
    currentKeeper = out.keeper;
    currentManifest = out.manifest;
    results.push(out.result);
  }

  // Replace queue with any that didn't fit the limit
  currentKeeper = { ...currentKeeper, repair_queue: remaining };

  return { keeper: currentKeeper, manifest: currentManifest, results };
}

// ─── Full sweep cycle ─────────────────────────────────────────────────────────

/**
 * Run a complete sweep-and-repair cycle:
 *   1. Call sweepKeepers on the manifest
 *   2. Convert sweep.repair_actions into the repair queue
 *   3. Drain the queue (up to max_repairs_per_sweep)
 *   4. Any sweep escalations that remain in the queue become keeper escalations
 *   5. Return updated keeper, manifest, and full run result
 */
export function runSweep(
  keeper: KeeperAgent,
  manifest: StationManifest,
  opts: { now?: string; dry_run?: boolean } = {}
): { keeper: KeeperAgent; manifest: StationManifest; result: KeeperRunResult } {
  const now = opts.now ?? new Date().toISOString();
  const isDryRun = opts.dry_run ?? keeper.config.dry_run;

  const sweep = sweepKeepers(manifest, {
    stale_threshold_ms: keeper.config.stale_threshold_ms,
    now,
  });

  // Load sweep actions into the queue (replace any pre-existing queue for this cycle)
  let currentKeeper: KeeperAgent = { ...keeper, repair_queue: sweep.repair_actions };

  // Drain
  const {
    keeper: afterDrain,
    manifest: updatedManifest,
    results,
  } = drainRepairQueue(currentKeeper, manifest, { now, dry_run: isDryRun });
  currentKeeper = afterDrain;

  // Collect new escalations produced this cycle
  const prevEscalationCount = keeper.total_escalations;
  const newEscalations = currentKeeper.escalation_log.slice(prevEscalationCount);

  // Advance sweep stats
  currentKeeper = {
    ...currentKeeper,
    last_sweep: now,
    total_sweeps: currentKeeper.total_sweeps + 1,
  };

  const result: KeeperRunResult = {
    schema_version: 'scbe_keeper_run_v1',
    keeper_id: keeper.keeper_id,
    run_at: now,
    sweep,
    repairs: results,
    new_escalations: newEscalations,
    zones_repaired: results.filter((r) => r.applied).length,
    zones_escalated: newEscalations.length,
    dry_run: isDryRun,
  };

  return { keeper: currentKeeper, manifest: updatedManifest, result };
}

// ─── Introspection ────────────────────────────────────────────────────────────

export interface KeeperStatus {
  schema_version: 'scbe_keeper_status_v1';
  keeper_id: string;
  last_sweep?: string;
  total_sweeps: number;
  total_repairs_applied: number;
  total_escalations: number;
  open_escalations: number;
  queued_repairs: number;
  config: KeeperConfig;
}

export function getKeeperStatus(keeper: KeeperAgent): KeeperStatus {
  return {
    schema_version: 'scbe_keeper_status_v1',
    keeper_id: keeper.keeper_id,
    last_sweep: keeper.last_sweep,
    total_sweeps: keeper.total_sweeps,
    total_repairs_applied: keeper.total_repairs_applied,
    total_escalations: keeper.total_escalations,
    open_escalations: keeper.escalation_log.filter((e) => !e.resolved).length,
    queued_repairs: keeper.repair_queue.length,
    config: keeper.config,
  };
}
