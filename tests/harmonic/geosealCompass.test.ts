/**
 * @file geosealCompass.test.ts
 * @module tests/harmonic/geosealCompass
 * @layer Layer 3, Layer 5, Layer 7, Layer 11
 *
 * Tests for GeoSeal Compass — multi-point navigation through Sacred Tongue space-time.
 *
 * Test tiers:
 * - L1 (smoke): compass rose generation, waypoint creation
 * - L2 (unit): bearing computation, geodesic interpolation, segment scoring
 * - L3 (integration): full route planning, auto-routing
 * - L4 (property): bearing symmetry, governance monotonicity
 */

import { describe, it, expect } from 'vitest';
import {
  COMPASS_BEARINGS,
  computeBearing,
  tongueAnchorPosition,
  bearingToPosition,
  createWaypoint,
  createTongueWaypoint,
  geodesicInterpolate,
  buildSegment,
  planDirectRoute,
  planRoute,
  autoRoute,
  applyTemporalWindows,
  triadicTemporalDistance,
  generateCompassRose,
  bearingToString,
} from '../../src/geosealCompass.js';

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════

function vecNorm(v: number[]): number {
  return Math.sqrt(v.reduce((s, x) => s + x * x, 0));
}

const DIM = 6;

// ═══════════════════════════════════════════════════════════════
// L1: Smoke tests
// ═══════════════════════════════════════════════════════════════

