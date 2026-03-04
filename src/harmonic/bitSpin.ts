/**
 * @file bitSpin.ts
 * @module harmonic/bitSpin
 * @layer Layer 9, Layer 10, Layer 12
 * @component Probabilistic Bit Spin (P-Bit) Operators
 * @version 1.0.0
 * @since 2026-03-04
 *
 * Implements LOCAL stochastic bias operators on edges/nodes of
 * the governance graph — the "bit spin" half of the
 * BIT_SPIN / CHIRALITY_COUPLING duality.
 *
 * A p-bit (probabilistic bit) fluctuates between 0 and 1 with a
 * tunable probability bias, acting as a binary stochastic neuron
 * (Ising spin). Coupling between p-bits encodes an energy landscape
 * (Boltzmann/Ising machine) for governance sampling.
 *
 * Key distinction from chirality coupling:
 *   BIT_SPIN     = local, stochastic, no inherent handedness
 *   CHIRALITY    = global, geometric, orientation-dependent
 *
 * Energy: E({s}) = -Σ J_ij s_i s_j - Σ h_i s_i
 * Probability: P(s_i = 1) = σ(h_i + Σ_j J_ij s_j)
 *
 * Integration with Sacred Tongues:
 *   Each tongue modulates the local bias field h_i by its φ^k weight.
 *   KO (w=1.00) → baseline bias
 *   AV (w=1.618) → elevated coupling
 *   RU (w=2.618) → expanded field
 *   CA (w=4.236) → constraint amplification
 *   UM (w=6.854) → harmonic resonance
 *   DR (w=11.09) → deep governance
 *
 * References:
 *   [1] Camsari et al., "p-Bits for Probabilistic Spin Logic" (2019)
 *   [2] Borders et al., "Integer Factorization with Stochastic p-Bits" (2019)
 */

import { PHI, BRAIN_EPSILON } from '../ai_brain/types.js';

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════

/** Sacred Tongue weights: φ^k for k = 0..5 */
const TONGUE_WEIGHTS: readonly number[] = [
  1.0,                // KO
  PHI,                // AV ≈ 1.618
  PHI ** 2,           // RU ≈ 2.618
  PHI ** 3,           // CA ≈ 4.236
  PHI ** 4,           // UM ≈ 6.854
  PHI ** 5,           // DR ≈ 11.09
];

/** Tongue names for reference */
const TONGUE_NAMES = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'] as const;
export type TongueName = (typeof TONGUE_NAMES)[number];

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

/**
 * A single probabilistic bit (p-bit).
 *
 * Unlike a classical bit (deterministic 0/1) or qubit (superposition),
 * a p-bit fluctuates stochastically with a tunable bias.
 */
export interface PBit {
  /** Node identifier */
  readonly id: string;
  /** Current binary state: 0 or 1 */
  state: 0 | 1;
  /** Local bias field h_i (determines P(s_i = 1) when uncoupled) */
  bias: number;
  /** Which Sacred Tongue modulates this p-bit's bias (optional) */
  tongue?: TongueName;
  /** Fluctuation temperature (higher = more random) */
  temperature: number;
}

/**
 * Coupling between two p-bits (Ising interaction).
 * J_ij > 0: ferromagnetic (prefer same state)
 * J_ij < 0: antiferromagnetic (prefer opposite state)
 */
export interface SpinCoupling {
  /** Source p-bit id */
  from: string;
  /** Target p-bit id */
  to: string;
  /** Coupling strength J_ij */
  strength: number;
}

/**
 * Configuration for the spin field.
 */
export interface SpinFieldConfig {
  /** Global temperature (Boltzmann kT, default 1.0) */
  temperature: number;
  /** Number of Gibbs sampling sweeps per step (default 1) */
  samplingSweeeps: number;
  /** Enable tongue-modulated bias (default true) */
  tongueModulation: boolean;
  /** Damping factor for energy computation (default 1.0) */
  damping: number;
}

/**
 * Snapshot of the spin field state for analysis.
 */
