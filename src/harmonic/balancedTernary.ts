/**
 * @file balancedTernary.ts
 * @module harmonic/balancedTernary
 * @layer Layer 1, Layer 2, Layer 14
 * @component Balanced Ternary Encoding
 * @version 1.0.0
 *
 * Balanced ternary (base 3 with digits {-1, 0, +1}) encoding for SCBE vectors
 * and trust signals. Unlike binary or standard ternary, balanced ternary is
 * symmetric around zero — making it ideal for encoding signed intent,
 * direction, and magnitude in a single representation.
 *
 * Benefits:
 * - No separate sign bit needed (symmetry around zero)
 * - Fewer carry operations → faster hardware addition
 * - Natural representation for tri-state governance: DENY(-1), NEUTRAL(0), ALLOW(+1)
 * - Efficient encoding of Sacred Tongues dimensions (KO/AV/RU/CA/UM/DR)
 *
 * Trit values: T (-1), 0 (0), 1 (+1)
 * Notation: "1T0" = 1·9 + (-1)·3 + 0·1 = 6
 *
 * Layer mapping:
 *   L1 (Composition): Balanced ternary pipeline state encoding
 *   L2 (Realification): Complex → balanced ternary quantization
 *   L14 (Audio): Ternary pulse coding for audio axis signals
 */

/**
 * A single trit (balanced ternary digit): -1, 0, or +1
 */
export type Trit = -1 | 0 | 1;

/**
 * A balanced ternary number (array of trits, most significant first)
 */
export interface BalancedTernaryNumber {
  /** Trit array (MST first) */
  trits: Trit[];
  /** Decimal value (cached) */
  value: number;
}

/**
 * Quantized vector in balanced ternary
 */
export interface TernaryVector {
  /** Array of balanced ternary numbers (one per dimension) */
  components: BalancedTernaryNumber[];
  /** Original floating-point values (for reconstruction error) */
  original: number[];
  /** Quantization error (L2 norm of difference) */
  quantizationError: number;
}

/**
 * Convert a decimal integer to balanced ternary representation.
 *
 * Algorithm: Repeatedly divide by 3, adjusting remainders to {-1, 0, +1}.
 *
 * @param n - Integer to convert
 * @param minTrits - Minimum number of trits (zero-padded)
 * @returns Balanced ternary number
 */
export function toBalancedTernary(n: number, minTrits: number = 1): BalancedTernaryNumber {
  n = Math.round(n);
  if (n === 0) {
    return { trits: new Array(Math.max(1, minTrits)).fill(0) as Trit[], value: 0 };
  }

  const negative = n < 0;
  let absN = Math.abs(n);
  const trits: Trit[] = [];

  while (absN > 0) {
    let remainder = absN % 3;
    absN = Math.floor(absN / 3);

    if (remainder === 2) {
      remainder = -1;
      absN += 1;
    }

    trits.push(remainder as Trit);
  }

  // Negate all trits if original was negative
  if (negative) {
    for (let i = 0; i < trits.length; i++) {
      trits[i] = (-trits[i]) as Trit;
    }
  }

  // Reverse for MST-first ordering
  trits.reverse();

  // Pad to minimum length
  while (trits.length < minTrits) {
    trits.unshift(0);
  }

  return { trits, value: Math.round(n) };
}

/**
 * Convert balanced ternary back to decimal.
 *
 * @param trits - Array of trits (MST first)
 * @returns Decimal integer value
 */
export function fromBalancedTernary(trits: Trit[]): number {
  let value = 0;
  for (let i = 0; i < trits.length; i++) {
    value = value * 3 + trits[i];
  }
  return value;
}

/**
 * Add two balanced ternary numbers.
 *
 * Balanced ternary addition with carry propagation.
 * Carry is simpler than binary: at most 1 carry per position.
 *
 * @param a - First operand
 * @param b - Second operand
 * @returns Sum in balanced ternary
 */
export function addBalancedTernary(
  a: BalancedTernaryNumber,
  b: BalancedTernaryNumber
): BalancedTernaryNumber {
  // Pad to same length
  const maxLen = Math.max(a.trits.length, b.trits.length);
  const aTrits = [...new Array(maxLen - a.trits.length).fill(0), ...a.trits] as Trit[];
  const bTrits = [...new Array(maxLen - b.trits.length).fill(0), ...b.trits] as Trit[];

  const result: Trit[] = new Array(maxLen + 1).fill(0);
  let carry: Trit = 0;

  // Process from LST to MST
  for (let i = maxLen - 1; i >= 0; i--) {
    let sum = aTrits[i] + bTrits[i] + carry;
    carry = 0;

    if (sum > 1) {
      sum -= 3;
      carry = 1;
    } else if (sum < -1) {
      sum += 3;
      carry = -1;
    }

    result[i + 1] = sum as Trit;
  }

  result[0] = carry;

  // Remove leading zeros
  let start = 0;
  while (start < result.length - 1 && result[start] === 0) start++;
  const trits = result.slice(start) as Trit[];

  return {
    trits,
    value: a.value + b.value,
  };
}

/**
 * Negate a balanced ternary number (flip all trits).
 *
 * @param n - Number to negate
 * @returns Negated balanced ternary number
 */
