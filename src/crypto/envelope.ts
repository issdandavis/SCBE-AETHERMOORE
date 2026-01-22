/**
 * @file envelope.ts
 * @module crypto/envelope
 * @component Cryptographic Envelope System
 * @version 3.0.0
 * @since 2026-01-20
 *
 * SCBE Cryptographic Envelope - Sealed, tamper-evident message containers
 *
 * Features:
 * - AES-256-GCM authenticated encryption
 * - HKDF-SHA256 key derivation
 * - Nonce management with replay prevention
 * - AAD (Additional Authenticated Data) binding
 * - Risk-gated envelope creation
 *
 * Usage:
 * ```typescript
 * const envelope = await createEnvelope({
 *   body: { message: 'secret' },
 *   aad: { intent_id: 'auth-001', ... }
 * });
 * const decrypted = await verifyEnvelope(envelope, key);
 * ```
 */

import crypto from 'node:crypto';
import { hkdfSha256 } from './hkdf.js';
import { canonicalize } from './jcs.js';
import { deriveNoncePrefix, nextNonce } from './nonceManager.js';
import { getMasterKey } from './kms.js';
import { ReplayGuard } from './replayGuard.js';
import { metrics } from '../metrics/telemetry.js';

function b64u(buf: Buffer) {
  return buf.toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}
function fromB64u(s: string) {
  s = s.replace(/-/g, '+').replace(/_/g, '/');
  while (s.length % 4) s += '=';
  return Buffer.from(s, 'base64');
}

export interface AAD {
  envelope_version: string;
  env: string;
  provider_id: string;
  model_id: string;
  intent_id: string;
  phase: string;
  ts: number; // ms epoch
  ttl: number; // ms
  content_type: string;
  schema_hash: string; // SHA-256 hex
  canonical_body_hash: string; // SHA-256 hex
  request_id: string;
  replay_nonce: string; // random string
}

export interface Envelope {
  aad: AAD; // logged only as hashes/ids in production
  kid: string; // key id
  nonce: string; // base64url (96-bit)
  tag: string; // base64url (128-bit)
  ciphertext: string; // base64url
  salt: string; // base64url (256-bit) - for key derivation
}

export type CreateParams = {
  kid: string;
  env: string;
  provider_id: string;
  model_id: string;
  intent_id: string;
  phase: string;
  ttlMs: number;
  content_type: string;
  schema_hash: string;
  request_id: string;
  session_id: string; // for nonce prefix derivation
  body: any; // object/string
};

const replay = new ReplayGuard({
  ttlSeconds: Number(process.env.SCBE_REPLAY_TTL_SECONDS || '600'),
  sizeBits: Number(process.env.SCBE_REPLAY_BLOOM_BITS || '2048'),
  hashes: Number(process.env.SCBE_REPLAY_BLOOM_HASHES || '4'),
});

function sha256Hex(buf: Buffer) {
  return crypto.createHash('sha256').update(buf).digest('hex');
}

export async function createEnvelope(p: CreateParams): Promise<Envelope> {
  const t0 = metrics.now();
  // 1) Canonicalize body (JCS) and hash
  const bodyStr = typeof p.body === 'string' ? p.body : canonicalize(p.body);
  const bodyBuf = Buffer.from(bodyStr, 'utf8');
  const canonical_body_hash = sha256Hex(bodyBuf);

  const aad: AAD = {
    envelope_version: 'scbe-v1',
    env: p.env,
    provider_id: p.provider_id,
    model_id: p.model_id,
    intent_id: p.intent_id,
    phase: p.phase,
    ts: Date.now(),
    ttl: p.ttlMs,
    content_type: p.content_type,
    schema_hash: p.schema_hash,
    canonical_body_hash,
    request_id: p.request_id,
    replay_nonce: crypto.randomBytes(16).toString('hex'),
  };

  // 2) Derive subkeys via HKDF: k_enc, k_nonce, k_log
  const ikm = await getMasterKey(p.kid);
  const salt = crypto.randomBytes(32); // per-envelope salt; in prod you may pin/rotate by policy
  const infoBase = Buffer.from(
    `scbe:derivation:v1|env=${p.env}|provider=${p.provider_id}|intent=${p.intent_id}`
  );
  const k_enc = hkdfSha256(ikm, salt, Buffer.concat([infoBase, Buffer.from('|k=enc')]), 32);
  const k_nonce = hkdfSha256(ikm, salt, Buffer.concat([infoBase, Buffer.from('|k=nonce')]), 32);
  const k_log = hkdfSha256(ikm, salt, Buffer.concat([infoBase, Buffer.from('|k=log')]), 32);
  // k_log reserved for future audit record MACs

  // 3) Nonce discipline
  const prefix = deriveNoncePrefix(k_nonce, p.session_id); // 64-bit
  const { nonce } = nextNonce(prefix, p.session_id); // 64b || 32b counter => 96-bit

  // 4) AAD canonicalization (hashes only logged in prod)
  const aadStr = canonicalize(aad);
  const aadBuf = Buffer.from(aadStr, 'utf8');

  // 5) Encrypt (AES-256-GCM, 96-bit nonce, complete AAD coverage)
  try {
    const cipher = crypto.createCipheriv('aes-256-gcm', k_enc, nonce);
    cipher.setAAD(aadBuf);
    const ct = Buffer.concat([cipher.update(bodyBuf), cipher.final()]);
    const tag = cipher.getAuthTag();

    const envl: Envelope = {
      aad,
      kid: p.kid,
      nonce: b64u(nonce),
      tag: b64u(tag),
      ciphertext: b64u(ct),
      salt: b64u(salt),
    };

    metrics.timing('envelope_create_ms', metrics.now() - t0, {
      provider_id: p.provider_id,
      model_id: p.model_id,
      intent_id: p.intent_id,
      phase: p.phase,
    });
    return envl;
  } catch (e) {
    metrics.incr('gcm_failures', 1, { op: 'create' });
    throw e;
  }
}

