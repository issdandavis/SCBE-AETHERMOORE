"use strict";
/**
 * @file entropicLayer.ts
 * @module harmonic/entropicLayer
 * @layer Layer 7, Layer 12, Layer 13
 * @component Entropic Layer — Escape Detection, Adaptive k, Expansion Tracking
 * @version 3.2.4
 *
 * Consolidates the "Entropic / GeoSeal bottom layer" from the DualLatticeStack v2:
 *
 *   1. Escape Detection: Detects when a CHSFN state is leaving its trust basin
 *      (velocity toward boundary exceeds threshold, or state crosses basin lip).
 *
 *   2. Adaptive k: Dynamically adjusts the number of governance nodes (neighbors)
 *      queried for consensus, based on local threat level and state stability.
 *
 *   3. Expansion Tracking: Measures how fast a state's reachable volume grows.
 *      Rapid expansion = the state is "exploring" (possibly adversarial drift).
 *      Contraction = the state is stabilizing toward an attractor.
 *
 *   4. Time Dilation: For hostile loops, increases the effective step cost
 *      so repeated probing becomes exponentially slower.
 *
 * The UM tongue ("entropic sink") acts as the primary driver:
 *   higher UM impedance → more entropy → faster decay / redaction.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.DEFAULT_ENTROPIC_CONFIG = void 0;
exports.detectEscape = detectEscape;
exports.computeThreatLevel = computeThreatLevel;
exports.computeStability = computeStability;
exports.adaptiveK = adaptiveK;
exports.trackExpansion = trackExpansion;
exports.detectTimeDilation = detectTimeDilation;
exports.computePositionEntropy = computePositionEntropy;
exports.assess = assess;
const chsfn_js_1 = require("./chsfn.js");
// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════
const PHI = (1 + Math.sqrt(5)) / 2;
const EPSILON = 1e-10;
/** UM tongue index (entropic sink) */
const UM_INDEX = 5;
exports.DEFAULT_ENTROPIC_CONFIG = {
    escapeVelocityThreshold: 0.01,
    basinFractionThreshold: 0.8,
    minK: 2,
    maxK: 6,
    highAlertThreshold: 0.7,
    expansionSampleSteps: 10,
    expansionStepSize: 0.005,
    loopWindowSize: 20,
    loopSimilarityThreshold: 0.95,
};
// ═══════════════════════════════════════════════════════════════
// 1. Escape Detection
// ═══════════════════════════════════════════════════════════════
/**
 * Detect whether a state is escaping its trust basin.
 *
 * A state escapes when:
 * 1. Its radial velocity (projected drift toward boundary) exceeds threshold
 * 2. Its current norm exceeds a fraction of the basin radius
 * 3. UM impedance is high (entropic pressure pushing outward)
 *
 * @param state - Current CHSFN state
 * @param coherence - Unit coherence (determines basin radius)
 * @param config - Entropic configuration
 * @returns EscapeStatus
 */
function detectEscape(state, coherence, config = exports.DEFAULT_ENTROPIC_CONFIG) {
    const currentNorm = (0, chsfn_js_1.poincareNorm)(state.position);
    const basinRadius = Math.min(-Math.log(1 - Math.min(coherence, 0.999)), 0.95);
    // Compute radial velocity: project energy gradient onto radial direction
    const grad = (0, chsfn_js_1.energyGradient)(state);
    let radialVelocity = 0;
    if (currentNorm > EPSILON) {
        // Dot product of -gradient (drift direction) with radial unit vector
        for (let i = 0; i < 6; i++) {
            radialVelocity += (-grad[i]) * (state.position[i] / currentNorm);
        }
    }
    const basinFraction = basinRadius > 0 ? currentNorm / basinRadius : 1;
    const energy = (0, chsfn_js_1.energyFunctional)(state);
    const umImpedance = (0, chsfn_js_1.tongueImpedanceAt)(state, UM_INDEX);
    const escaping = radialVelocity > config.escapeVelocityThreshold ||
        basinFraction > config.basinFractionThreshold ||
        (umImpedance > 0.5 && radialVelocity > 0);
    return {
        escaping,
        radialVelocity,
        currentNorm,
        basinRadius,
        basinFraction,
        energy,
        umImpedance,
    };
}
// ═══════════════════════════════════════════════════════════════
// 2. Adaptive k
// ═══════════════════════════════════════════════════════════════
/**
 * Compute the threat level from a CHSFN state.
 *
 * Threat is a composite of:
 * - Distance from origin (far = more threatening)
 * - Phase misalignment (average tongue impedance)
 * - Energy level (higher = more unstable)
 *
 * @param state - Current CHSFN state
 * @returns Threat level in [0, 1]
 */
