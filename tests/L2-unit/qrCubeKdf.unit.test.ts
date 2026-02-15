/**
 * @file qrCubeKdf.unit.test.ts
 * @module tests/L2-unit/qrCubeKdf
 * @layer Layer 12, Layer 13
 * @component Holographic QR Cube π^φ KDF — Unit Tests
 * @version 1.0.0
 *
 * Mirrors the Python contract tests (test_qr_cube_pi_phi_kdf.py):
 *   - Deterministic output for identical inputs
 *   - Input sensitivity (d*, coherence, cubeId, aad, nonce, salt, context)
 *   - Domain separation
 *   - Numeric hygiene (NaN, Inf, out-of-range coherence)
 *   - Output length control + HKDF prefix property
 *   - Avalanche smoke tests
 *   - Cross-language parity with Python reference
 */

import { describe, it, expect } from 'vitest';
import { derivePiPhiKey, piPhiScalar, type PiPhiKdfParams } from '../../src/harmonic/qrCubeKdf.js';

// =============================================================================
// HELPERS
// =============================================================================

const BASE_PARAMS: PiPhiKdfParams = {
  dStar: 0.25,
  coherence: 0.9,
  cubeId: 'cube-001',
  aad: Buffer.from('aad:header-hash'),
  nonce: Buffer.alloc(12, 0x01),
  salt: Buffer.alloc(32, 0x02),
  outLen: 32,
  context: Buffer.from('scbe:qr-cube:pi_phi:v1'),
};

function withOverrides(overrides: Partial<PiPhiKdfParams>): PiPhiKdfParams {
  return { ...BASE_PARAMS, ...overrides };
}

// =============================================================================
// CORE CONTRACT
// =============================================================================

describe('π^φ KDF — Core contract', () => {
  it('returns Buffer of expected length', () => {
    const key = derivePiPhiKey(BASE_PARAMS);
    expect(Buffer.isBuffer(key)).toBe(true);
    expect(key.length).toBe(32);
  });

  it('deterministic for same inputs', () => {
    const k1 = derivePiPhiKey(BASE_PARAMS);
    const k2 = derivePiPhiKey(BASE_PARAMS);
    expect(k1.equals(k2)).toBe(true);
  });

  it('changing dStar changes key', () => {
    const k1 = derivePiPhiKey(withOverrides({ dStar: 0.25 }));
    const k2 = derivePiPhiKey(withOverrides({ dStar: 0.35 }));
    expect(k1.equals(k2)).toBe(false);
  });

  it('changing coherence changes key', () => {
    const k1 = derivePiPhiKey(withOverrides({ coherence: 0.90 }));
    const k2 = derivePiPhiKey(withOverrides({ coherence: 0.91 }));
    expect(k1.equals(k2)).toBe(false);
  });

  it('changing cubeId changes key', () => {
    const k1 = derivePiPhiKey(withOverrides({ cubeId: 'cube-001' }));
    const k2 = derivePiPhiKey(withOverrides({ cubeId: 'cube-002' }));
    expect(k1.equals(k2)).toBe(false);
  });

  it('changing aad changes key', () => {
    const k1 = derivePiPhiKey(withOverrides({ aad: Buffer.from('aad:header-hash') }));
    const k2 = derivePiPhiKey(withOverrides({ aad: Buffer.from('aad:header-hash:mutated') }));
    expect(k1.equals(k2)).toBe(false);
  });

  it('changing nonce changes key', () => {
    const k1 = derivePiPhiKey(withOverrides({ nonce: Buffer.alloc(12, 0x01) }));
    const k2 = derivePiPhiKey(withOverrides({ nonce: Buffer.alloc(12, 0x03) }));
    expect(k1.equals(k2)).toBe(false);
  });

  it('changing salt changes key', () => {
    const k1 = derivePiPhiKey(withOverrides({ salt: Buffer.alloc(32, 0x02) }));
    const k2 = derivePiPhiKey(withOverrides({ salt: Buffer.alloc(32, 0x04) }));
    expect(k1.equals(k2)).toBe(false);
  });

  it('changing context changes key (domain separation)', () => {
    const k1 = derivePiPhiKey(withOverrides({ context: Buffer.from('scbe:qr-cube:pi_phi:v1') }));
    const k2 = derivePiPhiKey(
      withOverrides({ context: Buffer.from('scbe:sacred-egg:pi_phi:v1') }),
    );
    expect(k1.equals(k2)).toBe(false);
  });
});

// =============================================================================
// OUTPUT LENGTH + PREFIX PROPERTY
// =============================================================================

describe('π^φ KDF — Output length control', () => {
  it('out_len controls output size', () => {
    const k16 = derivePiPhiKey(withOverrides({ outLen: 16 }));
    const k32 = derivePiPhiKey(withOverrides({ outLen: 32 }));
    const k64 = derivePiPhiKey(withOverrides({ outLen: 64 }));
    expect(k16.length).toBe(16);
    expect(k32.length).toBe(32);
    expect(k64.length).toBe(64);
  });

  it('HKDF prefix property: shorter is prefix of longer', () => {
    const k16 = derivePiPhiKey(withOverrides({ outLen: 16 }));
    const k32 = derivePiPhiKey(withOverrides({ outLen: 32 }));
    const k64 = derivePiPhiKey(withOverrides({ outLen: 64 }));
    expect(k32.subarray(0, 16).equals(k16)).toBe(true);
    expect(k64.subarray(0, 32).equals(k32)).toBe(true);
  });
});

