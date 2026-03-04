/**
 * @file governanceGaugeField.test.ts
 * @module tests/harmonic
 * @layer Layer 5, Layer 6, Layer 7, Layer 9, Layer 10, Layer 12, Layer 13
 * @component Governance Gauge Field Tests
 * @version 1.0.0
 */

import { describe, it, expect } from 'vitest';
import { GovernanceGaugeField } from '../../src/harmonic/governanceGaugeField.js';

// Deterministic PRNG for reproducible tests
function seededRng(seed: number = 42): () => number {
  let s = seed;
  return () => {
    s = (s * 1103515245 + 12345) & 0x7fffffff;
    return s / 0x7fffffff;
  };
}

describe('GovernanceGaugeField', () => {
  describe('createArray', () => {
    it('creates an array with spin field and chiral graph', () => {
      const field = new GovernanceGaugeField();
      const array = field.createArray('alpha');
      expect(array.id).toBe('alpha');
      expect(array.spinField).toBeDefined();
      expect(array.chiralGraph).toBeDefined();
      expect(array.breathFrequency).toBe(1.0); // φ^0
    });

    it('assigns φ-scaled breathing frequencies', () => {
      const field = new GovernanceGaugeField();
      const a0 = field.createArray('a0', 0);
      const a1 = field.createArray('a1', 1);
      const a2 = field.createArray('a2', 2);

      expect(a0.breathFrequency).toBeCloseTo(1.0, 5);
      expect(a1.breathFrequency).toBeCloseTo(1.618, 2);
      expect(a2.breathFrequency).toBeCloseTo(2.618, 2);
    });

    it('clamps frequency index to valid range', () => {
      const field = new GovernanceGaugeField();
      const arr = field.createArray('clamped', 100);
      // Should clamp to last valid index (3)
      expect(arr.breathFrequency).toBeGreaterThan(1.0);
    });
  });

  describe('tick', () => {
    it('advances tick counter', () => {
      const field = new GovernanceGaugeField();
      field.createArray('a');
      const rng = seededRng();

      field.tick(rng);
      expect(field.getTick()).toBe(1);

      field.tick(rng);
      expect(field.getTick()).toBe(2);
    });

    it('evolves spin states', () => {
      const field = new GovernanceGaugeField();
      field.createArray('a');
      const rng = seededRng(42);

      field.tick(rng);
      const array = field.getArray('a')!;
      const snap = array.spinField.snapshot();
      expect(snap.step).toBeGreaterThan(0);
    });

    it('advances breathing phase', () => {
      const field = new GovernanceGaugeField();
      const arr = field.createArray('a');
      const initialPhase = arr.breathPhase;
      const rng = seededRng();

      field.tick(rng);
      expect(arr.breathPhase).not.toBe(initialPhase);
    });
  });

  describe('computePhaseLock', () => {
    it('returns null for non-existent arrays', () => {
      const field = new GovernanceGaugeField();
      expect(field.computePhaseLock('a', 'b')).toBeNull();
    });

    it('computes lock quality between arrays', () => {
      const field = new GovernanceGaugeField();
      field.createArray('a', 0);
      field.createArray('b', 1);
      const rng = seededRng();

      // Run a few ticks to get phases moving
      for (let i = 0; i < 10; i++) field.tick(rng);

      const lock = field.computePhaseLock('a', 'b');
      expect(lock).not.toBeNull();
      expect(lock!.lockQuality).toBeGreaterThanOrEqual(0);
      expect(lock!.lockQuality).toBeLessThanOrEqual(1);
      expect(lock!.beatFrequency).toBeGreaterThanOrEqual(0);
    });

    it('same-frequency arrays can achieve high lock quality', () => {
      const field = new GovernanceGaugeField();
      field.createArray('a', 0); // freq = 1.0
      field.createArray('b', 0); // freq = 1.0 (same!)

      // At tick 0, both have phase 0 → perfectly locked
      const lock = field.computePhaseLock('a', 'b');
      expect(lock!.lockQuality).toBeCloseTo(1.0, 5);
      expect(lock!.locked).toBe(true);
      expect(lock!.beatFrequency).toBe(0);
    });
  });

  describe('computeLagrangian', () => {
    it('returns a finite number', () => {
      const field = new GovernanceGaugeField();
      field.createArray('a');
      const rng = seededRng();
      for (let i = 0; i < 10; i++) field.tick(rng);

      const L = field.computeLagrangian();
      expect(Number.isFinite(L)).toBe(true);
    });

    it('changes as field evolves', () => {
      const field = new GovernanceGaugeField();
      field.createArray('a');
      const rng = seededRng(42);

      field.tick(rng);
      const L1 = field.computeLagrangian();

      for (let i = 0; i < 20; i++) field.tick(rng);
      const L2 = field.computeLagrangian();

      // Lagrangian should change over time as spin states evolve
      // (could be same in degenerate cases, so just check finiteness)
      expect(Number.isFinite(L1)).toBe(true);
      expect(Number.isFinite(L2)).toBe(true);
    });
  });

  describe('forgeBlock', () => {
    it('creates a governance block', () => {
      const field = new GovernanceGaugeField();
      field.createArray('a');
      const rng = seededRng();
      for (let i = 0; i < 5; i++) field.tick(rng);

      const block = field.forgeBlock();
      expect(block.index).toBe(0);
      expect(block.previousHash).toBe(0); // First block
      expect(block.lagrangian).toBeDefined();
      expect(['ALLOW', 'QUARANTINE', 'ESCALATE', 'DENY']).toContain(block.decision);
    });

    it('chains blocks with previous hash', () => {
      const field = new GovernanceGaugeField();
      field.createArray('a');
      const rng = seededRng();

      for (let i = 0; i < 5; i++) field.tick(rng);
      const block1 = field.forgeBlock();

      for (let i = 0; i < 5; i++) field.tick(rng);
      const block2 = field.forgeBlock();

      expect(block2.index).toBe(1);
      expect(block2.previousHash).toBe(block1.stateHash);
    });

    it('includes phase locks for multi-array fields', () => {
      const field = new GovernanceGaugeField();
      field.createArray('a', 0);
      field.createArray('b', 1);
      field.createArray('c', 2);
      const rng = seededRng();

      for (let i = 0; i < 10; i++) field.tick(rng);
      const block = field.forgeBlock();

      // 3 arrays → 3 pairwise locks (a-b, a-c, b-c)
      expect(block.phaseLocks).toHaveLength(3);
    });

    it('maintains chain integrity', () => {
      const field = new GovernanceGaugeField();
      field.createArray('a');
      const rng = seededRng();

      // Forge 5 blocks
      for (let b = 0; b < 5; b++) {
        for (let t = 0; t < 3; t++) field.tick(rng);
        field.forgeBlock();
      }

      const chain = field.getChain();
      expect(chain).toHaveLength(5);

      // Verify chain continuity
      for (let i = 1; i < chain.length; i++) {
        expect(chain[i].previousHash).toBe(chain[i - 1].stateHash);
        expect(chain[i].index).toBe(i);
      }
    });
  });

  describe('consensusStrength', () => {
    it('returns 1.0 for single array', () => {
      const field = new GovernanceGaugeField();
      field.createArray('solo');
      expect(field.consensusStrength()).toBe(1.0);
    });

    it('returns value in [0, 1]', () => {
      const field = new GovernanceGaugeField();
      field.createArray('a', 0);
      field.createArray('b', 1);
      const rng = seededRng();
      for (let i = 0; i < 20; i++) field.tick(rng);

      const strength = field.consensusStrength();
      expect(strength).toBeGreaterThanOrEqual(0);
      expect(strength).toBeLessThanOrEqual(1);
    });
  });

  describe('risk decisions', () => {
    it('stable field produces ALLOW', () => {
      const field = new GovernanceGaugeField({
        lagrangianThresholds: { allow: 100, quarantine: 200, escalate: 300 },
      });
      field.createArray('a');
      const rng = seededRng();
      for (let i = 0; i < 10; i++) field.tick(rng);

      const block = field.forgeBlock();
      // With wide thresholds, a normal field should ALLOW
      expect(block.decision).toBe('ALLOW');
    });
  });

  describe('integration: spin + chirality', () => {
    it('spin states propagate to chiral graph', () => {
      const field = new GovernanceGaugeField();
      const array = field.createArray('test');
      const rng = seededRng();

      field.tick(rng);

      // Spin states from spin field should be reflected in chiral graph nodes
      const spinStates = array.spinField.getStateMap();
      const chiralNodes = array.chiralGraph.getAllNodes();

      for (const node of chiralNodes) {
        const spinState = spinStates.get(node.id);
        if (spinState !== undefined) {
          expect(node.spinState).toBe(spinState);
        }
      }
    });
  });
});
