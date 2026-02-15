/**
 * @file mmx.ts
 * @module harmonic/mmx
 * @layer Layer 9.5 — Cross-Modal Coherence Tensor
 * @component Multimodality Matrix (MMX)
 * @version 1.0.0
 *
 * TypeScript port of the Multimodality Matrix (MMX).
 *
 * Computes a cross-modal alignment tensor from K modality feature vectors,
 * then derives three governance-facing scalars:
 *
 *   coherence  — mean pairwise cosine similarity         ∈ [0, 1]
 *   conflict   — fraction of pairs below agreement floor  ∈ [0, 1]
 *   drift      — max absolute delta vs previous snapshot  ∈ [0, ∞)
 *
 * Integration:
 *   • Pipeline inserts MMX between L10 (spin coherence) and L12 (harmonic scaling).
 *   • Governance rules at L13:
 *       conflict > 0.35                   → override to QUARANTINE
 *       conflict > 0.60 or min(w) < 0.10  → override to DENY
 *
 * Zero npm dependencies — pure math only.
 */

// =============================================================================
// TYPES
// =============================================================================

/** Result of computeMMX(). */
export interface MMXResult {
  /** K×K cosine-similarity matrix */
  alignment: number[][];
  /** Per-modality reliability weights */
  weights: number[];
  /** Mean pairwise cosine similarity ∈ [0,1] */
  coherence: number;
  /** Fraction of pairs below agreement floor ∈ [0,1] */
  conflict: number;
  /** Max |delta| vs previous alignment ∈ [0,∞) */
  drift: number;
  /** Ordered modality labels */
  modalityLabels: string[];
}

export interface ComputeMMXOptions {
  /** Cosine similarity threshold below which a pair is in "conflict" (default 0.5) */
  agreementFloor?: number;
  /** Previous alignment matrix for drift computation */
  prevAlignment?: number[][];
}

// =============================================================================
// HELPERS
// =============================================================================

/**
 * Cosine similarity between two vectors. Returns 0.0 on degenerate input.
 */
function cosineSimilarity(a: readonly number[], b: readonly number[]): number {
  if (a.length !== b.length || a.length === 0) return 0.0;
  let dot = 0;
  let normA = 0;
  let normB = 0;
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }
  normA = Math.sqrt(normA);
  normB = Math.sqrt(normB);
  if (normA < 1e-12 || normB < 1e-12) return 0.0;
  return dot / (normA * normB);
}

/**
 * Reliability weight for a single modality feature vector.
 *
 * w = 1 - 1/(1 + ||v||)
 *
 * Maps: zero-vector → 0, large-norm → ~1.
 */
function reliabilityWeight(vec: readonly number[], eps: number = 1e-8): number {
  let norm = 0;
  for (let i = 0; i < vec.length; i++) {
    norm += vec[i] * vec[i];
  }
  norm = Math.sqrt(norm);
  return 1.0 - 1.0 / (1.0 + norm + eps);
}

// =============================================================================
// CORE
// =============================================================================

/**
 * Compute the Multimodality Matrix for a set of modality feature vectors.
 *
 * @param features - Map from modality label to its feature vector.
 *                   All vectors must have the same dimensionality. At least 2 required.
 * @param options - Optional agreement floor and previous alignment for drift.
 * @returns MMXResult with alignment matrix, weights, coherence, conflict, drift.
 * @throws Error if fewer than 2 modalities or vectors have mismatched lengths.
 */
export function computeMMX(
  features: Record<string, readonly number[]>,
  options?: ComputeMMXOptions,
): MMXResult {
  const agreementFloor = options?.agreementFloor ?? 0.5;
  const prevAlignment = options?.prevAlignment ?? null;

  const labels = Object.keys(features).sort();
  const K = labels.length;

  if (K < 2) {
    throw new Error(`MMX requires ≥2 modalities, got ${K}`);
  }

  const vecs: number[][] = labels.map((lbl) => [...features[lbl]]);

  // Validate dimension parity
  const dim = vecs[0].length;
  for (let i = 1; i < K; i++) {
    if (vecs[i].length !== dim) {
      throw new Error(
        `Dimension mismatch: modality '${labels[0]}' has dim=${dim}, ` +
          `but '${labels[i]}' has dim=${vecs[i].length}`,
      );
    }
  }

  // ---- Alignment matrix (K×K) ----
  const alignment: number[][] = Array.from({ length: K }, () => new Array(K).fill(0));
  for (let i = 0; i < K; i++) {
    alignment[i][i] = 1.0;
    for (let j = i + 1; j < K; j++) {
      const sim = cosineSimilarity(vecs[i], vecs[j]);
      alignment[i][j] = sim;
      alignment[j][i] = sim;
    }
  }

  // ---- Reliability weights ----
  const weights = vecs.map((v) => reliabilityWeight(v));

  // ---- Governance scalars ----
  const pairSims: number[] = [];
  let conflictCount = 0;
  for (let i = 0; i < K; i++) {
    for (let j = i + 1; j < K; j++) {
      const sim = alignment[i][j];
      pairSims.push(sim);
      if (sim < agreementFloor) {
        conflictCount++;
      }
    }
  }

  const nPairs = pairSims.length;
  let coherence = nPairs > 0 ? pairSims.reduce((s, v) => s + v, 0) / nPairs : 1.0;
  coherence = Math.max(0.0, Math.min(1.0, coherence));

  const conflict = nPairs > 0 ? conflictCount / nPairs : 0.0;

  // ---- Drift ----
  let drift = 0.0;
  if (prevAlignment !== null && prevAlignment.length === K) {
    for (let i = 0; i < K; i++) {
      for (let j = 0; j < K; j++) {
        if (prevAlignment[i] && j < prevAlignment[i].length) {
          const delta = Math.abs(alignment[i][j] - prevAlignment[i][j]);
          drift = Math.max(drift, delta);
        }
      }
    }
  }

  return {
    alignment,
    weights,
    coherence,
    conflict,
    drift,
    modalityLabels: labels,
  };
}
