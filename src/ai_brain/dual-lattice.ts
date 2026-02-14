/**
 * @file dual-lattice.ts
 * @module ai_brain/dual-lattice
 * @layer Layer 4, Layer 5, Layer 9, Layer 12
 * @component Dual Lattice Architecture
 * @version 1.0.0
 * @since 2026-02-08
 *
 * Implements the Dual Lattice Architecture for quasicrystal-based AI security.
 *
 * Both projection modes operate simultaneously:
 *
 *   Static Lattice (6D → 3D): Structure Generation
 *     Creates the aperiodic polyhedral mesh
 *     Defines valid Hamiltonian paths
 *     Establishes the topology that adversaries cannot predict
 *
 *   Dynamic Lattice (3D → 6D → 3D): Runtime Transform
 *     Lifts thought vectors through the 6D space
 *     Applies phason shifts for security response
 *     Projects back with transformed aperiodic structure
 *
 * Key insight: Multiples of 2 and 1 → 3 create interference patterns
 * at 3x frequencies — natural for icosahedral/φ-based symmetry.
 *
 * The dual lattice harmonics produce mutual verification:
 * the static topology constrains the dynamic transform, and the
 * dynamic transform validates the static topology.
 */

import { PHI, BRAIN_EPSILON, POINCARE_MAX_NORM } from './types.js';
import { icosahedralProjection } from './quasi-space.js';

// ═══════════════════════════════════════════════════════════════
// Dual Lattice Types
// ═══════════════════════════════════════════════════════════════

/**
 * A point in the 6D hyperspace lattice.
 * Components map to the icosahedral symmetry basis.
 */
export interface Lattice6D {
  readonly components: readonly [number, number, number, number, number, number];
}

/**
 * A point in the 3D projected space.
 * Result of cut-and-project from 6D.
 */
export interface Lattice3D {
  readonly x: number;
  readonly y: number;
  readonly z: number;
}

/**
 * A phason shift vector in 6D perpendicular space.
 * Phasons are collective excitations that rearrange
 * the aperiodic tiling without changing its statistics.
 */
export interface PhasonShift {
  /** Shift components in the 3D perpendicular subspace */
  readonly perpShift: readonly [number, number, number];
  /** Shift magnitude (amplitude of phason excitation) */
  readonly magnitude: number;
  /** Phase angle (direction in perpendicular space) */
  readonly phase: number;
}

/**
 * Result from the static lattice projection (6D → 3D).
 */
export interface StaticProjectionResult {
  /** Projected 3D point */
  point3D: Lattice3D;
  /** Perpendicular (internal) space component */
  perpComponent: readonly [number, number, number];
  /** Acceptance flag (point falls within acceptance domain) */
  accepted: boolean;
  /** Distance to acceptance boundary */
  boundaryDistance: number;
  /** Which Penrose tile type this point maps to (thick/thin rhombus analog) */
  tileType: 'thick' | 'thin';
}

/**
 * Result from the dynamic lattice transform (3D → 6D → 3D).
 */
export interface DynamicTransformResult {
  /** Lifted 6D point */
  lifted6D: Lattice6D;
  /** Phason-shifted 6D point */
  shifted6D: Lattice6D;
  /** Re-projected 3D point */
  projected3D: Lattice3D;
  /** Displacement from original position (security metric) */
  displacement: number;
  /** Interference pattern value at this point */
  interferenceValue: number;
  /** Whether the transform preserved aperiodic structure */
  structurePreserved: boolean;
}

/**
 * Combined result from both lattice modes operating together.
 */
export interface DualLatticeResult {
  /** Static lattice result */
  static: StaticProjectionResult;
  /** Dynamic lattice result */
  dynamic: DynamicTransformResult;
  /** Cross-verification score [0, 1] (how well both lattices agree) */
  coherence: number;
  /** 3x frequency interference pattern */
  tripleFrequencyInterference: number;
  /** Whether the dual lattice validates this point */
  validated: boolean;
}

/**
 * Dual Lattice configuration
 */
export interface DualLatticeConfig {
  /** Acceptance domain radius (Penrose window size) */
  acceptanceRadius: number;
  /** Phason coupling strength (how strongly shifts affect topology) */
  phasonCoupling: number;
  /** Interference detection threshold */
  interferenceThreshold: number;
  /** Maximum phason amplitude before structure breaks */
  maxPhasonAmplitude: number;
  /** Coherence threshold for dual validation */
  coherenceThreshold: number;
}

