/**
 * SCBE Symphonic Cipher - Test Suite
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  Complex,
  FFT,
  Feistel,
  ZBase32,
  SymphonicAgent,
  HybridCrypto,
  signIntent,
  verifyIntent,
} from '../../src/symphonic/index.js';

describe('Complex Number', () => {
  it('should create complex numbers', () => {
    const c = new Complex(3, 4);
    expect(c.re).toBe(3);
    expect(c.im).toBe(4);
  });

  it('should add complex numbers', () => {
    const a = new Complex(1, 2);
    const b = new Complex(3, 4);
    const sum = a.add(b);
    expect(sum.re).toBe(4);
    expect(sum.im).toBe(6);
  });

  it('should subtract complex numbers', () => {
    const a = new Complex(5, 7);
    const b = new Complex(2, 3);
    const diff = a.sub(b);
    expect(diff.re).toBe(3);
    expect(diff.im).toBe(4);
  });

  it('should multiply complex numbers', () => {
    const a = new Complex(3, 2);
    const b = new Complex(1, 4);
    const prod = a.mul(b);
    // (3+2i)(1+4i) = 3 + 12i + 2i + 8i² = 3 + 14i - 8 = -5 + 14i
    expect(prod.re).toBe(-5);
    expect(prod.im).toBe(14);
  });

  it('should calculate magnitude', () => {
    const c = new Complex(3, 4);
    expect(c.magnitude).toBe(5); // 3-4-5 triangle
  });

  it('should calculate phase', () => {
    const c = new Complex(1, 1);
    expect(c.phase).toBeCloseTo(Math.PI / 4, 10);
  });

  it('should create from Euler formula', () => {
    const c = Complex.fromEuler(Math.PI / 2);
    expect(c.re).toBeCloseTo(0, 10);
    expect(c.im).toBeCloseTo(1, 10);
  });

  it('should conjugate', () => {
    const c = new Complex(3, 4);
    const conj = c.conjugate();
    expect(conj.re).toBe(3);
    expect(conj.im).toBe(-4);
  });
});

describe('FFT', () => {
  it('should require power of 2 input', () => {
    const signal = [new Complex(1, 0), new Complex(2, 0), new Complex(3, 0)];
    expect(() => FFT.transform(signal)).toThrow();
  });

  it('should transform DC signal', () => {
    // Constant signal should have all energy at DC (k=0)
    const signal = [
      new Complex(1, 0),
      new Complex(1, 0),
      new Complex(1, 0),
      new Complex(1, 0),
    ];
    const spectrum = FFT.transform(signal);
    expect(spectrum[0].magnitude).toBeCloseTo(4, 5);
    expect(spectrum[1].magnitude).toBeCloseTo(0, 5);
    expect(spectrum[2].magnitude).toBeCloseTo(0, 5);
    expect(spectrum[3].magnitude).toBeCloseTo(0, 5);
  });

  it('should transform alternating signal', () => {
    // [1, -1, 1, -1] should have energy at Nyquist (k=N/2)
    const signal = [
      new Complex(1, 0),
      new Complex(-1, 0),
      new Complex(1, 0),
      new Complex(-1, 0),
    ];
    const spectrum = FFT.transform(signal);
    expect(spectrum[0].magnitude).toBeCloseTo(0, 5);
    expect(spectrum[2].magnitude).toBeCloseTo(4, 5); // Nyquist
  });

  it('should inverse transform correctly', () => {
    const original = [
      new Complex(1, 0),
      new Complex(2, 0),
      new Complex(3, 0),
      new Complex(4, 0),
    ];
    const spectrum = FFT.transform(original);
    const recovered = FFT.inverse(spectrum);

    for (let i = 0; i < original.length; i++) {
      expect(recovered[i].re).toBeCloseTo(original[i].re, 5);
      expect(recovered[i].im).toBeCloseTo(original[i].im, 5);
    }
  });

  it('should analyze real signal', () => {
    const signal = [1, 2, 3, 4, 5, 6, 7, 8];
    const result = FFT.analyze(signal);
    expect(result.n).toBe(8);
    expect(result.magnitudes.length).toBe(8);
    expect(result.phases.length).toBe(8);
  });

  it('should compute spectral coherence', () => {
    // Low frequency signal should have high coherence
    const lowFreq = Array(64).fill(0).map((_, i) => Math.sin(2 * Math.PI * i / 32));
    const coherence = FFT.spectralCoherence(lowFreq);
    expect(coherence).toBeGreaterThan(0.5);
  });

  it('should prepare signal with padding', () => {
    const data = [1, 2, 3, 4, 5];
    const prepared = FFT.prepareSignal(data);
    expect(prepared.length).toBe(8); // Next power of 2
    expect(prepared[0].re).toBe(1);
    expect(prepared[5].re).toBe(0); // Padded
  });
});

describe('Feistel Network', () => {
  let feistel: Feistel;

  beforeEach(() => {
    feistel = new Feistel({ rounds: 6 });
  });

  it('should encrypt and decrypt', () => {
    const plaintext = new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8]);
    const key = 'test-key-12345';

    const encrypted = feistel.encrypt(plaintext, key);
    const decrypted = feistel.decrypt(encrypted, key);

    // Check original bytes match
    for (let i = 0; i < plaintext.length; i++) {
      expect(decrypted[i]).toBe(plaintext[i]);
    }
  });

  it('should encrypt strings', () => {
    const plaintext = 'Hello, Symphonic Cipher!';
    const key = 'secret-key';

    const encrypted = feistel.encryptString(plaintext, key);
    const decrypted = feistel.decryptString(encrypted, key);

    expect(decrypted).toBe(plaintext);
  });

  it('should produce different output for different keys', () => {
    const data = new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8]);

    const enc1 = feistel.encrypt(data, 'key1');
    const enc2 = feistel.encrypt(data, 'key2');

    // Should be different
    let same = true;
    for (let i = 0; i < enc1.length; i++) {
      if (enc1[i] !== enc2[i]) same = false;
    }
    expect(same).toBe(false);
  });

  it('should verify round-trip', () => {
    const data = new Uint8Array([10, 20, 30, 40, 50, 60, 70, 80]);
    const key = 'verification-key';
    expect(feistel.verify(data, key)).toBe(true);
  });

  it('should generate random keys', () => {
    const key1 = Feistel.generateKey(32);
    const key2 = Feistel.generateKey(32);
    expect(key1.length).toBe(32);
    expect(key2.length).toBe(32);
    // Should be different
    let same = true;
    for (let i = 0; i < 32; i++) {
      if (key1[i] !== key2[i]) same = false;
    }
    expect(same).toBe(false);
  });
});

describe('Z-Base-32', () => {
  it('should encode bytes', () => {
    const data = new Uint8Array([0x00]);
    const encoded = ZBase32.encode(data);
    expect(encoded).toBe('yy'); // 0x00 -> 00000 000 -> y + padding
  });

  it('should decode to bytes', () => {
    const encoded = 'yy';
    const decoded = ZBase32.decode(encoded);
    expect(decoded[0]).toBe(0);
  });

  it('should round-trip bytes', () => {
    const original = new Uint8Array([0x12, 0x34, 0x56, 0x78, 0x9a]);
    const encoded = ZBase32.encode(original);
    const decoded = ZBase32.decode(encoded);

    for (let i = 0; i < original.length; i++) {
      expect(decoded[i]).toBe(original[i]);
    }
  });

  it('should encode strings', () => {
    const text = 'Hello';
    const encoded = ZBase32.encodeString(text);
    const decoded = ZBase32.decodeString(encoded);
    expect(decoded).toBe(text);
  });

  it('should validate Z-Base-32 strings', () => {
    expect(ZBase32.isValid('ybndrfg8')).toBe(true);
    expect(ZBase32.isValid('invalid!')).toBe(false);
    expect(ZBase32.isValid('YBNDRFG8')).toBe(true); // Case insensitive
  });

  it('should reject invalid characters', () => {
    expect(() => ZBase32.decode('invalid!')).toThrow();
  });

  it('should handle empty input', () => {
    expect(ZBase32.encode(new Uint8Array(0))).toBe('');
    expect(ZBase32.decode('').length).toBe(0);
  });
});

describe('Symphonic Agent', () => {
  let agent: SymphonicAgent;

  beforeEach(() => {
    agent = new SymphonicAgent();
  });

  it('should synthesize harmonics from intent', () => {
    const result = agent.synthesizeHarmonics('TRANSFER_100_AETHER', 'secret-key');

    expect(result.modulatedData).toBeInstanceOf(Uint8Array);
    expect(result.signal.length).toBeGreaterThan(0);
    expect(result.spectrum.length).toBeGreaterThan(0);
    expect(result.fingerprint.length).toBe(32);
    expect(result.coherence).toBeGreaterThanOrEqual(0);
    expect(result.coherence).toBeLessThanOrEqual(1);
  });

  it('should produce consistent fingerprints', () => {
    const intent = 'CONSISTENT_INTENT';
    const key = 'consistent-key';

    const result1 = agent.synthesizeHarmonics(intent, key);
    const result2 = agent.synthesizeHarmonics(intent, key);

    // Fingerprints should be identical
    for (let i = 0; i < result1.fingerprint.length; i++) {
      expect(result1.fingerprint[i]).toBeCloseTo(result2.fingerprint[i], 10);
    }
  });

  it('should produce different fingerprints for different intents', () => {
    const key = 'same-key';
    const result1 = agent.synthesizeHarmonics('INTENT_A', key);
    const result2 = agent.synthesizeHarmonics('INTENT_B', key);

    const similarity = SymphonicAgent.fingerprintSimilarity(
      result1.fingerprint,
      result2.fingerprint
    );
    expect(similarity).toBeLessThan(1);
  });

  it('should quantize fingerprints', () => {
    const result = agent.synthesizeHarmonics('TEST', 'key');
    const quantized = agent.quantizeFingerprint(result.fingerprint);

    expect(quantized).toBeInstanceOf(Uint8Array);
    expect(quantized.length).toBe(result.fingerprint.length);
    // Values should be 0-255
    for (const v of quantized) {
      expect(v).toBeGreaterThanOrEqual(0);
      expect(v).toBeLessThanOrEqual(255);
    }
  });

  it('should compute fingerprint similarity', () => {
    const fp1 = [1, 2, 3, 4, 5];
    const fp2 = [1, 2, 3, 4, 5];
    const fp3 = [5, 4, 3, 2, 1];

    expect(SymphonicAgent.fingerprintSimilarity(fp1, fp2)).toBeCloseTo(1, 5);
    expect(SymphonicAgent.fingerprintSimilarity(fp1, fp3)).toBeLessThan(1);
  });
});

describe('Hybrid Crypto', () => {
  let crypto: HybridCrypto;
  const secretKey = 'test-secret-key-for-signing';

  beforeEach(() => {
    crypto = new HybridCrypto();
  });

  it('should sign intents', () => {
    const envelope = crypto.sign('TRANSFER_500_AETHER', secretKey);

    expect(envelope.intent).toBe('TRANSFER_500_AETHER');
    expect(envelope.signature.fingerprint).toBeTruthy();
    expect(envelope.signature.hmac).toBeTruthy();
    expect(envelope.signature.timestamp).toBeTruthy();
    expect(envelope.version).toBe('1.0.0');
  });

  it('should verify valid signatures', () => {
    const envelope = crypto.sign('TRANSFER_500_AETHER', secretKey);
    const result = crypto.verify(envelope, secretKey);

    expect(result.valid).toBe(true);
    expect(result.coherence).toBeGreaterThan(0);
    expect(result.similarity).toBeGreaterThan(0.8);
  });

  it('should reject tampered intents', () => {
    const envelope = crypto.sign('ORIGINAL_INTENT', secretKey);
    envelope.intent = 'TAMPERED_INTENT';
    const result = crypto.verify(envelope, secretKey);

    expect(result.valid).toBe(false);
  });

  it('should reject wrong keys', () => {
    const envelope = crypto.sign('TEST_INTENT', secretKey);
    const result = crypto.verify(envelope, 'wrong-key');

    expect(result.valid).toBe(false);
  });

  it('should create compact signatures', () => {
    const compact = crypto.signCompact('COMPACT_TEST', secretKey);

    expect(typeof compact).toBe('string');
    expect(compact.split('~').length).toBe(6);
  });

  it('should verify compact signatures', () => {
    const intent = 'COMPACT_VERIFY_TEST';
    const compact = crypto.signCompact(intent, secretKey);
    const result = crypto.verifyCompact(intent, compact, secretKey);

    // Debug: print reason if failed
    if (!result.valid) {
      console.log('Compact verification failed:', result.reason);
    }
    expect(result.valid).toBe(true);
  });

  it('should reject invalid compact format', () => {
    const result = crypto.verifyCompact('TEST', 'invalid', secretKey);
    expect(result.valid).toBe(false);
    expect(result.reason).toContain('Invalid');
  });

  it('should generate secure keys', () => {
    const key1 = HybridCrypto.generateKey();
    const key2 = HybridCrypto.generateKey();

    expect(key1).not.toBe(key2);
    expect(key1.length).toBeGreaterThan(40); // Z-Base-32 encoded 32 bytes
  });

  it('convenience functions should work', () => {
    const envelope = signIntent('CONVENIENCE_TEST', secretKey);
    const result = verifyIntent(envelope, secretKey);

    expect(result.valid).toBe(true);
  });
});

describe('Integration', () => {
  it('should handle full pipeline', () => {
    const intent = 'FULL_PIPELINE_TEST:amount=1000,recipient=0xABC';
    const key = HybridCrypto.generateKey();

    // Sign
    const envelope = signIntent(intent, key);

    // Verify
    const result = verifyIntent(envelope, key);
    expect(result.valid).toBe(true);

    // Check metrics
    expect(result.coherence).toBeGreaterThan(0);
    expect(result.similarity).toBeGreaterThan(0.85);
  });

  it('should handle large intents', () => {
    const largeIntent = 'X'.repeat(1000);
    const key = 'large-intent-key';

    const envelope = signIntent(largeIntent, key);
    const result = verifyIntent(envelope, key);

    expect(result.valid).toBe(true);
  });

  it('should handle unicode intents', () => {
    const unicodeIntent = '转账 500 以太币 → 受益人';
    const key = 'unicode-key';

    const envelope = signIntent(unicodeIntent, key);
    const result = verifyIntent(envelope, key);

    expect(result.valid).toBe(true);
  });
});
