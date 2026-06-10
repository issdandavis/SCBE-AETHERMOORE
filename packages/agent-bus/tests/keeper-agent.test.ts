import { describe, it, expect } from 'vitest';
import {
  createKeeper,
  queueRepair,
  clearRepairQueue,
  escalate,
  resolveEscalation,
  applyRepair,
  drainRepairQueue,
  runSweep,
  getKeeperStatus,
  type KeeperAgent,
} from '../src/keeper-agent.js';
import {
  createStation,
  addZone,
  type StationZone,
  defaultGravityFrame,
} from '../src/station-manifest.js';
import type { KeeperRepairAction } from '../src/station-manifest.js';

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const NOW = '2026-05-30T00:00:00.000Z';
const STALE_NOW = '2026-06-01T00:00:00.000Z';

function makeZone(id: string, overrides: Partial<StationZone> = {}): StationZone {
  return {
    id,
    label: `Zone ${id}`,
    district: 'code',
    state: 'active',
    gravity: defaultGravityFrame(id),
    clearance: 'none',
    capacity: 4,
    occupants: [],
    linked_zones: [],
    updated_at: NOW,
    ...overrides,
  };
}

function freshStation() {
  return createStation('STATION-TEST', { now: NOW });
}

// ─── createKeeper ─────────────────────────────────────────────────────────────

describe('createKeeper', () => {
  it('produces a valid keeper agent', () => {
    const k = createKeeper('keeper-alpha');
    expect(k.schema_version).toBe('scbe_keeper_agent_v1');
    expect(k.keeper_id).toBe('keeper-alpha');
    expect(k.repair_queue).toHaveLength(0);
    expect(k.escalation_log).toHaveLength(0);
    expect(k.total_sweeps).toBe(0);
    expect(k.total_repairs_applied).toBe(0);
    expect(k.total_escalations).toBe(0);
    expect(k.config.dry_run).toBe(false);
  });

  it('accepts config overrides', () => {
    const k = createKeeper('k', {
      dry_run: true,
      max_repairs_per_sweep: 5,
      sweep_interval_ms: 60_000,
    });
    expect(k.config.dry_run).toBe(true);
    expect(k.config.max_repairs_per_sweep).toBe(5);
    expect(k.config.sweep_interval_ms).toBe(60_000);
  });
});

// ─── queueRepair / clearRepairQueue ──────────────────────────────────────────

describe('queueRepair', () => {
  it('appends an action to the repair queue', () => {
    const k = createKeeper('k');
    const action: KeeperRepairAction = { zone_id: 'z1', action: 'schedule_audit', priority: 'low' };
    const k2 = queueRepair(k, action);
    expect(k2.repair_queue).toHaveLength(1);
    expect(k2.repair_queue[0]).toEqual(action);
  });

  it('is immutable — original queue unchanged', () => {
    const k = createKeeper('k');
    queueRepair(k, { zone_id: 'z1', action: 'schedule_audit', priority: 'low' });
    expect(k.repair_queue).toHaveLength(0);
  });
});

describe('clearRepairQueue', () => {
  it('empties the queue', () => {
    let k = createKeeper('k');
    k = queueRepair(k, { zone_id: 'z1', action: 'schedule_audit', priority: 'low' });
    k = clearRepairQueue(k);
    expect(k.repair_queue).toHaveLength(0);
  });
});

// ─── escalate / resolveEscalation ─────────────────────────────────────────────

describe('escalate', () => {
  it('appends to escalation log and increments counter', () => {
    const k = createKeeper('k');
    const k2 = escalate(k, 'z1', 'review_quarantine', 'quarantine_requires_governance', {
      now: NOW,
    });
    expect(k2.escalation_log).toHaveLength(1);
    expect(k2.escalation_log[0].zone_id).toBe('z1');
    expect(k2.escalation_log[0].resolved).toBe(false);
    expect(k2.total_escalations).toBe(1);
  });

  it('is immutable', () => {
    const k = createKeeper('k');
    escalate(k, 'z1', 'review_quarantine', 'reason', { now: NOW });
    expect(k.escalation_log).toHaveLength(0);
  });
});

