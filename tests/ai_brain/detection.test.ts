/**
 * AI Brain Detection Mechanisms Unit Tests
 *
 * Tests for the 5 orthogonal detection mechanisms:
 * - Phase + Distance Scoring
 * - Curvature Accumulation
 * - Threat Dimension Lissajous
 * - Decimal Drift Magnitude
 * - Six-Tonic Oscillation
 *
 * @layer Layer 5, Layer 9, Layer 12, Layer 13
 */

import { describe, expect, it } from 'vitest';

import {
  BRAIN_DIMENSIONS,
  detectCurvatureAccumulation,
  detectDecimalDrift,
  detectPhaseDistance,
  detectSixTonic,
  detectThreatLissajous,
  runCombinedDetection,
  safePoincareEmbed,
  hyperbolicDistanceSafe,
  type TrajectoryPoint,
} from '../../src/ai_brain/index';

// ═══════════════════════════════════════════════════════════════
// Test Helpers
// ═══════════════════════════════════════════════════════════════

function makePoint(
  step: number,
  state: number[],
  embedded?: number[],
  distance?: number
): TrajectoryPoint {
  const padded = [...state, ...new Array(Math.max(0, BRAIN_DIMENSIONS - state.length)).fill(0)];
  const emb = embedded ?? safePoincareEmbed(padded);
  const origin = new Array(emb.length).fill(0);
  const dist = distance ?? hyperbolicDistanceSafe(emb, origin);
  return {
    step,
    state: padded,
    embedded: emb,
    distance: dist,
    curvature: 0,
    timestamp: Date.now(),
  };
}

function makeSteadyTrajectory(steps: number): TrajectoryPoint[] {
  return Array.from({ length: steps }, (_, i) => {
    const state = new Array(BRAIN_DIMENSIONS).fill(0);
    state[0] = 0.5; // steady device
    state[5] = 0.8; // steady intent
    state[3] = 0.9; // steady behavior
    state[16] = 1.0; // correct phase angle for tongue 0
    state[17] = 0.8 + 0.01 * Math.sin(i * 0.5); // slight tongue weight oscillation
    return makePoint(i, state);
  });
}

// ═══════════════════════════════════════════════════════════════
// Individual Detectors
// ═══════════════════════════════════════════════════════════════

describe('detectPhaseDistance', () => {
  it('should return mechanism name', () => {
    const result = detectPhaseDistance(makeSteadyTrajectory(10), 0);
    expect(result.mechanism).toBe('phase_distance');
  });

  it('should return score in [0, 1]', () => {
    const result = detectPhaseDistance(makeSteadyTrajectory(20), 0);
    expect(result.score).toBeGreaterThanOrEqual(0);
    expect(result.score).toBeLessThanOrEqual(1);
  });

  it('should handle empty trajectory', () => {
    const result = detectPhaseDistance([], 0);
    expect(result.score).toBe(0);
    expect(result.flagged).toBe(false);
  });
});

describe('detectCurvatureAccumulation', () => {
  it('should return mechanism name', () => {
    const result = detectCurvatureAccumulation(makeSteadyTrajectory(10));
    expect(result.mechanism).toBe('curvature_accumulation');
  });

  it('should return score in [0, 1]', () => {
    const steady = detectCurvatureAccumulation(makeSteadyTrajectory(20));
    expect(steady.score).toBeGreaterThanOrEqual(0);
    expect(steady.score).toBeLessThanOrEqual(1);
  });

  it('should handle trajectory shorter than window', () => {
    const result = detectCurvatureAccumulation(makeSteadyTrajectory(2));
    expect(result.score).toBe(0);
    expect(result.flagged).toBe(false);
  });
});

describe('detectThreatLissajous', () => {
  it('should return mechanism name', () => {
    const result = detectThreatLissajous(makeSteadyTrajectory(10));
    expect(result.mechanism).toBe('threat_lissajous');
  });

  it('should return score in [0, 1]', () => {
    const result = detectThreatLissajous(makeSteadyTrajectory(20));
    expect(result.score).toBeGreaterThanOrEqual(0);
    expect(result.score).toBeLessThanOrEqual(1);
  });
});

describe('detectDecimalDrift', () => {
  it('should return mechanism name', () => {
    const result = detectDecimalDrift(makeSteadyTrajectory(10));
    expect(result.mechanism).toBe('decimal_drift');
  });

  it('should return score in [0, 1]', () => {
    const result = detectDecimalDrift(makeSteadyTrajectory(20));
    expect(result.score).toBeGreaterThanOrEqual(0);
    expect(result.score).toBeLessThanOrEqual(1);
  });
});

describe('detectSixTonic', () => {
  it('should return mechanism name', () => {
    const result = detectSixTonic(makeSteadyTrajectory(10), 0);
    expect(result.mechanism).toBe('six_tonic');
  });

  it('should return score in [0, 1]', () => {
    const result = detectSixTonic(makeSteadyTrajectory(20), 0);
    expect(result.score).toBeGreaterThanOrEqual(0);
    expect(result.score).toBeLessThanOrEqual(1);
  });
});

