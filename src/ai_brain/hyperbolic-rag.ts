/**
 * @file hyperbolic-rag.ts
 * @module ai_brain/hyperbolic-rag
 * @layer Layer 5, Layer 12, Layer 13
 * @version 1.0.0
 *
 * HyperbolicRAG: Nearest-neighbor retrieval in the Poincare ball with d* cost gating.
 *
 * Turns the Poincare ball into a governed retrieval engine:
 * - k-NN search via hyperbolic distance (arcosh metric)
 * - d* cost gating: high-cost candidates are quarantined (Layer 12 wall)
 * - Phase alignment: tongue-phase consistency filters off-grammar chunks
 * - Realm overlap: octree-based spatial overlap scoring from quasi-space
 *
 * Integrates with GeoSeal (immune dynamics) and the 14-layer pipeline
 * (Layer 12 harmonic wall provides cost threshold, Layer 13 risk decision).
 */

import {
  hyperbolicDistance,
  phaseDeviation,
  projectEmbeddingToBall,
  clampToBall,
} from '../harmonic/hyperbolic.js';

import { TONGUE_PHASES } from '../geoseal.js';

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

/** A candidate chunk for RAG retrieval */
export interface RAGCandidate {
  id: string;
  embedding: number[];
  tongue?: string;
  metadata?: Record<string, unknown>;
}

/** Scored retrieval result after d* gating */
export interface RAGResult {
  id: string;
  /** Hyperbolic distance to query */
  distance: number;
  /** Trust score: inverse of normalized cost */
  trust_score: number;
  /** Phase alignment score [0, 1] */
  phase_score: number;
  /** Whether this candidate was gated (quarantined) */
  gated: boolean;
  metadata?: Record<string, unknown>;
}

/** Configuration for HyperbolicRAG retrieval */
export interface HyperbolicRAGConfig {
  /** Maximum candidates to return */
  maxK: number;
  /** d* cost threshold - candidates above this are gated (Layer 12 wall) */
  costThreshold: number;
  /** Minimum phase alignment to pass (0 = accept all, 1 = exact match only) */
  minPhaseAlignment: number;
  /** Weight for phase in combined scoring (0 = ignore phase) */
  phaseWeight: number;
}

export const DEFAULT_RAG_CONFIG: HyperbolicRAGConfig = {
  maxK: 20,
  costThreshold: 1.5,
  minPhaseAlignment: 0.0,
  phaseWeight: 2.0,
};

// ═══════════════════════════════════════════════════════════════
// HyperbolicRAG class
// ═══════════════════════════════════════════════════════════════

export class HyperbolicRAG {
  private config: HyperbolicRAGConfig;

  constructor(config: Partial<HyperbolicRAGConfig> = {}) {
    this.config = { ...DEFAULT_RAG_CONFIG, ...config };
  }

  /**
   * Perform hyperbolic k-NN retrieval with cost gating.
   *
   * 1. Project all embeddings to Poincare ball
   * 2. Compute hyperbolic distances from query
   * 3. Sort by distance, take top-k
   * 4. Gate by d* cost threshold (Layer 12 harmonic wall)
   * 5. Filter by phase alignment (tongue discipline)
   * 6. Return scored results
   *
   * @param queryEmbedding - Query vector (will be projected to ball)
   * @param candidates - Candidate chunks with embeddings
   * @param queryTongue - Optional tongue for phase-based filtering
   * @returns Sorted RAGResult array (trusted candidates only)
   */
  retrieve(
    queryEmbedding: number[],
    candidates: RAGCandidate[],
    queryTongue?: string
  ): RAGResult[] {
    const query = projectEmbeddingToBall(queryEmbedding);
    const queryPhase = queryTongue ? (TONGUE_PHASES[queryTongue] ?? null) : null;

    // Compute distances and scores
    const scored: RAGResult[] = candidates.map((c) => {
      const projected = projectEmbeddingToBall([...c.embedding]);
      const dist = hyperbolicDistance(query, projected);

      // Phase alignment
      const candPhase = c.tongue ? (TONGUE_PHASES[c.tongue] ?? null) : null;
      const phaseDev = phaseDeviation(queryPhase, candPhase);
      const phase_score = 1.0 - phaseDev;

      // Combined trust: inverse cost with phase weighting
      const rawTrust = 1.0 / (1.0 + dist + this.config.phaseWeight * phaseDev);

      // Gating: d* above threshold OR phase below minimum
      const gated =
        dist > this.config.costThreshold ||
        phase_score < this.config.minPhaseAlignment;

      return {
        id: c.id,
        distance: dist,
        trust_score: gated ? 0 : rawTrust,
        phase_score,
        gated,
        metadata: c.metadata,
      };
    });

    // Sort by distance (ascending)
    scored.sort((a, b) => a.distance - b.distance);

    // Take top-k, exclude gated
    const results: RAGResult[] = [];
    for (const s of scored) {
      if (results.length >= this.config.maxK) break;
      if (!s.gated) {
        results.push(s);
      }
    }

    return results;
  }

  /**
   * Retrieve and return all results (including gated), for diagnostics.
   */
  retrieveAll(
    queryEmbedding: number[],
    candidates: RAGCandidate[],
    queryTongue?: string
  ): RAGResult[] {
    const query = projectEmbeddingToBall(queryEmbedding);
    const queryPhase = queryTongue ? (TONGUE_PHASES[queryTongue] ?? null) : null;

    const scored: RAGResult[] = candidates.map((c) => {
      const projected = projectEmbeddingToBall([...c.embedding]);
      const dist = hyperbolicDistance(query, projected);
      const candPhase = c.tongue ? (TONGUE_PHASES[c.tongue] ?? null) : null;
      const phaseDev = phaseDeviation(queryPhase, candPhase);
      const phase_score = 1.0 - phaseDev;
      const rawTrust = 1.0 / (1.0 + dist + this.config.phaseWeight * phaseDev);
      const gated =
        dist > this.config.costThreshold ||
        phase_score < this.config.minPhaseAlignment;

      return {
        id: c.id,
        distance: dist,
        trust_score: gated ? 0 : rawTrust,
        phase_score,
        gated,
        metadata: c.metadata,
      };
    });

    scored.sort((a, b) => a.distance - b.distance);
    return scored;
  }

  /**
   * Update configuration at runtime (e.g., adjust cost threshold).
   */
  updateConfig(partial: Partial<HyperbolicRAGConfig>): void {
    Object.assign(this.config, partial);
  }

  /**
   * Get current configuration.
   */
  getConfig(): Readonly<HyperbolicRAGConfig> {
    return { ...this.config };
  }
}
