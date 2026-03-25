/**
 * @file entropySurface.test.ts
 * @description Tests for the Entropy Surface Defense Layer
 *
 * Tests cover:
 * - Probing detection: legitimate vs adversarial query patterns
 * - Leakage budget: consumption, exhaustion, rate tracking
 * - Semantic nullification: sigmoid gating, signal degradation
 * - Entropy surface distance: boundary detection
 * - Stateful tracker: observation window, nullification application
 * - Anti-extraction property: probing yields diminishing information
 *
 * @module tests/harmonic/entropySurface
 * @layer Layer 12, Layer 13
 */

import { describe, it, expect, beforeEach } from 'vitest';
import type { Vector6D } from '../../packages/kernel/src/constants.js';
import {
  shannonEntropy,
  detectTemporalRegularity,
  computeCoverageBreadth,
  computeRepetitionScore,
  detectProbing,
  computeLeakageBudget,
  sigmoidGate,
  computeNullification,
  surfaceDistance,
  assessEntropySurface,
  EntropySurfaceTracker,
  DEFAULT_ENTROPY_SURFACE_CONFIG,
  type QueryObservation,
  type EntropySurfaceConfig,
} from '../../src/harmonic/entropySurface.js';

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════

function makeObs(
  position: Vector6D,
  timestamp: number,
  responseMI: number = 1.0
): QueryObservation {
  return { position, timestamp, responseMI };
}

const ORIGIN: Vector6D = [0, 0, 0, 0, 0, 0];

/** Generate a random point inside the Poincaré ball. */
function randomBallPoint(maxNorm: number = 0.5): Vector6D {
  const v = Array.from({ length: 6 }, () => Math.random() * 2 - 1);
  const n = Math.sqrt(v.reduce((s, x) => s + x * x, 0));
  const r = Math.random() * maxNorm;
  return v.map((x) => (x / n) * r) as Vector6D;
}

/** Generate evenly-spaced timestamps (machine-like). */
function regularTimestamps(count: number, interval: number = 100): number[] {
  return Array.from({ length: count }, (_, i) => 1000 + i * interval);
}

/** Generate jittery timestamps (human-like). */
function jitteryTimestamps(count: number, baseInterval: number = 1000): number[] {
  const ts: number[] = [1000];
  for (let i = 1; i < count; i++) {
    ts.push(ts[i - 1] + baseInterval + (Math.random() - 0.5) * baseInterval * 2);
  }
  return ts;
}

// ═══════════════════════════════════════════════════════════════
// Shannon Entropy
// ═══════════════════════════════════════════════════════════════

