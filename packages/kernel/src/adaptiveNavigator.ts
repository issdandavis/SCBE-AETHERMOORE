/**
 * @file adaptiveNavigator.ts
 * @module harmonic/adaptiveNavigator
 * @layer Layer 5, Layer 6, Layer 7, Layer 9, Layer 13
 * @component Adaptive Hyperbolic Navigator
 * @version 1.0.0
 * @since 2026-02-06
 *
 * SCBE Adaptive Hyperbolic Navigator - Dynamic geometry that evolves with intent validation.
 *
 * Key Innovation: The Poincaré ball becomes a "living manifold" where:
 * - Harmonic scaling R(t) varies with coherence: R(t) = R_base + λ(1 - C)
 * - Curvature κ(t) can adapt: κ(t) = -1 * exp(γ(1 - C))
 * - ODE-based drift with attraction/repulsion modulated by trust
 *
 * Mathematical Foundation:
 * - Generalized Poincaré metric with variable curvature
 * - Distance formula: d_κ(u,v) = (1/√|κ|) arccosh(1 + (2|κ|‖u-v‖²)/((1-|κ|‖u‖²)(1-|κ|‖v‖²)))
 * - Harmonic wall: H(d,R) = R^(d²) where R adapts to coherence
 *
 * Integration:
 * - Layer 9/10: Spectral coherence feeds into C ∈ [0,1]
 * - Layer 13: Intent validation modulates drift velocity
 * - HYDRA: Swarm consensus can trigger geometry evolution
 */

const EPSILON = 1e-10;
const PHI = (1 + Math.sqrt(5)) / 2; // Golden ratio

// ═══════════════════════════════════════════════════════════════
// Sacred Tongue Realm Centers (6D)
// ═══════════════════════════════════════════════════════════════

/** Sacred Tongue realm centers in 6D Poincaré ball */
export const REALM_CENTERS: Record<string, number[]> = {
  KO: [0.3, 0.0, 0.0, 0.0, 0.0, 0.0],   // Knowledge - axis 0
  AV: [0.0, 0.3, 0.0, 0.0, 0.0, 0.0],   // Avatara - axis 1
  RU: [0.0, 0.0, 0.3, 0.0, 0.0, 0.0],   // Runes - axis 2
  CA: [0.0, 0.0, 0.0, 0.3, 0.0, 0.0],   // Cascade - axis 3
  UM: [0.0, 0.0, 0.0, 0.0, 0.3, 0.0],   // Umbra - axis 4
  DR: [0.0, 0.0, 0.0, 0.0, 0.0, 0.3],   // Draconic - axis 5
};

/** Tongue weights (golden ratio based) */
export const TONGUE_WEIGHTS: Record<string, number> = {
  KO: 1.0,
  AV: 1 / PHI,
  RU: 1 / (PHI * PHI),
  CA: 1 / (PHI * PHI * PHI),
  UM: 1 / (PHI * PHI * PHI * PHI),
  DR: 1 / (PHI * PHI * PHI * PHI * PHI),
};

// ═══════════════════════════════════════════════════════════════
// Vector Operations
// ═══════════════════════════════════════════════════════════════

function norm(v: number[]): number {
  let sum = 0;
  for (const x of v) sum += x * x;
  return Math.sqrt(sum);
}

function normSq(v: number[]): number {
  let sum = 0;
  for (const x of v) sum += x * x;
  return sum;
}

function dot(u: number[], v: number[]): number {
  let sum = 0;
  for (let i = 0; i < u.length; i++) sum += u[i] * v[i];
  return sum;
}

function scale(v: number[], s: number): number[] {
  return v.map((x) => x * s);
}

function add(u: number[], v: number[]): number[] {
  return u.map((x, i) => x + v[i]);
}

function sub(u: number[], v: number[]): number[] {
  return u.map((x, i) => x - v[i]);
}

function zeros(n: number): number[] {
  return new Array(n).fill(0);
}

// ═══════════════════════════════════════════════════════════════
// Configuration Interface
// ═══════════════════════════════════════════════════════════════