describe('resolveEscalation', () => {
  it('marks matching escalation as resolved', () => {
    let k = createKeeper('k');
    k = escalate(k, 'z1', 'review_quarantine', 'reason', { now: NOW });
    k = resolveEscalation(k, 'z1', 'review_quarantine');
    expect(k.escalation_log[0].resolved).toBe(true);
  });

  it('does not resolve different actions', () => {
    let k = createKeeper('k');
    k = escalate(k, 'z1', 'review_quarantine', 'reason', { now: NOW });
    k = resolveEscalation(k, 'z1', 'add_transit_link');
    expect(k.escalation_log[0].resolved).toBe(false);
  });
});

// ─── applyRepair ──────────────────────────────────────────────────────────────

describe('applyRepair — schedule_audit', () => {
  it('stamps zone with a receipt ID and marks applied', () => {
    let m = freshStation();
    m = addZone(m, makeZone('z1', { updated_at: NOW }), { now: NOW });
    const k = createKeeper('k');
    const action: KeeperRepairAction = {
      zone_id: 'z1',
      action: 'schedule_audit',
      priority: 'medium',
    };
    const { keeper: k2, manifest: m2, result } = applyRepair(k, m, action, { now: NOW });
    expect(result.applied).toBe(true);
    expect(result.skipped).toBe(false);
    expect(m2.zones['z1'].audit_receipt).toBeTruthy();
    expect(k2.total_repairs_applied).toBe(1);
  });

  it('does not mutate on dry_run', () => {
    let m = freshStation();
    m = addZone(m, makeZone('z1'), { now: NOW });
    const k = createKeeper('k', { dry_run: true });
    const action: KeeperRepairAction = {
      zone_id: 'z1',
      action: 'schedule_audit',
      priority: 'medium',
    };
    const { manifest: m2, result } = applyRepair(k, m, action, { now: NOW });
    expect(result.applied).toBe(false);
    expect(result.dry_run).toBe(true);
    expect(m2.zones['z1'].audit_receipt).toBeUndefined();
  });

  it('skips if zone does not exist', () => {
    const m = freshStation();
    const k = createKeeper('k');
    const action: KeeperRepairAction = {
      zone_id: 'ghost',
      action: 'schedule_audit',
      priority: 'low',
    };
    const { result } = applyRepair(k, m, action, { now: NOW });
    expect(result.applied).toBe(false);
    expect(result.skipped).toBe(true);
  });
});

describe('applyRepair — evict_excess_occupants', () => {
  it('trims occupants to capacity', () => {
    let m = freshStation();
    m = addZone(m, makeZone('z1', { capacity: 2, occupants: ['a', 'b', 'c', 'd'] }), { now: NOW });
    const k = createKeeper('k');
    const action: KeeperRepairAction = {
      zone_id: 'z1',
      action: 'evict_excess_occupants',
      priority: 'medium',
    };
    const { manifest: m2, result } = applyRepair(k, m, action, { now: NOW });
    expect(result.applied).toBe(true);
    expect(m2.zones['z1'].occupants).toHaveLength(2);
    expect(m2.zones['z1'].occupants).toEqual(['a', 'b']);
  });

  it('no-ops when occupants <= capacity', () => {
    let m = freshStation();
    m = addZone(m, makeZone('z1', { capacity: 4, occupants: ['a'] }), { now: NOW });
    const k = createKeeper('k');
    const action: KeeperRepairAction = {
      zone_id: 'z1',
      action: 'evict_excess_occupants',
      priority: 'low',
    };
    const { manifest: m2, result } = applyRepair(k, m, action, { now: NOW });
    expect(result.applied).toBe(false);
    expect(result.skipped).toBe(true);
    expect(m2.zones['z1'].occupants).toHaveLength(1);
  });
});