function computeThreatLevel(state) {
    const origin = [0, 0, 0, 0, 0, 0];
    const dist = (0, chsfn_js_1.hyperbolicDistance6D)(state.position, origin);
    // Distance contribution: sigmoid of d_H
    const distThreat = 1 / (1 + Math.exp(-2 * (dist - 1.5)));
    // Phase contribution: average impedance across tongues
    let avgImpedance = 0;
    for (let i = 0; i < 6; i++) {
        avgImpedance += (0, chsfn_js_1.tongueImpedanceAt)(state, i);
    }
    avgImpedance /= 6;
    // Energy contribution: normalized by typical baseline
    const energy = (0, chsfn_js_1.energyFunctional)(state);
    const energyThreat = 1 / (1 + Math.exp(-0.5 * (energy - 3)));
    // Weighted combination
    return Math.min(0.4 * distThreat + 0.3 * avgImpedance + 0.3 * energyThreat, 1);
}
/**
 * Compute stability score from energy gradient magnitude.
 *
 * Low gradient = near equilibrium = stable.
 * High gradient = far from equilibrium = unstable.
 *
 * @param state - Current CHSFN state
 * @returns Stability in [0, 1] where 1 = perfectly stable
 */
function computeStability(state) {
    const grad = (0, chsfn_js_1.energyGradient)(state);
    let gradNorm = 0;
    for (let i = 0; i < 6; i++)
        gradNorm += grad[i] * grad[i];
    gradNorm = Math.sqrt(gradNorm);
    // Sigmoid mapping: low gradient → high stability
    return 1 / (1 + gradNorm * 10);
}
/**
 * Adaptively select the number of governance nodes to query.
 *
 * Higher threat → higher k (more nodes for consensus).
 * More stable → lower k (fewer nodes needed).
 *
 * k = minK + round((maxK - minK) · threatLevel · (1 - stability))
 *
 * @param state - Current CHSFN state
 * @param config - Entropic configuration
 * @returns AdaptiveKResult
 */
function adaptiveK(state, config = exports.DEFAULT_ENTROPIC_CONFIG) {
    const threatLevel = computeThreatLevel(state);
    const stability = computeStability(state);
    // k scales with threat and inversely with stability
    const rawK = config.minK + (config.maxK - config.minK) * threatLevel * (1 - stability);
    const k = Math.max(config.minK, Math.min(config.maxK, Math.round(rawK)));
    return {
        k,
        threatLevel,
        stability,
        highAlert: threatLevel > config.highAlertThreshold,
    };
}
// ═══════════════════════════════════════════════════════════════
// 3. Expansion Tracking
// ═══════════════════════════════════════════════════════════════
/**
 * Track the expansion rate of reachable volume around a drifting state.
 *
 * Reachable volume in 6D hyperbolic space grows as V(r) ~ e^{5r}.
 * We measure the "effective radius" via the trust radius derived from
 * the energy level, then track how this changes over drift steps.
 *
 * Rapid expansion → adversarial exploration.
 * Contraction → stabilizing toward attractor.
 *
 * @param state - Initial CHSFN state
 * @param config - Entropic configuration
 * @returns ExpansionResult
 */
function trackExpansion(state, config = exports.DEFAULT_ENTROPIC_CONFIG) {
    const volumeTrace = [];
    let current = state;
    for (let step = 0; step <= config.expansionSampleSteps; step++) {
        // Effective radius: inverse of energy gives a trust-like measure
        const energy = (0, chsfn_js_1.energyFunctional)(current);
        const effectiveRadius = 1 / (1 + energy);
        volumeTrace.push((0, chsfn_js_1.quasiSphereVolume)(effectiveRadius));
        if (step < config.expansionSampleSteps) {
            current = (0, chsfn_js_1.driftStep)(current, config.expansionStepSize);
        }
    }
    // Growth rate: average delta between consecutive volumes
    let totalGrowth = 0;
    for (let i = 1; i < volumeTrace.length; i++) {
        totalGrowth += volumeTrace[i] - volumeTrace[i - 1];
    }
    const growthRate = totalGrowth / Math.max(volumeTrace.length - 1, 1);
    // Acceleration: compare first-half growth to second-half growth
    const mid = Math.floor(volumeTrace.length / 2);
    let firstHalf = 0;
    let secondHalf = 0;
    for (let i = 1; i <= mid; i++) {
        firstHalf += volumeTrace[i] - volumeTrace[i - 1];
    }
    for (let i = mid + 1; i < volumeTrace.length; i++) {
        secondHalf += volumeTrace[i] - volumeTrace[i - 1];
    }
    const accelerating = secondHalf > firstHalf + EPSILON;
    return {
        currentVolume: volumeTrace[0],
        growthRate,
        accelerating,
        contracting: growthRate < -EPSILON,
        volumeTrace,
    };
}
// ═══════════════════════════════════════════════════════════════
// 4. Time Dilation (Hostile Loop Detection)
// ═══════════════════════════════════════════════════════════════
/**
 * Detect hostile loops and compute time dilation factor.
 *
 * If a state is repeatedly visiting similar positions (low position entropy),
 * it's likely probing. Time dilation exponentially increases the effective
 * step cost for each detected repetition.
 *
 * dilationFactor = φ^loopCount
 *
 * @param positionHistory - Array of recent 6D positions
 * @param config - Entropic configuration
 * @returns TimeDilationResult
 */
