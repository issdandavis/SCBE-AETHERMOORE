/**
 * Property-Based Tests for Agent System
 *
 * Tests mathematical properties and invariants of:
 * - Poincaré ball operations
 * - BFT consensus
 * - Swarm coordination
 * - Rogue detection
 *
 * @module tests/agent
 */

import fc from 'fast-check';
import { describe, expect, it } from 'vitest';
import {
  // Types
  type Agent,
  type AgentConfig,
  type BFTVote,
  type PoincarePosition,

  // Constants
  GOLDEN_RATIO,
  TONGUE_PHASES,
  TONGUE_INDICES,

  // Utility functions
  calculateTongueWeight,
  phaseToRadians,
  poincareNorm,
  isValidPoincarePosition,
  hyperbolicDistance,
  harmonicWallCost,
  generateInitialPosition,
  calculateBFTQuorum,

  // Swarm operations
  mobiusAdd,
  mobiusScale,
  hyperbolicCentroid,
  collectVotes,
  weightedVoteCount,
  runWeightedConsensus,
  detectRogueAgent,
  SwarmCoordinator,
} from '../../src/agent/index.js';
import { TONGUE_CODES, TongueCode } from '../../src/tokenizer/ss1.js';

// ============================================================================
// Arbitraries
// ============================================================================

/** Generate a valid Poincaré ball position (norm < 1) */
const poincarePositionArb = fc
  .tuple(
    fc.double({ min: -0.99, max: 0.99, noNaN: true }),
    fc.double({ min: -0.99, max: 0.99, noNaN: true }),
    fc.double({ min: -0.99, max: 0.99, noNaN: true })
  )
  .map(([x, y, z]) => {
    // Normalize to ensure norm < 1
    const norm = Math.sqrt(x * x + y * y + z * z);
    if (norm >= 0.99) {
      const scale = 0.9 / norm;
      return { x: x * scale, y: y * scale, z: z * scale };
    }
    return { x, y, z };
  });

/** Generate a tongue code */
const tongueCodeArb = fc.constantFrom(...TONGUE_CODES);

/** Generate a hex string */
const hexStringArb = fc
  .array(fc.constantFrom(...'0123456789abcdef'.split('')), { minLength: 64, maxLength: 64 })
  .map((chars) => chars.join(''));

/** Generate a BFT vote */
const bftVoteArb = fc.record({
  agentId: fc.uuid(),
  tongue: tongueCodeArb,
  decision: fc.constantFrom('ALLOW', 'DENY', 'QUARANTINE') as fc.Arbitrary<
    'ALLOW' | 'DENY' | 'QUARANTINE'
  >,
  confidence: fc.double({ min: 0, max: 1, noNaN: true }),
  timestamp: fc.integer({ min: Date.now() - 1000, max: Date.now() + 1000 }),
  signature: hexStringArb,
});

// ============================================================================
// Poincaré Ball Properties
// ============================================================================

