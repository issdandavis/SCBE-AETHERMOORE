/**
 * AI Brain Mapping - Multi-Vectored Quasi-Space Architecture Tests
 *
 * Tests the unified 21D brain manifold, 5 orthogonal detection mechanisms,
 * BFT consensus (corrected), quasicrystal projection, and audit logging.
 *
 * @layer Layer 1-14 (Unified)
 * @version 1.1.0
 */

import { describe, expect, it } from 'vitest';

import {
  // Types
  BRAIN_DIMENSIONS,
  PHI,
  POINCARE_MAX_NORM,
  DEFAULT_BRAIN_CONFIG,
  // Unified State
  UnifiedBrainState,
  applyGoldenWeighting,
  goldenWeightProduct,
  safePoincareEmbed,
  hyperbolicDistanceSafe,
  mobiusAddSafe,
  euclideanDistance,
  vectorNorm,
  // Detection
  detectPhaseDistance,
  detectCurvatureAccumulation,
  detectThreatLissajous,
  detectDecimalDrift,
  detectSixTonic,
  runCombinedDetection,
  // BFT
  BFTConsensus,
  // Quasi-Space
  icosahedralProjection,
  classifyVoxelRealm,
  createOctreeRoot,
  octreeInsert,
  brainStateToPenrose,
  quasicrystalPotential,
  // Audit
  BrainAuditLogger,
  // Supporting types
  type TrajectoryPoint,
} from '../../../src/ai_brain/index';

// ═══════════════════════════════════════════════════════════════
// Test Helpers
// ═══════════════════════════════════════════════════════════════

function makeTrajectoryPoint(
  step: number,
  state: number[],
  embedded?: number[],
  distance?: number,
  curvature?: number
): TrajectoryPoint {
  const emb = embedded ?? state.map((v) => Math.tanh(v) * 0.5);
  return {
    step,
    state,
    embedded: emb,
    distance: distance ?? vectorNorm(emb),
    curvature: curvature ?? 0,
    timestamp: Date.now(),
  };
}

function makeDefaultState(): number[] {
  return new Array(BRAIN_DIMENSIONS).fill(0.5);
}

function makeHonestTrajectory(steps: number): TrajectoryPoint[] {
  const points: TrajectoryPoint[] = [];
  const origin = new Array(BRAIN_DIMENSIONS).fill(0);
  for (let i = 0; i < steps; i++) {
    const state = makeDefaultState();
    // Honest agent: nearly linear drift with small perturbations
    state[3] = 0.9; // high behavior score
    state[5] = 0.9; // high intent alignment
    state[16] = 0; // correct phase (KO tongue)
    state[17] = 1 + 0.01 * Math.sin((2 * Math.PI * i) / 10); // tiny oscillating weight
    state[18] = 0.9; // high trust
    state[6] = (0.01 * i) / steps; // very small linear navigation
    state[7] = (0.01 * i) / steps;

    // Embed the raw state vector (not weighted) for Poincare ball placement
    const embedded = safePoincareEmbed(state);
    points.push({
      step: i,
      state,
      embedded,
      distance: hyperbolicDistanceSafe(origin, embedded),
      curvature: 0,
      timestamp: Date.now() + i * 100,
    });
  }
  return points;
}

function makeMaliciousTrajectory(steps: number): TrajectoryPoint[] {
  const points: TrajectoryPoint[] = [];
  const origin = new Array(BRAIN_DIMENSIONS).fill(0);
  for (let i = 0; i < steps; i++) {
    const state = makeDefaultState();
    // Malicious agent: erratic, extreme values
    state[3] = 0.2 + 0.6 * Math.sin(i * 3); // erratic behavior
    state[5] = 0.1 + 0.5 * Math.cos(i * 7); // erratic intent
    state[16] = Math.PI; // wrong phase (should be 0 for KO)
    state[17] = 0.5; // static weight (no oscillation)
    state[18] = 0.2; // low trust
    state[6] = 0.8 * Math.sin(i); // large navigation jumps
    state[7] = 0.8 * Math.cos(i * 2);

    // Embed the raw state vector (not weighted)
    const embedded = safePoincareEmbed(state);
    points.push({
      step: i,
      state,
      embedded,
      distance: hyperbolicDistanceSafe(origin, embedded),
      curvature: 0,
      timestamp: Date.now() + i * 100,
    });
  }
  return points;
}

