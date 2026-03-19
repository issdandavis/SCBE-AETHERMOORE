/**
 * @file hyperspace.ts
 * @module security-engine/hyperspace
 * @layer L1-L14
 * @component Hyperspace State Engine
 *
 * Defines and operates the N-dimensional hyperspace where tokens, agents,
 * and flows are embedded. This is the shared coordinate system that binds
 * all SCBE subsystems together.
 *
 * Dimensions (9D canonical):
 *   0: context    — 6D context hash projected to scalar manifold position
 *   1: time       — monotonic temporal coordinate (Q16.16 microseconds)
 *   2: intention  — accumulated intent vector from temporal-intent tracker
 *   3: trust      — current trust score (0 = exiled, 1 = fully trusted)
 *   4: risk       — composite risk score from pipeline layers
 *   5: entropy    — local entropy measure (spectral coherence inverse)
 *   6: policy     — aggregate policy field pressure at this point
 *   7: load       — system load normalized to [0, 1]
 *   8: behavior   — behavioral signature deviation from attractor
 *
 * Tokens are embedded into this space via the HyperspacePoint type.
 * Their position encodes state, their velocity encodes evolution,
 * and policy fields shape where they can stably exist.
 *
 * The metric on this space is a weighted Riemannian product metric
 * where each dimension has a machine-constant-defined weight.
 */

import {
  type MachineConstants,
  toQ16,
  fromQ16,
  mulQ16,
  getGlobalRegistry,
} from './machine-constants.js';

// ═══════════════════════════════════════════════════════════════
// Dimension Enumeration
// ═══════════════════════════════════════════════════════════════

/** Canonical hyperspace dimension indices */
export enum HyperDim {
  CONTEXT = 0,
  TIME = 1,
  INTENTION = 2,
  TRUST = 3,
  RISK = 4,
  ENTROPY = 5,
  POLICY = 6,
  LOAD = 7,
  BEHAVIOR = 8,
}

/** Total number of hyperspace dimensions */
export const HYPER_DIMS = 9;

/** Dimension names for serialization/logging */
export const DIMENSION_NAMES: readonly string[] = [
  'context',
  'time',
  'intention',
  'trust',
  'risk',
  'entropy',
  'policy',
  'load',
  'behavior',
] as const;

// ═══════════════════════════════════════════════════════════════
// Hyperspace Types
// ═══════════════════════════════════════════════════════════════

/** A point in 9D hyperspace */
export type HyperspaceCoord = [
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
];

/** A point in hyperspace with metadata */
export interface HyperspacePoint {
  /** 9D coordinate vector */
  readonly coords: HyperspaceCoord;
  /** Agent or token identifier */
  readonly entityId: string;
  /** Timestamp of this embedding (monotonic microseconds) */
  readonly timestampUs: number;
  /** Velocity vector (rate of change per tick) */
  readonly velocity: HyperspaceCoord;
  /** Whether this point is clamped to a stable attractor */
  readonly clamped: boolean;
}

/** Dimension weights for the product metric */
export interface DimensionWeights {
  readonly context: number;
  readonly time: number;
  readonly intention: number;
  readonly trust: number;
  readonly risk: number;
  readonly entropy: number;
  readonly policy: number;
  readonly load: number;
  readonly behavior: number;
}

/** Default dimension weights — derived from golden ratio scaling */
const PHI = 1.618033988749895;
export const DEFAULT_DIMENSION_WEIGHTS: DimensionWeights = {
  context: 1.0,
  time: PHI,
  intention: PHI ** 2, // ~2.618 — intention matters more than raw context
  trust: PHI ** 3, // ~4.236 — trust is heavily weighted
  risk: PHI ** 2, // ~2.618 — risk matches intention weight
  entropy: 1.0, // entropy is observational
  policy: PHI, // ~1.618 — policy is a shaping force
  load: 0.5, // load is informational, low weight
  behavior: PHI ** 2, // ~2.618 — behavioral deviation is critical
};

// ═══════════════════════════════════════════════════════════════
// Metric Operations
// ═══════════════════════════════════════════════════════════════

/** Convert DimensionWeights to array form */
function weightsToArray(w: DimensionWeights): number[] {
  return [w.context, w.time, w.intention, w.trust, w.risk, w.entropy, w.policy, w.load, w.behavior];
}

