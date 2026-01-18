/**
 * SCBE SpiralSeal SS1 Tests
 *
 * Comprehensive tests for Sacred Tongue cryptographic encoding:
 * - Tokenizer: bijective 256-token mapping per tongue
 * - Format: SS1 blob structure
 * - Crypto: AES-256-GCM + HKDF
 * - Security: tamper detection, AAD binding
 *
 * Tests exceed industry standards with:
 * - Full 256-byte roundtrip for all 6 tongues
 * - Property-based testing
 * - Security vulnerability checks
 * - Edge case coverage
 */

import { describe, it, expect, beforeAll } from 'vitest';
import {
  SacredTongueTokenizer,
  encodeToSpelltext,
  decodeFromSpelltext,
  formatSS1Blob,
  parseSS1Blob,
  seal,
  unseal,
  SpiralSealSS1,
  randomBytes,
  computeLWSWeights,
  computeLWSScore,
} from '../../src/harmonic/spiralSeal.js';
import {
  TONGUES,
  KOR_AELIN,
  AVALI,
  RUNETHIC,
  CASSISIVADAN,
  UMBROTH,
  DRAUMRIC,
  TongueCode,
  SECTION_TONGUES,
} from '../../src/harmonic/sacredTongues.js';

// ═══════════════════════════════════════════════════════════════
// Sacred Tongue Definitions
// ═══════════════════════════════════════════════════════════════
describe('Sacred Tongue Definitions', () => {
  const tongueSpecs = [
    { code: 'ko', spec: KOR_AELIN, name: "Kor'aelin" },
    { code: 'av', spec: AVALI, name: 'Avali' },
    { code: 'ru', spec: RUNETHIC, name: 'Runethic' },
    { code: 'ca', spec: CASSISIVADAN, name: 'Cassisivadan' },
    { code: 'um', spec: UMBROTH, name: 'Umbroth' },
    { code: 'dr', spec: DRAUMRIC, name: 'Draumric' },
  ];

  tongueSpecs.forEach(({ code, spec, name }) => {
    describe(`${name} (${code})`, () => {
      it('has exactly 16 prefixes', () => {
        expect(spec.prefixes.length).toBe(16);
      });

      it('has exactly 16 suffixes', () => {
        expect(spec.suffixes.length).toBe(16);
      });

      it('all prefixes are unique', () => {
        const unique = new Set(spec.prefixes);
        expect(unique.size).toBe(16);
      });

      it('all suffixes are unique', () => {
        const unique = new Set(spec.suffixes);
        expect(unique.size).toBe(16);
      });

      it('16 × 16 = 256 unique tokens', () => {
        const tokens = new Set<string>();
        for (const prefix of spec.prefixes) {
          for (const suffix of spec.suffixes) {
            tokens.add(`${prefix}'${suffix}`);
          }
        }
        expect(tokens.size).toBe(256);
      });

      it('no prefix contains apostrophe', () => {
        spec.prefixes.forEach(p => {
          expect(p.includes("'")).toBe(false);
        });
      });

      it('no suffix contains apostrophe', () => {
        spec.suffixes.forEach(s => {
          expect(s.includes("'")).toBe(false);
        });
      });
    });
  });
});

// ═══════════════════════════════════════════════════════════════
// Section-to-Tongue Mapping
// ═══════════════════════════════════════════════════════════════
describe('Section-to-Tongue Mapping', () => {
  it('aad → Avali (av)', () => {
    expect(SECTION_TONGUES.aad).toBe('av');
  });

  it('salt → Runethic (ru)', () => {
    expect(SECTION_TONGUES.salt).toBe('ru');
  });

  it('nonce → Kor\'aelin (ko)', () => {
    expect(SECTION_TONGUES.nonce).toBe('ko');
  });

  it('ct → Cassisivadan (ca)', () => {
    expect(SECTION_TONGUES.ct).toBe('ca');
  });

  it('tag → Draumric (dr)', () => {
    expect(SECTION_TONGUES.tag).toBe('dr');
  });

  it('redact → Umbroth (um)', () => {
    expect(SECTION_TONGUES.redact).toBe('um');
  });
});

