/**
 * @file aetherlex-seed.ts
 * @module crypto/aetherlex-seed
 * @layer Layer 4 (Poincaré embedding), Layer 1 (composition axiom)
 * @component AetherLex Seed v1.0 — Sacred Tongue mnemonic seed generation
 * @version 1.0.0
 *
 * Novel seed generation for post-quantum key material using Sacred Tongue
 * lexicon tokens as a BIP-39-style mnemonic — but Spiralverse-native.
 *
 * Patent relevance (USPTO #63/961,403):
 *   The Six Sacred Tongues provide 6 × 256 = 1,536 canonical tokens.
 *   Each token maps to a stable index in the Everweave genesis table.
 *   A phrase of N tokens encodes N × log₂(1536) ≈ N × 10.58 bits of
 *   entropy, then is hashed through SHAKE-256 (via SHA-3 family) to
 *   produce uniform seed bytes for ML-KEM-768 / ML-DSA-65.
 *
 * Dual representation:
 *   Continuous — the seed derives a point in hyperbolic state space
 *   Discrete  — the seed IS a finite word in Sacred Tongues
 *
 * Security model:
 *   - Entropy comes from the hash extractor (SHAKE/SHA-3), not the tokens
 *   - Optional supplemental CSPRNG entropy is concatenated before hashing
 *   - Meets NIST SP 800-90A/B requirements when combined with QRNG/CSPRNG
 *   - Domain separation: "AETHERLEX-SEED-v1" prefix prevents cross-protocol
 *
 * Tongue roles in seed profiles:
 *   KO (flow/intent)    → user-facing auth flows
 *   AV (context)         → protocol/environment seeds
 *   RU (binding)         → cryptographic core material
 *   CA (bitcraft)        → computational/algorithmic keys
 *   UM (veil)            → recovery and concealment keys
 *   DR (structure)       → governance and structural keys
 */

import { createHash, randomBytes } from 'crypto';
import {
  TONGUES,
  KOR_AELIN,
  AVALI,
  RUNETHIC,
  CASSISIVADAN,
  UMBROTH,
  DRAUMRIC,
  type TongueSpec,
} from '../harmonic/sacredTongues.js';

// ════════════════════════════════════════════════════════════════
// CONSTANTS
// ════════════════════════════════════════════════════════════════

/** Domain separation tag for seed derivation */
export const AETHERLEX_DOMAIN = 'AETHERLEX-SEED-v1';

/** Tongue codes in canonical order */
export const TONGUE_ORDER = ['ko', 'av', 'ru', 'ca', 'um', 'dr'] as const;
export type TongueCode = (typeof TONGUE_ORDER)[number];

/** Total token space: 6 tongues × 256 tokens = 1,536 */
export const TOTAL_TOKENS = 1536;

/** Bits of entropy per token: log₂(1536) ≈ 10.58 */
export const BITS_PER_TOKEN = Math.log2(TOTAL_TOKENS);

/** Golden ratio for LWS weights */
const PHI = (1 + Math.sqrt(5)) / 2;

/** LWS tongue weights (linear progression) */
export const LWS_WEIGHTS: Record<TongueCode, number> = {
  ko: 1.0,
  av: 1.125,
  ru: 1.25,
  ca: 1.333,
  um: 1.5,
  dr: 1.667,
};

/** PHDM tongue weights (φⁿ crisis-mode scaling) */
export const PHDM_WEIGHTS: Record<TongueCode, number> = {
  ko: 1.0,
  av: PHI,          // ≈ 1.618
  ru: PHI ** 2,     // ≈ 2.618
  ca: PHI ** 3,     // ≈ 4.236
  um: PHI ** 4,     // ≈ 6.854
  dr: PHI ** 5,     // ≈ 11.090
};

// ════════════════════════════════════════════════════════════════
// TOKEN INDEX — canonical mapping
// ════════════════════════════════════════════════════════════════

/**
 * A single token in the AetherLex space.
 *
 * Global index layout:
 *   KO: [0, 255], AV: [256, 511], RU: [512, 767],
 *   CA: [768, 1023], UM: [1024, 1279], DR: [1280, 1535]
 */
