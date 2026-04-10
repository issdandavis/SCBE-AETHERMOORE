/**
 * @file geosealCompass.ts
 * @module geosealCompass
 * @layer Layer 3, Layer 5, Layer 7, Layer 11
 * @component GeoSeal Compass — Multi-Point Navigation through Sacred Tongue Space-Time
 * @version 1.0.0
 *
 * The Six Sacred Tongues form a hexagonal compass rose in the Poincaré ball:
 *
 *        Kor'aelin (0°)
 *          ╱    ╲
 *   Draumric      Avali
 *   (300°)         (60°)
 *      │             │
 *   Umbroth       Runethic
 *   (240°)         (120°)
 *          ╲    ╱
 *       Cassisivadan (180°)
 *
 * Any direction through the manifold can be expressed as a weighted blend of
 * tongue bearings. Routes between waypoints follow hyperbolic geodesics,
 * with governance scoring at each hop.
 *
 * Integrates with:
 * - GeoSeal v1/v2 (immune swarm trust scoring)
 * - DTN Bundle system (store-and-forward relay)
 * - L11 Triadic temporal distance (time-windowed routing)
 * - L12 Harmonic wall (governance scoring per segment)
 *
 * @axiom Unitarity — Route preserves total signal through manifold
 * @axiom Locality — Each hop respects spatial bounds (ball containment)
 * @axiom Causality — Temporal windows enforce time-ordering
 * @axiom Symmetry — Compass rose is symmetric under tongue rotation
 */

import {
  hyperbolicDistance,
  exponentialMap,
  logarithmicMap,
  mobiusAdd,
  projectToBall,
  clampToBall,
  phaseDeviation,
} from './harmonic/hyperbolic.js';

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════

const PHI = (1 + Math.sqrt(5)) / 2;
const EPSILON = 1e-8;

/** Sacred Tongue compass bearings (radians, evenly spaced at π/3) */
export const COMPASS_BEARINGS: Record<string, number> = {
  KO: 0.0,                    // Kor'aelin — North (Control)
  AV: Math.PI / 3,            // Avali — NE (Transport)
  RU: (2 * Math.PI) / 3,      // Runethic — SE (Policy)
  CA: Math.PI,                 // Cassisivadan — South (Compute)
  UM: (4 * Math.PI) / 3,      // Umbroth — SW (Privacy)
  DR: (5 * Math.PI) / 3,      // Draumric — NW (Integrity)
};

/** Tongue phi weights (L3 Langues Weighting System) */
const TONGUE_WEIGHTS: Record<string, number> = {
  KO: 1.0,
  AV: PHI,
  RU: PHI ** 2,
  CA: PHI ** 3,
  UM: PHI ** 4,
  DR: PHI ** 5,
};

/** All tongue keys in compass order */
const TONGUES: string[] = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

/** A compass bearing expressed as tongue-weight blend */
export interface CompassBearing {
  /** Raw angle in radians [0, 2π) */
  angle: number;
  /** Dominant tongue (closest compass point) */
  dominantTongue: string;
  /** Secondary tongue (second-closest compass point) */
  secondaryTongue: string;
  /** Blend ratio: 0 = pure dominant, 1 = pure secondary */
  blend: number;
  /** Per-tongue affinity weights (sum to 1) */
  tongueAffinities: Record<string, number>;
}

/** A named point in the product manifold */
export interface Waypoint {
  /** Unique waypoint identifier */
  readonly id: string;
  /** Human-readable label */
  readonly label: string;
  /** Position in Poincaré ball (||p|| < 1) */
  readonly position: number[];
  /** Tongue phase at this waypoint (null = unaligned) */
  readonly phase: number | null;
  /** Temporal coordinate (simulation step or timestamp) */
  readonly time: number;
  /** Tongue assignment (if any) */
  readonly tongue?: string;
  /** Governance score at this waypoint */
  readonly governanceScore: number;
}

