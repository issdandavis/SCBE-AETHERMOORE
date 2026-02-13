/**
 * @file swarm-formation.test.ts
 * @module ai_brain/swarm-formation.test
 * @layer Layer 10, Layer 13
 * Tests for the Swarm Formation Coordination module.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  SwarmFormationManager,
  DEFAULT_SWARM_CONFIG,
  type FormationType,
  type SwarmFormation,
  type FormationPosition,
  type SwarmConfig,
} from '../../src/ai_brain/swarm-formation.js';
import { BRAIN_DIMENSIONS } from '../../src/ai_brain/types.js';

// ═══════════════════════════════════════════════════════════════
// Test Helpers
// ═══════════════════════════════════════════════════════════════

function make21D(overrides: Partial<Record<number, number>> = {}): number[] {
  const v = new Array(BRAIN_DIMENSIONS).fill(0);
  for (const [k, val] of Object.entries(overrides)) {
    v[Number(k)] = val;
  }
  return v;
}

function makeAgent(id: string, trust: number = 0.8) {
  return {
    agentId: id,
    currentPosition: make21D({ 6: Math.random() * 0.1, 7: Math.random() * 0.1 }),
    trustScore: trust,
  };
}

function makeAgents(count: number, trust: number = 0.8) {
  return Array.from({ length: count }, (_, i) => makeAgent(`agent-${i}`, trust));
}

// ═══════════════════════════════════════════════════════════════
// Config Defaults
// ═══════════════════════════════════════════════════════════════

describe('DEFAULT_SWARM_CONFIG', () => {
  it('has reasonable default radius', () => {
    expect(DEFAULT_SWARM_CONFIG.defaultRadius).toBeGreaterThan(0);
    expect(DEFAULT_SWARM_CONFIG.defaultRadius).toBeLessThan(1);
  });

  it('requires minimum 3 agents', () => {
    expect(DEFAULT_SWARM_CONFIG.minAgents).toBe(3);
  });

  it('has positive coherence decay', () => {
    expect(DEFAULT_SWARM_CONFIG.coherenceDecay).toBeGreaterThan(0);
  });

  it('has trust exponent ≥ 1', () => {
    expect(DEFAULT_SWARM_CONFIG.trustExponent).toBeGreaterThanOrEqual(1);
  });
});

// ═══════════════════════════════════════════════════════════════
// Defensive Circle
// ═══════════════════════════════════════════════════════════════

describe('createDefensiveCircle', () => {
  let mgr: SwarmFormationManager;

  beforeEach(() => {
    mgr = new SwarmFormationManager();
  });

  it('creates a formation with correct type', () => {
    const agents = makeAgents(5);
    const center = make21D();
    const f = mgr.createDefensiveCircle(agents, center);
    expect(f.type).toBe('defensive_circle');
  });

  it('assigns all agents positions', () => {
    const agents = makeAgents(4);
    const f = mgr.createDefensiveCircle(agents, make21D());
    expect(f.positions.length).toBe(4);
    for (const pos of f.positions) {
      expect(pos.targetPosition.length).toBeGreaterThanOrEqual(2);
    }
  });

  it('first agent is leader, rest are wing', () => {
    const agents = makeAgents(3);
    const f = mgr.createDefensiveCircle(agents, make21D());
    expect(f.positions[0].role).toBe('leader');
    expect(f.positions[1].role).toBe('wing');
    expect(f.positions[2].role).toBe('wing');
  });

  it('positions are equally spaced angularly', () => {
    const agents = makeAgents(4);
    const center = make21D();
    const f = mgr.createDefensiveCircle(agents, center, 0.5);

    // Check that positionIndex values are evenly spaced
    for (let i = 0; i < 4; i++) {
      expect(f.positions[i].positionIndex).toBeCloseTo(i / 4);
    }
  });

  it('uses configured default radius', () => {
    const f = mgr.createDefensiveCircle(makeAgents(3), make21D());
    expect(f.radius).toBe(DEFAULT_SWARM_CONFIG.defaultRadius);
  });

  it('accepts custom radius', () => {
    const f = mgr.createDefensiveCircle(makeAgents(3), make21D(), 0.7);
    expect(f.radius).toBe(0.7);
  });

  it('trust weight uses configured exponent', () => {
    const mgr2 = new SwarmFormationManager({ trustExponent: 3 });
    const agents = [makeAgent('a', 0.5)];
    const f = mgr2.createDefensiveCircle(agents, make21D());
    expect(f.positions[0].trustWeight).toBeCloseTo(0.5 ** 3);
  });

  it('registers formation and increments count', () => {
    expect(mgr.formationCount).toBe(0);
    mgr.createDefensiveCircle(makeAgents(3), make21D());
    expect(mgr.formationCount).toBe(1);
    mgr.createDefensiveCircle(makeAgents(3), make21D());
    expect(mgr.formationCount).toBe(2);
  });
});

// ═══════════════════════════════════════════════════════════════
// Investigation Wedge
// ═══════════════════════════════════════════════════════════════

describe('createInvestigationWedge', () => {
  let mgr: SwarmFormationManager;

  beforeEach(() => {
    mgr = new SwarmFormationManager();
  });

  it('creates a formation with correct type', () => {
    const agents = makeAgents(5);
    const origin = make21D();
    const target = make21D({ 6: 1.0, 7: 0.5 });
    const f = mgr.createInvestigationWedge(agents, target, origin);
    expect(f.type).toBe('investigation_wedge');
  });

  it('sorts agents by trust (highest first at tip)', () => {
    const agents = [
      makeAgent('low', 0.2),
      makeAgent('high', 0.9),
      makeAgent('mid', 0.5),
    ];
    const f = mgr.createInvestigationWedge(agents, make21D({ 6: 1 }), make21D());
    // Leader should be the highest trust agent
    expect(f.positions[0].role).toBe('leader');
    expect(f.positions[0].agentId).toBe('high');
  });

  it('leader and first wings get correct roles', () => {
    const agents = makeAgents(6);
    const f = mgr.createInvestigationWedge(agents, make21D({ 6: 1 }), make21D());
    expect(f.positions[0].role).toBe('leader');
    expect(f.positions[1].role).toBe('wing');
    expect(f.positions[2].role).toBe('wing');
    expect(f.positions[3].role).toBe('support');
  });

  it('center is midpoint between origin and target', () => {
    const origin = make21D({ 0: 0 });
    const target = make21D({ 0: 2 });
    const f = mgr.createInvestigationWedge(makeAgents(3), target, origin);
    expect(f.center[0]).toBeCloseTo(1.0);
  });
});

// ═══════════════════════════════════════════════════════════════
// Consensus Ring
// ═══════════════════════════════════════════════════════════════

describe('createConsensusRing', () => {
  let mgr: SwarmFormationManager;

  beforeEach(() => {
    mgr = new SwarmFormationManager();
  });

  it('creates a formation with correct type', () => {
    const f = mgr.createConsensusRing(makeAgents(5), make21D());
    expect(f.type).toBe('consensus_ring');
  });

  it('uses tighter radius than defensive circle', () => {
    const f = mgr.createConsensusRing(makeAgents(3), make21D());
    expect(f.radius).toBe(DEFAULT_SWARM_CONFIG.defaultRadius * 0.5);
  });

  it('all agents get wing role', () => {
    const f = mgr.createConsensusRing(makeAgents(4), make21D());
    for (const pos of f.positions) {
      expect(pos.role).toBe('wing');
    }
  });

  it('positions vary with trust-weighted angles', () => {
    const agents = [
      makeAgent('high', 0.9),
      makeAgent('low', 0.1),
    ];
    const f = mgr.createConsensusRing(agents, make21D());
    // Higher-trust agent gets more arc space
    // Both should have target positions but they should differ
    expect(f.positions[0].targetPosition).not.toEqual(f.positions[1].targetPosition);
  });
});

// ═══════════════════════════════════════════════════════════════
// Formation Health
// ═══════════════════════════════════════════════════════════════

describe('computeHealth', () => {
  let mgr: SwarmFormationManager;

  beforeEach(() => {
    mgr = new SwarmFormationManager();
  });

  it('returns 0 for unknown formation', () => {
    expect(mgr.computeHealth('nonexistent')).toBe(0);
  });

  it('returns 1.0 when agents are exactly at target positions', () => {
    const agents = makeAgents(3);
    const f = mgr.createDefensiveCircle(agents, make21D());
    // Move agents to their targets
    for (const pos of f.positions) {
      pos.currentPosition = [...pos.targetPosition];
    }
    expect(mgr.computeHealth(f.id)).toBeCloseTo(1.0);
  });

  it('returns < 1 when agents drift from targets', () => {
    const agents = makeAgents(3);
    const f = mgr.createDefensiveCircle(agents, make21D());
    // Agents stay at initial positions (not at targets)
    const health = mgr.computeHealth(f.id);
    expect(health).toBeLessThan(1.0);
  });

  it('health is trust-weighted', () => {
    const agents = [
      { agentId: 'trusted', currentPosition: make21D(), trustScore: 0.9 },
      { agentId: 'untrusted', currentPosition: make21D(), trustScore: 0.1 },
    ];
    const f = mgr.createDefensiveCircle(agents, make21D());
    // Move trusted to target, leave untrusted far
    f.positions[0].currentPosition = [...f.positions[0].targetPosition];
    const health = mgr.computeHealth(f.id);
    // Health should be high because the trusted agent dominates
    expect(health).toBeGreaterThan(0.5);
  });
});

// ═══════════════════════════════════════════════════════════════
// Formation Coherence
// ═══════════════════════════════════════════════════════════════

describe('computeCoherence', () => {
  let mgr: SwarmFormationManager;

  beforeEach(() => {
    mgr = new SwarmFormationManager();
  });

  it('returns 1.0 for unknown formation', () => {
    // Coherence of nonexistent formation
    // Actually the code returns 1 for < 2 positions
    expect(mgr.computeCoherence('nonexistent')).toBe(1);
  });

  it('returns 1.0 when agents preserve relative distances', () => {
    const agents = makeAgents(3);
    const f = mgr.createDefensiveCircle(agents, make21D());
    // Set current positions = target positions (perfect preservation)
    for (const pos of f.positions) {
      pos.currentPosition = [...pos.targetPosition];
    }
    const coherence = mgr.computeCoherence(f.id);
    expect(coherence).toBeCloseTo(1.0);
  });

  it('returns < 1 when distances are distorted', () => {
    const agents = makeAgents(4);
    const f = mgr.createDefensiveCircle(agents, make21D(), 0.5);
    // Leave agents at their initial positions (not targets)
    const coherence = mgr.computeCoherence(f.id);
    expect(coherence).toBeLessThan(1.0);
  });

  it('returns 1.0 for single-agent formation', () => {
    const agents = makeAgents(1);
    const f = mgr.createDefensiveCircle(agents, make21D());
    expect(mgr.computeCoherence(f.id)).toBe(1);
  });
});

// ═══════════════════════════════════════════════════════════════
// Position Updates
// ═══════════════════════════════════════════════════════════════

describe('updatePositions', () => {
  it('updates agent current positions', () => {
    const mgr = new SwarmFormationManager();
    const agents = makeAgents(2);
    const f = mgr.createDefensiveCircle(agents, make21D());

    const newPositions = new Map<string, number[]>();
    const newPos = make21D({ 0: 0.5, 1: 0.5 });
    newPositions.set('agent-0', newPos);

    mgr.updatePositions(f.id, newPositions);

    const updated = mgr.getFormation(f.id)!;
    expect(updated.positions[0].currentPosition[0]).toBeCloseTo(0.5);
    expect(updated.positions[0].currentPosition[1]).toBeCloseTo(0.5);
  });

  it('does nothing for unknown formation', () => {
    const mgr = new SwarmFormationManager();
    // Should not throw
    mgr.updatePositions('nonexistent', new Map());
  });
});

// ═══════════════════════════════════════════════════════════════
// Weighted Vote
// ═══════════════════════════════════════════════════════════════

describe('computeWeightedVote', () => {
  it('returns zeros for unknown formation', () => {
    const mgr = new SwarmFormationManager();
    const vote = mgr.computeWeightedVote('nonexistent');
    expect(vote.allow).toBe(0);
    expect(vote.deny).toBe(0);
    expect(vote.total).toBe(0);
  });

  it('trusted agents vote allow', () => {
    const mgr = new SwarmFormationManager();
    const agents = makeAgents(3, 0.8);
    const f = mgr.createDefensiveCircle(agents, make21D());
    // Move agents to target so they have proximity influence
    for (const pos of f.positions) {
      pos.currentPosition = [...pos.targetPosition];
    }
    const vote = mgr.computeWeightedVote(f.id);
    expect(vote.allow).toBeGreaterThan(0);
    expect(vote.total).toBeGreaterThan(0);
  });

  it('untrusted agents vote deny', () => {
    const mgr = new SwarmFormationManager();
    const agents = makeAgents(3, 0.1);
    const f = mgr.createDefensiveCircle(agents, make21D());
    for (const pos of f.positions) {
      pos.currentPosition = [...pos.targetPosition];
    }
    const vote = mgr.computeWeightedVote(f.id);
    expect(vote.deny).toBeGreaterThan(0);
  });

  it('total equals allow + deny', () => {
    const mgr = new SwarmFormationManager();
    const agents = [makeAgent('a', 0.8), makeAgent('b', 0.2)];
    const f = mgr.createDefensiveCircle(agents, make21D());
    for (const pos of f.positions) {
      pos.currentPosition = [...pos.targetPosition];
    }
    const vote = mgr.computeWeightedVote(f.id);
    expect(vote.total).toBeCloseTo(vote.allow + vote.deny);
  });
});

// ═══════════════════════════════════════════════════════════════
// Formation Lifecycle
// ═══════════════════════════════════════════════════════════════

describe('Formation lifecycle', () => {
  let mgr: SwarmFormationManager;

  beforeEach(() => {
    mgr = new SwarmFormationManager();
  });

  it('getFormation returns undefined for unknown id', () => {
    expect(mgr.getFormation('nonexistent')).toBeUndefined();
  });

  it('getFormation returns created formation', () => {
    const f = mgr.createDefensiveCircle(makeAgents(3), make21D());
    const retrieved = mgr.getFormation(f.id);
    expect(retrieved).toBeDefined();
    expect(retrieved!.id).toBe(f.id);
  });

  it('getAllFormations returns all active formations', () => {
    mgr.createDefensiveCircle(makeAgents(3), make21D());
    mgr.createConsensusRing(makeAgents(4), make21D());
    expect(mgr.getAllFormations().length).toBe(2);
  });

  it('dissolveFormation removes formation', () => {
    const f = mgr.createDefensiveCircle(makeAgents(3), make21D());
    expect(mgr.formationCount).toBe(1);
    const result = mgr.dissolveFormation(f.id);
    expect(result).toBe(true);
    expect(mgr.formationCount).toBe(0);
    expect(mgr.getFormation(f.id)).toBeUndefined();
  });

  it('dissolveFormation returns false for unknown id', () => {
    expect(mgr.dissolveFormation('nonexistent')).toBe(false);
  });

  it('formation IDs are unique', () => {
    const f1 = mgr.createDefensiveCircle(makeAgents(3), make21D());
    const f2 = mgr.createConsensusRing(makeAgents(3), make21D());
    expect(f1.id).not.toBe(f2.id);
  });
});

// ═══════════════════════════════════════════════════════════════
// Custom Configuration
// ═══════════════════════════════════════════════════════════════

describe('Custom configuration', () => {
  it('applies custom trust exponent', () => {
    const mgr = new SwarmFormationManager({ trustExponent: 1 });
    const agents = [makeAgent('a', 0.7)];
    const f = mgr.createDefensiveCircle(agents, make21D());
    expect(f.positions[0].trustWeight).toBeCloseTo(0.7);
  });

  it('applies custom default radius', () => {
    const mgr = new SwarmFormationManager({ defaultRadius: 0.5 });
    const f = mgr.createDefensiveCircle(makeAgents(3), make21D());
    expect(f.radius).toBe(0.5);
  });
});
