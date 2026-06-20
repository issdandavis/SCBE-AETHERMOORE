import { describe, it, expect } from 'vitest';
import {
  createControlIntent,
  mergeIntents,
  validateSafety,
  toROS2Twist,
  toPX4OffboardSetpoint,
  toMAVLinkGuidedVelocity,
  toCARLAVehicleControl,
  toAirSimCarControls,
  toMSFSSimVars,
  toXPlaneDatarefs,
  toFlightView,
  toDrivingView,
  ZERO_AXES,
  ZERO_COMMANDS,
} from '../src/control-intent.js';

const NOW = '2026-05-30T00:00:00.000Z';

// ─── createControlIntent ──────────────────────────────────────────────────────

describe('createControlIntent', () => {
  it('defaults to sim mode with zero axes', () => {
    const i = createControlIntent('ai', 'flight', { now: NOW });
    expect(i.schema_version).toBe('scbe_control_intent_v1');
    expect(i.source).toBe('ai');
    expect(i.domain).toBe('flight');
    expect(i.safety.mode).toBe('sim');
    expect(i.axes).toEqual(ZERO_AXES);
    expect(i.commands).toEqual(ZERO_COMMANDS);
    expect(i.intent_id).toMatch(/^ci-/);
  });

  it('applies partial axes override', () => {
    const i = createControlIntent('keyboard', 'flight', {
      now: NOW,
      axes: { throttle: 0.8, pitch: -0.3 },
    });
    expect(i.axes.throttle).toBe(0.8);
    expect(i.axes.pitch).toBe(-0.3);
    expect(i.axes.roll).toBe(0); // untouched
  });

  it('applies partial commands override', () => {
    const i = createControlIntent('cli', 'flight', { now: NOW, commands: { hold: true } });
    expect(i.commands.hold).toBe(true);
    expect(i.commands.land).toBe(false);
  });

  it('applies partial safety override', () => {
    const i = createControlIntent('ai', 'flight', {
      now: NOW,
      safety: { mode: 'hardware', deadman_active: true, operator_confirmed: true },
    });
    expect(i.safety.mode).toBe('hardware');
    expect(i.safety.deadman_active).toBe(true);
  });

  it('generates unique intent IDs', () => {
    const a = createControlIntent('ai', 'flight', { now: NOW });
    const b = createControlIntent('ai', 'flight', { now: NOW });
    expect(a.intent_id).not.toBe(b.intent_id);
  });
});

// ─── validateSafety ───────────────────────────────────────────────────────────

describe('validateSafety — sim mode', () => {
  it('always passes in sim mode regardless of gate values', () => {
    const i = createControlIntent('ai', 'flight', {
      now: NOW,
      safety: {
        mode: 'sim',
        deadman_active: false,
        geofence_ok: false,
        heartbeat_age_ms: 999_999,
        operator_confirmed: false,
      },
    });
    const v = validateSafety(i);
    expect(v.ok).toBe(true);
    expect(v.mode).toBe('sim');
    expect(v.failures).toHaveLength(0);
  });
});

describe('validateSafety — hardware mode', () => {
  function hardwareIntent(overrides: Partial<Parameters<typeof createControlIntent>[2]> = {}) {
    return createControlIntent('ai', 'flight', {
      now: NOW,
      safety: {
        mode: 'hardware',
        deadman_active: true,
        geofence_ok: true,
        heartbeat_age_ms: 0,
        operator_confirmed: true,
      },
      ...overrides,
    });
  }

  it('passes when all gates are satisfied', () => {
    const v = validateSafety(hardwareIntent());
    expect(v.ok).toBe(true);
    expect(v.failures).toHaveLength(0);
  });

  it('fails when deadman is not active', () => {
    const i = hardwareIntent({
      safety: {
        mode: 'hardware',
        deadman_active: false,
        geofence_ok: true,
        heartbeat_age_ms: 0,
        operator_confirmed: true,
      },
    });
    const v = validateSafety(i);
    expect(v.ok).toBe(false);
    expect(v.failures).toContain('deadman_not_active');
  });

  it('fails when outside geofence', () => {
    const i = hardwareIntent({
      safety: {
        mode: 'hardware',
        deadman_active: true,
        geofence_ok: false,
        heartbeat_age_ms: 0,
        operator_confirmed: true,
      },
    });
    const v = validateSafety(i);
    expect(v.ok).toBe(false);
    expect(v.failures).toContain('outside_geofence');
  });

  it('fails when heartbeat is stale', () => {
    const i = hardwareIntent({
      safety: {
        mode: 'hardware',
        deadman_active: true,
        geofence_ok: true,
        heartbeat_age_ms: 600,
        operator_confirmed: true,
      },
    });
    const v = validateSafety(i, { heartbeat_timeout_ms: 500 });
    expect(v.ok).toBe(false);
    expect(v.failures.some((f) => f.startsWith('heartbeat_stale'))).toBe(true);
  });

  it('fails when operator not confirmed', () => {
    const i = hardwareIntent({
      safety: {
        mode: 'hardware',
        deadman_active: true,
        geofence_ok: true,
        heartbeat_age_ms: 0,
        operator_confirmed: false,
      },
    });
    const v = validateSafety(i);
    expect(v.ok).toBe(false);
    expect(v.failures).toContain('operator_not_confirmed');
  });

  it('accumulates multiple failures', () => {
    const i = hardwareIntent({
      safety: {
        mode: 'hardware',
        deadman_active: false,
        geofence_ok: false,
        heartbeat_age_ms: 999,
        operator_confirmed: false,
      },
    });
    const v = validateSafety(i);
    expect(v.ok).toBe(false);
    expect(v.failures.length).toBeGreaterThanOrEqual(3);
  });
});

