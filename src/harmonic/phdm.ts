/**
 * Polyhedral Hamiltonian Defense Manifold (PHDM)
 *
 * @file phdm.ts
 * @module harmonic/phdm
 * @layer Layer 8
 * @component PHDM — Polyhedral Hamiltonian Defense Manifold
 * @version 3.3.0
 *
 * Unified security + governance system built on 16 canonical polyhedra:
 *
 * 1. INTRUSION DETECTION — Monitors state deviations from the expected
 *    geodesic curve through 6D polyhedral space via cubic spline interpolation.
 *    Deviation or curvature anomalies trigger intrusion flags.
 *
 * 2. HMAC KEY CHAIN — Traverses the polyhedra in a Hamiltonian path,
 *    generating K_{i+1} = HMAC-SHA256(K_i, Serialize(P_i)) at each step.
 *    Path integrity verified via timingSafeEqual.
 *
 * 3. FLUX GOVERNANCE — Polyhedra are classified by family (Platonic, Archimedean,
 *    Kepler-Poinsot, Toroidal, Johnson, Rhombic). Flux states restrict which
 *    families are active:
 *      POLLY (full) → all 16 polyhedra
 *      QUASI (defensive) → Platonic + Archimedean (8)
 *      DEMI (survival) → Platonic only (5)
 *
 * 4. PHASON SHIFT — Rotates the 6D→3D projection matrix (quasicrystal key
 *    rotation), invalidating cached geodesic positions. Defense mechanism
 *    against persistent adversaries.
 *
 * Merges the security manifold (formerly phdm.ts) and cognitive lattice
 * (formerly python/scbe/brain.py) into a single canonical module.
 *
 * Canonical name: Polyhedral Hamiltonian Defense Manifold
 * (All other expansions — "Dynamic Mesh", "Half-plane Drift Monitor",
 *  "Piecewise Hamiltonian Distance Metric" — are retired.)
 */

import * as crypto from 'crypto';

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

/** Polyhedra family classification */
export type PolyhedronFamily =
  | 'platonic'
  | 'archimedean'
  | 'kepler-poinsot'
  | 'toroidal'
  | 'johnson'
  | 'rhombic';

/**
 * Polyhedron representation with topological properties
 */
export interface Polyhedron {
  name: string;
  vertices: number; // V
  edges: number; // E
  faces: number; // F
  genus: number; // g (topological invariant)
  family: PolyhedronFamily;
}

/**
 * Flux state — controls which polyhedra families are active.
 * Maps to the POLLY/QUASI/DEMI containment postures.
 */
export type FluxState = 'POLLY' | 'QUASI' | 'DEMI';

/** Families active per flux state */
const FLUX_FAMILIES: Record<FluxState, PolyhedronFamily[]> = {
  POLLY: ['platonic', 'archimedean', 'kepler-poinsot', 'toroidal', 'johnson', 'rhombic'],
  QUASI: ['platonic', 'archimedean'],
  DEMI: ['platonic'],
};

/**
 * Compute Euler characteristic: χ = V - E + F = 2(1-g)
 */
export function eulerCharacteristic(poly: Polyhedron): number {
  return poly.vertices - poly.edges + poly.faces;
}

/**
 * Verify topological validity: χ = 2(1-g)
 */
export function isValidTopology(poly: Polyhedron): boolean {
  const chi = eulerCharacteristic(poly);
  const expected = 2 * (1 - poly.genus);
  return chi === expected;
}

/**
 * Generate topological hash (SHA256) for tamper detection
 */
export function topologicalHash(poly: Polyhedron): string {
  const data = `${poly.name}:${poly.vertices}:${poly.edges}:${poly.faces}:${poly.genus}`;
  return crypto.createHash('sha256').update(data).digest('hex');
}

/**
 * Serialize polyhedron for HMAC input
 */