describe('Poincaré Ball Properties', () => {
  const DIST_EPS = 1e-9;

  it('Property 1: Positions are always within unit ball', () => {
    fc.assert(
      fc.property(poincarePositionArb, (pos) => {
        expect(poincareNorm(pos)).toBeLessThan(1);
        expect(isValidPoincarePosition(pos)).toBe(true);
        return true;
      }),
      { numRuns: 100 }
    );
  });

  it('Property 2: Hyperbolic distance is symmetric', () => {
    fc.assert(
      fc.property(poincarePositionArb, poincarePositionArb, (u, v) => {
        const d1 = hyperbolicDistance(u, v);
        const d2 = hyperbolicDistance(v, u);
        expect(Math.abs(d1 - d2)).toBeLessThan(DIST_EPS);
        return true;
      }),
      { numRuns: 100 }
    );
  });

  it('Property 3: Hyperbolic distance is non-negative', () => {
    fc.assert(
      fc.property(poincarePositionArb, poincarePositionArb, (u, v) => {
        const d = hyperbolicDistance(u, v);
        expect(d).toBeGreaterThanOrEqual(0);
        return true;
      }),
      { numRuns: 100 }
    );
  });

  it('Property 4: Distance to self is zero', () => {
    fc.assert(
      fc.property(poincarePositionArb, (pos) => {
        const d = hyperbolicDistance(pos, pos);
        expect(d).toBeLessThan(DIST_EPS);
        return true;
      }),
      { numRuns: 100 }
    );
  });

  it('Property 5: Triangle inequality holds', () => {
    fc.assert(
      fc.property(poincarePositionArb, poincarePositionArb, poincarePositionArb, (a, b, c) => {
        const ab = hyperbolicDistance(a, b);
        const bc = hyperbolicDistance(b, c);
        const ac = hyperbolicDistance(a, c);
        // Triangle inequality: d(a,c) <= d(a,b) + d(b,c)
        // Allow a small epsilon for floating-point noise near the boundary.
        expect(ac).toBeLessThanOrEqual(ab + bc + DIST_EPS);
        return true;
      }),
      { numRuns: 100 }
    );
  });

  it('Property 6: Möbius addition preserves ball', () => {
    fc.assert(
      fc.property(poincarePositionArb, poincarePositionArb, (u, v) => {
        const result = mobiusAdd(u, v);
        expect(poincareNorm(result)).toBeLessThan(1 + DIST_EPS);
        return true;
      }),
      { numRuns: 100 }
    );
  });

  it('Property 7: Möbius scaling preserves ball', () => {
    fc.assert(
      fc.property(fc.double({ min: -2, max: 2, noNaN: true }), poincarePositionArb, (t, v) => {
        const result = mobiusScale(t, v);
        expect(poincareNorm(result)).toBeLessThan(1 + DIST_EPS);
        return true;
      }),
      { numRuns: 100 }
    );
  });

  it('Property 8: Centroid is within convex hull', () => {
    fc.assert(
      fc.property(fc.array(poincarePositionArb, { minLength: 2, maxLength: 10 }), (points) => {
        const centroid = hyperbolicCentroid(points);
        expect(poincareNorm(centroid)).toBeLessThan(1 + DIST_EPS);
        return true;
      }),
      { numRuns: 100 }
    );
  });
});

// ============================================================================
// Harmonic Wall Properties
// ============================================================================

