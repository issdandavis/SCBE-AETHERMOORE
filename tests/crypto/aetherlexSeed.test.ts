/**
 * @file aetherlexSeed.test.ts
 * @module tests/crypto/aetherlexSeed
 *
 * Tests for AetherLex Seed v1.0 — Sacred Tongue mnemonic seed generation.
 *
 * Coverage:
 *   A - Token indexing (byte↔token, global index)
 *   B - Phrase parsing
 *   C - Seed derivation (determinism, domain separation)
 *   D - Profile validation
 *   E - Random phrase generation
 *   F - ML-KEM / ML-DSA seed splitting
 *   G - Entropy and security properties
 *   H - Edge cases and error handling
 *   I - LWS / PHDM weights
 *   J - Cross-tongue token resolution
 */

import { describe, it, expect } from 'vitest';
import {
  byteToToken,
  tokenToAether,
  parsePhrase,
  deriveSeed,
  generatePhrase,
  validatePhrase,
  encodeTokenIndices,
  splitForMLKEM,
  splitForMLDSA,
  TONGUE_ORDER,
  TOTAL_TOKENS,
  BITS_PER_TOKEN,
  LWS_WEIGHTS,
  PHDM_WEIGHTS,
  AETHERLEX_DOMAIN,
  PROFILE_FORGE,
  PROFILE_VEIL,
  PROFILE_EVERWEAVE,
  PROFILE_FLOW,
  SEED_PROFILES,
  type AetherToken,
  type TongueCode,
} from '../../src/crypto/aetherlex-seed.js';

// ═══════════════════════════════════════════════════════════════
// A — Token Indexing
// ═══════════════════════════════════════════════════════════════

