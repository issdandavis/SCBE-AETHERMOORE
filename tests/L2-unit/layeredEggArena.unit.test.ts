/**
 * @file layeredEggArena.unit.test.ts
 * @module tests/L2-unit/layeredEggArena
 * @layer Layer 1-14
 *
 * Tests for the Layered Egg Arena — Sacred Eggs × Shifting Keyspace × Pipeline.
 * Validates that systems are about LAYERS: 14 nested eggs, each with
 * different predicates, composing into a chain that's exponentially harder
 * to break than any single egg.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  LayeredEggChain,
  createGovernanceFingerprint,
  verifyGovernanceFingerprint,
  LAYER_TONGUE_MAP,
  LAYER_RING_REQUIREMENT,
  LAYER_AXIOM_MAP,
} from '../../src/crypto/layeredEggArena';
import type { HatchContext } from '../../src/crypto/layeredEggArena';

// ============================================================================
// Helpers
// ============================================================================

/** Build a Map of dummy layer outputs */
function dummyLayerOutputs(): Map<number, string> {
  const outputs = new Map<number, string>();
  for (let i = 1; i <= 14; i++) {
    outputs.set(i, `output_layer_${i}_${Math.random().toString(36).slice(2)}`);
  }
  return outputs;
}

// ============================================================================
// Tests
// ============================================================================

