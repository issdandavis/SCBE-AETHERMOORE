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
  accessCost as chsfnAccessCost,
  tongueImpedanceAt,
  type CHSFNState,
  type TongueImpedance,
  DEFAULT_IMPEDANCE,
} from './chsfn.js';
/**
 * @layer Layer 5, Layer 7, Layer 12, Layer 13
 * @component HyperbolicRAG — Poincaré Ball Retrieval-Augmented Generation
 * @version 3.2.4
 *
 * Nearest-neighbor retrieval in the Poincaré ball where access cost
 * (harmonic wall) gates what enters context. Documents closer to the
 * origin (trust center) are cheaper to retrieve; documents near the
 * boundary are exponentially expensive, making adversarial injection
 * into context computationally infeasible.
 *
 * Key invariants:
 *   1. accessCost(d*) >= 1 for all retrievals (minimum cost = 1)
 *   2. accessCost grows as phi^d / (1 + e^{-R}) near boundary
 *   3. Context budget enforces a hard cap on total retrieval cost
 *   4. Phase alignment gates relevance — wrong-phase docs are filtered
 *
 * Builds on:
 *   - hyperbolic.ts: Poincaré ball ops (L5-L7)
 *   - harmonicScaling.ts: harmonicScale (L12)
 *   - adaptiveNavigator.ts: realm centers, trajectoryEntropy (L5, L13)
 */

import {
  hyperbolicDistance,
  projectEmbeddingToBall,
  expMap0,
  logMap0,
  mobiusAdd,
  clampToBall,
  phaseDistanceScore,
  scoreRetrievals,
} from './hyperbolic.js';
import { harmonicScale } from './harmonicScaling.js';
import { REALM_CENTERS, TONGUE_WEIGHTS } from './adaptiveNavigator.js';

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
  const cost = chsfnAccessCost(dist);
  const baseCost = chsfnAccessCost(0);
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

/** A document embedded in the Poincaré ball for retrieval. */
export interface RAGDocument {
  /** Unique identifier */
  id: string;
  /** Position in Poincaré ball (any dimension, must match query) */
  embedding: number[];
  /** Phase angle for tongue alignment (radians, or null if unclassified) */
  phase: number | null;
  /** Optional metadata */
  metadata?: Record<string, unknown>;
  /** Timestamp of insertion (ms since epoch) */
  insertedAt: number;
}

/** Internal indexed entry with precomputed norm. */
interface IndexedDocument {
  doc: RAGDocument;
  norm: number;
}

/** Result of a single retrieval with cost accounting. */
export interface RetrievalResult {
  /** Document id */
  id: string;
  /** Trust-distance score in (0, 1] — higher is more trusted */
  trustScore: number;
  /** Access cost for this retrieval — phi^d gated */
  accessCost: number;
  /** Phase-distance score from scoreRetrievals */
  relevanceScore: number;
  /** Combined rank score (relevance / accessCost) */
  rankScore: number;
  /** The original document */
  document: RAGDocument;
}

/** Configuration for the RAG engine. */
export interface HyperbolicRAGConfig {
  /** Maximum total access cost budget per query (default: 20.0) */
  contextBudget: number;
  /** Maximum number of documents to return (default: 10) */
  maxResults: number;
  /** Minimum relevance score to include (default: 0.1) */
  minRelevance: number;
  /** Phase weight for scoring (default: 2.0) */
  phaseWeight: number;
  /** Access cost base — controls exponential steepness (default: PHI) */
  costBase: number;
  /** Risk amplification factor for boundary documents (default: 1.0) */
  riskAmplification: number;
  /** Maximum age for documents in ms (0 = no limit, default: 0) */
  maxAge: number;
  /** Dimension of the Poincaré ball (default: 6) */
  dimension: number;
}

/** Summary of a retrieval batch. */
export interface RetrievalSummary {
  /** Documents returned, ranked by rankScore descending */
  results: RetrievalResult[];
  /** Total access cost consumed */
  totalCost: number;
  /** Remaining budget */
  remainingBudget: number;
  /** Number of candidates considered */
  candidatesConsidered: number;
  /** Number of candidates rejected by phase/relevance filter */
  filteredOut: number;
  /** Number of candidates rejected by budget exhaustion */
  budgetExhausted: number;
  /** Query position norm (distance from trust center) */
  queryNorm: number;
}

// ═══════════════════════════════════════════════════════════════
// Access Cost Function
// ═══════════════════════════════════════════════════════════════

/**
 * Compute the access cost for retrieving a document at hyperbolic
 * distance `d` from the query. Cost grows exponentially with distance,
 * making adversarial documents near the boundary infeasible to include.
 *
 * Formula: accessCost = base^d * (1 + riskAmp * (1 - harmonicScale(d)))
 *
 * @param d - Hyperbolic distance from query to document
 * @param base - Exponential base (default: PHI)
 * @param riskAmplification - Risk scaling factor (default: 1.0)
 * @returns Access cost >= 1
 */
