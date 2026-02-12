/**
 * SCBE SpiralSeal SS1 - Sacred Tongue Cryptographic Encoding
 *
 * Transforms binary ciphertext into Sacred Tongue spell-text,
 * making encrypted data look like fantasy language incantations
 * rather than obvious base64 or hex strings.
 *
 * Features:
 * - Steganographic obfuscation (human-plausible text)
 * - Domain separation (different sections use different tongues)
 * - Collision-free (256 unique tokens per tongue)
 * - Lossless roundtrip encoding/decoding
 *
 * SS1 Format:
 * SS1|kid=<key_id>|aad=<context>|<salt_spell>|<nonce_spell>|<ct_spell>|<tag_spell>
 */
import { TongueSpec, TongueCode, SS1Section } from './sacredTongues.js';
/**
 * Sacred Tongue Tokenizer
 *
 * Encodes/decodes bytes to spell-text tokens using the 16×16 grid.
 * Each byte maps to exactly one token: prefix'suffix
 */
export declare class SacredTongueTokenizer {
    readonly tongue: TongueSpec;
    private readonly byteToToken;
    private readonly tokenToByte;
    constructor(tongueCode?: TongueCode);
    /**
     * Encode a single byte to a token
     */
    encodeByte(b: number): string;
    /**
     * Decode a single token to a byte
     */
    decodeToken(token: string): number;
    /**
     * Encode bytes to space-separated spell-text tokens
     */
    encode(data: Uint8Array | number[]): string;
    /**
     * Encode bytes without tongue prefix (for compact format)
     */
    encodeCompact(data: Uint8Array | number[]): string;
    /**
     * Decode spell-text tokens back to bytes
     */
    decode(spelltext: string): Uint8Array;
    /**
     * Get all 256 tokens for this tongue
     */
    getAllTokens(): string[];
    /**
     * Validate that a token belongs to this tongue
     */
    isValidToken(token: string): boolean;
}
/**
 * Encode bytes using the canonical tongue for a section
 */
export declare function encodeToSpelltext(data: Uint8Array | number[], section: SS1Section): string;
/**
 * Decode spell-text using the canonical tongue for a section
 */
export declare function decodeFromSpelltext(spelltext: string, section: SS1Section): Uint8Array;
/**
 * SS1 Blob structure (parsed)
 */
export interface SS1Blob {
    version: 'SS1';
    kid: string;
    aad: string;
    salt: Uint8Array;
    nonce: Uint8Array;
    ciphertext: Uint8Array;
    tag: Uint8Array;
}
/**
 * Format a complete SS1 spell-text blob
 */
export declare function formatSS1Blob(kid: string, aad: string, salt: Uint8Array, nonce: Uint8Array, ciphertext: Uint8Array, tag: Uint8Array): string;
/**
 * Parse an SS1 spell-text blob
 */
export declare function parseSS1Blob(blob: string): SS1Blob;
/**
 * Generate random bytes
 */
export declare function randomBytes(length: number): Uint8Array;
/**
 * Seal plaintext into an SS1 spell-text blob
 *
 * @param plaintext - Data to encrypt
 * @param masterSecret - 32-byte master secret
 * @param aad - Additional authenticated data (context string)
 * @param kid - Key identifier for rotation
 * @returns SS1 spell-text blob
 */
export declare function seal(plaintext: Uint8Array, masterSecret: Uint8Array, aad: string, kid?: string): Promise<string>;
/**
 * Unseal an SS1 spell-text blob back to plaintext
 *
 * @param blob - SS1 spell-text blob
 * @param masterSecret - 32-byte master secret
 * @param aad - Additional authenticated data (must match sealed AAD)
 * @returns Decrypted plaintext
 */
export declare function unseal(blob: string, masterSecret: Uint8Array, aad: string): Promise<Uint8Array>;
/**
 * SpiralSeal SS1 class for stateful operations
 */
export declare class SpiralSealSS1 {
    private masterSecret;
    private kid;
    constructor(masterSecret: Uint8Array, kid?: string);
    /**
     * Seal plaintext with instance's master secret
     */
    seal(plaintext: Uint8Array, aad: string): Promise<string>;
    /**
     * Unseal blob with instance's master secret
     */
    unseal(blob: string, aad: string): Promise<Uint8Array>;
    /**
     * Rotate to a new key
     */
    rotateKey(newKid: string, newMasterSecret: Uint8Array): void;
    /**
     * Get current key ID
     */
    getKid(): string;
    /**
     * Get status report
     */
    getStatus(): {
        version: string;
        kid: string;
        capabilities: string[];
    };
}
/**
 * Compute Langues Weighting System weights for a tongue
 *
 * Weights follow golden ratio progression: wₗ = φˡ
 */
export declare function computeLWSWeights(tongueCode: TongueCode): number[];
/**
 * Compute combined LWS score for a spell-text string
 */
export declare function computeLWSScore(spelltext: string): number;
//# sourceMappingURL=spiralSeal.d.ts.map