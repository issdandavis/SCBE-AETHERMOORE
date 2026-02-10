/**
 * @file hyperbolicRAG.ts
 * @module harmonic/hyperbolicRAG
 * @layer Layer 5, Layer 12, Layer 13
 * @component Hyperbolic Retrieval-Augmented Generation — GeoSeal v2 Scorer
 * @version 3.2.4
 *
 * Retrieval scoring in the Poincaré ball where trust-distance gates what enters
 * context. Replaces hand-tuned "repulsion + suspicion counters" with a
 * geometry-aware three-signal fusion:
 *
 *   1. Hyperbolic proximity: d_H(query, chunk), d_H(anchor, chunk)
 *   2. Phase consistency:    phase deviation across 6 tongues
 *   3. Uncertainty:          variance proxy for retrieval confidence
 *
 * Output per chunk: { trustScore, anomalyProb, quarantineFlag, attentionWeight }
 *
 * Design: This is a *scoring engine*, not the whole security system.
 * Crypto gates (RWP), dialect grammar, and audio axis remain unchanged.
 */

import type { Vector6D } from './constants.js';
import {
  hyperbolicDistance6D,
  poincareNorm,
  projectIntoBall,
  accessCost,
  tongueImpedanceAt,
  type CHSFNState,
  type TongueImpedance,
  DEFAULT_IMPEDANCE,
} from './chsfn.js';

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════

const PHI = (1 + Math.sqrt(5)) / 2;
const EPSILON = 1e-10;

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

/**
 * A retrieval chunk projected into the Poincaré ball.
 *
 * Raw embeddings (e.g. 768-dim) are projected via tanh mapping
 * before entering this pipeline. The 6D projection aligns with
 * the Sacred Tongue basis.
 */
export interface HyperbolicChunk {
  /** Unique chunk identifier */
  chunkId: string;
  /** Position in 6D Poincaré ball (‖p‖ < 1) */
  position: Vector6D;
  /** Phase features per tongue [cos(θ), sin(θ)] flattened to 6 values */
  phase: Vector6D;
  /** Uncertainty estimate (higher = less confident). Variance proxy. */
  uncertainty: number;
  /** Optional: original embedding norm before projection (for calibration) */
  originalNorm?: number;
}

/**
 * Trust score output for a single retrieval chunk.
 */
export interface ChunkTrustScore {
  /** Chunk identifier */
  chunkId: string;
  /** Trust score in [0, 1]: 1 = fully trusted, 0 = adversarial */
  trustScore: number;
  /** Anomaly probability in [0, 1]: likelihood this is foreign/poisoned */
  anomalyProb: number;
  /** Whether this chunk should be quarantined (blocked from context) */
  quarantineFlag: boolean;
  /** Attention weight for context assembly (higher = more influence) */
  attentionWeight: number;
  /** Individual signal components for interpretability */
  signals: {
    /** Hyperbolic proximity score [0, 1] */
    proximityScore: number;
    /** Phase consistency score [0, 1] */
    phaseScore: number;
    /** Uncertainty penalty [0, 1] */
    uncertaintyPenalty: number;
    /** Hyperbolic distance to query */
    distanceToQuery: number;
    /** Hyperbolic distance to nearest tongue anchor */
    distanceToAnchor: number;
  };
}

/**
 * Configuration for the RAG scorer.
 */
export interface RAGScorerConfig {
  /** Hyperbolic distance above which trust drops to near-zero (default 3.0) */
  maxTrustDistance: number;
  /** Phase coherence threshold below which anomaly is flagged (default 0.4) */
  minPhaseCoherence: number;
  /** Uncertainty threshold above which quarantine is triggered (default 0.7) */
  maxUncertainty: number;
  /** Weight for proximity signal in fusion (default 0.5) */
  weightProximity: number;
  /** Weight for phase signal in fusion (default 0.3) */
  weightPhase: number;
  /** Weight for uncertainty signal in fusion (default 0.2) */
  weightUncertainty: number;
  /** Trust score below which quarantine is triggered (default 0.3) */
  quarantineThreshold: number;
  /** Tongue impedance weights for phase scoring */
  impedance: TongueImpedance;
}

export const DEFAULT_RAG_CONFIG: Readonly<RAGScorerConfig> = {
  maxTrustDistance: 3.0,
  minPhaseCoherence: 0.4,
  maxUncertainty: 0.7,
  weightProximity: 0.5,
  weightPhase: 0.3,
  weightUncertainty: 0.2,
  quarantineThreshold: 0.3,
  impedance: DEFAULT_IMPEDANCE,
};

// ═══════════════════════════════════════════════════════════════
// Projection: Arbitrary Embeddings → Poincaré Ball
// ═══════════════════════════════════════════════════════════════