export type VerifyParams = {
  envelope: Envelope;
  session_id: string;
  allowSkewMs?: number; // default 120000
};

export async function verifyEnvelope(p: VerifyParams): Promise<{ body: any }> {
  const t0 = metrics.now();
  const { envelope } = p;
  const allowSkew = p.allowSkewMs ?? 120_000;
  const now = Date.now();

  // 1) Skew window
  const skew = Math.abs(now - envelope.aad.ts);
  if (skew > allowSkew) {
    metrics.incr('replay_rejects', 1, { reason: 'skew', skew_ms: skew });
    throw new Error('skew/replay');
  }
  // 2) Replay guard (provider_id, request_id)
  const ok = replay.checkAndSet(envelope.aad.provider_id, envelope.aad.request_id, now);
  if (!ok) {
    metrics.incr('replay_rejects', 1, { reason: 'duplicate' });
    throw new Error('replay');
  }

  // 3) Key derivation (must bind env/provider/intent)
  const ikm = await getMasterKey(envelope.kid);
  const salt = fromB64u(envelope.salt);
  if (salt.length !== 32) throw new Error('bad salt size');
  const infoBase = Buffer.from(
    `scbe:derivation:v1|env=${envelope.aad.env}|provider=${envelope.aad.provider_id}|intent=${envelope.aad.intent_id}`
  );
  const k_enc = hkdfSha256(ikm, salt, Buffer.concat([infoBase, Buffer.from('|k=enc')]), 32);
  const k_nonce = hkdfSha256(ikm, salt, Buffer.concat([infoBase, Buffer.from('|k=nonce')]), 32);

  // 4) Nonce re-derive prefix to sanity-check session context (optional)
  const prefix = deriveNoncePrefix(k_nonce, p.session_id);
  const nonce = fromB64u(envelope.nonce);
  if (nonce.length !== 12) throw new Error('bad nonce size');
  if (!nonce.subarray(0, 8).equals(prefix)) {
    metrics.incr('nonce_prefix_mismatch', 1);
    // Not fatal if topologies differ; choose to fail closed:
    throw new Error('nonce/prefix');
  }

  // 5) Verify AAD and decrypt
  const aadStr = canonicalize(envelope.aad);
  const aadBuf = Buffer.from(aadStr, 'utf8');
  const tag = fromB64u(envelope.tag);
  const ct = fromB64u(envelope.ciphertext);

  try {
    const decipher = crypto.createDecipheriv('aes-256-gcm', k_enc, nonce);
    decipher.setAAD(aadBuf);
    decipher.setAuthTag(tag);
    const pt = Buffer.concat([decipher.update(ct), decipher.final()]);
    metrics.timing('envelope_verify_ms', metrics.now() - t0, {
      provider_id: envelope.aad.provider_id,
      model_id: envelope.aad.model_id,
      intent_id: envelope.aad.intent_id,
      phase: envelope.aad.phase,
    });
    // Fail-to-noise policy: return opaque error details (we already threw on failure)
    const contentType = envelope.aad.content_type || 'application/json';
    const body = contentType.includes('json')
      ? JSON.parse(pt.toString('utf8'))
      : pt.toString('utf8');
    return { body };
  } catch (e) {
    metrics.incr('gcm_failures', 1, { op: 'verify' });
    // Fail-to-noise: do not expose differentiating details
    throw new Error('auth-failed');
  }
}
