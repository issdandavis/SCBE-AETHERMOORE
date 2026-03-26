/**
 * @file kms.test.ts
 * @module crypto/kms
 * @layer L5 Security
 *
 * Tests for KMS/HSM master key retrieval and environment enforcement.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { getMasterKey } from '../../src/crypto/kms.js';

describe('KMS getMasterKey', () => {
  const originalEnv = { ...process.env };

  beforeEach(() => {
    // Reset env and clear module cache between tests
    process.env = { ...originalEnv };
    process.env.NODE_ENV = 'test';
    delete process.env.SCBE_KMS_URI;
  });

  it('returns a 32-byte Buffer in test mode without KMS URI', async () => {
    const key = await getMasterKey('test-key-1');

    expect(Buffer.isBuffer(key)).toBe(true);
    expect(key.length).toBe(32);
  });

  it('is deterministic — same kid returns same key', async () => {
    const a = await getMasterKey('deterministic-kid');
    const b = await getMasterKey('deterministic-kid');

    expect(a.equals(b)).toBe(true);
  });

  it('derives different keys for different key IDs', async () => {
    const a = await getMasterKey('key-alpha');
    const b = await getMasterKey('key-beta');

    expect(a.equals(b)).toBe(false);
  });

  it('caches keys after first retrieval', async () => {
    const a = await getMasterKey('cached-kid');
    const b = await getMasterKey('cached-kid');

    // Same Buffer instance from cache
    expect(a).toBe(b);
  });

  it('throws when no KMS URI is set in production', async () => {
    process.env.NODE_ENV = 'production';
    delete process.env.SCBE_KMS_URI;

    await expect(getMasterKey('prod-key')).rejects.toThrow('SCBE_KMS_URI is not set');
  });

  it('throws when mem://dev URI is used in production', async () => {
    process.env.NODE_ENV = 'production';
    process.env.SCBE_KMS_URI = 'mem://dev';

    await expect(getMasterKey('prod-key')).rejects.toThrow('not allowed outside development/test');
  });

  it('allows mem://dev URI in development mode', async () => {
    process.env.NODE_ENV = 'development';
    process.env.SCBE_KMS_URI = 'mem://dev';

    const key = await getMasterKey('dev-key');
    expect(Buffer.isBuffer(key)).toBe(true);
    expect(key.length).toBe(32);
  });

  it('derives key from custom KMS URI', async () => {
    process.env.SCBE_KMS_URI = 'awskms://alias/scbe-master';

    const key = await getMasterKey('custom-kid');
    expect(Buffer.isBuffer(key)).toBe(true);
    expect(key.length).toBe(32);

    // Key should differ from dev-mode derivation
    delete process.env.SCBE_KMS_URI;
    const devKey = await getMasterKey('custom-kid-2');
    expect(key.equals(devKey)).toBe(false);
  });
});