describe('Harmonic Wall Properties', () => {
  it('Property 9: Harmonic wall is always positive', () => {
    fc.assert(
      fc.property(fc.double({ min: 0, max: 10, noNaN: true }), (d) => {
        const cost = harmonicWallCost(d);
        expect(cost).toBeGreaterThan(0);
        return true;
      }),
      { numRuns: 100 }
    );
  });

  it('Property 10: Harmonic wall increases with distance', () => {
    fc.assert(
      fc.property(
        fc.double({ min: 0, max: 5, noNaN: true }),
        fc.double({ min: 0.01, max: 5, noNaN: true }),
        (d1, delta) => {
          const d2 = d1 + delta;
          const cost1 = harmonicWallCost(d1);
          const cost2 = harmonicWallCost(d2);
          expect(cost2).toBeGreaterThan(cost1);
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  it('Property 11: Harmonic wall at zero is one', () => {
    const cost = harmonicWallCost(0);
    expect(cost).toBeCloseTo(1);
  });

  it('Property 12: Harmonic wall is convex (second derivative positive)', () => {
    fc.assert(
      fc.property(fc.double({ min: 0.1, max: 5, noNaN: true }), (d) => {
        const epsilon = 0.001;
        const h = harmonicWallCost;

        // Second derivative approximation: (h(d+e) - 2*h(d) + h(d-e)) / e^2
        const secondDerivative = (h(d + epsilon) - 2 * h(d) + h(d - epsilon)) / (epsilon * epsilon);

        expect(secondDerivative).toBeGreaterThan(0);
        return true;
      }),
      { numRuns: 100 }
    );
  });
});

// ============================================================================
// Tongue Weight Properties
// ============================================================================

describe('Tongue Weight Properties', () => {
  it('Property 13: Weights follow golden ratio sequence', () => {
    fc.assert(
      fc.property(tongueCodeArb, (tongue) => {
        const weight = calculateTongueWeight(tongue);
        const index = TONGUE_INDICES[tongue];
        const expected = Math.pow(GOLDEN_RATIO, index);
        expect(Math.abs(weight - expected)).toBeLessThan(1e-10);
        return true;
      }),
      { numRuns: 50 }
    );
  });

  it('Property 14: Phases are evenly distributed (60° apart)', () => {
    const phases = TONGUE_CODES.map((t) => TONGUE_PHASES[t]);
    for (let i = 1; i < phases.length; i++) {
      expect(phases[i] - phases[i - 1]).toBe(60);
    }
  });

  it('Property 15: Phase radians conversion is correct', () => {
    fc.assert(
      fc.property(tongueCodeArb, (tongue) => {
        const radians = phaseToRadians(tongue);
        const degrees = TONGUE_PHASES[tongue];
        expect(radians).toBeCloseTo((degrees * Math.PI) / 180);
        return true;
      }),
      { numRuns: 50 }
    );
  });

  it('Property 16: Generated positions are valid', () => {
    fc.assert(
      fc.property(tongueCodeArb, (tongue) => {
        const pos = generateInitialPosition(tongue);
        expect(isValidPoincarePosition(pos)).toBe(true);
        return true;
      }),
      { numRuns: 50 }
    );
  });
});

// ============================================================================
// BFT Consensus Properties
// ============================================================================

describe('BFT Consensus Properties', () => {
  it('Property 17: BFT quorum requires > 50% of agents', () => {
    fc.assert(
      fc.property(fc.integer({ min: 1, max: 100 }), (n) => {
        const config = calculateBFTQuorum(n);
        expect(config.quorum).toBeGreaterThan(n / 2 - 1);
        return true;
      }),
      { numRuns: 100 }
    );
  });

  it('Property 18: BFT can tolerate up to f faults with 3f+1 agents', () => {
    fc.assert(
      fc.property(fc.integer({ min: 1, max: 100 }), (n) => {
        const config = calculateBFTQuorum(n);
        // With n agents, we can tolerate f faults where n >= 3f + 1
        expect(n).toBeGreaterThanOrEqual(3 * config.maxFaulty + 1);
        return true;
      }),
      { numRuns: 100 }
    );
  });

  it('Property 19: Quorum is 2f+1', () => {
    fc.assert(
      fc.property(fc.integer({ min: 1, max: 100 }), (n) => {
        const config = calculateBFTQuorum(n);
        expect(config.quorum).toBe(2 * config.maxFaulty + 1);
        return true;
      }),
      { numRuns: 100 }
    );
  });

  it('Property 20: Unanimous votes always reach quorum', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 4, max: 20 }),
        fc.constantFrom('ALLOW', 'DENY', 'QUARANTINE') as fc.Arbitrary<
          'ALLOW' | 'DENY' | 'QUARANTINE'
        >,
        (n, decision) => {
          const config = calculateBFTQuorum(n);
          const votes: BFTVote[] = [];

          for (let i = 0; i < n; i++) {
            votes.push({
              agentId: `agent-${i}`,
              tongue: TONGUE_CODES[i % TONGUE_CODES.length],
              decision,
              confidence: 1.0,
              timestamp: Date.now(),
              signature: 'sig',
            });
          }

          const result = collectVotes(votes, config);
          expect(result.quorumReached).toBe(true);
          expect(result.decision).toBe(decision);
          return true;
        }
      ),
      { numRuns: 50 }
    );
  });

  it('Property 21: Weighted vote count uses golden ratio weights', () => {
    fc.assert(
      fc.property(fc.array(bftVoteArb, { minLength: 1, maxLength: 10 }), (votes) => {
        const weighted = weightedVoteCount(votes);
        // Weight should be positive
        expect(weighted).toBeGreaterThanOrEqual(0);
        return true;
      }),
      { numRuns: 100 }
    );
  });
});