// ─── mergeIntents ─────────────────────────────────────────────────────────────

describe('mergeIntents', () => {
  it('override non-zero axes win', () => {
    const base = createControlIntent('keyboard', 'flight', {
      now: NOW,
      axes: { throttle: 0.5, pitch: -0.2 },
    });
    const override = createControlIntent('ai', 'flight', { now: NOW, axes: { pitch: 0.8 } });
    const merged = mergeIntents(base, override, { now: NOW });
    expect(merged.axes.throttle).toBe(0.5); // base wins (override = 0)
    expect(merged.axes.pitch).toBe(0.8); // override wins
  });

  it('true commands from override propagate', () => {
    const base = createControlIntent('ai', 'flight', { now: NOW });
    const override = createControlIntent('cli', 'flight', { now: NOW, commands: { hold: true } });
    const merged = mergeIntents(base, override, { now: NOW });
    expect(merged.commands.hold).toBe(true);
  });

  it('produces a new intent_id', () => {
    const base = createControlIntent('ai', 'flight', { now: NOW });
    const merged = mergeIntents(base, {}, { now: NOW });
    expect(merged.intent_id).not.toBe(base.intent_id);
  });

  it('safety comes from override when provided', () => {
    const base = createControlIntent('ai', 'flight', {
      now: NOW,
      safety: {
        mode: 'sim',
        deadman_active: false,
        geofence_ok: true,
        heartbeat_age_ms: 0,
        operator_confirmed: false,
      },
    });
    const safetyOverride = {
      mode: 'hardware' as const,
      deadman_active: true,
      geofence_ok: true,
      heartbeat_age_ms: 0,
      operator_confirmed: true,
    };
    const merged = mergeIntents(base, { safety: safetyOverride }, { now: NOW });
    expect(merged.safety.mode).toBe('hardware');
  });
});

// ─── toROS2Twist ──────────────────────────────────────────────────────────────

describe('toROS2Twist', () => {
  it('maps throttle to linear.x', () => {
    const i = createControlIntent('ai', 'driving', { now: NOW, axes: { throttle: 0.6 } });
    const t = toROS2Twist(i);
    expect(t.linear.x).toBeCloseTo(0.6);
    expect(t.linear.y).toBe(0);
    expect(t.linear.z).toBe(0);
  });

  it('maps roll to angular.z (negated)', () => {
    const i = createControlIntent('ai', 'ground-robot', { now: NOW, axes: { roll: 1.0 } });
    const t = toROS2Twist(i);
    expect(t.angular.z).toBe(-1.0);
  });

  it('reverses linear.x when reverse command set', () => {
    const i = createControlIntent('ai', 'driving', {
      now: NOW,
      axes: { throttle: 0.5 },
      commands: { reverse: true },
    });
    const t = toROS2Twist(i);
    expect(t.linear.x).toBeLessThan(0);
  });

  it('respects max scale factors', () => {
    const i = createControlIntent('ai', 'ground-robot', {
      now: NOW,
      axes: { throttle: 1.0, roll: 1.0 },
    });
    const t = toROS2Twist(i, { max_linear_ms: 2.0, max_angular_rads: 1.5 });
    expect(t.linear.x).toBeCloseTo(2.0);
    expect(t.angular.z).toBeCloseTo(-1.5);
  });
});

// ─── toPX4OffboardSetpoint ────────────────────────────────────────────────────

