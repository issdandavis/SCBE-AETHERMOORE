/**
 * @file governanceSim.unit.test.ts
 * @module tests/L2-unit/governanceSim
 * @layer Layer 5, Layer 12, Layer 13
 * @component Governance Simulation Helper Tests
 * @version 3.2.4
 *
 * Tests for Poincaré ball geometry, NK coherence, BFT consensus,
 * Layer 12 cost, voxel encoding, and Sacred Egg HMAC signing.
 * Mirrors tests/test_layer12_voxel.py for backend parity.
 */

import { describe, it, expect } from 'vitest';
import {
  clamp,
  wrapPi,
  quantize,
  coherenceFromPhases,
  driftStar,
  layer12Cost,
  poincareDist,
  invMetricFactor,
  localVote,
  bftConsensus,
  governanceTick,
  encodeVoxelKey,
  eggSign,
  commitVoxel,
  GovernanceSimState,
  DANGER_QUORUM,
  COMMIT_EVERY,
  type Point3D,
  type VoxelBase,
  type SimVoxelRecord,
} from '../../src/harmonic/governanceSim.js';
import type { Lang, Decision } from '../../src/harmonic/scbe_voxel_types.js';

const ORIGIN: Point3D = { x: 0, y: 0, z: 0 };
const BALANCED_WEIGHTS: Record<string, number> = {
  KO: 1, AV: 1, RU: 1, CA: 1, UM: 1, DR: 1,
};
const ALIGNED_PHASES: Record<string, number> = {
  KO: 0, AV: 0, RU: 0, CA: 0, UM: 0, DR: 0,
};

// ═══════════════════════════════════════════════════════════════
// coherenceFromPhases
// ═══════════════════════════════════════════════════════════════

describe('coherenceFromPhases', () => {
  it('all equal phases → 1.0', () => {
    const phases = { KO: 0.25, AV: 0.25, RU: 0.25, CA: 0.25, UM: 0.25, DR: 0.25 };
    expect(coherenceFromPhases(phases)).toBeCloseTo(1.0, 10);
  });

  it('all zero → 1.0', () => {
    expect(coherenceFromPhases(ALIGNED_PHASES)).toBeCloseTo(1.0, 10);
  });

  it('alternating phases → -0.2', () => {
    const phases = { KO: 0, AV: 0, RU: 0, CA: Math.PI, UM: Math.PI, DR: Math.PI };
    expect(coherenceFromPhases(phases)).toBeCloseTo(-0.2, 10);
  });

  it('range bounded [-1, 1]', () => {
    const phases = { KO: 0, AV: Math.PI, RU: 0, CA: Math.PI, UM: 0, DR: Math.PI };
    const c = coherenceFromPhases(phases);
    expect(c).toBeGreaterThanOrEqual(-1);
    expect(c).toBeLessThanOrEqual(1);
  });
});

// ═══════════════════════════════════════════════════════════════
// quantize
// ═══════════════════════════════════════════════════════════════

describe('quantize', () => {
  it('endpoints', () => {
    expect(quantize(-3, -3, 3, 24)).toBe(0);
    expect(quantize(3, -3, 3, 24)).toBe(23);
    expect(quantize(999, -3, 3, 24)).toBe(23);
    expect(quantize(-999, -3, 3, 24)).toBe(0);
  });

  it('monotone non-decreasing', () => {
    let last = -1;
    for (let v = -30; v <= 30; v++) {
      const q = quantize(v / 10, -3, 3, 24);
      expect(q).toBeGreaterThanOrEqual(last);
      last = q;
    }
  });

  it('midpoint', () => {
    expect(quantize(0, -3, 3, 24)).toBe(12);
  });

  it('single bin always 0', () => {
    expect(quantize(5, 0, 10, 1)).toBe(0);
  });

  it('two bins', () => {
    expect(quantize(0, 0, 10, 2)).toBe(0);
    expect(quantize(10, 0, 10, 2)).toBe(1);
  });
});

// ═══════════════════════════════════════════════════════════════
// driftStar
// ═══════════════════════════════════════════════════════════════

