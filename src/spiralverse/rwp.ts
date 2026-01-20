/**
 * RWP v2.1 Multi-Signature Envelopes
 * ===================================
 *
 * Real World Protocol for secure AI-to-AI communication using
 * domain-separated HMAC-SHA256 signatures via Sacred Tongues.
 *
 * @module spiralverse/rwp
 * @version 2.1.0
 * @since 2026-01-18
 */

import { createHmac, randomBytes } from 'crypto';
import { enforcePolicy } from './policy';
import {
  EnvelopeOptions,
  Keyring,
  NonceCacheEntry,
  RWP2MultiEnvelope,
  ReplayError,
  SignatureError,
  TongueID,
  VerificationOptions,
  VerificationResult,
} from './types';

/**
 * Nonce cache for replay protection
 * LRU cache with automatic expiration
 */
class NonceCache {
  private cache: Map<string, NonceCacheEntry> = new Map();
  private maxSize: number;
  private cleanupInterval: NodeJS.Timeout;

  constructor(maxSize: number = 10000) {
    this.maxSize = maxSize;

    // Cleanup expired entries every minute
    this.cleanupInterval = setInterval(() => this.cleanup(), 60000);
  }

  /**
   * Check if nonce exists in cache
   */
  has(nonce: string): boolean {
    return this.cache.has(nonce);
  }

  /**
   * Add nonce to cache
   */
  add(nonce: string, timestamp: number): void {
    // LRU eviction if cache is full
    if (this.cache.size >= this.maxSize) {
      const firstKey = this.cache.keys().next().value;
      if (firstKey !== undefined) {
        this.cache.delete(firstKey);
      }
    }

    this.cache.set(nonce, { nonce, timestamp });
  }

  /**
   * Remove expired entries
   */
  private cleanup(): void {
    const now = Date.now();
    const expiry = 300000; // 5 minutes

    for (const [nonce, entry] of this.cache.entries()) {
      if (now - entry.timestamp > expiry) {
        this.cache.delete(nonce);
      }
    }
  }

  /**
   * Clear all entries
   */
  clear(): void {
    this.cache.clear();
  }

  /**
   * Get cache size
   */
  size(): number {
    return this.cache.size;
  }

  /**
   * Destroy cache and cleanup interval
   */
  destroy(): void {
    clearInterval(this.cleanupInterval);
    this.cache.clear();
  }
}

// Global nonce cache
const nonceCache = new NonceCache();

/**
 * Generate signature input string
 *
 * Format: ver|primary_tongue|aad|ts|nonce|payload
 */
function getSignatureInput(env: Omit<RWP2MultiEnvelope, 'sigs'>): string {
  return `${env.ver}|${env.primary_tongue}|${env.aad}|${env.ts}|${env.nonce}|${env.payload}`;
}

/**
 * Generate HMAC-SHA256 signature
 */
function generateSignature(input: string, key: Buffer): string {
  const hmac = createHmac('sha256', key);
  hmac.update(input);
  return hmac.digest('base64url');
}

/**
 * Verify HMAC-SHA256 signature
 */
function verifySignature(input: string, signature: string, key: Buffer): boolean {
  const expected = generateSignature(input, key);

  // Constant-time comparison to prevent timing attacks
  if (expected.length !== signature.length) {
    return false;
  }

  let mismatch = 0;
  for (let i = 0; i < expected.length; i++) {
    mismatch |= expected.charCodeAt(i) ^ signature.charCodeAt(i);
  }

  return mismatch === 0;
}

/**
 * Create RWP v2.1 multi-signature envelope
 *
 * @param payload - Payload object (must be JSON-serializable)
 * @param primaryTongue - Primary tongue indicating intent domain
 * @param aad - Additional authenticated data (metadata)
 * @param keyring - HMAC keys for each tongue
 * @param signingTongues - List of tongues to sign with
 * @param options - Optional envelope options
 * @returns Signed envelope
 *
 * @example
 * ```typescript
 * const keyring = {
 *   ko: Buffer.from('...'),
 *   av: Buffer.from('...'),
 *   ru: Buffer.from('...'),
 * };
 *
 * const envelope = signRoundtable(
 *   { action: 'deploy', target: 'production' },
 *   'ko',
 *   'agent-123',
 *   keyring,
 *   ['ko', 'ru', 'um']  // Sign with Control, Policy, Security
 * );
 * ```
 */
