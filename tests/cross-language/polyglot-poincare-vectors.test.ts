import { describe, expect, it } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';
import { hyperbolicDistance } from '../../src/harmonic/hyperbolic.js';

type VectorCase = {
  id: string;
  u: number[];
  v: number[];
  expected: number;
};

type VectorFile = {
  version: string;
  metric: string;
  cases: VectorCase[];
};

function loadVectors(): VectorFile {
  const vectorPath = path.resolve(
    __dirname,
    '../interop/polyglot_vectors/poincare_distance.v1.json'
  );
  const raw = fs.readFileSync(vectorPath, 'utf-8');
  return JSON.parse(raw) as VectorFile;
}

describe('Polyglot vectors: poincare distance', () => {
  const vectors = loadVectors();

  it('loads the expected fixture metadata', () => {
    expect(vectors.metric).toBe('poincare_distance');
    expect(vectors.version).toBe('1.0.0');
    expect(vectors.cases.length).toBeGreaterThan(0);
  });

  for (const entry of vectors.cases) {
    it(`matches fixture ${entry.id}`, () => {
      const actual = hyperbolicDistance(entry.u, entry.v);
      expect(actual).toBeCloseTo(entry.expected, 12);
    });
  }
});