export function serializePolyhedron(poly: Polyhedron): Buffer {
  const chi = eulerCharacteristic(poly);
  const hash = topologicalHash(poly);
  const data = `${poly.name}|V=${poly.vertices}|E=${poly.edges}|F=${poly.faces}|χ=${chi}|g=${poly.genus}|hash=${hash}`;
  return Buffer.from(data, 'utf-8');
}

/**
 * 16 Canonical Polyhedra — classified by family for flux governance.
 *
 * Platonic (5): Core axioms — always available, even in DEMI mode
 * Archimedean (3): Processing layer — available in QUASI and POLLY
 * Kepler-Poinsot (2): High-risk zone — POLLY only
 * Toroidal (2): Recursive/self-diagnostic — POLLY only
 * Johnson (2): Domain connectors — POLLY only
 * Rhombic (2): Space-filling logic — POLLY only
 */
export const CANONICAL_POLYHEDRA: Polyhedron[] = [
  // Platonic Solids (5) — Core
  { name: 'Tetrahedron', vertices: 4, edges: 6, faces: 4, genus: 0, family: 'platonic' },
  { name: 'Cube', vertices: 8, edges: 12, faces: 6, genus: 0, family: 'platonic' },
  { name: 'Octahedron', vertices: 6, edges: 12, faces: 8, genus: 0, family: 'platonic' },
  { name: 'Dodecahedron', vertices: 20, edges: 30, faces: 12, genus: 0, family: 'platonic' },
  { name: 'Icosahedron', vertices: 12, edges: 30, faces: 20, genus: 0, family: 'platonic' },

  // Archimedean Solids (3) — Processing
  { name: 'Truncated Tetrahedron', vertices: 12, edges: 18, faces: 8, genus: 0, family: 'archimedean' },
  { name: 'Cuboctahedron', vertices: 12, edges: 24, faces: 14, genus: 0, family: 'archimedean' },
  { name: 'Icosidodecahedron', vertices: 30, edges: 60, faces: 32, genus: 0, family: 'archimedean' },

  // Kepler-Poinsot (2) — High-risk
  { name: 'Small Stellated Dodecahedron', vertices: 12, edges: 30, faces: 12, genus: 4, family: 'kepler-poinsot' },
  { name: 'Great Dodecahedron', vertices: 12, edges: 30, faces: 12, genus: 4, family: 'kepler-poinsot' },

  // Toroidal (2) — Recursive
  { name: 'Szilassi', vertices: 7, edges: 21, faces: 14, genus: 1, family: 'toroidal' },
  { name: 'Csaszar', vertices: 7, edges: 21, faces: 14, genus: 1, family: 'toroidal' },

  // Johnson Solids (2) — Connectors
  { name: 'Pentagonal Bipyramid', vertices: 7, edges: 15, faces: 10, genus: 0, family: 'johnson' },
  { name: 'Triangular Cupola', vertices: 9, edges: 15, faces: 8, genus: 0, family: 'johnson' },

  // Rhombic (2) — Space-filling
  { name: 'Rhombic Dodecahedron', vertices: 14, edges: 24, faces: 12, genus: 0, family: 'rhombic' },
  { name: 'Bilinski Dodecahedron', vertices: 8, edges: 18, faces: 12, genus: 0, family: 'rhombic' },
];

/**
 * Hamiltonian Path through polyhedra with HMAC chaining
 */
export class PHDMHamiltonianPath {
  private polyhedra: Polyhedron[];
  private keys: Buffer[] = [];

  constructor(polyhedra: Polyhedron[] = CANONICAL_POLYHEDRA) {
    this.polyhedra = polyhedra;
  }

  /**
   * Compute Hamiltonian path with sequential HMAC chaining
   * K_{i+1} = HMAC-SHA256(K_i, Serialize(P_i))
   */
  computePath(masterKey: Buffer): Buffer[] {
    this.keys = [masterKey];

    for (let i = 0; i < this.polyhedra.length; i++) {
      const poly = this.polyhedra[i];
      const currentKey = this.keys[i];
      const polyData = serializePolyhedron(poly);

      // K_{i+1} = HMAC-SHA256(K_i, Serialize(P_i))
      const hmac = crypto.createHmac('sha256', currentKey);
      hmac.update(polyData);
      const nextKey = hmac.digest();

      this.keys.push(nextKey);
    }

    return this.keys;
  }

