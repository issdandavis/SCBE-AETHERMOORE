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
import { TONGUES, SECTION_TONGUES } from './sacredTongues.js';
// ═══════════════════════════════════════════════════════════════
// Sacred Tongue Tokenizer
// ═══════════════════════════════════════════════════════════════
/**
 * Sacred Tongue Tokenizer
 *
 * Encodes/decodes bytes to spell-text tokens using the 16×16 grid.
 * Each byte maps to exactly one token: prefix'suffix
 */
export class SacredTongueTokenizer {
  tongue;
  byteToToken;
  tokenToByte;
  constructor(tongueCode = 'ko') {
    const tongue = TONGUES[tongueCode];
    if (!tongue) {
      throw new Error(`Unknown tongue: ${tongueCode}. Valid: ${Object.keys(TONGUES).join(', ')}`);
    }
    this.tongue = tongue;
    // Build lookup tables
    this.byteToToken = [];
    this.tokenToByte = new Map();
    for (let b = 0; b < 256; b++) {
      const prefixIdx = b >> 4; // High nibble (0-15)
      const suffixIdx = b & 0x0f; // Low nibble (0-15)
      const token = `${tongue.prefixes[prefixIdx]}'${tongue.suffixes[suffixIdx]}`;
      this.byteToToken.push(token);
      this.tokenToByte.set(token, b);
    }
  }
  /**
   * Encode a single byte to a token
   */
  encodeByte(b) {
    if (b < 0 || b > 255) {
      throw new RangeError(`Byte must be 0-255, got ${b}`);
    }
    return this.byteToToken[b];
  }
  /**
   * Decode a single token to a byte
   */
  decodeToken(token) {
    const b = this.tokenToByte.get(token);
    if (b === undefined) {
      throw new Error(`Unknown token: ${token}`);
    }
    return b;
  }
  /**
   * Encode bytes to space-separated spell-text tokens
   */
  encode(data) {
    const tokens = [];
    for (const b of data) {
      tokens.push(`${this.tongue.code}:${this.byteToToken[b]}`);
    }
    return tokens.join(' ');
  }
  /**
   * Encode bytes without tongue prefix (for compact format)
   */
  encodeCompact(data) {
    const tokens = [];
    for (const b of data) {
      tokens.push(this.byteToToken[b]);
    }
    return tokens.join(' ');
  }
  /**
   * Decode spell-text tokens back to bytes
   */
  decode(spelltext) {
    const result = [];
    for (const token of spelltext.split(/\s+/)) {
      if (!token) continue;
      // Strip tongue prefix if present (e.g., "ko:sil'a" → "sil'a")
      const cleanToken = token.includes(':') ? token.split(':')[1] : token;
      const b = this.tokenToByte.get(cleanToken);
      if (b === undefined) {
        throw new Error(`Unknown token: ${cleanToken}`);
      }
      result.push(b);
    }
    return new Uint8Array(result);
  }
  /**
   * Get all 256 tokens for this tongue
   */
  getAllTokens() {
    return [...this.byteToToken];
  }
  /**
   * Validate that a token belongs to this tongue
   */
  isValidToken(token) {
    return this.tokenToByte.has(token);
  }
}
// ═══════════════════════════════════════════════════════════════
// Section Encoding Helpers
// ═══════════════════════════════════════════════════════════════
/**
 * Encode bytes using the canonical tongue for a section
 */
export function encodeToSpelltext(data, section) {
  const tongueCode = SECTION_TONGUES[section] || 'ca';
  const tokenizer = new SacredTongueTokenizer(tongueCode);
  return `${tongueCode}:${tokenizer.encodeCompact(data)}`;
}
/**
 * Decode spell-text using the canonical tongue for a section
 */
export function decodeFromSpelltext(spelltext, section) {
  const tongueCode = SECTION_TONGUES[section] || 'ca';
  const tokenizer = new SacredTongueTokenizer(tongueCode);
  // Remove tongue prefix if present
  let text = spelltext;
  if (text.startsWith(`${tongueCode}:`)) {
    text = text.slice(tongueCode.length + 1);
  }
  return tokenizer.decode(text);
}
/**
 * Format a complete SS1 spell-text blob
 */
export function formatSS1Blob(kid, aad, salt, nonce, ciphertext, tag) {
  const parts = [
    'SS1',
    `kid=${kid}`,
    `aad=${aad}`,
    encodeToSpelltext(salt, 'salt'),
    encodeToSpelltext(nonce, 'nonce'),
    encodeToSpelltext(ciphertext, 'ct'),
    encodeToSpelltext(tag, 'tag'),
  ];
  return parts.join('|');
}
/**
 * Parse an SS1 spell-text blob
 */
