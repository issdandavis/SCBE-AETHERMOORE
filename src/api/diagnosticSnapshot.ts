/**
 * @file diagnosticSnapshot.ts
 * @module api/diagnosticSnapshot
 * @layer Layer 13
 * @component Diagnostic Snapshot — Triage-Grade Decision States
 *
 * Extends the 4-tier decision model (ALLOW / QUARANTINE / ESCALATE / DENY)
 * with granular diagnostic triage states that capture *why* an item is in a
 * partial-trust zone and *what to do next*.
 *
 * Diagnostic states (ordered by urgency):
 *
 *   PASS       — Fully verified, no issues found
 *   WATCH      — Passed but with anomalies worth monitoring
 *   RETEST     — Inconclusive; re-run with fresh context
 *   TRIAGE     — Needs human classification (ambiguous risk)
 *   DEFERRED   — Intentionally postponed (e.g. off-hours, batch window)
 *   DEGRADED   — Partial capability loss, still functional
 *   ISOLATED   — Quarantined from swarm, can operate in sandbox
 *   FLAGGED    — Marked for audit trail, no block yet
 *   SUSPENDED  — Blocked pending review, auto-resumes if cleared
 *   REJECTED   — Hard deny with fail-to-noise
 *
 * Each diagnostic snapshot captures the full 14-layer pipeline state,
 * Sacred Tongue resonance, trust trajectory, and recommended next action.
 *
 * A3: Causality — snapshots are temporally ordered
 * A4: Symmetry — same inputs produce the same diagnostic
 * A5: Composition — snapshot composes pipeline + tongue + queue state
 */

import { createHash, randomBytes } from 'crypto';

// ============================================================================
// Diagnostic States
// ============================================================================

/**
 * Diagnostic triage states — granular replacement for binary pass/fail.
 *
 * Ordered from least to most severe. Each state implies an action.
 */
export type DiagnosticState =
  | 'PASS' // Fully verified
  | 'WATCH' // Pass with anomaly monitoring
  | 'RETEST' // Re-run with fresh context
  | 'TRIAGE' // Human classification needed
  | 'DEFERRED' // Intentionally postponed
  | 'DEGRADED' // Partial capability, still functional
  | 'ISOLATED' // Sandbox-only operation
  | 'FLAGGED' // Audit trail marker, no block
  | 'SUSPENDED' // Blocked pending review
  | 'REJECTED'; // Hard deny

/** Severity level for the diagnostic */
export type DiagnosticSeverity = 'nominal' | 'advisory' | 'caution' | 'warning' | 'critical';

/** Recommended next action for a diagnostic state */
export type RecommendedAction =
  | 'proceed' // Continue normally
  | 'monitor' // Continue but log enhanced telemetry
  | 'retest_immediate' // Retry the check with fresh data
  | 'retest_delayed' // Retry after a cooldown period
  | 'human_classify' // Route to human reviewer for classification
  | 'batch_review' // Group with similar items for bulk review
  | 'sandbox_execute' // Allow in sandboxed environment only
  | 'hold_for_window' // Wait for appropriate processing window
  | 'escalate_to_admin' // Escalate to security admin
  | 'block_with_noise' // Hard block with fail-to-noise payload
  | 'auto_release_check'; // Check if auto-release conditions are met

// ============================================================================
// Tongue Diagnostic
// ============================================================================

/** Per-tongue diagnostic detail */
export interface TongueDiagnostic {
  /** Tongue code */
  tongue: 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';
  /** Pass/fail for this tongue */
  passed: boolean;
  /** Confidence in this tongue's evaluation [0,1] */
  confidence: number;
  /** Specific finding for this tongue */
  finding: string;
  /** Whether this tongue triggered the diagnostic state */
  triggered: boolean;
}

// ============================================================================
// Diagnostic Snapshot
// ============================================================================

/** Complete diagnostic snapshot of a pipeline evaluation */
export interface DiagnosticSnapshot {
  /** Unique snapshot ID */
  snapshotId: string;
  /** Timestamp of snapshot creation */
  timestamp: number;

