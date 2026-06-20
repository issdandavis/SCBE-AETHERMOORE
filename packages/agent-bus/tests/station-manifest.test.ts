import { describe, it, expect } from 'vitest';
import {
  createStation,
  addZone,
  removeZone,
  updateZone,
  getZone,
  observeZone,
  canEnterZone,
  resolveGravity,
  planTransit,
  getDockingPort,
  dockAgent,
  undockAgent,
  sweepKeepers,
  summarizeStation,
  reportDamage,
  defaultGravityFrame,
  defaultCulturalProtocol,
  ALL_DISTRICTS,
  type StationZone,
  type TransitNode,
  type DockingPort,
} from '../src/station-manifest.js';

// ─── Helpers ──────────────────────────────────────────────────────────────────

const NOW = '2026-05-30T00:00:00.000Z';
const STALE_NOW = '2026-06-01T00:00:00.000Z'; // 2 days later

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

function makePort(id: string, zoneId: string, overrides: Partial<DockingPort> = {}): DockingPort {
  return {
    id,
    zone_id: zoneId,
    protocol: 'agent-pad',
    ...overrides,
  };
}

// ─── createStation ────────────────────────────────────────────────────────────

describe('createStation', () => {
  it('produces a valid empty manifest', () => {
    const m = createStation('STATION-ALPHA', { now: NOW });
    expect(m.schema_version).toBe('scbe_station_manifest_v1');
    expect(m.station_id).toBe('STATION-ALPHA');
    expect(m.created_at).toBe(NOW);
    expect(m.updated_at).toBe(NOW);
    expect(Object.keys(m.zones)).toHaveLength(0);
    expect(m.fog_of_war).toHaveLength(0);
  });

  it('initialises cultural protocols for all districts', () => {
    const m = createStation('S', { now: NOW });
    for (const district of ALL_DISTRICTS) {
      expect(m.cultural_protocols[district]).toBeDefined();
      expect(m.cultural_protocols[district]!.district).toBe(district);
    }
  });

  it('respects a custom district subset', () => {
    const m = createStation('S', { districts: ['code', 'security'], now: NOW });
    expect(m.cultural_protocols['code']).toBeDefined();
    expect(m.cultural_protocols['security']).toBeDefined();
    expect(m.cultural_protocols['writing']).toBeUndefined();
  });
});

// ─── Zone operations ──────────────────────────────────────────────────────────

describe('addZone', () => {
  it('adds zone to zones and district index', () => {
    const m = createStation('S', { now: NOW });
    const zone = makeZone('z1', { district: 'research' });
    const m2 = addZone(m, zone, { now: NOW });
    expect(m2.zones['z1']).toEqual(zone);
    expect(m2.districts['research']).toContain('z1');
  });

  it('puts zone in fog of war', () => {
    const m = createStation('S', { now: NOW });
    const m2 = addZone(m, makeZone('z1'), { now: NOW });
    expect(m2.fog_of_war).toContain('z1');
  });

  it('does not duplicate district entry on double add', () => {
    const m = addZone(createStation('S', { now: NOW }), makeZone('z1'), { now: NOW });
    const m2 = addZone(m, makeZone('z1'), { now: NOW });
    expect(m2.districts['code']!.filter((id) => id === 'z1')).toHaveLength(1);
  });

  it('is immutable — original manifest unchanged', () => {
    const m = createStation('S', { now: NOW });
    addZone(m, makeZone('z1'), { now: NOW });
    expect(Object.keys(m.zones)).toHaveLength(0);
  });
});

describe('removeZone', () => {
  it('removes zone from all indexes', () => {
    let m = createStation('S', { now: NOW });
    m = addZone(m, makeZone('z1'), { now: NOW });
    m = removeZone(m, 'z1', { now: NOW });
    expect(m.zones['z1']).toBeUndefined();
    expect(m.districts['code']).not.toContain('z1');
    expect(m.fog_of_war).not.toContain('z1');
  });

  it('is a no-op for unknown zone id', () => {
    const m = createStation('S', { now: NOW });
    const m2 = removeZone(m, 'nonexistent', { now: NOW });
    expect(m2.updated_at).toBe(m.updated_at);
  });
});

describe('updateZone', () => {
  it('replaces zone data', () => {
    let m = createStation('S', { now: NOW });
    m = addZone(m, makeZone('z1'), { now: NOW });
    const updated = makeZone('z1', { label: 'Updated', state: 'maintenance' });
    m = updateZone(m, updated, { now: NOW });
    expect(m.zones['z1'].label).toBe('Updated');
    expect(m.zones['z1'].state).toBe('maintenance');
  });

  it('is a no-op for unknown zone', () => {
    const m = createStation('S', { now: NOW });
    const m2 = updateZone(m, makeZone('ghost'), { now: NOW });
    expect(Object.keys(m2.zones)).toHaveLength(0);
  });
});

