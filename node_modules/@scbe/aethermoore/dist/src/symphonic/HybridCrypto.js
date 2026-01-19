"use strict";
/**
 * SCBE Symphonic Cipher - Hybrid Crypto
 *
 * Combines all Symphonic Cipher components into a unified cryptographic
 * signing and verification system. This is the main entry point for
 * the Symphonic Cipher functionality.
 *
 * Pipeline:
 * 1. Intent → Feistel Modulation → Pseudo-random signal
 * 2. Signal → FFT → Frequency spectrum
 * 3. Spectrum → Fingerprint extraction → Harmonic signature
 * 4. Signature → Z-Base-32 encoding → Human-readable output
 *
 * @module symphonic/HybridCrypto
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.verifyIntent = exports.signIntent = exports.createHybridCrypto = exports.HybridCrypto = void 0;
const crypto_1 = require("crypto");
const SymphonicAgent_js_1 = require("./SymphonicAgent.js");
const ZBase32_js_1 = require("./ZBase32.js");
const DEFAULT_CONFIG = {
    fingerprintSize: 32,
    validityMs: 5 * 60 * 1000, // 5 minutes
    minCoherence: 0.1,
    minSimilarity: 0.7,
};
/**
 * Hybrid Crypto - main Symphonic Cipher interface
 */
