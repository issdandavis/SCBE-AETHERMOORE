/**
 * SCBE Harmonic Assertions
 * Runtime validation utilities for harmonic calculations.
 */
/**
 * Assert that a value is an integer >= minVal
 */
export function assertIntGE(name, val, minVal) {
  if (!Number.isInteger(val) || val < minVal) {
    throw new RangeError(`${name} must be an integer >= ${minVal}, got ${val}`);
  }
}
/**
 * Assert that a value is finite (not NaN or Infinity)
 */
export function assertFinite(val, msg) {
  if (!Number.isFinite(val)) {
    throw new RangeError(msg);
  }
}
/**
 * Base-2 logarithm
 */
export function log2(x) {
  return Math.log(x) / Math.LN2;
}
//# sourceMappingURL=assertions.js.map