/**
 * Project an arbitrary-dimensional embedding into the 6D Poincaré ball.
 *
 * Uses tanh mapping: u = tanh(α·‖x‖) · x / (‖x‖ + ε)
 *
 * For high-dim embeddings (768, 1536, etc.), we first reduce to 6D
 * by chunked averaging (each of the 6 dims gets avg of dim/6 components).
 *
 * @param embedding - Raw embedding vector of any dimension >= 6
 * @param scale - Contraction factor α (default 0.5) — controls how
 *                compressed the projection is. Lower = more centered.
 * @returns 6D position inside the Poincaré ball
 */
export function projectToBall(embedding: number[], scale: number = 0.5): Vector6D {
  // Reduce to 6D by chunked averaging
  const reduced: Vector6D = [0, 0, 0, 0, 0, 0];
  const chunkSize = Math.max(1, Math.floor(embedding.length / 6));

  for (let dim = 0; dim < 6; dim++) {
    const start = dim * chunkSize;
    const end = dim === 5 ? embedding.length : (dim + 1) * chunkSize;
    let sum = 0;
    let count = 0;
    for (let j = start; j < end; j++) {
      sum += embedding[j];
      count++;
    }
    reduced[dim] = count > 0 ? sum / count : 0;
  }

  // Compute norm of reduced vector
  let normSq = 0;
  for (let i = 0; i < 6; i++) normSq += reduced[i] * reduced[i];
  const norm = Math.sqrt(normSq);

  if (norm < EPSILON) return [0, 0, 0, 0, 0, 0];

  // tanh mapping: u = tanh(α·‖x‖) · x / ‖x‖
  const mappedNorm = Math.tanh(scale * norm);
  const result: Vector6D = [0, 0, 0, 0, 0, 0];
  for (let i = 0; i < 6; i++) {
    result[i] = mappedNorm * (reduced[i] / norm);
  }

  return result;
}

/**
 * Extract phase features from an embedding.
 *
 * Maps each tongue's chunk of the embedding to an angle via atan2
 * of even/odd component averages.
 *
 * @param embedding - Raw embedding vector
 * @returns Phase vector [θ_KO, θ_AV, θ_RU, θ_CA, θ_DR, θ_UM]
 */
export function extractPhase(embedding: number[]): Vector6D {
  const chunkSize = Math.max(2, Math.floor(embedding.length / 6));
  const phase: Vector6D = [0, 0, 0, 0, 0, 0];

  for (let dim = 0; dim < 6; dim++) {
    const start = dim * chunkSize;
    let evenSum = 0;
    let oddSum = 0;
    const end = Math.min(start + chunkSize, embedding.length);
    for (let j = start; j < end; j++) {
      if ((j - start) % 2 === 0) evenSum += embedding[j];
      else oddSum += embedding[j];
    }
    phase[dim] = Math.atan2(oddSum, evenSum + EPSILON);
  }

  return phase;
}

/**
 * Estimate uncertainty from an embedding using variance of components.
 *
 * Higher variance ≈ more spread-out representation ≈ less confident.
 * Normalized to [0, 1] via sigmoid.
 *
 * @param embedding - Raw embedding vector
 * @returns Uncertainty in [0, 1]
 */
export function estimateUncertainty(embedding: number[]): number {
  if (embedding.length === 0) return 1.0;

  let sum = 0;
  let sumSq = 0;
  for (const v of embedding) {
    sum += v;
    sumSq += v * v;
  }
  const mean = sum / embedding.length;
  const variance = sumSq / embedding.length - mean * mean;

  // Sigmoid normalization: maps variance to [0, 1]
  // Calibrated so variance ~0.1 → uncertainty ~0.5
  return 1 / (1 + Math.exp(-10 * (variance - 0.1)));
}

/**
 * Build a HyperbolicChunk from a raw embedding.
 *
 * Convenience function that runs projection + phase extraction + uncertainty.
 *
 * @param chunkId - Unique identifier
 * @param embedding - Raw embedding vector (any dimension >= 6)
 * @param scale - Poincaré ball projection scale
 * @returns HyperbolicChunk ready for scoring
 */
export function buildChunk(
  chunkId: string,
  embedding: number[],
  scale: number = 0.5
): HyperbolicChunk {
  const norm = Math.sqrt(embedding.reduce((s, v) => s + v * v, 0));
  return {
    chunkId,
    position: projectToBall(embedding, scale),
    phase: extractPhase(embedding),
    uncertainty: estimateUncertainty(embedding),
    originalNorm: norm,
  };
}

// ═══════════════════════════════════════════════════════════════
// Tongue Anchors
// ═══════════════════════════════════════════════════════════════

/**
 * The 6 tongue anchors in the Poincaré ball.
 *
 * Each tongue occupies a canonical position along its primary axis.
 * These are the "safe poles" — trusted retrieval should cluster near these.
 */
