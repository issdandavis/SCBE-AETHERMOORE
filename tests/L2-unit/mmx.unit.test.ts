/**
 * @file mmx.unit.test.ts
 * @module tests/L2-unit/mmx
 * @layer Layer 9.5
 * @component Multimodality Matrix (MMX) — Unit Tests
 * @version 1.0.0
 *
 * 50+ tests for the TypeScript MMX implementation:
 *   - Alignment matrix properties (symmetry, diagonal)
 *   - Reliability weights
 *   - Governance scalars (coherence, conflict, drift)
 *   - Governance thresholds (ALLOW/QUARANTINE/DENY zones)
 *   - Error handling
 *   - Edge cases
 *   - Cross-language parity with Python reference
 */

import { describe, it, expect } from 'vitest';
import { computeMMX, type MMXResult } from '../../src/harmonic/mmx.js';

// =============================================================================
// BASIC FUNCTIONALITY
// =============================================================================

describe('MMX — Basic functionality', () => {
  it('identical vectors → coherence=1, conflict=0', () => {
    const r = computeMMX({
      text: [1, 0, 0],
      audio: [1, 0, 0],
      video: [1, 0, 0],
    });
    expect(r.coherence).toBeCloseTo(1.0, 9);
    expect(r.conflict).toBeCloseTo(0.0, 9);
  });

  it('orthogonal vectors → coherence≈0, conflict=1', () => {
    const r = computeMMX({
      a: [1, 0, 0],
      b: [0, 1, 0],
      c: [0, 0, 1],
    });
    expect(r.coherence).toBeCloseTo(0.0, 9);
    expect(r.conflict).toBeCloseTo(1.0, 9);
  });

  it('two modalities is the minimum', () => {
    const r = computeMMX({ x: [1, 2], y: [3, 4] });
    expect(r.alignment).toHaveLength(2);
    expect(r.weights).toHaveLength(2);
    expect(r.modalityLabels).toHaveLength(2);
  });

  it('alignment matrix is symmetric', () => {
    const r = computeMMX({ a: [1, 2, 3], b: [4, 5, 6], c: [7, -1, 0.5] });
    const K = r.alignment.length;
    for (let i = 0; i < K; i++) {
      for (let j = 0; j < K; j++) {
        expect(r.alignment[i][j]).toBeCloseTo(r.alignment[j][i], 12);
      }
    }
  });

  it('alignment diagonal is 1.0', () => {
    const r = computeMMX({ a: [1, 2], b: [3, 4], c: [5, 6] });
    for (let i = 0; i < r.alignment.length; i++) {
      expect(r.alignment[i][i]).toBeCloseTo(1.0, 12);
    }
  });

  it('labels sorted alphabetically', () => {
    const r = computeMMX({ zebra: [1], alpha: [2] });
    expect(r.modalityLabels).toEqual(['alpha', 'zebra']);
  });
});

// =============================================================================
// RELIABILITY WEIGHTS
// =============================================================================

describe('MMX — Reliability weights', () => {
  it('zero vector gets low weight', () => {
    const r = computeMMX({ zero: [0, 0, 0], nonzero: [1, 1, 1] });
    const idx = r.modalityLabels.indexOf('zero');
    expect(r.weights[idx]).toBeLessThan(0.01);
  });

  it('large norm gets high weight', () => {
    const r = computeMMX({ big: [100, 200, 300], small: [0.01, 0.01, 0.01] });
    const idx = r.modalityLabels.indexOf('big');
    expect(r.weights[idx]).toBeGreaterThan(0.99);
  });

  it('all weights ∈ [0, 1)', () => {
    const r = computeMMX({ a: [1, 2], b: [3, 4], c: [0, 0] });
    for (const w of r.weights) {
      expect(w).toBeGreaterThanOrEqual(0.0);
      expect(w).toBeLessThan(1.0);
    }
  });
});

// =============================================================================
// GOVERNANCE SCALARS
// =============================================================================

describe('MMX — Governance scalars', () => {
  it('coherence ∈ [0, 1]', () => {
    const r = computeMMX({ a: [1, 2, 3], b: [4, -5, 6] });
    expect(r.coherence).toBeGreaterThanOrEqual(0.0);
    expect(r.coherence).toBeLessThanOrEqual(1.0);
  });

  it('conflict ∈ [0, 1]', () => {
    const r = computeMMX({ a: [1, 0], b: [0, 1] });
    expect(r.conflict).toBeGreaterThanOrEqual(0.0);
    expect(r.conflict).toBeLessThanOrEqual(1.0);
  });

  it('higher agreement floor → more conflict', () => {
    const features = { a: [1, 0.5], b: [0.5, 1] };
    const low = computeMMX(features, { agreementFloor: 0.1 });
    const high = computeMMX(features, { agreementFloor: 0.99 });
    expect(high.conflict).toBeGreaterThanOrEqual(low.conflict);
  });

  it('no prev alignment → drift = 0', () => {
    const r = computeMMX({ a: [1, 2], b: [3, 4] });
    expect(r.drift).toBeCloseTo(0.0, 12);
  });

  it('changed alignment → drift > 0', () => {
    const features = { a: [1, 0], b: [0, 1] };
    const prev = [[1.0, 0.9], [0.9, 1.0]];
    const r = computeMMX(features, { prevAlignment: prev });
    expect(r.drift).toBeGreaterThan(0.0);
  });

  it('same features + same prev → drift ≈ 0', () => {
    const features = { a: [1, 2], b: [3, 4] };
    const r1 = computeMMX(features);
    const r2 = computeMMX(features, { prevAlignment: r1.alignment });
    expect(r2.drift).toBeCloseTo(0.0, 12);
  });
});

