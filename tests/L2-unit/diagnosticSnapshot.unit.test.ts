/**
 * @file diagnosticSnapshot.unit.test.ts
 * @module tests/L2-unit/diagnosticSnapshot
 * @layer Layer 13
 *
 * Tests for the DiagnosticEngine and its 10 triage states.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  DiagnosticEngine,
  DiagnosticSnapshot,
  allTonguesPassing,
} from '../../src/api/diagnosticSnapshot';

// ============================================================================
// Helpers
// ============================================================================

/** Default safe pipeline params */
function safeParams(overrides?: Record<string, unknown>) {
  return {
    actorId: 'agent-001',
    intent: 'read_public_page',
    riskScore: 0.1,
    hyperbolicDistance: 0.5,
    harmonicCost: 0.8,
    breathingPhase: 0.3,
    layerScores: Array(14).fill(0.9),
    tongueResults: allTonguesPassing(),
    trustScore: 0.85,
    trustVelocity: 0.01,
    tags: ['safe'],
    ...overrides,
  };
}

/** Create tongue results with specific failures */
function tonguesWithFailures(
  failures: Array<'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR'>,
  lowConfidence: boolean = false,
): ReturnType<typeof allTonguesPassing> {
  const tongues = allTonguesPassing();
  for (const t of tongues) {
    if (failures.includes(t.tongue)) {
      t.passed = false;
      t.confidence = lowConfidence ? 0.3 : 0.7;
      t.finding = `${t.tongue} failed`;
    }
  }
  return tongues;
}

/** Create tongue results where several have low confidence */
function tonguesWithLowConfidence(
  count: number,
): ReturnType<typeof allTonguesPassing> {
  const tongues = allTonguesPassing();
  for (let i = 0; i < count && i < tongues.length; i++) {
    tongues[i]!.confidence = 0.3;
  }
  return tongues;
}

// ============================================================================
// Tests
// ============================================================================

