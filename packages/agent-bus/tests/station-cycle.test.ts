import { describe, it, expect } from 'vitest';
import { runStationCycle } from '../src/station-cycle.js';
import {
  createStation,
  addZone,
  observeZone,
  defaultGravityFrame,
} from '../src/station-manifest.js';
import { createKeeper } from '../src/keeper-agent.js';
import type { StationZone } from '../src/station-manifest.js';

const NOW = '2026-05-30T10:00:00.000Z';
const STALE = new Date(new Date(NOW).getTime() - 48 * 60 * 60 * 1000).toISOString();

// ─── Helpers ─────────────────────────────────────────────────────────────────

function makeZone(id: string, overrides: Partial<StationZone> = {}): StationZone {
  return {
    id,
    label: `Zone ${id}`,
    district: 'core',
    state: 'active',
    clearance: 'civilian',
    capacity: 5,
    occupants: [],
    linked_zones: [],
    gravity: defaultGravityFrame(id),
    updated_at: NOW,
    ...overrides,
  };
}

function buildGreenStation() {
  let manifest = createStation('STATION-ALPHA', { created_at: NOW });
  manifest = addZone(manifest, makeZone('z1'), { now: NOW });
  manifest = observeZone(manifest, 'z1', { now: NOW });
  return manifest;
}

function buildStaleAuditStation() {
  let manifest = createStation('STATION-BETA', { created_at: NOW });
  // Zone last updated 48 h ago → stale when threshold is 24 h
  manifest = addZone(manifest, makeZone('z-stale', { updated_at: STALE }), { now: NOW });
  manifest = observeZone(manifest, 'z-stale', { now: NOW });
  return manifest;
}

function buildOvercrowdedStation() {
  let manifest = createStation('STATION-GAMMA', { created_at: NOW });
  manifest = addZone(
    manifest,
    makeZone('z-crowd', { capacity: 2, occupants: ['agent-a', 'agent-b', 'agent-c'] }),
    { now: NOW }
  );
  manifest = observeZone(manifest, 'z-crowd', { now: NOW });
  return manifest;
}

// ─── runStationCycle — schema & structure ─────────────────────────────────────

describe('runStationCycle schema', () => {
  it('returns correct schema_version', () => {
    const manifest = buildGreenStation();
    const keeper = createKeeper('keeper-1');
    const result = runStationCycle(manifest, keeper, { now: NOW });
    expect(result.schema_version).toBe('scbe_station_cycle_v1');
  });

  it('populates cycle_id and cycle_at', () => {
    const manifest = buildGreenStation();
    const keeper = createKeeper('keeper-1');
    const result = runStationCycle(manifest, keeper, { now: NOW });
    expect(result.cycle_id).toMatch(/^cycle-/);
    expect(result.cycle_at).toBe(NOW);
  });

  it('returns a PollyOperatorBrief with matching schema', () => {
    const manifest = buildGreenStation();
    const keeper = createKeeper('keeper-1');
    const result = runStationCycle(manifest, keeper, { now: NOW });
    expect(result.brief.schema_version).toBe('scbe_polly_operator_brief_v1');
    expect(result.brief.station_id).toBe('STATION-ALPHA');
  });

  it('returns a KeeperRunResult with matching schema', () => {
    const manifest = buildGreenStation();
    const keeper = createKeeper('keeper-1');
    const result = runStationCycle(manifest, keeper, { now: NOW });
    expect(result.keeperRun.schema_version).toBe('scbe_keeper_run_v1');
    expect(result.keeperRun.keeper_id).toBe('keeper-1');
  });
});

// ─── Green cycle (nothing to repair) ─────────────────────────────────────────

