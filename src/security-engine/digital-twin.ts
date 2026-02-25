/**
 * @file digital-twin.ts
 * @module security-engine/digital-twin
 * @layer L12, L13, L14
 * @component Digital Twin Governor
 *
 * Deterministic control oracle that runs a real-time predictive model
 * of the security manifold. The twin:
 *
 *   1. Ingests hyperspace snapshots at non-harmonic tick intervals
 *   2. Predicts near-future state via exponential moving averages
 *   3. Adjusts AQM thresholds, routing weights, and shaper parameters
 *   4. Operates in Q16.16 fixed-point for cross-platform determinism
 *
 * Tick rate: 144.72 Hz (non-harmonic — avoids 50/60Hz grid aliasing)
 *
 * The twin is NOT a physics simulation — it is a machine-science control
 * loop that uses physics-style invariants as its coordination substrate.
 *
 * Control outputs:
 *   - AQM threshold adjustments (how aggressively to queue/drop)
 *   - Routing cost multipliers (latency gradient shaping)
 *   - Trust decay rate overrides (tighten/relax trust)
 *   - Policy field strength adjustments (reshape the "physics")
 */

import {
  type MachineConstants,
  getGlobalRegistry,
  toQ16,
  fromQ16,
  mulQ16,
} from './machine-constants.js';
import type { HyperspacePoint } from './hyperspace.js';
import { distanceFromSafe } from './hyperspace.js';

// ═══════════════════════════════════════════════════════════════
// Twin State
// ═══════════════════════════════════════════════════════════════

/** Aggregated statistics from a hyperspace snapshot */
export interface ManifoldStats {
  /** Total entities tracked */
  entityCount: number;
  /** Mean distance from safe origin */
  meanDistance: number;
  /** Max distance from safe origin */
  maxDistance: number;
  /** Fraction of entities clamped to attractor */
  clampedFraction: number;
  /** Mean trust score */
  meanTrust: number;
  /** Mean accumulated intent */
  meanIntent: number;
  /** Entities in danger zone (distance > 1.0) */
  dangerCount: number;
  /** Exiled entity count */
  exiledCount: number;
}

/** Control outputs from the digital twin */
export interface ControlOutputs {
  /** AQM drop probability multiplier [0.5, 2.0] */
  aqmMultiplier: number;
  /** Routing cost base multiplier [1.0, 10.0] */
  routingCostBase: number;
  /** Trust decay rate override (null = use default) */
  trustDecayOverride: number | null;
  /** Safety field strength override */
  safetyFieldStrength: number;
  /** Compliance field coupling override */
  complianceFieldCoupling: number;
  /** Threat level assessment [0, 1] */
  threatLevel: number;
  /** Whether the twin recommends tightening controls */
  tighten: boolean;
  /** Tick number when this output was computed */
  tickNumber: number;
}

/** Internal EMA (Exponential Moving Average) state */
interface EMAState {
  meanDistance: number;
  maxDistance: number;
  meanTrust: number;
  meanIntent: number;
  dangerFraction: number;
  threatLevel: number;
}

// ═══════════════════════════════════════════════════════════════
// Digital Twin Governor
// ═══════════════════════════════════════════════════════════════

/**
 * The Digital Twin Governor maintains a predictive model of the
 * security manifold and outputs control adjustments at each tick.
 *
 * It runs at 144.72 Hz (configurable via machine constants) using
 * Q16.16 fixed-point arithmetic for deterministic cross-platform
 * behavior.
 *
 * The twin is the "global governor" — it sees the whole manifold
 * and adjusts the "physics" (machine constants) to keep the system
 * stable.
 */
export class DigitalTwinGovernor {
  private _tickCount: number = 0;
  private _ema: EMAState;
  private _history: ManifoldStats[] = [];
  private _lastOutputs: ControlOutputs | null = null;
  private _emaAlpha: number; // EMA smoothing factor

  /** Maximum history entries to retain */
  private readonly MAX_HISTORY = 1000;

