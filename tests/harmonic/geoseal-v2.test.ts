/**
 * @file geoseal-v2.test.ts
 * GeoSeal v2: Mixed-Curvature Geometric Access Control Kernel tests
 *
 * Covers:
 * - Individual geometry scores (hyperbolic, phase, certainty)
 * - Product manifold fusion and action thresholds
 * - v2 repulsion with uncertainty amplification
 * - Uncertainty evolution (sigma decay/growth)
 * - Swarm dynamics with mixed geometry
 * - Batch scoring against tongue anchors
 * - Memory write gating (high trust only)
 */

import { describe, it, expect } from 'vitest';
import {
  createMixedAgent,
  scoreHyperbolic,
  scorePhase,
  scoreCertainty,
  fuseScores,
  computeRepelForceV2,
  swarmStepV2,
  runSwarmV2,
  scoreAllCandidates,
  updateSuspicionV2,
  TONGUE_PHASES,
  DEFAULT_FUSION_WEIGHTS,
  QUARANTINE_TRUST_THRESHOLD,
  MEMORY_WRITE_THRESHOLD,
  MixedAgent,
} from '../../src/geoseal-v2.js';

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════

function vecNorm(v: number[]): number {
  return Math.sqrt(v.reduce((a, b) => a + b * b, 0));
}

function makeTongueAgent(tongue: string, pos: number[]): MixedAgent {
  return createMixedAgent(
    `tongue-${tongue}`,
    pos,
    TONGUE_PHASES[tongue],
    0.0, // zero uncertainty
    tongue,
    1.0 // fully trusted
  );
}

function makeRetrieval(id: string, pos: number[], sigma: number, tongue?: string): MixedAgent {
  const phase = tongue ? (TONGUE_PHASES[tongue] ?? null) : null;
  return createMixedAgent(id, pos, phase, sigma, tongue, 0.5);
}

// ═══════════════════════════════════════════════════════════════
// Individual geometry scores
// ═══════════════════════════════════════════════════════════════

describe('Individual geometry scores', () => {
  it('scoreHyperbolic: close points score high', () => {
    const a = createMixedAgent('a', [0.1, 0], 0);
    const b = createMixedAgent('b', [0.12, 0], 0);
    expect(scoreHyperbolic(a, b)).toBeGreaterThan(0.8);
  });

  it('scoreHyperbolic: far points score low', () => {
    const a = createMixedAgent('a', [0.1, 0], 0);
    const b = createMixedAgent('b', [0.9, 0], 0);
    expect(scoreHyperbolic(a, b)).toBeLessThan(0.3);
  });

  it('scorePhase: same phase = 1.0', () => {
    const a = createMixedAgent('a', [0, 0], TONGUE_PHASES.KO);
    const b = createMixedAgent('b', [0, 0], TONGUE_PHASES.KO);
    expect(scorePhase(a, b)).toBeCloseTo(1.0, 5);
  });

  it('scorePhase: opposite phase = 0.0', () => {
    const a = createMixedAgent('a', [0, 0], 0);
    const b = createMixedAgent('b', [0, 0], Math.PI);
    expect(scorePhase(a, b)).toBeCloseTo(0.0, 5);
  });

  it('scorePhase: null phase = 0.0', () => {
    const a = createMixedAgent('a', [0, 0], TONGUE_PHASES.KO);
    const b = createMixedAgent('b', [0, 0], null);
    expect(scorePhase(a, b)).toBeCloseTo(0.0, 5);
  });

  it('scoreCertainty: zero sigma = 1.0', () => {
    const b = createMixedAgent('b', [0, 0], 0, 0.0);
    expect(scoreCertainty(b)).toBeCloseTo(1.0, 5);
  });

  it('scoreCertainty: high sigma = low score', () => {
    const b = createMixedAgent('b', [0, 0], 0, 5.0);
    expect(scoreCertainty(b)).toBeLessThan(0.2);
  });
});

// ═══════════════════════════════════════════════════════════════
// Product manifold fusion
// ═══════════════════════════════════════════════════════════════

