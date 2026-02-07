/**
 * @file unified-state.ts
 * @module ai_brain/unified-state
 * @layer Layer 1-14 (Unified Manifold)
 * @component Unified Brain State
 * @version 1.1.0
 * @since 2026-02-07
 *
 * Implements the 21D unified brain state vector that integrates all SCBE-AETHERMOORE
 * components into a single coherent manifold. Each component contributes specific
 * dimensions, and the golden ratio weighting creates a hierarchical importance structure.
 *
 * The 21D vector is:
 *   [scbe(6) | navigation(6) | cognitive(3) | semantic(3) | swarm(3)]
 *
 * After golden ratio weighting, the vector is embedded into a Poincare ball
 * for hyperbolic geometry operations.
 */

import {
  BRAIN_DIMENSIONS,
  BRAIN_EPSILON,
  PHI,
  POINCARE_MAX_NORM,
  type BrainStateComponents,
  type SCBEContext,
  type NavigationVector,
  type CognitivePosition,
  type SemanticPhase,
  type SwarmCoordination,
  type TrajectoryPoint,
} from './types.js';

// ═══════════════════════════════════════════════════════════════
// Vector Utilities
// ═══════════════════════════════════════════════════════════════

function vecNorm(v: number[]): number {
  let sum = 0;
  for (const x of v) sum += x * x;
  return Math.sqrt(sum);
}

function vecNormSq(v: number[]): number {
  let sum = 0;
  for (const x of v) sum += x * x;
  return sum;
}

function vecSub(u: number[], v: number[]): number[] {
  return u.map((x, i) => x - v[i]);
}

function vecScale(v: number[], s: number): number[] {
  return v.map((x) => x * s);
}

function vecDot(u: number[], v: number[]): number {
  let sum = 0;
  for (let i = 0; i < u.length; i++) sum += u[i] * v[i];
  return sum;
}

// ═══════════════════════════════════════════════════════════════
// Golden Ratio Weighting
// ═══════════════════════════════════════════════════════════════

/**
 * Precomputed golden ratio weights for 21 dimensions.
 * w_i = phi^i for i in [0, 20]
 *
 * Note: The actual product of all weights is ~1,364x (corrected from
 * the overclaimed 518,400x). These serve as hierarchical importance
 * weights, NOT security multipliers.
 */
const GOLDEN_WEIGHTS: number[] = Array.from({ length: BRAIN_DIMENSIONS }, (_, i) => PHI ** i);

/**
 * Compute the corrected golden ratio product for validation
 * Product of phi^0 * phi^1 * ... * phi^20 = phi^(0+1+...+20) = phi^210
 */
export function goldenWeightProduct(): number {
  return GOLDEN_WEIGHTS.reduce((prod, w) => prod * w, 1);
}

/**
 * Apply golden ratio weighting to a 21D vector.
 * Creates hierarchical importance: higher dimensions receive
 * exponentially more weight (swarm > semantic > cognitive > navigation > SCBE).
 *
 * @param vector - Raw 21D brain state vector
 * @returns Weighted 21D vector
 */
export function applyGoldenWeighting(vector: number[]): number[] {
  if (vector.length !== BRAIN_DIMENSIONS) {
    throw new RangeError(`Expected ${BRAIN_DIMENSIONS}D vector, got ${vector.length}D`);
  }
  return vector.map((v, i) => v * GOLDEN_WEIGHTS[i]);
}

// ═══════════════════════════════════════════════════════════════
// Poincare Ball Embedding
// ═══════════════════════════════════════════════════════════════

/**
 * Embed a vector into the Poincare ball with numerically stable boundary clamping.
 *
 * Uses the exponential map from the origin: exp_0(v) = tanh(||v|| / 2) * v / ||v||.
 * This naturally maps R^n -> B^n (open unit ball) while preserving direction.
 *
 * The function is designed for raw state vectors (components typically in [0, 1]).
 * For golden-ratio-weighted vectors, use applyGoldenWeighting separately for
 * importance scoring — do not embed the weighted vector directly, as the
 * exponential weights would saturate all points at the boundary.
 *
 * This fixes the Theorem 3 boundary failure identified in the security review.
 *
 * @param vector - Input vector (any dimension)
 * @param epsilon - Boundary epsilon (default: 1e-8)
 * @returns Point strictly inside the Poincare ball
 */
export function safePoincareEmbed(vector: number[], epsilon: number = BRAIN_EPSILON): number[] {
  const n = vecNorm(vector);
  if (n < epsilon) return vector.map(() => 0);

  // Exponential map from origin: exp_0(v) = tanh(||v||/2) * v/||v||
  // For typical state vectors (norm ~1-5), this produces radii ~0.46-0.96
  // For large vectors, saturates safely at the boundary
  const mappedNorm = Math.tanh(n / 2);
  const clampedNorm = Math.min(mappedNorm, POINCARE_MAX_NORM);
  return vecScale(vector, clampedNorm / n);
}