export interface AdaptiveNavigatorConfig {
  /** Base harmonic scaling factor (default 1.5) */
  baseR: number;
  /** Penalty multiplier for low coherence (default 1.0) */
  lambdaPenalty: number;
  /** Chaos amplitude for Lorenz-like perturbations (default 0.1) */
  chaos: number;
  /** Curvature adaptation rate (default 0.5) */
  gamma: number;
  /** Dimension of the Poincaré ball (default 6 for Sacred Tongues) */
  dimension: number;
  /** Maximum trajectory history length (default 1000) */
  maxHistory: number;
  /** Ball boundary threshold (default 0.98) */
  boundaryThreshold: number;
}

export const DEFAULT_CONFIG: AdaptiveNavigatorConfig = {
  baseR: 1.5,
  lambdaPenalty: 1.0,
  chaos: 0.1,
  gamma: 0.5,
  dimension: 6,
  maxHistory: 1000,
  boundaryThreshold: 0.98,
};

// ═══════════════════════════════════════════════════════════════
// Navigator State
// ═══════════════════════════════════════════════════════════════

export interface NavigatorState {
  position: number[];
  velocity: number[];
  coherence: number;
  currentR: number;
  currentKappa: number;
  penalty: number;
  timestamp: number;
}

// ═══════════════════════════════════════════════════════════════
// Adaptive Hyperbolic Navigator Class
// ═══════════════════════════════════════════════════════════════

/**
 * Adaptive Hyperbolic Navigator
 *
 * A "living manifold" navigator where the Poincaré ball geometry
 * evolves based on intent validation coherence.
 *
 * @example
 * ```typescript
 * const nav = new AdaptiveHyperbolicNavigator();
 *
 * // Update with intent and coherence from Layer 9/13
 * const result = nav.update(['KO', 'AV'], 0.85);
 *
 * // Check adaptive penalty
 * if (result.penalty > 10) {
 *   console.log('High deviation detected');
 * }
 * ```
 */
export class AdaptiveHyperbolicNavigator {
  private config: AdaptiveNavigatorConfig;
  private position: number[];
  private velocity: number[];
  private history: number[][];
  private coherenceHistory: number[];

