/**
 * Unit tests for RWP v3.0 TypeScript Implementation
 * ==================================================
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  RWPv3Protocol,
  SacredTongueTokenizer,
  TOKENIZER,
  rwpEncryptMessage,
  rwpDecryptMessage,
  envelopeToDict,
  envelopeFromDict,
  type RWPv3Envelope,
} from '../../src/spiralverse/rwp_v3.js';
import { TONGUES, SECTION_TONGUES } from '../../src/harmonic/sacredTongues.js';
import { randomBytes } from 'crypto';

describe('SacredTongueTokenizer', () => {
  let tokenizer: SacredTongueTokenizer;

  beforeEach(() => {
    tokenizer = new SacredTongueTokenizer();
  });

  describe('bijectivity', () => {
    it('should roundtrip all 256 bytes for each tongue', () => {
      for (const tongueCode of Object.keys(TONGUES)) {
        for (let b = 0; b < 256; b++) {
          const data = Buffer.from([b]);
          const tokens = tokenizer.encodeBytes(tongueCode, data);
          const decoded = tokenizer.decodeTokens(tongueCode, tokens);
          expect(decoded).toEqual(data);
        }
      }
    });

    it('should produce 256 unique tokens per tongue', () => {
      for (const tongueCode of Object.keys(TONGUES)) {
        const tokens = new Set<string>();
        for (let b = 0; b < 256; b++) {
          const encoded = tokenizer.encodeBytes(tongueCode, Buffer.from([b]));
          tokens.add(encoded[0]);
        }
        expect(tokens.size).toBe(256);
      }
    });

    it('should produce tokens with apostrophe format', () => {
      for (const tongueCode of Object.keys(TONGUES)) {
        const tokens = tokenizer.encodeBytes(tongueCode, Buffer.from([0x00]));
        expect(tokens[0]).toContain("'");
        expect(tokens[0].split("'").length).toBe(2);
      }
    });
  });

  describe('encoding', () => {
    it('should encode empty buffer to empty array', () => {
      const tokens = tokenizer.encodeBytes('ko', Buffer.alloc(0));
      expect(tokens).toEqual([]);
    });

    it('should encode single byte to single token', () => {
      const tokens = tokenizer.encodeBytes('ko', Buffer.from([0x00]));
      expect(tokens.length).toBe(1);
      expect(tokens[0]).toBe("kor'ah"); // Kor'aelin v1.1: prefix[0]'suffix[0]
    });

    it('should encode multiple bytes to multiple tokens', () => {
      const tokens = tokenizer.encodeBytes('ko', Buffer.from([0x00, 0x01, 0x02]));
      expect(tokens.length).toBe(3);
    });

    it('should throw on unknown tongue', () => {
      expect(() => tokenizer.encodeBytes('invalid', Buffer.from([0]))).toThrow('Unknown tongue');
    });
  });

  describe('decoding', () => {
    it('should throw on invalid token', () => {
      expect(() => tokenizer.decodeTokens('ko', ['invalid_token'])).toThrow('Invalid token');
    });

    it('should fail with cross-tongue tokens', () => {
      // Encode with Kor'aelin
      const tokens = tokenizer.encodeBytes('ko', Buffer.from([0x00]));
      // Avali has different tokens, so decoding should fail
      expect(() => tokenizer.decodeTokens('av', tokens)).toThrow('Invalid token');
    });
  });

  describe('section API', () => {
    it('should use correct tongue for each section', () => {
      const data = Buffer.from([0x00]);

      // aad → Avali (av)
      const aadTokens = tokenizer.encodeSection('aad', data);
      const avTokens = tokenizer.encodeBytes('av', data);
      expect(aadTokens).toEqual(avTokens);

      // salt → Runethic (ru)
      const saltTokens = tokenizer.encodeSection('salt', data);
      const ruTokens = tokenizer.encodeBytes('ru', data);
      expect(saltTokens).toEqual(ruTokens);

      // nonce → Kor'aelin (ko)
      const nonceTokens = tokenizer.encodeSection('nonce', data);
      const koTokens = tokenizer.encodeBytes('ko', data);
      expect(nonceTokens).toEqual(koTokens);

      // ct → Cassisivadan (ca)
      const ctTokens = tokenizer.encodeSection('ct', data);
      const caTokens = tokenizer.encodeBytes('ca', data);
      expect(ctTokens).toEqual(caTokens);

      // tag → Draumric (dr)
      const tagTokens = tokenizer.encodeSection('tag', data);
      const drTokens = tokenizer.encodeBytes('dr', data);
      expect(tagTokens).toEqual(drTokens);
    });

    it('should roundtrip section encode/decode', () => {
      const data = randomBytes(64);
      for (const section of Object.keys(SECTION_TONGUES)) {
        const tokens = tokenizer.encodeSection(section, data);
        const decoded = tokenizer.decodeSection(section, tokens);
        expect(decoded).toEqual(data);
      }
    });
  });
});

describe('RWPv3Protocol', () => {
  let protocol: RWPv3Protocol;

  beforeEach(() => {
    protocol = new RWPv3Protocol();
  });

  describe('encryption', () => {
    it('should return valid envelope', () => {
      const envelope = protocol.encrypt(Buffer.from('password'), Buffer.from('hello'));

      expect(envelope.version).toEqual(['rwp', 'v3', 'ts']);
      expect(envelope.aad).toBeInstanceOf(Array);
      expect(envelope.salt).toBeInstanceOf(Array);
      expect(envelope.nonce).toBeInstanceOf(Array);
      expect(envelope.ct).toBeInstanceOf(Array);
      expect(envelope.tag).toBeInstanceOf(Array);
    });

    it('should produce Sacred Tongue tokens for all fields', () => {
      const envelope = protocol.encrypt(Buffer.from('password'), Buffer.from('hello'));

      // Verify tokens are valid for their sections
      expect(() => TOKENIZER.decodeSection('aad', envelope.aad)).not.toThrow();
      expect(() => TOKENIZER.decodeSection('salt', envelope.salt)).not.toThrow();
      expect(() => TOKENIZER.decodeSection('nonce', envelope.nonce)).not.toThrow();
      expect(() => TOKENIZER.decodeSection('ct', envelope.ct)).not.toThrow();
      expect(() => TOKENIZER.decodeSection('tag', envelope.tag)).not.toThrow();
    });

    it('should produce 16-byte salt', () => {
      const envelope = protocol.encrypt(Buffer.from('password'), Buffer.from('hello'));
      const salt = TOKENIZER.decodeSection('salt', envelope.salt);
      expect(salt.length).toBe(16);
    });

    it('should produce 12-byte nonce', () => {
      const envelope = protocol.encrypt(Buffer.from('password'), Buffer.from('hello'));
      const nonce = TOKENIZER.decodeSection('nonce', envelope.nonce);
      expect(nonce.length).toBe(12);
    });

    it('should produce 16-byte tag', () => {
      const envelope = protocol.encrypt(Buffer.from('password'), Buffer.from('hello'));
      const tag = TOKENIZER.decodeSection('tag', envelope.tag);
      expect(tag.length).toBe(16);
    });
  });

  describe('decryption', () => {
    it('should roundtrip encrypt/decrypt', () => {
      const password = Buffer.from('test-password');
      const plaintext = Buffer.from('Hello, Mars!');

      const envelope = protocol.encrypt(password, plaintext);
      const decrypted = protocol.decrypt(password, envelope);

      expect(decrypted).toEqual(plaintext);
    });

    it('should roundtrip with AAD', () => {
      const password = Buffer.from('password');
      const plaintext = Buffer.from('message');
      const aad = Buffer.from(JSON.stringify({ timestamp: '2026-01-18' }));

      const envelope = protocol.encrypt(password, plaintext, aad);
      const decrypted = protocol.decrypt(password, envelope);

      expect(decrypted).toEqual(plaintext);
    });

    it('should fail with wrong password', () => {
      const envelope = protocol.encrypt(Buffer.from('correct'), Buffer.from('secret'));

      expect(() => {
        protocol.decrypt(Buffer.from('wrong'), envelope);
      }).toThrow('AEAD authentication failed');
    });

    it('should fail with tampered ciphertext', () => {
      const password = Buffer.from('password');
      const envelope = protocol.encrypt(password, Buffer.from('message'));

      // Tamper with ciphertext
      envelope.ct[0] = "bip'u";

      expect(() => {
        protocol.decrypt(password, envelope);
      }).toThrow('AEAD authentication failed');
    });

    it('should fail with tampered tag', () => {
      const password = Buffer.from('password');
      const envelope = protocol.encrypt(password, Buffer.from('message'));

      // Tamper with tag
      envelope.tag[0] = "anvil'u";

      expect(() => {
        protocol.decrypt(password, envelope);
      }).toThrow('AEAD authentication failed');
    });

    it('should handle empty plaintext', () => {
      const password = Buffer.from('password');
      const plaintext = Buffer.alloc(0);

      const envelope = protocol.encrypt(password, plaintext);
      const decrypted = protocol.decrypt(password, envelope);

      expect(decrypted).toEqual(plaintext);
    });

    it('should handle large plaintext', () => {
      const password = Buffer.from('password');
      const plaintext = randomBytes(10000);

      const envelope = protocol.encrypt(password, plaintext);
      const decrypted = protocol.decrypt(password, envelope);

      expect(decrypted).toEqual(plaintext);
    });
  });

  describe('determinism', () => {
    it('should produce different nonces each encryption', () => {
      const password = Buffer.from('password');
      const plaintext = Buffer.from('same message');

      const env1 = protocol.encrypt(password, plaintext);
      const env2 = protocol.encrypt(password, plaintext);

      expect(env1.nonce).not.toEqual(env2.nonce);
    });

    it('should produce different salts each encryption', () => {
      const password = Buffer.from('password');
      const plaintext = Buffer.from('same message');

      const env1 = protocol.encrypt(password, plaintext);
      const env2 = protocol.encrypt(password, plaintext);

      expect(env1.salt).not.toEqual(env2.salt);
    });

    it('should produce different ciphertexts for same plaintext', () => {
      const password = Buffer.from('password');
      const plaintext = Buffer.from('same message');

      const env1 = protocol.encrypt(password, plaintext);
      const env2 = protocol.encrypt(password, plaintext);

      expect(env1.ct).not.toEqual(env2.ct);
    });
  });
});

describe('Convenience API', () => {
  it('should encrypt and decrypt string message', () => {
    const envelope = rwpEncryptMessage('password', 'Hello, Mars!');
    const message = rwpDecryptMessage('password', envelope);
    expect(message).toBe('Hello, Mars!');
  });

  it('should handle metadata', () => {
    const metadata = { timestamp: '2026-01-18', sender: 'earth' };
    const envelope = rwpEncryptMessage('password', 'Hello', metadata);
    const message = rwpDecryptMessage('password', envelope);
    expect(message).toBe('Hello');

    // Verify metadata is in AAD
    const aadBytes = TOKENIZER.decodeSection('aad', envelope.aad);
    const aadObj = JSON.parse(aadBytes.toString('utf-8'));
    expect(aadObj).toEqual(metadata);
  });

  it('should handle unicode messages', () => {
    const message = 'Hello, 火星! 🚀';
    const envelope = rwpEncryptMessage('password', message);
    const decrypted = rwpDecryptMessage('password', envelope);
    expect(decrypted).toBe(message);
  });
});

describe('Envelope serialization', () => {
  it('should serialize to dict', () => {
    const protocol = new RWPv3Protocol();
    const envelope = protocol.encrypt(Buffer.from('password'), Buffer.from('message'));

    const dict = envelopeToDict(envelope);
    expect(dict.version).toEqual(['rwp', 'v3', 'ts']);
    expect(dict.aad).toEqual(envelope.aad);
  });

  it('should roundtrip through JSON', () => {
    const protocol = new RWPv3Protocol();
    const password = Buffer.from('password');
    const plaintext = Buffer.from('message');

    const envelope = protocol.encrypt(password, plaintext);
    const json = JSON.stringify(envelopeToDict(envelope));
    const parsed = envelopeFromDict(JSON.parse(json));

    const decrypted = protocol.decrypt(password, parsed);
    expect(decrypted).toEqual(plaintext);
  });
});
