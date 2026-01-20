"use strict";
/**
 * SCBE Harmonic Scaling (Layer 12)
 *
 * Core mathematical functions for harmonic scaling:
 * - H(d, R) = R^(d²) - Exponential risk amplification
 * - Security bit calculations
 * - Harmonic distance in 6D space
 * - Octave transposition
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.octaveTranspose = exports.harmonicDistance = exports.securityLevel = exports.securityBits = exports.harmonicScale = void 0;
const constants_js_1 = require("./constants.js");
const assertions_js_1 = require("./assertions.js");
/**
 * Harmonic scale function H(d, R) = exp(d² * ln(R)) = R^(d²)
 *
 * For R=1.5, d=6: H = 1.5^36 ≈ 2.18 × 10⁶
 *
 * @param d - Dimension/deviation parameter (integer >= 1)
 * @param R - Base ratio (default: 1.5)
 * @returns Scaled value
 */
function harmonicScale(d, R = constants_js_1.CONSTANTS.DEFAULT_R) {
    (0, assertions_js_1.assertIntGE)('d', d, 1);
    if (!(R > 0))
        throw new RangeError('R must be > 0');
    const e = d * d * Math.log(R);
    const y = Math.exp(e);
    (0, assertions_js_1.assertFinite)(y, 'harmonicScale overflow');
    return y;
}
exports.harmonicScale = harmonicScale;
/**
 * Calculate security bits with harmonic amplification
 *
 * @param baseBits - Base security level in bits
 * @param d - Dimension parameter
 * @param R - Base ratio
 * @returns Amplified security bits
 */
function securityBits(baseBits, d, R = constants_js_1.CONSTANTS.DEFAULT_R) {
    (0, assertions_js_1.assertIntGE)('d', d, 1);
    if (!(R > 0))
        throw new RangeError('R must be > 0');
    return baseBits + d * d * (0, assertions_js_1.log2)(R);
}
exports.securityBits = securityBits;
/**
 * Calculate security level with harmonic scaling
 *
 * @param base - Base security level
 * @param d - Dimension parameter
 * @param R - Base ratio
 * @returns Scaled security level
 */
function securityLevel(base, d, R = constants_js_1.CONSTANTS.DEFAULT_R) {
    return base * harmonicScale(d, R);
}
exports.securityLevel = securityLevel;
/**
 * Harmonic distance in 6D phase space with weighted dimensions
 *
 * Uses R^(1/5) weighting for dimensions 4-6 (the "sacred tongue" dimensions)
 *
 * @param u - First 6D vector
 * @param v - Second 6D vector
 * @returns Weighted Euclidean distance
 */
function harmonicDistance(u, v) {
    const R5 = constants_js_1.CONSTANTS.R_FIFTH;
    const g = [1, 1, 1, R5, R5 * R5, R5 * R5 * R5];
    let s = 0;
    for (let i = 0; i < 6; i++) {
        const d = u[i] - v[i];
        s += g[i] * d * d;
    }
    return Math.sqrt(s);
}
exports.harmonicDistance = harmonicDistance;
/**
 * Transpose a frequency by octaves
 *
 * @param freq - Base frequency (must be > 0)
 * @param octaves - Number of octaves to transpose (can be negative)
 * @returns Transposed frequency
 */
function octaveTranspose(freq, octaves) {
    if (!(freq > 0))
        throw new RangeError('freq must be > 0');
    return freq * Math.pow(2, octaves);
}
exports.octaveTranspose = octaveTranspose;
//# sourceMappingURL=harmonicScaling.js.map