describe('GeoSeal Compass — Smoke', () => {
  it('generates a 6-point compass rose', () => {
    const rose = generateCompassRose();
    expect(rose).toHaveLength(6);
    expect(rose.map((r) => r.tongue)).toEqual(['KO', 'AV', 'RU', 'CA', 'UM', 'DR']);
  });

  it('creates waypoints inside the Poincaré ball', () => {
    const wp = createWaypoint('test', 'Test', [0.5, 0.3, 0, 0, 0, 0], 0, 0);
    expect(vecNorm(wp.position)).toBeLessThan(1.0);
    expect(wp.governanceScore).toBeGreaterThan(0);
    expect(wp.governanceScore).toBeLessThanOrEqual(1);
  });

  it('creates tongue waypoints for all 6 tongues', () => {
    const tongues = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
    for (const t of tongues) {
      const wp = createTongueWaypoint(t, 0, DIM);
      expect(wp.tongue).toBe(t);
      expect(wp.phase).toBe(COMPASS_BEARINGS[t]);
      expect(vecNorm(wp.position)).toBeLessThan(1.0);
    }
  });

  it('COMPASS_BEARINGS has 6 entries evenly spaced', () => {
    const bearings = Object.values(COMPASS_BEARINGS);
    expect(bearings).toHaveLength(6);
    for (let i = 1; i < bearings.length; i++) {
      expect(bearings[i] - bearings[i - 1]).toBeCloseTo(Math.PI / 3, 8);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// L2: Unit tests — Bearing computation
// ═══════════════════════════════════════════════════════════════

describe('GeoSeal Compass — Bearing', () => {
  it('bearing from origin to KO-direction points toward KO', () => {
    const origin = [0, 0, 0, 0, 0, 0];
    const ko = tongueAnchorPosition('KO', DIM);
    const bearing = computeBearing(origin, ko);
    expect(bearing.dominantTongue).toBe('KO');
    expect(bearing.tongueAffinities['KO']).toBeGreaterThan(0);
  });

  it('bearing from origin to CA-direction points toward CA (180°)', () => {
    const origin = [0, 0, 0, 0, 0, 0];
    const ca = tongueAnchorPosition('CA', DIM);
    const bearing = computeBearing(origin, ca);
    expect(bearing.dominantTongue).toBe('CA');
  });

  it('tongue affinities sum to approximately 1', () => {
    const origin = [0, 0, 0, 0, 0, 0];
    const target = [0.3, 0.4, 0, 0, 0, 0];
    const bearing = computeBearing(origin, target);
    const sum = Object.values(bearing.tongueAffinities).reduce((s, v) => s + v, 0);
    expect(sum).toBeCloseTo(1.0, 5);
  });

  it('bearing angle is in [0, 2π)', () => {
    const tests = [
      { from: [0, 0, 0, 0, 0, 0], to: [0.5, 0, 0, 0, 0, 0] },
      { from: [0, 0, 0, 0, 0, 0], to: [-0.5, 0, 0, 0, 0, 0] },
      { from: [0, 0, 0, 0, 0, 0], to: [0, 0.5, 0, 0, 0, 0] },
      { from: [0, 0, 0, 0, 0, 0], to: [0, -0.5, 0, 0, 0, 0] },
      { from: [0.1, 0.1, 0, 0, 0, 0], to: [-0.3, -0.2, 0, 0, 0, 0] },
    ];
    for (const { from, to } of tests) {
      const bearing = computeBearing(from, to);
      expect(bearing.angle).toBeGreaterThanOrEqual(0);
      expect(bearing.angle).toBeLessThan(2 * Math.PI);
    }
  });

  it('bearingToPosition creates a valid ball point', () => {
    const bearing = computeBearing([0, 0, 0, 0, 0, 0], [0.3, 0.4, 0, 0, 0, 0]);
    const pos = bearingToPosition(bearing, 0.5, DIM);
    expect(vecNorm(pos)).toBeLessThan(1.0);
    expect(pos).toHaveLength(DIM);
  });

  it('bearingToString returns readable direction', () => {
    const bearing = computeBearing([0, 0, 0, 0, 0, 0], tongueAnchorPosition('KO', DIM));
    const str = bearingToString(bearing);
    expect(typeof str).toBe('string');
    expect(str.length).toBeGreaterThan(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// L2: Unit tests — Geodesic interpolation
// ═══════════════════════════════════════════════════════════════

describe('GeoSeal Compass — Geodesic', () => {
  it('geodesic interpolation returns correct number of points', () => {
    const p = [0.1, 0, 0, 0, 0, 0];
    const q = [0, 0.5, 0, 0, 0, 0];
    const points = geodesicInterpolate(p, q, 7);
    expect(points).toHaveLength(7);
  });

  it('geodesic starts at p and ends at q', () => {
    const p = [0.1, 0.2, 0, 0, 0, 0];
    const q = [-0.3, 0.1, 0, 0, 0, 0];
    const points = geodesicInterpolate(p, q, 5);
    // First point should be p
    for (let i = 0; i < DIM; i++) {
      expect(points[0][i]).toBeCloseTo(p[i], 8);
    }
    // Last point should be q
    for (let i = 0; i < DIM; i++) {
      expect(points[points.length - 1][i]).toBeCloseTo(q[i], 8);
    }
  });

  it('all geodesic points are inside the Poincaré ball', () => {
    const p = [0.5, 0.3, 0, 0, 0, 0];
    const q = [-0.4, -0.5, 0, 0, 0, 0];
    const points = geodesicInterpolate(p, q, 10);
    for (const pt of points) {
      expect(vecNorm(pt)).toBeLessThan(1.0);
    }
  });

  it('geodesic with 2 steps returns just endpoints', () => {
    const p = [0.1, 0, 0, 0, 0, 0];
    const q = [0, 0.1, 0, 0, 0, 0];
    const points = geodesicInterpolate(p, q, 2);
    expect(points).toHaveLength(2);
  });
});

// ═══════════════════════════════════════════════════════════════
// L2: Unit tests — Segment scoring
// ═══════════════════════════════════════════════════════════════

describe('GeoSeal Compass — Segments', () => {
  it('segment between close same-tongue points has high governance', () => {
    const wp1 = createTongueWaypoint('KO', 0, DIM);
    const wp2 = createWaypoint('near-ko', 'near', [0.28, 0.01, 0, 0, 0, 0], 0, 1, 'KO');
    const seg = buildSegment(wp1, wp2);
    expect(seg.governanceScore).toBeGreaterThan(0.5);
    expect(seg.phaseDeviation).toBe(0); // Same phase
  });

  it('segment between opposite tongues has lower governance', () => {
    const ko = createTongueWaypoint('KO', 0, DIM);
    const ca = createTongueWaypoint('CA', 1, DIM);
    const seg = buildSegment(ko, ca);
    // Opposite tongues: phase deviation = 1.0, further apart
    expect(seg.phaseDeviation).toBe(1.0);
    expect(seg.governanceScore).toBeLessThan(0.5);
  });

  it('segment has non-negative distance', () => {
    const wp1 = createWaypoint('a', 'A', [0.1, 0.2, 0, 0, 0, 0], 0, 0);
    const wp2 = createWaypoint('b', 'B', [-0.3, 0.1, 0, 0, 0, 0], Math.PI, 1);
    const seg = buildSegment(wp1, wp2);
    expect(seg.distance).toBeGreaterThanOrEqual(0);
  });

  it('segment governance is in (0, 1]', () => {
    const wp1 = createWaypoint('a', 'A', [0, 0, 0, 0, 0, 0], 0, 0);
    const wp2 = createWaypoint('b', 'B', [0.8, 0, 0, 0, 0, 0], null, 1);
    const seg = buildSegment(wp1, wp2);
    expect(seg.governanceScore).toBeGreaterThan(0);
    expect(seg.governanceScore).toBeLessThanOrEqual(1);
  });

  it('segment includes geodesic interpolation points', () => {
    const wp1 = createTongueWaypoint('AV', 0, DIM);
    const wp2 = createTongueWaypoint('UM', 5, DIM);
    const seg = buildSegment(wp1, wp2, 8);
    expect(seg.geodesicPoints).toHaveLength(8);
  });
});

// ═══════════════════════════════════════════════════════════════
// L3: Integration — Route planning
// ═══════════════════════════════════════════════════════════════

describe('GeoSeal Compass — Route Planning', () => {
  it('direct route between nearby same-tongue points is viable', () => {
    const wp1 = createTongueWaypoint('KO', 0, DIM);
    const wp2 = createWaypoint('near-ko', 'near', [0.25, 0.05, 0, 0, 0, 0], 0, 1, 'KO');
    const route = planDirectRoute(wp1, wp2);
    expect(route.isViable).toBe(true);
    expect(route.segments).toHaveLength(1);
    expect(route.totalDistance).toBeGreaterThan(0);
  });

  it('multi-hop route through all 6 tongues', () => {
    const waypoints = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'].map((t, i) =>
      createTongueWaypoint(t, i, DIM)
    );
    const route = planRoute(waypoints);
    expect(route.segments).toHaveLength(5);
    expect(route.totalDistance).toBeGreaterThan(0);
    expect(route.temporalSpan).toBe(5);
  });

  it('route requires at least 2 waypoints', () => {
    const wp = createTongueWaypoint('KO', 0, DIM);
    expect(() => planRoute([wp])).toThrow('at least 2 waypoints');
  });

  it('auto-route finds viable path even when direct fails', () => {
    // Far apart, mismatched phases — direct route likely low governance
    const origin = createWaypoint('origin', 'Origin', [0.7, 0, 0, 0, 0, 0], null, 0);
    const dest = createWaypoint('dest', 'Dest', [-0.7, 0, 0, 0, 0, 0], null, 10);
    const route = autoRoute(origin, dest, { minGovernanceScore: 0.01 });
    expect(route.waypoints.length).toBeGreaterThanOrEqual(2);
    expect(route.totalDistance).toBeGreaterThan(0);
  });

  it('auto-route prefers direct when viable', () => {
    const wp1 = createTongueWaypoint('KO', 0, DIM);
    const wp2 = createWaypoint('near', 'Near', [0.28, 0.02, 0, 0, 0, 0], 0, 1, 'KO');
    const route = autoRoute(wp1, wp2);
    // Direct route should be viable for close same-tongue points
    expect(route.waypoints).toHaveLength(2);
  });

  it('route min governance is the bottleneck segment', () => {
    const wp1 = createTongueWaypoint('KO', 0, DIM);
    const wp2 = createTongueWaypoint('CA', 5, DIM); // Opposite tongue
    const wp3 = createTongueWaypoint('KO', 10, DIM); // Back to KO
    const route = planRoute([wp1, wp2, wp3]);
    // Min governance should be the worst segment
    const segGovs = route.segments.map((s) => s.governanceScore);
    expect(route.minGovernanceScore).toBeCloseTo(Math.min(...segGovs), 8);
  });
});

// ═══════════════════════════════════════════════════════════════
// L3: Integration — Temporal routing
// ═══════════════════════════════════════════════════════════════

describe('GeoSeal Compass — Temporal Windows', () => {
  it('segments outside temporal windows get zero governance', () => {
    const wp1 = createTongueWaypoint('KO', 0, DIM);
    const wp2 = createTongueWaypoint('AV', 5, DIM);
    const wp3 = createTongueWaypoint('RU', 10, DIM);
    const route = planRoute([wp1, wp2, wp3]);

    // Window only covers first segment
    const windows = [{ openTime: 0, closeTime: 5, resonantTongue: 'KO', bandwidth: 10 }];
    const filtered = applyTemporalWindows(route, windows);

    // Second segment should fail (time 5-10 not in any window)
    expect(filtered.segments[1].governanceScore).toBe(0);
    expect(filtered.isViable).toBe(false);
  });

  it('resonant tongue matching gives governance bonus', () => {
    const wp1 = createTongueWaypoint('KO', 0, DIM);
    const wp2 = createTongueWaypoint('AV', 5, DIM);
    const route = planRoute([wp1, wp2]);

    // Window with KO resonance — bearing from KO to AV has KO or AV dominant
    const windows = [{ openTime: 0, closeTime: 10, resonantTongue: 'KO', bandwidth: 10 }];
    const filtered = applyTemporalWindows(route, windows);
    // The original and filtered should differ if tongue matches
    // Either way, the filtered score should be >= original
    expect(filtered.segments[0].governanceScore).toBeGreaterThanOrEqual(
      route.segments[0].governanceScore
    );
  });
});

// ═══════════════════════════════════════════════════════════════
// L3: Integration — Triadic temporal distance
// ═══════════════════════════════════════════════════════════════

describe('GeoSeal Compass — Triadic Temporal Distance', () => {
  it('triadic distance is non-negative', () => {
    const waypoints = ['KO', 'AV', 'RU', 'CA'].map((t, i) => createTongueWaypoint(t, i, DIM));
    const route = planRoute(waypoints);
    const d = triadicTemporalDistance(route);
    expect(d).toBeGreaterThanOrEqual(0);
  });

  it('triadic distance is 0 for empty route', () => {
    const route: any = { segments: [], avgGovernanceScore: 0 };
    expect(triadicTemporalDistance(route)).toBe(0);
  });

  it('same-tongue route has lower triadic distance than cross-tongue', () => {
    // All KO waypoints (same tongue, low phase deviation)
    const sameRoute = planRoute([
      createWaypoint('a', 'A', [0.1, 0, 0, 0, 0, 0], 0, 0, 'KO'),
      createWaypoint('b', 'B', [0.2, 0, 0, 0, 0, 0], 0, 1, 'KO'),
      createWaypoint('c', 'C', [0.25, 0.01, 0, 0, 0, 0], 0, 2, 'KO'),
      createWaypoint('d', 'D', [0.28, 0.02, 0, 0, 0, 0], 0, 3, 'KO'),
    ]);

    // Cross-tongue (alternating KO and CA — maximum phase deviation)
    const crossRoute = planRoute([
      createTongueWaypoint('KO', 0, DIM),
      createTongueWaypoint('CA', 1, DIM),
      createTongueWaypoint('KO', 2, DIM),
      createTongueWaypoint('CA', 3, DIM),
    ]);

    const dSame = triadicTemporalDistance(sameRoute);
    const dCross = triadicTemporalDistance(crossRoute);
    expect(dSame).toBeLessThan(dCross);
  });
});

// ═══════════════════════════════════════════════════════════════
// L4: Property-based tests
// ═══════════════════════════════════════════════════════════════

describe('GeoSeal Compass — Properties', () => {
  it('A4: all tongue anchor positions have same norm', () => {
    const tongues = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
    const norms = tongues.map((t) => vecNorm(tongueAnchorPosition(t, DIM)));
    for (const n of norms) {
      expect(n).toBeCloseTo(0.3, 8);
    }
  });

  it('A2: governance score decreases with distance from origin', () => {
    const wp_near = createWaypoint('near', 'Near', [0.1, 0, 0, 0, 0, 0], 0, 0);
    const wp_mid = createWaypoint('mid', 'Mid', [0.4, 0, 0, 0, 0, 0], 0, 0);
    const wp_far = createWaypoint('far', 'Far', [0.8, 0, 0, 0, 0, 0], 0, 0);
    expect(wp_near.governanceScore).toBeGreaterThan(wp_mid.governanceScore);
    expect(wp_mid.governanceScore).toBeGreaterThan(wp_far.governanceScore);
  });

  it('compass rose positions lie on the unit circle', () => {
    const rose = generateCompassRose();
    for (const point of rose) {
      const [x, y] = point.position;
      const norm = Math.sqrt(x * x + y * y);
      expect(norm).toBeCloseTo(1.0, 8);
    }
  });

  it('A1: segment governance is bounded in (0, 1]', () => {
    // Test many random segments
    const tongues = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
    for (let i = 0; i < tongues.length; i++) {
      for (let j = 0; j < tongues.length; j++) {
        const wp1 = createTongueWaypoint(tongues[i], 0, DIM);
        const wp2 = createTongueWaypoint(tongues[j], 1, DIM);
        const seg = buildSegment(wp1, wp2);
        expect(seg.governanceScore).toBeGreaterThan(0);
        expect(seg.governanceScore).toBeLessThanOrEqual(1);
      }
    }
  });

  it('unknown tongue throws error', () => {
    expect(() => tongueAnchorPosition('INVALID')).toThrow('Unknown tongue');
    expect(() => createTongueWaypoint('INVALID')).toThrow('Unknown tongue');
  });
});
