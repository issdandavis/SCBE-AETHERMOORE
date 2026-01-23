/**
 * SCBE Langues Metric
 *
 * 6D phase-shifted exponential cost function with the Six Sacred Tongues.
 * L(x,t) = Σ wₗ exp(βₗ · (dₗ + sin(ωₗt + φₗ)))
 *
 * Tongues: KO, AV, RU, CA, UM, DR
 * Weights: wₗ = φˡ (golden ratio progression)
 * Phases: φₗ = 2πk/6 (60° intervals)
 */

import { Vector6D } from './constants.js';

/** Golden ratio φ = (1 + √5) / 2 */
const PHI = (1 + Math.sqrt(5)) / 2;

/** The Six Sacred Tongues */
export const TONGUES = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'] as const;
export type Tongue = typeof TONGUES[number];

/** Dimension flux state */
export type FluxState = 'Polly' | 'Quasi' | 'Demi' | 'Collapsed';

/** Decision outcome from risk evaluation */
export type Decision = 'ALLOW' | 'QUARANTINE' | 'DENY';

/**
 * Dimension flux dynamics
 * ν̇ᵢ = κᵢ(ν̄ᵢ - νᵢ) + σᵢ sin(Ωᵢt)
 */
export interface DimensionFlux {
  /** Current flux value ν ∈ [0, 1] */
  nu: number;
  /** Mean attractor ν̄ */
  nuBar: number;
  /** Relaxation rate κ */
  kappa: number;
  /** Oscillation amplitude σ */
  sigma: number;
  /** Oscillation frequency Ω */
  omega: number;
}

/**
 * Get the flux state name from ν value
 */
export function getFluxState(nu: number): FluxState {
  if (nu >= 0.9) return 'Polly';
  if (nu >= 0.5) return 'Quasi';
  if (nu >= 0.1) return 'Demi';
  return 'Collapsed';
}

/**
 * Langues Metric configuration
 */
export interface LanguesMetricConfig {
  /** Base β value for exponential (default: 1.0) */
  betaBase?: number;
  /** Base ω for phase oscillation (default: 1.0) */
  omegaBase?: number;
  /** Risk thresholds [low, high] */
  riskThresholds?: [number, number];
}

/**
 * Langues Metric - 6D governance cost function
 */
export class LanguesMetric {
  private betaBase: number;
  private omegaBase: number;
  private riskThresholds: [number, number];

  /** Golden ratio weights wₗ = φˡ */
  readonly weights: number[];
  /** Phase offsets φₗ = 2πk/6 */
  readonly phases: number[];
  /** Beta values per tongue */
  readonly betas: number[];

  constructor(config: LanguesMetricConfig = {}) {
    this.betaBase = config.betaBase ?? 1.0;
    this.omegaBase = config.omegaBase ?? 1.0;
    this.riskThresholds = config.riskThresholds ?? [1.0, 10.0];

    // Initialize weights: wₗ = φˡ
    this.weights = TONGUES.map((_, i) => Math.pow(PHI, i));

    // Initialize phases: φₗ = 2πk/6 (60° intervals)
    this.phases = TONGUES.map((_, i) => (2 * Math.PI * i) / 6);

    // Beta values scale with golden ratio
    this.betas = TONGUES.map((_, i) => this.betaBase * Math.pow(PHI, i * 0.5));
  }

  /**
   * Compute Langues metric value
   * L(x,t) = Σ wₗ exp(βₗ · (dₗ + sin(ωₗt + φₗ)))
   *
   * @param point - 6D point (distances in each tongue dimension)
   * @param t - Time parameter
   * @returns Metric value
   */
  compute(point: Vector6D, t: number = 0): number {
    let L = 0;
    for (let i = 0; i < 6; i++) {
      const d = point[i];
      const omega = this.omegaBase * (i + 1);
      const phase = this.phases[i];
      const sinTerm = Math.sin(omega * t + phase);
      const exponent = this.betas[i] * (d + sinTerm);
      L += this.weights[i] * Math.exp(exponent);
    }
    return L;
  }

  /**
   * Evaluate risk level and decision
   *
   * @param L - Langues metric value
   * @returns [risk, decision] tuple
   */
  riskLevel(L: number): [number, Decision] {
    const [low, high] = this.riskThresholds;
    if (L < low) return [L, 'ALLOW'];
    if (L < high) return [L, 'QUARANTINE'];
    return [L, 'DENY'];
  }

  /**
   * Compute gradient ∂L/∂dₗ (for optimization)
   */
  gradient(point: Vector6D, t: number = 0): Vector6D {
    const grad: Vector6D = [0, 0, 0, 0, 0, 0];
    for (let i = 0; i < 6; i++) {
      const d = point[i];
      const omega = this.omegaBase * (i + 1);
      const phase = this.phases[i];
      const sinTerm = Math.sin(omega * t + phase);
      const exponent = this.betas[i] * (d + sinTerm);
      // ∂L/∂dₗ = wₗ · βₗ · exp(βₗ · (dₗ + sin(...)))
      grad[i] = this.weights[i] * this.betas[i] * Math.exp(exponent);
    }
    return grad;
  }
}

/**
 * Fluxing Langues Metric - with dynamic dimension participation
 * L_f(x,t) = Σ νᵢ(t) wᵢ exp[βᵢ(dᵢ + sin(ωᵢt + φᵢ))]
 */
export class FluxingLanguesMetric extends LanguesMetric {
  private fluxes: DimensionFlux[];

  constructor(config: LanguesMetricConfig = {}, fluxes?: DimensionFlux[]) {
    super(config);

    // Default flux configuration
    this.fluxes = fluxes ?? TONGUES.map((_, i) => ({
      nu: 1.0,
      nuBar: 0.8,
      kappa: 0.1,
      sigma: 0.05,
      omega: 0.5 * (i + 1),
    }));
  }

  /**
   * Update flux values according to dynamics
   * ν̇ᵢ = κᵢ(ν̄ᵢ - νᵢ) + σᵢ sin(Ωᵢt)
   */
  updateFlux(t: number, dt: number): void {
    for (const flux of this.fluxes) {
      const nuDot = flux.kappa * (flux.nuBar - flux.nu) +
                    flux.sigma * Math.sin(flux.omega * t);
      flux.nu = Math.max(0, Math.min(1, flux.nu + nuDot * dt));
    }
  }

  /**
   * Get current flux values
   */
  getFluxValues(): number[] {
    return this.fluxes.map(f => f.nu);
  }

  /**
   * Get flux states for all dimensions
   */
  getFluxStates(): FluxState[] {
    return this.fluxes.map(f => getFluxState(f.nu));
  }

  /**
   * Compute fluxing Langues metric
   * L_f(x,t) = Σ νᵢ(t) wᵢ exp[βᵢ(dᵢ + sin(ωᵢt + φᵢ))]
   */
  computeFluxing(point: Vector6D, t: number = 0): number {
    let L = 0;
    for (let i = 0; i < 6; i++) {
      const nu = this.fluxes[i].nu;
      const d = point[i];
      const omega = (this as any).omegaBase * (i + 1);
      const phase = this.phases[i];
      const sinTerm = Math.sin(omega * t + phase);
      const exponent = this.betas[i] * (d + sinTerm);
      L += nu * this.weights[i] * Math.exp(exponent);
    }
    return L;
  }

  /**
   * Effective dimensionality D_f = Σνᵢ
   */
  effectiveDimensionality(): number {
    return this.fluxes.reduce((sum, f) => sum + f.nu, 0);
  }
}
