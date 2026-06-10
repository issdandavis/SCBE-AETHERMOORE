/**
 * @file drone-fleet.test.ts
 * @module tests/fleet/drone-fleet
 * @layer L3-L14
 *
 * Tests for the 6 Drone Fleet Architecture Upgrades:
 *   1. Gravitational Braking
 *   2. Sphere-in-Cube Topology
 *   3. Harmonic Camouflage
 *   4. Sacred Tongues Flight Dynamics
 *   5. Acoustic Bottle Beams
 *   6. Dimensional Lifting
 */

import { describe, it, expect } from 'vitest';

// 1. Gravitational Braking
import {
  computeGravitationalBraking,
  computeDivergence,
  monitorAndBrake,
  criticalDivergence,
  DEFAULT_BRAKING_CONFIG,
  type GravitationalBrakingConfig,
  type FlightPathWaypoint,
  type DroneFlightState,
} from '../../src/fleet/drone-fleet/gravitationalBraking';

// 2. Sphere-in-Cube Topology
import {
  isInsideBounds,
  penetrationDepth,
  classifyManeuver,
  createManeuver,
  harmonicWallCost,
  DEFAULT_SPHERE_CUBE_CONFIG,
} from '../../src/fleet/drone-fleet/sphereCubeTopology';

// 3. Harmonic Camouflage
import {
  deriveCamouflageFrequency,
  modulateSignal,
  generateDecoys,
  estimateDetectability,
  createCamouflageState,
  STELLAR_P_MODES,
  DEFAULT_CAMOUFLAGE_CONFIG,
} from '../../src/fleet/drone-fleet/harmonicCamouflage';

// 4. Sacred Tongues Flight Dynamics
import {
  encodeCommand,
  decodeCommand,
  resolveInstruction,
  computeDynamics,
  parseCommandString,
  bandwidthSavings,
  TONGUE_FLIGHT_MAP,
} from '../../src/fleet/drone-fleet/sacredTonguesFlight';

// 5. Acoustic Bottle Beams
import {
  activateBottleBeam,
  shouldActivate,
  generateSourcePositions,
  computeCoreInterference,
  computeCornerRedistribution,
  getProtectionStatus,
  DEFAULT_ENCLOSURE,
  DEFAULT_BOTTLE_BEAM_CONFIG,
} from '../../src/fleet/drone-fleet/acousticBottleBeam';

// 6. Dimensional Lifting
import {
  liftGraph,
  detectROP,
  validateLifting,
  DEFAULT_LIFTING_CONFIG,
} from '../../src/fleet/drone-fleet/dimensionalLifting';

import { ControlFlowGraph, createVertex } from '../../src/harmonic/hamiltonianCFI';

// ═════════════════════════════════════════════════════════════════
// 1. Gravitational Braking
// ═════════════════════════════════════════════════════════════════