  constructor(emaAlpha: number = 0.1) {
    this._emaAlpha = emaAlpha;
    this._ema = {
      meanDistance: 0,
      maxDistance: 0,
      meanTrust: 1.0,
      meanIntent: 0,
      dangerFraction: 0,
      threatLevel: 0,
    };
  }

  /** Current tick count */
  get tickCount(): number {
    return this._tickCount;
  }

  /** Last computed control outputs */
  get lastOutputs(): ControlOutputs | null {
    return this._lastOutputs;
  }

  /** Current EMA state (for telemetry) */
  get emaState(): Readonly<EMAState> {
    return this._ema;
  }

  /**
   * Compute ManifoldStats from a hyperspace snapshot.
   */
  computeStats(
    points: Map<string, HyperspacePoint>,
    exiledCount: number,
  ): ManifoldStats {
    if (points.size === 0) {
      return {
        entityCount: 0,
        meanDistance: 0,
        maxDistance: 0,
        clampedFraction: 1.0,
        meanTrust: 1.0,
        meanIntent: 0,
        dangerCount: 0,
        exiledCount,
      };
    }

    let totalDistance = 0;
    let maxDistance = 0;
    let clampedCount = 0;
    let dangerCount = 0;
    let totalTrust = 0;
    let totalIntent = 0;

    for (const point of points.values()) {
      const dist = distanceFromSafe(point.coords);
      totalDistance += dist;
      if (dist > maxDistance) maxDistance = dist;
      if (point.clamped) clampedCount++;
      if (dist > 1.0) dangerCount++;
      // Trust is dimension 3, intent is dimension 2
      totalTrust += point.coords[3];
      totalIntent += point.coords[2];
    }

    const n = points.size;
    return {
      entityCount: n,
      meanDistance: totalDistance / n,
      maxDistance,
      clampedFraction: clampedCount / n,
      meanTrust: totalTrust / n,
      meanIntent: totalIntent / n,
      dangerCount,
      exiledCount,
    };
  }

  /**
   * Run one tick of the digital twin.
   *
   * Ingests current manifold stats, updates EMA predictions,
   * and outputs control adjustments.
   *
   * This should be called at the non-harmonic tick rate (144.72 Hz).
   */
  tick(stats: ManifoldStats): ControlOutputs {
    const constants = getGlobalRegistry().active;
    this._tickCount++;

    // Store history
    this._history.push(stats);
    if (this._history.length > this.MAX_HISTORY) {
      this._history = this._history.slice(-this.MAX_HISTORY);
    }

    // Update EMA using Q16.16 for determinism
    const alphaQ16 = toQ16(this._emaAlpha);
    const oneMinusAlphaQ16 = toQ16(1.0 - this._emaAlpha);

    this._ema.meanDistance = fromQ16(
      mulQ16(alphaQ16, toQ16(stats.meanDistance)) +
      mulQ16(oneMinusAlphaQ16, toQ16(this._ema.meanDistance)),
    );
    this._ema.maxDistance = fromQ16(
      mulQ16(alphaQ16, toQ16(stats.maxDistance)) +
      mulQ16(oneMinusAlphaQ16, toQ16(this._ema.maxDistance)),
    );
    this._ema.meanTrust = fromQ16(
      mulQ16(alphaQ16, toQ16(stats.meanTrust)) +
      mulQ16(oneMinusAlphaQ16, toQ16(this._ema.meanTrust)),
    );
    this._ema.meanIntent = fromQ16(
      mulQ16(alphaQ16, toQ16(stats.meanIntent)) +
      mulQ16(oneMinusAlphaQ16, toQ16(this._ema.meanIntent)),
    );

    // Compute danger fraction
    const dangerFraction =
      stats.entityCount > 0 ? stats.dangerCount / stats.entityCount : 0;
    this._ema.dangerFraction = fromQ16(
      mulQ16(alphaQ16, toQ16(dangerFraction)) +
      mulQ16(oneMinusAlphaQ16, toQ16(this._ema.dangerFraction)),
    );

    // Compute threat level [0, 1]
    // Weighted combination of distance, intent, danger fraction, trust inverse
    const threatRaw =
      0.3 * Math.min(1, this._ema.meanDistance) +
      0.25 * Math.min(1, this._ema.meanIntent / constants.temporal.maxIntentAccumulation) +
      0.25 * this._ema.dangerFraction +
      0.2 * (1 - this._ema.meanTrust);
    this._ema.threatLevel = Math.max(0, Math.min(1, threatRaw));

    // Determine if we should tighten controls
    const tighten = this._ema.threatLevel > 0.4;

    // Compute AQM multiplier
    // Normal: 1.0, under threat: up to 2.0 (more aggressive dropping)
    const aqmMultiplier = Math.max(
      0.5,
      Math.min(2.0, 1.0 + this._ema.threatLevel),
    );

    // Compute routing cost base
    // Normal: 1.0, under threat: up to 10.0
    const routingCostBase = Math.max(
      1.0,
      Math.min(10.0, 1.0 + this._ema.threatLevel * 9.0),
    );

    // Trust decay override (tighter when threat is high)
    let trustDecayOverride: number | null = null;
    if (tighten) {
      // Faster decay: multiply default by (1 + threat)
      trustDecayOverride = constants.temporal.intentDecayRate *
        (1 - this._ema.threatLevel * 0.3);
    }

    // Safety field strength adjustment
    const safetyFieldStrength = constants.policy.safetyFieldStrength *
      (1 + this._ema.threatLevel);

    // Compliance field coupling adjustment
    const complianceFieldCoupling = constants.policy.complianceFieldCoupling *
      (1 + this._ema.threatLevel * 0.5);

    const outputs: ControlOutputs = {
      aqmMultiplier,
      routingCostBase,
      trustDecayOverride,
      safetyFieldStrength,
      complianceFieldCoupling,
      threatLevel: this._ema.threatLevel,
      tighten,
      tickNumber: this._tickCount,
    };

    this._lastOutputs = outputs;
    return outputs;
  }