describe('A – Token Indexing', () => {
  it('A1: byteToToken encodes byte 0x00 in KO correctly', () => {
    const t = byteToToken('ko', 0x00);
    expect(t.tongue).toBe('ko');
    expect(t.prefixIndex).toBe(0);
    expect(t.suffixIndex).toBe(0);
    expect(t.byteValue).toBe(0);
    expect(t.globalIndex).toBe(0);
    expect(t.token).toMatch(/'/); // has apostrophe
  });

  it('A2: byteToToken encodes byte 0xFF in KO correctly', () => {
    const t = byteToToken('ko', 0xff);
    expect(t.prefixIndex).toBe(15);
    expect(t.suffixIndex).toBe(15);
    expect(t.byteValue).toBe(255);
    expect(t.globalIndex).toBe(255);
  });

  it('A3: byteToToken encodes byte 0x00 in DR at correct global offset', () => {
    const t = byteToToken('dr', 0x00);
    expect(t.globalIndex).toBe(1280); // 5 * 256
  });

  it('A4: all 256 tokens per tongue are unique', () => {
    for (const code of TONGUE_ORDER) {
      const tokens = new Set<string>();
      for (let b = 0; b < 256; b++) {
        const t = byteToToken(code, b);
        tokens.add(t.token);
      }
      expect(tokens.size).toBe(256);
    }
  });

  it('A5: global index space is contiguous [0, 1535]', () => {
    const indices = new Set<number>();
    for (const code of TONGUE_ORDER) {
      for (let b = 0; b < 256; b++) {
        indices.add(byteToToken(code, b).globalIndex);
      }
    }
    expect(indices.size).toBe(TOTAL_TOKENS);
    expect(Math.min(...indices)).toBe(0);
    expect(Math.max(...indices)).toBe(1535);
  });

  it('A6: byteToToken rejects out-of-range bytes', () => {
    expect(() => byteToToken('ko', -1)).toThrow();
    expect(() => byteToToken('ko', 256)).toThrow();
  });

  it('A7: tokenToAether round-trips with byteToToken', () => {
    for (const code of TONGUE_ORDER) {
      for (let b = 0; b < 256; b++) {
        const encoded = byteToToken(code, b);
        const decoded = tokenToAether(encoded.token, code);
        expect(decoded.globalIndex).toBe(encoded.globalIndex);
        expect(decoded.byteValue).toBe(b);
      }
    }
  });

  it('A8: tokenToAether without tongue hint finds the right tongue', () => {
    const t = byteToToken('ca', 0x42);
    const decoded = tokenToAether(t.token);
    expect(decoded.tongue).toBe('ca');
    expect(decoded.byteValue).toBe(0x42);
  });

  it('A9: tokenToAether rejects malformed tokens', () => {
    expect(() => tokenToAether('notavalidtoken')).toThrow(/Invalid token format/);
    expect(() => tokenToAether('fake\'nonexistent')).toThrow(/not found/);
  });
});

// ═══════════════════════════════════════════════════════════════
// B — Phrase Parsing
// ═══════════════════════════════════════════════════════════════

describe('B – Phrase Parsing', () => {
  it('B1: parsePhrase parses a multi-tongue phrase', () => {
    // One token from each tongue
    const ko = byteToToken('ko', 0x00).token;
    const av = byteToToken('av', 0x00).token;
    const ru = byteToToken('ru', 0x00).token;
    const ca = byteToToken('ca', 0x00).token;
    const um = byteToToken('um', 0x00).token;
    const dr = byteToToken('dr', 0x00).token;

    const phrase = parsePhrase(`${ko} ${av} ${ru} ${ca} ${um} ${dr}`);
    expect(phrase.tokens.length).toBe(6);
    expect(phrase.tongueDistribution.ko).toBe(1);
    expect(phrase.tongueDistribution.av).toBe(1);
    expect(phrase.tongueDistribution.ru).toBe(1);
    expect(phrase.tongueDistribution.ca).toBe(1);
    expect(phrase.tongueDistribution.um).toBe(1);
    expect(phrase.tongueDistribution.dr).toBe(1);
  });

  it('B2: entropyBits scales with token count', () => {
    const tok = byteToToken('ko', 0x00).token;
    const p6 = parsePhrase(Array(6).fill(tok).join(' '));
    const p12 = parsePhrase(Array(12).fill(tok).join(' '));

    expect(p12.entropyBits).toBeCloseTo(p6.entropyBits * 2, 1);
    expect(p12.entropyBits).toBeCloseTo(12 * BITS_PER_TOKEN, 1);
  });

  it('B3: lwsWeight sums per-tongue weights', () => {
    const ko = byteToToken('ko', 0x00).token;
    const dr = byteToToken('dr', 0x00).token;

    const phrase = parsePhrase(`${ko} ${dr}`);
    expect(phrase.lwsWeight).toBeCloseTo(LWS_WEIGHTS.ko + LWS_WEIGHTS.dr, 3);
  });

  it('B4: parsePhrase rejects empty string', () => {
    expect(() => parsePhrase('')).toThrow();
  });

  it('B5: parsePhrase handles extra whitespace', () => {
    const tok = byteToToken('ko', 0x00).token;
    const phrase = parsePhrase(`  ${tok}   ${tok}  `);
    expect(phrase.tokens.length).toBe(2);
  });
});

// ═══════════════════════════════════════════════════════════════
// C — Seed Derivation
// ═══════════════════════════════════════════════════════════════

describe('C – Seed Derivation', () => {
  const makePhrase = () => {
    return Array.from({ length: 12 }, (_, i) => {
      const code = TONGUE_ORDER[i % 6];
      return byteToToken(code, i * 20).token;
    }).join(' ');
  };

  it('C1: deriveSeed is deterministic for same phrase', () => {
    const phrase = makePhrase();
    const a = deriveSeed(phrase);
    const b = deriveSeed(phrase);
    expect(Buffer.from(a.seed)).toEqual(Buffer.from(b.seed));
  });

  it('C2: different phrases produce different seeds', () => {
    const a = deriveSeed(makePhrase());
    const phrase2 = Array.from({ length: 12 }, (_, i) => {
      const code = TONGUE_ORDER[i % 6];
      return byteToToken(code, i * 20 + 1).token;
    }).join(' ');
    const b = deriveSeed(phrase2);
    expect(Buffer.from(a.seed)).not.toEqual(Buffer.from(b.seed));
  });

  it('C3: default output is 64 bytes', () => {
    const result = deriveSeed(makePhrase());
    expect(result.seed.length).toBe(64);
    expect(result.outputBytes).toBe(64);
  });

  it('C4: custom output length works', () => {
    const result = deriveSeed(makePhrase(), { outputBytes: 32 });
    expect(result.seed.length).toBe(32);
  });

  it('C5: supplemental entropy changes the seed', () => {
    const phrase = makePhrase();
    const a = deriveSeed(phrase);
    const b = deriveSeed(phrase, {
      supplementalEntropy: new Uint8Array(32).fill(0xff),
    });
    expect(Buffer.from(a.seed)).not.toEqual(Buffer.from(b.seed));
    expect(b.hasSupplementalEntropy).toBe(true);
    expect(a.hasSupplementalEntropy).toBe(false);
  });

  it('C6: domain separation tag changes the seed', () => {
    const phrase = makePhrase();
    const a = deriveSeed(phrase, { domain: 'DOMAIN-A' });
    const b = deriveSeed(phrase, { domain: 'DOMAIN-B' });
    expect(Buffer.from(a.seed)).not.toEqual(Buffer.from(b.seed));
  });

  it('C7: default domain is AETHERLEX_DOMAIN', () => {
    const result = deriveSeed(makePhrase());
    expect(result.domain).toBe(AETHERLEX_DOMAIN);
  });

  it('C8: deriveSeed accepts AetherPhrase object', () => {
    const phrase = parsePhrase(makePhrase());
    const result = deriveSeed(phrase);
    expect(result.seed.length).toBe(64);
  });

  it('C9: entropyBits is recorded in result', () => {
    const result = deriveSeed(makePhrase());
    expect(result.phraseEntropyBits).toBeCloseTo(12 * BITS_PER_TOKEN, 1);
  });
});

// ═══════════════════════════════════════════════════════════════
// D — Profile Validation
// ═══════════════════════════════════════════════════════════════

describe('D – Profile Validation', () => {
  const makeForgePhrase = () => {
    const tokens = [
      ...Array(3).fill(null).map((_, i) => byteToToken('ru', i).token),
      ...Array(3).fill(null).map((_, i) => byteToToken('um', i).token),
      ...Array(3).fill(null).map((_, i) => byteToToken('dr', i).token),
      ...Array(3).fill(null).map((_, i) => byteToToken('ko', i).token),
    ];
    return tokens.join(' ');
  };

  it('D1: forge-grade phrase validates successfully', () => {
    const result = validatePhrase(makeForgePhrase(), PROFILE_FORGE);
    expect(result.valid).toBe(true);
    expect(result.errors.length).toBe(0);
  });

  it('D2: insufficient tokens fail validation', () => {
    const shortPhrase = byteToToken('ko', 0).token;
    const result = validatePhrase(shortPhrase, PROFILE_FORGE);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.includes('tokens'))).toBe(true);
  });

  it('D3: missing required tongue fails validation', () => {
    // Forge requires RU, UM, DR but we provide only KO
    const allKo = Array(12)
      .fill(null)
      .map((_, i) => byteToToken('ko', i).token)
      .join(' ');
    const result = validatePhrase(allKo, PROFILE_FORGE);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => /RU/.test(e))).toBe(true);
  });

  it('D4: low entropy generates warning', () => {
    const shortPhrase = Array(4)
      .fill(null)
      .map((_, i) => byteToToken('ko', i).token)
      .join(' ');
    const result = validatePhrase(shortPhrase, PROFILE_FLOW);
    expect(result.warnings.some((w) => /entropy/i.test(w))).toBe(true);
  });

  it('D5: everweave-root requires 2 of each tongue', () => {
    // Build a phrase with exactly 2 of each
    const tokens = TONGUE_ORDER.flatMap((code) => [
      byteToToken(code, 0).token,
      byteToToken(code, 1).token,
    ]);
    const result = validatePhrase(tokens.join(' '), PROFILE_EVERWEAVE);
    expect(result.valid).toBe(true);
  });

  it('D6: all profiles are in SEED_PROFILES', () => {
    expect(SEED_PROFILES['forge-grade']).toBe(PROFILE_FORGE);
    expect(SEED_PROFILES['veil-grade']).toBe(PROFILE_VEIL);
    expect(SEED_PROFILES['everweave-root']).toBe(PROFILE_EVERWEAVE);
    expect(SEED_PROFILES['flow-grade']).toBe(PROFILE_FLOW);
  });
});

