/**
 * Tests for dual-regime harmonic scaling (patrol + wall + braided).
 *
 * Validates:
 *   A. Patrol formula properties (constant sensitivity, baseline at R)
 *   B. Wall formula properties (superexponential, identity at 0)
 *   C. Crossover distance computation
 *   D. Regime classification
 *   E. Dual-regime unified scaling
 *   F. Blended smooth transition
 *   G. Tongue-weighted braided scaling
 *   H. Risk decision thresholds
 *   I. Weight system differences (LWS vs PHDM)
 *   J. Drift velocity modulation
 *   K. Mathematical invariants (property-based)
 *   L. Edge cases and boundary conditions
 */

import { describe, it, expect } from 'vitest';
import {
  patrolScale,
  patrolSensitivity,
  patrolAmplify,
  wallScale,
  wallSensitivity,
  wallAmplify,
  crossoverDistance,
  activeRegime,
  dualRegimeScale,
  blendedScale,
  blendedAmplify,
  braidedScale,
  LWS_WEIGHTS,
  PHDM_WEIGHTS,
  R_DEFAULT,
  R_FIFTH,
  type TongueDrift,
  type TongueCode,
} from '../../src/harmonic/dualRegimeScaling.js';

const PHI = (1 + Math.sqrt(5)) / 2;
const EPSILON = 1e-6;

// ─── A. Patrol Formula Properties ───────────────────────────

describe('A. Patrol formula', () => {
  it('A1: H_p(0, R) = R (baseline is always "on watch")', () => {
    expect(patrolScale(0)).toBeCloseTo(Math.E, 6);
    expect(patrolScale(0, 1.5)).toBeCloseTo(1.5, 6);
    expect(patrolScale(0, 10)).toBeCloseTo(10, 6);
  });

  it('A2: H_p is monotonically increasing with distance', () => {
    let prev = patrolScale(0);
    for (let d = 0.1; d <= 5.0; d += 0.1) {
      const curr = patrolScale(d);
      expect(curr).toBeGreaterThan(prev);
      prev = curr;
    }
  });

  it('A3: H_p(1, e) ≈ e * π^φ ≈ 17.33', () => {
    const expected = Math.E * Math.pow(Math.PI, PHI);
    expect(patrolScale(1)).toBeCloseTo(expected, 2);
  });

  it('A4: relative sensitivity is constant ≈ 1.852', () => {
    const sens = patrolSensitivity();
    expect(sens).toBeCloseTo(PHI * Math.log(Math.PI), 6);
    expect(sens).toBeCloseTo(1.852, 2);
  });

  it('A5: patrolAmplify scales baseRisk by H_p', () => {
    const risk = 0.1;
    const d = 1.0;
    expect(patrolAmplify(risk, d)).toBeCloseTo(risk * patrolScale(d), 10);
  });

  it('A6: negative distance clamped to 0', () => {
    expect(patrolScale(-5)).toEqual(patrolScale(0));
  });
});

// ─── B. Wall Formula Properties ─────────────────────────────

describe('B. Wall formula', () => {
  it('B1: H_w(0, R) = 1 (identity — dormant at center)', () => {
    expect(wallScale(0)).toBeCloseTo(1, 10);
    expect(wallScale(0, 1.5)).toBeCloseTo(1, 10);
    expect(wallScale(0, 100)).toBeCloseTo(1, 10);
  });

  it('B2: H_w(1, e) = e ≈ 2.718', () => {
    expect(wallScale(1)).toBeCloseTo(Math.E, 4);
  });

  it('B3: H_w(3, e) = e^9 ≈ 8103.08', () => {
    expect(wallScale(3)).toBeCloseTo(Math.exp(9), 0);
  });

  it('B4: H_w is monotonically increasing', () => {
    let prev = wallScale(0);
    for (let d = 0.1; d <= 5.0; d += 0.1) {
      const curr = wallScale(d);
      expect(curr).toBeGreaterThan(prev);
      prev = curr;
    }
  });

  it('B5: superexponential growth — wall overtakes patrol', () => {
    // At d=3: wall >> patrol
    expect(wallScale(3)).toBeGreaterThan(patrolScale(3));
    // At d=6: wall is astronomically larger
    expect(wallScale(6) / patrolScale(6)).toBeGreaterThan(1e10);
  });

  it('B6: wall sensitivity grows linearly: 2d·ln(R)', () => {
    expect(wallSensitivity(0)).toBeCloseTo(0, 10);
    expect(wallSensitivity(1)).toBeCloseTo(2 * Math.log(Math.E), 6);
    expect(wallSensitivity(3)).toBeCloseTo(6, 6); // 2*3*1
  });

  it('B7: negative distance clamped to 0', () => {
    expect(wallScale(-5)).toEqual(wallScale(0));
  });
});