  /**
   * Verify path integrity
   */
  verifyPath(masterKey: Buffer, expectedFinalKey: Buffer): boolean {
    const computedKeys = this.computePath(masterKey);
    const finalKey = computedKeys[computedKeys.length - 1];
    return crypto.timingSafeEqual(finalKey, expectedFinalKey);
  }

  /**
   * Get key at specific step
   */
  getKey(step: number): Buffer | null {
    if (step < 0 || step >= this.keys.length) return null;
    return this.keys[step];
  }

  /**
   * Get polyhedron at specific step
   */
  getPolyhedron(step: number): Polyhedron | null {
    if (step < 0 || step >= this.polyhedra.length) return null;
    return this.polyhedra[step];
  }
}

/**
 * 6D point in Langues space
 */
export interface Point6D {
  x1: number;
  x2: number;
  x3: number;
  x4: number;
  x5: number;
  x6: number;
}

/**
 * Convert Point6D to array
 */
function point6DToArray(p: Point6D): number[] {
  return [p.x1, p.x2, p.x3, p.x4, p.x5, p.x6];
}

/**
 * Convert array to Point6D
 */
function arrayToPoint6D(arr: number[]): Point6D {
  return {
    x1: arr[0] || 0,
    x2: arr[1] || 0,
    x3: arr[2] || 0,
    x4: arr[3] || 0,
    x5: arr[4] || 0,
    x6: arr[5] || 0,
  };
}

/**
 * Euclidean distance in 6D space
 */
export function distance6D(p1: Point6D, p2: Point6D): number {
  const dx1 = p1.x1 - p2.x1;
  const dx2 = p1.x2 - p2.x2;
  const dx3 = p1.x3 - p2.x3;
  const dx4 = p1.x4 - p2.x4;
  const dx5 = p1.x5 - p2.x5;
  const dx6 = p1.x6 - p2.x6;

  return Math.sqrt(dx1 * dx1 + dx2 * dx2 + dx3 * dx3 + dx4 * dx4 + dx5 * dx5 + dx6 * dx6);
}

/**
 * Compute centroid of polyhedron in 6D space
 * Maps topological properties to 6D coordinates
 */
export function computeCentroid(poly: Polyhedron): Point6D {
  const chi = eulerCharacteristic(poly);

  return {
    x1: poly.vertices / 30.0, // Normalized vertices
    x2: poly.edges / 60.0, // Normalized edges
    x3: poly.faces / 32.0, // Normalized faces
    x4: chi / 2.0, // Euler characteristic
    x5: poly.genus, // Genus
    x6: Math.log(poly.vertices + poly.edges + poly.faces), // Complexity
  };
}

/**
 * Cubic spline interpolation in 6D
 */
export class CubicSpline6D {
  private points: Point6D[];
  private t: number[];

  constructor(points: Point6D[]) {
    this.points = points;
    this.t = Array.from({ length: points.length }, (_, i) => i / (points.length - 1));
  }