// ═══════════════════════════════════════════════════════════════
// E — Random Phrase Generation
// ═══════════════════════════════════════════════════════════════

describe('E – Random Phrase Generation', () => {
  it('E1: generates correct token count', () => {
    const phrase = generatePhrase(12);
    expect(phrase.tokens.length).toBe(12);
  });

  it('E2: generated tokens are valid AetherTokens', () => {
    const phrase = generatePhrase(8);
    for (const t of phrase.tokens) {
      expect(t.globalIndex).toBeGreaterThanOrEqual(0);
      expect(t.globalIndex).toBeLessThan(TOTAL_TOKENS);
      expect(t.token).toContain("'");
      // Verify round-trip
      const decoded = tokenToAether(t.token, t.tongue);
      expect(decoded.globalIndex).toBe(t.globalIndex);
    }
  });

  it('E3: two random phrases are different (with overwhelming probability)', () => {
    const a = generatePhrase(12);
    const b = generatePhrase(12);
    // The probability of collision is (1/1536)^12 ≈ 0
    expect(a.phrase).not.toBe(b.phrase);
  });

  it('E4: profile-constrained generation meets requirements', () => {
    const phrase = generatePhrase(12, PROFILE_FORGE);
    const validation = validatePhrase(phrase, PROFILE_FORGE);
    expect(validation.valid).toBe(true);
  });

  it('E5: everweave profile gets 2 of each tongue', () => {
    const phrase = generatePhrase(12, PROFILE_EVERWEAVE);
    for (const code of TONGUE_ORDER) {
      expect(phrase.tongueDistribution[code]).toBeGreaterThanOrEqual(2);
    }
  });

  it('E6: rejects token count out of range', () => {
    expect(() => generatePhrase(0)).toThrow();
    expect(() => generatePhrase(65)).toThrow();
  });

  it('E7: entropy bits match token count', () => {
    const phrase = generatePhrase(12);
    expect(phrase.entropyBits).toBeCloseTo(12 * BITS_PER_TOKEN, 1);
  });

  it('E8: LWS weight is populated', () => {
    const phrase = generatePhrase(6);
    expect(phrase.lwsWeight).toBeGreaterThan(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// F — ML-KEM / ML-DSA Seed Splitting
// ═══════════════════════════════════════════════════════════════

describe('F – ML-KEM / ML-DSA Seed Splitting', () => {
  const makePhrase = () =>
    Array.from({ length: 12 }, (_, i) =>
      byteToToken(TONGUE_ORDER[i % 6], i * 20).token
    ).join(' ');

  it('F1: splitForMLKEM returns d (32 bytes) and z (32 bytes)', () => {
    const seed = deriveSeed(makePhrase(), { outputBytes: 64 });
    const { d, z } = splitForMLKEM(seed);
    expect(d.length).toBe(32);
    expect(z.length).toBe(32);
  });

  it('F2: d and z are different halves of the seed', () => {
    const seed = deriveSeed(makePhrase(), { outputBytes: 64 });
    const { d, z } = splitForMLKEM(seed);
    expect(Buffer.from(d)).not.toEqual(Buffer.from(z));
  });

  it('F3: splitForMLDSA returns xi (32 bytes)', () => {
    const seed = deriveSeed(makePhrase(), { outputBytes: 32 });
    const { xi } = splitForMLDSA(seed);
    expect(xi.length).toBe(32);
  });

  it('F4: splitForMLKEM rejects short seeds', () => {
    const seed = deriveSeed(makePhrase(), { outputBytes: 32 });
    expect(() => splitForMLKEM(seed)).toThrow(/64-byte/);
  });

  it('F5: splitForMLDSA rejects very short seeds', () => {
    const seed = deriveSeed(makePhrase(), { outputBytes: 16 });
    expect(() => splitForMLDSA(seed)).toThrow(/32-byte/);
  });

  it('F6: deterministic — same phrase → same KEM seed', () => {
    const phrase = makePhrase();
    const a = splitForMLKEM(deriveSeed(phrase));
    const b = splitForMLKEM(deriveSeed(phrase));
    expect(Buffer.from(a.d)).toEqual(Buffer.from(b.d));
    expect(Buffer.from(a.z)).toEqual(Buffer.from(b.z));
  });
});

// ═══════════════════════════════════════════════════════════════
// G — Entropy and Security Properties
// ═══════════════════════════════════════════════════════════════

describe('G – Entropy & Security', () => {
  it('G1: 13-token phrase exceeds 128 bits of entropy (12 tokens ≈ 127 bits)', () => {
    // 12 tokens × 10.585 bits = ~127 bits (just under 128)
    // 13 tokens × 10.585 bits = ~137 bits (safely above 128)
    expect(12 * BITS_PER_TOKEN).toBeCloseTo(127, 0);
    expect(13 * BITS_PER_TOKEN).toBeGreaterThan(128);
  });

  it('G2: TOTAL_TOKENS is 1536', () => {
    expect(TOTAL_TOKENS).toBe(1536);
  });

  it('G3: BITS_PER_TOKEN ≈ 10.58', () => {
    expect(BITS_PER_TOKEN).toBeCloseTo(10.585, 2);
  });

  it('G4: seed bytes have reasonable distribution', () => {
    // Generate 100 seeds and check byte distribution isn't degenerate
    const counts = new Uint32Array(256);
    for (let i = 0; i < 100; i++) {
      const phrase = generatePhrase(12);
      const seed = deriveSeed(phrase);
      for (const b of seed.seed) {
        counts[b]++;
      }
    }
    // With 100 × 64 = 6400 bytes, expect ~25 per bucket on average
    // Check no bucket has 0 (extremely unlikely if distribution is good)
    const nonZero = [...counts].filter((c) => c > 0).length;
    expect(nonZero).toBeGreaterThan(200); // at least 200 of 256 buckets hit
  });

  it('G5: encodeTokenIndices packs 11 bits per token', () => {
    const tokens: AetherToken[] = [
      byteToToken('ko', 0),    // global 0
      byteToToken('dr', 255),  // global 1535
    ];
    const bits = encodeTokenIndices(tokens);
    // 2 tokens × 11 bits = 22 bits = 3 bytes
    expect(bits.length).toBe(3);
  });

  it('G6: domain separation prevents cross-protocol seed reuse', () => {
    const phrase = generatePhrase(12);
    const a = deriveSeed(phrase, { domain: 'PROTOCOL-A' });
    const b = deriveSeed(phrase, { domain: 'PROTOCOL-B' });
    expect(Buffer.from(a.seed)).not.toEqual(Buffer.from(b.seed));
  });
});

// ═══════════════════════════════════════════════════════════════
// H — Edge Cases
// ═══════════════════════════════════════════════════════════════

describe('H – Edge Cases', () => {
  it('H1: single-token phrase works', () => {
    const tok = byteToToken('ko', 42).token;
    const seed = deriveSeed(tok);
    expect(seed.seed.length).toBe(64);
    expect(seed.phrase.tokens.length).toBe(1);
  });

  it('H2: max token count (64) works', () => {
    const phrase = generatePhrase(64);
    expect(phrase.tokens.length).toBe(64);
    const seed = deriveSeed(phrase);
    expect(seed.seed.length).toBe(64);
  });

  it('H3: all same tongue works', () => {
    const phrase = Array(12)
      .fill(null)
      .map((_, i) => byteToToken('ru', i).token)
      .join(' ');
    const seed = deriveSeed(phrase);
    expect(seed.seed.length).toBe(64);
  });

  it('H4: all same token works (low entropy but valid)', () => {
    const tok = byteToToken('ko', 0).token;
    const phrase = Array(12).fill(tok).join(' ');
    const seed = deriveSeed(phrase);
    expect(seed.seed.length).toBe(64);
  });
});

// ═══════════════════════════════════════════════════════════════
// I — LWS and PHDM Weights
// ═══════════════════════════════════════════════════════════════

describe('I – Weight Systems', () => {
  it('I1: LWS weights are monotonically increasing', () => {
    const vals = TONGUE_ORDER.map((c) => LWS_WEIGHTS[c]);
    for (let i = 1; i < vals.length; i++) {
      expect(vals[i]).toBeGreaterThan(vals[i - 1]);
    }
  });

  it('I2: PHDM weights follow φⁿ progression', () => {
    const phi = (1 + Math.sqrt(5)) / 2;
    for (let i = 0; i < TONGUE_ORDER.length; i++) {
      expect(PHDM_WEIGHTS[TONGUE_ORDER[i]]).toBeCloseTo(phi ** i, 2);
    }
  });

  it('I3: LWS KO = 1.0, DR = 1.667', () => {
    expect(LWS_WEIGHTS.ko).toBe(1.0);
    expect(LWS_WEIGHTS.dr).toBeCloseTo(1.667, 3);
  });

  it('I4: PHDM DR ≈ 11.09', () => {
    expect(PHDM_WEIGHTS.dr).toBeCloseTo(11.09, 1);
  });
});

// ═══════════════════════════════════════════════════════════════
// J — Cross-Tongue Resolution
// ═══════════════════════════════════════════════════════════════

describe('J – Cross-Tongue Resolution', () => {
  it('J1: tokenToAether resolves tongue from token alone', () => {
    // Draumric token should resolve to DR
    const drToken = byteToToken('dr', 0x10);
    const resolved = tokenToAether(drToken.token);
    expect(resolved.tongue).toBe('dr');
  });

  it('J2: tongue hint speeds up resolution', () => {
    const token = byteToToken('ca', 0x55);
    const resolved = tokenToAether(token.token, 'ca');
    expect(resolved.tongue).toBe('ca');
    expect(resolved.byteValue).toBe(0x55);
  });

  it('J3: wrong tongue hint falls through (only searches given tongue)', () => {
    const drToken = byteToToken('dr', 0x10);
    // DR token won't be found in KO
    expect(() => tokenToAether(drToken.token, 'ko')).toThrow(/not found/);
  });

  it('J4: TONGUE_ORDER has exactly 6 entries', () => {
    expect(TONGUE_ORDER.length).toBe(6);
    expect(TONGUE_ORDER).toEqual(['ko', 'av', 'ru', 'ca', 'um', 'dr']);
  });
});
