/**
 * @file nonceManager.test.ts
 * @module crypto/nonceManager
 * @layer L5 Security
 *
 * Tests for nonce generation (HIGH-001 fix: random nonces).
 */

import { describe, it, expect } from 'vitest';
import {
  nextNonce,
  deriveNoncePrefix,
  resetSessionCounter,
} from '../../src/crypto/nonceManager.js';

describe('nonceManager', () => {
  describe('nextNonce', () => {
    it('returns a 12-byte nonce buffer', () => {
      const { nonce } = nextNonce();
      expect(Buffer.isBuffer(nonce)).toBe(true);
      expect(nonce.length).toBe(12);
    });

    it('returns unique nonces on consecutive calls', () => {
      const nonces = new Set<string>();
      for (let i = 0; i < 100; i++) {
        nonces.add(nextNonce().nonce.toString('hex'));
      }
      // All 100 should be unique (collision probability ~2^-48 per pair)
      expect(nonces.size).toBe(100);
    });

    it('nonce contains non-zero bytes (statistical check)', () => {
      // Generate multiple nonces and verify they are not all zeros
      let hasNonZero = false;
      for (let i = 0; i < 10; i++) {
        const { nonce } = nextNonce();
        if (nonce.some((b) => b !== 0)) {
          hasNonZero = true;
          break;
        }
      }
      expect(hasNonZero).toBe(true);
    });
  });

  describe('deriveNoncePrefix (deprecated)', () => {
    it('returns 8 zero bytes regardless of input', () => {
      const result = deriveNoncePrefix(Buffer.from('key'), 'session-1');
      expect(result.length).toBe(8);
      expect(result.every((b) => b === 0)).toBe(true);
    });
  });

  describe('resetSessionCounter (deprecated)', () => {
    it('is a no-op that does not throw', () => {
      expect(() => resetSessionCounter('session-1')).not.toThrow();
    });
  });
});
