/**
 * RWP v2 Wire Format (ver="2")
 * ============================
 *
 * Implements the Spiralverse Protocol v2 JSON envelope shape:
 * {
 *   "ver": "2",
 *   "tongue": "KO|AV|RU|CA|UM|DR",
 *   "aad": "...",
 *   "ts": <unix_timestamp>,
 *   "nonce": "<base64url>",
 *   "kid": "<optional>",
 *   "payload": "<base64url_data>",
 *   "sigs": [{"tongue":"KO","kid":"...","sig":"..."}]
 * }
 *
 * This module is intentionally additive to the existing v2.1 code.
 *
 * @module spiralverse/rwp_v2_wire
 * @since 2026-04-07
 */

import { createHmac, randomBytes } from 'crypto';
import type { Keyring, PolicyLevel, TongueID } from './types';
import { checkPolicy, getRequiredTongues } from './policy';

/** Wire-format tongue identifiers (Spiralverse v2 spec) */
export type RWP2WireTongue = 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';

/** Wire-format signature entry (Spiralverse v2 spec) */
export interface RWP2WireSig {
  tongue: RWP2WireTongue;
  kid?: string;
  sig: string; // base64url HMAC signature
}

/** RWP v2 wire envelope structure (Spiralverse v2 spec) */
export interface RWP2WireEnvelope {
  ver: '2';
  tongue: RWP2WireTongue; // Primary protocol layer
  aad: string; // Sorted context metadata
  ts: number; // Unix timestamp (seconds or ms allowed)
  nonce: string; // base64url random
  kid?: string; // Versioned key (optional)
  payload: string; // base64url data
  sigs: RWP2WireSig[]; // Multi-sig list
}

/** Verification result for RWP v2 wire */
export interface VerifyWireResult {
  valid: boolean;
  validTongues: RWP2WireTongue[];
  payloadBytes?: Buffer;
  payload?: unknown; // JSON if payload is valid JSON utf-8
  error?: string;
}

function toBase64Url(buf: Buffer): string {
  return buf.toString('base64url');
}

function fromBase64Url(s: string): Buffer {
  return Buffer.from(s, 'base64url');
}

function toWireTongue(t: TongueID): RWP2WireTongue {
  switch (t) {
    case 'ko':
      return 'KO';
    case 'av':
      return 'AV';
    case 'ru':
      return 'RU';
    case 'ca':
      return 'CA';
    case 'um':
      return 'UM';
    case 'dr':
      return 'DR';
  }
}

function fromWireTongue(t: RWP2WireTongue): TongueID {
  switch (t) {
    case 'KO':
      return 'ko';
    case 'AV':
      return 'av';
    case 'RU':
      return 'ru';
    case 'CA':
      return 'ca';
    case 'UM':
      return 'um';
    case 'DR':
      return 'dr';
  }
}

function createSignature(key: Buffer, data: Buffer): string {
  const hmac = createHmac('sha256', key);
  hmac.update(data);
  return toBase64Url(hmac.digest());
}

function verifySignature(key: Buffer, data: Buffer, signature: string): boolean {
  const expected = createSignature(key, data);
  if (expected.length !== signature.length) return false;
  let result = 0;
  for (let i = 0; i < expected.length; i++) {
    result |= expected.charCodeAt(i) ^ signature.charCodeAt(i);
  }
  return result === 0;
}

/**
 * Create signature data for v2 wire format (domain-separated per signing tongue).
 *
 * Includes `kid` in the transcript when present (empty-string otherwise).
 */
function createWireSignatureData(
  env: Omit<RWP2WireEnvelope, 'sigs'>,
  signingTongue: TongueID
): Buffer {
  const kid = env.kid ?? '';
  const data = `${env.ver}.${env.tongue}.${signingTongue}.${env.aad}.${env.payload}.${env.nonce}.${env.ts}.${kid}`;
  return Buffer.from(data, 'utf8');
}

// ---------------------------------------------------------------------------
// Nonce Cache (Replay Protection) - local to v2 wire
// ---------------------------------------------------------------------------

const wireNonceCache = new Set<string>();
const wireNonceCacheTimestamps = new Map<string, number>();

function checkAndAddWireNonce(nonce: string, timestampMs: number): boolean {
  const now = Date.now();
  for (const [n, ts] of wireNonceCacheTimestamps) {
    if (now - ts > 600000) {
      wireNonceCache.delete(n);
      wireNonceCacheTimestamps.delete(n);
    }
  }

  if (wireNonceCache.has(nonce)) return false;
  wireNonceCache.add(nonce);
  wireNonceCacheTimestamps.set(nonce, timestampMs);
  return true;
}

