/**
 * @file resource-harmonic.ts
 * @module fleet/polly-pads/resource-harmonic
 * @layer Layer 12
 * @component Resource-Aware Harmonic Wall
 * @version 1.0.0
 *
 * Extends the Layer 12 Harmonic Wall with resource scarcity multipliers.
 *
 * Core formula:
 *   H_resource(d*, R, resources) = R * pi^(phi * d*) * Product(S_i)
 *
 * Where each scarcity multiplier:
 *   S_i = 1 / (current_i)^2   when current > critical_threshold
 *   S_i = Infinity             when current <= critical_threshold (hard deny)
 *
 * Effect: as resources deplete, harmonic cost grows quadratically per resource,
 * making non-essential actions prohibitively expensive. When any resource
 * crosses its critical threshold the cost becomes infinite — a hard lock that
 * "freezes" the agent to preserve the swarm.
 *
 * Designed for: Mars rovers, autonomous drones, submarine ops, any fleet
 * operating under constrained or non-renewable resource budgets.
 */

import {
  harmonicCost,
  scbeDecide,
  type SCBEThresholds,
  DEFAULT_THRESHOLDS,
} from '../../harmonic/voxelRecord.js';
import type { Decision } from '../../harmonic/scbe_voxel_types.js';
import { type UnitState, createUnitState } from '../polly-pad-runtime.js';

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════

/** Golden ratio phi — local copy for self-contained math */
const PHI = (1 + Math.sqrt(5)) / 2;

// ═══════════════════════════════════════════════════════════════
// Resource State Types
// ═══════════════════════════════════════════════════════════════

/** Individual resource metric */
export interface ResourceMetric {
  /** Resource name (e.g. "power", "bandwidth") */
  name: string;
  /** Current level [0, 1] where 1 = full, 0 = depleted */
  current: number;
  /** Critical threshold — below this, resource is in danger zone (hard deny) */
  criticalThreshold: number;
  /** Warning threshold — above critical, below this triggers elevated cost */
  warningThreshold: number;
  /** Depletion rate per hour (negative = consuming, positive = charging) */
  ratePerHour: number;
}

/** Standard resource set for a space unit */
export interface ResourceState {
  /** Electrical power supply [0, 1] */
  power: ResourceMetric;
  /** Communication bandwidth [0, 1] */
  bandwidth: ResourceMetric;
  /** Thermal headroom [0, 1] (1 = cool, 0 = overheating) */
  thermalMargin: ResourceMetric;
  /** Mechanical wear (inverted: 1 = fresh, 0 = worn out) */
  mechanicalWear: ResourceMetric;
  /** Propellant remaining [0, 1] */
  propellant: ResourceMetric;
  /** On-board storage [0, 1] */
  storage: ResourceMetric;
}

/** Extended unit state with resource tracking */
export interface ResourceAwareUnitState extends UnitState {
  /** Full resource state for this unit */
  resources: ResourceState;
}

/** Result of a resource-aware SCBE decision */
export interface ResourceAwareDecisionResult {
  /** SCBE decision: ALLOW, QUARANTINE, or DENY */
  decision: Decision;
  /** Effective harmonic cost (resource-adjusted) */
  hEff: number;
  /** Combined scarcity product across consumed resources */
  scarcity: number;
  /** Name of the resource closest to critical (the bottleneck) */
  limitingResource?: string;
}

// ═══════════════════════════════════════════════════════════════
// Scarcity Multiplier Math
// ═══════════════════════════════════════════════════════════════

/**
 * Compute scarcity multiplier for a single resource.
 *
 * S_i = 1 / (current)^2   when current > critical_threshold
 * S_i = Infinity           when current <= critical_threshold (hard deny)
 *
 * At full resource (current = 1.0): S_i = 1.0 (no penalty)
 * At half resource (current = 0.5): S_i = 4.0 (4x cost)
 * At quarter (current = 0.25):      S_i = 16.0 (16x cost)
 * At 10% (current = 0.10):          S_i = 100.0 (100x cost)
 * Below critical:                    S_i = Infinity (hard lock)
 *
 * @param resource - The resource metric to evaluate
 * @returns Scarcity multiplier >= 1.0 (or Infinity)
 */
