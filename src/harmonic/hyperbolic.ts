/**
 * @file hyperbolic.ts
 * @module harmonic/hyperbolic
 * @layer Layer 5, Layer 6, Layer 7
 * @component Poincaré Ball Operations
 * @version 3.0.0
 * @since 2026-01-20
 *
 * SCBE Hyperbolic Geometry - Core mathematical operations for the 14-layer pipeline.
 * The invariant hyperbolic metric NEVER changes - all dynamics come from
 * transforming points within the Poincaré ball.
 *
 * Layer 5: Invariant Metric d_ℍ(u,v) = arcosh(1 + 2‖u-v‖²/((1-‖u‖²)(1-‖v‖²)))
 * Layer 6: Breathing Transform B(p,t) = tanh(‖p‖ + A·sin(ωt))·p/‖p‖
 * Layer 7: Phase Modulation Φ(p,θ) = Möbius rotation in tangent space
 */

/** Small epsilon for numerical stability */
const EPSILON = 1e-10;

/**
 * Compute Euclidean norm of a vector
 */
function norm(v: number[]): number {
  let sum = 0;
  for (const x of v) sum += x * x;
  return Math.sqrt(sum);
}

/**
 * Compute squared Euclidean norm
 */
function normSq(v: number[]): number {
  let sum = 0;
  for (const x of v) sum += x * x;
  return sum;
}

/**
 * Dot product of two vectors
 */
function dot(u: number[], v: number[]): number {
  let sum = 0;
  for (let i = 0; i < u.length; i++) sum += u[i] * v[i];
  return sum;
}

/**
 * Scale a vector by a scalar
 */
function scale(v: number[], s: number): number[] {
  return v.map((x) => x * s);
}

/**
 * Add two vectors
 */
function add(u: number[], v: number[]): number[] {
  return u.map((x, i) => x + v[i]);
}

/**
 * Subtract two vectors
 */
function sub(u: number[], v: number[]): number[] {
  return u.map((x, i) => x - v[i]);
}

// ═══════════════════════════════════════════════════════════════
// Layer 5: Invariant Hyperbolic Metric
// ═══════════════════════════════════════════════════════════════

/**
 * Hyperbolic distance in the Poincaré ball model (Layer 5)
 *
 * dℍ(u,v) = arcosh(1 + 2‖u-v‖² / ((1-‖u‖²)(1-‖v‖²)))
 *
 * This metric is INVARIANT - it never changes. Points move; the metric does not.
 *
 * @param u - First point in Poincaré ball (‖u‖ < 1)
 * @param v - Second point in Poincaré ball (‖v‖ < 1)
 * @returns Hyperbolic distance
 */
export function hyperbolicDistance(u: number[], v: number[]): number {
  const diff = sub(u, v);
  const diffNormSq = normSq(diff);
  const uNormSq = normSq(u);
  const vNormSq = normSq(v);

  // Clamp to ensure points are inside the ball
  const uFactor = Math.max(EPSILON, 1 - uNormSq);
  const vFactor = Math.max(EPSILON, 1 - vNormSq);

  const arg = 1 + (2 * diffNormSq) / (uFactor * vFactor);

  // arcosh(x) = ln(x + sqrt(x² - 1))
  return Math.acosh(Math.max(1, arg));
}

/**
 * Möbius addition in the Poincaré ball
 *
 * u ⊕ v = ((1 + 2⟨u,v⟩ + ‖v‖²)u + (1 - ‖u‖²)v) / (1 + 2⟨u,v⟩ + ‖u‖²‖v‖²)
 *
 * This is the gyrovector addition for hyperbolic geometry.
 *
 * @param u - First point
 * @param v - Second point
 * @returns Möbius sum u ⊕ v
 */
export function mobiusAdd(u: number[], v: number[]): number[] {
  const uv = dot(u, v);
  const uNormSq = normSq(u);
  const vNormSq = normSq(v);

  const numeratorCoeffU = 1 + 2 * uv + vNormSq;
  const numeratorCoeffV = 1 - uNormSq;
  const denominator = 1 + 2 * uv + uNormSq * vNormSq;

  const result: number[] = [];
  for (let i = 0; i < u.length; i++) {
    result.push((numeratorCoeffU * u[i] + numeratorCoeffV * v[i]) / denominator);
  }

  return result;
}

