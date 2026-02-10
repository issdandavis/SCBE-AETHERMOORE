/**
 * @file hyperbolicRAG.unit.test.ts
 * @tier L2-unit
 * @axiom 2 (Locality), 4 (Symmetry)
 * @category unit
 *
 * Unit tests for HyperbolicRAG — trust-gated retrieval scoring in Poincaré ball.
 */

import { describe, it, expect } from 'vitest';
import type { Vector6D } from '../../src/harmonic/constants.js';
import {
  projectToBall,
  extractPhase,
  estimateUncertainty,
  buildChunk,
  nearestTongueAnchor,
  proximityScore,
  phaseConsistencyScore,
  uncertaintyPenalty,
  scoreChunk,
  scoreAndFilter,
  retrieveWithTrust,
  quarantineReport,
  TONGUE_ANCHORS,
  DEFAULT_RAG_CONFIG,
  type HyperbolicChunk,
} from '../../src/harmonic/hyperbolicRAG.js';

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════

const ORIGIN: Vector6D = [0, 0, 0, 0, 0, 0];
const ALIGNED_PHASE: Vector6D = [0, Math.PI / 3, (2 * Math.PI) / 3, Math.PI, (4 * Math.PI) / 3, (5 * Math.PI) / 3];

function makeChunk(id: string, pos: Vector6D, phase?: Vector6D, uncertainty?: number): HyperbolicChunk {
  return {
    chunkId: id,
    position: pos,
    phase: phase ?? ALIGNED_PHASE,
    uncertainty: uncertainty ?? 0.1,
  };
}

function randomEmbedding(dim: number, seed: number = 42): number[] {
  const result: number[] = [];
  let x = seed;
  for (let i = 0; i < dim; i++) {
    // Simple LCG for deterministic pseudo-random
    x = (x * 1664525 + 1013904223) & 0x7fffffff;
    result.push((x / 0x7fffffff) * 2 - 1);
  }
  return result;
}

// ═══════════════════════════════════════════════════════════════
// projectToBall
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: projectToBall', () => {
  it('should produce a vector inside the Poincaré ball', () => {
    const emb = randomEmbedding(768);
    const pos = projectToBall(emb);
    const normSq = pos.reduce((s, v) => s + v * v, 0);
    expect(normSq).toBeLessThan(1);
  });

  it('should produce 6D output for any input dimension', () => {
    for (const dim of [6, 12, 128, 768, 1536]) {
      const pos = projectToBall(randomEmbedding(dim));
      expect(pos).toHaveLength(6);
    }
  });

  it('should map zero embedding to origin', () => {
    const pos = projectToBall(new Array(768).fill(0));
    for (const v of pos) expect(v).toBeCloseTo(0, 8);
  });

  it('should place similar embeddings close together', () => {
    const base = randomEmbedding(768, 1);
    const similar = base.map((v) => v + 0.01);
    const different = randomEmbedding(768, 999);

    const pBase = projectToBall(base);
    const pSimilar = projectToBall(similar);
    const pDifferent = projectToBall(different);

    // Euclidean distance as proxy
    let dSim = 0;
    let dDiff = 0;
    for (let i = 0; i < 6; i++) {
      dSim += (pBase[i] - pSimilar[i]) ** 2;
      dDiff += (pBase[i] - pDifferent[i]) ** 2;
    }
    expect(Math.sqrt(dSim)).toBeLessThan(Math.sqrt(dDiff));
  });

  it('should respect scale parameter', () => {
    const emb = randomEmbedding(768);
    const tight = projectToBall(emb, 0.1);
    const wide = projectToBall(emb, 2.0);
    const tightNorm = Math.sqrt(tight.reduce((s, v) => s + v * v, 0));
    const wideNorm = Math.sqrt(wide.reduce((s, v) => s + v * v, 0));
    expect(tightNorm).toBeLessThan(wideNorm);
  });
});

// ═══════════════════════════════════════════════════════════════
// extractPhase
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: extractPhase', () => {
  it('should return 6 phase values', () => {
    const phase = extractPhase(randomEmbedding(768));
    expect(phase).toHaveLength(6);
  });

  it('should have phases in [-π, π]', () => {
    const phase = extractPhase(randomEmbedding(768));
    for (const p of phase) {
      expect(p).toBeGreaterThanOrEqual(-Math.PI);
      expect(p).toBeLessThanOrEqual(Math.PI);
    }
  });

  it('should produce different phases for different embeddings', () => {
    const p1 = extractPhase(randomEmbedding(768, 1));
    const p2 = extractPhase(randomEmbedding(768, 999));
    let same = true;
    for (let i = 0; i < 6; i++) {
      if (Math.abs(p1[i] - p2[i]) > 0.01) same = false;
    }
    expect(same).toBe(false);
  });
});