export const DEFAULT_DUAL_LATTICE_CONFIG: DualLatticeConfig = {
  acceptanceRadius: 1.0 / PHI, // Golden ratio acceptance window
  phasonCoupling: 0.1,
  interferenceThreshold: 0.3,
  maxPhasonAmplitude: 0.5,
  coherenceThreshold: 0.6,
};

// ═══════════════════════════════════════════════════════════════
// Icosahedral Projection Matrices
// ═══════════════════════════════════════════════════════════════

/**
 * Build the 6×3 "physical" projection matrix (E_parallel).
 * Projects from 6D to the 3D physical subspace.
 */
function buildParallelProjection(): number[][] {
  const c1 = Math.cos(0);
  const s1 = Math.sin(0);
  const c2 = Math.cos((2 * Math.PI) / 5);
  const s2 = Math.sin((2 * Math.PI) / 5);
  const c3 = Math.cos((4 * Math.PI) / 5);
  const s3 = Math.sin((4 * Math.PI) / 5);
  const c4 = Math.cos((6 * Math.PI) / 5);
  const s4 = Math.sin((6 * Math.PI) / 5);
  const c5 = Math.cos((8 * Math.PI) / 5);
  const s5 = Math.sin((8 * Math.PI) / 5);

  // 5-fold symmetric basis with golden ratio elevation
  const norm = Math.sqrt(2.0 / 5);
  return [
    [norm * c1, norm * c2, norm * c3, norm * c4, norm * c5, 0],
    [norm * s1, norm * s2, norm * s3, norm * s4, norm * s5, 0],
    [norm / PHI, norm / PHI, norm / PHI, norm / PHI, norm / PHI, norm * PHI],
  ];
}

/**
 * Build the 6×3 "perpendicular" projection matrix (E_perp).
 * Projects from 6D to the 3D internal (perpendicular) subspace.
 * Points in this subspace determine acceptance in the cut-and-project scheme.
 */
function buildPerpProjection(): number[][] {
  const c1 = Math.cos(0);
  const s1 = Math.sin(0);
  const c2p = Math.cos((4 * Math.PI) / 5);
  const s2p = Math.sin((4 * Math.PI) / 5);
  const c3p = Math.cos((8 * Math.PI) / 5);
  const s3p = Math.sin((8 * Math.PI) / 5);
  const c4p = Math.cos((12 * Math.PI) / 5);
  const s4p = Math.sin((12 * Math.PI) / 5);
  const c5p = Math.cos((16 * Math.PI) / 5);
  const s5p = Math.sin((16 * Math.PI) / 5);

  // Perpendicular projection uses doubled angles (2k instead of k)
  const norm = Math.sqrt(2.0 / 5);
  return [
    [norm * c1, norm * c2p, norm * c3p, norm * c4p, norm * c5p, 0],
    [norm * s1, norm * s2p, norm * s3p, norm * s4p, norm * s5p, 0],
    [norm * PHI, norm * PHI, norm * PHI, norm * PHI, norm * PHI, -norm / PHI],
  ];
}

const E_PARALLEL = buildParallelProjection();
const E_PERP = buildPerpProjection();

/**
 * Project a 6D vector to 3D using a projection matrix.
 */
function project6Dto3D(vec6: readonly number[], matrix: number[][]): Lattice3D {
  let x = 0,
    y = 0,
    z = 0;
  for (let j = 0; j < 6; j++) {
    x += matrix[0][j] * vec6[j];
    y += matrix[1][j] * vec6[j];
    z += matrix[2][j] * vec6[j];
  }
  return { x, y, z };
}

/**
 * Lift a 3D point back to 6D using pseudoinverse of parallel projection.
 * Uses least-squares fit: x6 = E_par^T (E_par E_par^T)^{-1} x3
 *
 * Since E_par is not square, we use the Moore-Penrose pseudoinverse.
 */
