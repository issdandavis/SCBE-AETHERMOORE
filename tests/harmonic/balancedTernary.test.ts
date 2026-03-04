/**
 * @file balancedTernary.test.ts
 * @module tests/harmonic
 * @layer Layer 1, Layer 12, Layer 13
 * @component Balanced Ternary Arithmetic
 * @version 3.2.4
 */

import { describe, it, expect } from 'vitest';
import {
  toBalancedTernary,
  fromBalancedTernary,
  addBalancedTernary,
  negateBalancedTernary,
  multiplyByTrit,
  quantize,
  dequantize,
  quantizeVector,
  dequantizeVector,
  governanceToTrit,
  tritToGovernance,
  formatBalancedTernary,
  parseBalancedTernary,
} from '../../src/harmonic/balancedTernary.js';

describe('toBalancedTernary', () => {
  it('converts 0 to [0]', () => {
    const result = toBalancedTernary(0);
    expect(result.value).toBe(0);
    expect(result.trits).toEqual([0]);
  });

  it('converts 1 to [1]', () => {
    const result = toBalancedTernary(1);
    expect(result.value).toBe(1);
    expect(result.trits).toEqual([1]);
  });

  it('converts -1 to [-1]', () => {
    const result = toBalancedTernary(-1);
    expect(result.value).toBe(-1);
    expect(result.trits).toEqual([-1]);
  });

  it('converts 2 to [1, -1] (3 - 1 = 2)', () => {
    const result = toBalancedTernary(2);
    expect(result.value).toBe(2);
    expect(result.trits).toEqual([1, -1]);
  });

  it('converts 3 to [1, 0]', () => {
    const result = toBalancedTernary(3);
    expect(result.value).toBe(3);
    expect(result.trits).toEqual([1, 0]);
  });

  it('converts 6 to [1, -1, 0] (9 - 3 = 6)', () => {
    const result = toBalancedTernary(6);
    expect(result.value).toBe(6);
    expect(result.trits).toEqual([1, -1, 0]);
  });

  it('converts -2 correctly', () => {
    const result = toBalancedTernary(-2);
    expect(result.value).toBe(-2);
    expect(fromBalancedTernary(result.trits)).toBe(-2);
  });

  it('converts -3 correctly', () => {
    const result = toBalancedTernary(-3);
    expect(result.value).toBe(-3);
    expect(fromBalancedTernary(result.trits)).toBe(-3);
  });

  it('converts 4 correctly', () => {
    const result = toBalancedTernary(4);
    expect(result.value).toBe(4);
    expect(fromBalancedTernary(result.trits)).toBe(4);
  });

  it('converts 13 correctly', () => {
    const result = toBalancedTernary(13);
    expect(result.value).toBe(13);
    expect(fromBalancedTernary(result.trits)).toBe(13);
  });

  it('produces only valid trits (-1, 0, or 1) in output', () => {
    for (const n of [-50, -13, -7, 0, 7, 13, 50]) {
      const result = toBalancedTernary(n);
      for (const trit of result.trits) {
        expect([-1, 0, 1]).toContain(trit);
      }
    }
  });

  it('respects minTrits padding', () => {
    const result = toBalancedTernary(1, 5);
    expect(result.trits.length).toBeGreaterThanOrEqual(5);
    expect(result.value).toBe(1);
  });

  it('sets .value equal to the input integer', () => {
    for (const n of [0, 1, -1, 5, -5, 27, -27]) {
      const result = toBalancedTernary(n);
      expect(result.value).toBe(n);
    }
  });
});

describe('fromBalancedTernary', () => {
  it('converts [0] to 0', () => {
    expect(fromBalancedTernary([0])).toBe(0);
  });

  it('converts [1] to 1', () => {
    expect(fromBalancedTernary([1])).toBe(1);
  });

  it('converts [-1] to -1', () => {
    expect(fromBalancedTernary([-1])).toBe(-1);
  });

  it('converts [1, -1] to 2', () => {
    expect(fromBalancedTernary([1, -1])).toBe(2);
  });

  it('converts [1, 0] to 3', () => {
    expect(fromBalancedTernary([1, 0])).toBe(3);
  });

  it('converts [1, -1, 0] to 6', () => {
    expect(fromBalancedTernary([1, -1, 0])).toBe(6);
  });

  it('round-trips with toBalancedTernary for range -50..50', () => {
    for (let n = -50; n <= 50; n++) {
      const bt = toBalancedTernary(n);
      const recovered = fromBalancedTernary(bt.trits);
      expect(recovered).toBe(n);
    }
  });
});

