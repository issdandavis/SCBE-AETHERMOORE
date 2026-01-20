"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.getAlphabet = exports.ZBase32 = void 0;
/**
 * Z-Base-32 alphabet optimized for human usability
 * Most common characters map to easiest-to-write symbols
 */
const ALPHABET = 'ybndrfg8ejkmcpqxot1uwisza345h769';
/**
 * Reverse lookup table for decoding
 */
const DECODE_MAP = new Map();
for (let i = 0; i < ALPHABET.length; i++) {
    DECODE_MAP.set(ALPHABET[i], i);
}
/**
 * Z-Base-32 encoding and decoding utility
 */
class ZBase32 {
    /**
     * Encodes a byte array into a Z-Base-32 string.
     *
     * @param data Input bytes
     * @returns Z-Base-32 encoded string
     */
    static encode(data) {
        if (data.length === 0)
            return '';
        let result = '';
        let accumulator = 0;
        let bits = 0;
        for (let i = 0; i < data.length; i++) {
            // Load 8 bits from the buffer into accumulator
            accumulator = (accumulator << 8) | data[i];
            bits += 8;
            // Extract as many 5-bit chunks as possible
            while (bits >= 5) {
                const index = (accumulator >>> (bits - 5)) & 0x1f;
                result += ALPHABET[index];
                bits -= 5;
            }
        }
        // Handle remaining bits (1-4 bits left over)
        if (bits > 0) {
            // Left-shift to align to 5-bit boundary
            const index = (accumulator << (5 - bits)) & 0x1f;
            result += ALPHABET[index];
        }
        return result;
    }
    /**
     * Decodes a Z-Base-32 string back to bytes.
     *
     * @param input Z-Base-32 encoded string
     * @returns Decoded byte array
     * @throws Error if invalid character encountered
     */
    static decode(input) {
        if (input.length === 0)
            return new Uint8Array(0);
        // Normalize to lowercase
        const normalized = input.toLowerCase();
        const result = [];
        let accumulator = 0;
        let bits = 0;
        for (let i = 0; i < normalized.length; i++) {
            const char = normalized[i];
            const value = DECODE_MAP.get(char);
            if (value === undefined) {
                throw new Error(`Invalid Z-Base-32 character: '${char}' at position ${i}`);
            }
            // Load 5 bits into accumulator
            accumulator = (accumulator << 5) | value;
            bits += 5;
            // Extract complete bytes
            while (bits >= 8) {
                const byte = (accumulator >>> (bits - 8)) & 0xff;
                result.push(byte);
                bits -= 8;
            }
        }
        return new Uint8Array(result);
    }
    /**
     * Encodes a string (UTF-8) to Z-Base-32.
     *
     * @param text String to encode
     * @returns Z-Base-32 encoded string
     */
    static encodeString(text) {
        const bytes = new TextEncoder().encode(text);
        return ZBase32.encode(bytes);
    }
    /**
     * Decodes Z-Base-32 to a string (UTF-8).
     *
     * @param encoded Z-Base-32 encoded string
     * @returns Decoded string
     */
    static decodeString(encoded) {
        const bytes = ZBase32.decode(encoded);
        return new TextDecoder().decode(bytes);
    }
    /**
     * Encodes a hexadecimal string to Z-Base-32.
     *
     * @param hex Hexadecimal string
     * @returns Z-Base-32 encoded string
     */
    static encodeHex(hex) {
        const bytes = ZBase32.hexToBytes(hex);
        return ZBase32.encode(bytes);
    }
    /**
     * Decodes Z-Base-32 to a hexadecimal string.
     *
     * @param encoded Z-Base-32 encoded string
     * @returns Hexadecimal string
     */
    static decodeHex(encoded) {
        const bytes = ZBase32.decode(encoded);
        return ZBase32.bytesToHex(bytes);
    }
    /**
     * Validates if a string is valid Z-Base-32.
     *
     * @param input String to validate
     * @returns True if valid Z-Base-32
     */
    static isValid(input) {
        const normalized = input.toLowerCase();
        for (const char of normalized) {
            if (!DECODE_MAP.has(char)) {
                return false;
            }
        }
        return true;
    }
    /**
     * Gets the encoded length for a given input length.
     *
     * @param inputLength Number of bytes to encode
     * @returns Number of characters in encoded output
     */
    static encodedLength(inputLength) {
        // 5 bits per character, 8 bits per byte
        // ceil(inputLength * 8 / 5)
        return Math.ceil((inputLength * 8) / 5);
    }
    /**
     * Gets the decoded length for a given encoded length.
     *
     * @param encodedLength Number of Z-Base-32 characters
     * @returns Number of bytes in decoded output (approximate, may have trailing zeros)
     */
    static decodedLength(encodedLength) {
        // floor(encodedLength * 5 / 8)
        return Math.floor((encodedLength * 5) / 8);
    }
    /**
     * Converts hex string to bytes.
     */
    static hexToBytes(hex) {
        const normalized = hex.replace(/^0x/i, '');
        if (normalized.length % 2 !== 0) {
            throw new Error('Hex string must have even length');
        }
        const bytes = new Uint8Array(normalized.length / 2);
        for (let i = 0; i < normalized.length; i += 2) {
            bytes[i / 2] = parseInt(normalized.substring(i, i + 2), 16);
        }
        return bytes;
    }
    /**
     * Converts bytes to hex string.
     */
    static bytesToHex(bytes) {
        return Array.from(bytes)
            .map((b) => b.toString(16).padStart(2, '0'))
            .join('');
    }
}
exports.ZBase32 = ZBase32;
/**
 * Returns the Z-Base-32 alphabet.
 */
function getAlphabet() {
    return ALPHABET;
}
exports.getAlphabet = getAlphabet;
//# sourceMappingURL=ZBase32.js.map