describe('applyRepair — escalation-only actions', () => {
  it('escalates review_quarantine without modifying manifest', () => {
    let m = freshStation();
    m = addZone(m, makeZone('z1', { state: 'quarantined' }), { now: NOW });
    const k = createKeeper('k');
    const action: KeeperRepairAction = {
      zone_id: 'z1',
      action: 'review_quarantine',
      priority: 'high',
    };
    const { keeper: k2, manifest: m2, result } = applyRepair(k, m, action, { now: NOW });
    expect(result.applied).toBe(false);
    expect(result.skipped).toBe(true);
    expect(k2.total_escalations).toBe(1);
    expect(m2.zones['z1'].state).toBe('quarantined'); // untouched
  });

  it('escalates add_transit_link', () => {
    let m = freshStation();
    m = addZone(m, makeZone('z1'), { now: NOW });
    const k = createKeeper('k');
    const action: KeeperRepairAction = {
      zone_id: 'z1',
      action: 'add_transit_link',
      priority: 'low',
    };
    const { keeper: k2, result } = applyRepair(k, m, action, { now: NOW });
    expect(result.applied).toBe(false);
    expect(result.skipped).toBe(true);
    expect(k2.escalation_log[0].action).toBe('add_transit_link');
  });

  it('skips unknown action with note', () => {
    const m = freshStation();
    const k = createKeeper('k');
    const action: KeeperRepairAction = {
      zone_id: 'z1',
      action: 'warp_reality' as string,
      priority: 'low',
    };
    const { result } = applyRepair(k, m, action, { now: NOW });
    expect(result.applied).toBe(false);
    expect(result.skip_reason).toBe('unknown_repair_action');
  });
});

// ─── drainRepairQueue ─────────────────────────────────────────────────────────

describe('drainRepairQueue', () => {
  it('applies all queued repairs and empties the queue', () => {
    let m = freshStation();
    m = addZone(m, makeZone('z1'), { now: NOW });
    m = addZone(m, makeZone('z2'), { now: NOW });

    let k = createKeeper('k');
    k = queueRepair(k, { zone_id: 'z1', action: 'schedule_audit', priority: 'low' });
    k = queueRepair(k, { zone_id: 'z2', action: 'schedule_audit', priority: 'low' });

    const { keeper: k2, manifest: m2, results } = drainRepairQueue(k, m, { now: NOW });
    expect(results).toHaveLength(2);
    expect(results.every((r) => r.applied)).toBe(true);
    expect(k2.repair_queue).toHaveLength(0);
    expect(m2.zones['z1'].audit_receipt).toBeTruthy();
    expect(m2.zones['z2'].audit_receipt).toBeTruthy();
  });

  it('respects max_repairs_per_sweep limit', () => {
    let m = freshStation();
    for (let i = 0; i < 5; i++) m = addZone(m, makeZone(`z${i}`), { now: NOW });

    let k = createKeeper('k', { max_repairs_per_sweep: 2 });
    for (let i = 0; i < 5; i++) {
      k = queueRepair(k, { zone_id: `z${i}`, action: 'schedule_audit', priority: 'low' });
    }

    const { keeper: k2, results } = drainRepairQueue(k, m, { now: NOW });
    expect(results).toHaveLength(2);
    expect(k2.repair_queue).toHaveLength(3); // 3 left in queue
  });
});

// ─── runSweep ─────────────────────────────────────────────────────────────────

describe('runSweep — clean station', () => {
  it('produces a valid run result with no repairs', () => {
    const m = freshStation();
    const k = createKeeper('k');
    const { keeper: k2, result } = runSweep(k, m, { now: NOW });
    expect(result.schema_version).toBe('scbe_keeper_run_v1');
    expect(result.zones_repaired).toBe(0);
    expect(result.zones_escalated).toBe(0);
    expect(k2.total_sweeps).toBe(1);
    expect(k2.last_sweep).toBe(NOW);
  });
});

