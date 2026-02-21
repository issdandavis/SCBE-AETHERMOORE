/**
 * @file frecency.ts
 * @module harmonic/frecency
 * @layer Layer 14, Layer 12, Layer 11
 * @component Frecency Scoring Engine
 * @version 1.0.0
 *
 * Frecency (frequency + recency) scoring that originates at Layer 14 (audio axis)
 * and propagates through the harmonic pipeline layers. Contexts accessed frequently
 * AND recently score higher, with exponential decay for stale entries.
 *
 * Propagation chain:
 *   L14 (audio stability) → L12 (harmonic amplification) → L11 (temporal weighting)
 *
 * Formula:
 *   frecency(ctx) = α·frequency + β·(1/recency) + γ·coherence
 *   propagated(ctx, layer) = frecency(ctx) · H_score(d, pd)
 *
 * Uses exponential decay: score *= e^(-λ·Δt) on each update.
 */

const EPSILON = 1e-10;

/**
 * A single frecency entry tracking access patterns
 */
export interface FrecencyEntry {
  /** Context key identifier */
  key: string;
  /** Access frequency count */
  frequency: number;
  /** Timestamp of last access (ms since epoch) */
  lastAccessedAt: number;
  /** Coherence score from L9/L10 at last access */
  coherence: number;
  /** Current computed frecency score */
  score: number;
}

/**
 * Configuration for the frecency engine
 */
export interface FrecencyConfig {
  /** Weight for frequency component (default: 1.0) */
  alpha?: number;
  /** Weight for recency component (default: 2.0) */
  beta?: number;
  /** Weight for coherence component (default: 1.5) */
  gamma?: number;
  /** Decay rate per second (default: 0.01) */
  decayLambda?: number;
  /** Maximum entries to track (default: 1000) */
  maxEntries?: number;
}

/**
 * Frecency scoring engine for context embeddings in Polly Pads.
 *
 * Tracks how frequently and recently contexts are accessed,
 * integrating coherence from the spectral layers (L9/L10)
 * to rank memories and prioritize agentic decisions.
 */
export class FrecencyEngine {
  private entries: Map<string, FrecencyEntry> = new Map();
  private alpha: number;
  private beta: number;
  private gamma: number;
  private decayLambda: number;
  private maxEntries: number;

  constructor(config: FrecencyConfig = {}) {
    this.alpha = config.alpha ?? 1.0;
    this.beta = config.beta ?? 2.0;
    this.gamma = config.gamma ?? 1.5;
    this.decayLambda = config.decayLambda ?? 0.01;
    this.maxEntries = config.maxEntries ?? 1000;
  }

  /**
   * Record an access to a context key, updating its frecency score.
   *
   * @param key - Context identifier
   * @param coherence - Current L9/L10 coherence score (0-1)
   * @param now - Current timestamp in ms (default: Date.now())
   * @returns Updated frecency score
   */
  recordAccess(key: string, coherence: number = 0.8, now: number = Date.now()): number {
    const existing = this.entries.get(key);

    if (existing) {
      // Apply decay to existing score based on time elapsed
      const deltaSeconds = Math.max(0, (now - existing.lastAccessedAt) / 1000);
      const decayedScore = existing.score * Math.exp(-this.decayLambda * deltaSeconds);

      existing.frequency += 1;
      existing.lastAccessedAt = now;
      existing.coherence = coherence;
      existing.score = decayedScore + this.computeIncrement(existing.frequency, 1.0, coherence);
      return existing.score;
    }

    // New entry
    const score = this.computeIncrement(1, 1.0, coherence);
    const entry: FrecencyEntry = {
      key,
      frequency: 1,
      lastAccessedAt: now,
      coherence,
      score,
    };
    this.entries.set(key, entry);

    // Evict lowest-scoring entry if over capacity
    if (this.entries.size > this.maxEntries) {
      this.evictLowest();
    }

    return score;
  }

  /**
   * Compute the base frecency increment.
   *
   * frecency_inc = α·frequency + β·(1/recency) + γ·coherence
   *
   * @param frequency - Access count
   * @param recency - Time factor (1.0 = just now)
   * @param coherence - Spectral coherence (0-1)
   */
  private computeIncrement(frequency: number, recency: number, coherence: number): number {
    return (
      this.alpha * Math.log1p(frequency) +
      this.beta * (1 / (recency + EPSILON)) +
      this.gamma * coherence
    );
  }

  /**
   * Get the current frecency score for a context, with time-based decay applied.
   *
   * @param key - Context identifier
   * @param now - Current timestamp in ms
   * @returns Decayed frecency score, or 0 if not found
   */
  getScore(key: string, now: number = Date.now()): number {
    const entry = this.entries.get(key);
    if (!entry) return 0;

    const deltaSeconds = Math.max(0, (now - entry.lastAccessedAt) / 1000);
    return entry.score * Math.exp(-this.decayLambda * deltaSeconds);
  }

  /**
   * Propagate frecency through harmonic scaling (L12).
   *
   * propagated = frecency · H_score
   * where H_score = 1 / (1 + d_H + 2·phaseDeviation)
   *
   * Higher distance → lower propagated score (safe contexts amplified,
   * risky contexts suppressed).
   *
   * @param key - Context identifier
   * @param hyperbolicDistance - d_H from Layer 5
   * @param phaseDeviation - Phase deviation from L7
   * @param now - Current timestamp
   * @returns Propagated frecency score
   */
  propagateThroughHarmonic(
    key: string,
    hyperbolicDistance: number,
    phaseDeviation: number = 0,
    now: number = Date.now()
  ): number {
    const baseFrecency = this.getScore(key, now);
    const hScore = 1 / (1 + hyperbolicDistance + 2 * phaseDeviation);
    return baseFrecency * hScore;
  }

  /**
   * Get the top-K entries by frecency score (with decay applied).
   *
   * @param k - Number of entries to return
   * @param now - Current timestamp
   * @returns Sorted entries (highest score first)
   */
  getTopK(k: number, now: number = Date.now()): FrecencyEntry[] {
    const scored = Array.from(this.entries.values()).map((entry) => ({
      ...entry,
      score: this.getScore(entry.key, now),
    }));
    scored.sort((a, b) => b.score - a.score);
    return scored.slice(0, k);
  }

  /**
   * Decay all entries and remove those below threshold.
   *
   * @param threshold - Minimum score to keep (default: 0.01)
   * @param now - Current timestamp
   * @returns Number of entries pruned
   */
  prune(threshold: number = 0.01, now: number = Date.now()): number {
    let pruned = 0;
    for (const [key, entry] of this.entries) {
      const decayedScore = this.getScore(key, now);
      if (decayedScore < threshold) {
        this.entries.delete(key);
        pruned++;
      } else {
        entry.score = decayedScore;
        entry.lastAccessedAt = now;
      }
    }
    return pruned;
  }

  /**
   * Get all entries (snapshot).
   */
  getAllEntries(): FrecencyEntry[] {
    return Array.from(this.entries.values());
  }

  /**
   * Get the total number of tracked entries.
   */
  get size(): number {
    return this.entries.size;
  }

  /**
   * Clear all entries.
   */
  clear(): void {
    this.entries.clear();
  }

  private evictLowest(): void {
    let lowestKey: string | null = null;
    let lowestScore = Infinity;
    for (const [key, entry] of this.entries) {
      if (entry.score < lowestScore) {
        lowestScore = entry.score;
        lowestKey = key;
      }
    }
    if (lowestKey) this.entries.delete(lowestKey);
  }
}