  constructor(config: Partial<AdaptiveNavigatorConfig> = {}, initialPosition?: number[]) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.position = initialPosition
      ? [...initialPosition]
      : zeros(this.config.dimension);
    this.velocity = zeros(this.config.dimension);
    this.history = [this.position.slice()];
    this.coherenceHistory = [1.0];
  }

  // ═══════════════════════════════════════════════════════════════
  // Adaptive Geometry Parameters
  // ═══════════════════════════════════════════════════════════════

  /**
   * Compute adaptive harmonic scaling R(t) based on coherence
   *
   * R(t) = R_base + λ(1 - C)
   *
   * Low coherence → higher R → harsher exponential penalties
   *
   * @param coherence - Intent validation coherence [0, 1]
   */
  getCurrentR(coherence: number): number {
    const c = Math.max(0, Math.min(1, coherence));
    return this.config.baseR + this.config.lambdaPenalty * (1 - c);
  }

  /**
   * Compute adaptive curvature κ(t) based on coherence
   *
   * κ(t) = -1 * exp(γ(1 - C))
   *
   * Low coherence → more negative curvature → distances explode faster
   *
   * @param coherence - Intent validation coherence [0, 1]
   */
  getCurrentKappa(coherence: number): number {
    const c = Math.max(0, Math.min(1, coherence));
    return -1 * Math.exp(this.config.gamma * (1 - c));
  }

  // ═══════════════════════════════════════════════════════════════
  // Hyperbolic Distance with Variable Curvature
  // ═══════════════════════════════════════════════════════════════

  /**
   * Hyperbolic distance with variable curvature
   *
   * d_κ(u,v) = (1/√|κ|) arccosh(1 + (2|κ|‖u-v‖²)/((1-|κ|‖u‖²)(1-|κ|‖v‖²)))
   *
   * @param u - First point
   * @param v - Second point
   * @param kappa - Curvature (negative for hyperbolic)
   */
  hyperbolicDistanceKappa(u: number[], v: number[], kappa: number): number {
    const absKappa = Math.abs(kappa);
    const sqrtKappa = Math.sqrt(absKappa);

    const diff = sub(u, v);
    const diffNormSq = normSq(diff);
    const uNormSq = normSq(u);
    const vNormSq = normSq(v);

    const uFactor = Math.max(EPSILON, 1 - absKappa * uNormSq);
    const vFactor = Math.max(EPSILON, 1 - absKappa * vNormSq);

    const arg = 1 + (2 * absKappa * diffNormSq) / (uFactor * vFactor);

    return Math.acosh(Math.max(1, arg)) / sqrtKappa;
  }

  /**
   * Standard hyperbolic distance (κ = -1)
   */
  hyperbolicDistance(u: number[], v: number[]): number {
    return this.hyperbolicDistanceKappa(u, v, -1);
  }

  // ═══════════════════════════════════════════════════════════════
  // ODE Drift Dynamics
  // ═══════════════════════════════════════════════════════════════

  /**
   * Compute drift vector for ODE integration
   *
   * Combines:
   * - Attraction to target realm centers (scaled by coherence and R)
   * - Repulsion/mutations (amplified by low coherence)
   * - Chaos term (Lorenz-like, modulated by coherence)
   *
   * @param pos - Current position
   * @param targets - Target tongue realms
   * @param coherence - Intent validation coherence
   * @param mutations - Mutation rate for lexicon evolution
   */
  private computeDrift(
    pos: number[],
    targets: string[],
    coherence: number,
    mutations: number
  ): number[] {
    const R = this.getCurrentR(coherence);
    const dim = this.config.dimension;

    // Attraction to target realms
    const attraction = zeros(dim);
    for (const tongue of targets) {
      const center = REALM_CENTERS[tongue];
      if (center) {
        const weight = TONGUE_WEIGHTS[tongue] || 1.0;
        const delta = sub(center, pos);
        for (let i = 0; i < dim; i++) {
          // Stronger pull when trusted (high coherence)
          attraction[i] += delta[i] * coherence * weight * R;
        }
      }
    }

    // Repulsion/mutations (amplified by low coherence)
    const repulsion = zeros(dim);
    if (mutations > 0) {
      for (let i = 0; i < dim; i++) {
        // Gaussian-like mutation with coherence modulation
        repulsion[i] = (Math.random() - 0.5) * 2 * mutations * (1 - coherence);
      }
    }

    // Chaos term (Lorenz-like attractor simplified to 6D)
    const chaos = zeros(dim);
    if (this.config.chaos > 0) {
      const sigma = 10;
      const rho = 28;
      const beta = 8 / 3;
      const chaosScale = this.config.chaos * (1 - coherence);

      // Apply Lorenz-like dynamics to first 3 dimensions, mirror to last 3
      if (dim >= 6) {
        chaos[0] = chaosScale * sigma * (pos[1] - pos[0]);
        chaos[1] = chaosScale * (pos[0] * (rho - pos[2]) - pos[1]);
        chaos[2] = chaosScale * (pos[0] * pos[1] - beta * pos[2]);
        chaos[3] = chaosScale * sigma * (pos[4] - pos[3]);
        chaos[4] = chaosScale * (pos[3] * (rho - pos[5]) - pos[4]);
        chaos[5] = chaosScale * (pos[3] * pos[4] - beta * pos[5]);
      }
    }

    // Combine all forces
    return add(add(attraction, repulsion), chaos);
  }

  // ═══════════════════════════════════════════════════════════════
  // Runge-Kutta Integration
  // ═══════════════════════════════════════════════════════════════

  /**
   * RK4 integration step for smooth trajectory evolution
   */
  private rk4Step(
    pos: number[],
    targets: string[],
    coherence: number,
    mutations: number,
    dt: number
  ): number[] {
    const k1 = this.computeDrift(pos, targets, coherence, mutations);

    const pos2 = add(pos, scale(k1, dt / 2));
    const k2 = this.computeDrift(pos2, targets, coherence, mutations);

    const pos3 = add(pos, scale(k2, dt / 2));
    const k3 = this.computeDrift(pos3, targets, coherence, mutations);

    const pos4 = add(pos, scale(k3, dt));
    const k4 = this.computeDrift(pos4, targets, coherence, mutations);

    // Weighted average
    const dPos = zeros(pos.length);
    for (let i = 0; i < pos.length; i++) {
      dPos[i] = (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]) / 6;
    }

    return add(pos, scale(dPos, dt));
  }

  // ═══════════════════════════════════════════════════════════════
  // Main Update Method
  // ═══════════════════════════════════════════════════════════════

  /**
   * Update navigator position with intent and coherence
   *
   * This is the main integration point:
   * - Layer 9/10: coherence = spectral coherence C ∈ [0,1]
   * - Layer 13: coherence = 1 - risk' from intent validation
   * - mutations: from EvolvingLexicon mutation rate
   *
   * @param intentTongues - Target Sacred Tongue realms
   * @param coherence - Intent validation coherence [0, 1]
   * @param mutations - Mutation rate (default 0)
   * @param dt - Time step (default 0.1)
   * @returns Navigator state after update
   */
  update(
    intentTongues: string[],
    coherence: number = 1.0,
    mutations: number = 0,
    dt: number = 0.1
  ): NavigatorState {
    const c = Math.max(0, Math.min(1, coherence));

    // Multi-step integration for stability
    const steps = 10;
    const stepDt = dt / steps;
    let pos = this.position.slice();

    for (let i = 0; i < steps; i++) {
      pos = this.rk4Step(pos, intentTongues, c, mutations, stepDt);
    }

    // Soft projection back to ball
    const n = norm(pos);
    if (n > this.config.boundaryThreshold) {
      pos = scale(pos, this.config.boundaryThreshold / n);
    }

    // Update velocity (for momentum tracking)
    this.velocity = sub(pos, this.position);
    this.position = pos;

    // Record history
    this.history.push(pos.slice());
    this.coherenceHistory.push(c);

    // Trim history if too long
    if (this.history.length > this.config.maxHistory) {
      this.history.shift();
      this.coherenceHistory.shift();
    }

    // Compute adaptive parameters
    const currentR = this.getCurrentR(c);
    const currentKappa = this.getCurrentKappa(c);

    // Compute distance to origin
    const dCenter = this.hyperbolicDistanceKappa(pos, zeros(this.config.dimension), currentKappa);

    // Harmonic score: 1 / (1 + d_H + 2 * phaseDeviation)
    const phaseDeviation = 1 - c; // incoherence as phase deviation
    const penalty = 1 / (1 + dCenter + 2 * phaseDeviation);

    return {
      position: pos,
      velocity: this.velocity,
      coherence: c,
      currentR,
      currentKappa,
      penalty,
      timestamp: Date.now(),
    };
  }

  // ═══════════════════════════════════════════════════════════════
  // Analysis Methods
  // ═══════════════════════════════════════════════════════════════

  /**
   * Get distance to a specific realm center
   */
  distanceToRealm(tongue: string, coherence?: number): number {
    const center = REALM_CENTERS[tongue];
    if (!center) return Infinity;

    const kappa = coherence !== undefined
      ? this.getCurrentKappa(coherence)
      : -1;

    return this.hyperbolicDistanceKappa(this.position, center, kappa);
  }

  /**
   * Get the closest realm to current position
   */
  closestRealm(coherence?: number): { tongue: string; distance: number } {
    let minDist = Infinity;
    let closest = 'KO';

    for (const [tongue, center] of Object.entries(REALM_CENTERS)) {
      const kappa = coherence !== undefined
        ? this.getCurrentKappa(coherence)
        : -1;
      const dist = this.hyperbolicDistanceKappa(this.position, center, kappa);

      if (dist < minDist) {
        minDist = dist;
        closest = tongue;
      }
    }

    return { tongue: closest, distance: minDist };
  }

  /**
   * Compute trajectory entropy (measure of chaotic behavior)
   */
  trajectoryEntropy(): number {
    if (this.history.length < 10) return 0;

    // Compute displacement histogram
    const displacements: number[] = [];
    for (let i = 1; i < this.history.length; i++) {
      const d = norm(sub(this.history[i], this.history[i - 1]));
      displacements.push(d);
    }

    // Bin displacements
    const bins = 20;
    const maxD = Math.max(...displacements) + EPSILON;
    const counts = new Array(bins).fill(0);

    for (const d of displacements) {
      const bin = Math.min(bins - 1, Math.floor((d / maxD) * bins));
      counts[bin]++;
    }

    // Compute entropy
    let entropy = 0;
    const total = displacements.length;
    for (const count of counts) {
      if (count > 0) {
        const p = count / total;
        entropy -= p * Math.log2(p);
      }
    }

    return entropy / Math.log2(bins); // Normalize to [0, 1]
  }

  /**
   * Compute coherence stability (variance over recent history)
   */
  coherenceStability(window: number = 50): number {
    const recent = this.coherenceHistory.slice(-window);
    if (recent.length < 2) return 1.0;

    const mean = recent.reduce((a, b) => a + b, 0) / recent.length;
    const variance = recent.reduce((sum, c) => sum + (c - mean) ** 2, 0) / recent.length;

    // Return stability as 1 - normalized variance
    return Math.max(0, 1 - Math.sqrt(variance));
  }

  /**
   * Detect potential attack pattern (sustained low coherence + high movement)
   */
  detectAnomaly(thresholds = { coherence: 0.3, entropy: 0.7, stability: 0.4 }): {
    isAnomaly: boolean;
    score: number;
    indicators: string[];
  } {
    const indicators: string[] = [];
    let score = 0;

    const recentCoherence = this.coherenceHistory.slice(-20);
    const avgCoherence = recentCoherence.reduce((a, b) => a + b, 0) / recentCoherence.length;

    if (avgCoherence < thresholds.coherence) {
      indicators.push('low_coherence');
      score += 0.4;
    }

    const entropy = this.trajectoryEntropy();
    if (entropy > thresholds.entropy) {
      indicators.push('high_entropy');
      score += 0.3;
    }

    const stability = this.coherenceStability();
    if (stability < thresholds.stability) {
      indicators.push('unstable_coherence');
      score += 0.3;
    }

    return {
      isAnomaly: score >= 0.7,
      score,
      indicators,
    };
  }

  // ═══════════════════════════════════════════════════════════════
  // State Access
  // ═══════════════════════════════════════════════════════════════

  getPosition(): number[] {
    return this.position.slice();
  }

  getVelocity(): number[] {
    return this.velocity.slice();
  }

  getHistory(): number[][] {
    return this.history.map((p) => p.slice());
  }

  getCoherenceHistory(): number[] {
    return this.coherenceHistory.slice();
  }

  /**
   * Reset navigator to initial state
   */
  reset(initialPosition?: number[]): void {
    this.position = initialPosition
      ? [...initialPosition]
      : zeros(this.config.dimension);
    this.velocity = zeros(this.config.dimension);
    this.history = [this.position.slice()];
    this.coherenceHistory = [1.0];
  }

  /**
   * Serialize state for persistence
   */
  serialize(): string {
    return JSON.stringify({
      config: this.config,
      position: this.position,
      velocity: this.velocity,
      history: this.history.slice(-100), // Keep last 100
      coherenceHistory: this.coherenceHistory.slice(-100),
    });
  }

  /**
   * Restore from serialized state
   */
  static deserialize(json: string): AdaptiveHyperbolicNavigator {
    const data = JSON.parse(json);
    const nav = new AdaptiveHyperbolicNavigator(data.config, data.position);
    nav.velocity = data.velocity;
    nav.history = data.history;
    nav.coherenceHistory = data.coherenceHistory;
    return nav;
  }
}

