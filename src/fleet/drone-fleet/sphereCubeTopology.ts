/**
 * @file sphereCubeTopology.ts
 * @module fleet/drone-fleet/sphereCubeTopology
 * @layer Layer 8, Layer 12, Layer 13
 * @component Sphere-in-Cube Mission Bounds (GeoSeal Pattern)
 *
 * Configures governance so that drone AI "interior thoughts" (sphere geodesics)
 * are computationally free only if they exist within allowed hypercube cells.
 *
 * Sphere (Sⁿ): drone AI "brain" (behavior/intent)
 * Hypercube (ℝᵐ): hard mission rules (geofence, ROE)
 *
 * Interior Path: geodesic within cube → low latency, normal execution
 * Exterior Path: geodesic intersects cube boundary → high dwell time,
 *   Roundtable signatures required, Harmonic Wall scaling applied
 *
 * A2: Locality — spatial bounds enforced by cube containment
 */

/** 3D bounding box for mission area */
export interface MissionBounds {
  /** Minimum corner [x, y, z] */
  min: [number, number, number];
  /** Maximum corner [x, y, z] */
  max: [number, number, number];
}

/** Configuration for sphere-cube topology */
export interface SphereCubeConfig {
  /** Mission geofence bounds */
  missionBounds: MissionBounds;
  /** Harmonic wall base R for exterior path cost scaling */
  harmonicR: number;
  /** Golden ratio phi for cost exponent */
  phi: number;
  /** Base dwell time multiplier for exterior paths (ms) */
  exteriorDwellMultiplier: number;
  /** Number of roundtable signatures required for exterior path */
  roundtableQuorum: number;
}

/** Maneuver projected into sphere geometry */
export interface ManeuverProjection {
  /** Start position in 3D space */
  start: [number, number, number];
  /** End position in 3D space */
  end: [number, number, number];
  /** Sphere-space geodesic direction (unit vector) */
  geodesicDirection: [number, number, number];
  /** Geodesic arc length */
  arcLength: number;
}

/** Classification of a maneuver path */
export type PathType = 'INTERIOR' | 'EXTERIOR';

/** Result of maneuver classification */
export interface ManeuverClassification {
  /** Whether path is interior or exterior */
  pathType: PathType;
  /** Whether maneuver is authorized */
  authorized: boolean;
  /** Harmonic wall cost (1.0 for interior, exponential for exterior) */
  harmonicCost: number;
  /** Dwell time in ms before maneuver can execute */
  dwellTimeMs: number;
  /** Number of roundtable signatures required (0 for interior) */
  requiredSignatures: number;
  /** Fraction of geodesic that lies outside bounds [0, 1] */
  exteriorFraction: number;
  /** Penetration depth: max distance beyond boundary */
  penetrationDepth: number;
}

const PHI = 1.618033988749895;

export const DEFAULT_SPHERE_CUBE_CONFIG: SphereCubeConfig = {
  missionBounds: { min: [-1, -1, -1], max: [1, 1, 1] },
  harmonicR: 1.5,
  phi: PHI,
  exteriorDwellMultiplier: 100,
  roundtableQuorum: 3,
};

/**
 * Check whether a 3D point lies within the mission bounds hypercube.
 */
export function isInsideBounds(point: [number, number, number], bounds: MissionBounds): boolean {
  return (
    point[0] >= bounds.min[0] &&
    point[0] <= bounds.max[0] &&
    point[1] >= bounds.min[1] &&
    point[1] <= bounds.max[1] &&
    point[2] >= bounds.min[2] &&
    point[2] <= bounds.max[2]
  );
}

/**
 * Compute penetration depth — maximum distance any point on the geodesic
 * extends beyond the mission bounds.
 *
 * @param point - 3D point to test
 * @param bounds - Mission bounds
 * @returns Distance beyond nearest boundary face, or 0 if inside
 */