// ─── C. Crossover Distance ──────────────────────────────────

describe('C. Crossover distance', () => {
  it('C1: d_cross(e) ≈ 0.926', () => {
    expect(crossoverDistance()).toBeCloseTo(0.926, 2);
  });

  it('C2: d_cross(1.5) ≈ 2.284', () => {
    expect(crossoverDistance(1.5)).toBeCloseTo(2.284, 2);
  });

  it('C3: at crossover, patrol and wall sensitivities are equal', () => {
    const d = crossoverDistance();
    const ps = patrolSensitivity();
    const ws = wallSensitivity(d);
    expect(ps).toBeCloseTo(ws, 3);
  });

  it('C4: R ≤ 1 → Infinity (no crossover)', () => {
    expect(crossoverDistance(1.0)).toBe(Infinity);
    expect(crossoverDistance(0.5)).toBe(Infinity);
  });

  it('C5: higher R → lower crossover', () => {
    expect(crossoverDistance(2)).toBeGreaterThan(crossoverDistance(3));
    expect(crossoverDistance(3)).toBeGreaterThan(crossoverDistance(10));
  });
});

// ─── D. Regime Classification ───────────────────────────────

describe('D. Regime classification', () => {
  it('D1: patrol below crossover', () => {
    expect(activeRegime(0)).toBe('patrol');
    expect(activeRegime(0.5)).toBe('patrol');
    expect(activeRegime(0.9)).toBe('patrol');
  });

  it('D2: wall at/above crossover', () => {
    expect(activeRegime(1.0)).toBe('wall');
    expect(activeRegime(2.0)).toBe('wall');
    expect(activeRegime(10.0)).toBe('wall');
  });
});

// ─── E. Dual-Regime Unified Scaling ─────────────────────────

describe('E. Dual-regime scaling', () => {
  it('E1: uses patrol in patrol regime', () => {
    const result = dualRegimeScale(0.1, 0.5);
    expect(result.regime).toBe('patrol');
    expect(result.activeH).toBeCloseTo(patrolScale(0.5), 6);
  });

  it('E2: uses wall in wall regime', () => {
    const result = dualRegimeScale(0.1, 2.0);
    expect(result.regime).toBe('wall');
    expect(result.activeH).toBeCloseTo(wallScale(2.0), 6);
  });

  it('E3: amplified risk = baseRisk * activeH', () => {
    const result = dualRegimeScale(0.2, 1.5);
    expect(result.amplifiedRisk).toBeCloseTo(0.2 * result.activeH, 10);
  });

  it('E4: contains all diagnostic fields', () => {
    const result = dualRegimeScale(0.1, 1.0);
    expect(result).toHaveProperty('distance');
    expect(result).toHaveProperty('regime');
    expect(result).toHaveProperty('crossover');
    expect(result).toHaveProperty('patrolH');
    expect(result).toHaveProperty('wallH');
    expect(result).toHaveProperty('activeH');
    expect(result).toHaveProperty('amplifiedRisk');
    expect(result).toHaveProperty('decision');
    expect(result).toHaveProperty('patrolSens');
    expect(result).toHaveProperty('wallSens');
  });
});

// ─── F. Blended Scaling ─────────────────────────────────────