/** A single hop between two waypoints */
export interface RouteSegment {
  /** Source waypoint */
  from: Waypoint;
  /** Destination waypoint */
  to: Waypoint;
  /** Hyperbolic distance of this segment */
  distance: number;
  /** Compass bearing from → to */
  bearing: CompassBearing;
  /** Governance score for this segment: H(d,pd) = 1/(1+φ*d_H+2*pd) */
  governanceScore: number;
  /** Phase deviation between endpoints */
  phaseDeviation: number;
  /** Temporal span (to.time - from.time) */
  temporalSpan: number;
  /** Geodesic interpolation points (for visualization/relay) */
  geodesicPoints: number[][];
}

/** A complete route through multiple waypoints */
export interface Route {
  /** Ordered waypoints (including origin and destination) */
  waypoints: Waypoint[];
  /** Segments between consecutive waypoints */
  segments: RouteSegment[];
  /** Total hyperbolic distance */
  totalDistance: number;
  /** Minimum governance score across all segments (bottleneck) */
  minGovernanceScore: number;
  /** Average governance score */
  avgGovernanceScore: number;
  /** Total temporal span */
  temporalSpan: number;
  /** Whether the route passes governance threshold */
  isViable: boolean;
}

/** Temporal window for route validity */
export interface TemporalWindow {
  /** Start time (simulation step or timestamp) */
  openTime: number;
  /** End time */
  closeTime: number;
  /** Tongue resonance during this window */
  resonantTongue: string;
  /** Window bandwidth (how many bundles can transit) */
  bandwidth: number;
}

/** Route planning options */
export interface RoutePlanOptions {
  /** Maximum hops allowed (default 14 — one per layer) */
  maxHops?: number;
  /** Minimum governance score per segment (default 0.3) */
  minGovernanceScore?: number;
  /** Number of geodesic interpolation points per segment (default 5) */
  geodesicResolution?: number;
  /** Perturbation density for governance scoring (default 0.0) */
  perturbationDensity?: number;
  /** Available temporal windows (for time-constrained routing) */
  temporalWindows?: TemporalWindow[];
}

// ═══════════════════════════════════════════════════════════════
// Compass Rose — Direction computation
// ═══════════════════════════════════════════════════════════════

/**
 * Normalize an angle to [0, 2π).
 */
function normalizeAngle(angle: number): number {
  const TWO_PI = 2 * Math.PI;
  return ((angle % TWO_PI) + TWO_PI) % TWO_PI;
}

/**
 * Compute the compass bearing between two points in the Poincaré ball.
 *
 * Uses the logarithmic map to get the tangent vector at `from` pointing
 * toward `to`, then projects onto the 2D compass plane to get an angle.
 * The angle is decomposed into tongue-weight blends.
 *
 * A4: Symmetry — bearing computation is equivariant under tongue rotation.
 */
export function computeBearing(from: number[], to: number[]): CompassBearing {
  // Get tangent vector at `from` pointing toward `to`
  const tangent = logarithmicMap(from, to);

  // Project to 2D compass plane (first two dimensions carry phase geometry)
  const dx = tangent[0] || 0;
  const dy = tangent[1] || 0;

  // Angle in radians
  const rawAngle = Math.atan2(dy, dx);
  const angle = normalizeAngle(rawAngle);

  // Find dominant and secondary tongue
  const sectorSize = Math.PI / 3; // 60° per tongue
  let dominantIdx = Math.round(angle / sectorSize) % 6;
  const dominantAngle = dominantIdx * sectorSize;

  // Blend: how far between dominant and the next tongue?
  const angleDiff = normalizeAngle(angle - dominantAngle);
  const blend = angleDiff / sectorSize;

  // Secondary is the next tongue in the direction of travel
  const secondaryIdx = blend >= 0.5 ? (dominantIdx + 1) % 6 : (dominantIdx + 5) % 6;

  // Compute per-tongue affinities (inverse angular distance, normalized)
  const affinities: Record<string, number> = {};
  let totalAffinity = 0;
  for (let i = 0; i < 6; i++) {
    const tongueAngle = i * sectorSize;
    const dev = Math.min(
      Math.abs(angle - tongueAngle),
      2 * Math.PI - Math.abs(angle - tongueAngle)
    );
    // Affinity falls off as cosine of angular distance, floored at 0
    const aff = Math.max(0, Math.cos(dev));
    affinities[TONGUES[i]] = aff;
    totalAffinity += aff;
  }
  // Normalize
  if (totalAffinity > EPSILON) {
    for (const t of TONGUES) {
      affinities[t] /= totalAffinity;
    }
  }

  return {
    angle,
    dominantTongue: TONGUES[dominantIdx],
    secondaryTongue: TONGUES[secondaryIdx],
    blend: Math.min(blend, 1 - blend), // 0 = pure dominant, 0.5 = midpoint
    tongueAffinities: affinities,
  };
}

