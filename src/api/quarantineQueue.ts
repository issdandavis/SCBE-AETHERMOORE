/**
 * @file quarantineQueue.ts
 * @module api/quarantineQueue
 * @layer Layer 13
 * @component QUARANTINE Queue Manager
 *
 * Solves the human-in-the-loop approval backlog problem for QUARANTINE-tier
 * decisions (partial trust zone between ALLOW and DENY).
 *
 * Three backlog relief mechanisms:
 *   1. Trust decay with auto-deny — items that sit too long auto-DENY
 *   2. Cohort batching — similar items grouped for bulk review
 *   3. Probabilistic auto-release — low-risk quarantined items released
 *      if the recent QUARANTINE→ALLOW ratio exceeds a threshold
 *
 * A3: Causality — FIFO ordering within priority bands
 * A4: Symmetry — same risk score → same treatment regardless of actor
 */

import { createHash, randomBytes } from 'crypto';

// ============================================================================
// Types
// ============================================================================

/** Priority band for quarantine items */
export type QuarantinePriority = 'low' | 'medium' | 'high' | 'critical';

/** Resolution outcome */
export type QuarantineResolution = 'RELEASED' | 'DENIED' | 'EXPIRED' | 'AUTO_RELEASED';

/** Quarantine queue item */
export interface QuarantineItem {
  /** Unique item ID */
  id: string;
  /** Original request ID */
  requestId: string;
  /** Actor that triggered quarantine */
  actorId: string;
  /** Intent of the original request */
  intent: string;
  /** Risk score from L13 [0, 1] */
  riskScore: number;
  /** Harmonic wall cost at time of quarantine */
  harmonicCost: number;
  /** Rationale for quarantine */
  rationale: string;
  /** Timestamp when quarantined */
  enqueuedAt: number;
  /** When the item expires (auto-DENY) */
  expiresAt: number;
  /** Priority band */
  priority: QuarantinePriority;
  /** Cohort key for batch grouping */
  cohortKey: string;
  /** Trust score at time of quarantine */
  trustAtEnqueue: number;
  /** Current decayed trust */
  decayedTrust: number;
  /** Resolution (null if still pending) */
  resolution: QuarantineResolution | null;
  /** Who resolved it (null if auto or pending) */
  resolvedBy: string | null;
  /** When resolved (null if pending) */
  resolvedAt: number | null;
}

/** Queue statistics */
export interface QueueStats {
  /** Total items currently pending */
  pending: number;
  /** Items by priority */
  byPriority: Record<QuarantinePriority, number>;
  /** Number of distinct cohorts */
  cohorts: number;
  /** Items expiring in next 5 minutes */
  expiringImminently: number;
  /** Historical resolution rate: RELEASED / (RELEASED + DENIED) */
  releaseRate: number;
  /** Average time-to-resolution in ms */
  avgResolutionMs: number;
  /** Current backlog pressure [0, 1] */
  pressure: number;
}

/** Queue configuration */
export interface QuarantineConfig {
  /** Maximum pending items before pressure relief activates */
  maxPending: number;
  /** Default TTL for quarantine items in ms (default: 1 hour) */
  defaultTtlMs: number;
  /** Trust decay rate per second (default: 0.001) */
  trustDecayPerSec: number;
  /** Trust threshold below which items auto-deny (default: 0.15) */
  autoDeNyTrustThreshold: number;
  /** Release rate threshold for probabilistic auto-release (default: 0.8) */
  autoReleaseRateThreshold: number;
  /** Max risk score for probabilistic auto-release (default: 0.45) */
  autoReleaseMaxRisk: number;
  /** Pressure threshold to trigger backlog relief (default: 0.7) */
  pressureThreshold: number;
}

// ============================================================================
// Defaults
// ============================================================================

const DEFAULT_CONFIG: QuarantineConfig = {
  maxPending: 1000,
  defaultTtlMs: 60 * 60 * 1000, // 1 hour
  trustDecayPerSec: 0.001,
  autoDeNyTrustThreshold: 0.15,
  autoReleaseRateThreshold: 0.8,
  autoReleaseMaxRisk: 0.45,
  pressureThreshold: 0.7,
};

// ============================================================================
// Quarantine Queue Manager
// ============================================================================

/**
 * QUARANTINE Queue Manager with backlog pressure relief.
 *
 * Prevents approval backlogs via:
 * - Continuous trust decay (items get riskier the longer they wait)
 * - TTL-based auto-deny (unreviewed items expire to DENY)
 * - Cohort batching (similar items grouped for bulk action)
 * - Probabilistic auto-release under high release rate regimes
 */
