"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.DEFAULT_TOI_CONFIG = void 0;
exports.computeTimeDilation = computeTimeDilation;
exports.computeGamma = computeGamma;
exports.computeTriadicWeights = computeTriadicWeights;
exports.positiveKappa = positiveKappa;
exports.computeEffectiveR = computeEffectiveR;
exports.harmonicWallTOI = harmonicWallTOI;
exports.triadicDistance = triadicDistance;
exports.evaluateTimeOverIntent = evaluateTimeOverIntent;
exports.computeHatchWeight = computeHatchWeight;
exports.meetsGenesisThreshold = meetsGenesisThreshold;
const types_js_1 = require("./types.js");
/**
 * Default configuration matching the Maximum Build research report.
 */
exports.DEFAULT_TOI_CONFIG = {
    baseR: 1.5,
    alphaKappa: 0.5,
    alphaCoherence: 0.3,
    betaTau: 0.4,
    gammaMin: 0.5,
    gammaMax: 2.0,
    baseTriadicWeights: [0.4, 0.3, 0.3],
};
// ═══════════════════════════════════════════════════════════════
// Core Functions
// ═══════════════════════════════════════════════════════════════
/**
 * Compute time dilation ratio δτ(t) = τ_elapsed / τ_expected.
 *
 * δτ = 1 means on-time, > 1 means late, < 1 means early.
 * Returns 1.0 if expectedTime ≤ 0 (no temporal expectation).
 */
function computeTimeDilation(elapsed, expected) {
    if (expected <= types_js_1.BRAIN_EPSILON)
        return 1.0;
    return Math.max(0, elapsed) / expected;
}
/**
 * Compute dynamic boost factor γ(t).
 *
 * γ(t) = clip(1 + β_τ · (δτ - 1), γ_min, γ_max)
 *
 * When δτ = 1 (on-time): γ = 1 (no boost).
 * When δτ > 1 (late): γ > 1 (boost causality weight).
 * When δτ < 1 (early): γ < 1 (reduce causality weight).
 */
function computeGamma(timeDilation, betaTau = exports.DEFAULT_TOI_CONFIG.betaTau, gammaMin = exports.DEFAULT_TOI_CONFIG.gammaMin, gammaMax = exports.DEFAULT_TOI_CONFIG.gammaMax) {
    const raw = 1 + betaTau * (timeDilation - 1);
    return Math.max(gammaMin, Math.min(gammaMax, raw));
}
/**
 * Compute dynamic triadic weights λ(t) = [λ₁(t), λ₂(t), λ₃(t)].
 *
 * λ₃(t) = λ₃_base · γ(t), then renormalize so sum = 1.
 * The boost on λ₃ (causality) comes at the expense of λ₁ and λ₂,
 * preserving the simplex constraint.
 */
function computeTriadicWeights(gamma, baseWeights = exports.DEFAULT_TOI_CONFIG.baseTriadicWeights) {
    const [w1, w2, w3] = baseWeights;
    const boostedW3 = w3 * gamma;
    const total = w1 + w2 + boostedW3;
    if (total < types_js_1.BRAIN_EPSILON) {
        return [1 / 3, 1 / 3, 1 / 3];
    }
    return [w1 / total, w2 / total, boostedW3 / total];
}
/**
 * Compute positive curvature exceedance κ_τ⁺ = max(0, κ_τ).
 *
 * Negative curvature (concave regions near safe center) doesn't
 * penalize — only positive curvature (convex boundary drift) matters.
 */
