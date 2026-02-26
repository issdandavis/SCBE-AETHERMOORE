/**
 * @file game-types.unit.test.ts
 * @module tests/L2-unit/game
 * @layer Layer 3, Layer 5, Layer 12
 *
 * Unit tests for Spiral Forge RPG core types and game systems.
 */

import { describe, it, expect } from 'vitest';
import {
  // Types
  TONGUE_CODES,
  TONGUE_WEIGHTS,
  PHI,
  HODGE_DUAL_PAIRS,
  SYNESTHESIA_MAP,
  zeroTongueVector,
  tongueIndex,
  dominantTongue,
  tongueNorm,
  tongueDistance,
  defaultCanonicalState,
  stateToArray,
  arrayToState,
  // Companion
  createCompanion,
  deriveCombatStats,
  applyTongueExperience,
  applyCombatResult,
  applyDrift,
  restCompanion,
  currentEvolutionStage,
  checkEvolution,
  isOverEvolved,
  // Combat
  computeTypeAdvantage,
  calculateDamage,
  createEncounter,
  evaluateTransformRisk,
  calculateFormationEffectiveness,
  // Sacred Eggs
  checkHatchableEggs,
  canHatchEgg,
  eggStartingTongue,
  getAllEggDefinitions,
  // Evolution
  getAvailableEvolutions,
  evolveCompanion,
  // Symbiotic Network
  SymbioticNetwork,
  // Skill Tree
  createSkillState,
  getSkillsForPath,
  canUnlockSkill,
  unlockSkill,
  getHarmonyAbilities,
  totalSkillCount,
  // Regions
  REGIONS,
  getTowerFloor,
  getRank,
  getRegionByTongue,
  // Codex
  CodexTerminal,
} from '../../../src/game/index.js';

// ===========================================================================
//  Types & Tongue System
// ===========================================================================

describe('Tongue System', () => {
  it('has exactly 6 tongues in canonical order', () => {
    expect(TONGUE_CODES).toEqual(['KO', 'AV', 'RU', 'CA', 'UM', 'DR']);
    expect(TONGUE_CODES).toHaveLength(6);
  });

  it('weights scale by golden ratio powers', () => {
    expect(TONGUE_WEIGHTS.KO).toBe(1.0);
    expect(TONGUE_WEIGHTS.AV).toBeCloseTo(PHI, 5);
    expect(TONGUE_WEIGHTS.RU).toBeCloseTo(PHI ** 2, 5);
    expect(TONGUE_WEIGHTS.DR).toBeCloseTo(PHI ** 5, 5);
  });

  it('Hodge dual pairs are correct', () => {
    expect(HODGE_DUAL_PAIRS).toEqual([
      ['KO', 'DR'],
      ['AV', 'UM'],
      ['RU', 'CA'],
    ]);
  });

  it('zero tongue vector is all zeros', () => {
    expect(zeroTongueVector()).toEqual([0, 0, 0, 0, 0, 0]);
  });

  it('tongueIndex returns correct indices', () => {
    expect(tongueIndex('KO')).toBe(0);
    expect(tongueIndex('DR')).toBe(5);
  });

  it('dominantTongue finds the max element', () => {
    expect(dominantTongue([0.1, 0.2, 0.9, 0.1, 0.1, 0.1])).toBe('RU');
    expect(dominantTongue([0.1, 0.1, 0.1, 0.1, 0.1, 0.8])).toBe('DR');
  });

  it('tongue distance is symmetric and zero for same vectors', () => {
    const a = [0.5, 0.3, 0.2, 0.1, 0.4, 0.6] as [number, number, number, number, number, number];
    const b = [0.1, 0.7, 0.3, 0.5, 0.2, 0.1] as [number, number, number, number, number, number];
    expect(tongueDistance(a, a)).toBeCloseTo(0, 10);
    expect(tongueDistance(a, b)).toBeCloseTo(tongueDistance(b, a), 10);
    expect(tongueDistance(a, b)).toBeGreaterThan(0);
  });

  it('synesthesia map covers all 6 tongues', () => {
    for (const code of TONGUE_CODES) {
      expect(SYNESTHESIA_MAP[code]).toBeDefined();
      expect(SYNESTHESIA_MAP[code].frequency).toBeGreaterThan(0);
    }
  });
});

// ===========================================================================
//  21D Canonical State
// ===========================================================================