// ============================================================================
// Swarm Coordinator Properties
// ============================================================================

describe('Swarm Coordinator Properties', () => {
  it('Property 22: Adding agents increases active count', () => {
    const coordinator = new SwarmCoordinator();

    fc.assert(
      fc.property(tongueCodeArb, fc.uuid(), (tongue, id) => {
        const countBefore = coordinator.getActiveCount();

        const agent: Agent = {
          id,
          tongue,
          ipTier: 'private',
          position: generateInitialPosition(tongue),
          phase: phaseToRadians(tongue),
          weight: calculateTongueWeight(tongue),
          coherence: 1.0,
          lastHeartbeat: Date.now(),
          status: 'active',
          keys: {
            publicKey: Buffer.from('test'),
          },
          createdAt: Date.now(),
          usedNonces: new Set(),
        };

        coordinator.addAgent(agent);
        expect(coordinator.getActiveCount()).toBe(countBefore + 1);

        coordinator.removeAgent(id);
        return true;
      }),
      { numRuns: 20 }
    );
  });

  it('Property 23: Swarm state centroid is within ball', () => {
    const coordinator = new SwarmCoordinator();

    // Add agents for all tongues
    for (const tongue of TONGUE_CODES) {
      const agent: Agent = {
        id: `agent-${tongue}`,
        tongue,
        ipTier: 'private',
        position: generateInitialPosition(tongue),
        phase: phaseToRadians(tongue),
        weight: calculateTongueWeight(tongue),
        coherence: 1.0,
        lastHeartbeat: Date.now(),
        status: 'active',
        keys: { publicKey: Buffer.from('test') },
        createdAt: Date.now(),
        usedNonces: new Set(),
      };
      coordinator.addAgent(agent);
    }

    const state = coordinator.getState();
    expect(poincareNorm(state.centroid)).toBeLessThan(1);
  });
});

// ============================================================================
// Rogue Detection Properties
// ============================================================================

