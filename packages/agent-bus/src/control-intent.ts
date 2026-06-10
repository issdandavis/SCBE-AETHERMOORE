/**
 * @file control-intent.ts
 * @module agent-bus/control-intent
 * @layer Cross-layer governed control
 * @component ControlIntent — normalized cross-domain control packet
 *
 * A single packet type that carries control intent from any source
 * (keyboard, CLI, AI, simulator, robot, drone) to any target domain
 * (flight, driving, ground-robot, abstract).
 *
 * Safety invariant: hardware mode requires ALL four gates satisfied.
 *   deadman_active    — operator thumb is on the switch
 *   geofence_ok       — position is within permitted area
 *   heartbeat_age_ms  — link is live (< heartbeat_timeout_ms)
 *   operator_confirmed— operator has acknowledged the action class
 *
 * Sim mode: no hardware safety gates required. Default for every new intent.
 *
 * Adapter outputs map normalized axes to target-specific wire formats:
 *   ROS 2  — geometry_msgs/Twist  (diff drive teleop)
 *   PX4    — OffboardControlMode velocity setpoint
 *   ArduPilot — MAVLink GUIDED velocity target
 *   CARLA  — VehicleControl  (throttle/steer/brake)
 *   AirSim — CarControls     (throttle/steering/brake)
 *   MSFS   — SimVar key events
 *   X-Plane — Dataref write map
 *
 * Patent framing: governed cross-domain control compiler.
 * The governance layer decides WHAT is allowed; this module decides HOW
 * to express it to each target system.
 */

// ─── Source / domain / mode ───────────────────────────────────────────────────

export type ControlSource = 'keyboard' | 'cli' | 'ai' | 'simulator' | 'robot' | 'drone';

export type ControlDomain = 'flight' | 'driving' | 'ground-robot' | 'abstract';

export type ControlMode = 'sim' | 'hardware';

// ─── Axes ─────────────────────────────────────────────────────────────────────

/**
 * All axes are normalized to [-1.0, 1.0] or [0.0, 1.0] as noted.
 * Zero is the neutral/idle position.
 */
export interface ControlAxes {
  /**
   * Flight: collective thrust/throttle.  0.0 = min, 1.0 = max.
   * Driving: longitudinal throttle.      0.0 = idle, 1.0 = full.
   * Ground robot: forward/back speed.   -1.0 = full reverse, 1.0 = full forward.
   */
  throttle: number;
  /**
   * Flight: nose pitch.  -1.0 = nose down (forward), 1.0 = nose up (back).
   * Driving: unused (set to 0).
   * Ground robot: unused (set to 0).
   */
  pitch: number;
  /**
   * Flight: bank roll.  -1.0 = roll left, 1.0 = roll right.
   * Driving: steering.  -1.0 = full left, 1.0 = full right.
   * Ground robot: angular rate. -1.0 = turn left, 1.0 = turn right.
   */
  roll: number;
  /**
   * Yaw / heading rate.  -1.0 = rotate CCW, 1.0 = rotate CW.
   */
  yaw: number;
  /**
   * Flight: vertical speed.  -1.0 = descend, 1.0 = climb.
   * Other domains: unused (set to 0).
   */
  altitude: number;
  /**
   * Braking force.  0.0 = no brake, 1.0 = full brake.  Driving / robot only.
   */
  brake: number;
}

// ─── Commands (discrete flags) ────────────────────────────────────────────────

export interface ControlCommands {
  /** Flight: enter loiter / hold position. */
  hold: boolean;
  /** Flight: trigger return-to-launch sequence. */
  return_home: boolean;
  /** Flight: initiate controlled landing. */
  land: boolean;
  /** Driving: engage handbrake. */
  handbrake: boolean;
  /** Driving: select reverse gear. */
  reverse: boolean;
  /** All domains: immediate motor stop. Propagates even in sim mode. */
  emergency_stop: boolean;
}

// ─── Safety frame ─────────────────────────────────────────────────────────────

export interface SafetyFrame {
  mode: ControlMode;
  /** True while the operator physically holds the deadman switch. */
  deadman_active: boolean;
  /** True when the vehicle is within the permitted geofence. */
  geofence_ok: boolean;
  /** Milliseconds since the last valid heartbeat from the controller link. */
  heartbeat_age_ms: number;
  /** True when the operator has confirmed the current action class. */
  operator_confirmed: boolean;
}

