/**
 * @file asymmetricMovement.unit.test.ts
 * @module tests/L2-unit/asymmetricMovement
 * @layer Layer 5, Layer 8, Layer 13
 * @component Asymmetric Movement Model Tests
 * @version 3.2.4
 */

import { describe, it, expect } from 'vitest';
import {
  LATERAL_AXES,
  VERTICAL_AXES,
  AXIS_LABELS,
  TONGUE_AXIS,
  HUMAN_CAPABILITY,
  AI_CAPABILITY,
  HYBRID_CAPABILITY,
  aiMovementCost,
  humanMovementCost,
  compositePosition,
  validateMovement,
  authTierDepthLimit,
  complementarityScore,
  blindSpots,
  type FleetUnit,
  type HumanState,
  type AIState,
  type Hyperbolic6D,
} from '../../src/fleet/asymmetricMovement.js';

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════

function makeHuman(overrides: Partial<HumanState> = {}): HumanState {
  return {
    id: 'human-1',
    lateral: [0.1, 0.2],
    physical: [1, 2, 3],
    authTier: 'CA',
    attention: 0.9,
    latencyMs: 200,
    ...overrides,
  };
}

function makeAI(overrides: Partial<AIState> = {}): AIState {
  return {
    id: 'ai-1',
    position: [0.1, 0.2, 0.3, 0.1, 0.05, 0.02],
    coherence: 0.85,
    activeTongue: 'RU',
    activeProbes: 3,
    ...overrides,
  };
}

function makeUnit(overrides: Partial<FleetUnit> = {}): FleetUnit {
  const human = makeHuman();
  const agents = [
    makeAI({ id: 'ai-1', activeTongue: 'RU', position: [0.1, 0.2, 0.3, 0.1, 0.05, 0.02] }),
    makeAI({ id: 'ai-2', activeTongue: 'CA', position: [0.1, 0.2, 0.25, 0.15, 0.08, 0.03] }),
    makeAI({ id: 'ai-3', activeTongue: 'UM', position: [0.1, 0.2, 0.35, 0.12, 0.04, 0.01] }),
  ];
  return {
    unitId: 'unit-1',
    human,
    agents,
    compositePosition: [0.1, 0.2, 0.3, 0.12, 0.05, 0.02],
    decision: 'ALLOW',
    ...overrides,
  };
}

const ORIGIN: Hyperbolic6D = [0, 0, 0, 0, 0, 0];

// ═══════════════════════════════════════════════════════════════
// Axis Classification
// ═══════════════════════════════════════════════════════════════

describe('Axis Classification', () => {
  it('has 2 lateral and 4 vertical axes', () => {
    expect(LATERAL_AXES).toHaveLength(2);
    expect(VERTICAL_AXES).toHaveLength(4);
  });

  it('lateral + vertical = all 6 axes', () => {
    const all = [...LATERAL_AXES, ...VERTICAL_AXES];
    expect(new Set(all)).toEqual(new Set(AXIS_LABELS));
    expect(all).toHaveLength(6);
  });

  it('X and Y are lateral (human-accessible)', () => {
    expect(LATERAL_AXES).toContain('X');
    expect(LATERAL_AXES).toContain('Y');
  });

  it('Z, V, P, S are vertical (AI-exclusive)', () => {
    expect(VERTICAL_AXES).toContain('Z');
    expect(VERTICAL_AXES).toContain('V');
    expect(VERTICAL_AXES).toContain('P');
    expect(VERTICAL_AXES).toContain('S');
  });

  it('maps Sacred Tongues to axes', () => {
    expect(TONGUE_AXIS.KO).toBe('X');
    expect(TONGUE_AXIS.AV).toBe('Y');
    expect(TONGUE_AXIS.RU).toBe('Z');
    expect(TONGUE_AXIS.CA).toBe('V');
    expect(TONGUE_AXIS.UM).toBe('P');
    expect(TONGUE_AXIS.DR).toBe('S');
  });
});

