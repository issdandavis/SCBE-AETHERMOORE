/**
 * @file geoseal.test.ts
 * GeoSeal: Geometric Access Control Kernel tests
 *
 * Covers:
 * - Hyperbolic distance edge cases
 * - Phase deviation wrapping
 * - Repulsion force mechanics
 * - Suspicion counter decay
 * - Quarantine threshold logic
 * - Swarm dynamics (rogue ejection)
 * - Metrics computation
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  Agent,
  createAgent,
  computeRepelForce,
  updateSuspicion,
  swarmStep,
  runSwarm,
  TONGUE_PHASES,
  SUSPICION_THRESHOLD,
  QUARANTINE_CONSENSUS,
} from '../../src/geoseal.js';
import { hyperbolicDistance, phaseDeviation } from '../../src/harmonic/hyperbolic.js';
import { computeMetrics, checkPerformanceThresholds } from '../../src/geosealMetrics.js';

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════

function makeAgent(
  id: string,
  pos: number[],
  phase: number | null,
  tongue?: string
): Agent {
  return createAgent(id, pos, phase, tongue, phase !== null ? 1.0 : 0.5);
}

/** Euclidean norm */
function vecNorm(v: number[]): number {
  return Math.sqrt(v.reduce((a, b) => a + b * b, 0));
}

// ═══════════════════════════════════════════════════════════════
// Hyperbolic distance edge cases
// ═══════════════════════════════════════════════════════════════

describe('Hyperbolic distance', () => {
  it('returns 0 for identical points', () => {
    const p = [0.1, 0.2, 0.3];
    expect(hyperbolicDistance(p, p)).toBeCloseTo(0, 5);
  });

  it('is symmetric', () => {
    const u = [0.1, 0.2];
    const v = [0.3, -0.1];
    expect(hyperbolicDistance(u, v)).toBeCloseTo(hyperbolicDistance(v, u), 10);
  });

  it('increases as points move apart', () => {
    const origin = [0, 0, 0];
    const near = [0.1, 0, 0];
    const far = [0.5, 0, 0];
    expect(hyperbolicDistance(origin, near)).toBeLessThan(
      hyperbolicDistance(origin, far)
    );
  });

  it('returns large distance near boundary', () => {
    const center = [0, 0];
    const boundary = [0.98, 0];
    expect(hyperbolicDistance(center, boundary)).toBeGreaterThan(3);
  });
});

// ═══════════════════════════════════════════════════════════════
// Phase deviation wrapping
// ═══════════════════════════════════════════════════════════════

describe('Phase deviation', () => {
  it('returns 0 for identical phases', () => {
    expect(phaseDeviation(0, 0)).toBeCloseTo(0, 10);
  });

  it('returns 1.0 for null phases', () => {
    expect(phaseDeviation(null, 0.5)).toBe(1.0);
    expect(phaseDeviation(0.5, null)).toBe(1.0);
    expect(phaseDeviation(null, null)).toBe(1.0);
  });

  it('returns 1.0 for opposite phases', () => {
    expect(phaseDeviation(0, Math.PI)).toBeCloseTo(1.0, 5);
  });

  it('handles wrap-around correctly', () => {
    // Phase 0 and phase 2*PI should be very close
    expect(phaseDeviation(0.01, 2 * Math.PI - 0.01)).toBeLessThan(0.02);
  });

  it('is symmetric', () => {
    const p1 = Math.PI / 4;
    const p2 = (3 * Math.PI) / 4;
    expect(phaseDeviation(p1, p2)).toBeCloseTo(phaseDeviation(p2, p1), 10);
  });
});

// ═══════════════════════════════════════════════════════════════
// Repulsion force mechanics
// ═══════════════════════════════════════════════════════════════

