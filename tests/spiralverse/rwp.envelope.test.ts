/**
 * RWP v2.1 Multi-Signature Envelopes - Tests
 * ===========================================
 *
 * Feature: rwp-v2-integration
 * Validates: Requirements AC-2.1.1 through AC-2.6.6
 *
 * @module tests/spiralverse/rwp
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { randomBytes } from 'crypto';
import {
  signRoundtable,
  verifyRoundtable,
  clearNonceCache,
  // enforcePolicy,
  checkPolicy,
  getRequiredTongues,
  suggestPolicy,
  type Keyring,
  // type TongueID,
  // type PolicyLevel,
} from '../../src/spiralverse';

// Test keyring (32-byte keys for HMAC-SHA256)
const testKeyring: Keyring = {
  ko: randomBytes(32),  // Kor'aelin (Control)
  av: randomBytes(32),  // Avali (I/O)
  ru: randomBytes(32),  // Runethic (Policy)
  ca: randomBytes(32),  // Cassisivadan (Compute)
  um: randomBytes(32),  // Umbroth (Security)
  dr: randomBytes(32),  // Draumric (Structure)
};

describe('RWP v2.1 Multi-Signature Envelopes', () => {
  beforeEach(() => {
    clearNonceCache();
  });

  describe('Envelope Creation (AC-2.1.1 - AC-2.1.3)', () => {
    it('should create envelope with single signature', () => {
      const payload = { action: 'read', resource: 'file.txt' };
      const envelope = signRoundtable(
        payload,
        'ko',           // primaryTongue
        'test-aad',     // aad
        testKeyring,    // keyring
        ['ko']          // signingTongues
      );

      // Verify envelope structure
      expect(envelope.ver).toBe('2.1');
      expect(envelope.primary_tongue).toBe('ko');
      expect(envelope.aad).toBe('test-aad');
      expect(envelope.sigs.ko).toBeDefined();
      expect(typeof envelope.sigs.ko).toBe('string');
      expect(envelope.nonce).toBeDefined();
      expect(envelope.ts).toBeGreaterThan(0);
    });

    it('should create envelope with multiple signatures', () => {
      const payload = { action: 'deploy', target: 'production' };
      const envelope = signRoundtable(
        payload,
        'ko',                    // primaryTongue (Control)
        'deploy-metadata',       // aad
        testKeyring,             // keyring
        ['ko', 'ru', 'um']       // signingTongues (Control, Policy, Security)
      );

      // Verify envelope structure
      expect(envelope.ver).toBe('2.1');
      expect(envelope.primary_tongue).toBe('ko');
      expect(envelope.aad).toBe('deploy-metadata');

      // Verify all three signatures exist
      expect(envelope.sigs.ko).toBeDefined();
      expect(envelope.sigs.ru).toBeDefined();
      expect(envelope.sigs.um).toBeDefined();

      // Verify signatures are different
      expect(envelope.sigs.ko).not.toBe(envelope.sigs.ru);
      expect(envelope.sigs.ko).not.toBe(envelope.sigs.um);
      expect(envelope.sigs.ru).not.toBe(envelope.sigs.um);
    });

    it('should include optional kid field', () => {
      const payload = { action: 'read', resource: 'file.txt' };
      const envelope = signRoundtable(
        payload,
        'ko',
        'test-aad',
        testKeyring,
        ['ko'],
        { kid: 'key-123' }  // Optional key ID
      );

      expect(envelope.kid).toBe('key-123');
    });

    it('should generate unique nonces', () => {
      const payload = { action: 'read', resource: 'file.txt' };

      const env1 = signRoundtable(payload, 'ko', 'test-aad', testKeyring, ['ko']);
      const env2 = signRoundtable(payload, 'ko', 'test-aad', testKeyring, ['ko']);

      expect(env1.nonce).not.toBe(env2.nonce);
    });

    it('should throw error if payload is missing', () => {
      expect(() => {
        signRoundtable(null as any, 'ko', 'test-aad', testKeyring, ['ko']);
      }).toThrow('Payload is required');
    });

    it('should throw error if primary tongue is missing', () => {
      expect(() => {
        signRoundtable({ action: 'read' }, '' as any, 'test-aad', testKeyring, ['ko']);
      }).toThrow('Primary tongue is required');
    });

    it('should throw error if signing tongues array is empty', () => {
      expect(() => {
        signRoundtable({ action: 'read' }, 'ko', 'test-aad', testKeyring, []);
      }).toThrow('At least one signing tongue is required');
    });

    it('should throw error if keyring is missing key for signing tongue', () => {
      const incompleteKeyring = { ko: testKeyring.ko };

      expect(() => {
        signRoundtable(
          { action: 'read' },
          'ko',
          'test-aad',
          incompleteKeyring as any,
          ['ko', 'ru']  // ru key is missing
        );
      }).toThrow('Missing key for tongue: ru');
    });
  });

  describe('Envelope Verification (AC-2.2.1 - AC-2.2.4)', () => {
    it('should verify valid envelope with single signature', () => {
      const payload = { action: 'read', resource: 'file.txt' };
      const envelope = signRoundtable(payload, 'ko', 'test-aad', testKeyring, ['ko']);

      const result = verifyRoundtable(envelope, testKeyring);

      expect(result.valid).toBe(true);
      expect(result.validTongues).toEqual(['ko']);
      expect(result.payload).toEqual(payload);
      expect(result.error).toBeUndefined();
    });

    it('should verify valid envelope with multiple signatures', () => {
      const payload = { action: 'deploy', target: 'production' };
      const envelope = signRoundtable(
        payload,
        'ko',
        'deploy-metadata',
        testKeyring,
        ['ko', 'ru', 'um']
      );

      const result = verifyRoundtable(envelope, testKeyring);

      expect(result.valid).toBe(true);
      expect(result.validTongues).toContain('ko');
      expect(result.validTongues).toContain('ru');
      expect(result.validTongues).toContain('um');
      expect(result.validTongues.length).toBe(3);
      expect(result.payload).toEqual(payload);
    });

    it('should reject envelope with invalid signature', () => {
      const payload = { action: 'read', resource: 'file.txt' };
      const envelope = signRoundtable(payload, 'ko', 'test-aad', testKeyring, ['ko']);

      // Tamper with signature
      envelope.sigs.ko = 'invalid-signature';

      const result = verifyRoundtable(envelope, testKeyring);

      expect(result.valid).toBe(false);
      expect(result.error).toContain('No valid signatures found');
    });

    it('should reject envelope with tampered payload', () => {
      const payload = { action: 'read', resource: 'file.txt' };
      const envelope = signRoundtable(payload, 'ko', 'test-aad', testKeyring, ['ko']);

      // Tamper with payload
      const tamperedPayload = { action: 'write', resource: 'file.txt' };
      envelope.payload = Buffer.from(JSON.stringify(tamperedPayload)).toString('base64url');

      const result = verifyRoundtable(envelope, testKeyring);

      expect(result.valid).toBe(false);
      expect(result.error).toContain('No valid signatures found');
    });

    it('should reject envelope with unsupported version', () => {
      const payload = { action: 'read', resource: 'file.txt' };
      const envelope = signRoundtable(payload, 'ko', 'test-aad', testKeyring, ['ko']);

      // Change version
      envelope.ver = '1.0' as any;

      const result = verifyRoundtable(envelope, testKeyring);

      expect(result.valid).toBe(false);
      expect(result.error).toContain('Unsupported version');
    });
  });

  describe('Replay Protection (AC-2.3.1 - AC-2.3.3)', () => {
    it('should reject replayed envelope (duplicate nonce)', () => {
      const payload = { action: 'read', resource: 'file.txt' };
      const envelope = signRoundtable(payload, 'ko', 'test-aad', testKeyring, ['ko']);

      // First verification should succeed
      const result1 = verifyRoundtable(envelope, testKeyring);
      expect(result1.valid).toBe(true);

      // Second verification with same envelope should fail (nonce reuse)
      const result2 = verifyRoundtable(envelope, testKeyring);
      expect(result2.valid).toBe(false);
      expect(result2.error).toContain('Nonce already used');
    });

    it('should reject envelope with old timestamp', () => {
      const payload = { action: 'read', resource: 'file.txt' };
      const oldTimestamp = Date.now() - 400000; // 6 minutes ago (beyond 5-minute window)

      const envelope = signRoundtable(
        payload,
        'ko',
        'test-aad',
        testKeyring,
        ['ko'],
        { timestamp: oldTimestamp }
      );

      const result = verifyRoundtable(envelope, testKeyring);

      expect(result.valid).toBe(false);
      expect(result.error).toContain('Timestamp too old');
    });

    it('should reject envelope with future timestamp', () => {
      const payload = { action: 'read', resource: 'file.txt' };
      const futureTimestamp = Date.now() + 120000; // 2 minutes in future (beyond 1-minute skew)

      const envelope = signRoundtable(
        payload,
        'ko',
        'test-aad',
        testKeyring,
        ['ko'],
        { timestamp: futureTimestamp }
      );

      const result = verifyRoundtable(envelope, testKeyring);

      expect(result.valid).toBe(false);
      expect(result.error).toContain('Timestamp is in the future');
    });

    it('should accept envelope within clock skew tolerance', () => {
      const payload = { action: 'read', resource: 'file.txt' };
      const slightlyFutureTimestamp = Date.now() + 30000; // 30 seconds in future (within 1-minute skew)

      const envelope = signRoundtable(
        payload,
        'ko',
        'test-aad',
        testKeyring,
        ['ko'],
        { timestamp: slightlyFutureTimestamp }
      );

      const result = verifyRoundtable(envelope, testKeyring);

      expect(result.valid).toBe(true);
    });
  });

  describe('Policy Enforcement (AC-2.4.1 - AC-2.4.4)', () => {
    it('should enforce "standard" policy (requires KO)', () => {
      const payload = { action: 'read', resource: 'file.txt' };
      const envelope = signRoundtable(payload, 'ko', 'test-aad', testKeyring, ['ko']);

      const result = verifyRoundtable(envelope, testKeyring, { policy: 'standard' });

      expect(result.valid).toBe(true);
    });

    it('should enforce "strict" policy (requires RU)', () => {
      const payload = { action: 'deploy', target: 'staging' };
      const envelope = signRoundtable(payload, 'ko', 'test-aad', testKeyring, ['ko', 'ru']);

      const result = verifyRoundtable(envelope, testKeyring, { policy: 'strict' });

      expect(result.valid).toBe(true);
    });

    it('should reject "strict" policy with insufficient signatures', () => {
      const payload = { action: 'deploy', target: 'staging' };
      const envelope = signRoundtable(payload, 'ko', 'test-aad', testKeyring, ['ko']);

      const result = verifyRoundtable(envelope, testKeyring, { policy: 'strict' });

      expect(result.valid).toBe(false);
      expect(result.error).toContain("requires tongues");
    });

    it('should enforce "critical" policy (requires RU + UM + DR)', () => {
      const payload = { action: 'deploy', target: 'production' };
      const envelope = signRoundtable(
        payload,
        'ko',
        'test-aad',
        testKeyring,
        ['ko', 'ru', 'um', 'dr']
      );

      const result = verifyRoundtable(envelope, testKeyring, { policy: 'critical' });

      expect(result.valid).toBe(true);
    });

    it('should reject "critical" policy with insufficient signatures', () => {
      const payload = { action: 'deploy', target: 'production' };
      const envelope = signRoundtable(payload, 'ko', 'test-aad', testKeyring, ['ko', 'ru']);

      const result = verifyRoundtable(envelope, testKeyring, { policy: 'critical' });

      expect(result.valid).toBe(false);
      expect(result.error).toContain("requires tongues");
    });
  });

  describe('Policy Helpers (AC-2.5.1 - AC-2.5.3)', () => {
    it('should check if tongues satisfy policy', () => {
      expect(checkPolicy(['ko'], 'standard')).toBe(true);
      expect(checkPolicy(['ko', 'ru'], 'strict')).toBe(true);
      expect(checkPolicy(['ru', 'um', 'dr'], 'critical')).toBe(true);

      // Standard policy accepts any valid signature
      expect(checkPolicy(['av'], 'standard')).toBe(true);
      expect(checkPolicy(['ko'], 'strict')).toBe(false);
      expect(checkPolicy(['ko', 'ru'], 'critical')).toBe(false);
    });

    it('should get required tongues for policy', () => {
      // Standard has no required tongues (any valid signature)
      expect(getRequiredTongues('standard')).toEqual([]);
      expect(getRequiredTongues('strict')).toContain('ru');
      expect(getRequiredTongues('critical')).toEqual(['ru', 'um', 'dr']);
    });

    it('should suggest appropriate policy for action', () => {
      expect(suggestPolicy('read')).toBe('standard');
      // Write operations require strict policy
      expect(suggestPolicy('write')).toBe('strict');
      // Deploy operations require critical policy
      expect(suggestPolicy('deploy')).toBe('critical');
      // Delete operations require secret policy (security-sensitive)
      expect(suggestPolicy('delete')).toBe('secret');
      // Grant/revoke require critical policy
      expect(suggestPolicy('grant_access')).toBe('critical');
      expect(suggestPolicy('revoke')).toBe('critical');
      expect(suggestPolicy('unknown')).toBe('standard');
    });
  });

  describe('Edge Cases and Error Handling (AC-2.6.1 - AC-2.6.6)', () => {
    it('should handle large payloads', () => {
      const largePayload = {
        data: 'x'.repeat(10000),
        metadata: { items: Array(100).fill({ id: 1, name: 'test' }) }
      };

      const envelope = signRoundtable(largePayload, 'ko', 'test-aad', testKeyring, ['ko']);
      const result = verifyRoundtable(envelope, testKeyring);

      expect(result.valid).toBe(true);
      expect(result.payload).toEqual(largePayload);
    });

    it('should handle special characters in payload', () => {
      const payload = {
        text: 'Hello 世界 🌍',
        symbols: '!@#$%^&*()_+-=[]{}|;:\'",.<>?/\\',
        unicode: '\u0000\u001f\u007f\uffff'
      };

      const envelope = signRoundtable(payload, 'ko', 'test-aad', testKeyring, ['ko']);
      const result = verifyRoundtable(envelope, testKeyring);

      expect(result.valid).toBe(true);
      expect(result.payload).toEqual(payload);
    });

    it('should handle empty AAD', () => {
      const payload = { action: 'read' };
      const envelope = signRoundtable(payload, 'ko', '', testKeyring, ['ko']);
      const result = verifyRoundtable(envelope, testKeyring);

      expect(result.valid).toBe(true);
      expect(envelope.aad).toBe('');
    });

    it('should handle custom nonce', () => {
      const payload = { action: 'read' };
      const customNonce = randomBytes(16);

      const envelope = signRoundtable(
        payload,
        'ko',
        'test-aad',
        testKeyring,
        ['ko'],
        { nonce: customNonce }
      );

      expect(envelope.nonce).toBe(customNonce.toString('base64url'));

      const result = verifyRoundtable(envelope, testKeyring);
      expect(result.valid).toBe(true);
    });

    it('should handle partial keyring in verification', () => {
      const payload = { action: 'read' };
      const envelope = signRoundtable(
        payload,
        'ko',
        'test-aad',
        testKeyring,
        ['ko', 'ru', 'um']
      );

      // Verify with partial keyring (only ko and ru keys)
      const partialKeyring = {
        ko: testKeyring.ko,
        ru: testKeyring.ru,
      };

      const result = verifyRoundtable(envelope, partialKeyring as any);

      // Should succeed with 2 valid signatures (ko and ru)
      expect(result.valid).toBe(true);
      expect(result.validTongues).toContain('ko');
      expect(result.validTongues).toContain('ru');
      expect(result.validTongues).not.toContain('um'); // um key missing
    });

    it('should handle concurrent envelope creation', () => {
      const payload = { action: 'read' };

      // Create multiple envelopes concurrently
      const envelopes = Array(10).fill(null).map(() =>
        signRoundtable(payload, 'ko', 'test-aad', testKeyring, ['ko'])
      );

      // All should have unique nonces
      const nonces = envelopes.map(env => env.nonce);
      const uniqueNonces = new Set(nonces);
      expect(uniqueNonces.size).toBe(10);

      // All should verify successfully
      envelopes.forEach(envelope => {
        const result = verifyRoundtable(envelope, testKeyring);
        expect(result.valid).toBe(true);
      });
    });
  });
});