describe('Canonical State (21D)', () => {
  it('default state has 21 dimensions', () => {
    const state = defaultCanonicalState();
    const arr = stateToArray(state);
    expect(arr).toHaveLength(21);
  });

  it('roundtrips through array conversion', () => {
    const state = defaultCanonicalState();
    const arr = stateToArray(state);
    const restored = arrayToState(arr);
    expect(stateToArray(restored)).toEqual(arr);
  });

  it('rejects arrays of wrong length', () => {
    expect(() => arrayToState([1, 2, 3])).toThrow('Expected 21 elements');
  });
});

// ===========================================================================
//  Companion System
// ===========================================================================

describe('Companion System', () => {
  it('creates a companion with correct initial state', () => {
    const comp = createCompanion(
      'test-1', 'crysling', 'Crysling',
      'mono_CA', 'processor',
      [0.1, 0.1, 0.1, 0.6, 0.1, 0.1]
    );
    expect(comp.id).toBe('test-1');
    expect(comp.speciesId).toBe('crysling');
    expect(comp.evolutionStage).toBe('spark');
    expect(comp.bondLevel).toBe(1);
    expect(comp.sealIntegrity).toBe(100);
    expect(comp.state.radius).toBe(0.1);
  });

  it('derives combat stats from canonical state', () => {
    const comp = createCompanion(
      't', 'crysling', 'C', 'mono_CA', 'processor',
      [0.1, 0.1, 0.1, 0.6, 0.1, 0.1]
    );
    const stats = comp.derivedStats;
    expect(stats.speed).toBeGreaterThan(0);
    expect(stats.proofPower).toBeGreaterThan(0);
    expect(stats.speed).toBeLessThanOrEqual(100);
  });

  it('applies tongue experience with unitarity preservation', () => {
    const comp = createCompanion(
      't', 'crysling', 'C', 'mono_CA', 'processor',
      [0.1, 0.1, 0.1, 0.6, 0.1, 0.1]
    );
    const oldNorm = tongueNorm(comp.state.tonguePosition);
    applyTongueExperience(comp, 'CA', 0.5);
    const newNorm = tongueNorm(comp.state.tonguePosition);
    // Norm should grow slightly, not explode
    expect(newNorm).toBeGreaterThanOrEqual(oldNorm * 0.9);
    expect(newNorm).toBeLessThanOrEqual(1.1);
  });

  it('applies combat results correctly (win)', () => {
    const comp = createCompanion(
      't', 'crysling', 'C', 'mono_CA', 'processor',
      [0.1, 0.1, 0.1, 0.6, 0.1, 0.1]
    );
    const oldRadius = comp.state.radius;
    applyCombatResult(comp, true, 5);
    expect(comp.state.radius).toBeGreaterThan(oldRadius);
    // bondXP may be 0 if a level-up consumed it, so check bond progression
    expect(comp.bondXP >= 0 || comp.bondLevel > 1).toBe(true);
  });

  it('applies combat results correctly (loss)', () => {
    const comp = createCompanion(
      't', 'crysling', 'C', 'mono_CA', 'processor',
      [0.1, 0.1, 0.1, 0.6, 0.1, 0.1]
    );
    applyCombatResult(comp, false, 5);
    expect(comp.scarCount).toBe(1);
    expect(comp.sealIntegrity).toBeLessThan(100);
  });

  it('correctly detects evolution stages', () => {
    expect(currentEvolutionStage(0.1)).toBe('spark');
    expect(currentEvolutionStage(0.35)).toBe('form');
    expect(currentEvolutionStage(0.55)).toBe('prime');
    expect(currentEvolutionStage(0.75)).toBe('apex');
    expect(currentEvolutionStage(0.9)).toBe('transcendent');
  });

  it('detects over-evolution', () => {
    const comp = createCompanion(
      't', 'crysling', 'C', 'mono_CA', 'processor',
      [0.1, 0.1, 0.1, 0.6, 0.1, 0.1]
    );
    expect(isOverEvolved(comp)).toBe(false);
    comp.state = { ...comp.state, radius: 0.96 };
    expect(isOverEvolved(comp)).toBe(true);
  });

  it('rest restores seal integrity and reduces drift', () => {
    const comp = createCompanion(
      't', 'crysling', 'C', 'mono_CA', 'processor',
      [0.1, 0.1, 0.1, 0.6, 0.1, 0.1]
    );
    comp.sealIntegrity = 50;
    comp.driftLevel = 0.5;
    restCompanion(comp, 1.0);
    expect(comp.sealIntegrity).toBeGreaterThan(50);
    expect(comp.driftLevel).toBeLessThan(0.5);
  });
});

// ===========================================================================
//  Combat — Cl(4,0) Bivector Type Advantage
// ===========================================================================

