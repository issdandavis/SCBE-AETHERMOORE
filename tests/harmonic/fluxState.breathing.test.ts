/**
 * @file fluxState.breathing.test.ts
 * @description Tests for L6 breathing modulation and G6 phase-lock gating.
 *
 * Three invariants tested:
 * 1. Backwards-compatibility: ctx omitted -> old behavior unchanged
 * 2. Breathing modulation: b(t) deterministically tightens/relaxes maxStepNorm
 * 3. Phase-lock gating: unlocked ENTANGLED pairs -> observe-only (navigation denied)
 */

import { describe, it, expect } from 'vitest';
import {
  FluxState,
  FluxStateGate,
  breathingFactor,
  breathingAdjustedMaxStepNorm,
  phaseLockScore,
  circularDistanceRad,
  type FluxDynamicsContext,
} from '../../src/harmonic/fluxState';

// ═══════════════════════════════════════════════════════════════
// breathingFactor()
// ═══════════════════════════════════════════════════════════════

describe('breathingFactor', () => {
  it('should return 1.0 at t=0 (sin(0)=0)', () => {
    const b = breathingFactor(0, { amplitude: 0.5 });
    expect(b).toBeCloseTo(1.0, 8);
  });

  it('should be deterministic for same inputs', () => {
    const b1 = breathingFactor(42.7, { amplitude: 0.3, omega: 1.5 });
    const b2 = breathingFactor(42.7, { amplitude: 0.3, omega: 1.5 });
    expect(b1).toBe(b2);
  });

  it('should clamp to [min, max]', () => {
    // With amplitude near 1, b can reach ~2 or ~0 — clamp should catch it
    const bHigh = breathingFactor(Math.PI / 2, { amplitude: 0.9, omega: 1.0, min: 0.25, max: 2.5 });
    expect(bHigh).toBeGreaterThanOrEqual(0.25);
    expect(bHigh).toBeLessThanOrEqual(2.5);

    const bLow = breathingFactor((3 * Math.PI) / 2, { amplitude: 0.9, omega: 1.0, min: 0.25, max: 2.5 });
    expect(bLow).toBeGreaterThanOrEqual(0.25);
    expect(bLow).toBeLessThanOrEqual(2.5);
  });

  it('should use defaults when no params given', () => {
    const b = breathingFactor(0);
    expect(b).toBeCloseTo(1.0, 8);
  });

  it('should tighten (b>1) at expansion phase', () => {
    // omega = 2*PI/60, at t=15: sin(PI/2) = 1
    const b = breathingFactor(15, { amplitude: 0.5, omega: (2 * Math.PI) / 60 });
    expect(b).toBeCloseTo(1.5, 6);
  });

  it('should relax (b<1) at contraction phase', () => {
    // omega = 2*PI/60, at t=45: sin(3*PI/2) = -1
    const b = breathingFactor(45, { amplitude: 0.5, omega: (2 * Math.PI) / 60 });
    expect(b).toBeCloseTo(0.5, 6);
  });
});

// ═══════════════════════════════════════════════════════════════
// breathingAdjustedMaxStepNorm()
// ═══════════════════════════════════════════════════════════════

describe('breathingAdjustedMaxStepNorm', () => {
  it('should return null for null base', () => {
    expect(breathingAdjustedMaxStepNorm(null, 10)).toBeNull();
  });

  it('should tighten maxStepNorm when b(t) > 1', () => {
    const base = 0.3;
    // At t=15 with omega=2*PI/60, amplitude=0.5: b=1.5, effective=0.2
    const eff = breathingAdjustedMaxStepNorm(base, 15, { amplitude: 0.5, omega: (2 * Math.PI) / 60 });
    expect(eff).toBeCloseTo(0.2, 6);
  });

  it('should relax maxStepNorm when b(t) < 1', () => {
    const base = 0.3;
    // At t=45 with omega=2*PI/60, amplitude=0.5: b=0.5, effective=0.6
    const eff = breathingAdjustedMaxStepNorm(base, 45, { amplitude: 0.5, omega: (2 * Math.PI) / 60 });
    expect(eff).toBeCloseTo(0.6, 6);
  });

  it('should leave maxStepNorm unchanged when b(t)=1', () => {
    const base = 0.3;
    const eff = breathingAdjustedMaxStepNorm(base, 0, { amplitude: 0.5 });
    expect(eff).toBeCloseTo(0.3, 8);
  });
});

// ═══════════════════════════════════════════════════════════════
// circularDistanceRad() and phaseLockScore()
// ═══════════════════════════════════════════════════════════════

