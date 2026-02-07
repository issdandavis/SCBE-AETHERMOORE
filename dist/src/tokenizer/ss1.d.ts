/**
 * SS1 (Spiralverse System 1) Tokenizer Protocol
 *
 * A bijective cryptographic encoding system that maps raw bytes to
 * phonetically-engineered "Spell-Text" using the Six Sacred Tongues.
 *
 * Properties:
 * - Perfect bijectivity (every byte maps to exactly one token)
 * - Semantic domain separation (different data types use different "languages")
 * - Phonetic engineering (tokens sound like their purpose)
 * - O(1) encode/decode (no neural networks)
 *
 * @module tokenizer/ss1
 * @version 1.0.0
 */
/** Sacred Tongue identifier */
export type TongueCode = 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';
/** Tongue metadata */
export interface TongueInfo {
    code: TongueCode;
    name: string;
    domain: string;
    phaseOffset: number;
    weight: number;
    frequency: number;
}
/** Cross-tokenization attestation */
export interface XlateAttestation {
    fromTongue: TongueCode;
    toTongue: TongueCode;
    phaseDelta: number;
    weightRatio: number;
    timestamp: number;
    signature: string;
}
/** Blend pattern for stripe mode */
export interface BlendPattern {
    tongue: TongueCode;
    count: number;
}
/** Tongue configurations */
export declare const TONGUES: Record<TongueCode, TongueInfo>;
/** Array of tongue codes for iteration */
export declare const TONGUE_CODES: TongueCode[];
/**
 * Encode a single byte to a token
 *
 * Formula: Token = Prefix[High_Nibble] + "'" + Suffix[Low_Nibble]
 *
 * @param byte - The byte value (0-255)
 * @param tongue - The tongue to use for encoding
 * @returns The encoded token (e.g., "vel'an")
 */
export declare function encodeByte(byte: number, tongue: TongueCode): string;
/**
 * Decode a token to a byte
 *
 * @param token - The token to decode (e.g., "vel'an")
 * @param tongue - The tongue used for encoding
 * @returns The decoded byte value (0-255)
 */
export declare function decodeByte(token: string, tongue: TongueCode): number;
/**
 * Encode a buffer to spell-text
 *
 * @param data - The data to encode
 * @param tongue - The tongue to use
 * @param includePrefix - Whether to include tongue prefix (e.g., "ko:")
 * @returns Space-separated tokens
 */
export declare function encode(data: Buffer | Uint8Array, tongue: TongueCode, includePrefix?: boolean): string;
/**
 * Decode spell-text to a buffer
 *
 * @param spellText - The spell-text to decode
 * @param tongue - The tongue used (optional if prefix included)
 * @returns The decoded buffer
 */
export declare function decode(spellText: string, tongue?: TongueCode): Buffer;
/**
 * Translate spell-text from one tongue to another
 *
 * The binary payload is preserved; only the encoding changes.
 *
 * @param spellText - The source spell-text
 * @param fromTongue - The source tongue
 * @param toTongue - The target tongue
 * @param secretKey - Key for attestation signature (optional)
 * @returns Translated spell-text and attestation
 */
export declare function xlate(spellText: string, fromTongue: TongueCode, toTongue: TongueCode, secretKey?: Buffer): {
    translated: string;
    attestation: XlateAttestation;
};
/**
 * Verify an xlate attestation
 */
export declare function verifyXlateAttestation(attestation: XlateAttestation, secretKey: Buffer): boolean;
/**
 * Encode data using a blending pattern
 *
 * @param data - The data to encode
 * @param pattern - Array of {tongue, count} specifying the stripe pattern
 * @returns Blended spell-text
 */
export declare function blend(data: Buffer | Uint8Array, pattern: BlendPattern[]): string;
/**
 * Decode blended spell-text
 *
 * @param spellText - The blended spell-text (must include tongue prefixes)
 * @returns The decoded buffer
 */
export declare function unblend(spellText: string): Buffer;
/** RWP Envelope with SS1 encoding */
export interface SS1Envelope {
    version: 'SS1';
    kid: string;
    salt: string;
    ct: string;
    tag: string;
    aad?: string;
    nonce?: string;
}
/**
 * Create an SS1-encoded envelope
 */
export declare function createSS1Envelope(params: {
    kid: string;
    salt: Buffer;
    ciphertext: Buffer;
    tag: Buffer;
    aad?: Buffer;
    nonce?: Buffer;
}): SS1Envelope;
/**
 * Parse an SS1-encoded envelope
 */
export declare function parseSS1Envelope(envelope: SS1Envelope): {
    kid: string;
    salt: Buffer;
    ciphertext: Buffer;
    tag: Buffer;
    aad?: Buffer;
    nonce?: Buffer;
};
/**
 * Serialize envelope to string format
 */
export declare function serializeSS1Envelope(envelope: SS1Envelope): string;
/**
 * Parse envelope from string format
 */
export declare function deserializeSS1Envelope(str: string): SS1Envelope;
/**
 * Detect the tongue of a token by analyzing its phonetic signature
 */
export declare function detectTongue(token: string): TongueCode | null;
/**
 * Validate that all tokens in spell-text use the expected tongue
 */
export declare function validateTongueConsistency(spellText: string, expectedTongue: TongueCode): boolean;
/**
 * Calculate the total harmonic weight of spell-text
 */
export declare function calculateHarmonicWeight(spellText: string): number;
/**
 * Generate audio frequencies for spell-text (for Layer 14 telemetry)
 */
export declare function getAudioSignature(spellText: string): number[];
export declare class SS1Tokenizer {
    private defaultTongue;
    constructor(defaultTongue?: TongueCode);
    encode(data: Buffer | Uint8Array, tongue?: TongueCode): string;
    decode(spellText: string, tongue?: TongueCode): Buffer;
    xlate(spellText: string, fromTongue: TongueCode, toTongue: TongueCode, secretKey?: Buffer): {
        translated: string;
        attestation: XlateAttestation;
    };
    blend(data: Buffer | Uint8Array, pattern: BlendPattern[]): string;
    unblend(spellText: string): Buffer;
    createEnvelope: typeof createSS1Envelope;
    parseEnvelope: typeof parseSS1Envelope;
    serializeEnvelope: typeof serializeSS1Envelope;
    deserializeEnvelope: typeof deserializeSS1Envelope;
    detectTongue: typeof detectTongue;
    validateTongueConsistency: typeof validateTongueConsistency;
    calculateHarmonicWeight: typeof calculateHarmonicWeight;
    getAudioSignature: typeof getAudioSignature;
}
export default SS1Tokenizer;
//# sourceMappingURL=ss1.d.ts.map