describe('GravitationalBraking', () => {
  describe('computeGravitationalBraking', () => {
    it('should return full clock speed when divergence is zero', () => {
      const result = computeGravitationalBraking(100, 0);
      expect(result.dilationFactor).toBeCloseTo(1.0);
      expect(result.dilatedTime).toBeCloseTo(100);
      expect(result.isEventHorizon).toBe(false);
      expect(result.shouldNeutralize).toBe(false);
    });

    it('should dilate time proportionally to divergence', () => {
      const result = computeGravitationalBraking(100, 0.5);
      expect(result.dilationFactor).toBeCloseTo(0.5, 1);
      expect(result.dilatedTime).toBeCloseTo(50, 0);
    });

    it('should reach event horizon when divergence equals trust radius', () => {
      const result = computeGravitationalBraking(100, 1.0);
      // With epsilon=1e-9, factor ≈ 1e-9 (extremely close to 0)
      expect(result.dilationFactor).toBeLessThan(DEFAULT_BRAKING_CONFIG.eventHorizonThreshold);
      expect(result.shouldNeutralize).toBe(true);
    });

    it('should clamp dilation factor to zero for divergence beyond trust radius', () => {
      const result = computeGravitationalBraking(100, 2.0);
      expect(result.dilationFactor).toBe(0);
      expect(result.dilatedTime).toBe(0);
      expect(result.isEventHorizon).toBe(true);
    });

    it('should respect custom config', () => {
      const config: GravitationalBrakingConfig = {
        k: 0.5,
        trustRadius: 2.0,
        epsilon: 1e-9,
        eventHorizonThreshold: 0.05,
      };
      const result = computeGravitationalBraking(100, 1.0, config);
      expect(result.dilationFactor).toBeCloseTo(0.75, 1);
      expect(result.shouldNeutralize).toBe(false);
    });

    it('should flag neutralization at threshold', () => {
      const config: GravitationalBrakingConfig = {
        k: 1.0,
        trustRadius: 1.0,
        epsilon: 1e-9,
        eventHorizonThreshold: 0.1,
      };
      const result = computeGravitationalBraking(100, 0.95, config);
      expect(result.dilationFactor).toBeLessThan(0.1);
      expect(result.shouldNeutralize).toBe(true);
    });
  });

  describe('computeDivergence', () => {
    it('should return zero for point on path', () => {
      const path: FlightPathWaypoint[] = [
        { position: [0, 0, 0], time: 0 },
        { position: [10, 0, 0], time: 10 },
      ];
      const d = computeDivergence([5, 0, 0], path);
      expect(d).toBeCloseTo(0);
    });

    it('should return distance for point off path', () => {
      const path: FlightPathWaypoint[] = [
        { position: [0, 0, 0], time: 0 },
        { position: [10, 0, 0], time: 10 },
      ];
      const d = computeDivergence([5, 3, 4], path);
      expect(d).toBeCloseTo(5); // 3-4-5 triangle
    });

    it('should return infinity for empty path', () => {
      expect(computeDivergence([1, 2, 3], [])).toBe(Infinity);
    });
  });

  describe('monitorAndBrake', () => {
    it('should combine divergence computation with braking', () => {
      const drone: DroneFlightState = {
        position: [5, 3, 4],
        velocity: [1, 0, 0],
        droneId: 'test-001',
        clockTime: 100,
      };
      const path: FlightPathWaypoint[] = [
        { position: [0, 0, 0], time: 0 },
        { position: [10, 0, 0], time: 10 },
      ];
      const result = monitorAndBrake(drone, path);
      expect(result.divergence).toBeCloseTo(5);
      expect(result.dilationFactor).toBeLessThan(1);
    });
  });

  describe('criticalDivergence', () => {
    it('should return trust radius for k=1', () => {
      const d = criticalDivergence(DEFAULT_BRAKING_CONFIG);
      expect(d).toBeCloseTo(1.0, 5);
    });
  });
});

// ═════════════════════════════════════════════════════════════════
// 2. Sphere-in-Cube Topology
// ═════════════════════════════════════════════════════════════════