describe('getZone', () => {
  it('returns zone when present', () => {
    let m = createStation('S', { now: NOW });
    m = addZone(m, makeZone('z1'), { now: NOW });
    expect(getZone(m, 'z1')).not.toBeNull();
  });

  it('returns null for missing zone', () => {
    const m = createStation('S', { now: NOW });
    expect(getZone(m, 'missing')).toBeNull();
  });
});

describe('observeZone', () => {
  it('removes zone from fog of war', () => {
    let m = createStation('S', { now: NOW });
    m = addZone(m, makeZone('z1'), { now: NOW });
    expect(m.fog_of_war).toContain('z1');
    m = observeZone(m, 'z1', { now: NOW });
    expect(m.fog_of_war).not.toContain('z1');
  });
});

// ─── canEnterZone ─────────────────────────────────────────────────────────────

describe('canEnterZone', () => {
  it('allows entry when clearance is sufficient', () => {
    const zone = makeZone('z', { clearance: 'read_only' });
    expect(canEnterZone(zone, 'write')).toBe(true);
    expect(canEnterZone(zone, 'admin')).toBe(true);
  });

  it('denies entry when clearance is insufficient', () => {
    const zone = makeZone('z', { clearance: 'execute' });
    expect(canEnterZone(zone, 'none')).toBe(false);
    expect(canEnterZone(zone, 'write')).toBe(false);
  });

  it('blocks quarantined zones regardless of clearance', () => {
    const zone = makeZone('z', { clearance: 'none', state: 'quarantined' });
    expect(canEnterZone(zone, 'admin')).toBe(false);
  });

  it('blocks offline zones', () => {
    const zone = makeZone('z', { state: 'offline' });
    expect(canEnterZone(zone, 'admin')).toBe(false);
  });

  it('blocks entry when at capacity', () => {
    const zone = makeZone('z', { capacity: 1, occupants: ['agent-1'] });
    expect(canEnterZone(zone, 'admin')).toBe(false);
  });
});

// ─── resolveGravity ───────────────────────────────────────────────────────────

describe('resolveGravity', () => {
  it('returns gravity frame for known zone', () => {
    let m = createStation('S', { now: NOW });
    m = addZone(m, makeZone('z1'), { now: NOW });
    const g = resolveGravity(m, 'z1');
    expect(g).not.toBeNull();
    expect(g!.zone_id).toBe('z1');
  });

  it('returns null for unknown zone', () => {
    const m = createStation('S', { now: NOW });
    expect(resolveGravity(m, 'ghost')).toBeNull();
  });
});

// ─── planTransit ─────────────────────────────────────────────────────────────

describe('planTransit (linked_zones BFS fallback)', () => {
  it('returns zero-cost plan for same zone', () => {
    let m = createStation('S', { now: NOW });
    m = addZone(m, makeZone('z1'), { now: NOW });
    const plan = planTransit(m, 'z1', 'z1');
    expect(plan.blocked).toBe(false);
    expect(plan.total_cost).toBe(0);
    expect(plan.hops).toHaveLength(0);
  });

  it('finds path via linked_zones when no transit nodes', () => {
    let m = createStation('S', { now: NOW });
    m = addZone(m, makeZone('z1', { linked_zones: ['z2'] }), { now: NOW });
    m = addZone(m, makeZone('z2', { linked_zones: ['z3'] }), { now: NOW });
    m = addZone(m, makeZone('z3'), { now: NOW });
    const plan = planTransit(m, 'z1', 'z3');
    expect(plan.blocked).toBe(false);
    expect(plan.hops.length).toBeGreaterThan(0);
  });

  it('blocks when no route exists', () => {
    let m = createStation('S', { now: NOW });
    m = addZone(m, makeZone('z1'), { now: NOW });
    m = addZone(m, makeZone('z2'), { now: NOW });
    const plan = planTransit(m, 'z1', 'z2');
    expect(plan.blocked).toBe(true);
    expect(plan.block_reason).toBe('no_route');
  });

  it('blocks for unknown from zone', () => {
    const m = createStation('S', { now: NOW });
    const plan = planTransit(m, 'ghost', 'z2');
    expect(plan.blocked).toBe(true);
    expect(plan.block_reason).toBe('from_zone_unknown');
  });
});

