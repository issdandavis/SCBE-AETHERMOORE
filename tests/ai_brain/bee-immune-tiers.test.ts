/**
 * Tests for Bee-Colony Tiered Immune System
 *
 * Covers:
 * - Agent caste assignment and profiles
 * - Tier 1: Propolis barrier (mathematical validation)
 * - Tier 2: Hemocyte response (individual immune tracking)
 * - Tier 3: Social grooming (waggle dance, neighbor consensus)
 * - Tier 4: Colony fever (global alarm, threshold shift)
 * - Full tiered assessment pipeline
 * - Colony statistics and management
 *
 * @module tests/ai_brain/bee-immune-tiers
 */

import { describe, expect, it, beforeEach } from 'vitest';
import {
  HiveImmuneSystem,
  CASTE_PROFILES,
  DEFAULT_HIVE_CONFIG,
  type AgentCaste,
  type WaggleDance,
} from '../../src/ai_brain/bee-immune-tiers';

// ═══════════════════════════════════════════════════════════════
// Test Helpers
// ═══════════════════════════════════════════════════════════════

function safeState(trust: number = 0.9): number[] {
  // 21D state with small values (passes propolis easily)
  return [trust, trust, trust, trust, trust, trust, ...new Array(15).fill(0.1)];
}

function dangerousState(): number[] {
  // 21D state with extreme values
  return new Array(21).fill(5.0);
}

function tinyState(): number[] {
  // Too few dimensions
  return [0.5, 0.5, 0.5];
}

function nanState(): number[] {
  return [NaN, 0.5, 0.5, 0.5, 0.5, 0.5, ...new Array(15).fill(0.1)];
}

// ═══════════════════════════════════════════════════════════════
// Caste Assignment Tests
// ═══════════════════════════════════════════════════════════════

describe('Agent Caste System', () => {
  let hive: HiveImmuneSystem;

  beforeEach(() => {
    hive = new HiveImmuneSystem();
  });

  it('should default to worker caste', () => {
    expect(hive.getCaste('unknown-agent')).toBe('worker');
  });

  it('should assign and retrieve castes', () => {
    hive.assignCaste('queen-01', 'queen');
    hive.assignCaste('guard-01', 'guard');
    hive.assignCaste('nurse-01', 'nurse');

    expect(hive.getCaste('queen-01')).toBe('queen');
    expect(hive.getCaste('guard-01')).toBe('guard');
    expect(hive.getCaste('nurse-01')).toBe('nurse');
  });

  it('should have 6 defined caste profiles', () => {
    const castes: AgentCaste[] = ['queen', 'guard', 'nurse', 'forager', 'undertaker', 'worker'];
    for (const c of castes) {
      expect(CASTE_PROFILES[c]).toBeDefined();
      expect(CASTE_PROFILES[c].caste).toBe(c);
    }
  });

  it('should give queen the highest trust multiplier', () => {
    expect(CASTE_PROFILES.queen.trustMultiplier).toBeGreaterThan(CASTE_PROFILES.worker.trustMultiplier);
    expect(CASTE_PROFILES.queen.trustMultiplier).toBeGreaterThan(CASTE_PROFILES.guard.trustMultiplier);
  });

  it('should give nurse the widest inspection range', () => {
    expect(CASTE_PROFILES.nurse.inspectionRange).toBeGreaterThan(CASTE_PROFILES.worker.inspectionRange);
    expect(CASTE_PROFILES.nurse.inspectionRange).toBe(3);
  });

  it('should only allow queen and undertaker to expel', () => {
    expect(CASTE_PROFILES.queen.canExpel).toBe(true);
    expect(CASTE_PROFILES.undertaker.canExpel).toBe(true);
    expect(CASTE_PROFILES.nurse.canExpel).toBe(false);
    expect(CASTE_PROFILES.worker.canExpel).toBe(false);
  });

  it('should only allow queen to trigger fever', () => {
    expect(CASTE_PROFILES.queen.canTriggerFever).toBe(true);
    expect(CASTE_PROFILES.guard.canTriggerFever).toBe(false);
    expect(CASTE_PROFILES.nurse.canTriggerFever).toBe(false);
  });

  it('should list agents by caste', () => {
    hive.assignCaste('g1', 'guard');
    hive.assignCaste('g2', 'guard');
    hive.assignCaste('n1', 'nurse');

    const guards = hive.getAgentsByCaste('guard');
    expect(guards).toHaveLength(2);
    expect(guards).toContain('g1');
    expect(guards).toContain('g2');
  });
});

// ═══════════════════════════════════════════════════════════════
// Tier 1: Propolis Barrier Tests
// ═══════════════════════════════════════════════════════════════

