/**
 * @file policy-fields.ts
 * @module security-engine/policy-fields
 * @layer L12, L13
 * @component Policy Field Evaluator
 *
 * Implements overlapping policy regimes as "fields" in hyperspace.
 *
 * Each policy is a function from hyperspace position → scalar force.
 * Multiple policies compose additively (like electromagnetic fields),
 * creating regions where certain behaviors are cheap (low gradient)
 * and others are expensive (high gradient).
 *
 * Policy types:
 *   - Safety:     Exponential cost near Poincare boundary
 *   - Compliance: Flat penalty for violating regulatory constraints
 *   - Resource:   Load-dependent cost scaling
 *   - Trust:      Viscous drag on low-trust entities
 *   - Role:       Coupling field — wrong role in wrong place costs more
 *   - Temporal:   Time-window constraints (actions only valid in windows)
 *
 * The composite field F(p) = sum_i alpha_i * f_i(p) determines the
 * total "policy pressure" at any point in hyperspace — dimension 6
 * of the HyperspaceCoord.
 */

import { type HyperspaceCoord, HyperDim, distanceFromSafe } from './hyperspace.js';
import { type MachineConstants, getGlobalRegistry } from './machine-constants.js';

// ═══════════════════════════════════════════════════════════════
// Policy Field Interfaces
// ═══════════════════════════════════════════════════════════════

/** A single policy field that exerts force at a hyperspace position */
export interface PolicyField {
  /** Unique policy identifier */
  readonly id: string;
  /** Human-readable name */
  readonly name: string;
  /** Policy category */
  readonly category: PolicyCategory;
  /** Whether this policy is currently active */
  enabled: boolean;
  /** Base strength multiplier (alpha_i) */
  strength: number;
  /**
   * Evaluate the scalar force this policy exerts at a hyperspace position.
   * Returns a value >= 0 where 0 = no constraint, higher = more pressure.
   */
  evaluate(point: HyperspaceCoord, constants: MachineConstants): number;
}

/** Policy categories */
export enum PolicyCategory {
  SAFETY = 'safety',
  COMPLIANCE = 'compliance',
  RESOURCE = 'resource',
  TRUST = 'trust',
  ROLE = 'role',
  TEMPORAL = 'temporal',
}

/** Result of evaluating all policy fields at a point */
export interface PolicyEvaluation {
  /** Total composite field pressure */
  readonly totalPressure: number;
  /** Per-policy breakdown */
  readonly fieldPressures: ReadonlyArray<{
    id: string;
    name: string;
    category: PolicyCategory;
    pressure: number;
  }>;
  /** Dominant policy (highest pressure contributor) */
  readonly dominantPolicy: string;
  /** Whether total pressure exceeds the danger threshold */
  readonly isDangerous: boolean;
  /** Gradient direction (which dimension is contributing most) */
  readonly gradientDim: number;
}

// ═══════════════════════════════════════════════════════════════
// Built-in Policy Fields
// ═══════════════════════════════════════════════════════════════

/**
 * Safety Field — Exponential cost as entity drifts from safe origin.
 * Uses the harmonic wall: R^(d^2) where d = distance from safe origin.
 * This is the core SCBE invariant that makes attacks computationally infeasible.
 */
export class SafetyField implements PolicyField {
  readonly id = 'safety-harmonic-wall';
  readonly name = 'Harmonic Safety Wall';
  readonly category = PolicyCategory.SAFETY;
  enabled = true;
  strength: number;

  constructor(strength?: number) {
    this.strength = strength ?? 2.0;
  }

  evaluate(point: HyperspaceCoord, constants: MachineConstants): number {
    const d = distanceFromSafe(point);
    const R = constants.harmonic.harmonicR;
    // H(d, R) = R^(d^2) — exponential cost scaling
    const wall = Math.pow(R, d * d);
    // Normalize: subtract 1 so safe origin = 0 pressure
    return this.strength * Math.max(0, wall - 1);
  }
}