export function signRoundtable<T = any>(
  payload: T,
  primaryTongue: TongueID,
  aad: string,
  keyring: Keyring,
  signingTongues: TongueID[],
  options: EnvelopeOptions = {}
): RWP2MultiEnvelope<T> {
  // Validate inputs
  if (!payload) {
    throw new Error('Payload is required');
  }
  if (!primaryTongue) {
    throw new Error('Primary tongue is required');
  }
  if (!signingTongues || signingTongues.length === 0) {
    throw new Error('At least one signing tongue is required');
  }

  // Check that all signing tongues have keys
  for (const tongue of signingTongues) {
    if (!keyring[tongue]) {
      throw new Error(`Missing key for tongue: ${tongue}`);
    }
  }

  // Create envelope (without signatures)
  const env: Omit<RWP2MultiEnvelope<T>, 'sigs'> = {
    ver: '2.1',
    primary_tongue: primaryTongue,
    aad,
    ts: options.timestamp ?? Date.now(),
    nonce: (options.nonce ?? randomBytes(16)).toString('base64url'),
    payload: Buffer.from(JSON.stringify(payload)).toString('base64url'),
    ...(options.kid && { kid: options.kid }),
  };

  // Generate signature input
  const input = getSignatureInput(env);

  // Generate signatures for each tongue
  const sigs: Partial<Record<TongueID, string>> = {};
  for (const tongue of signingTongues) {
    sigs[tongue] = generateSignature(input, keyring[tongue]);
  }

  return { ...env, sigs };
}

/**
 * Verify RWP v2.1 multi-signature envelope
 *
 * @param env - Envelope to verify
 * @param keyring - HMAC keys for each tongue
 * @param options - Verification options
 * @returns Verification result with valid tongues and decoded payload
 *
 * @example
 * ```typescript
 * const result = verifyRoundtable(envelope, keyring, {
 *   replayWindowMs: 300000,  // 5 minutes
 *   policy: 'critical',      // Requires RU + UM + DR
 * });
 *
 * if (result.valid) {
 *   console.log('Valid tongues:', result.validTongues);
 *   console.log('Payload:', result.payload);
 * } else {
 *   console.error('Verification failed:', result.error);
 * }
 * ```
 */
export function verifyRoundtable(
  env: RWP2MultiEnvelope,
  keyring: Keyring,
  options: VerificationOptions = {}
): VerificationResult {
  const {
    replayWindowMs = 300000, // 5 minutes
    clockSkewMs = 60000, // 1 minute
    policy = 'standard',
  } = options;

  try {
    // 1. Check version
    if (env.ver !== '2.1') {
      throw new SignatureError(`Unsupported version: ${env.ver}`);
    }

    // 2. Check timestamp (replay protection)
    const now = Date.now();
    const age = now - env.ts;

    // Reject future timestamps (with clock skew tolerance)
    if (env.ts > now + clockSkewMs) {
      throw new ReplayError(`Timestamp is in the future: ${env.ts} > ${now}`);
    }

    // Reject old timestamps
    if (age > replayWindowMs) {
      throw new ReplayError(`Timestamp too old: ${age}ms > ${replayWindowMs}ms (replay window)`);
    }

    // 3. Check nonce (replay protection)
    if (nonceCache.has(env.nonce)) {
      throw new ReplayError(`Nonce already used: ${env.nonce}`);
    }

    // 4. Verify signatures
    const input = getSignatureInput(env);
    const validTongues: TongueID[] = [];

    for (const [tongue, signature] of Object.entries(env.sigs)) {
      const key = keyring[tongue];
      if (!key) {
        // Skip tongues without keys (don't fail, just don't count as valid)
        continue;
      }

      if (verifySignature(input, signature, key)) {
        validTongues.push(tongue as TongueID);
      }
    }

    // 5. Check if at least one signature is valid
    if (validTongues.length === 0) {
      throw new SignatureError('No valid signatures found');
    }

    // 6. Enforce policy
    enforcePolicy(validTongues, policy);

    // 7. Add nonce to cache (after all checks pass)
    nonceCache.add(env.nonce, env.ts);

    // 8. Decode payload
    const payloadJson = Buffer.from(env.payload, 'base64url').toString('utf-8');
    const payload = JSON.parse(payloadJson);

    return {
      valid: true,
      validTongues,
      payload,
    };
  } catch (error) {
    return {
      valid: false,
      validTongues: [],
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

/**
 * Clear nonce cache (for testing)
 */
export function clearNonceCache(): void {
  nonceCache.clear();
}

/**
 * Get nonce cache size (for monitoring)
 */
export function getNonceCacheSize(): number {
  return nonceCache.size();
}

/**
 * Destroy nonce cache (cleanup)
 */
export function destroyNonceCache(): void {
  nonceCache.destroy();
}
