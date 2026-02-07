/**
 * @file sacredEggs.test.ts
 * @description Hard-wall experiments for Sacred Eggs
 *
 * These experiments provide clean "pass/fail" evidence for the patent claims.
 *
 * SE-1: Predicate gating matrix (16 cases, only 1,1,1,1 decrypts)
 * SE-2: Output collapse check (all failures look the same)
 * SE-3: Wrong-geometry key separation
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  SacredEgg,
  VerifierState,
  EggPolicy,
  Tongue,
  RingLevel,
  Approval,
  hatch,
  createEgg,
  predicateTongue,
  predicateGeo,
  predicatePath,
  predicateQuorum,
  getRingLevel,
  HatchResult,
} from '../../src/harmonic/sacredEggs';

// ═══════════════════════════════════════════════════════════════
// Test Fixtures
// ═══════════════════════════════════════════════════════════════

function createTestPolicy(): EggPolicy {
  return {
    primaryTongue: 'KO',
    maxRing: 2 as RingLevel,
    quorumRequired: 1,
    allowedCells: [[0.5, 0.5]],
    attractors: [[0.1, 0.1, 0.1]],
    maxGeoDistance: 1.0,
  };
}

function createValidState(): VerifierState {
  return {
    observedTongue: 'KO',
    validTongues: new Set(['KO']),
    position: [0.1, 0.1, 0.1], // Inside ball, near attractor
    policyCell: [0.5, 0.5],
    ringHistory: [4, 3, 2, 1, 0] as RingLevel[], // Strict descent to core
    approvals: [
      {
        approverId: 'approver-1',
        signature: new Uint8Array(64),
        timestamp: Date.now(),
      },
    ],
    sharedSecret: new Uint8Array(32).fill(0x42),
  };
}

// ═══════════════════════════════════════════════════════════════
// SE-1: Predicate Gating Matrix
// ═══════════════════════════════════════════════════════════════

describe('SE-1: Predicate Gating Matrix', () => {
  /**
   * Test all 16 combinations of predicate pass/fail.
   * Only (tongue=1, geo=1, path=1, quorum=1) should decrypt.
   */

  const testCases: Array<{
    tongue: boolean;
    geo: boolean;
    path: boolean;
    quorum: boolean;
    shouldDecrypt: boolean;
  }> = [];

  // Generate all 16 combinations
  for (let t = 0; t <= 1; t++) {
    for (let g = 0; g <= 1; g++) {
      for (let p = 0; p <= 1; p++) {
        for (let q = 0; q <= 1; q++) {
          testCases.push({
            tongue: t === 1,
            geo: g === 1,
            path: p === 1,
            quorum: q === 1,
            shouldDecrypt: t === 1 && g === 1 && p === 1 && q === 1,
          });
        }
      }
    }
  }

  it.each(testCases)(
    'tongue=$tongue, geo=$geo, path=$path, quorum=$quorum → decrypt=$shouldDecrypt',
    async ({ tongue, geo, path, quorum, shouldDecrypt }) => {
      const policy = createTestPolicy();
      const validState = createValidState();
      const plaintext = new TextEncoder().encode('SECRET_DATA_12345');

      // Create egg with valid state
      const egg = await createEgg(plaintext, policy, validState.sharedSecret, validState);

      // Create test state with controlled predicate outcomes
      const testState: VerifierState = {
        // Tongue: correct or wrong
        observedTongue: tongue ? 'KO' : 'DR',
        validTongues: tongue ? new Set(['KO']) : new Set(['DR']),

        // Geo: valid position or boundary position
        position: geo ? [0.1, 0.1, 0.1] : [0.9, 0.9, 0.9],
        policyCell: geo ? [0.5, 0.5] : [0.9, 0.9],

        // Path: strict descent or non-descent
        ringHistory: path
          ? ([4, 3, 2, 1, 0] as RingLevel[])
          : ([1, 2, 3] as RingLevel[]), // Wrong: ascending

        // Quorum: sufficient approvals or none
        approvals: quorum
          ? [{ approverId: 'a1', signature: new Uint8Array(64), timestamp: Date.now() }]
          : [],

        sharedSecret: validState.sharedSecret,
      };

      const result = await hatch(egg, testState);

      if (shouldDecrypt) {
        expect(result.success).toBe(true);
        if (result.success) {
          const decoded = new TextDecoder().decode(result.plaintext);
          expect(decoded).toBe('SECRET_DATA_12345');
        }
      } else {
        expect(result.success).toBe(false);
      }
    }
  );

  it('confirms exactly 1 of 16 cases decrypts', async () => {
    let successCount = 0;

    for (const tc of testCases) {
      const policy = createTestPolicy();
      const validState = createValidState();
      const plaintext = new TextEncoder().encode('TEST');
      const egg = await createEgg(plaintext, policy, validState.sharedSecret, validState);

      const testState: VerifierState = {
        observedTongue: tc.tongue ? 'KO' : 'DR',
        validTongues: tc.tongue ? new Set(['KO']) : new Set(['DR']),
        position: tc.geo ? [0.1, 0.1, 0.1] : [0.9, 0.9, 0.9],
        policyCell: tc.geo ? [0.5, 0.5] : [0.9, 0.9],
        ringHistory: tc.path ? ([4, 3, 2, 1, 0] as RingLevel[]) : ([1, 2, 3] as RingLevel[]),
        approvals: tc.quorum
          ? [{ approverId: 'a1', signature: new Uint8Array(64), timestamp: Date.now() }]
          : [],
        sharedSecret: validState.sharedSecret,
      };

      const result = await hatch(egg, testState);
      if (result.success) successCount++;
    }

    expect(successCount).toBe(1);
  });
});

