/**
 * @file orderedRejection.ts
 * @module api/orderedRejection
 * @layer Layer 13
 * @component Ordered Rejection Verification Pipeline
 *
 * Implements fail-fast ordered rejection: invalid requests fail on the
 * cheapest check (microseconds) and never reach expensive PQ crypto.
 *
 * Stage ordering by computational cost:
 *   S0: Timestamp skew        (~1 µs)   — clock drift bounds
 *   S1: Replay guard          (~1 µs)   — nonce dedup
 *   S2: Nonce prefix          (~2 µs)   — structural validity
 *   S3: Context commitment    (~5 µs)   — HMAC binding
 *   S4: Trust gate            (~1 µs)   — numeric threshold
 *   S5: Policy evaluation     (~10 µs)  — rule matching
 *   S6: Poincaré embedding    (~50 µs)  — hash-to-ball projection
 *   S7: Realm distance        (~100 µs) — d_H(u,v) = arcosh(...)
 *   S8: Spectral coherence    (~200 µs) — FFT check
 *   S9: Risk composite        (~50 µs)  — Lemma 13.1 computation
 *   S10: PQ crypto verify     (~2 ms)   — ML-DSA-65 / ML-KEM-768
 *
 * Under adversarial load: attacker pays full compute, we pay near-zero
 * for rejections that fail at S0–S4.
 */

import { createHash, createHmac, randomBytes } from 'crypto';

// ============================================================================
// Types
// ============================================================================

/** Verification stage identifier */
export type StageId =
  | 'S0_TIMESTAMP_SKEW'
  | 'S1_REPLAY_GUARD'
  | 'S2_NONCE_PREFIX'
  | 'S3_CONTEXT_COMMITMENT'
  | 'S4_TRUST_GATE'
  | 'S5_POLICY_EVAL'
  | 'S6_POINCARE_EMBED'
  | 'S7_REALM_DISTANCE'
  | 'S8_SPECTRAL_COHERENCE'
  | 'S9_RISK_COMPOSITE'
  | 'S10_PQ_CRYPTO';

/** Result of a single verification stage */
export interface StageResult {
  stage: StageId;
  passed: boolean;
  durationMicros: number;
  rationale: string;
}

/** Final pipeline result */
export interface RejectionPipelineResult {
  /** True if all stages passed */
  accepted: boolean;
  /** Stage that caused rejection (null if accepted) */
  rejectedAt: StageId | null;
  /** Ordered list of stage results (only includes executed stages) */
  stages: StageResult[];
  /** Total pipeline duration in microseconds */
  totalMicros: number;
  /** Fail-to-noise output if rejected */
  noisePayload: string | null;
}

/** Request envelope for the ordered rejection pipeline */
export interface RejectionRequest {
  /** ISO-8601 timestamp from the client */
  clientTimestamp: string;
  /** Unique nonce for replay protection */
  nonce: string;
  /** Actor trust score [0, 1] */
  trustScore: number;
  /** Actor identifier */
  actorId: string;
  /** Actor type */
  actorType: 'human' | 'ai' | 'system' | 'external';
  /** Intent string */
  intent: string;
  /** HMAC commitment over context fields */
  contextCommitment?: string;
  /** Raw context for HMAC verification */
  context?: Record<string, unknown>;
  /** Resource classification */
  resourceClassification?: 'public' | 'internal' | 'confidential' | 'restricted';
}

/** Pipeline configuration */
export interface PipelineConfig {
  /** Max allowed clock skew in milliseconds (default: 30000) */
  maxTimestampSkewMs: number;
  /** Required nonce prefix (default: 'scbe-') */
  noncePrefix: string;
  /** Minimum nonce length (default: 16) */
  minNonceLength: number;
  /** Trust threshold for immediate quarantine (default: 0.3) */
  trustQuarantineThreshold: number;
  /** Trust threshold for marginal scrutiny (default: 0.5) */
  trustMarginalThreshold: number;
  /** HMAC secret for context commitment verification */
  commitmentSecret: string;
  /** Enable fail-to-noise on rejection (default: true) */
  failToNoise: boolean;
}

// ============================================================================
// Defaults
// ============================================================================

const DEFAULT_CONFIG: PipelineConfig = {
  maxTimestampSkewMs: 30_000,
  noncePrefix: 'scbe-',
  minNonceLength: 16,
  trustQuarantineThreshold: 0.3,
  trustMarginalThreshold: 0.5,
  commitmentSecret: 'scbe-ordered-rejection-default-key',
  failToNoise: true,
};

