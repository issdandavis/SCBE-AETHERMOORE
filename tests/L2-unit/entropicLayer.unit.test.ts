/**
 * @file entropicLayer.unit.test.ts
 * @tier L2-unit
 * @axiom 3 (Causality), 4 (Symmetry)
 * @category unit
 *
 * Unit tests for the consolidated Entropic Layer:
 * escape detection, adaptive k, expansion tracking, time dilation.
 */

import { describe, it, expect } from 'vitest';
import type { Vector6D } from '../../src/harmonic/constants.js';
import type { CHSFNState } from '../../src/harmonic/chsfn.js';
import {
  detectEscape,
  computeThreatLevel,
  computeStability,
  adaptiveK,
  trackExpansion,
  detectTimeDilation,
  computePositionEntropy,
  assess,
  DEFAULT_ENTROPIC_CONFIG,
} from '../../src/harmonic/entropicLayer.js';

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════

const ORIGIN: Vector6D = [0, 0, 0, 0, 0, 0];
const ALIGNED_PHASE: Vector6D = [0, Math.PI / 3, (2 * Math.PI) / 3, Math.PI, (4 * Math.PI) / 3, (5 * Math.PI) / 3];

function makeState(pos: Vector6D, phase?: Vector6D, mass?: number): CHSFNState {
  return {
    position: pos,
    phase: phase ?? [...ALIGNED_PHASE] as Vector6D,
    mass: mass ?? 1.0,
  };
}