export function penetrationDepth(point: [number, number, number], bounds: MissionBounds): number {
  let maxPen = 0;
  for (let i = 0; i < 3; i++) {
    if (point[i] < bounds.min[i]) maxPen = Math.max(maxPen, bounds.min[i] - point[i]);
    if (point[i] > bounds.max[i]) maxPen = Math.max(maxPen, point[i] - bounds.max[i]);
  }
  return maxPen;
}

/**
 * Sample a geodesic (straight-line approximation in 3D) and determine
 * what fraction lies outside the mission bounds.
 *
 * @param maneuver - Projected maneuver
 * @param bounds - Mission bounds
 * @param samples - Number of sample points along geodesic (default 50)
 * @returns Fraction outside bounds [0, 1] and max penetration depth
 */
export function sampleGeodesic(
  maneuver: ManeuverProjection,
  bounds: MissionBounds,
  samples: number = 50
): { exteriorFraction: number; maxPenetration: number } {
  let outsideCount = 0;
  let maxPen = 0;

  for (let i = 0; i <= samples; i++) {
    const t = i / samples;
    const point: [number, number, number] = [
      maneuver.start[0] + t * (maneuver.end[0] - maneuver.start[0]),
      maneuver.start[1] + t * (maneuver.end[1] - maneuver.start[1]),
      maneuver.start[2] + t * (maneuver.end[2] - maneuver.start[2]),
    ];

    if (!isInsideBounds(point, bounds)) {
      outsideCount++;
      const pen = penetrationDepth(point, bounds);
      if (pen > maxPen) maxPen = pen;
    }
  }

  return {
    exteriorFraction: outsideCount / (samples + 1),
    maxPenetration: maxPen,
  };
}

/**
 * Compute Harmonic Wall cost for exterior path.
 *
 * H(d*, R) = R^((φ · d*)²)
 *
 * where d* is the penetration depth (normalized).
 *
 * @param penetration - Penetration depth
 * @param R - Harmonic wall base
 * @param phi - Golden ratio
 * @returns Harmonic cost (≥ 1.0)
 */
export function harmonicWallCost(penetration: number, R: number, phi: number): number {
  if (penetration <= 0) return 1.0;
  const exponent = phi * penetration * (phi * penetration);
  return Math.pow(R, exponent);
}

/**
 * Classify a maneuver as Interior or Exterior path and compute
 * associated costs.
 *
 * Interior: geodesic within cube → zero additional cost
 * Exterior: geodesic crosses boundary → Harmonic Wall cost + dwell time
 *
 * @param maneuver - The planned maneuver
 * @param config - Sphere-cube configuration
 * @returns ManeuverClassification
 */
export function classifyManeuver(
  maneuver: ManeuverProjection,
  config: SphereCubeConfig = DEFAULT_SPHERE_CUBE_CONFIG
): ManeuverClassification {
  const { exteriorFraction, maxPenetration } = sampleGeodesic(maneuver, config.missionBounds);

  const isInterior = exteriorFraction === 0;
  const pathType: PathType = isInterior ? 'INTERIOR' : 'EXTERIOR';

  // A4: Clamping — cost clamped to [1.0, ∞)
  const harmonicCost = isInterior
    ? 1.0
    : harmonicWallCost(maxPenetration, config.harmonicR, config.phi);

  const dwellTimeMs = isInterior ? 0 : config.exteriorDwellMultiplier * harmonicCost;

  const requiredSignatures = isInterior ? 0 : config.roundtableQuorum;

  return {
    pathType,
    authorized: isInterior,
    harmonicCost,
    dwellTimeMs,
    requiredSignatures,
    exteriorFraction,
    penetrationDepth: maxPenetration,
  };
}

/**
 * Create a maneuver projection from start/end positions.
 */
export function createManeuver(
  start: [number, number, number],
  end: [number, number, number]
): ManeuverProjection {
  const dx = end[0] - start[0];
  const dy = end[1] - start[1];
  const dz = end[2] - start[2];
  const len = Math.sqrt(dx * dx + dy * dy + dz * dz);
  const dir: [number, number, number] = len > 0 ? [dx / len, dy / len, dz / len] : [0, 0, 0];

  return {
    start,
    end,
    geodesicDirection: dir,
    arcLength: len,
  };
}