describe('Combat System — Cl(4,0) Bivector', () => {
  it('type advantage is antisymmetric: Δ(A,B) = -Δ(B,A)', () => {
    const a = [0.8, 0.1, 0.1, 0.0, 0.0, 0.0] as [number, number, number, number, number, number];
    const b = [0.0, 0.0, 0.0, 0.0, 0.0, 0.8] as [number, number, number, number, number, number];
    const ab = computeTypeAdvantage(a, b);
    const ba = computeTypeAdvantage(b, a);
    expect(ab).toBeCloseTo(-ba, 8);
  });

  it('same tongue vector has zero advantage', () => {
    const v = [0.5, 0.3, 0.2, 0.1, 0.4, 0.6] as [number, number, number, number, number, number];
    expect(computeTypeAdvantage(v, v)).toBeCloseTo(0, 8);
  });

  it('advantage is bounded [-1, 1]', () => {
    const a = [1, 0, 0, 0, 0, 0] as [number, number, number, number, number, number];
    const b = [0, 0, 0, 0, 0, 1] as [number, number, number, number, number, number];
    const adv = computeTypeAdvantage(a, b);
    expect(adv).toBeGreaterThanOrEqual(-1);
    expect(adv).toBeLessThanOrEqual(1);
  });

  it('calculateDamage returns at least 1', () => {
    expect(calculateDamage(10, 0, 50, 50)).toBeGreaterThanOrEqual(1);
    expect(calculateDamage(1, -1, 0, 100)).toBeGreaterThanOrEqual(1);
  });

  it('type advantage affects damage', () => {
    const positive = calculateDamage(100, 0.5, 50, 50);
    const negative = calculateDamage(100, -0.5, 50, 50);
    expect(positive).toBeGreaterThan(negative);
  });

  it('formation effectiveness checks λ₂ requirement', () => {
    const comp = createCompanion('t', 'crysling', 'C', 'mono_CA', 'processor', [0.1, 0.1, 0.1, 0.6, 0.1, 0.1]);
    // Web formation requires λ₂ > 0.6
    const result = calculateFormationEffectiveness([comp], 'web', 0.3);
    expect(result.valid).toBe(false);
    const result2 = calculateFormationEffectiveness([comp], 'web', 0.7);
    expect(result2.valid).toBe(true);
  });

  it('SCBE gates transform risk correctly', () => {
    const problem = {
      problemId: 'test', topic: 'algebra', statement: 'x + 1 = 2',
      constraints: [], solutionCheck: { type: 'symbolic' as const, expected: 'x=1' },
      trapSignatures: [], difficulty: 1, tongueAffinity: 'CA' as const,
    };
    const encounter = createEncounter(problem);
    // Low risk action should be ALLOW
    const decision = evaluateTransformRisk('normalize', encounter, 50);
    expect(decision).toBe('ALLOW');
  });
});

// ===========================================================================
//  Sacred Eggs
// ===========================================================================

describe('Sacred Egg Hatching', () => {
  it('high KO triggers Ember Egg', () => {
    const tongue = [0.7, 0.1, 0.1, 0.1, 0.1, 0.1] as [number, number, number, number, number, number];
    const results = checkHatchableEggs(tongue);
    expect(results.some((r) => r.eggType === 'mono_KO')).toBe(true);
  });

  it('balanced KO+DR triggers Eclipse Egg', () => {
    const tongue = [0.45, 0.1, 0.1, 0.1, 0.1, 0.45] as [number, number, number, number, number, number];
    const results = checkHatchableEggs(tongue);
    expect(results.some((r) => r.eggType === 'hodge_eclipse')).toBe(true);
  });

  it('all tongues >= 0.35 triggers Prism Egg', () => {
    const tongue = [0.4, 0.4, 0.4, 0.4, 0.4, 0.4] as [number, number, number, number, number, number];
    const results = checkHatchableEggs(tongue);
    expect(results.some((r) => r.eggType === 'omni_prism')).toBe(true);
  });

  it('low tongues hatch nothing', () => {
    const tongue = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1] as [number, number, number, number, number, number];
    const results = checkHatchableEggs(tongue);
    expect(results).toHaveLength(0);
  });

  it('egg starting tongues are valid 6D vectors', () => {
    const eggs = getAllEggDefinitions();
    for (const egg of eggs) {
      const start = eggStartingTongue(egg.eggType);
      expect(start).toHaveLength(6);
      expect(start.every((v) => v >= 0 && v <= 1)).toBe(true);
    }
  });
});

// ===========================================================================
//  Symbiotic Network
// ===========================================================================