/**
 * Get the canonical compass position for a tongue.
 *
 * Returns a point in the Poincaré ball at radius 0.3 in the tongue's
 * compass direction. Used as anchor points for route planning.
 */
export function tongueAnchorPosition(tongue: string, dimension: number = 6): number[] {
  const bearing = COMPASS_BEARINGS[tongue];
  if (bearing === undefined) throw new Error(`Unknown tongue: ${tongue}`);

  const pos = new Array(dimension).fill(0);
  pos[0] = 0.3 * Math.cos(bearing);
  pos[1] = 0.3 * Math.sin(bearing);
  return pos;
}

/**
 * Express an arbitrary direction as a tongue-weighted vector.
 *
 * Given a bearing, returns a position in the Poincaré ball that lies
 * in that compass direction at the specified radius.
 */
export function bearingToPosition(
  bearing: CompassBearing,
  radius: number = 0.5,
  dimension: number = 6,
): number[] {
  const pos = new Array(dimension).fill(0);
  pos[0] = radius * Math.cos(bearing.angle);
  pos[1] = radius * Math.sin(bearing.angle);
  return pos;
}

// ═══════════════════════════════════════════════════════════════
// Waypoint creation
// ═══════════════════════════════════════════════════════════════

/**
 * Create a waypoint at a specific position in the product manifold.
 */
export function createWaypoint(
  id: string,
  label: string,
  position: number[],
  phase: number | null = null,
  time: number = 0,
  tongue?: string,
): Waypoint {
  // Ensure position is inside the ball
  const safePos = clampToBall([...position], 0.99);

  // Compute governance score at this point
  // H(d,0) = 1/(1+φ*d_origin) where d_origin is distance from origin
  const origin = new Array(safePos.length).fill(0);
  const d = hyperbolicDistance(origin, safePos);
  const governanceScore = 1 / (1 + PHI * d);

  return {
    id,
    label,
    position: safePos,
    phase,
    time,
    tongue,
    governanceScore,
  };
}

/**
 * Create a waypoint at a tongue's anchor position.
 */
export function createTongueWaypoint(
  tongue: string,
  time: number = 0,
  dimension: number = 6,
): Waypoint {
  const bearing = COMPASS_BEARINGS[tongue];
  if (bearing === undefined) throw new Error(`Unknown tongue: ${tongue}`);

  return createWaypoint(
    `tongue-${tongue}`,
    tongue,
    tongueAnchorPosition(tongue, dimension),
    bearing,
    time,
    tongue,
  );
}

// ═══════════════════════════════════════════════════════════════
// Geodesic interpolation
// ═══════════════════════════════════════════════════════════════

/**
 * Interpolate along the hyperbolic geodesic from p to q.
 *
 * Uses exponential/logarithmic maps to walk along the geodesic arc
 * in the Poincaré ball. Returns `steps` points including endpoints.
 *
 * A1: Unitarity — geodesic preserves norm through the manifold.
 * A2: Locality — all points remain inside the ball.
 */
export function geodesicInterpolate(
  p: number[],
  q: number[],
  steps: number = 5,
): number[][] {
  if (steps < 2) return [p, q];

  const points: number[][] = [p];

  // Tangent vector from p toward q
  const tangent = logarithmicMap(p, q);

  for (let i = 1; i < steps - 1; i++) {
    const t = i / (steps - 1);
    // Scale tangent by t, then exponential map from p
    const scaledTangent = tangent.map((v) => v * t);
    const point = exponentialMap(p, scaledTangent);
    points.push(clampToBall(point, 0.99));
  }

  points.push(q);
  return points;
}

// ═══════════════════════════════════════════════════════════════
// Route Segment computation
// ═══════════════════════════════════════════════════════════════