// =============================================================================
// NUMERIC HYGIENE
// =============================================================================

describe('π^φ KDF — Numeric hygiene', () => {
  for (const bad of [NaN, Infinity, -Infinity]) {
    it(`rejects non-finite dStar: ${bad}`, () => {
      expect(() => derivePiPhiKey(withOverrides({ dStar: bad }))).toThrow(/dStar|finite/);
    });
  }

  for (const bad of [NaN, Infinity, -Infinity]) {
    it(`rejects non-finite coherence: ${bad}`, () => {
      expect(() => derivePiPhiKey(withOverrides({ coherence: bad }))).toThrow(/coherence|finite/);
    });
  }

  it('rejects coherence > 1.0', () => {
    expect(() => derivePiPhiKey(withOverrides({ coherence: 1.5 }))).toThrow(/coherence|range/);
  });

  it('rejects coherence < 0.0', () => {
    expect(() => derivePiPhiKey(withOverrides({ coherence: -0.1 }))).toThrow(/coherence|range/);
  });

  it('accepts coherence at boundaries (0.0 and 1.0)', () => {
    expect(() => derivePiPhiKey(withOverrides({ coherence: 0.0 }))).not.toThrow();
    expect(() => derivePiPhiKey(withOverrides({ coherence: 1.0 }))).not.toThrow();
  });
});

// =============================================================================
// π^φ SCALAR
// =============================================================================

describe('π^φ scalar', () => {
  it('returns 1.0 at d*=0', () => {
    expect(piPhiScalar(0)).toBeCloseTo(1.0, 10);
  });

  it('monotonically increasing', () => {
    expect(piPhiScalar(0.1)).toBeLessThan(piPhiScalar(0.2));
    expect(piPhiScalar(0.2)).toBeLessThan(piPhiScalar(0.3));
    expect(piPhiScalar(0.5)).toBeLessThan(piPhiScalar(1.0));
  });

  it('π^φ ≈ 5.047 at d*=1', () => {
    const PHI = (1 + Math.sqrt(5)) / 2;
    expect(piPhiScalar(1)).toBeCloseTo(Math.PI ** PHI, 6);
  });
});

// =============================================================================
// AVALANCHE SMOKE
// =============================================================================

describe('π^φ KDF — Avalanche smoke', () => {
  it('single bit flip in aad changes key', () => {
    const aad1 = Buffer.from('aad:header-hash');
    const aad2 = Buffer.from(aad1);
    aad2[aad2.length - 1] ^= 0x01;

    const k1 = derivePiPhiKey(withOverrides({ aad: aad1 }));
    const k2 = derivePiPhiKey(withOverrides({ aad: aad2 }));
    expect(k1.equals(k2)).toBe(false);
  });

  it('25 random inputs produce 25 unique keys', () => {
    const seen = new Set<string>();
    for (let i = 0; i < 25; i++) {
      const key = derivePiPhiKey({
        dStar: 0.01 * (i + 1),
        coherence: Math.min(0.5 + 0.01 * i, 1.0),
        cubeId: `cube-${String(i).padStart(3, '0')}`,
        aad: Buffer.from(`aad-${i}`),
        nonce: Buffer.from(`nonce-${String(i).padStart(6, '0')}`),
        salt: Buffer.from(`salt-${String(i).padStart(26, '0')}`),
        outLen: 32,
      });
      const hex = key.toString('hex');
      expect(seen.has(hex)).toBe(false);
      seen.add(hex);
    }
  });
});

// =============================================================================
// CROSS-LANGUAGE PARITY
// =============================================================================

describe('π^φ KDF — Cross-language parity', () => {
  it('empty salt defaults to 32 zero bytes (matches Python)', () => {
    const k1 = derivePiPhiKey(withOverrides({ salt: Buffer.alloc(0) }));
    const k2 = derivePiPhiKey(withOverrides({ salt: undefined }));
    expect(k1.equals(k2)).toBe(true);
  });

  it('byte-for-byte parity: vector 1 (k16)', () => {
    const key = derivePiPhiKey(withOverrides({ outLen: 16 }));
    expect(key.toString('hex')).toBe('434715c507c065d3a4943fd5134e3664');
  });

  it('byte-for-byte parity: vector 1 (k32)', () => {
    const key = derivePiPhiKey(withOverrides({ outLen: 32 }));
    expect(key.toString('hex')).toBe(
      '434715c507c065d3a4943fd5134e36641dd4a12736685caf942f125425eeff5a',
    );
  });

  it('byte-for-byte parity: vector 1 (k64)', () => {
    const key = derivePiPhiKey(withOverrides({ outLen: 64 }));
    expect(key.toString('hex')).toBe(
      '434715c507c065d3a4943fd5134e3664' +
        '1dd4a12736685caf942f125425eeff5a' +
        'ba98bee3e6cf55818708bf232dc457c9' +
        'c66108d85cfaaead35e5e0790ee9ad53',
    );
  });

  it('byte-for-byte parity: vector 2 (different d_star/coherence/cube_id)', () => {
    const key = derivePiPhiKey(
      withOverrides({ dStar: 1.0, coherence: 0.5, cubeId: 'cube-999', outLen: 32 }),
    );
    expect(key.toString('hex')).toBe(
      '39627b7e61364c07dbcc9d9cf653d67b3ca5f7ddc105b0bbdf53eedccad78756',
    );
  });
});