describe('green station cycle', () => {
  it('brief health is not critical when station has an observed zone', () => {
    const manifest = buildGreenStation();
    const keeper = createKeeper('keeper-1');
    const result = runStationCycle(manifest, keeper, { now: NOW });
    // Station with a single unrouted zone (no linked_zones) is amber, not critical/red
    expect(['green', 'amber']).toContain(result.brief.health);
    expect(result.brief.health).not.toBe('critical');
    expect(result.brief.health).not.toBe('red');
  });

  it('all suggested handoffs are in HELD state', () => {
    const manifest = buildGreenStation();
    const keeper = createKeeper('keeper-1');
    const result = runStationCycle(manifest, keeper, { now: NOW });
    for (const h of result.suggestedHandoffs) {
      expect(h.state).toBe('HELD');
    }
  });

  it('all suggested handoffs have auto authority', () => {
    const manifest = buildGreenStation();
    const keeper = createKeeper('keeper-1');
    const result = runStationCycle(manifest, keeper, { now: NOW });
    for (const h of result.suggestedHandoffs) {
      expect(h.authority).toBe('auto');
    }
  });

  it('suggestedHandoffs is non-empty (at least one auto action exists)', () => {
    const manifest = buildGreenStation();
    const keeper = createKeeper('keeper-1');
    const result = runStationCycle(manifest, keeper, { now: NOW });
    expect(result.suggestedHandoffs.length).toBeGreaterThan(0);
  });
});

// ─── Keeper repairs cycle ─────────────────────────────────────────────────────

describe('keeper repairs stale zone', () => {
  it('schedule_audit repair is applied when zone is stale', () => {
    const manifest = buildStaleAuditStation();
    const keeper = createKeeper('keeper-2', { stale_threshold_ms: 24 * 60 * 60 * 1000 });
    const result = runStationCycle(manifest, keeper, { now: NOW });
    expect(result.keeperRun.zones_repaired).toBeGreaterThan(0);
  });

  it('updated keeper has advanced total_sweeps', () => {
    const manifest = buildStaleAuditStation();
    const keeper = createKeeper('keeper-2');
    const result = runStationCycle(manifest, keeper, { now: NOW });
    expect(result.keeper.total_sweeps).toBe(keeper.total_sweeps + 1);
    expect(result.keeper.last_sweep).toBe(NOW);
  });

  it('does not mutate input manifest', () => {
    const manifest = buildStaleAuditStation();
    const originalUpdatedAt = manifest.updated_at;
    const keeper = createKeeper('keeper-2');
    runStationCycle(manifest, keeper, { now: NOW });
    expect(manifest.updated_at).toBe(originalUpdatedAt);
  });

  it('does not mutate input keeper', () => {
    const manifest = buildStaleAuditStation();
    const keeper = createKeeper('keeper-2');
    const originalSweeps = keeper.total_sweeps;
    runStationCycle(manifest, keeper, { now: NOW });
    expect(keeper.total_sweeps).toBe(originalSweeps);
  });
});

describe('keeper evicts excess occupants', () => {
  it('evict_excess_occupants is applied when zone is over capacity', () => {
    const manifest = buildOvercrowdedStation();
    const keeper = createKeeper('keeper-3');
    const result = runStationCycle(manifest, keeper, { now: NOW });
    expect(result.keeperRun.zones_repaired).toBeGreaterThan(0);
  });
});

// ─── Dry run mode ────────────────────────────────────────────────────────────

describe('dry run mode', () => {
  it('dry run does not repair zones', () => {
    const manifest = buildStaleAuditStation();
    const keeper = createKeeper('keeper-4', { stale_threshold_ms: 24 * 60 * 60 * 1000 });
    const result = runStationCycle(manifest, keeper, { now: NOW, dryRun: true });
    expect(result.keeperRun.zones_repaired).toBe(0);
    expect(result.keeperRun.dry_run).toBe(true);
  });

  it('dry run: output manifest is same object reference as input', () => {
    const manifest = buildStaleAuditStation();
    const keeper = createKeeper('keeper-4', { stale_threshold_ms: 24 * 60 * 60 * 1000 });
    const result = runStationCycle(manifest, keeper, { now: NOW, dryRun: true });
    expect(result.manifest).toBe(manifest);
  });
});