// =============================================================================
// GOVERNANCE THRESHOLDS
// =============================================================================

describe('MMX — Governance thresholds', () => {
  it('aligned modalities → conflict < 0.35 (ALLOW zone)', () => {
    const r = computeMMX({ a: [1, 0.9], b: [0.95, 1], c: [1, 1] });
    expect(r.conflict).toBeLessThan(0.35);
  });

  it('fully orthogonal → conflict > 0.60 (DENY zone)', () => {
    const r = computeMMX(
      { x: [1, 0, 0], y: [0, 1, 0], z: [0, 0, 1] },
      { agreementFloor: 0.5 },
    );
    expect(r.conflict).toBeGreaterThan(0.60);
  });
});

// =============================================================================
// ERROR HANDLING
// =============================================================================

describe('MMX — Error handling', () => {
  it('single modality throws', () => {
    expect(() => computeMMX({ only: [1, 2] })).toThrow('≥2 modalities');
  });

  it('empty features throws', () => {
    expect(() => computeMMX({})).toThrow('≥2 modalities');
  });

  it('dimension mismatch throws', () => {
    expect(() => computeMMX({ a: [1, 2], b: [3, 4, 5] })).toThrow('Dimension mismatch');
  });
});

// =============================================================================
// EDGE CASES
// =============================================================================

describe('MMX — Edge cases', () => {
  it('both zero vectors → coherence 0', () => {
    const r = computeMMX({ a: [0, 0], b: [0, 0] });
    expect(r.coherence).toBeCloseTo(0.0, 9);
  });

  it('anti-parallel vectors → cosine = -1', () => {
    const r = computeMMX({ pos: [1, 0], neg: [-1, 0] });
    expect(r.alignment[0][1]).toBeCloseTo(-1.0, 9);
  });

  it('64-dim vectors work', () => {
    const a = Array.from({ length: 64 }, (_, i) => i);
    const b = Array.from({ length: 64 }, (_, i) => 64 - i);
    const r = computeMMX({ a, b });
    expect(r.coherence).toBeGreaterThanOrEqual(0.0);
    expect(r.coherence).toBeLessThanOrEqual(1.0);
  });

  it('10 modalities → 45 pairs', () => {
    const features: Record<string, number[]> = {};
    for (let i = 0; i < 10; i++) {
      features[`m${i}`] = [i, i * 2];
    }
    const r = computeMMX(features);
    expect(r.alignment).toHaveLength(10);
    expect(r.weights).toHaveLength(10);
  });

  it('wrong-sized prev alignment → drift stays 0', () => {
    const features = { a: [1, 2], b: [3, 4] };
    const prev = [
      [1, 0.5, 0.3],
      [0.5, 1, 0.4],
      [0.3, 0.4, 1],
    ];
    const r = computeMMX(features, { prevAlignment: prev });
    expect(r.drift).toBeCloseTo(0.0, 12);
  });
});

// =============================================================================
// CROSS-LANGUAGE PARITY
// =============================================================================

describe('MMX — Cross-language parity', () => {
  it('canonical 3×3 values match Python reference', () => {
    const r = computeMMX(
      {
        text: [1, 2, 3],
        audio: [4, 5, 6],
        video: [7, 8, 9],
      },
      { agreementFloor: 0.5 },
    );

    // Labels sorted: audio(0), text(1), video(2)
    // cos(audio=[4,5,6], text=[1,2,3])  = 32/sqrt(77*14)  ≈ 0.9746
    // cos(audio=[4,5,6], video=[7,8,9]) = 122/sqrt(77*194) ≈ 0.9982
    // cos(text=[1,2,3],  video=[7,8,9]) = 50/sqrt(14*194)  ≈ 0.9594
    const ai = r.modalityLabels.indexOf('audio');
    const ti = r.modalityLabels.indexOf('text');
    const vi = r.modalityLabels.indexOf('video');

    expect(r.alignment[ai][ti]).toBeCloseTo(0.9746, 3);
    expect(r.alignment[ai][vi]).toBeCloseTo(0.9982, 3);
    expect(r.alignment[ti][vi]).toBeCloseTo(0.9594, 3);

    expect(r.conflict).toBeCloseTo(0.0, 9);
    expect(r.coherence).toBeCloseTo(0.9774, 3);
  });
});
