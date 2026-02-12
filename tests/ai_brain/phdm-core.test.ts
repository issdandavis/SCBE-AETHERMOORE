/**
 * Tests for PHDM Core Integration
 *
 * Covers:
 * - K₀ derivation from Kyber KEM shared secret
 * - Hamiltonian path HMAC chain integrity
 * - 6D Langues space decomposition (4D intent + 2D temporal)
 * - Geodesic intrusion detection with snap threshold ε
 * - Langues metric cost computation
 * - PHDM → flux state evolution (intrusion penalties)
 * - Numerical false positive rate analysis
 * - PHDM-enabled brain integration pipeline
 *
 * @module tests/ai_brain/phdm-core
 */

import { describe, expect, it, beforeEach } from 'vitest';
import * as crypto from 'crypto';
import {
  PHDMCore,
  DEFAULT_PHDM_CORE_CONFIG,
  deriveK0,
  decomposeLangues,
  brainStateToLangues,
  TONGUE_LABELS,
  INTENT_TONGUES,
  TEMPORAL_TONGUES,
  type K0DerivationParams,
  type PHDMMonitorResult,
} from '../../src/ai_brain/phdm-core';
import { FluxStateManager } from '../../src/ai_brain/flux-states';
import { BrainIntegrationPipeline } from '../../src/ai_brain/brain-integration';
import {
  generateTrajectory,
  generateMixedBatch,
  AGENT_PROFILES,
  type SimulationConfig,
} from '../../src/ai_brain/trajectory-simulator';
import { computeCentroid, CANONICAL_POLYHEDRA, type Point6D } from '../../src/harmonic/phdm';

const defaultSimConfig: SimulationConfig = {
  steps: 50,
  tongueIndex: 0,
  seed: 42,
};

// ═══════════════════════════════════════════════════════════════
// Test Helpers
// ═══════════════════════════════════════════════════════════════

function makeSharedSecret(): Uint8Array {
  return crypto.randomBytes(32);
}

function makeK0Params(overrides: Partial<K0DerivationParams> = {}): K0DerivationParams {
  return {
    sharedSecret: makeSharedSecret(),
    intentFingerprint: 'agent-test-001',
    epoch: 1000,
    ...overrides,
  };
}

function makeDeterministicParams(): K0DerivationParams {
  const ss = Buffer.alloc(32);
  Buffer.from('deterministic-shared-secret-32b!').copy(ss);
  return {
    sharedSecret: new Uint8Array(ss),
    intentFingerprint: 'test-agent',
    epoch: 42,
  };
}

// ═══════════════════════════════════════════════════════════════
// K₀ Derivation Tests
// ═══════════════════════════════════════════════════════════════

describe('K₀ Derivation from Kyber KEM', () => {
  it('should produce 32-byte K₀', () => {
    const k0 = deriveK0(makeK0Params());
    expect(k0).toHaveLength(32);
    expect(Buffer.isBuffer(k0)).toBe(true);
  });

  it('should be deterministic for same inputs', () => {
    const params = makeDeterministicParams();
    const k0a = deriveK0(params);
    const k0b = deriveK0(params);
    expect(k0a.equals(k0b)).toBe(true);
  });

  it('should differ with different shared secrets', () => {
    const params1 = makeK0Params({ sharedSecret: crypto.randomBytes(32) });
    const params2 = makeK0Params({ sharedSecret: crypto.randomBytes(32) });
    const k0a = deriveK0(params1);
    const k0b = deriveK0(params2);
    expect(k0a.equals(k0b)).toBe(false);
  });

  it('should differ with different intent fingerprints', () => {
    const ss = makeSharedSecret();
    const k0a = deriveK0({ sharedSecret: ss, intentFingerprint: 'agent-A', epoch: 1 });
    const k0b = deriveK0({ sharedSecret: ss, intentFingerprint: 'agent-B', epoch: 1 });
    expect(k0a.equals(k0b)).toBe(false);
  });

  it('should differ with different epochs', () => {
    const ss = makeSharedSecret();
    const k0a = deriveK0({ sharedSecret: ss, intentFingerprint: 'agent', epoch: 1 });
    const k0b = deriveK0({ sharedSecret: ss, intentFingerprint: 'agent', epoch: 2 });
    expect(k0a.equals(k0b)).toBe(false);
  });

  it('should handle epoch 0', () => {
    const k0 = deriveK0(makeK0Params({ epoch: 0 }));
    expect(k0).toHaveLength(32);
  });

  it('should handle large epoch values', () => {
    const k0 = deriveK0(makeK0Params({ epoch: Number.MAX_SAFE_INTEGER }));
    expect(k0).toHaveLength(32);
  });
});