describe('fuseScores', () => {
  it('trusted retrieval with matching phase and low uncertainty => ALLOW', () => {
    const anchor = makeTongueAgent('KO', [0.1, 0]);
    const candidate = makeRetrieval('r1', [0.12, 0], 0.0, 'KO');
    const fused = fuseScores(anchor, candidate);

    expect(fused.trust).toBeGreaterThan(MEMORY_WRITE_THRESHOLD);
    expect(fused.action).toBe('ALLOW');
    expect(fused.anomaly).toBe(false);
  });

  it('rogue retrieval with null phase => low trust', () => {
    const anchor = makeTongueAgent('KO', [0.1, 0]);
    const rogue = makeRetrieval('rogue', [0.12, 0], 0.0);
    const fused = fuseScores(anchor, rogue);

    // sS = 0 (null phase), so trust takes a big hit
    expect(fused.sS).toBeCloseTo(0.0, 5);
    expect(fused.anomaly).toBe(true);
    expect(fused.trust).toBeLessThan(MEMORY_WRITE_THRESHOLD);
  });

  it('high uncertainty retrieval => anomaly flag', () => {
    const anchor = makeTongueAgent('KO', [0.1, 0]);
    const uncertain = makeRetrieval('u1', [0.12, 0], 3.0, 'KO');
    const fused = fuseScores(anchor, uncertain);

    expect(fused.sG).toBeLessThan(0.5);
    expect(fused.anomaly).toBe(true);
  });

  it('far + wrong phase + high uncertainty => DENY', () => {
    const anchor = makeTongueAgent('KO', [0.1, 0]);
    const bad = createMixedAgent('bad', [0.9, 0], Math.PI, 5.0, undefined, 0.5);
    const fused = fuseScores(anchor, bad);

    expect(fused.trust).toBeLessThan(QUARANTINE_TRUST_THRESHOLD);
    expect(fused.action).toBe('DENY');
  });

  it('moderate uncertainty + matching phase => QUARANTINE', () => {
    const anchor = makeTongueAgent('KO', [0.1, 0]);
    // Far away, matching phase, moderate uncertainty
    const candidate = makeRetrieval('m1', [0.7, 0], 2.0, 'KO');
    const fused = fuseScores(anchor, candidate);

    // Phase score high, but distance and uncertainty hurt
    expect(fused.action).toBe('QUARANTINE');
  });

  it('custom weights shift balance', () => {
    const anchor = makeTongueAgent('KO', [0.1, 0]);
    const candidate = makeRetrieval('r1', [0.5, 0], 0.0, 'KO');

    // Phase-heavy weights
    const phaseHeavy = { wH: 0.1, wS: 0.8, wG: 0.1 };
    const fused = fuseScores(anchor, candidate, phaseHeavy);

    // Phase match is perfect, so trust should be high
    expect(fused.trust).toBeGreaterThan(0.8);
  });
});

// ═══════════════════════════════════════════════════════════════
// v2 Repulsion
// ═══════════════════════════════════════════════════════════════