describe('addBalancedTernary', () => {
  it('adds 0 + 0 = 0', () => {
    const a = toBalancedTernary(0);
    const b = toBalancedTernary(0);
    const result = addBalancedTernary(a, b);
    expect(result.value).toBe(0);
  });

  it('adds 1 + 1 = 2', () => {
    const a = toBalancedTernary(1);
    const b = toBalancedTernary(1);
    const result = addBalancedTernary(a, b);
    expect(result.value).toBe(2);
  });

  it('adds 1 + (-1) = 0', () => {
    const a = toBalancedTernary(1);
    const b = toBalancedTernary(-1);
    const result = addBalancedTernary(a, b);
    expect(result.value).toBe(0);
  });

  it('adds 3 + 4 = 7', () => {
    const a = toBalancedTernary(3);
    const b = toBalancedTernary(4);
    const result = addBalancedTernary(a, b);
    expect(result.value).toBe(7);
  });

  it('adds 13 + (-6) = 7', () => {
    const a = toBalancedTernary(13);
    const b = toBalancedTernary(-6);
    const result = addBalancedTernary(a, b);
    expect(result.value).toBe(7);
  });

  it('adds -5 + (-8) = -13', () => {
    const a = toBalancedTernary(-5);
    const b = toBalancedTernary(-8);
    const result = addBalancedTernary(a, b);
    expect(result.value).toBe(-13);
  });

  it('result trits decode correctly via fromBalancedTernary', () => {
    for (const [x, y] of [[7, 3], [-4, 9], [0, -12], [15, -15]]) {
      const a = toBalancedTernary(x);
      const b = toBalancedTernary(y);
      const result = addBalancedTernary(a, b);
      expect(fromBalancedTernary(result.trits)).toBe(x + y);
    }
  });

  it('result only contains valid trits', () => {
    const a = toBalancedTernary(27);
    const b = toBalancedTernary(13);
    const result = addBalancedTernary(a, b);
    for (const trit of result.trits) {
      expect([-1, 0, 1]).toContain(trit);
    }
  });
});

describe('negateBalancedTernary', () => {
  it('negates 1 to -1', () => {
    const bt = toBalancedTernary(1);
    const neg = negateBalancedTernary(bt);
    expect(neg.value).toBe(-1);
  });

  it('negates -1 to 1', () => {
    const bt = toBalancedTernary(-1);
    const neg = negateBalancedTernary(bt);
    expect(neg.value).toBe(1);
  });

  it('negates 0 to 0', () => {
    const bt = toBalancedTernary(0);
    const neg = negateBalancedTernary(bt);
    expect(neg.value).toBe(0);
  });

  it('flips all trits individually', () => {
    const bt = toBalancedTernary(13);
    const neg = negateBalancedTernary(bt);
    expect(neg.trits.length).toBe(bt.trits.length);
    for (let i = 0; i < bt.trits.length; i++) {
      expect(neg.trits[i]).toBe(-bt.trits[i] as -1 | 0 | 1);
    }
  });

  it('double negation returns original value', () => {
    for (const n of [-13, -7, 0, 7, 13]) {
      const bt = toBalancedTernary(n);
      const neg = negateBalancedTernary(bt);
      const negNeg = negateBalancedTernary(neg);
      expect(negNeg.value).toBe(n);
    }
  });

  it('negates 6 to -6 with all trits flipped', () => {
    const bt = toBalancedTernary(6);
    const neg = negateBalancedTernary(bt);
    expect(neg.value).toBe(-6);
    for (let i = 0; i < bt.trits.length; i++) {
      expect(neg.trits[i]).toBe(-bt.trits[i] as -1 | 0 | 1);
    }
  });
});

describe('multiplyByTrit', () => {
  it('multiply by 1 returns same value', () => {
    const bt = toBalancedTernary(5);
    const result = multiplyByTrit(bt, 1);
    expect(result.value).toBe(5);
  });

  it('multiply by -1 negates the value', () => {
    const bt = toBalancedTernary(5);
    const result = multiplyByTrit(bt, -1);
    expect(result.value).toBe(-5);
  });

  it('multiply by 0 gives 0', () => {
    const bt = toBalancedTernary(13);
    const result = multiplyByTrit(bt, 0);
    expect(result.value).toBe(0);
  });

  it('multiply negative by -1 gives positive', () => {
    const bt = toBalancedTernary(-7);
    const result = multiplyByTrit(bt, -1);
    expect(result.value).toBe(7);
  });

  it('multiply 0 by any trit gives 0', () => {
    const bt = toBalancedTernary(0);
    for (const trit of [-1, 0, 1] as const) {
      const result = multiplyByTrit(bt, trit);
      expect(result.value).toBe(0);
    }
  });

  it('result trits decode correctly', () => {
    const bt = toBalancedTernary(9);
    const result = multiplyByTrit(bt, -1);
    expect(fromBalancedTernary(result.trits)).toBe(-9);
  });
});