function lift3Dto6D(point: Lattice3D): Lattice6D {
  const x3 = [point.x, point.y, point.z];

  // E_par * E_par^T (3×3 matrix)
  const EET: number[][] = [
    [0, 0, 0],
    [0, 0, 0],
    [0, 0, 0],
  ];
  for (let i = 0; i < 3; i++) {
    for (let j = 0; j < 3; j++) {
      for (let k = 0; k < 6; k++) {
        EET[i][j] += E_PARALLEL[i][k] * E_PARALLEL[j][k];
      }
    }
  }

  // Invert 3×3 matrix
  const inv = invert3x3(EET);

  // E_par^T * inv * x3
  const temp = [0, 0, 0];
  for (let i = 0; i < 3; i++) {
    for (let j = 0; j < 3; j++) {
      temp[i] += inv[i][j] * x3[j];
    }
  }

  const result: [number, number, number, number, number, number] = [0, 0, 0, 0, 0, 0];
  for (let k = 0; k < 6; k++) {
    for (let i = 0; i < 3; i++) {
      result[k] += E_PARALLEL[i][k] * temp[i];
    }
  }

  return { components: result };
}

/**
 * Invert a 3×3 matrix using Cramer's rule.
 */
function invert3x3(m: number[][]): number[][] {
  const a = m[0][0],
    b = m[0][1],
    c = m[0][2];
  const d = m[1][0],
    e = m[1][1],
    f = m[1][2];
  const g = m[2][0],
    h = m[2][1],
    k = m[2][2];

  const det = a * (e * k - f * h) - b * (d * k - f * g) + c * (d * h - e * g);
  if (Math.abs(det) < BRAIN_EPSILON) {
    // Near-singular: return identity
    return [
      [1, 0, 0],
      [0, 1, 0],
      [0, 0, 1],
    ];
  }

  const invDet = 1 / det;
  return [
    [
      (e * k - f * h) * invDet,
      (c * h - b * k) * invDet,
      (b * f - c * e) * invDet,
    ],
    [
      (f * g - d * k) * invDet,
      (a * k - c * g) * invDet,
      (c * d - a * f) * invDet,
    ],
    [
      (d * h - e * g) * invDet,
      (b * g - a * h) * invDet,
      (a * e - b * d) * invDet,
    ],
  ];
}

// ═══════════════════════════════════════════════════════════════
// Static Lattice (6D → 3D): Structure Generation
// ═══════════════════════════════════════════════════════════════

/**
 * Project from 6D to 3D using the cut-and-project method.
 *
 * The "acceptance domain" in perpendicular space determines which
 * 6D lattice points produce valid 3D quasicrystal vertices.
 * Points outside the acceptance domain are rejected.
 */
export function staticProjection(
  point6D: Lattice6D,
  config: DualLatticeConfig = DEFAULT_DUAL_LATTICE_CONFIG
): StaticProjectionResult {
  const vec = point6D.components;

  // Project to physical (parallel) subspace
  const point3D = project6Dto3D(vec, E_PARALLEL);

  // Project to perpendicular (internal) subspace
  const perp = project6Dto3D(vec, E_PERP);
  const perpComponent: [number, number, number] = [perp.x, perp.y, perp.z];

  // Check acceptance domain (icosahedral window)
  const perpNorm = Math.sqrt(perp.x * perp.x + perp.y * perp.y + perp.z * perp.z);
  const accepted = perpNorm <= config.acceptanceRadius;
  const boundaryDistance = Math.max(0, config.acceptanceRadius - perpNorm);

  // Tile type classification based on perpendicular distance
  // Thick rhombus: closer to center of acceptance domain
  // Thin rhombus: closer to boundary
  const tileType: 'thick' | 'thin' =
    perpNorm < config.acceptanceRadius / PHI ? 'thick' : 'thin';

  return {
    point3D,
    perpComponent,
    accepted,
    boundaryDistance,
    tileType,
  };
}

/**
 * Generate an aperiodic mesh of valid Hamiltonian path vertices.
 *
 * Scans integer lattice points in 6D and projects only those
 * within the acceptance domain, creating a quasicrystalline mesh.
 *
 * @param radius - Search radius in 6D (default: 3)
 * @param config - Lattice configuration
 * @returns Array of accepted 3D vertices with metadata
 */
export function generateAperiodicMesh(
  radius: number = 3,
  config: DualLatticeConfig = DEFAULT_DUAL_LATTICE_CONFIG
): StaticProjectionResult[] {
  const results: StaticProjectionResult[] = [];
  const r = Math.floor(radius);

  // Scan a bounded region of the 6D integer lattice
  // For efficiency, only scan first 3 dimensions (extend later)
  for (let i = -r; i <= r; i++) {
    for (let j = -r; j <= r; j++) {
      for (let k = -r; k <= r; k++) {
        const point6D: Lattice6D = {
          components: [i, j, k, 0, 0, 0],
        };
        const result = staticProjection(point6D, config);
        if (result.accepted) {
          results.push(result);
        }
      }
    }
  }

  return results;
}

