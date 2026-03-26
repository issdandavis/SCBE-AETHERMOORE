/**
 * Setup Verification Test
 *
 * Verifies that the enterprise quantum testing infrastructure is properly
 * configured: TestConfig thresholds are sane, fast-check runs property tests,
 * and core pipeline modules are importable.
 */

import fc from 'fast-check';
import { describe, expect, it } from 'vitest';
import { TestConfig } from '../test.config';
import { hyperbolicDistance } from '../../../src/harmonic/hyperbolic';
import { harmonicScale } from '../../../src/harmonic/harmonicScaling';

describe('Enterprise Quantum Testing Infrastructure Setup', () => {
  it('should have quantum test config with valid thresholds', () => {
    expect(TestConfig.quantum.targetSecurityBits).toBeGreaterThanOrEqual(128);
    expect(TestConfig.quantum.maxQubits).toBeGreaterThan(0);
    expect(TestConfig.quantum.algorithms.shor.enabled).toBe(true);
    expect(TestConfig.quantum.algorithms.grover.enabled).toBe(true);
  });

  it('should have property-test iterations configured above minimum', () => {
    expect(TestConfig.propertyTests.minIterations).toBeGreaterThanOrEqual(100);
    expect(TestConfig.propertyTests.maxIterations).toBeGreaterThan(
      TestConfig.propertyTests.minIterations
    );
  });

  it('should compute Poincare distance for valid ball points', () => {
    const d = hyperbolicDistance([0, 0], [0.5, 0]);
    expect(d).toBeGreaterThan(0);
    expect(Number.isFinite(d)).toBe(true);
  });

  it('should produce bounded harmonic wall scores', () => {
    fc.assert(
      fc.property(
        fc.float({ min: 0, max: 10, noNaN: true }),
        fc.float({ min: 0, max: 1, noNaN: true }),
        (distance, pDrift) => {
          const score = harmonicScale(distance, pDrift);
          return score > 0 && score <= 1 && Number.isFinite(score);
        }
      ),
      { numRuns: TestConfig.propertyTests.minIterations }
    );
  });

  it('should enforce distance monotonicity: farther points get lower wall scores', () => {
    const near = harmonicScale(0.1, 0);
    const far = harmonicScale(5.0, 0);
    expect(near).toBeGreaterThan(far);
  });
});