describe('F. Blended scaling', () => {
  it('F1: near d=0 → approximately patrol', () => {
    const b = blendedScale(0);
    const p = patrolScale(0);
    // At d=0, far below crossover, blend should be ~patrol
    expect(b).toBeCloseTo(p, 0);
  });

  it('F2: far above crossover → approximately wall', () => {
    const d = 5.0;
    const b = blendedScale(d);
    const w = wallScale(d);
    expect(Math.abs(b - w) / w).toBeLessThan(0.01);
  });

  it('F3: smooth transition (no discontinuity at crossover)', () => {
    const cross = crossoverDistance();
    const before = blendedScale(cross - 0.01);
    const at = blendedScale(cross);
    const after = blendedScale(cross + 0.01);
    // Values should be close together
    expect(Math.abs(at - before) / at).toBeLessThan(0.1);
    expect(Math.abs(after - at) / at).toBeLessThan(0.1);
  });

  it('F4: blendedAmplify = baseRisk * blendedScale', () => {
    expect(blendedAmplify(0.15, 1.5)).toBeCloseTo(0.15 * blendedScale(1.5), 10);
  });

  it('F5: higher sharpness → closer to hard switch', () => {
    const d = crossoverDistance() + 0.5;
    const soft = blendedScale(d, R_DEFAULT, 2);
    const sharp = blendedScale(d, R_DEFAULT, 100);
    // Sharp should be closer to pure wall
    const wall = wallScale(d);
    expect(Math.abs(sharp - wall)).toBeLessThan(Math.abs(soft - wall));
  });
});

// ─── G. Tongue-Weighted Braided Scaling ─────────────────────

describe('G. Braided scaling', () => {
  const zeroDrift: TongueDrift = {
    distances: { KO: 0, AV: 0, RU: 0, CA: 0, UM: 0, DR: 0 },
  };

  const mildDrift: TongueDrift = {
    distances: { KO: 0.3, AV: 0.1, RU: 0.2, CA: 0.1, UM: 0.4, DR: 0.5 },
  };

  const severeDrift: TongueDrift = {
    distances: { KO: 2.0, AV: 1.5, RU: 3.0, CA: 1.0, UM: 2.5, DR: 4.0 },
  };

  it('G1: zero drift → patrol regime, low amplification', () => {
    const result = braidedScale(0.1, zeroDrift);
    expect(result.aggregateDistance).toBeCloseTo(0, 6);
    expect(result.aggregateDecision).toBe('ALLOW');
  });

  it('G2: severe drift → high amplification', () => {
    const result = braidedScale(0.1, severeDrift);
    expect(result.amplifiedRisk).toBeGreaterThan(1.0);
    expect(result.aggregateDecision).toBe('DENY');
  });

  it('G3: per-tongue patrol computed correctly', () => {
    const result = braidedScale(0.1, mildDrift);
    for (const tg of ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'] as TongueCode[]) {
      const d = mildDrift.distances[tg];
      expect(result.tonguePatrol[tg]).toBeCloseTo(patrolScale(d), 4);
    }
  });

  it('G4: aggregate distance is weighted RMS', () => {
    const result = braidedScale(0.1, mildDrift, 'lws');
    // Manual weighted RMS
    let wdSq = 0;
    let wSum = 0;
    for (const tg of ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'] as TongueCode[]) {
      const w = LWS_WEIGHTS[tg];
      const d = mildDrift.distances[tg];
      wdSq += w * d * d;
      wSum += w;
    }
    expect(result.aggregateDistance).toBeCloseTo(Math.sqrt(wdSq / wSum), 6);
  });

  it('G5: dominant tongue is the one with highest weighted patrol', () => {
    const result = braidedScale(0.1, mildDrift);
    const maxTg = Object.entries(result.tongueWeightedPatrol)
      .sort((a, b) => b[1] - a[1])[0][0];
    expect(result.dominantTongue).toBe(maxTg);
  });

  it('G6: PHDM weights produce different results than LWS', () => {
    const lws = braidedScale(0.1, mildDrift, 'lws');
    const phdm = braidedScale(0.1, mildDrift, 'phdm');
    expect(lws.braidedH).not.toBeCloseTo(phdm.braidedH, 2);
    expect(phdm.weightSystem).toBe('phdm');
    expect(lws.weightSystem).toBe('lws');
  });

  it('G7: wall component present in braided result', () => {
    const result = braidedScale(0.1, mildDrift);
    const aggD = result.aggregateDistance;
    expect(result.wallH).toBeCloseTo(wallScale(aggD), 4);
  });
});

// ─── H. Risk Decision Thresholds ────────────────────────────