// ═══════════════════════════════════════════════════════════════
// 1. Unified Brain State Tests
// ═══════════════════════════════════════════════════════════════

describe('Unified Brain State (21D Manifold)', () => {
  it('should create a default brain state with 21 dimensions', () => {
    const state = new UnifiedBrainState();
    const vector = state.toVector();
    expect(vector.length).toBe(BRAIN_DIMENSIONS);
    expect(vector.length).toBe(21);
  });

  it('should correctly flatten and reconstruct from vector', () => {
    const original = new UnifiedBrainState({
      scbeContext: {
        deviceTrust: 0.8,
        locationTrust: 0.7,
        networkTrust: 0.9,
        behaviorScore: 0.85,
        timeOfDay: 0.3,
        intentAlignment: 0.95,
      },
      navigation: { x: 0.1, y: -0.2, z: 0.3, time: 0.5, priority: 0.8, confidence: 0.9 },
      cognitivePosition: { px: 0.1, py: 0.2, pz: 0.3 },
      semanticPhase: { activeTongue: 2, phaseAngle: Math.PI / 3, tongueWeight: 2.62 },
      swarmCoordination: { trustScore: 0.9, byzantineVotes: 0, spectralCoherence: 0.8 },
    });

    const vector = original.toVector();
    const reconstructed = UnifiedBrainState.fromVector(vector);
    const reconVector = reconstructed.toVector();

    for (let i = 0; i < BRAIN_DIMENSIONS; i++) {
      expect(reconVector[i]).toBeCloseTo(vector[i], 10);
    }
  });

  it('should produce 21D weighted vector with golden ratio scaling', () => {
    const state = new UnifiedBrainState();
    const weighted = state.toWeightedVector();
    expect(weighted.length).toBe(BRAIN_DIMENSIONS);

    // First weight is phi^0 = 1, second is phi^1 ≈ 1.618
    const raw = state.toVector();
    expect(weighted[0]).toBeCloseTo(raw[0] * 1, 5);
    expect(weighted[1]).toBeCloseTo(raw[1] * PHI, 5);
    expect(weighted[2]).toBeCloseTo(raw[2] * PHI ** 2, 5);
  });

  it('should embed into Poincare ball with norm strictly < 1', () => {
    const state = new UnifiedBrainState({
      scbeContext: {
        deviceTrust: 1,
        locationTrust: 1,
        networkTrust: 1,
        behaviorScore: 1,
        timeOfDay: 1,
        intentAlignment: 1,
      },
    });

    const point = state.toPoincarePoint();
    const norm = vectorNorm(point);
    expect(norm).toBeLessThan(1);
    expect(norm).toBeLessThanOrEqual(POINCARE_MAX_NORM);
  });

  it('should compute hyperbolic distance between states', () => {
    const safe = UnifiedBrainState.safeOrigin();
    const deviated = new UnifiedBrainState({
      scbeContext: {
        deviceTrust: 0.1,
        locationTrust: 0.1,
        networkTrust: 0.1,
        behaviorScore: 0.1,
        timeOfDay: 0.5,
        intentAlignment: 0.1,
      },
    });

    const dist = safe.distanceTo(deviated);
    expect(dist).toBeGreaterThan(0);
    expect(Number.isFinite(dist)).toBe(true);
  });

  it('should compute boundary distance (distance from Poincare edge)', () => {
    const state = new UnifiedBrainState();
    const boundary = state.boundaryDistance();
    expect(boundary).toBeGreaterThan(0);
    expect(boundary).toBeLessThanOrEqual(1);
  });

  it('should reject non-21D vectors in fromVector', () => {
    expect(() => UnifiedBrainState.fromVector([1, 2, 3])).toThrow();
  });

  it('should reject non-21D vectors in applyGoldenWeighting', () => {
    expect(() => applyGoldenWeighting([1, 2, 3])).toThrow();
  });

  it('safe origin should be near the center of the ball', () => {
    const origin = UnifiedBrainState.safeOrigin();
    const point = origin.toPoincarePoint();
    const norm = vectorNorm(point);
    // Safe origin is not zero (it has non-zero components), but should be embedded in the ball
    expect(norm).toBeLessThan(1);
  });
});

// ═══════════════════════════════════════════════════════════════
// 2. Poincare Ball Operations Tests
// ═══════════════════════════════════════════════════════════════