// ═══════════════════════════════════════════════════════════════
// Dynamic Lattice (3D → 6D → 3D): Runtime Transform
// ═══════════════════════════════════════════════════════════════

/**
 * Apply a phason shift to a 6D lattice point.
 *
 * Phasons shift points in perpendicular space, causing some
 * to enter or leave the acceptance domain. This changes the
 * local tiling without affecting statistical properties.
 *
 * Security application: phason shifts can dynamically rearrange
 * the quasicrystal structure in response to threats, making
 * the topology a moving target.
 */
export function applyPhasonShift(point6D: Lattice6D, phason: PhasonShift): Lattice6D {
  const vec = [...point6D.components] as [number, number, number, number, number, number];

  // The perpendicular projection defines which components to shift.
  // We modify the 6D point so its perpendicular projection shifts
  // by the desired amount.
  //
  // Since E_perp maps 6D → 3D, we need E_perp^T to lift the shift back.
  const shift = phason.perpShift;
  for (let k = 0; k < 6; k++) {
    for (let i = 0; i < 3; i++) {
      vec[k] += E_PERP[i][k] * shift[i] * phason.magnitude;
    }
  }

  return { components: vec };
}

/**
 * Execute the full dynamic lattice transform: 3D → 6D → 3D.
 *
 * 1. Lift the 3D thought vector to 6D using pseudoinverse
 * 2. Apply phason shift in 6D perpendicular space
 * 3. Project back to 3D with the transformed structure
 *
 * The displacement between original and re-projected points
 * is a security metric: large displacement = suspicious behavior.
 */
export function dynamicTransform(
  point3D: Lattice3D,
  phason: PhasonShift,
  config: DualLatticeConfig = DEFAULT_DUAL_LATTICE_CONFIG
): DynamicTransformResult {
  // Step 1: Lift 3D → 6D
  const lifted6D = lift3Dto6D(point3D);

  // Step 2: Apply phason shift in 6D
  const shifted6D = applyPhasonShift(lifted6D, phason);

  // Step 3: Project back 6D → 3D
  const projected3D = project6Dto3D(shifted6D.components, E_PARALLEL);

  // Compute displacement
  const dx = projected3D.x - point3D.x;
  const dy = projected3D.y - point3D.y;
  const dz = projected3D.z - point3D.z;
  const displacement = Math.sqrt(dx * dx + dy * dy + dz * dz);

  // Compute 3x frequency interference pattern
  // The dual lattice harmonics create interference at triple frequency
  const interferenceValue = computeTripleFrequencyInterference(
    lifted6D,
    shifted6D,
    point3D
  );

  // Check if aperiodic structure is preserved
  // If phason amplitude exceeds max, structure breaks
  const structurePreserved = phason.magnitude <= config.maxPhasonAmplitude;

  return {
    lifted6D,
    shifted6D,
    projected3D,
    displacement,
    interferenceValue,
    structurePreserved,
  };
}

/**
 * Compute the 3x frequency interference pattern.
 *
 * When both lattice modes are active simultaneously,
 * the harmonics create interference at 3× the fundamental frequency.
 * This is a consequence of icosahedral/φ-based symmetry where
 * multiples of 2 and 1 combine to 3.
 *
 * @returns Interference value in [-1, 1]
 */
function computeTripleFrequencyInterference(
  original6D: Lattice6D,
  shifted6D: Lattice6D,
  anchor3D: Lattice3D
): number {
  // Dot product of original and shifted in 6D (correlation)
  let dotProd = 0;
  let normA = 0;
  let normB = 0;
  for (let i = 0; i < 6; i++) {
    dotProd += original6D.components[i] * shifted6D.components[i];
    normA += original6D.components[i] * original6D.components[i];
    normB += shifted6D.components[i] * shifted6D.components[i];
  }

  const normProduct = Math.sqrt(normA * normB);
  if (normProduct < BRAIN_EPSILON) return 0;

  const correlation = dotProd / normProduct;

  // 3× frequency modulation from anchor point
  const anchorPhase =
    anchor3D.x * PHI + anchor3D.y * PHI * PHI + anchor3D.z / PHI;

  // The interference pattern at triple frequency
  return correlation * Math.cos(3 * anchorPhase);
}