// ═══════════════════════════════════════════════════════════════
// 6D Langues Space Decomposition Tests
// ═══════════════════════════════════════════════════════════════

describe('6D Langues Space Decomposition', () => {
  it('should have correct tongue labels', () => {
    expect(TONGUE_LABELS).toEqual(['KO', 'AV', 'RU', 'CA', 'UM', 'DR']);
    expect(INTENT_TONGUES).toEqual(['KO', 'AV', 'RU', 'CA']);
    expect(TEMPORAL_TONGUES).toEqual(['UM', 'DR']);
  });

  it('should decompose 6D point into 4D intent + 2D temporal', () => {
    const point: Point6D = { x1: 0.9, x2: 0.8, x3: 0.7, x4: 0.6, x5: 0.5, x6: 0.4 };
    const decomp = decomposeLangues(point);

    expect(decomp.intent).toEqual([0.9, 0.8, 0.7, 0.6]);
    expect(decomp.temporal).toEqual([0.5, 0.4]);
    expect(decomp.full).toEqual(point);
  });

  it('should map 21D brain state to 6D Langues space', () => {
    const state21D = [0.9, 0.85, 0.8, 0.75, 0.7, 0.65, ...new Array(15).fill(0)];
    const langues = brainStateToLangues(state21D);

    expect(langues.x1).toBe(0.9);   // KO: deviceTrust
    expect(langues.x2).toBe(0.85);  // AV: locationTrust
    expect(langues.x3).toBe(0.8);   // RU: networkTrust
    expect(langues.x4).toBe(0.75);  // CA: behaviorScore
    expect(langues.x5).toBe(0.7);   // UM: timeOfDay
    expect(langues.x6).toBe(0.65);  // DR: intentAlignment
  });

  it('should throw for state with fewer than 6 dimensions', () => {
    expect(() => brainStateToLangues([0.5, 0.5])).toThrow('Expected at least 6 dimensions');
  });

  it('should decompose mapped state correctly', () => {
    const state21D = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, ...new Array(15).fill(0)];
    const langues = brainStateToLangues(state21D);
    const decomp = decomposeLangues(langues);

    expect(decomp.intent).toEqual([0.1, 0.2, 0.3, 0.4]);
    expect(decomp.temporal).toEqual([0.5, 0.6]);
  });
});

// ═══════════════════════════════════════════════════════════════
// PHDM Core Initialization Tests
// ═══════════════════════════════════════════════════════════════

describe('PHDMCore Initialization', () => {
  it('should initialize from Kyber KEM parameters', () => {
    const core = new PHDMCore();
    core.initializeFromKyber(makeDeterministicParams());

    expect(core.getK0()).not.toBeNull();
    expect(core.getK0()!).toHaveLength(32);
  });

  it('should initialize with raw master key', () => {
    const core = new PHDMCore();
    const key = Buffer.from('phdm-test-master-key-32-bytes!!A');
    core.initializeWithKey(key);

    expect(core.getK0()!.equals(key)).toBe(true);
  });

  it('should have 16 canonical polyhedra', () => {
    const core = new PHDMCore();
    expect(core.getPolyhedra()).toHaveLength(16);
  });

  it('should verify HMAC chain integrity after initialization', () => {
    const core = new PHDMCore();
    core.initializeFromKyber(makeDeterministicParams());
    expect(core.verifyChainIntegrity()).toBe(true);
  });

  it('should produce deterministic Hamiltonian path keys', () => {
    const params = makeDeterministicParams();
    const core1 = new PHDMCore();
    const core2 = new PHDMCore();

    core1.initializeFromKyber(params);
    core2.initializeFromKyber(params);

    // Same K₀ → same Hamiltonian path keys
    expect(core1.getK0()!.equals(core2.getK0()!)).toBe(true);
    for (let i = 0; i <= 16; i++) {
      const key1 = core1.getPathKey(i);
      const key2 = core2.getPathKey(i);
      expect(key1).not.toBeNull();
      expect(key1!.equals(key2!)).toBe(true);
    }
  });

  it('should throw if monitoring without initialization', () => {
    const core = new PHDMCore();
    const state = new Array(21).fill(0.5);
    expect(() => core.monitor(state, 0.5)).toThrow('not initialized');
  });
});

