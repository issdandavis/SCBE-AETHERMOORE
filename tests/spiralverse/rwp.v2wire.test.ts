/**
 * RWP v2 Wire Format (ver="2") - Tests
 * ====================================
 *
 * Validates the Spiralverse v2 JSON envelope shape described in the spec paste:
 * - ver="2"
 * - tongue="KO|AV|RU|CA|UM|DR"
 * - sigs as an array of { tongue, kid?, sig }
 * - timestamp + nonce replay checks
 * - policy enforcement ("critical" requires RU+UM+DR)
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { randomBytes } from 'crypto';
import {
  clearWireNonceCache,
  signRoundtableV2Wire,
  verifyRoundtableV2Wire,
  type Keyring,
  type RWP2WireEnvelope,
} from '../../src/spiralverse';

const testKeyring: Keyring = {
  ko: randomBytes(32),
  av: randomBytes(32),
  ru: randomBytes(32),
  ca: randomBytes(32),
  um: randomBytes(32),
  dr: randomBytes(32),
};

describe('RWP v2 wire envelopes (ver="2")', () => {
  beforeEach(() => {
    clearWireNonceCache();
  });

  it('creates the exact v2 wire shape with sigs[] entries', () => {
    const env = signRoundtableV2Wire({ hello: 'world' }, 'KO', 'k=v', testKeyring, ['KO', 'RU'], {
      kid: 'k1',
      timestamp: 1800000000,
    });

    expect(env.ver).toBe('2');
    expect(env.tongue).toBe('KO');
    expect(typeof env.aad).toBe('string');
    expect(typeof env.ts).toBe('number');
    expect(typeof env.nonce).toBe('string');
    expect(typeof env.payload).toBe('string');
    expect(Array.isArray(env.sigs)).toBe(true);
    expect(env.sigs.length).toBe(2);
    expect(env.sigs[0]).toHaveProperty('tongue');
    expect(env.sigs[0]).toHaveProperty('sig');
    expect(env.sigs[0]).toHaveProperty('kid');
  });

  it('verifies valid signatures and decodes JSON payload', () => {
    const env = signRoundtableV2Wire(
      { action: 'deploy', ok: true },
      'KO',
      'agent=abc',
      testKeyring,
      ['KO', 'RU'],
      {
        timestamp: Math.floor(Date.now() / 1000),
      }
    );

    const vr = verifyRoundtableV2Wire(env, testKeyring, { policy: 'strict' });
    expect(vr.valid).toBe(true);
    expect(vr.validTongues.length).toBeGreaterThan(0);
    expect(vr.payload).toMatchObject({ action: 'deploy', ok: true });
    expect(vr.payloadBytes).toBeDefined();
  });

  it('rejects tampered payload', () => {
    const env = signRoundtableV2Wire({ x: 1 }, 'KO', 'aad', testKeyring, ['KO', 'RU'], {
      timestamp: Math.floor(Date.now() / 1000),
    });

    const tampered: RWP2WireEnvelope = { ...env, payload: env.payload.slice(0, -2) + 'aa' };
    const vr = verifyRoundtableV2Wire(tampered, testKeyring, { policy: 'standard' });
    expect(vr.valid).toBe(false);
  });

  it('enforces critical policy (requires RU+UM+DR)', () => {
    const env = signRoundtableV2Wire(
      { action: 'admin' },
      'KO',
      'aad',
      testKeyring,
      ['RU', 'UM', 'DR'],
      { timestamp: Math.floor(Date.now() / 1000) }
    );

    const vr = verifyRoundtableV2Wire(env, testKeyring, { policy: 'critical' });
    expect(vr.valid).toBe(true);
    expect(vr.validTongues.sort()).toEqual(['DR', 'RU', 'UM']);
  });

  it('rejects replayed nonce', () => {
    const ts = Math.floor(Date.now() / 1000);
    const nonce = randomBytes(16);

    const env = signRoundtableV2Wire({ n: 1 }, 'KO', 'aad', testKeyring, ['KO', 'RU'], {
      timestamp: ts,
      nonce,
    });

    const first = verifyRoundtableV2Wire(env, testKeyring, { policy: 'standard' });
    expect(first.valid).toBe(true);

    const second = verifyRoundtableV2Wire(env, testKeyring, { policy: 'standard' });
    expect(second.valid).toBe(false);
    expect(second.error?.toLowerCase()).toContain('nonce');
  });
});
