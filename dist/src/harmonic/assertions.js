"use strict";
/**
 * SCBE Harmonic Assertions
 * Runtime validation utilities for harmonic calculations.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.assertIntGE = assertIntGE;
exports.assertFinite = assertFinite;
exports.log2 = log2;
/**
 * Assert that a value is an integer >= minVal
 */
function assertIntGE(name, val, minVal) {
    if (!Number.isInteger(val) || val < minVal) {
        throw new RangeError(`${name} must be an integer >= ${minVal}, got ${val}`);
    }
}
/**
 * Assert that a value is finite (not NaN or Infinity)
 */
function assertFinite(val, msg) {
    if (!Number.isFinite(val)) {
        throw new RangeError(msg);
    }
}
/**
 * Base-2 logarithm
 */
function log2(x) {
    return Math.log(x) / Math.LN2;
}
//# sourceMappingURL=assertions.js.map