/**
 * @file codexTerminal.ts
 * @module game/codexTerminal
 * @layer Layer 1-14
 * @component Codex Terminal — SCBE-Gated Internet Access
 *
 * In-game Codex terminals provide real, limited internet access.
 * Every outbound request passes through the full SCBE 14-layer pipeline.
 *
 * In-world visualization:
 *   Green glow = ALLOW
 *   Yellow shimmer = QUARANTINE (limited, logged, slower)
 *   Red pulse + Polly warning = DENY
 *
 * A3: Causality — request ordering preserved.
 * A5: Composition — full pipeline integrity per request.
 */

import { RiskDecision, TongueVector, tongueNorm, GameEvent, DatasetTier } from './types.js';

// ---------------------------------------------------------------------------
//  Request Types
// ---------------------------------------------------------------------------

/** Categories of allowed codex queries */
export type CodexCategory =
  | 'math_reference' // Look up mathematical concepts
  | 'lore_wiki' // Browse in-world lore
  | 'creature_codex' // Companion/creature information
  | 'strategy_guide' // Gameplay strategies
  | 'visual_thermal' // Real-time data visualization
  | 'external_api'; // External API call (most restricted)

/** A codex terminal request */
export interface CodexRequest {
  readonly requestId: string;
  readonly timestamp: number;
  readonly category: CodexCategory;
  readonly query: string;
  readonly playerTongue: TongueVector;
  readonly playerFloor: number;
  readonly sessionDuration: number; // seconds since session start
}

/** Result of SCBE evaluation */
export interface CodexEvaluation {
  readonly requestId: string;
  readonly decision: RiskDecision;
  readonly scbeCost: number;
  readonly harmonicScore: number;
  readonly pipelineLayers: PipelineLayerResult[];
  readonly visualEffect: 'green_glow' | 'yellow_shimmer' | 'red_pulse';
  readonly pollyWarning: string | null;
  readonly rateLimitRemaining: number;
}

/** Individual pipeline layer result */
export interface PipelineLayerResult {
  readonly layer: number;
  readonly name: string;
  readonly score: number;
  readonly passed: boolean;
}

// ---------------------------------------------------------------------------
//  Rate Limiting
// ---------------------------------------------------------------------------

/** Per-category rate limits (requests per 10-minute window) */
const RATE_LIMITS: Record<CodexCategory, number> = {
  math_reference: 20,
  lore_wiki: 30,
  creature_codex: 30,
  strategy_guide: 15,
  visual_thermal: 5,
  external_api: 3,
};

/** Category risk weights */
const CATEGORY_RISK: Record<CodexCategory, number> = {
  math_reference: 0.1,
  lore_wiki: 0.05,
  creature_codex: 0.05,
  strategy_guide: 0.15,
  visual_thermal: 0.4,
  external_api: 0.8,
};

// ---------------------------------------------------------------------------
//  Codex Terminal State
// ---------------------------------------------------------------------------

export class CodexTerminal {
  private requestLog: CodexRequest[] = [];
  private windowStart: number = Date.now();
  private windowCounts: Map<CodexCategory, number> = new Map();

  /**
   * Evaluate a codex request through the SCBE 14-layer pipeline.
   *
   * This is the structural framework — in production, layers 1-14
   * would call the actual SCBE pipeline modules. Here we implement
   * the cost/risk logic that determines ALLOW/QUARANTINE/DENY.
   */
  evaluateRequest(request: CodexRequest): CodexEvaluation {
    // Reset window if expired (10 minutes)
    const now = Date.now();
    if (now - this.windowStart > 600_000) {
      this.windowStart = now;
      this.windowCounts.clear();
    }

    // Rate limit check
    const currentCount = this.windowCounts.get(request.category) ?? 0;
    const limit = RATE_LIMITS[request.category];
    const rateLimitRemaining = Math.max(0, limit - currentCount);

    if (rateLimitRemaining <= 0) {
      return this.buildDeny(request, 'Rate limit exceeded', 0);
    }

    // Run simplified 14-layer pipeline
    const layers = this.runPipeline(request);

    // Aggregate score
    const failedLayers = layers.filter((l) => !l.passed);
    const avgScore = layers.reduce((s, l) => s + l.score, 0) / layers.length;

    // L12: Harmonic score
    const categoryRisk = CATEGORY_RISK[request.category];
    const d = categoryRisk + failedLayers.length * 0.15;
    const pd = (1 - avgScore) * 0.5;
    const harmonicScore = 1 / (1 + d + 2 * pd);

    // L13: Decision
    let decision: RiskDecision;
    let visualEffect: 'green_glow' | 'yellow_shimmer' | 'red_pulse';
    let pollyWarning: string | null = null;

    if (harmonicScore > 0.7 && failedLayers.length === 0) {
      decision = 'ALLOW';
      visualEffect = 'green_glow';
    } else if (harmonicScore > 0.4) {
      decision = 'QUARANTINE';
      visualEffect = 'yellow_shimmer';
      pollyWarning = 'Polly ruffles her feathers. "Careful, that query feels... off."';
    } else {
      decision = 'DENY';
      visualEffect = 'red_pulse';
      pollyWarning = 'Polly screeches! "DENIED. That request would breach the ward."';
    }

    // Log the request
    this.requestLog.push(request);
    if (decision !== 'DENY') {
      this.windowCounts.set(request.category, currentCount + 1);
    }

    return {
      requestId: request.requestId,
      decision,
      scbeCost: d + pd,
      harmonicScore,
      pipelineLayers: layers,
      visualEffect,
      pollyWarning,
      rateLimitRemaining: rateLimitRemaining - (decision !== 'DENY' ? 1 : 0),
    };
  }

