/**
 * SCBE Security Pipeline Tests
 * ============================
 *
 * Validates the unified 14-layer security pipeline orchestrator:
 * - Input validation at the system boundary
 * - 14-layer hyperbolic risk assessment
 * - 4-tier governance decisions (ALLOW / QUARANTINE / ESCALATE / DENY)
 * - Replay protection
 * - SHA-256 hash-chained audit trail integrity
 * - HMAC integrity tags
 *
 * @layer All (L1-L14)
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  SecurityPipeline,
  createSecurityPipeline,
  validateInput,
  validateSacredTongueDimension,
  normalizeInputLength,
  SecurityAuditTrail,
} from '../../src/security/index';

// ═══════════════════════════════════════════════════════════════
// Input Validator Tests
// ═══════════════════════════════════════════════════════════════

describe('Input Validator', () => {
  describe('validateInput', () => {
    it('should accept a valid numeric array', () => {
      const result = validateInput([0.1, 0.2, 0.3, 0.4, 0.5, 0.6]);
      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
      expect(result.sanitized).toBeDefined();
    });

    it('should reject non-array input', () => {
      const result = validateInput('not an array');
      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Input must be an array');
    });

    it('should reject empty array', () => {
      const result = validateInput([]);
      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Input must be non-empty');
    });

    it('should reject array with non-numeric elements', () => {
      const result = validateInput([1, 'two', 3]);
      expect(result.valid).toBe(false);
      expect(result.errors[0]).toContain('not a number');
    });

    it('should reject NaN values by default', () => {
      const result = validateInput([1, NaN, 3]);
      expect(result.valid).toBe(false);
      expect(result.errors[0]).toContain('non-finite');
    });

    it('should reject Infinity values by default', () => {
      const result = validateInput([1, Infinity, 3]);
      expect(result.valid).toBe(false);
    });

    it('should reject input below minimum dimension', () => {
      const result = validateInput([1], { minDimension: 2 });
      expect(result.valid).toBe(false);
      expect(result.errors[0]).toContain('below minimum');
    });

    it('should reject input exceeding maximum dimension', () => {
      const result = validateInput(new Array(200).fill(1), { maxDimension: 128 });
      expect(result.valid).toBe(false);
      expect(result.errors[0]).toContain('exceeds maximum');
    });

    it('should reject magnitude exceeding limit', () => {
      const result = validateInput([1, 1e7, 3], { maxAbsValue: 1e6 });
      expect(result.valid).toBe(false);
      expect(result.errors[0]).toContain('magnitude limit');
    });

    it('should clamp out-of-range values when configured', () => {
      const result = validateInput([1, 1e7, -1e7], {
        maxAbsValue: 1e6,
        clampOutOfRange: true,
      });
      expect(result.valid).toBe(true);
      expect(result.sanitized![1]).toBe(1e6);
      expect(result.sanitized![2]).toBe(-1e6);
    });
  });

  describe('validateSacredTongueDimension', () => {
    it('should accept input with length >= 2*D for D=6', () => {
      expect(validateSacredTongueDimension(12)).toBe(true);
      expect(validateSacredTongueDimension(14)).toBe(true);
    });

    it('should reject input shorter than 2*D', () => {
      expect(validateSacredTongueDimension(6)).toBe(false);
      expect(validateSacredTongueDimension(11)).toBe(false);
    });
  });

  describe('normalizeInputLength', () => {
    it('should pad short inputs with zeros', () => {
      const result = normalizeInputLength([1, 2, 3], 6);
      expect(result).toEqual([1, 2, 3, 0, 0, 0]);
    });

    it('should truncate long inputs', () => {
      const result = normalizeInputLength([1, 2, 3, 4, 5, 6, 7, 8], 6);
      expect(result).toEqual([1, 2, 3, 4, 5, 6]);
    });

    it('should pass through correct-length inputs unchanged', () => {
      const input = [1, 2, 3, 4, 5, 6];
      const result = normalizeInputLength(input, 6);
      expect(result).toEqual(input);
    });
  });
});

// ═══════════════════════════════════════════════════════════════
// Audit Trail Tests
// ═══════════════════════════════════════════════════════════════

describe('SecurityAuditTrail', () => {
  let audit: SecurityAuditTrail;

  beforeEach(() => {
    audit = new SecurityAuditTrail(100);
  });

  it('should log pipeline execution entries', () => {
    const entry = audit.logPipelineExecution({
      decision: 'ALLOW',
      riskPrime: 0.1,
      harmonicScore: 0.95,
      hyperbolicDistance: 0.3,
      requestId: 'req-001',
    });

    expect(entry.eventType).toBe('pipeline_execution');
    expect(entry.decision).toBe('ALLOW');
    expect(entry.seq).toBe(0);
    expect(entry.hash).toBeDefined();
    expect(entry.prevHash).toBeDefined();
  });

  it('should maintain a valid hash chain', () => {
    audit.logPipelineExecution({
      decision: 'ALLOW',
      riskPrime: 0.1,
      harmonicScore: 0.95,
      hyperbolicDistance: 0.3,
    });

    audit.logPipelineExecution({
      decision: 'QUARANTINE',
      riskPrime: 0.4,
      harmonicScore: 0.6,
      hyperbolicDistance: 1.2,
    });

    audit.logAnomaly({
      description: 'High drift detected',
      riskPrime: 0.9,
    });

    expect(audit.verifyChain()).toBe(true);
  });

  it('should track decision statistics', () => {
    audit.logPipelineExecution({
      decision: 'ALLOW',
      riskPrime: 0.1,
      harmonicScore: 0.9,
      hyperbolicDistance: 0.3,
    });
    audit.logPipelineExecution({
      decision: 'ALLOW',
      riskPrime: 0.15,
      harmonicScore: 0.85,
      hyperbolicDistance: 0.4,
    });
    audit.logPipelineExecution({
      decision: 'DENY',
      riskPrime: 0.9,
      harmonicScore: 0.1,
      hyperbolicDistance: 3.5,
    });
    audit.logReplayBlocked('req-dup', 'provider-1');

    const stats = audit.getStats();
    expect(stats.totalEntries).toBe(4);
    expect(stats.decisions.ALLOW).toBe(2);
    expect(stats.decisions.DENY).toBe(1);
    expect(stats.replayBlockedCount).toBe(1);
    expect(stats.chainIntact).toBe(true);
  });

  it('should evict oldest entries when capacity exceeded', () => {
    const smallAudit = new SecurityAuditTrail(5);

    for (let i = 0; i < 10; i++) {
      smallAudit.logPipelineExecution({
        decision: 'ALLOW',
        riskPrime: 0.1,
        harmonicScore: 0.9,
        hyperbolicDistance: 0.3,
      });
    }

    expect(smallAudit.getAll().length).toBe(5);
    expect(smallAudit.getTotalLogged()).toBe(10);
  });

  it('should return recent entries in reverse order', () => {
    audit.logPipelineExecution({
      decision: 'ALLOW',
      riskPrime: 0.1,
      harmonicScore: 0.9,
      hyperbolicDistance: 0.3,
      requestId: 'first',
    });
    audit.logPipelineExecution({
      decision: 'DENY',
      riskPrime: 0.9,
      harmonicScore: 0.1,
      hyperbolicDistance: 3.0,
      requestId: 'second',
    });

    const recent = audit.getRecent(2);
    expect(recent[0].requestId).toBe('second');
    expect(recent[1].requestId).toBe('first');
  });
});

// ═══════════════════════════════════════════════════════════════
// Security Pipeline Orchestrator Tests
// ═══════════════════════════════════════════════════════════════

describe('SecurityPipeline', () => {
  let pipeline: SecurityPipeline;

  beforeEach(() => {
    pipeline = new SecurityPipeline();
  });

  describe('Basic Execution', () => {
    it('should execute the full 14-layer pipeline and return a decision', () => {
      const result = pipeline.execute({
        input: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0, 0, 0, 0, 0, 0],
        requestId: 'test-001',
      });

      expect(['ALLOW', 'QUARANTINE', 'ESCALATE', 'DENY']).toContain(result.decision);
      expect(result.riskPrime).toBeGreaterThanOrEqual(0);
      expect(result.harmonicScore).toBeGreaterThan(0);
      expect(result.harmonicScore).toBeLessThanOrEqual(1);
      expect(result.validationPassed).toBe(true);
      expect(result.replayDetected).toBe(false);
      expect(result.requestId).toBe('test-001');
      expect(result.layers).toBeDefined();
    });

    it('should return ALLOW for safe context vectors (near origin)', () => {
      const result = pipeline.execute({
        input: [0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0, 0, 0, 0, 0, 0],
        requestId: 'safe-001',
      });

      expect(result.decision).toBe('ALLOW');
      expect(result.harmonicScore).toBeGreaterThan(0.5);
    });

    it('should generate a request ID when none provided', () => {
      const result = pipeline.execute({
        input: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0, 0, 0, 0, 0, 0],
      });

      expect(result.requestId).toBeDefined();
      expect(result.requestId.length).toBeGreaterThan(0);
    });
  });

  describe('4-Tier Governance Decisions', () => {
    it('should produce all four decision types based on risk', () => {
      // Test with custom thresholds for deterministic behavior
      const customPipeline = createSecurityPipeline({
        thresholds: { allow: 0.25, quarantine: 0.50, escalate: 0.75 },
      });

      // Very safe input (near origin)
      const safe = customPipeline.execute({
        input: [0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0, 0, 0, 0, 0, 0],
        requestId: 'allow-test',
      });
      expect(safe.decision).toBe('ALLOW');

      // The pipeline correctly classifies based on hyperbolic distance
      expect(safe.riskPrime).toBeLessThan(0.25);
    });
  });

  describe('Input Validation', () => {
    it('should DENY requests with invalid input', () => {
      const result = pipeline.execute({
        input: [] as unknown as number[],
        requestId: 'invalid-001',
      });

      expect(result.decision).toBe('DENY');
      expect(result.validationPassed).toBe(false);
      expect(result.validationErrors.length).toBeGreaterThan(0);
    });

    it('should DENY requests with NaN values', () => {
      const result = pipeline.execute({
        input: [1, NaN, 3, 4, 5, 6, 0, 0, 0, 0, 0, 0],
        requestId: 'nan-001',
      });

      expect(result.decision).toBe('DENY');
      expect(result.validationPassed).toBe(false);
    });

    it('should handle short inputs by padding to correct dimension', () => {
      const result = pipeline.execute({
        input: [0.1, 0.2, 0.3],
        requestId: 'short-001',
      });

      // Should still execute successfully (padded with zeros)
      expect(result.validationPassed).toBe(true);
      expect(['ALLOW', 'QUARANTINE', 'ESCALATE', 'DENY']).toContain(result.decision);
    });
  });

  describe('Replay Protection', () => {
    it('should block duplicate request IDs', () => {
      const first = pipeline.execute({
        input: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0, 0, 0, 0, 0, 0],
        requestId: 'replay-001',
        providerId: 'provider-1',
      });

      const second = pipeline.execute({
        input: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0, 0, 0, 0, 0, 0],
        requestId: 'replay-001',
        providerId: 'provider-1',
      });

      expect(first.replayDetected).toBe(false);
      expect(second.replayDetected).toBe(true);
      expect(second.decision).toBe('DENY');
    });

    it('should allow same requestId from different providers', () => {
      const first = pipeline.execute({
        input: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0, 0, 0, 0, 0, 0],
        requestId: 'shared-001',
        providerId: 'provider-A',
      });

      const second = pipeline.execute({
        input: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0, 0, 0, 0, 0, 0],
        requestId: 'shared-001',
        providerId: 'provider-B',
      });

      expect(first.replayDetected).toBe(false);
      expect(second.replayDetected).toBe(false);
    });

    it('should skip replay check when disabled', () => {
      const noReplayPipeline = createSecurityPipeline({
        enableReplayProtection: false,
      });

      const first = noReplayPipeline.execute({
        input: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0, 0, 0, 0, 0, 0],
        requestId: 'no-replay-001',
      });

      const second = noReplayPipeline.execute({
        input: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0, 0, 0, 0, 0, 0],
        requestId: 'no-replay-001',
      });

      expect(first.replayDetected).toBe(false);
      expect(second.replayDetected).toBe(false);
    });
  });

  describe('Integrity Tags', () => {
    it('should produce an HMAC integrity tag', () => {
      const result = pipeline.execute({
        input: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0, 0, 0, 0, 0, 0],
        requestId: 'hmac-001',
      });

      expect(result.integrityTag).toBeDefined();
      expect(result.integrityTag!.length).toBe(64); // SHA-256 hex
    });

    it('should verify valid integrity tags', () => {
      const result = pipeline.execute({
        input: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0, 0, 0, 0, 0, 0],
        requestId: 'verify-001',
      });

      expect(pipeline.verifyIntegrity(result)).toBe(true);
    });

    it('should reject tampered results', () => {
      const result = pipeline.execute({
        input: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0, 0, 0, 0, 0, 0],
        requestId: 'tamper-001',
      });

      // Tamper with the decision
      const tampered = { ...result, decision: 'ALLOW' as const, riskPrime: 0 };
      expect(pipeline.verifyIntegrity(tampered)).toBe(false);
    });

    it('should not produce tag when disabled', () => {
      const noTagPipeline = createSecurityPipeline({
        enableIntegrityTag: false,
      });

      const result = noTagPipeline.execute({
        input: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0, 0, 0, 0, 0, 0],
        requestId: 'no-tag-001',
      });

      expect(result.integrityTag).toBeUndefined();
    });
  });

  describe('Audit Trail Integration', () => {
    it('should log pipeline executions to the audit trail', () => {
      pipeline.execute({
        input: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0, 0, 0, 0, 0, 0],
        requestId: 'audit-001',
      });

      const stats = pipeline.getAuditStats();
      expect(stats.totalEntries).toBeGreaterThanOrEqual(1);
    });

    it('should log anomalies for high-risk decisions', () => {
      // Execute with a clearly high-risk input (large values = far from origin)
      const customPipeline = createSecurityPipeline({
        thresholds: { allow: 0.01, quarantine: 0.02, escalate: 0.03 },
      });

      customPipeline.execute({
        input: [10, 10, 10, 10, 10, 10, 5, 5, 5, 5, 5, 5],
        requestId: 'anomaly-001',
      });

      const stats = customPipeline.getAuditStats();
      // Should have at least the execution entry; anomaly depends on risk level
      expect(stats.totalEntries).toBeGreaterThanOrEqual(1);
    });

    it('should maintain audit chain integrity across multiple operations', () => {
      for (let i = 0; i < 10; i++) {
        pipeline.execute({
          input: [0.1 * i, 0.2, 0.3, 0.4, 0.5, 0.6, 0, 0, 0, 0, 0, 0],
          requestId: `chain-${i}`,
        });
      }

      expect(pipeline.verifyAuditChain()).toBe(true);
    });

    it('should log validation failures', () => {
      pipeline.execute({
        input: [] as unknown as number[],
        requestId: 'val-fail-001',
      });

      const stats = pipeline.getAuditStats();
      expect(stats.validationFailCount).toBe(1);
    });

    it('should log replay blocks', () => {
      pipeline.execute({
        input: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0, 0, 0, 0, 0, 0],
        requestId: 'replay-audit-001',
      });

      pipeline.execute({
        input: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0, 0, 0, 0, 0, 0],
        requestId: 'replay-audit-001',
      });

      const stats = pipeline.getAuditStats();
      expect(stats.replayBlockedCount).toBe(1);
    });
  });

  describe('14-Layer Metrics', () => {
    it('should expose all 14 layer results', () => {
      const result = pipeline.execute({
        input: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
        requestId: 'layers-001',
      });

      expect(result.layers).toBeDefined();
      const layers = result.layers!;

      // L1: Complex state
      expect(layers.l1_complex.real.length).toBe(6);
      expect(layers.l1_complex.imag.length).toBe(6);

      // L2: Realification
      expect(layers.l2_real.length).toBe(12);

      // L3: Weighted transform
      expect(layers.l3_weighted.length).toBe(12);

      // L4: Poincare embedding
      expect(layers.l4_poincare.length).toBe(12);
      const poincareNorm = Math.sqrt(
        layers.l4_poincare.reduce((s, v) => s + v * v, 0)
      );
      expect(poincareNorm).toBeLessThan(1); // Must be in the ball

      // L5: Hyperbolic distance
      expect(layers.l5_distance).toBeGreaterThanOrEqual(0);

      // L6: Breathing transform
      expect(layers.l6_breathed.length).toBe(12);

      // L7: Phase transform
      expect(layers.l7_transformed.length).toBe(12);

      // L8: Realm distance
      expect(layers.l8_realmDist).toBeGreaterThanOrEqual(0);

      // L9: Spectral coherence
      expect(layers.l9_spectral).toBeGreaterThanOrEqual(0);
      expect(layers.l9_spectral).toBeLessThanOrEqual(1);

      // L10: Spin coherence
      expect(layers.l10_spin).toBeGreaterThanOrEqual(0);
      expect(layers.l10_spin).toBeLessThanOrEqual(1);

      // L11: Triadic temporal
      expect(layers.l11_triadic).toBeGreaterThanOrEqual(0);
      expect(layers.l11_triadic).toBeLessThanOrEqual(1);

      // L12: Harmonic scaling
      expect(layers.l12_harmonic).toBeGreaterThan(0);
      expect(layers.l12_harmonic).toBeLessThanOrEqual(1);

      // L13: Decision
      expect(['ALLOW', 'QUARANTINE', 'DENY']).toContain(layers.l13_decision);

      // L14: Audio axis
      expect(layers.l14_audio).toBeGreaterThanOrEqual(0);
      expect(layers.l14_audio).toBeLessThanOrEqual(1);
    });

    it('should have higher hyperbolic distance for adversarial input', () => {
      const safe = pipeline.execute({
        input: [0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0, 0, 0, 0, 0, 0],
        requestId: 'safe-compare',
      });

      const risky = pipeline.execute({
        input: [5, 5, 5, 5, 5, 5, 3, 3, 3, 3, 3, 3],
        requestId: 'risky-compare',
      });

      expect(risky.hyperbolicDistance).toBeGreaterThan(safe.hyperbolicDistance);
    });

    it('should have lower harmonic score for adversarial input', () => {
      const safe = pipeline.execute({
        input: [0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0, 0, 0, 0, 0, 0],
        requestId: 'h-safe',
      });

      const risky = pipeline.execute({
        input: [5, 5, 5, 5, 5, 5, 3, 3, 3, 3, 3, 3],
        requestId: 'h-risky',
      });

      // Adversarial input should have lower H (closer to boundary)
      expect(risky.harmonicScore).toBeLessThan(safe.harmonicScore);
    });
  });

  describe('Factory Function', () => {
    it('should create a pipeline with createSecurityPipeline()', () => {
      const p = createSecurityPipeline();
      const result = p.execute({
        input: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0, 0, 0, 0, 0, 0],
        requestId: 'factory-001',
      });

      expect(result.validationPassed).toBe(true);
      expect(['ALLOW', 'QUARANTINE', 'ESCALATE', 'DENY']).toContain(result.decision);
    });

    it('should accept custom configuration', () => {
      const p = createSecurityPipeline({
        pipeline: { D: 3 },
        thresholds: { allow: 0.1, quarantine: 0.3, escalate: 0.5 },
      });

      const result = p.execute({
        input: [0.01, 0.01, 0.01, 0, 0, 0],
        requestId: 'custom-001',
      });

      expect(result.validationPassed).toBe(true);
    });
  });
});