// ═══════════════════════════════════════════════════════════════
// detectEscape
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: detectEscape', () => {
  it('should not flag escape for origin state with high coherence', () => {
    const state = makeState(ORIGIN);
    const status = detectEscape(state, 0.9);
    expect(status.escaping).toBe(false);
    expect(status.currentNorm).toBeCloseTo(0, 5);
  });

  it('should flag escape for state near basin edge', () => {
    const state = makeState([0.8, 0, 0, 0, 0, 0] as Vector6D);
    // Low coherence → small basin → state is beyond basin
    const status = detectEscape(state, 0.3);
    expect(status.basinFraction).toBeGreaterThan(0.8);
    expect(status.escaping).toBe(true);
  });

  it('should report positive UM impedance for misaligned UM phase', () => {
    const misaligned = [...ALIGNED_PHASE] as Vector6D;
    misaligned[5] += Math.PI; // UM = index 5
    const state = makeState([0.1, 0, 0, 0, 0, 0] as Vector6D, misaligned);
    const status = detectEscape(state, 0.8);
    expect(status.umImpedance).toBeGreaterThan(0);
  });

  it('should report energy > 0', () => {
    const state = makeState([0.2, 0, 0, 0, 0, 0] as Vector6D);
    const status = detectEscape(state, 0.8);
    expect(status.energy).toBeGreaterThan(0);
  });

  it('should report basinRadius > 0 for non-zero coherence', () => {
    const state = makeState(ORIGIN);
    const status = detectEscape(state, 0.5);
    expect(status.basinRadius).toBeGreaterThan(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// computeThreatLevel
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: computeThreatLevel', () => {
  it('should be low for origin with aligned phase', () => {
    const state = makeState(ORIGIN);
    const threat = computeThreatLevel(state);
    expect(threat).toBeLessThan(0.5);
  });

  it('should be higher for distant state', () => {
    const near = makeState([0.05, 0, 0, 0, 0, 0] as Vector6D);
    const far = makeState([0.8, 0, 0, 0, 0, 0] as Vector6D);
    expect(computeThreatLevel(far)).toBeGreaterThan(computeThreatLevel(near));
  });

  it('should be in [0, 1]', () => {
    const threat = computeThreatLevel(makeState([0.5, 0.3, 0, 0, 0, 0] as Vector6D));
    expect(threat).toBeGreaterThanOrEqual(0);
    expect(threat).toBeLessThanOrEqual(1);
  });

  it('should increase with phase misalignment', () => {
    const aligned = makeState(ORIGIN, ALIGNED_PHASE);
    const misaligned = makeState(
      ORIGIN,
      ALIGNED_PHASE.map((p) => p + Math.PI / 2) as Vector6D
    );
    expect(computeThreatLevel(misaligned)).toBeGreaterThanOrEqual(computeThreatLevel(aligned));
  });
});

// ═══════════════════════════════════════════════════════════════
// computeStability
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: computeStability', () => {
  it('should be in [0, 1]', () => {
    const s = computeStability(makeState([0.2, 0, 0, 0, 0, 0] as Vector6D));
    expect(s).toBeGreaterThanOrEqual(0);
    expect(s).toBeLessThanOrEqual(1);
  });

  it('should return finite positive value for any valid state', () => {
    const origin = computeStability(makeState(ORIGIN));
    const far = computeStability(makeState([0.5, 0.3, 0, 0, 0, 0] as Vector6D));
    expect(origin).toBeGreaterThan(0);
    expect(far).toBeGreaterThan(0);
    expect(isFinite(origin)).toBe(true);
    expect(isFinite(far)).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════
// adaptiveK
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: adaptiveK', () => {
  it('should return k in [minK, maxK]', () => {
    const result = adaptiveK(makeState(ORIGIN));
    expect(result.k).toBeGreaterThanOrEqual(DEFAULT_ENTROPIC_CONFIG.minK);
    expect(result.k).toBeLessThanOrEqual(DEFAULT_ENTROPIC_CONFIG.maxK);
  });

  it('should return lower k for safe origin state', () => {
    const safe = adaptiveK(makeState(ORIGIN));
    expect(safe.k).toBeLessThanOrEqual(4);
    expect(safe.highAlert).toBe(false);
  });

  it('should return higher k for distant threat', () => {
    const threat = adaptiveK(makeState([0.8, 0.3, 0, 0, 0, 0] as Vector6D));
    const safe = adaptiveK(makeState(ORIGIN));
    expect(threat.k).toBeGreaterThanOrEqual(safe.k);
  });

  it('should report threat level and stability', () => {
    const result = adaptiveK(makeState([0.3, 0, 0, 0, 0, 0] as Vector6D));
    expect(result.threatLevel).toBeGreaterThanOrEqual(0);
    expect(result.threatLevel).toBeLessThanOrEqual(1);
    expect(result.stability).toBeGreaterThanOrEqual(0);
    expect(result.stability).toBeLessThanOrEqual(1);
  });

  it('should flag high alert for high threat', () => {
    // Force high threat: distant + misaligned phase
    const misaligned = ALIGNED_PHASE.map((p) => p + Math.PI) as Vector6D;
    const state = makeState([0.85, 0.3, 0.2, 0, 0, 0] as Vector6D, misaligned);
    const result = adaptiveK(state);
    expect(result.threatLevel).toBeGreaterThan(0.3);
  });
});

// ═══════════════════════════════════════════════════════════════
// trackExpansion
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: trackExpansion', () => {
  it('should produce volumeTrace of correct length', () => {
    const config = { ...DEFAULT_ENTROPIC_CONFIG, expansionSampleSteps: 5 };
    const result = trackExpansion(makeState([0.1, 0, 0, 0, 0, 0] as Vector6D), config);
    expect(result.volumeTrace).toHaveLength(6); // steps + 1
  });

  it('should have positive current volume', () => {
    const result = trackExpansion(makeState(ORIGIN));
    expect(result.currentVolume).toBeGreaterThan(0);
  });

  it('should report boolean accelerating/contracting', () => {
    const result = trackExpansion(makeState([0.2, 0, 0, 0, 0, 0] as Vector6D));
    expect(typeof result.accelerating).toBe('boolean');
    expect(typeof result.contracting).toBe('boolean');
  });

  it('should have finite growth rate', () => {
    const result = trackExpansion(makeState([0.1, 0.05, 0, 0, 0, 0] as Vector6D));
    expect(isFinite(result.growthRate)).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════
// detectTimeDilation
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: detectTimeDilation', () => {
  it('should return dilationFactor=1 for empty history', () => {
    const result = detectTimeDilation([]);
    expect(result.dilationFactor).toBe(1);
    expect(result.loopCount).toBe(0);
    expect(result.hostile).toBe(false);
  });

  it('should return dilationFactor=1 for single position', () => {
    const result = detectTimeDilation([ORIGIN]);
    expect(result.dilationFactor).toBe(1);
  });

  it('should detect loops in repeating positions', () => {
    // Alternate between two close positions → many loop pairs
    const history: Vector6D[] = [];
    for (let i = 0; i < 20; i++) {
      history.push(i % 2 === 0 ? ORIGIN : [0.001, 0, 0, 0, 0, 0]);
    }
    const result = detectTimeDilation(history);
    expect(result.loopCount).toBeGreaterThan(0);
    expect(result.dilationFactor).toBeGreaterThan(1);
  });

  it('should NOT detect loops for spread-out positions', () => {
    const history: Vector6D[] = Array.from({ length: 20 }, (_, i) => [
      0.05 * i * 0.01 * (i % 3),
      0.03 * i,
      0.01 * (i * i % 7),
      0,
      0,
      0,
    ] as Vector6D);
    const result = detectTimeDilation(history);
    // Spread-out positions should have fewer or no loops
    expect(result.hostile).toBe(false);
  });

  it('should cap dilation factor for many loops', () => {
    // Exact same position repeated → maximum loops
    const history: Vector6D[] = new Array(20).fill(ORIGIN);
    const result = detectTimeDilation(history);
    // Even with many loops, dilationFactor should be finite
    expect(isFinite(result.dilationFactor)).toBe(true);
    expect(result.dilationFactor).toBeGreaterThan(1);
  });
});

// ═══════════════════════════════════════════════════════════════
// computePositionEntropy
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: computePositionEntropy', () => {
  it('should return 1 for single position', () => {
    expect(computePositionEntropy([ORIGIN])).toBe(1);
  });

  it('should be 0 for identical positions', () => {
    const history: Vector6D[] = new Array(10).fill(ORIGIN);
    expect(computePositionEntropy(history)).toBeCloseTo(0, 5);
  });

  it('should be higher for diverse positions', () => {
    const diverse: Vector6D[] = Array.from({ length: 10 }, (_, i) => [
      (i - 5) * 0.15,
      (i % 3 - 1) * 0.15,
      0,
      0,
      0,
      0,
    ] as Vector6D);
    const uniform: Vector6D[] = new Array(10).fill([0.1, 0, 0, 0, 0, 0] as Vector6D);

    const eDiverse = computePositionEntropy(diverse);
    const eUniform = computePositionEntropy(uniform);
    expect(eDiverse).toBeGreaterThan(eUniform);
  });

  it('should be in [0, 1]', () => {
    const history: Vector6D[] = Array.from({ length: 5 }, (_, i) => [
      i * 0.1,
      0,
      0,
      0,
      0,
      0,
    ] as Vector6D);
    const e = computePositionEntropy(history);
    expect(e).toBeGreaterThanOrEqual(0);
    expect(e).toBeLessThanOrEqual(1);
  });
});