  /**
   * Evaluate spline at parameter t ∈ [0, 1]
   */
  evaluate(t: number): Point6D {
    if (t <= 0) return this.points[0];
    if (t >= 1) return this.points[this.points.length - 1];

    // Find segment
    let i = 0;
    while (i < this.t.length - 1 && this.t[i + 1] < t) {
      i++;
    }

    // Local parameter within segment
    const t0 = this.t[i];
    const t1 = this.t[i + 1];
    const localT = (t - t0) / (t1 - t0);

    // Cubic Hermite interpolation
    const p0 = this.points[i];
    const p1 = this.points[i + 1];

    // Hermite basis functions
    const h00 = 2 * localT ** 3 - 3 * localT ** 2 + 1;
    const h10 = localT ** 3 - 2 * localT ** 2 + localT;
    const h01 = -2 * localT ** 3 + 3 * localT ** 2;
    const h11 = localT ** 3 - localT ** 2;

    // Tangents (finite differences)
    const m0 = this.getTangent(i);
    const m1 = this.getTangent(i + 1);

    return {
      x1: h00 * p0.x1 + h10 * m0.x1 + h01 * p1.x1 + h11 * m1.x1,
      x2: h00 * p0.x2 + h10 * m0.x2 + h01 * p1.x2 + h11 * m1.x2,
      x3: h00 * p0.x3 + h10 * m0.x3 + h01 * p1.x3 + h11 * m1.x3,
      x4: h00 * p0.x4 + h10 * m0.x4 + h01 * p1.x4 + h11 * m1.x4,
      x5: h00 * p0.x5 + h10 * m0.x5 + h01 * p1.x5 + h11 * m1.x5,
      x6: h00 * p0.x6 + h10 * m0.x6 + h01 * p1.x6 + h11 * m1.x6,
    };
  }

  /**
   * Compute tangent at point i using finite differences
   */
  private getTangent(i: number): Point6D {
    if (i === 0) {
      // Forward difference
      return {
        x1: this.points[1].x1 - this.points[0].x1,
        x2: this.points[1].x2 - this.points[0].x2,
        x3: this.points[1].x3 - this.points[0].x3,
        x4: this.points[1].x4 - this.points[0].x4,
        x5: this.points[1].x5 - this.points[0].x5,
        x6: this.points[1].x6 - this.points[0].x6,
      };
    } else if (i === this.points.length - 1) {
      // Backward difference
      return {
        x1: this.points[i].x1 - this.points[i - 1].x1,
        x2: this.points[i].x2 - this.points[i - 1].x2,
        x3: this.points[i].x3 - this.points[i - 1].x3,
        x4: this.points[i].x4 - this.points[i - 1].x4,
        x5: this.points[i].x5 - this.points[i - 1].x5,
        x6: this.points[i].x6 - this.points[i - 1].x6,
      };
    } else {
      // Central difference
      return {
        x1: (this.points[i + 1].x1 - this.points[i - 1].x1) / 2,
        x2: (this.points[i + 1].x2 - this.points[i - 1].x2) / 2,
        x3: (this.points[i + 1].x3 - this.points[i - 1].x3) / 2,
        x4: (this.points[i + 1].x4 - this.points[i - 1].x4) / 2,
        x5: (this.points[i + 1].x5 - this.points[i - 1].x5) / 2,
        x6: (this.points[i + 1].x6 - this.points[i - 1].x6) / 2,
      };
    }
  }

  /**
   * Compute first derivative γ'(t)
   */
  derivative(t: number, h: number = 0.001): Point6D {
    const p1 = this.evaluate(t - h);
    const p2 = this.evaluate(t + h);

    return {
      x1: (p2.x1 - p1.x1) / (2 * h),
      x2: (p2.x2 - p1.x2) / (2 * h),
      x3: (p2.x3 - p1.x3) / (2 * h),
      x4: (p2.x4 - p1.x4) / (2 * h),
      x5: (p2.x5 - p1.x5) / (2 * h),
      x6: (p2.x6 - p1.x6) / (2 * h),
    };
  }

  /**
   * Compute second derivative γ''(t)
   */
  secondDerivative(t: number, h: number = 0.001): Point6D {
    const d1 = this.derivative(t - h, h);
    const d2 = this.derivative(t + h, h);

    return {
      x1: (d2.x1 - d1.x1) / (2 * h),
      x2: (d2.x2 - d1.x2) / (2 * h),
      x3: (d2.x3 - d1.x3) / (2 * h),
      x4: (d2.x4 - d1.x4) / (2 * h),
      x5: (d2.x5 - d1.x5) / (2 * h),
      x6: (d2.x6 - d1.x6) / (2 * h),
    };
  }