// ─── Metadata ─────────────────────────────────────────────────────────────────

export interface ControlMetadata {
  /** Originating agent or process ID. */
  agent_id?: string;
  /** Mission or task context. */
  mission_id?: string;
  /** Human-readable label for this intent. */
  label?: string;
  /** Governance tags propagated to the audit trail. */
  tags: string[];
}

// ─── Root packet ─────────────────────────────────────────────────────────────

export interface ControlIntent {
  schema_version: 'scbe_control_intent_v1';
  intent_id: string;
  timestamp: string;
  source: ControlSource;
  domain: ControlDomain;
  safety: SafetyFrame;
  axes: ControlAxes;
  commands: ControlCommands;
  metadata: ControlMetadata;
}

// ─── Safety validation ────────────────────────────────────────────────────────

export interface SafetyValidation {
  ok: boolean;
  mode: ControlMode;
  gates: {
    deadman: boolean;
    geofence: boolean;
    heartbeat: boolean;
    operator_confirmed: boolean;
  };
  failures: string[];
}

/**
 * Validate hardware safety gates.
 * Sim mode always passes (returns ok:true with all gates reported as satisfied).
 * Hardware mode requires all four gates.
 */
export function validateSafety(
  intent: ControlIntent,
  opts: { heartbeat_timeout_ms?: number } = {}
): SafetyValidation {
  const timeout = opts.heartbeat_timeout_ms ?? 500;

  if (intent.safety.mode === 'sim') {
    return {
      ok: true,
      mode: 'sim',
      gates: { deadman: true, geofence: true, heartbeat: true, operator_confirmed: true },
      failures: [],
    };
  }

  const gates = {
    deadman: intent.safety.deadman_active,
    geofence: intent.safety.geofence_ok,
    heartbeat: intent.safety.heartbeat_age_ms <= timeout,
    operator_confirmed: intent.safety.operator_confirmed,
  };

  const failures: string[] = [];
  if (!gates.deadman) failures.push('deadman_not_active');
  if (!gates.geofence) failures.push('outside_geofence');
  if (!gates.heartbeat)
    failures.push(`heartbeat_stale_${intent.safety.heartbeat_age_ms}ms_exceeds_${timeout}ms`);
  if (!gates.operator_confirmed) failures.push('operator_not_confirmed');

  return { ok: failures.length === 0, mode: 'hardware', gates, failures };
}

// ─── Factories ────────────────────────────────────────────────────────────────

let _intentSeq = 0;

function newIntentId(now: string): string {
  const ts = new Date(now).getTime().toString(36);
  return `ci-${ts}-${(++_intentSeq).toString(36).padStart(4, '0')}`;
}

export const ZERO_AXES: ControlAxes = {
  throttle: 0,
  pitch: 0,
  roll: 0,
  yaw: 0,
  altitude: 0,
  brake: 0,
};

export const ZERO_COMMANDS: ControlCommands = {
  hold: false,
  return_home: false,
  land: false,
  handbrake: false,
  reverse: false,
  emergency_stop: false,
};

export function createControlIntent(
  source: ControlSource,
  domain: ControlDomain,
  opts: {
    now?: string;
    axes?: Partial<ControlAxes>;
    commands?: Partial<ControlCommands>;
    safety?: Partial<SafetyFrame>;
    metadata?: Partial<ControlMetadata>;
  } = {}
): ControlIntent {
  const now = opts.now ?? new Date().toISOString();
  return {
    schema_version: 'scbe_control_intent_v1',
    intent_id: newIntentId(now),
    timestamp: now,
    source,
    domain,
    safety: {
      mode: 'sim',
      deadman_active: false,
      geofence_ok: true,
      heartbeat_age_ms: 0,
      operator_confirmed: false,
      ...opts.safety,
    },
    axes: { ...ZERO_AXES, ...opts.axes },
    commands: { ...ZERO_COMMANDS, ...opts.commands },
    metadata: {
      tags: [],
      ...opts.metadata,
    },
  };
}

/**
 * Merge two intents — override wins on non-zero axes and true commands.
 * Safety frame comes entirely from the override intent.
 * Intent ID and timestamp are reset to a new value.
 */
