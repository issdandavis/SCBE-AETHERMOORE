/**
 * @file temporalPhase.unit.test.ts
 * @module tests/L2-unit/temporalPhase
 * @layer Layer 6, Layer 11, Layer 12, Layer 13
 * @component Multi-Clock Temporal Phase System — Unit Tests
 * @version 3.2.4
 *
 * Tests the 5-clock T-phase system: FAST, MEMORY, GOVERNANCE, CIRCADIAN, SET.
 * Each clock ticks at its own rate with its own decay and breathing factor.
 */

import { describe, it, expect } from 'vitest';
import {
  TPhaseType,
  TPhaseConfig,
  DEFAULT_PHASE_CONFIGS,
  createClock,
  computeBreathingFactor,
  circadianTongueAffinity,
  tickClock,
  ContextEventType,
  ContextEvent,
  applyContextEvent,
  createMultiClock,
  tickPhase,
  tickPhases,
  injectContext,
  triadicRisk,
  combinedXFactor,
  computeMultiPhaseRisk,
} from '../../src/harmonic/temporalPhase.js';

// ═══════════════════════════════════════════════════════════════
// 1. T-Phase Type Enum
// ═══════════════════════════════════════════════════════════════

describe('TPhaseType enum', () => {
  it('has exactly 5 phases', () => {
    const values = Object.values(TPhaseType);
    expect(values).toHaveLength(5);
  });

  it('contains all expected phase types', () => {
    expect(TPhaseType.FAST).toBe('fast');
    expect(TPhaseType.MEMORY).toBe('memory');
    expect(TPhaseType.GOVERNANCE).toBe('governance');
    expect(TPhaseType.CIRCADIAN).toBe('circadian');
    expect(TPhaseType.SET).toBe('set');
  });
});

// ═══════════════════════════════════════════════════════════════
// 2. Default Phase Configs
// ═══════════════════════════════════════════════════════════════