export function scarcityMultiplier(resource: ResourceMetric): number {
  // A4: Clamping — at or below critical threshold, cost is infinite (hard deny)
  if (resource.current <= resource.criticalThreshold) {
    return Infinity;
  }

  // S_i = 1/r^2 where r = current resource level
  const r = resource.current;
  return 1 / (r * r);
}

/**
 * Compute combined scarcity product across all consumed resources.
 *
 * Only includes resources that the action actually uses, so a
 * comms-only action is not penalized by low propellant.
 *
 * Combined = Product(S_i) for each i in consumedResources
 *
 * If consumedResources is empty, returns 1.0 (no scarcity penalty).
 * If any consumed resource is at or below critical, returns Infinity.
 *
 * @param resources - Full resource state of the unit
 * @param consumedResources - Which resources this action uses (e.g., ['power', 'bandwidth'])
 * @returns Product of scarcity multipliers for consumed resources
 */
export function combinedScarcity(
  resources: ResourceState,
  consumedResources: (keyof ResourceState)[],
): number {
  if (consumedResources.length === 0) return 1.0;

  let product = 1.0;

  for (const key of consumedResources) {
    const metric = resources[key];
    const si = scarcityMultiplier(metric);

    // Short-circuit: if any resource is critical, total cost is infinite
    if (!isFinite(si)) return Infinity;

    // Product(S_i) — multiplicative composition across resources
    product *= si;
  }

  return product;
}

/**
 * Resource-aware harmonic cost.
 *
 * H_resource = harmonicCost(dStar, R) * combinedScarcity
 *            = R * pi^(phi * d*) * Product(S_i)
 *
 * This is the upgraded Layer 12 formula for space missions. The base
 * harmonic wall still enforces exponential cost with hyperbolic distance;
 * the scarcity multiplier further penalizes actions when resources are
 * depleted, "freezing" non-essential agents to save the swarm.
 *
 * @param dStar - Hyperbolic realm distance d*
 * @param R - Base cost scaling factor (default 1.5)
 * @param resources - Full resource state of the unit
 * @param consumedResources - Which resources this action uses
 * @returns Resource-adjusted harmonic cost (may be Infinity)
 */
export function resourceAwareHarmonicCost(
  dStar: number,
  R: number,
  resources: ResourceState,
  consumedResources: (keyof ResourceState)[],
): number {
  // H_base = R * pi^(phi * d*) — standard Layer 12 wall
  const hBase = harmonicCost(dStar, R);

  // Scarcity = Product(S_i) for consumed resources
  const scarcity = combinedScarcity(resources, consumedResources);

  // H_resource = H_base * Scarcity
  return hBase * scarcity;
}

/**
 * Resource-aware SCBE decision.
 *
 * Wraps scbeDecide() but uses resource-adjusted hEff. This means that
 * as resources deplete, agents naturally get QUARANTINED then DENIED
 * even if their hyperbolic distance d* is still acceptable.
 *
 * Also identifies the limiting resource — the one closest to critical
 * or with the highest scarcity multiplier — so the fleet manager knows
 * which resource to replenish first.
 *
 * @param dStar - Hyperbolic realm distance d*
 * @param coherence - NK coherence [0, 1]
 * @param resources - Full resource state of the unit
 * @param consumedResources - Which resources this action uses
 * @param R - Base cost scaling factor (default 1.5)
 * @param thresholds - SCBE governance thresholds (default DEFAULT_THRESHOLDS)
 * @returns Decision result with hEff, scarcity, and limiting resource
 */