export function parseSS1Blob(blob) {
  if (!blob.startsWith('SS1|')) {
    throw new Error("Invalid SS1 blob: must start with 'SS1|'");
  }
  const parts = blob.split('|');
  const result = { version: 'SS1' };
  for (let i = 1; i < parts.length; i++) {
    const part = parts[i];
    if (part.startsWith('kid=')) {
      result.kid = part.slice(4);
    } else if (part.startsWith('aad=')) {
      result.aad = part.slice(4);
    } else if (part.startsWith('ru:')) {
      result.salt = decodeFromSpelltext(part, 'salt');
    } else if (part.startsWith('ko:')) {
      result.nonce = decodeFromSpelltext(part, 'nonce');
    } else if (part.startsWith('ca:')) {
      result.ciphertext = decodeFromSpelltext(part, 'ct');
    } else if (part.startsWith('dr:')) {
      result.tag = decodeFromSpelltext(part, 'tag');
    }
  }
  // Validate required fields
  if (!result.kid) throw new Error('SS1 blob missing kid');
  if (!result.aad) throw new Error('SS1 blob missing aad');
  if (!result.salt) throw new Error('SS1 blob missing salt');
  if (!result.nonce) throw new Error('SS1 blob missing nonce');
  if (!result.ciphertext) throw new Error('SS1 blob missing ciphertext');
  if (!result.tag) throw new Error('SS1 blob missing tag');
  return result;
}
// ═══════════════════════════════════════════════════════════════
// Crypto Utilities (Web Crypto API)
// ═══════════════════════════════════════════════════════════════
/**
 * Generate random bytes
 */
export function randomBytes(length) {
  const bytes = new Uint8Array(length);
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
    crypto.getRandomValues(bytes);
  } else {
    // Fallback for Node.js without global crypto
    for (let i = 0; i < length; i++) {
      bytes[i] = Math.floor(Math.random() * 256);
    }
  }
  return bytes;
}
/**
 * HKDF key derivation (simplified - uses SHA-256)
 */
async function hkdfDerive(masterSecret, salt, info, length = 32) {
  // Check if Web Crypto is available
  if (typeof crypto === 'undefined' || !crypto.subtle) {
    throw new Error('Web Crypto API not available');
  }
  // Import master secret as HKDF key
  const keyMaterial = await crypto.subtle.importKey('raw', masterSecret, 'HKDF', false, [
    'deriveBits',
  ]);
  // Derive key using HKDF
  const derivedBits = await crypto.subtle.deriveBits(
    {
      name: 'HKDF',
      hash: 'SHA-256',
      salt: salt,
      info: info,
    },
    keyMaterial,
    length * 8
  );
  return new Uint8Array(derivedBits);
}
/**
 * AES-GCM encryption
 */
async function aesGcmEncrypt(plaintext, key, nonce, aad) {
  if (typeof crypto === 'undefined' || !crypto.subtle) {
    throw new Error('Web Crypto API not available');
  }
  const cryptoKey = await crypto.subtle.importKey('raw', key, 'AES-GCM', false, ['encrypt']);
  const result = await crypto.subtle.encrypt(
    {
      name: 'AES-GCM',
      iv: nonce,
      additionalData: aad,
      tagLength: 128,
    },
    cryptoKey,
    plaintext
  );
  // Result includes ciphertext + tag (last 16 bytes)
  const combined = new Uint8Array(result);
  const ciphertext = combined.slice(0, -16);
  const tag = combined.slice(-16);
  return { ciphertext, tag };
}
/**
 * AES-GCM decryption
 */
async function aesGcmDecrypt(ciphertext, tag, key, nonce, aad) {
  if (typeof crypto === 'undefined' || !crypto.subtle) {
    throw new Error('Web Crypto API not available');
  }
  const cryptoKey = await crypto.subtle.importKey('raw', key, 'AES-GCM', false, ['decrypt']);
  // Combine ciphertext + tag for Web Crypto
  const combined = new Uint8Array(ciphertext.length + tag.length);
  combined.set(ciphertext);
  combined.set(tag, ciphertext.length);
  const result = await crypto.subtle.decrypt(
    {
      name: 'AES-GCM',
      iv: nonce,
      additionalData: aad,
      tagLength: 128,
    },
    cryptoKey,
    combined
  );
  return new Uint8Array(result);
}
// ═══════════════════════════════════════════════════════════════
// SpiralSeal SS1 - High-Level API
// ═══════════════════════════════════════════════════════════════
/**
 * Seal plaintext into an SS1 spell-text blob
 *
 * @param plaintext - Data to encrypt
 * @param masterSecret - 32-byte master secret
 * @param aad - Additional authenticated data (context string)
 * @param kid - Key identifier for rotation
 * @returns SS1 spell-text blob
 */
