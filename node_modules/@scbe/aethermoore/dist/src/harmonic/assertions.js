"use strict";
/**
 * SCBE Harmonic Assertions
 * Runtime validation utilities for harmonic calculations.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.log2 = exports.assertFinite = exports.assertIntGE = void 0;
/**
 * Assert that a value is an integer >= minVal
 */
function assertIntGE(name, val, minVal) {
    if (!Number.isInteger(val) || val < minVal) {
        throw new RangeError(`${name} must be an integer >= ${minVal}, got ${val}`);
    }
}
exports.assertIntGE = assertIntGE;
/**
 * Assert that a value is finite (not NaN or Infinity)
 */
function assertFinite(val, msg) {
    if (!Number.isFinite(val)) {
        throw new RangeError(msg);
    }
}
exports.assertFinite = assertFinite;
/**
 * Base-2 logarithm
 */
function log2(x) {
    return Math.log(x) / Math.LN2;
}
exports.log2 = log2;
//# sourceMappingURL=assertions.js.map