/**
 * Weighted Riemannian distance in hyperspace.
 *
 * d(p, q) = sqrt( sum_i w_i * (p_i - q_i)^2 )
 *
 * This is a product metric where each dimension has a machine-constant
 * weight, making the "physics" of the space configurable.
 */
export function hyperspaceDistance(
  a: HyperspaceCoord,
  b: HyperspaceCoord,
  weights?: DimensionWeights
): number {
  const w = weightsToArray(weights ?? DEFAULT_DIMENSION_WEIGHTS);
  let sum = 0;
  for (let i = 0; i < HYPER_DIMS; i++) {
    const diff = a[i] - b[i];
    sum += w[i] * diff * diff;
  }
  return Math.sqrt(sum);
}

/**
 * Q16.16 deterministic distance (integer arithmetic only in the core loop).
 * Returns the distance as a Q16.16 fixed-point value.
 */
export function hyperspaceDistanceQ16(
  a: HyperspaceCoord,
  b: HyperspaceCoord,
  weights?: DimensionWeights
): number {
  const w = weightsToArray(weights ?? DEFAULT_DIMENSION_WEIGHTS);
  let sumQ16 = 0;
  for (let i = 0; i < HYPER_DIMS; i++) {
    const diffQ16 = toQ16(a[i]) - toQ16(b[i]);
    const wQ16 = toQ16(w[i]);
    // w * diff^2 in Q16.16: mulQ16(w, mulQ16(diff, diff))
    sumQ16 += mulQ16(wQ16, mulQ16(diffQ16, diffQ16));
  }
  // sqrt in Q16.16: convert to float, sqrt, convert back
  return toQ16(Math.sqrt(fromQ16(sumQ16)));
}

/**
 * Compute the "safe origin" in hyperspace — the attractor point for
 * legitimate, cooperative behavior.
 */
export function safeOrigin(): HyperspaceCoord {
  return [
    0.0, // context: neutral
    0.0, // time: present
    0.0, // intention: benign
    1.0, // trust: fully trusted
    0.0, // risk: no risk
    0.0, // entropy: low entropy (coherent)
    0.0, // policy: no constraint pressure
    0.0, // load: idle
    0.0, // behavior: on-attractor
  ];
}

/**
 * Compute distance from safe origin — this is the "cost position" of an entity.
 * Greater distance = higher cost regime = more hostile simulated environment.
 *
 * The TIME dimension is excluded from safe-origin distance because absolute time
 * is always non-zero and monotonically increasing — it is a coordinate, not a risk
 * indicator. Time only matters for relative distances between entities (temporal
 * synchronization) and for velocity computation.
 */
export function distanceFromSafe(point: HyperspaceCoord, weights?: DimensionWeights): number {
  const origin = safeOrigin();
  // Match time dimension so it doesn't contribute to "safety distance"
  origin[HyperDim.TIME] = point[HyperDim.TIME];
  return hyperspaceDistance(point, origin, weights);
}

// ═══════════════════════════════════════════════════════════════
// Hyperspace Embedding
// ═══════════════════════════════════════════════════════════════

/** Raw context inputs for embedding an entity into hyperspace */
export interface EmbeddingInputs {
  /** 6D context vector [time, device, threat, entropy, load, behavior] */
  context6D: [number, number, number, number, number, number];
  /** Current monotonic timestamp in microseconds */
  timestampUs: number;
  /** Accumulated intent from TemporalSecurityGate */
  accumulatedIntent: number;
  /** Current trust score [0, 1] */
  trustScore: number;
  /** Composite risk from pipeline layers [0, 1+] */
  riskScore: number;
  /** Spectral entropy (inverse coherence) [0, 1] */
  spectralEntropy: number;
  /** Aggregate policy pressure at this point [0, 1+] */
  policyPressure: number;
  /** Normalized system load [0, 1] */
  systemLoad: number;
  /** Behavioral deviation from Hopfield attractor [0, 1+] */
  behaviorDeviation: number;
}

/**
 * Project 6D context vector to scalar manifold position.
 * Uses golden-ratio-weighted norm of the 6 context channels.
 */
function projectContext6D(ctx: [number, number, number, number, number, number]): number {
  const constants = getGlobalRegistry().active;
  const weights = constants.harmonic.tongueWeights;
  let sum = 0;
  let wSum = 0;
  for (let i = 0; i < 6; i++) {
    sum += weights[i] * ctx[i] * ctx[i];
    wSum += weights[i];
  }
  return Math.sqrt(sum / wSum);
}