export async function seal(plaintext, masterSecret, aad, kid = 'k01') {
  // 1. Generate random salt (16 bytes)
  const salt = randomBytes(16);
  // 2. Derive encryption key via HKDF
  const info = new TextEncoder().encode(`SS1-${kid}`);
  const key = await hkdfDerive(masterSecret, salt, info, 32);
  // 3. Encrypt with AES-256-GCM
  const nonce = randomBytes(12);
  const aadBytes = new TextEncoder().encode(aad);
  const { ciphertext, tag } = await aesGcmEncrypt(plaintext, key, nonce, aadBytes);
  // 4. Format SS1 blob
  return formatSS1Blob(kid, aad, salt, nonce, ciphertext, tag);
}
/**
 * Unseal an SS1 spell-text blob back to plaintext
 *
 * @param blob - SS1 spell-text blob
 * @param masterSecret - 32-byte master secret
 * @param aad - Additional authenticated data (must match sealed AAD)
 * @returns Decrypted plaintext
 */
export async function unseal(blob, masterSecret, aad) {
  // 1. Parse SS1 blob
  const parsed = parseSS1Blob(blob);
  // 2. Verify AAD matches
  if (parsed.aad !== aad) {
    throw new Error('AAD mismatch: authentication failed');
  }
  // 3. Derive encryption key via HKDF
  const info = new TextEncoder().encode(`SS1-${parsed.kid}`);
  const key = await hkdfDerive(masterSecret, parsed.salt, info, 32);
  // 4. Decrypt with AES-256-GCM
  const aadBytes = new TextEncoder().encode(aad);
  return aesGcmDecrypt(parsed.ciphertext, parsed.tag, key, parsed.nonce, aadBytes);
}
/**
 * SpiralSeal SS1 class for stateful operations
 */
export class SpiralSealSS1 {
  masterSecret;
  kid;
  constructor(masterSecret, kid = 'k01') {
    if (masterSecret.length < 32) {
      throw new Error('Master secret must be at least 32 bytes');
    }
    this.masterSecret = masterSecret;
    this.kid = kid;
  }
  /**
   * Seal plaintext with instance's master secret
   */
  async seal(plaintext, aad) {
    return seal(plaintext, this.masterSecret, aad, this.kid);
  }
  /**
   * Unseal blob with instance's master secret
   */
  async unseal(blob, aad) {
    return unseal(blob, this.masterSecret, aad);
  }
  /**
   * Rotate to a new key
   */
  rotateKey(newKid, newMasterSecret) {
    if (newMasterSecret.length < 32) {
      throw new Error('Master secret must be at least 32 bytes');
    }
    this.kid = newKid;
    this.masterSecret = newMasterSecret;
  }
  /**
   * Get current key ID
   */
  getKid() {
    return this.kid;
  }
  /**
   * Get status report
   */
  getStatus() {
    return {
      version: 'SS1',
      kid: this.kid,
      capabilities: ['AES-256-GCM', 'HKDF-SHA256', 'Sacred Tongue encoding', 'Key rotation'],
    };
  }
}
// ═══════════════════════════════════════════════════════════════
// Langues Weighting System Integration
// ═══════════════════════════════════════════════════════════════
/** Golden ratio for weight progression */
const PHI = (1 + Math.sqrt(5)) / 2;
/**
 * Compute Langues Weighting System weights for a tongue
 *
 * Weights follow golden ratio progression: wₗ = φˡ
 */
export function computeLWSWeights(tongueCode) {
  const tongue = TONGUES[tongueCode];
  if (!tongue) {
    throw new Error(`Unknown tongue: ${tongueCode}`);
  }
  // 6 dimensions corresponding to the 6 tongues
  const tongueOrder = ['ko', 'av', 'ru', 'ca', 'um', 'dr'];
  const index = tongueOrder.indexOf(tongueCode);
  // Weights: φ^0, φ^1, φ^2, φ^3, φ^4, φ^5
  const weights = [];
  for (let i = 0; i < 6; i++) {
    // Weight is highest for the matching tongue
    const distance = Math.abs(i - index);
    weights.push(Math.pow(PHI, 5 - distance));
  }
  return weights;
}
/**
 * Compute combined LWS score for a spell-text string
 */
export function computeLWSScore(spelltext) {
  // Count tokens per tongue
  const counts = { ko: 0, av: 0, ru: 0, ca: 0, um: 0, dr: 0 };
  for (const token of spelltext.split(/\s+/)) {
    if (!token) continue;
    if (token.includes(':')) {
      const [code] = token.split(':');
      if (code in counts) {
        counts[code]++;
      }
    }
  }
  // Compute weighted score
  const tongueOrder = ['ko', 'av', 'ru', 'ca', 'um', 'dr'];
  let totalScore = 0;
  let totalCount = 0;
  for (let i = 0; i < tongueOrder.length; i++) {
    const code = tongueOrder[i];
    const weight = Math.pow(PHI, i);
    totalScore += counts[code] * weight;
    totalCount += counts[code];
  }
  return totalCount > 0 ? totalScore / totalCount : 0;
}
//# sourceMappingURL=spiralSeal.js.map