describe('toPX4OffboardSetpoint', () => {
  it('maps pitch to vx (negated — nose-down = forward)', () => {
    const i = createControlIntent('ai', 'flight', { now: NOW, axes: { pitch: -1.0 } });
    const s = toPX4OffboardSetpoint(i, { max_speed_ms: 5 });
    expect(s.vx).toBeCloseTo(5.0); // -pitch*maxSpeed = 5
  });

  it('maps roll to vy', () => {
    const i = createControlIntent('ai', 'flight', { now: NOW, axes: { roll: 0.5 } });
    const s = toPX4OffboardSetpoint(i, { max_speed_ms: 4 });
    expect(s.vy).toBeCloseTo(2.0);
  });

  it('maps altitude to vz (negated — NED down is positive)', () => {
    const i = createControlIntent('ai', 'flight', { now: NOW, axes: { altitude: 1.0 } });
    const s = toPX4OffboardSetpoint(i, { max_speed_ms: 3 });
    expect(s.vz).toBeCloseTo(-3.0); // climb → negative vz in NED
  });

  it('sets velocity_control to true', () => {
    const i = createControlIntent('ai', 'flight', { now: NOW });
    expect(toPX4OffboardSetpoint(i).velocity_control).toBe(true);
  });
});

// ─── toMAVLinkGuidedVelocity ──────────────────────────────────────────────────

describe('toMAVLinkGuidedVelocity', () => {
  it('produces correct type_mask', () => {
    const i = createControlIntent('ai', 'flight', { now: NOW });
    const m = toMAVLinkGuidedVelocity(i);
    expect(m.type_mask).toBe(0b0000111111000111);
  });

  it('defaults to BODY_NED frame', () => {
    const i = createControlIntent('ai', 'flight', { now: NOW });
    expect(toMAVLinkGuidedVelocity(i).coordinate_frame).toBe('BODY_NED');
  });

  it('accepts frame override', () => {
    const i = createControlIntent('ai', 'flight', { now: NOW });
    const m = toMAVLinkGuidedVelocity(i, { frame: 'GLOBAL_RELATIVE_ALT' });
    expect(m.coordinate_frame).toBe('GLOBAL_RELATIVE_ALT');
  });
});

// ─── toCARLAVehicleControl ────────────────────────────────────────────────────

describe('toCARLAVehicleControl', () => {
  it('maps throttle, steer, brake correctly', () => {
    const i = createControlIntent('ai', 'driving', {
      now: NOW,
      axes: { throttle: 0.7, roll: -0.4, brake: 0.1 },
    });
    const c = toCARLAVehicleControl(i);
    expect(c.throttle).toBeCloseTo(0.7);
    expect(c.steer).toBeCloseTo(-0.4);
    expect(c.brake).toBeCloseTo(0.1);
    expect(c.hand_brake).toBe(false);
    expect(c.reverse).toBe(false);
  });

  it('propagates handbrake and reverse flags', () => {
    const i = createControlIntent('ai', 'driving', {
      now: NOW,
      commands: { handbrake: true, reverse: true },
    });
    const c = toCARLAVehicleControl(i);
    expect(c.hand_brake).toBe(true);
    expect(c.reverse).toBe(true);
  });

  it('clamps out-of-range values', () => {
    const i = createControlIntent('ai', 'driving', {
      now: NOW,
      axes: { throttle: 2.0, roll: 3.0 },
    });
    const c = toCARLAVehicleControl(i);
    expect(c.throttle).toBeLessThanOrEqual(1.0);
    expect(c.steer).toBeLessThanOrEqual(1.0);
  });
});

// ─── toAirSimCarControls ──────────────────────────────────────────────────────

describe('toAirSimCarControls', () => {
  it('has correct fixed fields', () => {
    const i = createControlIntent('ai', 'driving', { now: NOW });
    const c = toAirSimCarControls(i);
    expect(c.is_manual_gear).toBe(false);
    expect(c.manual_gear).toBe(0);
    expect(c.gear_immediate).toBe(true);
  });

  it('maps steering from roll axis', () => {
    const i = createControlIntent('ai', 'driving', { now: NOW, axes: { roll: -0.6 } });
    expect(toAirSimCarControls(i).steering).toBeCloseTo(-0.6);
  });
});

// ─── toMSFSSimVars ────────────────────────────────────────────────────────────