  // --- Decision ---
  /** Legacy 4-tier decision (for backward compatibility) */
  legacyDecision: 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY';
  /** Granular diagnostic state */
  diagnosticState: DiagnosticState;
  /** Severity level */
  severity: DiagnosticSeverity;
  /** Recommended next action */
  recommendedAction: RecommendedAction;

  // --- Pipeline State ---
  /** Risk score [0, 1] */
  riskScore: number;
  /** Hyperbolic distance from safe origin */
  hyperbolicDistance: number;
  /** Harmonic wall cost (Layer 12) */
  harmonicCost: number;
  /** Breathing phase at evaluation time */
  breathingPhase: number;
  /** Per-layer scores (L1-L14) */
  layerScores: number[];

  // --- Sacred Tongue Resonance ---
  /** Per-tongue diagnostic details */
  tongueDiagnostics: TongueDiagnostic[];
  /** Count of tongues passing */
  tonguePassCount: number;
  /** Count of tongues failing */
  tongueFailCount: number;

  // --- Trust Trajectory ---
  /** Current trust score */
  trustScore: number;
  /** Trust velocity (positive = improving, negative = degrading) */
  trustVelocity: number;
  /** Projected trust at TTL expiry */
  projectedTrustAtExpiry: number;

  // --- Context ---
  /** Actor ID */
  actorId: string;
  /** Intent */
  intent: string;
  /** Human-readable explanation */
  explanation: string;
  /** Tags for categorization */
  tags: string[];

  // --- Retest Metadata ---
  /** How many times this item has been tested */
  retestCount: number;
  /** Cooldown before next retest (ms, 0 if immediate) */
  retestCooldownMs: number;
  /** Whether auto-release conditions could apply */
  autoReleaseEligible: boolean;
}

// ============================================================================
// Diagnostic Engine
// ============================================================================

/** Configuration for the diagnostic engine */
export interface DiagnosticConfig {
  /** Risk threshold for PASS (below = PASS) */
  passThreshold: number;
  /** Risk threshold for WATCH (below = WATCH) */
  watchThreshold: number;
  /** Risk threshold for TRIAGE (below = TRIAGE) */
  triageThreshold: number;
  /** Risk threshold for SUSPENDED (below = SUSPENDED, above = REJECTED) */
  suspendedThreshold: number;
  /** Minimum tongue pass count for PASS state */
  minTonguesForPass: number;
  /** Tongue pass count below which we ISOLATE */
  isolateTongueThreshold: number;
  /** Trust velocity below which we flag DEGRADED */
  degradedTrustVelocity: number;
  /** Max retests before forcing TRIAGE */
  maxRetestsBeforeTriage: number;
  /** Cooldown between retests (ms) */
  retestCooldownMs: number;
  /** Trust decay rate per second (for projection) */
  trustDecayPerSec: number;
  /** TTL for projection (ms) */
  projectionTtlMs: number;
}

const DEFAULT_CONFIG: DiagnosticConfig = {
  passThreshold: 0.25,
  watchThreshold: 0.4,
  triageThreshold: 0.65,
  suspendedThreshold: 0.85,
  minTonguesForPass: 6,
  isolateTongueThreshold: 3,
  degradedTrustVelocity: -0.05,
  maxRetestsBeforeTriage: 3,
  retestCooldownMs: 30_000,
  trustDecayPerSec: 0.001,
  projectionTtlMs: 60 * 60 * 1000,
};

/**
 * Diagnostic Engine — classifies pipeline evaluations into triage states.
 *
 * Replaces the flat ALLOW/QUARANTINE/ESCALATE/DENY model with a
 * diagnostic snapshot that tells reviewers exactly what happened,
 * why, and what to do next.
 */
export class DiagnosticEngine {
  private readonly config: DiagnosticConfig;
  private readonly retestHistory: Map<string, number> = new Map();