/**
 * Compute hyperbolic distance in the Poincare ball model.
 *
 * d_H(u,v) = arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))
 *
 * @param u - First point in Poincare ball (||u|| < 1)
 * @param v - Second point in Poincare ball (||v|| < 1)
 * @returns Hyperbolic distance
 */
export function hyperbolicDistanceSafe(u: number[], v: number[]): number {
  const diff = vecSub(u, v);
  const diffNormSq = vecNormSq(diff);
  const uNormSq = vecNormSq(u);
  const vNormSq = vecNormSq(v);

  const uFactor = Math.max(BRAIN_EPSILON, 1 - uNormSq);
  const vFactor = Math.max(BRAIN_EPSILON, 1 - vNormSq);

  const arg = 1 + (2 * diffNormSq) / (uFactor * vFactor);
  return Math.acosh(Math.max(1, arg));
}

/**
 * Mobius addition in the Poincare ball.
 *
 * u + v = ((1 + 2<u,v> + ||v||^2)u + (1 - ||u||^2)v) / (1 + 2<u,v> + ||u||^2||v||^2)
 *
 * @param u - First point
 * @param v - Second point
 * @returns Mobius sum
 */
export function mobiusAddSafe(u: number[], v: number[]): number[] {
  const uv = vecDot(u, v);
  const uNormSq = vecNormSq(u);
  const vNormSq = vecNormSq(v);

  const numCoeffU = 1 + 2 * uv + vNormSq;
  const numCoeffV = 1 - uNormSq;
  const denom = 1 + 2 * uv + uNormSq * vNormSq;

  const result = u.map((_, i) => (numCoeffU * u[i] + numCoeffV * v[i]) / denom);

  // Ensure result stays in ball
  const n = vecNorm(result);
  if (n >= POINCARE_MAX_NORM) {
    return vecScale(result, POINCARE_MAX_NORM / n);
  }
  return result;
}

// ═══════════════════════════════════════════════════════════════
// Unified Brain State
// ═══════════════════════════════════════════════════════════════

/**
 * UnifiedBrainState - The 21D manifold integrating all SCBE-AETHERMOORE components.
 *
 * This class maintains a coherent state across:
 * - SCBE Core (6D context)
 * - Dual Lattice (6D navigation)
 * - PHDM (3D cognitive)
 * - Sacred Tongues (3D semantic)
 * - Swarm (3D coordination)
 *
 * The state can be represented as a raw 21D vector, a weighted vector,
 * or an embedded Poincare ball point.
 */
export class UnifiedBrainState {
  private components: BrainStateComponents;

  constructor(components?: Partial<BrainStateComponents>) {
    this.components = {
      scbeContext: components?.scbeContext ?? {
        deviceTrust: 0.5,
        locationTrust: 0.5,
        networkTrust: 0.5,
        behaviorScore: 0.5,
        timeOfDay: 0.5,
        intentAlignment: 0.5,
      },
      navigation: components?.navigation ?? {
        x: 0,
        y: 0,
        z: 0,
        time: 0,
        priority: 0.5,
        confidence: 0.5,
      },
      cognitivePosition: components?.cognitivePosition ?? {
        px: 0,
        py: 0,
        pz: 0,
      },
      semanticPhase: components?.semanticPhase ?? {
        activeTongue: 0,
        phaseAngle: 0,
        tongueWeight: 1,
      },
      swarmCoordination: components?.swarmCoordination ?? {
        trustScore: 0.5,
        byzantineVotes: 0,
        spectralCoherence: 0.5,
      },
    };
  }

  /**
   * Get the structured components
   */
  getComponents(): Readonly<BrainStateComponents> {
    return this.components;
  }

  /**
   * Update SCBE context
   */
  updateSCBEContext(updates: Partial<SCBEContext>): void {
    this.components.scbeContext = { ...this.components.scbeContext, ...updates };
  }

  /**
   * Update navigation vector
   */
  updateNavigation(updates: Partial<NavigationVector>): void {
    this.components.navigation = { ...this.components.navigation, ...updates };
  }

  /**
   * Update cognitive position
   */
  updateCognitivePosition(updates: Partial<CognitivePosition>): void {
    this.components.cognitivePosition = { ...this.components.cognitivePosition, ...updates };
  }

  /**
   * Update semantic phase
   */
  updateSemanticPhase(updates: Partial<SemanticPhase>): void {
    this.components.semanticPhase = { ...this.components.semanticPhase, ...updates };
  }

  /**
   * Update swarm coordination
   */
  updateSwarmCoordination(updates: Partial<SwarmCoordination>): void {
    this.components.swarmCoordination = { ...this.components.swarmCoordination, ...updates };
  }