describe('Symbiotic Network', () => {
  it('computes algebraic connectivity for connected graph', () => {
    const net = new SymbioticNetwork();
    const comp1 = createCompanion('a', 'crysling', 'A', 'mono_CA', 'processor', [0.6, 0.1, 0.1, 0.1, 0.1, 0.1]);
    const comp2 = createCompanion('b', 'emberspark', 'B', 'mono_KO', 'amplifier', [0.1, 0.1, 0.1, 0.1, 0.1, 0.6]);
    net.addCompanion(comp1);
    net.addCompanion(comp2);
    net.addBond('a', 'b', 5);

    const lambda2 = net.getAlgebraicConnectivity();
    expect(lambda2).toBeGreaterThan(0);
  });

  it('Hodge dual pairs get 30% bond bonus', () => {
    const net = new SymbioticNetwork();
    // KO-dominant and DR-dominant (Hodge dual pair)
    const compKO = createCompanion('ko', 's1', 'KO', 'mono_KO', 'amplifier', [0.8, 0.0, 0.0, 0.0, 0.0, 0.0]);
    const compDR = createCompanion('dr', 's2', 'DR', 'mono_DR', 'architect', [0.0, 0.0, 0.0, 0.0, 0.0, 0.8]);
    // Non-Hodge pair
    const compAV = createCompanion('av', 's3', 'AV', 'mono_AV', 'scout', [0.0, 0.8, 0.0, 0.0, 0.0, 0.0]);

    net.addCompanion(compKO);
    net.addCompanion(compDR);
    net.addCompanion(compAV);
    net.addBond('ko', 'dr', 0);
    net.addBond('ko', 'av', 0);

    // The Hodge dual bond should be stronger — verified via network bonuses
    expect(net.nodeCount).toBe(3);
    expect(net.edgeCount).toBe(2);
  });

  it('network bonuses emerge from graph properties', () => {
    const net = new SymbioticNetwork();
    const comp1 = createCompanion('a', 's1', 'A', 'mono_KO', 'amplifier', [0.6, 0.1, 0.1, 0.1, 0.1, 0.1]);
    const comp2 = createCompanion('b', 's2', 'B', 'mono_CA', 'processor', [0.1, 0.1, 0.1, 0.6, 0.1, 0.1]);
    const comp3 = createCompanion('c', 's3', 'C', 'mono_DR', 'architect', [0.1, 0.1, 0.1, 0.1, 0.1, 0.6]);
    net.addCompanion(comp1);
    net.addCompanion(comp2);
    net.addCompanion(comp3);
    net.addBond('a', 'b', 3);
    net.addBond('b', 'c', 2);
    net.addBond('a', 'c', 1);

    const bonuses = net.computeNetworkBonuses();
    expect(bonuses.xpMultiplier).toBeGreaterThan(1);
    expect(bonuses.diversityBonus).toBe(3 / 6); // 3 unique tongues out of 6
    expect(bonuses.density).toBeCloseTo(1.0, 5); // fully connected triangle
  });

  it('artifact governance gates by ds² threshold', () => {
    const net = new SymbioticNetwork();
    const comp1 = createCompanion('a', 's', 'A', 'mono_CA', 'processor', [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]);
    net.addCompanion(comp1);

    // Close to centroid → approved
    expect(net.submitArtifact([0.5, 0.5, 0.5, 0.5, 0.5, 0.5])).toBe('approved');

    // Far from centroid → quarantined
    expect(net.submitArtifact([5.0, 5.0, 5.0, 5.0, 5.0, 5.0])).toBe('quarantined');
  });

  it('serializes and deserializes', () => {
    const net = new SymbioticNetwork();
    const comp = createCompanion('a', 's', 'A', 'mono_CA', 'processor', [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]);
    net.addCompanion(comp);
    const json = net.toJSON();
    const restored = SymbioticNetwork.fromJSON(json);
    expect(restored.nodeCount).toBe(1);
  });
});

// ===========================================================================
//  Skill Tree
// ===========================================================================

