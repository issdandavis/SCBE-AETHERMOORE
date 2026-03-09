/**
 * @file orderedRejection.unit.test.ts
 * @module tests/L2-unit
 * @layer Layer 13
 * @component Ordered Rejection Verification Pipeline + Quarantine Queue
 *
 * Tests:
 *   - Fail-fast stage ordering (cheap checks first)
 *   - Each rejection stage independently
 *   - QUARANTINE queue enqueue/release/deny
 *   - Backlog pressure relief mechanisms
 *   - Cohort batching for bulk review
 *   - Trust decay with auto-deny
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { OrderedRejectionPipeline, type RejectionRequest } from '../../src/api/orderedRejection';
import { QuarantineQueue } from '../../src/api/quarantineQueue';

// ============================================================================
// Helpers
// ============================================================================

function validRequest(overrides?: Partial<RejectionRequest>): RejectionRequest {
  return {
    clientTimestamp: new Date().toISOString(),
    nonce: `scbe-${Date.now()}-${Math.random().toString(36).slice(2)}`,
    trustScore: 0.7,
    actorId: 'test-actor',
    actorType: 'human',
    intent: 'read',
    resourceClassification: 'internal',
    ...overrides,
  };
}

// ============================================================================
// OrderedRejectionPipeline
// ============================================================================

describe('OrderedRejectionPipeline', () => {
  let pipeline: OrderedRejectionPipeline;

  beforeEach(() => {
    pipeline = new OrderedRejectionPipeline();
  });

  it('accepts a valid request through all stages', () => {
    const result = pipeline.verify(validRequest());
    expect(result.accepted).toBe(true);
    expect(result.rejectedAt).toBeNull();
    expect(result.noisePayload).toBeNull();
    expect(result.stages.length).toBe(6);
    expect(result.stages.every((s) => s.passed)).toBe(true);
  });

  describe('S0: Timestamp Skew', () => {
    it('rejects requests with extreme clock drift', () => {
      const result = pipeline.verify(
        validRequest({
          clientTimestamp: new Date(Date.now() - 120_000).toISOString(), // 2 min ago
        })
      );
      expect(result.accepted).toBe(false);
      expect(result.rejectedAt).toBe('S0_TIMESTAMP_SKEW');
      expect(result.stages.length).toBe(1); // Short-circuited
    });

    it('rejects requests with invalid timestamp format', () => {
      const result = pipeline.verify(validRequest({ clientTimestamp: 'not-a-date' }));
      expect(result.accepted).toBe(false);
      expect(result.rejectedAt).toBe('S0_TIMESTAMP_SKEW');
    });
  });

  describe('S1: Replay Guard', () => {
    it('rejects duplicate nonces', () => {
      const req = validRequest();
      pipeline.verify(req); // First use
      const result = pipeline.verify(req); // Replay
      expect(result.accepted).toBe(false);
      expect(result.rejectedAt).toBe('S1_REPLAY_GUARD');
    });
  });

  describe('S2: Nonce Prefix', () => {
    it('rejects nonces without required prefix', () => {
      const result = pipeline.verify(validRequest({ nonce: 'bad-nonce-no-prefix-12345' }));
      expect(result.accepted).toBe(false);
      expect(result.rejectedAt).toBe('S2_NONCE_PREFIX');
    });

    it('rejects nonces that are too short', () => {
      const result = pipeline.verify(validRequest({ nonce: 'scbe-short' }));
      expect(result.accepted).toBe(false);
      expect(result.rejectedAt).toBe('S2_NONCE_PREFIX');
    });
  });

  describe('S3: Context Commitment', () => {
    it('passes when no commitment is provided', () => {
      const result = pipeline.verify(validRequest());
      expect(result.accepted).toBe(true);
    });

    it('rejects mismatched HMAC commitment', () => {
      const result = pipeline.verify(
        validRequest({
          context: { key: 'value' },
          contextCommitment: 'badhash',
        })
      );
      expect(result.accepted).toBe(false);
      expect(result.rejectedAt).toBe('S3_CONTEXT_COMMITMENT');
    });

    it('validates correct HMAC commitment', () => {
      const context = { key: 'value' };
      const commitment = OrderedRejectionPipeline.computeCommitment(
        context,
        'scbe-ordered-rejection-default-key'
      );
      const result = pipeline.verify(
        validRequest({ context, contextCommitment: commitment })
      );
      expect(result.accepted).toBe(true);
    });
  });

  describe('S4: Trust Gate', () => {
    it('rejects low-trust actors', () => {
      const result = pipeline.verify(validRequest({ trustScore: 0.1 }));
      expect(result.accepted).toBe(false);
      expect(result.rejectedAt).toBe('S4_TRUST_GATE');
    });

    it('accepts actors above trust threshold', () => {
      const result = pipeline.verify(validRequest({ trustScore: 0.5 }));
      expect(result.accepted).toBe(true);
    });
  });

  describe('S5: Policy Evaluation', () => {
    it('rejects destructive intent from AI actors', () => {
      const result = pipeline.verify(
        validRequest({ intent: 'delete', actorType: 'ai' })
      );
      expect(result.accepted).toBe(false);
      expect(result.rejectedAt).toBe('S5_POLICY_EVAL');
    });

    it('allows destructive intent from human actors', () => {
      const result = pipeline.verify(
        validRequest({ intent: 'delete', actorType: 'human' })
      );
      expect(result.accepted).toBe(true);
    });

    it('rejects AI access to restricted resources', () => {
      const result = pipeline.verify(
        validRequest({
          actorType: 'ai',
          resourceClassification: 'restricted',
        })
      );
      expect(result.accepted).toBe(false);
      expect(result.rejectedAt).toBe('S5_POLICY_EVAL');
    });
  });

  describe('Fail-fast ordering', () => {
    it('rejects at cheapest failing stage even when multiple would fail', () => {
      // Both timestamp AND trust would fail, but timestamp is checked first
      const result = pipeline.verify(
        validRequest({
          clientTimestamp: new Date(Date.now() - 120_000).toISOString(),
          trustScore: 0.1,
        })
      );
      expect(result.rejectedAt).toBe('S0_TIMESTAMP_SKEW');
      expect(result.stages.length).toBe(1);
    });

    it('returns noise payload on rejection when failToNoise is enabled', () => {
      const result = pipeline.verify(validRequest({ trustScore: 0.1 }));
      expect(result.accepted).toBe(false);
      expect(result.noisePayload).not.toBeNull();
      expect(result.noisePayload!.length).toBeGreaterThan(0);
    });

    it('returns no noise payload when failToNoise is disabled', () => {
      const quietPipeline = new OrderedRejectionPipeline({ failToNoise: false });
      const result = quietPipeline.verify(validRequest({ trustScore: 0.1 }));
      expect(result.noisePayload).toBeNull();
    });
  });

  describe('Performance', () => {
    it('completes valid requests within reasonable time', () => {
      const result = pipeline.verify(validRequest());
      // The cheap stages should complete well under 1ms total
      expect(result.totalMicros).toBeLessThan(50_000); // 50ms generous bound
    });

    it('rejects faster than accepting (fail-fast property)', () => {
      const acceptResult = pipeline.verify(validRequest());
      const rejectResult = pipeline.verify(validRequest({ trustScore: 0.1 }));
      // Rejection should process fewer stages
      expect(rejectResult.stages.length).toBeLessThan(acceptResult.stages.length);
    });
  });
});

// ============================================================================
// QuarantineQueue
// ============================================================================

describe('QuarantineQueue', () => {
  let queue: QuarantineQueue;

  beforeEach(() => {
    queue = new QuarantineQueue({
      maxPending: 100,
      defaultTtlMs: 60_000,
      trustDecayPerSec: 0.01,
      autoDeNyTrustThreshold: 0.15,
      autoReleaseRateThreshold: 0.8,
      autoReleaseMaxRisk: 0.45,
      pressureThreshold: 0.7,
    });
  });

  describe('Enqueue & Retrieve', () => {
    it('enqueues an item and assigns priority', () => {
      const item = queue.enqueue({
        requestId: 'req-1',
        actorId: 'actor-1',
        intent: 'transfer',
        riskScore: 0.5,
        harmonicCost: 1.2,
        rationale: 'Marginal trust',
        trustScore: 0.4,
      });

      expect(item.id).toBeTruthy();
      expect(item.priority).toBe('medium');
      expect(item.resolution).toBeNull();
    });

    it('retrieves pending items sorted by priority', () => {
      queue.enqueue({
        requestId: 'r1',
        actorId: 'a1',
        intent: 'read',
        riskScore: 0.3,
        harmonicCost: 0.5,
        rationale: 'Low risk',
        trustScore: 0.4,
      });
      queue.enqueue({
        requestId: 'r2',
        actorId: 'a2',
        intent: 'write',
        riskScore: 0.8,
        harmonicCost: 3.0,
        rationale: 'High risk',
        trustScore: 0.35,
      });

      const pending = queue.getPending();
      expect(pending.length).toBe(2);
      expect(pending[0].riskScore).toBe(0.8); // Critical first
      expect(pending[1].riskScore).toBe(0.3); // Low second
    });
  });

  describe('Release & Deny', () => {
    it('releases an item', () => {
      const item = queue.enqueue({
        requestId: 'req-1',
        actorId: 'actor-1',
        intent: 'transfer',
        riskScore: 0.5,
        harmonicCost: 1.2,
        rationale: 'Test',
        trustScore: 0.4,
      });

      const released = queue.release(item.id, 'admin');
      expect(released).not.toBeNull();
      expect(released!.resolution).toBe('RELEASED');
      expect(released!.resolvedBy).toBe('admin');
      expect(queue.getPending().length).toBe(0);
    });

    it('denies an item', () => {
      const item = queue.enqueue({
        requestId: 'req-1',
        actorId: 'actor-1',
        intent: 'transfer',
        riskScore: 0.5,
        harmonicCost: 1.2,
        rationale: 'Test',
        trustScore: 0.4,
      });

      const denied = queue.deny(item.id, 'admin');
      expect(denied).not.toBeNull();
      expect(denied!.resolution).toBe('DENIED');
    });

    it('returns null for non-existent item', () => {
      expect(queue.release('nonexistent', 'admin')).toBeNull();
    });
  });

  describe('Cohort Batching', () => {
    it('groups items by intent + risk bucket into cohorts', () => {
      // Same intent, similar risk → same cohort
      const item1 = queue.enqueue({
        requestId: 'r1',
        actorId: 'a1',
        intent: 'transfer',
        riskScore: 0.45,
        harmonicCost: 1.0,
        rationale: 'Test',
        trustScore: 0.4,
      });
      const item2 = queue.enqueue({
        requestId: 'r2',
        actorId: 'a2',
        intent: 'transfer',
        riskScore: 0.42,
        harmonicCost: 1.1,
        rationale: 'Test',
        trustScore: 0.4,
      });
      // Same cohort key since both risk in [0.4, 0.5) bucket
      expect(item1.cohortKey).toBe(item2.cohortKey);
    });

    it('bulk-releases an entire cohort', () => {
      const item1 = queue.enqueue({
        requestId: 'r1',
        actorId: 'a1',
        intent: 'transfer',
        riskScore: 0.45,
        harmonicCost: 1.0,
        rationale: 'Test',
        trustScore: 0.4,
      });

      queue.enqueue({
        requestId: 'r2',
        actorId: 'a2',
        intent: 'transfer',
        riskScore: 0.42,
        harmonicCost: 1.1,
        rationale: 'Test',
        trustScore: 0.4,
      });

      const released = queue.releaseCohort(item1.cohortKey, 'admin');
      expect(released.length).toBe(2);
      expect(queue.getPending().length).toBe(0);
    });

    it('lists distinct cohorts', () => {
      queue.enqueue({
        requestId: 'r1',
        actorId: 'a1',
        intent: 'transfer',
        riskScore: 0.45,
        harmonicCost: 1.0,
        rationale: 'Test',
        trustScore: 0.4,
      });
      queue.enqueue({
        requestId: 'r2',
        actorId: 'a2',
        intent: 'delete',
        riskScore: 0.7,
        harmonicCost: 2.0,
        rationale: 'Test',
        trustScore: 0.35,
      });

      const cohorts = queue.listCohorts();
      expect(cohorts.length).toBe(2);
    });
  });

  describe('Trust Decay', () => {
    it('decays trust over time', () => {
      const item = queue.enqueue({
        requestId: 'r1',
        actorId: 'a1',
        intent: 'read',
        riskScore: 0.3,
        harmonicCost: 0.5,
        rationale: 'Test',
        trustScore: 0.4,
      });

      // Manually simulate time passage by adjusting enqueuedAt
      const retrieved = queue.getItem(item.id)!;
      // Set enqueue time to 20 seconds ago
      (retrieved as any).enqueuedAt = Date.now() - 20_000;

      queue.runMaintenance();

      const updated = queue.getItem(item.id);
      if (updated) {
        // Trust should have decayed: 0.4 - (0.01 * 20) = 0.2
        expect(updated.decayedTrust).toBeLessThan(item.trustAtEnqueue);
      }
    });
  });

  describe('Statistics', () => {
    it('reports accurate queue stats', () => {
      queue.enqueue({
        requestId: 'r1',
        actorId: 'a1',
        intent: 'read',
        riskScore: 0.3,
        harmonicCost: 0.5,
        rationale: 'Test',
        trustScore: 0.4,
      });
      queue.enqueue({
        requestId: 'r2',
        actorId: 'a2',
        intent: 'write',
        riskScore: 0.8,
        harmonicCost: 3.0,
        rationale: 'Test',
        trustScore: 0.35,
      });

      const stats = queue.getStats();
      expect(stats.pending).toBe(2);
      expect(stats.byPriority.low).toBe(1);
      expect(stats.byPriority.critical).toBe(1);
      expect(stats.pressure).toBe(2 / 100); // 2 items / maxPending 100
    });

    it('tracks release rate from resolved history', () => {
      // Enqueue and release 3 items
      for (let i = 0; i < 3; i++) {
        const item = queue.enqueue({
          requestId: `r${i}`,
          actorId: `a${i}`,
          intent: 'read',
          riskScore: 0.3,
          harmonicCost: 0.5,
          rationale: 'Test',
          trustScore: 0.4,
        });
        queue.release(item.id, 'admin');
      }

      // Enqueue and deny 1 item
      const denied = queue.enqueue({
        requestId: 'deny-1',
        actorId: 'a-deny',
        intent: 'write',
        riskScore: 0.6,
        harmonicCost: 2.0,
        rationale: 'Test',
        trustScore: 0.35,
      });
      queue.deny(denied.id, 'admin');

      const stats = queue.getStats();
      expect(stats.releaseRate).toBe(0.75); // 3 released / 4 total
    });
  });

  describe('Priority Assignment', () => {
    it('assigns correct priority bands', () => {
      const lowItem = queue.enqueue({
        requestId: 'r1',
        actorId: 'a1',
        intent: 'read',
        riskScore: 0.35,
        harmonicCost: 0.5,
        rationale: 'Test',
        trustScore: 0.4,
      });
      const medItem = queue.enqueue({
        requestId: 'r2',
        actorId: 'a2',
        intent: 'write',
        riskScore: 0.5,
        harmonicCost: 1.5,
        rationale: 'Test',
        trustScore: 0.4,
      });
      const highItem = queue.enqueue({
        requestId: 'r3',
        actorId: 'a3',
        intent: 'admin',
        riskScore: 0.6,
        harmonicCost: 2.0,
        rationale: 'Test',
        trustScore: 0.4,
      });
      const critItem = queue.enqueue({
        requestId: 'r4',
        actorId: 'a4',
        intent: 'escalate',
        riskScore: 0.75,
        harmonicCost: 4.0,
        rationale: 'Test',
        trustScore: 0.35,
      });

      expect(lowItem.priority).toBe('low');
      expect(medItem.priority).toBe('medium');
      expect(highItem.priority).toBe('high');
      expect(critItem.priority).toBe('critical');
    });
  });
});