export function accessCost(
  d: number,
  base: number = PHI,
  riskAmplification: number = 1.0,
): number {
  if (d < 0) throw new RangeError('Distance must be non-negative');
  if (d < EPSILON) return 1.0;

  const baseCost = Math.pow(base, d);
  const safetyDecay = 1 - harmonicScale(d);
  return baseCost * (1 + riskAmplification * safetyDecay);
}

/**
 * Compute trust from a position's distance to the origin.
 * Mirrors geo_seal.py trust_from_position.
 *
 * @param point - Position in Poincaré ball
 * @returns Trust in (0, 1]
 */
export function trustFromPosition(point: number[]): number {
  const n = norm(point);
  if (n < EPSILON) return 1.0;
  // Hyperbolic distance from origin: 2 * arctanh(||p||)
  const d = 2 * Math.atanh(Math.min(n, 1 - EPSILON));
  return 1.0 / (1.0 + d);
}

// ═══════════════════════════════════════════════════════════════
// HyperbolicRAG Engine
// ═══════════════════════════════════════════════════════════════

/**
 * Retrieval-Augmented Generation engine using Poincaré ball geometry.
 *
 * Documents are embedded in the Poincaré ball. Retrieval uses hyperbolic
 * distance + phase alignment for relevance, and the harmonic wall
 * (accessCost) to gate what enters context. A fixed context budget
 * ensures that including adversarial (boundary-positioned) documents
 * exhausts the budget, protecting the downstream model.
 */
export class HyperbolicRAGEngine {
  private readonly config: HyperbolicRAGConfig;
  private readonly index: Map<string, IndexedDocument> = new Map();

  constructor(config?: Partial<HyperbolicRAGConfig>) {
    this.config = {
      contextBudget: 20.0,
      maxResults: 10,
      minRelevance: 0.1,
      phaseWeight: 2.0,
      costBase: PHI,
      riskAmplification: 1.0,
      maxAge: 0,
      dimension: 6,
      ...config,
    };
  }

  // ─────────────────────────────────────────────────────────────
  // Index Management
  // ─────────────────────────────────────────────────────────────

  /**
   * Add a document to the index. The embedding must be inside the
   * Poincaré ball (norm < 1). If not, it is projected via
   * projectEmbeddingToBall.
   */
  addDocument(doc: RAGDocument): void {
    const emb = this.ensureInBall(doc.embedding);
    const n = norm(emb);
    this.index.set(doc.id, {
      doc: { ...doc, embedding: emb },
      norm: n,
    });
  }

  /**
   * Add multiple documents at once.
   */
  addDocuments(docs: RAGDocument[]): void {
    for (const doc of docs) {
      this.addDocument(doc);
    }
  }

  /**
   * Remove a document by id.
   * @returns true if the document was found and removed
   */
  removeDocument(id: string): boolean {
    return this.index.delete(id);
  }

  /**
   * Get the number of indexed documents.
   */
  get size(): number {
    return this.index.size;
  }

  /**
   * Clear all documents from the index.
   */
  clear(): void {
    this.index.clear();
  }

  /**
   * Retrieve a document by id (or undefined if not found).
   */
  getDocument(id: string): RAGDocument | undefined {
    return this.index.get(id)?.doc;
  }

  // ─────────────────────────────────────────────────────────────
  // Retrieval
  // ─────────────────────────────────────────────────────────────

  /**
   * Retrieve documents relevant to a query, gated by access cost.
   *
   * Algorithm:
   *   1. Project query into the Poincaré ball
   *   2. Compute hyperbolic distance + phase-distance score for each doc
   *   3. Filter by minimum relevance and max age
   *   4. Compute access cost for each candidate
   *   5. Rank by rankScore = relevanceScore / accessCost
   *   6. Greedily fill context budget in rank order
   *
   * @param queryEmbedding - Query vector (will be projected to ball)
   * @param queryPhase - Query phase angle (radians, or null)
   * @returns RetrievalSummary with ranked, cost-gated results
   */
  retrieve(queryEmbedding: number[], queryPhase: number | null): RetrievalSummary {
    const query = this.ensureInBall(queryEmbedding);
    const queryNorm = norm(query);
    const now = Date.now();

    // Score all candidates
    const candidates: Array<{
      id: string;
      doc: RAGDocument;
      distance: number;
      relevanceScore: number;
      accessCost: number;
      rankScore: number;
    }> = [];

    let filteredOut = 0;

    for (const [id, entry] of this.index) {
      // Age filter
      if (this.config.maxAge > 0 && (now - entry.doc.insertedAt) > this.config.maxAge) {
        filteredOut++;
        continue;
      }

      // Compute hyperbolic distance
      const d = hyperbolicDistance(query, entry.doc.embedding);

      // Compute relevance via phase-distance score
      const relevance = phaseDistanceScore(query, entry.doc.embedding, queryPhase, entry.doc.phase, this.config.phaseWeight);

      // Filter low relevance
      if (relevance < this.config.minRelevance) {
        filteredOut++;
        continue;
      }

      // Compute access cost
      const cost = accessCost(d, this.config.costBase, this.config.riskAmplification);

      candidates.push({
        id,
        doc: entry.doc,
        distance: d,
        relevanceScore: relevance,
        accessCost: cost,
        rankScore: relevance / cost,
      });
    }

    // Sort by rankScore descending (best value first)
    candidates.sort((a, b) => b.rankScore - a.rankScore);

    // Greedily fill context budget
    const results: RetrievalResult[] = [];
    let totalCost = 0;
    let budgetExhausted = 0;

    for (const c of candidates) {
      if (results.length >= this.config.maxResults) break;

      if (totalCost + c.accessCost > this.config.contextBudget) {
        budgetExhausted++;
        continue;
      }

      totalCost += c.accessCost;
      results.push({
        id: c.id,
        trustScore: trustFromPosition(c.doc.embedding),
        accessCost: c.accessCost,
        relevanceScore: c.relevanceScore,
        rankScore: c.rankScore,
        document: c.doc,
      });
    }

    return {
      results,
      totalCost,
      remainingBudget: this.config.contextBudget - totalCost,
      candidatesConsidered: this.index.size,
      filteredOut,
      budgetExhausted,
      queryNorm,
    };
  }

