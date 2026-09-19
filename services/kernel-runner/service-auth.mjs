import { createHash, createHmac, timingSafeEqual } from 'node:crypto';

export const AUTH_VERSION = 'scbe-kernel-v1';
export const DECISION_VERSION = 'scbe-kernel-decision-v2';
export const MIN_SECRET_BYTES = 32;
export const DEFAULT_MAX_SKEW_MS = 60_000;

export const AUTH_HEADERS = Object.freeze({
  version: 'x-scbe-auth-version',
  timestamp: 'x-scbe-timestamp',
  nonce: 'x-scbe-nonce',
  signature: 'x-scbe-signature',
});

function asBuffer(value) {
  return Buffer.isBuffer(value) ? value : Buffer.from(value ?? '');
}

function getHeader(headers, name) {
  if (headers && typeof headers.get === 'function') {
    return String(headers.get(name) ?? '');
  }
  const value = headers?.[name] ?? headers?.[name.toLowerCase()] ?? '';
  return String(Array.isArray(value) ? value[0] : value);
}

export function isStrongServiceSecret(secret) {
  return Buffer.byteLength(String(secret ?? ''), 'utf8') >= MIN_SECRET_BYTES;
}

export function sha256Hex(body) {
  return createHash('sha256').update(asBuffer(body)).digest('hex');
}

export function canonicalServiceRequest({ method, path, timestampMs, nonce, body }) {
  const normalizedMethod = String(method ?? '')
    .trim()
    .toUpperCase();
  const normalizedPath = String(path ?? '');
  const normalizedNonce = String(nonce ?? '');
  if (!normalizedMethod || normalizedMethod.includes('\n'))
    throw new Error('invalid service request method');
  if (!normalizedPath.startsWith('/') || normalizedPath.includes('\n')) {
    throw new Error('service request path must be absolute');
  }
  if (!Number.isSafeInteger(timestampMs) || timestampMs <= 0)
    throw new Error('invalid service request timestamp');
  if (!normalizedNonce || normalizedNonce.includes('\n'))
    throw new Error('service request nonce is required');
  return [
    AUTH_VERSION,
    normalizedMethod,
    normalizedPath,
    String(timestampMs),
    normalizedNonce,
    sha256Hex(body),
  ].join('\n');
}

export function signServiceRequest({ secret, method, path, timestampMs, nonce, body }) {
  if (!isStrongServiceSecret(secret)) throw new Error('service secret is not configured securely');
  const canonical = canonicalServiceRequest({ method, path, timestampMs, nonce, body });
  return createHmac('sha256', String(secret)).update(canonical, 'utf8').digest('hex');
}

export function canonicalDecisionReceipt({
  requestMethod,
  requestPath,
  requestDigest,
  requestNonce,
  timestamp,
  action,
  confidence,
  stateVector,
  reason,
}) {
  const method = String(requestMethod ?? '').trim().toUpperCase();
  const path = String(requestPath ?? '');
  const digest = String(requestDigest ?? '').toLowerCase();
  const nonce = String(requestNonce ?? '');
  const issuedAt = String(timestamp ?? '');
  const decision = String(action ?? '');
  const explanation = String(reason ?? '');
  const coherence = Number(stateVector?.coherence);
  const energy = Number(stateVector?.energy);
  const drift = Number(stateVector?.drift);
  const certainty = Number(confidence);

  if (!method || method.includes('\n')) throw new Error('invalid receipt method');
  if (!path.startsWith('/') || path.includes('\n')) throw new Error('invalid receipt path');
  if (!/^[a-f0-9]{64}$/.test(digest)) throw new Error('invalid receipt request digest');
  if (!/^[A-Za-z0-9_-]{22,128}$/.test(nonce)) throw new Error('invalid receipt nonce');
  if (!issuedAt || !decision || !explanation) throw new Error('incomplete decision receipt');
  if (![certainty, coherence, energy, drift].every(Number.isFinite)) {
    throw new Error('non-finite decision receipt value');
  }

  // A JSON array gives an unambiguous typed order without key-order reliance.
  return JSON.stringify([
    DECISION_VERSION,
    method,
    path,
    digest,
    nonce,
    issuedAt,
    decision,
    certainty.toFixed(4),
    coherence.toFixed(4),
    energy.toFixed(4),
    drift.toFixed(4),
    explanation,
  ]);
}