// ═══════════════════════════════════════════════════════════════
// Dual Lattice System (Both Modes Active)
// ═══════════════════════════════════════════════════════════════

/**
 * Dual Lattice System — both projection modes operating simultaneously.
 *
 * The static lattice provides the structure; the dynamic lattice
 * transforms within that structure. Cross-verification between
 * the two ensures mathematical consistency.
 */
export class DualLatticeSystem {
  private readonly config: DualLatticeConfig;
  private staticMesh: StaticProjectionResult[] | null = null;
  private stepCounter: number = 0;

  constructor(config: Partial<DualLatticeConfig> = {}) {
    this.config = { ...DEFAULT_DUAL_LATTICE_CONFIG, ...config };
  }

  /**
   * Initialize the static mesh (one-time topology generation).
   * Call this once; the mesh defines the Hamiltonian path topology.
   */
  initializeMesh(radius: number = 3): StaticProjectionResult[] {
    this.staticMesh = generateAperiodicMesh(radius, this.config);
    return this.staticMesh;
  }

  /**
   * Get the cached static mesh.
   */
  getMesh(): StaticProjectionResult[] | null {
    return this.staticMesh;
  }

  /**
   * Process a 21D brain state through the dual lattice system.
   *
   * Both lattice modes run simultaneously:
   * 1. Static: Take 6D subspace, project to 3D, check acceptance
   * 2. Dynamic: Take projected 3D, lift → shift → reproject
   * 3. Cross-verify both results for coherence
   *
   * @param state21D - 21D brain state vector
   * @param phason - Phason shift for dynamic response
   * @returns Combined dual lattice result
   */
  process(state21D: number[], phason: PhasonShift): DualLatticeResult {
    this.stepCounter++;

    if (state21D.length < 6) {
      throw new RangeError(`Expected at least 6D state, got ${state21D.length}D`);
    }

    // Extract 6D subspace (navigation dimensions 6-11 from brain state)
    const nav6D: Lattice6D = {
      components: [
        state21D.length > 6 ? state21D[6] : state21D[0],
        state21D.length > 7 ? state21D[7] : state21D[1],
        state21D.length > 8 ? state21D[8] : state21D[2],
        state21D.length > 9 ? state21D[9] : state21D[3],
        state21D.length > 10 ? state21D[10] : state21D[4],
        state21D.length > 11 ? state21D[11] : state21D[5],
      ],
    };

    // ═══ Static Lattice (6D → 3D) ═══
    const staticResult = staticProjection(nav6D, this.config);

    // ═══ Dynamic Lattice (3D → 6D → 3D) ═══
    const dynamicResult = dynamicTransform(staticResult.point3D, phason, this.config);

    // ═══ Cross-Verification ═══
    const coherence = this.computeCoherence(staticResult, dynamicResult);

    // 3× frequency interference from both lattices combined
    const tripleFrequencyInterference = dynamicResult.interferenceValue;

    // Validation: both lattices must agree above threshold
    const validated =
      staticResult.accepted &&
      dynamicResult.structurePreserved &&
      coherence >= this.config.coherenceThreshold;

    return {
      static: staticResult,
      dynamic: dynamicResult,
      coherence,
      tripleFrequencyInterference,
      validated,
    };
  }

  /**
   * Create a security-responsive phason shift based on threat level.
   *
   * Higher threat → larger phason amplitude → more topology rearrangement.
   * This makes the quasicrystal structure a moving target that adapts
   * to the current threat landscape.
   */
  createThreatPhason(
    threatLevel: number,
    anomalyDimensions: number[] = []
  ): PhasonShift {
    const clampedThreat = Math.max(0, Math.min(1, threatLevel));
    const magnitude =
      clampedThreat * this.config.maxPhasonAmplitude * this.config.phasonCoupling;

    // Derive shift direction from anomaly dimensions
    let px = 0,
      py = 0,
      pz = 0;
    if (anomalyDimensions.length > 0) {
      for (const dim of anomalyDimensions) {
        const angle = (2 * Math.PI * dim) / 21; // Map dim index to angle
        px += Math.cos(angle);
        py += Math.sin(angle);
        pz += Math.cos(angle * PHI);
      }
      const norm = Math.sqrt(px * px + py * py + pz * pz);
      if (norm > BRAIN_EPSILON) {
        px /= norm;
        py /= norm;
        pz /= norm;
      }
    } else {
      // Default shift direction based on golden angle
      const angle = this.stepCounter * 2 * Math.PI / PHI;
      px = Math.cos(angle);
      py = Math.sin(angle);
      pz = Math.cos(angle / PHI);
    }

    return {
      perpShift: [px, py, pz],
      magnitude,
      phase: Math.atan2(py, px),
    };
  }

