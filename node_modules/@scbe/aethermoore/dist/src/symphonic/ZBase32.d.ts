/**
 * SCBE Symphonic Cipher - Z-Base-32 Encoding
 *
 * Human-friendly Base32 encoding developed by Phil Zimmermann.
 * Optimized for:
 * - Reduced transcription errors (no 0, 1, l, v, 2)
 * - Easy verbal communication
 * - Case-insensitive
 *
 * Alphabet: ybndrfg8ejkmcpqxot1uwisza345h769
 *
 * @module symphonic/ZBase32
 */
/**
 * Z-Base-32 encoding and decoding utility
 */
export declare class ZBase32 {
    /**
     * Encodes a byte array into a Z-Base-32 string.
     *
     * @param data Input bytes
     * @returns Z-Base-32 encoded string
     */
    static encode(data: Uint8Array): string;
    /**
     * Decodes a Z-Base-32 string back to bytes.
     *
     * @param input Z-Base-32 encoded string
     * @returns Decoded byte array
     * @throws Error if invalid character encountered
     */
    static decode(input: string): Uint8Array;
    /**
     * Encodes a string (UTF-8) to Z-Base-32.
     *
     * @param text String to encode
     * @returns Z-Base-32 encoded string
     */
    static encodeString(text: string): string;
    /**
     * Decodes Z-Base-32 to a string (UTF-8).
     *
     * @param encoded Z-Base-32 encoded string
     * @returns Decoded string
     */
    static decodeString(encoded: string): string;
    /**
     * Encodes a hexadecimal string to Z-Base-32.
     *
     * @param hex Hexadecimal string
     * @returns Z-Base-32 encoded string
     */
    static encodeHex(hex: string): string;
    /**
     * Decodes Z-Base-32 to a hexadecimal string.
     *
     * @param encoded Z-Base-32 encoded string
     * @returns Hexadecimal string
     */
    static decodeHex(encoded: string): string;
    /**
     * Validates if a string is valid Z-Base-32.
     *
     * @param input String to validate
     * @returns True if valid Z-Base-32
     */
    static isValid(input: string): boolean;
    /**
     * Gets the encoded length for a given input length.
     *
     * @param inputLength Number of bytes to encode
     * @returns Number of characters in encoded output
     */
    static encodedLength(inputLength: number): number;
    /**
     * Gets the decoded length for a given encoded length.
     *
     * @param encodedLength Number of Z-Base-32 characters
     * @returns Number of bytes in decoded output (approximate, may have trailing zeros)
     */
    static decodedLength(encodedLength: number): number;
    /**
     * Converts hex string to bytes.
     */
    private static hexToBytes;
    /**
     * Converts bytes to hex string.
     */
    private static bytesToHex;
}
/**
 * Returns the Z-Base-32 alphabet.
 */
export declare function getAlphabet(): string;
//# sourceMappingURL=ZBase32.d.ts.map