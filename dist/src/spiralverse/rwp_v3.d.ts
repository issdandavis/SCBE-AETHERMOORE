/**
 * RWP v3.0 Protocol - TypeScript Implementation
 * ==============================================
 *
 * Post-quantum hybrid encryption with Sacred Tongue encoding.
 * Matches Python implementation in src/crypto/rwp_v3.py
 *
 * Security Stack:
 * 1. Argon2id KDF (RFC 9106) for password → key derivation
 * 2. ChaCha20-Poly1305 AEAD (Node.js native - 12-byte nonce)
 * 3. Sacred Tongue encoding for semantic binding
 *
 * Note: Uses ChaCha20-Poly1305 (12-byte nonce) instead of XChaCha20
 * for Node.js compatibility without external dependencies.
 *
 * @module spiralverse/rwp_v3
 * @version 3.0.0
 * @since 2026-02-01
 */
/**
 * Argon2id parameters for key derivation
 * Note: Uses PBKDF2 as fallback if argon2 not available
 */
export declare const ARGON2_PARAMS: {
    timeCost: number;
    memoryCost: number;
    parallelism: number;
    hashLen: number;
    saltLen: number;
};
/**
 * Sacred Tongue tokenizer for byte ↔ token encoding.
 * Bijective mapping: 256 bytes → 256 unique tokens per tongue.
 */
export declare class SacredTongueTokenizer {
    private byteToToken;
    private tokenToByte;
    constructor();
    private buildTables;
    private validateSecurityProperties;
    /**
     * Encode bytes to Sacred Tongue tokens
     */
    encodeBytes(tongueCode: string, data: Buffer): string[];
    /**
     * Decode Sacred Tongue tokens to bytes
     */
    decodeTokens(tongueCode: string, tokens: string[]): Buffer;
    /**
     * Encode RWP section using canonical tongue
     */
    encodeSection(section: string, data: Buffer): string[];
    /**
     * Decode RWP section from tokens
     */
    decodeSection(section: string, tokens: string[]): Buffer;
}
export declare const TOKENIZER: SacredTongueTokenizer;
/**
 * RWP v3.0 envelope with Sacred Tongue encoded fields
 */
export interface RWPv3Envelope {
    /** Protocol version */
    version: string[];
    /** Additional Authenticated Data (Avali tokens) */
    aad: string[];
    /** Argon2id salt (Runethic tokens) */
    salt: string[];
    /** ChaCha20 nonce (Kor'aelin tokens) */
    nonce: string[];
    /** Ciphertext (Cassisivadan tokens) */
    ct: string[];
    /** Poly1305 auth tag (Draumric tokens) */
    tag: string[];
    /** ML-KEM ciphertext (optional, Umbroth tokens) */
    ml_kem_ct?: string[];
    /** ML-DSA signature (optional, Draumric tokens) */
    ml_dsa_sig?: string[];
}
/**
 * RWP v3.0 Protocol with AEAD encryption and Sacred Tongue encoding.
 *
 * Security stack:
 * 1. PBKDF2-SHA256 KDF (fallback for Argon2id)
 * 2. ChaCha20-Poly1305 AEAD (Node.js native)
 * 3. Sacred Tongue encoding for all envelope fields
 */
export declare class RWPv3Protocol {
    private tokenizer;
    enablePqc: boolean;
    constructor(options?: {
        enablePqc?: boolean;
    });
    /**
     * Derive 256-bit key using PBKDF2 (Argon2id fallback)
     */
    private deriveKey;
    /**
     * Encrypt plaintext with RWP v3.0 protocol
     */
    encrypt(password: Buffer, plaintext: Buffer, aad?: Buffer): RWPv3Envelope;
    /**
     * Decrypt RWP v3.0 envelope
     */
    decrypt(password: Buffer, envelope: RWPv3Envelope): Buffer;
}
/**
 * High-level API: Encrypt a message with RWP v3.0
 */
export declare function rwpEncryptMessage(password: string, message: string, metadata?: Record<string, unknown>): RWPv3Envelope;
/**
 * High-level API: Decrypt RWP v3.0 envelope
 */
export declare function rwpDecryptMessage(password: string, envelope: RWPv3Envelope): string;
/**
 * Serialize envelope to JSON-compatible object
 */
export declare function envelopeToDict(envelope: RWPv3Envelope): Record<string, unknown>;
/**
 * Deserialize envelope from JSON object
 */
export declare function envelopeFromDict(dict: Record<string, unknown>): RWPv3Envelope;
//# sourceMappingURL=rwp_v3.d.ts.map