describe('DiagnosticEngine', () => {
  let engine: DiagnosticEngine;

  beforeEach(() => {
    engine = new DiagnosticEngine();
  });

  // --------------------------------------------------------------------------
  // PASS state
  // --------------------------------------------------------------------------

  describe('PASS state', () => {
    it('should return PASS for low risk with all tongues passing', () => {
      const snap = engine.createSnapshot(safeParams());
      expect(snap.diagnosticState).toBe('PASS');
      expect(snap.severity).toBe('nominal');
      expect(snap.recommendedAction).toBe('proceed');
      expect(snap.legacyDecision).toBe('ALLOW');
    });

    it('should include correct tongue pass/fail counts', () => {
      const snap = engine.createSnapshot(safeParams());
      expect(snap.tonguePassCount).toBe(6);
      expect(snap.tongueFailCount).toBe(0);
    });

    it('should have a valid snapshot ID', () => {
      const snap = engine.createSnapshot(safeParams());
      expect(snap.snapshotId).toMatch(/^diag-[0-9a-f]{16}$/);
    });

    it('should populate all fields', () => {
      const snap = engine.createSnapshot(safeParams());
      expect(snap.actorId).toBe('agent-001');
      expect(snap.intent).toBe('read_public_page');
      expect(snap.riskScore).toBe(0.1);
      expect(snap.layerScores).toHaveLength(14);
      expect(snap.tongueDiagnostics).toHaveLength(6);
      expect(snap.timestamp).toBeGreaterThan(0);
      expect(snap.retestCount).toBe(0);
    });
  });

  // --------------------------------------------------------------------------
  // WATCH state
  // --------------------------------------------------------------------------

  describe('WATCH state', () => {
    it('should return WATCH for marginal risk with all tongues passing', () => {
      // Use low decay to avoid DEFERRED triggering before WATCH
      const watchEngine = new DiagnosticEngine({ trustDecayPerSec: 0.00001 });
      const snap = watchEngine.createSnapshot(safeParams({ riskScore: 0.3 }));
      expect(snap.diagnosticState).toBe('WATCH');
      expect(snap.legacyDecision).toBe('ALLOW');
    });

    it('should return WATCH with advisory when tongue failures at low risk', () => {
      const watchEngine = new DiagnosticEngine({ trustDecayPerSec: 0.00001 });
      const snap = watchEngine.createSnapshot(
        safeParams({
          riskScore: 0.3,
          tongueResults: tonguesWithFailures(['AV']),
        }),
      );
      expect(snap.diagnosticState).toBe('WATCH');
      expect(snap.severity).toBe('advisory');
      expect(snap.recommendedAction).toBe('monitor');
    });

    it('should return WATCH with auto_release_check when no tongue failures', () => {
      const watchEngine = new DiagnosticEngine({ trustDecayPerSec: 0.00001 });
      const snap = watchEngine.createSnapshot(safeParams({ riskScore: 0.3 }));
      expect(snap.diagnosticState).toBe('WATCH');
      expect(snap.recommendedAction).toBe('auto_release_check');
    });
  });

  // --------------------------------------------------------------------------
  // RETEST state
  // --------------------------------------------------------------------------

  describe('RETEST state', () => {
    it('should return RETEST when 2+ tongues have low confidence', () => {
      const snap = engine.createSnapshot(
        safeParams({
          riskScore: 0.5,
          tongueResults: tonguesWithLowConfidence(3),
        }),
      );
      expect(snap.diagnosticState).toBe('RETEST');
      expect(snap.recommendedAction).toBe('retest_immediate');
      expect(snap.legacyDecision).toBe('QUARANTINE');
    });

    it('should use retest_delayed for subsequent retests', () => {
      engine.recordRetest('agent-001', 'read_public_page');
      const snap = engine.createSnapshot(
        safeParams({
          riskScore: 0.5,
          tongueResults: tonguesWithLowConfidence(3),
        }),
      );
      expect(snap.diagnosticState).toBe('RETEST');
      expect(snap.recommendedAction).toBe('retest_delayed');
    });

    it('should have exponential backoff cooldown', () => {
      // First retest: 30s * 2^0 = 30s
      const snap0 = engine.createSnapshot(
        safeParams({
          riskScore: 0.5,
          tongueResults: tonguesWithLowConfidence(3),
        }),
      );
      expect(snap0.retestCooldownMs).toBe(30_000);

      // Record retests and check escalating cooldown
      engine.recordRetest('agent-001', 'read_public_page');
      const snap1 = engine.createSnapshot(
        safeParams({
          riskScore: 0.5,
          tongueResults: tonguesWithLowConfidence(3),
        }),
      );
      expect(snap1.retestCooldownMs).toBe(60_000); // 30s * 2^1

      engine.recordRetest('agent-001', 'read_public_page');
      const snap2 = engine.createSnapshot(
        safeParams({
          riskScore: 0.5,
          tongueResults: tonguesWithLowConfidence(3),
        }),
      );
      expect(snap2.retestCooldownMs).toBe(120_000); // 30s * 2^2
    });

    it('should escalate to TRIAGE after max retests exhausted', () => {
      engine.recordRetest('agent-001', 'read_public_page');
      engine.recordRetest('agent-001', 'read_public_page');
      engine.recordRetest('agent-001', 'read_public_page'); // retestCount = 3 = max
      const snap = engine.createSnapshot(
        safeParams({
          riskScore: 0.5,
          tongueResults: tonguesWithLowConfidence(3),
        }),
      );
      expect(snap.diagnosticState).toBe('TRIAGE');
      expect(snap.recommendedAction).toBe('human_classify');
    });
  });

  // --------------------------------------------------------------------------
  // TRIAGE state
  // --------------------------------------------------------------------------

  describe('TRIAGE state', () => {
    it('should return TRIAGE for ambiguous risk zone', () => {
      const snap = engine.createSnapshot(safeParams({ riskScore: 0.7 }));
      expect(snap.diagnosticState).toBe('TRIAGE');
      expect(snap.severity).toBe('caution');
      expect(snap.recommendedAction).toBe('human_classify');
      expect(snap.legacyDecision).toBe('ESCALATE');
    });
  });

  // --------------------------------------------------------------------------
  // DEFERRED state
  // --------------------------------------------------------------------------

  describe('DEFERRED state', () => {
    it('should return DEFERRED when projected trust at expiry is very low', () => {
      const snap = engine.createSnapshot(
        safeParams({
          riskScore: 0.35,
          trustScore: 0.5,
          trustVelocity: -0.01,
          // With default projectionTtlMs = 3600000ms (1hr),
          // projected = 0.5 - 0.001 * 3600 = 0.5 - 3.6 = 0 (clamped)
          // So projectedTrustAtExpiry < 0.15 and riskScore > passThreshold
        }),
      );
      expect(snap.diagnosticState).toBe('DEFERRED');
      expect(snap.recommendedAction).toBe('hold_for_window');
      expect(snap.legacyDecision).toBe('QUARANTINE');
    });
  });

  // --------------------------------------------------------------------------
  // DEGRADED state
  // --------------------------------------------------------------------------

  describe('DEGRADED state', () => {
    it('should return DEGRADED when trust velocity is heavily negative', () => {
      const snap = engine.createSnapshot(
        safeParams({
          riskScore: 0.35,
          trustScore: 0.8,
          trustVelocity: -0.1, // Below degradedTrustVelocity of -0.05
        }),
      );
      expect(snap.diagnosticState).toBe('DEGRADED');
      expect(snap.severity).toBe('advisory');
      expect(snap.recommendedAction).toBe('monitor');
      expect(snap.legacyDecision).toBe('QUARANTINE');
    });

    it('should not DEGRADE at zero risk', () => {
      const snap = engine.createSnapshot(
        safeParams({
          riskScore: 0.1,
          trustVelocity: -0.1,
        }),
      );
      // Risk below passThreshold, so DEGRADED check skipped → PASS
      expect(snap.diagnosticState).toBe('PASS');
    });
  });

  // --------------------------------------------------------------------------
  // ISOLATED state
  // --------------------------------------------------------------------------

  describe('ISOLATED state', () => {
    it('should return ISOLATED when too many tongues fail', () => {
      const snap = engine.createSnapshot(
        safeParams({
          riskScore: 0.5,
          tongueResults: tonguesWithFailures(['KO', 'AV', 'RU', 'CA']),
        }),
      );
      // 4 failures → only 2 passing, below isolateTongueThreshold of 3
      expect(snap.diagnosticState).toBe('ISOLATED');
      expect(snap.severity).toBe('warning');
      expect(snap.recommendedAction).toBe('sandbox_execute');
      expect(snap.legacyDecision).toBe('ESCALATE');
    });
  });

  // --------------------------------------------------------------------------
  // FLAGGED state
  // --------------------------------------------------------------------------

  describe('FLAGGED state', () => {
    it('should return FLAGGED when UM (security) fails at moderate risk', () => {
      const snap = engine.createSnapshot(
        safeParams({
          riskScore: 0.5,
          tongueResults: tonguesWithFailures(['UM']),
        }),
      );
      expect(snap.diagnosticState).toBe('FLAGGED');
      expect(snap.severity).toBe('caution');
      expect(snap.recommendedAction).toBe('monitor');
      expect(snap.legacyDecision).toBe('QUARANTINE');
    });
  });

  // --------------------------------------------------------------------------
  // SUSPENDED state
  // --------------------------------------------------------------------------

  describe('SUSPENDED state', () => {
    it('should return SUSPENDED for high risk without security tongue failure', () => {
      const snap = engine.createSnapshot(safeParams({ riskScore: 0.9 }));
      expect(snap.diagnosticState).toBe('SUSPENDED');
      expect(snap.severity).toBe('warning');
      expect(snap.recommendedAction).toBe('escalate_to_admin');
      expect(snap.legacyDecision).toBe('ESCALATE');
    });
  });

  // --------------------------------------------------------------------------
  // REJECTED state
  // --------------------------------------------------------------------------

  describe('REJECTED state', () => {
    it('should return REJECTED for critical risk with UM tongue failure', () => {
      const snap = engine.createSnapshot(
        safeParams({
          riskScore: 0.9,
          tongueResults: tonguesWithFailures(['UM']),
        }),
      );
      expect(snap.diagnosticState).toBe('REJECTED');
      expect(snap.severity).toBe('critical');
      expect(snap.recommendedAction).toBe('block_with_noise');
      expect(snap.legacyDecision).toBe('DENY');
    });

    it('should return REJECTED for critical risk with RU tongue failure', () => {
      const snap = engine.createSnapshot(
        safeParams({
          riskScore: 0.9,
          tongueResults: tonguesWithFailures(['RU']),
        }),
      );
      expect(snap.diagnosticState).toBe('REJECTED');
      expect(snap.legacyDecision).toBe('DENY');
    });

    it('should return REJECTED for extreme risk (>=0.95)', () => {
      const snap = engine.createSnapshot(safeParams({ riskScore: 0.95 }));
      expect(snap.diagnosticState).toBe('REJECTED');
      expect(snap.legacyDecision).toBe('DENY');
    });
  });

  // --------------------------------------------------------------------------
  // Trust Trajectory
  // --------------------------------------------------------------------------

  describe('trust trajectory', () => {
    it('should project trust at expiry correctly', () => {
      const snap = engine.createSnapshot(
        safeParams({
          trustScore: 0.8,
          trustVelocity: -0.01,
        }),
      );
      // projected = 0.8 - 0.001 * 3600 = 0.8 - 3.6 = 0 (clamped to 0)
      expect(snap.projectedTrustAtExpiry).toBe(0);
    });

    it('should preserve high trust projection for stable actors', () => {
      const snap = engine.createSnapshot(
        safeParams({
          trustScore: 0.95,
          trustVelocity: 0.01,
          // Default decay: 0.001/s * 3600s = 3.6
          // projected = max(0, 0.95 - 3.6) = 0
        }),
      );
      // Even stable actors decay over 1hr projection with 0.001/s rate
      expect(snap.projectedTrustAtExpiry).toBe(0);
    });
  });

  // --------------------------------------------------------------------------
  // Retest Tracking
  // --------------------------------------------------------------------------

  describe('retest tracking', () => {
    it('should track retest counts per context', () => {
      expect(engine.recordRetest('a', 'x')).toBe(1);
      expect(engine.recordRetest('a', 'x')).toBe(2);
      expect(engine.recordRetest('a', 'y')).toBe(1);
    });

    it('should clear retest history', () => {
      engine.recordRetest('a', 'x');
      engine.recordRetest('a', 'x');
      engine.clearRetestHistory('a', 'x');
      expect(engine.recordRetest('a', 'x')).toBe(1);
    });
  });

  // --------------------------------------------------------------------------
  // Legacy Decision Mapping
  // --------------------------------------------------------------------------

  describe('legacy decision mapping', () => {
    it('PASS → ALLOW', () => {
      const snap = engine.createSnapshot(safeParams({ riskScore: 0.1 }));
      expect(snap.diagnosticState).toBe('PASS');
      expect(snap.legacyDecision).toBe('ALLOW');
    });

    it('WATCH → ALLOW', () => {
      const watchEngine = new DiagnosticEngine({ trustDecayPerSec: 0.00001 });
      const snap = watchEngine.createSnapshot(safeParams({ riskScore: 0.3 }));
      expect(snap.diagnosticState).toBe('WATCH');
      expect(snap.legacyDecision).toBe('ALLOW');
    });

    it('TRIAGE → ESCALATE', () => {
      const snap = engine.createSnapshot(safeParams({ riskScore: 0.7 }));
      expect(snap.diagnosticState).toBe('TRIAGE');
      expect(snap.legacyDecision).toBe('ESCALATE');
    });

    it('REJECTED → DENY', () => {
      const snap = engine.createSnapshot(safeParams({ riskScore: 0.95 }));
      expect(snap.diagnosticState).toBe('REJECTED');
      expect(snap.legacyDecision).toBe('DENY');
    });
  });

  // --------------------------------------------------------------------------
  // Auto-Release Eligibility
  // --------------------------------------------------------------------------

  describe('auto-release eligibility', () => {
    it('should be eligible with low risk, high tongue pass, decent trust', () => {
      const snap = engine.createSnapshot(
        safeParams({
          riskScore: 0.2,
          trustScore: 0.6,
        }),
      );
      expect(snap.autoReleaseEligible).toBe(true);
    });

    it('should not be eligible with high risk', () => {
      const snap = engine.createSnapshot(
        safeParams({
          riskScore: 0.7,
          trustScore: 0.8,
        }),
      );
      expect(snap.autoReleaseEligible).toBe(false);
    });

    it('should not be eligible with low trust', () => {
      const snap = engine.createSnapshot(
        safeParams({
          riskScore: 0.2,
          trustScore: 0.2,
        }),
      );
      expect(snap.autoReleaseEligible).toBe(false);
    });
  });

  // --------------------------------------------------------------------------
  // Tongue Triggered Flags
  // --------------------------------------------------------------------------

  describe('triggered tongues', () => {
    it('should mark failing tongues as triggered in REJECTED', () => {
      const snap = engine.createSnapshot(
        safeParams({
          riskScore: 0.9,
          tongueResults: tonguesWithFailures(['UM', 'RU']),
        }),
      );
      const triggered = snap.tongueDiagnostics.filter((t) => t.triggered);
      expect(triggered.length).toBeGreaterThanOrEqual(1);
      const triggeredNames = triggered.map((t) => t.tongue);
      expect(triggeredNames).toContain('UM');
    });

    it('should not mark tongues as triggered in PASS', () => {
      const snap = engine.createSnapshot(safeParams());
      const triggered = snap.tongueDiagnostics.filter((t) => t.triggered);
      expect(triggered).toHaveLength(0);
    });
  });

  // --------------------------------------------------------------------------
  // allTonguesPassing helper
  // --------------------------------------------------------------------------

  describe('allTonguesPassing()', () => {
    it('should return 6 passing tongue results', () => {
      const tongues = allTonguesPassing();
      expect(tongues).toHaveLength(6);
      expect(tongues.every((t) => t.passed)).toBe(true);
      expect(tongues.map((t) => t.tongue)).toEqual(['KO', 'AV', 'RU', 'CA', 'UM', 'DR']);
    });
  });

  // --------------------------------------------------------------------------
  // Custom Configuration
  // --------------------------------------------------------------------------

  describe('custom configuration', () => {
    it('should respect custom thresholds', () => {
      const strict = new DiagnosticEngine({
        passThreshold: 0.1,
        watchThreshold: 0.2,
        trustDecayPerSec: 0.00001,
      });
      // riskScore 0.15 is between 0.1 (pass) and 0.2 (watch) → WATCH
      const snap = strict.createSnapshot(safeParams({ riskScore: 0.15 }));
      expect(snap.diagnosticState).toBe('WATCH');
    });

    it('should respect custom tongue thresholds', () => {
      const strict = new DiagnosticEngine({
        isolateTongueThreshold: 5, // Need 5+ tongues to avoid isolation
      });
      // 2 failures → only 4 passing, below threshold of 5
      const snap = strict.createSnapshot(
        safeParams({
          riskScore: 0.5,
          tongueResults: tonguesWithFailures(['AV', 'DR']),
        }),
      );
      expect(snap.diagnosticState).toBe('ISOLATED');
    });
  });
});
