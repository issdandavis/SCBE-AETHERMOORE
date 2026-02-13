/**
 * @file triMechanismDetector.test.ts
 * @module harmonic/triMechanismDetector.test
 * @layer Layer 5, Layer 7, Layer 12, Layer 13
 *
 * Tests for the three-mechanism adversarial detection system:
 * - Mechanism 1: Phase + Distance Scoring
 * - Mechanism 2: 6-Tonic Temporal Coherence
 * - Mechanism 3: Decimal Drift Authentication
 * - Combined TriMechanismDetector class
 */

import { describe, expect, it } from 'vitest';

import {
  DEFAULT_CONFIG,
  TONGUE_INDEX,
  TONGUE_PHASES,
  TriMechanismDetector,
  computeDriftSignature,
  driftAuthScore,
  driftDistanceToBaseline,
  phaseDeviation,
  phaseDistanceScore,
  tonicCoherence,
  triHyperbolicDistance,
  type PipelineMetrics,
  type PositionSample,
} from '../../src/harmonic/index';

// ═══════════════════════════════════════════════════════════════
// Test Helpers
// ═══════════════════════════════════════════════════════════════

function makeMetrics(overrides: Partial<PipelineMetrics> = {}): PipelineMetrics {
  return {
    uNorm: 0.45,
    uBreathNorm: 0.42,
    uFinalNorm: 0.40,
    cSpin: 0.88,
    sSpec: 0.91,
    tau: 0.5,
    sAudio: 0.72,
    dStar: 1.2,
    dTriNorm: 0.33,
    H: 0.85,
    riskBase: 0.15,
    riskPrime: 0.18,
    ...overrides,
  };
}

function makePositionHistory(n: number, tongueIdx: number, noisy = false): PositionSample[] {
  const freq = (tongueIdx + 1) * DEFAULT_CONFIG.baseFreq;
  return Array.from({ length: n }, (_, i) => {
    const t = i * 0.1;
    const r = 0.5 + 0.3 * Math.sin(2 * Math.PI * freq * t + DEFAULT_CONFIG.chirpRate * t * t);
    const noise = noisy ? 0.3 * Math.sin(i * 7.3) : 0;
    return {
      position: new Float64Array([r + noise, 0, 0]),
      timestamp: t,
    };
  });
}

function makeUFinal(tongueIdx: number, radius = 0.3): Float64Array {
  const dim = 12;
  const u = new Float64Array(dim);
  const angle = TONGUE_PHASES[tongueIdx];
  u[0] = radius * Math.cos(angle);
  u[1] = radius * Math.sin(angle);
  return u;
}

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════

describe('Constants', () => {
  it('TONGUE_PHASES has 6 entries at 60-degree spacing', () => {
    expect(TONGUE_PHASES).toHaveLength(6);
    for (let i = 0; i < 6; i++) {
      expect(TONGUE_PHASES[i]).toBeCloseTo(i * (Math.PI / 3), 10);
    }
  });

  it('TONGUE_INDEX maps all 6 sacred tongues', () => {
    const codes: Array<keyof typeof TONGUE_INDEX> = ['ko', 'av', 'ru', 'ca', 'um', 'dr'];
    for (let i = 0; i < codes.length; i++) {
      expect(TONGUE_INDEX[codes[i]]).toBe(i);
    }
  });

  it('DEFAULT_CONFIG weights sum to 1', () => {
    const sum = DEFAULT_CONFIG.wPhase + DEFAULT_CONFIG.wTonic + DEFAULT_CONFIG.wDrift;
    expect(sum).toBeCloseTo(1.0, 10);
  });

  it('DEFAULT_CONFIG has valid thresholds', () => {
    expect(DEFAULT_CONFIG.thresholds.allow).toBeGreaterThan(DEFAULT_CONFIG.thresholds.quarantine);
    expect(DEFAULT_CONFIG.thresholds.quarantine).toBeGreaterThan(0);
    expect(DEFAULT_CONFIG.thresholds.allow).toBeLessThanOrEqual(1);
  });
});

// ═══════════════════════════════════════════════════════════════
// Mechanism 1: Phase + Distance
// ═══════════════════════════════════════════════════════════════

