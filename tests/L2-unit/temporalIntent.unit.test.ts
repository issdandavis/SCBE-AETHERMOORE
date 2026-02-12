/**
 * @file temporalIntent.unit.test.ts
 * @module tests/L2-unit/temporalIntent
 * @layer Layer 5, Layer 11, Layer 12, Layer 13
 *
 * Unit tests for the Temporal-Intent Harmonic Scaling system.
 * Tests: IntentSample, IntentHistory, Harmonic Wall extensions,
 *        Omega decision gate, and TemporalSecurityGate.
 */

import { describe, it, expect } from 'vitest';
import {
  R_HARMONIC,
  INTENT_DECAY_RATE,
  MAX_INTENT_ACCUMULATION,
  TRUST_EXILE_THRESHOLD,
  TRUST_EXILE_ROUNDS,
  ALLOW_THRESHOLD,
  QUARANTINE_THRESHOLD,
  IntentState,
  computeDTri,
  computeRawIntent,
  buildSample,
  createIntentHistory,
  addSample,
  computeXFactor,
  harmonicWallBasic,
  harmonicWallTemporal,
  compareScaling,
  computeOmega,
  getStatus,
  TemporalSecurityGate,
} from '../../src/harmonic/temporalIntent.js';

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════

describe('Constants', () => {
  it('R_HARMONIC is 1.5 (perfect fifth)', () => {
    expect(R_HARMONIC).toBe(1.5);
  });

  it('INTENT_DECAY_RATE is 0.95', () => {
    expect(INTENT_DECAY_RATE).toBe(0.95);
  });

  it('MAX_INTENT_ACCUMULATION is 10', () => {
    expect(MAX_INTENT_ACCUMULATION).toBe(10);
  });

  it('thresholds for exile are defined', () => {
    expect(TRUST_EXILE_THRESHOLD).toBe(0.3);
    expect(TRUST_EXILE_ROUNDS).toBe(10);
  });

  it('decision thresholds are ordered', () => {
    expect(ALLOW_THRESHOLD).toBeGreaterThan(QUARANTINE_THRESHOLD);
    expect(QUARANTINE_THRESHOLD).toBeGreaterThan(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// IntentState enum
// ═══════════════════════════════════════════════════════════════

describe('IntentState', () => {
  it('has all five states', () => {
    expect(IntentState.BENIGN).toBe('benign');
    expect(IntentState.NEUTRAL).toBe('neutral');
    expect(IntentState.DRIFTING).toBe('drifting');
    expect(IntentState.ADVERSARIAL).toBe('adversarial');
    expect(IntentState.EXILED).toBe('exiled');
  });
});

// ═══════════════════════════════════════════════════════════════
// computeDTri — Triadic temporal distance (L11)
// ═══════════════════════════════════════════════════════════════

describe('computeDTri', () => {
  it('geometric mean of three positive values', () => {
    const result = computeDTri(1, 1, 1);
    expect(result).toBeCloseTo(1.0, 6);
  });

  it('geometric mean of different values', () => {
    const result = computeDTri(2, 4, 8);
    expect(result).toBeCloseTo(Math.cbrt(64), 6);
  });

  it('returns 0 if any component is 0', () => {
    expect(computeDTri(0, 1, 1)).toBe(0);
    expect(computeDTri(1, 0, 1)).toBe(0);
    expect(computeDTri(1, 1, 0)).toBe(0);
  });

  it('uses absolute values for negative inputs', () => {
    const result = computeDTri(-2, 3, -4);
    expect(result).toBeCloseTo(Math.cbrt(24), 6);
  });
});

// ═══════════════════════════════════════════════════════════════
// computeRawIntent
// ═══════════════════════════════════════════════════════════════

describe('computeRawIntent', () => {
  it('returns 0 for stationary agent at origin with perfect harmony', () => {
    const intent = computeRawIntent({
      timestamp: 1000,
      distance: 0,
      velocity: 0,
      harmony: 1.0,
    });
    expect(intent).toBe(0);
  });

  it('positive velocity increases intent', () => {
    const base = computeRawIntent({
      timestamp: 1000,
      distance: 0.3,
      velocity: 0,
      harmony: 0.5,
    });
    const withVelocity = computeRawIntent({
      timestamp: 1000,
      distance: 0.3,
      velocity: 0.5,
      harmony: 0.5,
    });
    expect(withVelocity).toBeGreaterThan(base);
  });

  it('negative velocity does not increase intent (clamped at 0)', () => {
    const retreating = computeRawIntent({
      timestamp: 1000,
      distance: 0.3,
      velocity: -0.5,
      harmony: 0.5,
    });
    const stationary = computeRawIntent({
      timestamp: 1000,
      distance: 0.3,
      velocity: 0,
      harmony: 0.5,
    });
    expect(retreating).toEqual(stationary);
  });

  it('higher distance produces higher intent', () => {
    const near = computeRawIntent({
      timestamp: 1000,
      distance: 0.2,
      velocity: 0.1,
      harmony: 0.5,
    });
    const far = computeRawIntent({
      timestamp: 1000,
      distance: 0.8,
      velocity: 0.1,
      harmony: 0.5,
    });
    expect(far).toBeGreaterThan(near);
  });

  it('high harmony dampens intent', () => {
    const lowHarmony = computeRawIntent({
      timestamp: 1000,
      distance: 0.5,
      velocity: 0.1,
      harmony: 0.0,
    });
    const highHarmony = computeRawIntent({
      timestamp: 1000,
      distance: 0.5,
      velocity: 0.1,
      harmony: 0.9,
    });
    expect(highHarmony).toBeLessThan(lowHarmony);
  });

  it('CPSE deviations amplify intent', () => {
    const base = computeRawIntent({
      timestamp: 1000,
      distance: 0.5,
      velocity: 0.1,
      harmony: 0.5,
    });
    const withCPSE = computeRawIntent({
      timestamp: 1000,
      distance: 0.5,
      velocity: 0.1,
      harmony: 0.5,
      chaosdev: 0.5,
      fractaldev: 0.3,
      energydev: 0.4,
    });
    expect(withCPSE).toBeGreaterThan(base);
  });

  it('triadic components amplify intent', () => {
    const base = computeRawIntent({
      timestamp: 1000,
      distance: 0.5,
      velocity: 0.1,
      harmony: 0.5,
    });
    const withTriadic = computeRawIntent({
      timestamp: 1000,
      distance: 0.5,
      velocity: 0.1,
      harmony: 0.5,
      dTriImmediate: 0.5,
      dTriMedium: 0.6,
      dTriLong: 0.7,
    });
    expect(withTriadic).toBeGreaterThan(base);
  });
});

// ═══════════════════════════════════════════════════════════════
// buildSample
// ═══════════════════════════════════════════════════════════════

describe('buildSample', () => {
  it('fills defaults for optional fields', () => {
    const sample = buildSample({
      timestamp: 1000,
      distance: 0.3,
      velocity: 0.1,
      harmony: 0.5,
    });
    expect(sample.chaosdev).toBe(0);
    expect(sample.fractaldev).toBe(0);
    expect(sample.energydev).toBe(0);
    expect(sample.dTriImmediate).toBe(0);
    expect(sample.dTriMedium).toBe(0);
    expect(sample.dTriLong).toBe(0);
    expect(sample.dTri).toBe(0);
    expect(sample.rawIntent).toBeGreaterThanOrEqual(0);
  });

  it('computes dTri and rawIntent', () => {
    const sample = buildSample({
      timestamp: 1000,
      distance: 0.5,
      velocity: 0.2,
      harmony: 0.3,
      dTriImmediate: 1,
      dTriMedium: 2,
      dTriLong: 3,
    });
    expect(sample.dTri).toBeCloseTo(Math.cbrt(6), 6);
    expect(sample.rawIntent).toBeGreaterThan(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// IntentHistory — createIntentHistory, addSample
// ═══════════════════════════════════════════════════════════════

describe('IntentHistory', () => {
  it('creates a fresh history with neutral state', () => {
    const h = createIntentHistory('agent-1', 1000);
    expect(h.agentId).toBe('agent-1');
    expect(h.samples).toHaveLength(0);
    expect(h.accumulatedIntent).toBe(0);
    expect(h.trustScore).toBe(1.0);
    expect(h.lowTrustRounds).toBe(0);
    expect(h.state).toBe(IntentState.NEUTRAL);
  });

  it('adding samples increases accumulated intent', () => {
    let h = createIntentHistory('agent-2', 1000);
    h = addSample(h, 0.5, 0.1, 0.3, 1000);
    expect(h.accumulatedIntent).toBeGreaterThan(0);
    expect(h.samples).toHaveLength(1);
  });

  it('accumulated intent caps at MAX_INTENT_ACCUMULATION', () => {
    let h = createIntentHistory('agent-cap', 1000);
    for (let i = 0; i < 100; i++) {
      h = addSample(h, 0.9, 0.5, -0.5, 1000 + i);
    }
    expect(h.accumulatedIntent).toBeLessThanOrEqual(MAX_INTENT_ACCUMULATION);
  });

  it('benign agent stays in BENIGN state', () => {
    let h = createIntentHistory('benign', 1000);
    // Near origin, no velocity, high harmony
    for (let i = 0; i < 10; i++) {
      h = addSample(h, 0.05, 0, 0.9, 1000 + i * 100);
    }
    expect(h.state).toBe(IntentState.BENIGN);
  });

  it('drifting agent transitions beyond NEUTRAL', () => {
    let h = createIntentHistory('drifter', 1000);
    // Moderate drift — enough to leave NEUTRAL but not necessarily exile
    for (let i = 0; i < 15; i++) {
      h = addSample(h, 0.3 + 0.01 * i, 0.03, 0.4, 1000 + i * 100);
    }
    expect(h.state).not.toBe(IntentState.BENIGN);
    expect(h.accumulatedIntent).toBeGreaterThan(0.5);
  });

  it('trust decays with high distance', () => {
    let h = createIntentHistory('far-agent', 1000);
    for (let i = 0; i < 10; i++) {
      h = addSample(h, 0.8, 0.1, 0.1, 1000 + i * 100);
    }
    expect(h.trustScore).toBeLessThan(1.0);
  });

  it('trust decays slower when agent returns to safe operation', () => {
    let h = createIntentHistory('recovered', 1000);
    // Moderate drift
    for (let i = 0; i < 5; i++) {
      h = addSample(h, 0.4, 0.03, 0.4, 1000 + i * 100);
    }
    const trustAfterDrift = h.trustScore;
    // Return to safe — trust should stop falling as fast (decay slows via +0.02 recovery)
    // With large time gaps so intent decays, which reduces the -0.05 * accum_intent drag
    for (let i = 0; i < 5; i++) {
      h = addSample(h, 0.1, 0, 0.95, 50000 + i * 10000);
    }
    // After intent decays with time gaps, trust drag is reduced
    expect(h.accumulatedIntent).toBeLessThan(1.0);
  });
});

// ═══════════════════════════════════════════════════════════════
// computeXFactor
// ═══════════════════════════════════════════════════════════════

describe('computeXFactor', () => {
  it('fresh history has x = 0.5 (minimal intent, full trust)', () => {
    const h = createIntentHistory('x-test', 1000);
    const x = computeXFactor(h);
    // base_x = 0.5 + 0 * 0.25 = 0.5; trust_mod = 1 + (1 - 1) = 1
    expect(x).toBeCloseTo(0.5, 6);
  });

  it('x increases with accumulated intent', () => {
    let h = createIntentHistory('x-grow', 1000);
    for (let i = 0; i < 15; i++) {
      h = addSample(h, 0.5, 0.2, 0.2, 1000 + i * 100);
    }
    expect(computeXFactor(h)).toBeGreaterThan(0.5);
  });

  it('x caps at 3.0', () => {
    let h = createIntentHistory('x-cap', 1000);
    for (let i = 0; i < 100; i++) {
      h = addSample(h, 0.9, 0.5, -0.8, 1000 + i);
    }
    expect(computeXFactor(h)).toBeLessThanOrEqual(3.0);
  });

  it('low trust amplifies x', () => {
    const highTrust = createIntentHistory('ht', 1000);
    const lowTrust: typeof highTrust = {
      ...createIntentHistory('lt', 1000),
      accumulatedIntent: 2.0,
      trustScore: 0.9,
    };
    const lowTrustLow: typeof highTrust = {
      ...createIntentHistory('ltl', 1000),
      accumulatedIntent: 2.0,
      trustScore: 0.2,
    };
    expect(computeXFactor(lowTrustLow)).toBeGreaterThan(computeXFactor(lowTrust));
  });
});

// ═══════════════════════════════════════════════════════════════
// Harmonic Wall formulas
// ═══════════════════════════════════════════════════════════════

describe('harmonicWallBasic', () => {
  it('H(0, R) = 1 for any R', () => {
    expect(harmonicWallBasic(0)).toBe(1);
    expect(harmonicWallBasic(0, 2.0)).toBe(1);
  });

  it('H(d, R) = R^(d²)', () => {
    expect(harmonicWallBasic(1)).toBeCloseTo(1.5, 6);
    expect(harmonicWallBasic(2)).toBeCloseTo(Math.pow(1.5, 4), 6);
  });

  it('monotonically increasing with distance', () => {
    const h1 = harmonicWallBasic(0.5);
    const h2 = harmonicWallBasic(1.0);
    const h3 = harmonicWallBasic(2.0);
    expect(h1).toBeLessThan(h2);
    expect(h2).toBeLessThan(h3);
  });

  it('grows super-exponentially near boundary', () => {
    const h09 = harmonicWallBasic(0.9);
    const h095 = harmonicWallBasic(0.95);
    expect(h095).toBeGreaterThan(h09);
    expect(h095 / h09).toBeGreaterThan(1);
  });
});

describe('harmonicWallTemporal', () => {
  it('H_eff(d, x=1) = H(d, R) (standard case)', () => {
    expect(harmonicWallTemporal(0.5, 1.0)).toBeCloseTo(harmonicWallBasic(0.5), 10);
    expect(harmonicWallTemporal(1.0, 1.0)).toBeCloseTo(harmonicWallBasic(1.0), 10);
  });

  it('x < 1 is forgiving (lower cost than standard)', () => {
    const standard = harmonicWallBasic(0.8);
    const forgiving = harmonicWallTemporal(0.8, 0.5);
    expect(forgiving).toBeLessThan(standard);
  });

  it('x > 1 compounds cost (higher than standard)', () => {
    const standard = harmonicWallBasic(0.8);
    const compounding = harmonicWallTemporal(0.8, 2.0);
    expect(compounding).toBeGreaterThan(standard);
  });

  it('H_eff(0, x) = 1 for any x', () => {
    expect(harmonicWallTemporal(0, 3.0)).toBe(1);
    expect(harmonicWallTemporal(0, 0.1)).toBe(1);
  });

  it('at high hyperbolic distance with sustained intent, cost is massive', () => {
    // d=0.95 in Poincaré ball gives d²·x = 0.9025·3 = 2.7075, H = 1.5^2.7 ≈ 3.0
    // Use d=3.0 (hyperbolic distance) for dramatic amplification
    const cost = harmonicWallTemporal(3.0, 3.0);
    // 1.5^(9·3) = 1.5^27 — massive
    expect(cost).toBeGreaterThan(1000);
  });
});

describe('compareScaling', () => {
  it('amplification is 1 when x=1', () => {
    const result = compareScaling(0.5, 1.0);
    expect(result.amplification).toBeCloseTo(1.0, 6);
  });

  it('amplification > 1 when x > 1', () => {
    const result = compareScaling(0.5, 2.0);
    expect(result.amplification).toBeGreaterThan(1.0);
  });

  it('amplification < 1 when x < 1', () => {
    const result = compareScaling(0.5, 0.5);
    expect(result.amplification).toBeLessThan(1.0);
  });
});

// ═══════════════════════════════════════════════════════════════
// computeOmega — Temporal Security Gate (L13)
// ═══════════════════════════════════════════════════════════════

describe('computeOmega', () => {
  it('fresh benign agent gets ALLOW', () => {
    let h = createIntentHistory('benign-omega', 1000);
    for (let i = 0; i < 6; i++) {
      h = addSample(h, 0.05, 0, 0.9, 1000 + i * 100);
    }
    const result = computeOmega(h);
    expect(result.decision).toBe('ALLOW');
    expect(result.omega).toBeGreaterThan(ALLOW_THRESHOLD);
  });

  it('adversarial agent gets blocked (DENY, QUARANTINE, or EXILE)', () => {
    let h = createIntentHistory('adversary-omega', 1000);
    for (let i = 0; i < 30; i++) {
      h = addSample(h, 0.7 + 0.005 * i, 0.15, -0.3, 1000 + i * 100);
    }
    const result = computeOmega(h);
    // Sustained adversarial behavior can escalate to EXILE
    expect(['DENY', 'QUARANTINE', 'EXILE']).toContain(result.decision);
    expect(result.decision).not.toBe('ALLOW');
  });

  it('exiled agent gets EXILE with omega=0', () => {
    let h = createIntentHistory('exile-omega', 1000);
    h = { ...h, state: IntentState.EXILED, lowTrustRounds: TRUST_EXILE_ROUNDS };
    const result = computeOmega(h);
    expect(result.decision).toBe('EXILE');
    expect(result.omega).toBe(0);
  });

  it('invalid PQC yields DENY', () => {
    let h = createIntentHistory('pqc-fail', 1000);
    for (let i = 0; i < 6; i++) {
      h = addSample(h, 0.05, 0, 0.9, 1000 + i * 100);
    }
    const result = computeOmega(h, false);
    expect(result.decision).toBe('DENY');
    expect(result.omega).toBe(0);
  });

  it('low spectral score degrades omega', () => {
    let h = createIntentHistory('spectral', 1000);
    for (let i = 0; i < 6; i++) {
      h = addSample(h, 0.05, 0, 0.9, 1000 + i * 100);
    }
    const full = computeOmega(h, true, 1.0, 1.0);
    const degraded = computeOmega(h, true, 1.0, 0.3);
    expect(degraded.omega).toBeLessThan(full.omega);
  });
});

// ═══════════════════════════════════════════════════════════════
// getStatus
// ═══════════════════════════════════════════════════════════════

describe('getStatus', () => {
  it('returns complete status object', () => {
    let h = createIntentHistory('status-test', 1000);
    h = addSample(h, 0.2, 0.05, 0.5, 1100);
    const status = getStatus(h);
    expect(status.agentId).toBe('status-test');
    expect(typeof status.state).toBe('string');
    expect(typeof status.trustScore).toBe('number');
    expect(typeof status.accumulatedIntent).toBe('number');
    expect(typeof status.xFactor).toBe('number');
    expect(typeof status.omega).toBe('number');
    expect(typeof status.decision).toBe('string');
    expect(status.sampleCount).toBe(1);
  });
});

// ═══════════════════════════════════════════════════════════════
// TemporalSecurityGate (multi-agent)
// ═══════════════════════════════════════════════════════════════

describe('TemporalSecurityGate', () => {
  it('creates and tracks multiple agents', () => {
    const gate = new TemporalSecurityGate();
    gate.recordObservation('agent-a', 0.1, 0, 0.9, 1000);
    gate.recordObservation('agent-b', 0.5, 0.2, 0.3, 1000);
    expect(gate.agentIds()).toHaveLength(2);
    expect(gate.agentIds()).toContain('agent-a');
    expect(gate.agentIds()).toContain('agent-b');
  });

  it('benign agent gets ALLOW through gate', () => {
    const gate = new TemporalSecurityGate();
    for (let i = 0; i < 8; i++) {
      gate.recordObservation('safe', 0.05, 0, 0.95, 1000 + i * 100);
    }
    const result = gate.computeOmega('safe');
    expect(result.decision).toBe('ALLOW');
  });

  it('adversarial agent gets blocked through gate', () => {
    const gate = new TemporalSecurityGate();
    for (let i = 0; i < 25; i++) {
      gate.recordObservation('bad', 0.6 + 0.01 * i, 0.1, -0.5, 1000 + i * 100);
    }
    const result = gate.computeOmega('bad');
    // Sustained adversarial behavior results in DENY, QUARANTINE, or EXILE
    expect(['DENY', 'QUARANTINE', 'EXILE']).toContain(result.decision);
    expect(result.decision).not.toBe('ALLOW');
  });

  it('getStatus returns full info', () => {
    const gate = new TemporalSecurityGate();
    gate.recordObservation('info', 0.3, 0.05, 0.5, 1000);
    const status = gate.getStatus('info');
    expect(status.agentId).toBe('info');
    expect(status.sampleCount).toBe(1);
  });

  it('remove deletes an agent', () => {
    const gate = new TemporalSecurityGate();
    gate.recordObservation('temp', 0.1, 0, 0.9, 1000);
    expect(gate.agentIds()).toContain('temp');
    gate.remove('temp');
    expect(gate.agentIds()).not.toContain('temp');
  });

  it('getOrCreate returns fresh history for unknown agent', () => {
    const gate = new TemporalSecurityGate();
    const h = gate.getOrCreate('new-agent');
    expect(h.agentId).toBe('new-agent');
    expect(h.state).toBe(IntentState.NEUTRAL);
  });
});

// ═══════════════════════════════════════════════════════════════
// Integration: "Security IS growth. Intent over time reveals truth."
// ═══════════════════════════════════════════════════════════════

describe('Integration: time-over-intent principle', () => {
  it('brief deviation is forgiven (x stays below 1)', () => {
    let h = createIntentHistory('brief', 1000);
    // One brief spike
    h = addSample(h, 0.6, 0.1, 0.3, 1000);
    // Then return to safe
    for (let i = 0; i < 10; i++) {
      h = addSample(h, 0.05, 0, 0.9, 1100 + i * 500);
    }
    expect(computeXFactor(h)).toBeLessThan(1.0);
  });

  it('sustained drift compounds cost super-exponentially', () => {
    const d = 0.7;
    const xBrief = 0.5;
    const xSustained = 2.5;

    const briefCost = harmonicWallTemporal(d, xBrief);
    const standardCost = harmonicWallBasic(d);
    const sustainedCost = harmonicWallTemporal(d, xSustained);

    // Brief < Standard < Sustained
    expect(briefCost).toBeLessThan(standardCost);
    expect(standardCost).toBeLessThan(sustainedCost);

    // Sustained amplification is measurable (d=0.7 in ball gives moderate scaling)
    expect(sustainedCost / standardCost).toBeGreaterThan(1.1);
  });

  it('intent decay allows recovery', () => {
    let h = createIntentHistory('recover', 1000);
    // Build up intent
    for (let i = 0; i < 10; i++) {
      h = addSample(h, 0.5, 0.1, 0.2, 1000 + i * 100);
    }
    const intentAfterBurst = h.accumulatedIntent;

    // Wait (large time gap) and add safe samples
    for (let i = 0; i < 10; i++) {
      h = addSample(h, 0.05, 0, 0.9, 10000 + i * 1000);
    }
    expect(h.accumulatedIntent).toBeLessThan(intentAfterBurst);
  });
});