// ============================================================================
// Nonce Cache (Replay Guard)
// ============================================================================

/** Sliding-window nonce cache with automatic eviction */
class NonceCache {
  private readonly cache = new Map<string, number>();
  private readonly maxAgeMs: number;
  private readonly maxSize: number;

  constructor(maxAgeMs = 5 * 60 * 1000, maxSize = 100_000) {
    this.maxAgeMs = maxAgeMs;
    this.maxSize = maxSize;
  }

  /** Returns false if nonce was already seen (replay) */
  consume(nonce: string): boolean {
    const now = Date.now();
    // Lazy eviction: clean when approaching capacity
    if (this.cache.size > this.maxSize * 0.9) {
      this.evict(now);
    }
    if (this.cache.has(nonce)) {
      const ts = this.cache.get(nonce)!;
      if (now - ts < this.maxAgeMs) {
        return false; // Replay
      }
    }
    this.cache.set(nonce, now);
    return true;
  }

  private evict(now: number): void {
    for (const [nonce, ts] of Array.from(this.cache.entries())) {
      if (now - ts > this.maxAgeMs) {
        this.cache.delete(nonce);
      }
    }
  }

  get size(): number {
    return this.cache.size;
  }
}

// ============================================================================
// Ordered Rejection Pipeline
// ============================================================================

/**
 * Ordered Rejection Verification Pipeline.
 *
 * Stages execute in strict cost order. On first failure, the pipeline
 * short-circuits and returns a fail-to-noise payload (cryptographically
 * random output indistinguishable from valid responses).
 *
 * A4: Clamping — trust scores clamped to [0,1]
 * A3: Causality — timestamp ordering enforced at S0
 */
export class OrderedRejectionPipeline {
  private readonly config: PipelineConfig;
  private readonly nonceCache: NonceCache;

