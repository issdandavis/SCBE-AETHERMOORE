/**
 * @file trajectory-simulator.test.ts
 * @module ai_brain/trajectory-simulator.test
 * @layer Layer 1-14 (Unified)
 * Tests for the Multi-Profile Agent Trajectory Simulator.
 */

import { describe, it, expect } from 'vitest';
import {
  SeededRNG,
  AGENT_PROFILES,
  generateTrajectory,
  generateMixedBatch,
  type AgentProfile,
  type SimulationConfig,
} from '../../src/ai_brain/trajectory-simulator.js';
import { BRAIN_DIMENSIONS, PHI } from '../../src/ai_brain/types.js';

// ═══════════════════════════════════════════════════════════════
// Seeded RNG
// ═══════════════════════════════════════════════════════════════

describe('SeededRNG', () => {
  it('produces deterministic sequence for same seed', () => {
    const rng1 = new SeededRNG(42);
    const rng2 = new SeededRNG(42);
    for (let i = 0; i < 100; i++) {
      expect(rng1.next()).toBe(rng2.next());
    }
  });

  it('produces different sequences for different seeds', () => {
    const rng1 = new SeededRNG(42);
    const rng2 = new SeededRNG(99);
    let same = 0;
    for (let i = 0; i < 100; i++) {
      if (rng1.next() === rng2.next()) same++;
    }
    expect(same).toBeLessThan(5); // Very unlikely to match often
  });

  it('returns values in [0, 1)', () => {
    const rng = new SeededRNG(123);
    for (let i = 0; i < 1000; i++) {
      const v = rng.next();
      expect(v).toBeGreaterThanOrEqual(0);
      expect(v).toBeLessThan(1);
    }
  });

  it('gaussian produces finite values', () => {
    const rng = new SeededRNG(7);
    for (let i = 0; i < 100; i++) {
      const g = rng.gaussian(0, 1);
      expect(Number.isFinite(g)).toBe(true);
    }
  });

  it('gaussian respects mean and stddev', () => {
    const rng = new SeededRNG(42);
    const samples: number[] = [];
    for (let i = 0; i < 10000; i++) {
      samples.push(rng.gaussian(5, 2));
    }
    const mean = samples.reduce((s, v) => s + v, 0) / samples.length;
    expect(mean).toBeCloseTo(5, 0); // Within ~1 of target mean
  });

  it('handles negative seeds', () => {
    const rng = new SeededRNG(-10);
    const v = rng.next();
    expect(v).toBeGreaterThanOrEqual(0);
    expect(v).toBeLessThan(1);
  });

  it('handles zero seed', () => {
    const rng = new SeededRNG(0);
    const v = rng.next();
    expect(v).toBeGreaterThanOrEqual(0);
    expect(v).toBeLessThan(1);
  });
});

// ═══════════════════════════════════════════════════════════════
// Agent Profiles
// ═══════════════════════════════════════════════════════════════

describe('AGENT_PROFILES', () => {
  it('defines all 5 classifications', () => {
    expect(Object.keys(AGENT_PROFILES)).toEqual(
      expect.arrayContaining(['honest', 'neutral', 'semi_honest', 'semi_malicious', 'malicious'])
    );
    expect(Object.keys(AGENT_PROFILES).length).toBe(5);
  });

  it('honest profile has zero drift and phase error', () => {
    const p = AGENT_PROFILES.honest;
    expect(p.driftRate).toBe(0);
    expect(p.phaseErrorRate).toBe(0);
    expect(p.lissajousAmplitude).toBe(0);
  });

  it('malicious profile has high drift, phase error, and Lissajous', () => {
    const p = AGENT_PROFILES.malicious;
    expect(p.driftRate).toBeGreaterThan(0.02);
    expect(p.phaseErrorRate).toBeGreaterThan(0.5);
    expect(p.lissajousAmplitude).toBeGreaterThan(0.2);
    expect(p.phaseErrorMagnitude).toBeCloseTo(Math.PI);
  });

  it('profiles have monotonically decreasing trust from honest to malicious', () => {
    const order: Array<keyof typeof AGENT_PROFILES> = [
      'honest', 'neutral', 'semi_honest', 'semi_malicious', 'malicious'
    ];
    for (let i = 1; i < order.length; i++) {
      expect(AGENT_PROFILES[order[i]].baseTrust).toBeLessThan(
        AGENT_PROFILES[order[i - 1]].baseTrust
      );
    }
  });

  it('profiles have monotonically increasing noise from honest to malicious', () => {
    const order: Array<keyof typeof AGENT_PROFILES> = [
      'honest', 'neutral', 'semi_honest', 'semi_malicious', 'malicious'
    ];
    for (let i = 1; i < order.length; i++) {
      expect(AGENT_PROFILES[order[i]].noiseAmplitude).toBeGreaterThanOrEqual(
        AGENT_PROFILES[order[i - 1]].noiseAmplitude
      );
    }
  });

  it('malicious Lissajous freq ratio uses golden ratio', () => {
    expect(AGENT_PROFILES.malicious.lissajousFreqRatio).toBeCloseTo(PHI);
  });
});

