import { describe, expect, it } from 'vitest';
import * as source from '../../src/harmonic/hyperbolic.js';
import * as kernel from '../../packages/kernel/src/hyperbolic.js';

for (const [name, api] of Object.entries({ source, kernel })) {
  describe(`${name} positive radial breathing`, () => {
    it('preserves tiny nonzero points and round-trips across both cycle halves', () => {
      for (const radius of [0, 1e-14, 0.01, 0.4, 0.9]) {
        for (const t of [0, Math.PI / 2, Math.PI, (3 * Math.PI) / 2]) {
          const p = [radius, 0, 0];
          const moved = api.breathTransform(p, t);
          if (radius > 0) expect(moved[0]).toBeGreaterThan(0);
          expect(Math.hypot(...moved)).toBeLessThan(1);
          const inverse = api.inverseBreathTransform(moved, t);
          inverse.forEach((v, i) => expect(v).toBeCloseTo(p[i], 12));
        }
      }
    });
    it('has identity at neutral phase and never reverses the radial order', () => {
      expect(api.breathTransform([0.4, 0], 0)[0]).toBeCloseTo(0.4, 12);
      for (const t of [Math.PI / 2, (3 * Math.PI) / 2]) {
        expect(api.breathTransform([0.01, 0], t)[0]).toBeLessThan(
          api.breathTransform([0.02, 0], t)[0]
        );
      }
    });
    it('rejects missing, sparse, nonfinite and boundary inputs', () => {
      const sparse = [0.1, 0];
      delete sparse[1];
      for (const p of [[], sparse, [NaN, 0], [Infinity, 0], [1, 0], [2, 0]]) {
        expect(() => api.breathTransform(p, 0)).toThrow();
        expect(() => api.inverseBreathTransform(p, 0)).toThrow();
      }
      expect(() => api.breathTransform([0.2, 0], NaN)).toThrow();
    });
  });
}