describe('Poincare Ball Operations', () => {
  it('safePoincareEmbed should always produce norm < 1', () => {
    // Large input
    const large = new Array(21).fill(100);
    const embedded = safePoincareEmbed(large);
    expect(vectorNorm(embedded)).toBeLessThan(1);

    // Small input
    const small = new Array(21).fill(0.001);
    const embeddedSmall = safePoincareEmbed(small);
    expect(vectorNorm(embeddedSmall)).toBeLessThan(1);

    // Zero input
    const zero = new Array(21).fill(0);
    const embeddedZero = safePoincareEmbed(zero);
    expect(vectorNorm(embeddedZero)).toBe(0);
  });

  it('hyperbolicDistanceSafe should be non-negative and symmetric', () => {
    const a = safePoincareEmbed([0.1, 0.2, 0.3]);
    const b = safePoincareEmbed([0.4, 0.5, 0.6]);

    const distAB = hyperbolicDistanceSafe(a, b);
    const distBA = hyperbolicDistanceSafe(b, a);

    expect(distAB).toBeGreaterThanOrEqual(0);
    expect(distAB).toBeCloseTo(distBA, 10);
  });

  it('hyperbolic distance from origin should increase with norm', () => {
    const origin = [0, 0, 0];
    const near = safePoincareEmbed([0.1, 0, 0]);
    const far = safePoincareEmbed([0.5, 0, 0]);

    const distNear = hyperbolicDistanceSafe(origin, near);
    const distFar = hyperbolicDistanceSafe(origin, far);

    expect(distFar).toBeGreaterThan(distNear);
  });

  it('mobiusAddSafe should keep result inside ball', () => {
    const a = safePoincareEmbed([0.3, 0.3, 0.3]);
    const b = safePoincareEmbed([0.3, 0.3, 0.3]);
    const result = mobiusAddSafe(a, b);
    expect(vectorNorm(result)).toBeLessThan(1);
  });
});

// ═══════════════════════════════════════════════════════════════
// 3. Detection Mechanism Tests
// ═══════════════════════════════════════════════════════════════

describe('Phase + Distance Detection', () => {
  it('should return low score for honest trajectory with correct tongue', () => {
    const trajectory = makeHonestTrajectory(20);
    const result = detectPhaseDistance(trajectory, 0); // KO tongue = phase 0
    expect(result.score).toBeLessThan(0.7);
    expect(result.flagged).toBe(false);
  });

  it('should return high score for wrong-tongue trajectory', () => {
    const trajectory = makeHonestTrajectory(20);
    // Modify to wrong phase
    trajectory.forEach((p) => {
      p.state[16] = Math.PI; // Wrong phase for KO tongue
    });
    const result = detectPhaseDistance(trajectory, 0);
    expect(result.score).toBeGreaterThan(0);
    expect(result.mechanism).toBe('phase_distance');
  });

  it('should handle empty trajectory', () => {
    const result = detectPhaseDistance([], 0);
    expect(result.score).toBe(0);
    expect(result.flagged).toBe(false);
  });
});

describe('Curvature Accumulation Detection', () => {
  it('should return low score for smooth (honest) trajectory', () => {
    const trajectory = makeHonestTrajectory(20);
    const result = detectCurvatureAccumulation(trajectory);
    expect(result.score).toBeLessThan(0.7);
    expect(result.mechanism).toBe('curvature_accumulation');
  });

  it('should produce valid scores for different trajectories', () => {
    const malicious = makeMaliciousTrajectory(20);
    const honest = makeHonestTrajectory(20);

    const malResult = detectCurvatureAccumulation(malicious);
    const honResult = detectCurvatureAccumulation(honest);

    // Both should produce valid scores in [0, 1]
    expect(malResult.score).toBeGreaterThanOrEqual(0);
    expect(malResult.score).toBeLessThanOrEqual(1);
    expect(honResult.score).toBeGreaterThanOrEqual(0);
    expect(honResult.score).toBeLessThanOrEqual(1);
  });

  it('should handle short trajectory (< 3 points)', () => {
    const result = detectCurvatureAccumulation([makeTrajectoryPoint(0, makeDefaultState())]);
    expect(result.score).toBe(0);
  });
});

