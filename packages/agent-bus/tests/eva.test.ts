import { describe, expect, it } from 'vitest';
import {
  addZone,
  buildEvaActions,
  buildEvaAlerts,
  buildEvaBrief,
  createKeeper,
  createStation,
  defaultGravityFrame,
  observeZone,
  renderEvaBrief,
  reportDamage,
  runSweep,
  type StationZone,
} from '../src/index.js';

const NOW = '2026-05-30T12:00:00.000Z';
const STALE = '2026-06-01T12:00:00.000Z';

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
    linked_zones: ['hub'],
    updated_at: NOW,
    ...overrides,
  };
}

describe('buildEvaBrief', () => {
  it('renders a green operator brief with watch as the next action', () => {
    let station = createStation('STATION-EVA', { now: NOW });
    station = addZone(station, makeZone('hub', { linked_zones: ['ops'] }), { now: NOW });
    station = addZone(station, makeZone('ops', { linked_zones: ['hub'] }), { now: NOW });
    station = observeZone(observeZone(station, 'hub', { now: NOW }), 'ops', { now: NOW });

    const brief = buildEvaBrief(station, { now: NOW });
    const rendered = renderEvaBrief(brief);

    expect(brief.schema_version).toBe('scbe_eva_brief_v1');
    expect(brief.health).toBe('green');
    expect(brief.headline).toBe('Station STATION-EVA is green');
    expect(brief.actions[0].command).toBe('scbe eva watch');
    expect(rendered).toContain('EVA status: Station STATION-EVA is green');
  });

  it('prioritizes security and critical-zone actions over passive observation', () => {
    let station = createStation('STATION-EVA', { now: NOW });
    station = addZone(
      station,
      makeZone('security-core', {
        state: 'quarantined',
        clearance: 'admin',
        linked_zones: ['hub'],
      }),
      { now: NOW }
    );
    station = {
      ...station,
      security_boundaries: {
        boundary: {
          id: 'boundary',
          zone_ids: ['security-core'],
          min_clearance: 'read_only',
          allowed_lanes: ['keeper'],
        },
      },
    };

    const brief = buildEvaBrief(station, { now: NOW, mode: 'damage' });

    expect(brief.health).toBe('critical');
    expect(brief.alerts.map((alert) => alert.id)).toContain('damage.security-breaches');
    expect(brief.actions[0].id).toBe('action.security-review');
    expect(brief.actions[1].id).toBe('action.inspect-critical-zones');
    expect(brief.cli_lines.join('\n')).toContain('scbe station damage --review-security');
  });

  it('turns keeper sweep results into repaired and escalation status lines', () => {
    let station = createStation('STATION-EVA', { now: NOW });
    station = addZone(
      station,
      makeZone('stale-zone', {
        linked_zones: ['hub'],
        updated_at: NOW,
      }),
      { now: NOW }
    );
    station = addZone(
      station,
      makeZone('quarantine-zone', {
        state: 'quarantined',
        linked_zones: ['hub'],
        updated_at: NOW,
      }),
      { now: NOW }
    );

    const keeper = createKeeper('keeper-eva', { stale_threshold_ms: 1 });
    const run = runSweep(keeper, station, { now: STALE });
    const brief = buildEvaBrief(run.manifest, {
      now: STALE,
      keeperRun: run.result,
    });

    expect(brief.keeper?.keeper_id).toBe('keeper-eva');
    expect(brief.keeper?.zones_repaired).toBe(2);
    expect(brief.keeper?.zones_escalated).toBe(1);
    expect(brief.alerts.map((a) => a.id)).toContain('keeper.escalations');
    expect(brief.alerts.map((a) => a.id)).toContain('keeper.repairs-applied');
    expect(brief.cli_lines.join('\n')).toContain('keeper=keeper-eva repaired=2 escalated=1');
  });

  it('caps alerts and actions for compact CLI output', () => {
    let station = createStation('STATION-EVA', { now: NOW });
    station = addZone(station, makeZone('a', { state: 'quarantined' }), { now: NOW });
    station = addZone(station, makeZone('b', { linked_zones: [] }), { now: NOW });

    const brief = buildEvaBrief(station, {
      now: NOW,
      maxAlerts: 1,
      maxActions: 1,
    });

    expect(brief.alerts).toHaveLength(1);
    expect(brief.actions).toHaveLength(1);
  });
});

describe('buildEvaAlerts / buildEvaActions', () => {
  it('keeps alert/action builders deterministic from supplied reports', () => {
    let station = createStation('STATION-EVA', { now: NOW });
    station = addZone(station, makeZone('isolated', { linked_zones: [] }), { now: NOW });

    const brief = buildEvaBrief(station, { now: NOW });
    const damage = reportDamage(station, { now: NOW });
    const alerts = buildEvaAlerts(brief.summary, damage);
    const actions = buildEvaActions(brief.summary, damage);

    expect(alerts.map((a) => a.id)).toEqual(['damage.overall-health', 'station.fog-of-war']);
    expect(actions.map((a) => a.id)).toContain('action.add-transit');
    expect(actions.map((a) => a.id)).toContain('action.observe-fog');
  });
});