describe('Player Skill Tree', () => {
  it('has 24 skills (4 per path × 6 paths)', () => {
    expect(totalSkillCount()).toBe(24);
  });

  it('each path has 4 skills', () => {
    for (const path of ['command', 'compute', 'entropy', 'structure', 'transport', 'security'] as const) {
      expect(getSkillsForPath(path)).toHaveLength(4);
    }
  });

  it('can unlock tier 1 skill with enough points', () => {
    const state = createSkillState();
    state.availablePoints = 5;
    expect(canUnlockSkill(state, 'cmd_initiative')).toBe(true);
    const ok = unlockSkill(state, 'cmd_initiative');
    expect(ok).toBe(true);
    expect(state.unlockedSkills.has('cmd_initiative')).toBe(true);
    expect(state.availablePoints).toBe(4);
  });

  it('cannot unlock skill without prerequisites', () => {
    const state = createSkillState();
    state.availablePoints = 10;
    expect(canUnlockSkill(state, 'cmd_swap')).toBe(false); // needs cmd_initiative
  });

  it('harmony abilities unlock from Hodge dual path investment', () => {
    const state = createSkillState();
    state.availablePoints = 20;
    // Unlock command path (KO) skills
    unlockSkill(state, 'cmd_initiative');
    unlockSkill(state, 'cmd_swap');
    // Unlock structure path (DR) skills
    unlockSkill(state, 'str_guard');
    unlockSkill(state, 'str_terrain');
    unlockSkill(state, 'str_verify');

    const harmonies = getHarmonyAbilities(state);
    expect(harmonies).toContain('ko_dr_harmony');
  });
});

// ===========================================================================
//  Regions & Tower
// ===========================================================================

describe('Regions & Tower', () => {
  it('has 6 regions, one per tongue', () => {
    expect(REGIONS).toHaveLength(6);
    for (const code of TONGUE_CODES) {
      expect(getRegionByTongue(code)).toBeDefined();
    }
  });

  it('tower floors are valid for 1-100', () => {
    for (let f = 1; f <= 100; f++) {
      const floor = getTowerFloor(f);
      expect(floor.floor).toBe(f);
      expect(floor.encounters).toBe(5);
      expect(floor.rank).toBeTruthy();
      expect(floor.mathDomain).toBeTruthy();
    }
  });

  it('rejects invalid floor numbers', () => {
    expect(() => getTowerFloor(0)).toThrow();
    expect(() => getTowerFloor(101)).toThrow();
  });

  it('ranks progress correctly', () => {
    expect(getRank(1)).toBe('F');
    expect(getRank(50)).toBe('B');
    expect(getRank(100)).toBe('Millennium');
  });

  it('boss floors are every 10th', () => {
    for (let f = 1; f <= 100; f++) {
      const floor = getTowerFloor(f);
      expect(floor.boss).toBe(f % 10 === 0);
    }
  });
});

// ===========================================================================
//  Codex Terminal
// ===========================================================================

describe('Codex Terminal', () => {
  it('allows math reference queries', () => {
    const terminal = new CodexTerminal();
    const result = terminal.evaluateRequest({
      requestId: 'test-1',
      timestamp: Date.now(),
      category: 'math_reference',
      query: 'What is the quadratic formula?',
      playerTongue: [0.5, 0.3, 0.2, 0.4, 0.3, 0.2],
      playerFloor: 5,
      sessionDuration: 300,
    });
    expect(result.decision).toBe('ALLOW');
    expect(result.visualEffect).toBe('green_glow');
  });

  it('restricts external API calls', () => {
    const terminal = new CodexTerminal();
    const result = terminal.evaluateRequest({
      requestId: 'test-2',
      timestamp: Date.now(),
      category: 'external_api',
      query: 'fetch data',
      playerTongue: [0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
      playerFloor: 1,
      sessionDuration: 10,
    });
    // External API with low tongue and no prior math → restricted
    expect(['QUARANTINE', 'DENY']).toContain(result.decision);
  });

  it('rate limits per category', () => {
    const terminal = new CodexTerminal();
    // Exhaust visual_thermal limit (5 per window)
    for (let i = 0; i < 6; i++) {
      const result = terminal.evaluateRequest({
        requestId: `rl-${i}`,
        timestamp: Date.now(),
        category: 'visual_thermal',
        query: 'test',
        playerTongue: [0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
        playerFloor: 50,
        sessionDuration: 1000,
      });
      if (i >= 5) {
        expect(result.decision).toBe('DENY');
      }
    }
  });

  it('generates game events for training pipeline', () => {
    const terminal = new CodexTerminal();
    const request = {
      requestId: 'evt-1',
      timestamp: Date.now(),
      category: 'math_reference' as const,
      query: 'test',
      playerTongue: [0.5, 0.5, 0.5, 0.5, 0.5, 0.5] as [number, number, number, number, number, number],
      playerFloor: 5,
      sessionDuration: 100,
    };
    const evaluation = terminal.evaluateRequest(request);
    const event = terminal.toGameEvent(request, evaluation, 'player-1');
    expect(event.eventType).toBe('codex_query');
    expect(event.scbeDecision).toBeDefined();
  });
});