// ═══════════════════════════════════════════════════════════════
// SE-2: Output Collapse Check
// ═══════════════════════════════════════════════════════════════

describe('SE-2: Output Collapse Check', () => {
  /**
   * Collect outputs from all 15 failure cases:
   * - Check same length distribution
   * - Check same content class (random-looking)
   * - Check no error code leakage
   */

  it('all failure outputs have same length', async () => {
    const policy = createTestPolicy();
    const validState = createValidState();
    const plaintext = new TextEncoder().encode('SECRET_DATA_12345');
    const egg = await createEgg(plaintext, policy, validState.sharedSecret, validState);

    const lengths: number[] = [];

    // Test various failure conditions
    const failureStates: VerifierState[] = [
      // Wrong tongue
      { ...validState, observedTongue: 'DR' as Tongue, validTongues: new Set(['DR' as Tongue]) },
      // Wrong position (outside ring)
      { ...validState, position: [0.95, 0.0, 0.0] },
      // Wrong cell
      { ...validState, policyCell: [0.9, 0.9] },
      // Wrong path (not descending)
      { ...validState, ringHistory: [1, 2, 3, 4] as RingLevel[] },
      // No approvals
      { ...validState, approvals: [] },
      // Wrong shared secret
      { ...validState, sharedSecret: new Uint8Array(32).fill(0x00) },
    ];

    for (const state of failureStates) {
      const result = await hatch(egg, state);
      expect(result.success).toBe(false);
      if (!result.success) {
        lengths.push(result.output.length);
      }
    }

    // All failure outputs should have the same length
    const uniqueLengths = new Set(lengths);
    expect(uniqueLengths.size).toBe(1);
    expect(lengths[0]).toBe(egg.ciphertext.length);
  });

  it('failure outputs look random (high entropy)', async () => {
    const policy = createTestPolicy();
    const validState = createValidState();
    const plaintext = new TextEncoder().encode('AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'); // Uniform
    const egg = await createEgg(plaintext, policy, validState.sharedSecret, validState);

    // Wrong tongue → failure
    const failState = {
      ...validState,
      observedTongue: 'DR' as Tongue,
      validTongues: new Set(['DR' as Tongue]),
    };
    const result = await hatch(egg, failState);

    expect(result.success).toBe(false);
    if (!result.success) {
      // Check output is not all zeros or all same value
      const uniqueBytes = new Set(result.output);
      expect(uniqueBytes.size).toBeGreaterThan(1); // Should have variety

      // Check output is not the plaintext
      const outputStr = new TextDecoder().decode(result.output);
      expect(outputStr).not.toBe('AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA');
    }
  });

  it('no error codes leak in failure outputs', async () => {
    const policy = createTestPolicy();
    const validState = createValidState();
    const plaintext = new TextEncoder().encode('SECRET');
    const egg = await createEgg(plaintext, policy, validState.sharedSecret, validState);

    // Collect failure outputs from different failure modes
    const outputs: Uint8Array[] = [];

    const failureModes = [
      { ...validState, observedTongue: 'DR' as Tongue }, // Tongue fail
      { ...validState, position: [0.95, 0.0, 0.0] }, // Geo fail
      { ...validState, ringHistory: [1, 2, 3] as RingLevel[] }, // Path fail
      { ...validState, approvals: [] }, // Quorum fail
    ];

    for (const state of failureModes) {
      const result = await hatch(egg, state);
      if (!result.success) {
        outputs.push(result.output);
      }
    }

    // Check no outputs contain recognizable error strings
    const errorPatterns = ['ERROR', 'FAIL', 'TONGUE', 'GEO', 'PATH', 'QUORUM', 'DENIED'];
    for (const output of outputs) {
      const str = new TextDecoder().decode(output);
      for (const pattern of errorPatterns) {
        expect(str.toUpperCase()).not.toContain(pattern);
      }
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// SE-3: Wrong-Geometry Key Separation
// ═══════════════════════════════════════════════════════════════

describe('SE-3: Wrong-Geometry Key Separation', () => {
  /**
   * Hold everything constant except geometry parameters used in key derivation.
   * Measure AEAD failure rate goes to ~100% once geometry mismatches.
   */

  it('same geometry → successful decryption', async () => {
    const policy = createTestPolicy();
    const validState = createValidState();
    const plaintext = new TextEncoder().encode('GEOMETRY_TEST');
    const egg = await createEgg(plaintext, policy, validState.sharedSecret, validState);

    const result = await hatch(egg, validState);
    expect(result.success).toBe(true);
  });

  it('different ring level → decryption fails', async () => {
    const policy = createTestPolicy();
    const validState = createValidState();
    validState.ringHistory = [4, 3, 2, 1, 0] as RingLevel[]; // Ends at ring 0

    const plaintext = new TextEncoder().encode('RING_TEST');
    const egg = await createEgg(plaintext, policy, validState.sharedSecret, validState);

    // Same everything, but different current ring (via position)
    const altState: VerifierState = {
      ...validState,
      position: [0.5, 0.0, 0.0], // Ring 2 instead of ring 0
    };

    // Even if predicates pass, key derivation uses different ring → AEAD fails
    const result = await hatch(egg, altState);

    // This tests the cryptographic binding to geometry
    // The key is derived from ring level, so wrong ring = wrong key = decryption fails
    expect(result.success).toBe(false);
  });

  it('different policy cell → decryption fails', async () => {
    const policy = createTestPolicy();
    policy.allowedCells = [[0.5, 0.5], [0.6, 0.6]]; // Allow multiple cells

    const validState = createValidState();
    validState.policyCell = [0.5, 0.5];

    const plaintext = new TextEncoder().encode('CELL_TEST');
    const egg = await createEgg(plaintext, policy, validState.sharedSecret, validState);

    // Different cell (still allowed by policy, but different key)
    const altState: VerifierState = {
      ...validState,
      policyCell: [0.6, 0.6], // Different cell
    };

    // Key derivation includes cell → different key → AEAD fails
    const result = await hatch(egg, altState);
    expect(result.success).toBe(false);
  });

  it('different path history → decryption fails', async () => {
    const policy = createTestPolicy();
    const validState = createValidState();
    validState.ringHistory = [4, 3, 2, 1, 0] as RingLevel[];

    const plaintext = new TextEncoder().encode('PATH_TEST');
    const egg = await createEgg(plaintext, policy, validState.sharedSecret, validState);

    // Same final ring, but different path
    const altState: VerifierState = {
      ...validState,
      ringHistory: [3, 2, 1, 0] as RingLevel[], // Shorter path
    };

    // Key derivation includes path digest → different key → AEAD fails
    const result = await hatch(egg, altState);
    expect(result.success).toBe(false);
  });

  it('different ring levels cause 100% failure rate', async () => {
    const policy = createTestPolicy();
    policy.maxRing = 4; // Allow all rings for predicate to pass

    const validState = createValidState();
    validState.position = [0.1, 0.0, 0.0]; // Ring 0 (radius 0.1 < 0.2)

    const plaintext = new TextEncoder().encode('BATCH_TEST');
    const egg = await createEgg(plaintext, policy, validState.sharedSecret, validState);

    let failures = 0;

    // Test each different ring level (1-4, since egg was created with ring 0)
    const testPositions = [
      [0.3, 0.0, 0.0],  // Ring 1 (0.2 < 0.3 < 0.4)
      [0.5, 0.0, 0.0],  // Ring 2 (0.4 < 0.5 < 0.6)
      [0.7, 0.0, 0.0],  // Ring 3 (0.6 < 0.7 < 0.8)
      [0.9, 0.0, 0.0],  // Ring 4 (0.8 < 0.9 < 0.95)
    ];

    for (const pos of testPositions) {
      const altState: VerifierState = {
        ...validState,
        position: pos,
      };

      const result = await hatch(egg, altState);
      if (!result.success) failures++;
    }

    // All should fail (key bound to ring 0, but we're using rings 1-4)
    expect(failures).toBe(testPositions.length);
  });
});

// ═══════════════════════════════════════════════════════════════
// Individual Predicate Unit Tests
// ═══════════════════════════════════════════════════════════════

describe('Predicate Unit Tests', () => {
  describe('predicateTongue', () => {
    it('solitary mode: exact match passes', () => {
      const egg = { policy: { primaryTongue: 'KO' as Tongue } } as SacredEgg;
      const state = { observedTongue: 'KO' as Tongue, validTongues: new Set() } as VerifierState;
      expect(predicateTongue(egg, state)).toBe(true);
    });

    it('solitary mode: mismatch fails', () => {
      const egg = { policy: { primaryTongue: 'KO' as Tongue } } as SacredEgg;
      const state = { observedTongue: 'DR' as Tongue, validTongues: new Set() } as VerifierState;
      expect(predicateTongue(egg, state)).toBe(false);
    });

    it('multi-tongue mode: sufficient weight passes', () => {
      const egg = {
        policy: {
          primaryTongue: 'KO' as Tongue,
          requiredTongues: ['KO', 'AV', 'RU'] as Tongue[],
          minWeightSum: 2.0,
        },
      } as SacredEgg;
      const state = {
        observedTongue: 'KO' as Tongue,
        validTongues: new Set(['KO', 'AV'] as Tongue[]),
      } as VerifierState;
      expect(predicateTongue(egg, state)).toBe(true);
    });

    it('multi-tongue mode: insufficient weight fails', () => {
      const egg = {
        policy: {
          primaryTongue: 'KO' as Tongue,
          requiredTongues: ['KO', 'AV', 'RU'] as Tongue[],
          minWeightSum: 3.0,
        },
      } as SacredEgg;
      const state = {
        observedTongue: 'KO' as Tongue,
        validTongues: new Set(['KO', 'AV'] as Tongue[]),
      } as VerifierState;
      expect(predicateTongue(egg, state)).toBe(false);
    });
  });

  describe('predicatePath', () => {
    it('strict descent passes', () => {
      const egg = { policy: {} } as SacredEgg;
      const state = { ringHistory: [4, 3, 2, 1, 0] as RingLevel[] } as VerifierState;
      expect(predicatePath(egg, state)).toBe(true);
    });

    it('non-descent fails', () => {
      const egg = { policy: {} } as SacredEgg;
      const state = { ringHistory: [1, 2, 3] as RingLevel[] } as VerifierState;
      expect(predicatePath(egg, state)).toBe(false);
    });

    it('plateau fails', () => {
      const egg = { policy: {} } as SacredEgg;
      const state = { ringHistory: [3, 2, 2, 1] as RingLevel[] } as VerifierState;
      expect(predicatePath(egg, state)).toBe(false);
    });

    it('empty history passes', () => {
      const egg = { policy: {} } as SacredEgg;
      const state = { ringHistory: [] } as VerifierState;
      expect(predicatePath(egg, state)).toBe(true);
    });
  });

  describe('getRingLevel', () => {
    it('maps radii to correct rings', () => {
      expect(getRingLevel(0.1)).toBe(0); // Core
      expect(getRingLevel(0.3)).toBe(1); // Inner
      expect(getRingLevel(0.5)).toBe(2); // Middle
      expect(getRingLevel(0.7)).toBe(3); // Outer
      expect(getRingLevel(0.9)).toBe(4); // Edge
      expect(getRingLevel(0.99)).toBe(4); // Edge
    });
  });
});
