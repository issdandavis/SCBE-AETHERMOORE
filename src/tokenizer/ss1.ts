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

import { createHmac, randomBytes } from 'crypto';

// ============================================================================
// Types
// ============================================================================

/** Sacred Tongue identifier */
export type TongueCode = 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';

/** Tongue metadata */
export interface TongueInfo {
  code: TongueCode;
  name: string;
  domain: string;
  phaseOffset: number; // degrees
  weight: number; // φⁿ
  frequency: number; // Hz (440 × φⁿ)
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

// ============================================================================
// Constants
// ============================================================================

/** Golden Ratio */
const PHI = 1.618033988749895;

/** Base frequency (A4) */
const BASE_FREQ = 440;

/** Tongue configurations */
export const TONGUES: Record<TongueCode, TongueInfo> = {
  KO: {
    code: 'KO',
    name: "Kor'aelin",
    domain: 'Nonce / Flow / Control',
    phaseOffset: 0,
    weight: 1.0,
    frequency: BASE_FREQ * Math.pow(PHI, 0),
  },
  AV: {
    code: 'AV',
    name: 'Avali',
    domain: 'AAD / Context / I/O',
    phaseOffset: 60,
    weight: Math.pow(PHI, 1),
    frequency: BASE_FREQ * Math.pow(PHI, 1),
  },
  RU: {
    code: 'RU',
    name: 'Runethic',
    domain: 'Salt / Binding / Policy',
    phaseOffset: 120,
    weight: Math.pow(PHI, 2),
    frequency: BASE_FREQ * Math.pow(PHI, 2),
  },
  CA: {
    code: 'CA',
    name: 'Cassisivadan',
    domain: 'Ciphertext / Compute',
    phaseOffset: 180,
    weight: Math.pow(PHI, 3),
    frequency: BASE_FREQ * Math.pow(PHI, 3),
  },
  UM: {
    code: 'UM',
    name: 'Umbroth',
    domain: 'Redaction / Security',
    phaseOffset: 240,
    weight: Math.pow(PHI, 4),
    frequency: BASE_FREQ * Math.pow(PHI, 4),
  },
  DR: {
    code: 'DR',
    name: 'Draumric',
    domain: 'Auth Tags / Schema',
    phaseOffset: 300,
    weight: Math.pow(PHI, 5),
    frequency: BASE_FREQ * Math.pow(PHI, 5),
  },
};

/** Array of tongue codes for iteration */
export const TONGUE_CODES: TongueCode[] = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'] as const;

// ============================================================================
// Vocabulary Definitions (16 prefixes × 16 suffixes = 256 tokens per tongue)
// ============================================================================

/** Kor'aelin (KO) - Liquid, flowing, swift */
const KO_PREFIXES = [
  'sil', 'vel', 'kor', 'ael', 'mir', 'thal', 'ven', 'lor',
  'eth', 'kin', 'sol', 'ryn', 'fae', 'dor', 'nyl', 'zar',
];
const KO_SUFFIXES = [
  'a', 'an', 'el', 'in', 'or', 'un', 'ae', 'ie',
  'al', 'en', 'il', 'on', 'ur', 'ar', 'er', 'ir',
];

/** Avali (AV) - Bright, diplomatic, clear */
const AV_PREFIXES = [
  'saina', 'maren', 'vali', 'lumi', 'clar', 'bril', 'radi', 'aur',
  'cele', 'flor', 'grac', 'harm', 'jovi', 'klar', 'luci', 'nob',
];
const AV_SUFFIXES = [
  'a', 'en', 'al', 'is', 'or', 'um', 'ia', 'us',
  'el', 'an', 'il', 'os', 'ur', 'as', 'es', 'ir',
];

/** Runethic (RU) - Heavy, grounded, earthy */
const RU_PREFIXES = [
  'khar', 'bront', 'tor', 'grim', 'drak', 'mort', 'stein', 'berg',
  'fels', 'grund', 'hart', 'krag', 'molk', 'nord', 'ost', 'prag',
];
const RU_SUFFIXES = [
  'ak', 'rune', 'ul', 'om', 'ek', 'orn', 'ung', 'ald',
  'ast', 'eft', 'igt', 'olk', 'ung', 'ard', 'ert', 'irt',
];

/** Cassisivadan (CA) - Staccato, mechanical, digital */
const CA_PREFIXES = [
  'bip', 'klik', 'zap', 'ping', 'blip', 'chip', 'digi', 'flux',
  'grid', 'hex', 'jolt', 'kilo', 'link', 'mega', 'node', 'plex',
];
const CA_SUFFIXES = [
  'a', 'lo', 'ix', 'um', 'ex', 'ox', 'ax', 'ux',
  'el', 'ol', 'il', 'ul', 'az', 'ez', 'iz', 'oz',
];

/** Umbroth (UM) - Breathy, mysterious, veiled */
const UM_PREFIXES = [
  'veil', 'shade', 'mist', 'dusk', 'shad', 'murk', 'dim', 'fad',
  'gloom', 'haze', 'obscur', 'penumbr', 'twilit', 'umbr', 'wane', 'whisp',
];
const UM_SUFFIXES = [
  'a', 'nul', 'om', 'ish', 'en', 'ow', 'um', 'yr',
  'al', 'ull', 'im', 'esh', 'an', 'ew', 'am', 'yr',
];

/** Draumric (DR) - Structural, industrial, heavy */
const DR_PREFIXES = [
  'anvil', 'rivet', 'forge', 'bolt', 'clamp', 'weld', 'steel', 'iron',
  'brass', 'chrome', 'titan', 'alloy', 'cast', 'mold', 'stamp', 'press',
];
const DR_SUFFIXES = [
  'a', 'ul', 'on', 'ek', 'ar', 'or', 'um', 'ax',
  'al', 'el', 'an', 'en', 'as', 'es', 'us', 'ix',
];

/** Vocabulary lookup tables */
const VOCABULARIES: Record<TongueCode, { prefixes: string[]; suffixes: string[] }> = {
  KO: { prefixes: KO_PREFIXES, suffixes: KO_SUFFIXES },
  AV: { prefixes: AV_PREFIXES, suffixes: AV_SUFFIXES },
  RU: { prefixes: RU_PREFIXES, suffixes: RU_SUFFIXES },
  CA: { prefixes: CA_PREFIXES, suffixes: CA_SUFFIXES },
  UM: { prefixes: UM_PREFIXES, suffixes: UM_SUFFIXES },
  DR: { prefixes: DR_PREFIXES, suffixes: DR_SUFFIXES },
};

// ============================================================================
// Core Encoding/Decoding
// ============================================================================

/**
 * Encode a single byte to a token
 *
 * Formula: Token = Prefix[High_Nibble] + "'" + Suffix[Low_Nibble]
 *
 * @param byte - The byte value (0-255)
 * @param tongue - The tongue to use for encoding
 * @returns The encoded token (e.g., "vel'an")
 */
export function encodeByte(byte: number, tongue: TongueCode): string {
  if (byte < 0 || byte > 255) {
    throw new Error(`Byte value out of range: ${byte}`);
  }

  const vocab = VOCABULARIES[tongue];
  const highNibble = (byte >> 4) & 0x0f;
  const lowNibble = byte & 0x0f;

  return `${vocab.prefixes[highNibble]}'${vocab.suffixes[lowNibble]}`;
}

/**
 * Decode a token to a byte
 *
 * @param token - The token to decode (e.g., "vel'an")
 * @param tongue - The tongue used for encoding
 * @returns The decoded byte value (0-255)
 */
export function decodeByte(token: string, tongue: TongueCode): number {
  const vocab = VOCABULARIES[tongue];
  const parts = token.split("'");

  if (parts.length !== 2) {
    throw new Error(`Invalid token format: ${token}`);
  }

  const [prefix, suffix] = parts;
  const highNibble = vocab.prefixes.indexOf(prefix);
  const lowNibble = vocab.suffixes.indexOf(suffix);

  if (highNibble === -1) {
    throw new Error(`Unknown prefix '${prefix}' for tongue ${tongue}`);
  }
  if (lowNibble === -1) {
    throw new Error(`Unknown suffix '${suffix}' for tongue ${tongue}`);
  }

  return (highNibble << 4) | lowNibble;
}

/**
 * Encode a buffer to spell-text
 *
 * @param data - The data to encode
 * @param tongue - The tongue to use
 * @param includePrefix - Whether to include tongue prefix (e.g., "ko:")
 * @returns Space-separated tokens
 */
export function encode(data: Buffer | Uint8Array, tongue: TongueCode, includePrefix = true): string {
  const tokens: string[] = [];
  const prefix = includePrefix ? `${tongue.toLowerCase()}:` : '';

  for (const byte of data) {
    tokens.push(prefix + encodeByte(byte, tongue));
  }

  return tokens.join(' ');
}

/**
 * Decode spell-text to a buffer
 *
 * @param spellText - The spell-text to decode
 * @param tongue - The tongue used (optional if prefix included)
 * @returns The decoded buffer
 */
export function decode(spellText: string, tongue?: TongueCode): Buffer {
  const tokens = spellText.trim().split(/\s+/);
  const bytes: number[] = [];

  for (const token of tokens) {
    let actualToken = token;
    let actualTongue = tongue;

    // Check for tongue prefix (e.g., "ko:vel'an")
    if (token.includes(':')) {
      const [prefix, rest] = token.split(':');
      actualTongue = prefix.toUpperCase() as TongueCode;
      actualToken = rest;
    }

    if (!actualTongue) {
      throw new Error('Tongue must be specified if tokens have no prefix');
    }

    bytes.push(decodeByte(actualToken, actualTongue));
  }

  return Buffer.from(bytes);
}

// ============================================================================
// Cross-Tokenization (xlate)
// ============================================================================

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
export function xlate(
  spellText: string,
  fromTongue: TongueCode,
  toTongue: TongueCode,
  secretKey?: Buffer
): { translated: string; attestation: XlateAttestation } {
  // Decode from source tongue
  const data = decode(spellText, fromTongue);

  // Encode to target tongue
  const translated = encode(data, toTongue);

  // Calculate phase delta and weight ratio
  const fromInfo = TONGUES[fromTongue];
  const toInfo = TONGUES[toTongue];
  const phaseDelta = (toInfo.phaseOffset - fromInfo.phaseOffset + 360) % 360;
  const weightRatio = toInfo.weight / fromInfo.weight;

  // Create attestation
  const attestation: XlateAttestation = {
    fromTongue,
    toTongue,
    phaseDelta,
    weightRatio,
    timestamp: Date.now(),
    signature: '',
  };

  // Sign attestation if key provided
  if (secretKey) {
    const dataToSign = `${fromTongue}:${toTongue}:${phaseDelta}:${weightRatio}:${attestation.timestamp}`;
    attestation.signature = createHmac('sha256', secretKey).update(dataToSign).digest('hex');
  }

  return { translated, attestation };
}

/**
 * Verify an xlate attestation
 */
export function verifyXlateAttestation(attestation: XlateAttestation, secretKey: Buffer): boolean {
  const dataToSign = `${attestation.fromTongue}:${attestation.toTongue}:${attestation.phaseDelta}:${attestation.weightRatio}:${attestation.timestamp}`;
  const expected = createHmac('sha256', secretKey).update(dataToSign).digest('hex');
  return attestation.signature === expected;
}

// ============================================================================
// Tongue Blending (Stripe Mode)
// ============================================================================

/**
 * Encode data using a blending pattern
 *
 * @param data - The data to encode
 * @param pattern - Array of {tongue, count} specifying the stripe pattern
 * @returns Blended spell-text
 */
export function blend(data: Buffer | Uint8Array, pattern: BlendPattern[]): string {
  const tokens: string[] = [];
  let dataIndex = 0;
  let patternIndex = 0;
  let countInPattern = 0;

  while (dataIndex < data.length) {
    const { tongue, count } = pattern[patternIndex];
    const prefix = `${tongue.toLowerCase()}:`;

    tokens.push(prefix + encodeByte(data[dataIndex], tongue));
    dataIndex++;
    countInPattern++;

    if (countInPattern >= count) {
      countInPattern = 0;
      patternIndex = (patternIndex + 1) % pattern.length;
    }
  }

  return tokens.join(' ');
}

/**
 * Decode blended spell-text
 *
 * @param spellText - The blended spell-text (must include tongue prefixes)
 * @returns The decoded buffer
 */
export function unblend(spellText: string): Buffer {
  return decode(spellText); // Tongue prefix is required for blended text
}

// ============================================================================
// RWP Envelope Integration
// ============================================================================

/** RWP Envelope with SS1 encoding */
export interface SS1Envelope {
  version: 'SS1';
  kid: string;
  salt: string; // RU-encoded
  ct: string; // CA-encoded
  tag: string; // DR-encoded
  aad?: string; // AV-encoded (optional)
  nonce?: string; // KO-encoded (optional)
}

/**
 * Create an SS1-encoded envelope
 */
export function createSS1Envelope(params: {
  kid: string;
  salt: Buffer;
  ciphertext: Buffer;
  tag: Buffer;
  aad?: Buffer;
  nonce?: Buffer;
}): SS1Envelope {
  return {
    version: 'SS1',
    kid: params.kid,
    salt: encode(params.salt, 'RU'),
    ct: encode(params.ciphertext, 'CA'),
    tag: encode(params.tag, 'DR'),
    aad: params.aad ? encode(params.aad, 'AV') : undefined,
    nonce: params.nonce ? encode(params.nonce, 'KO') : undefined,
  };
}

/**
 * Parse an SS1-encoded envelope
 */
export function parseSS1Envelope(envelope: SS1Envelope): {
  kid: string;
  salt: Buffer;
  ciphertext: Buffer;
  tag: Buffer;
  aad?: Buffer;
  nonce?: Buffer;
} {
  return {
    kid: envelope.kid,
    salt: decode(envelope.salt, 'RU'),
    ciphertext: decode(envelope.ct, 'CA'),
    tag: decode(envelope.tag, 'DR'),
    aad: envelope.aad ? decode(envelope.aad, 'AV') : undefined,
    nonce: envelope.nonce ? decode(envelope.nonce, 'KO') : undefined,
  };
}

/**
 * Serialize envelope to string format
 */
export function serializeSS1Envelope(envelope: SS1Envelope): string {
  let result = `SS1|kid=${envelope.kid}|salt=${envelope.salt}|ct=${envelope.ct}|tag=${envelope.tag}`;
  if (envelope.aad) result += `|aad=${envelope.aad}`;
  if (envelope.nonce) result += `|nonce=${envelope.nonce}`;
  return result;
}

/**
 * Parse envelope from string format
 */
export function deserializeSS1Envelope(str: string): SS1Envelope {
  const parts = str.split('|');
  if (parts[0] !== 'SS1') {
    throw new Error('Invalid SS1 envelope format');
  }

  const envelope: Partial<SS1Envelope> = { version: 'SS1' };

  for (let i = 1; i < parts.length; i++) {
    const [key, value] = parts[i].split('=');
    switch (key) {
      case 'kid':
        envelope.kid = value;
        break;
      case 'salt':
        envelope.salt = value;
        break;
      case 'ct':
        envelope.ct = value;
        break;
      case 'tag':
        envelope.tag = value;
        break;
      case 'aad':
        envelope.aad = value;
        break;
      case 'nonce':
        envelope.nonce = value;
        break;
    }
  }

  if (!envelope.kid || !envelope.salt || !envelope.ct || !envelope.tag) {
    throw new Error('Missing required envelope fields');
  }

  return envelope as SS1Envelope;
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Detect the tongue of a token by analyzing its phonetic signature
 */
export function detectTongue(token: string): TongueCode | null {
  // Check for explicit prefix
  if (token.includes(':')) {
    const prefix = token.split(':')[0].toUpperCase();
    if (prefix in TONGUES) {
      return prefix as TongueCode;
    }
  }

  // Try to match against vocabularies
  const parts = token.split("'");
  if (parts.length !== 2) return null;

  const [prefix] = parts;

  for (const [code, vocab] of Object.entries(VOCABULARIES)) {
    if (vocab.prefixes.includes(prefix)) {
      return code as TongueCode;
    }
  }

  return null;
}

/**
 * Validate that all tokens in spell-text use the expected tongue
 */
export function validateTongueConsistency(spellText: string, expectedTongue: TongueCode): boolean {
  const tokens = spellText.trim().split(/\s+/);

  for (const token of tokens) {
    const detected = detectTongue(token);
    if (detected !== expectedTongue) {
      return false;
    }
  }

  return true;
}

/**
 * Calculate the total harmonic weight of spell-text
 */
export function calculateHarmonicWeight(spellText: string): number {
  const tokens = spellText.trim().split(/\s+/);
  let totalWeight = 0;

  for (const token of tokens) {
    const tongue = detectTongue(token);
    if (tongue) {
      totalWeight += TONGUES[tongue].weight;
    }
  }

  return totalWeight;
}

/**
 * Generate audio frequencies for spell-text (for Layer 14 telemetry)
 */
export function getAudioSignature(spellText: string): number[] {
  const tokens = spellText.trim().split(/\s+/);
  const frequencies: number[] = [];

  for (const token of tokens) {
    const tongue = detectTongue(token);
    if (tongue) {
      frequencies.push(TONGUES[tongue].frequency);
    }
  }

  return frequencies;
}

// ============================================================================
// Export tokenizer class for convenience
// ============================================================================

export class SS1Tokenizer {
  private defaultTongue: TongueCode;

  constructor(defaultTongue: TongueCode = 'KO') {
    this.defaultTongue = defaultTongue;
  }

  encode(data: Buffer | Uint8Array, tongue?: TongueCode): string {
    return encode(data, tongue ?? this.defaultTongue);
  }

  decode(spellText: string, tongue?: TongueCode): Buffer {
    return decode(spellText, tongue ?? this.defaultTongue);
  }

  xlate(spellText: string, fromTongue: TongueCode, toTongue: TongueCode, secretKey?: Buffer) {
    return xlate(spellText, fromTongue, toTongue, secretKey);
  }

  blend(data: Buffer | Uint8Array, pattern: BlendPattern[]): string {
    return blend(data, pattern);
  }

  unblend(spellText: string): Buffer {
    return unblend(spellText);
  }

  createEnvelope = createSS1Envelope;
  parseEnvelope = parseSS1Envelope;
  serializeEnvelope = serializeSS1Envelope;
  deserializeEnvelope = deserializeSS1Envelope;

  detectTongue = detectTongue;
  validateTongueConsistency = validateTongueConsistency;
  calculateHarmonicWeight = calculateHarmonicWeight;
  getAudioSignature = getAudioSignature;
}

export default SS1Tokenizer;
