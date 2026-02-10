/**
 * @file voxelRecord.unit.test.ts
 * @tier L2-unit
 * @axiom 5 (Composition)
 * @category unit
 *
 * Unit tests for VoxelRecord: CubeId, digest, quorum, decision, builder.
 */

import { describe, it, expect } from 'vitest';
import {
  computeCubeId,
  computePayloadDigest,
  computeSignaturePayload,
  scbeDecide,
  harmonicCost,
  validateQuorum,
  buildVoxelRecord,
  simulateQuorum,
  DEFAULT_THRESHOLDS,
} from '../../src/harmonic/voxelRecord.js';
import type { Lang, PadMode, Voxel6, QuorumProof } from '../../src/harmonic/scbe_voxel_types.js';

// ═══════════════════════════════════════════════════════════════
// CubeId Tests
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: computeCubeId', () => {
  const lang: Lang = 'KO';
  const voxel: Voxel6 = [1, 2, 3, 4, 5, 6];
  const epoch = 0;
  const padMode: PadMode = 'ENGINEERING';

  it('should return a 64-character hex string', () => {
    const id = computeCubeId(lang, voxel, epoch, padMode);
    expect(id).toHaveLength(64);
    expect(/^[0-9a-f]{64}$/.test(id)).toBe(true);
  });

  it('should be deterministic (same inputs → same output)', () => {
    const id1 = computeCubeId(lang, voxel, epoch, padMode);
    const id2 = computeCubeId(lang, voxel, epoch, padMode);
    expect(id1).toBe(id2);
  });

  it('should differ for different lang', () => {
    const id1 = computeCubeId('KO', voxel, epoch, padMode);
    const id2 = computeCubeId('RU', voxel, epoch, padMode);
    expect(id1).not.toBe(id2);
  });

  it('should differ for different epoch', () => {
    const id1 = computeCubeId(lang, voxel, 0, padMode);
    const id2 = computeCubeId(lang, voxel, 1, padMode);
    expect(id1).not.toBe(id2);
  });

  it('should differ for different voxel', () => {
    const id1 = computeCubeId(lang, [1, 2, 3, 4, 5, 6], epoch, padMode);
    const id2 = computeCubeId(lang, [6, 5, 4, 3, 2, 1], epoch, padMode);
    expect(id1).not.toBe(id2);
  });

  it('should differ for different padMode', () => {
    const id1 = computeCubeId(lang, voxel, epoch, 'ENGINEERING');
    const id2 = computeCubeId(lang, voxel, epoch, 'NAVIGATION');
    expect(id1).not.toBe(id2);
  });
});

// ═══════════════════════════════════════════════════════════════
// Payload Digest Tests
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: computePayloadDigest', () => {
  it('should return a 64-character hex string', () => {
    const payload = Buffer.from('test payload', 'utf-8').toString('base64');
    const digest = computePayloadDigest(payload);
    expect(digest).toHaveLength(64);
  });

  it('should be deterministic', () => {
    const payload = Buffer.from('hello', 'utf-8').toString('base64');
    expect(computePayloadDigest(payload)).toBe(computePayloadDigest(payload));
  });

  it('should differ for different payloads', () => {
    const p1 = Buffer.from('payload1', 'utf-8').toString('base64');
    const p2 = Buffer.from('payload2', 'utf-8').toString('base64');
    expect(computePayloadDigest(p1)).not.toBe(computePayloadDigest(p2));
  });
});

// ═══════════════════════════════════════════════════════════════
// Signature Payload Tests
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: computeSignaturePayload', () => {
  it('should return a 64-character hex string', () => {
    const result = computeSignaturePayload('cube123', 'digest456', 0, 'ENGINEERING');
    expect(result).toHaveLength(64);
  });

  it('should be deterministic', () => {
    const r1 = computeSignaturePayload('c', 'd', 0, 'ENGINEERING');
    const r2 = computeSignaturePayload('c', 'd', 0, 'ENGINEERING');
    expect(r1).toBe(r2);
  });
});

// ═══════════════════════════════════════════════════════════════
// SCBE Decision Tests
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: scbeDecide', () => {
  it('should return ALLOW for safe state', () => {
    expect(scbeDecide(0.2, 0.9, 10.0)).toBe('ALLOW');
  });

  it('should return DENY for low coherence', () => {
    expect(scbeDecide(0.2, 0.1, 10.0)).toBe('DENY');
  });

  it('should return DENY for high cost', () => {
    expect(scbeDecide(0.2, 0.9, 2e6)).toBe('DENY');
  });

  it('should return DENY for high drift', () => {
    expect(scbeDecide(5.0, 0.9, 10.0)).toBe('DENY');
  });

  it('should return QUARANTINE for medium coherence', () => {
    expect(scbeDecide(0.5, 0.4, 500)).toBe('QUARANTINE');
  });

  it('should return QUARANTINE for medium drift', () => {
    expect(scbeDecide(1.5, 0.7, 100)).toBe('QUARANTINE');
  });

  it('should support custom thresholds', () => {
    const strict = {
      ...DEFAULT_THRESHOLDS,
      allowMinCoherence: 0.99,
    };
    expect(scbeDecide(0.1, 0.95, 10, strict)).toBe('QUARANTINE');
  });
});

// ═══════════════════════════════════════════════════════════════
// Harmonic Cost Tests
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: harmonicCost', () => {
  it('should return R at d*=0 (π^0 = 1)', () => {
    expect(harmonicCost(0)).toBeCloseTo(1.5, 1);
  });

  it('should grow with distance', () => {
    const c1 = harmonicCost(1);
    const c2 = harmonicCost(2);
    expect(c2).toBeGreaterThan(c1);
    expect(c1).toBeGreaterThan(1.5);
  });

  it('should grow super-exponentially', () => {
    const c1 = harmonicCost(1);
    const c10 = harmonicCost(10);
    expect(c10).toBeGreaterThan(c1 * 1000);
  });
});