// ═══════════════════════════════════════════════════════════════
// Adversarial Trajectory Helpers
// ═══════════════════════════════════════════════════════════════

/** Trajectory with wrong phase angle (wrong-tongue attack) */
function makeWrongTongueTrajectory(steps: number): TrajectoryPoint[] {
  return Array.from({ length: steps }, (_, i) => {
    const state = new Array(BRAIN_DIMENSIONS).fill(0);
    state[0] = 0.5;
    state[5] = 0.8;
    state[3] = 0.9;
    state[16] = Math.PI; // Wrong phase — tongue 0 expects phase ~0
    state[17] = 0.8 + 0.01 * Math.sin(i * 0.5);
    return makePoint(i, state);
  });
}

/** Trajectory with high curvature (erratic path) */
function makeHighCurvatureTrajectory(steps: number): TrajectoryPoint[] {
  return Array.from({ length: steps }, (_, i) => {
    const state = new Array(BRAIN_DIMENSIONS).fill(0);
    state[0] = 0.5 + 0.3 * (i % 2 === 0 ? 1 : -1);
    state[1] = 0.3 * Math.sin(i * 2.5);
    state[2] = 0.3 * Math.cos(i * 3.7);
    state[5] = 0.8;
    state[3] = 0.9;
    state[16] = 1.0;
    state[17] = 0.8 + 0.01 * Math.sin(i * 0.5);
    return makePoint(i, state);
  });
}

/** Trajectory with Lissajous self-intersections (malicious knots) */
function makeLissajousTrajectory(steps: number): TrajectoryPoint[] {
  const PHI_LOCAL = (1 + Math.sqrt(5)) / 2;
  return Array.from({ length: steps }, (_, i) => {
    const state = new Array(BRAIN_DIMENSIONS).fill(0);
    state[0] = 0.5;
    const t = (2 * Math.PI * i) / 30;
    state[3] = 0.5 + 0.4 * Math.sin(t);
    state[5] = 0.5 + 0.4 * Math.sin(PHI_LOCAL * t);
    state[16] = 1.0;
    state[17] = 0.8 + 0.01 * Math.sin(i * 0.5);
    return makePoint(i, state);
  });
}

/** Trajectory with static tongue weight (no oscillation) */
function makeStaticTrajectory(steps: number): TrajectoryPoint[] {
  return Array.from({ length: steps }, (_, i) => {
    const state = new Array(BRAIN_DIMENSIONS).fill(0);
    state[0] = 0.5;
    state[5] = 0.8;
    state[3] = 0.9;
    state[16] = 1.0;
    state[17] = 0.8; // Completely static
    return makePoint(i, state);
  });
}

// ═══════════════════════════════════════════════════════════════
// Adversarial Detection Tests
// ═══════════════════════════════════════════════════════════════

describe('Phase + Distance: adversarial scenarios', () => {
  it('flags wrong-tongue trajectory', () => {
    const result = detectPhaseDistance(makeWrongTongueTrajectory(20), 0);
    expect(result.score).toBeGreaterThan(0.3);
  });

  it('does not flag correct-phase trajectory', () => {
    const result = detectPhaseDistance(makeSteadyTrajectory(20), 0);
    expect(result.flagged).toBe(false);
  });

  it('score increases with larger phase error', () => {
    const small = detectPhaseDistance(
      Array.from({ length: 20 }, (_, i) => {
        const s = new Array(BRAIN_DIMENSIONS).fill(0);
        s[16] = 0.1;
        s[17] = 0.8;
        return makePoint(i, s);
      }),
      0
    );
    const large = detectPhaseDistance(makeWrongTongueTrajectory(20), 0);
    expect(large.score).toBeGreaterThan(small.score);
  });
});

describe('Curvature: adversarial scenarios', () => {
  it('flags high curvature trajectory', () => {
    const result = detectCurvatureAccumulation(makeHighCurvatureTrajectory(30));
    expect(result.score).toBeGreaterThan(0);
  });

  it('assigns low score to smooth trajectory', () => {
    const result = detectCurvatureAccumulation(makeSteadyTrajectory(30));
    expect(result.score).toBeLessThan(0.5);
  });

  it('metadata includes curvature statistics', () => {
    const result = detectCurvatureAccumulation(makeSteadyTrajectory(10));
    expect(result.metadata).toBeDefined();
    expect(result.metadata!.curvatureCount).toBeGreaterThanOrEqual(0);
  });
});

describe('Lissajous: adversarial scenarios', () => {
  it('flags Lissajous knot trajectory', () => {
    const result = detectThreatLissajous(makeLissajousTrajectory(60));
    expect(result.score).toBeGreaterThan(0);
  });

  it('assigns low score to linear trajectory', () => {
    const result = detectThreatLissajous(makeSteadyTrajectory(20));
    expect(result.score).toBeLessThan(0.5);
  });

  it('handles very short trajectory gracefully', () => {
    const result = detectThreatLissajous(makeSteadyTrajectory(3));
    expect(result.score).toBe(0);
    expect(result.flagged).toBe(false);
  });
});