export function negateBalancedTernary(n: BalancedTernaryNumber): BalancedTernaryNumber {
  return {
    trits: n.trits.map((t) => (-t) as Trit),
    value: n.value === 0 ? 0 : -n.value,
  };
}

/**
 * Multiply a balanced ternary number by a single trit.
 *
 * @param n - Number to multiply
 * @param trit - Single trit multiplier
 * @returns Product
 */
export function multiplyByTrit(n: BalancedTernaryNumber, trit: Trit): BalancedTernaryNumber {
  if (trit === 0) return toBalancedTernary(0, n.trits.length);
  if (trit === 1) return { trits: [...n.trits], value: n.value };
  return negateBalancedTernary(n);
}

/**
 * Quantize a floating-point value to balanced ternary with a given scale.
 *
 * Maps the value to an integer range [-3^(trits-1)..3^(trits-1)] then encodes.
 *
 * @param value - Floating-point value to quantize
 * @param scale - Scale factor (max absolute value representable)
 * @param numTrits - Number of trits for precision (default: 6)
 * @returns Balanced ternary number and quantization error
 */
export function quantize(
  value: number,
  scale: number,
  numTrits: number = 6
): { bt: BalancedTernaryNumber; error: number } {
  const maxInt = (Math.pow(3, numTrits) - 1) / 2; // e.g. 364 for 6 trits
  const safeScale = Math.max(scale, 1e-10);
  const clamped = Math.max(-1, Math.min(1, value / safeScale));
  const intVal = Math.round(clamped * maxInt);
  const bt = toBalancedTernary(intVal, numTrits);
  const reconstructed = (bt.value / maxInt) * safeScale;
  return { bt, error: Math.abs(value - reconstructed) };
}

/**
 * Dequantize a balanced ternary number back to floating-point.
 *
 * @param bt - Balanced ternary number
 * @param scale - Scale factor
 * @param numTrits - Number of trits used in quantization
 * @returns Reconstructed floating-point value
 */
export function dequantize(bt: BalancedTernaryNumber, scale: number, numTrits: number = 6): number {
  const maxInt = (Math.pow(3, numTrits) - 1) / 2;
  return (bt.value / maxInt) * scale;
}

/**
 * Quantize a full vector into balanced ternary.
 *
 * Each dimension is independently quantized with the given per-dimension
 * or global scale.
 *
 * @param vector - Float vector to quantize
 * @param scale - Global scale or per-dimension scales
 * @param numTrits - Trits per dimension (default: 6)
 * @returns Ternary vector with quantization error
 */
export function quantizeVector(
  vector: number[],
  scale: number | number[],
  numTrits: number = 6
): TernaryVector {
  const scales = typeof scale === 'number' ? vector.map(() => scale) : scale;
  const components: BalancedTernaryNumber[] = [];
  let totalErrorSq = 0;

  for (let i = 0; i < vector.length; i++) {
    const { bt, error } = quantize(vector[i], scales[i], numTrits);
    components.push(bt);
    totalErrorSq += error * error;
  }

  return {
    components,
    original: [...vector],
    quantizationError: Math.sqrt(totalErrorSq),
  };
}

/**
 * Dequantize a ternary vector back to floating-point.
 *
 * @param tv - Ternary vector
 * @param scale - Global scale or per-dimension scales
 * @param numTrits - Trits per dimension
 * @returns Reconstructed float vector
 */
export function dequantizeVector(
  tv: TernaryVector,
  scale: number | number[],
  numTrits: number = 6
): number[] {
  const scales = typeof scale === 'number' ? tv.components.map(() => scale) : scale;
  return tv.components.map((bt, i) => dequantize(bt, scales[i], numTrits));
}

/**
 * Encode a governance decision as a balanced ternary trit.
 *
 * DENY → T (-1), NEUTRAL/QUARANTINE → 0, ALLOW → 1
 *
 * @param decision - Governance decision
 * @returns Single trit
 */
export function governanceToTrit(decision: 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY'): Trit {
  switch (decision) {
    case 'ALLOW': return 1;
    case 'DENY': return -1;
    default: return 0;
  }
}

/**
 * Decode a trit back to a governance decision.
 *
 * @param trit - Trit value
 * @returns Governance decision string
 */
export function tritToGovernance(trit: Trit): 'ALLOW' | 'QUARANTINE' | 'DENY' {
  if (trit === 1) return 'ALLOW';
  if (trit === -1) return 'DENY';
  return 'QUARANTINE';
}

/**
 * Format balanced ternary as string using T notation.
 *
 * @param bt - Balanced ternary number
 * @returns String like "1T0" (where T represents -1)
 */
export function formatBalancedTernary(bt: BalancedTernaryNumber): string {
  return bt.trits.map((t) => (t === -1 ? 'T' : String(t))).join('');
}

/**
 * Parse a T-notation string into balanced ternary.
 *
 * @param s - String like "1T0"
 * @returns Balanced ternary number
 */
export function parseBalancedTernary(s: string): BalancedTernaryNumber {
  const trits: Trit[] = [];
  for (const ch of s) {
    if (ch === 'T' || ch === 't') trits.push(-1);
    else if (ch === '0') trits.push(0);
    else if (ch === '1') trits.push(1);
    else throw new Error(`Invalid balanced ternary digit: ${ch}`);
  }
  return { trits, value: fromBalancedTernary(trits) };
}