describe('driftStar', () => {
  it('increases with radius', () => {
    const d1 = driftStar({ x: 0.1, y: 0, z: 0 }, BALANCED_WEIGHTS);
    const d2 = driftStar({ x: 1.0, y: 0, z: 0 }, BALANCED_WEIGHTS);
    expect(d2).toBeGreaterThan(d1);
  });

  it('penalizes imbalance', () => {
    const p: Point3D = { x: 1, y: 0, z: 0 };
    const wBal = BALANCED_WEIGHTS;
    const wImb = { KO: 6, AV: 0.1, RU: 0.1, CA: 0.1, UM: 0.1, DR: 0.1 };
    expect(driftStar(p, wImb)).toBeGreaterThan(driftStar(p, wBal));
  });

  it('origin → 0', () => {
    expect(driftStar(ORIGIN, BALANCED_WEIGHTS)).toBe(0);
  });

  it('balanced weights factor = 1.25', () => {
    // max/sum = 1/6, factor = 1 + 1.5*(1/6) = 1.25
    expect(driftStar({ x: 1, y: 0, z: 0 }, BALANCED_WEIGHTS)).toBeCloseTo(1.25);
  });
});

// ═══════════════════════════════════════════════════════════════
// layer12Cost
// ═══════════════════════════════════════════════════════════════

describe('layer12Cost', () => {
  it('monotone in d*', () => {
    const c = 1.0;
    expect(layer12Cost(0.1, c)).toBeLessThan(layer12Cost(0.2, c));
    expect(layer12Cost(0.2, c)).toBeLessThan(layer12Cost(0.3, c));
  });

  it('increases when coherence drops', () => {
    const d = 0.6;
    expect(layer12Cost(d, 1.0)).toBeLessThan(layer12Cost(d, 0.5));
    expect(layer12Cost(d, 0.5)).toBeLessThan(layer12Cost(d, 0.0));
  });

  it('at origin with full coherence = 1', () => {
    expect(layer12Cost(0, 1.0)).toBeCloseTo(1.0);
  });

  it('super-exponential growth at d*=3', () => {
    expect(layer12Cost(3.0, 0.5)).toBeGreaterThan(100);
  });

  it('coherence penalty doubles cost (C=0 vs C=1)', () => {
    const ratio = layer12Cost(1, 0) / layer12Cost(1, 1);
    expect(ratio).toBeCloseTo(2.0);
  });
});

// ═══════════════════════════════════════════════════════════════
// Poincaré distance
// ═══════════════════════════════════════════════════════════════

describe('poincareDist', () => {
  it('same point = 0', () => {
    const p: Point3D = { x: 1, y: 1, z: 1 };
    expect(poincareDist(p, p)).toBeCloseTo(0, 8);
  });

  it('symmetric', () => {
    const a: Point3D = { x: 0.5, y: 0, z: 0 };
    const b: Point3D = { x: 0, y: 0.5, z: 0 };
    expect(poincareDist(a, b)).toBeCloseTo(poincareDist(b, a));
  });

  it('increases with separation', () => {
    const d1 = poincareDist(ORIGIN, { x: 0.5, y: 0, z: 0 });
    const d2 = poincareDist(ORIGIN, { x: 1.5, y: 0, z: 0 });
    expect(d2).toBeGreaterThan(d1);
  });

  it('origin to origin = 0', () => {
    expect(poincareDist(ORIGIN, ORIGIN)).toBeCloseTo(0, 12);
  });

  it('triangle inequality', () => {
    const a: Point3D = { x: 0.3, y: 0, z: 0 };
    const b: Point3D = { x: 0, y: 0.3, z: 0 };
    const c: Point3D = { x: 0, y: 0, z: 0.3 };
    const dab = poincareDist(a, b);
    const dbc = poincareDist(b, c);
    const dac = poincareDist(a, c);
    expect(dac).toBeLessThanOrEqual(dab + dbc + 1e-10);
  });
});

