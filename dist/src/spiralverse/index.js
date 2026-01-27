"use strict";
/**
 * Spiralverse Protocol - RWP v2.1 Multi-Signature Envelopes
 *
 * Provides multi-signature consensus (Roundtable) for AI governance.
 *
 * The Six Sacred Tongues:
 * - KO (Kor'aelin): Control & Orchestration
 * - AV (Avali): I/O & Messaging
 * - RU (Runethic): Policy & Constraints
 * - CA (Cassisivadan): Logic & Computation
 * - UM (Umbroth): Security & Privacy
 * - DR (Draumric): Types & Structures
 *
 * @module spiralverse
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.suggestPolicy = exports.getRequiredTongues = exports.checkPolicy = exports.verifyRoundtable = exports.signRoundtable = exports.clearNonceCache = void 0;
const crypto_1 = require("crypto");
// ============================================================================
// Constants
// ============================================================================
const VERSION = '2.1';
const DEFAULT_MAX_AGE = 300000; // 5 minutes
const DEFAULT_MAX_FUTURE_SKEW = 60000; // 1 minute
/** Policy requirements for each level */
const POLICY_REQUIREMENTS = {
    standard: ['ko'],
    strict: ['ru'],
    critical: ['ru', 'um', 'dr'],
};
/** Action to policy mapping */
const ACTION_POLICIES = {
    read: 'standard',
    write: 'standard',
    deploy: 'strict',
    delete: 'strict',
    admin: 'critical',
    security: 'critical',
};
// ============================================================================
// Nonce Cache (Replay Protection)
// ============================================================================
const nonceCache = new Set();
const nonceCacheTimestamps = new Map();
/**
 * Clear the nonce cache (for testing)
 */
function clearNonceCache() {
    nonceCache.clear();
    nonceCacheTimestamps.clear();
}
exports.clearNonceCache = clearNonceCache;
/**
 * Check if nonce has been used and add to cache
 */
function checkAndAddNonce(nonce, timestamp) {
    // Clean up old nonces (older than 10 minutes)
    const now = Date.now();
    for (const [n, ts] of nonceCacheTimestamps) {
        if (now - ts > 600000) {
            nonceCache.delete(n);
            nonceCacheTimestamps.delete(n);
        }
    }
    if (nonceCache.has(nonce)) {
        return false; // Already used
    }
    nonceCache.add(nonce);
    nonceCacheTimestamps.set(nonce, timestamp);
    return true;
}
// ============================================================================
// Utility Functions
// ============================================================================
function toBase64Url(buf) {
    return buf.toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}
function fromBase64Url(s) {
    let str = s.replace(/-/g, '+').replace(/_/g, '/');
    while (str.length % 4)
        str += '=';
    return Buffer.from(str, 'base64');
}
/**
 * Create HMAC-SHA256 signature
 */
function createSignature(key, data) {
    const hmac = (0, crypto_1.createHmac)('sha256', key);
    hmac.update(data);
    return toBase64Url(hmac.digest());
}
/**
 * Verify HMAC-SHA256 signature
 */
function verifySignature(key, data, signature) {
    const expected = createSignature(key, data);
    // Constant-time comparison
    if (expected.length !== signature.length)
        return false;
    let result = 0;
    for (let i = 0; i < expected.length; i++) {
        result |= expected.charCodeAt(i) ^ signature.charCodeAt(i);
    }
    return result === 0;
}
/**
 * Create signature data buffer
 */
function createSignatureData(version, primaryTongue, aad, payload, nonce, ts, tongue) {
    const data = `${version}.${primaryTongue}.${tongue}.${aad}.${payload}.${nonce}.${ts}`;
    return Buffer.from(data, 'utf8');
}
// ============================================================================
// Core Functions
// ============================================================================
/**
 * Sign a payload with multiple Sacred Tongues (Roundtable consensus)
 *
 * @param payload - The payload to sign
 * @param primaryTongue - The initiating tongue
 * @param aad - Additional authenticated data
 * @param keyring - Keys for signing
 * @param signingTongues - Which tongues should sign
 * @param options - Optional signing options
 * @returns The signed RWP envelope
 */
