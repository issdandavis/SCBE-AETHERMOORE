import { describe, expect, it } from 'vitest';
import { layer3WeightedTransform } from '../../packages/kernel/src/pipeline14';

function rootFromAction(metric: number[][]): number[][] {
  const n = metric.length;
  const columns = Array.from({ length: n }, (_, column) => {
    const basis = new Array(n).fill(0);
    basis[column] = 1;
    return layer3WeightedTransform(basis, metric);
  });
  return Array.from({ length: n }, (_, row) => columns.map((column) => column[row]));
}

function multiply(left: number[][], right: number[][]): number[][] {
  return left.map((row) =>
    right[0].map((_, column) => row.reduce((sum, value, k) => sum + value * right[k][column], 0))
  );
}

describe('Layer 3 canonical SPD matrix square root', () => {
  it('reconstructs supplied SPD metrics', () => {
    const metrics = [
      [
        [2, 1],
        [1, 2],
      ],
      [
        [4, 1, 0.5],
        [1, 3, 0.25],
        [0.5, 0.25, 2],
      ],
      [
        [9, 0, 0],
        [0, 4, 0],
        [0, 0, 1],
      ],
    ];
    for (const metric of metrics) {
      const squareRoot = rootFromAction(metric);
      const reconstructed = multiply(squareRoot, squareRoot);
      for (let i = 0; i < metric.length; i++) {
        for (let j = 0; j < metric.length; j++) {
          expect(reconstructed[i][j]).toBeCloseTo(metric[i][j], 10);
        }
      }
    }
  });

  it('preserves the metric quadratic form', () => {
    const metric = [
      [2, 1],
      [1, 2],
    ];
    const vector = [1.3, -0.7];
    const transformed = layer3WeightedTransform(vector, metric);
    const transformedNorm = transformed.reduce((sum, value) => sum + value * value, 0);
    const quadratic = vector.reduce(
      (sum, value, i) =>
        sum + value * metric[i].reduce((inner, item, j) => inner + item * vector[j], 0),
      0
    );
    expect(transformedNorm).toBeCloseTo(quadratic, 11);
  });

  it.each([
    [
      [
        [1, 2],
        [0, 1],
      ],
      [1, 2],
    ],
    [
      [
        [1, 0],
        [0, -1],
      ],
      [1, 2],
    ],
    [
      [
        [1, 0, 0],
        [0, 1, 0],
      ],
      [1, 2],
    ],
    [
      [
        [1, Number.NaN],
        [Number.NaN, 1],
      ],
      [1, 2],
    ],
  ])('rejects matrices outside the declared SPD domain', (metric, vector) => {
    expect(() => layer3WeightedTransform(vector, metric)).toThrow();
  });
});