// ═══════════════════════════════════════════════════════════════
// Factory Function
// ═══════════════════════════════════════════════════════════════

/**
 * Create an adaptive navigator with sensible defaults
 */
export function createAdaptiveNavigator(
  config?: Partial<AdaptiveNavigatorConfig>,
  initialPosition?: number[]
): AdaptiveHyperbolicNavigator {
  return new AdaptiveHyperbolicNavigator(config, initialPosition);
}

// ═══════════════════════════════════════════════════════════════
// Integration Helpers
// ═══════════════════════════════════════════════════════════════

/**
 * Compute coherence from Layer 9/10 spectral analysis
 *
 * @param spectralCoherence - Raw coherence from spectral analysis
 * @param spinCoherence - Spin coherence from consensus
 * @returns Combined coherence score
 */
export function computeCoherence(
  spectralCoherence: number,
  spinCoherence: number = 1.0
): number {
  // Geometric mean for balanced weighting
  return Math.sqrt(spectralCoherence * spinCoherence);
}

/**
 * Compute coherence from Layer 13 risk score
 *
 * @param riskScore - Risk' from intent validation [0, 1]
 * @returns Coherence as complement of risk
 */
export function riskToCoherence(riskScore: number): number {
  return 1 - Math.max(0, Math.min(1, riskScore));
}