export function clearWireNonceCache(): void {
  wireNonceCache.clear();
  wireNonceCacheTimestamps.clear();
}

/**
 * Sign an RWP v2 wire envelope (ver="2") with a Roundtable of tongues.
 */
export function signRoundtableV2Wire(
  payload: Buffer | Record<string, unknown> | string,
  primaryTongue: RWP2WireTongue,
  aad: string,
  keyring: Keyring,
  signingTongues: RWP2WireTongue[],
  options: { kid?: string; timestamp?: number; nonce?: Buffer } = {}
): RWP2WireEnvelope {
  if (payload === undefined || payload === null) {
    throw new Error('Payload is required');
  }
  if (!primaryTongue) {
    throw new Error('Primary tongue is required');
  }
  if (!signingTongues || signingTongues.length === 0) {
    throw new Error('At least one signing tongue is required');
  }

  const ts = options.timestamp ?? Math.floor(Date.now() / 1000);
  const nonce = toBase64Url(options.nonce ?? randomBytes(16));

  const payloadBytes =
    typeof payload === 'string'
      ? Buffer.from(payload, 'utf8')
      : Buffer.isBuffer(payload)
        ? payload
        : Buffer.from(JSON.stringify(payload), 'utf8');

  const env: Omit<RWP2WireEnvelope, 'sigs'> = {
    ver: '2',
    tongue: primaryTongue,
    aad,
    ts,
    nonce,
    payload: toBase64Url(payloadBytes),
    ...(options.kid ? { kid: options.kid } : {}),
  };

  const sigs: RWP2WireSig[] = [];
  for (const wireTongue of signingTongues) {
    const t = fromWireTongue(wireTongue);
    const key = keyring[t];
    if (!key) throw new Error(`Missing key for tongue: ${t}`);
    const data = createWireSignatureData(env, t);
    sigs.push({
      tongue: wireTongue,
      ...(options.kid ? { kid: options.kid } : {}),
      sig: createSignature(key, data),
    });
  }

  return { ...env, sigs };
}

/**
 * Verify an RWP v2 wire envelope (ver="2") with replay + policy enforcement.
 */
export function verifyRoundtableV2Wire(
  envelope: RWP2WireEnvelope,
  keyring: Keyring,
  options: { policy?: PolicyLevel; maxAge?: number; maxFutureSkew?: number } = {}
): VerifyWireResult {
  const policy = options.policy ?? 'standard';
  const maxAge = options.maxAge ?? 300000; // 5 minutes
  const maxFutureSkew = options.maxFutureSkew ?? 60000; // 1 minute

  const validTongues: RWP2WireTongue[] = [];

  try {
    if (envelope.ver !== '2') throw new Error(`Unsupported version: ${envelope.ver}`);

    const tsMs = envelope.ts < 1_000_000_000_000 ? envelope.ts * 1000 : envelope.ts;
    const now = Date.now();
    const age = now - tsMs;

    if (tsMs > now + maxFutureSkew) throw new Error('Timestamp is in the future');
    if (age > maxAge) throw new Error('Timestamp too old (replay window)');

    if (!checkAndAddWireNonce(envelope.nonce, tsMs)) {
      throw new Error('Nonce already used (replay)');
    }

    const base: Omit<RWP2WireEnvelope, 'sigs'> = {
      ver: envelope.ver,
      tongue: envelope.tongue,
      aad: envelope.aad,
      ts: envelope.ts,
      nonce: envelope.nonce,
      payload: envelope.payload,
      ...(envelope.kid ? { kid: envelope.kid } : {}),
    };

    for (const s of envelope.sigs) {
      const t = fromWireTongue(s.tongue);
      const key = keyring[t];
      if (!key) continue;
      const data = createWireSignatureData(base, t);
      if (verifySignature(key, data, s.sig)) validTongues.push(s.tongue);
    }

    if (validTongues.length === 0) throw new Error('No valid signatures');

    const lcTongues = validTongues.map(fromWireTongue);
    if (!checkPolicy(lcTongues, policy)) {
      const required = getRequiredTongues(policy).map(toWireTongue);
      const missing = required.filter((t) => !validTongues.includes(t));
      throw new Error(`Policy violation: missing required tongue(s): ${missing.join(', ')}`);
    }

    const payloadBytes = fromBase64Url(envelope.payload);
    let payloadJson: unknown | undefined;
    try {
      payloadJson = JSON.parse(payloadBytes.toString('utf8'));
    } catch {
      // allow non-JSON payloads
    }

    return {
      valid: true,
      validTongues,
      payloadBytes,
      ...(payloadJson !== undefined ? { payload: payloadJson } : {}),
    };
  } catch (err) {
    return { valid: false, validTongues, error: err instanceof Error ? err.message : String(err) };
  }
}