/**
 * Compute the harmonic wall governance score for a segment.
 *
 * H(d, pd) = 1 / (1 + φ * d_H + 2 * pd)
 *
 * @axiom L12 canonical formula
 */
function segmentGovernanceScore(distance: number, perturbationDensity: number): number {
  return 1 / (1 + PHI * distance + 2 * perturbationDensity);
}

/**
 * Build a route segment between two waypoints.
 */
export function buildSegment(
  from: Waypoint,
  to: Waypoint,
  geodesicResolution: number = 5,
  perturbationDensity: number = 0.0,
): RouteSegment {
  const distance = hyperbolicDistance(from.position, to.position);
  const bearing = computeBearing(from.position, to.position);
  const phaseDev = phaseDeviation(from.phase, to.phase);
  const temporalSpan = to.time - from.time;

  // Governance: use phase deviation as part of perturbation density
  const effectivePD = perturbationDensity + phaseDev * 0.5;
  const govScore = segmentGovernanceScore(distance, effectivePD);

  const geodesicPoints = geodesicInterpolate(
    from.position,
    to.position,
    geodesicResolution,
  );

  return {
    from,
    to,
    distance,
    bearing,
    governanceScore: govScore,
    phaseDeviation: phaseDev,
    temporalSpan,
    geodesicPoints,
  };
}

// ═══════════════════════════════════════════════════════════════
// Route planning
// ═══════════════════════════════════════════════════════════════

/** Governance threshold for route viability */
const DEFAULT_MIN_GOVERNANCE = 0.3;

/**
 * Plan a direct route between two waypoints (no intermediate hops).
 */
export function planDirectRoute(
  origin: Waypoint,
  destination: Waypoint,
  options: RoutePlanOptions = {},
): Route {
  const segment = buildSegment(
    origin,
    destination,
    options.geodesicResolution ?? 5,
    options.perturbationDensity ?? 0.0,
  );

  const minGov = options.minGovernanceScore ?? DEFAULT_MIN_GOVERNANCE;

  return {
    waypoints: [origin, destination],
    segments: [segment],
    totalDistance: segment.distance,
    minGovernanceScore: segment.governanceScore,
    avgGovernanceScore: segment.governanceScore,
    temporalSpan: segment.temporalSpan,
    isViable: segment.governanceScore >= minGov,
  };
}

/**
 * Plan a multi-hop route through intermediate waypoints.
 *
 * The waypoints array should include origin and destination.
 * Each consecutive pair becomes a segment. The route is evaluated
 * for governance viability — every segment must meet the threshold.
 *
 * A3: Causality — waypoints must be in temporal order.
 */
export function planRoute(
  waypoints: Waypoint[],
  options: RoutePlanOptions = {},
): Route {
  if (waypoints.length < 2) {
    throw new Error('Route requires at least 2 waypoints');
  }

  const resolution = options.geodesicResolution ?? 5;
  const pd = options.perturbationDensity ?? 0.0;
  const minGov = options.minGovernanceScore ?? DEFAULT_MIN_GOVERNANCE;

  const segments: RouteSegment[] = [];
  let totalDistance = 0;
  let minGovScore = Infinity;
  let totalGovScore = 0;

  for (let i = 0; i < waypoints.length - 1; i++) {
    const segment = buildSegment(waypoints[i], waypoints[i + 1], resolution, pd);
    segments.push(segment);
    totalDistance += segment.distance;
    minGovScore = Math.min(minGovScore, segment.governanceScore);
    totalGovScore += segment.governanceScore;
  }

  const avgGovScore = segments.length > 0 ? totalGovScore / segments.length : 0;
  const temporalSpan = waypoints[waypoints.length - 1].time - waypoints[0].time;

  return {
    waypoints,
    segments,
    totalDistance,
    minGovernanceScore: minGovScore === Infinity ? 0 : minGovScore,
    avgGovernanceScore: avgGovScore,
    temporalSpan,
    isViable: minGovScore >= minGov,
  };
}

/**
 * Auto-route: find a tongue-guided path from origin to destination.
 *
 * Strategy: if the direct route's governance score is below threshold,
 * route through the tongue anchors that lie closest to the bearing.
 * This "follows the compass" — using trusted tongue waypoints as
 * relay stations that boost governance scores.
 *
 * Like a ship navigating by stars: each tongue is a fixed celestial
 * point. The compass tells you which tongues to aim for.
 */