export function resourceAwareDecide(
  dStar: number,
  coherence: number,
  resources: ResourceState,
  consumedResources: (keyof ResourceState)[],
  R: number = 1.5,
  thresholds: SCBEThresholds = DEFAULT_THRESHOLDS,
): ResourceAwareDecisionResult {
  // Compute resource-adjusted harmonic cost
  const scarcity = combinedScarcity(resources, consumedResources);
  const hEff = resourceAwareHarmonicCost(dStar, R, resources, consumedResources);

  // Find the limiting resource (highest scarcity multiplier = closest to critical)
  let limitingResource: string | undefined;
  let maxScarcity = 0;

  for (const key of consumedResources) {
    const metric = resources[key];
    const si = scarcityMultiplier(metric);

    if (si > maxScarcity) {
      maxScarcity = si;
      limitingResource = metric.name;
    }
  }

  // Delegate to standard L13 decision gate with resource-adjusted hEff
  const decision = scbeDecide(dStar, coherence, hEff, thresholds);

  return {
    decision,
    hEff,
    scarcity,
    limitingResource,
  };
}

// ═══════════════════════════════════════════════════════════════
// Resource Prediction
// ═══════════════════════════════════════════════════════════════

/**
 * Predict resource state at a future time.
 *
 * Uses linear extrapolation from current depletion/charging rates.
 * All predicted levels are clamped to [0, 1].
 *
 * predicted_level = clamp(current + ratePerHour * hoursAhead, 0, 1)
 *
 * @param current - Current resource state
 * @param hoursAhead - Hours to project forward (must be >= 0)
 * @returns Predicted resource state with levels clamped to [0, 1]
 */
export function predictResources(current: ResourceState, hoursAhead: number): ResourceState {
  const keys: (keyof ResourceState)[] = [
    'power',
    'bandwidth',
    'thermalMargin',
    'mechanicalWear',
    'propellant',
    'storage',
  ];

  const predicted = {} as ResourceState;

  for (const key of keys) {
    const metric = current[key];
    // Linear extrapolation: level_future = level_now + rate * dt
    const rawLevel = metric.current + metric.ratePerHour * hoursAhead;
    // A4: Clamping to [0, 1] — cannot exceed full or go below zero
    const clampedLevel = Math.max(0, Math.min(1, rawLevel));

    predicted[key] = {
      ...metric,
      current: clampedLevel,
    };
  }

  return predicted;
}

/**
 * Compute "time to critical" for each resource.
 *
 * How many hours until each resource hits its critical threshold,
 * assuming current depletion rate continues linearly.
 *
 * t_critical = (current - criticalThreshold) / |ratePerHour|
 *
 * Returns Infinity if the resource is:
 * - Charging (positive rate) or stable (zero rate)
 * - Already below critical (returns 0 in that case)
 *
 * @param resources - Current resource state
 * @returns Map of resource name to hours until critical
 */
export function timeToCritical(resources: ResourceState): Record<keyof ResourceState, number> {
  const keys: (keyof ResourceState)[] = [
    'power',
    'bandwidth',
    'thermalMargin',
    'mechanicalWear',
    'propellant',
    'storage',
  ];

  const result = {} as Record<keyof ResourceState, number>;

  for (const key of keys) {
    const metric = resources[key];

    // Already below critical — time to critical is 0
    if (metric.current <= metric.criticalThreshold) {
      result[key] = 0;
      continue;
    }

    // If rate is non-negative (stable or charging), resource never hits critical
    if (metric.ratePerHour >= 0) {
      result[key] = Infinity;
      continue;
    }

    // t = (current - threshold) / |rate|
    // Rate is negative (consuming), so |rate| = -rate
    const margin = metric.current - metric.criticalThreshold;
    const absRate = -metric.ratePerHour;
    result[key] = margin / absRate;
  }

  return result;
}

/**
 * Ambient risk score: weighted average of resource scarcities.
 *
 * This runs continuously in the Systems mode pad as a background monitor.
 * It considers ALL resources (not just consumed ones) to give a holistic
 * picture of the unit's resource health.
 *
 * risk = 1 - (1/N) * Sum(current_i)   for all N resources
 *
 * Returns a value in [0, 1] where:
 *   0 = all resources at 100% (perfectly healthy)
 *   1 = all resources at 0% (fully depleted / critical)
 *
 * If any resource is at or below its critical threshold, returns 1.0
 * immediately (critical override).
 *
 * @param resources - Current resource state
 * @returns Risk score in [0, 1]
 */