export class QuarantineQueue {
  private readonly config: QuarantineConfig;
  private readonly pending: Map<string, QuarantineItem> = new Map();
  private readonly resolved: QuarantineItem[] = [];
  private readonly maxResolved = 10_000;

  constructor(config?: Partial<QuarantineConfig>) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Enqueue a request for human review.
   *
   * Returns the quarantine item with assigned priority and cohort.
   */
  enqueue(params: {
    requestId: string;
    actorId: string;
    intent: string;
    riskScore: number;
    harmonicCost: number;
    rationale: string;
    trustScore: number;
    ttlMs?: number;
  }): QuarantineItem {
    const now = Date.now();
    const ttl = params.ttlMs ?? this.config.defaultTtlMs;

    const item: QuarantineItem = {
      id: this.generateId(),
      requestId: params.requestId,
      actorId: params.actorId,
      intent: params.intent,
      riskScore: params.riskScore,
      harmonicCost: params.harmonicCost,
      rationale: params.rationale,
      enqueuedAt: now,
      expiresAt: now + ttl,
      priority: this.assignPriority(params.riskScore),
      cohortKey: this.computeCohortKey(params.intent, params.riskScore),
      trustAtEnqueue: params.trustScore,
      decayedTrust: params.trustScore,
      resolution: null,
      resolvedBy: null,
      resolvedAt: null,
    };

    this.pending.set(item.id, item);

    // Run maintenance after enqueue
    this.runMaintenance();

    return item;
  }

  /**
   * Release a quarantined item (human approves).
   */
  release(itemId: string, approver: string): QuarantineItem | null {
    return this.resolve(itemId, 'RELEASED', approver);
  }

  /**
   * Deny a quarantined item (human rejects).
   */
  deny(itemId: string, approver: string): QuarantineItem | null {
    return this.resolve(itemId, 'DENIED', approver);
  }

  /**
   * Bulk-release an entire cohort (batch approval).
   *
   * Returns array of released items.
   */
  releaseCohort(cohortKey: string, approver: string): QuarantineItem[] {
    const cohortItems = this.getCohort(cohortKey);
    const released: QuarantineItem[] = [];
    for (const item of cohortItems) {
      const resolved = this.resolve(item.id, 'RELEASED', approver);
      if (resolved) released.push(resolved);
    }
    return released;
  }

  /**
   * Bulk-deny an entire cohort.
   */
  denyCohort(cohortKey: string, approver: string): QuarantineItem[] {
    const cohortItems = this.getCohort(cohortKey);
    const denied: QuarantineItem[] = [];
    for (const item of cohortItems) {
      const resolved = this.resolve(item.id, 'DENIED', approver);
      if (resolved) denied.push(resolved);
    }
    return denied;
  }

  /**
   * Get all items in a cohort (for batch review).
   */
  getCohort(cohortKey: string): QuarantineItem[] {
    return Array.from(this.pending.values()).filter((i) => i.cohortKey === cohortKey);
  }

  /**
   * List all distinct cohorts with item counts.
   */
  listCohorts(): Array<{ cohortKey: string; count: number; avgRisk: number }> {
    const groups = new Map<string, QuarantineItem[]>();
    const items = Array.from(this.pending.values());
    for (const item of items) {
      const list = groups.get(item.cohortKey) ?? [];
      list.push(item);
      groups.set(item.cohortKey, list);
    }
    return Array.from(groups.entries()).map(([key, items]) => ({
      cohortKey: key,
      count: items.length,
      avgRisk: items.reduce((sum, i) => sum + i.riskScore, 0) / items.length,
    }));
  }

  /**
   * Get queue statistics.
   */
  getStats(): QueueStats {
    const now = Date.now();
    const pendingItems = Array.from(this.pending.values());

    const byPriority: Record<QuarantinePriority, number> = {
      low: 0,
      medium: 0,
      high: 0,
      critical: 0,
    };
    for (const item of pendingItems) {
      byPriority[item.priority]++;
    }

    const expiringImminently = pendingItems.filter((i) => i.expiresAt - now < 5 * 60 * 1000).length;

    const cohortSet = new Set(pendingItems.map((i) => i.cohortKey));

    // Release rate from resolved history
    const released = this.resolved.filter((i) => i.resolution === 'RELEASED').length;
    const denied = this.resolved.filter(
      (i) => i.resolution === 'DENIED' || i.resolution === 'EXPIRED'
    ).length;
    const releaseRate = released + denied > 0 ? released / (released + denied) : 0.5;

    // Average resolution time
    const resolvedWithTime = this.resolved.filter((i) => i.resolvedAt !== null);
    const avgResolutionMs =
      resolvedWithTime.length > 0
        ? resolvedWithTime.reduce((sum, i) => sum + (i.resolvedAt! - i.enqueuedAt), 0) /
          resolvedWithTime.length
        : 0;

    // Backlog pressure: ratio of pending to capacity
    const pressure = Math.min(1, pendingItems.length / this.config.maxPending);

    return {
      pending: pendingItems.length,
      byPriority,
      cohorts: cohortSet.size,
      expiringImminently,
      releaseRate,
      avgResolutionMs,
      pressure,
    };
  }