export function mergeIntents(
  base: ControlIntent,
  override: Partial<ControlIntent>,
  opts: { now?: string } = {}
): ControlIntent {
  const now = opts.now ?? new Date().toISOString();
  const baseAxes = base.axes;
  const overAxes: Partial<ControlAxes> = override.axes ?? {};
  const merged: ControlAxes = {
    throttle:
      overAxes.throttle !== undefined && overAxes.throttle !== 0
        ? overAxes.throttle
        : baseAxes.throttle,
    pitch: overAxes.pitch !== undefined && overAxes.pitch !== 0 ? overAxes.pitch : baseAxes.pitch,
    roll: overAxes.roll !== undefined && overAxes.roll !== 0 ? overAxes.roll : baseAxes.roll,
    yaw: overAxes.yaw !== undefined && overAxes.yaw !== 0 ? overAxes.yaw : baseAxes.yaw,
    altitude:
      overAxes.altitude !== undefined && overAxes.altitude !== 0
        ? overAxes.altitude
        : baseAxes.altitude,
    brake: overAxes.brake !== undefined && overAxes.brake !== 0 ? overAxes.brake : baseAxes.brake,
  };

  const baseCmds = base.commands;
  const overCmds: Partial<ControlCommands> = override.commands ?? {};
  const commands: ControlCommands = {
    hold: overCmds.hold ?? baseCmds.hold,
    return_home: overCmds.return_home ?? baseCmds.return_home,
    land: overCmds.land ?? baseCmds.land,
    handbrake: overCmds.handbrake ?? baseCmds.handbrake,
    reverse: overCmds.reverse ?? baseCmds.reverse,
    emergency_stop: overCmds.emergency_stop ?? baseCmds.emergency_stop,
  };

  return {
    ...base,
    intent_id: newIntentId(now),
    timestamp: now,
    axes: merged,
    commands,
    safety: override.safety ?? base.safety,
    metadata: override.metadata ?? base.metadata,
  };
}

/** Clamp a value to [-1, 1]. */
function clamp(v: number): number {
  return Math.max(-1, Math.min(1, v));
}

/** Clamp a value to [0, 1]. */
function clamp01(v: number): number {
  return Math.max(0, Math.min(1, v));
}

// ─── Adapter outputs ──────────────────────────────────────────────────────────

// ROS 2 geometry_msgs/Twist
export interface ROS2Twist {
  linear: { x: number; y: number; z: number };
  angular: { x: number; y: number; z: number };
}

/**
 * Map a driving or ground-robot intent to a ROS 2 Twist message.
 * linear.x = forward speed (m/s scale) from throttle.
 * angular.z = rotation rate from roll (yaw for differential drive).
 * Scale factors are unitless — callers multiply by their max velocity.
 */
export function toROS2Twist(
  intent: ControlIntent,
  opts: { max_linear_ms?: number; max_angular_rads?: number } = {}
): ROS2Twist {
  const maxLin = opts.max_linear_ms ?? 1.0;
  const maxAng = opts.max_angular_rads ?? 1.0;
  const fwd = intent.commands.reverse
    ? -clamp01(intent.axes.throttle) * maxLin
    : clamp01(intent.axes.throttle) * maxLin;
  return {
    linear: { x: fwd, y: 0, z: 0 },
    angular: { x: 0, y: 0, z: -clamp(intent.axes.roll) * maxAng },
  };
}

// PX4 Offboard velocity setpoint
export interface PX4OffboardSetpoint {
  /** NED frame: positive = north (m/s). */
  vx: number;
  /** NED frame: positive = east (m/s). */
  vy: number;
  /** NED frame: positive = down (m/s). */
  vz: number;
  /** Heading rate (rad/s). */
  yaw_rate: number;
  /** True = velocity control mode. */
  velocity_control: true;
}

/**
 * Map a flight intent to a PX4 Offboard velocity setpoint.
 * Axes are mapped to NED (north-east-down): pitch → vx, roll → vy, altitude → -vz.
 * Callers must stream this at ≥ 2 Hz to keep Offboard mode alive.
 */