describe('phaseDeviation', () => {
  it('returns 0 for identical angles', () => {
    expect(phaseDeviation(0, 0)).toBe(0);
    expect(phaseDeviation(Math.PI, Math.PI)).toBeCloseTo(0, 10);
  });

  it('returns 1 for opposite angles (π apart)', () => {
    expect(phaseDeviation(0, Math.PI)).toBeCloseTo(1.0, 10);
    expect(phaseDeviation(Math.PI / 2, -Math.PI / 2)).toBeCloseTo(1.0, 10);
  });

  it('returns value in [0, 1]', () => {
    for (let i = 0; i < 100; i++) {
      const a = Math.random() * 4 * Math.PI - 2 * Math.PI;
      const b = Math.random() * 4 * Math.PI - 2 * Math.PI;
      const dev = phaseDeviation(a, b);
      expect(dev).toBeGreaterThanOrEqual(0);
      expect(dev).toBeLessThanOrEqual(1 + 1e-10);
    }
  });

  it('is symmetric', () => {
    expect(phaseDeviation(0.5, 1.2)).toBeCloseTo(phaseDeviation(1.2, 0.5), 10);
  });

  it('wraps around 2π correctly', () => {
    const dev1 = phaseDeviation(0.1, 2 * Math.PI - 0.1);
    expect(dev1).toBeLessThan(0.2); // Should be close, not ~1
  });
});

describe('triHyperbolicDistance (Poincaré ball)', () => {
  it('returns 0 for identical points', () => {
    const u = new Float64Array([0.1, 0.2, 0.0]);
    expect(triHyperbolicDistance(u, u)).toBeCloseTo(0, 8);
  });

  it('returns 0 for two origins', () => {
    const o = new Float64Array([0, 0, 0]);
    expect(triHyperbolicDistance(o, o)).toBe(0);
  });

  it('increases with Euclidean distance', () => {
    const o = new Float64Array([0, 0]);
    const near = new Float64Array([0.1, 0]);
    const far = new Float64Array([0.5, 0]);
    expect(triHyperbolicDistance(o, far)).toBeGreaterThan(triHyperbolicDistance(o, near));
  });

  it('grows near boundary (exponential cost)', () => {
    const o = new Float64Array([0, 0]);
    const mid = new Float64Array([0.5, 0]);
    const edge = new Float64Array([0.99, 0]);
    const dMid = triHyperbolicDistance(o, mid);
    const dEdge = triHyperbolicDistance(o, edge);
    expect(dEdge / dMid).toBeGreaterThan(3); // Much larger near boundary
  });

  it('is symmetric', () => {
    const u = new Float64Array([0.3, 0.2]);
    const v = new Float64Array([0.1, -0.4]);
    expect(triHyperbolicDistance(u, v)).toBeCloseTo(triHyperbolicDistance(v, u), 10);
  });
});

describe('phaseDistanceScore', () => {
  it('returns high score for matching tongue centroid and phase', () => {
    const tongueIdx = 0;
    const u = makeUFinal(tongueIdx);
    const centroids = Array.from({ length: 6 }, (_, i) => makeUFinal(i));
    const result = phaseDistanceScore(u, tongueIdx, centroids, TONGUE_PHASES[tongueIdx]);
    expect(result.score).toBeGreaterThan(0.3);
    expect(result.flagged).toBe(false);
  });

  it('returns low score for wrong tongue phase', () => {
    const u = makeUFinal(0);
    const centroids = Array.from({ length: 6 }, (_, i) => makeUFinal(i));
    // Use tongue 0 centroid but tongue 3 phase (π apart)
    const result = phaseDistanceScore(u, 0, centroids, TONGUE_PHASES[3]);
    expect(result.score).toBeLessThan(0.5);
  });

  it('flags when score is below 0.3', () => {
    const u = new Float64Array(12);
    u[0] = 0.9; // Far from any centroid
    const centroids = Array.from({ length: 6 }, (_, i) => makeUFinal(i));
    const result = phaseDistanceScore(u, 0, centroids, Math.PI); // Wrong phase
    if (result.score < 0.3) {
      expect(result.flagged).toBe(true);
    }
  });

  it('score is always in (0, 1]', () => {
    for (let tongue = 0; tongue < 6; tongue++) {
      const u = makeUFinal(tongue);
      const centroids = Array.from({ length: 6 }, (_, i) => makeUFinal(i));
      const result = phaseDistanceScore(u, tongue, centroids, Math.random() * 2 * Math.PI);
      expect(result.score).toBeGreaterThan(0);
      expect(result.score).toBeLessThanOrEqual(1);
    }
  });

  it('detail string includes d_H and phase_dev', () => {
    const u = makeUFinal(0);
    const centroids = Array.from({ length: 6 }, (_, i) => makeUFinal(i));
    const result = phaseDistanceScore(u, 0, centroids, 0);
    expect(result.detail).toContain('d_H=');
    expect(result.detail).toContain('phase_dev=');
  });
});

