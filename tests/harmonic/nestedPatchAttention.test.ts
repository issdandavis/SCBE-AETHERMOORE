import { describe, expect, it } from 'vitest';
import {
  dressPatchForModels,
  placementRadius,
  type ViewToken,
} from '../../src/harmonic/nestedPatchAttention';
import { layer4PoincareEmbedding } from '../../src/harmonic/pipeline14';

function token(views: number[]): ViewToken {
  return { views };
}

function norm(point: number[]): number {
  return Math.hypot(...point);
}

describe('nested patch attention', () => {
  it('dresses one token through all 14 layers and six scatter points', () => {
    const dressed = dressPatchForModels([token([1, 0, 0, 0, 0, 0])]);
    const region = dressed.regions[0];
    const layers = region.dressed.layers;

    expect(dressed.tokenCount).toBe(1);
    expect(dressed.spanDistance).toBe(0);
    expect(region.scatter).toHaveLength(6);
    expect(norm(region.center)).toBeLessThan(1);
    expect(region.scatter.every((point) => norm(point) < 1)).toBe(true);
    expect(layers.l1_complex.real).toHaveLength(6);
    expect(layers.l4_poincare.length).toBeGreaterThan(0);
    expect(Number.isFinite(layers.l5_distance)).toBe(true);
    expect(layers.l13_decision).toMatch(/ALLOW|QUARANTINE|DENY/);
    expect(Number.isFinite(layers.l14_audio)).toBe(true);
    expect(dressed.attention[0].weights).toEqual([1]);
  });

  it('keeps attention width equal to the patch, with no shared fixed length', () => {
    const short = dressPatchForModels([
      token([1, 0, 0, 0, 0, 0]),
      token([0, 1, 0, 0, 0, 0]),
      token([0, 0, 1, 0, 0, 0]),
    ]);
    const flat = Array.from({ length: 8 }, () => token([0.2, 0.2, 0.2, 0.2, 0.2, 0.2]));
    const long = dressPatchForModels(flat);

    expect(short.attention[0].weights).toHaveLength(3);
    expect(long.attention[0].weights).toHaveLength(8);
    expect(long.regions).toHaveLength(1);
    expect(short.attention[0].weights.reduce((sum, weight) => sum + weight, 0)).toBeCloseTo(1);
  });

  it('nests a long patch at a density break and sorts dense regions inward', () => {
    const low = token([0.1, 0, 0, 0, 0, 0]);
    const high = token([4, 0, 0, 0, 0, 0]);
    const dressed = dressPatchForModels([low, low, low, low, high, high, high, high]);
    const blockRows = dressed.attention.filter((row) => row.scope === 'block');

    expect(blockRows).toHaveLength(1);
    expect(blockRows[0].keys).toHaveLength(2);
    expect(dressed.regions.map((region) => region.density)).toEqual(
      [...dressed.regions.map((region) => region.density)].sort((a, b) => b - a)
    );
    expect(norm(dressed.regions[0].center)).toBeLessThan(
      norm(dressed.regions[dressed.regions.length - 1].center)
    );
    expect(placementRadius(0, 3)).toBeLessThan(placementRadius(2, 3));
    expect(dressed.spanDistance).toBeGreaterThan(0);
  });

  it('places the densest preimage through the existing Layer 4 map', () => {
    const views = [1, 0, 0, 0, 0, 0];
    const radius = placementRadius(0, 1);
    const expected = layer4PoincareEmbedding(
      views.map((value) => value * radius),
      1,
      0.01
    );
    const dressed = dressPatchForModels([token(views)]);

    expect(dressed.regions[0].center).toEqual(expected);
  });
});
