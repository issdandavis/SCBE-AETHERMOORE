/**
 * @file governanceGaugeField.ts
 * @module harmonic/governanceGaugeField
 * @layer Layer 5, Layer 6, Layer 7, Layer 9, Layer 10, Layer 12, Layer 13
 * @component Governance Gauge Field — Unified Spin × Chirality × Phase Locking
 * @version 1.0.0
 * @since 2026-03-04
 *
 * Unifies BitSpin (local stochastic operators) and ChiralityCoupling
 * (global handedness constraints) into a single Governance Gauge Field.
 *
 * The gauge field is a physical analogy: the Six Sacred Tongues create
 * an internal "charge" (like color charge in QCD) that propagates through
 * the governance mesh. Each drone/agent operates at a different harmonic
 * based on which tongue dominates its governance.
 *
 * Key concepts:
 *
 *   HEXAGONAL ARRAY: 6 tongue-nodes with explicit nearest-neighbor
 *   policy enforcement (solid lines) and implicit φ-weighted modifier
 *   web (dashed lines). Adjusting KO ripples through the entire field
 *   via φ-scaling.
 *
 *   CONSENSUS FIELD: When two agents get close, they create beat
 *   frequencies — constructive interference (agreement) or destructive
 *   interference (conflict detection).
 *
 *   BREATHING SYNCHRONIZATION: Arrays "breathe" at frequencies φ, φ²,
 *   φ³, etc. Phase locking occurs when they need to form super-array
 *   consensus — this is "hyperbolic blockchain": blocks of governance
 *   chained through harmonic phase locking (not crypto, literal blocks).
 *
 *   LAGRANGIAN: The "profit matrix" is the system's Lagrangian —
 *   the action principle that minimizes energy across the entire mesh.
 *   L = T - V where T = kinetic (spin fluctuation energy) and
 *   V = potential (chirality + coupling energy).
 *
 * @axiom A4: Symmetry — gauge invariance under tongue permutations
 * @axiom A2: Unitarity — total charge conservation
 */

import { PHI, BRAIN_EPSILON } from '../ai_brain/types.js';
import { SpinField } from './bitSpin.js';
import type { SpinFieldSnapshot } from './bitSpin.js';
import { ChiralGraph, computeCompatibility } from './chiralityCoupling.js';
import type { ChiralCompatibility, ChiralNode } from './chiralityCoupling.js';

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════

/** Sacred Tongue names */
const TONGUE_NAMES = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'] as const;
type TongueName = (typeof TONGUE_NAMES)[number];

/** Tongue harmonic frequencies (sacred harmonic ratios) */
const TONGUE_FREQUENCIES = [
  1.0,    // KO: unison
  9 / 8,  // AV: major 2nd
  5 / 4,  // RU: major 3rd
  4 / 3,  // CA: perfect 4th
  3 / 2,  // UM: perfect 5th
  5 / 3,  // DR: major 6th
];

/** Golden ratio breathing frequencies for arrays */
const ARRAY_BREATH_FREQUENCIES = [
  1.0,          // Array 0: φ^0
  PHI,          // Array 1: φ^1
  PHI ** 2,     // Array 2: φ^2
  PHI ** 3,     // Array 3: φ^3
];

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

/**
 * A governance array — a complete hexagonal tongue arrangement
 * with both spin field and chirality graph.
 */
export interface GovernanceArray {
  /** Array identifier */
  readonly id: string;
  /** Spin field (local stochastic operators) */
  spinField: SpinField;
  /** Chiral graph (global handedness constraints) */
  chiralGraph: ChiralGraph;
  /** Breathing frequency (φ^k for array k) */
  breathFrequency: number;
  /** Current breathing phase */
  breathPhase: number;
  /** Breathing amplitude */
  breathAmplitude: number;
}

/**
 * Phase lock state between two arrays.
 */
