/**
 * @file pqcArena.unit.test.ts
 * @module tests/L2-unit/pqcArena
 * @layer Layer 5, Layer 12
 *
 * Tests for the PQC Arena — system-vs-system comparison
 * and shifting keyspace with governance axis injection.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { PQCArena, ShiftingKeyspace, ARENA_SYSTEMS } from '../../src/crypto/pqcArena';

// ============================================================================
// ShiftingKeyspace Tests
// ============================================================================

describe('ShiftingKeyspace', () => {
  let ks: ShiftingKeyspace;

  beforeEach(() => {
    ks = new ShiftingKeyspace(192); // ML-KEM-768 base
  });

  describe('axis injection', () => {
    it('should start with base bits only', () => {
      expect(ks.getEffectiveBits()).toBe(192);
      expect(ks.getGovernanceBits()).toBe(0);
    });

    it('should add bits when injecting an axis', () => {
      // Inject a 32-bit TIME axis: 2^32 cardinality = 32 bits
      ks.injectAxis({
        name: 'TIME',
        tongue: 'KO',
        cardinality: Math.pow(2, 32),
        temporal: true,
        description: 'test time axis',
      });
      expect(ks.getEffectiveBits()).toBe(192 + 32);
      expect(ks.getGovernanceBits()).toBe(32);
    });

    it('should accumulate bits from multiple axes', () => {
      ks.injectAxis({
        name: 'TIME',
        tongue: 'KO',
        cardinality: Math.pow(2, 32),
        temporal: true,
        description: 'time',
      });
      ks.injectAxis({
        name: 'INTENT',
        tongue: 'CA',
        cardinality: Math.pow(2, 16),
        temporal: false,
        description: 'intent',
      });
      ks.injectAxis({
        name: 'AUTHORITY',
        tongue: 'RU',
        cardinality: Math.pow(2, 8),
        temporal: false,
        description: 'authority',
      });
      // 192 + 32 + 16 + 8 = 248
      expect(ks.getEffectiveBits()).toBe(248);
      expect(ks.getGovernanceBits()).toBe(56);
    });

    it('should count temporal vs static axes', () => {
      ks.injectAxis({
        name: 'TIME',
        tongue: 'KO',
        cardinality: 1024,
        temporal: true,
        description: 'temporal',
      });
      ks.injectAxis({
        name: 'INTENT',
        tongue: 'CA',
        cardinality: 256,
        temporal: false,
        description: 'static',
      });
      ks.injectAxis({
        name: 'BREATHING',
        tongue: 'AV',
        cardinality: 4096,
        temporal: true,
        description: 'temporal',
      });
      expect(ks.getTemporalAxisCount()).toBe(2);
      expect(ks.getStaticAxisCount()).toBe(1);
    });
  });

  describe('breathing (stairwell rotation)', () => {
    it('should shift temporal axis values on breathe()', () => {
      const axis = ks.injectAxis({
        name: 'TIME',
        tongue: 'KO',
        cardinality: 1000,
        temporal: true,
        description: 'test',
      });
      const initialValue = axis.currentValue;

      ks.breathe();

      // Value should have changed (golden ratio step)
      expect(axis.currentValue).not.toBe(initialValue);
    });

    it('should NOT shift static axis values on breathe()', () => {
      const axis = ks.injectAxis({
        name: 'INTENT',
        tongue: 'CA',
        cardinality: 1000,
        temporal: false,
        description: 'test',
      });
      const initialValue = axis.currentValue;

      ks.breathe();

      // Static axis should not change
      expect(axis.currentValue).toBe(initialValue);
    });

    it('should use golden ratio stepping (never repeats exactly)', () => {
      ks.injectAxis({
        name: 'PHASE',
        tongue: 'DR',
        cardinality: 100,
        temporal: true,
        description: 'test',
      });

      // Collect values over many breathe cycles
      const values = new Set<number>();
      for (let i = 0; i < 50; i++) {
        ks.breathe();
        const snap = ks.snapshot();
        values.add(snap.axes[0]!.currentValue);
      }

      // Golden ratio stepping should produce many distinct values
      // (not cycling back quickly like a linear step would)
      expect(values.size).toBeGreaterThan(30);
    });

    it('should increment shift count on each temporal shift', () => {
      ks.injectAxis({
        name: 'A',
        tongue: 'KO',
        cardinality: 100,
        temporal: true,
        description: '',
      });
      ks.injectAxis({
        name: 'B',
        tongue: 'AV',
        cardinality: 100,
        temporal: true,
        description: '',
      });

      const snap0 = ks.snapshot();
      const initialShifts = snap0.shiftCount;

      ks.breathe();

      const snap1 = ks.snapshot();
      // 2 temporal axes shifted = +2 shift count
      expect(snap1.shiftCount).toBe(initialShifts + 2);
    });
  });

  describe('attacker progress estimation', () => {
    it('should show negligible progress for 192-bit base', () => {
      const snap = ks.snapshot(1e12, 365.25 * 24 * 3600); // 1yr at 1T ops/sec
      // 1e12 * 3.15e7 ≈ 3.15e19 ≈ 2^64.7
      // vs 2^192 search space
      // progress ≈ 2^(64.7 - 192) = 2^(-127.3) ≈ 0
      expect(snap.attackerProgress).toBeLessThan(1e-30);
    });

    it('should show even less progress with governance axes', () => {
      const snapBase = ks.snapshot(1e12, 3.15e7);

      ks.injectAxis({
        name: 'TIME',
        tongue: 'KO',
        cardinality: Math.pow(2, 32),
        temporal: true,
        description: '',
      });

      const snapGov = ks.snapshot(1e12, 3.15e7);

      // Governance makes it harder → less progress
      expect(snapGov.attackerProgress).toBeLessThanOrEqual(snapBase.attackerProgress);
      expect(snapGov.effectiveBits).toBeGreaterThan(snapBase.effectiveBits);
    });
  });

  describe('snapshot', () => {
    it('should include harmonic wall cost', () => {
      const snap = ks.snapshot();
      expect(snap.harmonicCost).toBeGreaterThan(0);
      expect(snap.harmonicCost).toBeLessThanOrEqual(1);
    });

    it('should include timestamp', () => {
      const snap = ks.snapshot();
      expect(snap.timestamp).toBeGreaterThan(0);
    });
  });
});

// ============================================================================
// PQCArena Tests
// ============================================================================

describe('PQCArena', () => {
  let arena: PQCArena;

  beforeEach(() => {
    arena = new PQCArena();
  });

  describe('system registry', () => {
    it('should have all NIST systems registered', () => {
      const ids = arena.listSystems();
      expect(ids).toContain('kem768');
      expect(ids).toContain('kem1024');
      expect(ids).toContain('mceliece');
      expect(ids).toContain('dsa65');
      expect(ids).toContain('slh128s');
      expect(ids).toContain('slh256s');
    });

    it('should return system descriptors with correct parameters', () => {
      const kem768 = arena.getSystem('kem768');
      expect(kem768).toBeDefined();
      expect(kem768!.publicKeyBytes).toBe(1184);
      expect(kem768!.outputBytes).toBe(1088);
      expect(kem768!.quantumBits).toBe(96);
      expect(kem768!.standard).toBe('FIPS 203');
    });

    it('should have correct McEliece parameters (giant keys, tiny ciphertext)', () => {
      const mc = arena.getSystem('mceliece');
      expect(mc).toBeDefined();
      expect(mc!.publicKeyBytes).toBe(261120); // ~255 KB
      expect(mc!.outputBytes).toBe(128); // tiny
    });
  });

  describe('governance keyspace builder', () => {
    it('should create 6 governance axes', () => {
      const sys = arena.getSystem('kem768')!;
      const ks = arena.buildGovernanceKeyspace(sys);
      const snap = ks.snapshot();

      expect(snap.axes).toHaveLength(6);
      expect(snap.axes.map((a) => a.name)).toEqual([
        'TIME',
        'INTENT',
        'AUTHORITY',
        'TONGUE_PHASE',
        'BREATHING',
        'FLUX',
      ]);
    });

    it('should assign different tongues to each axis', () => {
      const sys = arena.getSystem('kem768')!;
      const ks = arena.buildGovernanceKeyspace(sys);
      const snap = ks.snapshot();

      const tongues = snap.axes.map((a) => a.tongue);
      // All 6 tongues should be used (each axis has a different tongue)
      expect(new Set(tongues).size).toBe(6);
    });

    it('should add 96 governance bits total', () => {
      const sys = arena.getSystem('kem768')!;
      const ks = arena.buildGovernanceKeyspace(sys);

      // 32 + 16 + 8 + 24 + 12 + 4 = 96 governance bits
      expect(ks.getGovernanceBits()).toBe(96);
      // 96 (base) + 96 (governance) = 192 effective
      expect(ks.getEffectiveBits()).toBe(192);
    });

    it('should have 4 temporal and 2 static axes', () => {
      const sys = arena.getSystem('kem768')!;
      const ks = arena.buildGovernanceKeyspace(sys);

      expect(ks.getTemporalAxisCount()).toBe(4);
      expect(ks.getStaticAxisCount()).toBe(2);
    });
  });

  describe('head-to-head matches', () => {
    it('should compare ML-KEM-768 vs ML-KEM-1024', () => {
      const result = arena.match('kem768', 'kem1024');

      // KEM-1024 has more raw quantum bits (128 vs 96)
      expect(result.rawSecurityWinner).toBe('ML-KEM-1024');

      // Both get same governance overlay, so 1024 still wins
      expect(result.effectiveSecurityWinner).toBe('ML-KEM-1024');

      // Cost ratio: 1024 is 32 bits harder (128+96=224 vs 96+96=192)
      expect(result.costRatioLog2).toBe(-32); // negative = B is harder

      // Summary should be a string
      expect(result.summary).toContain('ML-KEM-768');
      expect(result.summary).toContain('ML-KEM-1024');
    });

    it('should compare ML-KEM-768 vs Classic McEliece', () => {
      const result = arena.match('kem768', 'mceliece');

      // McEliece has fewer quantum bits (64 vs 96) at NIST Level 1
      expect(result.rawSecurityWinner).toBe('ML-KEM-768');

      // KEM-768 has smaller wire size (1184+1088 vs 261120+128)
      expect(result.sizeWinner).toBe('ML-KEM-768');
    });

    it('should compare lattice vs hash-based signatures', () => {
      const result = arena.match('dsa65', 'slh128s');

      // DSA-65 is Level 3 (96 quantum bits), SLH-128s is Level 1 (64 bits)
      expect(result.rawSecurityWinner).toBe('ML-DSA-65');

      // SLH-128s has tiny keys but huge signatures
      const slh = arena.getSystem('slh128s')!;
      expect(slh.publicKeyBytes).toBe(32); // tiny
      expect(slh.outputBytes).toBe(7856); // huge sig
    });

    it('should show governance amplification for all systems', () => {
      const result = arena.match('kem512', 'kem1024');

      // Lower base bits → higher amplification ratio
      // KEM-512: 64 base → 64+96=160 effective → 2.5× amplification
      // KEM-1024: 128 base → 128+96=224 effective → 1.75× amplification
      expect(result.governanceAmplificationA).toBeGreaterThan(result.governanceAmplificationB);
    });

    it('should throw for unknown system IDs', () => {
      expect(() => arena.match('nonexistent', 'kem768')).toThrow('Unknown system: nonexistent');
    });
  });

  describe('tournament', () => {
    it('should rank all systems by effective security', () => {
      const leaderboard = arena.tournament();

      expect(leaderboard.entries.length).toBe(ARENA_SYSTEMS.length);

      // Should be sorted descending by effectiveBits
      for (let i = 1; i < leaderboard.entries.length; i++) {
        expect(leaderboard.entries[i - 1]!.effectiveBits).toBeGreaterThanOrEqual(
          leaderboard.entries[i]!.effectiveBits
        );
      }
    });

    it('should show ML-KEM-1024 or ML-DSA-87 at the top (highest base bits)', () => {
      const leaderboard = arena.tournament();
      const topEntry = leaderboard.entries[0]!;

      // Both have 128 quantum bits → 128+96=224 effective
      expect(topEntry.baseBits).toBe(128);
      expect(topEntry.effectiveBits).toBe(224);
    });

    it('should show governance amplification for every entry', () => {
      const leaderboard = arena.tournament();

      for (const entry of leaderboard.entries) {
        expect(entry.governanceBits).toBe(96);
        expect(entry.effectiveBits).toBe(entry.baseBits + 96);
        expect(entry.amplification).toBeCloseTo(entry.effectiveBits / entry.baseBits, 1);
      }
    });

    it('should show negligible attacker progress for all systems', () => {
      const leaderboard = arena.tournament();

      for (const entry of leaderboard.entries) {
        // Even the weakest system with governance should be un-searchable
        expect(entry.attackerProgress).toBeLessThan(1e-10);
      }
    });

    it('should include wire size for bandwidth comparison', () => {
      const leaderboard = arena.tournament();

      // Find McEliece — should have the largest wire size
      const mc = leaderboard.entries.find((e) => e.system.id === 'mceliece');
      expect(mc).toBeDefined();
      expect(mc!.wireSize).toBe(261120 + 128); // 261248 bytes

      // Find SLH-DSA-128s — tiny keys but huge sigs
      const slh = leaderboard.entries.find((e) => e.system.id === 'slh128s');
      expect(slh).toBeDefined();
      expect(slh!.wireSize).toBe(32 + 7856); // 7888 bytes
    });
  });

  describe('the stairwell effect (shifting mid-search)', () => {
    it('should demonstrate that breathing invalidates attacker work', () => {
      const sys = arena.getSystem('kem768')!;
      const ks = arena.buildGovernanceKeyspace(sys);

      // Take snapshot before breathing
      const snap1 = ks.snapshot();
      const axes1Values = snap1.axes.filter((a) => a.temporal).map((a) => a.currentValue);

      // Breathe — the stairwell rotates
      ks.breathe();

      // Take snapshot after breathing
      const snap2 = ks.snapshot();
      const axes2Values = snap2.axes.filter((a) => a.temporal).map((a) => a.currentValue);

      // Temporal axis values should have shifted
      expect(axes2Values).not.toEqual(axes1Values);

      // Shift count should have increased
      expect(snap2.shiftCount).toBeGreaterThan(snap1.shiftCount);

      // Effective bits stay the same (the SPACE is the same size)
      expect(snap2.effectiveBits).toBe(snap1.effectiveBits);

      // But the TARGET within that space has moved
      // This is the key insight: the attacker's search so far
      // is now in the WRONG part of the space
    });

    it('should show that multiple breathe cycles compound shifts', () => {
      const sys = arena.getSystem('kem768')!;
      const ks = arena.buildGovernanceKeyspace(sys);

      const snap0 = ks.snapshot();
      const initialShifts = snap0.shiftCount;

      // 10 breathing cycles
      for (let i = 0; i < 10; i++) {
        ks.breathe();
      }

      const snap10 = ks.snapshot();
      // 4 temporal axes × 10 cycles = 40 shifts
      expect(snap10.shiftCount).toBe(initialShifts + 40);
    });
  });
});

// ============================================================================
// ARENA_SYSTEMS Static Data Tests
// ============================================================================

describe('ARENA_SYSTEMS catalog', () => {
  it('should have correct FIPS 203 KEM parameters', () => {
    for (const sys of ARENA_SYSTEMS.filter((s) => s.standard === 'FIPS 203')) {
      expect(sys.primitive).toBe('kem');
      expect(sys.sharedSecretBytes).toBe(32);
      expect(sys.family).toBe('lattice');
    }
  });

  it('should have correct FIPS 204 signature parameters', () => {
    for (const sys of ARENA_SYSTEMS.filter((s) => s.standard === 'FIPS 204')) {
      expect(sys.primitive).toBe('signature');
      expect(sys.sharedSecretBytes).toBe(0);
      expect(sys.family).toBe('lattice');
    }
  });

  it('should have correct FIPS 205 hash-based parameters', () => {
    for (const sys of ARENA_SYSTEMS.filter((s) => s.standard === 'FIPS 205')) {
      expect(sys.primitive).toBe('signature');
      expect(sys.family).toBe('hash-based');
      // Hash-based sigs have tiny keys
      expect(sys.publicKeyBytes).toBeLessThanOrEqual(64);
    }
  });

  it('should cover all three major PQC families', () => {
    const families = new Set(ARENA_SYSTEMS.map((s) => s.family));
    expect(families).toContain('lattice');
    expect(families).toContain('code-based');
    expect(families).toContain('hash-based');
  });

  it('should cover NIST levels 1, 2, 3, and 5', () => {
    const levels = new Set(ARENA_SYSTEMS.map((s) => s.nistLevel));
    expect(levels).toContain(1);
    expect(levels).toContain(2);
    expect(levels).toContain(3);
    expect(levels).toContain(5);
  });
});