describe('DEFAULT_PHASE_CONFIGS', () => {
  it('provides config for every TPhaseType', () => {
    for (const phase of Object.values(TPhaseType)) {
      const cfg = DEFAULT_PHASE_CONFIGS[phase];
      expect(cfg).toBeDefined();
      expect(cfg.decayRate).toBeGreaterThan(0);
      expect(cfg.decayRate).toBeLessThanOrEqual(1);
      expect(cfg.tongueAffinity).toHaveLength(6);
    }
  });

  it('FAST has highest decay rate (slowest forgetting)', () => {
    expect(DEFAULT_PHASE_CONFIGS[TPhaseType.FAST].decayRate).toBe(0.99);
  });

  it('SET has lowest decay rate (fastest forgetting)', () => {
    expect(DEFAULT_PHASE_CONFIGS[TPhaseType.SET].decayRate).toBe(0.5);
  });

  it('CIRCADIAN has strongest breathing amplitude', () => {
    const circAmp = DEFAULT_PHASE_CONFIGS[TPhaseType.CIRCADIAN].breathAmplitude;
    for (const phase of Object.values(TPhaseType)) {
      expect(circAmp).toBeGreaterThanOrEqual(DEFAULT_PHASE_CONFIGS[phase].breathAmplitude);
    }
  });

  it('FAST has no breathing', () => {
    expect(DEFAULT_PHASE_CONFIGS[TPhaseType.FAST].breathAmplitude).toBe(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// 3. createClock
// ═══════════════════════════════════════════════════════════════

describe('createClock', () => {
  it('creates a fresh clock with correct type', () => {
    const clock = createClock(TPhaseType.FAST);
    expect(clock.type).toBe(TPhaseType.FAST);
  });

  it('starts at tick 0', () => {
    expect(createClock(TPhaseType.MEMORY).tick).toBe(0);
  });

  it('starts with zero accumulated intent', () => {
    expect(createClock(TPhaseType.GOVERNANCE).accumulatedIntent).toBe(0);
  });

  it('starts with full trust', () => {
    expect(createClock(TPhaseType.CIRCADIAN).trustScore).toBe(1.0);
  });

  it('starts with breathing factor 1.0', () => {
    expect(createClock(TPhaseType.SET).breathingFactor).toBe(1.0);
  });

  it('starts active', () => {
    expect(createClock(TPhaseType.FAST).active).toBe(true);
  });

  it('starts with empty intent window', () => {
    expect(createClock(TPhaseType.FAST).intentWindow).toEqual([]);
  });
});

// ═══════════════════════════════════════════════════════════════
// 4. computeBreathingFactor
// ═══════════════════════════════════════════════════════════════

describe('computeBreathingFactor', () => {
  const cfg: TPhaseConfig = {
    decayRate: 0.95,
    breathAmplitude: 0.3,
    breathPeriod: 24,
    tongueAffinity: [1, 1, 1, 1, 1, 1],
  };

  it('returns 1.0 when amplitude is 0', () => {
    const noBreathe = { ...cfg, breathAmplitude: 0 };
    expect(computeBreathingFactor(10, noBreathe)).toBe(1.0);
  });

  it('returns 1.0 when period <= 0', () => {
    const zeroPeriod = { ...cfg, breathPeriod: 0 };
    expect(computeBreathingFactor(10, zeroPeriod)).toBe(1.0);
  });

  it('equals 1.0 at tick 0 (sin(0) = 0)', () => {
    expect(computeBreathingFactor(0, cfg)).toBeCloseTo(1.0);
  });

  it('peaks at quarter period (sin(π/2) = 1)', () => {
    const quarterPeriod = cfg.breathPeriod / 4; // tick 6
    const bf = computeBreathingFactor(quarterPeriod, cfg);
    expect(bf).toBeCloseTo(1.0 + cfg.breathAmplitude);
  });

  it('troughs at three-quarter period (sin(3π/2) = -1)', () => {
    const threeQuarterPeriod = (3 * cfg.breathPeriod) / 4; // tick 18
    const bf = computeBreathingFactor(threeQuarterPeriod, cfg);
    expect(bf).toBeCloseTo(1.0 - cfg.breathAmplitude);
  });

  it('is periodic: same value after full period', () => {
    const t = 7;
    const bf1 = computeBreathingFactor(t, cfg);
    const bf2 = computeBreathingFactor(t + cfg.breathPeriod, cfg);
    expect(bf1).toBeCloseTo(bf2);
  });

  it('stays within [1-A, 1+A]', () => {
    for (let t = 0; t < 100; t++) {
      const bf = computeBreathingFactor(t, cfg);
      expect(bf).toBeGreaterThanOrEqual(1.0 - cfg.breathAmplitude - 1e-10);
      expect(bf).toBeLessThanOrEqual(1.0 + cfg.breathAmplitude + 1e-10);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// 5. circadianTongueAffinity
// ═══════════════════════════════════════════════════════════════

describe('circadianTongueAffinity', () => {
  it('returns uniform [1,1,1,1,1,1] when period <= 0', () => {
    expect(circadianTongueAffinity(5, 0)).toEqual([1, 1, 1, 1, 1, 1]);
    expect(circadianTongueAffinity(5, -1)).toEqual([1, 1, 1, 1, 1, 1]);
  });

  it('at tick 0 (peak day): KO and AV are maximal (1.5)', () => {
    const aff = circadianTongueAffinity(0, 24);
    expect(aff[0]).toBeCloseTo(1.5); // KO
    expect(aff[1]).toBeCloseTo(1.5); // AV
  });

  it('at tick 0 (peak day): CA, DR, UM are minimal (0.5)', () => {
    const aff = circadianTongueAffinity(0, 24);
    expect(aff[3]).toBeCloseTo(0.5); // CA
    expect(aff[4]).toBeCloseTo(0.5); // DR
    expect(aff[5]).toBeCloseTo(0.5); // UM
  });

  it('at half period (peak night): KO and AV are minimal', () => {
    const aff = circadianTongueAffinity(12, 24);
    expect(aff[0]).toBeCloseTo(0.5); // KO
    expect(aff[1]).toBeCloseTo(0.5); // AV
  });

  it('at half period (peak night): CA, DR, UM are maximal', () => {
    const aff = circadianTongueAffinity(12, 24);
    expect(aff[3]).toBeCloseTo(1.5); // CA
    expect(aff[4]).toBeCloseTo(1.5); // DR
    expect(aff[5]).toBeCloseTo(1.5); // UM
  });

  it('RU stays moderate (always near 1.0)', () => {
    const day = circadianTongueAffinity(0, 24);
    const night = circadianTongueAffinity(12, 24);
    expect(day[2]).toBeCloseTo(1.0);
    expect(night[2]).toBeCloseTo(1.0);
  });

  it('all weights are in [0.5, 1.5]', () => {
    for (let t = 0; t < 48; t++) {
      const aff = circadianTongueAffinity(t, 24);
      for (let i = 0; i < 6; i++) {
        expect(aff[i]).toBeGreaterThanOrEqual(0.5 - 1e-10);
        expect(aff[i]).toBeLessThanOrEqual(1.5 + 1e-10);
      }
    }
  });

  it('is periodic', () => {
    const a1 = circadianTongueAffinity(5, 24);
    const a2 = circadianTongueAffinity(29, 24); // 5 + 24
    for (let i = 0; i < 6; i++) {
      expect(a1[i]).toBeCloseTo(a2[i]);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// 6. tickClock
// ═══════════════════════════════════════════════════════════════

describe('tickClock', () => {
  it('increments tick by 1', () => {
    const clock = createClock(TPhaseType.FAST);
    const next = tickClock(clock, 0.1);
    expect(next.tick).toBe(1);
  });

  it('accumulates intent', () => {
    const clock = createClock(TPhaseType.FAST);
    const next = tickClock(clock, 0.5);
    expect(next.accumulatedIntent).toBeGreaterThan(0);
  });

  it('applies decay from config', () => {
    let clock = createClock(TPhaseType.SET); // decay = 0.5
    clock = tickClock(clock, 1.0); // accum = 0 * 0.5 + 1.0 = 1.0
    clock = tickClock(clock, 0.0); // accum = 1.0 * 0.5 + 0 = 0.5
    expect(clock.accumulatedIntent).toBeCloseTo(0.5);
  });

  it('caps accumulated intent at 10.0', () => {
    let clock = createClock(TPhaseType.FAST);
    for (let i = 0; i < 100; i++) {
      clock = tickClock(clock, 5.0);
    }
    expect(clock.accumulatedIntent).toBeLessThanOrEqual(10.0);
  });

  it('appends to intent window', () => {
    let clock = createClock(TPhaseType.FAST);
    clock = tickClock(clock, 0.3);
    expect(clock.intentWindow).toEqual([0.3]);
    clock = tickClock(clock, 0.7);
    expect(clock.intentWindow).toEqual([0.3, 0.7]);
  });

  it('caps intent window at 50 entries', () => {
    let clock = createClock(TPhaseType.FAST);
    for (let i = 0; i < 60; i++) {
      clock = tickClock(clock, 0.1);
    }
    expect(clock.intentWindow.length).toBe(50);
  });

  it('returns same clock if inactive', () => {
    const clock = { ...createClock(TPhaseType.FAST), active: false };
    const next = tickClock(clock, 1.0);
    expect(next).toBe(clock); // same reference
  });

  it('trust decreases with high accumulated intent', () => {
    let clock = createClock(TPhaseType.FAST);
    for (let i = 0; i < 20; i++) {
      clock = tickClock(clock, 2.0);
    }
    expect(clock.trustScore).toBeLessThan(1.0);
  });

  it('trust stays non-negative', () => {
    let clock = createClock(TPhaseType.FAST);
    for (let i = 0; i < 200; i++) {
      clock = tickClock(clock, 5.0);
    }
    expect(clock.trustScore).toBeGreaterThanOrEqual(0);
  });

  it('respects immutability — original clock unchanged', () => {
    const clock = createClock(TPhaseType.FAST);
    const _next = tickClock(clock, 1.0);
    expect(clock.tick).toBe(0);
    expect(clock.accumulatedIntent).toBe(0);
  });

  it('accepts custom config', () => {
    const customCfg: TPhaseConfig = {
      decayRate: 0.1,
      breathAmplitude: 0,
      breathPeriod: 1,
      tongueAffinity: [1, 1, 1, 1, 1, 1],
    };
    let clock = createClock(TPhaseType.FAST);
    clock = tickClock(clock, 1.0, customCfg); // accum = 0 * 0.1 + 1.0 = 1.0
    clock = tickClock(clock, 0.0, customCfg); // accum = 1.0 * 0.1 + 0 = 0.1
    expect(clock.accumulatedIntent).toBeCloseTo(0.1);
  });
});

// ═══════════════════════════════════════════════════════════════
// 7. Context Events (applyContextEvent)
// ═══════════════════════════════════════════════════════════════

describe('applyContextEvent', () => {
  describe('DEPLOY event', () => {
    it('halves trust by default (trustDecay = 0.5)', () => {
      const clock = createClock(TPhaseType.FAST);
      const event: ContextEvent = {
        type: ContextEventType.DEPLOY,
        targetClocks: [],
      };
      const updated = applyContextEvent(clock, event);
      expect(updated.trustScore).toBeCloseTo(0.5);
    });

    it('partially resets accumulated intent', () => {
      let clock = createClock(TPhaseType.FAST);
      for (let i = 0; i < 10; i++) clock = tickClock(clock, 1.0);
      const before = clock.accumulatedIntent;

      const event: ContextEvent = {
        type: ContextEventType.DEPLOY,
        targetClocks: [],
      };
      const updated = applyContextEvent(clock, event);
      expect(updated.accumulatedIntent).toBeCloseTo(before * 0.3);
    });

    it('respects custom trustDecay', () => {
      const clock = createClock(TPhaseType.FAST);
      const event: ContextEvent = {
        type: ContextEventType.DEPLOY,
        targetClocks: [],
        trustDecay: 0.8,
      };
      const updated = applyContextEvent(clock, event);
      expect(updated.trustScore).toBeCloseTo(0.8);
    });
  });

  describe('SECURITY_ALERT event', () => {
    it('spikes breathing factor to 2.0 by default', () => {
      const clock = createClock(TPhaseType.FAST);
      const event: ContextEvent = {
        type: ContextEventType.SECURITY_ALERT,
        targetClocks: [],
      };
      const updated = applyContextEvent(clock, event);
      expect(updated.breathingFactor).toBe(2.0);
    });

    it('reduces trust by 30%', () => {
      const clock = createClock(TPhaseType.FAST);
      const event: ContextEvent = {
        type: ContextEventType.SECURITY_ALERT,
        targetClocks: [],
      };
      const updated = applyContextEvent(clock, event);
      expect(updated.trustScore).toBeCloseTo(0.7);
    });

    it('respects custom breathingOverride', () => {
      const clock = createClock(TPhaseType.FAST);
      const event: ContextEvent = {
        type: ContextEventType.SECURITY_ALERT,
        targetClocks: [],
        breathingOverride: 3.5,
      };
      const updated = applyContextEvent(clock, event);
      expect(updated.breathingFactor).toBe(3.5);
    });
  });

  describe('RESET event', () => {
    it('resets clock to fresh state', () => {
      let clock = createClock(TPhaseType.FAST);
      for (let i = 0; i < 20; i++) clock = tickClock(clock, 2.0);
      expect(clock.tick).toBe(20);
      expect(clock.accumulatedIntent).toBeGreaterThan(0);

      const event: ContextEvent = {
        type: ContextEventType.RESET,
        targetClocks: [],
      };
      const updated = applyContextEvent(clock, event);
      expect(updated.tick).toBe(0);
      expect(updated.accumulatedIntent).toBe(0);
      expect(updated.trustScore).toBe(1.0);
      expect(updated.intentWindow).toEqual([]);
      expect(updated.breathingFactor).toBe(1.0);
    });

    it('preserves clock type', () => {
      const clock = createClock(TPhaseType.GOVERNANCE);
      const event: ContextEvent = {
        type: ContextEventType.RESET,
        targetClocks: [],
      };
      const updated = applyContextEvent(clock, event);
      expect(updated.type).toBe(TPhaseType.GOVERNANCE);
    });
  });

  describe('PROBATION event', () => {
    it('caps trust at 0.3', () => {
      const clock = createClock(TPhaseType.FAST); // trust = 1.0
      const event: ContextEvent = {
        type: ContextEventType.PROBATION,
        targetClocks: [],
      };
      const updated = applyContextEvent(clock, event);
      expect(updated.trustScore).toBeCloseTo(0.3);
    });

    it('does not increase already-low trust', () => {
      let clock = createClock(TPhaseType.FAST);
      // Drive trust down
      for (let i = 0; i < 100; i++) clock = tickClock(clock, 5.0);
      const lowTrust = clock.trustScore;
      expect(lowTrust).toBeLessThan(0.3);

      const event: ContextEvent = {
        type: ContextEventType.PROBATION,
        targetClocks: [],
      };
      const updated = applyContextEvent(clock, event);
      expect(updated.trustScore).toBe(lowTrust); // Unchanged
    });
  });

  describe('targeting', () => {
    it('applies to all clocks when targetClocks is empty', () => {
      const clock = createClock(TPhaseType.FAST);
      const event: ContextEvent = {
        type: ContextEventType.PROBATION,
        targetClocks: [],
      };
      const updated = applyContextEvent(clock, event);
      expect(updated.trustScore).toBeCloseTo(0.3);
    });

    it('applies to matching clock type', () => {
      const clock = createClock(TPhaseType.FAST);
      const event: ContextEvent = {
        type: ContextEventType.PROBATION,
        targetClocks: [TPhaseType.FAST],
      };
      const updated = applyContextEvent(clock, event);
      expect(updated.trustScore).toBeCloseTo(0.3);
    });

    it('skips non-matching clock type', () => {
      const clock = createClock(TPhaseType.FAST);
      const event: ContextEvent = {
        type: ContextEventType.PROBATION,
        targetClocks: [TPhaseType.GOVERNANCE],
      };
      const updated = applyContextEvent(clock, event);
      expect(updated.trustScore).toBe(1.0); // Unchanged
    });
  });

  it('is immutable — original clock unchanged', () => {
    const clock = createClock(TPhaseType.FAST);
    const _updated = applyContextEvent(clock, {
      type: ContextEventType.PROBATION,
      targetClocks: [],
    });
    expect(clock.trustScore).toBe(1.0);
  });
});

// ═══════════════════════════════════════════════════════════════
// 8. Multi-Clock System
// ═══════════════════════════════════════════════════════════════

describe('createMultiClock', () => {
  it('creates state with correct agentId', () => {
    const state = createMultiClock('agent-42');
    expect(state.agentId).toBe('agent-42');
  });

  it('has all 5 clock types', () => {
    const state = createMultiClock('test');
    for (const phase of Object.values(TPhaseType)) {
      expect(state.clocks[phase]).toBeDefined();
      expect(state.clocks[phase].type).toBe(phase);
    }
  });

  it('all clocks start fresh', () => {
    const state = createMultiClock('test');
    for (const phase of Object.values(TPhaseType)) {
      expect(state.clocks[phase].tick).toBe(0);
      expect(state.clocks[phase].trustScore).toBe(1.0);
      expect(state.clocks[phase].accumulatedIntent).toBe(0);
    }
  });
});

describe('tickPhase', () => {
  it('only advances the specified phase', () => {
    const state = createMultiClock('test');
    const next = tickPhase(state, TPhaseType.FAST, 0.5);
    expect(next.clocks[TPhaseType.FAST].tick).toBe(1);
    expect(next.clocks[TPhaseType.MEMORY].tick).toBe(0);
    expect(next.clocks[TPhaseType.GOVERNANCE].tick).toBe(0);
  });

  it('preserves other clocks', () => {
    const state = createMultiClock('test');
    const next = tickPhase(state, TPhaseType.FAST, 0.5);
    expect(next.clocks[TPhaseType.CIRCADIAN]).toEqual(state.clocks[TPhaseType.CIRCADIAN]);
  });

  it('is immutable', () => {
    const state = createMultiClock('test');
    const _next = tickPhase(state, TPhaseType.FAST, 0.5);
    expect(state.clocks[TPhaseType.FAST].tick).toBe(0);
  });
});

describe('tickPhases', () => {
  it('advances multiple clocks simultaneously', () => {
    const state = createMultiClock('test');
    const next = tickPhases(state, [TPhaseType.FAST, TPhaseType.MEMORY], 0.3);
    expect(next.clocks[TPhaseType.FAST].tick).toBe(1);
    expect(next.clocks[TPhaseType.MEMORY].tick).toBe(1);
    expect(next.clocks[TPhaseType.GOVERNANCE].tick).toBe(0);
  });

  it('each clock gets same raw intent', () => {
    const state = createMultiClock('test');
    const next = tickPhases(state, [TPhaseType.FAST, TPhaseType.MEMORY], 0.7);
    // Both got 0.7 as raw intent
    expect(next.clocks[TPhaseType.FAST].intentWindow).toContain(0.7);
    expect(next.clocks[TPhaseType.MEMORY].intentWindow).toContain(0.7);
  });
});

describe('injectContext', () => {
  it('applies event to all clocks when targetClocks empty', () => {
    const state = createMultiClock('test');
    const event: ContextEvent = {
      type: ContextEventType.PROBATION,
      targetClocks: [],
    };
    const next = injectContext(state, event);
    for (const phase of Object.values(TPhaseType)) {
      expect(next.clocks[phase].trustScore).toBeCloseTo(0.3);
    }
  });

  it('applies event only to targeted clocks', () => {
    const state = createMultiClock('test');
    const event: ContextEvent = {
      type: ContextEventType.PROBATION,
      targetClocks: [TPhaseType.FAST, TPhaseType.MEMORY],
    };
    const next = injectContext(state, event);
    expect(next.clocks[TPhaseType.FAST].trustScore).toBeCloseTo(0.3);
    expect(next.clocks[TPhaseType.MEMORY].trustScore).toBeCloseTo(0.3);
    expect(next.clocks[TPhaseType.GOVERNANCE].trustScore).toBe(1.0);
    expect(next.clocks[TPhaseType.CIRCADIAN].trustScore).toBe(1.0);
  });

  it('preserves agentId', () => {
    const state = createMultiClock('agent-x');
    const next = injectContext(state, {
      type: ContextEventType.RESET,
      targetClocks: [],
    });
    expect(next.agentId).toBe('agent-x');
  });
});

// ═══════════════════════════════════════════════════════════════
// 9. Triadic Risk
// ═══════════════════════════════════════════════════════════════

describe('triadicRisk', () => {
  const PHI = (1 + Math.sqrt(5)) / 2;

  it('returns near-zero for zero inputs', () => {
    const r = triadicRisk(0, 0, 0);
    expect(r).toBeLessThan(0.01);
  });

  it('increases when any input increases', () => {
    const r0 = triadicRisk(0.5, 0.5, 0.5);
    const r1 = triadicRisk(0.5, 0.5, 2.0);
    expect(r1).toBeGreaterThan(r0);
  });

  it('is dominated by MEMORY (λ₂=0.5 default)', () => {
    const rMemHigh = triadicRisk(0.1, 5.0, 0.1);
    const rFastHigh = triadicRisk(5.0, 0.1, 0.1);
    expect(rMemHigh).toBeGreaterThan(rFastHigh);
  });

  it('uses golden-ratio exponents (no single dimension can zero the sum)', () => {
    // Even if two inputs are near-zero, one large input still produces risk
    const r = triadicRisk(0, 0, 3.0);
    expect(r).toBeGreaterThan(0.5);
  });

  it('respects custom lambdas', () => {
    const r1 = triadicRisk(1.0, 0.0, 0.0, 1.0, 0.0, 0.0);
    const r2 = triadicRisk(0.0, 1.0, 0.0, 1.0, 0.0, 0.0);
    // r1 should be larger since λ₁ = 1 weights iFast only
    expect(r1).toBeGreaterThan(r2);
  });

  it('is always non-negative', () => {
    expect(triadicRisk(0, 0, 0)).toBeGreaterThanOrEqual(0);
    expect(triadicRisk(1, 2, 3)).toBeGreaterThanOrEqual(0);
  });

  it('manual calculation: single-input case', () => {
    // triadicRisk(1.0, 0, 0) = (0.3·1^φ + 0.5·ε^φ + 0.2·ε^φ)^(1/φ)
    const r = triadicRisk(1.0, 0, 0);
    const expected = Math.pow(0.3 * Math.pow(1.0, PHI), 1 / PHI);
    expect(r).toBeCloseTo(expected, 2);
  });
});

// ═══════════════════════════════════════════════════════════════
// 10. combinedXFactor
// ═══════════════════════════════════════════════════════════════

describe('combinedXFactor', () => {
  it('returns 0.5 for a fresh agent (no intent, full trust)', () => {
    const state = createMultiClock('test');
    const x = combinedXFactor(state);
    expect(x).toBeCloseTo(0.5, 1);
  });

  it('increases with accumulated intent', () => {
    let state = createMultiClock('test');
    for (let i = 0; i < 30; i++) {
      state = tickPhases(state, [TPhaseType.FAST, TPhaseType.MEMORY, TPhaseType.GOVERNANCE], 1.0);
    }
    const x = combinedXFactor(state);
    expect(x).toBeGreaterThan(0.5);
  });

  it('is capped at 3.0', () => {
    let state = createMultiClock('test');
    for (let i = 0; i < 200; i++) {
      state = tickPhases(state, [TPhaseType.FAST, TPhaseType.MEMORY, TPhaseType.GOVERNANCE], 5.0);
    }
    const x = combinedXFactor(state);
    expect(x).toBeLessThanOrEqual(3.0);
  });

  it('amplifies when trust drops', () => {
    let state = createMultiClock('test');
    const xBefore = combinedXFactor(state);

    // Inject probation to lower trust
    state = injectContext(state, {
      type: ContextEventType.PROBATION,
      targetClocks: [],
    });

    // Add some intent so base isn't minimal
    for (let i = 0; i < 5; i++) {
      state = tickPhases(state, [TPhaseType.FAST, TPhaseType.MEMORY], 0.5);
    }
    const xAfter = combinedXFactor(state);
    expect(xAfter).toBeGreaterThan(xBefore);
  });
});

// ═══════════════════════════════════════════════════════════════
// 11. computeMultiPhaseRisk
// ═══════════════════════════════════════════════════════════════

describe('computeMultiPhaseRisk', () => {
  it('returns ALLOW for a fresh agent', () => {
    const state = createMultiClock('test');
    const risk = computeMultiPhaseRisk(state);
    expect(risk.decision).toBe('ALLOW');
  });

  it('returns per-phase intents and trusts', () => {
    const state = createMultiClock('test');
    const risk = computeMultiPhaseRisk(state);
    for (const phase of Object.values(TPhaseType)) {
      expect(risk.phaseIntents[phase]).toBeDefined();
      expect(risk.phaseTrust[phase]).toBeDefined();
    }
  });

  it('includes circadian tongue affinity', () => {
    const state = createMultiClock('test');
    const risk = computeMultiPhaseRisk(state);
    expect(risk.tongueAffinity).toHaveLength(6);
  });

  it('includes breathing factor', () => {
    const state = createMultiClock('test');
    const risk = computeMultiPhaseRisk(state);
    expect(risk.breathingFactor).toBe(1.0);
  });

  it('transitions to QUARANTINE with moderate intent', () => {
    let state = createMultiClock('test');
    // Drive some intent to push x above 1.0
    for (let i = 0; i < 50; i++) {
      state = tickPhases(state, [TPhaseType.FAST, TPhaseType.MEMORY, TPhaseType.GOVERNANCE], 1.5);
    }
    const risk = computeMultiPhaseRisk(state);
    // With sustained moderate intent, we expect at least QUARANTINE
    expect(['QUARANTINE', 'DENY', 'EXILE']).toContain(risk.decision);
  });

  it('transitions to DENY with high intent', () => {
    let state = createMultiClock('test');
    for (let i = 0; i < 80; i++) {
      state = tickPhases(state, [TPhaseType.FAST, TPhaseType.MEMORY, TPhaseType.GOVERNANCE], 3.0);
    }
    const risk = computeMultiPhaseRisk(state);
    expect(['DENY', 'EXILE']).toContain(risk.decision);
  });

  it('transitions to EXILE with extreme intent (maxIntent >= 9)', () => {
    let state = createMultiClock('test');
    for (let i = 0; i < 100; i++) {
      state = tickPhases(state, [TPhaseType.FAST, TPhaseType.MEMORY, TPhaseType.GOVERNANCE], 5.0);
    }
    const risk = computeMultiPhaseRisk(state);
    // Accumulated intent capped at 10.0 ≥ 9.0, and trust near 0
    expect(risk.decision).toBe('EXILE');
  });

  it('PROBATION triggers at least QUARANTINE (minTrust = 0.3 < 0.6)', () => {
    let state = createMultiClock('test');
    state = injectContext(state, {
      type: ContextEventType.PROBATION,
      targetClocks: [],
    });
    const risk = computeMultiPhaseRisk(state);
    // Trust = 0.3 exactly. DENY requires < 0.3 (strict), so QUARANTINE (< 0.6)
    expect(['QUARANTINE', 'DENY', 'EXILE']).toContain(risk.decision);
    expect(risk.decision).not.toBe('ALLOW');
  });

  it('combinedXFactor is consistent', () => {
    let state = createMultiClock('test');
    for (let i = 0; i < 10; i++) {
      state = tickPhases(state, [TPhaseType.FAST, TPhaseType.MEMORY], 0.3);
    }
    const risk = computeMultiPhaseRisk(state);
    expect(risk.combinedXFactor).toBeCloseTo(combinedXFactor(state));
  });

  it('triadicRisk is consistent', () => {
    let state = createMultiClock('test');
    for (let i = 0; i < 10; i++) {
      state = tickPhases(state, [TPhaseType.FAST, TPhaseType.MEMORY, TPhaseType.GOVERNANCE], 0.5);
    }
    const risk = computeMultiPhaseRisk(state);
    const expected = triadicRisk(
      state.clocks[TPhaseType.FAST].accumulatedIntent,
      state.clocks[TPhaseType.MEMORY].accumulatedIntent,
      state.clocks[TPhaseType.GOVERNANCE].accumulatedIntent
    );
    expect(risk.triadicRisk).toBeCloseTo(expected);
  });
});

// ═══════════════════════════════════════════════════════════════
// 12. Integration Scenarios
// ═══════════════════════════════════════════════════════════════

describe('integration scenarios', () => {
  it('benign agent stays ALLOW across many ticks', () => {
    let state = createMultiClock('benign-agent');
    for (let i = 0; i < 100; i++) {
      state = tickPhases(state, [TPhaseType.FAST, TPhaseType.MEMORY], 0.0);
    }
    const risk = computeMultiPhaseRisk(state);
    expect(risk.decision).toBe('ALLOW');
    expect(risk.combinedXFactor).toBeCloseTo(0.5, 1);
  });

  it('different clocks decay at different rates', () => {
    let state = createMultiClock('test');
    // Inject intent into all 3 main clocks
    state = tickPhases(state, [TPhaseType.FAST, TPhaseType.SET], 2.0);
    // Then let them both decay
    state = tickPhases(state, [TPhaseType.FAST, TPhaseType.SET], 0.0);
    // SET decays much faster (0.5) than FAST (0.99)
    expect(state.clocks[TPhaseType.FAST].accumulatedIntent)
      .toBeGreaterThan(state.clocks[TPhaseType.SET].accumulatedIntent);
  });

  it('deploy event forces re-evaluation', () => {
    let state = createMultiClock('test');
    // Build some trust history
    for (let i = 0; i < 10; i++) {
      state = tickPhases(state, [TPhaseType.FAST, TPhaseType.MEMORY], 0.0);
    }

    // Deploy event halves trust
    state = injectContext(state, {
      type: ContextEventType.DEPLOY,
      targetClocks: [],
    });
    const risk = computeMultiPhaseRisk(state);
    // Trust 0.5 → QUARANTINE (minTrust < 0.6)
    expect(['QUARANTINE', 'DENY']).toContain(risk.decision);
  });

  it('security alert reduces trust and spikes breathing', () => {
    let state = createMultiClock('test');
    // Alert: spike breathing, reduce trust to 0.7
    state = injectContext(state, {
      type: ContextEventType.SECURITY_ALERT,
      targetClocks: [],
    });
    const alertRisk = computeMultiPhaseRisk(state);
    // Trust 0.7 is above QUARANTINE threshold (0.6) but breathing spikes
    expect(alertRisk.breathingFactor).toBe(2.0);
    for (const phase of Object.values(TPhaseType)) {
      expect(alertRisk.phaseTrust[phase]).toBeCloseTo(0.7);
    }

    // Double alert pushes to QUARANTINE: trust 0.7 * 0.7 = 0.49 < 0.6
    state = injectContext(state, {
      type: ContextEventType.SECURITY_ALERT,
      targetClocks: [],
    });
    const doubleAlertRisk = computeMultiPhaseRisk(state);
    expect(doubleAlertRisk.decision).not.toBe('ALLOW');

    // Reset to recover
    state = injectContext(state, {
      type: ContextEventType.RESET,
      targetClocks: [],
    });
    const recoveredRisk = computeMultiPhaseRisk(state);
    expect(recoveredRisk.decision).toBe('ALLOW');
  });

  it('circadian clock breathing varies with ticks', () => {
    let state = createMultiClock('test');
    const breathValues: number[] = [];
    for (let i = 0; i < 24; i++) {
      state = tickPhase(state, TPhaseType.CIRCADIAN, 0.0);
      breathValues.push(state.clocks[TPhaseType.CIRCADIAN].breathingFactor);
    }
    // Should see variation (not all 1.0)
    const unique = new Set(breathValues.map(v => v.toFixed(3)));
    expect(unique.size).toBeGreaterThan(1);
  });

  it('multi-phase risk captures worst-case trust', () => {
    let state = createMultiClock('test');
    // Probation on FAST only → trust capped at 0.3
    state = injectContext(state, {
      type: ContextEventType.PROBATION,
      targetClocks: [TPhaseType.FAST],
    });
    // All other clocks at trust 1.0, but FAST at 0.3
    // minTrust = 0.3 exactly. DENY requires < 0.3 (strict), so QUARANTINE (< 0.6)
    const risk = computeMultiPhaseRisk(state);
    expect(['QUARANTINE', 'DENY', 'EXILE']).toContain(risk.decision);
    expect(risk.decision).not.toBe('ALLOW');
    // Verify FAST trust is indeed 0.3
    expect(risk.phaseTrust[TPhaseType.FAST]).toBeCloseTo(0.3);
    // And other clocks are still 1.0
    expect(risk.phaseTrust[TPhaseType.MEMORY]).toBeCloseTo(1.0);
  });

  it('gradual escalation: ALLOW → QUARANTINE → DENY → EXILE', () => {
    let state = createMultiClock('test');
    const decisions: string[] = [];

    // Phase 1: low intent
    for (let i = 0; i < 5; i++) {
      state = tickPhases(state, [TPhaseType.FAST, TPhaseType.MEMORY, TPhaseType.GOVERNANCE], 0.0);
    }
    decisions.push(computeMultiPhaseRisk(state).decision);

    // Phase 2: moderate intent
    for (let i = 0; i < 30; i++) {
      state = tickPhases(state, [TPhaseType.FAST, TPhaseType.MEMORY, TPhaseType.GOVERNANCE], 1.5);
    }
    decisions.push(computeMultiPhaseRisk(state).decision);

    // Phase 3: high intent
    for (let i = 0; i < 50; i++) {
      state = tickPhases(state, [TPhaseType.FAST, TPhaseType.MEMORY, TPhaseType.GOVERNANCE], 3.0);
    }
    decisions.push(computeMultiPhaseRisk(state).decision);

    // Phase 4: extreme intent
    for (let i = 0; i < 50; i++) {
      state = tickPhases(state, [TPhaseType.FAST, TPhaseType.MEMORY, TPhaseType.GOVERNANCE], 5.0);
    }
    decisions.push(computeMultiPhaseRisk(state).decision);

    // Verify escalation: each phase should be at least as strict as the previous
    const severity: Record<string, number> = { ALLOW: 0, QUARANTINE: 1, DENY: 2, EXILE: 3 };
    for (let i = 1; i < decisions.length; i++) {
      expect(severity[decisions[i]]).toBeGreaterThanOrEqual(severity[decisions[i - 1]]);
    }
    // The first should be ALLOW (benign)
    expect(decisions[0]).toBe('ALLOW');
    // The last should be EXILE (extreme)
    expect(decisions[decisions.length - 1]).toBe('EXILE');
  });
});