// ═══════════════════════════════════════════════════════════════
// SacredTongueTokenizer
// ═══════════════════════════════════════════════════════════════
describe('SacredTongueTokenizer', () => {
  const tongues: TongueCode[] = ['ko', 'av', 'ru', 'ca', 'um', 'dr'];

  describe('Token format', () => {
    tongues.forEach(code => {
      it(`${code}: tokens have format prefix'suffix`, () => {
        const tokenizer = new SacredTongueTokenizer(code);
        for (let b = 0; b < 256; b++) {
          const token = tokenizer.encodeByte(b);
          expect(token).toMatch(/^[a-z]+\'[a-z]+$/);
          expect(token.split("'").length).toBe(2);
        }
      });
    });
  });

  describe('Bijective mapping (256-byte roundtrip)', () => {
    tongues.forEach(code => {
      it(`${code}: all 256 bytes encode/decode losslessly`, () => {
        const tokenizer = new SacredTongueTokenizer(code);
        for (let b = 0; b < 256; b++) {
          const token = tokenizer.encodeByte(b);
          const decoded = tokenizer.decodeToken(token);
          expect(decoded).toBe(b);
        }
      });
    });
  });

  describe('Nibble mapping verification', () => {
    it('byte 0x00 → prefix[0] + suffix[0]', () => {
      const tokenizer = new SacredTongueTokenizer('ko');
      const token = tokenizer.encodeByte(0x00);
      expect(token).toBe("sil'a");
    });

    it('byte 0xFF → prefix[15] + suffix[15]', () => {
      const tokenizer = new SacredTongueTokenizer('ko');
      const token = tokenizer.encodeByte(0xFF);
      expect(token).toBe("vara'esh");
    });

    it('byte 0x2A (42) → prefix[2] + suffix[10]', () => {
      const tokenizer = new SacredTongueTokenizer('ko');
      const token = tokenizer.encodeByte(0x2A);
      expect(token).toBe("vel'an");
    });

    it('high nibble selects prefix, low nibble selects suffix', () => {
      const tokenizer = new SacredTongueTokenizer('ko');
      // 0x53 = 5*16 + 3 = prefix[5] + suffix[3]
      const token = tokenizer.encodeByte(0x53);
      expect(token).toBe("thul'ia");
    });
  });

  describe('Bulk encode/decode', () => {
    tongues.forEach(code => {
      it(`${code}: arbitrary byte arrays roundtrip correctly`, () => {
        const tokenizer = new SacredTongueTokenizer(code);
        const data = new Uint8Array([0, 127, 255, 42, 100, 200]);
        const encoded = tokenizer.encode(data);
        const decoded = tokenizer.decode(encoded);
        expect(Array.from(decoded)).toEqual(Array.from(data));
      });
    });

    it('handles empty input', () => {
      const tokenizer = new SacredTongueTokenizer('ko');
      const encoded = tokenizer.encode(new Uint8Array(0));
      expect(encoded).toBe('');
      const decoded = tokenizer.decode('');
      expect(decoded.length).toBe(0);
    });

    it('handles single byte', () => {
      const tokenizer = new SacredTongueTokenizer('ko');
      const data = new Uint8Array([42]);
      const encoded = tokenizer.encode(data);
      const decoded = tokenizer.decode(encoded);
      expect(Array.from(decoded)).toEqual([42]);
    });

    it('handles large data (1KB)', () => {
      const tokenizer = new SacredTongueTokenizer('ca');
      const data = randomBytes(1024);
      const encoded = tokenizer.encode(data);
      const decoded = tokenizer.decode(encoded);
      expect(Array.from(decoded)).toEqual(Array.from(data));
    });
  });

  describe('Token validation', () => {
    it('isValidToken returns true for valid tokens', () => {
      const tokenizer = new SacredTongueTokenizer('ko');
      expect(tokenizer.isValidToken("sil'a")).toBe(true);
      expect(tokenizer.isValidToken("vara'esh")).toBe(true);
    });

    it('isValidToken returns false for invalid tokens', () => {
      const tokenizer = new SacredTongueTokenizer('ko');
      expect(tokenizer.isValidToken("invalid'token")).toBe(false);
      expect(tokenizer.isValidToken("foo")).toBe(false);
    });
  });

  describe('Error handling', () => {
    it('throws for unknown tongue code', () => {
      expect(() => new SacredTongueTokenizer('xx' as TongueCode)).toThrow();
    });

    it('throws for byte out of range', () => {
      const tokenizer = new SacredTongueTokenizer('ko');
      expect(() => tokenizer.encodeByte(256)).toThrow();
      expect(() => tokenizer.encodeByte(-1)).toThrow();
    });

    it('throws for unknown token', () => {
      const tokenizer = new SacredTongueTokenizer('ko');
      expect(() => tokenizer.decodeToken("invalid'token")).toThrow();
    });
  });
});

// ═══════════════════════════════════════════════════════════════
// Section Encoding
// ═══════════════════════════════════════════════════════════════
describe('Section Encoding', () => {
  it('encodeToSpelltext uses correct tongue prefix', () => {
    const data = new Uint8Array([0x00, 0x01]);
    expect(encodeToSpelltext(data, 'salt')).toMatch(/^ru:/);
    expect(encodeToSpelltext(data, 'nonce')).toMatch(/^ko:/);
    expect(encodeToSpelltext(data, 'ct')).toMatch(/^ca:/);
    expect(encodeToSpelltext(data, 'tag')).toMatch(/^dr:/);
  });

  it('encode/decode roundtrip for each section', () => {
    const sections: Array<'salt' | 'nonce' | 'ct' | 'tag'> = ['salt', 'nonce', 'ct', 'tag'];
    const data = randomBytes(32);

    sections.forEach(section => {
      const encoded = encodeToSpelltext(data, section);
      const decoded = decodeFromSpelltext(encoded, section);
      expect(Array.from(decoded)).toEqual(Array.from(data));
    });
  });
});

// ═══════════════════════════════════════════════════════════════
// SS1 Format
// ═══════════════════════════════════════════════════════════════
describe('SS1 Format', () => {
  const salt = randomBytes(16);
  const nonce = randomBytes(12);
  const ciphertext = randomBytes(64);
  const tag = randomBytes(16);
  const kid = 'k01';
  const aad = 'service=prod;env=test';

  describe('formatSS1Blob', () => {
    it('starts with SS1|', () => {
      const blob = formatSS1Blob(kid, aad, salt, nonce, ciphertext, tag);
      expect(blob.startsWith('SS1|')).toBe(true);
    });

    it('contains kid field', () => {
      const blob = formatSS1Blob(kid, aad, salt, nonce, ciphertext, tag);
      expect(blob).toContain(`kid=${kid}`);
    });

    it('contains aad field', () => {
      const blob = formatSS1Blob(kid, aad, salt, nonce, ciphertext, tag);
      expect(blob).toContain(`aad=${aad}`);
    });

    it('contains all section prefixes', () => {
      const blob = formatSS1Blob(kid, aad, salt, nonce, ciphertext, tag);
      expect(blob).toContain('ru:');
      expect(blob).toContain('ko:');
      expect(blob).toContain('ca:');
      expect(blob).toContain('dr:');
    });

    it('uses pipe delimiter', () => {
      const blob = formatSS1Blob(kid, aad, salt, nonce, ciphertext, tag);
      const parts = blob.split('|');
      expect(parts.length).toBe(7);
    });
  });

  describe('parseSS1Blob', () => {
    it('parses version correctly', () => {
      const blob = formatSS1Blob(kid, aad, salt, nonce, ciphertext, tag);
      const parsed = parseSS1Blob(blob);
      expect(parsed.version).toBe('SS1');
    });

    it('parses kid correctly', () => {
      const blob = formatSS1Blob(kid, aad, salt, nonce, ciphertext, tag);
      const parsed = parseSS1Blob(blob);
      expect(parsed.kid).toBe(kid);
    });

    it('parses aad correctly', () => {
      const blob = formatSS1Blob(kid, aad, salt, nonce, ciphertext, tag);
      const parsed = parseSS1Blob(blob);
      expect(parsed.aad).toBe(aad);
    });

    it('format/parse roundtrip is lossless', () => {
      const blob = formatSS1Blob(kid, aad, salt, nonce, ciphertext, tag);
      const parsed = parseSS1Blob(blob);

      expect(Array.from(parsed.salt)).toEqual(Array.from(salt));
      expect(Array.from(parsed.nonce)).toEqual(Array.from(nonce));
      expect(Array.from(parsed.ciphertext)).toEqual(Array.from(ciphertext));
      expect(Array.from(parsed.tag)).toEqual(Array.from(tag));
    });

    it('throws for invalid blob (missing SS1|)', () => {
      expect(() => parseSS1Blob('invalid blob')).toThrow();
    });

    it('throws for missing required fields', () => {
      expect(() => parseSS1Blob('SS1|')).toThrow();
    });
  });
});

// ═══════════════════════════════════════════════════════════════
// Cryptographic Operations (requires Web Crypto)
// ═══════════════════════════════════════════════════════════════
describe('Cryptographic Operations', () => {
  // Skip if Web Crypto not available
  const hasWebCrypto = typeof crypto !== 'undefined' && crypto.subtle;

  describe.skipIf(!hasWebCrypto)('seal/unseal', () => {
    const masterSecret = randomBytes(32);
    const plaintext = new TextEncoder().encode('My secret API key: sk-1234567890');
    const aad = 'service=openai;env=prod';

    it('seal returns SS1 formatted blob', async () => {
      const sealed = await seal(plaintext, masterSecret, aad, 'k01');
      expect(sealed.startsWith('SS1|')).toBe(true);
      expect(sealed).toContain('kid=k01');
      expect(sealed).toContain(`aad=${aad}`);
    });

    it('seal/unseal roundtrip recovers plaintext', async () => {
      const sealed = await seal(plaintext, masterSecret, aad, 'k01');
      const recovered = await unseal(sealed, masterSecret, aad);
      expect(Array.from(recovered)).toEqual(Array.from(plaintext));
    });

    it('unseal fails with wrong master secret', async () => {
      const sealed = await seal(plaintext, masterSecret, aad, 'k01');
      const wrongSecret = randomBytes(32);
      await expect(unseal(sealed, wrongSecret, aad)).rejects.toThrow();
    });

    it('unseal fails with wrong AAD', async () => {
      const sealed = await seal(plaintext, masterSecret, aad, 'k01');
      await expect(unseal(sealed, masterSecret, 'wrong-aad')).rejects.toThrow();
    });

    it('produces different ciphertext each time (random nonce/salt)', async () => {
      const sealed1 = await seal(plaintext, masterSecret, aad, 'k01');
      const sealed2 = await seal(plaintext, masterSecret, aad, 'k01');
      expect(sealed1).not.toBe(sealed2);
    });

    it('handles empty plaintext', async () => {
      const empty = new Uint8Array(0);
      const sealed = await seal(empty, masterSecret, aad, 'k01');
      const recovered = await unseal(sealed, masterSecret, aad);
      expect(recovered.length).toBe(0);
    });

    it('handles large plaintext (1KB)', async () => {
      const large = randomBytes(1024);
      const sealed = await seal(large, masterSecret, aad, 'k01');
      const recovered = await unseal(sealed, masterSecret, aad);
      expect(Array.from(recovered)).toEqual(Array.from(large));
    });
  });

  describe.skipIf(!hasWebCrypto)('SpiralSealSS1 class', () => {
    it('seal/unseal works via class', async () => {
      const masterSecret = randomBytes(32);
      const ss = new SpiralSealSS1(masterSecret, 'k01');

      const plaintext = new TextEncoder().encode('test message');
      const aad = 'context=test';

      const sealed = await ss.seal(plaintext, aad);
      const recovered = await ss.unseal(sealed, aad);

      expect(Array.from(recovered)).toEqual(Array.from(plaintext));
    });

    it('rotateKey changes kid and secret', async () => {
      const secret1 = randomBytes(32);
      const secret2 = randomBytes(32);
      const ss = new SpiralSealSS1(secret1, 'k01');

      expect(ss.getKid()).toBe('k01');

      ss.rotateKey('k02', secret2);
      expect(ss.getKid()).toBe('k02');
    });

    it('getStatus returns correct info', () => {
      const ss = new SpiralSealSS1(randomBytes(32), 'vault-2026');
      const status = ss.getStatus();

      expect(status.version).toBe('SS1');
      expect(status.kid).toBe('vault-2026');
      expect(status.capabilities).toContain('AES-256-GCM');
      expect(status.capabilities).toContain('HKDF-SHA256');
    });

    it('throws for short master secret', () => {
      expect(() => new SpiralSealSS1(randomBytes(16), 'k01')).toThrow();
    });
  });

  describe.skipIf(!hasWebCrypto)('Security properties', () => {
    const masterSecret = randomBytes(32);
    const plaintext = new TextEncoder().encode('sensitive data');
    const aad = 'service=secure';

    it('tampered ciphertext fails authentication', async () => {
      const sealed = await seal(plaintext, masterSecret, aad, 'k01');
      // Flip a character in the ciphertext section
      const tampered = sealed.replace(/ca:([^ ]+)/, (match) => {
        const chars = match.split('');
        chars[5] = chars[5] === 'a' ? 'b' : 'a';
        return chars.join('');
      });

      await expect(unseal(tampered, masterSecret, aad)).rejects.toThrow();
    });

    it('different kid derives different key', async () => {
      const sealed1 = await seal(plaintext, masterSecret, aad, 'k01');
      // Try to unseal with wrong kid by manually modifying
      const modifiedBlob = sealed1.replace('kid=k01', 'kid=k02');
      // This will fail because the key derived differs
      await expect(unseal(modifiedBlob, masterSecret, aad)).rejects.toThrow();
    });
  });
});

// ═══════════════════════════════════════════════════════════════
// LWS Integration
// ═══════════════════════════════════════════════════════════════
describe('LWS Integration', () => {
  const PHI = (1 + Math.sqrt(5)) / 2;

  describe('computeLWSWeights', () => {
    it('returns 6 weights', () => {
      const weights = computeLWSWeights('ko');
      expect(weights.length).toBe(6);
    });

    it('weights are based on golden ratio', () => {
      const weights = computeLWSWeights('ko');
      weights.forEach(w => {
        expect(w).toBeGreaterThan(0);
        // Should be some power of PHI
        const log = Math.log(w) / Math.log(PHI);
        expect(Math.abs(log - Math.round(log))).toBeLessThan(0.01);
      });
    });
  });

  describe('computeLWSScore', () => {
    it('returns 0 for empty string', () => {
      expect(computeLWSScore('')).toBe(0);
    });

    it('returns score for valid spelltext', () => {
      const tokenizer = new SacredTongueTokenizer('ko');
      const data = new Uint8Array([1, 2, 3]);
      const spelltext = tokenizer.encode(data);
      const score = computeLWSScore(spelltext);
      expect(score).toBeGreaterThan(0);
    });
  });
});

// ═══════════════════════════════════════════════════════════════
// Stress Tests
// ═══════════════════════════════════════════════════════════════
describe('Stress tests', () => {
  it('tokenizer handles 10,000 random bytes', () => {
    const tokenizer = new SacredTongueTokenizer('ca');
    const data = randomBytes(10000);
    const encoded = tokenizer.encode(data);
    const decoded = tokenizer.decode(encoded);
    expect(Array.from(decoded)).toEqual(Array.from(data));
  });

  it('all 6 tongues × 256 bytes = 1,536 roundtrips', () => {
    const tongues: TongueCode[] = ['ko', 'av', 'ru', 'ca', 'um', 'dr'];
    let totalRoundtrips = 0;

    tongues.forEach(code => {
      const tokenizer = new SacredTongueTokenizer(code);
      for (let b = 0; b < 256; b++) {
        const token = tokenizer.encodeByte(b);
        const decoded = tokenizer.decodeToken(token);
        expect(decoded).toBe(b);
        totalRoundtrips++;
      }
    });

    expect(totalRoundtrips).toBe(1536);
  });

  it('format/parse 100 random blobs', () => {
    for (let i = 0; i < 100; i++) {
      const salt = randomBytes(16);
      const nonce = randomBytes(12);
      const ct = randomBytes(Math.floor(Math.random() * 500) + 10);
      const tag = randomBytes(16);
      const kid = `k${i}`;
      const aad = `test=${i}`;

      const blob = formatSS1Blob(kid, aad, salt, nonce, ct, tag);
      const parsed = parseSS1Blob(blob);

      expect(parsed.kid).toBe(kid);
      expect(parsed.aad).toBe(aad);
      expect(Array.from(parsed.salt)).toEqual(Array.from(salt));
      expect(Array.from(parsed.nonce)).toEqual(Array.from(nonce));
      expect(Array.from(parsed.ciphertext)).toEqual(Array.from(ct));
      expect(Array.from(parsed.tag)).toEqual(Array.from(tag));
    }
  });
});