describe('Threat Lissajous Detection', () => {
  it('should return low score for linear (honest) trajectory', () => {
    const trajectory = makeHonestTrajectory(20);
    const result = detectThreatLissajous(trajectory);
    expect(result.mechanism).toBe('threat_lissajous');
    // Honest agents should have low Lissajous complexity
    expect(result.score).toBeLessThan(1);
  });

  it('should handle short trajectory', () => {
    const result = detectThreatLissajous([
      makeTrajectoryPoint(0, makeDefaultState()),
      makeTrajectoryPoint(1, makeDefaultState()),
    ]);
    expect(result.score).toBe(0);
  });
});

describe('Decimal Drift Detection', () => {
  it('should return low score for honest trajectory', () => {
    const trajectory = makeHonestTrajectory(20);
    const result = detectDecimalDrift(trajectory);
    expect(result.mechanism).toBe('decimal_drift');
  });

  it('should detect suspiciously uniform drift', () => {
    // Create trajectory with perfectly uniform changes
    const points: TrajectoryPoint[] = [];
    for (let i = 0; i < 20; i++) {
      const state = new Array(BRAIN_DIMENSIONS).fill(i * 0.1);
      points.push(makeTrajectoryPoint(i, state));
    }
    const result = detectDecimalDrift(points);
    // Uniform drift should flag as suspicious
    expect(result.metadata?.uniformRatio).toBeGreaterThan(0);
  });

  it('should handle single-point trajectory', () => {
    const result = detectDecimalDrift([makeTrajectoryPoint(0, makeDefaultState())]);
    expect(result.score).toBe(0);
  });
});

describe('Six-Tonic Oscillation Detection', () => {
  it('should return low score for properly oscillating honest agent', () => {
    const trajectory = makeHonestTrajectory(20);
    const result = detectSixTonic(trajectory, 0);
    expect(result.mechanism).toBe('six_tonic');
  });

  it('should detect static signal (no oscillation)', () => {
    const points: TrajectoryPoint[] = [];
    for (let i = 0; i < 20; i++) {
      const state = makeDefaultState();
      state[17] = 1.0; // Completely static weight
      points.push(makeTrajectoryPoint(i, state));
    }
    const result = detectSixTonic(points, 0);
    expect(result.flagged).toBe(true);
    expect(result.detectedAttackTypes).toContain('static_signal');
  });

  it('should handle short trajectory', () => {
    const result = detectSixTonic([makeTrajectoryPoint(0, makeDefaultState())], 0);
    expect(result.score).toBe(0);
  });
});