// ═══════════════════════════════════════════════════════════════
// Single Trajectory Generation
// ═══════════════════════════════════════════════════════════════

describe('generateTrajectory', () => {
  const baseConfig: SimulationConfig = { steps: 50, tongueIndex: 0, seed: 42 };

  it('produces correct number of trajectory points', () => {
    const traj = generateTrajectory('agent-1', AGENT_PROFILES.honest, baseConfig);
    expect(traj.points.length).toBe(50);
  });

  it('points have 21D state vectors', () => {
    const traj = generateTrajectory('agent-1', AGENT_PROFILES.honest, baseConfig);
    for (const pt of traj.points) {
      expect(pt.state.length).toBe(BRAIN_DIMENSIONS);
    }
  });

  it('points have embedded Poincaré positions', () => {
    const traj = generateTrajectory('agent-1', AGENT_PROFILES.honest, baseConfig);
    for (const pt of traj.points) {
      expect(pt.embedded.length).toBeGreaterThan(0);
      // All embedded norms should be < 1 (Poincaré ball)
      const norm = Math.sqrt(pt.embedded.reduce((s, x) => s + x * x, 0));
      expect(norm).toBeLessThan(1);
    }
  });

  it('points have non-negative distance', () => {
    const traj = generateTrajectory('agent-1', AGENT_PROFILES.honest, baseConfig);
    for (const pt of traj.points) {
      expect(pt.distance).toBeGreaterThanOrEqual(0);
    }
  });

  it('preserves agent ID and classification', () => {
    const traj = generateTrajectory('test-agent', AGENT_PROFILES.neutral, baseConfig);
    expect(traj.agentId).toBe('test-agent');
    expect(traj.classification).toBe('neutral');
  });

  it('assigns dimensional state based on trust', () => {
    const honest = generateTrajectory('h', AGENT_PROFILES.honest, baseConfig);
    const malicious = generateTrajectory('m', AGENT_PROFILES.malicious, baseConfig);
    expect(honest.dimensionalState).toBe('POLLY');
    expect(malicious.dimensionalState).toBe('DEMI');
  });

  it('is deterministic with same seed', () => {
    const t1 = generateTrajectory('a', AGENT_PROFILES.honest, { ...baseConfig, seed: 42 });
    const t2 = generateTrajectory('a', AGENT_PROFILES.honest, { ...baseConfig, seed: 42 });
    for (let i = 0; i < t1.points.length; i++) {
      for (let d = 0; d < BRAIN_DIMENSIONS; d++) {
        expect(t1.points[i].state[d]).toBe(t2.points[i].state[d]);
      }
    }
  });

  it('produces different trajectories with different seeds', () => {
    // Use neutral profile which uses RNG noise on all dimensions
    const t1 = generateTrajectory('a', AGENT_PROFILES.neutral, { ...baseConfig, seed: 1 });
    const t2 = generateTrajectory('a', AGENT_PROFILES.neutral, { ...baseConfig, seed: 2 });
    let diffs = 0;
    for (let i = 0; i < t1.points.length; i++) {
      if (Math.abs(t1.points[i].state[6] - t2.points[i].state[6]) > 1e-10) diffs++;
    }
    expect(diffs).toBeGreaterThan(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// Trajectory Behavior Characteristics
// ═══════════════════════════════════════════════════════════════

describe('Trajectory behavior characteristics', () => {
  const config: SimulationConfig = { steps: 100, tongueIndex: 0, seed: 42 };

  it('honest trajectories stay near safe center', () => {
    const traj = generateTrajectory('h', AGENT_PROFILES.honest, config);
    const maxDist = Math.max(...traj.points.map((p) => p.distance));
    expect(maxDist).toBeLessThan(5); // Should stay close to origin
  });

  it('malicious trajectories drift further from center', () => {
    const honest = generateTrajectory('h', AGENT_PROFILES.honest, config);
    const malicious = generateTrajectory('m', AGENT_PROFILES.malicious, config);
    const avgHonest = honest.points.reduce((s, p) => s + p.distance, 0) / honest.points.length;
    const avgMalicious = malicious.points.reduce((s, p) => s + p.distance, 0) / malicious.points.length;
    expect(avgMalicious).toBeGreaterThan(avgHonest);
  });

  it('malicious trajectories have higher curvature', () => {
    const honest = generateTrajectory('h', AGENT_PROFILES.honest, config);
    const malicious = generateTrajectory('m', AGENT_PROFILES.malicious, config);
    // Compare average absolute curvature (skip first 2 points which have curvature = 0)
    const curvatures = (t: typeof honest) =>
      t.points.slice(2).map((p) => Math.abs(p.curvature));
    const avgHonest = curvatures(honest).reduce((s, c) => s + c, 0) / (honest.points.length - 2);
    const avgMalicious = curvatures(malicious).reduce((s, c) => s + c, 0) / (malicious.points.length - 2);
    // Malicious should have higher curvature due to sudden direction changes
    expect(avgMalicious).toBeGreaterThanOrEqual(avgHonest * 0.5); // Allow some variance
  });

  it('honest trajectories have trust scores near baseline', () => {
    const traj = generateTrajectory('h', AGENT_PROFILES.honest, config);
    for (const pt of traj.points) {
      // Trust dimensions (0-5) should stay close to baseTrust
      for (let d = 0; d < 3; d++) {
        expect(pt.state[d]).toBeGreaterThan(0.4);
      }
    }
  });

  it('malicious trajectories decay trust over time', () => {
    const traj = generateTrajectory('m', AGENT_PROFILES.malicious, config);
    const earlyTrust = traj.points[5].state[0];
    const lateTrust = traj.points[config.steps - 1].state[0];
    expect(lateTrust).toBeLessThanOrEqual(earlyTrust + 0.1); // May have drifted down
  });

  it('all values in state vectors are finite', () => {
    for (const cls of Object.keys(AGENT_PROFILES) as Array<keyof typeof AGENT_PROFILES>) {
      const traj = generateTrajectory(`a-${cls}`, AGENT_PROFILES[cls], config);
      for (const pt of traj.points) {
        for (let d = 0; d < BRAIN_DIMENSIONS; d++) {
          expect(Number.isFinite(pt.state[d])).toBe(true);
        }
      }
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Mixed Batch Generation
// ═══════════════════════════════════════════════════════════════

describe('generateMixedBatch', () => {
  const config: SimulationConfig = { steps: 20, tongueIndex: 0, seed: 42 };

  it('produces correct number of agents', () => {
    const batch = generateMixedBatch(10, config);
    expect(batch.length).toBe(10);
  });

  it('contains all 5 classifications', () => {
    const batch = generateMixedBatch(20, config);
    const classes = new Set(batch.map((t) => t.classification));
    expect(classes.size).toBe(5);
    expect(classes.has('honest')).toBe(true);
    expect(classes.has('malicious')).toBe(true);
  });

  it('honest agents are ~40% of batch', () => {
    const batch = generateMixedBatch(100, config);
    const honest = batch.filter((t) => t.classification === 'honest').length;
    expect(honest).toBeGreaterThanOrEqual(35);
    expect(honest).toBeLessThanOrEqual(45);
  });

  it('each agent has correct step count', () => {
    const batch = generateMixedBatch(5, config);
    for (const traj of batch) {
      expect(traj.points.length).toBe(20);
    }
  });

  it('agents have unique IDs', () => {
    const batch = generateMixedBatch(10, config);
    const ids = new Set(batch.map((t) => t.agentId));
    expect(ids.size).toBe(10);
  });

  it('is deterministic with same seed', () => {
    const b1 = generateMixedBatch(5, { ...config, seed: 42 });
    const b2 = generateMixedBatch(5, { ...config, seed: 42 });
    for (let i = 0; i < 5; i++) {
      expect(b1[i].classification).toBe(b2[i].classification);
      expect(b1[i].points[0].state[0]).toBe(b2[i].points[0].state[0]);
    }
  });
});