describe('circularDistanceRad', () => {
  it('should return 0 for identical angles', () => {
    expect(circularDistanceRad(0, 0)).toBeCloseTo(0, 10);
    expect(circularDistanceRad(1.5, 1.5)).toBeCloseTo(0, 10);
  });

  it('should return PI for opposite angles', () => {
    expect(circularDistanceRad(0, Math.PI)).toBeCloseTo(Math.PI, 10);
    expect(circularDistanceRad(Math.PI, 0)).toBeCloseTo(Math.PI, 10);
  });

  it('should handle wraparound', () => {
    // 0 and 2*PI are the same angle
    expect(circularDistanceRad(0, 2 * Math.PI)).toBeCloseTo(0, 8);
    // Small distance across 0/2PI boundary
    expect(circularDistanceRad(0.1, 2 * Math.PI - 0.1)).toBeCloseTo(0.2, 8);
  });

  it('should always return a value in [0, PI]', () => {
    for (let a = 0; a < 2 * Math.PI; a += 0.3) {
      for (let b = 0; b < 2 * Math.PI; b += 0.3) {
        const d = circularDistanceRad(a, b);
        expect(d).toBeGreaterThanOrEqual(-1e-10);
        expect(d).toBeLessThanOrEqual(Math.PI + 1e-10);
      }
    }
  });
});