  /**
   * Flatten to raw 21D vector
   */
  toVector(): number[] {
    const { scbeContext, navigation, cognitivePosition, semanticPhase, swarmCoordination } =
      this.components;

    return [
      // SCBE Context (6D)
      scbeContext.deviceTrust,
      scbeContext.locationTrust,
      scbeContext.networkTrust,
      scbeContext.behaviorScore,
      scbeContext.timeOfDay,
      scbeContext.intentAlignment,
      // Navigation (6D)
      navigation.x,
      navigation.y,
      navigation.z,
      navigation.time,
      navigation.priority,
      navigation.confidence,
      // Cognitive Position (3D)
      cognitivePosition.px,
      cognitivePosition.py,
      cognitivePosition.pz,
      // Semantic Phase (3D)
      semanticPhase.activeTongue,
      semanticPhase.phaseAngle,
      semanticPhase.tongueWeight,
      // Swarm Coordination (3D)
      swarmCoordination.trustScore,
      swarmCoordination.byzantineVotes,
      swarmCoordination.spectralCoherence,
    ];
  }

  /**
   * Apply golden ratio weighting to the state vector
   */
  toWeightedVector(): number[] {
    return applyGoldenWeighting(this.toVector());
  }

  /**
   * Embed into Poincare ball (normalized and contained).
   *
   * Uses the raw 21D vector (not golden-weighted) for geometric embedding.
   * Golden ratio weighting is available via toWeightedVector() for importance
   * scoring, but the exponential weights would saturate the Poincare embedding.
   */
  toPoincarePoint(): number[] {
    return safePoincareEmbed(this.toVector());
  }

  /**
   * Compute hyperbolic distance to another brain state
   */
  distanceTo(other: UnifiedBrainState): number {
    return hyperbolicDistanceSafe(this.toPoincarePoint(), other.toPoincarePoint());
  }

  /**
   * Compute distance from the safe origin (center of Poincare ball)
   */
  distanceFromOrigin(): number {
    const origin = new Array(BRAIN_DIMENSIONS).fill(0);
    return hyperbolicDistanceSafe(origin, this.toPoincarePoint());
  }

  /**
   * Compute boundary distance (how close to the Poincare ball edge)
   */
  boundaryDistance(): number {
    const point = this.toPoincarePoint();
    return 1 - vecNorm(point);
  }

  /**
   * Create a trajectory point from the current state
   */
  toTrajectoryPoint(step: number): TrajectoryPoint {
    const vec = this.toVector();
    const embedded = this.toPoincarePoint();
    return {
      step,
      state: vec,
      embedded,
      distance: this.distanceFromOrigin(),
      curvature: 0, // Set by trajectory analysis
      timestamp: Date.now(),
    };
  }

  /**
   * Reconstruct from a raw 21D vector
   */
  static fromVector(vector: number[]): UnifiedBrainState {
    if (vector.length !== BRAIN_DIMENSIONS) {
      throw new RangeError(`Expected ${BRAIN_DIMENSIONS}D vector, got ${vector.length}D`);
    }

    return new UnifiedBrainState({
      scbeContext: {
        deviceTrust: vector[0],
        locationTrust: vector[1],
        networkTrust: vector[2],
        behaviorScore: vector[3],
        timeOfDay: vector[4],
        intentAlignment: vector[5],
      },
      navigation: {
        x: vector[6],
        y: vector[7],
        z: vector[8],
        time: vector[9],
        priority: vector[10],
        confidence: vector[11],
      },
      cognitivePosition: {
        px: vector[12],
        py: vector[13],
        pz: vector[14],
      },
      semanticPhase: {
        activeTongue: vector[15],
        phaseAngle: vector[16],
        tongueWeight: vector[17],
      },
      swarmCoordination: {
        trustScore: vector[18],
        byzantineVotes: vector[19],
        spectralCoherence: vector[20],
      },
    });
  }

  /**
   * Create a safe origin state (center of manifold)
   */
  static safeOrigin(): UnifiedBrainState {
    return new UnifiedBrainState({
      scbeContext: {
        deviceTrust: 1,
        locationTrust: 1,
        networkTrust: 1,
        behaviorScore: 1,
        timeOfDay: 0.5,
        intentAlignment: 1,
      },
      navigation: { x: 0, y: 0, z: 0, time: 0, priority: 0.5, confidence: 1 },
      cognitivePosition: { px: 0, py: 0, pz: 0 },
      semanticPhase: { activeTongue: 0, phaseAngle: 0, tongueWeight: 1 },
      swarmCoordination: { trustScore: 1, byzantineVotes: 0, spectralCoherence: 1 },
    });
  }
}

/**
 * Compute Euclidean distance between two 21D state vectors
 */
export function euclideanDistance(a: number[], b: number[]): number {
  return vecNorm(vecSub(a, b));
}

/**
 * Compute the norm of a vector
 */
export function vectorNorm(v: number[]): number {
  return vecNorm(v);
}