  constructor(config?: Partial<DiagnosticConfig>) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Create a diagnostic snapshot from pipeline evaluation data.
   */
  createSnapshot(params: {
    actorId: string;
    intent: string;
    riskScore: number;
    hyperbolicDistance: number;
    harmonicCost: number;
    breathingPhase: number;
    layerScores: number[];
    tongueResults: Array<{
      tongue: 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';
      passed: boolean;
      confidence: number;
      finding: string;
    }>;
    trustScore: number;
    trustVelocity: number;
    tags?: string[];
  }): DiagnosticSnapshot {
    const {
      actorId,
      intent,
      riskScore,
      hyperbolicDistance,
      harmonicCost,
      breathingPhase,
      layerScores,
      tongueResults,
      trustScore,
      trustVelocity,
      tags = [],
    } = params;

    // Build tongue diagnostics
    const tongueDiagnostics: TongueDiagnostic[] = tongueResults.map((t) => ({
      ...t,
      triggered: false, // Will be set below
    }));

    const tonguePassCount = tongueDiagnostics.filter((t) => t.passed).length;
    const tongueFailCount = tongueDiagnostics.filter((t) => !t.passed).length;

    // Track retest count
    const contextKey = this.contextKey(actorId, intent);
    const retestCount = this.retestHistory.get(contextKey) ?? 0;

    // Project trust at TTL expiry
    const projectedTrustAtExpiry = Math.max(
      0,
      trustScore - this.config.trustDecayPerSec * (this.config.projectionTtlMs / 1000)
    );

    // Classify diagnostic state
    const { state, severity, action, explanation, triggeredTongues } = this.classify({
      riskScore,
      tonguePassCount,
      tongueFailCount,
      tongueDiagnostics,
      trustScore,
      trustVelocity,
      retestCount,
      harmonicCost,
      projectedTrustAtExpiry,
    });

    // Mark triggered tongues
    for (const idx of triggeredTongues) {
      if (tongueDiagnostics[idx]) {
        tongueDiagnostics[idx]!.triggered = true;
      }
    }

    // Map to legacy decision
    const legacyDecision = this.toLegacyDecision(state);

    // Auto-release eligibility
    const autoReleaseEligible =
      riskScore < this.config.watchThreshold && tonguePassCount >= 5 && trustScore > 0.4;

    // Retest cooldown
    const retestCooldownMs =
      state === 'RETEST' ? this.config.retestCooldownMs * Math.pow(2, retestCount) : 0;

    const snapshot: DiagnosticSnapshot = {
      snapshotId: this.generateSnapshotId(actorId, intent),
      timestamp: Date.now(),
      legacyDecision,
      diagnosticState: state,
      severity,
      recommendedAction: action,
      riskScore,
      hyperbolicDistance,
      harmonicCost,
      breathingPhase,
      layerScores,
      tongueDiagnostics,
      tonguePassCount,
      tongueFailCount,
      trustScore,
      trustVelocity,
      projectedTrustAtExpiry,
      actorId,
      intent,
      explanation,
      tags,
      retestCount,
      retestCooldownMs,
      autoReleaseEligible,
    };

    return snapshot;
  }

  /**
   * Record a retest for a given actor+intent context.
   */
  recordRetest(actorId: string, intent: string): number {
    const key = this.contextKey(actorId, intent);
    const count = (this.retestHistory.get(key) ?? 0) + 1;
    this.retestHistory.set(key, count);
    return count;
  }

  /**
   * Clear retest history for a context (e.g. after resolution).
   */
  clearRetestHistory(actorId: string, intent: string): void {
    this.retestHistory.delete(this.contextKey(actorId, intent));
  }

  // --------------------------------------------------------------------------
  // Classification Logic
  // --------------------------------------------------------------------------