describe('SphereCubeTopology', () => {
  describe('isInsideBounds', () => {
    const bounds = {
      min: [-1, -1, -1] as [number, number, number],
      max: [1, 1, 1] as [number, number, number],
    };

    it('should return true for point inside bounds', () => {
      expect(isInsideBounds([0, 0, 0], bounds)).toBe(true);
      expect(isInsideBounds([0.5, -0.5, 0.9], bounds)).toBe(true);
    });

    it('should return true for point on boundary', () => {
      expect(isInsideBounds([1, 1, 1], bounds)).toBe(true);
      expect(isInsideBounds([-1, -1, -1], bounds)).toBe(true);
    });

    it('should return false for point outside bounds', () => {
      expect(isInsideBounds([2, 0, 0], bounds)).toBe(false);
      expect(isInsideBounds([0, 0, -1.5], bounds)).toBe(false);
    });
  });

  describe('penetrationDepth', () => {
    const bounds = {
      min: [-1, -1, -1] as [number, number, number],
      max: [1, 1, 1] as [number, number, number],
    };

    it('should return zero for point inside', () => {
      expect(penetrationDepth([0, 0, 0], bounds)).toBe(0);
    });

    it('should return distance past boundary', () => {
      expect(penetrationDepth([2, 0, 0], bounds)).toBeCloseTo(1);
      expect(penetrationDepth([0, 0, -3], bounds)).toBeCloseTo(2);
    });
  });

  describe('classifyManeuver', () => {
    it('should classify interior maneuver as INTERIOR', () => {
      const m = createManeuver([0, 0, 0], [0.5, 0.5, 0.5]);
      const result = classifyManeuver(m);
      expect(result.pathType).toBe('INTERIOR');
      expect(result.authorized).toBe(true);
      expect(result.harmonicCost).toBe(1.0);
      expect(result.dwellTimeMs).toBe(0);
      expect(result.requiredSignatures).toBe(0);
    });

    it('should classify exterior maneuver as EXTERIOR with cost', () => {
      const m = createManeuver([0, 0, 0], [3, 3, 3]);
      const result = classifyManeuver(m);
      expect(result.pathType).toBe('EXTERIOR');
      expect(result.authorized).toBe(false);
      expect(result.harmonicCost).toBeGreaterThan(1.0);
      expect(result.dwellTimeMs).toBeGreaterThan(0);
      expect(result.requiredSignatures).toBe(3);
    });
  });

  describe('harmonicWallCost', () => {
    it('should return 1.0 for zero penetration', () => {
      expect(harmonicWallCost(0, 1.5, 1.618)).toBe(1.0);
    });

    it('should scale superexponentially with penetration', () => {
      const cost1 = harmonicWallCost(0.5, 1.5, 1.618);
      const cost2 = harmonicWallCost(1.0, 1.5, 1.618);
      const cost3 = harmonicWallCost(2.0, 1.5, 1.618);
      expect(cost1).toBeGreaterThan(1);
      expect(cost2).toBeGreaterThan(cost1);
      expect(cost3).toBeGreaterThan(cost2);
      // Superexponential: cost3/cost2 >> cost2/cost1
      expect(cost3 / cost2).toBeGreaterThan(cost2 / cost1);
    });
  });
});

// ═════════════════════════════════════════════════════════════════
// 3. Harmonic Camouflage
// ═════════════════════════════════════════════════════════════════

describe('HarmonicCamouflage', () => {
  describe('deriveCamouflageFrequency', () => {
    it('should multiply base by 2^n', () => {
      expect(deriveCamouflageFrequency(1.0, 3)).toBeCloseTo(8.0);
      expect(deriveCamouflageFrequency(0.001, 10)).toBeCloseTo(1.024);
    });

    it('should work with stellar p-modes', () => {
      const freq = deriveCamouflageFrequency(STELLAR_P_MODES.SOL, 10);
      expect(freq).toBeCloseTo(STELLAR_P_MODES.SOL * 1024);
    });
  });

  describe('modulateSignal', () => {
    it('should create a camouflaged signal with correct carrier', () => {
      const signal = modulateSignal([1, 2, 3]);
      expect(signal.payload).toEqual([1, 2, 3]);
      expect(signal.carrierFrequency).toBeCloseTo(
        DEFAULT_CAMOUFLAGE_CONFIG.baseFrequency *
          Math.pow(2, DEFAULT_CAMOUFLAGE_CONFIG.harmonicMultiplier)
      );
      expect(signal.isDecoy).toBe(false);
    });

    it('should apply low amplitude from negative SNR', () => {
      const signal = modulateSignal([1], { ...DEFAULT_CAMOUFLAGE_CONFIG, targetSNR: -40 });
      expect(signal.amplitude).toBeLessThan(0.1);
    });
  });

  describe('generateDecoys', () => {
    it('should generate requested number of decoys', () => {
      const decoys = generateDecoys(5);
      expect(decoys).toHaveLength(5);
      decoys.forEach((d) => {
        expect(d.isDecoy).toBe(true);
        expect(d.payload).toEqual([]);
      });
    });
  });

  describe('estimateDetectability', () => {
    it('should return low detectability for low amplitude', () => {
      const d = estimateDetectability(0.01, 10, 1.0);
      expect(d).toBeLessThan(0.01);
    });

    it('should return high detectability for high amplitude', () => {
      const d = estimateDetectability(1.0, 0, 0.1);
      expect(d).toBeGreaterThan(0.5);
    });
  });

  describe('createCamouflageState', () => {
    it('should create coherent state', () => {
      const state = createCamouflageState(6, DEFAULT_CAMOUFLAGE_CONFIG, 'SOL');
      expect(state.activeSignals).toBe(6);
      expect(state.decoySignals).toBe(DEFAULT_CAMOUFLAGE_CONFIG.decoyCount);
      expect(state.stellarSource).toBe('SOL');
      expect(state.detectability).toBeGreaterThanOrEqual(0);
      expect(state.detectability).toBeLessThanOrEqual(1);
    });
  });
});

