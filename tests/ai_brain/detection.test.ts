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
});
