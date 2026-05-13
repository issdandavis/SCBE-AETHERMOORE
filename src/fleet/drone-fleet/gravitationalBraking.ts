/**
 * @file gravitationalBraking.ts
 * @module fleet/drone-fleet/gravitationalBraking
 * @layer Layer 11, Layer 13
 * @component Gravitational Braking Simulation for Off-Path Agents
 *
 * Models a control-rate reduction as an agent diverges from an authorized
 * flight path. This module emits deterministic braking factors for simulation
 * and governance tests; it does not claim hardware-level clock control.
 *
 * Core formula:
 *   tG = t · (1 - (k · d) / (r + ε))
 *
 * where:
 *   d = geometric divergence from authorized flight path
 *   r = trust radius
 *   k = scaling constant
 *   ε = epsilon (prevents division by zero)
 *
 * As d approaches r, tG approaches zero in the simulation and downstream
 * policy can mark the agent for neutralization.
 *
 * Patent: USPTO Provisional #63/961,403 — Gravitational Time Axis binding
 */

// A3: Causality — time ordering enforced via gravitational dilation

/** Configuration for gravitational braking */
export interface GravitationalBrakingConfig {
  /** Scaling constant (default 1.0) */
  k: number;
  /** Trust radius — divergence at which tG reaches zero (default 1.0) */
  trustRadius: number;
  /** Epsilon to prevent division by zero (default 1e-9) */
  epsilon: number;
  /** Minimum time dilation factor before declaring event horizon (default 0.01) */
  eventHorizonThreshold: number;
}

/** Result of gravitational braking computation */
export interface BrakingResult {
  /** Dilated time: tG = t · (1 - k·d / (r + ε)) */
  dilatedTime: number;
  /** Time dilation factor in [0, 1] — 0 = frozen, 1 = normal */
  dilationFactor: number;
  /** Whether drone has entered the event horizon */
  isEventHorizon: boolean;
  /** Whether drone should be neutralized (factor below threshold) */
  shouldNeutralize: boolean;
  /** Geometric divergence that was measured */
  divergence: number;
  /** Effective CPU clock multiplier */
  clockMultiplier: number;
}

/** Drone flight state for divergence monitoring */
export interface DroneFlightState {
  /** Current 3D position */
  position: [number, number, number];
  /** Current velocity vector */
  velocity: [number, number, number];
  /** Drone identifier */
  droneId: string;
  /** Current internal clock time */
  clockTime: number;
}

/** Authorized flight path waypoint */
export interface FlightPathWaypoint {
  /** 3D position */
  position: [number, number, number];
  /** Expected arrival time */
  time: number;
}

export const DEFAULT_BRAKING_CONFIG: GravitationalBrakingConfig = {
  k: 1.0,
  trustRadius: 1.0,
  epsilon: 1e-9,
  eventHorizonThreshold: 0.01,
};

/**
 * Compute geometric divergence between drone position and nearest
 * point on authorized flight path.
 *
 * @param dronePos - Current drone 3D position
 * @param path - Authorized flight path waypoints
 * @returns Minimum Euclidean distance to any path segment
 */
export function computeDivergence(
  dronePos: [number, number, number],
  path: FlightPathWaypoint[]
): number {
  if (path.length === 0) return Infinity;
  if (path.length === 1) {
    return euclideanDistance3D(dronePos, path[0].position);
  }

  let minDist = Infinity;
  for (let i = 0; i < path.length - 1; i++) {
    const d = pointToSegmentDistance(dronePos, path[i].position, path[i + 1].position);
    if (d < minDist) minDist = d;
  }
  return minDist;
}

/**
 * Compute gravitational time dilation.
 *
 * tG = t · (1 - (k · d) / (r + ε))
 *
 * Clamped: dilation factor is in [0, 1]. When d ≥ r the factor is 0.
 *
 * @param clockTime - Drone's internal clock time (t)
 * @param divergence - Geometric divergence (d)
 * @param config - Braking configuration
 * @returns BrakingResult
 */
export function computeGravitationalBraking(
  clockTime: number,
  divergence: number,
  config: GravitationalBrakingConfig = DEFAULT_BRAKING_CONFIG
): BrakingResult {
  const { k, trustRadius, epsilon, eventHorizonThreshold } = config;

  // A4: Clamping — divergence and factor are clamped to valid range
  const d = Math.max(0, divergence);
  const dilationFactor = Math.max(0, 1 - (k * d) / (trustRadius + epsilon));
  const dilatedTime = clockTime * dilationFactor;
  const isEventHorizon = dilationFactor <= 0;
  const shouldNeutralize = dilationFactor < eventHorizonThreshold;

  return {
    dilatedTime,
    dilationFactor,
    isEventHorizon,
    shouldNeutralize,
    divergence: d,
    clockMultiplier: dilationFactor,
  };
}

/**
 * Monitor a drone's flight state and apply gravitational braking.
 *
 * @param drone - Current drone flight state
 * @param authorizedPath - Authorized flight path
 * @param config - Braking configuration
 * @returns BrakingResult with measured divergence
 */
export function monitorAndBrake(
  drone: DroneFlightState,
  authorizedPath: FlightPathWaypoint[],
  config: GravitationalBrakingConfig = DEFAULT_BRAKING_CONFIG
): BrakingResult {
  const divergence = computeDivergence(drone.position, authorizedPath);
  return computeGravitationalBraking(drone.clockTime, divergence, config);
}

/**
 * Compute the divergence at which the drone will reach event horizon.
 * Useful for early-warning systems.
 *
 * @param config - Braking configuration
 * @returns Critical divergence value
 */
export function criticalDivergence(
  config: GravitationalBrakingConfig = DEFAULT_BRAKING_CONFIG
): number {
  return (config.trustRadius + config.epsilon) / config.k;
}

// ── Internal helpers ─────────────────────────────────────────────

function euclideanDistance3D(a: [number, number, number], b: [number, number, number]): number {
  const dx = a[0] - b[0];
  const dy = a[1] - b[1];
  const dz = a[2] - b[2];
  return Math.sqrt(dx * dx + dy * dy + dz * dz);
}

function pointToSegmentDistance(
  p: [number, number, number],
  a: [number, number, number],
  b: [number, number, number]
): number {
  const ab = [b[0] - a[0], b[1] - a[1], b[2] - a[2]];
  const ap = [p[0] - a[0], p[1] - a[1], p[2] - a[2]];
  const abLenSq = ab[0] * ab[0] + ab[1] * ab[1] + ab[2] * ab[2];

  if (abLenSq < 1e-12) return euclideanDistance3D(p, a);

  const t = Math.max(0, Math.min(1, (ap[0] * ab[0] + ap[1] * ab[1] + ap[2] * ab[2]) / abLenSq));
  const closest: [number, number, number] = [a[0] + t * ab[0], a[1] + t * ab[1], a[2] + t * ab[2]];
  return euclideanDistance3D(p, closest);
}