describe('phaseLockScore', () => {
  it('should be 1 for identical phase', () => {
    expect(phaseLockScore(0, 0)).toBeCloseTo(1, 8);
    expect(phaseLockScore(2.0, 2.0)).toBeCloseTo(1, 8);
  });

  it('should be ~0 for opposite phase (PI apart)', () => {
    expect(phaseLockScore(0, Math.PI)).toBeCloseTo(0, 8);
    expect(phaseLockScore(Math.PI, 0)).toBeCloseTo(0, 8);
  });

  it('should be ~0.5 for 90-degree offset', () => {
    expect(phaseLockScore(0, Math.PI / 2)).toBeCloseTo(0.5, 8);
  });

  it('should always return a value in [0, 1]', () => {
    for (let a = 0; a < 2 * Math.PI; a += 0.3) {
      for (let b = 0; b < 2 * Math.PI; b += 0.3) {
        const s = phaseLockScore(a, b);
        expect(s).toBeGreaterThanOrEqual(-1e-10);
        expect(s).toBeLessThanOrEqual(1 + 1e-10);
      }
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// FluxStateGate.checkNavigation(ctx) — Backwards Compatibility
// ═══════════════════════════════════════════════════════════════

describe('FluxStateGate with FluxDynamicsContext', () => {
  describe('backwards compatibility', () => {
    it('should behave identically when ctx is omitted', () => {
      const gate = new FluxStateGate(FluxState.SUPERPOSITION);
      const step = [0.1, 0, 0, 0, 0, 0];

      const r1 = gate.checkNavigation('KO', step);
      const r2 = gate.checkNavigation('KO', step, undefined);

      expect(r1.allowed).toBe(r2.allowed);
    });

    it('should behave identically when ctx is empty object', () => {
      const gate = new FluxStateGate(FluxState.SUPERPOSITION);
      const step = [0.1, 0, 0, 0, 0, 0];

      const r1 = gate.checkNavigation('KO', step);
      const r2 = gate.checkNavigation('KO', step, {});

      expect(r1.allowed).toBe(r2.allowed);
    });

    it('POLLY with no ctx should still allow everything', () => {
      const gate = new FluxStateGate(FluxState.POLLY);
      const r = gate.checkNavigation('DR', [0.9, 0, 0, 0, 0, 0]);
      expect(r.allowed).toBe(true);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Breathing Modulation
  // ═══════════════════════════════════════════════════════════════

  describe('L6 breathing modulation', () => {
    it('should tighten SUPERPOSITION maxStepNorm at expansion', () => {
      const gate = new FluxStateGate(FluxState.SUPERPOSITION);
      // Base maxStepNorm = 0.3. At b(t)=1.5, effective = 0.2
      const ctx: FluxDynamicsContext = {
        tSec: 15,
        breathing: { amplitude: 0.5, omega: (2 * Math.PI) / 60 },
      };

      // Step of 0.25 should exceed effective 0.2
      const r = gate.checkNavigation('KO', [0.25, 0, 0, 0, 0, 0], ctx);
      expect(r.allowed).toBe(false);
      expect(r.reason).toContain('magnitude');
    });

    it('should relax SUPERPOSITION maxStepNorm at contraction', () => {
      const gate = new FluxStateGate(FluxState.SUPERPOSITION);
      // Base maxStepNorm = 0.3. At b(t)=0.5, effective = 0.6
      const ctx: FluxDynamicsContext = {
        tSec: 45,
        breathing: { amplitude: 0.5, omega: (2 * Math.PI) / 60 },
      };

      // Step of 0.5 should now pass (< 0.6)
      const r = gate.checkNavigation('KO', [0.5, 0, 0, 0, 0, 0], ctx);
      expect(r.allowed).toBe(true);
    });

    it('should not affect POLLY (null maxStepNorm stays null)', () => {
      const gate = new FluxStateGate(FluxState.POLLY);
      const ctx: FluxDynamicsContext = {
        tSec: 15,
        breathing: { amplitude: 0.9 },
      };

      const r = gate.checkNavigation('DR', [999, 0, 0, 0, 0, 0], ctx);
      expect(r.allowed).toBe(true);
    });

    it('should return effective policy in result', () => {
      const gate = new FluxStateGate(FluxState.SUPERPOSITION);
      const ctx: FluxDynamicsContext = {
        tSec: 15,
        breathing: { amplitude: 0.5, omega: (2 * Math.PI) / 60 },
      };

      const r = gate.checkNavigation('KO', [0.1, 0, 0, 0, 0, 0], ctx);
      expect(r.policy.maxStepNorm).toBeCloseTo(0.2, 6);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // G6 Phase-Lock Gating (ENTANGLED)
  // ═══════════════════════════════════════════════════════════════

  describe('G6 phase-lock gating (ENTANGLED)', () => {
    it('should deny ENTANGLED navigation when phases are opposite (unlocked)', () => {
      const gate = new FluxStateGate(FluxState.ENTANGLED, 'partner-1');
      const step = [0.05, 0, 0, 0, 0, 0];

      const ctx: FluxDynamicsContext = {
        tSec: 0,
        phase: { selfTheta: 0, partnerTheta: Math.PI, lockThreshold: 0.8 },
      };

      const r = gate.checkNavigation('KO', step, ctx);
      expect(r.allowed).toBe(false);
      expect(r.reason).toContain('not permitted');
    });

    it('should allow ENTANGLED navigation when phases are close (locked)', () => {
      const gate = new FluxStateGate(FluxState.ENTANGLED, 'partner-1');
      const step = [0.05, 0, 0, 0, 0, 0];

      const ctx: FluxDynamicsContext = {
        tSec: 0,
        phase: { selfTheta: 0, partnerTheta: 0.1, lockThreshold: 0.8 },
      };

      const r = gate.checkNavigation('KO', step, ctx);
      expect(r.allowed).toBe(true);
    });

    it('should not affect non-ENTANGLED states even with phase context', () => {
      const gate = new FluxStateGate(FluxState.SUPERPOSITION);
      const step = [0.1, 0, 0, 0, 0, 0];

      const ctx: FluxDynamicsContext = {
        tSec: 0,
        phase: { selfTheta: 0, partnerTheta: Math.PI, lockThreshold: 0.8 },
      };

      // SUPERPOSITION allows KO — phase-lock should NOT affect this
      const r = gate.checkNavigation('KO', step, ctx);
      expect(r.allowed).toBe(true);
    });

    it('should respect custom lockThreshold', () => {
      const gate = new FluxStateGate(FluxState.ENTANGLED, 'partner-1');
      const step = [0.05, 0, 0, 0, 0, 0];

      // Score is ~0.68 for PI/2 offset. With threshold 0.5 it should pass.
      const ctx: FluxDynamicsContext = {
        tSec: 0,
        phase: { selfTheta: 0, partnerTheta: Math.PI / 2, lockThreshold: 0.5 },
      };

      const r = gate.checkNavigation('KO', step, ctx);
      expect(r.allowed).toBe(true);
    });

    it('should honor unlockDisablesNavigation=false', () => {
      const gate = new FluxStateGate(FluxState.ENTANGLED, 'partner-1');
      const step = [0.05, 0, 0, 0, 0, 0];

      const ctx: FluxDynamicsContext = {
        tSec: 0,
        phase: {
          selfTheta: 0,
          partnerTheta: Math.PI,
          lockThreshold: 0.8,
          unlockDisablesNavigation: false,
        },
      };

      // Even though unlocked, navigation should still be allowed
      const r = gate.checkNavigation('KO', step, ctx);
      expect(r.allowed).toBe(true);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Combined: Breathing + Phase-Lock
  // ═══════════════════════════════════════════════════════════════

  describe('combined breathing + phase-lock', () => {
    it('should apply both breathing and phase-lock together', () => {
      const gate = new FluxStateGate(FluxState.ENTANGLED, 'partner-1');

      const ctx: FluxDynamicsContext = {
        tSec: 15,
        breathing: { amplitude: 0.5, omega: (2 * Math.PI) / 60 },
        phase: { selfTheta: 0, partnerTheta: 0.05, lockThreshold: 0.8 },
      };

      // Locked (close phases) + breathing tightens step norm
      // ENTANGLED base maxStepNorm = 0.2. At b=1.5, effective ~= 0.133
      const step = [0.1, 0, 0, 0, 0, 0]; // norm = 0.1, should pass
      const r = gate.checkNavigation('KO', step, ctx);
      expect(r.allowed).toBe(true);
      expect(r.policy.maxStepNorm).not.toBeNull();
      expect(r.policy.maxStepNorm!).toBeLessThan(0.2);
    });
  });
});
