import { describe, expect, it } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';
import {
  mobiusAdd,
  exponentialMap,
  logarithmicMap,
} from '../../src/harmonic/hyperbolic.js';
import { harmonicScalePhi } from '../../packages/kernel/src/harmonicScaling.js';

const FIXTURE_DIR = path.resolve(__dirname, '../interop/polyglot_vectors');

function loadFixture<T>(name: string): T {
  return JSON.parse(fs.readFileSync(path.join(FIXTURE_DIR, name), 'utf-8')) as T;
}

function expectVectorClose(actual: number[], expected: number[]): void {
  expect(actual.length).toBe(expected.length);
  for (let i = 0; i < expected.length; i++) {
    expect(actual[i]).toBeCloseTo(expected[i], 12);
  }
}

type MobiusFixture = {
  version: string;
  metric: string;
  cases: { id: string; u: number[]; v: number[]; expected: number[] }[];
};

type MapFixture = {
  version: string;
  metric: string;
  cases: { id: string; p: number[]; v?: number[]; q?: number[]; expected: number[] }[];
};

type WallFixture = {
  version: string;
  metric: string;
  phi: number;
  cases: { id: string; d: number; pd: number; expected: number }[];
};

describe('Polyglot vectors: mobius addition', () => {
  const fixture = loadFixture<MobiusFixture>('mobius_addition.v1.json');

  it('loads expected fixture metadata', () => {
    expect(fixture.metric).toBe('mobius_addition');
    expect(fixture.version).toBe('1.0.0');
    expect(fixture.cases.length).toBeGreaterThan(0);
  });

  for (const entry of fixture.cases) {
    it(`matches fixture ${entry.id}`, () => {
      const actual = mobiusAdd(entry.u, entry.v);
      expectVectorClose(actual, entry.expected);
    });
  }
});

describe('Polyglot vectors: exponential map', () => {
  const fixture = loadFixture<MapFixture>('exponential_map.v1.json');

  it('loads expected fixture metadata', () => {
    expect(fixture.metric).toBe('exponential_map');
    expect(fixture.version).toBe('1.0.0');
    expect(fixture.cases.length).toBeGreaterThan(0);
  });

  for (const entry of fixture.cases) {
    it(`matches fixture ${entry.id}`, () => {
      const actual = exponentialMap(entry.p, entry.v as number[]);
      expectVectorClose(actual, entry.expected);
    });
  }
});

describe('Polyglot vectors: logarithmic map', () => {
  const fixture = loadFixture<MapFixture>('logarithmic_map.v1.json');

  it('loads expected fixture metadata', () => {
    expect(fixture.metric).toBe('logarithmic_map');
    expect(fixture.version).toBe('1.0.0');
    expect(fixture.cases.length).toBeGreaterThan(0);
  });

  for (const entry of fixture.cases) {
    it(`matches fixture ${entry.id}`, () => {
      const actual = logarithmicMap(entry.p, entry.q as number[]);
      expectVectorClose(actual, entry.expected);
    });
  }
});

describe('Polyglot vectors: harmonic wall (phi-weighted)', () => {
  const fixture = loadFixture<WallFixture>('harmonic_wall.v1.json');
  const PHI = (1 + Math.sqrt(5)) / 2;

  it('loads expected fixture metadata', () => {
    expect(fixture.metric).toBe('harmonic_wall_phi');
    expect(fixture.version).toBe('1.0.0');
    expect(fixture.phi).toBeCloseTo(PHI, 15);
    expect(fixture.cases.length).toBeGreaterThan(0);
  });

  for (const entry of fixture.cases) {
    it(`matches fixture ${entry.id}`, () => {
      const actual = harmonicScalePhi(entry.d, entry.pd);
      expect(actual).toBeCloseTo(entry.expected, 12);
    });
  }
});
