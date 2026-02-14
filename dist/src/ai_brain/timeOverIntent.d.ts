/**
 * @file timeOverIntent.ts
 * @module ai_brain/timeOverIntent
 * @layer Layer 11, Layer 12
 * @component Time-over-Intent Coupling — Maximum Build
 * @version 1.0.0
 * @since 2026-02-11
 *
 * Implements dynamic triadic weight modulation and effective harmonic base
 * R_eff(t) that couples temporal governance signals into the harmonic wall.
 *
 * Key formulas:
 *   δτ(t) = τ_elapsed / τ_expected           — time dilation ratio
 *   γ(t) = clip(1 + β_τ·(δτ - 1), γ_min, γ_max)  — dynamic boost
 *   λ₃(t) = λ₃_base · γ(t)                  — causality weight boosted
 *   R_eff(t) = R₀ · exp(α_κ · κτ⁺ + α_Coh · (1 - Coh))
 *   H_toi(d*, t) = R_eff(t)^(d*²)            — time-aware harmonic wall
 *   Risk'(t) = Risk_base · H_toi(d*, t)       — modulated risk
 *
 * The triadic weight vector λ(t) = [λ₁, λ₂, λ₃(t)] sums to 1.
 * λ₁ = unitarity/symmetry, λ₂ = locality, λ₃ = causality (time-sensitive).
 * When governance latency δτ diverges from 1.0, λ₃ is boosted and
 * the other two are renormalized, increasing the temporal penalty.
 */
/**
 * Configuration for time-over-intent coupling.
 */
export interface TimeOverIntentConfig {
    /** Base harmonic wall exponent R₀ (default: 1.5, matching CONSTANTS.DEFAULT_R) */
    baseR: number;
    /** Curvature sensitivity α_κ (default: 0.5) */
    alphaKappa: number;
    /** Coherence sensitivity α_Coh (default: 0.3) */
    alphaCoherence: number;
    /** Time-boost sensitivity β_τ (default: 0.4) */
    betaTau: number;
    /** Minimum dynamic boost γ_min (default: 0.5) */
    gammaMin: number;
    /** Maximum dynamic boost γ_max (default: 2.0) */
    gammaMax: number;
    /** Base triadic weights [λ₁, λ₂, λ₃] — must sum to 1 */
    baseTriadicWeights: [number, number, number];
}
/**
 * Default configuration matching the Maximum Build research report.
 */
export declare const DEFAULT_TOI_CONFIG: TimeOverIntentConfig;
/**
 * Temporal observation at a given instant.
 */
export interface TemporalObservation {
    /** Elapsed governance time (seconds) */
    elapsedTime: number;
    /** Expected governance time (seconds) */
    expectedTime: number;
    /** Curvature at current position κ_τ */
    curvature: number;
    /** Spectral coherence Coh ∈ [0, 1] */
    coherence: number;
    /** Hyperbolic distance d* from safe origin */
    distance: number;
    /** Base risk score from detection pipeline ∈ [0, 1] */
    baseRisk: number;
}
/**
 * Result from time-over-intent evaluation.
 */
export interface TimeOverIntentResult {
    /** Time dilation ratio δτ */
    timeDilation: number;
    /** Dynamic boost factor γ(t) */
    gamma: number;
    /** Dynamic triadic weights [λ₁(t), λ₂(t), λ₃(t)] */
    triadicWeights: [number, number, number];
    /** Positive curvature exceedance κ_τ⁺ */
    positiveKappa: number;
    /** Effective harmonic base R_eff(t) */
    effectiveR: number;
    /** Time-aware harmonic wall H_toi(d*, t) */
    harmonicWall: number;
    /** Modulated risk Risk'(t) = baseRisk · H_toi */
    modulatedRisk: number;
    /** Weighted triadic distance d_triadic */
    triadicDistance: number;
}
/**
 * Compute time dilation ratio δτ(t) = τ_elapsed / τ_expected.
 *
 * δτ = 1 means on-time, > 1 means late, < 1 means early.
 * Returns 1.0 if expectedTime ≤ 0 (no temporal expectation).
 */
export declare function computeTimeDilation(elapsed: number, expected: number): number;
/**
 * Compute dynamic boost factor γ(t).
 *
 * γ(t) = clip(1 + β_τ · (δτ - 1), γ_min, γ_max)
 *
 * When δτ = 1 (on-time): γ = 1 (no boost).
 * When δτ > 1 (late): γ > 1 (boost causality weight).
 * When δτ < 1 (early): γ < 1 (reduce causality weight).
 */