export function ambientRiskScore(resources: ResourceState): number {
  const keys: (keyof ResourceState)[] = [
    'power',
    'bandwidth',
    'thermalMargin',
    'mechanicalWear',
    'propellant',
    'storage',
  ];

  let sum = 0;

  for (const key of keys) {
    const metric = resources[key];

    // Critical override: if any resource is at or below critical, risk = 1.0
    if (metric.current <= metric.criticalThreshold) {
      return 1.0;
    }

    sum += metric.current;
  }

  // risk = 1 - mean(current_i)
  // When all at 1.0: risk = 1 - 1.0 = 0.0 (healthy)
  // When all at 0.0: risk = 1 - 0.0 = 1.0 (depleted)
  return 1 - sum / keys.length;
}

// ═══════════════════════════════════════════════════════════════
// Resource-Aware Unit State Factory
// ═══════════════════════════════════════════════════════════════

/**
 * Create default resource state for a Mars surface unit.
 *
 * Sensible defaults for a freshly deployed rover or drone:
 * - All resources at 100% (full charge, fresh hardware)
 * - Conservative critical thresholds (5-15% depending on resource)
 * - Warning thresholds at 20-30%
 * - Typical depletion rates for sol-length operations
 *
 * @returns Default ResourceState with all resources at full capacity
 */
export function createDefaultResources(): ResourceState {
  return {
    power: {
      name: 'power',
      current: 1.0,
      criticalThreshold: 0.05,
      warningThreshold: 0.20,
      ratePerHour: -0.02, // ~50 hours of operation on full charge
    },
    bandwidth: {
      name: 'bandwidth',
      current: 1.0,
      criticalThreshold: 0.05,
      warningThreshold: 0.20,
      ratePerHour: 0.0, // Bandwidth is usually stable (not consumed)
    },
    thermalMargin: {
      name: 'thermalMargin',
      current: 1.0,
      criticalThreshold: 0.10,
      warningThreshold: 0.25,
      ratePerHour: -0.01, // Slow thermal degradation
    },
    mechanicalWear: {
      name: 'mechanicalWear',
      current: 1.0,
      criticalThreshold: 0.10,
      warningThreshold: 0.30,
      ratePerHour: -0.005, // Very slow mechanical wear
    },
    propellant: {
      name: 'propellant',
      current: 1.0,
      criticalThreshold: 0.15,
      warningThreshold: 0.30,
      ratePerHour: -0.03, // ~33 hours at full burn
    },
    storage: {
      name: 'storage',
      current: 1.0,
      criticalThreshold: 0.05,
      warningThreshold: 0.20,
      ratePerHour: -0.01, // Gradual storage consumption from telemetry
    },
  };
}

/**
 * Create a ResourceAwareUnitState with sensible defaults for a fresh Mars rover/drone.
 *
 * Combines createUnitState() with createDefaultResources(), applying
 * any resource overrides provided.
 *
 * @param unitId - Unique unit identifier
 * @param position - Initial 3D position [x, y, z] (default [0, 0, 0])
 * @param overrides - Partial resource state overrides (merged with defaults)
 * @returns A fully initialized ResourceAwareUnitState
 */
export function createResourceAwareUnit(
  unitId: string,
  position?: [number, number, number],
  overrides?: Partial<ResourceState>,
): ResourceAwareUnitState {
  const [x, y, z] = position ?? [0, 0, 0];

  // Build base unit state via standard factory
  const baseState = createUnitState(unitId, x, y, z);

  // Build resource state with defaults, applying overrides
  const defaultResources = createDefaultResources();
  const resources: ResourceState = {
    power: overrides?.power ?? defaultResources.power,
    bandwidth: overrides?.bandwidth ?? defaultResources.bandwidth,
    thermalMargin: overrides?.thermalMargin ?? defaultResources.thermalMargin,
    mechanicalWear: overrides?.mechanicalWear ?? defaultResources.mechanicalWear,
    propellant: overrides?.propellant ?? defaultResources.propellant,
    storage: overrides?.storage ?? defaultResources.storage,
  };

  return {
    ...baseState,
    resources,
  };
}