  /**
   * Retrieve using tongue-aligned query — projects the query toward
   * the specified Sacred Tongue realm center before retrieval.
   *
   * @param queryEmbedding - Raw query vector
   * @param queryPhase - Query phase
   * @param tongue - Sacred Tongue code (KO, AV, RU, CA, UM, DR)
   * @param tongueInfluence - How much to bias toward tongue center (0-1, default: 0.3)
   */
  retrieveByTongue(
    queryEmbedding: number[],
    queryPhase: number | null,
    tongue: string,
    tongueInfluence: number = 0.3,
  ): RetrievalSummary {
    const center = REALM_CENTERS[tongue];
    if (!center) {
      throw new Error(`Unknown tongue: ${tongue}. Valid: ${Object.keys(REALM_CENTERS).join(', ')}`);
    }

    // Blend query toward tongue center in tangent space
    const query = this.ensureInBall(queryEmbedding);
    const padded = padToLength(query, center.length);
    const blended = padded.map((q, i) => q * (1 - tongueInfluence) + center[i] * tongueInfluence);
    const projected = clampToBall(blended, 0.95);

    return this.retrieve(projected, queryPhase);
  }

  /**
   * Compute the maximum number of documents retrievable from a given
   * position before exhausting the context budget. Useful for capacity
   * planning.
   *
   * @param position - Position in the Poincaré ball
   * @param avgDocDistance - Average hyperbolic distance to docs (default: 1.0)
   */
  estimateCapacity(position: number[], avgDocDistance: number = 1.0): number {
    const cost = accessCost(avgDocDistance, this.config.costBase, this.config.riskAmplification);
    return Math.floor(this.config.contextBudget / cost);
  }

  // ─────────────────────────────────────────────────────────────
  // Nearest Neighbors (raw, without cost gating)
  // ─────────────────────────────────────────────────────────────

  /**
   * Find k nearest neighbors by hyperbolic distance (no cost gating).
   * Useful for diagnostics and visualization.
   */
  kNearest(queryEmbedding: number[], k: number): Array<{ id: string; distance: number; doc: RAGDocument }> {
    const query = this.ensureInBall(queryEmbedding);
    const scored: Array<{ id: string; distance: number; doc: RAGDocument }> = [];

    for (const [id, entry] of this.index) {
      const d = hyperbolicDistance(query, entry.doc.embedding);
      scored.push({ id, distance: d, doc: entry.doc });
    }

    scored.sort((a, b) => a.distance - b.distance);
    return scored.slice(0, k);
  }

  // ─────────────────────────────────────────────────────────────
  // Internals
  // ─────────────────────────────────────────────────────────────

  /**
   * Ensure a vector is inside the Poincaré ball. If norm >= 1,
   * project using the smooth tanh mapping.
   */
  private ensureInBall(v: number[]): number[] {
    const dim = this.config.dimension;
    const padded = padToLength(v, dim);
    const n = norm(padded);
    if (n >= 1 - EPSILON) {
      return projectEmbeddingToBall(padded);
    }
    return padded;
  }
}

// ═══════════════════════════════════════════════════════════════
// Utility Helpers
// ═══════════════════════════════════════════════════════════════

function norm(v: number[]): number {
  return Math.sqrt(v.reduce((s, x) => s + x * x, 0));
}

function padToLength(v: number[], length: number): number[] {
  if (v.length >= length) return v.slice(0, length);
  const padded = new Array(length).fill(0);
  for (let i = 0; i < v.length; i++) padded[i] = v[i];
  return padded;
}

// ═══════════════════════════════════════════════════════════════
// Factory
// ═══════════════════════════════════════════════════════════════

/**
 * Create a pre-configured HyperbolicRAG engine.
 */
export function createHyperbolicRAG(config?: Partial<HyperbolicRAGConfig>): HyperbolicRAGEngine {
  return new HyperbolicRAGEngine(config);
}