// ═══════════════════════════════════════════════════════════════
// Geodesic Monitoring Tests
// ═══════════════════════════════════════════════════════════════

describe('Geodesic Monitoring', () => {
  let core: PHDMCore;

  beforeEach(() => {
    core = new PHDMCore();
    core.initializeWithKey(Buffer.from('geodesic-test-key-32-bytes-long!'));
  });

  it('should monitor a safe state on the geodesic', () => {
    // Get the centroid of the first polyhedron as a "safe" state
    const centroid = computeCentroid(CANONICAL_POLYHEDRA[0]);
    const state21D = [centroid.x1, centroid.x2, centroid.x3, centroid.x4, centroid.x5, centroid.x6,
      ...new Array(15).fill(0)];

    const result = core.monitor(state21D, 0);

    expect(result.intrusion).toBeDefined();
    expect(result.langues).toBeDefined();
    expect(result.languesCost).toBeGreaterThan(0);
    expect(result.hamiltonianStep).toBe(0);
    expect(result.currentPolyhedron).toBe('Tetrahedron');
    expect(result.keyFingerprint).toHaveLength(16);
    expect(typeof result.phdmEscalation).toBe('boolean');
  });

  it('should produce low deviation for on-geodesic states', () => {
    const centroid = computeCentroid(CANONICAL_POLYHEDRA[0]);
    const state21D = [centroid.x1, centroid.x2, centroid.x3, centroid.x4, centroid.x5, centroid.x6,
      ...new Array(15).fill(0)];

    const result = core.monitor(state21D, 0);
    expect(result.intrusion.deviation).toBeLessThan(0.05);
  });

  it('should detect intrusion for off-geodesic states', () => {
    // Create a state far from the geodesic
    const state21D = [5.0, 5.0, 5.0, 5.0, 5.0, 5.0, ...new Array(15).fill(0)];

    const result = core.monitor(state21D, 0);
    expect(result.intrusion.isIntrusion).toBe(true);
    expect(result.intrusion.deviation).toBeGreaterThan(0.1);
  });

  it('should track intrusion count over multiple monitors', () => {
    const badState = [5.0, 5.0, 5.0, 5.0, 5.0, 5.0, ...new Array(15).fill(0)];

    for (let i = 0; i < 6; i++) {
      core.monitor(badState, i / 15);
    }

    const stats = core.getStats();
    expect(stats.intrusionCount).toBeGreaterThan(0);
    expect(stats.totalSteps).toBe(6);
    expect(stats.intrusionRate).toBeGreaterThan(0);
  });

  it('should trigger PHDM escalation after exceeding max intrusions', () => {
    const badState = [5.0, 5.0, 5.0, 5.0, 5.0, 5.0, ...new Array(15).fill(0)];

    let escalated = false;
    for (let i = 0; i < 10; i++) {
      const result = core.monitor(badState, i / 15);
      if (result.phdmEscalation) {
        escalated = true;
        break;
      }
    }
    expect(escalated).toBe(true);
  });

  it('should build rhythm pattern as 1s and 0s', () => {
    const centroid = computeCentroid(CANONICAL_POLYHEDRA[0]);
    const safeState = [centroid.x1, centroid.x2, centroid.x3, centroid.x4, centroid.x5, centroid.x6,
      ...new Array(15).fill(0)];

    core.monitor(safeState, 0);
    core.monitor(safeState, 0.05);
    core.monitor(safeState, 0.1);

    const stats = core.getStats();
    expect(stats.rhythmPattern).toMatch(/^[01]+$/);
    expect(stats.rhythmPattern.length).toBe(3);
  });

  it('should track Hamiltonian step as t progresses', () => {
    const state = new Array(21).fill(0.1);

    const r1 = core.monitor(state, 0);
    expect(r1.hamiltonianStep).toBe(0);

    const r2 = core.monitor(state, 0.5);
    expect(r2.hamiltonianStep).toBe(8); // floor(0.5 * 16)

    const r3 = core.monitor(state, 0.99);
    expect(r3.hamiltonianStep).toBe(15); // clamped to last polyhedron
  });

  it('should include Langues decomposition in monitor result', () => {
    const state21D = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, ...new Array(15).fill(0)];
    const result = core.monitor(state21D, 0.25);

    expect(result.langues.intent).toEqual([0.9, 0.8, 0.7, 0.6]);
    expect(result.langues.temporal).toEqual([0.5, 0.4]);
  });

  it('should reset monitoring while keeping keys', () => {
    const state = [5.0, 5.0, 5.0, 5.0, 5.0, 5.0, ...new Array(15).fill(0)];
    core.monitor(state, 0.1);
    core.monitor(state, 0.2);

    const statsBefore = core.getStats();
    expect(statsBefore.totalSteps).toBe(2);
    expect(statsBefore.chainIntact).toBe(true);

    core.resetMonitoring();

    const statsAfter = core.getStats();
    expect(statsAfter.totalSteps).toBe(0);
    expect(statsAfter.intrusionCount).toBe(0);
    expect(statsAfter.chainIntact).toBe(true); // keys preserved
  });
});

