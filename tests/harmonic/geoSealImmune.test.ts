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
  phaseDistanceScore,
  phaseDistanceFilter,
  sphericalNodalPosition,
  oscillatingTongueAgents,
  temporalPhaseScore,
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

  // ═══════════════════════════════════════════════════════════════
  // PROVEN: Phase + Distance Scoring Tests (0.9999 AUC)
  // ═══════════════════════════════════════════════════════════════

  describe('phaseDistanceScore (PROVEN 0.9999 AUC)', () => {
    it('should give high scores to tongue-aligned agents', () => {
      const tongues = createTongueAgents(8);
      const aligned = createCandidateAgent(
        'aligned',
        [0.25, 0.05, 0, 0, 0, 0, 0, 0], // Near KO tongue position
        'KO'
      );

      const score = phaseDistanceScore(aligned, tongues);
      expect(score).toBeGreaterThan(0.5);
    });

    it('should give low scores to rogue agents (null phase)', () => {
      const tongues = createTongueAgents(8);
      const rogue = createCandidateAgent(
        'rogue',
        [0.25, 0.05, 0, 0, 0, 0, 0, 0] // Same position, no tongue
      );

      const score = phaseDistanceScore(rogue, tongues);
      expect(score).toBeLessThan(0.4);
    });

    it('should discriminate between aligned and rogue at same position', () => {
      const tongues = createTongueAgents(8);
      const position = [0.2, 0.1, 0, 0, 0, 0, 0, 0];

      const aligned = createCandidateAgent('aligned', position, 'KO');
      const rogue = createCandidateAgent('rogue', position); // No tongue

      const alignedScore = phaseDistanceScore(aligned, tongues);
      const rogueScore = phaseDistanceScore(rogue, tongues);

      // Key test: phase deviation should cause significant score difference
      expect(alignedScore).toBeGreaterThan(rogueScore * 1.5);
    });

    it('should give higher scores to agents closer to center', () => {
      const tongues = createTongueAgents(8);

      const nearCenter = createCandidateAgent(
        'near',
        [0.1, 0, 0, 0, 0, 0, 0, 0],
        'KO'
      );
      const nearBoundary = createCandidateAgent(
        'far',
        [0.9, 0, 0, 0, 0, 0, 0, 0],
        'KO'
      );

      const nearScore = phaseDistanceScore(nearCenter, tongues);
      const farScore = phaseDistanceScore(nearBoundary, tongues);

      expect(nearScore).toBeGreaterThan(farScore);
    });

    it('should penalize wrong phase assignment', () => {
      const tongues = createTongueAgents(8);

      // Agent at KO position but claiming CA phase (opposite)
      const wrongPhase = createCandidateAgent(
        'wrong',
        [0.3, 0, 0, 0, 0, 0, 0, 0], // Near KO
        'CA' // But claims CA (180° opposite)
      );

      const rightPhase = createCandidateAgent(
        'right',
        [0.3, 0, 0, 0, 0, 0, 0, 0],
        'KO' // Correct phase
      );

      const wrongScore = phaseDistanceScore(wrongPhase, tongues);
      const rightScore = phaseDistanceScore(rightPhase, tongues);

      expect(rightScore).toBeGreaterThan(wrongScore);
    });
  });

  describe('phaseDistanceFilter', () => {
    it('should batch score multiple candidates', () => {
      const candidates = [
        { id: 'legit-1', embedding: [0.1, 0, 0, 0, 0, 0, 0, 0], tongue: 'KO' },
        { id: 'legit-2', embedding: [-0.1, 0.1, 0, 0, 0, 0, 0, 0], tongue: 'AV' },
        { id: 'rogue-1', embedding: [0.1, 0.1, 0, 0, 0, 0, 0, 0] }, // No tongue
      ];

      const scores = phaseDistanceFilter(candidates, 8);

      expect(scores.size).toBe(3);
      expect(scores.get('legit-1')!).toBeGreaterThan(scores.get('rogue-1')!);
    });

    it('should achieve high separation between legitimate and rogue', () => {
      // Simulate the experiment that proved 0.9999 AUC
      const legitimate = [
        { id: 'l1', embedding: [0.2, 0.05, 0, 0, 0, 0, 0, 0], tongue: 'KO' },
        { id: 'l2', embedding: [0.1, 0.2, 0, 0, 0, 0, 0, 0], tongue: 'AV' },
        { id: 'l3', embedding: [-0.1, 0.2, 0, 0, 0, 0, 0, 0], tongue: 'RU' },
      ];
      const rogues = [
        { id: 'r1', embedding: [0.2, 0.05, 0, 0, 0, 0, 0, 0] }, // Same positions
        { id: 'r2', embedding: [0.1, 0.2, 0, 0, 0, 0, 0, 0] },  // but no tongue
        { id: 'r3', embedding: [-0.1, 0.2, 0, 0, 0, 0, 0, 0] },
      ];

      const allCandidates = [...legitimate, ...rogues];
      const scores = phaseDistanceFilter(allCandidates, 8);

      // All legitimate should score higher than all rogues
      const legitScores = legitimate.map((c) => scores.get(c.id)!);
      const rogueScores = rogues.map((c) => scores.get(c.id)!);

      const minLegit = Math.min(...legitScores);
      const maxRogue = Math.max(...rogueScores);

      // Perfect separation: min legitimate > max rogue
      expect(minLegit).toBeGreaterThan(maxRogue);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Spherical Nodal Oscillation (6-Tonic System)
  // ═══════════════════════════════════════════════════════════════

  describe('sphericalNodalPosition', () => {
    it('should generate position in Poincaré ball', () => {
      const position = sphericalNodalPosition(0, 0, 1.0, 8);
      const norm = Math.sqrt(position.reduce((sum, x) => sum + x * x, 0));
      expect(norm).toBeLessThan(1.0);
    });

    it('should change position with time (oscillation)', () => {
      // Use time values where sin() differs: sin(0) = 0, sin(π/2) = 1
      const pos0 = sphericalNodalPosition(0, 0, 1.0, 8);
      const pos1 = sphericalNodalPosition(0, Math.PI / 2, 1.0, 8);

      // Position should differ due to oscillation
      const diff = pos0.some((v, i) => Math.abs(v - pos1[i]) > 0.01);
      expect(diff).toBe(true);
    });

    it('should use higher dimensions for harmonics', () => {
      const position = sphericalNodalPosition(Math.PI / 2, 1.0, 1.0, 8);

      // Dimensions 2-7 should have non-zero values from harmonics
      const hasHigherDims = position.slice(2, 8).some((v) => Math.abs(v) > 1e-6);
      expect(hasHigherDims).toBe(true);
    });
  });

  describe('oscillatingTongueAgents', () => {
    it('should create 6 tongues at each time step', () => {
      const agents0 = oscillatingTongueAgents(0, 8);
      const agents1 = oscillatingTongueAgents(1, 8);

      expect(agents0).toHaveLength(6);
      expect(agents1).toHaveLength(6);
    });

    it('should have tongues move slightly over time', () => {
      const agents0 = oscillatingTongueAgents(0, 8);
      const agents1 = oscillatingTongueAgents(Math.PI, 8);

      // Same tongue should be at slightly different positions
      const ko0 = agents0.find((a) => a.tongue === 'KO')!;
      const ko1 = agents1.find((a) => a.tongue === 'KO')!;

      const moved = ko0.position.some(
        (v, i) => Math.abs(v - ko1.position[i]) > 0.01
      );
      expect(moved).toBe(true);
    });

    it('should maintain phase assignments', () => {
      const agents = oscillatingTongueAgents(2.5, 8);

      for (const agent of agents) {
        expect(agent.phase).toBe(TONGUE_PHASES[agent.tongue!]);
        expect(agent.trustScore).toBe(1.0);
      }
    });
  });

  describe('temporalPhaseScore', () => {
    it('should give consistent scores to aligned agents', () => {
      const aligned = createCandidateAgent(
        'aligned',
        [0.25, 0.05, 0, 0, 0, 0, 0, 0],
        'KO'
      );

      const score = temporalPhaseScore(aligned, 5, 8);
      expect(score).toBeGreaterThan(0.4);
    });

    it('should penalize rogue agents across time steps', () => {
      const aligned = createCandidateAgent(
        'aligned',
        [0.2, 0.1, 0, 0, 0, 0, 0, 0],
        'KO'
      );
      const rogue = createCandidateAgent(
        'rogue',
        [0.2, 0.1, 0, 0, 0, 0, 0, 0]
      );

      const alignedScore = temporalPhaseScore(aligned, 5, 8);
      const rogueScore = temporalPhaseScore(rogue, 5, 8);

      expect(alignedScore).toBeGreaterThan(rogueScore);
    });

    it('should detect agents that drift (wrong phase)', () => {
      // Agent at KO position claiming opposite phase
      const wrongPhase = createCandidateAgent(
        'wrong',
        [0.3, 0, 0, 0, 0, 0, 0, 0],
        'CA' // Opposite of KO
      );
      const rightPhase = createCandidateAgent(
        'right',
        [0.3, 0, 0, 0, 0, 0, 0, 0],
        'KO'
      );

      const wrongScore = temporalPhaseScore(wrongPhase, 5, 8);
      const rightScore = temporalPhaseScore(rightPhase, 5, 8);

      expect(rightScore).toBeGreaterThan(wrongScore);
    });
  });
});