  /**
   * Compute curvature κ(t) = |γ''(t)| / |γ'(t)|²
   */
  curvature(t: number): number {
    const d1 = this.derivative(t);
    const d2 = this.secondDerivative(t);

    const d1Mag = Math.sqrt(
      d1.x1 ** 2 + d1.x2 ** 2 + d1.x3 ** 2 + d1.x4 ** 2 + d1.x5 ** 2 + d1.x6 ** 2
    );

    const d2Mag = Math.sqrt(
      d2.x1 ** 2 + d2.x2 ** 2 + d2.x3 ** 2 + d2.x4 ** 2 + d2.x5 ** 2 + d2.x6 ** 2
    );

    if (d1Mag < 1e-10) return 0;

    return d2Mag / d1Mag ** 2;
  }
}

/**
 * Intrusion detection via manifold deviation
 */
export interface IntrusionResult {
  isIntrusion: boolean;
  deviation: number;
  threatVelocity: number;
  curvature: number;
  rhythmPattern: string;
  timestamp: number;
}

export class PHDMDeviationDetector {
  private geodesic: CubicSpline6D;
  private snapThreshold: number;
  private curvatureThreshold: number;
  private deviationHistory: number[] = [];

  constructor(
    polyhedra: Polyhedron[] = CANONICAL_POLYHEDRA,
    snapThreshold: number = 0.1,
    curvatureThreshold: number = 0.5
  ) {
    // Compute centroids for all polyhedra
    const centroids = polyhedra.map(computeCentroid);

    // Create geodesic curve through centroids
    this.geodesic = new CubicSpline6D(centroids);

    this.snapThreshold = snapThreshold;
    this.curvatureThreshold = curvatureThreshold;
  }

  /**
   * Detect intrusion at time t
   */
  detect(state: Point6D, t: number): IntrusionResult {
    // Expected position on geodesic
    const expected = this.geodesic.evaluate(t);

    // Deviation from geodesic
    const deviation = distance6D(state, expected);

    // Threat velocity (rate of deviation change)
    this.deviationHistory.push(deviation);
    if (this.deviationHistory.length > 10) {
      this.deviationHistory.shift();
    }

    const threatVelocity =
      this.deviationHistory.length > 1
        ? this.deviationHistory[this.deviationHistory.length - 1] -
          this.deviationHistory[this.deviationHistory.length - 2]
        : 0;

    // Curvature at current position
    const curvature = this.geodesic.curvature(t);

    // Intrusion detection
    const isIntrusion = deviation > this.snapThreshold || curvature > this.curvatureThreshold;

    // 1-0 rhythm pattern (1=safe, 0=intrusion)
    const rhythmBit = isIntrusion ? '0' : '1';

    return {
      isIntrusion,
      deviation,
      threatVelocity,
      curvature,
      rhythmPattern: rhythmBit,
      timestamp: Date.now(),
    };
  }

  /**
   * Simulate attack scenarios
   */
  simulateAttack(
    attackType: 'deviation' | 'skip' | 'curvature',
    intensity: number = 1.0
  ): IntrusionResult[] {
    const results: IntrusionResult[] = [];
    const steps = 16;

    for (let i = 0; i < steps; i++) {
      const t = i / (steps - 1);
      let state = this.geodesic.evaluate(t);

      // Apply attack
      switch (attackType) {
        case 'deviation':
          // Add random noise
          state.x1 += (Math.random() - 0.5) * intensity;
          state.x2 += (Math.random() - 0.5) * intensity;
          break;

        case 'skip':
          // Skip a polyhedron (jump ahead)
          if (i === 4) {
            const tSkip = (i + 2) / (steps - 1);
            state = this.geodesic.evaluate(tSkip);
          }
          break;

        case 'curvature':
          // Manipulate path curvature
          state.x3 += Math.sin(t * Math.PI * 4) * intensity;
          state.x4 += Math.cos(t * Math.PI * 4) * intensity;
          break;
      }

      results.push(this.detect(state, t));
    }

    return results;
  }

