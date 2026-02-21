/**
 * @file frecency.test.ts
 * @module tests/harmonic/frecency
 * @layer Layer 14, Layer 12, Layer 11
 * @component Frecency Scoring Engine Tests
 * @version 1.0.0
 *
 * Tests for FrecencyEngine covering:
 *   - Basic recording and scoring
 *   - Frequency contribution to score
 *   - Time-based exponential decay
 *   - Propagation through harmonic scaling (L12)
 *   - Top-K retrieval sorted by score
 *   - Pruning of low-score entries
 *   - Max-entries eviction
 *   - Edge cases: zero coherence, large distances
 */

import { describe, it, expect } from 'vitest';
import { FrecencyEngine } from '../../src/harmonic/frecency.js';

// ─────────────────────────────────────────────────────────────────────────────
// Constants mirroring the source module
// ─────────────────────────────────────────────────────────────────────────────
const EPSILON = 1e-10;
const DEFAULT_ALPHA = 1.0;
const DEFAULT_BETA = 2.0;
const DEFAULT_GAMMA = 1.5;
const DEFAULT_DECAY_LAMBDA = 0.01;

/** Compute the expected increment the same way the source does. */
function expectedIncrement(
  alpha: number,
  beta: number,
  gamma: number,
  frequency: number,
  recency: number,
  coherence: number
): number {
  return alpha * Math.log1p(frequency) + beta * (1 / (recency + EPSILON)) + gamma * coherence;
}

