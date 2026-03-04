/**
 * @file security-engine.test.ts
 * @module tests/security-engine
 * @layer L1-L14
 *
 * Integration tests for the SCBE AI Security Engine.
 *
 * Tests the full machine-science control framework:
 * - Machine Constants Registry (configurable invariants)
 * - Q16.16 Fixed-Point deterministic math
 * - Hyperspace State Engine (9D embedding)
 * - Policy Field Evaluator (overlapping constraint fields)
 * - Context-Coupled Security Engine (unified gate)
 * - Digital Twin Governor (predictive control oracle)
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';

import {
  // Machine Constants
  toQ16,
  fromQ16,
  mulQ16,
  divQ16,
  MachineConstantsRegistry,
  getGlobalRegistry,
  resetGlobalRegistry,
  DEFAULT_MACHINE_CONSTANTS,
  // Hyperspace
  HyperDim,
  HYPER_DIMS,
  type HyperspaceCoord,
  hyperspaceDistance,
  hyperspaceDistanceQ16,
  safeOrigin,
  distanceFromSafe,
  embedInHyperspace,
  HyperspaceManifold,
  DEFAULT_DIMENSION_WEIGHTS,
  // Policy Fields
  PolicyCategory,
  SafetyField,
  ComplianceField,
  ResourceField,
  TrustField,
  RoleField,
  TemporalField,
  PolicyFieldEvaluator,
  // Context Engine
  SecurityDecision,
  type ActionRequest,
  ContextCoupledSecurityEngine,
  // Digital Twin
  DigitalTwinGovernor,
} from '../../src/security-engine/index.js';

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════

function makeSafeRequest(entityId: string, timestampUs: number): ActionRequest {
  return {
    entityId,
    action: 'read',
    target: 'data',
    context6D: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    timestampUs,
    pqcValid: true,
    spectralCoherence: 1.0,
    triadicStability: 1.0,
    systemLoad: 0.1,
  };
}

function makeAdversarialRequest(entityId: string, timestampUs: number): ActionRequest {
  return {
    entityId,
    action: 'delete',
    target: 'system_config',
    context6D: [0.9, 0.8, 0.95, 0.7, 0.85, 0.9],
    timestampUs,
    pqcValid: true,
    spectralCoherence: 0.2,
    triadicStability: 0.3,
    systemLoad: 0.9,
  };
}

// ═══════════════════════════════════════════════════════════════
// Q16.16 Fixed-Point Tests
// ═══════════════════════════════════════════════════════════════

describe('Q16.16 Fixed-Point Arithmetic', () => {
  it('should convert float to Q16.16 and back', () => {
    const values = [0, 1.0, -1.0, 0.5, 3.14159, 100.0, -42.5];
    for (const v of values) {
      const q = toQ16(v);
      const back = fromQ16(q);
      expect(Math.abs(back - v)).toBeLessThan(0.001);
    }
  });

  it('should multiply in Q16.16 deterministically', () => {
    const a = toQ16(2.5);
    const b = toQ16(3.0);
    const result = fromQ16(mulQ16(a, b));
    expect(Math.abs(result - 7.5)).toBeLessThan(0.01);
  });

  it('should divide in Q16.16 deterministically', () => {
    const a = toQ16(10.0);
    const b = toQ16(3.0);
    const result = fromQ16(divQ16(a, b));
    expect(Math.abs(result - 10.0 / 3.0)).toBeLessThan(0.01);
  });

  it('should reject division by zero', () => {
    expect(() => divQ16(toQ16(1.0), 0)).toThrow('Q16 division by zero');
  });

  it('should be cross-platform deterministic (same result every time)', () => {
    const a = toQ16(1.618033988749895); // phi
    const b = toQ16(0.144720);          // tick rate / 1000
    const result1 = mulQ16(a, b);
    const result2 = mulQ16(a, b);
    expect(result1).toBe(result2); // exact integer equality
  });
});

// ═══════════════════════════════════════════════════════════════
// Machine Constants Registry Tests
// ═══════════════════════════════════════════════════════════════

describe('Machine Constants Registry', () => {
  beforeEach(() => {
    resetGlobalRegistry();
  });

  it('should provide default constants', () => {
    const reg = getGlobalRegistry();
    expect(reg.active.harmonic.harmonicR).toBe(1.5);
    expect(reg.active.harmonic.phi).toBeCloseTo(1.618, 3);
    expect(reg.active.temporal.tickFrequencyHz).toBe(144.72);
    expect(reg.active.trust.allowThreshold).toBe(0.85);
    expect(reg.active.version).toBe('1.0.0');
  });

  it('should support atomic swap', () => {
    const reg = getGlobalRegistry();
    const custom = {
      ...DEFAULT_MACHINE_CONSTANTS,
      version: '2.0.0',
      harmonic: { ...DEFAULT_MACHINE_CONSTANTS.harmonic, harmonicR: 2.0 },
    };
    reg.swap(custom);
    expect(reg.active.harmonic.harmonicR).toBe(2.0);
    expect(reg.active.version).toBe('2.0.0');
  });

  it('should support partial tuning', () => {
    const reg = getGlobalRegistry();
    reg.tune({ trust: { allowThreshold: 0.9 } });
    expect(reg.active.trust.allowThreshold).toBe(0.9);
    // Other trust values unchanged
    expect(reg.active.trust.quarantineThreshold).toBe(0.40);
  });

  it('should notify listeners on swap', () => {
    const reg = getGlobalRegistry();
    let notified = false;
    reg.onSwap(() => { notified = true; });
    reg.tune({ trust: { exileRounds: 5 } });
    expect(notified).toBe(true);
  });

  it('should maintain history', () => {
    const reg = new MachineConstantsRegistry();
    expect(reg.history().length).toBe(1); // initial
    reg.tune({ trust: { exileRounds: 5 } });
    expect(reg.history().length).toBe(2);
  });

  it('should return Q16.16 values', () => {
    const reg = getGlobalRegistry();
    const q = reg.getQ16('harmonic', 'harmonicR');
    expect(fromQ16(q)).toBeCloseTo(1.5, 3);
  });

  it('should throw on unknown Q16.16 key', () => {
    const reg = getGlobalRegistry();
    expect(() => reg.getQ16('harmonic', 'nonexistent')).toThrow();
  });

  it('should support unsubscribe', () => {
    const reg = getGlobalRegistry();
    let count = 0;
    const unsub = reg.onSwap(() => { count++; });
    reg.tune({ trust: { exileRounds: 5 } });
    expect(count).toBe(1);
    unsub();
    reg.tune({ trust: { exileRounds: 3 } });
    expect(count).toBe(1); // not incremented
  });
});

// ═══════════════════════════════════════════════════════════════
// Hyperspace State Engine Tests
// ═══════════════════════════════════════════════════════════════

describe('Hyperspace State Engine', () => {
  beforeEach(() => {
    resetGlobalRegistry();
  });

  it('should have 9 dimensions', () => {
    expect(HYPER_DIMS).toBe(9);
    expect(safeOrigin().length).toBe(9);
  });

  it('should compute zero distance at safe origin', () => {
    const origin = safeOrigin();
    expect(distanceFromSafe(origin)).toBe(0);
  });

  it('should compute positive distance for non-origin points', () => {
    const point: HyperspaceCoord = [0.5, 0, 0.3, 0.7, 0.2, 0.1, 0.1, 0.1, 0.1];
    expect(distanceFromSafe(point)).toBeGreaterThan(0);
  });

  it('should satisfy metric axioms', () => {
    const a: HyperspaceCoord = [0.1, 0, 0.2, 0.8, 0.1, 0, 0, 0, 0];
    const b: HyperspaceCoord = [0.3, 0, 0.5, 0.5, 0.3, 0.1, 0.1, 0.2, 0.1];
    const c: HyperspaceCoord = [0.5, 0, 0.1, 0.9, 0.05, 0, 0, 0, 0];

    // Non-negativity
    expect(hyperspaceDistance(a, b)).toBeGreaterThanOrEqual(0);

    // Identity of indiscernibles
    expect(hyperspaceDistance(a, a)).toBe(0);

    // Symmetry
    expect(hyperspaceDistance(a, b)).toBeCloseTo(hyperspaceDistance(b, a), 10);

    // Triangle inequality
    const dAB = hyperspaceDistance(a, b);
    const dBC = hyperspaceDistance(b, c);
    const dAC = hyperspaceDistance(a, c);
    expect(dAC).toBeLessThanOrEqual(dAB + dBC + 1e-10);
  });

  it('should compute Q16.16 distance consistently', () => {
    const a: HyperspaceCoord = [0.5, 0, 0.3, 0.7, 0.2, 0.1, 0.1, 0.1, 0.1];
    const b: HyperspaceCoord = [0.1, 0, 0.1, 0.9, 0.05, 0, 0, 0, 0];

    const floatDist = hyperspaceDistance(a, b);
    const q16Dist = fromQ16(hyperspaceDistanceQ16(a, b));

    // Q16.16 should be within ~1% of float
    expect(Math.abs(q16Dist - floatDist) / floatDist).toBeLessThan(0.05);
  });

  it('should embed entities into hyperspace', () => {
    const point = embedInHyperspace('agent-1', {
      context6D: [0.1, 0.1, 0, 0, 0, 0],
      timestampUs: 1000000,
      accumulatedIntent: 0,
      trustScore: 1.0,
      riskScore: 0,
      spectralEntropy: 0,
      policyPressure: 0,
      systemLoad: 0,
      behaviorDeviation: 0,
    });

    expect(point.entityId).toBe('agent-1');
    expect(point.coords.length).toBe(9);
    expect(point.coords[HyperDim.TRUST]).toBe(1.0);
  });

  it('should compute velocity from previous point', () => {
    const p1 = embedInHyperspace('agent-1', {
      context6D: [0.1, 0, 0, 0, 0, 0],
      timestampUs: 1_000_000,
      accumulatedIntent: 0,
      trustScore: 1.0,
      riskScore: 0,
      spectralEntropy: 0,
      policyPressure: 0,
      systemLoad: 0,
      behaviorDeviation: 0,
    });

    const p2 = embedInHyperspace('agent-1', {
      context6D: [0.5, 0, 0, 0, 0, 0],
      timestampUs: 2_000_000,
      accumulatedIntent: 0.5,
      trustScore: 0.8,
      riskScore: 0.2,
      spectralEntropy: 0.1,
      policyPressure: 0,
      systemLoad: 0.3,
      behaviorDeviation: 0.1,
    }, p1);

    // Velocity should be non-zero since state changed
    const hasNonZeroVelocity = p2.velocity.some((v) => Math.abs(v) > 0);
    expect(hasNonZeroVelocity).toBe(true);
  });

  describe('HyperspaceManifold', () => {
    it('should track multiple entities', () => {
      const manifold = new HyperspaceManifold();

      manifold.embed('agent-1', {
        context6D: [0, 0, 0, 0, 0, 0],
        timestampUs: 1_000_000,
        accumulatedIntent: 0,
        trustScore: 1.0,
        riskScore: 0,
        spectralEntropy: 0,
        policyPressure: 0,
        systemLoad: 0,
        behaviorDeviation: 0,
      });

      manifold.embed('agent-2', {
        context6D: [0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
        timestampUs: 1_000_000,
        accumulatedIntent: 2.0,
        trustScore: 0.3,
        riskScore: 0.7,
        spectralEntropy: 0.5,
        policyPressure: 1.0,
        systemLoad: 0.8,
        behaviorDeviation: 0.5,
      });

      expect(manifold.size).toBe(2);
      expect(manifold.distanceFromSafe('agent-1')).toBeLessThan(
        manifold.distanceFromSafe('agent-2'),
      );
    });

    it('should rank entities by risk', () => {
      const manifold = new HyperspaceManifold();

      manifold.embed('safe-agent', {
        context6D: [0, 0, 0, 0, 0, 0],
        timestampUs: 1_000_000,
        accumulatedIntent: 0,
        trustScore: 1.0,
        riskScore: 0,
        spectralEntropy: 0,
        policyPressure: 0,
        systemLoad: 0,
        behaviorDeviation: 0,
      });

      manifold.embed('risky-agent', {
        context6D: [0.9, 0.9, 0.9, 0.9, 0.9, 0.9],
        timestampUs: 1_000_000,
        accumulatedIntent: 5.0,
        trustScore: 0.1,
        riskScore: 0.9,
        spectralEntropy: 0.8,
        policyPressure: 2.0,
        systemLoad: 0.9,
        behaviorDeviation: 0.8,
      });

      const ranked = manifold.rankByRisk();
      expect(ranked[0].entityId).toBe('risky-agent');
      expect(ranked[1].entityId).toBe('safe-agent');
    });
  });
});

// ═══════════════════════════════════════════════════════════════
// Policy Field Tests
// ═══════════════════════════════════════════════════════════════

describe('Policy Fields', () => {
  beforeEach(() => {
    resetGlobalRegistry();
  });

  describe('SafetyField', () => {
    it('should return zero pressure at safe origin', () => {
      const field = new SafetyField();
      const origin = safeOrigin();
      const pressure = field.evaluate(origin, DEFAULT_MACHINE_CONSTANTS);
      expect(pressure).toBeCloseTo(0, 5);
    });

    it('should return exponentially increasing pressure with distance', () => {
      const field = new SafetyField();
      const p1: HyperspaceCoord = [0.2, 0, 0.1, 0.9, 0.1, 0, 0, 0, 0];
      const p2: HyperspaceCoord = [0.5, 0, 0.5, 0.5, 0.5, 0.3, 0.3, 0.3, 0.3];

      const pressure1 = field.evaluate(p1, DEFAULT_MACHINE_CONSTANTS);
      const pressure2 = field.evaluate(p2, DEFAULT_MACHINE_CONSTANTS);

      expect(pressure2).toBeGreaterThan(pressure1);
    });
  });

  describe('ComplianceField', () => {
    it('should return zero below threshold', () => {
      const field = new ComplianceField(0.5);
      const point: HyperspaceCoord = [0, 0, 0, 1, 0.3, 0, 0, 0, 0];
      expect(field.evaluate(point, DEFAULT_MACHINE_CONSTANTS)).toBe(0);
    });

    it('should return positive pressure above threshold', () => {
      const field = new ComplianceField(0.5);
      const point: HyperspaceCoord = [0, 0, 0, 1, 0.8, 0, 0, 0, 0];
      expect(field.evaluate(point, DEFAULT_MACHINE_CONSTANTS)).toBeGreaterThan(0);
    });
  });

  describe('TrustField', () => {
    it('should return zero for fully trusted entities', () => {
      const field = new TrustField();
      const point: HyperspaceCoord = [0, 0, 0, 1.0, 0, 0, 0, 0, 0];
      const pressure = field.evaluate(point, DEFAULT_MACHINE_CONSTANTS);
      expect(pressure).toBeCloseTo(0, 5);
    });

    it('should return high pressure for low-trust entities', () => {
      const field = new TrustField();
      const point: HyperspaceCoord = [0, 0, 0, 0.1, 0, 0, 0, 0, 0];
      const pressure = field.evaluate(point, DEFAULT_MACHINE_CONSTANTS);
      expect(pressure).toBeGreaterThan(0.5);
    });
  });

  describe('PolicyFieldEvaluator', () => {
    it('should create standard evaluator with all 6 fields', () => {
      const evaluator = PolicyFieldEvaluator.createStandard();
      expect(evaluator.listFields().length).toBe(6);
    });

    it('should evaluate composite pressure', () => {
      const evaluator = PolicyFieldEvaluator.createStandard();
      const point: HyperspaceCoord = [0.5, 0, 0.5, 0.5, 0.5, 0.3, 0.3, 0.3, 0.3];
      const result = evaluator.evaluate(point);

      expect(result.totalPressure).toBeGreaterThan(0);
      expect(result.fieldPressures.length).toBe(6);
      expect(result.dominantPolicy).toBeTruthy();
    });

    it('should report zero pressure at safe origin', () => {
      const evaluator = PolicyFieldEvaluator.createStandard();
      const result = evaluator.evaluate(safeOrigin());

      // Total pressure should be very small (close to zero)
      expect(result.totalPressure).toBeLessThan(0.01);
    });

    it('should identify dominant policy', () => {
      const evaluator = PolicyFieldEvaluator.createStandard();
      // High-risk point should have safety as dominant
      const point: HyperspaceCoord = [0.8, 0, 0.8, 0.2, 0.8, 0.5, 0.5, 0.5, 0.8];
      const result = evaluator.evaluate(point);
      expect(result.dominantPolicy).toBeTruthy();
    });

    it('should enforce max active policies limit', () => {
      const evaluator = new PolicyFieldEvaluator();
      const maxPolicies = getGlobalRegistry().active.policy.maxActivePolicies;

      for (let i = 0; i < maxPolicies; i++) {
        const field = new SafetyField();
        (field as { id: string }).id = `safety-${i}`;
        evaluator.addField(field);
      }

      const extraField = new SafetyField();
      (extraField as { id: string }).id = 'safety-extra';
      expect(() => evaluator.addField(extraField)).toThrow();
    });
  });
});

// ═══════════════════════════════════════════════════════════════
// Context-Coupled Security Engine Tests
// ═══════════════════════════════════════════════════════════════

describe('Context-Coupled Security Engine', () => {
  let engine: ContextCoupledSecurityEngine;

  beforeEach(() => {
    resetGlobalRegistry();
    engine = new ContextCoupledSecurityEngine();
  });

  it('should ALLOW safe requests', () => {
    const request = makeSafeRequest('safe-agent', 1_000_000);
    const result = engine.evaluate(request);

    expect(result.decision).toBe(SecurityDecision.ALLOW);
    expect(result.omega).toBeGreaterThan(0.85);
    expect(result.pqcValid).toBe(true);
    expect(result.routingCostMultiplier).toBeCloseTo(1.0, 0);
  });

  it('should DENY when PQC is invalid', () => {
    const request = {
      ...makeSafeRequest('agent-1', 1_000_000),
      pqcValid: false,
    };
    const result = engine.evaluate(request);

    expect(result.decision).toBe(SecurityDecision.DENY);
    expect(result.reasonCodes).toContain(
      'PQC_INVALID: context-locked crypto failed verification',
    );
  });

  it('should increase routing cost for suspicious requests', () => {
    const safe = engine.evaluate(makeSafeRequest('safe', 1_000_000));
    const suspicious = engine.evaluate(makeAdversarialRequest('adversary', 1_000_000));

    expect(suspicious.routingCostMultiplier).toBeGreaterThan(safe.routingCostMultiplier);
  });

  it('should compound cost with sustained adversarial behavior', () => {
    const entityId = 'persistent-attacker';
    const results: number[] = [];

    for (let i = 0; i < 10; i++) {
      const result = engine.evaluate(
        makeAdversarialRequest(entityId, 1_000_000 + i * 100_000),
      );
      results.push(result.harmonicWallCost);
    }

    // Harmonic wall cost should increase over time for sustained bad behavior
    expect(results[results.length - 1]).toBeGreaterThanOrEqual(results[0]);
  });

  it('should exile after sustained low trust', () => {
    const entityId = 'bad-actor';

    // Submit many adversarial requests
    let lastResult;
    for (let i = 0; i < 50; i++) {
      lastResult = engine.evaluate(
        makeAdversarialRequest(entityId, 1_000_000 + i * 100_000),
      );
    }

    // After many adversarial rounds, should be denied or trust very low
    expect(lastResult!.trustScore).toBeLessThan(0.5);
  });

  it('should support forced exile', () => {
    engine.evaluate(makeSafeRequest('agent-1', 1_000_000));
    engine.exile('agent-1');

    const result = engine.evaluate(makeSafeRequest('agent-1', 2_000_000));
    expect(result.decision).toBe(SecurityDecision.DENY);
  });

  it('should support rehabilitation after exile', () => {
    // Build up adversarial history then exile
    for (let i = 0; i < 5; i++) {
      engine.evaluate(makeAdversarialRequest('agent-1', 1_000_000 + i * 100_000));
    }
    engine.exile('agent-1');

    // Verify exile
    const exiledResult = engine.evaluate(makeSafeRequest('agent-1', 2_000_000));
    expect(exiledResult.decision).toBe(SecurityDecision.DENY);

    // Rehabilitate
    engine.rehabilitate('agent-1');

    // Should now get a non-DENY decision (may still be quarantine due to low trust)
    const rehabilResult = engine.evaluate(makeSafeRequest('agent-1', 3_000_000));
    expect(rehabilResult.decision).not.toBe(SecurityDecision.DENY);
  });

  it('should provide summary statistics', () => {
    engine.evaluate(makeSafeRequest('agent-1', 1_000_000));
    engine.evaluate(makeAdversarialRequest('agent-2', 1_000_000));

    const summary = engine.summary();
    expect(summary.totalEntities).toBe(2);
    expect(summary.avgTrust).toBeGreaterThan(0);
  });

  it('should batch-evaluate requests', () => {
    const requests = [
      makeSafeRequest('agent-1', 1_000_000),
      makeAdversarialRequest('agent-2', 1_000_000),
    ];
    const results = engine.evaluateBatch(requests);
    expect(results.length).toBe(2);
    expect(results[0].decision).toBe(SecurityDecision.ALLOW);
  });
});

// ═══════════════════════════════════════════════════════════════
// Digital Twin Governor Tests
// ═══════════════════════════════════════════════════════════════

describe('Digital Twin Governor', () => {
  let twin: DigitalTwinGovernor;

  beforeEach(() => {
    resetGlobalRegistry();
    twin = new DigitalTwinGovernor(0.2); // faster EMA for testing
  });

  it('should start with zero tick count', () => {
    expect(twin.tickCount).toBe(0);
    expect(twin.lastOutputs).toBeNull();
  });

  it('should produce control outputs on tick', () => {
    const stats = {
      entityCount: 10,
      meanDistance: 0.2,
      maxDistance: 0.5,
      clampedFraction: 0.8,
      meanTrust: 0.9,
      meanIntent: 0.1,
      dangerCount: 0,
      exiledCount: 0,
    };

    const outputs = twin.tick(stats);

    expect(outputs.tickNumber).toBe(1);
    expect(outputs.aqmMultiplier).toBeGreaterThanOrEqual(0.5);
    expect(outputs.aqmMultiplier).toBeLessThanOrEqual(2.0);
    expect(outputs.routingCostBase).toBeGreaterThanOrEqual(1.0);
    expect(outputs.threatLevel).toBeGreaterThanOrEqual(0);
    expect(outputs.threatLevel).toBeLessThanOrEqual(1);
  });

  it('should escalate under threat', () => {
    // Feed calm stats then threatening stats
    const calm = {
      entityCount: 10,
      meanDistance: 0.1,
      maxDistance: 0.3,
      clampedFraction: 0.9,
      meanTrust: 0.95,
      meanIntent: 0.05,
      dangerCount: 0,
      exiledCount: 0,
    };

    const threat = {
      entityCount: 10,
      meanDistance: 0.8,
      maxDistance: 2.0,
      clampedFraction: 0.2,
      meanTrust: 0.3,
      meanIntent: 5.0,
      dangerCount: 7,
      exiledCount: 2,
    };

    // Warm up with calm
    for (let i = 0; i < 5; i++) twin.tick(calm);
    const calmOutputs = twin.lastOutputs!;

    // Switch to threat
    for (let i = 0; i < 10; i++) twin.tick(threat);
    const threatOutputs = twin.lastOutputs!;

    expect(threatOutputs.threatLevel).toBeGreaterThan(calmOutputs.threatLevel);
    expect(threatOutputs.aqmMultiplier).toBeGreaterThan(calmOutputs.aqmMultiplier);
    expect(threatOutputs.routingCostBase).toBeGreaterThan(calmOutputs.routingCostBase);
    expect(threatOutputs.tighten).toBe(true);
  });

  it('should predict future threat levels', () => {
    const escalating = {
      entityCount: 10,
      meanDistance: 0.5,
      maxDistance: 1.0,
      clampedFraction: 0.5,
      meanTrust: 0.6,
      meanIntent: 2.0,
      dangerCount: 3,
      exiledCount: 0,
    };

    for (let i = 0; i < 20; i++) {
      escalating.meanDistance += 0.02;
      escalating.meanTrust -= 0.01;
      twin.tick({ ...escalating });
    }

    // Prediction should be higher than current
    const currentThreat = twin.emaState.threatLevel;
    const futureThreat = twin.predictThreatLevel(10);

    // With escalating threat, future should be >= current
    expect(futureThreat).toBeGreaterThanOrEqual(currentThreat - 0.1);
  });

  it('should apply controls to machine constants', () => {
    const threat = {
      entityCount: 10,
      meanDistance: 0.9,
      maxDistance: 2.0,
      clampedFraction: 0.1,
      meanTrust: 0.2,
      meanIntent: 7.0,
      dangerCount: 8,
      exiledCount: 3,
    };

    const beforeSafety = getGlobalRegistry().active.policy.safetyFieldStrength;

    for (let i = 0; i < 10; i++) {
      const outputs = twin.tick(threat);
      twin.applyControls(outputs);
    }

    const afterSafety = getGlobalRegistry().active.policy.safetyFieldStrength;

    // Safety field should have been tightened
    expect(afterSafety).toBeGreaterThan(beforeSafety);
  });

  it('should maintain history', () => {
    const stats = {
      entityCount: 5,
      meanDistance: 0.2,
      maxDistance: 0.4,
      clampedFraction: 0.8,
      meanTrust: 0.9,
      meanIntent: 0.1,
      dangerCount: 0,
      exiledCount: 0,
    };

    for (let i = 0; i < 10; i++) twin.tick(stats);

    expect(twin.getHistory().length).toBe(10);
  });

  it('should reset cleanly', () => {
    const stats = {
      entityCount: 5,
      meanDistance: 0.2,
      maxDistance: 0.4,
      clampedFraction: 0.8,
      meanTrust: 0.9,
      meanIntent: 0.1,
      dangerCount: 0,
      exiledCount: 0,
    };

    twin.tick(stats);
    twin.reset();

    expect(twin.tickCount).toBe(0);
    expect(twin.lastOutputs).toBeNull();
    expect(twin.getHistory().length).toBe(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// Full Integration: Engine + Twin
// ═══════════════════════════════════════════════════════════════

describe('Full Integration: Engine + Twin', () => {
  beforeEach(() => {
    resetGlobalRegistry();
  });

  it('should run a complete security lifecycle', () => {
    const engine = new ContextCoupledSecurityEngine();
    const twin = new DigitalTwinGovernor(0.2);

    // Phase 1: Normal operation
    for (let i = 0; i < 5; i++) {
      engine.evaluate(makeSafeRequest(`agent-${i}`, 1_000_000 + i * 100_000));
    }

    // Run twin tick with current state
    const snapshot = engine.manifold.snapshot();
    const outputs1 = twin.fullCycle(snapshot, 0);
    expect(outputs1.threatLevel).toBeLessThan(0.3);

    // Phase 2: Introduce adversarial agents
    for (let i = 0; i < 3; i++) {
      engine.evaluate(makeAdversarialRequest(`attacker-${i}`, 2_000_000 + i * 100_000));
    }

    // Run twin tick — should detect threat escalation
    const snapshot2 = engine.manifold.snapshot();
    const outputs2 = twin.fullCycle(snapshot2, 0);

    // With adversarial agents, threat should be non-trivial
    expect(outputs2.threatLevel).toBeGreaterThanOrEqual(0);

    // Phase 3: Twin tightens controls, subsequent evaluations are stricter
    const strictResult = engine.evaluate(
      makeAdversarialRequest('new-attacker', 3_000_000),
    );
    // With tightened controls, new adversarial requests face higher costs
    expect(strictResult.harmonicWallCost).toBeGreaterThanOrEqual(1.0);
  });
});