export function signDecisionReceipt({ secret, ...receipt }) {
  if (!isStrongServiceSecret(secret)) throw new Error('service secret is not configured securely');
  return createHmac('sha256', String(secret))
    .update(canonicalDecisionReceipt(receipt), 'utf8')
    .digest('hex');
}

export function verifyDecisionReceipt({ secret, signature, ...receipt }) {
  if (!isStrongServiceSecret(secret)) return false;
  let expected;
  try {
    expected = signDecisionReceipt({ secret, ...receipt });
  } catch {
    return false;
  }
  return constantTimeHexEqual(expected, signature);
}

function constantTimeHexEqual(left, right) {
  if (!/^[a-f0-9]{64}$/i.test(String(left)) || !/^[a-f0-9]{64}$/i.test(String(right))) return false;
  return timingSafeEqual(Buffer.from(String(left), 'hex'), Buffer.from(String(right), 'hex'));
}

export class ReplayGuard {
  constructor({ windowMs = DEFAULT_MAX_SKEW_MS, maxEntries = 10_000 } = {}) {
    this.windowMs = windowMs;
    this.maxEntries = maxEntries;
    this.nonces = new Map();
  }

  prune(nowMs) {
    for (const [nonce, expiresAt] of this.nonces) {
      if (expiresAt <= nowMs) this.nonces.delete(nonce);
    }
  }

  consume(nonce, nowMs) {
    this.prune(nowMs);
    if (this.nonces.has(nonce)) {
      return { ok: false, code: 'service_request_replay' };
    }
    if (this.nonces.size >= this.maxEntries) {
      // Never evict a live nonce to admit new work: eviction would reopen its
      // replay window. Saturation is availability loss and must fail closed.
      return { ok: false, code: 'service_replay_cache_full' };
    }
    this.nonces.set(nonce, nowMs + this.windowMs);
    return { ok: true, code: 'service_request_fresh' };
  }

  get size() {
    return this.nonces.size;
  }
}

export function verifyServiceRequest({
  secret,
  method,
  path,
  body,
  headers,
  nowMs = Date.now(),
  maxSkewMs = DEFAULT_MAX_SKEW_MS,
  replayGuard,
}) {
  if (!isStrongServiceSecret(secret)) {
    return { ok: false, status: 503, code: 'service_auth_not_configured' };
  }

  const version = getHeader(headers, AUTH_HEADERS.version);
  const timestampText = getHeader(headers, AUTH_HEADERS.timestamp);
  const nonce = getHeader(headers, AUTH_HEADERS.nonce);
  const suppliedSignature = getHeader(headers, AUTH_HEADERS.signature);
  if (version !== AUTH_VERSION) return { ok: false, status: 401, code: 'invalid_service_auth' };
  if (!/^\d{10,16}$/.test(timestampText))
    return { ok: false, status: 401, code: 'invalid_service_auth' };
  if (!/^[A-Za-z0-9_-]{22,128}$/.test(nonce))
    return { ok: false, status: 401, code: 'invalid_service_auth' };

  const timestampMs = Number(timestampText);
  if (!Number.isSafeInteger(timestampMs) || Math.abs(nowMs - timestampMs) > maxSkewMs) {
    return { ok: false, status: 401, code: 'stale_service_request' };
  }

  let expectedSignature;
  try {
    expectedSignature = signServiceRequest({ secret, method, path, timestampMs, nonce, body });
  } catch {
    return { ok: false, status: 401, code: 'invalid_service_auth' };
  }
  if (!constantTimeHexEqual(expectedSignature, suppliedSignature)) {
    return { ok: false, status: 401, code: 'invalid_service_auth' };
  }
  if (replayGuard) {
    const replayStatus = replayGuard.consume(nonce, nowMs);
    if (!replayStatus.ok) {
      return {
        ok: false,
        status: replayStatus.code === 'service_request_replay' ? 409 : 503,
        code: replayStatus.code,
      };
    }
  }
  return { ok: true, status: 200, code: 'service_auth_valid' };
}
