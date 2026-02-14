/**
 * @file pqc-strategies.test.ts
 * @module tests/crypto/pqc-strategies
 * @layer Layer 4, Layer 5, Layer 13
 *
 * Tests for PQC strategy profiles, TriStitch combiner, and geometric key binding.
 * 68 tests across 9 groups (A-I).
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import {
  // Strategy catalog
  STRATEGY_CATALOG,
  getStrategy,
  registerStrategy,
  listStrategyNames,
  clearCustomStrategies,
  type PQCStrategy,
  // TriStitch
  triStitch,
  type TriStitchResult,
  // Geometric binding
  geometricFingerprint,
  bindKeyToGeometry,
  verifyGeometricBinding,
  type GeoBoundKey,
  // Strategy executor
  executeStrategy,
  signWithStrategy,
  type StrategyExecutionResult,
} from '../../src/crypto/pqc-strategies.js';
import { clearRegistry } from '../../src/crypto/quantum-safe.js';

// Helper: create a mock 21D brain state
function mock21D(seed: number = 42): number[] {
  const state: number[] = [];
  let x = seed;
  for (let i = 0; i < 21; i++) {
    x = ((x * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
    state.push(x * 0.8 - 0.4); // Range [-0.4, 0.4] (inside Poincaré ball)
  }
  return state;
}

// ═══════════════════════════════════════════════════════════════
// A. Strategy Catalog
// ═══════════════════════════════════════════════════════════════

describe('A. Strategy Catalog', () => {
  it('should have 4 built-in strategies', () => {
    expect(Object.keys(STRATEGY_CATALOG)).toHaveLength(4);
  });

  it('balanced-v1 should use single lattice KEM + lattice sig', () => {
    const s = STRATEGY_CATALOG['balanced-v1'];
    expect(s.kemAlgorithms).toEqual(['ML-KEM-768']);
    expect(s.sigAlgorithm).toBe('ML-DSA-65');
    expect(s.classicalHybrid).toBe(true);
    expect(s.families).toContain('lattice');
  });

  it('paranoid-v1 should use 3-family TriStitch', () => {
    const s = STRATEGY_CATALOG['paranoid-v1'];
    expect(s.kemAlgorithms).toHaveLength(3);
    expect(s.sigAlgorithm).toBe('SLH-DSA-256s');
    expect(s.families).toContain('lattice');
    expect(s.families).toContain('code-based');
    expect(s.families).toContain('hash-based');
    expect(s.minNistLevel).toBe(5);
  });

  it('conservative-v1 should mix lattice KEM + hash-based sig', () => {
    const s = STRATEGY_CATALOG['conservative-v1'];
    expect(s.kemAlgorithms).toEqual(['ML-KEM-768']);
    expect(s.sigAlgorithm).toBe('SLH-DSA-128s');
    expect(s.families).toContain('lattice');
    expect(s.families).toContain('hash-based');
  });

  it('iot-v1 should be lightweight, no classical hybrid', () => {
    const s = STRATEGY_CATALOG['iot-v1'];
    expect(s.kemAlgorithms).toEqual(['ML-KEM-512']);
    expect(s.sigAlgorithm).toBe('ML-DSA-44');
    expect(s.classicalHybrid).toBe(false);
    expect(s.minNistLevel).toBe(1);
  });

  it('all strategies should have name, description, and useCase', () => {
    for (const [name, s] of Object.entries(STRATEGY_CATALOG)) {
      expect(s.name).toBe(name);
      expect(s.description.length).toBeGreaterThan(10);
      expect(s.useCase.length).toBeGreaterThan(10);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// B. Strategy Registry
// ═══════════════════════════════════════════════════════════════

describe('B. Strategy Registry', () => {
  afterEach(() => clearCustomStrategies());

  it('getStrategy should return built-in strategy', () => {
    const s = getStrategy('balanced-v1');
    expect(s.name).toBe('balanced-v1');
  });

  it('getStrategy should throw for unknown', () => {
    expect(() => getStrategy('nonexistent')).toThrow('Unknown PQC strategy');
  });

  it('registerStrategy should add custom strategy', () => {
    const custom: PQCStrategy = {
      name: 'test-v1',
      description: 'Test strategy',
      kemAlgorithms: ['ML-KEM-512'],
      sigAlgorithm: 'ML-DSA-44',
      classicalHybrid: false,
      minNistLevel: 1,
      useCase: 'testing',
      families: ['lattice'],
    };
    registerStrategy(custom);
    expect(getStrategy('test-v1')).toBe(custom);
  });

  it('custom strategy should override built-in with same name', () => {
    const override: PQCStrategy = {
      ...STRATEGY_CATALOG['balanced-v1'],
      description: 'Override!',
    };
    registerStrategy(override);
    expect(getStrategy('balanced-v1').description).toBe('Override!');
  });

  it('listStrategyNames should include built-in + custom', () => {
    registerStrategy({
      name: 'my-custom',
      description: 'x',
      kemAlgorithms: ['ML-KEM-512'],
      sigAlgorithm: 'ML-DSA-44',
      classicalHybrid: false,
      minNistLevel: 1,
      useCase: 'x',
      families: ['lattice'],
    });
    const names = listStrategyNames();
    expect(names).toContain('balanced-v1');
    expect(names).toContain('my-custom');
  });

  it('clearCustomStrategies should remove custom only', () => {
    registerStrategy({
      name: 'temp',
      description: 'x',
      kemAlgorithms: ['ML-KEM-512'],
      sigAlgorithm: 'ML-DSA-44',
      classicalHybrid: false,
      minNistLevel: 1,
      useCase: 'x',
      families: ['lattice'],
    });
    clearCustomStrategies();
    expect(() => getStrategy('temp')).toThrow();
    expect(getStrategy('balanced-v1')).toBeDefined(); // Built-in still works
  });
});

// ═══════════════════════════════════════════════════════════════
// C. TriStitch — Single KEM
// ═══════════════════════════════════════════════════════════════

describe('C. TriStitch — Single KEM', () => {
  beforeEach(() => clearRegistry());
  afterEach(() => clearRegistry());

  it('single KEM should produce 32-byte combined secret', async () => {
    const { result } = await triStitch(['ML-KEM-768']);
    expect(result.combinedSecret.length).toBe(32);
    expect(result.kemResults).toHaveLength(1);
    expect(result.familyCount).toBe(1);
  });

  it('single KEM with classical should flag classicalComponent', async () => {
    const { result } = await triStitch(['ML-KEM-768'], true);
    expect(result.classicalComponent).toBe(true);
  });

  it('single KEM without classical should flag accordingly', async () => {
    const { result } = await triStitch(['ML-KEM-768'], false);
    expect(result.classicalComponent).toBe(false);
  });

  it('should return key pairs matching KEM count', async () => {
    const { keyPairs } = await triStitch(['ML-KEM-768']);
    expect(keyPairs).toHaveLength(1);
    expect(keyPairs[0].publicKey.length).toBe(1184);
  });
});

// ═══════════════════════════════════════════════════════════════
// D. TriStitch — Multi-KEM (3-Family)
// ═══════════════════════════════════════════════════════════════

describe('D. TriStitch — Multi-KEM', () => {
  beforeEach(() => clearRegistry());
  afterEach(() => clearRegistry());

  it('3 KEMs should produce combined secret', async () => {
    const { result } = await triStitch(
      ['ML-KEM-768', 'Classic-McEliece-348864', 'ML-KEM-1024'],
      false
    );
    expect(result.combinedSecret.length).toBe(32);
    expect(result.kemResults).toHaveLength(3);
  });

  it('3-family stitch should report 2 distinct families', async () => {
    // ML-KEM-768 (lattice) + McEliece (code-based) + ML-KEM-1024 (lattice)
    const { result } = await triStitch(
      ['ML-KEM-768', 'Classic-McEliece-348864', 'ML-KEM-1024']
    );
    expect(result.familyCount).toBe(2); // lattice + code-based
  });

  it('audit trail should include per-KEM algorithm + family', async () => {
    const { result } = await triStitch(['ML-KEM-768', 'ML-KEM-512']);
    expect(result.kemResults[0].algorithm).toBe('ML-KEM-768');
    expect(result.kemResults[0].family).toBe('lattice');
    expect(result.kemResults[1].algorithm).toBe('ML-KEM-512');
  });

  it('different KEM combos should produce different secrets', async () => {
    const { result: r1 } = await triStitch(['ML-KEM-768'], false);
    const { result: r2 } = await triStitch(['ML-KEM-768', 'ML-KEM-512'], false);
    expect(Buffer.from(r1.combinedSecret).equals(Buffer.from(r2.combinedSecret))).toBe(false);
  });

  it('should reject empty KEM list', async () => {
    await expect(triStitch([])).rejects.toThrow('at least one');
  });

  it('should reject more than 4 KEMs', async () => {
    await expect(
      triStitch(['ML-KEM-512', 'ML-KEM-768', 'ML-KEM-1024', 'Classic-McEliece-348864', 'ML-KEM-512'])
    ).rejects.toThrow('at most 4');
  });
});

// ═══════════════════════════════════════════════════════════════
// E. Geometric Fingerprint
// ═══════════════════════════════════════════════════════════════

describe('E. Geometric Fingerprint', () => {
  it('should produce 32-byte fingerprint', () => {
    const fp = geometricFingerprint(mock21D());
    expect(fp.length).toBe(32);
  });

  it('same state should produce same fingerprint', () => {
    const fp1 = geometricFingerprint(mock21D(42));
    const fp2 = geometricFingerprint(mock21D(42));
    expect(Buffer.from(fp1).equals(Buffer.from(fp2))).toBe(true);
  });

  it('different state should produce different fingerprint', () => {
    const fp1 = geometricFingerprint(mock21D(42));
    const fp2 = geometricFingerprint(mock21D(99));
    expect(Buffer.from(fp1).equals(Buffer.from(fp2))).toBe(false);
  });

  it('should be sensitive to tiny changes (decimal drift)', () => {
    const state = mock21D(42);
    const perturbed = [...state];
    perturbed[10] += 1e-15; // Tiny perturbation
    const fp1 = geometricFingerprint(state);
    const fp2 = geometricFingerprint(perturbed);
    expect(Buffer.from(fp1).equals(Buffer.from(fp2))).toBe(false);
  });

  it('should handle empty state', () => {
    const fp = geometricFingerprint([]);
    expect(fp.length).toBe(32); // SHA-256 of empty buffer
  });

  it('should handle non-21D state (any dimension)', () => {
    const fp = geometricFingerprint([0.1, 0.2, 0.3]);
    expect(fp.length).toBe(32);
  });
});

// ═══════════════════════════════════════════════════════════════
// F. Geometric Key Binding
// ═══════════════════════════════════════════════════════════════

describe('F. Geometric Key Binding', () => {
  const mockSecret = new Uint8Array(32);
  mockSecret.fill(0xab);

  it('should produce 32-byte bound key', () => {
    const result = bindKeyToGeometry(mockSecret, mock21D());
    expect(result.boundKey.length).toBe(32);
  });

  it('should produce 32-byte geo fingerprint', () => {
    const result = bindKeyToGeometry(mockSecret, mock21D());
    expect(result.geoFingerprint.length).toBe(32);
  });

  it('should produce 16-char hex keyId', () => {
    const result = bindKeyToGeometry(mockSecret, mock21D());
    expect(result.keyId).toHaveLength(16);
    expect(/^[0-9a-f]{16}$/.test(result.keyId)).toBe(true);
  });

  it('should compute state norm', () => {
    const result = bindKeyToGeometry(mockSecret, mock21D());
    expect(result.stateNorm).toBeGreaterThan(0);
    expect(result.stateNorm).toBeLessThan(10);
  });

  it('same inputs should produce same bound key', () => {
    const r1 = bindKeyToGeometry(mockSecret, mock21D(42));
    const r2 = bindKeyToGeometry(mockSecret, mock21D(42));
    expect(Buffer.from(r1.boundKey).equals(Buffer.from(r2.boundKey))).toBe(true);
    expect(r1.keyId).toBe(r2.keyId);
  });

  it('different state should produce different bound key', () => {
    const r1 = bindKeyToGeometry(mockSecret, mock21D(42));
    const r2 = bindKeyToGeometry(mockSecret, mock21D(99));
    expect(Buffer.from(r1.boundKey).equals(Buffer.from(r2.boundKey))).toBe(false);
  });

  it('different secret should produce different bound key', () => {
    const secret2 = new Uint8Array(32);
    secret2.fill(0xcd);
    const r1 = bindKeyToGeometry(mockSecret, mock21D());
    const r2 = bindKeyToGeometry(secret2, mock21D());
    expect(Buffer.from(r1.boundKey).equals(Buffer.from(r2.boundKey))).toBe(false);
  });

  it('should respect custom domain', () => {
    const r1 = bindKeyToGeometry(mockSecret, mock21D(), { domain: 'custom:v1' });
    const r2 = bindKeyToGeometry(mockSecret, mock21D(), { domain: 'custom:v2' });
    expect(Buffer.from(r1.boundKey).equals(Buffer.from(r2.boundKey))).toBe(false);
  });

  it('should differ with/without norm in info', () => {
    const r1 = bindKeyToGeometry(mockSecret, mock21D(), { includeNorm: true });
    const r2 = bindKeyToGeometry(mockSecret, mock21D(), { includeNorm: false });
    expect(Buffer.from(r1.boundKey).equals(Buffer.from(r2.boundKey))).toBe(false);
  });

  it('should differ with/without phase in info', () => {
    const r1 = bindKeyToGeometry(mockSecret, mock21D(), { includePhase: true });
    const r2 = bindKeyToGeometry(mockSecret, mock21D(), { includePhase: false });
    expect(Buffer.from(r1.boundKey).equals(Buffer.from(r2.boundKey))).toBe(false);
  });
});

// ═══════════════════════════════════════════════════════════════
// G. Geometric Binding Verification
// ═══════════════════════════════════════════════════════════════

describe('G. Geometric Binding Verification', () => {
  const secret = new Uint8Array(32);
  secret.fill(0x42);
  const state = mock21D(77);

  it('should verify matching state', () => {
    const bound = bindKeyToGeometry(secret, state);
    expect(verifyGeometricBinding(bound.boundKey, secret, state)).toBe(true);
  });

  it('should reject different state', () => {
    const bound = bindKeyToGeometry(secret, state);
    expect(verifyGeometricBinding(bound.boundKey, secret, mock21D(88))).toBe(false);
  });

  it('should reject different secret', () => {
    const bound = bindKeyToGeometry(secret, state);
    const wrongSecret = new Uint8Array(32);
    wrongSecret.fill(0xff);
    expect(verifyGeometricBinding(bound.boundKey, wrongSecret, state)).toBe(false);
  });

  it('should reject wrong-length key', () => {
    expect(verifyGeometricBinding(new Uint8Array(16), secret, state)).toBe(false);
  });

  it('should be sensitive to 1-bit state change', () => {
    const bound = bindKeyToGeometry(secret, state);
    const perturbed = [...state];
    perturbed[0] += 1e-15;
    expect(verifyGeometricBinding(bound.boundKey, secret, perturbed)).toBe(false);
  });
});

// ═══════════════════════════════════════════════════════════════
// H. Strategy Execution
// ═══════════════════════════════════════════════════════════════

describe('H. Strategy Execution', () => {
  beforeEach(() => clearRegistry());
  afterEach(() => { clearRegistry(); clearCustomStrategies(); });

  it('balanced-v1 should execute with single KEM', async () => {
    const result = await executeStrategy('balanced-v1', mock21D());
    expect(result.strategyName).toBe('balanced-v1');
    expect(result.boundKey.boundKey.length).toBe(32);
    expect(result.triStitch.kemResults).toHaveLength(1);
    expect(result.sigAlgorithm).toBe('ML-DSA-65');
    expect(result.families).toContain('lattice');
  });

  it('paranoid-v1 should execute with 3 KEMs', async () => {
    const result = await executeStrategy('paranoid-v1', mock21D());
    expect(result.triStitch.kemResults).toHaveLength(3);
    expect(result.sigAlgorithm).toBe('SLH-DSA-256s');
    expect(result.families).toContain('code-based');
    expect(result.families).toContain('hash-based');
  });

  it('iot-v1 should execute without classical hybrid', async () => {
    const result = await executeStrategy('iot-v1', mock21D());
    expect(result.triStitch.classicalComponent).toBe(false);
  });

  it('should produce unique executions per call', async () => {
    const r1 = await executeStrategy('balanced-v1', mock21D(42));
    const r2 = await executeStrategy('balanced-v1', mock21D(42));
    // Different random KEM seeds → different secrets → different bound keys
    expect(Buffer.from(r1.boundKey.boundKey).equals(Buffer.from(r2.boundKey.boundKey))).toBe(false);
  });

  it('different states should produce different bound keys', async () => {
    const r1 = await executeStrategy('balanced-v1', mock21D(42));
    const r2 = await executeStrategy('balanced-v1', mock21D(99));
    expect(Buffer.from(r1.boundKey.boundKey).equals(Buffer.from(r2.boundKey.boundKey))).toBe(false);
  });

  it('should include timestamp', async () => {
    const before = Date.now();
    const result = await executeStrategy('balanced-v1', mock21D());
    expect(result.timestamp).toBeGreaterThanOrEqual(before);
    expect(result.timestamp).toBeLessThanOrEqual(Date.now());
  });

  it('should produce valid sig key pair', async () => {
    const result = await executeStrategy('balanced-v1', mock21D());
    expect(result.sigKeyPair.publicKey.length).toBe(1952); // ML-DSA-65
    expect(result.sigKeyPair.secretKey.length).toBe(4032);
  });
});

// ═══════════════════════════════════════════════════════════════
// I. Strategy Signing
// ═══════════════════════════════════════════════════════════════

describe('I. Strategy Signing', () => {
  beforeEach(() => clearRegistry());
  afterEach(() => clearRegistry());

  it('should sign governance decisions', async () => {
    const execution = await executeStrategy('balanced-v1', mock21D());
    const message = new TextEncoder().encode('ALLOW agent-007 escalation');
    const sig = await signWithStrategy(message, execution);
    expect(sig.length).toBe(3293); // ML-DSA-65 signature size
  });

  it('should sign with hash-based sig when paranoid', async () => {
    const execution = await executeStrategy('paranoid-v1', mock21D());
    const message = new TextEncoder().encode('DENY hostile-agent');
    const sig = await signWithStrategy(message, execution);
    expect(sig.length).toBe(29792); // SLH-DSA-256s
  });

  it('should sign with lightweight sig for iot', async () => {
    const execution = await executeStrategy('iot-v1', mock21D());
    const message = new TextEncoder().encode('QUARANTINE edge-device-3');
    const sig = await signWithStrategy(message, execution);
    expect(sig.length).toBe(2420); // ML-DSA-44
  });
});