describe('LayeredEggChain', () => {
  let chain: LayeredEggChain;

  beforeEach(() => {
    chain = new LayeredEggChain(192); // ML-KEM-768 base
  });

  // --------------------------------------------------------------------------
  // Pipeline Sealing
  // --------------------------------------------------------------------------

  describe('sealing the 14-layer pipeline', () => {
    it('should seal all 14 layers as eggs', () => {
      const eggs = chain.sealPipeline(dummyLayerOutputs());
      expect(eggs).toHaveLength(14);
    });

    it('should assign correct tongues to each layer', () => {
      const eggs = chain.sealPipeline(dummyLayerOutputs());

      for (const egg of eggs) {
        expect(egg.requiredTongue).toBe(LAYER_TONGUE_MAP[egg.layerNumber]);
      }
    });

    it('should assign correct ring requirements', () => {
      const eggs = chain.sealPipeline(dummyLayerOutputs());

      // L13 (Risk Decision) requires ring 0 (CORE)
      const l13 = eggs.find((e) => e.layerNumber === 13)!;
      expect(l13.maxRing).toBe(0);

      // L1 (Complex Context) allows any ring
      const l1 = eggs.find((e) => e.layerNumber === 1)!;
      expect(l1.maxRing).toBe(4);
    });

    it('should chain eggs with hash links', () => {
      const eggs = chain.sealPipeline(dummyLayerOutputs());

      // First egg's previous hash is 'genesis'
      expect(eggs[0]!.previousEggHash).toBe('genesis');

      // Each subsequent egg's previousEggHash should differ from 'genesis'
      for (let i = 1; i < eggs.length; i++) {
        expect(eggs[i]!.previousEggHash).not.toBe('genesis');
        // And it should not equal the egg before it (different layer outputs)
        expect(eggs[i]!.previousEggHash).not.toBe(eggs[i - 1]!.previousEggHash);
      }
    });

    it('should bind governance fingerprint to all eggs', () => {
      const eggs = chain.sealPipeline(dummyLayerOutputs());

      // All eggs share the same governance fingerprint (sealed at same time)
      const fingerprint = eggs[0]!.governanceFingerprint;
      for (const egg of eggs) {
        expect(egg.governanceFingerprint).toBe(fingerprint);
      }
    });

    it('should tag each egg with its quantum axiom', () => {
      const eggs = chain.sealPipeline(dummyLayerOutputs());

      const l1 = eggs.find((e) => e.layerNumber === 1)!;
      expect(l1.axiom).toBe('composition');

      const l5 = eggs.find((e) => e.layerNumber === 5)!;
      expect(l5.axiom).toBe('symmetry');

      const l13 = eggs.find((e) => e.layerNumber === 13)!;
      expect(l13.axiom).toBe('causality');
    });

    it('should use all 6 Sacred Tongues across the pipeline', () => {
      const eggs = chain.sealPipeline(dummyLayerOutputs());
      const tongues = new Set(eggs.map((e) => e.requiredTongue));
      expect(tongues.size).toBe(6);
      expect(tongues).toContain('KO');
      expect(tongues).toContain('AV');
      expect(tongues).toContain('RU');
      expect(tongues).toContain('CA');
      expect(tongues).toContain('UM');
      expect(tongues).toContain('DR');
    });
  });

  // --------------------------------------------------------------------------
  // Hatching Eggs
  // --------------------------------------------------------------------------

  describe('hatching layer eggs', () => {
    it('should hatch Layer 1 with correct tongue + ring + governance + chain', () => {
      chain.sealPipeline(dummyLayerOutputs());
      const snapshot = chain.getKeyspaceSnapshot();

      const result = chain.hatchLayer(1, {
        tongue: 'KO',        // L1 requires KO
        ringLevel: 0,        // Core (0 <= 4)
        currentKeyspace: snapshot,
        previousEggHash: 'genesis', // First egg
      });

      expect(result.success).toBe(true);
      expect(result.tongueValid).toBe(true);
      expect(result.ringValid).toBe(true);
      expect(result.governanceValid).toBe(true);
      expect(result.chainValid).toBe(true);
      expect(result.failureMode).toBeNull();
    });

    it('should fail with noise when tongue is wrong', () => {
      chain.sealPipeline(dummyLayerOutputs());
      const snapshot = chain.getKeyspaceSnapshot();

      const result = chain.hatchLayer(1, {
        tongue: 'UM',        // L1 requires KO, not UM
        ringLevel: 0,
        currentKeyspace: snapshot,
        previousEggHash: 'genesis',
      });

      expect(result.success).toBe(false);
      expect(result.failureMode).toBe('noise');
      expect(result.tongueValid).toBe(false);
    });

    it('should fail with noise when ring level is too high', () => {
      chain.sealPipeline(dummyLayerOutputs());
      const snapshot = chain.getKeyspaceSnapshot();

      // L13 requires ring 0 (CORE), try with ring 2
      const result = chain.hatchLayer(13, {
        tongue: 'RU',
        ringLevel: 2,         // Too high — L13 requires 0
        currentKeyspace: snapshot,
        previousEggHash: chain.computeEggHash(12),
      });

      expect(result.success).toBe(false);
      expect(result.ringValid).toBe(false);
    });

    it('should fail with noise when chain hash is wrong', () => {
      chain.sealPipeline(dummyLayerOutputs());
      const snapshot = chain.getKeyspaceSnapshot();

      const result = chain.hatchLayer(2, {
        tongue: 'KO',
        ringLevel: 0,
        currentKeyspace: snapshot,
        previousEggHash: 'wrong_hash', // Doesn't match L1's egg hash
      });

      expect(result.success).toBe(false);
      expect(result.chainValid).toBe(false);
    });

    it('should produce DIFFERENT noise on each failed attempt', () => {
      chain.sealPipeline(dummyLayerOutputs());
      const snapshot = chain.getKeyspaceSnapshot();

      const fail1 = chain.hatchLayer(1, {
        tongue: 'UM',
        ringLevel: 0,
        currentKeyspace: snapshot,
        previousEggHash: 'genesis',
      });

      const fail2 = chain.hatchLayer(1, {
        tongue: 'UM',
        ringLevel: 0,
        currentKeyspace: snapshot,
        previousEggHash: 'genesis',
      });

      // Noise should be random each time (fail-to-noise oracle safety)
      expect(fail1.payload).not.toBe(fail2.payload);
    });

    it('should successfully hatch L1 then L2 with chain proof', () => {
      chain.sealPipeline(dummyLayerOutputs());
      const snapshot = chain.getKeyspaceSnapshot();

      // Hatch L1
      const r1 = chain.hatchLayer(1, {
        tongue: 'KO',
        ringLevel: 0,
        currentKeyspace: snapshot,
        previousEggHash: 'genesis',
      });
      expect(r1.success).toBe(true);

      // Hatch L2 using L1's egg hash as chain proof
      const l1Hash = chain.computeEggHash(1);
      const r2 = chain.hatchLayer(2, {
        tongue: 'KO',       // L2 also requires KO
        ringLevel: 0,
        currentKeyspace: snapshot,
        previousEggHash: l1Hash,
      });
      expect(r2.success).toBe(true);
    });
  });

  // --------------------------------------------------------------------------
  // Stairwell Effect (Breathing Invalidation)
  // --------------------------------------------------------------------------

  describe('stairwell effect — breathing invalidates eggs', () => {
    it('should invalidate governance fingerprint after breathe()', () => {
      chain.sealPipeline(dummyLayerOutputs());

      // Before breathing: should succeed
      const snapBefore = chain.getKeyspaceSnapshot();
      const r1 = chain.hatchLayer(1, {
        tongue: 'KO',
        ringLevel: 0,
        currentKeyspace: snapBefore,
        previousEggHash: 'genesis',
      });
      expect(r1.success).toBe(true);

      // BREATHE — the stairwell rotates
      chain.breathe();

      // After breathing: governance fingerprint no longer matches
      const snapAfter = chain.getKeyspaceSnapshot();
      const r2 = chain.hatchLayer(1, {
        tongue: 'KO',
        ringLevel: 0,
        currentKeyspace: snapAfter,
        previousEggHash: 'genesis',
      });
      expect(r2.success).toBe(false);
      expect(r2.governanceValid).toBe(false);
    });

    it('should invalidate ALL 14 eggs simultaneously on breathe()', () => {
      chain.sealPipeline(dummyLayerOutputs());
      chain.breathe(); // Rotate stairwell

      const snapshot = chain.getKeyspaceSnapshot();
      let previousHash = 'genesis';

      for (let layer = 1; layer <= 14; layer++) {
        const egg = chain.getEgg(layer)!;
        const result = chain.hatchLayer(layer, {
          tongue: egg.requiredTongue,
          ringLevel: 0,
          currentKeyspace: snapshot,
          previousEggHash: previousHash,
        });

        // Every egg should fail because governance shifted
        expect(result.success).toBe(false);
        expect(result.governanceValid).toBe(false);

        previousHash = chain.computeEggHash(layer);
      }
    });
  });

  // --------------------------------------------------------------------------
  // Security Analysis
  // --------------------------------------------------------------------------

  describe('security analysis', () => {
    it('should report correct base and governance bits', () => {
      chain.sealPipeline(dummyLayerOutputs());
      const analysis = chain.getSecurityAnalysis();

      expect(analysis.baseBitsPerEgg).toBe(192);
      expect(analysis.governanceBitsPerEgg).toBe(96); // 32+16+8+24+12+4
      expect(analysis.effectiveBitsPerEgg).toBe(288); // 192+96
    });

    it('should show sequential cost exceeds per-egg cost', () => {
      chain.sealPipeline(dummyLayerOutputs());
      const analysis = chain.getSecurityAnalysis();

      // Sequential = per_egg + log2(14) ≈ per_egg + 3.8
      expect(analysis.sequentialCostLog2).toBeGreaterThan(analysis.effectiveBitsPerEgg);
    });

    it('should require all 6 tongues', () => {
      chain.sealPipeline(dummyLayerOutputs());
      const analysis = chain.getSecurityAnalysis();

      expect(analysis.tonguesRequired).toHaveLength(6);
      expect(analysis.tonguesRequired).toContain('KO');
      expect(analysis.tonguesRequired).toContain('UM');
    });

    it('should report ring 0 as the strictest requirement', () => {
      chain.sealPipeline(dummyLayerOutputs());
      const analysis = chain.getSecurityAnalysis();

      expect(analysis.strictestRing).toBe(0); // L13 requires CORE
    });

    it('should cover all 5 quantum axioms', () => {
      chain.sealPipeline(dummyLayerOutputs());
      const analysis = chain.getSecurityAnalysis();

      expect(analysis.axiomsCovered).toContain('composition');
      expect(analysis.axiomsCovered).toContain('unitarity');
      expect(analysis.axiomsCovered).toContain('locality');
      expect(analysis.axiomsCovered).toContain('causality');
      expect(analysis.axiomsCovered).toContain('symmetry');
    });

    it('should report breathing invalidates all eggs', () => {
      chain.sealPipeline(dummyLayerOutputs());
      const analysis = chain.getSecurityAnalysis();

      expect(analysis.breathingInvalidatesAll).toBe(true);
    });

    it('should produce a human-readable summary', () => {
      chain.sealPipeline(dummyLayerOutputs());
      const analysis = chain.getSecurityAnalysis();

      expect(analysis.summary).toContain('14 layers');
      expect(analysis.summary).toContain('Sacred Egg');
      expect(analysis.summary).toContain('STAIRWELL EFFECT');
    });

    it('should show total effective bits > sequential cost', () => {
      chain.sealPipeline(dummyLayerOutputs());
      const analysis = chain.getSecurityAnalysis();

      // Total = sequential + tongue diversity + ring escalation
      expect(analysis.totalEffectiveBits).toBeGreaterThan(
        analysis.sequentialCostLog2,
      );
    });
  });

  // --------------------------------------------------------------------------
  // Governance Fingerprint
  // --------------------------------------------------------------------------

  describe('governance fingerprint', () => {
    it('should produce deterministic fingerprints for same state', () => {
      const snap = chain.getKeyspaceSnapshot();
      const fp1 = createGovernanceFingerprint(snap);
      const fp2 = createGovernanceFingerprint(snap);
      expect(fp1).toBe(fp2);
    });

    it('should verify correct fingerprint', () => {
      const snap = chain.getKeyspaceSnapshot();
      const fp = createGovernanceFingerprint(snap);
      expect(verifyGovernanceFingerprint(fp, snap)).toBe(true);
    });

    it('should reject fingerprint after breathing', () => {
      const snap1 = chain.getKeyspaceSnapshot();
      const fp = createGovernanceFingerprint(snap1);

      chain.breathe();

      const snap2 = chain.getKeyspaceSnapshot();
      expect(verifyGovernanceFingerprint(fp, snap2)).toBe(false);
    });
  });

  // --------------------------------------------------------------------------
  // Layer Configuration Constants
  // --------------------------------------------------------------------------

  describe('layer configuration', () => {
    it('should have tongue mappings for all 14 layers', () => {
      for (let i = 1; i <= 14; i++) {
        expect(LAYER_TONGUE_MAP[i]).toBeDefined();
        expect(['KO', 'AV', 'RU', 'CA', 'UM', 'DR']).toContain(LAYER_TONGUE_MAP[i]);
      }
    });

    it('should have ring requirements for all 14 layers', () => {
      for (let i = 1; i <= 14; i++) {
        expect(LAYER_RING_REQUIREMENT[i]).toBeDefined();
        expect(LAYER_RING_REQUIREMENT[i]).toBeGreaterThanOrEqual(0);
        expect(LAYER_RING_REQUIREMENT[i]).toBeLessThanOrEqual(4);
      }
    });

    it('should have axiom mappings for all 14 layers', () => {
      for (let i = 1; i <= 14; i++) {
        expect(LAYER_AXIOM_MAP[i]).toBeDefined();
      }
    });

    it('should have ring requirements that get stricter deeper in pipeline', () => {
      // Early layers (1-4) should be more permissive
      expect(LAYER_RING_REQUIREMENT[1]).toBeGreaterThanOrEqual(3);
      // Core security layers (8, 11, 12, 13) should be strict
      expect(LAYER_RING_REQUIREMENT[8]).toBeLessThanOrEqual(1);
      expect(LAYER_RING_REQUIREMENT[12]).toBeLessThanOrEqual(1);
      expect(LAYER_RING_REQUIREMENT[13]).toBe(0);
    });
  });
});
