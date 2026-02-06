/**
 * @file geoSealImmune.test.ts
 * @description Tests for GeoSeal Immune System
 */

import { describe, it, expect } from 'vitest';
import {
  TONGUE_PHASES,
  phaseDeviation,
  computeRepelForce,
  updateSuspicion,
  swarmStep,
  runSwarmDynamics,
  createTongueAgents,
  createCandidateAgent,
  filterByTrust,
  getAttentionWeights,
  computeSwarmMetrics,
  geoSealFilter,
  SwarmAgent,
} from '../../src/harmonic/geoSealImmune';

describe('GeoSeal Immune System', () => {
  describe('TONGUE_PHASES', () => {
    it('should have 6 sacred tongues', () => {
      expect(Object.keys(TONGUE_PHASES)).toHaveLength(6);
    });

    it('should have evenly spaced phases', () => {
      const phases = Object.values(TONGUE_PHASES);
      const spacing = Math.PI / 3; // 60 degrees

      for (let i = 0; i < phases.length; i++) {
        expect(phases[i]).toBeCloseTo(i * spacing, 5);
      }
    });
  });

  describe('phaseDeviation', () => {
    it('should return 0 for same phase', () => {
      expect(phaseDeviation(0, 0)).toBe(0);
      expect(phaseDeviation(Math.PI, Math.PI)).toBe(0);
    });

    it('should return 1 for opposite phases', () => {
      expect(phaseDeviation(0, Math.PI)).toBe(1);
    });

    it('should return 1 for null phase (rogue)', () => {
      expect(phaseDeviation(null, 0)).toBe(1);
      expect(phaseDeviation(0, null)).toBe(1);
      expect(phaseDeviation(null, null)).toBe(1);
    });

    it('should wrap around correctly', () => {
      // 350 degrees and 10 degrees should be close
      const phase1 = (350 / 180) * Math.PI;
      const phase2 = (10 / 180) * Math.PI;
      expect(phaseDeviation(phase1, phase2)).toBeLessThan(0.2);
    });
  });

  describe('createTongueAgents', () => {
    it('should create 6 tongue agents', () => {
      const agents = createTongueAgents(8);
      expect(agents).toHaveLength(6);
    });

    it('should give each tongue full trust', () => {
      const agents = createTongueAgents(8);
      for (const agent of agents) {
        expect(agent.trustScore).toBe(1.0);
        expect(agent.isQuarantined).toBe(false);
        expect(agent.phase).not.toBeNull();
      }
    });

    it('should place agents inside Poincaré ball', () => {
      const agents = createTongueAgents(8);
      for (const agent of agents) {
        const norm = Math.sqrt(
          agent.position.reduce((sum, x) => sum + x * x, 0)
        );
        expect(norm).toBeLessThan(1.0);
      }
    });
  });

  describe('createCandidateAgent', () => {
    it('should create agent with assigned tongue phase', () => {
      const agent = createCandidateAgent(
        'test-001',
        [0.1, 0.2, 0, 0, 0, 0, 0, 0],
        'KO'
      );
      expect(agent.phase).toBe(TONGUE_PHASES.KO);
      expect(agent.tongue).toBe('KO');
    });

    it('should create rogue agent with null phase', () => {
      const agent = createCandidateAgent(
        'rogue-001',
        [0.1, 0.2, 0, 0, 0, 0, 0, 0]
      );
      expect(agent.phase).toBeNull();
      expect(agent.tongue).toBeUndefined();
    });

    it('should project to ball if embedding too large', () => {
      const agent = createCandidateAgent(
        'test-002',
        [1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5]
      );
      const norm = Math.sqrt(
        agent.position.reduce((sum, x) => sum + x * x, 0)
      );
      expect(norm).toBeLessThan(1.0);
    });
  });

  describe('computeRepelForce', () => {
    it('should flag rogue agents as anomalous', () => {
      const legitimate = createCandidateAgent(
        'legit',
        [0.1, 0.1, 0, 0, 0, 0, 0, 0],
        'KO'
      );
      const rogue = createCandidateAgent(
        'rogue',
        [0.2, 0.1, 0, 0, 0, 0, 0, 0]
      );

      const result = computeRepelForce(legitimate, rogue);
      expect(result.anomalyFlag).toBe(true);
      expect(result.amplification).toBe(2.0);
    });

    it('should not flag matching phases as anomalous', () => {
      const agent1 = createCandidateAgent(
        'agent1',
        [0.1, 0.1, 0, 0, 0, 0, 0, 0],
        'KO'
      );
      const agent2 = createCandidateAgent(
        'agent2',
        [0.15, 0.05, 0, 0, 0, 0, 0, 0],
        'KO'
      );

      const result = computeRepelForce(agent1, agent2);
      expect(result.anomalyFlag).toBe(false);
      expect(result.amplification).toBe(1.0);
    });

    it('should amplify force for quarantined agents', () => {
      const agent1 = createCandidateAgent(
        'agent1',
        [0.1, 0.1, 0, 0, 0, 0, 0, 0],
        'KO'
      );
      const quarantined: SwarmAgent = {
        ...createCandidateAgent('quarantined', [0.2, 0.1, 0, 0, 0, 0, 0, 0]),
        isQuarantined: true,
      };

      const result = computeRepelForce(agent1, quarantined);
      expect(result.amplification).toBeGreaterThan(1.0);
    });
  });

  describe('updateSuspicion', () => {
    it('should increment suspicion on anomaly', () => {
      const agent = createCandidateAgent(
        'test',
        [0.1, 0.1, 0, 0, 0, 0, 0, 0]
      );

      updateSuspicion(agent, 'neighbor-1', true);
      expect(agent.suspicionCount.get('neighbor-1')).toBe(1);

      updateSuspicion(agent, 'neighbor-1', true);
      expect(agent.suspicionCount.get('neighbor-1')).toBe(2);
    });

    it('should decay suspicion when no anomaly', () => {
      const agent = createCandidateAgent(
        'test',
        [0.1, 0.1, 0, 0, 0, 0, 0, 0]
      );

      // Build up suspicion
      for (let i = 0; i < 5; i++) {
        updateSuspicion(agent, 'neighbor-1', true);
      }
      expect(agent.suspicionCount.get('neighbor-1')).toBe(5);

      // Decay
      updateSuspicion(agent, 'neighbor-1', false);
      expect(agent.suspicionCount.get('neighbor-1')).toBe(4.5);
    });

    it('should quarantine when consensus reached', () => {
      const agent = createCandidateAgent(
        'test',
        [0.1, 0.1, 0, 0, 0, 0, 0, 0]
      );

      // 3 neighbors with suspicion >= 3 each
      for (let n = 1; n <= 3; n++) {
        for (let i = 0; i < 3; i++) {
          updateSuspicion(agent, `neighbor-${n}`, true);
        }
      }

      expect(agent.isQuarantined).toBe(true);
    });

    it('should reduce trust with accumulated suspicion', () => {
      const agent = createCandidateAgent(
        'test',
        [0.1, 0.1, 0, 0, 0, 0, 0, 0],
        'KO',
        1.0
      );

      // Accumulate suspicion
      for (let i = 0; i < 10; i++) {
        updateSuspicion(agent, 'neighbor-1', true);
      }

      expect(agent.trustScore).toBeLessThan(1.0);
    });
  });

  describe('swarmStep and runSwarmDynamics', () => {
    it('should move agents based on forces', () => {
      const agents = createTongueAgents(8);
      const initial = agents[0].position.slice();

      swarmStep(agents, 0.1);

      // Position should change due to repulsion from other tongues
      const moved = agents[0].position.some((v, i) => v !== initial[i]);
      expect(moved).toBe(true);
    });

    it('should keep agents inside Poincaré ball', () => {
      const agents = createTongueAgents(8);

      // Run many steps with high drift
      runSwarmDynamics(agents, 50, 0.1);

      for (const agent of agents) {
        const norm = Math.sqrt(
          agent.position.reduce((sum, x) => sum + x * x, 0)
        );
        expect(norm).toBeLessThan(1.0);
      }
    });

    it('should detect and penalize rogue agents', () => {
      const tongues = createTongueAgents(8);
      const rogue = createCandidateAgent(
        'rogue-001',
        [0.2, 0.1, 0, 0, 0, 0, 0, 0],
        undefined, // No tongue = rogue
        0.5
      );

      let agents = [...tongues, rogue];
      agents = runSwarmDynamics(agents, 15, 0.02);

      const rogueAfter = agents.find((a) => a.id === 'rogue-001')!;
      expect(rogueAfter.trustScore).toBeLessThan(1.0);
    });

    it('should preserve trust for legitimate agents', () => {
      const tongues = createTongueAgents(8);
      const legit = createCandidateAgent(
        'legit-001',
        [0.25, 0, 0, 0, 0, 0, 0, 0],
        'KO', // Has KO tongue phase
        0.5
      );

      let agents = [...tongues, legit];
      agents = runSwarmDynamics(agents, 15, 0.02);

      const legitAfter = agents.find((a) => a.id === 'legit-001')!;
      // Legitimate agent should have higher trust than a rogue would
      expect(legitAfter.trustScore).toBeGreaterThan(0.3);
    });
  });

  describe('filterByTrust', () => {
    it('should filter out low-trust agents', () => {
      const agents: SwarmAgent[] = [
        { ...createCandidateAgent('low', [0.1, 0.1, 0, 0, 0, 0, 0, 0]), trustScore: 0.1 },
        { ...createCandidateAgent('high', [0.2, 0.2, 0, 0, 0, 0, 0, 0]), trustScore: 0.8 },
      ];

      const filtered = filterByTrust(agents, 0.3);
      expect(filtered).toHaveLength(1);
      expect(filtered[0].id).toBe('high');
    });

    it('should always include tongue agents', () => {
      const tongues = createTongueAgents(8);
      tongues[0].trustScore = 0.1; // Artificially low

      const filtered = filterByTrust(tongues, 0.5);
      expect(filtered).toHaveLength(6); // All tongues kept
    });
  });

  describe('getAttentionWeights', () => {
    it('should return weights for non-tongue agents only', () => {
      const tongues = createTongueAgents(8);
      const candidate = createCandidateAgent('test', [0.1, 0.1, 0, 0, 0, 0, 0, 0]);

      const weights = getAttentionWeights([...tongues, candidate]);

      expect(weights.size).toBe(1);
      expect(weights.has('test')).toBe(true);
      expect(weights.has('tongue-KO')).toBe(false);
    });
  });

  describe('computeSwarmMetrics', () => {
    it('should compute correct metrics', () => {
      const agents: SwarmAgent[] = [
        {
          ...createCandidateAgent('quarantined', [0.95, 0, 0, 0, 0, 0, 0, 0]),
          isQuarantined: true,
          trustScore: 0.0,
        },
        {
          ...createCandidateAgent('healthy', [0.1, 0.1, 0, 0, 0, 0, 0, 0]),
          isQuarantined: false,
          trustScore: 0.8,
        },
      ];

      const metrics = computeSwarmMetrics(agents);

      expect(metrics.quarantineCount).toBe(1);
      expect(metrics.avgTrustScore).toBe(0.4); // (0 + 0.8) / 2
      expect(metrics.boundaryAgents).toBe(1); // norm 0.95 > 0.9
    });

    it('should return defaults for tongue-only swarm', () => {
      const tongues = createTongueAgents(8);
      const metrics = computeSwarmMetrics(tongues);

      expect(metrics.quarantineCount).toBe(0);
      expect(metrics.avgTrustScore).toBe(1.0);
    });
  });

  describe('geoSealFilter', () => {
    it('should return attention weights for candidates', () => {
      const candidates = [
        { id: 'doc-1', embedding: [0.1, 0.2, 0, 0, 0, 0, 0, 0], tongue: 'KO' },
        { id: 'doc-2', embedding: [0.3, 0.1, 0, 0, 0, 0, 0, 0] }, // No tongue
      ];

      const weights = geoSealFilter(candidates, 10, 8);

      expect(weights.size).toBe(2);
      expect(weights.has('doc-1')).toBe(true);
      expect(weights.has('doc-2')).toBe(true);
    });

    it('should give higher weight to tongue-aligned candidates', () => {
      const candidates = [
        { id: 'aligned', embedding: [0.1, 0, 0, 0, 0, 0, 0, 0], tongue: 'KO' },
        { id: 'rogue', embedding: [0.1, 0, 0, 0, 0, 0, 0, 0] }, // Same position, no tongue
      ];

      const weights = geoSealFilter(candidates, 15, 8);

      const alignedWeight = weights.get('aligned')!;
      const rogueWeight = weights.get('rogue')!;

      expect(alignedWeight).toBeGreaterThan(rogueWeight);
    });
  });
});
