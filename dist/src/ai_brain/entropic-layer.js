"use strict";
/**
 * @file entropic-layer.ts
 * @module ai_brain/entropic-layer
 * @layer Layer 12, Layer 13
 * @version 1.0.0
 *
 * EntropicLayer: Escape detection, adaptive-k, and expansion tracking.
 *
 * Consolidates entropy-related mechanics into a unified module:
 * - Escape detection: monitors state volume growth (hyperbolic volume proxy)
 * - Adaptive k: dynamically adjusts governance k based on coherence
 * - Expansion volume: approximates hyperbolic volume for 6D manifold
 *
 * Escape velocity theorem: k > 2*C_quantum / sqrt(N0)
 * where C_quantum is the quantum coupling constant and N0 is initial node count.
 *
 * Integration: feeds into Layer 12 (harmonic wall) and Layer 13 (risk decision).
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.EntropicLayer = exports.DEFAULT_ENTROPIC_CONFIG = exports.MAX_K = exports.MIN_K = exports.DEFAULT_MAX_VOLUME = void 0;
// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════
/** Default maximum volume before escape detection triggers */
exports.DEFAULT_MAX_VOLUME = 1e6;
/** Golden ratio for phi-weighted bounds */
const PHI = (1 + Math.sqrt(5)) / 2;
/** Minimum adaptive k (always at least 1 governance node) */
exports.MIN_K = 1;
/** Maximum adaptive k (cap to prevent over-governance) */
exports.MAX_K = 50;
exports.DEFAULT_ENTROPIC_CONFIG = {
    maxVolume: exports.DEFAULT_MAX_VOLUME,
    baseK: 5,
    cQuantum: 1.0,
    n0: 100,
};
// ═══════════════════════════════════════════════════════════════
// EntropicLayer class
// ═══════════════════════════════════════════════════════════════
class EntropicLayer {
    config;
    constructor(config = {}) {
        this.config = { ...exports.DEFAULT_ENTROPIC_CONFIG, ...config };
    }
    /**
     * Compute approximate hyperbolic volume for a state position.
     *
     * For a point at radius r in the Poincare ball in d dimensions,
     * the hyperbolic volume of the ball of that radius is approximately:
     *   V ~ (pi^(d/2) * r^d / Gamma(d/2+1)) * exp((d-1) * r)
     *
     * For 6D (our Sacred Tongues manifold):
     *   V ~ (pi^3 * r^6 / 6) * exp(5r)
     *
     * @param position - Point in Poincare ball
     * @returns Approximate hyperbolic volume
     */
    computeExpansionVolume(position) {
        let rSq = 0;
        for (let i = 0; i < position.length; i++) {
            rSq += position[i] * position[i];
        }
        const r = Math.sqrt(rSq);
        const d = position.length;
        // Euclidean volume factor: pi^(d/2) * r^d / Gamma(d/2 + 1)
        const halfD = d / 2;
        const eucFactor = Math.pow(Math.PI, halfD) * Math.pow(r, d) / this.gamma(halfD + 1);
        // Hyperbolic expansion factor: exp((d-1) * r)
        const hypFactor = Math.exp(Math.min((d - 1) * r, 50)); // cap to avoid overflow
        return eucFactor * hypFactor;
    }
    /**
     * Detect whether a state has escaped the safe operational region.
     *
     * Escape occurs when:
     * 1. Expansion volume exceeds threshold, OR
     * 2. Radial velocity exceeds escape velocity bound
     *
     * @param state - Current position and velocity
     * @returns Escape assessment with diagnostics
     */
    detectEscape(state) {
        const volume = this.computeExpansionVolume(state.position);
        const volumeRatio = volume / this.config.maxVolume;
        // Escape velocity bound: k > 2*C_quantum / sqrt(N0)
        const escapeVelocityBound = (2 * this.config.cQuantum) / Math.sqrt(this.config.n0);
        // Radial velocity (dot product of velocity with normalized position)
        let rSq = 0;
        let vDotR = 0;
        for (let i = 0; i < state.position.length; i++) {
            rSq += state.position[i] * state.position[i];
            vDotR += state.velocity[i] * state.position[i];
        }
        const r = Math.sqrt(rSq);
        const radialVelocity = r > 1e-10 ? vDotR / r : 0;
        const escaped = volume > this.config.maxVolume ||
            radialVelocity > escapeVelocityBound;
        return {
            escaped,
            volume,
            volumeRatio,
            escapeVelocityBound,
            radialVelocity,
        };
    }
    /**
     * Compute adaptive k (number of governance nodes) based on coherence.
     *
     * Low coherence -> fewer governance nodes (tighter control).
     * High coherence -> more nodes (broader participation).
     *
     * Formula: k = floor(baseK * coherence) + 1
     *
     * @param coherence - NK coherence score [0, 1]
     * @returns Adaptive k value
     */
    adaptiveK(coherence) {
        const clamped = Math.max(0, Math.min(1, coherence));
        const k = Math.floor(this.config.baseK * clamped) + 1;
        return Math.max(exports.MIN_K, Math.min(exports.MAX_K, k));
    }
    /**
     * Check if the escape velocity theorem is satisfied.
     *
     * Theorem: For stable operation, k > 2*C_quantum / sqrt(N0)
     *
     * @param currentK - Current number of governance nodes
     * @returns Whether the bound is satisfied
     */
    escapeVelocityBoundSatisfied(currentK) {
        const bound = (2 * this.config.cQuantum) / Math.sqrt(this.config.n0);
        return currentK > bound;
    }
    /**
     * Update configuration at runtime.
     */
    updateConfig(partial) {
        Object.assign(this.config, partial);
    }
    /**
     * Get current configuration.
     */
    getConfig() {
        return { ...this.config };
    }
    /**
     * Gamma function approximation (Stirling's for non-integers, exact for small integers).
     */
    gamma(n) {
        // For integer and half-integer values commonly used in volume formulas
        if (n === 1)
            return 1;
        if (n === 2)
            return 1;
        if (n === 3)
            return 2;
        if (n === 4)
            return 6;
        if (n === 0.5)
            return Math.sqrt(Math.PI);
        if (n === 1.5)
            return Math.sqrt(Math.PI) / 2;
        if (n === 2.5)
            return (3 * Math.sqrt(Math.PI)) / 4;
        if (n === 3.5)
            return (15 * Math.sqrt(Math.PI)) / 8;
        // Stirling's approximation for other values
        return Math.sqrt((2 * Math.PI) / n) * Math.pow(n / Math.E, n);
    }
}
exports.EntropicLayer = EntropicLayer;
//# sourceMappingURL=entropic-layer.js.map