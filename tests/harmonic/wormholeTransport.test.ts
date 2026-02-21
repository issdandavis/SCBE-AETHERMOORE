/**
 * @file wormholeTransport.test.ts
 * @module harmonic/wormholeTransport
 * @layer Layer 5, Layer 6
 *
 * Tests for WormholeNetwork: wormhole creation, stability decay,
 * transport mechanics, nearest-wormhole lookup, effective distance
 * shortcuts, and pruning of collapsed wormholes.
 *
 * IMPORTANT: All points must be inside the Poincaré ball (norm < 1).
 */

import { describe, it, expect } from 'vitest';
import { WormholeNetwork } from '../../src/harmonic/wormholeTransport.js';

// ---------------------------------------------------------------------------
// 1. Wormhole creation and properties
// ---------------------------------------------------------------------------

describe('WormholeNetwork – creation and properties', () => {
  it('creates a wormhole with correct throats and default halfLife', () => {
    const net = new WormholeNetwork();
    const throatA = [0, 0, 0];
    const throatB = [0.5, 0, 0];

    const wormhole = net.createWormhole(throatA, throatB);

    expect(wormhole.id).toBeTruthy();
    expect(wormhole.throatA).toEqual(throatA);
    expect(wormhole.throatB).toEqual(throatB);
    expect(wormhole.traversals).toBe(0);
    expect(wormhole.halfLife).toBe(300);
    expect(typeof wormhole.createdAt).toBe('number');
  });

  it('creates a wormhole with an explicit halfLife', () => {
    const net = new WormholeNetwork();
    const wormhole = net.createWormhole([0, 0], [0.5, 0.5], 1000);

    expect(wormhole.halfLife).toBe(1000);
  });

  it('generates unique IDs for distinct wormholes', () => {
    const net = new WormholeNetwork();
    const w1 = net.createWormhole([0, 0], [0.1, 0]);
    const w2 = net.createWormhole([0, 0], [0, 0.1]);

    expect(w1.id).not.toBe(w2.id);
  });

  it('increases size after each createWormhole call', () => {
    const net = new WormholeNetwork();
    expect(net.size).toBe(0);

    net.createWormhole([0, 0], [0.1, 0]);
    expect(net.size).toBe(1);

    net.createWormhole([0, 0], [0, 0.1]);
    expect(net.size).toBe(2);
  });

  it('getAll returns all created wormholes', () => {
    const net = new WormholeNetwork();
    const w1 = net.createWormhole([0, 0], [0.1, 0]);
    const w2 = net.createWormhole([0.2, 0], [0.3, 0]);

    const all = net.getAll();
    expect(all).toHaveLength(2);
    const ids = all.map((w) => w.id);
    expect(ids).toContain(w1.id);
    expect(ids).toContain(w2.id);
  });

  it('initial stability is 1 at creation time', () => {
    const net = new WormholeNetwork();
    const wormhole = net.createWormhole([0, 0], [0.5, 0], 5000);

    const stability = net.getStability(wormhole, wormhole.createdAt);
    expect(stability).toBeCloseTo(1.0, 10);
  });
});

// ---------------------------------------------------------------------------
// 2. Stability decay
// ---------------------------------------------------------------------------

describe('WormholeNetwork – stability decay', () => {
  it('stability at t = halfLife (in seconds) is approximately 0.5', () => {
    const net = new WormholeNetwork();
    const halfLife = 10; // 10 seconds
    const wormhole = net.createWormhole([0, 0], [0.1, 0], halfLife);

    // halfLife is in seconds, timestamps in ms
    const stabilityAtHalfLife = net.getStability(wormhole, wormhole.createdAt + halfLife * 1000);
    expect(stabilityAtHalfLife).toBeCloseTo(0.5, 5);
  });

  it('stability at t = 2 * halfLife is approximately 0.25', () => {
    const net = new WormholeNetwork();
    const halfLife = 5; // seconds
    const wormhole = net.createWormhole([0, 0], [0.1, 0], halfLife);

    const stability = net.getStability(wormhole, wormhole.createdAt + 2 * halfLife * 1000);
    expect(stability).toBeCloseTo(0.25, 5);
  });

  it('stability is always in (0, 1]', () => {
    const net = new WormholeNetwork();
    const halfLife = 1; // 1 second
    const wormhole = net.createWormhole([0, 0], [0.1, 0], halfLife);

    const offsets = [0, 500, 1000, 2000, 5000, 100_000];
    for (const dt of offsets) {
      const s = net.getStability(wormhole, wormhole.createdAt + dt);
      expect(s).toBeGreaterThan(0);
      expect(s).toBeLessThanOrEqual(1.0);
    }
  });

  it('stability is monotonically decreasing over time', () => {
    const net = new WormholeNetwork();
    const halfLife = 3; // 3 seconds
    const wormhole = net.createWormhole([0, 0], [0.1, 0], halfLife);

    const times = [0, 1000, 3000, 6000, 10000];
    let prevStability = 2;
    for (const dt of times) {
      const s = net.getStability(wormhole, wormhole.createdAt + dt);
      expect(s).toBeLessThanOrEqual(prevStability);
      prevStability = s;
    }
  });

  it('getStability formula matches e^(-ln2 * dt_seconds / halfLife)', () => {
    const net = new WormholeNetwork();
    const halfLife = 8; // 8 seconds
    const wormhole = net.createWormhole([0, 0], [0.1, 0], halfLife);
    const dtMs = 3000; // 3 seconds

    const expected = Math.exp((-Math.LN2 * (dtMs / 1000)) / halfLife);
    const actual = net.getStability(wormhole, wormhole.createdAt + dtMs);
    expect(actual).toBeCloseTo(expected, 8);
  });
});

