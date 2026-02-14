/**
 * @file sacredEggsGenesis.test.ts
 * @module harmonic/sacredEggsGenesis.test
 * @layer Layer 12, Layer 13
 * Tests for the Sacred Eggs Genesis Gate (Agent-Only Scope v1).
 */

import { describe, it, expect } from 'vitest';
import {
  computeHatchWeight,
  geoSealDistance,
  evaluateGenesis,
  genesis,
  verifyCertificateSeal,
  GENESIS_THRESHOLD,
  DEFAULT_GEOSEAL_MAX_DISTANCE,
  DEFAULT_GENESIS_CONFIG,
  type GenesisConfig,
} from '../../src/harmonic/sacredEggsGenesis.js';
import type {
  SacredEgg,
  VerifierState,
  EggPolicy,
  Approval,
  Tongue,
} from '../../src/harmonic/sacredEggs.js';

const PHI = (1 + Math.sqrt(5)) / 2;

// ═══════════════════════════════════════════════════════════════
// Test Helpers
// ═══════════════════════════════════════════════════════════════

function makePolicy(overrides: Partial<EggPolicy> = {}): EggPolicy {
  return {
    primaryTongue: 'KO' as Tongue,
    maxRing: 4,
    quorumRequired: 2,
    ...overrides,
  };
}

function makeApproval(id: string): Approval {
  return {
    approverId: id,
    signature: new Uint8Array([1, 2, 3]),
    timestamp: Date.now(),
  };
}

function makeEgg(overrides: Partial<SacredEgg> = {}): SacredEgg {
  return {
    header: { id: 'test-egg-1', epoch: Date.now(), policyHash: 'abc' },
    ciphertext: new Uint8Array(32),
    tag: new Uint8Array(16),
    policy: makePolicy(),
    dst: new Uint8Array(0),
    ...overrides,
  };
}

function makeState(overrides: Partial<VerifierState> = {}): VerifierState {
  return {
    observedTongue: 'KO' as Tongue,
    validTongues: new Set<Tongue>(['KO', 'AV', 'RU']),
    position: [0.1, 0.1, 0.0],
    policyCell: [0, 0, 0],
    ringHistory: [4, 3, 2, 1, 0],
    approvals: [makeApproval('A'), makeApproval('B'), makeApproval('C')],
    sharedSecret: new Uint8Array([10, 20, 30, 40]),
    ...overrides,
  };
}

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════

describe('Genesis Constants', () => {
  it('GENESIS_THRESHOLD equals φ³', () => {
    expect(GENESIS_THRESHOLD).toBeCloseTo(PHI * PHI * PHI);
  });

  it('GENESIS_THRESHOLD ≈ 4.236', () => {
    expect(GENESIS_THRESHOLD).toBeCloseTo(4.236, 2);
  });

  it('DEFAULT_GEOSEAL_MAX_DISTANCE is 2.0', () => {
    expect(DEFAULT_GEOSEAL_MAX_DISTANCE).toBe(2.0);
  });
});

// ═══════════════════════════════════════════════════════════════
// Hatch Weight
// ═══════════════════════════════════════════════════════════════

describe('computeHatchWeight', () => {
  it('returns 0 when no predicates pass', () => {
    expect(computeHatchWeight([false, false, false, false, false])).toBe(0);
  });

  it('returns sum of φ^k_i for passed predicates', () => {
    // All pass with default ranks [0,1,2,3,4]
    const W = computeHatchWeight([true, true, true, true, true]);
    const expected = 1 + PHI + PHI ** 2 + PHI ** 3 + PHI ** 4;
    expect(W).toBeCloseTo(expected);
  });

  it('returns φ^0 = 1 when only first predicate passes', () => {
    expect(computeHatchWeight([true, false, false, false, false])).toBeCloseTo(1.0);
  });

  it('weights higher ranks more heavily', () => {
    // Only rank 4 passes
    const W4 = computeHatchWeight([false, false, false, false, true]);
    // Only rank 0 passes
    const W0 = computeHatchWeight([true, false, false, false, false]);
    expect(W4).toBeGreaterThan(W0);
  });

  it('respects custom ranks', () => {
    const W = computeHatchWeight([true, false, false, false, false], [5, 0, 0, 0, 0]);
    expect(W).toBeCloseTo(PHI ** 5);
  });

  it('returns ≥ GENESIS_THRESHOLD when 3+ high-rank predicates pass', () => {
    // Ranks [0,1,2,3,4], first 3 pass: W = 1 + φ + φ² = 1 + 1.618 + 2.618 = 5.236
    const W = computeHatchWeight([true, true, true, false, false]);
    expect(W).toBeGreaterThanOrEqual(GENESIS_THRESHOLD);
  });
});

// ═══════════════════════════════════════════════════════════════
// GeoSeal Distance
// ═══════════════════════════════════════════════════════════════