export const TONGUE_ANCHORS: Readonly<Record<string, Vector6D>> = {
  KO: [0.5, 0, 0, 0, 0, 0],
  AV: [0, 0.5, 0, 0, 0, 0],
  RU: [0, 0, 0.5, 0, 0, 0],
  CA: [0, 0, 0, 0.5, 0, 0],
  DR: [0, 0, 0, 0, 0.5, 0],
  UM: [0, 0, 0, 0, 0, 0.5],
};

/** Tongue names indexed */
const TONGUE_NAMES = ['KO', 'AV', 'RU', 'CA', 'DR', 'UM'] as const;

/**
 * Find the nearest tongue anchor to a position.
 *
 * @param position - 6D position in Poincaré ball
 * @returns { tongue, distance } of nearest anchor
 */
export function nearestTongueAnchor(
  position: Vector6D
): { tongue: string; distance: number } {
  let bestTongue = 'KO';
  let bestDist = Infinity;

  for (const tongue of TONGUE_NAMES) {
    const d = hyperbolicDistance6D(position, TONGUE_ANCHORS[tongue]);
    if (d < bestDist) {
      bestDist = d;
      bestTongue = tongue;
    }
  }

  return { tongue: bestTongue, distance: bestDist };
}

// ═══════════════════════════════════════════════════════════════
// Three-Signal Scoring
// ═══════════════════════════════════════════════════════════════

/**
 * Compute hyperbolic proximity score.
 *
 * Score = 1 / (1 + accessCost(d_H(query, chunk)))
 *
 * Near query → high score; far → near-zero (exponential decay).
 *
 * @param queryPos - Query position in ball
 * @param chunkPos - Chunk position in ball
 * @param maxDist - Distance at which score is effectively zero
 * @returns Proximity score in [0, 1]
 */
export function proximityScore(
  queryPos: Vector6D,
  chunkPos: Vector6D,
  maxDist: number = 3.0
): number {
  const dist = hyperbolicDistance6D(queryPos, chunkPos);
  if (dist > maxDist) return 0;
  // Use access cost for exponential decay, but normalize
  const cost = accessCost(dist);
  const baseCost = accessCost(0);
  return baseCost / cost; // Ratio: cost at origin / cost at d → decays exponentially
}

/**
 * Compute phase consistency score.
 *
 * Average cosine similarity between chunk phase and expected tongue phases.
 * Measures whether the chunk "speaks the right language."
 *
 * @param chunkPhase - Phase vector of the chunk
 * @param queryPhase - Phase vector of the query (or expected alignment)
 * @returns Phase score in [0, 1]
 */
export function phaseConsistencyScore(
  chunkPhase: Vector6D,
  queryPhase: Vector6D
): number {
  let sum = 0;
  for (let i = 0; i < 6; i++) {
    sum += Math.cos(chunkPhase[i] - queryPhase[i]);
  }
  // cos ranges [-1, 1]; normalize to [0, 1]
  return (sum / 6 + 1) / 2;
}

/**
 * Compute uncertainty penalty.
 *
 * Higher uncertainty → higher penalty → lower trust.
 *
 * @param uncertainty - Chunk uncertainty in [0, 1]
 * @returns Penalty in [0, 1] where 0 = no penalty, 1 = max penalty
 */
export function uncertaintyPenalty(uncertainty: number): number {
  return Math.min(Math.max(uncertainty, 0), 1);
}

// ═══════════════════════════════════════════════════════════════
// Fusion: Three Signals → Trust Score
// ═══════════════════════════════════════════════════════════════

/**
 * Score a single retrieval chunk against a query.
 *
 * Three-signal fusion:
 *   trustScore = w_p · proximity + w_φ · phase - w_u · uncertainty
 *   anomalyProb = 1 - trustScore
 *   quarantine if trustScore < threshold
 *   attentionWeight = trustScore² (soft gating)
 *
 * @param query - Query state (position + phase)
 * @param chunk - Retrieval chunk
 * @param config - Scorer configuration
 * @returns ChunkTrustScore
 */
export function scoreChunk(
  query: { position: Vector6D; phase: Vector6D },
  chunk: HyperbolicChunk,
  config: RAGScorerConfig = DEFAULT_RAG_CONFIG
): ChunkTrustScore {
  const proxScore = proximityScore(query.position, chunk.position, config.maxTrustDistance);
  const phaseScore = phaseConsistencyScore(chunk.phase, query.phase);
  const uncPenalty = uncertaintyPenalty(chunk.uncertainty);

  // Distances for interpretability
  const distToQuery = hyperbolicDistance6D(query.position, chunk.position);
  const { distance: distToAnchor } = nearestTongueAnchor(chunk.position);

  // Weighted fusion
  const raw =
    config.weightProximity * proxScore +
    config.weightPhase * phaseScore -
    config.weightUncertainty * uncPenalty;

  // Clamp to [0, 1]
  const trustScore = Math.max(0, Math.min(1, raw));
  const anomalyProb = 1 - trustScore;
  const quarantineFlag =
    trustScore < config.quarantineThreshold ||
    chunk.uncertainty > config.maxUncertainty;

  // Soft attention gating: trust² ensures quarantined chunks get near-zero weight
  const attentionWeight = quarantineFlag ? 0 : trustScore * trustScore;

  return {
    chunkId: chunk.chunkId,
    trustScore,
    anomalyProb,
    quarantineFlag,
    attentionWeight,
    signals: {
      proximityScore: proxScore,
      phaseScore,
      uncertaintyPenalty: uncPenalty,
      distanceToQuery: distToQuery,
      distanceToAnchor: distToAnchor,
    },
  };
}

