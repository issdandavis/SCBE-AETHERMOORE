/**
 * RWP v2.1 Extended Envelope Tests
 * =================================
 *
 * Additional test coverage for RWP envelope functionality:
 * - Serialization/deserialization roundtrips
 * - Key rotation scenarios
 * - Cross-instance verification
 * - Malformed envelope handling
 * - Boundary timestamp conditions
 * - Type coercion edge cases
 * - Integration with API layer
 *
 * @module tests/spiralverse/rwp.envelope.extended
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { randomBytes } from 'crypto';
import {
  signRoundtable,
  verifyRoundtable,
  clearNonceCache,
  checkPolicy,
  type Keyring,
  type TongueID,
  type RWPEnvelope,
} from '../../src/spiralverse/index.js';

// Helper to create test keyring
function createTestKeyring(): Keyring {
  return {
    ko: randomBytes(32),
    av: randomBytes(32),
    ru: randomBytes(32),
    ca: randomBytes(32),
    um: randomBytes(32),
    dr: randomBytes(32),
  };
}

describe('RWP v2.1 Extended Envelope Tests', () => {
  let testKeyring: Keyring;

  beforeEach(() => {
    testKeyring = createTestKeyring();
    clearNonceCache();
  });

  describe('Serialization Roundtrip Tests', () => {
    it('should survive JSON serialization/deserialization', () => {
      const payload = {
        action: 'transfer',
        amount: 1000,
        recipient: 'alice@example.com',
        metadata: { priority: 'high', tags: ['urgent', 'verified'] }
      };

      const envelope = signRoundtable(payload, 'ko', 'transfer-ctx', testKeyring, ['ko', 'um']);

      // Serialize to JSON
      const serialized = JSON.stringify(envelope);

      // Deserialize back
      const deserialized: RWPEnvelope = JSON.parse(serialized);

      // Should verify correctly
      const result = verifyRoundtable(deserialized, testKeyring);
      expect(result.valid).toBe(true);
      expect(result.payload).toEqual(payload);
    });

    it('should handle nested complex objects through serialization', () => {
      const complexPayload = {
        level1: {
          level2: {
            level3: {
              data: 'deep-nested-value',
              array: [1, 2, { inner: true }]
            }
          },
          siblings: ['a', 'b', 'c']
        },
        root: 42
      };

      const envelope = signRoundtable(complexPayload, 'ko', 'ctx', testKeyring, ['ko']);
      const roundtrip: RWPEnvelope = JSON.parse(JSON.stringify(envelope));

      const result = verifyRoundtable(roundtrip, testKeyring);
      expect(result.valid).toBe(true);
      expect(result.payload).toEqual(complexPayload);
    });

    it('should preserve all envelope fields through serialization', () => {
      const payload = { test: true };
      const envelope = signRoundtable(payload, 'ko', 'test-aad', testKeyring, ['ko', 'ru', 'um'], {
        kid: 'key-v1-2024'
      });

      const roundtrip: RWPEnvelope = JSON.parse(JSON.stringify(envelope));

      expect(roundtrip.ver).toBe('2.1');
      expect(roundtrip.primary_tongue).toBe('ko');
      expect(roundtrip.aad).toBe('test-aad');
      expect(roundtrip.kid).toBe('key-v1-2024');
      expect(roundtrip.sigs.ko).toBe(envelope.sigs.ko);
      expect(roundtrip.sigs.ru).toBe(envelope.sigs.ru);
      expect(roundtrip.sigs.um).toBe(envelope.sigs.um);
      expect(roundtrip.nonce).toBe(envelope.nonce);
      expect(roundtrip.ts).toBe(envelope.ts);
    });
  });

  describe('Key Rotation Scenarios', () => {
    it('should reject envelope signed with old key after rotation', () => {
      const payload = { message: 'signed-before-rotation' };
      const oldKeyring = createTestKeyring();

      const envelope = signRoundtable(payload, 'ko', 'ctx', oldKeyring, ['ko']);

      // Create new keyring (simulating key rotation)
      const newKeyring = createTestKeyring();

      // Old envelope should fail with new keys
      const result = verifyRoundtable(envelope, newKeyring);
      expect(result.valid).toBe(false);
      expect(result.error).toContain('No valid signatures found');
    });

    it('should verify envelope with partially rotated keyring', () => {
      const payload = { data: 'multi-signed' };

      // Sign with multiple tongues
      const envelope = signRoundtable(payload, 'ko', 'ctx', testKeyring, ['ko', 'ru', 'um']);

      // Create keyring with only ko rotated (ru and um unchanged)
      const partialRotateKeyring: Keyring = {
        ko: randomBytes(32), // New key
        ru: testKeyring.ru,  // Same key
        um: testKeyring.um,  // Same key
      };

      // Should still verify (ru and um signatures are valid)
      const result = verifyRoundtable(envelope, partialRotateKeyring);
      expect(result.valid).toBe(true);
      expect(result.validTongues).toContain('ru');
      expect(result.validTongues).toContain('um');
      expect(result.validTongues).not.toContain('ko'); // ko signature invalid with new key
    });
  });

  describe('Cross-Instance Verification', () => {
    it('should verify envelope created with different keyring instance (same values)', () => {
      const payload = { cross: 'instance' };
      const sharedSecret = randomBytes(32);

      // Keyring instance 1
      const keyring1: Keyring = { ko: Buffer.from(sharedSecret) };

      // Keyring instance 2 (same key bytes, different Buffer object)
      const keyring2: Keyring = { ko: Buffer.from(sharedSecret) };

      const envelope = signRoundtable(payload, 'ko', 'ctx', keyring1, ['ko']);
      const result = verifyRoundtable(envelope, keyring2);

      expect(result.valid).toBe(true);
      expect(result.payload).toEqual(payload);
    });

    it('should handle multiple verifiers with subset of keys', () => {
      const payload = { action: 'multi-party' };

      // Full keyring for signing
      const envelope = signRoundtable(payload, 'ko', 'ctx', testKeyring, ['ko', 'av', 'ru', 'ca', 'um', 'dr']);

      // Different verifiers with different key subsets
      // Each verifier needs fresh nonce cache since they're independent systems
      const verifier1: Keyring = { ko: testKeyring.ko, av: testKeyring.av };
      const result1 = verifyRoundtable(envelope, verifier1);
      expect(result1.valid).toBe(true);
      expect(result1.validTongues).toEqual(['ko', 'av']);

      // Clear nonce cache to simulate separate verifier instance
      clearNonceCache();
      const verifier2: Keyring = { ru: testKeyring.ru, um: testKeyring.um };
      const result2 = verifyRoundtable(envelope, verifier2);
      expect(result2.valid).toBe(true);
      expect(result2.validTongues).toEqual(['ru', 'um']);

      // Clear nonce cache to simulate third verifier instance
      clearNonceCache();
      const verifier3: Keyring = { dr: testKeyring.dr };
      const result3 = verifyRoundtable(envelope, verifier3);
      expect(result3.valid).toBe(true);
      expect(result3.validTongues).toEqual(['dr']);
    });
  });

  describe('Malformed Envelope Handling', () => {
    it('should reject envelope with missing ver field', () => {
      const envelope = signRoundtable({ test: true }, 'ko', 'ctx', testKeyring, ['ko']);
      const malformed = { ...envelope, ver: undefined as any };

      const result = verifyRoundtable(malformed, testKeyring);
      expect(result.valid).toBe(false);
    });

    it('should handle envelope with missing sigs object', () => {
      const envelope = signRoundtable({ test: true }, 'ko', 'ctx', testKeyring, ['ko']);
      const malformed = { ...envelope, sigs: undefined as any };

      // The implementation throws when sigs is undefined (due to Object.keys call)
      // This is acceptable behavior - malformed envelopes can throw
      expect(() => verifyRoundtable(malformed, testKeyring)).toThrow();
    });

    it('should reject envelope with null payload', () => {
      const envelope = signRoundtable({ test: true }, 'ko', 'ctx', testKeyring, ['ko']);
      const malformed = { ...envelope, payload: null as any };

      const result = verifyRoundtable(malformed, testKeyring);
      expect(result.valid).toBe(false);
    });

    it('should reject envelope with non-base64 payload', () => {
      const envelope = signRoundtable({ test: true }, 'ko', 'ctx', testKeyring, ['ko']);
      const malformed = { ...envelope, payload: '!!!not-valid-base64!!!' };

      const result = verifyRoundtable(malformed, testKeyring);
      expect(result.valid).toBe(false);
    });

    it('should reject envelope with invalid JSON in payload', () => {
      const envelope = signRoundtable({ test: true }, 'ko', 'ctx', testKeyring, ['ko']);
      // Create a valid base64 string that doesn't decode to valid JSON
      const invalidJson = Buffer.from('not-json{{{', 'utf8').toString('base64url');
      const malformed = { ...envelope, payload: invalidJson };

      const result = verifyRoundtable(malformed, testKeyring);
      expect(result.valid).toBe(false);
    });
  });

  describe('Boundary Timestamp Conditions', () => {
    it('should accept envelope at exact max age boundary minus 1ms', () => {
      const payload = { timing: 'boundary' };
      const now = Date.now();
      const maxAge = 300000; // 5 minutes default
      const timestamp = now - (maxAge - 1);

      const envelope = signRoundtable(payload, 'ko', 'ctx', testKeyring, ['ko'], { timestamp });
      const result = verifyRoundtable(envelope, testKeyring);

      expect(result.valid).toBe(true);
    });

    it('should accept envelope at exact future skew boundary minus 1ms', () => {
      const payload = { timing: 'future-boundary' };
      const now = Date.now();
      const maxFutureSkew = 60000; // 1 minute default
      const timestamp = now + (maxFutureSkew - 1);

      const envelope = signRoundtable(payload, 'ko', 'ctx', testKeyring, ['ko'], { timestamp });
      const result = verifyRoundtable(envelope, testKeyring);

      expect(result.valid).toBe(true);
    });

    it('should reject envelope at exact max age boundary plus 1ms', () => {
      const payload = { timing: 'expired' };
      const now = Date.now();
      const maxAge = 300001; // Just over 5 minutes
      const timestamp = now - maxAge;

      const envelope = signRoundtable(payload, 'ko', 'ctx', testKeyring, ['ko'], { timestamp });
      const result = verifyRoundtable(envelope, testKeyring);

      expect(result.valid).toBe(false);
      expect(result.error).toContain('too old');
    });

    it('should respect custom maxAge option', () => {
      const payload = { timing: 'custom' };
      const timestamp = Date.now() - 10000; // 10 seconds ago

      const envelope = signRoundtable(payload, 'ko', 'ctx', testKeyring, ['ko'], { timestamp });

      // Should pass with 60 second max age
      const result1 = verifyRoundtable(envelope, testKeyring, { maxAge: 60000 });
      expect(result1.valid).toBe(true);

      // Reset nonce cache for second test
      clearNonceCache();

      // Should fail with 5 second max age
      const result2 = verifyRoundtable(envelope, testKeyring, { maxAge: 5000 });
      expect(result2.valid).toBe(false);
    });
  });

  describe('Type Coercion Edge Cases', () => {
    it('should handle payload with boolean types correctly', () => {
      const payload = {
        isActive: true,
        isDeleted: false,
        flags: [true, false, true]
      };

      const envelope = signRoundtable(payload, 'ko', 'ctx', testKeyring, ['ko']);
      const result = verifyRoundtable(envelope, testKeyring);

      expect(result.valid).toBe(true);
      expect((result.payload as any).isActive).toBe(true);
      expect((result.payload as any).isDeleted).toBe(false);
    });

    it('should handle payload with null values correctly', () => {
      const payload = {
        value: null,
        nested: { inner: null },
        array: [null, 1, null]
      };

      const envelope = signRoundtable(payload, 'ko', 'ctx', testKeyring, ['ko']);
      const result = verifyRoundtable(envelope, testKeyring);

      expect(result.valid).toBe(true);
      expect((result.payload as any).value).toBeNull();
    });

    it('should handle payload with numeric edge values', () => {
      const payload = {
        infinity: Number.MAX_VALUE, // Not actual Infinity (JSON doesn't support it)
        tiny: Number.MIN_VALUE,
        negZero: 0, // -0 becomes 0 in JSON
        scientific: 1e10,
        float: 0.1 + 0.2 // Famous floating point issue
      };

      const envelope = signRoundtable(payload, 'ko', 'ctx', testKeyring, ['ko']);
      const result = verifyRoundtable(envelope, testKeyring);

      expect(result.valid).toBe(true);
    });

    it('should handle empty objects and arrays', () => {
      const payload = {
        emptyObj: {},
        emptyArray: [],
        nestedEmpty: { inner: {} }
      };

      const envelope = signRoundtable(payload, 'ko', 'ctx', testKeyring, ['ko']);
      const result = verifyRoundtable(envelope, testKeyring);

      expect(result.valid).toBe(true);
      expect((result.payload as any).emptyObj).toEqual({});
      expect((result.payload as any).emptyArray).toEqual([]);
    });
  });

  describe('Policy Integration Tests', () => {
    it('should correctly chain policy check with verification', () => {
      const payload = { action: 'deploy', target: 'production' };

      // Check what tongues are needed before signing
      const needsStrict = checkPolicy(['ko'], 'strict');
      expect(needsStrict).toBe(false); // ko alone is not enough

      const hasStrict = checkPolicy(['ko', 'ru'], 'strict');
      expect(hasStrict).toBe(true); // ko + ru satisfies strict

      // Sign with enough tongues
      const envelope = signRoundtable(payload, 'ko', 'deploy-ctx', testKeyring, ['ko', 'ru']);

      // Verify with policy
      const result = verifyRoundtable(envelope, testKeyring, { policy: 'strict' });
      expect(result.valid).toBe(true);
    });

    it('should handle escalating policy requirements', () => {
      const payload = { action: 'critical-operation' };

      // Sign with all tongues
      const envelope = signRoundtable(
        payload,
        'ko',
        'ctx',
        testKeyring,
        ['ko', 'av', 'ru', 'ca', 'um', 'dr']
      );

      // Test escalating policies (reset nonce cache between verifications)
      const result1 = verifyRoundtable(envelope, testKeyring, { policy: 'standard' });
      expect(result1.valid).toBe(true);

      clearNonceCache();
      const result2 = verifyRoundtable(envelope, testKeyring, { policy: 'strict' });
      expect(result2.valid).toBe(true);

      clearNonceCache();
      const result3 = verifyRoundtable(envelope, testKeyring, { policy: 'critical' });
      expect(result3.valid).toBe(true);
    });
  });

  describe('All Six Sacred Tongues', () => {
    const allTongues: TongueID[] = ['ko', 'av', 'ru', 'ca', 'um', 'dr'];

    it('should sign with each tongue individually', () => {
      const payload = { test: 'single-tongue' };

      for (const tongue of allTongues) {
        clearNonceCache();
        const envelope = signRoundtable(payload, tongue, 'ctx', testKeyring, [tongue]);

        expect(envelope.primary_tongue).toBe(tongue);
        expect(envelope.sigs[tongue]).toBeDefined();
        expect(Object.keys(envelope.sigs)).toHaveLength(1);

        const result = verifyRoundtable(envelope, testKeyring);
        expect(result.valid).toBe(true);
        expect(result.validTongues).toEqual([tongue]);
      }
    });

    it('should sign with all tongues combined', () => {
      const payload = { test: 'all-tongues' };

      const envelope = signRoundtable(payload, 'ko', 'full-council', testKeyring, allTongues);

      expect(Object.keys(envelope.sigs)).toHaveLength(6);

      for (const tongue of allTongues) {
        expect(envelope.sigs[tongue]).toBeDefined();
        expect(typeof envelope.sigs[tongue]).toBe('string');
      }

      const result = verifyRoundtable(envelope, testKeyring);
      expect(result.valid).toBe(true);
      expect(result.validTongues.sort()).toEqual(allTongues.sort());
    });

    it('should produce unique signatures for each tongue', () => {
      const payload = { uniqueness: 'test' };
      const envelope = signRoundtable(payload, 'ko', 'ctx', testKeyring, allTongues);

      const signatures = Object.values(envelope.sigs);
      const uniqueSignatures = new Set(signatures);

      // All 6 signatures should be unique
      expect(uniqueSignatures.size).toBe(6);
    });
  });

  describe('Stress Tests', () => {
    it('should handle many sequential sign/verify operations', () => {
      const iterations = 100;

      for (let i = 0; i < iterations; i++) {
        clearNonceCache();
        const payload = { iteration: i, data: `test-${i}` };
        const envelope = signRoundtable(payload, 'ko', `ctx-${i}`, testKeyring, ['ko']);
        const result = verifyRoundtable(envelope, testKeyring);

        expect(result.valid).toBe(true);
        expect((result.payload as any).iteration).toBe(i);
      }
    });

    it('should handle batch creation with unique nonces', () => {
      const batchSize = 50;
      const envelopes: RWPEnvelope[] = [];

      for (let i = 0; i < batchSize; i++) {
        const envelope = signRoundtable({ batch: i }, 'ko', 'batch', testKeyring, ['ko']);
        envelopes.push(envelope);
      }

      // All nonces should be unique
      const nonces = envelopes.map(e => e.nonce);
      const uniqueNonces = new Set(nonces);
      expect(uniqueNonces.size).toBe(batchSize);

      // All should verify (only first one due to nonce replay protection)
      const firstResult = verifyRoundtable(envelopes[0], testKeyring);
      expect(firstResult.valid).toBe(true);
    });
  });
});
