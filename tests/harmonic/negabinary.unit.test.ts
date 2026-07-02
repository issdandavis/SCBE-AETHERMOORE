/**
 * @file negabinary.unit.test.ts
 * @component Negabinary spine cord — encoding round trips & polarity (L2-unit)
 */

import { describe, expect, it } from 'vitest';
import { NegaBinary } from '../../src/harmonic/negabinary.js';

describe('negabinary encoding', () => {
  it('matches the canonical reference examples (MSB-first strings)', () => {
    const cases: Array<[number, string]> = [
      [0, '0'],
      [1, '1'],
      [-1, '11'],
      [2, '110'],
      [-2, '10'],
      [3, '111'],
      [-3, '1101'],
    ];
    for (const [n, str] of cases) {
      expect(NegaBinary.fromInt(n).toString(), `encode ${n}`).toBe(str);
      expect(NegaBinary.fromInt(n).toInt(), `decode ${n}`).toBe(n);
    }
  });

  it('round-trips every integer in a signed range with no sign bit', () => {
    for (let n = -300; n <= 300; n++) {
      const nb = NegaBinary.fromInt(n);
      expect(nb.toInt()).toBe(n);
      // Signless: every digit is 0 or 1.
      for (const b of nb.bits) expect(b === 0 || b === 1).toBe(true);
    }
  });

  it('fromBits round-trips MSB-first', () => {
    const nb = NegaBinary.fromInt(-3); // "1101"
    expect(NegaBinary.fromBits([1, 1, 0, 1]).toInt()).toBe(-3);
    expect(NegaBinary.fromBits(nb.bitsMsb).toInt()).toBe(-3);
  });

  it('addition agrees with integer addition', () => {
    for (const [a, b] of [
      [5, 7],
      [-4, 9],
      [12, -30],
      [-11, -6],
    ]) {
      expect(NegaBinary.fromInt(a).add(NegaBinary.fromInt(b)).toInt()).toBe(a + b);
    }
  });

  it('negate agrees with integer negation', () => {
    for (const n of [0, 1, -1, 7, -13, 42]) {
      // `-0 || 0` normalizes JS negative zero so Object.is-based toBe passes.
      expect(NegaBinary.fromInt(n).negate().toInt()).toBe(-n || 0);
    }
  });

  it('reads polarity from alternating bit positions', () => {
    // 1 = "1": single even-position bit → positive.
    expect(NegaBinary.fromInt(1).polarityProfile().polarity).toBe('positive');
    expect(NegaBinary.fromInt(1).tonguePolarity()).toBe('KO');
    // -2 = "10": single odd-position bit → negative.
    expect(NegaBinary.fromInt(-2).polarityProfile().polarity).toBe('negative');
    expect(NegaBinary.fromInt(-2).tonguePolarity()).toBe('AV');
    // -1 = "11": one even + one odd → balanced.
    expect(NegaBinary.fromInt(-1).polarityProfile().polarity).toBe('balanced');
    expect(NegaBinary.fromInt(-1).tonguePolarity()).toBe('RU');
  });

  it('encodes each bit as a tongue by polarity', () => {
    // 2 = "110" → bits LSB-first [0,1,1]: pos0=0→UM, pos1=1(odd)→AV, pos2=1(even)→KO
    expect(NegaBinary.fromInt(2).tongueEncoding()).toEqual(['UM', 'AV', 'KO']);
  });
});
