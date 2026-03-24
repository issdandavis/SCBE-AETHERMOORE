/**
 * @file hkdf.test.ts
 * @module crypto/hkdf
 * @layer L5 Security
 *
 * Tests for HKDF-SHA256 key derivation function.
 */

import { describe, it, expect } from 'vitest';
import { hkdfSha256 } from '../../src/crypto/hkdf.js';

describe('hkdfSha256', () => {
  const ikm = Buffer.from('input-keying-material');
  const salt = Buffer.from('salt-value');
  const info = Buffer.from('context-info');

  it('derives key material of the requested length', () => {
    const key16 = hkdfSha256(ikm, salt, info, 16);
    expect(key16.length).toBe(16);

    const key32 = hkdfSha256(ikm, salt, info, 32);
    expect(key32.length).toBe(32);

    const key64 = hkdfSha256(ikm, salt, info, 64);
    expect(key64.length).toBe(64);
  });

  it('is deterministic — same inputs produce same output', () => {
    const a = hkdfSha256(ikm, salt, info, 32);
    const b = hkdfSha256(ikm, salt, info, 32);
    expect(Buffer.compare(a, b)).toBe(0);
  });

  it('different IKM produces different output', () => {
    const a = hkdfSha256(Buffer.from('key-a'), salt, info, 32);
    const b = hkdfSha256(Buffer.from('key-b'), salt, info, 32);
    expect(Buffer.compare(a, b)).not.toBe(0);
  });

  it('different salt produces different output', () => {
    const a = hkdfSha256(ikm, Buffer.from('salt-a'), info, 32);
    const b = hkdfSha256(ikm, Buffer.from('salt-b'), info, 32);
    expect(Buffer.compare(a, b)).not.toBe(0);
  });

  it('different info produces different output', () => {
    const a = hkdfSha256(ikm, salt, Buffer.from('info-a'), 32);
    const b = hkdfSha256(ikm, salt, Buffer.from('info-b'), 32);
    expect(Buffer.compare(a, b)).not.toBe(0);
  });

  it('shorter output is a prefix of longer output', () => {
    const short = hkdfSha256(ikm, salt, info, 16);
    const long = hkdfSha256(ikm, salt, info, 32);
    expect(Buffer.compare(short, long.subarray(0, 16))).toBe(0);
  });

  it('handles empty salt and info', () => {
    const key = hkdfSha256(ikm, Buffer.alloc(0), Buffer.alloc(0), 32);
    expect(key.length).toBe(32);
    expect(key.some((b) => b !== 0)).toBe(true);
  });

  it('handles single-byte output', () => {
    const key = hkdfSha256(ikm, salt, info, 1);
    expect(key.length).toBe(1);
  });

  it('handles output larger than one SHA-256 block (>32 bytes)', () => {
    const key = hkdfSha256(ikm, salt, info, 128);
    expect(key.length).toBe(128);
    expect(key.some((b) => b !== 0)).toBe(true);
  });
});
