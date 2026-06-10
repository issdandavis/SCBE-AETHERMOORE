import { describe, expect, it } from 'vitest';
import {
  decode,
  decodeByte,
  encode,
  encodeByte,
  TONGUES,
  type TongueCode,
} from '../../src/tokenizer/ss1.js';

const TONGUE_CODES = Object.keys(TONGUES) as TongueCode[];

describe('SS1 patent support invariants', () => {
  it('maps every byte to exactly one token per tongue and back again', () => {
    for (const tongue of TONGUE_CODES) {
      const tokens = new Set<string>();

      for (let byte = 0; byte <= 255; byte += 1) {
        const token = encodeByte(byte, tongue);
        tokens.add(token);
        expect(decodeByte(token, tongue)).toBe(byte);
      }

      expect(tokens.size).toBe(256);
    }
  });

  it('keeps serialized token vocabularies disjoint across semantic axes', () => {
    const tokenToTongue = new Map<string, TongueCode>();

    for (const tongue of TONGUE_CODES) {
      for (let byte = 0; byte <= 255; byte += 1) {
        const token = encode(Buffer.from([byte]), tongue);
        const priorTongue = tokenToTongue.get(token);

        expect(priorTongue).toBeUndefined();
        tokenToTongue.set(token, tongue);
        expect(decode(token)).toEqual(Buffer.from([byte]));
      }
    }

    expect(tokenToTongue.size).toBe(TONGUE_CODES.length * 256);
  });

  it('uses uniformly spaced sixty-degree phase offsets for the six tongues', () => {
    const sortedOffsets = TONGUE_CODES.map((tongue) => TONGUES[tongue].phaseOffset).sort(
      (a, b) => a - b
    );

    expect(sortedOffsets).toEqual([0, 60, 120, 180, 240, 300]);
  });
});