describe('computeRepelForceV2', () => {
  it('adds uncertainty amplification for sigma > 0.5', () => {
    const a = makeTongueAgent('KO', [0.1, 0]);
    const uncertain = createMixedAgent('u', [0.15, 0], TONGUE_PHASES.KO, 1.0, 'KO');

    const result = computeRepelForceV2(a, uncertain);
    // Should have +0.5 from uncertainty
    expect(result.amplification).toBeGreaterThan(1.0);
    expect(result.anomaly_flag).toBe(true);
  });

  it('no extra amplification for sigma <= 0.5', () => {
    const a = makeTongueAgent('KO', [0.1, 0]);
    const certain = createMixedAgent('c', [0.15, 0], TONGUE_PHASES.KO, 0.3, 'KO');

    const result = computeRepelForceV2(a, certain);
    // Same phase, close range, low uncertainty => no anomaly
    expect(result.anomaly_flag).toBe(false);
    expect(result.amplification).toBe(1.0);
  });

  it('null phase + high uncertainty = maximum amplification', () => {
    const a = makeTongueAgent('KO', [0.1, 0]);
    const rogue = createMixedAgent('rogue', [0.15, 0], null, 3.0);

    const result = computeRepelForceV2(a, rogue);
    // 2.0 (null) + 0.5 (uncertainty) + 0.25 (fused anomaly) = 2.75
    expect(result.amplification).toBeGreaterThanOrEqual(2.75);
  });

  it('returns fused score breakdown', () => {
    const a = makeTongueAgent('KO', [0.1, 0]);
    const b = makeRetrieval('r1', [0.12, 0], 0.5, 'KO');

    const result = computeRepelForceV2(a, b);
    expect(result.fused).toBeDefined();
    expect(result.fused.sH).toBeGreaterThan(0);
    expect(result.fused.sS).toBeGreaterThan(0);
    expect(result.fused.sG).toBeGreaterThan(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// Uncertainty evolution
// ═══════════════════════════════════════════════════════════════

describe('Uncertainty evolution', () => {
  it('sigma decays for consistent agents', () => {
    // 4 matching KO agents with moderate initial sigma
    const agents = [
      createMixedAgent('ko1', [0.1, 0], TONGUE_PHASES.KO, 0.5, 'KO', 1.0),
      createMixedAgent('ko2', [-0.1, 0], TONGUE_PHASES.KO, 0.5, 'KO', 1.0),
      createMixedAgent('ko3', [0, 0.1], TONGUE_PHASES.KO, 0.5, 'KO', 1.0),
      createMixedAgent('ko4', [0, -0.1], TONGUE_PHASES.KO, 0.5, 'KO', 1.0),
    ];

    const initialSigma = agents[0].sigma;
    runSwarmV2(agents, 20, 0.005, 0.02);

    // Sigma should have decayed since no anomalies between same-phase agents
    expect(agents[0].sigma).toBeLessThan(initialSigma);
  });

  it('sigma grows for rogue agents', () => {
    const agents = [
      makeTongueAgent('KO', [0.1, 0]),
      makeTongueAgent('KO', [-0.1, 0]),
      makeTongueAgent('KO', [0, 0.1]),
      makeTongueAgent('KO', [0, -0.1]),
      createMixedAgent('rogue', [0.05, 0.05], null, 0.5),
    ];

    const initialSigma = agents[4].sigma;
    runSwarmV2(agents, 30, 0.005, 0.02);

    // Rogue's sigma should grow since it triggers anomalies
    expect(agents[4].sigma).toBeGreaterThan(initialSigma);
  });

  it('sigma never goes below 0', () => {
    const agents = [
      createMixedAgent('a', [0.1, 0], TONGUE_PHASES.KO, 0.01, 'KO', 1.0),
      createMixedAgent('b', [-0.1, 0], TONGUE_PHASES.KO, 0.01, 'KO', 1.0),
    ];

    runSwarmV2(agents, 50, 0.005, 0.1);
    expect(agents[0].sigma).toBeGreaterThanOrEqual(0);
    expect(agents[1].sigma).toBeGreaterThanOrEqual(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// v2 Swarm dynamics
// ═══════════════════════════════════════════════════════════════

describe('v2 Swarm dynamics', () => {
  it('rogue pushed toward boundary', () => {
    const agents = [
      makeTongueAgent('KO', [0.1, 0]),
      makeTongueAgent('KO', [-0.1, 0]),
      makeTongueAgent('KO', [0, 0.1]),
      makeTongueAgent('KO', [0, -0.1]),
      createMixedAgent('rogue', [0.05, 0.05], null, 1.0),
    ];

    const initialNorm = vecNorm(agents[4].position);
    runSwarmV2(agents, 50, 0.005);
    expect(vecNorm(agents[4].position)).toBeGreaterThan(initialNorm);
  });

  it('legitimate agents retain higher trust than rogue', () => {
    const agents = [
      makeTongueAgent('KO', [0.1, 0]),
      makeTongueAgent('KO', [-0.1, 0]),
      makeTongueAgent('KO', [0, 0.1]),
      makeTongueAgent('KO', [0, -0.1]),
      createMixedAgent('rogue', [0.05, 0.05], null, 2.0),
    ];

    runSwarmV2(agents, 30, 0.005);
    expect(agents[0].trust_score).toBeGreaterThan(agents[4].trust_score);
  });

  it('positions clamped to ball', () => {
    const agents = [
      createMixedAgent('a', [0.95, 0], TONGUE_PHASES.KO, 0, 'KO', 1.0),
      createMixedAgent('rogue', [0.96, 0], null, 1.0),
    ];

    runSwarmV2(agents, 10, 0.01);
    for (const agent of agents) {
      expect(vecNorm(agent.position)).toBeLessThanOrEqual(0.99 + 1e-6);
    }
  });

  it('empty swarm does not throw', () => {
    expect(() => swarmStepV2([])).not.toThrow();
  });
});

// ═══════════════════════════════════════════════════════════════
// Batch scoring
// ═══════════════════════════════════════════════════════════════

describe('scoreAllCandidates', () => {
  it('ranks matching+certain above rogue+uncertain', () => {
    const anchors = [
      makeTongueAgent('KO', [0.1, 0]),
      makeTongueAgent('AV', [-0.1, 0]),
    ];

    const candidates = [
      makeRetrieval('good', [0.12, 0], 0.0, 'KO'),
      makeRetrieval('ok', [0.12, 0], 1.0, 'KO'),
      createMixedAgent('rogue', [0.12, 0], null, 3.0),
    ];

    const scored = scoreAllCandidates(anchors, candidates);

    expect(scored[0].id).toBe('good');
    expect(scored[scored.length - 1].id).toBe('rogue');
    expect(scored[0].trust).toBeGreaterThan(scored[scored.length - 1].trust);
  });

  it('assigns correct actions', () => {
    const anchors = [makeTongueAgent('KO', [0.1, 0])];

    const candidates = [
      makeRetrieval('allow', [0.12, 0], 0.0, 'KO'),      // high trust
      createMixedAgent('deny', [0.9, 0], Math.PI, 5.0),   // low trust
    ];

    const scored = scoreAllCandidates(anchors, candidates);
    const allowC = scored.find((s) => s.id === 'allow');
    const denyC = scored.find((s) => s.id === 'deny');

    expect(allowC?.action).toBe('ALLOW');
    expect(denyC?.action).toBe('DENY');
  });

  it('returns empty for no candidates', () => {
    const anchors = [makeTongueAgent('KO', [0.1, 0])];
    const scored = scoreAllCandidates(anchors, []);
    expect(scored).toHaveLength(0);
  });

  it('picks best anchor per candidate', () => {
    const anchors = [
      makeTongueAgent('KO', [0.1, 0]),
      makeTongueAgent('AV', [0.1, 0.1]),
    ];

    // AV-phase candidate near AV anchor
    const candidate = makeRetrieval('av-match', [0.12, 0.1], 0.0, 'AV');
    const scored = scoreAllCandidates(anchors, [candidate]);

    // Should get high trust from AV anchor match
    expect(scored[0].trust).toBeGreaterThan(0.5);
  });
});

// ═══════════════════════════════════════════════════════════════
// Phase vector computation
// ═══════════════════════════════════════════════════════════════

describe('MixedAgent.phaseVec', () => {
  it('computes cos/sin for valid phase', () => {
    const agent = createMixedAgent('a', [0, 0], Math.PI / 2);
    expect(agent.phaseVec[0]).toBeCloseTo(0, 5);   // cos(π/2) ≈ 0
    expect(agent.phaseVec[1]).toBeCloseTo(1, 5);   // sin(π/2) = 1
  });

  it('returns [0, 0] for null phase', () => {
    const agent = createMixedAgent('a', [0, 0], null);
    expect(agent.phaseVec).toEqual([0, 0]);
  });
});

// ═══════════════════════════════════════════════════════════════
// Memory write gating
// ═══════════════════════════════════════════════════════════════

describe('Memory write gating', () => {
  it('only ALLOW action chunks pass memory write threshold', () => {
    const anchor = makeTongueAgent('KO', [0.1, 0]);

    const good = makeRetrieval('good', [0.12, 0], 0.0, 'KO');
    const bad = createMixedAgent('bad', [0.9, 0], null, 5.0);

    const goodFused = fuseScores(anchor, good);
    const badFused = fuseScores(anchor, bad);

    expect(goodFused.trust).toBeGreaterThan(MEMORY_WRITE_THRESHOLD);
    expect(goodFused.action).toBe('ALLOW');

    expect(badFused.trust).toBeLessThan(MEMORY_WRITE_THRESHOLD);
    expect(badFused.action).not.toBe('ALLOW');
  });
});