// ─── Action-to-handoff translation ───────────────────────────────────────────

describe('action to handoff translation', () => {
  it('only requires_human=false actions become handoffs', () => {
    const manifest = buildGreenStation();
    const keeper = createKeeper('keeper-5');
    const result = runStationCycle(manifest, keeper, { now: NOW });
    const humanActions = result.brief.actions.filter((a) => a.requires_human);
    const humanTasks = humanActions.map((a) => a.command);
    const handoffTasks = result.suggestedHandoffs.map((h) => h.mission.task);
    for (const task of humanTasks) {
      expect(handoffTasks).not.toContain(task);
    }
  });

  it('handoff mission.task matches Polly action command', () => {
    const manifest = buildGreenStation();
    const keeper = createKeeper('keeper-5');
    const result = runStationCycle(manifest, keeper, { now: NOW });
    const autoActions = result.brief.actions.filter((a) => !a.requires_human);
    const autoCommands = autoActions.map((a) => a.command).sort();
    const handoffTasks = result.suggestedHandoffs.map((h) => h.mission.task).sort();
    expect(handoffTasks).toEqual(autoCommands);
  });

  it('handoff mission payload contains action_id and reason', () => {
    const manifest = buildGreenStation();
    const keeper = createKeeper('keeper-5');
    const result = runStationCycle(manifest, keeper, { now: NOW });
    if (result.suggestedHandoffs.length > 0) {
      const payload = result.suggestedHandoffs[0].mission.payload;
      expect(payload).toHaveProperty('action_id');
      expect(payload).toHaveProperty('reason');
    }
  });

  it('handoff issuer_id matches keeper_id', () => {
    const manifest = buildGreenStation();
    const keeper = createKeeper('keeper-5');
    const result = runStationCycle(manifest, keeper, { now: NOW });
    for (const h of result.suggestedHandoffs) {
      expect(h.issuer_id).toBe('keeper-5');
    }
  });

  it('deadline propagated to handoffs when handoffDeadlineMs is set', () => {
    const manifest = buildGreenStation();
    const keeper = createKeeper('keeper-5');
    const result = runStationCycle(manifest, keeper, {
      now: NOW,
      handoffDeadlineMs: 60_000,
    });
    for (const h of result.suggestedHandoffs) {
      expect(h.deadline_at).toBeDefined();
      expect(new Date(h.deadline_at!).getTime()).toBe(new Date(NOW).getTime() + 60_000);
    }
  });
});

// ─── Multi-cycle chaining ────────────────────────────────────────────────────

describe('multi-cycle chaining', () => {
  it('cycle IDs are unique across back-to-back cycles', () => {
    const manifest = buildGreenStation();
    const keeper = createKeeper('keeper-6');
    const r1 = runStationCycle(manifest, keeper, { now: NOW });
    const r2 = runStationCycle(r1.manifest, r1.keeper, { now: NOW });
    expect(r1.cycle_id).not.toBe(r2.cycle_id);
  });

  it('total_sweeps increments each cycle', () => {
    const manifest = buildGreenStation();
    const keeper = createKeeper('keeper-6');
    const r1 = runStationCycle(manifest, keeper, { now: NOW });
    const r2 = runStationCycle(r1.manifest, r1.keeper, { now: NOW });
    expect(r2.keeper.total_sweeps).toBe(2);
  });

  it('second cycle sees repairs from first (stale zone audited, not re-audited)', () => {
    const manifest = buildStaleAuditStation();
    const keeper = createKeeper('keeper-6', { stale_threshold_ms: 24 * 60 * 60 * 1000 });
    // First cycle repairs the stale zone
    const r1 = runStationCycle(manifest, keeper, { now: NOW });
    expect(r1.keeperRun.zones_repaired).toBeGreaterThan(0);
    // Second cycle: zone now has audit_receipt — should not be stale again
    const r2 = runStationCycle(r1.manifest, r1.keeper, { now: NOW });
    expect(r2.keeperRun.zones_repaired).toBe(0);
  });
});