  private classify(params: {
    riskScore: number;
    tonguePassCount: number;
    tongueFailCount: number;
    tongueDiagnostics: TongueDiagnostic[];
    trustScore: number;
    trustVelocity: number;
    retestCount: number;
    harmonicCost: number;
    projectedTrustAtExpiry: number;
  }): {
    state: DiagnosticState;
    severity: DiagnosticSeverity;
    action: RecommendedAction;
    explanation: string;
    triggeredTongues: number[];
  } {
    const {
      riskScore,
      tonguePassCount,
      tongueFailCount,
      tongueDiagnostics,
      trustScore,
      trustVelocity,
      retestCount,
      harmonicCost,
      projectedTrustAtExpiry,
    } = params;

    // Find failing tongue indices
    const failingTongueIndices = tongueDiagnostics
      .map((t, i) => (!t.passed ? i : -1))
      .filter((i) => i >= 0);

    // Check for critical tongue failures (UM = Security, index 4)
    const umFailed = tongueDiagnostics[4] && !tongueDiagnostics[4].passed;
    const ruFailed = tongueDiagnostics[2] && !tongueDiagnostics[2].passed;

    // ── REJECTED: Critical security violations ──
    if (riskScore >= this.config.suspendedThreshold && (umFailed || ruFailed)) {
      return {
        state: 'REJECTED',
        severity: 'critical',
        action: 'block_with_noise',
        explanation: `Critical risk (${riskScore.toFixed(3)}) with security tongue failure`,
        triggeredTongues: failingTongueIndices,
      };
    }

    // ── REJECTED: Extreme risk ──
    if (riskScore >= 0.95) {
      return {
        state: 'REJECTED',
        severity: 'critical',
        action: 'block_with_noise',
        explanation: `Extreme risk score ${riskScore.toFixed(3)}`,
        triggeredTongues: failingTongueIndices,
      };
    }

    // ── SUSPENDED: High risk, pending review ──
    if (riskScore >= this.config.suspendedThreshold) {
      return {
        state: 'SUSPENDED',
        severity: 'warning',
        action: 'escalate_to_admin',
        explanation: `Risk ${riskScore.toFixed(3)} exceeds suspension threshold`,
        triggeredTongues: failingTongueIndices,
      };
    }

    // ── ISOLATED: Too many tongue failures — sandbox only ──
    if (tonguePassCount <= this.config.isolateTongueThreshold) {
      return {
        state: 'ISOLATED',
        severity: 'warning',
        action: 'sandbox_execute',
        explanation: `Only ${tonguePassCount}/6 tongues passing — sandbox isolation required`,
        triggeredTongues: failingTongueIndices,
      };
    }

    // ── FLAGGED: UM (security) tongue failed but risk is moderate ──
    if (umFailed && riskScore < this.config.triageThreshold) {
      return {
        state: 'FLAGGED',
        severity: 'caution',
        action: 'monitor',
        explanation: `Security tongue (UM) failed at moderate risk — flagged for audit`,
        triggeredTongues: failingTongueIndices,
      };
    }

    // ── RETEST: Inconclusive or low-confidence tongues ──
    const lowConfidenceTongues = tongueDiagnostics.filter((t) => t.confidence < 0.5);
    if (lowConfidenceTongues.length >= 2 && retestCount < this.config.maxRetestsBeforeTriage) {
      return {
        state: 'RETEST',
        severity: 'advisory',
        action: retestCount === 0 ? 'retest_immediate' : 'retest_delayed',
        explanation: `${lowConfidenceTongues.length} tongues with low confidence — retest #${retestCount + 1}`,
        triggeredTongues: tongueDiagnostics
          .map((t, i) => (t.confidence < 0.5 ? i : -1))
          .filter((i) => i >= 0),
      };
    }

    // ── TRIAGE: Ambiguous risk zone or max retests exhausted ──
    if (
      riskScore >= this.config.triageThreshold ||
      retestCount >= this.config.maxRetestsBeforeTriage
    ) {
      return {
        state: 'TRIAGE',
        severity: 'caution',
        action: 'human_classify',
        explanation:
          retestCount >= this.config.maxRetestsBeforeTriage
            ? `Max retests (${retestCount}) exhausted — human classification required`
            : `Risk ${riskScore.toFixed(3)} in triage zone [${this.config.watchThreshold}, ${this.config.suspendedThreshold})`,
        triggeredTongues: failingTongueIndices,
      };
    }

    // ── DEGRADED: Trust trajectory is deteriorating ──
    if (
      trustVelocity < this.config.degradedTrustVelocity &&
      riskScore > this.config.passThreshold
    ) {
      return {
        state: 'DEGRADED',
        severity: 'advisory',
        action: 'monitor',
        explanation: `Trust velocity ${trustVelocity.toFixed(4)}/s indicates degradation`,
        triggeredTongues: [],
      };
    }

    // ── DEFERRED: Projected trust will exhaust before TTL ──
    if (projectedTrustAtExpiry < 0.15 && riskScore > this.config.passThreshold) {
      return {
        state: 'DEFERRED',
        severity: 'advisory',
        action: 'hold_for_window',
        explanation: `Projected trust at expiry: ${projectedTrustAtExpiry.toFixed(3)} — deferring`,
        triggeredTongues: [],
      };
    }

    // ── WATCH: Low risk but with some tongue failures or anomalies ──
    if (riskScore >= this.config.passThreshold && riskScore < this.config.watchThreshold) {
      if (tongueFailCount > 0) {
        return {
          state: 'WATCH',
          severity: 'advisory',
          action: 'monitor',
          explanation: `Low risk (${riskScore.toFixed(3)}) with ${tongueFailCount} tongue anomaly — monitoring`,
          triggeredTongues: failingTongueIndices,
        };
      }
      return {
        state: 'WATCH',
        severity: 'nominal',
        action: 'auto_release_check',
        explanation: `Marginal risk (${riskScore.toFixed(3)}) — watching with auto-release check`,
        triggeredTongues: [],
      };
    }

    // ── PASS: Fully verified ──
    if (tonguePassCount >= this.config.minTonguesForPass) {
      return {
        state: 'PASS',
        severity: 'nominal',
        action: 'proceed',
        explanation: `All checks passed (risk=${riskScore.toFixed(3)}, ${tonguePassCount}/6 tongues)`,
        triggeredTongues: [],
      };
    }

    // Fallback: WATCH if tongues not fully passing but risk is low
    return {
      state: 'WATCH',
      severity: 'advisory',
      action: 'monitor',
      explanation: `Low risk but ${tongueFailCount} tongue(s) not passing — monitoring`,
      triggeredTongues: failingTongueIndices,
    };
  }