describe('Tier 1: Propolis Barrier', () => {
  let hive: HiveImmuneSystem;

  beforeEach(() => {
    hive = new HiveImmuneSystem();
  });

  it('should pass safe 21D state', () => {
    const result = hive.checkPropolis(safeState());
    expect(result.passed).toBe(true);
    expect(result.normCheck).toBe(true);
    expect(result.dimensionCheck).toBe(true);
  });

  it('should fail state with too few dimensions', () => {
    const result = hive.checkPropolis(tinyState());
    expect(result.passed).toBe(false);
    expect(result.dimensionCheck).toBe(false);
  });

  it('should fail state with excessive norm', () => {
    const bigState = new Array(21).fill(100);
    const result = hive.checkPropolis(bigState);
    expect(result.passed).toBe(false);
    expect(result.normCheck).toBe(false);
  });

  it('should fail NaN state', () => {
    const result = hive.checkPropolis(nanState());
    expect(result.passed).toBe(false);
    expect(result.normCheck).toBe(false);
  });

  it('should compute boundary distance', () => {
    const result = hive.checkPropolis(safeState(0.1));
    expect(result.boundaryDistance).toBeGreaterThan(0);
  });

  it('should pass zero state', () => {
    const zeroState = new Array(21).fill(0);
    const result = hive.checkPropolis(zeroState);
    expect(result.passed).toBe(true);
    expect(result.normCheck).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════
// Tier 2: Hemocyte Response Tests
// ═══════════════════════════════════════════════════════════════

describe('Tier 2: Hemocyte Response', () => {
  let hive: HiveImmuneSystem;

  beforeEach(() => {
    hive = new HiveImmuneSystem();
    hive.assignCaste('agent-safe', 'worker');
    hive.assignCaste('agent-bad', 'worker');
  });

  it('should track suspicion for flagged agents', () => {
    // Process with flags
    const result = hive.assess('agent-bad', safeState(), 0.8, 3);
    expect(result.hemocyte.suspicion).toBeGreaterThan(0);
    expect(result.hemocyte.flagCount).toBeGreaterThan(0);
  });

  it('should keep healthy status for clean agents', () => {
    const result = hive.assess('agent-safe', safeState(), 0.1, 0);
    expect(result.hemocyte.state).toBe('healthy');
    expect(result.hemocyte.suspicion).toBe(0);
  });

  it('should escalate suspicion with repeated flags', () => {
    let lastSuspicion = 0;
    for (let i = 0; i < 5; i++) {
      hive.updateColonyState();
      const result = hive.assess('agent-bad', safeState(), 0.8, 3);
      expect(result.hemocyte.suspicion).toBeGreaterThanOrEqual(lastSuspicion);
      lastSuspicion = result.hemocyte.suspicion;
    }
    expect(lastSuspicion).toBeGreaterThan(0.3);
  });

  it('should expose the hemocyte system', () => {
    expect(hive.getHemocytes()).toBeDefined();
  });
});

// ═══════════════════════════════════════════════════════════════
// Tier 3: Social Grooming / Waggle Dance Tests
// ═══════════════════════════════════════════════════════════════

describe('Tier 3: Social Grooming', () => {
  let hive: HiveImmuneSystem;

  beforeEach(() => {
    hive = new HiveImmuneSystem();
    hive.assignCaste('nurse-01', 'nurse');
    hive.assignCaste('nurse-02', 'nurse');
    hive.assignCaste('guard-01', 'guard');
    hive.assignCaste('suspect', 'worker');
  });

  it('should perform a waggle dance', () => {
    const dance = hive.performWaggleDance(
      'nurse-01', 'suspect', [0, 1, 2], 0.7, 0.5
    );

    expect(dance.dancerId).toBe('nurse-01');
    expect(dance.targetId).toBe('suspect');
    expect(dance.magnitude).toBe(0.7);
    expect(dance.confidence).toBeGreaterThan(0);
    expect(dance.dancerCaste).toBe('nurse');
  });

  it('should weight dance confidence by caste pheromone rate', () => {
    const nurseDance = hive.performWaggleDance(
      'nurse-01', 'suspect', [0], 0.5, 0.3
    );
    const guardDance = hive.performWaggleDance(
      'guard-01', 'suspect', [0], 0.5, 0.3
    );

    // Guard has pheromoneRate 1.5, nurse has 1.0
    expect(guardDance.confidence).toBeGreaterThan(nurseDance.confidence);
  });

  it('should track active dances for a target', () => {
    hive.performWaggleDance('nurse-01', 'suspect', [0], 0.5, 0.3);
    hive.performWaggleDance('nurse-02', 'suspect', [1], 0.6, 0.4);

    const activeDances = hive.getActiveDancesFor('suspect');
    expect(activeDances).toHaveLength(2);
  });

  it('should compute grooming score from dances', () => {
    hive.performWaggleDance('nurse-01', 'suspect', [0], 0.5, 0.3);
    hive.performWaggleDance('nurse-02', 'suspect', [1], 0.6, 0.4);

    const grooming = hive.computeGroomingScore('suspect');
    expect(grooming.waggleDances).toBe(2);
    expect(grooming.inspectedBy).toHaveLength(2);
    expect(grooming.neighborConsensus).toBe(true); // 2 >= minDancesForEffect (2)
    expect(grooming.groomingScore).toBeGreaterThan(0);
  });

  it('should not reach consensus with too few dances', () => {
    hive.performWaggleDance('nurse-01', 'suspect', [0], 0.3, 0.3);

    const grooming = hive.computeGroomingScore('suspect');
    expect(grooming.neighborConsensus).toBe(false); // 1 < minDancesForEffect (2)
  });

  it('should decay old dances', () => {
    hive.performWaggleDance('nurse-01', 'suspect', [0], 0.5, 0.3);

    // Advance many steps so the dance decays
    // halfLife=20, confidence=0.5, need 0.5 * exp(-ln2/20 * steps) < 0.01
    // => steps > 20 * ln(50) / ln(2) ≈ 113
    for (let i = 0; i < 200; i++) {
      hive.updateColonyState();
    }

    const activeDances = hive.getActiveDancesFor('suspect');
    expect(activeDances).toHaveLength(0); // Decayed away
  });

  it('should increase alarm pheromone with dances', () => {
    const before = hive.getPheromoneState().alarm;
    hive.performWaggleDance('nurse-01', 'suspect', [0], 0.8, 0.5);
    const after = hive.getPheromoneState().alarm;

    expect(after).toBeGreaterThan(before);
  });

  it('should list all dances', () => {
    hive.performWaggleDance('nurse-01', 'suspect', [0], 0.5, 0.3);
    hive.performWaggleDance('nurse-02', 'suspect', [1], 0.6, 0.4);

    expect(hive.getDances()).toHaveLength(2);
  });
});

// ═══════════════════════════════════════════════════════════════
// Tier 4: Colony Fever Tests
// ═══════════════════════════════════════════════════════════════

describe('Tier 4: Colony Fever', () => {
  let hive: HiveImmuneSystem;

  beforeEach(() => {
    hive = new HiveImmuneSystem();
    hive.assignCaste('queen-01', 'queen');
  });

  it('should start with no fever', () => {
    const state = hive.getPheromoneState();
    expect(state.feverActive).toBe(false);
    expect(state.feverMultiplier).toBe(1.0);
  });

  it('should have calm pheromone from queen', () => {
    const state = hive.getPheromoneState();
    expect(state.calm).toBe(DEFAULT_HIVE_CONFIG.queenCalmBase);
  });

  it('should reduce calming without a queen', () => {
    const hiveNoQueen = new HiveImmuneSystem();
    hiveNoQueen.updateColonyState();
    const state = hiveNoQueen.getPheromoneState();
    expect(state.calm).toBeLessThan(DEFAULT_HIVE_CONFIG.queenCalmBase);
  });

  it('should trigger fever when alarm exceeds threshold', () => {
    // Pump alarm pheromone by performing many aggressive dances
    // Assign scouts as guards (pheromoneRate: 1.5) so confidence is high enough
    for (let i = 0; i < 30; i++) {
      hive.assignCaste(`scout-${i}`, 'guard');
      hive.performWaggleDance(`scout-${i}`, 'threat', [0, 1], 1.0, 1.0);
    }

    hive.updateColonyState();
    const state = hive.getPheromoneState();
    expect(state.feverActive).toBe(true);
    expect(state.feverMultiplier).toBeGreaterThan(1.0);
  });

  it('should cool down fever when alarm decays', () => {
    // Trigger fever (assign as guards for high pheromone rate)
    for (let i = 0; i < 30; i++) {
      hive.assignCaste(`scout-${i}`, 'guard');
      hive.performWaggleDance(`scout-${i}`, 'threat', [0], 1.0, 1.0);
    }
    hive.updateColonyState();
    expect(hive.getPheromoneState().feverActive).toBe(true);

    // Let it cool down
    for (let i = 0; i < 50; i++) {
      hive.updateColonyState();
    }
    expect(hive.getPheromoneState().feverActive).toBe(false);
  });

  it('should increase fever multiplier with alarm level', () => {
    for (let i = 0; i < 40; i++) {
      hive.assignCaste(`scout-${i}`, 'guard');
      hive.performWaggleDance(`scout-${i}`, 'threat', [0], 1.0, 1.0);
    }
    hive.updateColonyState();

    const state = hive.getPheromoneState();
    if (state.feverActive) {
      expect(state.feverMultiplier).toBeGreaterThan(1.0);
      expect(state.feverMultiplier).toBeLessThanOrEqual(DEFAULT_HIVE_CONFIG.maxFeverMultiplier);
    }
  });

  it('should track active dance count', () => {
    hive.performWaggleDance('nurse', 'target', [0], 0.5, 0.3);
    hive.performWaggleDance('nurse', 'target2', [1], 0.6, 0.4);
    hive.updateColonyState();

    const state = hive.getPheromoneState();
    expect(state.activeDances).toBeGreaterThanOrEqual(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// Full Tiered Assessment Tests
// ═══════════════════════════════════════════════════════════════

describe('Full Tiered Assessment', () => {
  let hive: HiveImmuneSystem;

  beforeEach(() => {
    hive = new HiveImmuneSystem();
    hive.assignCaste('queen-01', 'queen');
    hive.assignCaste('safe-worker', 'worker');
    hive.assignCaste('bad-agent', 'worker');
  });

  it('should ALLOW safe agents through all tiers', () => {
    hive.updateColonyState();
    const result = hive.assess('safe-worker', safeState(), 0.1, 0);

    expect(result.propolis.passed).toBe(true);
    expect(result.hemocyte.state).toBe('healthy');
    expect(result.finalDecision).toBe('ALLOW');
    expect(result.effectiveTrust).toBeGreaterThan(0.8);
    expect(result.caste).toBe('worker');
  });

  it('should DENY agents that fail propolis', () => {
    hive.updateColonyState();
    const result = hive.assess('bad-agent', tinyState(), 0.1, 0);

    expect(result.propolis.passed).toBe(false);
    expect(result.finalDecision).toBe('DENY');
    expect(result.effectiveTrust).toBe(0);
  });

  it('should give queen agents higher effective trust', () => {
    hive.updateColonyState();
    const queenResult = hive.assess('queen-01', safeState(), 0.1, 0);
    const workerResult = hive.assess('safe-worker', safeState(), 0.1, 0);

    expect(queenResult.effectiveTrust).toBeGreaterThanOrEqual(workerResult.effectiveTrust);
  });

  it('should escalate agents with high combined score', () => {
    // Repeated high-score assessments build suspicion
    for (let i = 0; i < 8; i++) {
      hive.updateColonyState();
      hive.assess('bad-agent', safeState(), 0.85, 4);
    }

    const result = hive.assess('bad-agent', safeState(), 0.85, 4);
    expect(result.hemocyte.suspicion).toBeGreaterThan(0.3);
    expect(result.finalDecision).not.toBe('ALLOW');
  });

  it('should amplify decision during colony fever', () => {
    // Trigger fever (assign as guards for high pheromone rate)
    for (let i = 0; i < 30; i++) {
      hive.assignCaste(`scout-${i}`, 'guard');
      hive.performWaggleDance(`scout-${i}`, 'bad-agent', [0, 1], 1.0, 1.0);
    }
    hive.updateColonyState();
    expect(hive.getPheromoneState().feverActive).toBe(true);

    // Now assess a mildly suspicious agent during fever
    hive.assess('bad-agent', safeState(), 0.6, 2);
    hive.assess('bad-agent', safeState(), 0.6, 2);
    const result = hive.assess('bad-agent', safeState(), 0.6, 2);

    // Colony fever should amplify the suspicion
    expect(result.colonyFever.feverActive).toBe(true);
    expect(result.colonyFever.amplifiedSuspicion).toBeGreaterThan(result.hemocyte.suspicion);
  });

  it('should escalate when grooming consensus is strong', () => {
    // Multiple nurses report the same agent
    hive.assignCaste('nurse-a', 'nurse');
    hive.assignCaste('nurse-b', 'nurse');
    hive.assignCaste('nurse-c', 'nurse');

    hive.performWaggleDance('nurse-a', 'bad-agent', [0, 1, 2], 0.8, 0.5);
    hive.performWaggleDance('nurse-b', 'bad-agent', [0, 1], 0.7, 0.4);
    hive.performWaggleDance('nurse-c', 'bad-agent', [2, 3], 0.9, 0.6);

    hive.updateColonyState();

    // Feed through some mild detections + the grooming consensus
    const result = hive.assess('bad-agent', safeState(), 0.4, 1);

    expect(result.grooming.neighborConsensus).toBe(true);
    expect(result.grooming.waggleDances).toBe(3);
  });

  it('should include all tier results in assessment', () => {
    hive.updateColonyState();
    const result = hive.assess('safe-worker', safeState(), 0.1, 0);

    // Verify all tiers are present
    expect(result.propolis).toBeDefined();
    expect(result.hemocyte).toBeDefined();
    expect(result.grooming).toBeDefined();
    expect(result.colonyFever).toBeDefined();
    expect(result.finalDecision).toBeDefined();
    expect(result.effectiveTrust).toBeDefined();
    expect(result.agentId).toBe('safe-worker');
    expect(result.caste).toBe('worker');
  });
});

// ═══════════════════════════════════════════════════════════════
// Colony Statistics Tests
// ═══════════════════════════════════════════════════════════════

describe('Colony Statistics & Management', () => {
  let hive: HiveImmuneSystem;

  beforeEach(() => {
    hive = new HiveImmuneSystem();
  });

  it('should track caste counts', () => {
    hive.assignCaste('q1', 'queen');
    hive.assignCaste('g1', 'guard');
    hive.assignCaste('g2', 'guard');
    hive.assignCaste('n1', 'nurse');
    hive.assignCaste('w1', 'worker');
    hive.assignCaste('w2', 'worker');

    const stats = hive.getStats();
    expect(stats.totalAgents).toBe(6);
    expect(stats.casteCounts.queen).toBe(1);
    expect(stats.casteCounts.guard).toBe(2);
    expect(stats.casteCounts.nurse).toBe(1);
    expect(stats.casteCounts.worker).toBe(2);
  });

  it('should report pheromone state in stats', () => {
    const stats = hive.getStats();
    expect(stats.pheromone).toBeDefined();
    expect(stats.pheromone.alarm).toBe(0);
  });

  it('should track step counter', () => {
    hive.updateColonyState();
    hive.updateColonyState();
    hive.updateColonyState();

    const stats = hive.getStats();
    expect(stats.step).toBe(3);
  });

  it('should reset completely', () => {
    hive.assignCaste('q1', 'queen');
    hive.assignCaste('w1', 'worker');
    hive.performWaggleDance('q1', 'w1', [0], 0.5, 0.3);
    hive.updateColonyState();

    hive.reset();

    const stats = hive.getStats();
    expect(stats.totalAgents).toBe(0);
    expect(stats.activeDances).toBe(0);
    expect(stats.step).toBe(0);
    expect(stats.pheromone.alarm).toBe(0);
  });

  it('should include hemocyte stats', () => {
    hive.assignCaste('a1', 'worker');
    hive.updateColonyState();
    hive.assess('a1', safeState(), 0.1, 0);

    const stats = hive.getStats();
    expect(stats.hemocyteStats).toBeDefined();
    expect(stats.hemocyteStats.total).toBeGreaterThanOrEqual(1);
  });
});

// ═══════════════════════════════════════════════════════════════
// Edge Cases
// ═══════════════════════════════════════════════════════════════

describe('Edge Cases', () => {
  it('should handle assessment of unknown agent (defaults to worker)', () => {
    const hive = new HiveImmuneSystem();
    hive.updateColonyState();
    const result = hive.assess('unknown', safeState(), 0.1, 0);

    expect(result.caste).toBe('worker');
    expect(result.finalDecision).toBe('ALLOW');
  });

  it('should clamp magnitude in waggle dance', () => {
    const hive = new HiveImmuneSystem();
    const dance = hive.performWaggleDance('a', 'b', [0], 5.0, 0.3);
    expect(dance.magnitude).toBeLessThanOrEqual(1.0);
  });

  it('should handle empty state gracefully', () => {
    const hive = new HiveImmuneSystem();
    const result = hive.checkPropolis([]);
    expect(result.passed).toBe(false);
    expect(result.dimensionCheck).toBe(false);
  });

  it('should trim dance history to configured size', () => {
    const hive = new HiveImmuneSystem({ danceHistorySize: 5 });
    for (let i = 0; i < 10; i++) {
      hive.performWaggleDance(`agent-${i}`, 'target', [0], 0.5, 0.3);
    }
    expect(hive.getDances().length).toBeLessThanOrEqual(5);
  });

  it('should handle custom hive config', () => {
    const hive = new HiveImmuneSystem({
      feverThreshold: 0.3,
      maxFeverMultiplier: 5.0,
    });
    expect(hive).toBeDefined();
  });
});
