/**
 * @file tileLang.unit.test.ts
 * Kernel tile ↔ Sacred Tongue striping
 */

import { describe, expect, it } from 'vitest';
import {
  langAtTile,
  neighbourLangs,
  parseTileKey,
  tileKey,
  tileToVoxel6,
} from '../../packages/kernel/src/tileLang.js';
import { LANGS } from '../../packages/kernel/src/scbe_voxel_types.js';

describe('tileLang', () => {
  it('round-trips tileKey', () => {
    expect(parseTileKey(tileKey(3, -2))).toEqual({ row: 3, col: -2 });
    expect(parseTileKey('bad')).toBeNull();
  });

  it('langAtTile stays on LANGS and stripes diagonally', () => {
    expect(LANGS).toContain(langAtTile(0, 0));
    expect(langAtTile(0, 1)).toBe(LANGS[1 % LANGS.length]);
    expect(langAtTile(1, 0)).toBe(LANGS[1 % LANGS.length]);
    expect(langAtTile(6, 6)).toBe(langAtTile(0, 0));
  });

  it('tileToVoxel6 lifts row/col/layer', () => {
    expect(tileToVoxel6(7, 8, 2)).toEqual([7, 8, 2, 0, 0, 0]);
  });

  it('neighbourLangs returns four tongues', () => {
    expect(neighbourLangs(10, 10)).toHaveLength(4);
  });
});