export function toPX4OffboardSetpoint(
  intent: ControlIntent,
  opts: { max_speed_ms?: number; max_yaw_rate_rads?: number } = {}
): PX4OffboardSetpoint {
  const maxSpeed = opts.max_speed_ms ?? 5.0;
  const maxYaw = opts.max_yaw_rate_rads ?? 1.0;
  // pitch negative = nose-down = forward in NED
  return {
    vx: -clamp(intent.axes.pitch) * maxSpeed,
    vy: clamp(intent.axes.roll) * maxSpeed,
    vz: -clamp(intent.axes.altitude) * maxSpeed, // NED: down is positive
    yaw_rate: clamp(intent.axes.yaw) * maxYaw,
    velocity_control: true,
  };
}

// ArduPilot MAVLink GUIDED velocity target
export interface MAVLinkGuidedVelocity {
  /** Type mask: velocity-only control (0b0000111111000111). */
  type_mask: number;
  /** Body frame or global frame — callers choose coordinate system. */
  coordinate_frame: 'BODY_NED' | 'GLOBAL_RELATIVE_ALT';
  vx: number;
  vy: number;
  vz: number;
  yaw_rate: number;
}

/** Map a flight intent to an ArduPilot GUIDED-mode velocity MAVLink command. */
export function toMAVLinkGuidedVelocity(
  intent: ControlIntent,
  opts: { max_speed_ms?: number; frame?: 'BODY_NED' | 'GLOBAL_RELATIVE_ALT' } = {}
): MAVLinkGuidedVelocity {
  const maxSpeed = opts.max_speed_ms ?? 5.0;
  return {
    type_mask: 0b0000111111000111, // velocity + yaw rate only
    coordinate_frame: opts.frame ?? 'BODY_NED',
    vx: -clamp(intent.axes.pitch) * maxSpeed,
    vy: clamp(intent.axes.roll) * maxSpeed,
    vz: -clamp(intent.axes.altitude) * maxSpeed,
    yaw_rate: clamp(intent.axes.yaw),
  };
}

// CARLA VehicleControl
export interface CARLAVehicleControl {
  throttle: number; // [0, 1]
  steer: number; // [-1, 1]
  brake: number; // [0, 1]
  hand_brake: boolean;
  reverse: boolean;
}

/** Map a driving intent to a CARLA VehicleControl struct. */
export function toCARLAVehicleControl(intent: ControlIntent): CARLAVehicleControl {
  return {
    throttle: clamp01(intent.axes.throttle),
    steer: clamp(intent.axes.roll),
    brake: clamp01(intent.axes.brake),
    hand_brake: intent.commands.handbrake,
    reverse: intent.commands.reverse,
  };
}

// AirSim CarControls
export interface AirSimCarControls {
  throttle: number; // [0, 1]
  steering: number; // [-1, 1]
  brake: number; // [0, 1]
  handbrake: boolean;
  is_manual_gear: false;
  manual_gear: 0;
  gear_immediate: true;
}

/** Map a driving intent to an AirSim CarControls struct. */
export function toAirSimCarControls(intent: ControlIntent): AirSimCarControls {
  return {
    throttle: clamp01(intent.axes.throttle),
    steering: clamp(intent.axes.roll),
    brake: clamp01(intent.axes.brake),
    handbrake: intent.commands.handbrake,
    is_manual_gear: false,
    manual_gear: 0,
    gear_immediate: true,
  };
}

// MSFS SimVar / key-event map
export interface MSFSSimVarMap {
  /** SIMVAR AXIS_ELEVATOR_SET normalized [-16383, 16383] */
  AXIS_ELEVATOR_SET: number;
  /** SIMVAR AXIS_AILERONS_SET normalized [-16383, 16383] */
  AXIS_AILERONS_SET: number;
  /** SIMVAR AXIS_RUDDER_SET normalized [-16383, 16383] */
  AXIS_RUDDER_SET: number;
  /** SIMVAR GENERAL_ENG_THROTTLE_LEVER_POSITION_1 [0, 100] */
  GENERAL_ENG_THROTTLE_LEVER_POSITION_1: number;
  /** Key events */
  events: string[];
}

const MSFS_AXIS_SCALE = 16383;