describe('H. Risk decisions', () => {
  it('H1: ALLOW for low amplified risk', () => {
    const result = dualRegimeScale(0.01, 0.1);
    expect(result.decision).toBe('ALLOW');
  });

  it('H2: QUARANTINE for moderate risk', () => {
    // Patrol at d=0.1: ~3.27, so 0.1*3.27 = 0.327 → QUARANTINE
    const result = dualRegimeScale(0.1, 0.1);
    expect(result.decision).toBe('QUARANTINE');
  });

  it('H3: DENY for high drift', () => {
    const result = dualRegimeScale(0.1, 3.0);
    expect(result.decision).toBe('DENY');
  });

  it('H4: custom thresholds respected', () => {
    const result = dualRegimeScale(0.1, 0.1, R_DEFAULT, {
      allow: 0.5,
      quarantine: 0.8,
      escalate: 0.95,
    });
    // 0.1 * patrol(0.1) ≈ 0.327 < 0.5 → ALLOW
    expect(result.decision).toBe('ALLOW');
  });
});

// ─── I. Weight System Differences ───────────────────────────

describe('I. Weight systems', () => {
  it('I1: LWS weights are linear progression', () => {
    const vals = Object.values(LWS_WEIGHTS);
    for (let i = 1; i < vals.length; i++) {
      expect(vals[i]).toBeGreaterThan(vals[i - 1]);
    }
    expect(LWS_WEIGHTS.KO).toBe(1.0);
    expect(LWS_WEIGHTS.DR).toBeCloseTo(1.667, 2);
  });

  it('I2: PHDM weights are φⁿ progression', () => {
    expect(PHDM_WEIGHTS.KO).toBeCloseTo(1.0, 6);
    expect(PHDM_WEIGHTS.AV).toBeCloseTo(PHI, 4);
    expect(PHDM_WEIGHTS.RU).toBeCloseTo(PHI ** 2, 4);
    expect(PHDM_WEIGHTS.DR).toBeCloseTo(PHI ** 5, 2);
  });

  it('I3: PHDM DR/KO ratio ≈ 11.09', () => {
    expect(PHDM_WEIGHTS.DR / PHDM_WEIGHTS.KO).toBeCloseTo(11.09, 1);
  });

  it('I4: LWS DR/KO ratio ≈ 1.667', () => {
    expect(LWS_WEIGHTS.DR / LWS_WEIGHTS.KO).toBeCloseTo(1.667, 2);
  });
});

// ─── J. Drift Velocity Modulation ───────────────────────────

describe('J. Drift velocity modulation', () => {
  const baseDrift: TongueDrift = {
    distances: { KO: 0.5, AV: 0.3, RU: 0.2, CA: 0.4, UM: 0.6, DR: 0.3 },
  };

  it('J1: no velocities → factor = 1.0', () => {
    const result = braidedScale(0.1, baseDrift);
    expect(result.driftVelocityFactor).toBeCloseTo(1.0, 6);
  });

  it('J2: high velocity → factor > 1 (biases toward wall)', () => {
    const fastDrift: TongueDrift = {
      ...baseDrift,
      velocities: { KO: 2.0, AV: 0.1, RU: 0.1, CA: 0.1, UM: 0.1, DR: 0.1 },
    };
    const result = braidedScale(0.1, fastDrift);
    expect(result.driftVelocityFactor).toBeGreaterThan(1.0);
  });

  it('J3: zero velocity → factor ≈ 1 - tanh(0.5) ≈ 0.538', () => {
    const stillDrift: TongueDrift = {
      ...baseDrift,
      velocities: { KO: 0, AV: 0, RU: 0, CA: 0, UM: 0, DR: 0 },
    };
    const result = braidedScale(0.1, stillDrift);
    // 1 + tanh(0 - 0.5) = 1 + tanh(-0.5) ≈ 1 - 0.462 = 0.538
    expect(result.driftVelocityFactor).toBeCloseTo(1 + Math.tanh(-0.5), 3);
  });

  it('J4: fast drift biases toward wall regime', () => {
    // At high distances (where wall > patrol), velocity should increase risk.
    // At low distances (where patrol > wall), velocity biases toward lower wall.
    // The key behavior is: fast drift shifts the sigmoid toward wall.
    const highDrift: TongueDrift = {
      distances: { KO: 3.0, AV: 3.0, RU: 3.0, CA: 3.0, UM: 3.0, DR: 3.0 },
    };
    const slow: TongueDrift = {
      ...highDrift,
      velocities: { KO: 0.1, AV: 0.1, RU: 0.1, CA: 0.1, UM: 0.1, DR: 0.1 },
    };
    const fast: TongueDrift = {
      ...highDrift,
      velocities: { KO: 3.0, AV: 3.0, RU: 3.0, CA: 3.0, UM: 3.0, DR: 3.0 },
    };
    const slowResult = braidedScale(0.1, slow);
    const fastResult = braidedScale(0.1, fast);
    // At d=3, wall > patrol, so biasing toward wall increases risk
    expect(fastResult.amplifiedRisk).toBeGreaterThan(slowResult.amplifiedRisk);
  });
});

