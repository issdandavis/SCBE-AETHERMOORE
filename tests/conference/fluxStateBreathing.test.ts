/**
 * @file fluxStateBreathing.test.ts
 * @module tests/conference
 *
 * Tests for L6 breathing + phase-lock dynamics added to fluxState.ts.
 * Validates backwards-compatibility, breathing modulation, and
 * ENTANGLED phase-lock gating.
 */

import { describe, it, expect } from 'vitest';
import {
  FluxStateGate,
  FluxState,
  breathingFactor,
  breathingAdjustedMaxStepNorm,
  phaseLockScore,
  circularDistanceRad,
} from '../../packages/kernel/src/fluxState';

describe('breathingFactor()', () => {
  it('is deterministic and clamped', () => {
    const b0 = breathingFactor(0, { amplitude: 0.9, min: 0.25, max: 2.5 });
    expect(b0).toBeGreaterThan(0);
    expect(b0).toBeLessThanOrEqual(2.5);
  });

  it('returns 1 at t=0 with default amplitude', () => {
    const b = breathingFactor(0, { amplitude: 0.25 });
    expect(b).toBeCloseTo(1, 6);
  });

  it('tightens maxStepNorm when b(t) > 1', () => {
    const base = 0.3;
    // At t=15 with omega=2π/60: sin(π/2) = 1, so b(t) = 1 + 0.5 = 1.5
    const eff = breathingAdjustedMaxStepNorm(base, 15, { amplitude: 0.5, omega: (2 * Math.PI) / 60 });
    expect(eff).toBeCloseTo(0.2, 5);
  });

  it('returns null for null base', () => {
    expect(breathingAdjustedMaxStepNorm(null, 10)).toBeNull();
  });
});

describe('circularDistanceRad()', () => {
  it('is 0 for identical angles', () => {
    expect(circularDistanceRad(1.5, 1.5)).toBeCloseTo(0, 8);
  });

  it('is π for opposite angles', () => {
    expect(circularDistanceRad(0, Math.PI)).toBeCloseTo(Math.PI, 8);
  });

  it('wraps around correctly', () => {
    // 0 and 2π should be 0 distance
    expect(circularDistanceRad(0, 2 * Math.PI)).toBeCloseTo(0, 8);
  });
});

describe('phaseLockScore()', () => {
  it('is 1 for identical phase', () => {
    expect(phaseLockScore(0, 0)).toBeCloseTo(1, 8);
  });

  it('is ~0 for opposite phase', () => {
    expect(phaseLockScore(0, Math.PI)).toBeCloseTo(0, 8);
  });

  it('is ~0.5 for 90° offset', () => {
    expect(phaseLockScore(0, Math.PI / 2)).toBeCloseTo(0.5, 8);
  });
});

describe('FluxStateGate.checkNavigation(ctx) — backwards compatibility', () => {
  it('preserves old behavior when ctx omitted', () => {
    const gate = new FluxStateGate(FluxState.SUPERPOSITION);
    const step = [0.01, 0.0, 0.0, 0.0, 0.0, 0.0];
    const r1 = gate.checkNavigation('KO', step);
    const r2 = gate.checkNavigation('KO', step, undefined);
    expect(r1.allowed).toBe(r2.allowed);
    expect(r1.allowed).toBe(true);
  });

  it('still denies realm access as before', () => {
    const gate = new FluxStateGate(FluxState.SUPERPOSITION);
    const step = [0.01, 0.0, 0.0, 0.0, 0.0, 0.0];
    // SUPERPOSITION only allows KO, AV, RU
    const result = gate.checkNavigation('UM', step);
    expect(result.allowed).toBe(false);
  });
});

describe('FluxStateGate.checkNavigation(ctx) — breathing modulation', () => {
  it('tightens step norm during expansion', () => {
    const gate = new FluxStateGate(FluxState.SUPERPOSITION);
    // SUPERPOSITION maxStepNorm = 0.3
    // At b(t)=1.5, effective max = 0.2
    // Step of norm 0.25 should fail (0.25 > 0.2)
    const step = [0.25, 0.0, 0.0, 0.0, 0.0, 0.0];
    const result = gate.checkNavigation('KO', step, {
      tSec: 15,
      breathing: { amplitude: 0.5, omega: (2 * Math.PI) / 60 },
    });
    expect(result.allowed).toBe(false);
    expect(result.reason).toContain('exceeds max');
  });

  it('allows same step when breathing is relaxed', () => {
    const gate = new FluxStateGate(FluxState.SUPERPOSITION);
    // At t=0, b(t)=1, so effective max = 0.3
    // Step of norm 0.25 should pass
    const step = [0.25, 0.0, 0.0, 0.0, 0.0, 0.0];
    const result = gate.checkNavigation('KO', step, {
      tSec: 0,
      breathing: { amplitude: 0.5, omega: (2 * Math.PI) / 60 },
    });
    expect(result.allowed).toBe(true);
  });
});

describe('FluxStateGate.checkNavigation(ctx) — ENTANGLED phase-lock', () => {
  it('denies navigation when not phase-locked', () => {
    const gate = new FluxStateGate(FluxState.ENTANGLED, 'partner-1');
    const step = [0.01, 0.0, 0.0, 0.0, 0.0, 0.0];

    const result = gate.checkNavigation('KO', step, {
      tSec: 0,
      phase: { selfTheta: 0, partnerTheta: Math.PI, lockThreshold: 0.8 },
    });
    expect(result.allowed).toBe(false);
    expect(result.reason).toContain('not permitted');
  });

  it('allows navigation when phase-locked', () => {
    const gate = new FluxStateGate(FluxState.ENTANGLED, 'partner-1');
    const step = [0.01, 0.0, 0.0, 0.0, 0.0, 0.0];

    const result = gate.checkNavigation('KO', step, {
      tSec: 0,
      phase: { selfTheta: 0, partnerTheta: 0.1, lockThreshold: 0.8 },
    });
    expect(result.allowed).toBe(true);
  });

  it('does not affect non-ENTANGLED states', () => {
    const gate = new FluxStateGate(FluxState.SUPERPOSITION);
    const step = [0.01, 0.0, 0.0, 0.0, 0.0, 0.0];

    // Even with unlocked phase context, SUPERPOSITION ignores it
    const result = gate.checkNavigation('KO', step, {
      tSec: 0,
      phase: { selfTheta: 0, partnerTheta: Math.PI, lockThreshold: 0.8 },
    });
    expect(result.allowed).toBe(true);
  });
});