/** Map a flight intent to MSFS SimVar writes + key events. */
export function toMSFSSimVars(intent: ControlIntent): MSFSSimVarMap {
  const events: string[] = [];
  if (intent.commands.land) events.push('TOGGLE_MASTER_ALTERNATOR'); // sim landing signal placeholder
  if (intent.commands.emergency_stop) events.push('EMERGENCY_FUEL_SHUTOFF');
  if (intent.commands.return_home) events.push('AP_LOC_HOLD_ON');
  if (intent.commands.hold) events.push('AP_ALT_HOLD_ON');
  return {
    AXIS_ELEVATOR_SET: Math.round(clamp(intent.axes.pitch) * MSFS_AXIS_SCALE),
    AXIS_AILERONS_SET: Math.round(clamp(intent.axes.roll) * MSFS_AXIS_SCALE),
    AXIS_RUDDER_SET: Math.round(clamp(intent.axes.yaw) * MSFS_AXIS_SCALE),
    GENERAL_ENG_THROTTLE_LEVER_POSITION_1: Math.round(clamp01(intent.axes.throttle) * 100),
    events,
  };
}

// X-Plane dataref write map
export interface XPlaneDatarefMap {
  'sim/joystick/yoke_pitch_ratio': number; // [-1, 1]
  'sim/joystick/yoke_roll_ratio': number; // [-1, 1]
  'sim/joystick/yoke_heading_ratio': number; // [-1, 1]
  'sim/flightmodel/engine/ENGN_thro_use[0]': number; // [0, 1]
  'sim/cockpit2/controls/speedbrake_ratio': number; // [0, 1]
  commands: string[];
}

/** Map a flight intent to X-Plane dataref writes + command names. */
export function toXPlaneDatarefs(intent: ControlIntent): XPlaneDatarefMap {
  const commands: string[] = [];
  if (intent.commands.hold) commands.push('sim/autopilot/altitude_hold');
  if (intent.commands.return_home) commands.push('sim/autopilot/return');
  if (intent.commands.land) commands.push('sim/autopilot/land');
  if (intent.commands.emergency_stop) commands.push('sim/engines/carb_heat_all_on');
  return {
    'sim/joystick/yoke_pitch_ratio': clamp(intent.axes.pitch),
    'sim/joystick/yoke_roll_ratio': clamp(intent.axes.roll),
    'sim/joystick/yoke_heading_ratio': clamp(intent.axes.yaw),
    'sim/flightmodel/engine/ENGN_thro_use[0]': clamp01(intent.axes.throttle),
    'sim/cockpit2/controls/speedbrake_ratio': clamp01(intent.axes.brake),
    commands,
  };
}

// ─── Domain-normalized views ──────────────────────────────────────────────────

export interface FlightControlView {
  throttle: number; // [0, 1]
  pitch: number; // [-1, 1]
  roll: number; // [-1, 1]
  yaw: number; // [-1, 1]
  altitude: number; // [-1, 1]
  hold: boolean;
  return_home: boolean;
  land: boolean;
  emergency_stop: boolean;
}

export interface DrivingControlView {
  throttle: number; // [0, 1]
  steering: number; // [-1, 1]
  brake: number; // [0, 1]
  handbrake: boolean;
  reverse: boolean;
  emergency_stop: boolean;
}

/** Extract a clean flight-domain view from a ControlIntent. */
export function toFlightView(intent: ControlIntent): FlightControlView {
  return {
    throttle: clamp01(intent.axes.throttle),
    pitch: clamp(intent.axes.pitch),
    roll: clamp(intent.axes.roll),
    yaw: clamp(intent.axes.yaw),
    altitude: clamp(intent.axes.altitude),
    hold: intent.commands.hold,
    return_home: intent.commands.return_home,
    land: intent.commands.land,
    emergency_stop: intent.commands.emergency_stop,
  };
}

/** Extract a clean driving-domain view from a ControlIntent. */
export function toDrivingView(intent: ControlIntent): DrivingControlView {
  return {
    throttle: clamp01(intent.axes.throttle),
    steering: clamp(intent.axes.roll), // roll axis = steering in driving domain
    brake: clamp01(intent.axes.brake),
    handbrake: intent.commands.handbrake,
    reverse: intent.commands.reverse,
    emergency_stop: intent.commands.emergency_stop,
  };
}
