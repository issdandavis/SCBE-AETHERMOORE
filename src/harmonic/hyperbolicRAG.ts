/**
 * @file hyperbolicRAG.ts
 * @module harmonic/hyperbolicRAG
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