// ─── K. Mathematical Invariants ─────────────────────────────

describe('K. Mathematical invariants', () => {
  it('K1: patrol and wall are both positive for all d ≥ 0', () => {
    for (let d = 0; d <= 10; d += 0.5) {
      expect(patrolScale(d)).toBeGreaterThan(0);
      expect(wallScale(d)).toBeGreaterThan(0);
    }
  });

  it('K2: patrol(d) ≥ R for all d ≥ 0', () => {
    for (let d = 0; d <= 10; d += 0.5) {
      expect(patrolScale(d)).toBeGreaterThanOrEqual(Math.E - EPSILON);
    }
  });

  it('K3: wall(d) ≥ 1 for all d ≥ 0', () => {
    for (let d = 0; d <= 10; d += 0.5) {
      expect(wallScale(d)).toBeGreaterThanOrEqual(1 - EPSILON);
    }
  });

  it('K4: wall overtakes patrol in magnitude beyond d≈2.3', () => {
    // Sensitivity crossover is at d≈0.926, but MAGNITUDE crossover is later (~2.3).
    // Patrol starts higher (R ≈ 2.72 at d=0) while wall starts at 1.
    // Wall's superexponential growth eventually overtakes patrol's exponential growth.
    for (let d = 2.5; d <= 6; d += 0.5) {
      expect(wallScale(d)).toBeGreaterThan(patrolScale(d));
    }
  });

  it('K5: patrol dominates below crossover at small d', () => {
    // H_p(0) = e ≈ 2.72, H_w(0) = 1 → patrol > wall near 0
    expect(patrolScale(0)).toBeGreaterThan(wallScale(0));
    expect(patrolScale(0.3)).toBeGreaterThan(wallScale(0.3));
  });

  it('K6: blended is continuous', () => {
    // Check no jumps in blended scale
    const steps = 100;
    const maxD = 5.0;
    let prev = blendedScale(0);
    for (let i = 1; i <= steps; i++) {
      const d = (i / steps) * maxD;
      const curr = blendedScale(d);
      // Ratio between consecutive steps should be bounded
      expect(curr / prev).toBeLessThan(2.0);
      prev = curr;
    }
  });
});

// ─── L. Edge Cases ──────────────────────────────────────────

describe('L. Edge cases', () => {
  it('L1: baseRisk = 0 → amplified = 0', () => {
    expect(patrolAmplify(0, 5)).toBe(0);
    expect(wallAmplify(0, 5)).toBe(0);
    expect(blendedAmplify(0, 5)).toBe(0);
  });

  it('L2: negative baseRisk clamped to 0', () => {
    expect(patrolAmplify(-0.5, 1)).toBe(0);
    expect(wallAmplify(-0.5, 1)).toBe(0);
  });

  it('L3: R_DEFAULT is e', () => {
    expect(R_DEFAULT).toBeCloseTo(Math.E, 10);
  });

  it('L4: R_FIFTH is 1.5', () => {
    expect(R_FIFTH).toBe(1.5);
  });

  it('L5: very large distance wall doesnt throw', () => {
    // d=100 → e^10000 will be Infinity, but that's fine
    const w = wallScale(100);
    expect(w).toBe(Infinity);
    const result = dualRegimeScale(0.1, 100);
    expect(result.decision).toBe('DENY');
  });

  it('L6: braided with missing tongue defaults to 0', () => {
    const partial: TongueDrift = {
      distances: { KO: 0.5 } as any,
    };
    // Should not throw — missing tongues default to 0
    const result = braidedScale(0.1, partial);
    expect(result.tonguePatrol.KO).toBeCloseTo(patrolScale(0.5), 4);
    expect(result.tonguePatrol.AV).toBeCloseTo(patrolScale(0), 4);
  });
});