describe('computeRepelForce', () => {
  it('produces non-zero force between different agents', () => {
    const a = makeAgent('a', [0.1, 0.0], TONGUE_PHASES.KO, 'KO');
    const b = makeAgent('b', [0.3, 0.0], TONGUE_PHASES.KO, 'KO');
    const result = computeRepelForce(a, b);

    expect(result.force.some((f) => f !== 0)).toBe(true);
    expect(result.anomaly_flag).toBe(false);
    expect(result.amplification).toBe(1.0);
  });

  it('amplifies 2.0x for null-phase (rogue) agents', () => {
    const legit = makeAgent('legit', [0.1, 0.0], TONGUE_PHASES.KO, 'KO');
    const rogue = makeAgent('rogue', [0.15, 0.0], null);
    const result = computeRepelForce(legit, rogue);

    expect(result.amplification).toBe(2.0);
    expect(result.anomaly_flag).toBe(true);
  });

  it('amplifies for phase mismatch at close range', () => {
    // KO (0) vs CA (PI) at close range
    const a = makeAgent('a', [0.1, 0.0], TONGUE_PHASES.KO, 'KO');
    const b = makeAgent('b', [0.15, 0.0], TONGUE_PHASES.CA, 'CA');
    const result = computeRepelForce(a, b);

    expect(result.amplification).toBeGreaterThan(1.5);
    expect(result.anomaly_flag).toBe(true);
  });

  it('does not flag same-phase agents at close range', () => {
    const a = makeAgent('a', [0.1, 0.0], TONGUE_PHASES.KO, 'KO');
    const b = makeAgent('b', [0.15, 0.0], TONGUE_PHASES.KO, 'KO');
    const result = computeRepelForce(a, b);

    expect(result.anomaly_flag).toBe(false);
    expect(result.amplification).toBe(1.0);
  });

  it('further amplifies quarantined agents (1.5x multiplier)', () => {
    const a = makeAgent('a', [0.1, 0.0], TONGUE_PHASES.KO, 'KO');
    const rogue = makeAgent('rogue', [0.15, 0.0], null);
    rogue.is_quarantined = true;

    const result = computeRepelForce(a, rogue);
    // 2.0 (null phase) * 1.5 (quarantined) = 3.0
    expect(result.amplification).toBeCloseTo(3.0, 5);
  });
});

// ═══════════════════════════════════════════════════════════════
// Suspicion counters
// ═══════════════════════════════════════════════════════════════

describe('updateSuspicion', () => {
  it('increments suspicion on anomaly', () => {
    const agent = makeAgent('a', [0, 0], 0);
    updateSuspicion(agent, 'b', true);
    expect(agent.suspicion_count.get('b')).toBe(1);
    updateSuspicion(agent, 'b', true);
    expect(agent.suspicion_count.get('b')).toBe(2);
  });

  it('decays suspicion on non-anomaly', () => {
    const agent = makeAgent('a', [0, 0], 0);
    agent.suspicion_count.set('b', 3);
    updateSuspicion(agent, 'b', false);
    expect(agent.suspicion_count.get('b')).toBe(2.5);
  });

  it('does not go below 0', () => {
    const agent = makeAgent('a', [0, 0], 0);
    updateSuspicion(agent, 'b', false);
    expect(agent.suspicion_count.get('b')).toBe(0);
  });

  it('quarantines when 3+ neighbors have high suspicion', () => {
    const agent = makeAgent('a', [0, 0], 0);
    // Set 3 neighbors above threshold
    agent.suspicion_count.set('n1', SUSPICION_THRESHOLD);
    agent.suspicion_count.set('n2', SUSPICION_THRESHOLD);
    agent.suspicion_count.set('n3', SUSPICION_THRESHOLD);

    // Trigger update to recalculate quarantine
    updateSuspicion(agent, 'n4', false);

    expect(agent.is_quarantined).toBe(true);
  });

  it('does not quarantine with only 2 suspicious neighbors', () => {
    const agent = makeAgent('a', [0, 0], 0);
    agent.suspicion_count.set('n1', SUSPICION_THRESHOLD);
    agent.suspicion_count.set('n2', SUSPICION_THRESHOLD);

    updateSuspicion(agent, 'n3', false);
    expect(agent.is_quarantined).toBe(false);
  });

  it('updates trust score inversely to total suspicion', () => {
    const agent = makeAgent('a', [0, 0], 0);
    // Total suspicion = 10, trust = 1 - 10/20 = 0.5
    agent.suspicion_count.set('n1', 5);
    agent.suspicion_count.set('n2', 5);
    updateSuspicion(agent, 'n3', false);
    expect(agent.trust_score).toBeCloseTo(0.5, 1);
  });
});

// ═══════════════════════════════════════════════════════════════
// Swarm dynamics
// ═══════════════════════════════════════════════════════════════

