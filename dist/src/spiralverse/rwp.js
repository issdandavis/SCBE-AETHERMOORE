"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.destroyNonceCache = exports.getNonceCacheSize = exports.clearNonceCache = exports.verifyRoundtable = exports.signRoundtable = void 0;
const crypto_1 = require("crypto");
const policy_1 = require("./policy");
const types_1 = require("./types");
/**
 * Nonce cache for replay protection
 * LRU cache with automatic expiration
 */
class NonceCache {
    cache = new Map();
    maxSize;
    cleanupInterval;
    constructor(maxSize = 10000) {
        this.maxSize = maxSize;
        // Cleanup expired entries every minute
        this.cleanupInterval = setInterval(() => this.cleanup(), 60000);
    }
    /**
     * Check if nonce exists in cache
     */
    has(nonce) {
        return this.cache.has(nonce);
    }
    /**
     * Add nonce to cache
     */
    add(nonce, timestamp) {
        // LRU eviction if cache is full
        if (this.cache.size >= this.maxSize) {
            const firstKey = this.cache.keys().next().value;
            this.cache.delete(firstKey);
        }
        this.cache.set(nonce, { nonce, timestamp });
    }
    /**
     * Remove expired entries
     */
    cleanup() {
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
    clear() {
        this.cache.clear();
    }
    /**
     * Get cache size
     */
    size() {
        return this.cache.size;
    }
    /**
     * Destroy cache and cleanup interval
     */
    destroy() {
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
function getSignatureInput(env) {
    return `${env.ver}|${env.primary_tongue}|${env.aad}|${env.ts}|${env.nonce}|${env.payload}`;
}
/**
 * Generate HMAC-SHA256 signature
 */
function generateSignature(input, key) {
    const hmac = (0, crypto_1.createHmac)('sha256', key);
    hmac.update(input);
    return hmac.digest('base64url');
}
/**
 * Verify HMAC-SHA256 signature
 */
function verifySignature(input, signature, key) {
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
function signRoundtable(payload, primaryTongue, aad, keyring, signingTongues, options = {}) {
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
    const env = {
        ver: '2.1',
        primary_tongue: primaryTongue,
        aad,
        ts: options.timestamp ?? Date.now(),
        nonce: (options.nonce ?? (0, crypto_1.randomBytes)(16)).toString('base64url'),
        payload: Buffer.from(JSON.stringify(payload)).toString('base64url'),
        ...(options.kid && { kid: options.kid }),
    };
    // Generate signature input
    const input = getSignatureInput(env);
    // Generate signatures for each tongue
    const sigs = {};
    for (const tongue of signingTongues) {
        sigs[tongue] = generateSignature(input, keyring[tongue]);
    }
    return { ...env, sigs };
}
exports.signRoundtable = signRoundtable;
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
function verifyRoundtable(env, keyring, options = {}) {
    const { replayWindowMs = 300000, // 5 minutes
    clockSkewMs = 60000, // 1 minute
    policy = 'standard', } = options;
    try {
        // 1. Check version
        if (env.ver !== '2.1') {
            throw new types_1.SignatureError(`Unsupported version: ${env.ver}`);
        }
        // 2. Check timestamp (replay protection)
        const now = Date.now();
        const age = now - env.ts;
        // Reject future timestamps (with clock skew tolerance)
        if (env.ts > now + clockSkewMs) {
            throw new types_1.ReplayError(`Timestamp is in the future: ${env.ts} > ${now}`);
        }
        // Reject old timestamps
        if (age > replayWindowMs) {
            throw new types_1.ReplayError(`Timestamp too old: ${age}ms > ${replayWindowMs}ms (replay window)`);
        }
        // 3. Check nonce (replay protection)
        if (nonceCache.has(env.nonce)) {
            throw new types_1.ReplayError(`Nonce already used: ${env.nonce}`);
        }
        // 4. Verify signatures
        const input = getSignatureInput(env);
        const validTongues = [];
        for (const [tongue, signature] of Object.entries(env.sigs)) {
            const key = keyring[tongue];
            if (!key) {
                // Skip tongues without keys (don't fail, just don't count as valid)
                continue;
            }
            if (verifySignature(input, signature, key)) {
                validTongues.push(tongue);
            }
        }
        // 5. Check if at least one signature is valid
        if (validTongues.length === 0) {
            throw new types_1.SignatureError('No valid signatures found');
        }
        // 6. Enforce policy
        (0, policy_1.enforcePolicy)(validTongues, policy);
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
    }
    catch (error) {
        return {
            valid: false,
            validTongues: [],
            error: error instanceof Error ? error.message : String(error),
        };
    }
}
exports.verifyRoundtable = verifyRoundtable;
/**
 * Clear nonce cache (for testing)
 */
function clearNonceCache() {
    nonceCache.clear();
}
exports.clearNonceCache = clearNonceCache;
/**
 * Get nonce cache size (for monitoring)
 */
function getNonceCacheSize() {
    return nonceCache.size();
}
exports.getNonceCacheSize = getNonceCacheSize;
/**
 * Destroy nonce cache (cleanup)
 */
function destroyNonceCache() {
    nonceCache.destroy();
}
exports.destroyNonceCache = destroyNonceCache;
//# sourceMappingURL=rwp.js.map