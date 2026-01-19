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
/** The Six Sacred Tongues */
export declare const TONGUES: readonly ["KO", "AV", "RU", "CA", "UM", "DR"];
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
export declare function getFluxState(nu: number): FluxState;
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
export declare class LanguesMetric {
    private betaBase;
    private omegaBase;
    private riskThresholds;
    /** Golden ratio weights wₗ = φˡ */
    readonly weights: number[];
    /** Phase offsets φₗ = 2πk/6 */
    readonly phases: number[];
    /** Beta values per tongue */
    readonly betas: number[];
    constructor(config?: LanguesMetricConfig);
    /**
     * Compute Langues metric value
     * L(x,t) = Σ wₗ exp(βₗ · (dₗ + sin(ωₗt + φₗ)))
     *
     * @param point - 6D point (distances in each tongue dimension)
     * @param t - Time parameter
     * @returns Metric value
     */
    compute(point: Vector6D, t?: number): number;
    /**
     * Evaluate risk level and decision
     *
     * @param L - Langues metric value
     * @returns [risk, decision] tuple
     */
    riskLevel(L: number): [number, Decision];
    /**
     * Compute gradient ∂L/∂dₗ (for optimization)
     */
    gradient(point: Vector6D, t?: number): Vector6D;
}
/**
 * Fluxing Langues Metric - with dynamic dimension participation
 * L_f(x,t) = Σ νᵢ(t) wᵢ exp[βᵢ(dᵢ + sin(ωᵢt + φᵢ))]
 */
export declare class FluxingLanguesMetric extends LanguesMetric {
    private fluxes;
    constructor(config?: LanguesMetricConfig, fluxes?: DimensionFlux[]);
    /**
     * Update flux values according to dynamics
     * ν̇ᵢ = κᵢ(ν̄ᵢ - νᵢ) + σᵢ sin(Ωᵢt)
     */
    updateFlux(t: number, dt: number): void;
    /**
     * Get current flux values
     */
    getFluxValues(): number[];
    /**
     * Get flux states for all dimensions
     */
    getFluxStates(): FluxState[];
    /**
     * Compute fluxing Langues metric
     * L_f(x,t) = Σ νᵢ(t) wᵢ exp[βᵢ(dᵢ + sin(ωᵢt + φᵢ))]
     */
    computeFluxing(point: Vector6D, t?: number): number;
    /**
     * Effective dimensionality D_f = Σνᵢ
     */
    effectiveDimensionality(): number;
}
//# sourceMappingURL=languesMetric.d.ts.map