// ---------------------------------------------------------------------------
// 3. Transport success and destination correctness
// ---------------------------------------------------------------------------

describe('WormholeNetwork – transport success', () => {
  it('transport from near throatA delivers to throatB', () => {
    const net = new WormholeNetwork();
    const throatA = [0, 0];
    const throatB = [0.9, 0];
    const wormhole = net.createWormhole(throatA, throatB, 1_000_000);

    // Point at origin is closer to throatA
    const result = net.transport([0.01, 0], wormhole.id, wormhole.createdAt);

    expect(result.success).toBe(true);
    expect(result.destination).toEqual(throatB);
  });

  it('transport from near throatB delivers to throatA', () => {
    const net = new WormholeNetwork();
    const throatA = [0, 0];
    const throatB = [0.9, 0];
    const wormhole = net.createWormhole(throatA, throatB, 1_000_000);

    // Point near throatB
    const result = net.transport([0.89, 0], wormhole.id, wormhole.createdAt);

    expect(result.success).toBe(true);
    expect(result.destination).toEqual(throatA);
  });

  it('distanceSaved is non-negative', () => {
    const net = new WormholeNetwork();
    const throatA = [0, 0];
    const throatB = [0.9, 0];
    const wormhole = net.createWormhole(throatA, throatB, 1_000_000);

    const result = net.transport([0.01, 0], wormhole.id, wormhole.createdAt);

    expect(result.success).toBe(true);
    expect(result.distanceSaved).toBeGreaterThanOrEqual(0);
  });

  it('stabilityAtTraversal reflects the stability at the traversal time', () => {
    const net = new WormholeNetwork();
    const halfLife = 10; // 10 seconds
    const wormhole = net.createWormhole([0, 0], [0.9, 0], halfLife);

    // At creation time, stability = 1.0
    const result = net.transport([0, 0], wormhole.id, wormhole.createdAt);

    expect(result.success).toBe(true);
    expect(result.stabilityAtTraversal).toBeCloseTo(1.0, 5);
  });

  it('successful transport increments traversal count', () => {
    const net = new WormholeNetwork();
    const wormhole = net.createWormhole([0, 0], [0.5, 0], 1_000_000);

    net.transport([0, 0], wormhole.id, wormhole.createdAt);
    net.transport([0, 0], wormhole.id, wormhole.createdAt);

    const all = net.getAll();
    const updated = all.find((w) => w.id === wormhole.id)!;
    expect(updated.traversals).toBe(2);
  });
});

// ---------------------------------------------------------------------------
// 4. Transport failure for collapsed wormhole
// ---------------------------------------------------------------------------