export interface PhaseLock {
  /** First array id */
  arrayA: string;
  /** Second array id */
  arrayB: string;
  /** Phase difference between arrays */
  phaseDifference: number;
  /** Lock quality [0, 1] — 1 = perfectly locked */
  lockQuality: number;
  /** Beat frequency (|f_A - f_B|) */
  beatFrequency: number;
  /** Whether arrays are phase-locked (quality > threshold) */
  locked: boolean;
}

/**
 * Governance block — a snapshot of consensus state
 * at a point in time, "chained" to the previous block
 * through harmonic phase continuity.
 */
export interface GovernanceBlock {
  /** Block index */
  index: number;
  /** Timestamp */
  timestamp: number;
  /** Hash of the consensus state (simple checksum) */
  stateHash: number;
  /** Previous block's state hash */
  previousHash: number;
  /** Spin field snapshot at consensus */
  spinSnapshot: SpinFieldSnapshot;
  /** Total Lagrangian at consensus */
  lagrangian: number;
  /** Phase lock states between all arrays */
  phaseLocks: PhaseLock[];
  /** Consensus decision */
  decision: 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY';
}

/**
 * Configuration for the governance gauge field.
 */
export interface GaugeFieldConfig {
  /** Number of spin sampling sweeps per tick */
  samplesPerTick: number;
  /** Breathing amplitude for all arrays */
  breathAmplitude: number;
  /** Phase lock threshold (quality above this = locked) */
  phaseLockThreshold: number;
  /** Lagrangian thresholds for risk decisions */
  lagrangianThresholds: {
    allow: number;
    quarantine: number;
    escalate: number;
  };
  /** Spin-chirality coupling constant */
  couplingConstant: number;
}

export const DEFAULT_GAUGE_CONFIG: GaugeFieldConfig = {
  samplesPerTick: 3,
  breathAmplitude: 0.05,
  phaseLockThreshold: 0.7,
  lagrangianThresholds: {
    allow: 5.0,
    quarantine: 15.0,
    escalate: 30.0,
  },
  couplingConstant: 1.0,
};

// ═══════════════════════════════════════════════════════════════
// Governance Gauge Field
// ═══════════════════════════════════════════════════════════════

/**
 * The Governance Gauge Field unifies local spin dynamics with
 * global chirality constraints and phase-locked breathing.
 *
 * Think of it as "hyperbolic blockchain" — not crypto blockchain,
 * but literal blocks of governance state chained through harmonic
 * phase locking across arrays.
 *
 * Each array is a hexagonal tongue arrangement. When arrays need
 * to form super-array consensus, they phase-lock their breathing
 * transforms at specific φ-ratio frequencies.
 *
 * The Lagrangian L = T - V serves as the system's "profit matrix":
 *   T (kinetic) = spin fluctuation energy (how actively the field samples)
 *   V (potential) = chirality + coupling energy (how constrained the field is)
 *
 * Low Lagrangian → stable governance → ALLOW
 * High Lagrangian → unstable governance → ESCALATE/DENY
 */
export class GovernanceGaugeField {
  private arrays: Map<string, GovernanceArray> = new Map();
  private chain: GovernanceBlock[] = [];
  private readonly config: GaugeFieldConfig;
  private tickCounter: number = 0;

  constructor(config: Partial<GaugeFieldConfig> = {}) {
    this.config = { ...DEFAULT_GAUGE_CONFIG, ...config };
  }

  /**
   * Create a new governance array with full hexagonal tongue layout.
   */
  createArray(id: string, breathFrequencyIndex: number = 0): GovernanceArray {
    const spinField = new SpinField({
      temperature: 1.0,
      samplingSweeeps: this.config.samplesPerTick,
      tongueModulation: true,
    });
    spinField.buildTongueHexagon(this.config.couplingConstant);

    const chiralGraph = new ChiralGraph({
      spinChiralLambda: this.config.couplingConstant,
    });
    chiralGraph.buildTongueHexagon(this.config.couplingConstant);

    const freqIdx = Math.min(breathFrequencyIndex, ARRAY_BREATH_FREQUENCIES.length - 1);

    const array: GovernanceArray = {
      id,
      spinField,
      chiralGraph,
      breathFrequency: ARRAY_BREATH_FREQUENCIES[Math.max(0, freqIdx)],
      breathPhase: 0,
      breathAmplitude: this.config.breathAmplitude,
    };

    this.arrays.set(id, array);
    return array;
  }