export function autoRoute(
  origin: Waypoint,
  destination: Waypoint,
  options: RoutePlanOptions = {},
): Route {
  const minGov = options.minGovernanceScore ?? DEFAULT_MIN_GOVERNANCE;
  const maxHops = options.maxHops ?? 14;
  const dim = origin.position.length;

  // Try direct route first
  const direct = planDirectRoute(origin, destination, options);
  if (direct.isViable) return direct;

  // Direct route failed governance — route through tongue anchors
  const bearing = computeBearing(origin.position, destination.position);

  // Rank tongues by affinity to the travel direction
  const rankedTongues = TONGUES
    .map((t) => ({ tongue: t, affinity: bearing.tongueAffinities[t] }))
    .sort((a, b) => b.affinity - a.affinity);

  // Build intermediate waypoints through highest-affinity tongues
  // Time is interpolated linearly between origin and destination
  const intermediates: Waypoint[] = [];
  const timeStep = (destination.time - origin.time) / (maxHops + 1);

  for (let i = 0; i < Math.min(rankedTongues.length, maxHops - 1); i++) {
    const t = rankedTongues[i].tongue;
    if (rankedTongues[i].affinity < EPSILON) continue;

    const anchorPos = tongueAnchorPosition(t, dim);
    const wp = createWaypoint(
      `relay-${t}-${i}`,
      `${t} relay`,
      anchorPos,
      COMPASS_BEARINGS[t],
      origin.time + timeStep * (i + 1),
      t,
    );
    intermediates.push(wp);
  }

  if (intermediates.length === 0) {
    // No good relays — return direct even if suboptimal
    return direct;
  }

  // Sort intermediates by distance from origin (greedy nearest-first)
  intermediates.sort((a, b) => {
    const dA = hyperbolicDistance(origin.position, a.position);
    const dB = hyperbolicDistance(origin.position, b.position);
    return dA - dB;
  });

  // Build full waypoint sequence
  const fullPath = [origin, ...intermediates, destination];

  // Greedily prune: remove relays that don't improve governance
  const pruned = greedyPrune(fullPath, options);

  return planRoute(pruned, options);
}

/**
 * Greedy pruning: remove intermediate waypoints that don't improve
 * the route's minimum governance score.
 */
function greedyPrune(waypoints: Waypoint[], options: RoutePlanOptions): Waypoint[] {
  if (waypoints.length <= 2) return waypoints;

  const result = [...waypoints];
  let improved = true;

  while (improved && result.length > 2) {
    improved = false;
    const currentRoute = planRoute(result, options);

    for (let i = 1; i < result.length - 1; i++) {
      // Try removing waypoint i
      const candidate = [...result.slice(0, i), ...result.slice(i + 1)];
      const candidateRoute = planRoute(candidate, options);

      // Keep removal if it doesn't hurt governance
      if (candidateRoute.minGovernanceScore >= currentRoute.minGovernanceScore) {
        result.splice(i, 1);
        improved = true;
        break;
      }
    }
  }

  return result;
}

// ═══════════════════════════════════════════════════════════════
// Temporal routing
// ═══════════════════════════════════════════════════════════════

/**
 * Filter route segments by temporal windows.
 *
 * Each segment must fall within an active temporal window to be valid.
 * Returns the route with invalid segments flagged (governance = 0).
 *
 * A3: Causality — only forward-time routes are valid.
 */
