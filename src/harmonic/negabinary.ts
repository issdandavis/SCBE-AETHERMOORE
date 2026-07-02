/**
 * @file negabinary.ts
 * @module harmonic/negabinary
 * @layer Layer 9, Layer 12
 * @component Negabinary (base -2) Encoding — the signless spine cord
 * @version 1.0.0
 *
 * TypeScript port of `symphonic_cipher/scbe_aethermoore/negabinary.py`.
 *
 * Negabinary uses digits {0, 1} with base -2:
 *     value = Σ dᵢ · (-2)ⁱ,  dᵢ ∈ {0, 1}
 *
 * Every integer has a unique representation with NO sign bit — negatives
 * emerge naturally because polarity alternates per bit position (even
 * positions carry positive weight, odd positions negative). That makes it
 * the natural "spine cord" for the layer pipeline: one signless thread
 * whose alternating polarity binds the chain together (see spine.ts).
 *
 * Canon tongue mapping (matches the Python reference):
 *   even-position 1-bits → KO (positive/assertive)
 *   odd-position  1-bits → AV (negative/receptive)
 *   0-bits               → UM (silence/universal)
 */

import type { TongueCode } from '../tokenizer/index.js';

/** Polarity reading of a negabinary word. */
export interface PolarityProfile {
  positiveBits: number;
  negativeBits: number;
  positiveWeight: number;
  negativeWeight: number;
  polarity: 'positive' | 'negative' | 'balanced';
}

/**
 * A negabinary (base -2) number. Bits are stored LSB-first internally;
 * display and {@link bitsMsb} are MSB-first (human-readable).
 */
export class NegaBinary {
  /** Bits, LSB first, each 0 or 1. */
  readonly bits: readonly number[];

  private constructor(bits: readonly number[]) {
    this.bits = bits.length > 0 ? bits : [0];
  }

  /** Convert an integer to its unique negabinary representation. */
  static fromInt(n: number): NegaBinary {
    n = Math.trunc(n);
    if (n === 0) return new NegaBinary([0]);
    const bits: number[] = [];
    let value = n;
    while (value !== 0) {
      // Remainder in {0,1} for base -2 (JS % can be negative → adjust).
      let remainder = value % -2;
      value = Math.trunc(value / -2);
      if (remainder < 0) {
        remainder += 2;
        value += 1;
      }
      bits.push(remainder);
    }
    return new NegaBinary(bits);
  }

  /** Build from an explicit bit sequence. */
  static fromBits(bits: readonly number[], msbFirst = true): NegaBinary {
    const lsb = msbFirst ? [...bits].reverse() : [...bits];
    return new NegaBinary(lsb.map((b) => (b ? 1 : 0)));
  }

  /** Decode back to a signed integer. */
  toInt(): number {
    let result = 0;
    for (let i = 0; i < this.bits.length; i++) {
      if (this.bits[i]) result += (-2) ** i;
    }
    return result;
  }

  /** Bits in MSB-first order (human-readable). */
  get bitsMsb(): number[] {
    return [...this.bits].reverse();
  }

  /** Number of bits in the word. */
  get width(): number {
    return this.bits.length;
  }

  /** Negate (through the integer — negation is non-trivial in base -2). */
  negate(): NegaBinary {
    return NegaBinary.fromInt(-this.toInt());
  }

  /** Add two negabinary words (through the integer domain). */
  add(other: NegaBinary): NegaBinary {
    return NegaBinary.fromInt(this.toInt() + other.toInt());
  }

  /**
   * Analyze bit-position polarity. Even positions contribute positive
   * weight ((-2)⁰=1, (-2)²=4, …); odd positions negative ((-2)¹=-2, …).
   */
  polarityProfile(): PolarityProfile {
    let positiveBits = 0;
    let negativeBits = 0;
    let positiveWeight = 0;
    let negativeWeight = 0;
    for (let i = 0; i < this.bits.length; i++) {
      if (this.bits[i] !== 1) continue;
      if (i % 2 === 0) {
        positiveBits += 1;
        positiveWeight += (-2) ** i;
      } else {
        negativeBits += 1;
        negativeWeight += (-2) ** i;
      }
    }
    const polarity =
      positiveBits > negativeBits
        ? 'positive'
        : negativeBits > positiveBits
          ? 'negative'
          : 'balanced';
    return { positiveBits, negativeBits, positiveWeight, negativeWeight, polarity };
  }

  /** Shannon entropy of the 0/1 bit distribution. */
  bitEntropy(): number {
    const ones = this.bits.reduce((s, b) => s + b, 0);
    const zeros = this.bits.length - ones;
    const n = this.bits.length;
    if (n === 0) return 0;
    let entropy = 0;
    for (const c of [zeros, ones]) {
      if (c > 0) {
        const p = c / n;
        entropy -= p * Math.log2(p);
      }
    }
    return entropy;
  }

  /**
   * Net polarity → a Sacred Tongue affinity.
   * positive-dominant → KO, negative-dominant → AV, balanced → RU.
   */
  tonguePolarity(): TongueCode {
    const p = this.polarityProfile().polarity;
    return p === 'positive' ? 'KO' : p === 'negative' ? 'AV' : 'RU';
  }

  /** Encode each bit position as a tongue by polarity (KO/AV/UM). */
  tongueEncoding(): TongueCode[] {
    return this.bits.map((b, i) => (b === 0 ? 'UM' : i % 2 === 0 ? 'KO' : 'AV'));
  }

  /** MSB-first bit string, e.g. "110". */
  toString(): string {
    return this.bitsMsb.join('');
  }
}
