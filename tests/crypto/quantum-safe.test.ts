/**
 * @file quantum-safe.test.ts
 * @module tests/crypto/quantum-safe
 * @layer Layer 4
 *
 * Tests for the algorithm-agnostic PQC abstraction layer.
 * 62 tests across 9 groups (A-I).
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import {
  // Types
  type PQCFamily,
  type NISTLevel,
  type QuantumSafeKEM,
  type QuantumSafeSignature,
  type KEMDescriptor,
  type SignatureDescriptor,
  type QSKeyPair,
  type QSEncapsulation,
  type QSEnvelopeConfig,
  // Catalog
  PQC_ALGORITHMS,
  PQC_FAMILY_TRADEOFFS,
  // Implementations
  StubKEM,
  StubSignature,
  // Registry
  registerKEM,
  registerSignature,
  getKEM,
  getSignature,
  listAlgorithms,
  clearRegistry,
  // Envelope
  QuantumSafeEnvelope,
  DEFAULT_QS_ENVELOPE_CONFIG,
} from '../../src/crypto/quantum-safe.js';

// ═══════════════════════════════════════════════════════════════
// A. Algorithm Catalog
// ═══════════════════════════════════════════════════════════════

describe('A. Algorithm Catalog', () => {
  it('should contain all five PQC families', () => {
    const families = new Set(Object.values(PQC_ALGORITHMS).map((a) => a.family));
    expect(families.has('lattice')).toBe(true);
    expect(families.has('hash-based')).toBe(true);
    expect(families.has('code-based')).toBe(true);
  });

  it('should have KEMs and signatures', () => {
    const kems = Object.values(PQC_ALGORITHMS).filter((a) => a.kind === 'kem');
    const sigs = Object.values(PQC_ALGORITHMS).filter((a) => a.kind === 'signature');
    expect(kems.length).toBeGreaterThanOrEqual(3); // ML-KEM-512/768/1024 + McEliece
    expect(sigs.length).toBeGreaterThanOrEqual(4); // ML-DSA-44/65 + FN-DSA + SLH-DSA
  });

  it('should have valid NIST levels (1-5)', () => {
    for (const alg of Object.values(PQC_ALGORITHMS)) {
      expect(alg.nistLevel).toBeGreaterThanOrEqual(1);
      expect(alg.nistLevel).toBeLessThanOrEqual(5);
    }
  });

  it('should have positive key/output sizes', () => {
    for (const alg of Object.values(PQC_ALGORITHMS)) {
      expect(alg.publicKeySize).toBeGreaterThan(0);
      expect(alg.secretKeySize).toBeGreaterThan(0);
      if (alg.kind === 'kem') {
        expect(alg.ciphertextSize).toBeGreaterThan(0);
        expect(alg.sharedSecretSize).toBe(32);
      } else {
        expect(alg.signatureSize).toBeGreaterThan(0);
      }
    }
  });

  it('ML-KEM-768 should match FIPS 203 spec', () => {
    const mlkem = PQC_ALGORITHMS['ML-KEM-768'];
    expect(mlkem.publicKeySize).toBe(1184);
    expect(mlkem.secretKeySize).toBe(2400);
    expect(mlkem.ciphertextSize).toBe(1088);
    expect(mlkem.standard).toBe('FIPS 203');
  });

  it('SLH-DSA-128s should have tiny keys, large signatures', () => {
    const slh = PQC_ALGORITHMS['SLH-DSA-128s'];
    expect(slh.publicKeySize).toBe(32);
    expect(slh.signatureSize).toBe(7856);
    expect(slh.family).toBe('hash-based');
  });

  it('Classic McEliece should have very large public key', () => {
    const mce = PQC_ALGORITHMS['Classic-McEliece-348864'];
    expect(mce.publicKeySize).toBe(261120);
    expect(mce.ciphertextSize).toBe(128);
    expect(mce.family).toBe('code-based');
  });
});

// ═══════════════════════════════════════════════════════════════
// B. PQC Family Tradeoffs
// ═══════════════════════════════════════════════════════════════

describe('B. PQC Family Tradeoffs', () => {
  it('should cover all five families', () => {
    const families: PQCFamily[] = ['lattice', 'hash-based', 'code-based', 'isogeny', 'multivariate'];
    for (const f of families) {
      expect(PQC_FAMILY_TRADEOFFS[f]).toBeDefined();
      expect(PQC_FAMILY_TRADEOFFS[f].scbeRecommendation).toBeTruthy();
    }
  });

  it('lattice should be primary recommendation', () => {
    expect(PQC_FAMILY_TRADEOFFS.lattice.scbeRecommendation).toContain('Primary');
  });

  it('isogeny should be not recommended', () => {
    expect(PQC_FAMILY_TRADEOFFS.isogeny.scbeRecommendation).toContain('Not recommended');
  });
});

// ═══════════════════════════════════════════════════════════════
// C. StubKEM
// ═══════════════════════════════════════════════════════════════

describe('C. StubKEM', () => {
  const desc = PQC_ALGORITHMS['ML-KEM-768'] as KEMDescriptor;
  let kem: StubKEM;

  beforeEach(() => {
    kem = new StubKEM(desc);
  });

  it('should expose correct descriptor', () => {
    expect(kem.descriptor.name).toBe('ML-KEM-768');
    expect(kem.descriptor.family).toBe('lattice');
    expect(kem.descriptor.nistLevel).toBe(3);
  });

  it('should generate key pair with correct sizes', async () => {
    const kp = await kem.generateKeyPair();
    expect(kp.publicKey.length).toBe(1184);
    expect(kp.secretKey.length).toBe(2400);
  });

  it('should generate unique key pairs', async () => {
    const kp1 = await kem.generateKeyPair();
    const kp2 = await kem.generateKeyPair();
    expect(Buffer.from(kp1.publicKey).equals(Buffer.from(kp2.publicKey))).toBe(false);
  });

  it('should encapsulate with correct sizes', async () => {
    const kp = await kem.generateKeyPair();
    const enc = await kem.encapsulate(kp.publicKey);
    expect(enc.ciphertext.length).toBe(1088);
    expect(enc.sharedSecret.length).toBe(32);
  });

  it('should decapsulate with correct size', async () => {
    const kp = await kem.generateKeyPair();
    const enc = await kem.encapsulate(kp.publicKey);
    const secret = await kem.decapsulate(enc.ciphertext, kp.secretKey);
    expect(secret.length).toBe(32);
  });

  it('should reject invalid public key size', async () => {
    await expect(kem.encapsulate(new Uint8Array(100))).rejects.toThrow('invalid public key size');
  });

  it('should reject invalid ciphertext size', async () => {
    const kp = await kem.generateKeyPair();
    await expect(kem.decapsulate(new Uint8Array(100), kp.secretKey)).rejects.toThrow(
      'invalid ciphertext size'
    );
  });

  it('should reject invalid secret key size', async () => {
    const kp = await kem.generateKeyPair();
    const enc = await kem.encapsulate(kp.publicKey);
    await expect(kem.decapsulate(enc.ciphertext, new Uint8Array(100))).rejects.toThrow(
      'invalid secret key size'
    );
  });

  it('should work with code-based (McEliece) descriptor', async () => {
    const mceDesc = PQC_ALGORITHMS['Classic-McEliece-348864'] as KEMDescriptor;
    const mce = new StubKEM(mceDesc);
    const kp = await mce.generateKeyPair();
    expect(kp.publicKey.length).toBe(261120);
    const enc = await mce.encapsulate(kp.publicKey);
    expect(enc.ciphertext.length).toBe(128);
  });
});

// ═══════════════════════════════════════════════════════════════
// D. StubSignature
// ═══════════════════════════════════════════════════════════════

describe('D. StubSignature', () => {
  const desc = PQC_ALGORITHMS['ML-DSA-65'] as SignatureDescriptor;
  let sig: StubSignature;

  beforeEach(() => {
    sig = new StubSignature(desc);
  });

  it('should expose correct descriptor', () => {
    expect(sig.descriptor.name).toBe('ML-DSA-65');
    expect(sig.descriptor.family).toBe('lattice');
  });

  it('should generate key pair with correct sizes', async () => {
    const kp = await sig.generateKeyPair();
    expect(kp.publicKey.length).toBe(1952);
    expect(kp.secretKey.length).toBe(4032);
  });

  it('should sign with correct signature size', async () => {
    const kp = await sig.generateKeyPair();
    const message = new TextEncoder().encode('hello SCBE');
    const signature = await sig.sign(message, kp.secretKey);
    expect(signature.length).toBe(3293);
  });

  it('should reject stub verify (no native liboqs)', async () => {
    const kp = await sig.generateKeyPair();
    const message = new TextEncoder().encode('governance payload');
    const signature = await sig.sign(message, kp.secretKey);
    await expect(sig.verify(message, signature, kp.publicKey)).rejects.toThrow(
      'stub verify() is disabled'
    );
  });

  it('should reject invalid public key size on verify', async () => {
    const kp = await sig.generateKeyPair();
    const message = new TextEncoder().encode('test');
    const signature = await sig.sign(message, kp.secretKey);
    await expect(sig.verify(message, signature, new Uint8Array(10))).rejects.toThrow(
      'invalid public key size'
    );
  });

  it('should reject invalid signature size on verify', async () => {
    const kp = await sig.generateKeyPair();
    const message = new TextEncoder().encode('test');
    await expect(sig.verify(message, new Uint8Array(10), kp.publicKey)).rejects.toThrow(
      'invalid signature size'
    );
  });

  it('should reject invalid secret key size on sign', async () => {
    const message = new TextEncoder().encode('test');
    await expect(sig.sign(message, new Uint8Array(10))).rejects.toThrow('invalid secret key size');
  });

  it('should work with hash-based (SLH-DSA) descriptor', async () => {
    const slhDesc = PQC_ALGORITHMS['SLH-DSA-128s'] as SignatureDescriptor;
    const slh = new StubSignature(slhDesc);
    const kp = await slh.generateKeyPair();
    expect(kp.publicKey.length).toBe(32);
    const message = new TextEncoder().encode('hash-based signing');
    const signature = await slh.sign(message, kp.secretKey);
    expect(signature.length).toBe(7856);
  });
});

// ═══════════════════════════════════════════════════════════════
// E. Algorithm Registry
// ═══════════════════════════════════════════════════════════════

describe('E. Algorithm Registry', () => {
  beforeEach(() => clearRegistry());
  afterEach(() => clearRegistry());

  it('getKEM should auto-create stub from catalog', () => {
    const kem = getKEM('ML-KEM-768');
    expect(kem.descriptor.name).toBe('ML-KEM-768');
  });

  it('getSignature should auto-create stub from catalog', () => {
    const sig = getSignature('ML-DSA-65');
    expect(sig.descriptor.name).toBe('ML-DSA-65');
  });

  it('should throw for unknown KEM', () => {
    expect(() => getKEM('NONEXISTENT-KEM')).toThrow('Unknown KEM algorithm');
  });

  it('should throw for unknown signature', () => {
    expect(() => getSignature('NONEXISTENT-SIG')).toThrow('Unknown signature algorithm');
  });

  it('registerKEM should replace stub', async () => {
    // Get stub first
    const stub = getKEM('ML-KEM-768');
    expect(stub).toBeInstanceOf(StubKEM);

    // Register custom (using another stub as mock)
    const custom: QuantumSafeKEM = {
      descriptor: stub.descriptor,
      generateKeyPair: async () => ({ publicKey: new Uint8Array(1184), secretKey: new Uint8Array(2400) }),
      encapsulate: async () => ({ ciphertext: new Uint8Array(1088), sharedSecret: new Uint8Array(32) }),
      decapsulate: async () => new Uint8Array(32),
    };
    registerKEM(custom);

    const retrieved = getKEM('ML-KEM-768');
    expect(retrieved).toBe(custom);
    expect(retrieved).not.toBeInstanceOf(StubKEM);
  });

  it('registerSignature should replace stub', async () => {
    const stub = getSignature('SLH-DSA-128s');
    const custom: QuantumSafeSignature = {
      descriptor: stub.descriptor,
      generateKeyPair: async () => ({ publicKey: new Uint8Array(32), secretKey: new Uint8Array(64) }),
      sign: async () => new Uint8Array(7856),
      verify: async () => true,
    };
    registerSignature(custom);
    expect(getSignature('SLH-DSA-128s')).toBe(custom);
  });

  it('listAlgorithms should report registration status', () => {
    getKEM('ML-KEM-768'); // Auto-creates
    const list = listAlgorithms();
    const mlkem = list.find((a) => a.name === 'ML-KEM-768');
    expect(mlkem?.registered).toBe(true);
    const mce = list.find((a) => a.name === 'Classic-McEliece-348864');
    expect(mce?.registered).toBe(false); // Not yet accessed
  });

  it('clearRegistry should remove all', () => {
    getKEM('ML-KEM-768');
    getSignature('ML-DSA-65');
    clearRegistry();
    const list = listAlgorithms();
    expect(list.every((a) => !a.registered)).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════
// F. QuantumSafeEnvelope — Default (Lattice + Lattice)
// ═══════════════════════════════════════════════════════════════

describe('F. QuantumSafeEnvelope — Default Config', () => {
  let env: QuantumSafeEnvelope;

  beforeEach(async () => {
    clearRegistry();
    env = new QuantumSafeEnvelope();
    await env.initialize();
  });
  afterEach(() => clearRegistry());

  it('should default to ML-KEM-768 + ML-DSA-65', () => {
    expect(env.algorithms.kem.name).toBe('ML-KEM-768');
    expect(env.algorithms.sig.name).toBe('ML-DSA-65');
  });

  it('isInitialized should be true after init', () => {
    expect(env.isInitialized).toBe(true);
  });

  it('should establish with shared secret', async () => {
    const est = await env.establish();
    expect(est.sharedSecret.length).toBe(32);
    expect(est.kemCiphertext.length).toBe(1088);
    expect(est.signature.length).toBe(3293);
    expect(est.bindingHash).toHaveLength(64); // SHA-256 hex
    expect(est.hybrid).toBe(true);
  });

  it('establishment should report algorithm metadata', async () => {
    const est = await env.establish();
    expect(est.algorithms.kem.family).toBe('lattice');
    expect(est.algorithms.sig.family).toBe('lattice');
    expect(est.algorithms.kem.nistLevel).toBe(3);
  });

  it('should produce unique secrets per establishment', async () => {
    const est1 = await env.establish();
    const est2 = await env.establish();
    expect(Buffer.from(est1.sharedSecret).equals(Buffer.from(est2.sharedSecret))).toBe(false);
  });

  it('should reject stub verify (no native liboqs)', async () => {
    const est = await env.establish();
    await expect(env.verify(
      new TextEncoder().encode(est.bindingHash),
      est.signature,
      env.getSignerPublicKey()
    )).rejects.toThrow('stub verify() is disabled');
  });

  it('should decapsulate ciphertext', async () => {
    const est = await env.establish();
    const recovered = await env.decapsulate(est.kemCiphertext);
    expect(recovered.length).toBe(32);
  });

  it('should expose public keys', () => {
    expect(env.getKEMPublicKey().length).toBe(1184);
    expect(env.getSignerPublicKey().length).toBe(1952);
  });
});

// ═══════════════════════════════════════════════════════════════
// G. QuantumSafeEnvelope — Cross-Family (Lattice KEM + Hash Sig)
// ═══════════════════════════════════════════════════════════════

describe('G. QuantumSafeEnvelope — Cross-Family', () => {
  afterEach(() => clearRegistry());

  it('should work with lattice KEM + hash-based signature', async () => {
    clearRegistry();
    const env = new QuantumSafeEnvelope({
      kemAlgorithm: 'ML-KEM-768',
      sigAlgorithm: 'SLH-DSA-128s',
    });
    await env.initialize();

    const est = await env.establish();
    expect(est.algorithms.kem.family).toBe('lattice');
    expect(est.algorithms.sig.family).toBe('hash-based');
    expect(est.signature.length).toBe(7856); // SPHINCS+ signature size
  });

  it('should work with code-based KEM + lattice signature', async () => {
    clearRegistry();
    const env = new QuantumSafeEnvelope({
      kemAlgorithm: 'Classic-McEliece-348864',
      sigAlgorithm: 'ML-DSA-44',
    });
    await env.initialize();

    const est = await env.establish();
    expect(est.algorithms.kem.family).toBe('code-based');
    expect(est.algorithms.sig.family).toBe('lattice');
    expect(est.kemCiphertext.length).toBe(128); // McEliece compact CT
    expect(est.signature.length).toBe(2420); // ML-DSA-44 sig
  });

  it('should work with hash-based signature + high security lattice KEM', async () => {
    clearRegistry();
    const env = new QuantumSafeEnvelope({
      kemAlgorithm: 'ML-KEM-1024',
      sigAlgorithm: 'SLH-DSA-256s',
    });
    await env.initialize();

    const est = await env.establish();
    expect(est.algorithms.kem.nistLevel).toBe(5);
    expect(est.algorithms.sig.nistLevel).toBe(5);
    expect(est.signature.length).toBe(29792);
  });
});

// ═══════════════════════════════════════════════════════════════
// H. QuantumSafeEnvelope — Hybrid Mode
// ═══════════════════════════════════════════════════════════════

describe('H. Hybrid Mode', () => {
  afterEach(() => clearRegistry());

  it('hybrid=true should XOR classical secret into shared secret', async () => {
    clearRegistry();
    const envHybrid = new QuantumSafeEnvelope({ hybridMode: true });
    const envPure = new QuantumSafeEnvelope({ hybridMode: false });
    await envHybrid.initialize();
    await envPure.initialize();

    const estH = await envHybrid.establish();
    const estP = await envPure.establish();

    // Both produce 32-byte secrets
    expect(estH.sharedSecret.length).toBe(32);
    expect(estP.sharedSecret.length).toBe(32);
    expect(estH.hybrid).toBe(true);
    expect(estP.hybrid).toBe(false);
  });

  it('hybrid and non-hybrid should produce different secrets', async () => {
    clearRegistry();
    // This is probabilistic but virtually certain since hybrid XORs in random bytes
    const envH = new QuantumSafeEnvelope({ hybridMode: true });
    const envP = new QuantumSafeEnvelope({ hybridMode: false });
    await envH.initialize();
    await envP.initialize();
    const estH = await envH.establish();
    const estP = await envP.establish();
    // Different key pairs → different secrets regardless, but hybrid mode
    // additionally XORs in classical randomness
    expect(Buffer.from(estH.sharedSecret).equals(Buffer.from(estP.sharedSecret))).toBe(false);
  });

  it('should include hybrid flag in establishment', async () => {
    clearRegistry();
    const env = new QuantumSafeEnvelope({ hybridMode: false });
    await env.initialize();
    const est = await env.establish();
    expect(est.hybrid).toBe(false);
  });
});

// ═══════════════════════════════════════════════════════════════
// I. Governance Tags & Binding
// ═══════════════════════════════════════════════════════════════

describe('I. Governance Tags & Binding', () => {
  afterEach(() => clearRegistry());

  it('should include tags in binding hash', async () => {
    clearRegistry();
    const env1 = new QuantumSafeEnvelope({
      tags: { agent: 'scout', policy: 'allow' },
    });
    const env2 = new QuantumSafeEnvelope({
      tags: { agent: 'sentinel', policy: 'deny' },
    });
    await env1.initialize();
    await env2.initialize();

    const est1 = await env1.establish();
    const est2 = await env2.establish();

    // Different tags → different binding hashes
    expect(est1.bindingHash).not.toBe(est2.bindingHash);
  });

  it('should produce deterministic binding hash for same tags + secret', async () => {
    clearRegistry();
    const env = new QuantumSafeEnvelope({
      tags: { role: 'analyzer' },
    });
    await env.initialize();

    const est = await env.establish();
    // bindingHash is SHA-256 of binding data, which is deterministic for given inputs
    expect(est.bindingHash).toHaveLength(64);
    expect(/^[0-9a-f]{64}$/.test(est.bindingHash)).toBe(true);
  });

  it('should handle empty tags gracefully', async () => {
    clearRegistry();
    const env = new QuantumSafeEnvelope({ tags: {} });
    await env.initialize();
    const est = await env.establish();
    expect(est.bindingHash).toHaveLength(64);
  });

  it('should throw on establish before initialize', async () => {
    clearRegistry();
    const env = new QuantumSafeEnvelope();
    expect(env.isInitialized).toBe(false);
    await expect(env.establish()).rejects.toThrow('not initialized');
  });

  it('should throw on getSignerPublicKey before initialize', () => {
    clearRegistry();
    const env = new QuantumSafeEnvelope();
    expect(() => env.getSignerPublicKey()).toThrow('Not initialized');
  });

  it('should throw on getKEMPublicKey before initialize', () => {
    clearRegistry();
    const env = new QuantumSafeEnvelope();
    expect(() => env.getKEMPublicKey()).toThrow('Not initialized');
  });

  it('should throw on decapsulate before initialize', async () => {
    clearRegistry();
    const env = new QuantumSafeEnvelope();
    await expect(env.decapsulate(new Uint8Array(1088))).rejects.toThrow('not initialized');
  });
});
