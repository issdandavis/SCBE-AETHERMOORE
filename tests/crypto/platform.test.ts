/**
 * @file platform.test.ts
 * @module tests/crypto/platform
 * @component Platform-Agnostic Crypto Primitives Tests
 *
 * Groups:
 *   A: Runtime detection (3 tests)
 *   B: UUID generation (6 tests)
 *   C: Random bytes (5 tests)
 *   D: SHA-256 hashing (4 tests)
 *   E: Constant-time comparison (4 tests)
 */

import { describe, it, expect } from 'vitest';
import {
  detectRuntime,
  platformRandomUUID,
  platformRandomBytes,
  platformSHA256,
  platformSHA256Async,
  constantTimeEqual,
} from '../../src/crypto/platform.js';

// ═══════════════════════════════════════════════════════════════
// A: Runtime Detection
// ═══════════════════════════════════════════════════════════════

describe('A — Runtime Detection', () => {
  it('A1: detects Node.js runtime', () => {
    const runtime = detectRuntime();
    // In test environment (Node.js), should detect web or node
    expect(['web', 'node']).toContain(runtime);
  });

  it('A2: runtime is never "none" in test environment', () => {
    expect(detectRuntime()).not.toBe('none');
  });

  it('A3: returns consistent results', () => {
    const r1 = detectRuntime();
    const r2 = detectRuntime();
    expect(r1).toBe(r2);
  });
});

// ═══════════════════════════════════════════════════════════════
// B: UUID Generation
// ═══════════════════════════════════════════════════════════════

describe('B — UUID Generation', () => {
  it('B1: generates valid UUID v4 format', () => {
    const uuid = platformRandomUUID();
    // UUID v4: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
    expect(uuid).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
  });

  it('B2: generates unique UUIDs', () => {
    const uuids = new Set<string>();
    for (let i = 0; i < 100; i++) {
      uuids.add(platformRandomUUID());
    }
    expect(uuids.size).toBe(100);
  });

  it('B3: UUID has correct length', () => {
    const uuid = platformRandomUUID();
    expect(uuid).toHaveLength(36);
  });

  it('B4: UUID version nibble is 4', () => {
    const uuid = platformRandomUUID();
    expect(uuid[14]).toBe('4');
  });

  it('B5: UUID variant nibble is 8, 9, a, or b', () => {
    const uuid = platformRandomUUID();
    expect(['8', '9', 'a', 'b']).toContain(uuid[19]);
  });

  it('B6: UUID is lowercase hex', () => {
    const uuid = platformRandomUUID();
    expect(uuid.replace(/-/g, '')).toMatch(/^[0-9a-f]{32}$/);
  });
});

// ═══════════════════════════════════════════════════════════════
// C: Random Bytes
// ═══════════════════════════════════════════════════════════════

describe('C — Random Bytes', () => {
  it('C1: generates correct length', () => {
    const bytes = platformRandomBytes(32);
    expect(bytes).toHaveLength(32);
    expect(bytes).toBeInstanceOf(Uint8Array);
  });

  it('C2: zero length returns empty array', () => {
    const bytes = platformRandomBytes(0);
    expect(bytes).toHaveLength(0);
  });

  it('C3: generates different bytes each time', () => {
    const a = platformRandomBytes(32);
    const b = platformRandomBytes(32);
    // Probability of collision is astronomically small
    const same = a.every((v, i) => v === b[i]);
    expect(same).toBe(false);
  });

  it('C4: handles large requests', () => {
    const bytes = platformRandomBytes(1024);
    expect(bytes).toHaveLength(1024);
  });

  it('C5: bytes are in valid range [0, 255]', () => {
    const bytes = platformRandomBytes(256);
    for (const b of bytes) {
      expect(b).toBeGreaterThanOrEqual(0);
      expect(b).toBeLessThanOrEqual(255);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// D: SHA-256 Hashing
// ═══════════════════════════════════════════════════════════════

describe('D — SHA-256', () => {
  it('D1: produces correct hash for known input', () => {
    // SHA-256("hello") = 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824
    const hash = platformSHA256('hello');
    expect(hash).toBe('2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824');
  });

  it('D2: produces 64-character hex string', () => {
    const hash = platformSHA256('test data');
    expect(hash).toHaveLength(64);
    expect(hash).toMatch(/^[0-9a-f]{64}$/);
  });

  it('D3: deterministic (same input = same output)', () => {
    const h1 = platformSHA256('deterministic');
    const h2 = platformSHA256('deterministic');
    expect(h1).toBe(h2);
  });

  it('D4: async version matches sync', async () => {
    const sync = platformSHA256('async test');
    const async_ = await platformSHA256Async('async test');
    expect(async_).toBe(sync);
  });
});

// ═══════════════════════════════════════════════════════════════
// E: Constant-Time Comparison
// ═══════════════════════════════════════════════════════════════

describe('E — Constant-Time Comparison', () => {
  it('E1: equal arrays return true', () => {
    const a = new Uint8Array([1, 2, 3, 4, 5]);
    const b = new Uint8Array([1, 2, 3, 4, 5]);
    expect(constantTimeEqual(a, b)).toBe(true);
  });

  it('E2: different arrays return false', () => {
    const a = new Uint8Array([1, 2, 3, 4, 5]);
    const b = new Uint8Array([1, 2, 3, 4, 6]);
    expect(constantTimeEqual(a, b)).toBe(false);
  });

  it('E3: different lengths return false', () => {
    const a = new Uint8Array([1, 2, 3]);
    const b = new Uint8Array([1, 2, 3, 4]);
    expect(constantTimeEqual(a, b)).toBe(false);
  });

  it('E4: empty arrays are equal', () => {
    const a = new Uint8Array([]);
    const b = new Uint8Array([]);
    expect(constantTimeEqual(a, b)).toBe(true);
  });
});