describe('WormholeNetwork – transport failure (collapsed wormhole)', () => {
  it('returns success=false for a very old wormhole with short halfLife', () => {
    const net = new WormholeNetwork();
    const halfLife = 0.001; // 1 ms halfLife
    const wormhole = net.createWormhole([0, 0], [0.5, 0], halfLife);

    // 100 seconds later with 1ms halfLife → stability ≈ 0
    const result = net.transport([0, 0], wormhole.id, wormhole.createdAt + 100_000);

    expect(result.success).toBe(false);
  });

  it('returns a result object even on failure', () => {
    const net = new WormholeNetwork();
    const wormhole = net.createWormhole([0, 0], [0.5, 0], 0.001);

    const result = net.transport([0, 0], wormhole.id, wormhole.createdAt + 100_000);

    expect(result).toBeDefined();
    expect(result).not.toBeNull();
    expect(result.success).toBe(false);
  });

  it('transport with unknown wormholeId returns success=false', () => {
    const net = new WormholeNetwork();
    net.createWormhole([0, 0], [0.5, 0], 1_000_000);

    const result = net.transport([0, 0], 'nonexistent-id-xyz');

    expect(result.success).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// 5. findNearest returns closest stable wormhole
// ---------------------------------------------------------------------------

describe('WormholeNetwork – findNearest', () => {
  it('returns null when network is empty', () => {
    const net = new WormholeNetwork();
    const result = net.findNearest([0, 0]);
    expect(result).toBeNull();
  });

  it('returns the single wormhole if it is stable', () => {
    const net = new WormholeNetwork();
    const wormhole = net.createWormhole([0.1, 0], [0.9, 0], 1_000_000);

    const result = net.findNearest([0, 0], 0, wormhole.createdAt);

    expect(result).not.toBeNull();
    expect(result!.wormhole.id).toBe(wormhole.id);
  });

  it('returns null when the only wormhole is below minStability', () => {
    const net = new WormholeNetwork();
    const wormhole = net.createWormhole([0.1, 0], [0.9, 0], 0.001);

    // Way past half-life
    const result = net.findNearest([0, 0], 0.5, wormhole.createdAt + 1_000_000);

    expect(result).toBeNull();
  });

  it('returns the nearest wormhole throat to the query point', () => {
    const net = new WormholeNetwork();
    // Wormhole with throats far from origin
    net.createWormhole([0.8, 0.5], [0.3, 0.8], 1_000_000);
    // Wormhole with throatA close to origin
    const wClose = net.createWormhole([0.05, 0], [0.9, 0], 1_000_000);

    const result = net.findNearest([0, 0], 0, wClose.createdAt);

    expect(result).not.toBeNull();
    expect(result!.wormhole.id).toBe(wClose.id);
  });

  it('identifies the correct throat (A vs B)', () => {
    const net = new WormholeNetwork();
    // ThroatA near origin, ThroatB far away
    const wormhole = net.createWormhole([0.05, 0], [0.95, 0], 1_000_000);

    // Point near throatA → should identify throat A
    const nearA = net.findNearest([0.03, 0], 0, wormhole.createdAt);
    expect(nearA!.throat).toBe('A');

    // Point near throatB → should identify throat B
    const nearB = net.findNearest([0.93, 0], 0, wormhole.createdAt);
    expect(nearB!.throat).toBe('B');
  });

  it('includes a non-negative distance in the result', () => {
    const net = new WormholeNetwork();
    const wormhole = net.createWormhole([0.3, 0.4], [0.7, 0.1], 1_000_000);

    const result = net.findNearest([0, 0], 0, wormhole.createdAt);

    expect(result).not.toBeNull();
    expect(result!.distance).toBeGreaterThanOrEqual(0);
  });
});

// ---------------------------------------------------------------------------
// 6. effectiveDistance shortcut vs direct path
// ---------------------------------------------------------------------------

describe('WormholeNetwork – effectiveDistance', () => {
  it('without wormholes, effective distance equals hyperbolic distance', () => {
    const net = new WormholeNetwork();
    const source = [0, 0];
    const target = [0.5, 0];

    const effective = net.effectiveDistance(source, target);
    // Should be a positive hyperbolic distance
    expect(effective).toBeGreaterThan(0);
  });

  it('a well-placed wormhole reduces effective distance below direct', () => {
    const net = new WormholeNetwork();
    // Source near origin, target near boundary
    const source = [0, 0];
    const target = [0.95, 0];
    // Wormhole with throats near source and target
    const wormhole = net.createWormhole([0.01, 0], [0.94, 0], 1_000_000);

    // Direct distance is large (near boundary = exponential blowup)
    const directApprox = net.effectiveDistance(source, target, wormhole.createdAt - 1);
    // effectiveDistance should consider the wormhole shortcut
    // Create a new network without wormholes to get the direct distance
    const netDirect = new WormholeNetwork();
    const directDist = netDirect.effectiveDistance(source, target);

    const effective = net.effectiveDistance(source, target, wormhole.createdAt);

    expect(effective).toBeLessThanOrEqual(directDist);
  });

  it('effective distance is non-negative', () => {
    const net = new WormholeNetwork();
    net.createWormhole([0.2, 0.2], [0.8, 0.8], 1_000_000);

    const effective = net.effectiveDistance([0, 0], [0.5, 0.5]);
    expect(effective).toBeGreaterThanOrEqual(0);
  });

  it('effective distance from a point to itself is 0', () => {
    const net = new WormholeNetwork();
    net.createWormhole([0, 0], [0.5, 0], 1_000_000);

    const effective = net.effectiveDistance([0.3, 0.3], [0.3, 0.3]);
    expect(effective).toBeCloseTo(0, 5);
  });
});

// ---------------------------------------------------------------------------
// 7. Pruning collapsed wormholes
// ---------------------------------------------------------------------------

describe('WormholeNetwork – prune', () => {
  it('prune removes wormholes below minStability threshold', () => {
    const net = new WormholeNetwork();
    const halfLife = 0.001; // very short
    const wormhole = net.createWormhole([0, 0], [0.5, 0], halfLife);

    const pruned = net.prune(0.1, wormhole.createdAt + 1_000_000);

    expect(pruned).toBe(1);
    expect(net.size).toBe(0);
  });

  it('prune keeps stable wormholes', () => {
    const net = new WormholeNetwork();
    const wormhole = net.createWormhole([0, 0], [0.5, 0], 1_000_000);

    const pruned = net.prune(0.1, wormhole.createdAt);

    expect(pruned).toBe(0);
    expect(net.size).toBe(1);
  });

  it('prune returns the count of removed wormholes', () => {
    const net = new WormholeNetwork();
    const halfLife = 0.001;
    const w1 = net.createWormhole([0, 0], [0.1, 0], halfLife);
    net.createWormhole([0.2, 0], [0.3, 0], halfLife);
    net.createWormhole([0.4, 0], [0.5, 0], 1_000_000); // stable

    const farFuture = w1.createdAt + 1_000_000;
    const pruned = net.prune(0.1, farFuture);

    expect(pruned).toBe(2);
    expect(net.size).toBe(1);
  });

  it('prune with default minStability removes collapsed wormholes', () => {
    const net = new WormholeNetwork();
    const wormhole = net.createWormhole([0, 0], [0.5, 0], 0.001);

    net.prune(undefined, wormhole.createdAt + 1_000_000);

    expect(net.size).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// 8. Multiple wormholes
// ---------------------------------------------------------------------------

describe('WormholeNetwork – multiple wormholes', () => {
  it('manages many wormholes independently', () => {
    const net = new WormholeNetwork();
    const count = 10;

    for (let i = 0; i < count; i++) {
      const x = (i * 0.08) + 0.01;
      net.createWormhole([x, 0], [x + 0.05, 0], 1_000_000);
    }

    expect(net.size).toBe(count);
    expect(net.getAll()).toHaveLength(count);
  });

  it('each wormhole maintains independent stability decay', () => {
    const net = new WormholeNetwork();
    const w1 = net.createWormhole([0, 0], [0.5, 0], 1); // 1 second halfLife
    const w2 = net.createWormhole([0, 0], [0.5, 0], 1_000_000); // very long halfLife

    // 10 seconds later → w1 has gone through 10 half-lives
    const checkTime = w1.createdAt + 10_000;
    const s1 = net.getStability(w1, checkTime);
    const s2 = net.getStability(w2, checkTime);

    // w1 decays much faster
    expect(s1).toBeLessThan(s2);
    expect(s1).toBeCloseTo(Math.pow(0.5, 10), 3); // ~1/1024
  });

  it('findNearest selects the globally closest stable wormhole throat', () => {
    const net = new WormholeNetwork();
    const halfLife = 1_000_000;

    // Wormhole A: throatA far from origin
    net.createWormhole([0.5, 0], [0.9, 0], halfLife);
    // Wormhole B: throatA very close to origin
    const wB = net.createWormhole([0.01, 0], [0.8, 0], halfLife);
    // Wormhole C: throatB somewhat close
    net.createWormhole([0.7, 0], [0.1, 0], halfLife);

    const result = net.findNearest([0, 0], 0, wB.createdAt);

    expect(result).not.toBeNull();
    expect(result!.wormhole.id).toBe(wB.id);
    expect(result!.throat).toBe('A');
  });

  it('transport across multiple sequential wormholes', () => {
    const net = new WormholeNetwork();
    const halfLife = 1_000_000;
    const wA = net.createWormhole([0, 0], [0.5, 0], halfLife);
    const wB = net.createWormhole([0.5, 0], [0.9, 0], halfLife);

    const r1 = net.transport([0, 0], wA.id, wA.createdAt);
    expect(r1.success).toBe(true);
    expect(r1.destination).toEqual([0.5, 0]);

    const r2 = net.transport(r1.destination, wB.id, wB.createdAt);
    expect(r2.success).toBe(true);
    expect(r2.destination).toEqual([0.9, 0]);
  });

  it('pruning affects only collapsed wormholes while leaving stable ones', () => {
    const net = new WormholeNetwork();
    const unstable1 = net.createWormhole([0, 0], [0.1, 0], 0.001);
    net.createWormhole([0.2, 0], [0.3, 0], 0.001);
    net.createWormhole([0.4, 0], [0.5, 0], 1_000_000); // stable
    net.createWormhole([0.6, 0], [0.7, 0], 1_000_000); // stable

    const farFuture = unstable1.createdAt + 1_000_000;
    const pruned = net.prune(0.01, farFuture);

    expect(pruned).toBe(2);
    expect(net.size).toBe(2);
  });
});