class HybridCrypto {
    agent;
    config;
    constructor(config = {}) {
        this.config = { ...DEFAULT_CONFIG, ...config };
        this.agent = new SymphonicAgent_js_1.SymphonicAgent({
            fingerprintSize: this.config.fingerprintSize,
        });
    }
    /**
     * Signs an intent using harmonic signature generation.
     *
     * @param intent The transaction intent or message
     * @param secretKey User's secret key
     * @returns Signed envelope with harmonic signature
     */
    sign(intent, secretKey) {
        // Generate synthesis result
        const synthesis = this.agent.synthesizeHarmonics(intent, secretKey);
        // Quantize and encode fingerprint
        const quantized = this.agent.quantizeFingerprint(synthesis.fingerprint);
        const encodedFingerprint = ZBase32_js_1.ZBase32.encode(quantized);
        // Generate nonce
        const nonce = ZBase32_js_1.ZBase32.encode(new Uint8Array((0, crypto_1.randomBytes)(16)));
        // Create timestamp
        const timestamp = new Date().toISOString();
        // Compute HMAC over all signature components
        // Use rounded coherence (3 decimal places) to match compact format
        const roundedCoherence = Math.round(synthesis.coherence * 1000) / 1000;
        const hmacData = [
            encodedFingerprint,
            roundedCoherence.toFixed(3),
            synthesis.dominantFrequency.toString(),
            timestamp,
            nonce,
            intent,
        ].join('|');
        const hmac = (0, crypto_1.createHmac)('sha256', secretKey)
            .update(hmacData)
            .digest('hex')
            .substring(0, 32);
        const signature = {
            fingerprint: encodedFingerprint,
            coherence: synthesis.coherence,
            dominantFreq: synthesis.dominantFrequency,
            timestamp,
            nonce,
            hmac,
        };
        return {
            intent,
            signature,
            version: '1.0.0',
        };
    }
    /**
     * Verifies a signed envelope.
     *
     * @param envelope Signed envelope to verify
     * @param secretKey Secret key for verification
     * @returns Verification result
     */
    verify(envelope, secretKey) {
        const { intent, signature } = envelope;
        // 1. Check timestamp validity
        const sigTime = new Date(signature.timestamp).getTime();
        const now = Date.now();
        if (now - sigTime > this.config.validityMs) {
            return { valid: false, reason: 'Signature expired' };
        }
        if (sigTime > now + 60000) {
            // Allow 1 minute clock skew
            return { valid: false, reason: 'Signature timestamp in future' };
        }
        // 2. Verify HMAC
        // Use rounded coherence (3 decimal places) to match compact format
        const roundedCoherence = Math.round(signature.coherence * 1000) / 1000;
        const hmacData = [
            signature.fingerprint,
            roundedCoherence.toFixed(3),
            signature.dominantFreq.toString(),
            signature.timestamp,
            signature.nonce,
            intent,
        ].join('|');
        const expectedHmac = (0, crypto_1.createHmac)('sha256', secretKey)
            .update(hmacData)
            .digest('hex')
            .substring(0, 32);
        if (signature.hmac !== expectedHmac) {
            return { valid: false, reason: 'HMAC verification failed' };
        }
        // 3. Re-synthesize and compare fingerprints
        const synthesis = this.agent.synthesizeHarmonics(intent, secretKey);
        const quantized = this.agent.quantizeFingerprint(synthesis.fingerprint);
        // 4. Check coherence threshold
        if (synthesis.coherence < this.config.minCoherence) {
            return {
                valid: false,
                reason: 'Coherence below threshold',
                coherence: synthesis.coherence,
            };
        }
        // 5. Compare fingerprints
        const originalFp = ZBase32_js_1.ZBase32.decode(signature.fingerprint);
        const similarity = this.computeSimilarity(quantized, originalFp);
        if (similarity < this.config.minSimilarity) {
            return {
                valid: false,
                reason: 'Fingerprint mismatch',
                similarity,
                coherence: synthesis.coherence,
            };
        }
        return {
            valid: true,
            coherence: synthesis.coherence,
            similarity,
        };
    }
    /**
     * Creates a compact signature string (for embedding in headers, etc.)
     *
     * @param intent Intent to sign
     * @param secretKey Secret key
     * @returns Compact signature string
     */
    signCompact(intent, secretKey) {
        const envelope = this.sign(intent, secretKey);
        const sig = envelope.signature;
        // Format: fingerprint~coherence~dominantFreq~timestamp~nonce~hmac
        // Using ~ as separator since it's not in Z-Base-32 alphabet
        return [
            sig.fingerprint,
            Math.round(sig.coherence * 1000).toString(36),
            sig.dominantFreq.toString(36),
            Buffer.from(sig.timestamp).toString('base64url'),
            sig.nonce,
            sig.hmac,
        ].join('~');
    }
    /**
     * Verifies a compact signature string.
     *
     * @param intent Original intent
     * @param compactSig Compact signature string
     * @param secretKey Secret key
     * @returns Verification result
     */
    verifyCompact(intent, compactSig, secretKey) {
        try {
            const parts = compactSig.split('~');
            if (parts.length !== 6) {
                return { valid: false, reason: 'Invalid compact signature format' };
            }
            const [fingerprint, coherenceStr, domFreqStr, timestampB64, nonce, hmac] = parts;
            const signature = {
                fingerprint,
                coherence: parseInt(coherenceStr, 36) / 1000,
                dominantFreq: parseInt(domFreqStr, 36),
                timestamp: Buffer.from(timestampB64, 'base64url').toString(),
                nonce,
                hmac,
            };
            const envelope = {
                intent,
                signature,
                version: '1.0.0',
            };
            return this.verify(envelope, secretKey);
        }
        catch (e) {
            return { valid: false, reason: `Parse error: ${e}` };
        }
    }
    /**
     * Computes similarity between two byte arrays.
     */
    computeSimilarity(a, b) {
        const minLen = Math.min(a.length, b.length);
        if (minLen === 0)
            return 0;
        let dotProduct = 0;
        let normA = 0;
        let normB = 0;
        for (let i = 0; i < minLen; i++) {
            dotProduct += a[i] * b[i];
            normA += a[i] * a[i];
            normB += b[i] * b[i];
        }
        const denom = Math.sqrt(normA) * Math.sqrt(normB);
        return denom > 0 ? dotProduct / denom : 0;
    }
    /**
     * Generates a secure random key.
     *
     * @param length Key length in bytes (default 32)
     * @returns Z-Base-32 encoded key
     */
    static generateKey(length = 32) {
        return ZBase32_js_1.ZBase32.encode(new Uint8Array((0, crypto_1.randomBytes)(length)));
    }
    /**
     * Hashes data using SHA-256.
     */
    static hash(data) {
        const input = typeof data === 'string' ? data : Buffer.from(data);
        return (0, crypto_1.createHash)('sha256').update(input).digest('hex');
    }
    /**
     * Gets the underlying Symphonic Agent for advanced operations.
     */
    getAgent() {
        return this.agent;
    }
}
exports.HybridCrypto = HybridCrypto;
/**
 * Creates a HybridCrypto instance with default settings.
 */
function createHybridCrypto(config) {
    return new HybridCrypto(config);
}
exports.createHybridCrypto = createHybridCrypto;
/**
 * Convenience function to sign an intent.
 */
function signIntent(intent, secretKey) {
    return new HybridCrypto().sign(intent, secretKey);
}
exports.signIntent = signIntent;
/**
 * Convenience function to verify a signed envelope.
 */
function verifyIntent(envelope, secretKey) {
    return new HybridCrypto().verify(envelope, secretKey);
}
exports.verifyIntent = verifyIntent;
//# sourceMappingURL=HybridCrypto.js.map