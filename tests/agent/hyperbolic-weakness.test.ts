import { describe, expect, it } from 'vitest';
import { detectGeometricWeakness, hyperbolicDistance } from '../../src/harmonic/hyperbolic.js';

describe('Hyperbolic geometric weakness probes', () => {
  it('flags non-finite coordinate injection', () => {
    const u = [NaN, 0.1, 0.2];
    const v = [0.2, 0.1, 0.0];
    const signal = detectGeometricWeakness(u, v);
    expect(signal.isWeak).toBe(true);
    expect(signal.kind).toBe('non_finite');
    expect(hyperbolicDistance(u, v)).toBe(Number.POSITIVE_INFINITY);
  });

  it('flags boundary saturation near poincare wall', () => {
    const u = [0.999999999, 0, 0];
    const v = [-0.999999999, 0, 0];
    const signal = detectGeometricWeakness(u, v);
    expect(signal.isWeak).toBe(true);
    expect(['boundary_saturation', 'denominator_collapse']).toContain(signal.kind);
    const d = hyperbolicDistance(u, v);
    expect(Number.isFinite(d) || d === Number.POSITIVE_INFINITY).toBe(true);
  });

  it('reports safe interior points as non-weak', () => {
    const u = [0.1, 0.2, 0.05];
    const v = [0.05, -0.2, 0.1];
    const signal = detectGeometricWeakness(u, v);
    expect(signal.kind).toBe('ok');
    expect(signal.isWeak).toBe(false);
    const d = hyperbolicDistance(u, v);
    expect(Number.isFinite(d)).toBe(true);
    expect(d).toBeGreaterThanOrEqual(0);
  });
});