  /**
   * Apply control outputs to the machine constants registry.
   * This is where the twin "rewrites the physics" of the system.
   */
  applyControls(outputs: ControlOutputs): void {
    const registry = getGlobalRegistry();
    registry.tune({
      policy: {
        safetyFieldStrength: outputs.safetyFieldStrength,
        complianceFieldCoupling: outputs.complianceFieldCoupling,
      },
    });
  }

  /**
   * Run a full tick cycle: compute stats, run twin, apply controls.
   * This is the convenient "all-in-one" method.
   */
  fullCycle(
    points: Map<string, HyperspacePoint>,
    exiledCount: number,
  ): ControlOutputs {
    const stats = this.computeStats(points, exiledCount);
    const outputs = this.tick(stats);
    this.applyControls(outputs);
    return outputs;
  }

  /**
   * Get predicted threat level N ticks in the future.
   * Uses linear extrapolation from recent EMA trend.
   */
  predictThreatLevel(ticksAhead: number): number {
    if (this._history.length < 2) return this._ema.threatLevel;

    // Compute recent trend from last 10 ticks
    const recent = this._history.slice(-10);
    if (recent.length < 2) return this._ema.threatLevel;

    const firstThreat = recent[0].meanDistance * 0.5 +
      (1 - recent[0].meanTrust) * 0.5;
    const lastThreat = recent[recent.length - 1].meanDistance * 0.5 +
      (1 - recent[recent.length - 1].meanTrust) * 0.5;

    const trend = (lastThreat - firstThreat) / recent.length;
    const predicted = this._ema.threatLevel + trend * ticksAhead;

    return Math.max(0, Math.min(1, predicted));
  }

  /** Get the stat history (for auditing/visualization) */
  getHistory(): ReadonlyArray<ManifoldStats> {
    return this._history;
  }

  /** Reset the twin state */
  reset(): void {
    this._tickCount = 0;
    this._ema = {
      meanDistance: 0,
      maxDistance: 0,
      meanTrust: 1.0,
      meanIntent: 0,
      dangerFraction: 0,
      threatLevel: 0,
    };
    this._history = [];
    this._lastOutputs = null;
  }
}