  /**
   * Advance the field by one tick.
   *
   * 1. Evolve spin fields (Gibbs sampling)
   * 2. Propagate spin states to chiral graphs
   * 3. Advance breathing phases
   * 4. Check phase locks between arrays
   */
  tick(rng: () => number = Math.random): void {
    this.tickCounter++;

    for (const array of this.arrays.values()) {
      // 1. Spin field Gibbs sampling
      array.spinField.step(rng);

      // 2. Propagate spin → chirality
      const spinStates = array.spinField.getStateMap();
      array.chiralGraph.updateSpins(spinStates);

      // 3. Advance breathing phase
      array.breathPhase += array.breathFrequency * (2 * Math.PI / 100);
      // Normalize to [0, 2π)
      array.breathPhase = array.breathPhase % (2 * Math.PI);
    }
  }

  /**
   * Compute phase lock state between two arrays.
   *
   * Phase locking occurs when the breathing transforms synchronize.
   * Lock quality is determined by how close their phase difference
   * is to a rational multiple of π (harmonic resonance).
   */
  computePhaseLock(arrayIdA: string, arrayIdB: string): PhaseLock | null {
    const a = this.arrays.get(arrayIdA);
    const b = this.arrays.get(arrayIdB);
    if (!a || !b) return null;

    const rawDiff = Math.abs(a.breathPhase - b.breathPhase);
    const phaseDifference = Math.min(rawDiff, 2 * Math.PI - rawDiff);

    // Beat frequency
    const beatFrequency = Math.abs(a.breathFrequency - b.breathFrequency);

    // Lock quality: proximity to harmonic resonance
    // Check proximity to 0, π/3, 2π/3, π, 4π/3, 5π/3 (hexagonal symmetry)
    let minDeviation = phaseDifference;
    for (let k = 1; k <= 5; k++) {
      const harmonic = (k * Math.PI) / 3;
      const dev = Math.abs(phaseDifference - harmonic);
      minDeviation = Math.min(minDeviation, dev);
    }

    // Lock quality: 1 when perfectly at a harmonic, decays with deviation
    const lockQuality = Math.exp(-minDeviation * 3);

    return {
      arrayA: arrayIdA,
      arrayB: arrayIdB,
      phaseDifference,
      lockQuality,
      beatFrequency,
      locked: lockQuality >= this.config.phaseLockThreshold,
    };
  }

  /**
   * Compute the Lagrangian of the entire field.
   *
   * L = T - V
   *
   * T (kinetic) = total spin fluctuation energy
   *   = Σ_arrays Σ_pbits |velocity_i|²
   *   Approximated by the spin field energy variance.
   *
   * V (potential) = chirality coupling + constraint energy
   *   = Σ_arrays (|Ising energy| + transport asymmetry × coupling)
   */
  computeLagrangian(): number {
    let T = 0; // Kinetic
    let V = 0; // Potential

    for (const array of this.arrays.values()) {
      const snapshot = array.spinField.snapshot();

      // Kinetic: spin fluctuation energy ∝ |magnetization - 0.5|
      // Maximum kinetic when M is changing rapidly (near 0.5)
      // Minimum when stuck at extremes (0 or 1)
      const spinKinetic = 4 * snapshot.magnetization * (1 - snapshot.magnetization);
      T += spinKinetic;

      // Potential: Ising energy magnitude + chiral asymmetry
      const isingEnergy = Math.abs(snapshot.energy);
      const chiralAsymmetry = array.chiralGraph.transportAsymmetry();
      V += isingEnergy + chiralAsymmetry * this.config.couplingConstant;
    }

    return T - V;
  }

