/**
 * @file geoseal-operator-space.test.ts
 * @module tests/geoseal-operator-space
 *
 * Tests for the GeoSeal Operator System-Space Model.
 * Covers: ring derivation, FS topology, cross-plane claim detection,
 * governance flags, trust penalty, space ID determinism.
 */

import { describe, expect, it } from 'vitest';
import {
  derivefsTopology,
  evaluateOperatorSpace,
  operatorSpaceToRecord,
  ringToGovernanceTier,
  type OperatorAccessPlane,
  type OperatorAuthState,
  type OperatorSpaceDecision,
} from '../src/geosealOperatorSpace.js';

// ─────────────────────────────────────────────────────────────────────────────
// FS topology
// ─────────────────────────────────────────────────────────────────────────────

describe('derivefsTopology', () => {
  it('web+anonymous → full sandbox, temp only, no roots', () => {
    const topo = derivefsTopology('web', 'anonymous');
    expect(topo.sandboxLevel).toBe('full');
    expect(topo.accessibleRoots).toHaveLength(0);
    expect(topo.tempOnly).toBe(true);
    expect(topo.persistsAcrossSessions).toBe(false);
    expect(topo.mountPoints).toHaveLength(0);
  });

  it('web+authenticated → full sandbox but persists', () => {
    const topo = derivefsTopology('web', 'authenticated');
    expect(topo.sandboxLevel).toBe('full');
    expect(topo.persistsAcrossSessions).toBe(true);
    expect(topo.tempOnly).toBe(false);
  });

  it('terminal+sudo → no sandbox, full root access', () => {
    const topo = derivefsTopology('terminal', 'sudo');
    expect(topo.sandboxLevel).toBe('none');
    expect(topo.accessibleRoots).toContain('/');
    expect(topo.writablePaths).toContain('/');
    expect(topo.persistsAcrossSessions).toBe(true);
    expect(topo.tempOnly).toBe(false);
    expect(topo.mountPoints.length).toBeGreaterThan(0);
  });

  it('terminal+authenticated → no sandbox, home+tmp writable', () => {
    const topo = derivefsTopology('terminal', 'authenticated');
    expect(topo.sandboxLevel).toBe('none');
    expect(topo.accessibleRoots.some((r) => r.includes('home') || r === '~')).toBe(true);
    expect(topo.writablePaths.some((p) => p.includes('tmp') || p === '~')).toBe(true);
  });

  it('terminal+anonymous → partial sandbox, temp only', () => {
    const topo = derivefsTopology('terminal', 'anonymous');
    expect(topo.sandboxLevel).toBe('partial');
    expect(topo.tempOnly).toBe(true);
    expect(topo.persistsAcrossSessions).toBe(false);
  });

  it('app+authenticated → partial sandbox, app-data roots', () => {
    const topo = derivefsTopology('app', 'authenticated');
    expect(topo.sandboxLevel).toBe('partial');
    expect(topo.persistsAcrossSessions).toBe(true);
    expect(topo.mountPoints).toHaveLength(0);
  });

  it('app+anonymous → partial sandbox, no roots', () => {
    const topo = derivefsTopology('app', 'anonymous');
    expect(topo.sandboxLevel).toBe('partial');
    expect(topo.accessibleRoots).toHaveLength(0);
    expect(topo.tempOnly).toBe(true);
  });

  it('api+anonymous → full sandbox', () => {
    const topo = derivefsTopology('api', 'anonymous');
    expect(topo.sandboxLevel).toBe('full');
    expect(topo.accessibleRoots).toHaveLength(0);
  });

  it('api+service_account → partial sandbox, no FS', () => {
    const topo = derivefsTopology('api', 'service_account');
    expect(topo.sandboxLevel).toBe('partial');
    expect(topo.accessibleRoots).toHaveLength(0);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Ring and trust score
// ─────────────────────────────────────────────────────────────────────────────

describe('evaluateOperatorSpace — ring derivation', () => {
  const cases: Array<[OperatorAccessPlane, OperatorAuthState, string, number]> = [
    ['terminal', 'sudo', 'core', 0.95],
    ['terminal', 'authenticated', 'core', 0.85],
    ['terminal', 'service_account', 'core', 0.8],
    ['terminal', 'anonymous', 'restricted', 0.35],
    ['app', 'authenticated', 'outer', 0.7],
    ['app', 'service_account', 'outer', 0.65],
    ['app', 'anonymous', 'restricted', 0.25],
    ['api', 'service_account', 'core', 0.8],
    ['api', 'authenticated', 'outer', 0.7],
    ['api', 'anonymous', 'blocked', 0.05],
    ['web', 'authenticated', 'outer', 0.6],
    ['web', 'anonymous', 'blocked', 0.05],
  ];

  it.each(cases)('%s+%s → ring=%s trust=%f', (plane, auth, expectedRing, expectedTrust) => {
    const decision = evaluateOperatorSpace({
      accessPlane: plane,
      authState: auth,
      sessionFingerprint: 'test-sess-001',
      loginTimeMs: auth === 'anonymous' ? undefined : Date.now(),
    });
    expect(decision.ring).toBe(expectedRing);
    expect(decision.trustScore).toBe(expectedTrust);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Governance flags
// ─────────────────────────────────────────────────────────────────────────────

describe('evaluateOperatorSpace — governance flags', () => {
  it('terminal+sudo raises ELEVATED_TERMINAL', () => {
    const d = evaluateOperatorSpace({
      accessPlane: 'terminal',
      authState: 'sudo',
      sessionFingerprint: 'sudo-sess',
      loginTimeMs: Date.now(),
    });
    expect(d.governanceFlags).toContain('ELEVATED_TERMINAL');
  });

  it('web+anonymous raises UNAUTHENTICATED_WEB and TEMP_FS_ONLY', () => {
    const d = evaluateOperatorSpace({ accessPlane: 'web', authState: 'anonymous' });
    expect(d.governanceFlags).toContain('UNAUTHENTICATED_WEB');
    expect(d.governanceFlags).toContain('TEMP_FS_ONLY');
  });

  it('api+anonymous raises UNAUTHENTICATED_API and TEMP_FS_ONLY', () => {
    const d = evaluateOperatorSpace({ accessPlane: 'api', authState: 'anonymous' });
    expect(d.governanceFlags).toContain('UNAUTHENTICATED_API');
    expect(d.governanceFlags).toContain('TEMP_FS_ONLY');
  });

  it('terminal+service_account raises SERVICE_ACCOUNT_ELEVATED', () => {
    const d = evaluateOperatorSpace({
      accessPlane: 'terminal',
      authState: 'service_account',
      sessionFingerprint: 'svc-sess',
    });
    expect(d.governanceFlags).toContain('SERVICE_ACCOUNT_ELEVATED');
  });

  it('authenticated without loginTimeMs raises SESSION_MISSING_LOGIN_TIME', () => {
    const d = evaluateOperatorSpace({
      accessPlane: 'terminal',
      authState: 'authenticated',
      sessionFingerprint: 'sess-no-time',
      // loginTimeMs intentionally omitted
    });
    expect(d.governanceFlags).toContain('SESSION_MISSING_LOGIN_TIME');
  });

  it('web operator claiming native path raises CROSS_PLANE_CLAIM', () => {
    const d = evaluateOperatorSpace({
      accessPlane: 'web',
      authState: 'authenticated',
      sessionFingerprint: 'web-sess',
      loginTimeMs: Date.now(),
      claimedPaths: ['/home/user/documents', 'C:\\Users\\user\\Desktop'],
    });
    expect(d.governanceFlags).toContain('CROSS_PLANE_CLAIM');
  });

  it('terminal operator claiming HTTP URL raises CROSS_PLANE_CLAIM', () => {
    const d = evaluateOperatorSpace({
      accessPlane: 'terminal',
      authState: 'authenticated',
      sessionFingerprint: 'term-sess',
      loginTimeMs: Date.now(),
      claimedPaths: ['http://example.com/file.txt'],
    });
    expect(d.governanceFlags).toContain('CROSS_PLANE_CLAIM');
  });

  it('terminal operator claiming local path does NOT raise CROSS_PLANE_CLAIM', () => {
    const d = evaluateOperatorSpace({
      accessPlane: 'terminal',
      authState: 'authenticated',
      sessionFingerprint: 'term-sess-ok',
      loginTimeMs: Date.now(),
      claimedPaths: ['/home/user/documents'],
    });
    expect(d.governanceFlags).not.toContain('CROSS_PLANE_CLAIM');
  });

  it('API operator claiming any path raises CROSS_PLANE_CLAIM', () => {
    const d = evaluateOperatorSpace({
      accessPlane: 'api',
      authState: 'service_account',
      sessionFingerprint: 'api-svc',
      claimedPaths: ['/tmp/output.json'],
    });
    expect(d.governanceFlags).toContain('CROSS_PLANE_CLAIM');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Trust penalty and effective ring downgrade
// ─────────────────────────────────────────────────────────────────────────────

describe('evaluateOperatorSpace — trust penalty', () => {
  it('CROSS_PLANE_CLAIM reduces trust by 0.30', () => {
    const baseline = evaluateOperatorSpace({
      accessPlane: 'terminal',
      authState: 'authenticated',
      sessionFingerprint: 'base',
      loginTimeMs: Date.now(),
    });
    const withClaim = evaluateOperatorSpace({
      accessPlane: 'terminal',
      authState: 'authenticated',
      sessionFingerprint: 'base',
      loginTimeMs: Date.now(),
      claimedPaths: ['http://evil.com/file'],
    });
    expect(withClaim.trustScore).toBeCloseTo(baseline.trustScore - 0.3, 4);
  });

  it('SESSION_MISSING_LOGIN_TIME reduces trust by 0.15', () => {
    const baseline = evaluateOperatorSpace({
      accessPlane: 'terminal',
      authState: 'authenticated',
      sessionFingerprint: 'base',
      loginTimeMs: Date.now(),
    });
    const withMissing = evaluateOperatorSpace({
      accessPlane: 'terminal',
      authState: 'authenticated',
      sessionFingerprint: 'base',
      // no loginTimeMs
    });
    expect(withMissing.trustScore).toBeCloseTo(baseline.trustScore - 0.15, 4);
  });

  it('sufficient trust penalty downgrades ring from core to restricted', () => {
    // terminal+authenticated starts at 0.85 — if we subtract 0.45 it goes below 0.4
    // Use combined penalty: CROSS_PLANE_CLAIM (0.30) + SESSION_MISSING_LOGIN_TIME (0.15) = 0.45
    const d = evaluateOperatorSpace({
      accessPlane: 'terminal',
      authState: 'authenticated',
      sessionFingerprint: 'penalized',
      // no loginTimeMs → SESSION_MISSING_LOGIN_TIME
      claimedPaths: ['http://external.example.com/bad'], // → CROSS_PLANE_CLAIM
    });
    expect(d.ring).toBe('restricted');
    expect(d.trustScore).toBeCloseTo(0.4, 4);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Space ID determinism
// ─────────────────────────────────────────────────────────────────────────────

describe('evaluateOperatorSpace — space ID', () => {
  it('same inputs produce the same spaceId', () => {
    const input = {
      accessPlane: 'terminal' as OperatorAccessPlane,
      authState: 'authenticated' as OperatorAuthState,
      sessionFingerprint: 'fixed-fingerprint-abc',
      loginTimeMs: 1716000000000,
    };
    const a = evaluateOperatorSpace(input);
    const b = evaluateOperatorSpace(input);
    expect(a.spaceId).toBe(b.spaceId);
  });

  it('different fingerprints produce different spaceIds', () => {
    const a = evaluateOperatorSpace({
      accessPlane: 'terminal',
      authState: 'authenticated',
      sessionFingerprint: 'fp-aaa',
      loginTimeMs: Date.now(),
    });
    const b = evaluateOperatorSpace({
      accessPlane: 'terminal',
      authState: 'authenticated',
      sessionFingerprint: 'fp-bbb',
      loginTimeMs: Date.now(),
    });
    expect(a.spaceId).not.toBe(b.spaceId);
  });

  it('different planes produce different spaceIds even with same fingerprint', () => {
    const fp = 'shared-fp-xyz';
    const a = evaluateOperatorSpace({
      accessPlane: 'web',
      authState: 'authenticated',
      sessionFingerprint: fp,
    });
    const b = evaluateOperatorSpace({
      accessPlane: 'terminal',
      authState: 'authenticated',
      sessionFingerprint: fp,
    });
    expect(a.spaceId).not.toBe(b.spaceId);
  });

  it('spaceId is 16 hex characters', () => {
    const d = evaluateOperatorSpace({
      accessPlane: 'api',
      authState: 'service_account',
      sessionFingerprint: 'api-svc-001',
    });
    expect(d.spaceId).toMatch(/^[0-9a-f]{16}$/);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Serialisation
// ─────────────────────────────────────────────────────────────────────────────

describe('operatorSpaceToRecord', () => {
  it('produces a flat JSON-serialisable record', () => {
    const d = evaluateOperatorSpace({
      accessPlane: 'terminal',
      authState: 'authenticated',
      sessionFingerprint: 'ser-test',
      loginTimeMs: Date.now(),
    });
    const rec = operatorSpaceToRecord(d);
    expect(typeof rec['ring']).toBe('string');
    expect(typeof rec['trust_score']).toBe('number');
    expect(typeof rec['space_id']).toBe('string');
    expect(Array.isArray(rec['governance_flags'])).toBe(true);
    // Should be JSON-serialisable without error
    expect(() => JSON.stringify(rec)).not.toThrow();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// L13 tier mapping
// ─────────────────────────────────────────────────────────────────────────────

describe('ringToGovernanceTier', () => {
  it('maps rings to L13 governance tiers', () => {
    expect(ringToGovernanceTier('core')).toBe('ALLOW');
    expect(ringToGovernanceTier('outer')).toBe('QUARANTINE');
    expect(ringToGovernanceTier('restricted')).toBe('ESCALATE');
    expect(ringToGovernanceTier('blocked')).toBe('DENY');
  });
});