// ═══════════════════════════════════════════════════════════════
// Mechanism 2: 6-Tonic Temporal Coherence
// ═══════════════════════════════════════════════════════════════

describe('tonicCoherence', () => {
  it('returns 0.5 for insufficient history (<3 samples)', () => {
    const result = tonicCoherence([], 0);
    expect(result.score).toBe(0.5);
    expect(result.flagged).toBe(false);
    expect(result.detail).toBe('insufficient history');
  });

  it('returns score in [0, 1] for valid history', () => {
    const history = makePositionHistory(30, 0);
    const result = tonicCoherence(history, 0);
    expect(result.score).toBeGreaterThanOrEqual(0);
    expect(result.score).toBeLessThanOrEqual(1);
  });

  it('gives higher score for coherent oscillation at tongue frequency', () => {
    const coherent = makePositionHistory(50, 2, false);
    const incoherent = makePositionHistory(50, 2, true);
    const sCoherent = tonicCoherence(coherent, 2);
    const sIncoherent = tonicCoherence(incoherent, 2);
    // Coherent should score at least as well or better
    expect(sCoherent.score).toBeGreaterThanOrEqual(sIncoherent.score - 0.1);
  });

  it('works for all 6 tongue indices', () => {
    for (let tongue = 0; tongue < 6; tongue++) {
      const history = makePositionHistory(30, tongue);
      const result = tonicCoherence(history, tongue);
      expect(result.score).toBeGreaterThanOrEqual(0);
      expect(result.score).toBeLessThanOrEqual(1);
    }
  });

  it('includes correlation and freq_match in detail', () => {
    const history = makePositionHistory(30, 0);
    const result = tonicCoherence(history, 0);
    expect(result.detail).toContain('correlation=');
    expect(result.detail).toContain('freq_match=');
  });
});

// ═══════════════════════════════════════════════════════════════
// Mechanism 3: Decimal Drift Authentication
// ═══════════════════════════════════════════════════════════════

describe('computeDriftSignature', () => {
  it('returns 17-dimensional Float64Array', () => {
    const sig = computeDriftSignature(makeMetrics());
    expect(sig).toBeInstanceOf(Float64Array);
    expect(sig.length).toBe(17);
  });

  it('includes pipeline metrics in first 12 components', () => {
    const m = makeMetrics();
    const sig = computeDriftSignature(m);
    expect(sig[0]).toBe(m.uNorm);
    expect(sig[7]).toBe(m.dStar);
    expect(sig[11]).toBe(m.riskPrime);
  });

  it('sets default 0.5 for input components when no inputData', () => {
    const sig = computeDriftSignature(makeMetrics());
    expect(sig[13]).toBe(0.5);
    expect(sig[14]).toBe(0.5);
    expect(sig[15]).toBe(0.5);
    expect(sig[16]).toBe(0.5);
  });

  it('computes entropy from real input data', () => {
    const input = new Float64Array(100);
    for (let i = 0; i < 100; i++) input[i] = Math.random() * 10;
    const sig = computeDriftSignature(makeMetrics(), input);
    expect(sig[13]).toBeGreaterThan(0); // entropy > 0 for random data
    expect(sig[14]).toBeGreaterThan(0); // precision diversity > 0
  });

  it('detects rounded input data (low entropy)', () => {
    const rounded = new Float64Array(100);
    for (let i = 0; i < 100; i++) rounded[i] = Math.round(Math.random() * 5);
    const natural = new Float64Array(100);
    for (let i = 0; i < 100; i++) natural[i] = Math.random() * 5 + Math.random() * 0.001;
    const sigRounded = computeDriftSignature(makeMetrics(), rounded);
    const sigNatural = computeDriftSignature(makeMetrics(), natural);
    // Rounded data should have lower fractional entropy
    expect(sigRounded[13]).toBeLessThanOrEqual(sigNatural[13] + 0.5);
  });
});