/** Compute H_score from the harmonic propagation formula. */
function hScore(hyperbolicDistance: number, phaseDeviation: number = 0): number {
  return 1 / (1 + hyperbolicDistance + 2 * phaseDeviation);
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. Basic recording and scoring
// ─────────────────────────────────────────────────────────────────────────────
describe('FrecencyEngine - basic recording and scoring', () => {
  it('returns a positive score after the first access', () => {
    const engine = new FrecencyEngine();
    const score = engine.recordAccess('ctx-a', 0.8, 1000);
    expect(score).toBeGreaterThan(0);
  });

  it('getScore returns 0 for an unknown key', () => {
    const engine = new FrecencyEngine();
    expect(engine.getScore('missing', 1000)).toBe(0);
  });

  it('getScore matches score returned by recordAccess (same timestamp)', () => {
    const engine = new FrecencyEngine();
    const now = 5000;
    const recorded = engine.recordAccess('ctx-a', 0.8, now);
    const retrieved = engine.getScore('ctx-a', now);
    expect(retrieved).toBeCloseTo(recorded, 10);
  });

  it('size increases after recording a new key', () => {
    const engine = new FrecencyEngine();
    expect(engine.size).toBe(0);
    engine.recordAccess('a', 0.5, 1000);
    expect(engine.size).toBe(1);
    engine.recordAccess('b', 0.5, 1000);
    expect(engine.size).toBe(2);
  });

  it('size does not increase when re-recording the same key', () => {
    const engine = new FrecencyEngine();
    engine.recordAccess('a', 0.5, 1000);
    engine.recordAccess('a', 0.5, 2000);
    expect(engine.size).toBe(1);
  });

  it('getAllEntries returns a snapshot with one entry per key', () => {
    const engine = new FrecencyEngine();
    engine.recordAccess('x', 0.5, 1000);
    engine.recordAccess('y', 0.5, 1000);
    const entries = engine.getAllEntries();
    expect(entries).toHaveLength(2);
    const keys = entries.map((e) => e.key).sort();
    expect(keys).toEqual(['x', 'y']);
  });

  it('clear removes all entries', () => {
    const engine = new FrecencyEngine();
    engine.recordAccess('a', 0.5, 1000);
    engine.recordAccess('b', 0.5, 1000);
    engine.clear();
    expect(engine.size).toBe(0);
    expect(engine.getAllEntries()).toHaveLength(0);
  });

  it('first-access score matches expected increment formula', () => {
    const engine = new FrecencyEngine();
    const now = 1000;
    const coherence = 0.8;
    const score = engine.recordAccess('ctx', coherence, now);

    // First access: frequency=1, recency=1.0
    const expected = expectedIncrement(DEFAULT_ALPHA, DEFAULT_BETA, DEFAULT_GAMMA, 1, 1.0, coherence);
    expect(score).toBeCloseTo(expected, 8);
  });

  it('records lastAccessedAt correctly', () => {
    const engine = new FrecencyEngine();
    const now = 42000;
    engine.recordAccess('ctx', 0.8, now);
    const entries = engine.getAllEntries();
    expect(entries[0].lastAccessedAt).toBe(now);
  });

  it('records frequency=1 on first access', () => {
    const engine = new FrecencyEngine();
    engine.recordAccess('ctx', 0.8, 1000);
    const entries = engine.getAllEntries();
    expect(entries[0].frequency).toBe(1);
  });

  it('records coherence correctly on first access', () => {
    const engine = new FrecencyEngine();
    engine.recordAccess('ctx', 0.65, 1000);
    const entries = engine.getAllEntries();
    expect(entries[0].coherence).toBe(0.65);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 2. Frequency increases score
// ─────────────────────────────────────────────────────────────────────────────
describe('FrecencyEngine - frequency contribution', () => {
  it('score increases after a second access (same timestamp = no decay)', () => {
    const engine = new FrecencyEngine();
    const t0 = 1000;
    const score1 = engine.recordAccess('ctx', 0.8, t0);
    // Second access at the same ms so decay is zero
    const score2 = engine.recordAccess('ctx', 0.8, t0);
    expect(score2).toBeGreaterThan(score1);
  });

  it('frequency field increments on each access', () => {
    const engine = new FrecencyEngine();
    engine.recordAccess('ctx', 0.8, 1000);
    engine.recordAccess('ctx', 0.8, 1000);
    engine.recordAccess('ctx', 0.8, 1000);
    const entries = engine.getAllEntries();
    expect(entries[0].frequency).toBe(3);
  });

  it('score grows monotonically with repeated accesses (no time gap)', () => {
    const engine = new FrecencyEngine();
    const t = 1000;
    let prev = -Infinity;
    for (let i = 0; i < 10; i++) {
      const score = engine.recordAccess('ctx', 0.8, t);
      expect(score).toBeGreaterThan(prev);
      prev = score;
    }
  });

  it('log1p(frequency) grows sub-linearly: each unit of frequency adds less to log1p', () => {
    // Verify that log1p itself is sub-linear (core mathematical property)
    const increments: number[] = [];
    for (let freq = 1; freq <= 5; freq++) {
      increments.push(Math.log1p(freq) - Math.log1p(freq - 1));
    }
    // Each increment in log1p should be smaller than the previous
    for (let i = 1; i < increments.length; i++) {
      expect(increments[i]).toBeLessThan(increments[i - 1] + 1e-9);
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 3. Time-based decay
// ─────────────────────────────────────────────────────────────────────────────
describe('FrecencyEngine - time-based exponential decay', () => {
  it('getScore decreases as time advances after recording', () => {
    const engine = new FrecencyEngine({ decayLambda: 0.01 });
    const t0 = 0;
    engine.recordAccess('ctx', 0.8, t0);

    const scoreAt0 = engine.getScore('ctx', t0);
    const scoreAt10s = engine.getScore('ctx', t0 + 10_000); // 10 seconds later
    const scoreAt60s = engine.getScore('ctx', t0 + 60_000); // 60 seconds later

    expect(scoreAt10s).toBeLessThan(scoreAt0);
    expect(scoreAt60s).toBeLessThan(scoreAt10s);
  });

  it('getScore follows e^(-λ·Δt) decay formula exactly', () => {
    const lambda = 0.05;
    const engine = new FrecencyEngine({ decayLambda: lambda });
    const t0 = 0;
    const score0 = engine.recordAccess('ctx', 0.8, t0);

    const deltaSeconds = 20;
    const expected = score0 * Math.exp(-lambda * deltaSeconds);
    const actual = engine.getScore('ctx', t0 + deltaSeconds * 1000);

    expect(actual).toBeCloseTo(expected, 8);
  });

  it('score at time of recording is not decayed', () => {
    const engine = new FrecencyEngine({ decayLambda: 0.1 });
    const t0 = 12345;
    const recorded = engine.recordAccess('ctx', 0.8, t0);
    const retrieved = engine.getScore('ctx', t0);
    expect(retrieved).toBeCloseTo(recorded, 10);
  });

  it('decay with lambda=0 produces no decay', () => {
    const engine = new FrecencyEngine({ decayLambda: 0 });
    const t0 = 0;
    const score0 = engine.recordAccess('ctx', 0.8, t0);

    const scoreAfter = engine.getScore('ctx', t0 + 1_000_000);
    expect(scoreAfter).toBeCloseTo(score0, 8);
  });

  it('higher lambda decays faster', () => {
    const slowEngine = new FrecencyEngine({ decayLambda: 0.001 });
    const fastEngine = new FrecencyEngine({ decayLambda: 1.0 });
    const t0 = 0;
    const coherence = 0.8;
    slowEngine.recordAccess('ctx', coherence, t0);
    fastEngine.recordAccess('ctx', coherence, t0);

    const elapsed = 5_000; // 5 seconds
    const slowScore = slowEngine.getScore('ctx', t0 + elapsed);
    const fastScore = fastEngine.getScore('ctx', t0 + elapsed);

    expect(fastScore).toBeLessThan(slowScore);
  });

  it('recordAccess applies decay to existing score before adding increment', () => {
    const lambda = 0.1;
    const engine = new FrecencyEngine({ decayLambda: lambda });
    const t0 = 0;
    const score0 = engine.recordAccess('ctx', 0.8, t0);

    const deltaSeconds = 10;
    const t1 = t0 + deltaSeconds * 1000;
    const decayedPrior = score0 * Math.exp(-lambda * deltaSeconds);
    // frequency becomes 2, recency=1.0
    const increment = expectedIncrement(DEFAULT_ALPHA, DEFAULT_BETA, DEFAULT_GAMMA, 2, 1.0, 0.8);
    const expectedScore = decayedPrior + increment;

    const actualScore = engine.recordAccess('ctx', 0.8, t1);
    expect(actualScore).toBeCloseTo(expectedScore, 8);
  });

  it('getScore returns 0 for keys that were never recorded', () => {
    const engine = new FrecencyEngine();
    expect(engine.getScore('ghost', Date.now())).toBe(0);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 4. Propagation through harmonic scaling (L12)
// ─────────────────────────────────────────────────────────────────────────────
describe('FrecencyEngine - propagateThroughHarmonic', () => {
  it('propagated score equals frecency * H_score at distance 0 phaseDeviation 0', () => {
    const engine = new FrecencyEngine();
    const t0 = 1000;
    engine.recordAccess('ctx', 0.8, t0);

    const d = 0;
    const pd = 0;
    const propagated = engine.propagateThroughHarmonic('ctx', d, pd, t0);
    const baseFrecency = engine.getScore('ctx', t0);
    const expected = baseFrecency * hScore(d, pd); // H=1.0 at origin

    expect(propagated).toBeCloseTo(expected, 8);
    expect(propagated).toBeCloseTo(baseFrecency, 8);
  });

  it('H_score at origin (d=0, pd=0) equals 1 — propagated equals frecency', () => {
    const engine = new FrecencyEngine();
    const t0 = 0;
    engine.recordAccess('ctx', 0.8, t0);

    const propagated = engine.propagateThroughHarmonic('ctx', 0, 0, t0);
    const base = engine.getScore('ctx', t0);
    expect(propagated).toBeCloseTo(base, 10);
  });

  it('propagated score decreases as hyperbolic distance increases', () => {
    const engine = new FrecencyEngine();
    const t0 = 0;
    engine.recordAccess('ctx', 0.8, t0);

    const p0 = engine.propagateThroughHarmonic('ctx', 0, 0, t0);
    const p1 = engine.propagateThroughHarmonic('ctx', 1, 0, t0);
    const p5 = engine.propagateThroughHarmonic('ctx', 5, 0, t0);

    expect(p0).toBeGreaterThan(p1);
    expect(p1).toBeGreaterThan(p5);
  });

  it('propagated score decreases as phase deviation increases', () => {
    const engine = new FrecencyEngine();
    const t0 = 0;
    engine.recordAccess('ctx', 0.8, t0);

    const d = 1;
    const p0 = engine.propagateThroughHarmonic('ctx', d, 0, t0);
    const p1 = engine.propagateThroughHarmonic('ctx', d, 0.5, t0);
    const p2 = engine.propagateThroughHarmonic('ctx', d, 1.0, t0);

    expect(p0).toBeGreaterThan(p1);
    expect(p1).toBeGreaterThan(p2);
  });

  it('propagated score follows exact formula: frecency / (1 + d + 2*pd)', () => {
    const engine = new FrecencyEngine();
    const t0 = 5000;
    engine.recordAccess('ctx', 0.9, t0);

    const d = 2.5;
    const pd = 0.3;
    const base = engine.getScore('ctx', t0);
    const expected = base / (1 + d + 2 * pd);
    const actual = engine.propagateThroughHarmonic('ctx', d, pd, t0);

    expect(actual).toBeCloseTo(expected, 8);
  });

  it('returns 0 for an unknown key', () => {
    const engine = new FrecencyEngine();
    expect(engine.propagateThroughHarmonic('missing', 1, 0, 1000)).toBe(0);
  });

  it('default phaseDeviation is 0', () => {
    const engine = new FrecencyEngine();
    const t0 = 0;
    engine.recordAccess('ctx', 0.8, t0);

    const withDefault = engine.propagateThroughHarmonic('ctx', 2, undefined, t0);
    const explicit0 = engine.propagateThroughHarmonic('ctx', 2, 0, t0);

    expect(withDefault).toBeCloseTo(explicit0, 10);
  });

  it('very large hyperbolic distance drives propagated score near zero', () => {
    const engine = new FrecencyEngine();
    const t0 = 0;
    engine.recordAccess('ctx', 1.0, t0);

    const propagated = engine.propagateThroughHarmonic('ctx', 1e6, 0, t0);
    expect(propagated).toBeGreaterThan(0);
    expect(propagated).toBeLessThan(1e-4);
  });

  it('large phase deviation drives propagated score near zero', () => {
    const engine = new FrecencyEngine();
    const t0 = 0;
    engine.recordAccess('ctx', 1.0, t0);

    const propagated = engine.propagateThroughHarmonic('ctx', 0, 1e6, t0);
    expect(propagated).toBeGreaterThan(0);
    expect(propagated).toBeLessThan(1e-4);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 5. Top-K retrieval
// ─────────────────────────────────────────────────────────────────────────────
describe('FrecencyEngine - getTopK', () => {
  it('returns exactly k entries when k < size', () => {
    const engine = new FrecencyEngine();
    const t0 = 0;
    for (let i = 0; i < 5; i++) {
      engine.recordAccess(`ctx-${i}`, 0.5, t0);
    }
    expect(engine.getTopK(3, t0)).toHaveLength(3);
  });

  it('returns all entries when k >= size', () => {
    const engine = new FrecencyEngine();
    const t0 = 0;
    engine.recordAccess('a', 0.5, t0);
    engine.recordAccess('b', 0.5, t0);
    const top = engine.getTopK(10, t0);
    expect(top).toHaveLength(2);
  });

  it('results are sorted in descending score order', () => {
    const engine = new FrecencyEngine();
    const t0 = 0;
    // Record 'a' more times so it accumulates a higher score
    engine.recordAccess('a', 0.8, t0);
    engine.recordAccess('a', 0.8, t0);
    engine.recordAccess('a', 0.8, t0);
    engine.recordAccess('b', 0.8, t0);

    const top = engine.getTopK(2, t0);
    expect(top[0].key).toBe('a');
    expect(top[1].key).toBe('b');
    expect(top[0].score).toBeGreaterThanOrEqual(top[1].score);
  });

  it('scores in getTopK reflect decay at the provided timestamp', () => {
    const engine = new FrecencyEngine({ decayLambda: 0.1 });
    const t0 = 0;
    engine.recordAccess('ctx', 0.8, t0);

    const topNow = engine.getTopK(1, t0);
    const topLater = engine.getTopK(1, t0 + 10_000); // 10 s later

    expect(topNow[0].score).toBeGreaterThan(topLater[0].score);
  });

  it('returns empty array when no entries exist', () => {
    const engine = new FrecencyEngine();
    expect(engine.getTopK(5, 0)).toEqual([]);
  });

  it('returns empty array when k=0', () => {
    const engine = new FrecencyEngine();
    engine.recordAccess('a', 0.5, 0);
    expect(engine.getTopK(0, 0)).toEqual([]);
  });

  it('top-1 entry is the most recently and frequently accessed', () => {
    const engine = new FrecencyEngine();
    const t0 = 0;
    // 'hot' gets 5 accesses, 'cold' gets 1
    for (let i = 0; i < 5; i++) {
      engine.recordAccess('hot', 0.8, t0);
    }
    engine.recordAccess('cold', 0.8, t0);

    const top = engine.getTopK(1, t0);
    expect(top[0].key).toBe('hot');
  });

  it('scores returned by getTopK match getScore at same timestamp', () => {
    const engine = new FrecencyEngine();
    const t0 = 3000;
    engine.recordAccess('x', 0.7, t0);
    engine.recordAccess('y', 0.9, t0);

    const top = engine.getTopK(2, t0);
    for (const entry of top) {
      expect(entry.score).toBeCloseTo(engine.getScore(entry.key, t0), 10);
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 6. Pruning
// ─────────────────────────────────────────────────────────────────────────────
describe('FrecencyEngine - prune', () => {
  it('prune removes entries whose decayed score is below threshold', () => {
    const lambda = 1.0; // fast decay
    const engine = new FrecencyEngine({ decayLambda: lambda });
    const t0 = 0;
    engine.recordAccess('old', 0.8, t0);
    engine.recordAccess('fresh', 0.8, t0);

    // Advance 100 seconds — 'old' score should have decayed enormously
    const t1 = t0 + 100_000;
    engine.recordAccess('fresh', 0.8, t1); // re-access fresh to keep it alive

    const pruned = engine.prune(1.0, t1);
    expect(pruned).toBeGreaterThanOrEqual(1);
    // 'old' should be gone
    expect(engine.getScore('old', t1)).toBe(0);
  });

  it('returns the count of pruned entries', () => {
    const engine = new FrecencyEngine({ decayLambda: 10 }); // very fast decay
    const t0 = 0;
    engine.recordAccess('a', 0.5, t0);
    engine.recordAccess('b', 0.5, t0);
    engine.recordAccess('c', 0.5, t0);

    // Advance far into the future so all scores decay to near-zero
    const tFar = t0 + 10_000_000; // ~2.8 hours
    const pruned = engine.prune(1e-10, tFar);
    expect(pruned).toBe(3);
    expect(engine.size).toBe(0);
  });

  it('does not prune entries whose score is above threshold', () => {
    const engine = new FrecencyEngine({ decayLambda: 0.001 }); // very slow decay
    const t0 = 0;
    engine.recordAccess('safe', 0.8, t0);

    // Advance only slightly
    const t1 = t0 + 1000; // 1 second
    const pruned = engine.prune(0.001, t1);
    expect(pruned).toBe(0);
    expect(engine.size).toBe(1);
  });

  it('prune with threshold=0 removes nothing (all scores > 0)', () => {
    const engine = new FrecencyEngine({ decayLambda: 0.01 });
    const t0 = 0;
    engine.recordAccess('a', 0.5, t0);
    engine.recordAccess('b', 0.5, t0);

    const pruned = engine.prune(0, t0 + 60_000);
    expect(pruned).toBe(0);
  });

  it('after prune, surviving entries have updated scores', () => {
    const engine = new FrecencyEngine({ decayLambda: 0.001 });
    const t0 = 0;
    engine.recordAccess('ctx', 0.8, t0);
    const t1 = t0 + 5_000; // 5 seconds
    engine.prune(0.001, t1);

    const entries = engine.getAllEntries();
    expect(entries).toHaveLength(1);
    // The stored score should now reflect the decayed value at t1
    const expected = engine.getScore('ctx', t1);
    expect(entries[0].score).toBeCloseTo(expected, 8);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 7. Max entries eviction
// ─────────────────────────────────────────────────────────────────────────────
describe('FrecencyEngine - maxEntries eviction', () => {
  it('size never exceeds maxEntries', () => {
    const maxEntries = 5;
    const engine = new FrecencyEngine({ maxEntries });
    const t0 = 0;
    for (let i = 0; i < 20; i++) {
      engine.recordAccess(`ctx-${i}`, 0.5, t0);
    }
    expect(engine.size).toBe(maxEntries);
  });

  it('evicts the lowest-scoring entry when capacity is exceeded', () => {
    const engine = new FrecencyEngine({ maxEntries: 3, decayLambda: 0 });
    const t0 = 0;

    // Record three entries with different scores by varying coherence
    engine.recordAccess('low', 0.0, t0);   // lowest score
    engine.recordAccess('mid', 0.5, t0);
    engine.recordAccess('high', 1.0, t0);  // highest score

    // Adding a fourth entry should evict 'low'
    engine.recordAccess('new', 0.5, t0);

    expect(engine.size).toBe(3);
    expect(engine.getScore('low', t0)).toBe(0); // evicted
    expect(engine.getScore('high', t0)).toBeGreaterThan(0); // survived
  });

  it('maxEntries=1 retains only one entry', () => {
    const engine = new FrecencyEngine({ maxEntries: 1 });
    const t0 = 0;
    engine.recordAccess('first', 0.5, t0);
    engine.recordAccess('second', 0.5, t0);
    expect(engine.size).toBe(1);
  });

  it('re-accessing an existing key does not trigger eviction', () => {
    const engine = new FrecencyEngine({ maxEntries: 2, decayLambda: 0 });
    const t0 = 0;
    engine.recordAccess('a', 0.5, t0);
    engine.recordAccess('b', 0.5, t0);
    // Re-access 'a' — should not evict anything
    engine.recordAccess('a', 0.5, t0);
    expect(engine.size).toBe(2);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 8. Edge cases
// ─────────────────────────────────────────────────────────────────────────────
describe('FrecencyEngine - edge cases', () => {
  it('zero coherence still produces a positive score (frequency + recency terms)', () => {
    const engine = new FrecencyEngine();
    const score = engine.recordAccess('ctx', 0.0, 1000);
    // α·log1p(1) + β·(1/(1+ε)) + γ·0 > 0
    expect(score).toBeGreaterThan(0);
  });

  it('coherence=0 score is less than coherence=1 score (gamma > 0)', () => {
    const t0 = 0;
    const engineLow = new FrecencyEngine();
    const engineHigh = new FrecencyEngine();

    const scoreLow = engineLow.recordAccess('ctx', 0.0, t0);
    const scoreHigh = engineHigh.recordAccess('ctx', 1.0, t0);

    expect(scoreHigh).toBeGreaterThan(scoreLow);
  });

  it('coherence=1.0 gives maximum gamma contribution', () => {
    const alpha = 0;
    const beta = 0;
    const gamma = 2.0;
    const engine = new FrecencyEngine({ alpha, beta, gamma });
    const score = engine.recordAccess('ctx', 1.0, 0);
    // With alpha=beta=0: score = gamma * coherence = 2.0 * 1.0 = 2.0
    expect(score).toBeCloseTo(2.0, 8);
  });

  it('propagation with very large hyperbolicDistance is numerically stable (no NaN/Inf)', () => {
    const engine = new FrecencyEngine();
    engine.recordAccess('ctx', 0.8, 0);
    const result = engine.propagateThroughHarmonic('ctx', 1e15, 0, 0);
    expect(Number.isFinite(result)).toBe(true);
    expect(Number.isNaN(result)).toBe(false);
  });

  it('propagation with very large phaseDeviation is numerically stable', () => {
    const engine = new FrecencyEngine();
    engine.recordAccess('ctx', 0.8, 0);
    const result = engine.propagateThroughHarmonic('ctx', 0, 1e15, 0);
    expect(Number.isFinite(result)).toBe(true);
    expect(Number.isNaN(result)).toBe(false);
  });

  it('custom alpha/beta/gamma config affects score magnitude', () => {
    const defaultEngine = new FrecencyEngine();
    const highAlpha = new FrecencyEngine({ alpha: 10.0, beta: DEFAULT_BETA, gamma: DEFAULT_GAMMA });

    const scoreDefault = defaultEngine.recordAccess('ctx', 0.8, 0);
    const scoreHighAlpha = highAlpha.recordAccess('ctx', 0.8, 0);

    expect(scoreHighAlpha).toBeGreaterThan(scoreDefault);
  });

  it('getScore does not mutate stored entry', () => {
    const engine = new FrecencyEngine();
    const t0 = 1000;
    engine.recordAccess('ctx', 0.8, t0);
    const before = engine.getAllEntries()[0].score;

    // Query far in the future
    engine.getScore('ctx', t0 + 1_000_000);

    const after = engine.getAllEntries()[0].score;
    expect(after).toBeCloseTo(before, 10);
  });

  it('empty key string is accepted', () => {
    const engine = new FrecencyEngine();
    const score = engine.recordAccess('', 0.5, 0);
    expect(score).toBeGreaterThan(0);
    expect(engine.size).toBe(1);
  });

  it('zero timestamp is accepted', () => {
    const engine = new FrecencyEngine();
    const score = engine.recordAccess('ctx', 0.8, 0);
    expect(score).toBeGreaterThan(0);
    expect(engine.getScore('ctx', 0)).toBeCloseTo(score, 10);
  });

  it('coherence defaults to 0.8 when not provided', () => {
    const engine = new FrecencyEngine();
    const t0 = 0;
    // Call without coherence arg
    const scoreDefault = engine.recordAccess('a', undefined, t0);
    const engine2 = new FrecencyEngine();
    const scoreExplicit = engine2.recordAccess('b', 0.8, t0);
    expect(scoreDefault).toBeCloseTo(scoreExplicit, 8);
  });

  it('prune on empty engine returns 0', () => {
    const engine = new FrecencyEngine();
    expect(engine.prune(0.01, 1000)).toBe(0);
  });

  it('getTopK on empty engine returns empty array', () => {
    const engine = new FrecencyEngine();
    expect(engine.getTopK(10, 0)).toEqual([]);
  });

  it('multiple clear calls are idempotent', () => {
    const engine = new FrecencyEngine();
    engine.recordAccess('a', 0.5, 0);
    engine.clear();
    engine.clear();
    expect(engine.size).toBe(0);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 9. FrecencyEntry interface shape
// ─────────────────────────────────────────────────────────────────────────────
describe('FrecencyEntry shape', () => {
  it('entry has all required fields after first access', () => {
    const engine = new FrecencyEngine();
    const t0 = 999;
    engine.recordAccess('ctx', 0.7, t0);
    const entry = engine.getAllEntries()[0];

    expect(entry).toHaveProperty('key');
    expect(entry).toHaveProperty('frequency');
    expect(entry).toHaveProperty('lastAccessedAt');
    expect(entry).toHaveProperty('coherence');
    expect(entry).toHaveProperty('score');
  });

  it('entry.key matches the recorded key', () => {
    const engine = new FrecencyEngine();
    engine.recordAccess('my-context-key', 0.5, 0);
    const entry = engine.getAllEntries()[0];
    expect(entry.key).toBe('my-context-key');
  });

  it('entry.score is a finite positive number', () => {
    const engine = new FrecencyEngine();
    engine.recordAccess('ctx', 0.5, 0);
    const entry = engine.getAllEntries()[0];
    expect(Number.isFinite(entry.score)).toBe(true);
    expect(entry.score).toBeGreaterThan(0);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 10. Property-based style tests (determinism and monotonicity)
// ─────────────────────────────────────────────────────────────────────────────
describe('FrecencyEngine - determinism and monotonicity (property-style)', () => {
  const rand = (min: number, max: number) => Math.random() * (max - min) + min;

  it('recordAccess is deterministic given identical state (50 trials)', () => {
    for (let i = 0; i < 50; i++) {
      const coherence = rand(0, 1);
      const t0 = Math.floor(rand(0, 1e9));

      const engine1 = new FrecencyEngine();
      const engine2 = new FrecencyEngine();

      const s1 = engine1.recordAccess('ctx', coherence, t0);
      const s2 = engine2.recordAccess('ctx', coherence, t0);

      expect(s1).toBeCloseTo(s2, 10);
    }
  });

  it('getScore is non-negative for all keys (50 trials)', () => {
    const engine = new FrecencyEngine();
    const t0 = 0;
    for (let i = 0; i < 50; i++) {
      const key = `key-${i}`;
      engine.recordAccess(key, rand(0, 1), t0);
      expect(engine.getScore(key, t0)).toBeGreaterThanOrEqual(0);
    }
  });

  it('propagateThroughHarmonic score is in (0, base] for d>=0, pd>=0 (50 trials)', () => {
    const engine = new FrecencyEngine();
    const t0 = 0;
    engine.recordAccess('ctx', 0.8, t0);
    const base = engine.getScore('ctx', t0);

    for (let i = 0; i < 50; i++) {
      const d = rand(0, 100);
      const pd = rand(0, 10);
      const propagated = engine.propagateThroughHarmonic('ctx', d, pd, t0);
      expect(propagated).toBeGreaterThan(0);
      expect(propagated).toBeLessThanOrEqual(base + 1e-9);
    }
  });

  it('score decreases strictly with time (50 trials, lambda > 0)', () => {
    for (let i = 0; i < 50; i++) {
      const lambda = rand(0.001, 0.5);
      const engine = new FrecencyEngine({ decayLambda: lambda });
      const t0 = Math.floor(rand(0, 1e7));
      engine.recordAccess('ctx', rand(0, 1), t0);

      const dt = rand(1, 100) * 1000; // 1-100 seconds in ms
      const scoreBefore = engine.getScore('ctx', t0);
      const scoreAfter = engine.getScore('ctx', t0 + dt);

      expect(scoreAfter).toBeLessThan(scoreBefore);
    }
  });
});