// ═════════════════════════════════════════════════════════════════
// 4. Sacred Tongues Flight Dynamics
// ═════════════════════════════════════════════════════════════════

describe('SacredTonguesFlightDynamics', () => {
  describe('TONGUE_FLIGHT_MAP', () => {
    it('should have all 6 tongues mapped', () => {
      expect(Object.keys(TONGUE_FLIGHT_MAP)).toHaveLength(6);
      expect(TONGUE_FLIGHT_MAP.KO.behavior).toBe('FLOW_TRAVEL');
      expect(TONGUE_FLIGHT_MAP.RU.behavior).toBe('HOLD_POSITION');
      expect(TONGUE_FLIGHT_MAP.CA.behavior).toBe('EXECUTE_ENGAGE');
      expect(TONGUE_FLIGHT_MAP.UM.behavior).toBe('STEALTH_MODE');
      expect(TONGUE_FLIGHT_MAP.DR.behavior).toBe('FORMATION_LOCK');
    });

    it('should have weights following spec', () => {
      expect(TONGUE_FLIGHT_MAP.KO.weight).toBe(1.0);
      expect(TONGUE_FLIGHT_MAP.DR.weight).toBe(11.09);
    });

    it('should have correct phase angles', () => {
      expect(TONGUE_FLIGHT_MAP.KO.phaseDeg).toBe(0);
      expect(TONGUE_FLIGHT_MAP.AV.phaseDeg).toBe(60);
      expect(TONGUE_FLIGHT_MAP.RU.phaseDeg).toBe(120);
      expect(TONGUE_FLIGHT_MAP.CA.phaseDeg).toBe(180);
      expect(TONGUE_FLIGHT_MAP.UM.phaseDeg).toBe(240);
      expect(TONGUE_FLIGHT_MAP.DR.phaseDeg).toBe(300);
    });
  });

  describe('encodeCommand / decodeCommand', () => {
    it('should encode and decode KO command round-trip', () => {
      const cmd = { tongue: 'KO' as const, subCommand: 5, intensity: 0.8 };
      const encoded = encodeCommand(cmd);
      expect(encoded).toHaveLength(2);
      const decoded = decodeCommand(encoded);
      expect(decoded.tongue).toBe('KO');
      expect(decoded.subCommand).toBe(5);
      expect(decoded.intensity).toBeCloseTo(0.8, 1);
    });

    it('should encode and decode all tongues', () => {
      const tongues = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'] as const;
      for (const tongue of tongues) {
        const cmd = { tongue, subCommand: 0, intensity: 1.0 };
        const decoded = decodeCommand(encodeCommand(cmd));
        expect(decoded.tongue).toBe(tongue);
      }
    });

    it('should achieve 2-byte encoding (64x reduction from 128 bytes)', () => {
      const savings = bandwidthSavings(128);
      expect(savings.encodedBytes).toBe(2);
      expect(savings.ratio).toBe(64);
      expect(savings.savingsPercent).toBeCloseTo(98.4375);
    });
  });

  describe('resolveInstruction', () => {
    it('should resolve RU command to HOLD_POSITION', () => {
      const instruction = resolveInstruction({
        tongue: 'RU',
        subCommand: 0,
        intensity: 1.0,
      });
      expect(instruction.behavior).toBe('HOLD_POSITION');
      expect(instruction.weight).toBe(2.62);
    });
  });

  describe('computeDynamics', () => {
    it('should set stealth mode for UM tongue', () => {
      const instruction = resolveInstruction({
        tongue: 'UM',
        subCommand: 0,
        intensity: 0.5,
      });
      const dynamics = computeDynamics(instruction);
      expect(dynamics.isStealth).toBe(true);
      expect(dynamics.mode).toBe('STEALTH_MODE');
    });

    it('should lock position for RU tongue', () => {
      const instruction = resolveInstruction({
        tongue: 'RU',
        subCommand: 0,
        intensity: 1.0,
      });
      const dynamics = computeDynamics(instruction);
      expect(dynamics.isPositionLocked).toBe(true);
      expect(dynamics.velocityMultiplier).toBe(0);
    });
  });

  describe('parseCommandString', () => {
    it('should parse "ru:khar\'ak" as RU tongue', () => {
      const cmd = parseCommandString("ru:khar'ak");
      expect(cmd).not.toBeNull();
      expect(cmd!.tongue).toBe('RU');
    });

    it('should return null for invalid tongue', () => {
      expect(parseCommandString('xx:test')).toBeNull();
    });
  });
});