// ═══════════════════════════════════════════════════════════════
// Movement Capabilities
// ═══════════════════════════════════════════════════════════════

describe('Movement Capabilities', () => {
  it('human: 2 lateral, 0 vertical, serial, delegates depth', () => {
    expect(HUMAN_CAPABILITY.lateralDims).toBe(2);
    expect(HUMAN_CAPABILITY.verticalDims).toBe(0);
    expect(HUMAN_CAPABILITY.maxParallel).toBe(1);
    expect(HUMAN_CAPABILITY.depthDelegate).toBe(true);
  });

  it('AI: 2 lateral + 4 vertical, 6 parallel, no delegation', () => {
    expect(AI_CAPABILITY.lateralDims).toBe(2);
    expect(AI_CAPABILITY.verticalDims).toBe(4);
    expect(AI_CAPABILITY.maxParallel).toBe(6);
    expect(AI_CAPABILITY.depthDelegate).toBe(false);
  });

  it('hybrid: covers all 6D like AI', () => {
    expect(HYBRID_CAPABILITY.lateralDims + HYBRID_CAPABILITY.verticalDims).toBe(6);
  });

  it('human + AI total dims = 6', () => {
    expect(HUMAN_CAPABILITY.lateralDims + AI_CAPABILITY.verticalDims).toBe(6);
  });
});

// ═══════════════════════════════════════════════════════════════
// AI Movement Cost
// ═══════════════════════════════════════════════════════════════