/**
 * Project a point onto the Poincaré ball (clamp to ‖p‖ < 1)
 *
 * @param p - Point to project
 * @param maxNorm - Maximum norm (default 1 - ε)
 * @returns Projected point inside ball
 */
export function projectToBall(p: number[], maxNorm: number = 1 - EPSILON): number[] {
  const n = norm(p);
  if (n < maxNorm) return [...p];
  return scale(p, maxNorm / n);
}

/**
 * Exponential map from tangent space to Poincaré ball at origin
 *
 * exp_0(v) = tanh(‖v‖/2) · v/‖v‖
 *
 * @param v - Tangent vector at origin
 * @returns Point in Poincaré ball
 */
export function expMap0(v: number[]): number[] {
  const n = norm(v);
  if (n < EPSILON) return v.map(() => 0);
  const factor = Math.tanh(n / 2) / n;
  return scale(v, factor);
}

/**
 * Logarithmic map from Poincaré ball to tangent space at origin
 *
 * log_0(p) = 2 · arctanh(‖p‖) · p/‖p‖
 *
 * @param p - Point in Poincaré ball
 * @returns Tangent vector at origin
 */
export function logMap0(p: number[]): number[] {
  const n = norm(p);
  if (n < EPSILON) return p.map(() => 0);
  // arctanh(x) = 0.5 * ln((1+x)/(1-x))
  const atanh = 0.5 * Math.log((1 + n) / (1 - n + EPSILON));
  const factor = (2 * atanh) / n;
  return scale(p, factor);
}

// ═══════════════════════════════════════════════════════════════
// Layer 6: Breath Transform
// ═══════════════════════════════════════════════════════════════

/**
 * Breath Transform configuration
 */
export interface BreathConfig {
  /** Amplitude bound A ∈ [0, 0.1] */
  amplitude: number;
  /** Breathing frequency ω */
  omega: number;
}

/**
 * Breath Transform (Layer 6)
 *
 * B(p, t) = tanh(‖p‖ + A·sin(ωt)) · p/‖p‖
 *
 * Preserves direction, modulates radius. Creates a "breathing" effect
 * where points rhythmically move toward/away from the boundary.
 *
 * @param p - Point in Poincaré ball
 * @param t - Time parameter
 * @param config - Breath configuration
 * @returns Transformed point
 */
export function breathTransform(
  p: number[],
  t: number,
  config: BreathConfig = { amplitude: 0.05, omega: 1.0 }
): number[] {
  const n = norm(p);
  if (n < EPSILON) return p.map(() => 0);

  // Clamp amplitude to [0, 0.1] as per spec
  const A = Math.max(0, Math.min(0.1, config.amplitude));

  // Modulated radius
  const newRadius = Math.tanh(n + A * Math.sin(config.omega * t));

  // Scale to new radius while preserving direction
  return scale(p, newRadius / n);
}

/**
 * Inverse breath transform (approximate recovery)
 *
 * @param bp - Breath-transformed point
 * @param t - Time parameter
 * @param config - Breath configuration
 * @returns Approximate original point
 */
export function inverseBreathTransform(
  bp: number[],
  t: number,
  config: BreathConfig = { amplitude: 0.05, omega: 1.0 }
): number[] {
  const n = norm(bp);
  if (n < EPSILON) return bp.map(() => 0);

  const A = Math.max(0, Math.min(0.1, config.amplitude));

  // atanh(n) - A·sin(ωt) gives approximate original radius
  const atanh = 0.5 * Math.log((1 + n) / (1 - n + EPSILON));
  const originalRadius = Math.max(0, atanh - A * Math.sin(config.omega * t));

  return scale(bp, originalRadius / n);
}

// ═══════════════════════════════════════════════════════════════
// Layer 7: Phase Modulation
// ═══════════════════════════════════════════════════════════════

/**
 * Phase Modulation / Rotation (Layer 7)
 *
 * Φ(p, θ) = R_θ · p - rotation in tangent space
 *
 * For 2D, this is standard rotation. For higher dimensions,
 * we rotate in a chosen plane.
 *
 * @param p - Point in Poincaré ball
 * @param theta - Rotation angle in radians
 * @param plane - Pair of dimension indices to rotate in (default [0,1])
 * @returns Rotated point
 */