function detectTimeDilation(positionHistory, config = exports.DEFAULT_ENTROPIC_CONFIG) {
    if (positionHistory.length < 2) {
        return { dilationFactor: 1, loopCount: 0, hostile: false, traceEntropy: 1 };
    }
    const window = positionHistory.slice(-config.loopWindowSize);
    // Count loops: how many pairs of positions are "too similar"
    let loopCount = 0;
    for (let i = 0; i < window.length; i++) {
        for (let j = i + 2; j < window.length; j++) {
            // Skip adjacent pairs (they're naturally close)
            const dist = (0, chsfn_js_1.hyperbolicDistance6D)(window[i], window[j]);
            // Similarity: 1 / (1 + dist)
            const similarity = 1 / (1 + dist);
            if (similarity > config.loopSimilarityThreshold) {
                loopCount++;
            }
        }
    }
    // Trace entropy: discretize positions into bins and compute Shannon entropy
    const traceEntropy = computePositionEntropy(window);
    // Dilation factor: φ^loopCount
    const dilationFactor = Math.pow(PHI, Math.min(loopCount, 20)); // Cap to avoid overflow
    const hostile = loopCount >= 3 || traceEntropy < 0.3;
    return {
        dilationFactor,
        loopCount,
        hostile,
        traceEntropy,
    };
}
/**
 * Compute Shannon entropy of a position trace.
 *
 * Low entropy → positions cluster (looping).
 * High entropy → positions spread out (exploring or drifting normally).
 *
 * @param positions - Array of 6D positions
 * @returns Normalized entropy in [0, 1]
 */
function computePositionEntropy(positions) {
    if (positions.length < 2)
        return 1;
    // Discretize: bin each dimension into 10 bins in [-1, 1]
    const binCount = 10;
    const bins = new Map();
    for (const pos of positions) {
        const key = pos
            .map((v) => Math.min(binCount - 1, Math.max(0, Math.floor(((v + 1) / 2) * binCount))))
            .join(',');
        bins.set(key, (bins.get(key) ?? 0) + 1);
    }
    // Shannon entropy
    const n = positions.length;
    let entropy = 0;
    for (const count of bins.values()) {
        const p = count / n;
        if (p > 0)
            entropy -= p * Math.log2(p);
    }
    // Normalize by max possible entropy
    const maxEntropy = Math.log2(n);
    return maxEntropy > 0 ? entropy / maxEntropy : 0;
}
/**
 * Perform a full entropic layer assessment.
 *
 * Combines all four sub-systems into a unified risk score and recommendation.
 *
 * @param state - Current CHSFN state
 * @param coherence - Unit coherence
 * @param positionHistory - Recent position history (for loop detection)
 * @param config - Entropic configuration
 * @returns EntropicAssessment
 */
function assess(state, coherence, positionHistory = [], config = exports.DEFAULT_ENTROPIC_CONFIG) {
    const escape = detectEscape(state, coherence, config);
    const ak = adaptiveK(state, config);
    const expansion = trackExpansion(state, config);
    const dilation = detectTimeDilation(positionHistory, config);
    // Composite entropic risk
    const escapeRisk = escape.escaping ? 0.8 : escape.basinFraction * 0.3;
    const expansionRisk = expansion.accelerating ? 0.6 : (expansion.growthRate > 0 ? 0.3 : 0);
    const loopRisk = dilation.hostile ? 0.9 : (dilation.loopCount > 0 ? dilation.loopCount * 0.15 : 0);
    const threatRisk = ak.threatLevel;
    const entropicRisk = Math.min(1, 0.3 * escapeRisk + 0.2 * expansionRisk + 0.25 * loopRisk + 0.25 * threatRisk);
    // Recommendation based on risk
    let recommendation;
    if (entropicRisk > 0.8 || dilation.hostile) {
        recommendation = 'DENY';
    }
    else if (entropicRisk > 0.5 || escape.escaping) {
        recommendation = 'QUARANTINE';
    }
    else if (entropicRisk > 0.2 || dilation.loopCount > 0) {
        recommendation = 'SLOW';
    }
    else {
        recommendation = 'PROCEED';
    }
    return {
        escape,
        adaptiveK: ak,
        expansion,
        timeDilation: dilation,
        entropicRisk,
        recommendation,
    };
}
//# sourceMappingURL=entropicLayer.js.map