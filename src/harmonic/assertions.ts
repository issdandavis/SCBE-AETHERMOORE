/**
 * SCBE Harmonic Assertions
 * Runtime validation utilities for harmonic calculations.
 */

/**
 * Assert that a value is an integer >= minVal
 */
export function assertIntGE(name: string, val: number, minVal: number): void {
  if (!Number.isInteger(val) || val < minVal) {
    throw new RangeError(`${name} must be an integer >= ${minVal}, got ${val}`);
  }
}

/**
 * Assert that a value is finite (not NaN or Infinity)
 */
export function assertFinite(val: number, msg: string): void {
  if (!Number.isFinite(val)) {
    throw new RangeError(msg);
  }
}

/**
 * Base-2 logarithm
 */
export function log2(x: number): number {
  return Math.log(x) / Math.LN2;
}