  /**
   * Generate full rhythm pattern from results
   */
  static getRhythmPattern(results: IntrusionResult[]): string {
    return results.map((r) => r.rhythmPattern).join('');
  }
}

// ═══════════════════════════════════════════════════════════════
// Flux Governance — Polyhedra family filtering
// ═══════════════════════════════════════════════════════════════

/**
 * Get the active polyhedra for a given flux state.
 *
 * POLLY: all 16 — full capability
 * QUASI: Platonic + Archimedean (8) — defensive posture
 * DEMI: Platonic only (5) — survival mode
 */
export function getActivePolyhedra(
  fluxState: FluxState,
  polyhedra: Polyhedron[] = CANONICAL_POLYHEDRA,
): Polyhedron[] {
  const allowedFamilies = new Set(FLUX_FAMILIES[fluxState]);
  return polyhedra.filter((p) => allowedFamilies.has(p.family));
}

// ═══════════════════════════════════════════════════════════════
// Phason Shift — 6D projection rotation (key rotation defense)
// ═══════════════════════════════════════════════════════════════

const PHI = (1 + Math.sqrt(5)) / 2;

/**
 * Generate the default 6D→3D icosahedral projection matrix.
 * Based on golden ratio for quasicrystal symmetry.
 */
export function generateProjectionMatrix(): number[][] {
  const norm = Math.sqrt(2 + PHI);
  return [
    [1 / norm, PHI / norm, 0, -1 / norm, PHI / norm, 0],
    [PHI / norm, 0, 1 / norm, PHI / norm, 0, -1 / norm],
    [0, 1 / norm, PHI / norm, 0, -1 / norm, PHI / norm],
  ];
}

/**
 * Apply a phason shift: rotate the 6D→3D projection by angle theta
 * in the (dim0, dim1) plane. This changes which 3D slice of the 6D
 * lattice is visible, effectively rotating the quasicrystal tiling.
 *
 * @param matrix - Current 3x6 projection matrix
 * @param theta - Rotation angle (radians)
 * @param dim0 - First dimension of rotation plane (default: 0)
 * @param dim1 - Second dimension of rotation plane (default: 1)
 * @returns New projection matrix
 */
export function phasonShift(
  matrix: number[][],
  theta: number,
  dim0: number = 0,
  dim1: number = 1,
): number[][] {
  // Build 6D rotation matrix (identity + Givens rotation in (dim0, dim1))
  const rot6d: number[][] = Array.from({ length: 6 }, (_, i) =>
    Array.from({ length: 6 }, (_, j) => (i === j ? 1 : 0)),
  );
  const c = Math.cos(theta);
  const s = Math.sin(theta);
  rot6d[dim0][dim0] = c;
  rot6d[dim0][dim1] = -s;
  rot6d[dim1][dim0] = s;
  rot6d[dim1][dim1] = c;

  // Multiply: newMatrix = matrix @ rot6d^T  (each row of matrix * columns of rot6d)
  const result: number[][] = [];
  for (let r = 0; r < matrix.length; r++) {
    const row: number[] = [];
    for (let j = 0; j < 6; j++) {
      let sum = 0;
      for (let k = 0; k < 6; k++) {
        sum += matrix[r][k] * rot6d[k][j];
      }
      row.push(sum);
    }
    result.push(row);
  }

  return result;
}

// ═══════════════════════════════════════════════════════════════
// Complete PHDM System
// ═══════════════════════════════════════════════════════════════

/**
 * Polyhedral Hamiltonian Defense Manifold — unified security + governance.
 *
 * Combines:
 * - HMAC key chain (PHDMHamiltonianPath)
 * - Geodesic deviation intrusion detection (PHDMDeviationDetector)
 * - Flux state governance (POLLY/QUASI/DEMI)
 * - Phason shift defense (6D projection rotation)
 */