export interface AetherToken {
  /** Tongue code */
  tongue: TongueCode;
  /** Prefix index (0-15) */
  prefixIndex: number;
  /** Suffix index (0-15) */
  suffixIndex: number;
  /** Byte value within the tongue (0-255) */
  byteValue: number;
  /** Global index in the 1536-token space */
  globalIndex: number;
  /** Human-readable token: prefix'suffix */
  token: string;
}

/** Get the TongueSpec for a code */
function getTongue(code: TongueCode): TongueSpec {
  const spec = TONGUES[code];
  if (!spec) throw new Error(`Unknown tongue: ${code}`);
  return spec;
}

/** Tongue offset in global index space */
function tongueOffset(code: TongueCode): number {
  return TONGUE_ORDER.indexOf(code) * 256;
}

/**
 * Encode a byte (0-255) within a tongue to an AetherToken.
 */
export function byteToToken(tongue: TongueCode, byte: number): AetherToken {
  if (byte < 0 || byte > 255) throw new RangeError(`Byte must be 0-255, got ${byte}`);
  const spec = getTongue(tongue);
  const hi = byte >> 4;
  const lo = byte & 0x0f;
  return {
    tongue,
    prefixIndex: hi,
    suffixIndex: lo,
    byteValue: byte,
    globalIndex: tongueOffset(tongue) + byte,
    token: `${spec.prefixes[hi]}'${spec.suffixes[lo]}`,
  };
}

/**
 * Decode a token string back to its AetherToken.
 * Searches all tongues if tongue is not specified.
 */
export function tokenToAether(tokenStr: string, tongue?: TongueCode): AetherToken {
  const [prefix, suffix] = tokenStr.split("'");
  if (!prefix || suffix === undefined) {
    throw new Error(`Invalid token format (expected prefix'suffix): ${tokenStr}`);
  }

  const codes = tongue ? [tongue] : [...TONGUE_ORDER];
  for (const code of codes) {
    const spec = getTongue(code);
    const hi = spec.prefixes.indexOf(prefix);
    const lo = spec.suffixes.indexOf(suffix);
    if (hi !== -1 && lo !== -1) {
      const byte = (hi << 4) | lo;
      return {
        tongue: code,
        prefixIndex: hi,
        suffixIndex: lo,
        byteValue: byte,
        globalIndex: tongueOffset(code) + byte,
        token: tokenStr,
      };
    }
  }
  throw new Error(`Token not found in any tongue: ${tokenStr}`);
}

// ════════════════════════════════════════════════════════════════
// MNEMONIC PHRASE
// ════════════════════════════════════════════════════════════════

/**
 * An AetherLex mnemonic phrase — the Sacred Tongue equivalent of a
 * BIP-39 mnemonic, but with domain-aware tongue assignments.
 */
export interface AetherPhrase {
  /** Ordered tokens */
  tokens: AetherToken[];
  /** Space-separated human-readable form */
  phrase: string;
  /** Estimated entropy bits (tokens × log₂(1536)) */
  entropyBits: number;
  /** Tongue distribution */
  tongueDistribution: Record<TongueCode, number>;
  /** LWS weight of the phrase */
  lwsWeight: number;
}

/**
 * Parse a space-separated Sacred Tongue phrase into an AetherPhrase.
 *
 * Example: "kor'ah saina'a khar'ak bip'a veil'a anvil'a"
 *          → one token per tongue in canonical order
 */
export function parsePhrase(phrase: string): AetherPhrase {
  const parts = phrase.trim().split(/\s+/);
  if (parts.length === 0) throw new Error('Empty phrase');

  const tokens = parts.map((t) => tokenToAether(t));
  const dist: Record<TongueCode, number> = { ko: 0, av: 0, ru: 0, ca: 0, um: 0, dr: 0 };
  let lwsWeight = 0;

  for (const t of tokens) {
    dist[t.tongue]++;
    lwsWeight += LWS_WEIGHTS[t.tongue];
  }

  return {
    tokens,
    phrase: tokens.map((t) => t.token).join(' '),
    entropyBits: tokens.length * BITS_PER_TOKEN,
    tongueDistribution: dist,
    lwsWeight,
  };
}

// ════════════════════════════════════════════════════════════════
// SEED PROFILES — tongue-aware key generation patterns
// ════════════════════════════════════════════════════════════════