export function phaseModulation(
  p: number[],
  theta: number,
  plane: [number, number] = [0, 1]
): number[] {
  const [i, j] = plane;
  if (i >= p.length || j >= p.length || i === j) {
    throw new RangeError('Invalid rotation plane');
  }

  const result = [...p];
  const cos = Math.cos(theta);
  const sin = Math.sin(theta);

  // Givens rotation in plane (i, j)
  result[i] = p[i] * cos - p[j] * sin;
  result[j] = p[i] * sin + p[j] * cos;

  return result;
}

/**
 * Multi-plane phase modulation
 *
 * Applies rotations in multiple planes sequentially.
 *
 * @param p - Point in Poincaré ball
 * @param rotations - Array of [theta, plane] pairs
 * @returns Transformed point
 */
export function multiPhaseModulation(
  p: number[],
  rotations: Array<{ theta: number; plane: [number, number] }>
): number[] {
  let result = [...p];
  for (const { theta, plane } of rotations) {
    result = phaseModulation(result, theta, plane);
  }
  return result;
}

// ═══════════════════════════════════════════════════════════════
// Layer 8: Multi-Well Potential
// ═══════════════════════════════════════════════════════════════

/**
 * Well configuration for multi-well potential
 */
export interface Well {
  /** Well center position */
  center: number[];
  /** Well weight */
  weight: number;
  /** Well width (σ) */
  sigma: number;
}

/**
 * Multi-Well Potential (Layer 8)
 *
 * V(p) = Σᵢ wᵢ · exp(-‖p - cᵢ‖² / 2σᵢ²)
 *
 * Creates an energy landscape with multiple attractors (wells).
 *
 * @param p - Point in space
 * @param wells - Array of well configurations
 * @returns Potential energy at point p
 */
export function multiWellPotential(p: number[], wells: Well[]): number {
  let V = 0;
  for (const well of wells) {
    const diff = sub(p, well.center);
    const distSq = normSq(diff);
    V += well.weight * Math.exp(-distSq / (2 * well.sigma * well.sigma));
  }
  return V;
}

/**
 * Gradient of multi-well potential
 *
 * ∇V(p) = Σᵢ wᵢ · exp(-‖p-cᵢ‖²/2σᵢ²) · (-(p-cᵢ)/σᵢ²)
 *
 * @param p - Point in space
 * @param wells - Array of well configurations
 * @returns Gradient vector
 */
export function multiWellGradient(p: number[], wells: Well[]): number[] {
  const grad = p.map(() => 0);

  for (const well of wells) {
    const diff = sub(p, well.center);
    const distSq = normSq(diff);
    const expTerm = Math.exp(-distSq / (2 * well.sigma * well.sigma));
    const factor = (-well.weight * expTerm) / (well.sigma * well.sigma);

    for (let i = 0; i < p.length; i++) {
      grad[i] += factor * diff[i];
    }
  }

  return grad;
}

// ═══════════════════════════════════════════════════════════════
// Utility: Combined Transform Pipeline
// ═══════════════════════════════════════════════════════════════

/**
 * Apply the L5-L8 transform pipeline
 *
 * @param p - Input point
 * @param t - Time parameter
 * @param theta - Phase rotation angle
 * @param breathConfig - Breath transform config
 * @param wells - Multi-well potential config (optional)
 * @returns Transformed point and potential value
 */
export function applyHyperbolicPipeline(
  p: number[],
  t: number,
  theta: number,
  breathConfig?: BreathConfig,
  wells?: Well[]
): { point: number[]; potential: number; distance: number } {
  // Ensure point is in ball
  let point = projectToBall(p);

  // L6: Breath transform
  if (breathConfig) {
    point = breathTransform(point, t, breathConfig);
  }

  // L7: Phase modulation
  if (theta !== 0) {
    point = phaseModulation(point, theta);
  }

  // Ensure still in ball after transforms
  point = projectToBall(point);

  // L8: Compute potential (doesn't modify point)
  const potential = wells ? multiWellPotential(point, wells) : 0;

  // L5: Compute distance from origin (for reference)
  const origin = point.map(() => 0);
  const distance = hyperbolicDistance(origin, point);

  return { point, potential, distance };
}
