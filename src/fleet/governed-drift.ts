/**
 * @file governed-drift.ts
 * @module fleet/governed-drift
 * @layer L5, L12, L13
 * @component Governed Drift — Bounded Stochastic Exploration
 * @version 3.2.4
 *
 * Formalizes bounded exploration ("drift") with hard caps and auto-zero conditions.
 *
 * Drift magnitude per robot i:
 *   δ_i = f(uncertainty, energy, risk, trust)
 *
 * Hard constraints:
 *   δ_i ≤ δ_max                   (absolute ceiling — law)
 *   δ_i = 0 when:
 *     - hazard band detected       (oscillator bus reports HAZARD mode)
 *     - trust < trust_threshold    (agent untrusted)
 *     - energy < energy_floor      (reserve protection)
 *
 * This prevents chaotic divergence. Most swarm systems lack this formalization.
 *
 * @axiom Unitarity — Drift preserves total swarm energy bounds
 * @axiom Causality — Drift auto-zeros before hazard conditions manifest
 */

import { Vec, vecScale, vecMag, vecNormalize, VEC_ZERO } from './swarm-geometry.js';
import type { SwarmMode } from './oscillator-bus.js';

// ──────────────── Configuration ────────────────

/**
 * Drift governance configuration — hard laws.
 */
export interface DriftGovernanceConfig {
  /** Absolute maximum drift magnitude δ_max (hard cap — never exceeded) */
  maxDriftMagnitude: number;
  /** Trust threshold — drift zeros below this */
  trustThreshold: number;
  /** Energy floor — drift zeros below this reserve */
  energyFloor: number;
  /** Risk ceiling — drift zeros above this risk level */
  riskCeiling: number;
  /** Uncertainty scaling factor (higher uncertainty = more drift allowed) */
  uncertaintyScale: number;
  /** Energy scaling factor (more energy = more drift budget) */
  energyScale: number;
  /** Trust scaling factor (higher trust = more drift allowed) */
  trustScale: number;
  /** Risk decay factor (higher risk = less drift allowed) */
  riskDecay: number;
  /** Drift decay per step when no stimulus */
  naturalDecay: number;
  /** Modes that suppress drift to zero */
  suppressionModes: ReadonlyArray<SwarmMode>;
}

export const DEFAULT_DRIFT_CONFIG: Readonly<DriftGovernanceConfig> = {
  maxDriftMagnitude: 1.0,
  trustThreshold: 0.2,
  energyFloor: 0.1,
  riskCeiling: 0.8,
  uncertaintyScale: 0.5,
  energyScale: 0.3,
  trustScale: 0.4,
  riskDecay: 2.0,
  naturalDecay: 0.05,
  suppressionModes: ['HAZARD', 'REGROUP'],
};

// ──────────────── Per-Node State ────────────────

/**
 * Per-robot drift inputs — the variables that determine drift budget.
 */
export interface DriftInputs {
  /** Uncertainty about environment [0, 1] — higher = more exploration needed */
  uncertainty: number;
  /** Energy reserve [0, 1] — lower = less budget for exploration */
  energy: number;
  /** Current risk assessment [0, 1] — higher = suppress drift */
  risk: number;
  /** Trust score [0, 1] — lower trust = less freedom to drift */
  trust: number;
  /** Current oscillator mode (from bus) */
  currentMode: SwarmMode;
}

/**
 * Drift computation result with full telemetry.
 */
export interface DriftResult {
  /** Computed drift vector (3D) */
  vector: Vec;
  /** Drift magnitude before cap */
  rawMagnitude: number;
  /** Drift magnitude after cap */
  cappedMagnitude: number;
  /** Was the drift capped? */
  wasCapped: boolean;
  /** Was the drift zeroed? */
  wasZeroed: boolean;
  /** Reason for zeroing (null if not zeroed) */
  zeroReason: string | null;
  /** Individual factor contributions */
  factors: DriftFactors;
}

/**
 * Breakdown of drift factors for telemetry.
 */
export interface DriftFactors {
  uncertaintyContribution: number;
  energyContribution: number;
  trustContribution: number;
  riskSuppression: number;
  computedBudget: number;
}

// ──────────────── Core Engine ────────────────

/**
 * GovernedDrift — bounded exploration with hard safety guarantees.
 *
 * No randomness without a cap. No cap without proof.
 */