describe('runSweep — stale zones', () => {
  it('stamps stale zones with audit receipts', () => {
    let m = freshStation();
    // Zone updated 2 days ago, no audit receipt
    m = addZone(m, makeZone('z1', { updated_at: NOW }), { now: NOW });

    const k = createKeeper('k', { stale_threshold_ms: 3_600_000 }); // 1-hour threshold
    // Run sweep 2 days later → z1 is stale
    const { manifest: m2, result } = runSweep(k, m, { now: STALE_NOW });

    expect(result.zones_repaired).toBeGreaterThan(0);
    expect(m2.zones['z1'].audit_receipt).toBeTruthy();
  });
});

describe('runSweep — overcrowded zones', () => {
  it('evicts excess occupants', () => {
    let m = freshStation();
    m = addZone(m, makeZone('z1', { capacity: 2, occupants: ['a', 'b', 'c'] }), { now: NOW });

    const k = createKeeper('k');
    const { manifest: m2, result } = runSweep(k, m, { now: NOW });

    expect(result.zones_repaired).toBe(1);
    expect(m2.zones['z1'].occupants).toHaveLength(2);
  });
});

describe('runSweep — quarantined zones', () => {
  it('escalates quarantined zones without repairing them', () => {
    let m = freshStation();
    m = addZone(m, makeZone('z1', { state: 'quarantined' }), { now: NOW });

    const k = createKeeper('k');
    const { keeper: k2, manifest: m2, result } = runSweep(k, m, { now: NOW });

    expect(result.zones_escalated).toBeGreaterThan(0);
    expect(m2.zones['z1'].state).toBe('quarantined'); // not repaired
    expect(k2.total_escalations).toBeGreaterThan(0);
  });
});

describe('runSweep — unroutable zones', () => {
  it('escalates unroutable active zones', () => {
    let m = freshStation();
    // Active zone with no links and no transit nodes
    m = addZone(m, makeZone('z1', { linked_zones: [], state: 'active' }), { now: NOW });

    const k = createKeeper('k');
    const { result } = runSweep(k, m, { now: NOW });

    expect(result.zones_escalated).toBeGreaterThan(0);
  });
});

describe('runSweep — dry_run', () => {
  it('plans repairs but does not modify manifest', () => {
    let m = freshStation();
    m = addZone(m, makeZone('z1', { capacity: 1, occupants: ['a', 'b'] }), { now: NOW });

    const k = createKeeper('k', { dry_run: true });
    const { manifest: m2, result } = runSweep(k, m, { now: NOW });

    expect(result.dry_run).toBe(true);
    expect(result.zones_repaired).toBe(0); // nothing applied
    expect(m2.zones['z1'].occupants).toHaveLength(2); // unchanged
  });
});

describe('runSweep — counters accumulate across sweeps', () => {
  it('increments total_sweeps on each call', () => {
    let m = freshStation();
    m = addZone(m, makeZone('z1'), { now: NOW });
    let k = createKeeper('k');
    ({ keeper: k } = runSweep(k, m, { now: NOW }));
    ({ keeper: k } = runSweep(k, m, { now: NOW }));
    ({ keeper: k } = runSweep(k, m, { now: NOW }));
    expect(k.total_sweeps).toBe(3);
  });
});

// ─── getKeeperStatus ──────────────────────────────────────────────────────────

describe('getKeeperStatus', () => {
  it('returns correct status fields', () => {
    let k = createKeeper('k');
    k = escalate(k, 'z1', 'review_quarantine', 'reason', { now: NOW });
    k = queueRepair(k, { zone_id: 'z2', action: 'schedule_audit', priority: 'low' });

    const status = getKeeperStatus(k);
    expect(status.schema_version).toBe('scbe_keeper_status_v1');
    expect(status.keeper_id).toBe('k');
    expect(status.open_escalations).toBe(1);
    expect(status.queued_repairs).toBe(1);
    expect(status.total_escalations).toBe(1);
  });

  it('open_escalations decrements after resolve', () => {
    let k = createKeeper('k');
    k = escalate(k, 'z1', 'review_quarantine', 'reason', { now: NOW });
    k = resolveEscalation(k, 'z1', 'review_quarantine');
    expect(getKeeperStatus(k).open_escalations).toBe(0);
  });
});