// ═══════════════════════════════════════════════════════════════
// estimateUncertainty
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: estimateUncertainty', () => {
  it('should return high uncertainty for high-variance embedding', () => {
    const highVar = Array.from({ length: 100 }, (_, i) => (i % 2 === 0 ? 5 : -5));
    expect(estimateUncertainty(highVar)).toBeGreaterThan(0.5);
  });

  it('should return low uncertainty for constant embedding', () => {
    const constant = new Array(100).fill(0.1);
    expect(estimateUncertainty(constant)).toBeLessThan(0.5);
  });

  it('should return 1.0 for empty embedding', () => {
    expect(estimateUncertainty([])).toBe(1.0);
  });

  it('should return value in [0, 1]', () => {
    const u = estimateUncertainty(randomEmbedding(768));
    expect(u).toBeGreaterThanOrEqual(0);
    expect(u).toBeLessThanOrEqual(1);
  });
});

// ═══════════════════════════════════════════════════════════════
// buildChunk
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: buildChunk', () => {
  it('should build a complete HyperbolicChunk', () => {
    const chunk = buildChunk('c1', randomEmbedding(768));
    expect(chunk.chunkId).toBe('c1');
    expect(chunk.position).toHaveLength(6);
    expect(chunk.phase).toHaveLength(6);
    expect(chunk.uncertainty).toBeGreaterThanOrEqual(0);
    expect(chunk.originalNorm).toBeGreaterThan(0);
  });

  it('should produce position inside ball', () => {
    const chunk = buildChunk('c1', randomEmbedding(1536));
    const normSq = chunk.position.reduce((s, v) => s + v * v, 0);
    expect(normSq).toBeLessThan(1);
  });
});

// ═══════════════════════════════════════════════════════════════
// nearestTongueAnchor
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: nearestTongueAnchor', () => {
  it('should find KO for position on KO axis', () => {
    const pos: Vector6D = [0.4, 0, 0, 0, 0, 0];
    const { tongue } = nearestTongueAnchor(pos);
    expect(tongue).toBe('KO');
  });

  it('should find CA for position on CA axis', () => {
    const pos: Vector6D = [0, 0, 0, 0.4, 0, 0];
    const { tongue } = nearestTongueAnchor(pos);
    expect(tongue).toBe('CA');
  });

  it('should return a distance for origin', () => {
    const { distance } = nearestTongueAnchor(ORIGIN);
    expect(distance).toBeGreaterThan(0);
  });

  it('should have all 6 anchors defined', () => {
    for (const t of ['KO', 'AV', 'RU', 'CA', 'DR', 'UM']) {
      expect(TONGUE_ANCHORS[t]).toBeDefined();
      expect(TONGUE_ANCHORS[t]).toHaveLength(6);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// proximityScore
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: proximityScore', () => {
  it('should be 1 for co-located points', () => {
    expect(proximityScore(ORIGIN, ORIGIN)).toBeCloseTo(1, 5);
  });

  it('should decrease with distance', () => {
    const near: Vector6D = [0.05, 0, 0, 0, 0, 0];
    const far: Vector6D = [0.5, 0, 0, 0, 0, 0];
    expect(proximityScore(ORIGIN, near)).toBeGreaterThan(proximityScore(ORIGIN, far));
  });

  it('should be 0 for points beyond maxDist', () => {
    const far: Vector6D = [0.95, 0, 0, 0, 0, 0];
    expect(proximityScore(ORIGIN, far, 0.5)).toBe(0);
  });

  it('should be in [0, 1]', () => {
    const pos: Vector6D = [0.3, 0.1, 0, 0, 0, 0];
    const s = proximityScore(ORIGIN, pos);
    expect(s).toBeGreaterThanOrEqual(0);
    expect(s).toBeLessThanOrEqual(1);
  });
});

// ═══════════════════════════════════════════════════════════════
// phaseConsistencyScore
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: phaseConsistencyScore', () => {
  it('should be 1 for identical phases', () => {
    expect(phaseConsistencyScore(ALIGNED_PHASE, ALIGNED_PHASE)).toBeCloseTo(1, 5);
  });

  it('should be 0 for opposite phases', () => {
    const opposite = ALIGNED_PHASE.map((p) => p + Math.PI) as Vector6D;
    expect(phaseConsistencyScore(ALIGNED_PHASE, opposite)).toBeCloseTo(0, 5);
  });

  it('should be 0.5 for perpendicular phases', () => {
    const perp = ALIGNED_PHASE.map((p) => p + Math.PI / 2) as Vector6D;
    expect(phaseConsistencyScore(ALIGNED_PHASE, perp)).toBeCloseTo(0.5, 5);
  });

  it('should be symmetric', () => {
    const a = ALIGNED_PHASE;
    const b = ALIGNED_PHASE.map((p) => p + 0.5) as Vector6D;
    expect(phaseConsistencyScore(a, b)).toBeCloseTo(phaseConsistencyScore(b, a), 10);
  });
});