// ═══════════════════════════════════════════════════════════════
// Batch Scoring + kNN Retrieval
// ═══════════════════════════════════════════════════════════════

/**
 * Score all retrieval candidates and return trust-gated results.
 *
 * @param query - Query state
 * @param chunks - Candidate chunks (pre-projected into ball)
 * @param topK - Max results to return (default 10)
 * @param config - Scorer configuration
 * @returns Sorted array of trust scores (highest trust first), quarantined removed
 */
export function scoreAndFilter(
  query: { position: Vector6D; phase: Vector6D },
  chunks: HyperbolicChunk[],
  topK: number = 10,
  config: RAGScorerConfig = DEFAULT_RAG_CONFIG
): ChunkTrustScore[] {
  const scored = chunks.map((c) => scoreChunk(query, c, config));

  // Partition: trusted vs quarantined
  const trusted = scored.filter((s) => !s.quarantineFlag);
  const quarantined = scored.filter((s) => s.quarantineFlag);

  // Sort by trust score descending
  trusted.sort((a, b) => b.trustScore - a.trustScore);

  // Renormalize attention weights so they sum to 1
  const totalWeight = trusted.reduce((s, t) => s + t.attentionWeight, 0);
  if (totalWeight > 0) {
    for (const t of trusted) {
      t.attentionWeight /= totalWeight;
    }
  }

  return trusted.slice(0, topK);
}

/**
 * Full retrieval pipeline: project raw embeddings → score → filter → return.
 *
 * @param queryEmbedding - Raw query embedding
 * @param candidateEmbeddings - Array of { id, embedding } pairs
 * @param topK - Number of results
 * @param config - Scorer config
 * @param scale - Projection scale
 * @returns Trust-gated scored results
 */
export function retrieveWithTrust(
  queryEmbedding: number[],
  candidateEmbeddings: Array<{ id: string; embedding: number[] }>,
  topK: number = 10,
  config: RAGScorerConfig = DEFAULT_RAG_CONFIG,
  scale: number = 0.5
): ChunkTrustScore[] {
  const queryPos = projectToBall(queryEmbedding, scale);
  const queryPhase = extractPhase(queryEmbedding);

  const chunks = candidateEmbeddings.map((c) => buildChunk(c.id, c.embedding, scale));

  return scoreAndFilter({ position: queryPos, phase: queryPhase }, chunks, topK, config);
}

// ═══════════════════════════════════════════════════════════════
// Quarantine Analytics
// ═══════════════════════════════════════════════════════════════

/**
 * Score all chunks and return quarantine analytics.
 *
 * @param query - Query state
 * @param chunks - All chunks
 * @param config - Config
 * @returns { trusted, quarantined, stats }
 */
export function quarantineReport(
  query: { position: Vector6D; phase: Vector6D },
  chunks: HyperbolicChunk[],
  config: RAGScorerConfig = DEFAULT_RAG_CONFIG
): {
  trusted: ChunkTrustScore[];
  quarantined: ChunkTrustScore[];
  stats: {
    total: number;
    trustedCount: number;
    quarantinedCount: number;
    avgTrustScore: number;
    avgAnomalyProb: number;
    quarantineRate: number;
  };
} {
  const scored = chunks.map((c) => scoreChunk(query, c, config));
  const trusted = scored.filter((s) => !s.quarantineFlag);
  const quarantined = scored.filter((s) => s.quarantineFlag);

  const avgTrust = scored.length > 0
    ? scored.reduce((s, t) => s + t.trustScore, 0) / scored.length
    : 0;
  const avgAnomaly = scored.length > 0
    ? scored.reduce((s, t) => s + t.anomalyProb, 0) / scored.length
    : 0;

  return {
    trusted,
    quarantined,
    stats: {
      total: chunks.length,
      trustedCount: trusted.length,
      quarantinedCount: quarantined.length,
      avgTrustScore: avgTrust,
      avgAnomalyProb: avgAnomaly,
      quarantineRate: chunks.length > 0 ? quarantined.length / chunks.length : 0,
    },
  };
}
