/**
 * @file scbeGate.test.ts
 * @module tests/conference
 *
 * Tests for the SCBE governance gate used by the Vibe Coder Conference App.
 * Validates the 14-layer pipeline scoring, HYDRA audit, and access level computation.
 */

import { describe, it, expect } from 'vitest';
import {
  hyperbolicDistance,
  harmonicScore,
  breathingFactor,
  scoreProject,
  auditProject,
  computeAccessLevel,
} from '../../conference-app/src/shared/governance/scbeGate';
import type { ProjectCapsule } from '../../conference-app/src/shared/types/index';

function makeTestProject(overrides: Partial<ProjectCapsule> = {}): ProjectCapsule {
  return {
    id: 'test-1',
    scbeId: 'scbe-test1',
    creatorId: 'user-1',
    title: 'VibeDB',
    tagline: 'A database for vibes — fast, weird, and beautiful',
    description: 'VibeDB is a novel database engine that uses hyperbolic embeddings for semantic similarity. It supports real-time vector search with sub-millisecond latency and integrates with modern frontend frameworks.',
    techStack: ['TypeScript', 'Rust', 'WebGPU', 'React'],
    repoUrl: 'https://github.com/example/vibedb',
    demoUrl: 'https://vibedb.dev',
    videoUrl: 'https://loom.com/share/vibedb-demo',
    pitchDeckUrl: 'https://docs.google.com/presentation/vibedb',
    fundingAsk: { amount: 100_000, stage: 'pre-seed', useOfFunds: 'Hire 2 engineers' },
    status: 'draft',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    ...overrides,
  };
}

describe('hyperbolicDistance()', () => {
  it('returns 0 for identical points', () => {
    const p = [0, 0, 0, 0, 0, 0];
    expect(hyperbolicDistance(p, p)).toBeCloseTo(0, 8);
  });

  it('increases with distance from origin', () => {
    const origin = [0, 0, 0, 0, 0, 0];
    const near = [0.1, 0, 0, 0, 0, 0];
    const far = [0.5, 0, 0, 0, 0, 0];
    expect(hyperbolicDistance(origin, near)).toBeLessThan(hyperbolicDistance(origin, far));
  });

  it('returns Infinity when points are on the boundary', () => {
    const origin = [0, 0, 0, 0, 0, 0];
    const boundary = [1, 0, 0, 0, 0, 0];
    expect(hyperbolicDistance(origin, boundary)).toBe(Infinity);
  });
});

describe('harmonicScore()', () => {
  it('returns 1 at origin (dH=0, pd=0)', () => {
    expect(harmonicScore(0, 0)).toBe(1);
  });

  it('decreases as hyperbolic distance increases', () => {
    expect(harmonicScore(1, 0)).toBeLessThan(harmonicScore(0, 0));
    expect(harmonicScore(5, 0)).toBeLessThan(harmonicScore(1, 0));
  });

  it('is bounded in (0, 1]', () => {
    const score = harmonicScore(100, 10);
    expect(score).toBeGreaterThan(0);
    expect(score).toBeLessThanOrEqual(1);
  });
});

describe('breathingFactor()', () => {
  it('returns 1 at t=0 with default params', () => {
    expect(breathingFactor(0)).toBeCloseTo(1, 6);
  });

  it('is deterministic and clamped', () => {
    const b = breathingFactor(0, 0.9, (2 * Math.PI) / 60);
    expect(b).toBeGreaterThanOrEqual(0.25);
    expect(b).toBeLessThanOrEqual(2.5);
  });
});

describe('scoreProject()', () => {
  it('returns a valid decision for a well-formed project', () => {
    const project = makeTestProject();
    const result = scoreProject(project);
    expect(['ALLOW', 'QUARANTINE', 'ESCALATE']).toContain(result.decision);
    expect(result.coherence).toBeGreaterThan(0);
    expect(result.harmonicScore).toBeGreaterThan(0);
    expect(result.layerSummary).toHaveLength(14);
    expect(['low', 'medium', 'high']).toContain(result.riskLabel);
  });

  it('produces 14 layer scores', () => {
    const result = scoreProject(makeTestProject());
    expect(result.layerSummary.length).toBe(14);
    result.layerSummary.forEach((layer, i) => {
      expect(layer.layer).toBe(i + 1);
      expect(layer.name).toBeDefined();
    });
  });

  it('produces different scores for sparse vs complete projects', () => {
    const sparse = makeTestProject({
      description: 'short',
      techStack: [],
      repoUrl: undefined,
      demoUrl: undefined,
      videoUrl: undefined,
      pitchDeckUrl: undefined,
    });
    const sparseResult = scoreProject(sparse);
    const goodResult = scoreProject(makeTestProject());
    // They should produce meaningfully different hyperbolic distances
    expect(sparseResult.hyperbolicDistance).not.toBeCloseTo(goodResult.hyperbolicDistance, 2);
  });
});

describe('auditProject()', () => {
  it('returns 6 agent reports', () => {
    const result = auditProject(makeTestProject());
    expect(result.agents).toHaveLength(6);
    const tongues = result.agents.map(a => a.tongue);
    expect(tongues).toEqual(expect.arrayContaining(['KO', 'AV', 'RU', 'CA', 'UM', 'DR']));
  });

  it('meets quorum for well-formed projects', () => {
    const result = auditProject(makeTestProject());
    expect(result.quorumMet).toBe(true);
    expect(result.qualityScore).toBeGreaterThan(0.5);
  });

  it('flags missing repo', () => {
    const noRepo = makeTestProject({ repoUrl: undefined });
    const result = auditProject(noRepo);
    expect(result.securityFlags).toContain('no-repo-link');
  });
});

describe('computeAccessLevel()', () => {
  it('grants full access when NDA signed and ALLOW', () => {
    const access = computeAccessLevel(true, 'ALLOW');
    expect(access.canViewPublicProfile).toBe(true);
    expect(access.canViewFullDeck).toBe(true);
    expect(access.canAccessDataRoom).toBe(true);
    expect(access.canJoinLiveQA).toBe(true);
    expect(access.canSoftCommit).toBe(true);
  });

  it('denies sensitive access without NDA', () => {
    const access = computeAccessLevel(false, 'ALLOW');
    expect(access.canViewPublicProfile).toBe(true);
    expect(access.canViewFullDeck).toBe(false);
    expect(access.canAccessDataRoom).toBe(false);
    expect(access.canSoftCommit).toBe(false);
  });

  it('denies everything for DENY projects', () => {
    const access = computeAccessLevel(true, 'DENY');
    expect(access.canViewPublicProfile).toBe(false);
    expect(access.canViewFullDeck).toBe(false);
  });
});