function signRoundtable(payload, primaryTongue, aad, keyring, signingTongues, options = {}) {
    // Validate inputs
    if (payload === null || payload === undefined) {
        throw new Error('Payload is required');
    }
    if (!primaryTongue) {
        throw new Error('Primary tongue is required');
    }
    if (!signingTongues || signingTongues.length === 0) {
        throw new Error('At least one signing tongue is required');
    }
    // Check all required keys are present
    for (const tongue of signingTongues) {
        if (!keyring[tongue]) {
            throw new Error(`Missing key for tongue: ${tongue}`);
        }
    }
    // Encode payload
    const payloadJson = JSON.stringify(payload);
    const payloadEncoded = toBase64Url(Buffer.from(payloadJson, 'utf8'));
    // Generate nonce
    const nonce = options.nonce ?? (0, crypto_1.randomBytes)(16);
    const nonceEncoded = toBase64Url(nonce);
    // Timestamp
    const ts = options.timestamp ?? Date.now();
    // Create signatures for each tongue
    const sigs = {};
    for (const tongue of signingTongues) {
        const key = keyring[tongue];
        const sigData = createSignatureData(VERSION, primaryTongue, aad, payloadEncoded, nonceEncoded, ts, tongue);
        sigs[tongue] = createSignature(key, sigData);
    }
    // Build envelope
    const envelope = {
        ver: '2.1',
        primary_tongue: primaryTongue,
        aad,
        payload: payloadEncoded,
        sigs,
        nonce: nonceEncoded,
        ts,
    };
    if (options.kid) {
        envelope.kid = options.kid;
    }
    return envelope;
}
exports.signRoundtable = signRoundtable;
/**
 * Verify an RWP envelope
 *
 * @param envelope - The envelope to verify
 * @param keyring - Keys for verification
 * @param options - Verification options
 * @returns Verification result
 */
function verifyRoundtable(envelope, keyring, options = {}) {
    const maxAge = options.maxAge ?? DEFAULT_MAX_AGE;
    const maxFutureSkew = options.maxFutureSkew ?? DEFAULT_MAX_FUTURE_SKEW;
    // Check version
    if (envelope.ver !== '2.1') {
        return {
            valid: false,
            validTongues: [],
            error: `Unsupported version: ${envelope.ver}`,
        };
    }
    // Check timestamp
    const now = Date.now();
    const age = now - envelope.ts;
    if (age > maxAge) {
        return {
            valid: false,
            validTongues: [],
            error: 'Timestamp too old',
        };
    }
    if (age < -maxFutureSkew) {
        return {
            valid: false,
            validTongues: [],
            error: 'Timestamp is in the future',
        };
    }
    // Check nonce replay
    if (!checkAndAddNonce(envelope.nonce, envelope.ts)) {
        return {
            valid: false,
            validTongues: [],
            error: 'Nonce already used (replay detected)',
        };
    }
    // Verify signatures
    const validTongues = [];
    const allTongues = Object.keys(envelope.sigs);
    for (const tongue of allTongues) {
        const key = keyring[tongue];
        if (!key)
            continue; // Skip if key not in keyring
        const signature = envelope.sigs[tongue];
        if (!signature)
            continue;
        const sigData = createSignatureData(envelope.ver, envelope.primary_tongue, envelope.aad, envelope.payload, envelope.nonce, envelope.ts, tongue);
        if (verifySignature(key, sigData, signature)) {
            validTongues.push(tongue);
        }
    }
    if (validTongues.length === 0) {
        return {
            valid: false,
            validTongues: [],
            error: 'No valid signatures found',
        };
    }
    // Check policy if specified
    if (options.policy) {
        const required = POLICY_REQUIREMENTS[options.policy];
        const hasAllRequired = required.every((t) => validTongues.includes(t));
        if (!hasAllRequired) {
            const missing = required.filter((t) => !validTongues.includes(t));
            return {
                valid: false,
                validTongues,
                error: `Policy violation: missing required tongue(s): ${missing.join(', ')}`,
            };
        }
    }
    // Decode payload
    let payload;
    try {
        const payloadBuffer = fromBase64Url(envelope.payload);
        payload = JSON.parse(payloadBuffer.toString('utf8'));
    }
    catch {
        return {
            valid: false,
            validTongues,
            error: 'Failed to decode payload',
        };
    }
    return {
        valid: true,
        validTongues,
        payload,
    };
}
exports.verifyRoundtable = verifyRoundtable;
// ============================================================================
// Policy Helpers
// ============================================================================
/**
 * Check if a set of tongues satisfies a policy
 *
 * @param tongues - The tongues that have signed
 * @param policy - The policy level to check
 * @returns Whether the policy is satisfied
 */
function checkPolicy(tongues, policy) {
    const required = POLICY_REQUIREMENTS[policy];
    return required.every((t) => tongues.includes(t));
}
exports.checkPolicy = checkPolicy;
/**
 * Get the required tongues for a policy level
 *
 * @param policy - The policy level
 * @returns Array of required tongue IDs
 */
function getRequiredTongues(policy) {
    return [...POLICY_REQUIREMENTS[policy]];
}
exports.getRequiredTongues = getRequiredTongues;
/**
 * Suggest an appropriate policy level for an action
 *
 * @param action - The action being performed
 * @returns Suggested policy level
 */
function suggestPolicy(action) {
    const normalizedAction = action.toLowerCase();
    return ACTION_POLICIES[normalizedAction] ?? 'standard';
}
exports.suggestPolicy = suggestPolicy;
//# sourceMappingURL=index.js.map