// ═══════════════════════════════════════════════════════════════
// invMetricFactor
// ═══════════════════════════════════════════════════════════════

describe('invMetricFactor', () => {
  it('at origin = 0.25', () => {
    expect(invMetricFactor(ORIGIN)).toBeCloseTo(0.25);
  });

  it('decreases away from origin', () => {
    const f0 = invMetricFactor(ORIGIN);
    const f1 = invMetricFactor({ x: 1, y: 0, z: 0 });
    expect(f1).toBeLessThan(f0);
  });

  it('always positive', () => {
    for (const x of [0, 0.5, 1.0, 2.0, 2.8]) {
      expect(invMetricFactor({ x, y: 0, z: 0 })).toBeGreaterThan(0);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// BFT consensus
// ═══════════════════════════════════════════════════════════════

describe('bftConsensus', () => {
  it('all ALLOW → ALLOW', () => {
    const votes: Record<string, Decision> = {
      KO: 'ALLOW', AV: 'ALLOW', RU: 'ALLOW', CA: 'ALLOW', UM: 'ALLOW', DR: 'ALLOW',
    };
    expect(bftConsensus(votes)).toBe('ALLOW');
  });

  it('all DENY → DENY', () => {
    const votes: Record<string, Decision> = {
      KO: 'DENY', AV: 'DENY', RU: 'DENY', CA: 'DENY', UM: 'DENY', DR: 'DENY',
    };
    expect(bftConsensus(votes)).toBe('DENY');
  });

  it('1 faulty cant DENY', () => {
    const votes: Record<string, Decision> = {
      KO: 'DENY', AV: 'ALLOW', RU: 'ALLOW', CA: 'ALLOW', UM: 'ALLOW', DR: 'ALLOW',
    };
    expect(bftConsensus(votes)).toBe('ALLOW');
  });

  it('exactly 4 DENY → DENY', () => {
    const votes: Record<string, Decision> = {
      KO: 'DENY', AV: 'DENY', RU: 'DENY', CA: 'DENY', UM: 'ALLOW', DR: 'ALLOW',
    };
    expect(bftConsensus(votes)).toBe('DENY');
  });

  it('3 DENY not enough', () => {
    const votes: Record<string, Decision> = {
      KO: 'DENY', AV: 'DENY', RU: 'DENY', CA: 'ALLOW', UM: 'ALLOW', DR: 'ALLOW',
    };
    expect(bftConsensus(votes)).toBe('ALLOW');
  });

  it('4 QUARANTINE → QUARANTINE', () => {
    const votes: Record<string, Decision> = {
      KO: 'QUARANTINE', AV: 'QUARANTINE', RU: 'QUARANTINE', CA: 'QUARANTINE',
      UM: 'ALLOW', DR: 'ALLOW',
    };
    expect(bftConsensus(votes)).toBe('QUARANTINE');
  });

  it('mixed 3D+2Q+1A → ALLOW (neither reaches 4)', () => {
    const votes: Record<string, Decision> = {
      KO: 'DENY', AV: 'DENY', RU: 'DENY', CA: 'QUARANTINE', UM: 'QUARANTINE', DR: 'ALLOW',
    };
    expect(bftConsensus(votes)).toBe('ALLOW');
  });

  it('DENY takes priority over QUARANTINE', () => {
    const votes: Record<string, Decision> = {
      KO: 'DENY', AV: 'DENY', RU: 'DENY', CA: 'DENY',
      UM: 'QUARANTINE', DR: 'QUARANTINE',
    };
    expect(bftConsensus(votes)).toBe('DENY');
  });
});

// ═══════════════════════════════════════════════════════════════
// localVote
// ═══════════════════════════════════════════════════════════════

describe('localVote', () => {
  it('low cost allows', () => {
    expect(localVote('KO', 1, 1, ALIGNED_PHASES, BALANCED_WEIGHTS)).toBe('ALLOW');
  });

  it('high cost denies', () => {
    expect(localVote('KO', 100, 0, ALIGNED_PHASES, BALANCED_WEIGHTS)).toBe('DENY');
  });

  it('low coherence increases risk', () => {
    const decisions: Record<Decision, number> = { ALLOW: 0, QUARANTINE: 1, DENY: 2 };
    const vHigh = localVote('KO', 8, 1.0, ALIGNED_PHASES, BALANCED_WEIGHTS);
    const vLow = localVote('KO', 8, 0.0, ALIGNED_PHASES, BALANCED_WEIGHTS);
    expect(decisions[vLow]).toBeGreaterThanOrEqual(decisions[vHigh]);
  });
});

// ═══════════════════════════════════════════════════════════════
// governanceTick
// ═══════════════════════════════════════════════════════════════

describe('governanceTick', () => {
  it('returns 6 votes + consensus', () => {
    const { decision, votes } = governanceTick(1, 1, ALIGNED_PHASES, BALANCED_WEIGHTS);
    expect(decision).toBe('ALLOW');
    expect(Object.keys(votes)).toHaveLength(6);
  });

  it('high cost + low coherence → escalated decision', () => {
    const { decision } = governanceTick(100, 0, ALIGNED_PHASES, BALANCED_WEIGHTS);
    expect(['QUARANTINE', 'DENY']).toContain(decision);
  });
});

// ═══════════════════════════════════════════════════════════════
// Voxel key encoding
// ═══════════════════════════════════════════════════════════════

describe('encodeVoxelKey', () => {
  it('format: qr:{D}:{X}:{Y}:{Z}:{V}:{P}:{S}', () => {
    const base: VoxelBase = { X: 5, Y: 10, Z: 0, V: 23, P: 12, S: 1 };
    const key = encodeVoxelKey(base, 'ALLOW');
    expect(key).toMatch(/^qr:A:/);
    expect(key.split(':')).toHaveLength(8);
  });

  it('decision prefix', () => {
    const base: VoxelBase = { X: 0, Y: 0, Z: 0, V: 0, P: 0, S: 0 };
    expect(encodeVoxelKey(base, 'ALLOW').split(':')[1]).toBe('A');
    expect(encodeVoxelKey(base, 'QUARANTINE').split(':')[1]).toBe('Q');
    expect(encodeVoxelKey(base, 'DENY').split(':')[1]).toBe('D');
  });

  it('deterministic', () => {
    const base: VoxelBase = { X: 3, Y: 7, Z: 11, V: 20, P: 5, S: 15 };
    expect(encodeVoxelKey(base, 'QUARANTINE')).toBe(encodeVoxelKey(base, 'QUARANTINE'));
  });
});

// ═══════════════════════════════════════════════════════════════
// Sacred Egg HMAC
// ═══════════════════════════════════════════════════════════════

describe('eggSign + commitVoxel', () => {
  const testKey = Buffer.from('test-sacred-egg-key-32-bytes-xx!');

  it('eggSign returns hex string', () => {
    const sig = eggSign(testKey, 'hello');
    expect(sig).toMatch(/^[0-9a-f]{64}$/);
  });

  it('eggSign is deterministic', () => {
    expect(eggSign(testKey, 'data')).toBe(eggSign(testKey, 'data'));
  });

  it('different payloads → different sigs', () => {
    expect(eggSign(testKey, 'a')).not.toBe(eggSign(testKey, 'b'));
  });

  it('commitVoxel returns key + sig', () => {
    const rec: SimVoxelRecord = {
      key: 'qr:A:00:00:00:00:00:00',
      t: 100,
      decision: 'ALLOW',
      base: { X: 0, Y: 0, Z: 0, V: 0, P: 0, S: 0 },
      perLang: { KO: '', AV: '', RU: '', CA: '', UM: '', DR: '' },
      pos: { x: 0, y: 0, z: 0 },
      vel: { x: 0, y: 0, z: 0 },
      phases: { KO: 0, AV: 0, RU: 0, CA: 0, UM: 0, DR: 0 },
      weights: { KO: 1, AV: 1, RU: 1, CA: 1, UM: 1, DR: 1 },
      entropy: 0,
      metrics: { coh: 1, dStar: 0, cost: 1 },
    };
    const result = commitVoxel(rec, testKey);
    expect(result.key).toBe('qr:A:00:00:00:00:00:00');
    expect(result.sig).toMatch(/^[0-9a-f]{64}$/);
  });

  it('commitVoxel without key → no sig', () => {
    const rec: SimVoxelRecord = {
      key: 'qr:A:00:00:00:00:00:00',
      t: 0,
      decision: 'ALLOW',
      base: { X: 0, Y: 0, Z: 0, V: 0, P: 0, S: 0 },
      perLang: { KO: '', AV: '', RU: '', CA: '', UM: '', DR: '' },
      pos: ORIGIN,
      vel: ORIGIN,
      phases: ALIGNED_PHASES,
      weights: BALANCED_WEIGHTS,
      entropy: 0,
      metrics: { coh: 1, dStar: 0, cost: 1 },
    };
    const result = commitVoxel(rec);
    expect(result.sig).toBeUndefined();
  });
});

// ═══════════════════════════════════════════════════════════════
// GovernanceSimState (turnkey integration)
// ═══════════════════════════════════════════════════════════════

describe('GovernanceSimState', () => {
  it('tick at origin with aligned phases → ALLOW', () => {
    const gov = new GovernanceSimState();
    const r = gov.tick(ORIGIN, ALIGNED_PHASES, BALANCED_WEIGHTS);
    expect(r.decision).toBe('ALLOW');
    expect(r.motionAllowed).toBe(true);
    expect(r.coh).toBeCloseTo(1.0, 8);
  });

  it('tick far from origin → escalated', () => {
    const gov = new GovernanceSimState();
    const far: Point3D = { x: 2.5, y: 2.5, z: 2.5 };
    const misaligned = { KO: 0, AV: Math.PI, RU: 0, CA: Math.PI, UM: 0, DR: Math.PI };
    const r = gov.tick(far, misaligned, BALANCED_WEIGHTS);
    // High d* + low coherence → high cost → escalated decision
    expect(r.cost).toBeGreaterThan(10);
    expect(r.dStar).toBeGreaterThan(1);
  });

  it('shouldCommit works with interval', () => {
    const gov = new GovernanceSimState();
    expect(gov.shouldCommit(0)).toBe(false);
    expect(gov.shouldCommit(19)).toBe(false);
    expect(gov.shouldCommit(20)).toBe(true);
    expect(gov.shouldCommit(40)).toBe(true);
    expect(gov.shouldCommit(100, 50)).toBe(true);
    expect(gov.shouldCommit(51, 50)).toBe(false);
  });

  it('state persists between ticks', () => {
    const gov = new GovernanceSimState();
    gov.tick(ORIGIN, ALIGNED_PHASES, BALANCED_WEIGHTS);
    expect(gov.decision).toBe('ALLOW');
    expect(gov.coherence).toBeCloseTo(1.0);
  });
});

// ═══════════════════════════════════════════════════════════════
// wrapPi
// ═══════════════════════════════════════════════════════════════

describe('wrapPi', () => {
  it('zero stays zero', () => {
    expect(wrapPi(0)).toBeCloseTo(0);
  });

  it('π stays π', () => {
    expect(wrapPi(Math.PI)).toBeCloseTo(Math.PI);
  });

  it('2π → ~0', () => {
    expect(wrapPi(2 * Math.PI)).toBeCloseTo(0, 10);
  });

  it('-π → π', () => {
    expect(wrapPi(-Math.PI)).toBeCloseTo(Math.PI, 10);
  });

  it('7π → in (-π, π]', () => {
    const r = wrapPi(7 * Math.PI);
    expect(r).toBeGreaterThan(-Math.PI);
    expect(r).toBeLessThanOrEqual(Math.PI);
  });
});

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════

describe('constants', () => {
  it('DANGER_QUORUM = 4', () => {
    expect(DANGER_QUORUM).toBe(4);
  });

  it('COMMIT_EVERY = 20', () => {
    expect(COMMIT_EVERY).toBe(20);
  });
});