// ═══════════════════════════════════════════════════════════════
// uncertaintyPenalty
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: uncertaintyPenalty', () => {
  it('should return 0 for zero uncertainty', () => {
    expect(uncertaintyPenalty(0)).toBe(0);
  });

  it('should return 1 for max uncertainty', () => {
    expect(uncertaintyPenalty(1)).toBe(1);
  });

  it('should clamp negative to 0', () => {
    expect(uncertaintyPenalty(-0.5)).toBe(0);
  });

  it('should clamp above 1 to 1', () => {
    expect(uncertaintyPenalty(1.5)).toBe(1);
  });
});

// ═══════════════════════════════════════════════════════════════
// scoreChunk
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: scoreChunk', () => {
  const query = { position: ORIGIN, phase: ALIGNED_PHASE };

  it('should give high trust to nearby + aligned + low-uncertainty chunk', () => {
    const chunk = makeChunk('good', [0.05, 0, 0, 0, 0, 0] as Vector6D, ALIGNED_PHASE, 0.05);
    const result = scoreChunk(query, chunk);
    expect(result.trustScore).toBeGreaterThan(0.5);
    expect(result.quarantineFlag).toBe(false);
    expect(result.attentionWeight).toBeGreaterThan(0);
  });

  it('should quarantine high-uncertainty chunk', () => {
    const chunk = makeChunk('uncertain', ORIGIN, ALIGNED_PHASE, 0.9);
    const result = scoreChunk(query, chunk);
    expect(result.quarantineFlag).toBe(true);
    expect(result.attentionWeight).toBe(0);
  });

  it('should quarantine far-away chunk', () => {
    const chunk = makeChunk('distant', [0.95, 0, 0, 0, 0, 0] as Vector6D, ALIGNED_PHASE, 0.1);
    const result = scoreChunk(query, chunk);
    // Distance > maxTrustDistance → proximity ≈ 0 → low trust
    expect(result.trustScore).toBeLessThan(0.5);
  });

  it('should penalize phase-misaligned chunk', () => {
    const bad = ALIGNED_PHASE.map((p) => p + Math.PI) as Vector6D;
    const aligned = makeChunk('aligned', ORIGIN, ALIGNED_PHASE, 0.1);
    const misaligned = makeChunk('misaligned', ORIGIN, bad, 0.1);
    const scoreAligned = scoreChunk(query, aligned).trustScore;
    const scoreMisaligned = scoreChunk(query, misaligned).trustScore;
    expect(scoreAligned).toBeGreaterThan(scoreMisaligned);
  });

  it('should return all required signal fields', () => {
    const chunk = makeChunk('c1', ORIGIN, ALIGNED_PHASE, 0.1);
    const result = scoreChunk(query, chunk);
    expect(result.signals).toBeDefined();
    expect(result.signals.proximityScore).toBeGreaterThanOrEqual(0);
    expect(result.signals.phaseScore).toBeGreaterThanOrEqual(0);
    expect(typeof result.signals.uncertaintyPenalty).toBe('number');
    expect(result.signals.distanceToQuery).toBeGreaterThanOrEqual(0);
    expect(result.signals.distanceToAnchor).toBeGreaterThan(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// scoreAndFilter
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: scoreAndFilter', () => {
  const query = { position: ORIGIN, phase: ALIGNED_PHASE };

  it('should return at most topK results', () => {
    const chunks = Array.from({ length: 20 }, (_, i) =>
      makeChunk(`c${i}`, [0.01 * (i + 1), 0, 0, 0, 0, 0] as Vector6D)
    );
    const results = scoreAndFilter(query, chunks, 5);
    expect(results.length).toBeLessThanOrEqual(5);
  });

  it('should exclude quarantined chunks', () => {
    const chunks = [
      makeChunk('good', [0.05, 0, 0, 0, 0, 0] as Vector6D, ALIGNED_PHASE, 0.1),
      makeChunk('bad', ORIGIN, ALIGNED_PHASE, 0.95), // high uncertainty → quarantine
    ];
    const results = scoreAndFilter(query, chunks, 10);
    const ids = results.map((r) => r.chunkId);
    expect(ids).not.toContain('bad');
  });

  it('should sort by trust score descending', () => {
    const chunks = [
      makeChunk('far', [0.5, 0, 0, 0, 0, 0] as Vector6D, ALIGNED_PHASE, 0.1),
      makeChunk('near', [0.02, 0, 0, 0, 0, 0] as Vector6D, ALIGNED_PHASE, 0.1),
      makeChunk('mid', [0.2, 0, 0, 0, 0, 0] as Vector6D, ALIGNED_PHASE, 0.1),
    ];
    const results = scoreAndFilter(query, chunks, 10);
    for (let i = 1; i < results.length; i++) {
      expect(results[i - 1].trustScore).toBeGreaterThanOrEqual(results[i].trustScore);
    }
  });

  it('should normalize attention weights to sum to ~1', () => {
    const chunks = Array.from({ length: 5 }, (_, i) =>
      makeChunk(`c${i}`, [0.01 * (i + 1), 0, 0, 0, 0, 0] as Vector6D, ALIGNED_PHASE, 0.1)
    );
    const results = scoreAndFilter(query, chunks, 5);
    if (results.length > 0) {
      const sum = results.reduce((s, r) => s + r.attentionWeight, 0);
      expect(sum).toBeCloseTo(1, 2);
    }
  });

  it('should return empty array when all chunks are quarantined', () => {
    const chunks = [
      makeChunk('bad1', ORIGIN, ALIGNED_PHASE, 0.95),
      makeChunk('bad2', ORIGIN, ALIGNED_PHASE, 0.95),
    ];
    const results = scoreAndFilter(query, chunks, 10);
    expect(results).toHaveLength(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// retrieveWithTrust (end-to-end)
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: retrieveWithTrust', () => {
  it('should process raw embeddings end-to-end', () => {
    const queryEmb = randomEmbedding(768, 1);
    const candidates = Array.from({ length: 10 }, (_, i) => ({
      id: `chunk-${i}`,
      embedding: randomEmbedding(768, i + 10),
    }));
    const results = retrieveWithTrust(queryEmb, candidates, 5);
    expect(results.length).toBeLessThanOrEqual(5);
    for (const r of results) {
      expect(r.chunkId).toMatch(/^chunk-/);
      expect(r.trustScore).toBeGreaterThanOrEqual(0);
      expect(r.trustScore).toBeLessThanOrEqual(1);
    }
  });

  it('should rank similar embeddings higher', () => {
    const queryEmb = randomEmbedding(768, 1);
    // Make one candidate very similar to query
    const similar = queryEmb.map((v) => v + 0.001);
    const different = randomEmbedding(768, 999);
    const candidates = [
      { id: 'similar', embedding: similar },
      { id: 'different', embedding: different },
    ];
    const results = retrieveWithTrust(queryEmb, candidates, 2);
    if (results.length >= 2) {
      expect(results[0].chunkId).toBe('similar');
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// quarantineReport
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: quarantineReport', () => {
  const query = { position: ORIGIN, phase: ALIGNED_PHASE };

  it('should partition into trusted and quarantined', () => {
    const chunks = [
      makeChunk('good', [0.05, 0, 0, 0, 0, 0] as Vector6D, ALIGNED_PHASE, 0.1),
      makeChunk('bad', ORIGIN, ALIGNED_PHASE, 0.95),
    ];
    const report = quarantineReport(query, chunks);
    expect(report.stats.total).toBe(2);
    expect(report.stats.trustedCount + report.stats.quarantinedCount).toBe(2);
  });

  it('should compute valid stats', () => {
    const chunks = Array.from({ length: 5 }, (_, i) =>
      makeChunk(`c${i}`, [0.01 * (i + 1), 0, 0, 0, 0, 0] as Vector6D, ALIGNED_PHASE, 0.1)
    );
    const report = quarantineReport(query, chunks);
    expect(report.stats.avgTrustScore).toBeGreaterThanOrEqual(0);
    expect(report.stats.avgTrustScore).toBeLessThanOrEqual(1);
    expect(report.stats.quarantineRate).toBeGreaterThanOrEqual(0);
    expect(report.stats.quarantineRate).toBeLessThanOrEqual(1);
  });

  it('should handle empty chunk list', () => {
    const report = quarantineReport(query, []);
    expect(report.stats.total).toBe(0);
    expect(report.stats.quarantineRate).toBe(0);
  });
});
