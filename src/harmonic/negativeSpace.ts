/**
 * @file negativeSpace.ts
 * @module harmonic/negativeSpace
 * @layer Layer 5, Layer 4
 * @component Negative Space Context Embeddings
 * @version 1.0.0
 *
 * Extends the Poincaré ball model with negative-space embeddings.
 * Negative dimensions encode "absence" or "opposition" (e.g., anti-intent,
 * excluded contexts), creating richer, more discriminative representations.
 *
 * In hyperbolic space, negative-intent vectors are pushed toward the boundary
 * (‖u‖ → 1), where distances explode exponentially — creating natural "shadow
 * realms" that separate adversarial states from trusted ones.
 *
 * Key concepts:
 * - Signed embeddings: Components can be negative (opposition encoding)
 * - Pseudo-metric: Mixed positive/negative inner products
 * - Realm classification: Light (positive intent, near origin) vs Shadow (negative, boundary)
 * - Contrastive distance: Amplifies separation between opposing contexts
 */

const EPSILON = 1e-10;

/**
 * Realm classification for signed embeddings
 */
export type Realm = 'light' | 'shadow' | 'twilight';

/**
 * A signed context embedding with realm classification
 */
export interface SignedEmbedding {
  /** The embedding vector (may contain negative components) */
  vector: number[];
  /** Intent strength: -1.0 (opposing) to +1.0 (aligned) */
  intentStrength: number;
  /** Realm classification based on intent and position */
  realm: Realm;
  /** Euclidean norm of the vector */
  norm: number;
}

/**
 * Compute Euclidean norm
 */
function vecNorm(v: number[]): number {
  let sum = 0;
  for (const x of v) sum += x * x;
  return Math.sqrt(sum);
}

/**
 * Compute dot product
 */
function vecDot(u: number[], v: number[]): number {
  let sum = 0;
  for (let i = 0; i < u.length; i++) sum += u[i] * v[i];
  return sum;
}

/**
 * Classify a context into light/shadow/twilight realm based on
 * intent strength and position in the Poincaré ball.
 *
 * @param intentStrength - Signed intent (-1 to +1)
 * @param ballNorm - Norm of projected point (0 to <1)
 * @returns Realm classification
 */
export function classifyRealm(intentStrength: number, ballNorm: number): Realm {
  if (intentStrength > 0.3 && ballNorm < 0.7) return 'light';
  if (intentStrength < -0.3 || ballNorm > 0.9) return 'shadow';
  return 'twilight';
}

/**
 * Create a signed context embedding from raw features and intent.
 *
 * Features with negative intent are scaled toward the Poincaré boundary,
 * exploiting hyperbolic distance explosion for natural isolation.
 *
 * @param features - Raw feature vector (any dimensionality)
 * @param intentStrength - Signed intent: -1.0 (opposing) to +1.0 (aligned)
 * @returns Signed embedding with realm classification
 */
export function createSignedEmbedding(
  features: number[],
  intentStrength: number
): SignedEmbedding {
  const clampedIntent = Math.max(-1, Math.min(1, intentStrength));

  // Scale features by intent: negative intent inverts and pushes to boundary
  const scaled = features.map((f) => f * clampedIntent);

  // Project into Poincaré ball with boundary pressure for negatives
  const n = vecNorm(scaled);
  let projected: number[];
  if (n < EPSILON) {
    projected = scaled.map(() => 0);
  } else {
    // Push negative-intent vectors closer to boundary
    const boundaryPressure = clampedIntent < 0
      ? 0.85 + 0.14 * Math.abs(clampedIntent) // Shadow: 0.85-0.99
      : Math.tanh(n);                          // Light: normal tanh projection
    projected = scaled.map((x) => (x / n) * Math.min(boundaryPressure, 1 - EPSILON));
  }

  const projNorm = vecNorm(projected);
  const realm = classifyRealm(clampedIntent, projNorm);

  return {
    vector: projected,
    intentStrength: clampedIntent,
    realm,
    norm: projNorm,
  };
}

/**
 * Signed contrastive distance between two embeddings.
 *
 * For same-realm pairs, returns standard hyperbolic distance.
 * For cross-realm pairs (light ↔ shadow), applies amplification
 * to enforce exponential separation.
 *
 * @param a - First signed embedding
 * @param b - Second signed embedding
 * @returns Contrastive distance (always >= 0)
 */
export function contrastiveDistance(a: SignedEmbedding, b: SignedEmbedding): number {
  // Standard hyperbolic distance in Poincaré ball
  const diff: number[] = a.vector.map((x, i) => x - b.vector[i]);
  let diffNormSq = 0;
  for (const d of diff) diffNormSq += d * d;

  const aFactor = Math.max(EPSILON, 1 - a.norm * a.norm);
  const bFactor = Math.max(EPSILON, 1 - b.norm * b.norm);

  const arg = 1 + (2 * diffNormSq) / (aFactor * bFactor);
  const dH = Math.acosh(Math.max(1, arg));

  // Cross-realm amplification
  if (a.realm !== b.realm && a.realm !== 'twilight' && b.realm !== 'twilight') {
    // Light-shadow crossing: amplify by intent opposition
    const intentOpposition = Math.abs(a.intentStrength - b.intentStrength);
    return dH * (1 + intentOpposition);
  }

  return dH;
}

/**
 * Compute the pseudo-metric inner product with mixed signature.
 *
 * Positive dimensions contribute positively, negative dimensions contribute
 * negatively. This creates a Lorentzian-like metric for richer geometry.
 *
 * ⟨u,v⟩_signed = Σ_pos u_i·v_i - Σ_neg u_j·v_j
 *
 * @param u - First vector
 * @param v - Second vector
 * @param negDimStart - Index where negative dimensions begin (default: half)
 * @returns Pseudo-metric inner product
 */
export function pseudoMetricInnerProduct(
  u: number[],
  v: number[],
  negDimStart?: number
): number {
  const boundary = negDimStart ?? Math.floor(u.length / 2);
  let result = 0;

  for (let i = 0; i < u.length; i++) {
    if (i < boundary) {
      result += u[i] * v[i]; // Positive dimensions
    } else {
      result -= u[i] * v[i]; // Negative dimensions
    }
  }

  return result;
}

/**
 * Compute signed cosine similarity.
 *
 * Uses the pseudo-metric inner product, returning values in [-1, 1]
 * where negative values indicate cross-realm opposition.
 *
 * @param u - First vector
 * @param v - Second vector
 * @param negDimStart - Index where negative dimensions begin
 * @returns Signed similarity in [-1, 1]
 */
export function signedCosineSimilarity(
  u: number[],
  v: number[],
  negDimStart?: number
): number {
  const innerProduct = pseudoMetricInnerProduct(u, v, negDimStart);
  const uNorm = vecNorm(u);
  const vNorm = vecNorm(v);
  const denominator = uNorm * vNorm;

  if (denominator < EPSILON) return 0;
  return Math.max(-1, Math.min(1, innerProduct / denominator));
}
