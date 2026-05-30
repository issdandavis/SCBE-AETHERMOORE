import { describe, expect, it } from 'vitest';
import {
  addZone,
  buildPollyOperatorActions,
  buildPollyOperatorAlerts,
  buildPollyOperatorBrief,
  createKeeper,
  createStation,
  defaultGravityFrame,
  observeZone,
  POLLY_OPERATOR_SOURCE_REFS,
  renderPollyOperatorBrief,
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

describe('buildPollyOperatorBrief', () => {
  it('renders a green operator brief with watch as the next action', () => {
    let station = createStation('STATION-POLLY', { now: NOW });
    station = addZone(station, makeZone('hub', { linked_zones: ['ops'] }), { now: NOW });
    station = addZone(station, makeZone('ops', { linked_zones: ['hub'] }), { now: NOW });
    station = observeZone(observeZone(station, 'hub', { now: NOW }), 'ops', { now: NOW });

    const brief = buildPollyOperatorBrief(station, { now: NOW });
    const rendered = renderPollyOperatorBrief(brief);

    expect(brief.schema_version).toBe('scbe_polly_operator_brief_v1');
    expect(brief.health).toBe('green');
    expect(brief.headline).toBe('Station STATION-POLLY is green');
    expect(brief.actions[0].command).toBe('scbe polly watch');
    expect(brief.source_refs.map((ref) => ref.path)).toContain('src/fleet/polly-pad.ts');
    expect(brief.source_refs.map((ref) => ref.path)).toContain('kindle-app/www/polly-pad.html');
    expect(rendered).toContain('Polly status: Station STATION-POLLY is green');
  });

  it('prioritizes security and critical-zone actions over passive observation', () => {
    let station = createStation('STATION-POLLY', { now: NOW });
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

    const brief = buildPollyOperatorBrief(station, { now: NOW, mode: 'damage' });

    expect(brief.health).toBe('critical');
    expect(brief.alerts.map((alert) => alert.id)).toContain('damage.security-breaches');
    expect(brief.actions[0].id).toBe('action.security-review');
    expect(brief.actions[1].id).toBe('action.inspect-critical-zones');
    expect(brief.cli_lines.join('\n')).toContain('scbe station damage --review-security');
  });

  it('turns keeper sweep results into repaired and escalation status lines', () => {
    let station = createStation('STATION-POLLY', { now: NOW });
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

    const keeper = createKeeper('keeper-polly', { stale_threshold_ms: 1 });
    const run = runSweep(keeper, station, { now: STALE });
    const brief = buildPollyOperatorBrief(run.manifest, {
      now: STALE,
      keeperRun: run.result,
    });

    expect(brief.keeper?.keeper_id).toBe('keeper-polly');
    expect(brief.keeper?.zones_repaired).toBe(2);
    expect(brief.keeper?.zones_escalated).toBe(1);
    expect(brief.alerts.map((a) => a.id)).toContain('keeper.escalations');
    expect(brief.alerts.map((a) => a.id)).toContain('keeper.repairs-applied');
    expect(brief.cli_lines.join('\n')).toContain('keeper=keeper-polly repaired=2 escalated=1');
  });

  it('caps alerts and actions for compact CLI output', () => {
    let station = createStation('STATION-POLLY', { now: NOW });
    station = addZone(station, makeZone('a', { state: 'quarantined' }), { now: NOW });
    station = addZone(station, makeZone('b', { linked_zones: [] }), { now: NOW });

    const brief = buildPollyOperatorBrief(station, {
      now: NOW,
      maxAlerts: 1,
      maxActions: 1,
    });

    expect(brief.alerts).toHaveLength(1);
    expect(brief.actions).toHaveLength(1);
  });
});

describe('buildPollyOperatorAlerts / buildPollyOperatorActions', () => {
  it('keeps alert/action builders deterministic from supplied reports', () => {
    let station = createStation('STATION-POLLY', { now: NOW });
    station = addZone(station, makeZone('isolated', { linked_zones: [] }), { now: NOW });

    const brief = buildPollyOperatorBrief(station, { now: NOW });
    const damage = reportDamage(station, { now: NOW });
    const alerts = buildPollyOperatorAlerts(brief.summary, damage);
    const actions = buildPollyOperatorActions(brief.summary, damage);

    expect(alerts.map((a) => a.id)).toEqual(['damage.overall-health', 'station.fog-of-war']);
    expect(actions.map((a) => a.id)).toContain('action.add-transit');
    expect(actions.map((a) => a.id)).toContain('action.observe-fog');
  });

  it('publishes Polly source refs as the only operator narrator surface', () => {
    let station = createStation('STATION-POLLY', { now: NOW });
    station = addZone(station, makeZone('hub', { linked_zones: ['ops'] }), { now: NOW });
    station = observeZone(station, 'hub', { now: NOW });

    const brief = buildPollyOperatorBrief(station, { now: NOW });

    expect(POLLY_OPERATOR_SOURCE_REFS.map((ref) => ref.path)).toContain(
      'src/fleet/polly-pad-runtime.ts'
    );
    expect(renderPollyOperatorBrief(brief)).toContain('Polly status:');
  });
});