  /**
   * Simplified 14-layer pipeline evaluation.
   * Each layer produces a score (0-1) and pass/fail.
   */
  private runPipeline(request: CodexRequest): PipelineLayerResult[] {
    return [
      // L1-2: Context realization
      {
        layer: 1,
        name: 'Complex Context',
        score: this.scoreContext(request),
        passed: this.scoreContext(request) > 0.3,
      },
      {
        layer: 2,
        name: 'Realification',
        score: 0.9,
        passed: true,
      },
      // L3-4: Weighted transform + Poincaré embedding
      {
        layer: 3,
        name: 'Langues Metric',
        score: this.scoreTongueAlignment(request),
        passed: this.scoreTongueAlignment(request) > 0.2,
      },
      {
        layer: 4,
        name: 'Poincaré Embedding',
        score: 0.85,
        passed: true,
      },
      // L5: Hyperbolic distance
      {
        layer: 5,
        name: 'Hyperbolic Distance',
        score: this.scoreHyperbolicDistance(request),
        passed: this.scoreHyperbolicDistance(request) > 0.3,
      },
      // L6-7: Breathing transform + Möbius phase
      {
        layer: 6,
        name: 'Breathing Transform',
        score: 0.8,
        passed: true,
      },
      {
        layer: 7,
        name: 'Möbius Phase',
        score: 0.85,
        passed: true,
      },
      // L8: Hamiltonian CFI
      {
        layer: 8,
        name: 'Hamiltonian CFI',
        score: this.scoreCFI(request),
        passed: this.scoreCFI(request) > 0.5,
      },
      // L9-10: Spectral + spin coherence
      {
        layer: 9,
        name: 'Spectral Coherence',
        score: 0.9,
        passed: true,
      },
      {
        layer: 10,
        name: 'Spin Coherence',
        score: 0.88,
        passed: true,
      },
      // L11: Triadic temporal
      {
        layer: 11,
        name: 'Causality',
        score: this.scoreCausality(request),
        passed: this.scoreCausality(request) > 0.4,
      },
      // L12: Harmonic wall (computed in evaluateRequest)
      {
        layer: 12,
        name: 'Harmonic Wall',
        score: 0.75,
        passed: true,
      },
      // L13: Risk decision (computed in evaluateRequest)
      {
        layer: 13,
        name: 'Risk Decision',
        score: 0.8,
        passed: true,
      },
      // L14: Audio telemetry
      {
        layer: 14,
        name: 'Audio Axis',
        score: 1.0,
        passed: true,
      },
    ];
  }

  // -------------------------------------------------------------------------
  //  Layer Scoring Functions
  // -------------------------------------------------------------------------

  /** L1: Context score — based on query relevance to gameplay */
  private scoreContext(req: CodexRequest): number {
    // Higher score for categories that are core gameplay
    const contextScores: Record<CodexCategory, number> = {
      math_reference: 0.95,
      lore_wiki: 0.9,
      creature_codex: 0.9,
      strategy_guide: 0.7,
      visual_thermal: 0.5,
      external_api: 0.3,
    };
    return contextScores[req.category];
  }

  /** L3: Tongue alignment — does the player have governance rights? */
  private scoreTongueAlignment(req: CodexRequest): number {
    const norm = tongueNorm(req.playerTongue);
    // Higher tongue mastery = better alignment score
    return Math.min(1.0, norm * 1.5);
  }

  /** L5: Hyperbolic distance — how far is this request from safe center? */
  private scoreHyperbolicDistance(req: CodexRequest): number {
    const risk = CATEGORY_RISK[req.category];
    // Lower risk = higher score (closer to safe center)
    return 1.0 - risk;
  }

  /** L8: Control flow integrity — is this a valid request pattern? */
  private scoreCFI(req: CodexRequest): number {
    // Penalize rapid-fire requests (possible automation/exploit)
    const recentCount = this.requestLog.filter((r) => req.timestamp - r.timestamp < 10_000).length;
    return Math.max(0.1, 1.0 - recentCount * 0.15);
  }

  /** L11: Causality — does request order make sense? */
  private scoreCausality(req: CodexRequest): number {
    // External API without prior math_reference is suspicious
    if (req.category === 'external_api') {
      const hasRecentMath = this.requestLog.some(
        (r) => r.category === 'math_reference' && req.timestamp - r.timestamp < 300_000
      );
      return hasRecentMath ? 0.8 : 0.3;
    }
    return 0.9;
  }

  // -------------------------------------------------------------------------
  //  Utility
  // -------------------------------------------------------------------------

  private buildDeny(request: CodexRequest, reason: string, harmonicScore: number): CodexEvaluation {
    return {
      requestId: request.requestId,
      decision: 'DENY',
      scbeCost: 1.0,
      harmonicScore,
      pipelineLayers: [],
      visualEffect: 'red_pulse',
      pollyWarning: `Polly shakes her head. "${reason}"`,
      rateLimitRemaining: 0,
    };
  }

  /** Get request history (for training data export) */
  getRequestLog(): readonly CodexRequest[] {
    return this.requestLog;
  }

  /** Convert a request + evaluation to a game event for training pipeline */
  toGameEvent(request: CodexRequest, evaluation: CodexEvaluation, agentId: string): GameEvent {
    return {
      eventId: request.requestId,
      timestamp: request.timestamp,
      agentId,
      eventType: 'codex_query',
      data: {
        category: request.category,
        query: request.query,
        harmonicScore: evaluation.harmonicScore,
        layerScores: evaluation.pipelineLayers.map((l) => ({
          layer: l.layer,
          score: l.score,
        })),
      },
      scbeDecision: evaluation.decision,
      scbeCost: evaluation.scbeCost,
    };
  }
}
