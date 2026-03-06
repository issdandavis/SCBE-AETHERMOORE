/**
 * @file jwt.test.ts
 * @module tests/conference
 *
 * Tests for JWT auth service: password hashing, token signing/verification,
 * refresh token generation and hashing.
 */

import { describe, it, expect } from 'vitest';
import {
  hashPassword,
  verifyPassword,
  signAccessToken,
  verifyAccessToken,
  generateRefreshToken,
  hashRefreshToken,
  type AccessTokenPayload,
} from '../../conference-app/src/api/services/jwt';

describe('Password hashing', () => {
  it('hashes and verifies a password', () => {
    const hash = hashPassword('mySecurePass123');
    expect(hash).toContain(':');
    expect(verifyPassword('mySecurePass123', hash)).toBe(true);
  });

  it('rejects wrong password', () => {
    const hash = hashPassword('correct-password');
    expect(verifyPassword('wrong-password', hash)).toBe(false);
  });

  it('produces different hashes for same password (random salt)', () => {
    const h1 = hashPassword('samePass');
    const h2 = hashPassword('samePass');
    expect(h1).not.toBe(h2);
    // But both should verify
    expect(verifyPassword('samePass', h1)).toBe(true);
    expect(verifyPassword('samePass', h2)).toBe(true);
  });

  it('rejects malformed stored hash', () => {
    expect(verifyPassword('test', 'nocolon')).toBe(false);
    expect(verifyPassword('test', '')).toBe(false);
  });
});

describe('Access tokens', () => {
  const payload: AccessTokenPayload = {
    sub: 'user-123',
    email: 'test@example.com',
    role: 'coder',
    displayName: 'Test User',
  };

  it('signs and verifies a token', () => {
    const token = signAccessToken(payload);
    expect(typeof token).toBe('string');
    expect(token.split('.')).toHaveLength(3); // JWT format

    const decoded = verifyAccessToken(token);
    expect(decoded).not.toBeNull();
    expect(decoded!.sub).toBe('user-123');
    expect(decoded!.email).toBe('test@example.com');
    expect(decoded!.role).toBe('coder');
    expect(decoded!.displayName).toBe('Test User');
  });

  it('rejects invalid token', () => {
    expect(verifyAccessToken('not.a.valid.token')).toBeNull();
    expect(verifyAccessToken('')).toBeNull();
  });

  it('rejects tampered token', () => {
    const token = signAccessToken(payload);
    const tampered = token.slice(0, -4) + 'XXXX';
    expect(verifyAccessToken(tampered)).toBeNull();
  });
});

describe('Refresh tokens', () => {
  it('generates a refresh token with hash and expiry', () => {
    const rt = generateRefreshToken();
    expect(rt.token).toBeTruthy();
    expect(rt.hash).toBeTruthy();
    expect(rt.token).not.toBe(rt.hash);
    expect(new Date(rt.expiresAt).getTime()).toBeGreaterThan(Date.now());
  });

  it('hashRefreshToken matches generateRefreshToken hash', () => {
    const rt = generateRefreshToken();
    const rehash = hashRefreshToken(rt.token);
    expect(rehash).toBe(rt.hash);
  });

  it('different tokens produce different hashes', () => {
    const rt1 = generateRefreshToken();
    const rt2 = generateRefreshToken();
    expect(rt1.token).not.toBe(rt2.token);
    expect(rt1.hash).not.toBe(rt2.hash);
  });
});
