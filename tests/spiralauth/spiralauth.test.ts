import { describe, expect, it } from 'vitest';
import {
  DEFAULT_SPIRALAUTH_LEXICON,
  signSpiralAuthCommand,
  verifySpiralAuthEnvelope,
} from '../../src/spiralauth/index.js';

const secretKey = 'test-spiralauth-secret';
const nowMs = 1_800_000_000_000;

describe('SpiralAuth AI operation envelopes', () => {
  it('packages and verifies a strict conlang operation envelope', () => {
    const envelope = signSpiralAuthCommand({
      command: 'korah aelin dahru',
      modality: 'STRICT',
      secretKey,
      lexicon: DEFAULT_SPIRALAUTH_LEXICON,
      timestampMs: nowMs,
      nonce: 'nonce-1',
      body: { route: 'compile', target: 'demo' },
    });

    const result = verifySpiralAuthEnvelope({
      envelope,
      secretKey,
      lexicon: DEFAULT_SPIRALAUTH_LEXICON,
      nowMs,
    });

    expect(result.valid).toBe(true);
    expect(result.token_ids).toEqual([0, 1, 2]);
    expect(result.token_meanings).toEqual(['initiate', 'transform', 'finalize']);
  });

  it('rejects modality tamper through the integrity check', () => {
    const envelope = signSpiralAuthCommand({
      command: 'korah aelin dahru',
      modality: 'STRICT',
      secretKey,
      lexicon: DEFAULT_SPIRALAUTH_LEXICON,
      timestampMs: nowMs,
      nonce: 'nonce-2',
    });
    envelope.modality = 'EMERGENT';

    const result = verifySpiralAuthEnvelope({
      envelope,
      secretKey,
      lexicon: DEFAULT_SPIRALAUTH_LEXICON,
      nowMs,
    });

    expect(result).toEqual({ valid: false, reason: 'mac verification failed' });
  });

  it('rejects body tamper before routing the AI operation', () => {
    const envelope = signSpiralAuthCommand({
      command: 'sorin melik',
      modality: 'PROBE',
      secretKey,
      lexicon: DEFAULT_SPIRALAUTH_LEXICON,
      timestampMs: nowMs,
      nonce: 'nonce-3',
      body: { readOnly: true },
    });
    envelope.body = { readOnly: false };

    const result = verifySpiralAuthEnvelope({
      envelope,
      secretKey,
      lexicon: DEFAULT_SPIRALAUTH_LEXICON,
      nowMs,
    });

    expect(result).toEqual({ valid: false, reason: 'body hash mismatch' });
  });

  it('rejects stale envelopes', () => {
    const envelope = signSpiralAuthCommand({
      command: 'korah',
      modality: 'STRICT',
      secretKey,
      lexicon: DEFAULT_SPIRALAUTH_LEXICON,
      timestampMs: nowMs,
      ttlMs: 1000,
      nonce: 'nonce-4',
    });

    const result = verifySpiralAuthEnvelope({
      envelope,
      secretKey,
      lexicon: DEFAULT_SPIRALAUTH_LEXICON,
      nowMs: nowMs + 10_000,
      allowSkewMs: 20_000,
    });

    expect(result).toEqual({ valid: false, reason: 'envelope expired' });
  });

  it('rejects unknown private lexicon tokens', () => {
    expect(() =>
      signSpiralAuthCommand({
        command: 'korah unknown dahru',
        modality: 'STRICT',
        secretKey,
        lexicon: DEFAULT_SPIRALAUTH_LEXICON,
        timestampMs: nowMs,
      })
    ).toThrow('unknown command tokens: unknown');
  });
});