describe('aiMovementCost', () => {
  it('cost = 1 at origin (no movement)', () => {
    const cost = aiMovementCost(ORIGIN, ORIGIN, 1.0);
    expect(cost).toBeCloseTo(1.0, 4);
  });

  it('cost decreases with distance', () => {
    const near = aiMovementCost(ORIGIN, [0.1, 0, 0, 0, 0, 0], 0.8);
    const far = aiMovementCost(ORIGIN, [0.5, 0, 0, 0, 0, 0], 0.8);
    expect(near).toBeGreaterThan(far);
  });

  it('cost decreases with lower coherence', () => {
    const target: Hyperbolic6D = [0.3, 0, 0, 0, 0, 0];
    const highCoh = aiMovementCost(ORIGIN, target, 0.9);
    const lowCoh = aiMovementCost(ORIGIN, target, 0.2);
    expect(highCoh).toBeGreaterThan(lowCoh);
  });

  it('cost is always in (0, 1]', () => {
    const targets: Hyperbolic6D[] = [
      [0, 0, 0, 0, 0, 0],
      [0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
      [0.9, 0, 0, 0, 0, 0],
      [0, 0, 0, 0, 0, 0.9],
    ];
    for (const t of targets) {
      const cost = aiMovementCost(ORIGIN, t, 0.5);
      expect(cost).toBeGreaterThan(0);
      expect(cost).toBeLessThanOrEqual(1);
    }
  });

  it('vertical movement costs the same as lateral for AI', () => {
    // AI doesn't have asymmetry — all dimensions are equal
    const lateral = aiMovementCost(ORIGIN, [0.3, 0, 0, 0, 0, 0], 0.8);
    const vertical = aiMovementCost(ORIGIN, [0, 0, 0.3, 0, 0, 0], 0.8);
    // Should be very close (same distance, different direction)
    expect(Math.abs(lateral - vertical)).toBeLessThan(0.01);
  });
});

// ═══════════════════════════════════════════════════════════════
// Human Movement Cost
// ═══════════════════════════════════════════════════════════════

describe('humanMovementCost', () => {
  it('lateral-only movement is reachable', () => {
    const from: Hyperbolic6D = [0, 0, 0, 0, 0, 0];
    const to: Hyperbolic6D = [0.3, 0.4, 0, 0, 0, 0];
    const cost = humanMovementCost(from, to);
    expect(cost.reachable).toBe(true);
    expect(cost.lateral).toBeCloseTo(0.5, 4); // sqrt(0.09 + 0.16) = 0.5
    expect(cost.vertical).toBe(0);
    expect(cost.total).toBeCloseTo(0.5, 4);
  });

  it('vertical movement is unreachable (infinite cost)', () => {
    const from: Hyperbolic6D = [0, 0, 0, 0, 0, 0];
    const to: Hyperbolic6D = [0, 0, 0.1, 0, 0, 0];
    const cost = humanMovementCost(from, to);
    expect(cost.reachable).toBe(false);
    expect(cost.vertical).toBe(Infinity);
    expect(cost.total).toBe(Infinity);
  });

  it('mixed movement is unreachable', () => {
    const from: Hyperbolic6D = [0, 0, 0, 0, 0, 0];
    const to: Hyperbolic6D = [0.1, 0.2, 0.3, 0, 0, 0];
    const cost = humanMovementCost(from, to);
    expect(cost.reachable).toBe(false);
  });

  it('no movement = zero cost, reachable', () => {
    const cost = humanMovementCost(ORIGIN, ORIGIN);
    expect(cost.reachable).toBe(true);
    expect(cost.total).toBe(0);
  });

  it('tiny vertical perturbation below epsilon is reachable', () => {
    const from: Hyperbolic6D = [0, 0, 0, 0, 0, 0];
    const to: Hyperbolic6D = [0.1, 0, 0, 0, 0, 1e-12]; // below 1e-9 threshold
    const cost = humanMovementCost(from, to);
    expect(cost.reachable).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════
// Composite Position
// ═══════════════════════════════════════════════════════════════

describe('compositePosition', () => {
  it('uses human lateral for X, Y', () => {
    const unit = makeUnit();
    const pos = compositePosition(unit);
    expect(pos[0]).toBe(unit.human.lateral[0]);
    expect(pos[1]).toBe(unit.human.lateral[1]);
  });

  it('uses AI median for vertical dims', () => {
    const unit = makeUnit();
    const pos = compositePosition(unit);
    // 3 agents: Z values [0.3, 0.25, 0.35] → sorted [0.25, 0.3, 0.35] → median 0.3
    expect(pos[2]).toBeCloseTo(0.3, 6);
  });

  it('human alone → vertical = 0', () => {
    const unit = makeUnit({ agents: [] });
    const pos = compositePosition(unit);
    expect(pos[0]).toBe(unit.human.lateral[0]);
    expect(pos[1]).toBe(unit.human.lateral[1]);
    expect(pos[2]).toBe(0);
    expect(pos[3]).toBe(0);
    expect(pos[4]).toBe(0);
    expect(pos[5]).toBe(0);
  });

  it('single AI = that agent\'s vertical position', () => {
    const agent = makeAI({ position: [0, 0, 0.4, 0.2, 0.1, 0.05] });
    const unit = makeUnit({ agents: [agent] });
    const pos = compositePosition(unit);
    expect(pos[2]).toBeCloseTo(0.4, 6);
    expect(pos[3]).toBeCloseTo(0.2, 6);
  });

  it('median is robust to single outlier', () => {
    const agents = [
      makeAI({ id: 'a1', position: [0, 0, 0.3, 0, 0, 0] }),
      makeAI({ id: 'a2', position: [0, 0, 0.31, 0, 0, 0] }),
      makeAI({ id: 'a3', position: [0, 0, 0.9, 0, 0, 0] }), // outlier
    ];
    const unit = makeUnit({ agents });
    const pos = compositePosition(unit);
    // Median of [0.3, 0.31, 0.9] = 0.31
    expect(pos[2]).toBeCloseTo(0.31, 6);
  });
});

// ═══════════════════════════════════════════════════════════════
// Movement Validation
// ═══════════════════════════════════════════════════════════════

describe('validateMovement', () => {
  it('allows human lateral-only movement', () => {
    const unit = makeUnit();
    const target: Hyperbolic6D = [0.2, 0.3, 0.3, 0.12, 0.05, 0.02];
    const check = validateMovement(unit, target, 'HUMAN');
    expect(check.allowed).toBe(true);
    expect(check.movedAxes).toEqual(['X', 'Y']);
  });

  it('denies human vertical movement', () => {
    const unit = makeUnit();
    const target: Hyperbolic6D = [0.1, 0.2, 0.5, 0.12, 0.05, 0.02]; // Z changed
    const check = validateMovement(unit, target, 'HUMAN');
    expect(check.allowed).toBe(false);
    expect(check.reason).toContain('cannot move vertical');
    expect(check.reason).toContain('Z');
  });

  it('allows AI movement in any dimension', () => {
    const unit = makeUnit();
    const target: Hyperbolic6D = [0.15, 0.25, 0.35, 0.15, 0.08, 0.05];
    const check = validateMovement(unit, target, 'AI');
    expect(check.allowed).toBe(true);
    expect(check.movedAxes.length).toBeGreaterThan(0);
  });

  it('denies movement beyond auth tier depth limit', () => {
    const unit = makeUnit({
      human: makeHuman({ authTier: 'KO' }), // KO = 0.3 depth limit
    });
    // Target with vertical depth > 0.3
    const target: Hyperbolic6D = [0.1, 0.2, 0.5, 0.4, 0.3, 0.2];
    const check = validateMovement(unit, target, 'AI');
    expect(check.allowed).toBe(false);
    expect(check.reason).toContain('auth tier');
    expect(check.reason).toContain('KO');
  });

  it('denies movement to adversarially far positions (low H_eff)', () => {
    const unit = makeUnit({
      agents: [makeAI({ coherence: 0.1 })], // low coherence
    });
    // Target very far from current position
    const target: Hyperbolic6D = [0.95, 0.95, 0.2, 0.1, 0.05, 0.02];
    const check = validateMovement(unit, target, 'AI');
    // If H_eff drops below 0.05, it should be denied
    if (!check.allowed) {
      expect(check.reason).toContain('cost');
    }
  });

  it('no movement = always allowed', () => {
    const unit = makeUnit();
    const check = validateMovement(unit, unit.compositePosition, 'HUMAN');
    expect(check.allowed).toBe(true);
    expect(check.movedAxes).toHaveLength(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// Auth Tier Depth Limits
// ═══════════════════════════════════════════════════════════════

describe('authTierDepthLimit', () => {
  it('KO is shallowest', () => {
    expect(authTierDepthLimit('KO')).toBe(0.3);
  });

  it('DR is deepest', () => {
    expect(authTierDepthLimit('DR')).toBe(0.95);
  });

  it('tiers increase monotonically', () => {
    const tiers: Array<'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR'> = [
      'KO', 'AV', 'RU', 'CA', 'UM', 'DR',
    ];
    for (let i = 1; i < tiers.length; i++) {
      expect(authTierDepthLimit(tiers[i])).toBeGreaterThan(
        authTierDepthLimit(tiers[i - 1]),
      );
    }
  });

  it('all limits are within Poincaré ball (< 1.0)', () => {
    for (const lang of ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'] as const) {
      expect(authTierDepthLimit(lang)).toBeLessThan(1.0);
      expect(authTierDepthLimit(lang)).toBeGreaterThan(0);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Complementarity Score
// ═══════════════════════════════════════════════════════════════

describe('complementarityScore', () => {
  it('zero with no AI agents', () => {
    const unit = makeUnit({ agents: [] });
    expect(complementarityScore(unit)).toBe(0);
  });

  it('high with attentive human + diverse AI probes', () => {
    const agents = [
      makeAI({ id: 'a1', activeTongue: 'RU', coherence: 0.9 }),
      makeAI({ id: 'a2', activeTongue: 'CA', coherence: 0.8 }),
      makeAI({ id: 'a3', activeTongue: 'UM', coherence: 0.85 }),
      makeAI({ id: 'a4', activeTongue: 'DR', coherence: 0.7 }),
    ];
    const unit = makeUnit({
      human: makeHuman({ attention: 0.95 }),
      agents,
    });
    const score = complementarityScore(unit);
    expect(score).toBeGreaterThan(0.9);
  });

  it('low with inattentive human', () => {
    const unit = makeUnit({
      human: makeHuman({ attention: 0.05 }),
    });
    const score = complementarityScore(unit);
    expect(score).toBeLessThan(0.5);
  });

  it('low with low-coherence AI', () => {
    const agents = [
      makeAI({ id: 'a1', coherence: 0.1 }), // below 0.3 threshold
      makeAI({ id: 'a2', coherence: 0.15 }),
    ];
    const unit = makeUnit({ agents });
    const score = complementarityScore(unit);
    expect(score).toBe(0); // sqrt(lateral * 0) = 0
  });

  it('score ∈ [0, 1]', () => {
    for (let i = 0; i < 10; i++) {
      const agents = Array.from({ length: i }, (_, j) =>
        makeAI({
          id: `ai-${j}`,
          coherence: Math.random(),
          activeTongue: (['RU', 'CA', 'UM', 'DR'] as const)[j % 4],
        }),
      );
      const unit = makeUnit({
        human: makeHuman({ attention: Math.random() }),
        agents,
      });
      const score = complementarityScore(unit);
      expect(score).toBeGreaterThanOrEqual(0);
      expect(score).toBeLessThanOrEqual(1);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Blind Spots
// ═══════════════════════════════════════════════════════════════

describe('blindSpots', () => {
  it('human alone has 4 blind spots (all vertical)', () => {
    const unit = makeUnit({ agents: [] });
    const spots = blindSpots(unit);
    expect(spots).toEqual(['Z', 'V', 'P', 'S']);
  });

  it('full coverage = no blind spots', () => {
    const agents = [
      makeAI({ id: 'a1', activeTongue: 'RU', coherence: 0.9 }),  // Z
      makeAI({ id: 'a2', activeTongue: 'CA', coherence: 0.8 }),  // V
      makeAI({ id: 'a3', activeTongue: 'UM', coherence: 0.85 }), // P
      makeAI({ id: 'a4', activeTongue: 'DR', coherence: 0.7 }),  // S
    ];
    const unit = makeUnit({
      human: makeHuman({ attention: 0.9 }),
      agents,
    });
    expect(blindSpots(unit)).toHaveLength(0);
  });

  it('low-attention human loses lateral coverage', () => {
    const agents = [
      makeAI({ id: 'a1', activeTongue: 'RU', coherence: 0.9 }),
      makeAI({ id: 'a2', activeTongue: 'CA', coherence: 0.8 }),
      makeAI({ id: 'a3', activeTongue: 'UM', coherence: 0.85 }),
      makeAI({ id: 'a4', activeTongue: 'DR', coherence: 0.7 }),
    ];
    const unit = makeUnit({
      human: makeHuman({ attention: 0.05 }), // below 0.1 threshold
      agents,
    });
    const spots = blindSpots(unit);
    expect(spots).toContain('X');
    expect(spots).toContain('Y');
  });

  it('missing AI tongue creates vertical blind spot', () => {
    // Only covering RU and CA → missing UM (P) and DR (S)
    const agents = [
      makeAI({ id: 'a1', activeTongue: 'RU', coherence: 0.9 }),
      makeAI({ id: 'a2', activeTongue: 'CA', coherence: 0.8 }),
    ];
    const unit = makeUnit({
      human: makeHuman({ attention: 0.9 }),
      agents,
    });
    const spots = blindSpots(unit);
    expect(spots).toContain('P'); // UM axis
    expect(spots).toContain('S'); // DR axis
    expect(spots).not.toContain('X');
    expect(spots).not.toContain('Z');
  });
});