/**
 * Compliance Field — Flat penalty zone for policy violations.
 * Applies constant pressure when risk exceeds compliance threshold.
 */
export class ComplianceField implements PolicyField {
  readonly id = 'compliance-threshold';
  readonly name = 'Compliance Boundary';
  readonly category = PolicyCategory.COMPLIANCE;
  enabled = true;
  strength: number;
  private _threshold: number;

  constructor(threshold: number = 0.5, strength?: number) {
    this._threshold = threshold;
    this.strength = strength ?? 1.5;
  }

  evaluate(point: HyperspaceCoord, constants: MachineConstants): number {
    const risk = point[HyperDim.RISK];
    if (risk <= this._threshold) return 0;
    // Flat penalty scaled by how far over the threshold
    const excess = risk - this._threshold;
    return this.strength * constants.policy.complianceFieldCoupling * excess;
  }
}

/**
 * Resource Field — Load-dependent cost scaling.
 * Under high system load, operations become more expensive,
 * naturally throttling aggressive behavior.
 */
export class ResourceField implements PolicyField {
  readonly id = 'resource-load-scaling';
  readonly name = 'Resource Load Field';
  readonly category = PolicyCategory.RESOURCE;
  enabled = true;
  strength: number;

  constructor(strength?: number) {
    this.strength = strength ?? 1.0;
  }

  evaluate(point: HyperspaceCoord, constants: MachineConstants): number {
    const load = point[HyperDim.LOAD];
    const risk = point[HyperDim.RISK];
    // Cost increases quadratically with load, amplified by risk
    const loadPressure = load * load * (1 + risk);
    return this.strength * loadPressure;
  }
}

/**
 * Trust Field — Viscous drag on low-trust entities.
 * Low trust creates "friction" in hyperspace: every action costs more.
 */
export class TrustField implements PolicyField {
  readonly id = 'trust-viscosity';
  readonly name = 'Trust Viscosity Field';
  readonly category = PolicyCategory.TRUST;
  enabled = true;
  strength: number;

  constructor(strength?: number) {
    this.strength = strength ?? 1.5;
  }

  evaluate(point: HyperspaceCoord, constants: MachineConstants): number {
    const trust = point[HyperDim.TRUST];
    const viscosity = constants.policy.trustFieldViscosity;
    // Inverse trust: low trust = high drag
    // Uses 1/(trust + epsilon) scaled by viscosity
    const drag = viscosity * (1 - trust) * (1 - trust);
    return this.strength * drag;
  }
}

/**
 * Role Field — Coupling constraint based on entity behavior.
 * Entities exhibiting behavior inconsistent with their role face
 * increasing pressure, like being in the "wrong part" of hyperspace.
 */
export class RoleField implements PolicyField {
  readonly id = 'role-coupling';
  readonly name = 'Role Coupling Field';
  readonly category = PolicyCategory.ROLE;
  enabled = true;
  strength: number;

  constructor(strength?: number) {
    this.strength = strength ?? 1.0;
  }

  evaluate(point: HyperspaceCoord, constants: MachineConstants): number {
    const behavior = point[HyperDim.BEHAVIOR];
    const radius = constants.policy.roleFieldRadius;
    // Behavior deviation beyond role radius incurs cost
    if (behavior <= radius) return 0;
    const excess = behavior - radius;
    return this.strength * excess * excess;
  }
}

/**
 * Temporal Field — Time-window constraints.
 * Actions outside valid time windows face increasing cost.
 * Uses intention dimension to detect temporal anomalies.
 */
export class TemporalField implements PolicyField {
  readonly id = 'temporal-window';
  readonly name = 'Temporal Window Field';
  readonly category = PolicyCategory.TEMPORAL;
  enabled = true;
  strength: number;

  constructor(strength?: number) {
    this.strength = strength ?? 1.0;
  }