export declare function computeGamma(timeDilation: number, betaTau?: number, gammaMin?: number, gammaMax?: number): number;
/**
 * Compute dynamic triadic weights λ(t) = [λ₁(t), λ₂(t), λ₃(t)].
 *
 * λ₃(t) = λ₃_base · γ(t), then renormalize so sum = 1.
 * The boost on λ₃ (causality) comes at the expense of λ₁ and λ₂,
 * preserving the simplex constraint.
 */
export declare function computeTriadicWeights(gamma: number, baseWeights?: [number, number, number]): [number, number, number];
/**
 * Compute positive curvature exceedance κ_τ⁺ = max(0, κ_τ).
 *
 * Negative curvature (concave regions near safe center) doesn't
 * penalize — only positive curvature (convex boundary drift) matters.
 */
export declare function positiveKappa(curvature: number): number;
/**
 * Compute effective harmonic base R_eff(t).
 *
 * R_eff(t) = R₀ · exp(α_κ · κ_τ⁺ + α_Coh · (1 - Coh))
 *
 * When κ_τ⁺ = 0 and Coh = 1: R_eff = R₀ (baseline).
 * Positive curvature increases R_eff → steeper wall.
 * Low coherence (1 - Coh large) increases R_eff → steeper wall.
 *
 * Upper-bounded at R₀ · exp(10) ≈ R₀ · 22026 to prevent overflow.
 */
export declare function computeEffectiveR(curvature: number, coherence: number, config?: Partial<TimeOverIntentConfig>): number;
/**
 * Compute time-aware harmonic wall H_toi(d*, t) = R_eff(t)^(d*²).
 *
 * This replaces the static R^(d²) with a temporally modulated base.
 * At d* = 0: H_toi = 1 (no penalty at safe center).
 * As d* → ∞: H_toi → ∞ exponentially.
 *
 * Capped at Number.MAX_SAFE_INTEGER to prevent infinity.
 */
export declare function harmonicWallTOI(distance: number, effectiveR: number): number;
/**
 * Compute triadic distance — weighted combination of 3 geometric measures.
 *
 * d_triadic = λ₁·d_symmetry + λ₂·d_locality + λ₃·d_causality
 *
 * In the Maximum Build, these map to:
 *   d_symmetry  = Poincaré distance (gauge invariance cost)
 *   d_locality  = lattice hop distance (spatial locality cost)
 *   d_causality = phase deviation + temporal penalty
 *
 * For simplicity, we accept pre-computed component distances.
 */
export declare function triadicDistance(weights: [number, number, number], distances: [number, number, number]): number;
/**
 * Full time-over-intent evaluation.
 *
 * Given a temporal observation, computes:
 * 1. Time dilation δτ
 * 2. Dynamic boost γ(t)
 * 3. Triadic weights λ(t)
 * 4. Effective harmonic base R_eff(t)
 * 5. Time-aware harmonic wall H_toi(d*, t)
 * 6. Modulated risk Risk'(t) = baseRisk · H_toi
 *
 * @param obs - Temporal observation
 * @param config - Time-over-intent configuration
 */
export declare function evaluateTimeOverIntent(obs: TemporalObservation, config?: Partial<TimeOverIntentConfig>): TimeOverIntentResult;
/**
 * Compute golden ratio hatch weight W = Σ φ^(k_i) · w_i.
 *
 * This is the φ-weighted aggregate of predicate scores, used by
 * Sacred Eggs genesis gate to determine spawn eligibility.
 *
 * Each predicate i contributes φ^(k_i) · w_i where:
 *   k_i = predicate importance rank (0 = most important)
 *   w_i = predicate pass score (0 or 1 for boolean, continuous for weighted)
 *
 * @param predicateScores - Array of { rank, score } pairs
 * @returns Hatch weight W
 */
export declare function computeHatchWeight(predicateScores: Array<{
    rank: number;
    score: number;
}>): number;
/**
 * Check if hatch weight meets genesis threshold.
 *
 * Default threshold T_genesis = φ³ ≈ 4.236 — requires at least
 * 3 high-ranked predicates to pass or strong weighted scores.
 */
export declare function meetsGenesisThreshold(hatchWeight: number, threshold?: number): boolean;
//# sourceMappingURL=timeOverIntent.d.ts.map