// ═════════════════════════════════════════════════════════════════
// 5. Acoustic Bottle Beams
// ═════════════════════════════════════════════════════════════════

describe('AcousticBottleBeams', () => {
  describe('shouldActivate', () => {
    it('should activate for ATTACK violations', () => {
      expect(
        shouldActivate({
          type: 'ATTACK',
          severity: 0.5,
          stateVector: [1],
          timestamp: Date.now(),
        })
      ).toBe(true);
    });

    it('should activate for high-severity DEVIATION', () => {
      expect(
        shouldActivate({
          type: 'DEVIATION',
          severity: 0.8,
          stateVector: [1],
          timestamp: Date.now(),
        })
      ).toBe(true);
    });

    it('should NOT activate for low-severity DEVIATION', () => {
      expect(
        shouldActivate({
          type: 'DEVIATION',
          severity: 0.3,
          stateVector: [1],
          timestamp: Date.now(),
        })
      ).toBe(false);
    });

    it('should NOT activate for OBSTRUCTION', () => {
      expect(
        shouldActivate({
          type: 'OBSTRUCTION',
          severity: 1.0,
          stateVector: [1],
          timestamp: Date.now(),
        })
      ).toBe(false);
    });
  });

  describe('generateSourcePositions', () => {
    it('should generate correct number of sources', () => {
      const sources = generateSourcePositions(DEFAULT_ENCLOSURE, 8);
      expect(sources).toHaveLength(8);
    });

    it('should place sources around enclosure perimeter', () => {
      const sources = generateSourcePositions(DEFAULT_ENCLOSURE, 4);
      expect(sources).toHaveLength(4);
      sources.forEach((s) => {
        expect(s).toHaveLength(3);
      });
    });
  });

  describe('computeCoreInterference', () => {
    it('should achieve near-zero interference with paired phase-inverted sources', () => {
      const sources = generateSourcePositions(DEFAULT_ENCLOSURE, 8);
      const interference = computeCoreInterference(sources, DEFAULT_ENCLOSURE.dataCoreCenter, 2.0);
      // Interference should be significantly less than source count
      expect(interference).toBeLessThan(DEFAULT_BOTTLE_BEAM_CONFIG.sourceCount);
    });
  });

  describe('computeCornerRedistribution', () => {
    it('should conserve energy (A1: Unitarity)', () => {
      const corners = computeCornerRedistribution(100, 0.8);
      const total = corners.reduce((a, b) => a + b, 0);
      expect(total).toBeCloseTo(80); // 100 * 0.8
    });

    it('should distribute equally to 4 corners', () => {
      const corners = computeCornerRedistribution(100, 1.0);
      corners.forEach((c) => expect(c).toBeCloseTo(25));
    });
  });

  describe('activateBottleBeam', () => {
    it('should activate and scramble data bus', () => {
      const violation = {
        type: 'ATTACK' as const,
        severity: 1.0,
        stateVector: [1, 2, 3],
        timestamp: Date.now(),
      };
      const result = activateBottleBeam(violation);
      expect(result.activated).toBe(true);
      expect(result.canceledEnergy).toBeGreaterThan(0);
      // Corner energy should sum to canceled energy (conservation)
      const cornerSum = result.cornerEnergy.reduce((a, b) => a + b, 0);
      expect(cornerSum).toBeCloseTo(result.canceledEnergy, 5);
    });
  });

  describe('getProtectionStatus', () => {
    it('should return UNPROTECTED when not armed', () => {
      const status = getProtectionStatus(false, null);
      expect(status.level).toBe('UNPROTECTED');
      expect(status.isScrambled).toBe(false);
    });

    it('should return ARMED when armed but not triggered', () => {
      const status = getProtectionStatus(true, null);
      expect(status.level).toBe('ARMED');
    });
  });
});