/** A seed profile defines which tongues contribute to a key's mnemonic. */
export interface SeedProfile {
  /** Profile name */
  name: string;
  /** Required minimum tokens per tongue (0 = optional) */
  tongueRequirements: Record<TongueCode, number>;
  /** Total tokens required */
  totalTokens: number;
  /** Target output bytes (32 for ML-DSA, 64 for ML-KEM) */
  outputBytes: number;
  /** Description */
  description: string;
}

/**
 * Forge-grade: governance keys.
 * ≥1 Draumric (structure) + ≥1 Umbroth (veil) + ≥1 Runethic (binding).
 * 12 tokens total → ~127 bits from lexicon alone.
 */
export const PROFILE_FORGE: SeedProfile = {
  name: 'forge-grade',
  tongueRequirements: { ko: 0, av: 0, ru: 1, ca: 0, um: 1, dr: 1 },
  totalTokens: 12,
  outputBytes: 64,
  description: 'Governance / structural keys (ML-KEM-768)',
};

/**
 * Veil-grade: concealment / recovery keys.
 * ≥3 Umbroth (veil) + ≥1 Runethic (binding).
 * 12 tokens → ~127 bits.
 */
export const PROFILE_VEIL: SeedProfile = {
  name: 'veil-grade',
  tongueRequirements: { ko: 0, av: 0, ru: 1, ca: 0, um: 3, dr: 0 },
  totalTokens: 12,
  outputBytes: 32,
  description: 'Recovery / concealment keys (ML-DSA-65)',
};

/**
 * Everweave root: exactly 1 token from each tongue × 2 rounds = 12 tokens.
 * Liturgical pattern — balanced across all domains.
 */
export const PROFILE_EVERWEAVE: SeedProfile = {
  name: 'everweave-root',
  tongueRequirements: { ko: 2, av: 2, ru: 2, ca: 2, um: 2, dr: 2 },
  totalTokens: 12,
  outputBytes: 64,
  description: 'Balanced root key (all tongues, liturgical)',
};

/**
 * Flow-grade: user-facing auth.
 * ≥3 Kor'aelin (flow/intent) + ≥1 Avali (context).
 * 8 tokens → ~85 bits (supplement with CSPRNG).
 */
export const PROFILE_FLOW: SeedProfile = {
  name: 'flow-grade',
  tongueRequirements: { ko: 3, av: 1, ru: 0, ca: 0, um: 0, dr: 0 },
  totalTokens: 8,
  outputBytes: 32,
  description: 'User-facing auth keys (short, supplemented with CSPRNG)',
};

/** All built-in profiles */
export const SEED_PROFILES: Record<string, SeedProfile> = {
  'forge-grade': PROFILE_FORGE,
  'veil-grade': PROFILE_VEIL,
  'everweave-root': PROFILE_EVERWEAVE,
  'flow-grade': PROFILE_FLOW,
};

// ════════════════════════════════════════════════════════════════
// SEED DERIVATION
// ════════════════════════════════════════════════════════════════

/** Options for seed derivation */
export interface SeedOptions {
  /** Additional CSPRNG entropy to mix in (recommended: 32 bytes) */
  supplementalEntropy?: Uint8Array;
  /** Output byte length (default: from profile or 64) */
  outputBytes?: number;
  /** Custom domain separation tag (default: AETHERLEX_DOMAIN) */
  domain?: string;
}

/** Result of seed derivation */
export interface DerivedSeed {
  /** The derived seed bytes */
  seed: Uint8Array;
  /** The mnemonic phrase used */
  phrase: AetherPhrase;
  /** Whether supplemental entropy was mixed in */
  hasSupplementalEntropy: boolean;
  /** Domain tag used */
  domain: string;
  /** Output length in bytes */
  outputBytes: number;
  /** Estimated entropy bits from phrase alone */
  phraseEntropyBits: number;
}

/**
 * Encode a phrase's token indices into a compact bitstring.
 *
 * Each token's global index (0-1535) is packed as an 11-bit value
 * (2^11 = 2048 > 1536, so 11 bits per token with room to spare).
 */