describe('geoSealDistance', () => {
  it('returns 0 at origin', () => {
    expect(geoSealDistance([0, 0, 0])).toBeCloseTo(0);
  });

  it('returns positive value for non-origin points', () => {
    expect(geoSealDistance([0.5, 0, 0])).toBeGreaterThan(0);
  });

  it('increases with radius', () => {
    const d1 = geoSealDistance([0.3, 0, 0]);
    const d2 = geoSealDistance([0.6, 0, 0]);
    expect(d2).toBeGreaterThan(d1);
  });

  it('approaches infinity near boundary', () => {
    const d = geoSealDistance([0.999, 0, 0]);
    expect(d).toBeGreaterThan(5);
  });

  it('computes 2·arctanh(‖u‖) correctly', () => {
    // ‖u‖ = 0.5 → 2·arctanh(0.5) = 2·0.5493 ≈ 1.0986
    const d = geoSealDistance([0.5, 0, 0]);
    expect(d).toBeCloseTo(2 * Math.atanh(0.5));
  });

  it('handles multidimensional positions', () => {
    // ‖u‖ = sqrt(0.3² + 0.4²) = 0.5
    const d = geoSealDistance([0.3, 0.4]);
    expect(d).toBeCloseTo(2 * Math.atanh(0.5));
  });
});

// ═══════════════════════════════════════════════════════════════
// Genesis Evaluation
// ═══════════════════════════════════════════════════════════════

describe('evaluateGenesis', () => {
  it('grants genesis when all predicates pass', () => {
    const egg = makeEgg();
    const state = makeState();
    const eval_ = evaluateGenesis(egg, state);
    expect(eval_.genesisGranted).toBe(true);
    expect(eval_.meetsThreshold).toBe(true);
    expect(eval_.geoSealPassed).toBe(true);
  });

  it('denies genesis when tongue mismatch', () => {
    const egg = makeEgg({ policy: makePolicy({ primaryTongue: 'DR' as Tongue }) });
    const state = makeState({ observedTongue: 'KO' as Tongue });
    const eval_ = evaluateGenesis(egg, state);
    expect(eval_.predicateResults[0]).toBe(false);
    expect(eval_.genesisGranted).toBe(false);
  });

  it('denies genesis when GeoSeal distance exceeded', () => {
    const state = makeState({ position: [0.999, 0, 0] });
    const eval_ = evaluateGenesis(makeEgg(), state, { geoSealMaxDistance: 0.5 });
    expect(eval_.geoSealPassed).toBe(false);
    expect(eval_.genesisGranted).toBe(false);
  });

  it('denies genesis when quorum insufficient (3of3 mode)', () => {
    const state = makeState({
      approvals: [makeApproval('A'), makeApproval('B')],
    });
    const eval_ = evaluateGenesis(makeEgg(), state, { quorumMode: '3of3' });
    expect(eval_.genesisGranted).toBe(false);
  });

  it('grants genesis with 2 approvals in 2of3 mode', () => {
    const state = makeState({
      approvals: [makeApproval('A'), makeApproval('B')],
    });
    const eval_ = evaluateGenesis(makeEgg(), state, { quorumMode: '2of3' });
    expect(eval_.genesisGranted).toBe(true);
  });

  it('denies genesis when path is not monotone descending', () => {
    const state = makeState({ ringHistory: [2, 3, 1] }); // Not strictly descending
    const eval_ = evaluateGenesis(makeEgg(), state);
    expect(eval_.predicateResults[2]).toBe(false);
    expect(eval_.genesisGranted).toBe(false);
  });

  it('denies genesis when shared secret is empty', () => {
    const state = makeState({ sharedSecret: new Uint8Array(0) });
    const eval_ = evaluateGenesis(makeEgg(), state);
    expect(eval_.predicateResults[4]).toBe(false);
    // Hatch weight will be lower without crypto predicate
  });

  it('computes correct hatch weight', () => {
    const egg = makeEgg();
    const state = makeState();
    const eval_ = evaluateGenesis(egg, state);
    // All 5 predicates pass with default ranks [0,1,2,3,4]
    const expectedW = 1 + PHI + PHI ** 2 + PHI ** 3 + PHI ** 4;
    expect(eval_.hatchWeight).toBeCloseTo(expectedW);
  });

  it('reports correct GeoSeal distance', () => {
    const state = makeState({ position: [0.5, 0, 0] });
    const eval_ = evaluateGenesis(makeEgg(), state);
    expect(eval_.geoSealDistance).toBeCloseTo(2 * Math.atanh(0.5));
  });
});

// ═══════════════════════════════════════════════════════════════
// Genesis Gate (Main Function)
// ═══════════════════════════════════════════════════════════════