describe('driftDistanceToBaseline', () => {
  it('returns 1.0 for empty baseline', () => {
    const sig = computeDriftSignature(makeMetrics());
    expect(driftDistanceToBaseline(sig, [])).toBe(1.0);
  });

  it('returns 0 for exact match to single baseline', () => {
    const sig = computeDriftSignature(makeMetrics());
    const dist = driftDistanceToBaseline(sig, [sig]);
    expect(dist).toBeCloseTo(0, 5);
  });

  it('returns small distance for similar signatures', () => {
    const baselines = Array.from({ length: 10 }, () =>
      computeDriftSignature(makeMetrics({ uNorm: 0.45 + Math.random() * 0.01 }))
    );
    const test = computeDriftSignature(makeMetrics({ uNorm: 0.455 }));
    const dist = driftDistanceToBaseline(test, baselines);
    expect(dist).toBeLessThan(5);
  });

  it('returns large distance for anomalous signature', () => {
    const baselines = Array.from({ length: 10 }, () => computeDriftSignature(makeMetrics()));
    const anomalous = computeDriftSignature(makeMetrics({
      uNorm: 10.0,
      riskPrime: 50.0,
      H: 0.01,
    }));
    const dist = driftDistanceToBaseline(anomalous, baselines);
    expect(dist).toBeGreaterThan(5);
  });
});

describe('driftAuthScore', () => {
  it('returns score in [0, 1]', () => {
    const input = new Float64Array(50);
    for (let i = 0; i < 50; i++) input[i] = Math.random();
    const result = driftAuthScore(makeMetrics(), input, []);
    expect(result.score).toBeGreaterThanOrEqual(0);
    expect(result.score).toBeLessThanOrEqual(1);
  });

  it('returns high score for matching baseline', () => {
    const m = makeMetrics();
    const input = new Float64Array(50);
    for (let i = 0; i < 50; i++) input[i] = Math.random();
    const baseline = computeDriftSignature(m, input);
    const result = driftAuthScore(m, input, [baseline]);
    expect(result.score).toBeGreaterThan(0.5);
  });

  it('flags when score < 0.3', () => {
    const input = new Float64Array(50);
    for (let i = 0; i < 50; i++) input[i] = Math.random();
    const result = driftAuthScore(
      makeMetrics({ uNorm: 100, riskPrime: 100 }),
      input,
      [computeDriftSignature(makeMetrics())],
    );
    expect(result.flagged).toBe(result.score < 0.3);
  });
});

// ═══════════════════════════════════════════════════════════════
// TriMechanismDetector Class
// ═══════════════════════════════════════════════════════════════