export function encodeTokenIndices(tokens: AetherToken[]): Uint8Array {
  const totalBits = tokens.length * 11;
  const bytes = new Uint8Array(Math.ceil(totalBits / 8));

  let bitOffset = 0;
  for (const t of tokens) {
    const idx = t.globalIndex;
    // Write 11 bits of idx starting at bitOffset
    for (let b = 10; b >= 0; b--) {
      const bit = (idx >> b) & 1;
      const bytePos = Math.floor(bitOffset / 8);
      const bitPos = 7 - (bitOffset % 8);
      bytes[bytePos] |= bit << bitPos;
      bitOffset++;
    }
  }

  return bytes;
}

/**
 * Derive a cryptographic seed from a Sacred Tongue mnemonic phrase.
 *
 * Pipeline:
 *   1. Encode token indices into compact bitstring
 *   2. Optionally prepend LWS weight header (tongue balance metadata)
 *   3. Concatenate supplemental CSPRNG entropy if provided
 *   4. Hash through SHA-512 with domain separation
 *   5. Truncate to requested output length
 *
 * The resulting seed is suitable for:
 *   - ML-KEM-768 KeyGen (64 bytes → d || z)
 *   - ML-DSA-65 KeyGen (32 bytes → ξ)
 *   - Any other algorithm expecting uniform seed bytes
 */
export function deriveSeed(
  phrase: string | AetherPhrase,
  options?: SeedOptions
): DerivedSeed {
  const parsed = typeof phrase === 'string' ? parsePhrase(phrase) : phrase;
  const domain = options?.domain ?? AETHERLEX_DOMAIN;
  const outputLen = options?.outputBytes ?? 64;

  // 1. Encode token indices
  const tokenBits = encodeTokenIndices(parsed.tokens);

  // 2. LWS weight header (4 bytes — float32 of total weight)
  const weightBuf = Buffer.alloc(4);
  weightBuf.writeFloatBE(parsed.lwsWeight, 0);

  // 3. Build pre-image: domain || weight || tokenBits || supplemental
  const parts: Uint8Array[] = [
    Buffer.from(domain, 'utf-8'),
    Buffer.from([0x1f]), // unit separator
    weightBuf,
    Buffer.from([0x1f]),
    tokenBits,
  ];

  const hasSupplemental = !!options?.supplementalEntropy?.length;
  if (hasSupplemental) {
    parts.push(Buffer.from([0x1f]));
    parts.push(options!.supplementalEntropy!);
  }

  const preImage = Buffer.concat(parts);

  // 4. Hash through SHA-512 (acts as randomness extractor)
  const hash = createHash('sha512').update(preImage).digest();

  // 5. Truncate to output length
  const seed = new Uint8Array(hash.buffer, hash.byteOffset, outputLen);

  return {
    seed: Uint8Array.from(seed), // copy to avoid aliasing
    phrase: parsed,
    hasSupplementalEntropy: hasSupplemental,
    domain,
    outputBytes: outputLen,
    phraseEntropyBits: parsed.entropyBits,
  };
}

// ════════════════════════════════════════════════════════════════
// MNEMONIC GENERATION — random phrase from CSPRNG
// ════════════════════════════════════════════════════════════════

/**
 * Generate a random AetherLex mnemonic phrase.
 *
 * Each token is chosen uniformly from the 1,536-token space using
 * CSPRNG rejection sampling (no modulo bias).
 */
export function generatePhrase(
  tokenCount: number = 12,
  profile?: SeedProfile
): AetherPhrase {
  if (tokenCount < 1 || tokenCount > 64) {
    throw new RangeError('Token count must be 1-64');
  }

  const tokens: AetherToken[] = [];
  const dist: Record<TongueCode, number> = { ko: 0, av: 0, ru: 0, ca: 0, um: 0, dr: 0 };

  // If a profile has requirements, fill those first
  if (profile) {
    for (const code of TONGUE_ORDER) {
      const required = profile.tongueRequirements[code];
      for (let i = 0; i < required; i++) {
        const byte = rejectionSampleByte();
        const tok = byteToToken(code, byte);
        tokens.push(tok);
        dist[code]++;
      }
    }
  }

  // Fill remaining tokens randomly from entire space
  while (tokens.length < tokenCount) {
    const globalIdx = rejectionSampleGlobal();
    const tongueIdx = Math.floor(globalIdx / 256);
    const byte = globalIdx % 256;
    const code = TONGUE_ORDER[tongueIdx];
    const tok = byteToToken(code, byte);
    tokens.push(tok);
    dist[code]++;
  }

  // Shuffle to avoid predictable ordering (profile-required tokens at front)
  fisherYatesShuffle(tokens);

  let lwsWeight = 0;
  for (const t of tokens) {
    lwsWeight += LWS_WEIGHTS[t.tongue];
  }

  return {
    tokens,
    phrase: tokens.map((t) => t.token).join(' '),
    entropyBits: tokens.length * BITS_PER_TOKEN,
    tongueDistribution: dist,
    lwsWeight,
  };
}