describe('planTransit (transit nodes)', () => {
  function withNodes(m: ReturnType<typeof createStation>) {
    const node1: TransitNode = {
      id: 'n1',
      zone_id: 'z1',
      label: 'Node 1',
      routes: [{ to: 'n2', mode: 'direct', cost: 5 }],
    };
    const node2: TransitNode = {
      id: 'n2',
      zone_id: 'z2',
      label: 'Node 2',
      routes: [{ to: 'n3', mode: 'relay', cost: 3 }],
    };
    const node3: TransitNode = { id: 'n3', zone_id: 'z3', label: 'Node 3', routes: [] };
    return {
      ...m,
      transit_nodes: { n1: node1, n2: node2, n3: node3 },
    };
  }

  it('routes through transit nodes with correct cost', () => {
    let m = createStation('S', { now: NOW });
    m = addZone(m, makeZone('z1'), { now: NOW });
    m = addZone(m, makeZone('z2'), { now: NOW });
    m = addZone(m, makeZone('z3'), { now: NOW });
    m = withNodes(m);
    const plan = planTransit(m, 'z1', 'z3');
    expect(plan.blocked).toBe(false);
    expect(plan.total_cost).toBe(8); // 5 + 3
  });
});

// ─── Docking ──────────────────────────────────────────────────────────────────

describe('dockAgent / undockAgent', () => {
  it('records agent on port and zone', () => {
    let m = createStation('S', { now: NOW });
    m = addZone(m, makeZone('z1'), { now: NOW });
    m = { ...m, docking_ports: { p1: makePort('p1', 'z1') } };
    m = dockAgent(m, 'agent-007', 'p1', { now: NOW });
    expect(m.docking_ports['p1'].agent_id).toBe('agent-007');
    expect(m.zones['z1'].occupants).toContain('agent-007');
  });

  it('undock removes agent from port and zone', () => {
    let m = createStation('S', { now: NOW });
    m = addZone(m, makeZone('z1'), { now: NOW });
    m = { ...m, docking_ports: { p1: makePort('p1', 'z1') } };
    m = dockAgent(m, 'agent-007', 'p1', { now: NOW });
    m = undockAgent(m, 'p1', { now: NOW });
    expect(m.docking_ports['p1'].agent_id).toBeUndefined();
    expect(m.zones['z1'].occupants).not.toContain('agent-007');
  });

  it('getDockingPort returns port or null', () => {
    let m = createStation('S', { now: NOW });
    m = { ...m, docking_ports: { p1: makePort('p1', 'z1') } };
    expect(getDockingPort(m, 'p1')).not.toBeNull();
    expect(getDockingPort(m, 'ghost')).toBeNull();
  });

  it('no-op dockAgent when port missing', () => {
    const m = createStation('S', { now: NOW });
    const m2 = dockAgent(m, 'agent', 'missing-port', { now: NOW });
    expect(m2.updated_at).toBe(m.updated_at);
  });
});

// ─── sweepKeepers ─────────────────────────────────────────────────────────────

describe('sweepKeepers', () => {
  it('returns an empty sweep for a fresh station', () => {
    const m = createStation('S', { now: NOW });
    const sweep = sweepKeepers(m, { now: NOW });
    expect(sweep.schema_version).toBe('scbe_keeper_sweep_v1');
    expect(sweep.zones_checked).toBe(0);
    expect(sweep.stale_zones).toHaveLength(0);
  });

  it('flags quarantined zones', () => {
    let m = createStation('S', { now: NOW });
    m = addZone(m, makeZone('z1', { state: 'quarantined' }), { now: NOW });
    const sweep = sweepKeepers(m, { now: NOW });
    expect(sweep.quarantined_zones).toContain('z1');
    expect(sweep.escalations).toContain('z1');
  });

  it('flags overcrowded zones', () => {
    let m = createStation('S', { now: NOW });
    m = addZone(m, makeZone('z1', { capacity: 1, occupants: ['a', 'b'] }), { now: NOW });
    const sweep = sweepKeepers(m, { now: NOW });
    expect(sweep.overcrowded_zones).toContain('z1');
  });

  it('flags stale zones past threshold', () => {
    let m = createStation('S', { now: NOW });
    m = addZone(m, makeZone('z1', { audit_receipt: undefined, updated_at: NOW }), { now: NOW });
    // sweep 2 days later with a 1-hour threshold
    const sweep = sweepKeepers(m, { now: STALE_NOW, stale_threshold_ms: 3_600_000 });
    expect(sweep.stale_zones).toContain('z1');
  });
});