describe('genesis', () => {
  it('spawns agent with valid inputs', () => {
    const result = genesis(makeEgg(), makeState());
    expect(result.spawned).toBe(true);
    if (result.spawned) {
      expect(result.certificate.agentId).toBeTruthy();
      expect(result.certificate.tongueDomain).toBe('KO');
      expect(result.certificate.epoch).toBeGreaterThan(0);
      expect(result.certificate.hatchWeight).toBeGreaterThanOrEqual(GENESIS_THRESHOLD);
      expect(result.certificate.genesisSeal).toBeTruthy();
      expect(result.serialized.length).toBe(256);
    }
  });

  it('returns noise on failure', () => {
    const egg = makeEgg({ policy: makePolicy({ primaryTongue: 'DR' as Tongue }) });
    const state = makeState({ observedTongue: 'KO' as Tongue });
    const result = genesis(egg, state);
    expect(result.spawned).toBe(false);
    if (!result.spawned) {
      expect(result.output.length).toBe(256);
    }
  });

  it('fail-to-noise: failure output length equals success output length', () => {
    const successResult = genesis(makeEgg(), makeState());
    const failEgg = makeEgg({ policy: makePolicy({ primaryTongue: 'DR' as Tongue }) });
    const failResult = genesis(failEgg, makeState({ observedTongue: 'KO' as Tongue }));

    const successLen = successResult.spawned ? successResult.serialized.length : 0;
    const failLen = !failResult.spawned ? failResult.output.length : 0;
    expect(successLen).toBe(failLen);
  });

  it('generates unique agent IDs', () => {
    const r1 = genesis(makeEgg(), makeState());
    const r2 = genesis(makeEgg(), makeState());
    if (r1.spawned && r2.spawned) {
      expect(r1.certificate.agentId).not.toBe(r2.certificate.agentId);
    }
  });

  it('assigns ring level from position', () => {
    // Position at origin → ring 0
    const result = genesis(makeEgg(), makeState({ position: [0.05, 0, 0] }));
    if (result.spawned) {
      expect(result.certificate.ringLevel).toBe(0);
    }
  });

  it('assigns correct tongue domain from policy', () => {
    const egg = makeEgg({ policy: makePolicy({ primaryTongue: 'AV' as Tongue }) });
    const state = makeState({ observedTongue: 'AV' as Tongue });
    const result = genesis(egg, state);
    if (result.spawned) {
      expect(result.certificate.tongueDomain).toBe('AV');
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Certificate Seal Verification
// ═══════════════════════════════════════════════════════════════

describe('verifyCertificateSeal', () => {
  it('verifies a valid certificate', () => {
    const result = genesis(makeEgg(), makeState());
    if (result.spawned) {
      expect(verifyCertificateSeal(result.certificate)).toBe(true);
    }
  });

  it('rejects tampered agent ID', () => {
    const result = genesis(makeEgg(), makeState());
    if (result.spawned) {
      const tampered = { ...result.certificate, agentId: 'tampered-id' };
      expect(verifyCertificateSeal(tampered)).toBe(false);
    }
  });

  it('rejects tampered hatch weight', () => {
    const result = genesis(makeEgg(), makeState());
    if (result.spawned) {
      const tampered = { ...result.certificate, hatchWeight: 999 };
      expect(verifyCertificateSeal(tampered)).toBe(false);
    }
  });

  it('rejects tampered tongue domain', () => {
    const result = genesis(makeEgg(), makeState());
    if (result.spawned) {
      const tampered = { ...result.certificate, tongueDomain: 'DR' as Tongue };
      expect(verifyCertificateSeal(tampered)).toBe(false);
    }
  });

  it('rejects tampered predicate results', () => {
    const result = genesis(makeEgg(), makeState());
    if (result.spawned) {
      const tampered = {
        ...result.certificate,
        predicatesPassed: [false, false, false, false, false] as [boolean, boolean, boolean, boolean, boolean],
      };
      expect(verifyCertificateSeal(tampered)).toBe(false);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Edge Cases
// ═══════════════════════════════════════════════════════════════

describe('Edge Cases', () => {
  it('handles empty ring history (path predicate passes)', () => {
    const state = makeState({ ringHistory: [] });
    const eval_ = evaluateGenesis(makeEgg(), state);
    expect(eval_.predicateResults[2]).toBe(true);
  });

  it('handles zero-dimension position', () => {
    const state = makeState({ position: [] });
    expect(geoSealDistance(state.position)).toBeCloseTo(0);
  });

  it('handles high-dimensional position', () => {
    const pos = new Array(21).fill(0.01);
    const d = geoSealDistance(pos);
    expect(d).toBeGreaterThan(0);
    expect(Number.isFinite(d)).toBe(true);
  });

  it('custom predicate ranks change weight computation', () => {
    // Swap importance: crypto (rank 4) becomes rank 0
    const W_default = computeHatchWeight([false, false, false, false, true]);
    const W_custom = computeHatchWeight([false, false, false, false, true], [4, 3, 2, 1, 0]);
    expect(W_default).toBeCloseTo(PHI ** 4);
    expect(W_custom).toBeCloseTo(1.0); // rank 0 → φ^0 = 1
  });
});