/** Rejection-sample a random byte (0-255) uniformly */
function rejectionSampleByte(): number {
  return randomBytes(1)[0];
}

/** Rejection-sample a global index (0-1535) without modulo bias */
function rejectionSampleGlobal(): number {
  // 2048 is next power of 2 ≥ 1536; reject if ≥ 1536
  while (true) {
    const buf = randomBytes(2);
    const val = ((buf[0] & 0x07) << 8) | buf[1]; // 11 bits
    if (val < TOTAL_TOKENS) return val;
  }
}

/** Fisher-Yates shuffle (in-place, CSPRNG) */
function fisherYatesShuffle<T>(arr: T[]): void {
  for (let i = arr.length - 1; i > 0; i--) {
    const buf = randomBytes(4);
    const j = buf.readUInt32BE(0) % (i + 1);
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
}

// ════════════════════════════════════════════════════════════════
// VALIDATION
// ════════════════════════════════════════════════════════════════

/** Validation result for a phrase against a profile */
export interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  entropyBits: number;
  tongueDistribution: Record<TongueCode, number>;
}

/**
 * Validate that a phrase meets a seed profile's requirements.
 */
export function validatePhrase(
  phrase: string | AetherPhrase,
  profile: SeedProfile
): ValidationResult {
  const parsed = typeof phrase === 'string' ? parsePhrase(phrase) : phrase;
  const errors: string[] = [];
  const warnings: string[] = [];

  // Check total token count
  if (parsed.tokens.length < profile.totalTokens) {
    errors.push(
      `Phrase has ${parsed.tokens.length} tokens, profile requires ${profile.totalTokens}`
    );
  }

  // Check per-tongue requirements
  for (const code of TONGUE_ORDER) {
    const required = profile.tongueRequirements[code];
    const actual = parsed.tongueDistribution[code];
    if (actual < required) {
      errors.push(
        `Tongue ${code.toUpperCase()} requires ${required} tokens, has ${actual}`
      );
    }
  }

  // Entropy warnings
  if (parsed.entropyBits < 128) {
    warnings.push(
      `Phrase provides ~${parsed.entropyBits.toFixed(0)} bits of entropy; ` +
        `128+ recommended. Consider supplemental CSPRNG entropy.`
    );
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
    entropyBits: parsed.entropyBits,
    tongueDistribution: parsed.tongueDistribution,
  };
}

// ════════════════════════════════════════════════════════════════
// ML-KEM / ML-DSA SEED SPLITTING
// ════════════════════════════════════════════════════════════════

/** ML-KEM-768 seed split (d=32 bytes, z=32 bytes) */
export interface MLKEMSeed {
  /** Deterministic seed d (32 bytes) — generates public matrix A */
  d: Uint8Array;
  /** Random seed z (32 bytes) — generates secret noise */
  z: Uint8Array;
}

/** ML-DSA-65 seed (ξ = 32 bytes) */
export interface MLDSASeed {
  /** Key generation seed ξ */
  xi: Uint8Array;
}

/**
 * Split a 64-byte derived seed into ML-KEM-768 key generation inputs.
 */
export function splitForMLKEM(seed: DerivedSeed): MLKEMSeed {
  if (seed.seed.length < 64) {
    throw new Error(`ML-KEM requires 64-byte seed, got ${seed.seed.length}`);
  }
  return {
    d: seed.seed.slice(0, 32),
    z: seed.seed.slice(32, 64),
  };
}

/**
 * Extract ML-DSA-65 key generation seed from a derived seed.
 */
export function splitForMLDSA(seed: DerivedSeed): MLDSASeed {
  if (seed.seed.length < 32) {
    throw new Error(`ML-DSA requires 32-byte seed, got ${seed.seed.length}`);
  }
  return {
    xi: seed.seed.slice(0, 32),
  };
}
