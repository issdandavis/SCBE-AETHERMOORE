"use strict";
/**
 * Dual-Channel Consensus: Matched Filter Verification
 *
 * Computes matched-filter projections and correlation scores
 *
 * Part of SCBE-AETHERMOORE v3.0.0
 * Patent: USPTO #63/961,403
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.verifyWatermark = exports.computeProjections = void 0;
const types_1 = require("./types");
/**
 * Compute matched-filter projections
 *
 * Formula: p_j = (2/N) · Σ y[n] · sin(2π k_j · n/N + φ_j)
 *
 * @param audio - Received audio samples
 * @param bins - Expected bin indices
 * @param phases - Expected phases
 * @param N - Frame size (samples)
 * @returns Per-bin projections
 */
function computeProjections(audio, bins, phases, N) {
    const projections = [];
    for (let j = 0; j < bins.length; j++) {
        const k_j = bins[j];
        const phi_j = phases[j];
        // p_j = (2/N) · Σ y[n] · sin(2π k_j · n/N + φ_j)
        let p_j = 0;
        for (let n = 0; n < N; n++) {
            p_j += audio[n] * Math.sin(2 * Math.PI * k_j * n / N + phi_j);
        }
        p_j *= (2 / N);
        projections.push(p_j);
    }
    return projections;
}
exports.computeProjections = computeProjections;
/**
 * Verify challenge-bound watermark
 *
 * @param audio - Received audio samples
 * @param challenge - Expected challenge bitstring
 * @param bins - Expected bin indices
 * @param phases - Expected phases
 * @param profile - Audio profile with thresholds
 * @returns Verification result
 */
function verifyWatermark(audio, challenge, bins, phases, profile) {
    const N = profile.N;
    const beta = (0, types_1.computeBeta)(profile); // Compute beta from profile
    const E_min = profile.E_min;
    const clipThreshold = profile.clipThreshold;
    // Enforce exact N samples
    if (audio.length !== N) {
        throw new Error(`Audio must be exactly ${N} samples, got ${audio.length}`);
    }
    // Compute projections
    const projections = computeProjections(audio, bins, phases, N);
    // Compute correlation
    let correlation = 0;
    for (let j = 0; j < bins.length; j++) {
        const c_j = challenge[j]; // 0 or 1
        const sign = c_j === 0 ? 1 : -1;
        correlation += sign * projections[j];
    }
    // Compute total watermark energy
    const energy = projections.reduce((sum, p) => sum + p * p, 0);
    // Check for clipping
    const maxAmplitude = Math.max(...Array.from(audio).map(Math.abs));
    const clipped = maxAmplitude >= clipThreshold;
    // Decision
    const passed = correlation >= beta && energy >= E_min && !clipped;
    return {
        correlation,
        projections,
        energy,
        clipped,
        passed
    };
}
exports.verifyWatermark = verifyWatermark;
//# sourceMappingURL=matched-filter.js.map