  /**
   * Compute cross-verification coherence between static and dynamic results.
   *
   * Checks that the dynamic transform preserves the static topology's
   * essential properties (acceptance, tiling, boundary relationships).
   */
  private computeCoherence(
    staticResult: StaticProjectionResult,
    dynamicResult: DynamicTransformResult
  ): number {
    // Factor 1: Displacement should be small for safe operations
    // Small displacement → high coherence
    const displacementScore = 1 / (1 + dynamicResult.displacement * 5);

    // Factor 2: Structure preservation
    const structureScore = dynamicResult.structurePreserved ? 1.0 : 0.0;

    // Factor 3: Static acceptance (accepted = topology valid)
    const acceptanceScore = staticResult.accepted ? 1.0 : 0.3;

    // Factor 4: Interference pattern should be moderate (not saturated)
    const interferenceScore =
      1 - Math.abs(dynamicResult.interferenceValue) * 0.5;

    // Weighted combination
    return (
      displacementScore * 0.35 +
      structureScore * 0.25 +
      acceptanceScore * 0.25 +
      interferenceScore * 0.15
    );
  }

  /** Get the current step counter */
  getStep(): number {
    return this.stepCounter;
  }

  /** Reset the system state (keeps mesh) */
  reset(): void {
    this.stepCounter = 0;
  }

  /** Full reset including mesh */
  fullReset(): void {
    this.stepCounter = 0;
    this.staticMesh = null;
  }
}

// ═══════════════════════════════════════════════════════════════
// Utility Functions
// ═══════════════════════════════════════════════════════════════

/**
 * Compute the Hausdorff (fractal) dimension estimate for a set of
 * projected lattice points using box-counting.
 *
 * For a perfect quasicrystal, D ≈ 2 (fills 2D plane).
 * Phason disorder can push D to non-integer values.
 */
export function estimateFractalDimension(
  points: Lattice3D[],
  scales: number[] = [1.0, 0.5, 0.25, 0.125]
): number {
  if (points.length < 2) return 0;

  const logN: number[] = [];
  const logInvEps: number[] = [];

  for (const eps of scales) {
    // Count boxes of size eps that contain at least one point
    const boxes = new Set<string>();
    for (const p of points) {
      const bx = Math.floor(p.x / eps);
      const by = Math.floor(p.y / eps);
      const bz = Math.floor(p.z / eps);
      boxes.add(`${bx},${by},${bz}`);
    }
    if (boxes.size > 0) {
      logN.push(Math.log(boxes.size));
      logInvEps.push(Math.log(1 / eps));
    }
  }

  if (logN.length < 2) return 0;

  // Linear regression: D = slope of log(N) vs log(1/eps)
  let sumX = 0,
    sumY = 0,
    sumXY = 0,
    sumX2 = 0;
  const n = logN.length;
  for (let i = 0; i < n; i++) {
    sumX += logInvEps[i];
    sumY += logN[i];
    sumXY += logInvEps[i] * logN[i];
    sumX2 += logInvEps[i] * logInvEps[i];
  }

  const denom = n * sumX2 - sumX * sumX;
  if (Math.abs(denom) < BRAIN_EPSILON) return 0;

  return (n * sumXY - sumX * sumY) / denom;
}

/**
 * Compute the lattice norm (L2) of a 6D vector.
 */
export function latticeNorm6D(point: Lattice6D): number {
  let sum = 0;
  for (const c of point.components) {
    sum += c * c;
  }
  return Math.sqrt(sum);
}

/**
 * Compute the lattice distance between two 3D points.
 */
export function latticeDistance3D(a: Lattice3D, b: Lattice3D): number {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  const dz = a.z - b.z;
  return Math.sqrt(dx * dx + dy * dy + dz * dz);
}