  /**
   * Forge a governance block — snapshot consensus state and
   * chain it to the previous block through phase continuity.
   *
   * This is the "hyperbolic blockchain" mechanism: blocks are
   * not linked by cryptographic hashes (though we compute one)
   * but by the requirement that phase-lock states must be
   * continuous across blocks.
   */
  forgeBlock(): GovernanceBlock {
    const arrayIds = Array.from(this.arrays.keys());

    // Get representative spin snapshot (first array or combined)
    const firstArray = this.arrays.values().next().value;
    const spinSnapshot = firstArray
      ? firstArray.spinField.snapshot()
      : {
          states: new Map(),
          energy: 0,
          magnetization: 0,
          correlations: new Map(),
          anomalyScore: 0,
          step: 0,
        };

    // Compute all phase locks
    const phaseLocks: PhaseLock[] = [];
    for (let i = 0; i < arrayIds.length; i++) {
      for (let j = i + 1; j < arrayIds.length; j++) {
        const lock = this.computePhaseLock(arrayIds[i], arrayIds[j]);
        if (lock) phaseLocks.push(lock);
      }
    }

    const lagrangian = this.computeLagrangian();

    // Risk decision based on Lagrangian
    let decision: GovernanceBlock['decision'];
    const absL = Math.abs(lagrangian);
    if (absL < this.config.lagrangianThresholds.allow) {
      decision = 'ALLOW';
    } else if (absL < this.config.lagrangianThresholds.quarantine) {
      decision = 'QUARANTINE';
    } else if (absL < this.config.lagrangianThresholds.escalate) {
      decision = 'ESCALATE';
    } else {
      decision = 'DENY';
    }

    // State hash (simple numeric checksum)
    const stateHash = this.computeStateHash();
    const previousHash = this.chain.length > 0
      ? this.chain[this.chain.length - 1].stateHash
      : 0;

    const block: GovernanceBlock = {
      index: this.chain.length,
      timestamp: this.tickCounter,
      stateHash,
      previousHash,
      spinSnapshot,
      lagrangian,
      phaseLocks,
      decision,
    };

    this.chain.push(block);
    return block;
  }

  /**
   * Get the governance chain (all forged blocks).
   */
  getChain(): readonly GovernanceBlock[] {
    return this.chain;
  }

  /**
   * Get a specific array.
   */
  getArray(id: string): GovernanceArray | undefined {
    return this.arrays.get(id);
  }

  /**
   * Get all array ids.
   */
  getArrayIds(): string[] {
    return Array.from(this.arrays.keys());
  }

  /**
   * Get the current tick count.
   */
  getTick(): number {
    return this.tickCounter;
  }

  /**
   * Compute consensus across all arrays.
   *
   * Returns the fraction of arrays that are phase-locked
   * with at least one other array. Higher consensus = more
   * stable governance field.
   */
  consensusStrength(): number {
    const arrayIds = Array.from(this.arrays.keys());
    if (arrayIds.length < 2) return 1.0;

    const lockedWith = new Set<string>();
    for (let i = 0; i < arrayIds.length; i++) {
      for (let j = i + 1; j < arrayIds.length; j++) {
        const lock = this.computePhaseLock(arrayIds[i], arrayIds[j]);
        if (lock?.locked) {
          lockedWith.add(arrayIds[i]);
          lockedWith.add(arrayIds[j]);
        }
      }
    }

    return lockedWith.size / arrayIds.length;
  }

  // ═══════════════════════════════════════════════════════════════
  // Private
  // ═══════════════════════════════════════════════════════════════

  /**
   * Compute a numeric hash of the current field state.
   * Simple checksum for chain continuity verification.
   */
  private computeStateHash(): number {
    let hash = 0;
    for (const array of this.arrays.values()) {
      const states = array.spinField.getStateMap();
      for (const [id, state] of states) {
        // Simple hash: accumulate (id char sum * state weight + phase)
        let idSum = 0;
        for (let i = 0; i < id.length; i++) {
          idSum += id.charCodeAt(i);
        }
        hash = (hash * 31 + idSum * (state + 1) + Math.floor(array.breathPhase * 1000)) | 0;
      }
    }
    return hash;
  }
}