describe('Shannon Entropy', () => {
  it('should return 1 for uniform distribution', () => {
    const result = shannonEntropy([10, 10, 10, 10]);
    expect(result).toBeCloseTo(1, 2);
  });

  it('should return 0 for single-element distribution', () => {
    const result = shannonEntropy([100]);
    expect(result).toBe(0);
  });

  it('should return 0 for empty distribution', () => {
    expect(shannonEntropy([])).toBe(0);
  });

  it('should return low entropy for concentrated distribution', () => {
    const result = shannonEntropy([100, 1, 1, 1]);
    expect(result).toBeLessThan(0.5);
  });

  it('should be bounded in [0, 1]', () => {
    for (let i = 0; i < 20; i++) {
      const counts = Array.from({ length: 10 }, () => Math.floor(Math.random() * 50));
      const e = shannonEntropy(counts);
      expect(e).toBeGreaterThanOrEqual(0);
      expect(e).toBeLessThanOrEqual(1);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Temporal Regularity
// ═══════════════════════════════════════════════════════════════

describe('Temporal Regularity Detection', () => {
  it('should detect regular (machine-like) timing', () => {
    const ts = regularTimestamps(20);
    const regularity = detectTemporalRegularity(ts);
    expect(regularity).toBeGreaterThan(0.7);
  });

  it('should detect irregular (human-like) timing', () => {
    const ts = jitteryTimestamps(20);
    const regularity = detectTemporalRegularity(ts, 50);
    expect(regularity).toBeLessThan(0.7);
  });

  it('should return 0 for insufficient data', () => {
    expect(detectTemporalRegularity([1000, 2000])).toBe(0);
  });

  it('should return 1 for identical timestamps', () => {
    expect(detectTemporalRegularity([1000, 1000, 1000, 1000])).toBe(1);
  });
});

// ═══════════════════════════════════════════════════════════════
// Coverage Breadth
// ═══════════════════════════════════════════════════════════════

describe('Coverage Breadth', () => {
  it('should return 0 for empty positions', () => {
    expect(computeCoverageBreadth([])).toBe(0);
  });

  it('should return low coverage for clustered positions', () => {
    const positions: Vector6D[] = Array.from({ length: 20 }, () => [0.1, 0.1, 0.1, 0.1, 0.1, 0.1]);
    const coverage = computeCoverageBreadth(positions);
    expect(coverage).toBeLessThan(0.01); // All in one bin
  });

  it('should return higher coverage for spread positions', () => {
    const positions: Vector6D[] = [];
    for (let i = 0; i < 50; i++) {
      positions.push(randomBallPoint(0.9));
    }
    const coverage = computeCoverageBreadth(positions);
    expect(coverage).toBeGreaterThan(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// Repetition Score
// ═══════════════════════════════════════════════════════════════

describe('Repetition Score', () => {
  it('should return 0 for insufficient data', () => {
    expect(computeRepetitionScore([[0, 0, 0, 0, 0, 0]] as Vector6D[])).toBe(0);
  });

  it('should return 1 for identical positions', () => {
    const positions: Vector6D[] = Array.from({ length: 5 }, () => [0.1, 0.2, 0.3, 0.1, 0.2, 0.3]);
    const score = computeRepetitionScore(positions, 0.1);
    expect(score).toBe(1);
  });

  it('should return low score for diverse positions', () => {
    const positions: Vector6D[] = [
      [0.1, 0, 0, 0, 0, 0],
      [0, 0.5, 0, 0, 0, 0],
      [-0.3, 0, 0.4, 0, 0, 0],
      [0, 0, 0, 0.6, 0, 0],
      [0, 0, 0, 0, -0.4, 0.2],
    ];
    const score = computeRepetitionScore(positions, 0.1);
    expect(score).toBe(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// Probing Detection
// ═══════════════════════════════════════════════════════════════

describe('Probing Detection', () => {
  it('should classify sparse queries as LEGITIMATE', () => {
    const obs: QueryObservation[] = [makeObs(ORIGIN, 1000)];
    const result = detectProbing(obs);
    expect(result.classification).toBe('LEGITIMATE');
    expect(result.confidence).toBe(0);
  });

  it('should detect systematic grid probing', () => {
    // Generate a grid of positions with regular timing
    const observations: QueryObservation[] = [];
    const step = 0.3;
    let t = 0;
    for (let x = -0.5; x <= 0.5; x += step) {
      for (let y = -0.5; y <= 0.5; y += step) {
        observations.push(makeObs([x, y, 0, 0, 0, 0] as Vector6D, t, 1.0));
        t += 100; // Regular 100ms intervals
      }
    }
    const result = detectProbing(observations);
    expect(result.temporalRegularity).toBeGreaterThan(0.5);
    expect(result.confidence).toBeGreaterThan(0);
  });

  it('should detect repetitive probing at same point', () => {
    const observations: QueryObservation[] = Array.from({ length: 20 }, (_, i) =>
      makeObs([0.3, 0.3, 0, 0, 0, 0] as Vector6D, i * 100, 1.0)
    );
    const result = detectProbing(observations);
    expect(result.repetitionScore).toBe(1); // All identical
    expect(result.confidence).toBeGreaterThan(0.3);
  });

  it('should have lower confidence for natural usage patterns', () => {
    // Diverse positions, irregular timing, no repetition
    const timestamps = jitteryTimestamps(15, 5000);
    const observations: QueryObservation[] = timestamps.map((t, i) =>
      makeObs(randomBallPoint(0.3), t, 0.5)
    );
    const result = detectProbing(observations);
    expect(result.confidence).toBeLessThan(0.5);
  });

  // A4: Symmetry — probing detection should not depend on input order within a bin
  it('A4: should produce same confidence for permuted identical observations', () => {
    const obs1: QueryObservation[] = [
      makeObs([0.1, 0, 0, 0, 0, 0], 100, 1),
      makeObs([0.2, 0, 0, 0, 0, 0], 200, 1),
      makeObs([0.1, 0, 0, 0, 0, 0], 300, 1),
    ];
    const obs2: QueryObservation[] = [
      makeObs([0.2, 0, 0, 0, 0, 0], 100, 1),
      makeObs([0.1, 0, 0, 0, 0, 0], 200, 1),
      makeObs([0.1, 0, 0, 0, 0, 0], 300, 1),
    ];
    const r1 = detectProbing(obs1);
    const r2 = detectProbing(obs2);
    // Same query entropy (same set of bins), same coverage, similar repetition
    expect(r1.queryEntropy).toBeCloseTo(r2.queryEntropy, 5);
  });
});

// ═══════════════════════════════════════════════════════════════
// Leakage Budget
// ═══════════════════════════════════════════════════════════════

describe('Leakage Budget', () => {
  it('should start with full budget', () => {
    const result = computeLeakageBudget([]);
    expect(result.remaining).toBe(128);
    expect(result.consumed).toBe(0);
    expect(result.exhausted).toBe(false);
    expect(result.pressure).toBe(0);
  });

  it('should track consumption', () => {
    const observations = Array.from({ length: 10 }, (_, i) => makeObs(ORIGIN, i * 100, 5.0));
    const result = computeLeakageBudget(observations);
    expect(result.consumed).toBe(50);
    expect(result.remaining).toBe(78);
    expect(result.currentRate).toBe(5);
  });

  it('should exhaust budget', () => {
    const observations = Array.from({ length: 50 }, (_, i) => makeObs(ORIGIN, i * 100, 3.0));
    const result = computeLeakageBudget(observations);
    expect(result.consumed).toBe(150);
    expect(result.remaining).toBe(0);
    expect(result.exhausted).toBe(true);
    expect(result.pressure).toBeGreaterThanOrEqual(1);
  });

  // A3: Causality — consumption is monotonically non-decreasing
  it('A3: budget consumption should be monotonically non-decreasing within window', () => {
    const observations: QueryObservation[] = [];
    let prevConsumed = 0;
    for (let i = 0; i < 30; i++) {
      observations.push(makeObs(ORIGIN, i * 100, 1.0));
      const budget = computeLeakageBudget(observations);
      expect(budget.consumed).toBeGreaterThanOrEqual(prevConsumed);
      prevConsumed = budget.consumed;
    }
  });

  it('should only consider windowed observations', () => {
    const config: EntropySurfaceConfig = { ...DEFAULT_ENTROPY_SURFACE_CONFIG, windowSize: 5 };
    const observations = Array.from({ length: 20 }, (_, i) => makeObs(ORIGIN, i * 100, 2.0));
    const result = computeLeakageBudget(observations, config);
    // Only last 5 observations counted
    expect(result.consumed).toBe(10);
  });
});

// ═══════════════════════════════════════════════════════════════
// Sigmoid Gate
// ═══════════════════════════════════════════════════════════════

describe('Sigmoid Gate', () => {
  it('should return ~1 for low pressure', () => {
    expect(sigmoidGate(0, 10)).toBeGreaterThan(0.99);
  });

  it('should return ~0.5 at threshold', () => {
    expect(sigmoidGate(0.5, 10, 0.5)).toBeCloseTo(0.5, 1);
  });

  it('should return ~0 for high pressure', () => {
    expect(sigmoidGate(1.0, 10)).toBeLessThan(0.01);
  });

  it('should be monotonically decreasing', () => {
    let prev = 1;
    for (let p = 0; p <= 1; p += 0.05) {
      const v = sigmoidGate(p, 10);
      expect(v).toBeLessThanOrEqual(prev + 1e-10);
      prev = v;
    }
  });

  it('should be steeper with higher k', () => {
    const gentle = sigmoidGate(0.6, 2);
    const steep = sigmoidGate(0.6, 20);
    expect(steep).toBeLessThan(gentle);
  });
});

// ═══════════════════════════════════════════════════════════════
// Semantic Nullification
// ═══════════════════════════════════════════════════════════════

describe('Semantic Nullification', () => {
  it('should not activate under normal conditions', () => {
    const probing = detectProbing([]);
    const leakage = computeLeakageBudget([]);
    const result = computeNullification(probing, leakage);
    expect(result.active).toBe(false);
    expect(result.strength).toBeLessThan(0.05);
    expect(result.signalRetention).toBeGreaterThan(0.95);
    expect(result.reason).toBe('NOMINAL');
  });

  it('should activate when budget is exhausted', () => {
    const probing = detectProbing([]);
    const leakage: ReturnType<typeof computeLeakageBudget> = {
      totalBudget: 128,
      consumed: 200,
      remaining: 0,
      currentRate: 5,
      exhausted: true,
      pressure: 1.56,
    };
    const result = computeNullification(probing, leakage);
    expect(result.active).toBe(true);
    expect(result.strength).toBeGreaterThan(0.9);
    expect(result.signalRetention).toBeLessThan(0.1);
    expect(result.reason).toBe('BUDGET_EXHAUSTED');
  });

  it('should activate when probing is detected', () => {
    // Create high-confidence probing signature
    const probing = {
      queryEntropy: 0.2,
      temporalRegularity: 0.9,
      coverageBreadth: 0.5,
      repetitionScore: 0.8,
      confidence: 0.85,
      classification: 'PROBING' as const,
    };
    const leakage = computeLeakageBudget([]);
    const result = computeNullification(probing, leakage);
    expect(result.active).toBe(true);
    expect(result.strength).toBeGreaterThan(0.5);
    expect(result.reason).toBe('PROBING_DETECTED');
  });

  it('should preserve full signal under low pressure', () => {
    const probing = {
      queryEntropy: 0.9,
      temporalRegularity: 0.1,
      coverageBreadth: 0.01,
      repetitionScore: 0.0,
      confidence: 0.05,
      classification: 'LEGITIMATE' as const,
    };
    const leakage = computeLeakageBudget([makeObs(ORIGIN, 100, 0.1)]);
    const result = computeNullification(probing, leakage);
    expect(result.signalRetention).toBeGreaterThan(0.95);
  });
});

// ═══════════════════════════════════════════════════════════════
// Surface Distance
// ═══════════════════════════════════════════════════════════════

describe('Entropy Surface Distance', () => {
  it('should be negative (safe) under normal conditions', () => {
    const probing = detectProbing([]);
    const leakage = computeLeakageBudget([]);
    const d = surfaceDistance(probing, leakage);
    expect(d).toBeLessThan(0);
  });

  it('should be positive (nullified) under high pressure', () => {
    const probing = {
      queryEntropy: 0.2,
      temporalRegularity: 0.9,
      coverageBreadth: 0.5,
      repetitionScore: 0.8,
      confidence: 0.85,
      classification: 'PROBING' as const,
    };
    const leakage = computeLeakageBudget([]);
    const d = surfaceDistance(probing, leakage);
    expect(d).toBeGreaterThan(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// Unified Assessment
// ═══════════════════════════════════════════════════════════════

describe('Entropy Surface Assessment', () => {
  it('should be TRANSPARENT for empty history', () => {
    const result = assessEntropySurface([]);
    expect(result.posture).toBe('TRANSPARENT');
    expect(result.nullification.active).toBe(false);
  });

  it('should escalate posture as budget is consumed', () => {
    const observations: QueryObservation[] = [];

    // Add observations with high MI to consume budget
    for (let i = 0; i < 60; i++) {
      observations.push(makeObs(ORIGIN, i * 100, 3.0));
    }

    const result = assessEntropySurface(observations);
    expect(result.leakage.pressure).toBeGreaterThan(0.5);
    expect(result.posture).not.toBe('TRANSPARENT');
  });
});

// ═══════════════════════════════════════════════════════════════
// Stateful Tracker
// ═══════════════════════════════════════════════════════════════

describe('EntropySurfaceTracker', () => {
  let tracker: EntropySurfaceTracker;

  beforeEach(() => {
    tracker = new EntropySurfaceTracker();
  });

  it('should start with no assessment', () => {
    expect(tracker.lastAssessment).toBeNull();
    expect(tracker.observationCount).toBe(0);
  });

  it('should update assessment on observe', () => {
    const result = tracker.observe(ORIGIN, 1.0, 1000);
    expect(result).toBeDefined();
    expect(result.posture).toBeDefined();
    expect(tracker.observationCount).toBe(1);
  });

  it('should trim observations to bounded window', () => {
    const config = { windowSize: 5 };
    const t = new EntropySurfaceTracker(config);
    for (let i = 0; i < 20; i++) {
      t.observe(ORIGIN, 0.1, i * 100);
    }
    // 2 * windowSize = 10 max
    expect(t.observationCount).toBeLessThanOrEqual(10);
  });

  it('should nullify response vectors', () => {
    // Exhaust budget to trigger strong nullification
    for (let i = 0; i < 60; i++) {
      tracker.observe(ORIGIN, 5.0, i * 100);
    }

    const response: Vector6D = [0.5, 0.3, 0.2, 0.4, 0.1, 0.6];
    const nullified = tracker.nullify(response);

    // Nullified should have smaller magnitude
    const origNorm = Math.sqrt(response.reduce((s, x) => s + x * x, 0));
    const nullNorm = Math.sqrt(nullified.reduce((s, x) => s + x * x, 0));
    expect(nullNorm).toBeLessThan(origNorm);
  });

  it('should not nullify when posture is TRANSPARENT', () => {
    tracker.observe(ORIGIN, 0.001, 1000);
    const response: Vector6D = [0.5, 0.3, 0.2, 0.4, 0.1, 0.6];
    const result = tracker.nullify(response);
    expect(result).toEqual(response);
  });

  it('should reset cleanly', () => {
    tracker.observe(ORIGIN, 1.0, 1000);
    tracker.reset();
    expect(tracker.observationCount).toBe(0);
    expect(tracker.lastAssessment).toBeNull();
  });
});

// ═══════════════════════════════════════════════════════════════
// Anti-Extraction Property (L6 Adversarial)
// ═══════════════════════════════════════════════════════════════

describe('Anti-Extraction Property', () => {
  it('probing should yield diminishing information over time', () => {
    const tracker = new EntropySurfaceTracker({ leakageBudgetBits: 50 });
    const retentions: number[] = [];

    // Simulate systematic probing
    for (let i = 0; i < 40; i++) {
      const pos: Vector6D = [Math.sin(i * 0.5) * 0.3, Math.cos(i * 0.5) * 0.3, 0, 0, 0, 0];
      const assessment = tracker.observe(pos, 2.0, i * 100);
      retentions.push(assessment.nullification.signalRetention);
    }

    // Signal retention should decrease over time (non-increasing trend)
    const firstQuarter = retentions.slice(0, 10).reduce((a, b) => a + b, 0) / 10;
    const lastQuarter = retentions.slice(-10).reduce((a, b) => a + b, 0) / 10;
    expect(lastQuarter).toBeLessThan(firstQuarter);
  });

  it('legitimate sparse use should maintain high signal retention', () => {
    const tracker = new EntropySurfaceTracker();

    // Simulate sparse, diverse, low-MI queries with jittery timing
    let t = 1000;
    for (let i = 0; i < 10; i++) {
      const pos = randomBallPoint(0.3);
      t += 5000 + Math.random() * 10000; // 5-15s apart (irregular)
      const assessment = tracker.observe(pos, 0.1, t);
      expect(assessment.nullification.signalRetention).toBeGreaterThan(0.80);
    }
  });

  it('surrogate model should converge to noise under probing', () => {
    // Simulate what an attacker would collect
    const tracker = new EntropySurfaceTracker({ leakageBudgetBits: 30 });
    const trueResponses: Vector6D[] = [];
    const nullifiedResponses: Vector6D[] = [];

    for (let i = 0; i < 30; i++) {
      const input: Vector6D = [i * 0.03, 0, 0, 0, 0, 0];
      const trueOutput: Vector6D = [0.5, 0.3, 0.2, 0.4, 0.1, 0.6];

      tracker.observe(input, 2.0, i * 100);
      trueResponses.push(trueOutput);
      nullifiedResponses.push(tracker.nullify(trueOutput));
    }

    // Later nullified responses should be closer to origin (less informative)
    const earlyNorm = Math.sqrt(nullifiedResponses[0].reduce((s, x) => s + x * x, 0));
    const lateNorm = Math.sqrt(
      nullifiedResponses[nullifiedResponses.length - 1].reduce((s, x) => s + x * x, 0)
    );
    expect(lateNorm).toBeLessThan(earlyNorm);
  });
});
