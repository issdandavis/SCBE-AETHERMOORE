/**
 * pqc.ts real-backend tests — the SHA-256 "development stub" is gone; ML-KEM/ML-DSA
 * now run on @noble/post-quantum (real, pure-JS PQC). Green must mean working.
 */
import { describe, it, expect } from 'vitest';
import { MLKEM768, MLDSA65 } from '../../src/crypto/pqc.js';

describe('pqc.ts real PQC (noble, no stub)', () => {
  it('ML-KEM-768 encapsulate/decapsulate agree on the shared secret', async () => {
    const kem = new MLKEM768();
    const { publicKey, secretKey } = await kem.generateKeyPair();
    const { ciphertext, sharedSecret } = await kem.encapsulate(publicKey);
    const recovered = await kem.decapsulate(ciphertext, secretKey);
    expect(Buffer.from(recovered).equals(Buffer.from(sharedSecret))).toBe(true);
    expect(sharedSecret.length).toBe(32);
  });

  it('ML-DSA-65 sign/verify round-trips and rejects tamper + forgery', async () => {
    const dsa = new MLDSA65();
    const { publicKey, secretKey } = await dsa.generateKeyPair();
    const msg = new Uint8Array([1, 2, 3, 4]);
    const sig = await dsa.sign(msg, secretKey);
    expect(sig.length).toBe(3309); // real ML-DSA-65 signature size
    expect(await dsa.verify(msg, sig, publicKey)).toBe(true);
    // tampered message -> rejected
    expect(await dsa.verify(new Uint8Array([9, 9, 9, 9]), sig, publicKey)).toBe(false);
    // forged signature (all zeros, correct length) -> rejected
    expect(await dsa.verify(msg, new Uint8Array(sig.length), publicKey)).toBe(false);
  });
});