/**
 * Embed an entity into hyperspace from raw context inputs.
 */
export function embedInHyperspace(
  entityId: string,
  inputs: EmbeddingInputs,
  prevPoint?: HyperspacePoint
): HyperspacePoint {
  const coords: HyperspaceCoord = [
    projectContext6D(inputs.context6D),
    inputs.timestampUs / 1_000_000, // normalize to seconds
    inputs.accumulatedIntent,
    inputs.trustScore,
    inputs.riskScore,
    inputs.spectralEntropy,
    inputs.policyPressure,
    inputs.systemLoad,
    inputs.behaviorDeviation,
  ];

  // Compute velocity from previous point
  let velocity: HyperspaceCoord = [0, 0, 0, 0, 0, 0, 0, 0, 0];
  if (prevPoint) {
    const dt = (inputs.timestampUs - prevPoint.timestampUs) / 1_000_000;
    if (dt > 0) {
      velocity = coords.map((c, i) => (c - prevPoint.coords[i]) / dt) as HyperspaceCoord;
    }
  }

  // Check if the point is near the safe origin (clamped to attractor)
  const dist = distanceFromSafe(coords);
  const clamped = dist < 0.1; // within 10% of safe origin

  return {
    coords,
    entityId,
    timestampUs: inputs.timestampUs,
    velocity,
    clamped,
  };
}

// ═══════════════════════════════════════════════════════════════
// Hyperspace Manifold (manages all embedded entities)
// ═══════════════════════════════════════════════════════════════

/**
 * The Hyperspace Manifold maintains the current embedding of all
 * tracked entities. It is the shared coordinate system that all
 * SCBE subsystems reference.
 */
export class HyperspaceManifold {
  private _points: Map<string, HyperspacePoint> = new Map();
  private _weights: DimensionWeights;

  constructor(weights?: DimensionWeights) {
    this._weights = weights ?? DEFAULT_DIMENSION_WEIGHTS;
  }

  /** Update or insert an entity's position in hyperspace */
  embed(entityId: string, inputs: EmbeddingInputs): HyperspacePoint {
    const prev = this._points.get(entityId);
    const point = embedInHyperspace(entityId, inputs, prev);
    this._points.set(entityId, point);
    return point;
  }

  /** Get current position of an entity */
  getPoint(entityId: string): HyperspacePoint | undefined {
    return this._points.get(entityId);
  }

  /** Get distance from safe origin for an entity */
  distanceFromSafe(entityId: string): number {
    const p = this._points.get(entityId);
    if (!p) return Infinity;
    return distanceFromSafe(p.coords, this._weights);
  }

  /** Get distance between two entities in hyperspace */
  distanceBetween(entityA: string, entityB: string): number {
    const a = this._points.get(entityA);
    const b = this._points.get(entityB);
    if (!a || !b) return Infinity;
    return hyperspaceDistance(a.coords, b.coords, this._weights);
  }

  /** Get all entities sorted by distance from safe origin (most suspicious first) */
  rankByRisk(): Array<{ entityId: string; distance: number; point: HyperspacePoint }> {
    const entries = Array.from(this._points.entries()).map(([id, point]) => ({
      entityId: id,
      distance: distanceFromSafe(point.coords, this._weights),
      point,
    }));
    entries.sort((a, b) => b.distance - a.distance);
    return entries;
  }

  /** Get all clamped (safe) entities */
  getClamped(): HyperspacePoint[] {
    return Array.from(this._points.values()).filter((p) => p.clamped);
  }

  /** Get all unclamped (drifting/suspicious) entities */
  getUnclamped(): HyperspacePoint[] {
    return Array.from(this._points.values()).filter((p) => !p.clamped);
  }

  /** Remove an entity */
  remove(entityId: string): boolean {
    return this._points.delete(entityId);
  }

  /** Get total entity count */
  get size(): number {
    return this._points.size;
  }

  /** Get all entity IDs */
  entityIds(): string[] {
    return Array.from(this._points.keys());
  }

  /** Update dimension weights (reconfigures the "physics" of the space) */
  setWeights(weights: DimensionWeights): void {
    this._weights = weights;
  }

  /** Snapshot all points for digital twin consumption */
  snapshot(): Map<string, HyperspacePoint> {
    return new Map(this._points);
  }
}