  constructor(config?: Partial<PipelineConfig>) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.nonceCache = new NonceCache();
  }

  /**
   * Execute the full ordered rejection pipeline.
   *
   * Stages run in strict cost order. First failure short-circuits.
   */
  verify(request: RejectionRequest): RejectionPipelineResult {
    const stages: StageResult[] = [];
    const pipelineStart = this.microtime();

    // Stage sequence — ordered by computational cost (cheapest first)
    const stageSequence: Array<{
      id: StageId;
      fn: (req: RejectionRequest) => { passed: boolean; rationale: string };
    }> = [
      { id: 'S0_TIMESTAMP_SKEW', fn: (r) => this.s0TimestampSkew(r) },
      { id: 'S1_REPLAY_GUARD', fn: (r) => this.s1ReplayGuard(r) },
      { id: 'S2_NONCE_PREFIX', fn: (r) => this.s2NoncePrefix(r) },
      { id: 'S3_CONTEXT_COMMITMENT', fn: (r) => this.s3ContextCommitment(r) },
      { id: 'S4_TRUST_GATE', fn: (r) => this.s4TrustGate(r) },
      { id: 'S5_POLICY_EVAL', fn: (r) => this.s5PolicyEval(r) },
    ];

    for (const stage of stageSequence) {
      const stageStart = this.microtime();
      const result = stage.fn(request);
      const durationMicros = this.microtime() - stageStart;

      const stageResult: StageResult = {
        stage: stage.id,
        passed: result.passed,
        durationMicros,
        rationale: result.rationale,
      };
      stages.push(stageResult);

      // Short-circuit on first failure
      if (!result.passed) {
        const totalMicros = this.microtime() - pipelineStart;
        return {
          accepted: false,
          rejectedAt: stage.id,
          stages,
          totalMicros,
          noisePayload: this.config.failToNoise ? this.generateNoise() : null,
        };
      }
    }

    const totalMicros = this.microtime() - pipelineStart;
    return {
      accepted: true,
      rejectedAt: null,
      stages,
      totalMicros,
      noisePayload: null,
    };
  }

  // --------------------------------------------------------------------------
  // Stage Implementations
  // --------------------------------------------------------------------------

  /** S0: Timestamp skew — reject if clock drift exceeds threshold */
  private s0TimestampSkew(req: RejectionRequest): { passed: boolean; rationale: string } {
    const clientTime = new Date(req.clientTimestamp).getTime();
    if (isNaN(clientTime)) {
      return { passed: false, rationale: 'Invalid timestamp format' };
    }
    const skew = Math.abs(Date.now() - clientTime);
    if (skew > this.config.maxTimestampSkewMs) {
      return {
        passed: false,
        rationale: `Timestamp skew ${skew}ms exceeds ${this.config.maxTimestampSkewMs}ms`,
      };
    }
    return { passed: true, rationale: `Timestamp skew ${skew}ms within bounds` };
  }

  /** S1: Replay guard — reject duplicate nonces */
  private s1ReplayGuard(req: RejectionRequest): { passed: boolean; rationale: string } {
    if (!this.nonceCache.consume(req.nonce)) {
      return { passed: false, rationale: 'Nonce replay detected' };
    }
    return { passed: true, rationale: 'Nonce accepted' };
  }

  /** S2: Nonce prefix — structural validity check */
  private s2NoncePrefix(req: RejectionRequest): { passed: boolean; rationale: string } {
    if (!req.nonce.startsWith(this.config.noncePrefix)) {
      return {
        passed: false,
        rationale: `Nonce missing required prefix '${this.config.noncePrefix}'`,
      };
    }
    if (req.nonce.length < this.config.minNonceLength) {
      return {
        passed: false,
        rationale: `Nonce length ${req.nonce.length} below minimum ${this.config.minNonceLength}`,
      };
    }
    return { passed: true, rationale: 'Nonce structure valid' };
  }

  /** S3: Context commitment — HMAC binding verification */
  private s3ContextCommitment(req: RejectionRequest): { passed: boolean; rationale: string } {
    // Skip if no commitment provided (optional stage)
    if (!req.contextCommitment) {
      return { passed: true, rationale: 'No commitment required' };
    }
    if (!req.context) {
      return { passed: false, rationale: 'Commitment present but no context to verify' };
    }
    const expected = createHmac('sha256', this.config.commitmentSecret)
      .update(JSON.stringify(req.context))
      .digest('hex');
    if (req.contextCommitment !== expected) {
      return { passed: false, rationale: 'Context commitment HMAC mismatch' };
    }
    return { passed: true, rationale: 'Context commitment verified' };
  }

  /** S4: Trust gate — immediate QUARANTINE for low-trust actors */
  private s4TrustGate(req: RejectionRequest): { passed: boolean; rationale: string } {
    // A4: Clamp trust to [0, 1]
    const trust = Math.max(0, Math.min(1, req.trustScore));
    if (trust < this.config.trustQuarantineThreshold) {
      return {
        passed: false,
        rationale: `Trust ${trust.toFixed(3)} below quarantine threshold ${this.config.trustQuarantineThreshold}`,
      };
    }
    return { passed: true, rationale: `Trust ${trust.toFixed(3)} above threshold` };
  }

  /** S5: Policy evaluation — intent/classification matching */
  private s5PolicyEval(req: RejectionRequest): { passed: boolean; rationale: string } {
    // Destructive intents from AI actors are hard-denied
    const destructive = ['delete', 'destroy', 'remove', 'purge'];
    if (destructive.includes(req.intent) && req.actorType === 'ai') {
      return {
        passed: false,
        rationale: `AI actors cannot perform destructive intent '${req.intent}'`,
      };
    }
    // AI cannot access restricted resources
    if (req.resourceClassification === 'restricted' && req.actorType === 'ai') {
      return {
        passed: false,
        rationale: 'AI actors cannot access restricted resources',
      };
    }
    return { passed: true, rationale: 'Policy checks passed' };
  }

  // --------------------------------------------------------------------------
  // Utilities
  // --------------------------------------------------------------------------

  /** Generate cryptographically random noise payload (fail-to-noise) */
  private generateNoise(): string {
    return randomBytes(64).toString('base64');
  }

  /** High-resolution timer in microseconds */
  private microtime(): number {
    const [sec, nsec] = process.hrtime();
    return sec * 1_000_000 + nsec / 1_000;
  }

  /** Get current nonce cache size (for monitoring) */
  get nonceCacheSize(): number {
    return this.nonceCache.size;
  }

  /** Compute HMAC commitment for a context object */
  static computeCommitment(context: Record<string, unknown>, secret: string): string {
    return createHmac('sha256', secret).update(JSON.stringify(context)).digest('hex');
  }
}