export function applyTemporalWindows(
  route: Route,
  windows: TemporalWindow[],
): Route {
  const updatedSegments = route.segments.map((seg) => {
    // Check if segment falls within any active window
    const segStart = seg.from.time;
    const segEnd = seg.to.time;

    // Causality check: time must flow forward
    if (segEnd < segStart) {
      return { ...seg, governanceScore: 0 };
    }

    const validWindow = windows.find(
      (w) => segStart >= w.openTime && segEnd <= w.closeTime,
    );

    if (!validWindow) {
      // No window — segment is not temporally valid
      return { ...seg, governanceScore: 0 };
    }

    // Bonus governance if segment's tongue matches window's resonant tongue
    const tongueBonus =
      seg.bearing.dominantTongue === validWindow.resonantTongue ? 0.1 : 0;

    return {
      ...seg,
      governanceScore: Math.min(1, seg.governanceScore + tongueBonus),
    };
  });

  const minGov = Math.min(...updatedSegments.map((s) => s.governanceScore));
  const avgGov =
    updatedSegments.reduce((sum, s) => sum + s.governanceScore, 0) /
    updatedSegments.length;

  return {
    ...route,
    segments: updatedSegments,
    minGovernanceScore: minGov,
    avgGovernanceScore: avgGov,
    isViable: minGov >= DEFAULT_MIN_GOVERNANCE,
  };
}

// ═══════════════════════════════════════════════════════════════
// Triadic temporal distance (L11 integration)
// ═══════════════════════════════════════════════════════════════

/**
 * Compute triadic temporal distance for a route.
 *
 * Three time scales:
 * - Immediate: per-segment phase deviation (fast signal)
 * - Medium: rolling average governance over 3-segment windows
 * - Long-term: total route governance trend
 *
 * d_tri = w_i * d_immediate + w_m * d_medium + w_l * d_long
 *
 * @axiom A3: Causality — temporal distance is strictly non-negative
 * @layer L11
 */
export function triadicTemporalDistance(route: Route): number {
  if (route.segments.length === 0) return 0;

  // Immediate: average phase deviation across segments
  const immediate =
    route.segments.reduce((sum, s) => sum + s.phaseDeviation, 0) /
    route.segments.length;

  // Medium: variance of governance scores in rolling 3-segment windows
  let medium = 0;
  if (route.segments.length >= 3) {
    const windowScores: number[] = [];
    for (let i = 0; i <= route.segments.length - 3; i++) {
      const windowAvg =
        (route.segments[i].governanceScore +
          route.segments[i + 1].governanceScore +
          route.segments[i + 2].governanceScore) /
        3;
      windowScores.push(windowAvg);
    }
    const mean = windowScores.reduce((s, v) => s + v, 0) / windowScores.length;
    medium = windowScores.reduce((s, v) => s + (v - mean) ** 2, 0) / windowScores.length;
  }

  // Long-term: 1 - overall governance trend (high governance = low long-term distance)
  const longTerm = 1 - route.avgGovernanceScore;

  // Phi-weighted combination (immediate is fastest, long-term is deepest)
  const w_i = 1.0;
  const w_m = PHI;
  const w_l = PHI ** 2;
  const total = w_i + w_m + w_l;

  return (w_i * immediate + w_m * medium + w_l * longTerm) / total;
}

// ═══════════════════════════════════════════════════════════════
// Compass Rose visualization data
// ═══════════════════════════════════════════════════════════════

/** Compass rose point for visualization */
export interface CompassRosePoint {
  tongue: string;
  angle: number;
  weight: number;
  position: [number, number];
}

/**
 * Generate the compass rose as plottable data.
 *
 * Returns 6 points on the unit circle with phi-weighted radii,
 * suitable for rendering as a radar/spider chart.
 */
export function generateCompassRose(): CompassRosePoint[] {
  return TONGUES.map((tongue) => {
    const angle = COMPASS_BEARINGS[tongue];
    const weight = TONGUE_WEIGHTS[tongue];
    return {
      tongue,
      angle,
      weight,
      position: [Math.cos(angle), Math.sin(angle)] as [number, number],
    };
  });
}

/**
 * Get a human-readable compass direction string.
 *
 * Examples: "Kor'aelin-ward", "between Avali and Runethic"
 */
export function bearingToString(bearing: CompassBearing): string {
  const FULL_NAMES: Record<string, string> = {
    KO: "Kor'aelin",
    AV: 'Avali',
    RU: 'Runethic',
    CA: 'Cassisivadan',
    UM: 'Umbroth',
    DR: 'Draumric',
  };

  if (bearing.blend < 0.1) {
    return `${FULL_NAMES[bearing.dominantTongue]}-ward`;
  }

  return `between ${FULL_NAMES[bearing.dominantTongue]} and ${FULL_NAMES[bearing.secondaryTongue]}`;
}