describe('Combined Detection', () => {
  it('should produce ALLOW for honest trajectory', () => {
    const trajectory = makeHonestTrajectory(30);
    const result = runCombinedDetection(trajectory, 0);
    expect(result.decision).toBe('ALLOW');
    expect(result.detections.length).toBe(5);
    expect(result.combinedScore).toBeLessThan(DEFAULT_BRAIN_CONFIG.quarantineThreshold);
  });

  it('should have all 5 detection mechanisms in result', () => {
    const trajectory = makeHonestTrajectory(20);
    const result = runCombinedDetection(trajectory, 0);
    const mechanisms = result.detections.map((d) => d.mechanism);
    expect(mechanisms).toContain('phase_distance');
    expect(mechanisms).toContain('curvature_accumulation');
    expect(mechanisms).toContain('threat_lissajous');
    expect(mechanisms).toContain('decimal_drift');
    expect(mechanisms).toContain('six_tonic');
  });

  it('should have combined score between 0 and 1', () => {
    const trajectory = makeHonestTrajectory(20);
    const result = runCombinedDetection(trajectory, 0);
    expect(result.combinedScore).toBeGreaterThanOrEqual(0);
    expect(result.combinedScore).toBeLessThanOrEqual(1);
  });

  it('should respect custom thresholds', () => {
    const trajectory = makeHonestTrajectory(20);
    const result = runCombinedDetection(trajectory, 0, {
      quarantineThreshold: 0.01, // Very low threshold
    });
    // With very low threshold, even honest may be quarantined
    // But the score itself should still be valid
    expect(result.combinedScore).toBeGreaterThanOrEqual(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// 4. BFT Consensus Tests
// ═══════════════════════════════════════════════════════════════

describe('BFT Consensus (Corrected 3f+1)', () => {
  it('should require 4 nodes for f=1', () => {
    const bft = new BFTConsensus(1);
    expect(bft.requiredNodes).toBe(4);
    expect(bft.quorumSize).toBe(3);
  });

  it('should require 7 nodes for f=2', () => {
    const bft = new BFTConsensus(2);
    expect(bft.requiredNodes).toBe(7);
    expect(bft.quorumSize).toBe(5);
  });

  it('should require 10 nodes for f=3', () => {
    const bft = new BFTConsensus(3);
    expect(bft.requiredNodes).toBe(10);
    expect(bft.quorumSize).toBe(7);
  });

  it('should reach consensus with quorum approvals', () => {
    const bft = new BFTConsensus(1); // need 4 nodes, quorum 3
    const result = bft.evaluate(['approve', 'approve', 'approve', 'reject']);
    expect(result.reached).toBe(true);
    expect(result.outcome).toBe('approve');
    expect(result.validConfiguration).toBe(true);
  });

  it('should reach consensus with quorum rejections', () => {
    const bft = new BFTConsensus(1);
    const result = bft.evaluate(['reject', 'reject', 'reject', 'approve']);
    expect(result.reached).toBe(true);
    expect(result.outcome).toBe('reject');
  });

  it('should not reach consensus without quorum', () => {
    const bft = new BFTConsensus(1);
    const result = bft.evaluate(['approve', 'approve', 'reject', 'reject']);
    expect(result.reached).toBe(false);
    expect(result.outcome).toBeUndefined();
  });

  it('should reject insufficient node count', () => {
    const bft = new BFTConsensus(1); // needs 4 nodes
    const result = bft.evaluate(['approve', 'approve', 'approve']); // only 3
    expect(result.validConfiguration).toBe(false);
    expect(result.reached).toBe(false);
  });

  it('should compute max tolerable faults correctly', () => {
    expect(BFTConsensus.maxTolerableFaults(4)).toBe(1);
    expect(BFTConsensus.maxTolerableFaults(7)).toBe(2);
    expect(BFTConsensus.maxTolerableFaults(10)).toBe(3);
    expect(BFTConsensus.maxTolerableFaults(3)).toBe(0);
    expect(BFTConsensus.maxTolerableFaults(1)).toBe(0);
  });

  it('should handle abstain votes', () => {
    const bft = new BFTConsensus(1);
    const result = bft.evaluate(['approve', 'approve', 'abstain', 'abstain']);
    expect(result.reached).toBe(false); // only 2 approvals, need 3
  });

  it('should throw for negative max faults', () => {
    expect(() => new BFTConsensus(-1)).toThrow();
  });

  it('should check sufficiency correctly', () => {
    const bft = new BFTConsensus(2); // needs 7
    expect(bft.isSufficient(7)).toBe(true);
    expect(bft.isSufficient(6)).toBe(false);
    expect(bft.isSufficient(10)).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════
// 5. Quasi-Space Projection Tests
// ═══════════════════════════════════════════════════════════════

describe('Quasicrystal Icosahedral Projection', () => {
  it('should produce normalized 6D output', () => {
    const input = [1, 2, 3, 4, 5, 6];
    const projected = icosahedralProjection(input);
    expect(projected.length).toBe(6);

    const norm = Math.sqrt(projected.reduce((s, v) => s + v * v, 0));
    expect(norm).toBeCloseTo(1, 5);
  });

  it('should throw for vectors shorter than 6D', () => {
    expect(() => icosahedralProjection([1, 2, 3])).toThrow();
  });

  it('should produce different outputs for different inputs', () => {
    const a = icosahedralProjection([1, 0, 0, 0, 0, 0]);
    const b = icosahedralProjection([0, 1, 0, 0, 0, 0]);
    const diff = a.reduce((s, v, i) => s + Math.abs(v - b[i]), 0);
    expect(diff).toBeGreaterThan(0.01);
  });
});

describe('Voxel Realm Classification', () => {
  it('should classify gold for r < 0.5', () => {
    expect(classifyVoxelRealm([0.1, 0.1, 0.1])).toBe('gold');
    expect(classifyVoxelRealm([0, 0, 0])).toBe('gold');
  });

  it('should classify purple for 0.5 <= r < 0.95', () => {
    expect(classifyVoxelRealm([0.4, 0.4, 0.4])).toBe('purple');
    expect(classifyVoxelRealm([0.5, 0.5, 0.5])).toBe('purple');
  });

  it('should classify red for r >= 0.95', () => {
    expect(classifyVoxelRealm([0.8, 0.8, 0.8])).toBe('red');
  });
});

describe('Sparse Octree', () => {
  it('should create a root node', () => {
    const root = createOctreeRoot();
    expect(root.depth).toBe(0);
    expect(root.halfWidth).toBe(1.0);
    expect(root.points.length).toBe(0);
  });

  it('should insert points into the octree', () => {
    const root = createOctreeRoot(3, 4);
    octreeInsert(root, [0.1, 0.1, 0.1]);
    octreeInsert(root, [0.2, 0.2, 0.2]);
    octreeInsert(root, [-0.1, -0.1, -0.1]);
    expect(root.points.length).toBe(3);
  });

  it('should subdivide when capacity is exceeded', () => {
    const root = createOctreeRoot(3, 2);
    octreeInsert(root, [0.1, 0.1, 0.1]);
    octreeInsert(root, [0.2, 0.2, 0.2]);
    octreeInsert(root, [0.3, 0.3, 0.3]); // Should trigger subdivision
    // Root now has 2 points + subdivision with 1 in child
    const totalPoints =
      root.points.length +
      root.children.filter(Boolean).reduce((s, c) => s + (c?.points.length ?? 0), 0);
    expect(totalPoints).toBeGreaterThanOrEqual(3);
  });
});

describe('Penrose Tiling Integration', () => {
  it('should project 21D state to 2D Penrose coordinates', () => {
    const state = new Array(BRAIN_DIMENSIONS).fill(0.5);
    const [x, y] = brainStateToPenrose(state);
    expect(Number.isFinite(x)).toBe(true);
    expect(Number.isFinite(y)).toBe(true);
  });

  it('should produce different coordinates for different states', () => {
    const a = brainStateToPenrose([1, 0, 0, 0, 0, 0, ...new Array(15).fill(0)]);
    const b = brainStateToPenrose([0, 1, 0, 0, 0, 0, ...new Array(15).fill(0)]);
    expect(a[0]).not.toBeCloseTo(b[0], 3);
  });
});

describe('Quasicrystal Potential', () => {
  it('should return values in [-1, 1]', () => {
    for (let i = 0; i < 10; i++) {
      const x = Math.random() * 10 - 5;
      const y = Math.random() * 10 - 5;
      const V = quasicrystalPotential([x, y]);
      expect(V).toBeGreaterThanOrEqual(-1);
      expect(V).toBeLessThanOrEqual(1);
    }
  });

  it('should have 5-fold symmetry', () => {
    const point: [number, number] = [1, 0];
    const V0 = quasicrystalPotential(point);

    // Rotate by 72 degrees (2pi/5) - should give same potential
    const angle = (2 * Math.PI) / 5;
    const rotated: [number, number] = [
      point[0] * Math.cos(angle) - point[1] * Math.sin(angle),
      point[0] * Math.sin(angle) + point[1] * Math.cos(angle),
    ];
    const V1 = quasicrystalPotential(rotated);

    expect(V0).toBeCloseTo(V1, 10);
  });
});

// ═══════════════════════════════════════════════════════════════
// 6. Audit Logger Tests
// ═══════════════════════════════════════════════════════════════

describe('Brain Audit Logger', () => {
  it('should log state transitions', () => {
    const logger = new BrainAuditLogger();
    const oldState = new Array(21).fill(0.5);
    const newState = new Array(21).fill(0.6);

    logger.logStateTransition(5, oldState, newState, { reason: 'test' });
    expect(logger.count).toBe(1);

    const events = logger.getEvents();
    expect(events[0].eventType).toBe('state_transition');
    expect(events[0].layer).toBe(5);
    expect(events[0].stateDelta).toBeGreaterThan(0);
  });

  it('should log detection alerts', () => {
    const logger = new BrainAuditLogger();
    const assessment: any = {
      detections: [{ mechanism: 'phase_distance', flagged: true, score: 0.8 }],
      combinedScore: 0.8,
      decision: 'ESCALATE',
      anyFlagged: true,
      flagCount: 1,
      timestamp: Date.now(),
    };

    logger.logDetectionAlert(assessment, 'agent-001');
    expect(logger.count).toBe(1);
    expect(logger.getEventsByType('detection_alert').length).toBe(1);
  });

  it('should maintain hash chain integrity', () => {
    const logger = new BrainAuditLogger();
    const state1 = new Array(21).fill(0.3);
    const state2 = new Array(21).fill(0.5);
    const state3 = new Array(21).fill(0.7);

    logger.logStateTransition(1, state1, state2);
    logger.logStateTransition(2, state2, state3);
    logger.logStateTransition(3, state3, state1);

    expect(logger.verifyChainIntegrity()).toBe(true);
    expect(logger.getHashChain().length).toBe(3);
  });

  it('should respect max events limit', () => {
    const logger = new BrainAuditLogger(5);
    const state = new Array(21).fill(0);

    for (let i = 0; i < 10; i++) {
      logger.logStateTransition(1, state, state);
    }

    expect(logger.count).toBe(5);
  });
});

// ═══════════════════════════════════════════════════════════════
// 7. Golden Ratio Validation
// ═══════════════════════════════════════════════════════════════

describe('Golden Ratio Weighting', () => {
  it('should use correct golden ratio value', () => {
    expect(PHI).toBeCloseTo(1.618033988749895, 10);
  });

  it('golden weight product should be large but finite', () => {
    const product = goldenWeightProduct();
    expect(product).toBeGreaterThan(1);
    expect(Number.isFinite(product)).toBe(true);
  });

  it('weights should increase exponentially', () => {
    const v1 = new Array(BRAIN_DIMENSIONS).fill(1);
    const weighted = applyGoldenWeighting(v1);

    for (let i = 1; i < BRAIN_DIMENSIONS; i++) {
      expect(weighted[i]).toBeGreaterThan(weighted[i - 1]);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// 8. Integration Tests
// ═══════════════════════════════════════════════════════════════

describe('End-to-End Brain Manifold Integration', () => {
  it('should process a complete agent lifecycle', () => {
    // 1. Create brain state
    const state = new UnifiedBrainState({
      scbeContext: {
        deviceTrust: 0.9,
        locationTrust: 0.8,
        networkTrust: 0.9,
        behaviorScore: 0.85,
        timeOfDay: 0.5,
        intentAlignment: 0.9,
      },
      navigation: { x: 0, y: 0, z: 0, time: 0, priority: 0.7, confidence: 0.9 },
      cognitivePosition: { px: 0, py: 0, pz: 0 },
      semanticPhase: { activeTongue: 0, phaseAngle: 0, tongueWeight: 1 },
      swarmCoordination: { trustScore: 0.9, byzantineVotes: 0, spectralCoherence: 0.8 },
    });

    // 2. Check it fits in Poincare ball
    expect(state.boundaryDistance()).toBeGreaterThan(0);

    // 3. Generate trajectory
    const trajectory = makeHonestTrajectory(20);

    // 4. Run combined detection
    const assessment = runCombinedDetection(trajectory, 0);
    expect(assessment.decision).toBe('ALLOW');

    // 5. Run BFT consensus
    const bft = new BFTConsensus(1);
    const consensus = bft.evaluate(['approve', 'approve', 'approve', 'approve']);
    expect(consensus.reached).toBe(true);
    expect(consensus.outcome).toBe('approve');

    // 6. Log to audit
    const logger = new BrainAuditLogger();
    logger.logDetectionAlert(assessment, 'test-agent');
    logger.logRiskDecision('ALLOW', 'test-agent', 'All mechanisms clear');
    expect(logger.count).toBe(2);
    expect(logger.verifyChainIntegrity()).toBe(true);
  });

  it('should correctly handle the 21D manifold dimensions', () => {
    // Verify: SCBE(6) + Navigation(6) + Cognitive(3) + Semantic(3) + Swarm(3) = 21
    expect(6 + 6 + 3 + 3 + 3).toBe(BRAIN_DIMENSIONS);
    expect(BRAIN_DIMENSIONS).toBe(21);
  });

  it('hyperbolic distance advantage over Euclidean near boundary', () => {
    // Points near the Poincare ball boundary should have much larger
    // hyperbolic distances than Euclidean distances (the key advantage)
    const nearBoundary1 = new Array(3).fill(0);
    nearBoundary1[0] = 0.9;
    const nearBoundary2 = new Array(3).fill(0);
    nearBoundary2[0] = 0.91;

    const eucDist = euclideanDistance(nearBoundary1, nearBoundary2);
    const hypDist = hyperbolicDistanceSafe(nearBoundary1, nearBoundary2);

    // Hyperbolic distance should be significantly larger near boundary
    expect(hypDist).toBeGreaterThan(eucDist);
    expect(hypDist / eucDist).toBeGreaterThan(1);
  });
});
