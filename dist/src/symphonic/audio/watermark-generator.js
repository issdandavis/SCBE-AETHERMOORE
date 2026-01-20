"use strict";
/**
 * Dual-Channel Consensus: Watermark Generation
 *
 * Generates challenge-bound acoustic watermarks
 *
 * Part of SCBE-AETHERMOORE v3.0.0
 * Patent: USPTO #63/961,403
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.generateWatermarkWithMetadata = exports.generateWatermark = void 0;
/**
 * Generate challenge-bound watermark
 *
 * Formula: s[n] = Σ a_j · (-1)^(c_j) · sin(2π k_j · n/N + φ_j)
 *
 * @param challenge - Challenge bitstring
 * @param bins - Selected bin indices
 * @param phases - Per-bin phases
 * @param N - Frame size (samples)
 * @param gamma - Mix gain
 * @returns Watermark waveform
 */
function generateWatermark(challenge, bins, phases, N, gamma) {
    const b = bins.length;
    const a_j = 1 / Math.sqrt(b); // Normalized amplitude
    const waveform = new Float32Array(N);
    for (let n = 0; n < N; n++) {
        let sample = 0;
        for (let j = 0; j < b; j++) {
            const k_j = bins[j];
            const phi_j = phases[j];
            const c_j = challenge[j]; // 0 or 1
            // s[n] = Σ a_j · (-1)^(c_j) · sin(2π k_j · n/N + φ_j)
            const sign = c_j === 0 ? 1 : -1;
            sample += a_j * sign * Math.sin(2 * Math.PI * k_j * n / N + phi_j);
        }
        waveform[n] = gamma * sample;
    }
    return waveform;
}
exports.generateWatermark = generateWatermark;
/**
 * Generate watermark with full result metadata
 */
function generateWatermarkWithMetadata(challenge, bins, phases, N, gamma) {
    const waveform = generateWatermark(challenge, bins, phases, N, gamma);
    return {
        waveform,
        bins: [...bins],
        phases: [...phases]
    };
}
exports.generateWatermarkWithMetadata = generateWatermarkWithMetadata;
//# sourceMappingURL=watermark-generator.js.map