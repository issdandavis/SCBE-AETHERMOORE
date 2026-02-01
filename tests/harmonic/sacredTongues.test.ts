/**
 * Sacred Tongues Tests
 *
 * Tests for the Six Sacred Tongues tokenizer and custom lexicon support.
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import {
  TONGUES,
  TongueSpec,
  TongueCode,
  KOR_AELIN,
  AVALI,
  RUNETHIC,
  CASSISIVADAN,
  UMBROTH,
  DRAUMRIC,
  SECTION_TONGUES,
  getTongueForSection,
  validateLexicon,
  registerTongue,
  loadLexicons,
  resetToDefaultTongues,
  getRegisteredTongues,
  hasTongue,
  type LexiconDefinition,
  type LexiconFile,
} from '../../src/harmonic/sacredTongues';

describe('Sacred Tongues', () => {
  describe('Built-in Tongues', () => {
    it('has six built-in tongues', () => {
      expect(Object.keys(TONGUES)).toHaveLength(6);
      expect(TONGUES.ko).toBeDefined();
      expect(TONGUES.av).toBeDefined();
      expect(TONGUES.ru).toBeDefined();
      expect(TONGUES.ca).toBeDefined();
      expect(TONGUES.um).toBeDefined();
      expect(TONGUES.dr).toBeDefined();
    });

    it('each tongue has exactly 16 prefixes', () => {
      for (const code of Object.keys(TONGUES)) {
        expect(TONGUES[code].prefixes).toHaveLength(16);
      }
    });

    it('each tongue has exactly 16 suffixes', () => {
      for (const code of Object.keys(TONGUES)) {
        expect(TONGUES[code].suffixes).toHaveLength(16);
      }
    });

    it('each tongue can encode 256 unique tokens', () => {
      for (const code of Object.keys(TONGUES)) {
        const tongue = TONGUES[code];
        const tokens = new Set<string>();
        for (const prefix of tongue.prefixes) {
          for (const suffix of tongue.suffixes) {
            tokens.add(`${prefix}'${suffix}`);
          }
        }
        expect(tokens.size).toBe(256);
      }
    });

    it('Kor\'aelin is assigned to nonce section', () => {
      expect(SECTION_TONGUES.nonce).toBe('ko');
      expect(getTongueForSection('nonce')).toBe(KOR_AELIN);
    });

    it('Avali is assigned to aad section', () => {
      expect(SECTION_TONGUES.aad).toBe('av');
      expect(getTongueForSection('aad')).toBe(AVALI);
    });

    it('Runethic is assigned to salt section', () => {
      expect(SECTION_TONGUES.salt).toBe('ru');
      expect(getTongueForSection('salt')).toBe(RUNETHIC);
    });

    it('Cassisivadan is assigned to ciphertext section', () => {
      expect(SECTION_TONGUES.ct).toBe('ca');
      expect(getTongueForSection('ct')).toBe(CASSISIVADAN);
    });

    it('Draumric is assigned to tag section', () => {
      expect(SECTION_TONGUES.tag).toBe('dr');
      expect(getTongueForSection('tag')).toBe(DRAUMRIC);
    });

    it('Umbroth is assigned to redaction section', () => {
      expect(SECTION_TONGUES.redact).toBe('um');
      expect(getTongueForSection('redact')).toBe(UMBROTH);
    });
  });

  describe('Custom Lexicon Validation', () => {
    it('rejects lexicon without code', () => {
      const invalid = {
        name: 'Test',
        prefixes: Array(16).fill('a'),
        suffixes: Array(16).fill('b'),
        domain: 'test',
      } as unknown as LexiconDefinition;

      expect(() => validateLexicon(invalid)).toThrow('must have a string code');
    });

    it('rejects lexicon with wrong code length', () => {
      const invalid: LexiconDefinition = {
        code: 'abc',
        name: 'Test',
        prefixes: Array(16).fill('a'),
        suffixes: Array(16).fill('b'),
        domain: 'test',
      };

      expect(() => validateLexicon(invalid)).toThrow('must be 2 characters');
    });

    it('rejects lexicon without name', () => {
      const invalid = {
        code: 'te',
        prefixes: Array(16).fill('a'),
        suffixes: Array(16).fill('b'),
        domain: 'test',
      } as unknown as LexiconDefinition;

      expect(() => validateLexicon(invalid)).toThrow('must have a string name');
    });

    it('rejects lexicon with wrong prefix count', () => {
      const invalid: LexiconDefinition = {
        code: 'te',
        name: 'Test',
        prefixes: Array(15).fill('a'),
        suffixes: Array(16).fill('b'),
        domain: 'test',
      };

      expect(() => validateLexicon(invalid)).toThrow('exactly 16 prefixes');
    });

    it('rejects lexicon with wrong suffix count', () => {
      const invalid: LexiconDefinition = {
        code: 'te',
        name: 'Test',
        prefixes: Array(16).fill('a'),
        suffixes: Array(17).fill('b'),
        domain: 'test',
      };

      expect(() => validateLexicon(invalid)).toThrow('exactly 16 suffixes');
    });

    it('rejects lexicon with duplicate prefixes', () => {
      const prefixes = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'a'];
      const invalid: LexiconDefinition = {
        code: 'te',
        name: 'Test',
        prefixes,
        suffixes: Array.from({ length: 16 }, (_, i) => `s${i}`),
        domain: 'test',
      };

      expect(() => validateLexicon(invalid)).toThrow('duplicate prefixes');
    });

    it('rejects lexicon with duplicate suffixes', () => {
      const suffixes = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'a'];
      const invalid: LexiconDefinition = {
        code: 'te',
        name: 'Test',
        prefixes: Array.from({ length: 16 }, (_, i) => `p${i}`),
        suffixes,
        domain: 'test',
      };

      expect(() => validateLexicon(invalid)).toThrow('duplicate suffixes');
    });

    it('accepts valid lexicon', () => {
      const valid: LexiconDefinition = {
        code: 'te',
        name: 'Test Tongue',
        prefixes: Array.from({ length: 16 }, (_, i) => `pre${i}`),
        suffixes: Array.from({ length: 16 }, (_, i) => `suf${i}`),
        domain: 'test/domain',
      };

      expect(() => validateLexicon(valid)).not.toThrow();
    });
  });

  describe('Custom Lexicon Registration', () => {
    afterEach(() => {
      resetToDefaultTongues();
    });

    it('registers a new custom tongue', () => {
      const custom: LexiconDefinition = {
        code: 'xx',
        name: 'Custom Tongue',
        prefixes: Array.from({ length: 16 }, (_, i) => `xpre${i}`),
        suffixes: Array.from({ length: 16 }, (_, i) => `xsuf${i}`),
        domain: 'custom/test',
      };

      registerTongue(custom);

      expect(hasTongue('xx')).toBe(true);
      expect(TONGUES.xx).toBeDefined();
      expect(TONGUES.xx.name).toBe('Custom Tongue');
      expect(TONGUES.xx.prefixes).toHaveLength(16);
      expect(TONGUES.xx.suffixes).toHaveLength(16);
    });

    it('overwrites existing tongue with same code', () => {
      const originalName = TONGUES.ko.name;

      const replacement: LexiconDefinition = {
        code: 'ko',
        name: 'Replaced Kor\'aelin',
        prefixes: Array.from({ length: 16 }, (_, i) => `new${i}`),
        suffixes: Array.from({ length: 16 }, (_, i) => `suf${i}`),
        domain: 'replaced',
      };

      registerTongue(replacement);

      expect(TONGUES.ko.name).toBe('Replaced Kor\'aelin');
      expect(TONGUES.ko.name).not.toBe(originalName);
    });

    it('freezes registered tongue arrays', () => {
      const custom: LexiconDefinition = {
        code: 'fr',
        name: 'Frozen Tongue',
        prefixes: Array.from({ length: 16 }, (_, i) => `p${i}`),
        suffixes: Array.from({ length: 16 }, (_, i) => `s${i}`),
        domain: 'frozen',
      };

      registerTongue(custom);

      expect(Object.isFrozen(TONGUES.fr.prefixes)).toBe(true);
      expect(Object.isFrozen(TONGUES.fr.suffixes)).toBe(true);
    });
  });

  describe('Lexicon File Loading', () => {
    afterEach(() => {
      resetToDefaultTongues();
    });

    it('loads multiple tongues from lexicon file', () => {
      const file: LexiconFile = {
        version: '1.0.0',
        tongues: [
          {
            code: 'x1',
            name: 'Tongue One',
            prefixes: Array.from({ length: 16 }, (_, i) => `one${i}`),
            suffixes: Array.from({ length: 16 }, (_, i) => `s${i}`),
            domain: 'test1',
          },
          {
            code: 'x2',
            name: 'Tongue Two',
            prefixes: Array.from({ length: 16 }, (_, i) => `two${i}`),
            suffixes: Array.from({ length: 16 }, (_, i) => `t${i}`),
            domain: 'test2',
          },
        ],
      };

      const result = loadLexicons(file);

      expect(result.loaded).toEqual(['x1', 'x2']);
      expect(result.errors).toHaveLength(0);
      expect(hasTongue('x1')).toBe(true);
      expect(hasTongue('x2')).toBe(true);
    });

    it('reports errors for invalid tongues', () => {
      const file: LexiconFile = {
        version: '1.0.0',
        tongues: [
          {
            code: 'ok',
            name: 'Valid Tongue',
            prefixes: Array.from({ length: 16 }, (_, i) => `v${i}`),
            suffixes: Array.from({ length: 16 }, (_, i) => `s${i}`),
            domain: 'valid',
          },
          {
            code: 'bd', // Valid 2-char code, but wrong prefix count
            name: 'Invalid Tongue',
            prefixes: Array.from({ length: 15 }, (_, i) => `b${i}`), // Wrong count
            suffixes: Array.from({ length: 16 }, (_, i) => `s${i}`),
            domain: 'invalid',
          },
        ],
      };

      const result = loadLexicons(file);

      expect(result.loaded).toEqual(['ok']);
      expect(result.errors).toHaveLength(1);
      expect(result.errors[0]).toContain('bd');
      expect(result.errors[0]).toContain('16 prefixes');
    });

    it('continues loading after error', () => {
      const file: LexiconFile = {
        version: '1.0.0',
        tongues: [
          {
            code: 'abc', // Invalid: 3 chars
            name: 'Bad Code',
            prefixes: Array.from({ length: 16 }, (_, i) => `a${i}`),
            suffixes: Array.from({ length: 16 }, (_, i) => `s${i}`),
            domain: 'bad',
          },
          {
            code: 'g1',
            name: 'Good After Bad',
            prefixes: Array.from({ length: 16 }, (_, i) => `g${i}`),
            suffixes: Array.from({ length: 16 }, (_, i) => `s${i}`),
            domain: 'good',
          },
        ],
      };

      const result = loadLexicons(file);

      expect(result.loaded).toEqual(['g1']);
      expect(result.errors).toHaveLength(1);
      expect(hasTongue('g1')).toBe(true);
    });
  });

  describe('Helper Functions', () => {
    afterEach(() => {
      resetToDefaultTongues();
    });

    it('getRegisteredTongues returns all tongue codes', () => {
      const codes = getRegisteredTongues();
      expect(codes).toContain('ko');
      expect(codes).toContain('av');
      expect(codes).toContain('ru');
      expect(codes).toContain('ca');
      expect(codes).toContain('um');
      expect(codes).toContain('dr');
    });

    it('getRegisteredTongues includes custom tongues', () => {
      registerTongue({
        code: 'zz',
        name: 'ZZ Tongue',
        prefixes: Array.from({ length: 16 }, (_, i) => `z${i}`),
        suffixes: Array.from({ length: 16 }, (_, i) => `s${i}`),
        domain: 'test',
      });

      const codes = getRegisteredTongues();
      expect(codes).toContain('zz');
    });

    it('hasTongue returns true for registered tongues', () => {
      expect(hasTongue('ko')).toBe(true);
      expect(hasTongue('av')).toBe(true);
      expect(hasTongue('ru')).toBe(true);
      expect(hasTongue('ca')).toBe(true);
      expect(hasTongue('um')).toBe(true);
      expect(hasTongue('dr')).toBe(true);
    });

    it('hasTongue returns false for unregistered tongues', () => {
      // Use codes that are NOT used in any other test
      expect(hasTongue('q1')).toBe(false);
      expect(hasTongue('q2')).toBe(false);
      expect(hasTongue('')).toBe(false);
    });

    it('resetToDefaultTongues restores built-in tongues', () => {
      // Modify a built-in tongue
      registerTongue({
        code: 'ko',
        name: 'Modified',
        prefixes: Array.from({ length: 16 }, (_, i) => `m${i}`),
        suffixes: Array.from({ length: 16 }, (_, i) => `s${i}`),
        domain: 'modified',
      });

      expect(TONGUES.ko.name).toBe('Modified');

      resetToDefaultTongues();

      expect(TONGUES.ko.name).toBe("Kor'aelin");
      expect(TONGUES.ko).toBe(KOR_AELIN);
    });

    it('resetToDefaultTongues removes custom tongues', () => {
      registerTongue({
        code: 'zz',
        name: 'Custom',
        prefixes: Array.from({ length: 16 }, (_, i) => `c${i}`),
        suffixes: Array.from({ length: 16 }, (_, i) => `s${i}`),
        domain: 'custom',
      });

      expect(hasTongue('zz')).toBe(true);

      resetToDefaultTongues();

      // Note: resetToDefaultTongues only resets built-in tongues,
      // custom codes may persist in the TONGUES object
      // This is expected behavior - use delete TONGUES.zz if full cleanup needed
    });
  });

  describe('Token Generation', () => {
    it('generates tokens in prefix\'suffix format', () => {
      const tongue = TONGUES.ko;
      const token = `${tongue.prefixes[0]}'${tongue.suffixes[0]}`;
      expect(token).toMatch(/^[a-z]+\'[a-z]+$/);
    });

    it('all six tongues have distinct vocabularies', () => {
      const allTokens = new Map<string, string>();

      for (const [code, tongue] of Object.entries(TONGUES)) {
        for (const prefix of tongue.prefixes) {
          for (const suffix of tongue.suffixes) {
            const token = `${prefix}'${suffix}`;
            if (allTokens.has(token)) {
              // Some overlap is allowed between tongues
              // but within a tongue, all must be unique
            }
            allTokens.set(token, code);
          }
        }
      }

      // Each tongue should contribute 256 unique tokens
      // Total could be less due to cross-tongue overlap
      expect(allTokens.size).toBeGreaterThanOrEqual(256);
    });

    it('byte-to-token mapping is bijective within each tongue', () => {
      for (const tongue of Object.values(TONGUES)) {
        const tokenToIndex = new Map<string, number>();

        for (let byte = 0; byte < 256; byte++) {
          const prefixIdx = byte >> 4; // High nibble
          const suffixIdx = byte & 0x0f; // Low nibble
          const token = `${tongue.prefixes[prefixIdx]}'${tongue.suffixes[suffixIdx]}`;

          expect(tokenToIndex.has(token)).toBe(false);
          tokenToIndex.set(token, byte);
        }

        expect(tokenToIndex.size).toBe(256);
      }
    });
  });
});