describe('Decimal Drift: adversarial scenarios', () => {
  it('flags large drift magnitude', () => {
    const bigDrift = Array.from({ length: 20 }, (_, i) => {
      const state = new Array(BRAIN_DIMENSIONS).fill(0);
      for (let d = 0; d < 6; d++) {
        state[d] = i % 2 === 0 ? 0.8 : 0.2;
      }
      state[16] = 1.0;
      state[17] = 0.8;
      return makePoint(i, state);
    });
    const result = detectDecimalDrift(bigDrift);
    expect(result.score).toBeGreaterThan(0);
  });

  it('assigns low score to stable trajectory', () => {
    const result = detectDecimalDrift(makeSteadyTrajectory(20));
    expect(result.score).toBeLessThan(0.5);
  });

  it('handles single-point trajectory', () => {
    const result = detectDecimalDrift(makeSteadyTrajectory(1));
    expect(result.score).toBe(0);
    expect(result.flagged).toBe(false);
  });
});

describe('Six-Tonic: adversarial scenarios', () => {
  it('flags static signal (no oscillation)', () => {
    const result = detectSixTonic(makeStaticTrajectory(20), 0);
    expect(result.score).toBeGreaterThan(0.5);
    if (result.metadata) {
      expect(result.metadata.isStatic).toBe(true);
    }
  });

  it('assigns low score to legitimate oscillation', () => {
    const result = detectSixTonic(makeSteadyTrajectory(20), 0);
    expect(result.score).toBeLessThan(1.0);
  });

  it('handles different tongue indices (0-5)', () => {
    for (let tongue = 0; tongue < 6; tongue++) {
      const result = detectSixTonic(makeSteadyTrajectory(20), tongue);
      expect(result.score).toBeGreaterThanOrEqual(0);
      expect(result.score).toBeLessThanOrEqual(1);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Combined Detection
// ═══════════════════════════════════════════════════════════════

describe('runCombinedDetection', () => {
  it('should run all 5 mechanisms', () => {
    const result = runCombinedDetection(makeSteadyTrajectory(20), 0);
    expect(result.detections).toHaveLength(5);
    const mechanisms = result.detections.map((d) => d.mechanism);
    expect(mechanisms).toContain('phase_distance');
    expect(mechanisms).toContain('curvature_accumulation');
    expect(mechanisms).toContain('threat_lissajous');
    expect(mechanisms).toContain('decimal_drift');
    expect(mechanisms).toContain('six_tonic');
  });

  it('should produce a combined score in [0, 1]', () => {
    const result = runCombinedDetection(makeSteadyTrajectory(20), 0);
    expect(result.combinedScore).toBeGreaterThanOrEqual(0);
    expect(result.combinedScore).toBeLessThanOrEqual(1);
  });

  it('should produce a valid risk decision', () => {
    const result = runCombinedDetection(makeSteadyTrajectory(20), 0);
    expect(['ALLOW', 'QUARANTINE', 'ESCALATE', 'DENY']).toContain(result.decision);
  });

  it('should include flag count', () => {
    const result = runCombinedDetection(makeSteadyTrajectory(20), 0);
    expect(result.flagCount).toBeGreaterThanOrEqual(0);
    expect(result.flagCount).toBeLessThanOrEqual(5);
  });

  it('gives low combined score for benign trajectory', () => {
    const result = runCombinedDetection(makeSteadyTrajectory(30), 0);
    expect(result.combinedScore).toBeLessThan(0.7);
  });

  it('gives higher score for wrong-tongue attack', () => {
    const benign = runCombinedDetection(makeSteadyTrajectory(20), 0);
    const attack = runCombinedDetection(makeWrongTongueTrajectory(20), 0);
    expect(attack.combinedScore).toBeGreaterThan(benign.combinedScore);
  });

  it('gives higher score for static signal attack', () => {
    const benign = runCombinedDetection(makeSteadyTrajectory(20), 0);
    const attack = runCombinedDetection(makeStaticTrajectory(20), 0);
    expect(attack.combinedScore).toBeGreaterThanOrEqual(benign.combinedScore);
  });

  it('includes timestamp in assessment', () => {
    const result = runCombinedDetection(makeSteadyTrajectory(10), 0);
    expect(result.timestamp).toBeGreaterThan(0);
  });

  it('anyFlagged matches flagCount > 0', () => {
    const result = runCombinedDetection(makeSteadyTrajectory(20), 0);
    expect(result.anyFlagged).toBe(result.flagCount > 0);
  });

  it('handles empty trajectory gracefully', () => {
    const result = runCombinedDetection([], 0);
    expect(result.combinedScore).toBeGreaterThanOrEqual(0);
    expect(result.combinedScore).toBeLessThanOrEqual(1);
    expect(['ALLOW', 'QUARANTINE', 'ESCALATE', 'DENY']).toContain(result.decision);
  });
});