describe('quantize and dequantize', () => {
  it('quantizes and dequantizes 0.0 with small error', () => {
    const scale = 1.0;
    const { bt } = quantize(0.0, scale);
    const recovered = dequantize(bt, scale);
    expect(Math.abs(recovered - 0.0)).toBeLessThan(scale * 0.5);
  });

  it('quantizes and dequantizes 1.0 with small error', () => {
    const scale = 1.0;
    const { bt, error } = quantize(1.0, scale);
    const recovered = dequantize(bt, scale);
    expect(Math.abs(recovered - 1.0)).toBeLessThan(0.01);
    expect(Math.abs(error)).toBeLessThan(0.01);
  });

  it('quantizes and dequantizes -1.0 with small error', () => {
    const scale = 1.0;
    const { bt } = quantize(-1.0, scale);
    const recovered = dequantize(bt, scale);
    expect(Math.abs(recovered - (-1.0))).toBeLessThan(0.01);
  });

  it('error field reflects quantization residual', () => {
    const scale = 0.5;
    const value = 1.3;
    const { bt, error } = quantize(value, scale);
    const recovered = dequantize(bt, scale);
    expect(Math.abs(recovered + error - value)).toBeLessThan(1e-9);
  });

  it('quantizes a range of floats with bounded error', () => {
    const scale = 3.0;
    for (const v of [-3.0, -1.5, -0.5, 0.0, 0.5, 1.5, 3.0]) {
      const { bt } = quantize(v, scale);
      const recovered = dequantize(bt, scale);
      expect(Math.abs(recovered - v)).toBeLessThan(0.05);
    }
  });

  it('respects numTrits parameter', () => {
    const scale = 1.0;
    const numTrits = 4;
    const { bt } = quantize(5.0, scale, numTrits);
    expect(bt.trits.length).toBeLessThanOrEqual(numTrits + 1);
  });

  it('dequantize round-trips with same scale', () => {
    const scale = 3.0;
    const { bt } = quantize(2.5, scale);
    const recovered = dequantize(bt, scale);
    expect(Math.abs(recovered - 2.5)).toBeLessThan(0.05);
  });
});

describe('quantizeVector and dequantizeVector', () => {
  it('round-trips a simple vector with bounded error', () => {
    const vector = [1.0, 2.0, 3.0];
    const scale = 3.0;
    const tv = quantizeVector(vector, scale);
    const recovered = dequantizeVector(tv, scale);
    expect(recovered.length).toBe(vector.length);
    for (let i = 0; i < vector.length; i++) {
      expect(Math.abs(recovered[i] - vector[i])).toBeLessThan(0.05);
    }
  });

  it('round-trips a vector with per-component scales', () => {
    const vector = [0.5, 1.5, -2.0];
    const scales = [1.0, 2.0, 3.0];
    const tv = quantizeVector(vector, scales);
    const recovered = dequantizeVector(tv, scales);
    for (let i = 0; i < vector.length; i++) {
      expect(Math.abs(recovered[i] - vector[i])).toBeLessThan(0.05);
    }
  });

  it('TernaryVector has components, original, and quantizationError fields', () => {
    const vector = [1.0, -1.0, 0.5];
    const scale = 1.0;
    const tv = quantizeVector(vector, scale);
    expect(tv).toHaveProperty('components');
    expect(tv).toHaveProperty('original');
    expect(tv).toHaveProperty('quantizationError');
    expect(tv.original).toEqual(vector);
    expect(tv.components.length).toBe(vector.length);
    expect(typeof tv.quantizationError).toBe('number');
  });

  it('round-trips zero vector', () => {
    const vector = [0.0, 0.0, 0.0];
    const scale = 0.5;
    const tv = quantizeVector(vector, scale);
    const recovered = dequantizeVector(tv, scale);
    for (const val of recovered) {
      expect(Math.abs(val)).toBeLessThan(scale);
    }
  });

  it('round-trips negative values', () => {
    const vector = [-0.5, -1.0, -2.5];
    const scale = 3.0;
    const tv = quantizeVector(vector, scale);
    const recovered = dequantizeVector(tv, scale);
    for (let i = 0; i < vector.length; i++) {
      expect(Math.abs(recovered[i] - vector[i])).toBeLessThan(0.05);
    }
  });

  it('respects numTrits parameter per component', () => {
    const vector = [3.0, -3.0, 1.5];
    const scale = 0.5;
    const numTrits = 5;
    const tv = quantizeVector(vector, scale, numTrits);
    for (const component of tv.components) {
      expect(component.trits.length).toBeLessThanOrEqual(numTrits + 1);
    }
  });
});

