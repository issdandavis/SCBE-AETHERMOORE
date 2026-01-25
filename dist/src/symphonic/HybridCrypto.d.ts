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
import { SymphonicAgent } from './SymphonicAgent.js';
/**
 * Harmonic signature structure
 */
export interface HarmonicSignature {
    /** Z-Base-32 encoded fingerprint */
    fingerprint: string;
    /** Spectral coherence score */
    coherence: number;
    /** Dominant frequency bin */
    dominantFreq: number;
    /** Timestamp (ISO 8601) */
    timestamp: string;
    /** Nonce for replay protection */
    nonce: string;
    /** HMAC of the entire structure */
    hmac: string;
}
/**
 * Signed envelope wrapping data with harmonic signature
 */
export interface SignedEnvelope {
    /** Original intent/data */
    intent: string;
    /** Harmonic signature */
    signature: HarmonicSignature;
    /** Version identifier */
    version: string;
}
/**
 * Verification result
 */
export interface VerificationResult {
    /** Whether verification passed */
    valid: boolean;
    /** Reason for failure (if any) */
    reason?: string;
    /** Coherence score from verification */
    coherence?: number;
    /** Fingerprint similarity score */
    similarity?: number;
}
/**
 * Hybrid Crypto configuration
 */
export interface HybridCryptoConfig {
    /** Fingerprint size (default 32) */
    fingerprintSize: number;
    /** Signature validity duration in ms (default 5 minutes) */
    validityMs: number;
    /** Minimum coherence threshold (default 0.3) */
    minCoherence: number;
    /** Minimum similarity threshold (default 0.85) */
    minSimilarity: number;
}
/**
 * Hybrid Crypto - main Symphonic Cipher interface
 */
export declare class HybridCrypto {
    private readonly agent;
    private readonly config;
    constructor(config?: Partial<HybridCryptoConfig>);
    /**
     * Signs an intent using harmonic signature generation.
     *
     * @param intent The transaction intent or message
     * @param secretKey User's secret key
     * @returns Signed envelope with harmonic signature
     */
    sign(intent: string, secretKey: string): SignedEnvelope;
    /**
     * Verifies a signed envelope.
     *
     * @param envelope Signed envelope to verify
     * @param secretKey Secret key for verification
     * @returns Verification result
     */
    verify(envelope: SignedEnvelope, secretKey: string): VerificationResult;
    /**
     * Creates a compact signature string (for embedding in headers, etc.)
     *
     * @param intent Intent to sign
     * @param secretKey Secret key
     * @returns Compact signature string
     */
    signCompact(intent: string, secretKey: string): string;
    /**
     * Verifies a compact signature string.
     *
     * @param intent Original intent
     * @param compactSig Compact signature string
     * @param secretKey Secret key
     * @returns Verification result
     */
    verifyCompact(intent: string, compactSig: string, secretKey: string): VerificationResult;
    /**
     * Computes similarity between two byte arrays.
     */
    private computeSimilarity;
    /**
     * Generates a secure random key.
     *
     * @param length Key length in bytes (default 32)
     * @returns Z-Base-32 encoded key
     */
    static generateKey(length?: number): string;
    /**
     * Hashes data using SHA-256.
     */
    static hash(data: string | Uint8Array): string;
    /**
     * Gets the underlying Symphonic Agent for advanced operations.
     */
    getAgent(): SymphonicAgent;
}
/**
 * Creates a HybridCrypto instance with default settings.
 */
export declare function createHybridCrypto(config?: Partial<HybridCryptoConfig>): HybridCrypto;
/**
 * Convenience function to sign an intent.
 */
export declare function signIntent(intent: string, secretKey: string): SignedEnvelope;
/**
 * Convenience function to verify a signed envelope.
 */
export declare function verifyIntent(envelope: SignedEnvelope, secretKey: string): VerificationResult;
//# sourceMappingURL=HybridCrypto.d.ts.map