  // --------------------------------------------------------------------------
  // Helpers
  // --------------------------------------------------------------------------

  /** Map diagnostic state to legacy 4-tier decision */
  private toLegacyDecision(state: DiagnosticState): 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY' {
    switch (state) {
      case 'PASS':
      case 'WATCH':
        return 'ALLOW';
      case 'RETEST':
      case 'DEFERRED':
      case 'DEGRADED':
      case 'FLAGGED':
        return 'QUARANTINE';
      case 'TRIAGE':
      case 'ISOLATED':
      case 'SUSPENDED':
        return 'ESCALATE';
      case 'REJECTED':
        return 'DENY';
    }
  }

  /** Generate deterministic snapshot ID */
  private generateSnapshotId(actorId: string, intent: string): string {
    const hash = createHash('sha256')
      .update(`${actorId}:${intent}:${Date.now()}:${randomBytes(16).toString('hex')}`)
      .digest('hex')
      .slice(0, 16);
    return `diag-${hash}`;
  }

  /** Build context key for retest tracking */
  private contextKey(actorId: string, intent: string): string {
    return `${actorId}::${intent}`;
  }
}

// ============================================================================
// Convenience: Full Tongue Set Helper
// ============================================================================

/** Create a full set of passing tongue results (for testing / defaults) */
export function allTonguesPassing(): Array<{
  tongue: 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';
  passed: boolean;
  confidence: number;
  finding: string;
}> {
  return [
    { tongue: 'KO', passed: true, confidence: 0.95, finding: 'Control flow valid' },
    { tongue: 'AV', passed: true, confidence: 0.9, finding: 'I/O safe' },
    { tongue: 'RU', passed: true, confidence: 0.92, finding: 'Policy compliant' },
    { tongue: 'CA', passed: true, confidence: 0.88, finding: 'Logic sound' },
    { tongue: 'UM', passed: true, confidence: 0.95, finding: 'Secure connection' },
    { tongue: 'DR', passed: true, confidence: 0.91, finding: 'Type safe' },
  ];
}