export interface SpinFieldSnapshot {
  /** Current states of all p-bits */
  states: ReadonlyMap<string, 0 | 1>;
  /** Total Ising energy */
  energy: number;
  /** Magnetization (mean spin) [0, 1] */
  magnetization: number;
  /** Spin-spin correlation function C(i,j) = <s_i s_j> - <s_i><s_j> */
  correlations: Map<string, number>;
  /** Anomaly score based on correlation structure [0, 1] */
  anomalyScore: number;
  /** Step counter */
  step: number;
}

// ═══════════════════════════════════════════════════════════════
// Core Functions
// ═══════════════════════════════════════════════════════════════

/**
 * Sigmoid activation: σ(x) = 1 / (1 + exp(-x))
 */
export function sigmoid(x: number): number {
  if (x > 500) return 1.0;
  if (x < -500) return 0.0;
  return 1 / (1 + Math.exp(-x));
}

/**
 * Compute the effective field at p-bit i.
 *
 * h_eff(i) = h_i * w_tongue + Σ_j J_ij * s_j
 *
 * The tongue weight modulates the local bias, creating
 * a landscape where higher-order tongues have stronger
 * influence on governance decisions.
 */
export function effectiveField(
  pbit: PBit,
  couplings: SpinCoupling[],
  allStates: ReadonlyMap<string, 0 | 1>,
  tongueModulation: boolean = true
): number {
  // Local bias, optionally modulated by tongue weight
  let h = pbit.bias;
  if (tongueModulation && pbit.tongue) {
    const tongueIdx = TONGUE_NAMES.indexOf(pbit.tongue);
    if (tongueIdx >= 0) {
      h *= TONGUE_WEIGHTS[tongueIdx];
    }
  }

  // Sum coupling contributions from neighbors
  for (const coupling of couplings) {
    let neighborId: string | null = null;
    if (coupling.from === pbit.id) {
      neighborId = coupling.to;
    } else if (coupling.to === pbit.id) {
      neighborId = coupling.from;
    }
    if (neighborId !== null) {
      const neighborState = allStates.get(neighborId) ?? 0;
      // Convert {0,1} to Ising {-1,+1} for coupling: σ = 2s - 1
      const isingNeighbor = 2 * neighborState - 1;
      h += coupling.strength * isingNeighbor;
    }
  }

  return h;
}

/**
 * Compute the Ising energy of the entire spin field.
 *
 * E({s}) = -Σ_{<i,j>} J_ij σ_i σ_j - Σ_i h_i σ_i
 *
 * where σ_i = 2 * s_i - 1 maps {0,1} → {-1,+1}
 */
export function computeIsingEnergy(
  pbits: PBit[],
  couplings: SpinCoupling[],
  tongueModulation: boolean = true
): number {
  let energy = 0;

  // Coupling energy: -Σ J_ij σ_i σ_j
  for (const c of couplings) {
    const si = pbits.find((p) => p.id === c.from);
    const sj = pbits.find((p) => p.id === c.to);
    if (si && sj) {
      const isingI = 2 * si.state - 1;
      const isingJ = 2 * sj.state - 1;
      energy -= c.strength * isingI * isingJ;
    }
  }

  // Field energy: -Σ h_i σ_i
  for (const pbit of pbits) {
    let h = pbit.bias;
    if (tongueModulation && pbit.tongue) {
      const idx = TONGUE_NAMES.indexOf(pbit.tongue);
      if (idx >= 0) h *= TONGUE_WEIGHTS[idx];
    }
    const isingI = 2 * pbit.state - 1;
    energy -= h * isingI;
  }

  return energy;
}

/**
 * Compute the magnetization of the spin field.
 * M = (1/N) Σ s_i ∈ [0, 1]
 */
export function computeMagnetization(pbits: PBit[]): number {
  if (pbits.length === 0) return 0;
  const sum = pbits.reduce((acc, p) => acc + p.state, 0);
  return sum / pbits.length;
}

// ═══════════════════════════════════════════════════════════════
// Spin Field Class
// ═══════════════════════════════════════════════════════════════

/**
 * Spin Field — a graph of coupled p-bits implementing
 * Boltzmann sampling over governance states.
 *
 * This is the "local stochastic" half of the governance duality.
 * Each node is a p-bit with tunable bias; edges are Ising couplings.
 * The system relaxes toward low-energy configurations via Gibbs sampling.
 *
 * Security application: Normal governance traffic produces characteristic
 * spin correlation patterns. Adversarial manipulation shows up as
 * anomalous magnetization or broken correlation symmetries.
 */
