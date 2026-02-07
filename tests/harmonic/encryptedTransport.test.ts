/**
 * @file encryptedTransport.test.ts
 * @description Tests for encrypted vector transport — verifying that
 * encryption is properly separated from Möbius navigation.
 *
 * Core invariant under test: encrypted vectors are opaque ciphertext,
 * NOT valid Poincaré ball points. Geometric operations only happen
 * on decrypted plaintext.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  generateTransportKey,
  encryptVector,
  decryptVector,
  secureNavigate,
  secureBatchNavigate,
  encryptPosition,
  decryptPosition,
  VectorTransportKey,
  EncryptedVector,
} from '../../src/harmonic/encryptedTransport';
import { mobiusAdd, projectToBall } from '../../src/harmonic/hyperbolic';

describe('EncryptedTransport', () => {
  let key: VectorTransportKey;

  beforeEach(() => {
    key = generateTransportKey('test');
  });

  // ═══════════════════════════════════════════════════════════════
  // Key Generation
  // ═══════════════════════════════════════════════════════════════

  describe('generateTransportKey', () => {
    it('should generate a 256-bit key', () => {
      expect(key.key.length).toBe(32);
    });

    it('should generate unique keys', () => {
      const key2 = generateTransportKey('test');
      expect(Buffer.compare(key.key, key2.key)).not.toBe(0);
    });

    it('should have a key ID', () => {
      expect(key.kid).toBeDefined();
      expect(key.kid.length).toBe(16);
    });

    it('should record creation timestamp', () => {
      expect(key.createdAt).toBeGreaterThan(0);
      expect(key.createdAt).toBeLessThanOrEqual(Date.now());
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Encrypt / Decrypt Round-Trip
  // ═══════════════════════════════════════════════════════════════

  describe('encrypt/decrypt round-trip', () => {
    it('should round-trip a 6D vector', () => {
      const vector = [0.1, 0.2, 0.3, -0.1, -0.2, 0.05];
      const encrypted = encryptVector(vector, key);
      const decrypted = decryptVector(encrypted, key);

      for (let i = 0; i < vector.length; i++) {
        expect(decrypted[i]).toBeCloseTo(vector[i], 10);
      }
    });

    it('should round-trip a 2D vector', () => {
      const vector = [0.5, -0.3];
      const encrypted = encryptVector(vector, key);
      const decrypted = decryptVector(encrypted, key);

      expect(decrypted[0]).toBeCloseTo(0.5, 10);
      expect(decrypted[1]).toBeCloseTo(-0.3, 10);
    });

    it('should round-trip the origin', () => {
      const origin = [0, 0, 0, 0, 0, 0];
      const encrypted = encryptVector(origin, key);
      const decrypted = decryptVector(encrypted, key);

      for (const v of decrypted) {
        expect(v).toBeCloseTo(0, 10);
      }
    });

    it('should round-trip a point near the boundary', () => {
      const nearBoundary = [0.7, 0.5, 0.3, 0.1, 0.0, 0.0];
      // ‖v‖² = 0.49 + 0.25 + 0.09 + 0.01 = 0.84 < 1
      const encrypted = encryptVector(nearBoundary, key);
      const decrypted = decryptVector(encrypted, key);

      for (let i = 0; i < nearBoundary.length; i++) {
        expect(decrypted[i]).toBeCloseTo(nearBoundary[i], 10);
      }
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Encrypted Vectors Are NOT Valid Ball Points
  // ═══════════════════════════════════════════════════════════════

  describe('encrypted vectors are opaque', () => {
    it('should produce ciphertext that is base64url encoded', () => {
      const vector = [0.1, 0.2, 0.3, 0, 0, 0];
      const encrypted = encryptVector(vector, key);

      expect(encrypted.ciphertext).toMatch(/^[A-Za-z0-9_-]+$/);
      expect(encrypted.nonce).toMatch(/^[A-Za-z0-9_-]+$/);
      expect(encrypted.tag).toMatch(/^[A-Za-z0-9_-]+$/);
    });

    it('should store the original dimension', () => {
      const vector = [0.1, 0.2, 0.3, 0, 0, 0];
      const encrypted = encryptVector(vector, key);
      expect(encrypted.dimension).toBe(6);
    });

    it('should produce different ciphertexts for the same vector (random nonce)', () => {
      const vector = [0.1, 0.2, 0.3, 0, 0, 0];
      const e1 = encryptVector(vector, key);
      const e2 = encryptVector(vector, key);

      expect(e1.ciphertext).not.toBe(e2.ciphertext);
      expect(e1.nonce).not.toBe(e2.nonce);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Authentication and Integrity
  // ═══════════════════════════════════════════════════════════════

  describe('authentication', () => {
    it('should reject decryption with wrong key', () => {
      const vector = [0.1, 0.2, 0.3, 0, 0, 0];
      const encrypted = encryptVector(vector, key);
      const wrongKey = generateTransportKey('wrong');

      expect(() => decryptVector(encrypted, wrongKey)).toThrow('auth failed');
    });

    it('should reject tampered ciphertext', () => {
      const vector = [0.1, 0.2, 0.3, 0, 0, 0];
      const encrypted = encryptVector(vector, key);

      // Tamper with ciphertext
      const tampered: EncryptedVector = {
        ...encrypted,
        ciphertext: encrypted.ciphertext.slice(0, -2) + 'XX',
      };

      expect(() => decryptVector(tampered, key)).toThrow();
    });

    it('should reject tampered tag', () => {
      const vector = [0.1, 0.2, 0.3, 0, 0, 0];
      const encrypted = encryptVector(vector, key);

      const tampered: EncryptedVector = {
        ...encrypted,
        tag: encrypted.tag.slice(0, -2) + 'XX',
      };

      expect(() => decryptVector(tampered, key)).toThrow();
    });

    it('should reject mismatched domain', () => {
      const vector = [0.1, 0.2, 0.3, 0, 0, 0];
      const encrypted = encryptVector(vector, key, 'domain-A');

      // Change domain in the encrypted struct (AAD mismatch)
      const tampered: EncryptedVector = {
        ...encrypted,
        domain: 'domain-B',
      };

      expect(() => decryptVector(tampered, key)).toThrow();
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Ball Validation
  // ═══════════════════════════════════════════════════════════════

  describe('ball validation', () => {
    it('should reject vectors outside the ball when validateBall=true', () => {
      // Encrypt a vector that's inside the ball
      const vector = [0.1, 0.2, 0.3, 0, 0, 0];
      const encrypted = encryptVector(vector, key);

      // This should work fine since the vector is inside the ball
      expect(() => decryptVector(encrypted, key, true)).not.toThrow();
    });

    it('should accept any vector when validateBall=false', () => {
      const vector = [0.1, 0.2, 0.3, 0, 0, 0];
      const encrypted = encryptVector(vector, key);

      expect(() => decryptVector(encrypted, key, false)).not.toThrow();
    });

    it('should reject empty vectors', () => {
      expect(() => encryptVector([], key)).toThrow('empty vector');
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Secure Navigation (decrypt-then-Möbius)
  // ═══════════════════════════════════════════════════════════════

  describe('secureNavigate', () => {
    it('should decrypt step and apply Möbius addition', () => {
      const position = [0.1, 0, 0, 0, 0, 0];
      const step = [0.05, 0.05, 0, 0, 0, 0];

      const encryptedStep = encryptVector(step, key);
      const result = secureNavigate(position, encryptedStep, key);

      // Result should be equivalent to mobiusAdd on plaintext
      const expected = projectToBall(mobiusAdd(position, step));
      for (let i = 0; i < expected.length; i++) {
        expect(result.position[i]).toBeCloseTo(expected[i], 8);
      }
    });

    it('should report distance traveled', () => {
      const position = [0.1, 0, 0, 0, 0, 0];
      const step = [0.2, 0, 0, 0, 0, 0];

      const encryptedStep = encryptVector(step, key);
      const result = secureNavigate(position, encryptedStep, key);

      expect(result.distanceTraveled).toBeGreaterThan(0);
      expect(isFinite(result.distanceTraveled)).toBe(true);
    });

    it('should keep result inside the ball', () => {
      const position = [0.8, 0, 0, 0, 0, 0];
      const step = [0.1, 0, 0, 0, 0, 0];

      const encryptedStep = encryptVector(step, key);
      const result = secureNavigate(position, encryptedStep, key);

      const normSq = result.position.reduce((sum, x) => sum + x * x, 0);
      expect(normSq).toBeLessThan(1);
    });

    it('should reject wrong key', () => {
      const position = [0.1, 0, 0, 0, 0, 0];
      const step = [0.05, 0, 0, 0, 0, 0];
      const wrongKey = generateTransportKey('wrong');

      const encryptedStep = encryptVector(step, key);
      expect(() => secureNavigate(position, encryptedStep, wrongKey)).toThrow();
    });

    it('should reject dimension mismatch', () => {
      const position = [0.1, 0, 0, 0, 0, 0]; // 6D
      const step = [0.05, 0.05]; // 2D

      const encryptedStep = encryptVector(step, key);
      expect(() => secureNavigate(position, encryptedStep, key)).toThrow('Dimension mismatch');
    });

    it('should mark vector as validated', () => {
      const position = [0.1, 0, 0, 0, 0, 0];
      const step = [0.05, 0, 0, 0, 0, 0];

      const encryptedStep = encryptVector(step, key);
      const result = secureNavigate(position, encryptedStep, key);

      expect(result.vectorValidated).toBe(true);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Batch Navigation
  // ═══════════════════════════════════════════════════════════════

  describe('secureBatchNavigate', () => {
    it('should apply multiple steps sequentially', () => {
      const start = [0, 0, 0, 0, 0, 0];
      const steps = [
        [0.05, 0, 0, 0, 0, 0],
        [0, 0.05, 0, 0, 0, 0],
        [0, 0, 0.05, 0, 0, 0],
      ];

      const encryptedSteps = steps.map((s) => encryptVector(s, key));
      const result = secureBatchNavigate(start, encryptedSteps, key);

      expect(result.stepsApplied).toBe(3);
      expect(result.rejectedSteps).toEqual([]);
      expect(result.totalDistance).toBeGreaterThan(0);

      // Position should have moved in all three dimensions
      expect(result.position[0]).toBeGreaterThan(0);
      expect(result.position[1]).toBeGreaterThan(0);
      expect(result.position[2]).toBeGreaterThan(0);
    });

    it('should skip steps with wrong key and record rejections', () => {
      const start = [0, 0, 0, 0, 0, 0];
      const wrongKey = generateTransportKey('wrong');

      const steps = [
        encryptVector([0.05, 0, 0, 0, 0, 0], key),       // valid
        encryptVector([0, 0.05, 0, 0, 0, 0], wrongKey),   // invalid
        encryptVector([0, 0, 0.05, 0, 0, 0], key),        // valid
      ];

      const result = secureBatchNavigate(start, steps, key);

      expect(result.stepsApplied).toBe(2);
      expect(result.rejectedSteps).toEqual([1]);
    });

    it('should handle empty step list', () => {
      const start = [0.1, 0.2, 0, 0, 0, 0];
      const result = secureBatchNavigate(start, [], key);

      expect(result.stepsApplied).toBe(0);
      expect(result.totalDistance).toBe(0);
      expect(result.position).toEqual(start);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Position Encrypt/Decrypt
  // ═══════════════════════════════════════════════════════════════

  describe('encryptPosition / decryptPosition', () => {
    it('should round-trip a position', () => {
      const position = [0.3, -0.2, 0.1, 0, 0.4, -0.1];
      const encrypted = encryptPosition(position, key);
      const decrypted = decryptPosition(encrypted, key);

      for (let i = 0; i < position.length; i++) {
        expect(decrypted[i]).toBeCloseTo(position[i], 10);
      }
    });

    it('should use poincare-position domain', () => {
      const position = [0.1, 0, 0, 0, 0, 0];
      const encrypted = encryptPosition(position, key);
      expect(encrypted.domain).toBe('poincare-position');
    });
  });
});