// ═══════════════════════════════════════════════════════════════
// Langues Metric Cost Tests
// ═══════════════════════════════════════════════════════════════

describe('Langues Metric Cost', () => {
  let core: PHDMCore;

  beforeEach(() => {
    core = new PHDMCore();
    core.initializeWithKey(Buffer.from('langues-test-key-32-bytes-long!!'));
  });

  it('should compute positive cost for any input', () => {
    const point: Point6D = { x1: 0, x2: 0, x3: 0, x4: 0, x5: 0, x6: 0 };
    const cost = core.computeLanguesCost(point, 0);
    expect(cost).toBeGreaterThan(0);
  });

  it('should increase cost for higher deviation values', () => {
    const lowPoint: Point6D = { x1: 0.1, x2: 0.1, x3: 0.1, x4: 0.1, x5: 0.1, x6: 0.1 };
    const highPoint: Point6D = { x1: 2.0, x2: 2.0, x3: 2.0, x4: 2.0, x5: 2.0, x6: 2.0 };

    const lowCost = core.computeLanguesCost(lowPoint, 0);
    const highCost = core.computeLanguesCost(highPoint, 0);

    expect(highCost).toBeGreaterThan(lowCost);
  });

  it('should evaluate risk decisions based on thresholds', () => {
    expect(core.evaluateLanguesRisk(0.5)).toBe('ALLOW');
    expect(core.evaluateLanguesRisk(5.0)).toBe('QUARANTINE');
    expect(core.evaluateLanguesRisk(15.0)).toBe('DENY');
  });

  it('should include langues cost and decision in monitor result', () => {
    const state21D = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, ...new Array(15).fill(0)];
    const result = core.monitor(state21D, 0.3);

    expect(result.languesCost).toBeGreaterThan(0);
    expect(['ALLOW', 'QUARANTINE', 'DENY']).toContain(result.languesDecision);
  });
});

// ═══════════════════════════════════════════════════════════════
// PHDM → Flux State Integration Tests
// ═══════════════════════════════════════════════════════════════

