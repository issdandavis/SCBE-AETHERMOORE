/**
 * @file pqc.test.ts
 * @module tests/crypto/pqc
 */

import { describe, expect, it, vi } from 'vitest';

type PQCModule = typeof import('../../src/crypto/pqc.js');

async function loadPQCWithMock(mockModule: Record<string, any>): Promise<PQCModule> {
  vi.resetModules();
  vi.doMock('liboqs-node', () => mockModule);
  return import('../../src/crypto/pqc.js');
}

function createNativePQCMock() {
  const sharedSecret = new Uint8Array(32).fill(0x19);
  const nativeSharedSecret = new Uint8Array(sharedSecret);

  class MockKEM {
    constructor(_algorithm: unknown) {}

    generateKeyPair(): [Uint8Array, Uint8Array] {
      return [new Uint8Array(1184).fill(0x11), new Uint8Array(2400).fill(0x22)];
    }

    encapsulate(_publicKey: Uint8Array): [Uint8Array, Uint8Array] {
      return [new Uint8Array(1088).fill(0x33), new Uint8Array(32).fill(0x44)];
    }

    decapsulate(_ciphertext: Uint8Array, _secretKey: Uint8Array): Uint8Array {
      return nativeSharedSecret;
    }
  }

  class MockSignature {
    constructor(_algorithm: unknown) {}

    generateKeyPair(): [Uint8Array, Uint8Array] {
      return [new Uint8Array(1952).fill(0x55), new Uint8Array(4032).fill(0x66)];
    }

    sign(_message: Uint8Array, _secretKey: Uint8Array): Uint8Array {
      return new Uint8Array(3293).fill(0x77);
    }

    verify(message: Uint8Array, _signature: Uint8Array, _publicKey: Uint8Array): boolean {
      return message.length > 0;
    }
  }

  return { KEM: MockKEM, Signature: MockSignature };
}

describe('PQC module status and lattice metadata', () => {
  it('exposes the lattice-rank shape used by triadic flow systems', async () => {
    const pqc = await loadPQCWithMock({});
    expect(pqc.ML_KEM_768_PARAMS.k).toBe(3);
    expect(pqc.ML_DSA_65_PARAMS.k).toBe(6);
  });

  it.skipIf(!(() => { try { require.resolve('liboqs-node'); return true; } catch { return false; } })())('reports stub status when native constructors are missing', async () => {
    const pqc = await loadPQCWithMock({});
    const status = pqc.getPQCStatus();
    expect(status.available).toBe(false);
    expect(status.implementation).toBe('stub');
    expect(status.moduleName).toBe('liboqs-node');
    expect(status.reason).toContain('does not expose a usable ML-KEM interface');
  });

  it.skipIf(!(() => { try { require.resolve('liboqs-node'); return true; } catch { return false; } })())('parses native decapsulation output even when backend returns raw shared secret bytes', async () => {
    const pqc = await loadPQCWithMock(createNativePQCMock());
    const status = pqc.getPQCStatus();
    expect(status.available).toBe(true);

    const kem = pqc.MLKEM768.getInstance();
    const keyPair = await kem.generateKeyPair();
    const { ciphertext } = await kem.encapsulate(keyPair.publicKey);
    const sharedSecret = await kem.decapsulate(ciphertext, keyPair.secretKey);

    expect(sharedSecret.length).toBe(32);
    expect(sharedSecret).toEqual(new Uint8Array(32).fill(0x19));
  });
});