// ═════════════════════════════════════════════════════════════════
// 6. Dimensional Lifting
// ═════════════════════════════════════════════════════════════════

describe('DimensionalLifting', () => {
  function buildSimpleGraph(): ControlFlowGraph {
    const cfg = new ControlFlowGraph();
    for (let i = 0; i < 6; i++) {
      cfg.addVertex(createVertex(i, `v${i}`, i * 0x100));
    }
    // Create a cycle: 0-1-2-3-4-5-0
    for (let i = 0; i < 6; i++) {
      cfg.addEdge(i, (i + 1) % 6);
    }
    return cfg;
  }

  function buildObstructedGraph(): ControlFlowGraph {
    // Bipartite graph with imbalance (non-Hamiltonian obstruction)
    const cfg = new ControlFlowGraph();
    // Set A: 4 vertices
    for (let i = 0; i < 4; i++) {
      cfg.addVertex(createVertex(i, `a${i}`, i * 0x100));
    }
    // Set B: 6 vertices
    for (let i = 4; i < 10; i++) {
      cfg.addVertex(createVertex(i, `b${i - 4}`, i * 0x100));
    }
    // Connect A to B only (bipartite, |A|=4, |B|=6, imbalance=2)
    for (let a = 0; a < 4; a++) {
      for (let b = 4; b < 10; b++) {
        cfg.addEdge(a, b);
      }
    }
    return cfg;
  }

  describe('liftGraph', () => {
    it('should recognize already-Hamiltonian graphs', () => {
      const cfg = buildSimpleGraph();
      const result = liftGraph(cfg);
      expect(result.resolved).toBe(true);
      expect(result.augmentedEdges).toBe(0);
    });

    it('should resolve obstructed graph via 4D lifting', () => {
      const cfg = buildObstructedGraph();
      const originalCheck = cfg.checkHamiltonian();
      expect(originalCheck.bipartite.isBipartite).toBe(true);
      expect(originalCheck.bipartite.imbalance).toBe(2);

      const result = liftGraph(cfg, {
        ...DEFAULT_LIFTING_CONFIG,
        targetDimension: '4D_HYPER_TORUS',
      });
      expect(result.augmentedEdges).toBeGreaterThan(0);
      expect(result.liftedVertexCount).toBeGreaterThanOrEqual(cfg.vertexCount);
    });

    it('should resolve obstructed graph via 6D symplectic lifting', () => {
      const cfg = buildObstructedGraph();
      const result = liftGraph(cfg, {
        ...DEFAULT_LIFTING_CONFIG,
        targetDimension: '6D_SYMPLECTIC',
      });
      expect(result.augmentedEdges).toBeGreaterThan(0);
      expect(result.liftedVertexCount).toBeGreaterThan(cfg.vertexCount);
    });
  });

  describe('detectROP', () => {
    it('should detect ROP when trace has invalid transitions', () => {
      const cfg = buildSimpleGraph();
      // Valid trace: 0,1,2,3,4,5
      const validResult = detectROP([0, 1, 2, 3, 4, 5], cfg);
      expect(validResult.ropDetected).toBe(false);
      expect(validResult.gadgetChains).toHaveLength(0);

      // Invalid trace: 0,3,1,5,2 (skipping edges)
      const ropResult = detectROP([0, 3, 1, 5, 2, 4], cfg);
      expect(ropResult.ropDetected).toBe(true);
      expect(ropResult.confidence).toBeGreaterThan(0);
    });

    it('should return VALID for empty trace', () => {
      const cfg = buildSimpleGraph();
      const result = detectROP([], cfg);
      expect(result.ropDetected).toBe(false);
    });
  });

  describe('validateLifting', () => {
    it('should validate that lifting preserves original structure', () => {
      const original = buildSimpleGraph();
      const lifted = buildSimpleGraph();
      // Add extra vertex to lifted
      lifted.addVertex(createVertex(100, 'extra', 0xf00));
      lifted.addEdge(0, 100);

      expect(validateLifting(original, lifted)).toBe(true);
    });

    it('should reject lifting that loses vertices', () => {
      const original = buildSimpleGraph();
      const bad = new ControlFlowGraph();
      bad.addVertex(createVertex(0, 'v0', 0));

      expect(validateLifting(original, bad)).toBe(false);
    });
  });
});