export class SpinField {
  private pbits: Map<string, PBit> = new Map();
  private couplings: SpinCoupling[] = [];
  private readonly config: SpinFieldConfig;
  private stepCounter: number = 0;

  /** Running averages for correlation computation */
  private spinHistory: Map<string, number[]> = new Map();
  private readonly historyWindow = 64;

  constructor(config: Partial<SpinFieldConfig> = {}) {
    this.config = {
      temperature: 1.0,
      samplingSweeeps: 1,
      tongueModulation: true,
      damping: 1.0,
      ...config,
    };
  }

  /**
   * Add a p-bit node to the field.
   */
  addPBit(id: string, bias: number = 0, tongue?: TongueName): PBit {
    const pbit: PBit = {
      id,
      state: Math.random() < sigmoid(bias) ? 1 : 0,
      bias,
      tongue,
      temperature: this.config.temperature,
    };
    this.pbits.set(id, pbit);
    this.spinHistory.set(id, []);
    return pbit;
  }

  /**
   * Add a coupling (edge) between two p-bits.
   */
  addCoupling(from: string, to: string, strength: number): SpinCoupling {
    const coupling: SpinCoupling = { from, to, strength };
    this.couplings.push(coupling);
    return coupling;
  }

  /**
   * Build a hexagonal tongue field — 6 p-bits arranged
   * in the Sacred Tongue hexagon with nearest-neighbor couplings.
   *
   * KO → AV → RU → CA → UM → DR → (back to KO)
   *
   * Ferromagnetic coupling (J > 0) between neighbors means
   * adjacent tongues prefer to align.
   * Cross-diagonal dashed lines (implicit couplings) are weaker.
   */
  buildTongueHexagon(couplingStrength: number = 1.0): void {
    // Create one p-bit per tongue
    for (let i = 0; i < 6; i++) {
      this.addPBit(TONGUE_NAMES[i], 0, TONGUE_NAMES[i]);
    }

    // Nearest-neighbor couplings (hexagonal ring)
    for (let i = 0; i < 6; i++) {
      const next = (i + 1) % 6;
      this.addCoupling(TONGUE_NAMES[i], TONGUE_NAMES[next], couplingStrength);
    }

    // Cross-diagonal implicit couplings (weaker, φ-attenuated)
    // KO↔CA, AV↔UM, RU↔DR (opposite vertices)
    this.addCoupling('KO', 'CA', couplingStrength / PHI);
    this.addCoupling('AV', 'UM', couplingStrength / PHI);
    this.addCoupling('RU', 'DR', couplingStrength / PHI);
  }

  /**
   * Perform one Gibbs sampling sweep over all p-bits.
   *
   * For each p-bit, compute P(s_i = 1 | neighbors) using
   * the Boltzmann distribution, then sample stochastically.
   *
   * Uses a deterministic seed-based PRNG for reproducibility
   * when testing, but defaults to Math.random for production.
   */
  step(rng: () => number = Math.random): void {
    const stateMap = this.getStateMap();
    const pbitList = Array.from(this.pbits.values());

    for (let sweep = 0; sweep < this.config.samplingSweeeps; sweep++) {
      // Shuffle order for ergodicity (Fisher-Yates)
      const order = pbitList.map((_, i) => i);
      for (let i = order.length - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [order[i], order[j]] = [order[j], order[i]];
      }

      for (const idx of order) {
        const pbit = pbitList[idx];
        const hEff = effectiveField(
          pbit,
          this.couplings,
          stateMap,
          this.config.tongueModulation
        );

        // Boltzmann probability: P(s=1) = σ(h_eff / T)
        const T = Math.max(BRAIN_EPSILON, pbit.temperature * this.config.damping);
        const prob = sigmoid(hEff / T);

        // Sample
        pbit.state = rng() < prob ? 1 : 0;
        stateMap.set(pbit.id, pbit.state);
      }
    }

    // Update history
    for (const pbit of pbitList) {
      const hist = this.spinHistory.get(pbit.id) ?? [];
      hist.push(pbit.state);
      if (hist.length > this.historyWindow) hist.shift();
      this.spinHistory.set(pbit.id, hist);
    }

    this.stepCounter++;
  }