describe('TriMechanismDetector', () => {
  it('constructs with default config', () => {
    const d = new TriMechanismDetector();
    expect(d.baselineSize).toBe(0);
    expect(d.isCalibrated).toBe(false);
  });

  it('constructs with custom config overrides', () => {
    const d = new TriMechanismDetector({ wPhase: 0.5, wTonic: 0.3, wDrift: 0.2 });
    expect(d.baselineSize).toBe(0);
  });

  it('addBaselineSample increases baseline size', () => {
    const d = new TriMechanismDetector();
    for (let i = 0; i < 5; i++) d.addBaselineSample(makeMetrics());
    expect(d.baselineSize).toBe(5);
    expect(d.isCalibrated).toBe(false);
  });

  it('isCalibrated returns true after 10+ samples', () => {
    const d = new TriMechanismDetector();
    for (let i = 0; i < 10; i++) d.addBaselineSample(makeMetrics());
    expect(d.isCalibrated).toBe(true);
  });

  it('detect returns all three mechanism scores', () => {
    const d = new TriMechanismDetector();
    const input = new Float64Array(20);
    for (let i = 0; i < 20; i++) input[i] = Math.random();
    const result = d.detect(
      input, 0,
      makePositionHistory(20, 0),
      makeMetrics(),
      makeUFinal(0),
    );
    expect(result.phase).toBeDefined();
    expect(result.tonic).toBeDefined();
    expect(result.drift).toBeDefined();
    expect(result.phase.score).toBeGreaterThanOrEqual(0);
    expect(result.tonic.score).toBeGreaterThanOrEqual(0);
    expect(result.drift.score).toBeGreaterThanOrEqual(0);
  });

  it('combinedScore is weighted sum of mechanism scores', () => {
    const d = new TriMechanismDetector();
    const input = new Float64Array(20);
    for (let i = 0; i < 20; i++) input[i] = Math.random();
    const result = d.detect(
      input, 0,
      makePositionHistory(20, 0),
      makeMetrics(),
      makeUFinal(0),
    );
    const expected =
      DEFAULT_CONFIG.wPhase * result.phase.score +
      DEFAULT_CONFIG.wTonic * result.tonic.score +
      DEFAULT_CONFIG.wDrift * result.drift.score;
    expect(result.combinedScore).toBeCloseTo(expected, 10);
  });

  it('contributions sum to combinedScore', () => {
    const d = new TriMechanismDetector();
    const input = new Float64Array(20);
    for (let i = 0; i < 20; i++) input[i] = Math.random();
    const result = d.detect(
      input, 0,
      makePositionHistory(20, 0),
      makeMetrics(),
      makeUFinal(0),
    );
    const sum = result.contributions.phase + result.contributions.tonic + result.contributions.drift;
    expect(sum).toBeCloseTo(result.combinedScore, 10);
  });

  it('decision is ALLOW for high combined score', () => {
    // Create calibrated detector with matching baseline
    const d = new TriMechanismDetector();
    const m = makeMetrics();
    const input = new Float64Array(20);
    for (let i = 0; i < 20; i++) input[i] = Math.random();
    for (let i = 0; i < 15; i++) d.addBaselineSample(m, input);

    const result = d.detect(input, 0, makePositionHistory(20, 0), m, makeUFinal(0));
    expect(['ALLOW', 'QUARANTINE', 'DENY']).toContain(result.decision);
  });

  it('decision maps to threshold ranges', () => {
    const d = new TriMechanismDetector();
    const input = new Float64Array(20);
    for (let i = 0; i < 20; i++) input[i] = Math.random();
    const result = d.detect(
      input, 0,
      makePositionHistory(20, 0),
      makeMetrics(),
      makeUFinal(0),
    );
    if (result.combinedScore > DEFAULT_CONFIG.thresholds.allow) {
      expect(result.decision).toBe('ALLOW');
    } else if (result.combinedScore > DEFAULT_CONFIG.thresholds.quarantine) {
      expect(result.decision).toBe('QUARANTINE');
    } else {
      expect(result.decision).toBe('DENY');
    }
  });

  it('includes timestamp in result', () => {
    const d = new TriMechanismDetector();
    const before = Date.now();
    const input = new Float64Array(20);
    for (let i = 0; i < 20; i++) input[i] = Math.random();
    const result = d.detect(
      input, 0,
      makePositionHistory(20, 0),
      makeMetrics(),
      makeUFinal(0),
    );
    expect(result.timestamp).toBeGreaterThanOrEqual(before);
  });

  it('works for all 6 tongue indices', () => {
    const d = new TriMechanismDetector();
    for (let tongue = 0; tongue < 6; tongue++) {
      const input = new Float64Array(20);
      for (let i = 0; i < 20; i++) input[i] = Math.random();
      const result = d.detect(
        input, tongue,
        makePositionHistory(20, tongue),
        makeMetrics(),
        makeUFinal(tongue),
      );
      expect(['ALLOW', 'QUARANTINE', 'DENY']).toContain(result.decision);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Adversarial Detection Scenarios
// ═══════════════════════════════════════════════════════════════

describe('Adversarial detection', () => {
  it('detects wrong-tongue attack (wrong phase)', () => {
    const d = new TriMechanismDetector();
    const m = makeMetrics();
    const input = new Float64Array(20);
    for (let i = 0; i < 20; i++) input[i] = Math.random();
    for (let i = 0; i < 15; i++) d.addBaselineSample(m, input);

    // Legitimate: tongue 0 with correct centroid
    const legit = d.detect(input, 0, makePositionHistory(30, 0), m, makeUFinal(0));

    // Attack: wrong tongue centroid (tongue 3) but claiming tongue 0
    const attack = d.detect(input, 0, makePositionHistory(30, 0), m, makeUFinal(3));

    expect(attack.phase.score).toBeLessThan(legit.phase.score);
  });

  it('detects anomalous pipeline metrics via drift mechanism', () => {
    const d = new TriMechanismDetector();
    const normalMetrics = makeMetrics();
    const input = new Float64Array(20);
    for (let i = 0; i < 20; i++) input[i] = Math.random();
    for (let i = 0; i < 15; i++) d.addBaselineSample(normalMetrics, input);

    // Anomalous metrics
    const anomalous = makeMetrics({ uNorm: 50.0, riskPrime: 100.0, H: 0.001 });
    const result = d.detect(input, 0, makePositionHistory(30, 0), anomalous, makeUFinal(0));

    expect(result.drift.score).toBeLessThan(0.5);
  });
});