function positiveKappa(curvature) {
    return Math.max(0, curvature);
}
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
function computeEffectiveR(curvature, coherence, config = {}) {
    const baseR = config.baseR ?? exports.DEFAULT_TOI_CONFIG.baseR;
    const alphaK = config.alphaKappa ?? exports.DEFAULT_TOI_CONFIG.alphaKappa;
    const alphaCoh = config.alphaCoherence ?? exports.DEFAULT_TOI_CONFIG.alphaCoherence;
    const kPlus = positiveKappa(curvature);
    const cohDeficit = Math.max(0, Math.min(1, 1 - coherence));
    const exponent = alphaK * kPlus + alphaCoh * cohDeficit;
    // Clamp exponent to avoid overflow (exp(10) ≈ 22026)
    const clampedExp = Math.min(exponent, 10);
    return baseR * Math.exp(clampedExp);
}
/**
 * Compute time-aware harmonic wall H_toi(d*, t) = R_eff(t)^(d*²).
 *
 * This replaces the static R^(d²) with a temporally modulated base.
 * At d* = 0: H_toi = 1 (no penalty at safe center).
 * As d* → ∞: H_toi → ∞ exponentially.
 *
 * Capped at Number.MAX_SAFE_INTEGER to prevent infinity.
 */
function harmonicWallTOI(distance, effectiveR) {
    if (distance < types_js_1.BRAIN_EPSILON)
        return 1.0;
    if (effectiveR <= 1.0 + types_js_1.BRAIN_EPSILON)
        return 1.0;
    const dSq = distance * distance;
    const wall = Math.pow(effectiveR, dSq);
    return Math.min(wall, Number.MAX_SAFE_INTEGER);
}
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
function triadicDistance(weights, distances) {
    return weights[0] * distances[0] + weights[1] * distances[1] + weights[2] * distances[2];
}
// ═══════════════════════════════════════════════════════════════
// Composite Evaluation
// ═══════════════════════════════════════════════════════════════
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
function evaluateTimeOverIntent(obs, config = {}) {
    const cfg = { ...exports.DEFAULT_TOI_CONFIG, ...config };
    // Step 1: Time dilation
    const timeDilation = computeTimeDilation(obs.elapsedTime, obs.expectedTime);
    // Step 2: Dynamic boost
    const gamma = computeGamma(timeDilation, cfg.betaTau, cfg.gammaMin, cfg.gammaMax);
    // Step 3: Triadic weights
    const weights = computeTriadicWeights(gamma, cfg.baseTriadicWeights);
    // Step 4: Positive curvature exceedance
    const kPlus = positiveKappa(obs.curvature);
    // Step 5: Effective R
    const effectiveR = computeEffectiveR(obs.curvature, obs.coherence, cfg);
    // Step 6: Harmonic wall
    const wall = harmonicWallTOI(obs.distance, effectiveR);
    // Step 7: Modulated risk
    const modulatedRisk = Math.min(1.0, obs.baseRisk * wall);
    // Step 8: Triadic distance (using d* as all three components as a default
    // — callers with per-component distances should use triadicDistance directly)
    const tDist = triadicDistance(weights, [obs.distance, obs.distance, obs.distance]);
    return {
        timeDilation,
        gamma,
        triadicWeights: weights,
        positiveKappa: kPlus,
        effectiveR,
        harmonicWall: wall,
        modulatedRisk,
        triadicDistance: tDist,
    };
}
// ═══════════════════════════════════════════════════════════════
// Golden Ratio Hatch Weight (Bridge to Sacred Eggs)
// ═══════════════════════════════════════════════════════════════
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
function computeHatchWeight(predicateScores) {
    let W = 0;
    for (const { rank, score } of predicateScores) {
        W += Math.pow(types_js_1.PHI, rank) * score;
    }
    return W;
}
/**
 * Check if hatch weight meets genesis threshold.
 *
 * Default threshold T_genesis = φ³ ≈ 4.236 — requires at least
 * 3 high-ranked predicates to pass or strong weighted scores.
 */
function meetsGenesisThreshold(hatchWeight, threshold = types_js_1.PHI * types_js_1.PHI * types_js_1.PHI) {
    return hatchWeight >= threshold;
}
//# sourceMappingURL=timeOverIntent.js.map