export class GovernedDrift {
  private config: DriftGovernanceConfig;
  /** Per-node drift vectors (persisted between steps for decay) */
  private driftState: Map<string, Vec> = new Map();
  /** Per-node drift history for analysis */
  private driftHistory: Map<string, Array<{ magnitude: number; zeroed: boolean; timestamp: number }>> =
    new Map();
  /** Max history entries per node */
  private maxHistory: number = 100;

  constructor(config: Partial<DriftGovernanceConfig> = {}) {
    this.config = {
      ...DEFAULT_DRIFT_CONFIG,
      ...config,
      suppressionModes: config.suppressionModes ?? [...DEFAULT_DRIFT_CONFIG.suppressionModes],
    };
    // Hard cap validation — maxDriftMagnitude must be positive
    this.config.maxDriftMagnitude = Math.max(0.01, Math.abs(this.config.maxDriftMagnitude));
  }

  // ── Drift Computation ──

  /**
   * Compute the drift budget for a node given its inputs.
   *
   * δ_i = f(uncertainty, energy, risk, trust)
   *     = (u_scale · uncertainty + e_scale · energy + t_scale · trust) · exp(-r_decay · risk)
   *
   * Then clamped to [0, δ_max].
   *
   * Returns the scalar budget (direction is separate).
   */
  public computeBudget(inputs: DriftInputs): { budget: number; factors: DriftFactors } {
    const c = this.config;

    const uncertaintyContribution = c.uncertaintyScale * clamp01(inputs.uncertainty);
    const energyContribution = c.energyScale * clamp01(inputs.energy);
    const trustContribution = c.trustScale * clamp01(inputs.trust);

    // Risk exponential decay — higher risk = exponentially less drift
    const riskSuppression = Math.exp(-c.riskDecay * clamp01(inputs.risk));

    // Raw budget
    const raw = (uncertaintyContribution + energyContribution + trustContribution) * riskSuppression;

    // Hard cap
    const budget = Math.min(Math.max(raw, 0), c.maxDriftMagnitude);

    return {
      budget,
      factors: {
        uncertaintyContribution,
        energyContribution,
        trustContribution,
        riskSuppression,
        computedBudget: budget,
      },
    };
  }

  /**
   * Check auto-zero conditions. Returns null if drift is allowed,
   * or a reason string if drift must be zeroed.
   */
  public checkAutoZero(inputs: DriftInputs): string | null {
    const c = this.config;

    // Condition 1: Hazard/suppression mode
    if (c.suppressionModes.includes(inputs.currentMode)) {
      return `mode_suppressed:${inputs.currentMode}`;
    }

    // Condition 2: Trust below threshold
    if (inputs.trust < c.trustThreshold) {
      return `trust_below_threshold:${inputs.trust.toFixed(3)}<${c.trustThreshold}`;
    }

    // Condition 3: Energy below floor
    if (inputs.energy < c.energyFloor) {
      return `energy_below_floor:${inputs.energy.toFixed(3)}<${c.energyFloor}`;
    }

    // Condition 4: Risk above ceiling
    if (inputs.risk > c.riskCeiling) {
      return `risk_above_ceiling:${inputs.risk.toFixed(3)}>${c.riskCeiling}`;
    }

    return null;
  }

