/**
 * SpiralAuth - intent-bound AI operation envelopes.
 *
 * This module treats constructed-language tokens and harmonic/modal labels as
 * command taxonomy. It is not the primary SCBE security boundary; Sacred Eggs
 * and the separate security stack handle authority. The MAC here is transport
 * integrity for AI operation routing, replay hygiene, and auditability.
 */

import { createHash, createHmac, randomBytes, timingSafeEqual } from 'node:crypto';
import { canonicalize, type JsonValue } from '../crypto/jcs.js';

export type SpiralAuthModality = 'STRICT' | 'ADAPTIVE' | 'PROBE' | 'EMERGENT';

export interface SpiralAuthLexiconEntry {
  id: number;
  meaning: string;
  glyph?: string;
}

export type SpiralAuthLexicon = Record<string, SpiralAuthLexiconEntry>;

export interface SpiralAuthSignParams {
  command: string;
  modality: SpiralAuthModality;
  secretKey: string;
  lexicon: SpiralAuthLexicon;
  body?: JsonValue;
  tongue?: string;
  ttlMs?: number;
  nonce?: string;
  timestampMs?: number;
}

export interface SpiralAuthEnvelope {
  version: 'spiralauth-v1';
  tongue: string;
  modality: SpiralAuthModality;
  command: string;
  token_ids: number[];
  token_meanings: string[];
  ts: number;
  ttl: number;
  nonce: string;
  canonical_body_hash: string;
  body?: JsonValue;
  mac: string;
}

export interface SpiralAuthVerifyParams {
  envelope: SpiralAuthEnvelope;
  secretKey: string;
  lexicon: SpiralAuthLexicon;
  nowMs?: number;
  allowSkewMs?: number;
}

export interface SpiralAuthVerification {
  valid: boolean;
  reason?: string;
  token_ids?: number[];
  token_meanings?: string[];
}

const DEFAULT_TTL_MS = 5 * 60 * 1000;
const DEFAULT_SKEW_MS = 120 * 1000;

export const DEFAULT_SPIRALAUTH_LEXICON: SpiralAuthLexicon = {
  korah: { id: 0, meaning: 'initiate', glyph: '⟡' },
  aelin: { id: 1, meaning: 'transform', glyph: '◈' },
  dahru: { id: 2, meaning: 'finalize', glyph: '⬡' },
  melik: { id: 3, meaning: 'query', glyph: '◇' },
  sorin: { id: 4, meaning: 'protect', glyph: '⬢' },
  tivar: { id: 5, meaning: 'connect', glyph: '⟐' },
  ulmar: { id: 6, meaning: 'release', glyph: '◌' },
  vexin: { id: 7, meaning: 'archive', glyph: '⏣' },
};

function sha256HmacHex(secretKey: string, message: string): string {
  return createHmac('sha256', secretKey).update(message).digest('hex');
}

function macEqual(a: string, b: string): boolean {
  const left = Buffer.from(a, 'hex');
  const right = Buffer.from(b, 'hex');
  if (left.length !== right.length) return false;
  return timingSafeEqual(left, right);
}

function bodyHash(body: JsonValue | undefined): string {
  const bodyText = body === undefined ? '' : canonicalize(body);
  return createHash('sha256').update(bodyText).digest('hex');
}

export function tokenizeCommand(
  command: string,
  lexicon: SpiralAuthLexicon
): { tokenIds: number[]; tokenMeanings: string[]; unknownTokens: string[] } {
  const tokenIds: number[] = [];
  const tokenMeanings: string[] = [];
  const unknownTokens: string[] = [];
  for (const token of command.toLowerCase().split(/\s+/).filter(Boolean)) {
    const entry = lexicon[token];
    if (!entry) {
      unknownTokens.push(token);
      continue;
    }
    tokenIds.push(entry.id);
    tokenMeanings.push(entry.meaning);
  }
  return { tokenIds, tokenMeanings, unknownTokens };
}

export function canonicalSpiralAuthEnvelope(
  envelope: Omit<SpiralAuthEnvelope, 'mac'>
): string {
  return canonicalize(envelope);
}

export function signSpiralAuthCommand(params: SpiralAuthSignParams): SpiralAuthEnvelope {
  const { tokenIds, tokenMeanings, unknownTokens } = tokenizeCommand(params.command, params.lexicon);
  if (unknownTokens.length > 0) {
    throw new Error(`unknown command tokens: ${unknownTokens.join(',')}`);
  }
  if (tokenIds.length === 0) {
    throw new Error('command produced no known tokens');
  }

  const withoutMac: Omit<SpiralAuthEnvelope, 'mac'> = {
    version: 'spiralauth-v1',
    tongue: params.tongue || 'KO',
    modality: params.modality,
    command: params.command,
    token_ids: tokenIds,
    token_meanings: tokenMeanings,
    ts: params.timestampMs ?? Date.now(),
    ttl: params.ttlMs ?? DEFAULT_TTL_MS,
    nonce: params.nonce ?? randomBytes(16).toString('hex'),
    canonical_body_hash: bodyHash(params.body),
    ...(params.body === undefined ? {} : { body: params.body }),
  };
  const mac = sha256HmacHex(params.secretKey, canonicalSpiralAuthEnvelope(withoutMac));
  return { ...withoutMac, mac };
}

export function verifySpiralAuthEnvelope(params: SpiralAuthVerifyParams): SpiralAuthVerification {
  const now = params.nowMs ?? Date.now();
  const skew = Math.abs(now - params.envelope.ts);
  const allowSkew = params.allowSkewMs ?? DEFAULT_SKEW_MS;
  if (skew > allowSkew) {
    return { valid: false, reason: 'timestamp skew exceeded' };
  }
  if (now > params.envelope.ts + params.envelope.ttl) {
    return { valid: false, reason: 'envelope expired' };
  }

  const { tokenIds, tokenMeanings, unknownTokens } = tokenizeCommand(
    params.envelope.command,
    params.lexicon
  );
  if (unknownTokens.length > 0) {
    return { valid: false, reason: `unknown command tokens: ${unknownTokens.join(',')}` };
  }
  if (JSON.stringify(tokenIds) !== JSON.stringify(params.envelope.token_ids)) {
    return { valid: false, reason: 'token id mismatch' };
  }
  if (JSON.stringify(tokenMeanings) !== JSON.stringify(params.envelope.token_meanings)) {
    return { valid: false, reason: 'token meaning mismatch' };
  }
  if (bodyHash(params.envelope.body) !== params.envelope.canonical_body_hash) {
    return { valid: false, reason: 'body hash mismatch' };
  }

  const { mac: _mac, ...withoutMac } = params.envelope;
  const expected = sha256HmacHex(params.secretKey, canonicalSpiralAuthEnvelope(withoutMac));
  if (!macEqual(params.envelope.mac, expected)) {
    return { valid: false, reason: 'mac verification failed' };
  }
  return { valid: true, token_ids: tokenIds, token_meanings: tokenMeanings };
}
