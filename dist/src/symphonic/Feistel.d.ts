/**
 * SCBE Symphonic Cipher - Feistel Network
 *
 * Implementation of a Balanced Feistel Network for "Intent Modulation".
 * Scrambles input data into a pseudo-random signal while maintaining
 * reversibility (decryptability).
 *
 * The Feistel structure allows using a non-invertible round function (HMAC)
 * while still enabling full decryption. This is used to create high-entropy
 * signals from structured data (like JSON) before FFT analysis.
 *
 * @module symphonic/Feistel
 */
/**
 * Feistel Network configuration
 */
export interface FeistelConfig {
    /** Number of rounds (default 6) */
    rounds: number;
    /** Hash algorithm for round function (default 'sha256') */
    hashAlgorithm: 'sha256' | 'sha512' | 'sha384';
}
/**
 * Balanced Feistel Network implementation
 */
export declare class Feistel {
    private readonly config;
    /**
     * Creates a new Feistel cipher.
     *
     * @param config Configuration options
     */
    constructor(config?: Partial<FeistelConfig>);
    /**
     * The Round Function F.
     * F(R, K) = HMAC-SHA256(Key, R)
     *
     * The output is truncated or extended to match the length of the block half.
     *
     * @param right Right half of the block
     * @param roundKey Round-specific key
     * @returns Transformed output matching right's length
     */
    private roundFunction;
    /**
     * XORs two buffers together.
     *
     * @param a First buffer
     * @param b Second buffer
     * @returns XOR result
     */
    private xorBuffers;
    /**
     * Derives round keys from the master key.
     *
     * @param masterKey Master key buffer
     * @returns Array of round keys
     */
    private deriveRoundKeys;
    /**
     * Encrypts (modulates) the data buffer.
     *
     * @param data Raw input data
     * @param key Master key (string or buffer)
     * @returns Encrypted/modulated data
     */
    encrypt(data: Uint8Array, key: string | Uint8Array): Uint8Array;
    /**
     * Decrypts (demodulates) the data buffer.
     *
     * @param data Encrypted data
     * @param key Master key (string or buffer)
     * @returns Decrypted data
     */
    decrypt(data: Uint8Array, key: string | Uint8Array): Uint8Array;
    /**
     * Encrypts a string and returns the result as a Uint8Array.
     *
     * @param plaintext String to encrypt
     * @param key Encryption key
     * @returns Encrypted bytes
     */
    encryptString(plaintext: string, key: string): Uint8Array;
    /**
     * Decrypts bytes and returns the result as a string.
     *
     * @param ciphertext Encrypted bytes
     * @param key Decryption key
     * @returns Decrypted string
     */
    decryptString(ciphertext: Uint8Array, key: string): string;
    /**
     * Generates a random key of specified length.
     *
     * @param length Key length in bytes (default 32)
     * @returns Random key buffer
     */
    static generateKey(length?: number): Uint8Array;
    /**
     * Verifies that encryption/decryption round-trips correctly.
     *
     * @param data Test data
     * @param key Test key
     * @returns True if round-trip succeeds
     */
    verify(data: Uint8Array, key: string | Uint8Array): boolean;
}
/**
 * Creates a Feistel cipher with default settings.
 */
export declare function createFeistel(config?: Partial<FeistelConfig>): Feistel;
//# sourceMappingURL=Feistel.d.ts.map