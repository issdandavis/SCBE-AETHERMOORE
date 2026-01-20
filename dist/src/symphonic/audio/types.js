"use strict";
/**
 * Dual-Channel Consensus: Type Definitions
 *
 * Part of SCBE-AETHERMOORE v3.0.0
 * Patent: USPTO #63/961,403
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.PROFILE_48K = exports.PROFILE_44K = exports.PROFILE_16K = exports.computeBeta = exports.expectedCorrelation = void 0;
/**
 * Compute expected correlation for clean watermark
 */
function expectedCorrelation(profile) {
    return profile.gamma * Math.sqrt(profile.b);
}
exports.expectedCorrelation = expectedCorrelation;
/**
 * Compute beta threshold from profile
 */
function computeBeta(profile) {
    return profile.betaFactor * expectedCorrelation(profile);
}
exports.computeBeta = computeBeta;
/**
 * Predefined audio profiles for different use cases
 */
exports.PROFILE_16K = {
    SR: 16000,
    N: 4096,
    binResolution: 3.90625,
    f_min: 1200,
    f_max: 4200,
    k_min: 308,
    k_max: 1075,
    b: 32,
    delta_k_min: 12,
    gamma: 0.02,
    betaFactor: 0.4, // 40% of expected correlation
    E_min: 0.001,
    clipThreshold: 0.95
};
exports.PROFILE_44K = {
    SR: 44100,
    N: 8192,
    binResolution: 5.383,
    f_min: 2000,
    f_max: 9000,
    k_min: 372,
    k_max: 1672,
    b: 48,
    delta_k_min: 11,
    gamma: 0.015,
    betaFactor: 0.35, // 35% of expected correlation
    E_min: 0.0008,
    clipThreshold: 0.95
};
exports.PROFILE_48K = {
    SR: 48000,
    N: 8192,
    binResolution: 5.859,
    f_min: 2500,
    f_max: 12000,
    k_min: 427,
    k_max: 2048,
    b: 64,
    delta_k_min: 10,
    gamma: 0.01,
    betaFactor: 0.30, // 30% of expected correlation
    E_min: 0.0005,
    clipThreshold: 0.95
};
//# sourceMappingURL=types.js.map