  /**
   * Take a snapshot of the current field state.
   */
  snapshot(): SpinFieldSnapshot {
    const pbitList = Array.from(this.pbits.values());
    const stateMap = this.getStateMap();
    const energy = computeIsingEnergy(pbitList, this.couplings, this.config.tongueModulation);
    const magnetization = computeMagnetization(pbitList);

    // Compute spin-spin correlations from history
    const correlations = this.computeCorrelations();

    // Anomaly detection: compare actual correlations to expected
    const anomalyScore = this.computeAnomalyScore(correlations, magnetization);

    return {
      states: stateMap,
      energy,
      magnetization,
      correlations,
      anomalyScore,
      step: this.stepCounter,
    };
  }

  /**
   * Get a specific p-bit.
   */
  getPBit(id: string): PBit | undefined {
    return this.pbits.get(id);
  }

  /**
   * Get all p-bits.
   */
  getAllPBits(): PBit[] {
    return Array.from(this.pbits.values());
  }

  /**
   * Get current state map {id → 0|1}.
   */
  getStateMap(): Map<string, 0 | 1> {
    const map = new Map<string, 0 | 1>();
    for (const [id, pbit] of this.pbits) {
      map.set(id, pbit.state);
    }
    return map;
  }

  /**
   * Get all couplings.
   */
  getCouplings(): readonly SpinCoupling[] {
    return this.couplings;
  }

  /**
   * Get step counter.
   */
  getStep(): number {
    return this.stepCounter;
  }

  /**
   * Reset all states and history.
   */
  reset(): void {
    for (const pbit of this.pbits.values()) {
      pbit.state = 0;
    }
    this.spinHistory.clear();
    for (const id of this.pbits.keys()) {
      this.spinHistory.set(id, []);
    }
    this.stepCounter = 0;
  }

  // ═══════════════════════════════════════════════════════════════
  // Private: Correlation & Anomaly Detection
  // ═══════════════════════════════════════════════════════════════

  /**
   * Compute spin-spin correlations from history.
   * C(i,j) = <s_i * s_j> - <s_i> * <s_j>
   */
  private computeCorrelations(): Map<string, number> {
    const correlations = new Map<string, number>();

    for (const coupling of this.couplings) {
      const histI = this.spinHistory.get(coupling.from);
      const histJ = this.spinHistory.get(coupling.to);
      if (!histI || !histJ || histI.length < 2 || histJ.length < 2) {
        correlations.set(`${coupling.from}-${coupling.to}`, 0);
        continue;
      }

      const n = Math.min(histI.length, histJ.length);
      let sumIJ = 0;
      let sumI = 0;
      let sumJ = 0;
      for (let k = 0; k < n; k++) {
        sumIJ += histI[k] * histJ[k];
        sumI += histI[k];
        sumJ += histJ[k];
      }
      const meanIJ = sumIJ / n;
      const meanI = sumI / n;
      const meanJ = sumJ / n;
      correlations.set(`${coupling.from}-${coupling.to}`, meanIJ - meanI * meanJ);
    }

    return correlations;
  }

  /**
   * Anomaly score based on spin statistics.
   *
   * Normal governance: balanced magnetization, consistent correlations.
   * Adversarial: biased magnetization or anomalous correlations.
   */
  private computeAnomalyScore(
    correlations: Map<string, number>,
    magnetization: number
  ): number {
    // Magnetization anomaly: extreme bias suggests manipulation
    const magAnomaly = Math.abs(2 * magnetization - 1); // 0 at M=0.5, 1 at M=0 or M=1

    // Correlation anomaly: variance of correlations
    const corrValues = Array.from(correlations.values());
    if (corrValues.length === 0) return magAnomaly;

    const meanCorr = corrValues.reduce((a, b) => a + b, 0) / corrValues.length;
    const corrVariance =
      corrValues.reduce((a, b) => a + (b - meanCorr) ** 2, 0) / corrValues.length;

    // High variance in correlations = inconsistent coupling = anomalous
    const corrAnomaly = Math.min(1, corrVariance * 4);

    // Weighted combination
    return Math.min(1, magAnomaly * 0.6 + corrAnomaly * 0.4);
  }
}