describe('PHDM → Flux Integration', () => {
  let core: PHDMCore;
  let fluxManager: FluxStateManager;

  beforeEach(() => {
    core = new PHDMCore();
    core.initializeWithKey(Buffer.from('flux-integ-test-key-32-bytes-ok!'));
    fluxManager = new FluxStateManager();
  });

  it('should give high flux for on-geodesic states', () => {
    const centroid = computeCentroid(CANONICAL_POLYHEDRA[0]);
    const state21D = [centroid.x1, centroid.x2, centroid.x3, centroid.x4, centroid.x5, centroid.x6,
      ...new Array(15).fill(0)];

    const result = core.monitor(state21D, 0);
    const flux = core.applyToFlux(fluxManager, 'agent-safe', result, 'healthy');

    expect(flux.nu).toBeGreaterThan(0.5);
    expect(flux.state === 'POLLY' || flux.state === 'QUASI').toBe(true);
  });

  it('should penalize flux for intrusion states', () => {
    // Off-geodesic state
    const state21D = [5.0, 5.0, 5.0, 5.0, 5.0, 5.0, ...new Array(15).fill(0)];
    const result = core.monitor(state21D, 0.1);

    expect(result.intrusion.isIntrusion).toBe(true);

    const flux = core.applyToFlux(fluxManager, 'agent-bad', result, 'healthy');
    expect(flux.nu).toBeLessThan(0.5);
  });

  it('should force COLLAPSED flux on PHDM escalation', () => {
    const badState = [5.0, 5.0, 5.0, 5.0, 5.0, 5.0, ...new Array(15).fill(0)];

    // Drive intrusion count past maxIntrusionsBeforeDeny (default: 5)
    let phdmResult: PHDMMonitorResult | undefined;
    for (let i = 0; i < 6; i++) {
      phdmResult = core.monitor(badState, i / 15);
    }

    expect(phdmResult!.phdmEscalation).toBe(true);

    const flux = core.applyToFlux(fluxManager, 'agent-escalated', phdmResult!, 'healthy');
    // phdmTrust = 0 → flux evolves toward 0
    expect(flux.nu).toBeLessThan(0.1);
  });

  it('should degrade flux progressively with repeated intrusions', () => {
    const badState = [3.0, 3.0, 3.0, 3.0, 3.0, 3.0, ...new Array(15).fill(0)];

    const fluxValues: number[] = [];
    for (let i = 0; i < 4; i++) {
      const result = core.monitor(badState, i / 15);
      const flux = core.applyToFlux(fluxManager, 'agent-degrade', result, 'healthy');
      fluxValues.push(flux.nu);
    }

    // Each step should push flux lower (or stay low)
    for (let i = 1; i < fluxValues.length; i++) {
      expect(fluxValues[i]).toBeLessThanOrEqual(fluxValues[i - 1] + 0.01); // small tolerance
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Numerical False Positive Rate Tests
// ═══════════════════════════════════════════════════════════════

describe('PHDM Snap Threshold False Positive Analysis', () => {
  it('should have low deviation-based FPR for on-geodesic valid trajectories', () => {
    const snapThreshold = 0.1;
    const core = new PHDMCore({ snapThreshold, curvatureThreshold: 0.5 });
    core.initializeWithKey(Buffer.from('fpr-test-key-32-bytes-very-long!'));

    let falseDeviations = 0;
    const totalSteps = 16;

    // Walk exactly along the geodesic (centroids of each polyhedron)
    for (let i = 0; i < totalSteps; i++) {
      const t = i / (totalSteps - 1);
      const centroid = computeCentroid(CANONICAL_POLYHEDRA[i]);
      const state21D = [centroid.x1, centroid.x2, centroid.x3, centroid.x4, centroid.x5, centroid.x6,
        ...new Array(15).fill(0)];

      const result = core.monitor(state21D, t);
      // Check deviation only — curvature reflects the geodesic's own shape,
      // not the agent's distance from it
      if (result.intrusion.deviation > snapThreshold) {
        falseDeviations++;
      }
    }

    // Centroids are on the spline → deviation should be very small
    // Allow up to 2 false positives from edge effects at endpoints
    const fpr = falseDeviations / totalSteps;
    expect(fpr).toBeLessThan(0.2);
  });

  it('should have valid mean deviation for safe trajectories', () => {
    const core = new PHDMCore();
    core.initializeWithKey(Buffer.from('mean-dev-test-key-32-bytes-long!'));

    const deviations: number[] = [];

    for (let i = 0; i < 16; i++) {
      const t = i / 15;
      const centroid = computeCentroid(CANONICAL_POLYHEDRA[i]);
      const state21D = [centroid.x1, centroid.x2, centroid.x3, centroid.x4, centroid.x5, centroid.x6,
        ...new Array(15).fill(0)];

      const result = core.monitor(state21D, t);
      deviations.push(result.intrusion.deviation);
    }

    const meanDeviation = deviations.reduce((a, b) => a + b, 0) / deviations.length;
    // Mean deviation should be small for on-geodesic traversal
    expect(meanDeviation).toBeLessThan(0.5);
  });

  it('should have 100% detection rate for large deviations', () => {
    const core = new PHDMCore({ snapThreshold: 0.1 });
    core.initializeWithKey(Buffer.from('tpr-test-key-32-bytes-really-ok!'));

    let detected = 0;
    const totalSteps = 16;

    for (let i = 0; i < totalSteps; i++) {
      const t = i / (totalSteps - 1);
      // State far from any geodesic point
      const state21D = [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, ...new Array(15).fill(0)];

      const result = core.monitor(state21D, t);
      if (result.intrusion.isIntrusion) {
        detected++;
      }
    }

    expect(detected).toBe(totalSteps);
  });
});

// ═══════════════════════════════════════════════════════════════
// Hamiltonian Path Traversal Timing Tests
// ═══════════════════════════════════════════════════════════════

describe('Hamiltonian Path Traversal', () => {
  it('should traverse all 16 polyhedra as t goes 0→1', () => {
    const core = new PHDMCore();
    core.initializeWithKey(Buffer.from('traversal-test-key-32-bytes-ok!!'));

    const visitedPolyhedra = new Set<string>();
    const state = new Array(21).fill(0.1);

    // Sample at 17 points to cover all 16 steps
    for (let i = 0; i <= 16; i++) {
      const t = Math.min(i / 16, 0.999);
      const result = core.monitor(state, t);
      visitedPolyhedra.add(result.currentPolyhedron);
    }

    expect(visitedPolyhedra.size).toBe(16);
  });

  it('should produce unique key fingerprints per step', () => {
    const core = new PHDMCore();
    core.initializeWithKey(Buffer.from('keyfp-test-key-32-bytes-are-ok!!'));

    const fingerprints = new Set<string>();
    const state = new Array(21).fill(0.1);

    for (let i = 0; i < 16; i++) {
      const t = i / 16;
      const result = core.monitor(state, t);
      fingerprints.add(result.keyFingerprint);
    }

    // Each step has a unique HMAC-derived key
    expect(fingerprints.size).toBe(16);
  });

  it('should complete Hamiltonian traversal in reasonable time', () => {
    const core = new PHDMCore();
    core.initializeWithKey(Buffer.from('timing-test-key-32-bytes-number!'));

    const state = new Array(21).fill(0.5);
    const start = Date.now();

    for (let i = 0; i < 100; i++) {
      const t = (i % 16) / 16;
      core.monitor(state, t);
    }

    const elapsed = Date.now() - start;
    // 100 monitor calls should be fast (under 1 second)
    expect(elapsed).toBeLessThan(1000);
  });
});

// ═══════════════════════════════════════════════════════════════
// PHDM-Enabled Brain Integration Pipeline Tests
// ═══════════════════════════════════════════════════════════════

describe('PHDM-Enabled Brain Integration Pipeline', () => {
  it('should process agents with PHDM enabled', () => {
    const pipeline = new BrainIntegrationPipeline({
      enablePHDM: true,
    });

    expect(pipeline.phdmCore).not.toBeNull();

    const trajectory = generateTrajectory(
      'honest-phdm-001', AGENT_PROFILES.honest, { ...defaultSimConfig, seed: 999 }
    );
    const assessment = pipeline.processAgent(trajectory);

    expect(assessment.phdmResult).toBeDefined();
    expect(assessment.phdmResult!.langues).toBeDefined();
    expect(assessment.phdmResult!.languesCost).toBeGreaterThan(0);
    expect(assessment.phdmResult!.currentPolyhedron).toBeDefined();
  });

  it('should include PHDM result for malicious agents', () => {
    const pipeline = new BrainIntegrationPipeline({
      enablePHDM: true,
    });

    const trajectory = generateTrajectory(
      'mal-phdm-001', AGENT_PROFILES.malicious, { ...defaultSimConfig, seed: 888 }
    );
    const assessment = pipeline.processAgent(trajectory);

    expect(assessment.phdmResult).toBeDefined();
    // Malicious agents should have higher deviation
    expect(assessment.phdmResult!.intrusion.deviation).toBeGreaterThan(0);
  });

  it('should not have PHDM result when disabled', () => {
    const pipeline = new BrainIntegrationPipeline({
      enablePHDM: false,
    });

    expect(pipeline.phdmCore).toBeNull();

    const trajectory = generateTrajectory(
      'honest-no-phdm', AGENT_PROFILES.honest, { ...defaultSimConfig, seed: 777 }
    );
    const assessment = pipeline.processAgent(trajectory);

    expect(assessment.phdmResult).toBeUndefined();
  });

  it('should initialize PHDM with Kyber params when provided', () => {
    const params = makeDeterministicParams();
    const pipeline = new BrainIntegrationPipeline({
      enablePHDM: true,
      phdmKyberParams: params,
    });

    expect(pipeline.phdmCore).not.toBeNull();
    expect(pipeline.phdmCore!.getK0()).not.toBeNull();
    expect(pipeline.phdmCore!.verifyChainIntegrity()).toBe(true);
  });

  it('should process a batch trial with PHDM enabled', () => {
    const pipeline = new BrainIntegrationPipeline({
      enablePHDM: true,
    });

    const batch = generateMixedBatch(10, { ...defaultSimConfig, seed: 666 });
    const result = pipeline.processTrial(batch, 0);

    expect(result.assessments.length).toBe(10);
    // All assessments should have PHDM results
    for (const a of result.assessments) {
      expect(a.phdmResult).toBeDefined();
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Edge Cases and Custom Configuration Tests
// ═══════════════════════════════════════════════════════════════

describe('PHDM Core Edge Cases', () => {
  it('should handle custom snap threshold', () => {
    const core = new PHDMCore({ snapThreshold: 0.01 });
    core.initializeWithKey(Buffer.from('snap-edge-test-key-32-bytes-now!'));

    // Even the centroid will exceed a very tight threshold
    const state = new Array(21).fill(0.5);
    const result = core.monitor(state, 0.5);

    expect(result.intrusion).toBeDefined();
  });

  it('should handle custom intrusion rate threshold', () => {
    const core = new PHDMCore({ intrusionRateThreshold: 0.1 });
    core.initializeWithKey(Buffer.from('rate-edge-test-key-32-bytes-ok!!'));

    const badState = [5.0, 5.0, 5.0, 5.0, 5.0, 5.0, ...new Array(15).fill(0)];

    // With low threshold, escalation triggers faster
    let escalationStep = -1;
    for (let i = 0; i < 10; i++) {
      const result = core.monitor(badState, i / 15);
      if (result.phdmEscalation && escalationStep === -1) {
        escalationStep = i;
      }
    }

    expect(escalationStep).toBeGreaterThanOrEqual(0);
    expect(escalationStep).toBeLessThan(10);
  });

  it('should handle Langues risk thresholds customization', () => {
    const core = new PHDMCore({ languesRiskThresholds: [0.5, 2.0] });
    core.initializeWithKey(Buffer.from('risk-edge-test-key-32-bytes-ok!!'));

    expect(core.evaluateLanguesRisk(0.3)).toBe('ALLOW');
    expect(core.evaluateLanguesRisk(1.0)).toBe('QUARANTINE');
    expect(core.evaluateLanguesRisk(3.0)).toBe('DENY');
  });

  it('should have consistent stats across reset cycles', () => {
    const core = new PHDMCore();
    core.initializeWithKey(Buffer.from('reset-cycle-test-key-32-bytes!!A'));

    const state = [5.0, 5.0, 5.0, 5.0, 5.0, 5.0, ...new Array(15).fill(0)];
    core.monitor(state, 0.1);
    core.monitor(state, 0.2);

    core.resetMonitoring();

    const stats = core.getStats();
    expect(stats.totalSteps).toBe(0);
    expect(stats.intrusionCount).toBe(0);
    expect(stats.rhythmPattern).toBe('');
    expect(stats.chainIntact).toBe(true);
  });
});