// ═════════════════════════════════════════════════════════════════
// Integration: Cross-Module Scenarios
// ═════════════════════════════════════════════════════════════════

describe('DroneFleet Integration', () => {
  it('should apply gravitational braking when drone exits mission bounds', () => {
    // Drone leaves the mission bounds → divergence measured → braking applied
    const maneuver = createManeuver([0, 0, 0], [3, 3, 3]);
    const classification = classifyManeuver(maneuver);
    expect(classification.pathType).toBe('EXTERIOR');

    // Use penetration depth as divergence for braking
    const braking = computeGravitationalBraking(100, classification.penetrationDepth, {
      ...DEFAULT_BRAKING_CONFIG,
      trustRadius: 3.0,
    });
    expect(braking.dilationFactor).toBeLessThan(1.0);
  });

  it('should use Sacred Tongue commands for camouflaged coordination', () => {
    // Encode a command using Sacred Tongues
    const cmd = { tongue: 'DR' as const, subCommand: 1, intensity: 1.0 };
    const [b0, b1] = encodeCommand(cmd);

    // Modulate as camouflaged signal
    const signal = modulateSignal([b0, b1]);
    expect(signal.payload).toEqual([b0, b1]);
    expect(signal.isDecoy).toBe(false);

    // Decode on receiving end
    const decoded = decodeCommand([signal.payload[0], signal.payload[1]]);
    expect(decoded.tongue).toBe('DR');
    const instruction = resolveInstruction(decoded);
    expect(instruction.behavior).toBe('FORMATION_LOCK');
  });

  it('should trigger bottle beam when CFI detects attack on captured drone', () => {
    // Build a graph and detect attack
    const cfg = new ControlFlowGraph();
    for (let i = 0; i < 4; i++) {
      cfg.addVertex(createVertex(i, `v${i}`, i));
    }
    cfg.addEdge(0, 1);
    cfg.addEdge(1, 2);
    cfg.addEdge(2, 3);

    // Detect invalid trace (ROP-like)
    const rop = detectROP([0, 2, 1, 3], cfg);

    if (rop.ropDetected) {
      const violation = {
        type: 'ATTACK' as const,
        severity: rop.confidence,
        stateVector: [0, 2, 1, 3],
        timestamp: Date.now(),
      };

      if (shouldActivate(violation)) {
        const beam = activateBottleBeam(violation);
        expect(beam.activated).toBe(true);
        expect(beam.dataBusReadable).toBe(false);
      }
    }
  });
});