describe('Swarm dynamics', () => {
  it('pushes rogue agent toward boundary', () => {
    // 4 legitimate KO agents near center + 1 rogue
    const agents = [
      makeAgent('ko1', [0.1, 0.0], TONGUE_PHASES.KO, 'KO'),
      makeAgent('ko2', [-0.1, 0.0], TONGUE_PHASES.KO, 'KO'),
      makeAgent('ko3', [0.0, 0.1], TONGUE_PHASES.KO, 'KO'),
      makeAgent('ko4', [0.0, -0.1], TONGUE_PHASES.KO, 'KO'),
      makeAgent('rogue', [0.05, 0.05], null),
    ];

    const initialRogueNorm = vecNorm(agents[4].position);

    // Run many steps
    runSwarm(agents, 50, 0.005);

    const finalRogueNorm = vecNorm(agents[4].position);
    // Rogue should have been pushed outward
    expect(finalRogueNorm).toBeGreaterThan(initialRogueNorm);
  });

  it('keeps legitimate agents relatively stable', () => {
    const agents = [
      makeAgent('ko1', [0.1, 0.0], TONGUE_PHASES.KO, 'KO'),
      makeAgent('ko2', [-0.1, 0.0], TONGUE_PHASES.KO, 'KO'),
      makeAgent('rogue', [0.05, 0.05], null),
    ];

    const initialTrust1 = agents[0].trust_score;
    runSwarm(agents, 20, 0.005);

    // Legitimate agents should retain higher trust than rogue
    expect(agents[0].trust_score).toBeGreaterThan(agents[2].trust_score);
  });

  it('clamps positions to Poincaré ball', () => {
    const agents = [
      makeAgent('a', [0.95, 0.0], TONGUE_PHASES.KO, 'KO'),
      makeAgent('rogue', [0.96, 0.0], null),
    ];

    runSwarm(agents, 10, 0.01);

    for (const agent of agents) {
      expect(vecNorm(agent.position)).toBeLessThanOrEqual(0.99 + 1e-6);
    }
  });

  it('handles empty agent list gracefully', () => {
    const agents: Agent[] = [];
    expect(() => swarmStep(agents)).not.toThrow();
  });
});

// ═══════════════════════════════════════════════════════════════
// Metrics
// ═══════════════════════════════════════════════════════════════

describe('GeoSeal metrics', () => {
  it('computes metrics for quarantined rogue', () => {
    // Set up agents where rogue is quarantined
    const agents = [
      makeAgent('ko1', [0.1, 0.0], TONGUE_PHASES.KO, 'KO'),
      makeAgent('ko2', [-0.1, 0.0], TONGUE_PHASES.KO, 'KO'),
      makeAgent('ko3', [0.0, 0.1], TONGUE_PHASES.KO, 'KO'),
      makeAgent('ko4', [0.0, -0.1], TONGUE_PHASES.KO, 'KO'),
      makeAgent('rogue', [0.05, 0.05], null),
    ];

    runSwarm(agents, 50, 0.005);

    const metrics = computeMetrics(agents, 'rogue');
    expect(metrics.final_trust_scores.has('rogue')).toBe(true);
    // Rogue trust should be lower than legitimate
    const rogueTrust = metrics.final_trust_scores.get('rogue')!;
    const legitTrust = metrics.final_trust_scores.get('ko1')!;
    expect(rogueTrust).toBeLessThan(legitTrust);
  });

  it('throws for unknown rogue ID', () => {
    const agents = [makeAgent('a', [0, 0], 0)];
    expect(() => computeMetrics(agents, 'nonexistent')).toThrow('not found');
  });

  it('checkPerformanceThresholds validates criteria', () => {
    const goodMetrics = {
      time_to_isolation: 5,
      boundary_norm: 0.8,
      suspicion_consensus: 0.75,
      collateral_flags: 0,
      final_trust_scores: new Map(),
    };

    const result = checkPerformanceThresholds(goodMetrics);
    expect(result.rogue_quarantined).toBe(true);
    expect(result.low_collateral).toBe(true);
    expect(result.high_consensus).toBe(true);
    expect(result.boundary_pushed).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════
// TONGUE_PHASES
// ═══════════════════════════════════════════════════════════════

describe('TONGUE_PHASES', () => {
  it('has all 6 Sacred Tongues', () => {
    expect(Object.keys(TONGUE_PHASES)).toEqual(['KO', 'AV', 'RU', 'CA', 'UM', 'DR']);
  });

  it('phases are evenly spaced on unit circle', () => {
    const phases = Object.values(TONGUE_PHASES);
    for (let i = 1; i < phases.length; i++) {
      const gap = phases[i] - phases[i - 1];
      expect(gap).toBeCloseTo(Math.PI / 3, 5);
    }
  });

  it('all phases are in [0, 2PI)', () => {
    for (const phase of Object.values(TONGUE_PHASES)) {
      expect(phase).toBeGreaterThanOrEqual(0);
      expect(phase).toBeLessThan(2 * Math.PI);
    }
  });
});