// ─── summarizeStation ─────────────────────────────────────────────────────────

describe('summarizeStation', () => {
  it('counts zones by state', () => {
    let m = createStation('S', { now: NOW });
    m = addZone(m, makeZone('z1', { state: 'active' }), { now: NOW });
    m = addZone(m, makeZone('z2', { district: 'security', state: 'quarantined' }), { now: NOW });
    const summary = summarizeStation(m, undefined, { now: NOW });
    expect(summary.schema_version).toBe('scbe_station_summary_v1');
    expect(summary.total_zones).toBe(2);
    expect(summary.active_zones).toBe(1);
    expect(summary.quarantined_zones).toBe(1);
  });

  it('includes fog of war count', () => {
    let m = createStation('S', { now: NOW });
    m = addZone(m, makeZone('z1'), { now: NOW });
    const summary = summarizeStation(m, undefined, { now: NOW });
    expect(summary.fog_of_war_count).toBe(1);
  });

  it('marks district health red when zone is quarantined', () => {
    let m = createStation('S', { now: NOW });
    m = addZone(m, makeZone('z1', { district: 'security', state: 'quarantined' }), { now: NOW });
    const summary = summarizeStation(m, undefined, { now: NOW });
    const secHealth = summary.district_health.find((d) => d.district === 'security');
    expect(secHealth?.health).toBe('red');
  });

  it('marks district health amber when no zones', () => {
    const m = createStation('S', { now: NOW });
    const summary = summarizeStation(m, undefined, { now: NOW });
    for (const dh of summary.district_health) {
      expect(dh.health).toBe('amber');
    }
  });
});

// ─── reportDamage ─────────────────────────────────────────────────────────────

describe('reportDamage', () => {
  it('returns green for a clean station', () => {
    const m = createStation('S', { now: NOW });
    const report = reportDamage(m, { now: NOW });
    expect(report.schema_version).toBe('scbe_damage_report_v1');
    expect(report.overall_health).toBe('green');
    expect(report.critical_zones).toHaveLength(0);
  });

  it('identifies critical zones — 100% quarantined → critical health', () => {
    let m = createStation('S', { now: NOW });
    m = addZone(m, makeZone('z1', { state: 'quarantined' }), { now: NOW });
    const report = reportDamage(m, { now: NOW });
    expect(report.critical_zones).toContain('z1');
    // 1/1 zones quarantined = 100% > 50% threshold → critical
    expect(report.overall_health).toBe('critical');
  });

  it('identifies isolated zones', () => {
    let m = createStation('S', { now: NOW });
    m = addZone(m, makeZone('z1', { linked_zones: [] }), { now: NOW });
    const report = reportDamage(m, { now: NOW });
    expect(report.isolated_zones).toContain('z1');
  });

  it('identifies missing protocols after clearing protocols', () => {
    let m = createStation('S', { now: NOW });
    m = { ...m, cultural_protocols: {} };
    const report = reportDamage(m, { now: NOW });
    expect(report.missing_protocols.length).toBe(ALL_DISTRICTS.length);
  });

  it('flags stale docking ports', () => {
    let m = createStation('S', { now: NOW });
    m = addZone(m, makeZone('z1'), { now: NOW });
    m = {
      ...m,
      docking_ports: {
        p1: makePort('p1', 'z1', { agent_id: 'agent-1', docked_at: NOW }),
      },
    };
    // report 2 days later with 1-hour threshold
    const report = reportDamage(m, { now: STALE_NOW, stale_port_threshold_ms: 3_600_000 });
    expect(report.stale_docking_ports).toContain('p1');
  });
});

// ─── defaultGravityFrame / defaultCulturalProtocol ───────────────────────────

describe('defaults', () => {
  it('defaultGravityFrame has valid range values', () => {
    const g = defaultGravityFrame('test-zone');
    expect(g.security_slope).toBeGreaterThanOrEqual(0);
    expect(g.security_slope).toBeLessThanOrEqual(1);
    expect(g.importance_depth).toBeGreaterThanOrEqual(0);
    expect(g.importance_depth).toBeLessThanOrEqual(100);
  });

  it('defaultCulturalProtocol covers all districts', () => {
    for (const d of ALL_DISTRICTS) {
      const p = defaultCulturalProtocol(d);
      expect(p.district).toBe(d);
      expect(p.primary_tongue).toBeTruthy();
      expect(p.token_budget).toBeGreaterThan(0);
    }
  });
});
