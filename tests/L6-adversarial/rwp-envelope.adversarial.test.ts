/**
 * L6-ADVERSARIAL: RWP Envelope Adversarial Tests
 *
 * @tier L6
 * @category adversarial
 * @description Tests system behavior under malicious/hostile conditions
 * @level Security Researcher / Red Team
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { randomBytes } from 'crypto';
import {
  signRoundtable,
  verifyRoundtable,
  clearNonceCache,
  type Keyring
} from '../../src/spiralverse/index.js';

describe('L6-ADVERSARIAL: RWP Envelope Attack Resistance', () => {
  let testKeyring: Keyring;

  beforeEach(() => {
    testKeyring = {
      ko: randomBytes(32),
      av: randomBytes(32),
      ru: randomBytes(32),
      ca: randomBytes(32),
      um: randomBytes(32),
      dr: randomBytes(32),
    };
    clearNonceCache();
  });

  describe('Signature Tampering Attacks', () => {
    it('should reject envelope with truncated signature', () => {
      const payload = { data: 'sensitive', level: 'classified' };
      const envelope = signRoundtable(payload, 'ko', 'test-aad', testKeyring, ['ko']);

      // Truncate the signature
      const truncatedEnvelope = {
        ...envelope,
        sigs: { ...envelope.sigs, ko: envelope.sigs.ko.slice(0, 32) }
      };

      const result = verifyRoundtable(truncatedEnvelope, testKeyring);
      expect(result.valid).toBe(false);
    });

    it('should reject envelope with bit-flipped signature', () => {
      const payload = { message: 'critical-data' };
      const envelope = signRoundtable(payload, 'ko', 'aad', testKeyring, ['ko']);

      // Flip a single bit in the signature
      const sig = envelope.sigs.ko;
      const flippedSig = sig.slice(0, 10) +
        String.fromCharCode(sig.charCodeAt(10) ^ 0x01) +
        sig.slice(11);

      const tamperedEnvelope = {
        ...envelope,
        sigs: { ...envelope.sigs, ko: flippedSig }
      };

      const result = verifyRoundtable(tamperedEnvelope, testKeyring);
      expect(result.valid).toBe(false);
    });

    it('should reject envelope with signature from wrong key', () => {
      const payload = { action: 'execute' };
      const envelope = signRoundtable(payload, 'ko', 'aad', testKeyring, ['ko']);

      // Create a new keyring with different keys
      const attackerKeyring: Keyring = {
        ko: randomBytes(32),
        av: randomBytes(32),
        ru: randomBytes(32),
        ca: randomBytes(32),
        um: randomBytes(32),
        dr: randomBytes(32),
      };

      // Verification with original keyring should fail for attacker-signed envelope
      const attackerEnvelope = signRoundtable(payload, 'ko', 'aad', attackerKeyring, ['ko']);
      const result = verifyRoundtable(attackerEnvelope, testKeyring);
      expect(result.valid).toBe(false);
    });
  });

  describe('Nonce Attacks', () => {
    it('should reject envelope with empty nonce', () => {
      const payload = { data: 'test' };
      const envelope = signRoundtable(payload, 'ko', 'aad', testKeyring, ['ko']);

      const tamperedEnvelope = {
        ...envelope,
        nonce: ''
      };

      const result = verifyRoundtable(tamperedEnvelope, testKeyring);
      expect(result.valid).toBe(false);
    });

    it('should reject envelope with modified nonce', () => {
      const payload = { data: 'test' };
      const envelope = signRoundtable(payload, 'ko', 'aad', testKeyring, ['ko']);

      const tamperedEnvelope = {
        ...envelope,
        nonce: envelope.nonce.slice(0, -4) + 'XXXX'
      };

      const result = verifyRoundtable(tamperedEnvelope, testKeyring);
      expect(result.valid).toBe(false);
    });
  });

  describe('Payload Manipulation Attacks', () => {
    it('should reject envelope with modified payload', () => {
      const payload = { amount: 100, recipient: 'alice' };
      const envelope = signRoundtable(payload, 'ko', 'aad', testKeyring, ['ko']);

      // Modify the payload
      const tamperedEnvelope = {
        ...envelope,
        payload: { amount: 10000, recipient: 'attacker' }
      };

      const result = verifyRoundtable(tamperedEnvelope, testKeyring);
      expect(result.valid).toBe(false);
    });

    it('should reject envelope with injected fields', () => {
      const payload = { data: 'original' };
      const envelope = signRoundtable(payload, 'ko', 'aad', testKeyring, ['ko']);

      // Inject additional fields
      const tamperedEnvelope = {
        ...envelope,
        payload: { ...envelope.payload, admin: true, bypass: true }
      };

      const result = verifyRoundtable(tamperedEnvelope, testKeyring);
      expect(result.valid).toBe(false);
    });
  });

  describe('Multi-Signature Attack Vectors', () => {
    it('should require all specified signers', () => {
      const payload = { action: 'critical-operation' };
      const envelope = signRoundtable(payload, 'ko', 'aad', testKeyring, ['ko', 'um', 'dr']);

      // Verify needs all signatures
      expect(envelope.sigs.ko).toBeDefined();
      expect(envelope.sigs.um).toBeDefined();
      expect(envelope.sigs.dr).toBeDefined();

      const result = verifyRoundtable(envelope, testKeyring);
      expect(result.valid).toBe(true);
    });

    it('should verify multi-signature envelopes correctly', () => {
      const payload = { action: 'critical-operation' };
      const envelope = signRoundtable(payload, 'ko', 'aad', testKeyring, ['ko', 'um']);

      // Verify envelope with all required signatures
      expect(envelope.sigs.ko).toBeDefined();
      expect(envelope.sigs.um).toBeDefined();

      const result = verifyRoundtable(envelope, testKeyring);
      expect(result.valid).toBe(true);

      // Tamper with one signature (bit flip)
      const sig = envelope.sigs.um;
      const flippedSig = sig.slice(0, 5) + String.fromCharCode(sig.charCodeAt(5) ^ 0x01) + sig.slice(6);
      const tamperedEnvelope = {
        ...envelope,
        sigs: { ...envelope.sigs, um: flippedSig }
      };

      const tamperedResult = verifyRoundtable(tamperedEnvelope, testKeyring);
      expect(tamperedResult.valid).toBe(false);
    });
  });

  describe('AAD (Associated Authenticated Data) Attacks', () => {
    it('should reject envelope verified with wrong AAD', () => {
      const payload = { data: 'protected' };
      const envelope = signRoundtable(payload, 'ko', 'original-context', testKeyring, ['ko']);

      // The envelope was signed with 'original-context' AAD
      // An attacker trying to use it in a different context should fail
      // Note: AAD verification is implicit in signature verification
      expect(envelope.aad).toBe('original-context');

      // The signature binds to the AAD, so tampering would invalidate
      const tamperedEnvelope = {
        ...envelope,
        aad: 'attacker-context'
      };

      const result = verifyRoundtable(tamperedEnvelope, testKeyring);
      expect(result.valid).toBe(false);
    });
  });

  describe('Cryptographic Edge Cases', () => {
    it('should handle envelope with maximum payload size', () => {
      // Large payload stress test
      const largePayload = {
        data: 'x'.repeat(10000),
        nested: { deep: { value: 'y'.repeat(1000) } }
      };

      const envelope = signRoundtable(largePayload, 'ko', 'aad', testKeyring, ['ko']);
      const result = verifyRoundtable(envelope, testKeyring);
      expect(result.valid).toBe(true);
    });

    it('should handle special characters in payload', () => {
      const specialPayload = {
        unicode: '🔒🛡️🔐',
        escapes: '\n\r\t\0',
        quotes: '"\'`',
        symbols: '<>&;|$'
      };

      const envelope = signRoundtable(specialPayload, 'ko', 'aad', testKeyring, ['ko']);
      const result = verifyRoundtable(envelope, testKeyring);
      expect(result.valid).toBe(true);
    });

    it('should handle numeric edge cases in payload', () => {
      const numericPayload = {
        max: Number.MAX_SAFE_INTEGER,
        min: Number.MIN_SAFE_INTEGER,
        float: 3.14159265358979,
        zero: 0,
        negative: -1
      };

      const envelope = signRoundtable(numericPayload, 'ko', 'aad', testKeyring, ['ko']);
      const result = verifyRoundtable(envelope, testKeyring);
      expect(result.valid).toBe(true);
    });
  });
});