describe('governanceToTrit', () => {
  it('maps ALLOW to 1', () => {
    expect(governanceToTrit('ALLOW')).toBe(1);
  });

  it('maps DENY to -1', () => {
    expect(governanceToTrit('DENY')).toBe(-1);
  });

  it('maps QUARANTINE to 0', () => {
    expect(governanceToTrit('QUARANTINE')).toBe(0);
  });

  it('maps ESCALATE to 0', () => {
    expect(governanceToTrit('ESCALATE')).toBe(0);
  });
});

describe('tritToGovernance', () => {
  it('maps 1 to ALLOW', () => {
    expect(tritToGovernance(1)).toBe('ALLOW');
  });

  it('maps -1 to DENY', () => {
    expect(tritToGovernance(-1)).toBe('DENY');
  });

  it('maps 0 to QUARANTINE', () => {
    expect(tritToGovernance(0)).toBe('QUARANTINE');
  });
});

describe('governanceToTrit / tritToGovernance round-trip', () => {
  it('ALLOW round-trips through trit', () => {
    const trit = governanceToTrit('ALLOW');
    expect(tritToGovernance(trit)).toBe('ALLOW');
  });

  it('DENY round-trips through trit', () => {
    const trit = governanceToTrit('DENY');
    expect(tritToGovernance(trit)).toBe('DENY');
  });

  it('QUARANTINE maps to 0 which maps back to QUARANTINE', () => {
    const trit = governanceToTrit('QUARANTINE');
    const decision = tritToGovernance(trit);
    expect(decision).toBe('QUARANTINE');
  });
});

describe('formatBalancedTernary', () => {
  it('formats [0] as "0"', () => {
    const bt = toBalancedTernary(0);
    const formatted = formatBalancedTernary(bt);
    expect(formatted).toBe('0');
  });

  it('formats [1] as "1"', () => {
    const bt = toBalancedTernary(1);
    const formatted = formatBalancedTernary(bt);
    expect(formatted).toBe('1');
  });

  it('formats [-1] as "T"', () => {
    const bt = toBalancedTernary(-1);
    const formatted = formatBalancedTernary(bt);
    expect(formatted).toBe('T');
  });

  it('formats [1, -1, 0] as "1T0"', () => {
    const bt = { trits: [1, -1, 0] as const, value: 6 };
    const formatted = formatBalancedTernary(bt);
    expect(formatted).toBe('1T0');
  });

  it('uses T for -1 trits and digits for 0 and 1', () => {
    const bt = toBalancedTernary(13);
    const formatted = formatBalancedTernary(bt);
    for (const ch of formatted) {
      expect(['0', '1', 'T']).toContain(ch);
    }
  });

  it('formats 2 as "1T" ([1, -1])', () => {
    const bt = toBalancedTernary(2);
    const formatted = formatBalancedTernary(bt);
    expect(formatted).toBe('1T');
  });

  it('formats 3 as "10" ([1, 0])', () => {
    const bt = toBalancedTernary(3);
    const formatted = formatBalancedTernary(bt);
    expect(formatted).toBe('10');
  });
});

describe('parseBalancedTernary', () => {
  it('parses "0" to value 0', () => {
    const bt = parseBalancedTernary('0');
    expect(bt.value).toBe(0);
    expect(bt.trits).toEqual([0]);
  });

  it('parses "1" to value 1', () => {
    const bt = parseBalancedTernary('1');
    expect(bt.value).toBe(1);
    expect(bt.trits).toEqual([1]);
  });

  it('parses "T" to value -1', () => {
    const bt = parseBalancedTernary('T');
    expect(bt.value).toBe(-1);
    expect(bt.trits).toEqual([-1]);
  });

  it('parses "1T0" to [1, -1, 0] with value 6', () => {
    const bt = parseBalancedTernary('1T0');
    expect(bt.trits).toEqual([1, -1, 0]);
    expect(bt.value).toBe(6);
  });

  it('parses "1T" to value 2', () => {
    const bt = parseBalancedTernary('1T');
    expect(bt.value).toBe(2);
    expect(bt.trits).toEqual([1, -1]);
  });

  it('parses "10" to value 3', () => {
    const bt = parseBalancedTernary('10');
    expect(bt.value).toBe(3);
    expect(bt.trits).toEqual([1, 0]);
  });

  it('round-trips with formatBalancedTernary for range -13..13', () => {
    for (let n = -13; n <= 13; n++) {
      const bt = toBalancedTernary(n);
      const formatted = formatBalancedTernary(bt);
      const parsed = parseBalancedTernary(formatted);
      expect(parsed.value).toBe(n);
    }
  });
});