describe('toMSFSSimVars', () => {
  it('maps throttle to [0, 100] range', () => {
    const i = createControlIntent('ai', 'flight', { now: NOW, axes: { throttle: 0.5 } });
    expect(toMSFSSimVars(i).GENERAL_ENG_THROTTLE_LEVER_POSITION_1).toBe(50);
  });

  it('maps axes to [-16383, 16383] range', () => {
    const i = createControlIntent('ai', 'flight', {
      now: NOW,
      axes: { pitch: 1.0, roll: -1.0, yaw: 0.5 },
    });
    const v = toMSFSSimVars(i);
    expect(v.AXIS_ELEVATOR_SET).toBe(16383);
    expect(v.AXIS_AILERONS_SET).toBe(-16383);
    expect(v.AXIS_RUDDER_SET).toBe(Math.round(0.5 * 16383));
  });

  it('adds EMERGENCY_FUEL_SHUTOFF event on emergency_stop', () => {
    const i = createControlIntent('ai', 'flight', { now: NOW, commands: { emergency_stop: true } });
    expect(toMSFSSimVars(i).events).toContain('EMERGENCY_FUEL_SHUTOFF');
  });

  it('adds AP_ALT_HOLD_ON event on hold', () => {
    const i = createControlIntent('ai', 'flight', { now: NOW, commands: { hold: true } });
    expect(toMSFSSimVars(i).events).toContain('AP_ALT_HOLD_ON');
  });
});

// ─── toXPlaneDatarefs ─────────────────────────────────────────────────────────

describe('toXPlaneDatarefs', () => {
  it('maps pitch to yoke_pitch_ratio', () => {
    const i = createControlIntent('ai', 'flight', { now: NOW, axes: { pitch: 0.3 } });
    expect(toXPlaneDatarefs(i)['sim/joystick/yoke_pitch_ratio']).toBeCloseTo(0.3);
  });

  it('maps roll to yoke_roll_ratio', () => {
    const i = createControlIntent('ai', 'flight', { now: NOW, axes: { roll: -0.7 } });
    expect(toXPlaneDatarefs(i)['sim/joystick/yoke_roll_ratio']).toBeCloseTo(-0.7);
  });

  it('adds autopilot commands for hold', () => {
    const i = createControlIntent('ai', 'flight', { now: NOW, commands: { hold: true } });
    expect(toXPlaneDatarefs(i).commands).toContain('sim/autopilot/altitude_hold');
  });

  it('adds land command', () => {
    const i = createControlIntent('ai', 'flight', { now: NOW, commands: { land: true } });
    expect(toXPlaneDatarefs(i).commands).toContain('sim/autopilot/land');
  });
});

// ─── toFlightView / toDrivingView ─────────────────────────────────────────────

describe('toFlightView', () => {
  it('returns clamped normalized flight axes and commands', () => {
    const i = createControlIntent('ai', 'flight', {
      now: NOW,
      axes: { throttle: 1.5, pitch: -0.5, roll: 0.3, yaw: 0.1, altitude: 0.8 },
      commands: { hold: true, emergency_stop: true },
    });
    const v = toFlightView(i);
    expect(v.throttle).toBe(1.0); // clamped
    expect(v.pitch).toBeCloseTo(-0.5);
    expect(v.roll).toBeCloseTo(0.3);
    expect(v.hold).toBe(true);
    expect(v.emergency_stop).toBe(true);
  });
});

describe('toDrivingView', () => {
  it('maps roll to steering in driving domain', () => {
    const i = createControlIntent('ai', 'driving', {
      now: NOW,
      axes: { roll: 0.9, throttle: 0.4, brake: 0.2 },
    });
    const v = toDrivingView(i);
    expect(v.steering).toBeCloseTo(0.9);
    expect(v.throttle).toBeCloseTo(0.4);
    expect(v.brake).toBeCloseTo(0.2);
  });

  it('propagates reverse and handbrake commands', () => {
    const i = createControlIntent('ai', 'driving', {
      now: NOW,
      commands: { reverse: true, handbrake: true },
    });
    const v = toDrivingView(i);
    expect(v.reverse).toBe(true);
    expect(v.handbrake).toBe(true);
  });
});

// ─── Clamping invariants ──────────────────────────────────────────────────────

describe('axis clamping invariants', () => {
  it('toROS2Twist never exceeds max_linear_ms', () => {
    const i = createControlIntent('ai', 'driving', { now: NOW, axes: { throttle: 99.0 } });
    const t = toROS2Twist(i, { max_linear_ms: 2.0 });
    expect(Math.abs(t.linear.x)).toBeLessThanOrEqual(2.0);
  });

  it('toCARLAVehicleControl throttle stays in [0,1]', () => {
    const i = createControlIntent('ai', 'driving', { now: NOW, axes: { throttle: -5.0 } });
    const c = toCARLAVehicleControl(i);
    expect(c.throttle).toBe(0); // clamp01
  });

  it('toCARLAVehicleControl steer stays in [-1,1]', () => {
    const i = createControlIntent('ai', 'driving', { now: NOW, axes: { roll: 50.0 } });
    const c = toCARLAVehicleControl(i);
    expect(c.steer).toBe(1.0);
  });
});