export class PolyhedralHamiltonianDefenseManifold {
  private path: PHDMHamiltonianPath;
  private detector: PHDMDeviationDetector;
  private _fluxState: FluxState = 'POLLY';
  private _projectionMatrix: number[][];
  private _allPolyhedra: Polyhedron[];

  constructor(
    polyhedra: Polyhedron[] = CANONICAL_POLYHEDRA,
    snapThreshold: number = 0.1,
    curvatureThreshold: number = 0.5,
  ) {
    this._allPolyhedra = polyhedra;
    this._projectionMatrix = generateProjectionMatrix();
    this.path = new PHDMHamiltonianPath(polyhedra);
    this.detector = new PHDMDeviationDetector(polyhedra, snapThreshold, curvatureThreshold);
  }

  /**
   * Initialize with master key — computes HMAC key chain
   */
  initialize(masterKey: Buffer): Buffer[] {
    return this.path.computePath(masterKey);
  }

  /**
   * Monitor state at time t — intrusion detection
   */
  monitor(state: Point6D, t: number): IntrusionResult {
    return this.detector.detect(state, t);
  }

  /**
   * Simulate attack scenarios
   */
  simulateAttack(
    attackType: 'deviation' | 'skip' | 'curvature',
    intensity: number = 1.0,
  ): IntrusionResult[] {
    return this.detector.simulateAttack(attackType, intensity);
  }

  /**
   * Get all 16 canonical polyhedra
   */
  getPolyhedra(): Polyhedron[] {
    return this._allPolyhedra;
  }

  // ─────────────────────────────────────────────────────────────
  // Flux Governance
  // ─────────────────────────────────────────────────────────────

  /**
   * Get the current flux state.
   */
  get fluxState(): FluxState {
    return this._fluxState;
  }

  /**
   * Set flux state — restricts which polyhedra families are active.
   * Rebuilds the detector geodesic with only the active polyhedra.
   */
  setFluxState(state: FluxState, snapThreshold?: number, curvatureThreshold?: number): void {
    this._fluxState = state;
    const active = this.getActivePolyhedra();
    this.path = new PHDMHamiltonianPath(active);
    this.detector = new PHDMDeviationDetector(
      active,
      snapThreshold ?? 0.1,
      curvatureThreshold ?? 0.5,
    );
  }

  /**
   * Get polyhedra active under the current flux state.
   */
  getActivePolyhedra(): Polyhedron[] {
    return getActivePolyhedra(this._fluxState, this._allPolyhedra);
  }

  /**
   * Get count of active polyhedra.
   */
  get activeCount(): number {
    return this.getActivePolyhedra().length;
  }

  // ─────────────────────────────────────────────────────────────
  // Phason Shift
  // ─────────────────────────────────────────────────────────────

  /**
   * Execute a phason shift — rotates the 6D→3D projection matrix.
   * This is a defense mechanism that invalidates cached positions.
   *
   * @param theta - Rotation angle (radians). Default: random.
   * @param dim0 - First dimension of rotation plane
   * @param dim1 - Second dimension of rotation plane
   */
  executePhasonShift(theta?: number, dim0: number = 0, dim1: number = 1): void {
    const angle = theta ?? Math.random() * 2 * Math.PI;
    this._projectionMatrix = phasonShift(this._projectionMatrix, angle, dim0, dim1);
  }

  /**
   * Get the current projection matrix.
   */
  getProjectionMatrix(): number[][] {
    return this._projectionMatrix.map((row) => [...row]);
  }

  /**
   * Project a 6D point to 3D using the current projection matrix.
   */
  projectTo3D(point: Point6D): [number, number, number] {
    const p = point6DToArray(point);
    const result: [number, number, number] = [0, 0, 0];
    for (let r = 0; r < 3; r++) {
      for (let c = 0; c < 6; c++) {
        result[r] += this._projectionMatrix[r][c] * p[c];
      }
    }
    return result;
  }
}