  /**
   * Get a pending item by ID.
   */
  getItem(itemId: string): QuarantineItem | null {
    return this.pending.get(itemId) ?? null;
  }

  /**
   * Get all pending items sorted by priority then enqueue time.
   */
  getPending(): QuarantineItem[] {
    const priorityOrder: Record<QuarantinePriority, number> = {
      critical: 0,
      high: 1,
      medium: 2,
      low: 3,
    };
    return Array.from(this.pending.values()).sort((a, b) => {
      const pd = priorityOrder[a.priority] - priorityOrder[b.priority];
      if (pd !== 0) return pd;
      return a.enqueuedAt - b.enqueuedAt; // A3: FIFO within band
    });
  }

  // --------------------------------------------------------------------------
  // Maintenance & Backlog Relief
  // --------------------------------------------------------------------------

  /**
   * Run maintenance cycle: trust decay, expiration, auto-release.
   *
   * Call periodically or after each enqueue.
   */
  runMaintenance(): { expired: number; autoReleased: number; autoDenied: number } {
    const now = Date.now();
    let expired = 0;
    let autoReleased = 0;
    let autoDenied = 0;

    for (const [id, item] of Array.from(this.pending.entries())) {
      // 1. Trust decay
      const elapsedSec = (now - item.enqueuedAt) / 1000;
      item.decayedTrust = Math.max(0, item.trustAtEnqueue - this.config.trustDecayPerSec * elapsedSec);

      // 2. Auto-deny on trust exhaustion
      if (item.decayedTrust < this.config.autoDeNyTrustThreshold) {
        this.resolve(id, 'EXPIRED', null);
        autoDenied++;
        continue;
      }

      // 3. TTL expiration
      if (now >= item.expiresAt) {
        this.resolve(id, 'EXPIRED', null);
        expired++;
        continue;
      }
    }

    // 4. Probabilistic auto-release under high release regime
    const stats = this.getStats();
    if (
      stats.pressure > this.config.pressureThreshold &&
      stats.releaseRate > this.config.autoReleaseRateThreshold
    ) {
      autoReleased = this.autoReleaseLowRisk();
    }

    return { expired, autoReleased, autoDenied };
  }

  /**
   * Auto-release low-risk items when release rate is historically high.
   *
   * Only releases items with riskScore below autoReleaseMaxRisk.
   * Returns number of items auto-released.
   */
  private autoReleaseLowRisk(): number {
    let released = 0;
    for (const [id, item] of Array.from(this.pending.entries())) {
      if (item.riskScore <= this.config.autoReleaseMaxRisk && item.priority === 'low') {
        this.resolve(id, 'AUTO_RELEASED', null);
        released++;
      }
    }
    return released;
  }

  // --------------------------------------------------------------------------
  // Internal
  // --------------------------------------------------------------------------

  private resolve(
    itemId: string,
    resolution: QuarantineResolution,
    approver: string | null
  ): QuarantineItem | null {
    const item = this.pending.get(itemId);
    if (!item) return null;

    item.resolution = resolution;
    item.resolvedBy = approver;
    item.resolvedAt = Date.now();

    this.pending.delete(itemId);
    this.resolved.push(item);

    // Cap resolved history
    if (this.resolved.length > this.maxResolved) {
      this.resolved.splice(0, this.resolved.length - this.maxResolved);
    }

    return item;
  }

  private assignPriority(riskScore: number): QuarantinePriority {
    if (riskScore > 0.7) return 'critical';
    if (riskScore > 0.55) return 'high';
    if (riskScore > 0.4) return 'medium';
    return 'low';
  }

  /**
   * Compute cohort key from intent + quantized risk.
   *
   * Groups similar requests together for batch review.
   * A4: Symmetry — same intent + similar risk → same cohort.
   */
  private computeCohortKey(intent: string, riskScore: number): string {
    const riskBucket = Math.floor(riskScore * 10); // 0.0-0.1 → 0, 0.1-0.2 → 1, etc.
    return createHash('sha256').update(`${intent}:${riskBucket}`).digest('hex').slice(0, 12);
  }

  private generateId(): string {
    return `q-${Date.now().toString(36)}-${randomBytes(6).toString('hex')}`;
  }
}