// ═══════════════════════════════════════════════════════════════
// Quorum Validation Tests
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: validateQuorum', () => {
  const digest = 'abc123def456';

  function makeQuorum(count: number, digest: string): QuorumProof {
    return {
      n: 6,
      f: 1,
      threshold: 4,
      votes: Array.from({ length: count }, (_, i) => ({
        agentId: `agent-${i}`,
        digest,
        sig: `sig-${i}`,
        ts: Date.now(),
      })),
    };
  }

  it('should accept valid quorum with 4 matching votes', () => {
    const q = makeQuorum(4, digest);
    const result = validateQuorum(q, digest);
    expect(result.valid).toBe(true);
    expect(result.matchingVotes).toBe(4);
  });

  it('should accept quorum with 6 matching votes', () => {
    const q = makeQuorum(6, digest);
    const result = validateQuorum(q, digest);
    expect(result.valid).toBe(true);
    expect(result.matchingVotes).toBe(6);
  });

  it('should reject quorum with 3 votes (below threshold)', () => {
    const q = makeQuorum(3, digest);
    const result = validateQuorum(q, digest);
    expect(result.valid).toBe(false);
    expect(result.reason).toContain('insufficient');
  });

  it('should reject quorum with wrong n', () => {
    const q = makeQuorum(4, digest);
    q.n = 5;
    const result = validateQuorum(q, digest);
    expect(result.valid).toBe(false);
    expect(result.reason).toContain('n must be 6');
  });

  it('should reject quorum with mismatched digests', () => {
    const q = makeQuorum(4, 'wrong-digest');
    const result = validateQuorum(q, digest);
    expect(result.valid).toBe(false);
    expect(result.reason).toContain('digest mismatch');
  });

  it('should reject quorum with duplicate agent IDs', () => {
    const q = makeQuorum(4, digest);
    q.votes[1].agentId = q.votes[0].agentId; // Duplicate
    const result = validateQuorum(q, digest);
    expect(result.valid).toBe(false);
    expect(result.reason).toContain('duplicate');
  });
});

// ═══════════════════════════════════════════════════════════════
// VoxelRecord Builder Tests
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: buildVoxelRecord', () => {
  it('should build a complete record with all required fields', () => {
    const record = buildVoxelRecord({
      lang: 'KO',
      voxel: [1, 2, 3, 4, 5, 6],
      epoch: 0,
      padMode: 'ENGINEERING',
      coherence: 0.9,
      dStar: 0.2,
      payload: 'test data',
      eggId: 'egg-001',
    });

    expect(record.version).toBe(1);
    expect(record.lang).toBe('KO');
    expect(record.voxel).toEqual([1, 2, 3, 4, 5, 6]);
    expect(record.epoch).toBe(0);
    expect(record.padMode).toBe('ENGINEERING');
    expect(record.coherence).toBe(0.9);
    expect(record.dStar).toBe(0.2);
    expect(record.hEff).toBeGreaterThan(0);
    expect(record.decision).toBe('ALLOW');
    expect(record.cubeId).toHaveLength(64);
    expect(record.payloadDigest).toHaveLength(64);
    expect(record.seal.eggId).toBe('egg-001');
    expect(record.seal.kdf).toBe('pi_phi');
    expect(record.payloadCiphertext).toBeTruthy();
  });

  it('should set decision to DENY for unsafe state', () => {
    const record = buildVoxelRecord({
      lang: 'RU',
      voxel: [0, 0, 0, 0, 0, 0],
      epoch: 0,
      padMode: 'MISSION',
      coherence: 0.1,
      dStar: 5.0,
      payload: 'dangerous',
      eggId: 'egg-002',
    });

    expect(record.decision).toBe('DENY');
  });

  it('should include optional tags and parents', () => {
    const record = buildVoxelRecord({
      lang: 'CA',
      voxel: [0, 0, 0, 0, 0, 0],
      epoch: 0,
      padMode: 'SCIENCE',
      coherence: 0.9,
      dStar: 0.1,
      payload: 'data',
      eggId: 'egg-003',
      tags: ['test', 'crypto'],
      parents: ['parent-cube-1'],
    });

    expect(record.tags).toEqual(['test', 'crypto']);
    expect(record.parents).toEqual(['parent-cube-1']);
  });
});

// ═══════════════════════════════════════════════════════════════
// Simulated Quorum Tests
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: simulateQuorum', () => {
  it('should create valid quorum with default 4 agents', () => {
    const q = simulateQuorum('cube-id', 'digest-hash', 0, 'ENGINEERING');
    expect(q.n).toBe(6);
    expect(q.f).toBe(1);
    expect(q.threshold).toBe(4);
    expect(q.votes).toHaveLength(4);

    // Validate the simulated quorum
    const result = validateQuorum(q, 'digest-hash');
    expect(result.valid).toBe(true);
  });

  it('should create quorum with custom agent count', () => {
    const q = simulateQuorum('cube-id', 'digest-hash', 0, 'ENGINEERING', 6);
    expect(q.votes).toHaveLength(6);
  });

  it('should have unique agent IDs', () => {
    const q = simulateQuorum('cube-id', 'digest-hash', 0, 'ENGINEERING');
    const ids = new Set(q.votes.map((v) => v.agentId));
    expect(ids.size).toBe(q.votes.length);
  });

  it('should have unique signatures', () => {
    const q = simulateQuorum('cube-id', 'digest-hash', 0, 'ENGINEERING');
    const sigs = new Set(q.votes.map((v) => v.sig));
    expect(sigs.size).toBe(q.votes.length);
  });
});