  /**
   * Compute drift vector for a node.
   *
   * If a direction is provided, drift is along that direction with computed magnitude.
   * If no direction, drift decays existing drift or stays zero.
   *
   * @param nodeId - Robot identifier
   * @param inputs - Current drift inputs
   * @param direction - Optional exploration direction (will be normalized)
   */
  public computeDrift(nodeId: string, inputs: DriftInputs, direction?: Vec): DriftResult {
    // Check auto-zero first
    const zeroReason = this.checkAutoZero(inputs);

    if (zeroReason) {
      // Hard zero — no drift allowed
      this.driftState.set(nodeId, { ...VEC_ZERO });
      this.recordHistory(nodeId, 0, true);

      return {
        vector: { ...VEC_ZERO },
        rawMagnitude: 0,
        cappedMagnitude: 0,
        wasCapped: false,
        wasZeroed: true,
        zeroReason,
        factors: {
          uncertaintyContribution: 0,
          energyContribution: 0,
          trustContribution: 0,
          riskSuppression: 0,
          computedBudget: 0,
        },
      };
    }

    // Compute budget
    const { budget, factors } = this.computeBudget(inputs);

    // Get direction
    let dir: Vec;
    if (direction && vecMag(direction) > 1e-12) {
      dir = vecNormalize(direction);
    } else {
      // No new direction — decay existing drift
      const existing = this.driftState.get(nodeId) ?? { ...VEC_ZERO };
      const existingMag = vecMag(existing);
      if (existingMag < 1e-12) {
        this.recordHistory(nodeId, 0, false);
        return {
          vector: { ...VEC_ZERO },
          rawMagnitude: 0,
          cappedMagnitude: 0,
          wasCapped: false,
          wasZeroed: false,
          zeroReason: null,
          factors,
        };
      }
      // Decay
      const decayed = Math.max(0, existingMag - this.config.naturalDecay);
      const decayedVec = vecScale(vecNormalize(existing), decayed);
      this.driftState.set(nodeId, decayedVec);
      this.recordHistory(nodeId, decayed, false);

      return {
        vector: decayedVec,
        rawMagnitude: existingMag,
        cappedMagnitude: decayed,
        wasCapped: false,
        wasZeroed: false,
        zeroReason: null,
        factors,
      };
    }

    // Apply budget as magnitude along direction
    const rawMagnitude = budget;
    const wasCapped = rawMagnitude > this.config.maxDriftMagnitude;
    const cappedMagnitude = Math.min(rawMagnitude, this.config.maxDriftMagnitude);
    const vector = vecScale(dir, cappedMagnitude);

    this.driftState.set(nodeId, vector);
    this.recordHistory(nodeId, cappedMagnitude, false);

    return {
      vector,
      rawMagnitude,
      cappedMagnitude,
      wasCapped,
      wasZeroed: false,
      zeroReason: null,
      factors,
    };
  }

  /**
   * Get current drift vector for a node.
   */
  public getDrift(nodeId: string): Vec {
    return this.driftState.get(nodeId) ?? { ...VEC_ZERO };
  }

  /**
   * Force-zero a node's drift (e.g., human override).
   */
  public zeroDrift(nodeId: string): void {
    this.driftState.set(nodeId, { ...VEC_ZERO });
    this.recordHistory(nodeId, 0, true);
  }

  /**
   * Zero all drift across all nodes (emergency stop).
   */
  public zeroAll(): void {
    for (const id of this.driftState.keys()) {
      this.driftState.set(id, { ...VEC_ZERO });
      this.recordHistory(id, 0, true);
    }
  }

  // ── Analysis ──

  /**
   * Get total drift energy across all nodes.
   * E_drift = Σ_i ||δ_i||²
   */
  public getTotalDriftEnergy(): number {
    let energy = 0;
    for (const drift of this.driftState.values()) {
      const m = vecMag(drift);
      energy += m * m;
    }
    return energy;
  }

  /**
   * Get average drift magnitude.
   */
  public getAverageDriftMagnitude(): number {
    if (this.driftState.size === 0) return 0;
    let total = 0;
    for (const drift of this.driftState.values()) {
      total += vecMag(drift);
    }
    return total / this.driftState.size;
  }

  /**
   * Get drift history for a node.
   */
  public getHistory(
    nodeId: string,
  ): ReadonlyArray<{ magnitude: number; zeroed: boolean; timestamp: number }> {
    return this.driftHistory.get(nodeId) ?? [];
  }

  /**
   * Get the fraction of recent steps where drift was zeroed (last N entries).
   */
  public getZeroRatio(nodeId: string, window: number = 20): number {
    const history = this.driftHistory.get(nodeId);
    if (!history || history.length === 0) return 0;

    const slice = history.slice(-window);
    const zeroCount = slice.filter((h) => h.zeroed).length;
    return zeroCount / slice.length;
  }

  // ── Internal ──

  private recordHistory(nodeId: string, magnitude: number, zeroed: boolean): void {
    let history = this.driftHistory.get(nodeId);
    if (!history) {
      history = [];
      this.driftHistory.set(nodeId, history);
    }
    history.push({ magnitude, zeroed, timestamp: Date.now() });
    // Trim
    if (history.length > this.maxHistory) {
      history.splice(0, history.length - this.maxHistory);
    }
  }

  // ── Config ──

  public getConfig(): Readonly<DriftGovernanceConfig> {
    return {
      ...this.config,
      suppressionModes: [...this.config.suppressionModes],
    };
  }
}

// ──────────────── Utilities ────────────────

function clamp01(v: number): number {
  return Math.max(0, Math.min(1, v));
}