  evaluate(point: HyperspaceCoord, constants: MachineConstants): number {
    const intention = point[HyperDim.INTENTION];
    const entropy = point[HyperDim.ENTROPY];
    // High intention + high entropy = temporal anomaly
    // (sustained intent with high uncertainty is suspicious)
    const anomaly = intention * entropy;
    return this.strength * Math.max(0, anomaly);
  }
}

// ═══════════════════════════════════════════════════════════════
// Policy Field Evaluator
// ═══════════════════════════════════════════════════════════════

/** Danger threshold — total pressure above this triggers escalation */
const DANGER_THRESHOLD = 5.0;

/**
 * PolicyFieldEvaluator manages and evaluates a set of overlapping policy fields.
 * It computes the composite "policy pressure" at any point in hyperspace.
 */
export class PolicyFieldEvaluator {
  private _fields: PolicyField[] = [];
  private _dangerThreshold: number;

  constructor(dangerThreshold: number = DANGER_THRESHOLD) {
    this._dangerThreshold = dangerThreshold;
  }

  /** Add a policy field */
  addField(field: PolicyField): void {
    // Enforce max active policies
    const constants = getGlobalRegistry().active;
    if (this._fields.length >= constants.policy.maxActivePolicies) {
      throw new RangeError(
        `Cannot exceed ${constants.policy.maxActivePolicies} active policy fields`
      );
    }
    this._fields.push(field);
  }

  /** Remove a policy field by ID */
  removeField(id: string): boolean {
    const before = this._fields.length;
    this._fields = this._fields.filter((f) => f.id !== id);
    return this._fields.length < before;
  }

  /** Get a field by ID */
  getField(id: string): PolicyField | undefined {
    return this._fields.find((f) => f.id === id);
  }

  /** List all registered fields */
  listFields(): ReadonlyArray<PolicyField> {
    return this._fields;
  }

  /**
   * Evaluate all active policy fields at a hyperspace position.
   * Returns the composite pressure and per-field breakdown.
   */
  evaluate(point: HyperspaceCoord): PolicyEvaluation {
    const constants = getGlobalRegistry().active;
    const fieldPressures: Array<{
      id: string;
      name: string;
      category: PolicyCategory;
      pressure: number;
    }> = [];

    let totalPressure = 0;
    let maxPressure = 0;
    let dominantPolicy = 'none';
    let gradientDim = 0;
    let maxDimContribution = 0;

    for (const field of this._fields) {
      if (!field.enabled) continue;

      const pressure = field.evaluate(point, constants);
      fieldPressures.push({
        id: field.id,
        name: field.name,
        category: field.category,
        pressure,
      });
      totalPressure += pressure;

      if (pressure > maxPressure) {
        maxPressure = pressure;
        dominantPolicy = field.id;
      }
    }

    // Determine gradient direction by perturbing each dimension
    const epsilon = 0.001;
    for (let dim = 0; dim < point.length; dim++) {
      const perturbed = [...point] as HyperspaceCoord;
      perturbed[dim] += epsilon;

      let perturbedTotal = 0;
      for (const field of this._fields) {
        if (!field.enabled) continue;
        perturbedTotal += field.evaluate(perturbed, constants);
      }

      const gradient = Math.abs(perturbedTotal - totalPressure) / epsilon;
      if (gradient > maxDimContribution) {
        maxDimContribution = gradient;
        gradientDim = dim;
      }
    }

    return {
      totalPressure,
      fieldPressures,
      dominantPolicy,
      isDangerous: totalPressure > this._dangerThreshold,
      gradientDim,
    };
  }

  /** Create a standard evaluator with all built-in policy fields */
  static createStandard(): PolicyFieldEvaluator {
    const evaluator = new PolicyFieldEvaluator();
    evaluator.addField(new SafetyField());
    evaluator.addField(new ComplianceField());
    evaluator.addField(new ResourceField());
    evaluator.addField(new TrustField());
    evaluator.addField(new RoleField());
    evaluator.addField(new TemporalField());
    return evaluator;
  }
}