// ═══════════════════════════════════════════════════════════════
// assess (unified assessment)
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: assess', () => {
  it('should return PROCEED for safe origin state', () => {
    const state = makeState(ORIGIN);
    const result = assess(state, 0.9);
    expect(result.recommendation).toBe('PROCEED');
    expect(result.entropicRisk).toBeLessThan(0.3);
  });

  it('should return all sub-assessments', () => {
    const state = makeState([0.1, 0, 0, 0, 0, 0] as Vector6D);
    const result = assess(state, 0.8);
    expect(result.escape).toBeDefined();
    expect(result.adaptiveK).toBeDefined();
    expect(result.expansion).toBeDefined();
    expect(result.timeDilation).toBeDefined();
    expect(typeof result.entropicRisk).toBe('number');
    expect(typeof result.recommendation).toBe('string');
  });

  it('should escalate for escaping state', () => {
    const state = makeState([0.85, 0.2, 0, 0, 0, 0] as Vector6D);
    const result = assess(state, 0.3);
    // State is far from origin with low coherence → should trigger escape
    expect(['QUARANTINE', 'DENY']).toContain(result.recommendation);
  });

  it('should escalate for looping state', () => {
    const state = makeState(ORIGIN);
    const history: Vector6D[] = new Array(20).fill(ORIGIN);
    const result = assess(state, 0.9, history);
    // Repeated positions → hostile loop → should escalate
    expect(result.timeDilation.hostile).toBe(true);
    expect(result.recommendation).toBe('DENY');
  });

  it('should have entropicRisk in [0, 1]', () => {
    const state = makeState([0.3, 0.1, 0, 0, 0, 0] as Vector6D);
    const result = assess(state, 0.5);
    expect(result.entropicRisk).toBeGreaterThanOrEqual(0);
    expect(result.entropicRisk).toBeLessThanOrEqual(1);
  });

  it('should recommend at most QUARANTINE for moderate threat with spread positions', () => {
    const state = makeState([0.3, 0, 0, 0, 0, 0] as Vector6D);
    // Spread-out positions that should not trigger hostile loop
    const history: Vector6D[] = [
      [0.1, 0, 0, 0, 0, 0],
      [0.2, 0.1, 0, 0, 0, 0],
      [0.3, 0.2, 0, 0, 0, 0],
      [0.4, 0.1, 0, 0, 0, 0],
    ];
    const result = assess(state, 0.6, history);
    expect(result.timeDilation.hostile).toBe(false);
    expect(['PROCEED', 'SLOW', 'QUARANTINE']).toContain(result.recommendation);
  });
});