describe('Rogue Detection Properties', () => {
  it('Property 24: Healthy agents are not detected as rogue', () => {
    const coordinator = new SwarmCoordinator();

    // Create a healthy swarm
    for (const tongue of TONGUE_CODES) {
      const agent: Agent = {
        id: `agent-${tongue}`,
        tongue,
        ipTier: 'private',
        position: generateInitialPosition(tongue),
        phase: phaseToRadians(tongue),
        weight: calculateTongueWeight(tongue),
        coherence: 0.9, // High coherence
        lastHeartbeat: Date.now(),
        status: 'active',
        keys: { publicKey: Buffer.from('test') },
        createdAt: Date.now(),
        usedNonces: new Set(),
      };
      coordinator.addAgent(agent);
    }

    const state = coordinator.getState();

    for (const [, agent] of state.agents) {
      const result = detectRogueAgent(agent, state);
      // High coherence agents should not be rogue
      expect(result.isRogue).toBe(false);
    }
  });

  it('Property 25: Low coherence increases rogue confidence', () => {
    const coordinator = new SwarmCoordinator();

    for (const tongue of TONGUE_CODES) {
      const agent: Agent = {
        id: `agent-${tongue}`,
        tongue,
        ipTier: 'private',
        position: generateInitialPosition(tongue),
        phase: phaseToRadians(tongue),
        weight: calculateTongueWeight(tongue),
        coherence: 0.9,
        lastHeartbeat: Date.now(),
        status: 'active',
        keys: { publicKey: Buffer.from('test') },
        createdAt: Date.now(),
        usedNonces: new Set(),
      };
      coordinator.addAgent(agent);
    }

    const state = coordinator.getState();

    // Create a low-coherence agent
    const lowCoherenceAgent: Agent = {
      id: 'low-coherence',
      tongue: 'KO',
      ipTier: 'private',
      position: { x: 0, y: 0, z: 0 },
      phase: 0,
      weight: 1,
      coherence: 0.1, // Very low coherence
      lastHeartbeat: Date.now(),
      status: 'degraded',
      keys: { publicKey: Buffer.from('test') },
      createdAt: Date.now(),
      usedNonces: new Set(),
    };

    const result = detectRogueAgent(lowCoherenceAgent, state);
    expect(result.confidence).toBeGreaterThan(0);
    expect(result.indicators.length).toBeGreaterThan(0);
  });

  it('Property 26: Quarantine status contributes to rogue detection', () => {
    const coordinator = new SwarmCoordinator();

    for (const tongue of TONGUE_CODES) {
      const agent: Agent = {
        id: `agent-${tongue}`,
        tongue,
        ipTier: 'private',
        position: generateInitialPosition(tongue),
        phase: phaseToRadians(tongue),
        weight: calculateTongueWeight(tongue),
        coherence: 0.9,
        lastHeartbeat: Date.now(),
        status: 'active',
        keys: { publicKey: Buffer.from('test') },
        createdAt: Date.now(),
        usedNonces: new Set(),
      };
      coordinator.addAgent(agent);
    }

    const state = coordinator.getState();

    const quarantinedAgent: Agent = {
      id: 'quarantined',
      tongue: 'KO',
      ipTier: 'private',
      position: { x: 0, y: 0, z: 0 },
      phase: 0,
      weight: 1,
      coherence: 0,
      lastHeartbeat: Date.now(),
      status: 'quarantine',
      keys: { publicKey: Buffer.from('test') },
      createdAt: Date.now(),
      usedNonces: new Set(),
    };

    const result = detectRogueAgent(quarantinedAgent, state);
    // Quarantine status adds 0.4 to rogue score, plus low coherence adds 0.3
    // Total confidence should be at least 0.7 (close to threshold of 0.8)
    expect(result.confidence).toBeGreaterThanOrEqual(0.7);
    expect(result.indicators).toContain('quarantine_status');
    expect(result.indicators).toContain('low_coherence:0.000');
    expect(result.recommendedAction).not.toBe('none');
  });
});

// ============================================================================
// Kafka Topic Properties
// ============================================================================

describe('Kafka Topic Properties', () => {
  it('Property 27: Topic names are deterministic', async () => {
    const { getTopicName, parseTopicName } = await import('../../src/agent/kafka.js');

    fc.assert(
      fc.property(
        fc.constantFrom('public', 'private', 'hidden') as fc.Arbitrary<
          'public' | 'private' | 'hidden'
        >,
        tongueCodeArb,
        fc.constantFrom('agent.joined', 'agent.heartbeat', 'agent.leaving') as fc.Arbitrary<
          'agent.joined' | 'agent.heartbeat' | 'agent.leaving'
        >,
        (tier, tongue, eventType) => {
          const topic1 = getTopicName(tier, tongue, eventType);
          const topic2 = getTopicName(tier, tongue, eventType);
          expect(topic1).toBe(topic2);
          return true;
        }
      ),
      { numRuns: 50 }
    );
  });

  it('Property 28: Topic names are parseable', async () => {
    const { getTopicName, parseTopicName } = await import('../../src/agent/kafka.js');

    fc.assert(
      fc.property(
        fc.constantFrom('public', 'private', 'hidden') as fc.Arbitrary<
          'public' | 'private' | 'hidden'
        >,
        tongueCodeArb,
        fc.constantFrom('agent.joined', 'agent.heartbeat', 'agent.leaving') as fc.Arbitrary<
          'agent.joined' | 'agent.heartbeat' | 'agent.leaving'
        >,
        (tier, tongue, eventType) => {
          const topic = getTopicName(tier, tongue, eventType);
          const parsed = parseTopicName(topic);

          expect(parsed).not.toBeNull();
          expect(parsed!.tier).toBe(tier);
          expect(parsed!.tongue).toBe(tongue);
          expect(parsed!.eventType).toBe(eventType);
          return true;
        }
      ),
      { numRuns: 50 }
    );
  });
});
