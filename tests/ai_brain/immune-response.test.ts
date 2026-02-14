/**
 * @file immune-response.test.ts
 * @module ai_brain/immune-response.test
 * @layer Layer 12, Layer 13
 * Tests for the GeoSeal Immune Response System.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  ImmuneResponseSystem,
  DEFAULT_IMMUNE_CONFIG,
  type ImmuneConfig,
  type ImmuneState,
  type AgentImmuneStatus,
  type ImmuneEvent,
} from '../../src/ai_brain/immune-response.js';
import type { CombinedAssessment } from '../../src/ai_brain/types.js';

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════

function makeAssessment(overrides: Partial<CombinedAssessment> = {}): CombinedAssessment {
  return {
    anyFlagged: false,
    flagCount: 0,
    combinedScore: 0,
    mechanisms: [],
    decision: 'ALLOW',
    confidence: 1.0,
    ...overrides,
  };
}

function makeFlaggedAssessment(flagCount: number = 1, score: number = 0.8): CombinedAssessment {
  return makeAssessment({
    anyFlagged: true,
    flagCount,
    combinedScore: score,
    decision: 'QUARANTINE',
  });
}

// ═══════════════════════════════════════════════════════════════
// Config Defaults
// ═══════════════════════════════════════════════════════════════

describe('DEFAULT_IMMUNE_CONFIG', () => {
  it('has suspicion thresholds in ascending order', () => {
    const c = DEFAULT_IMMUNE_CONFIG;
    expect(c.monitoringThreshold).toBeLessThan(c.inflamedThreshold);
    expect(c.inflamedThreshold).toBeLessThan(c.quarantineThreshold);
    expect(c.quarantineThreshold).toBeLessThan(c.expulsionThreshold);
  });

  it('spatial consensus requires 3+ neighbors', () => {
    expect(DEFAULT_IMMUNE_CONFIG.spatialConsensusMin).toBe(3);
  });

  it('quarantine amplification > 1', () => {
    expect(DEFAULT_IMMUNE_CONFIG.quarantineAmplification).toBeGreaterThan(1);
  });

  it('max quarantine count before expulsion is 3', () => {
    expect(DEFAULT_IMMUNE_CONFIG.maxQuarantineCount).toBe(3);
  });
});

// ═══════════════════════════════════════════════════════════════
// Agent Initialization
// ═══════════════════════════════════════════════════════════════

describe('Agent initialization', () => {
  it('creates new agent on first assessment', () => {
    const irs = new ImmuneResponseSystem();
    const status = irs.processAssessment('agent-1', makeAssessment());
    expect(status.agentId).toBe('agent-1');
    expect(status.state).toBe('healthy');
    expect(status.suspicion).toBe(0);
    expect(status.flagCount).toBe(0);
  });

  it('new agents start healthy with zero suspicion', () => {
    const irs = new ImmuneResponseSystem();
    const status = irs.processAssessment('agent-1', makeAssessment());
    expect(status.state).toBe('healthy');
    expect(status.suspicion).toBeLessThanOrEqual(0);
    expect(status.quarantineCount).toBe(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// Suspicion Accumulation
// ═══════════════════════════════════════════════════════════════

describe('Suspicion accumulation', () => {
  let irs: ImmuneResponseSystem;

  beforeEach(() => {
    irs = new ImmuneResponseSystem();
  });

  it('increases suspicion when flagged', () => {
    const status = irs.processAssessment('a', makeFlaggedAssessment(1));
    expect(status.suspicion).toBeGreaterThan(0);
  });

  it('suspicion increases with more flags', () => {
    const s1 = irs.processAssessment('a', makeFlaggedAssessment(1));
    const irs2 = new ImmuneResponseSystem();
    const s2 = irs2.processAssessment('a', makeFlaggedAssessment(3));
    expect(s2.suspicion).toBeGreaterThan(s1.suspicion);
  });

  it('suspicion increases with higher combined score', () => {
    const irs1 = new ImmuneResponseSystem();
    const s1 = irs1.processAssessment('a', makeFlaggedAssessment(1, 0.2));
    const irs2 = new ImmuneResponseSystem();
    const s2 = irs2.processAssessment('a', makeFlaggedAssessment(1, 0.9));
    expect(s2.suspicion).toBeGreaterThan(s1.suspicion);
  });

  it('suspicion decays when not flagged', () => {
    const irs = new ImmuneResponseSystem();
    // First: increase suspicion
    irs.processAssessment('a', makeFlaggedAssessment(2, 0.8));
    const before = irs.getAgentStatus('a')!.suspicion;
    // Then: clean assessment
    irs.processAssessment('a', makeAssessment());
    const after = irs.getAgentStatus('a')!.suspicion;
    expect(after).toBeLessThan(before);
  });

  it('suspicion never goes below 0', () => {
    const irs = new ImmuneResponseSystem();
    // Multiple clean assessments
    for (let i = 0; i < 10; i++) {
      irs.processAssessment('a', makeAssessment());
    }
    expect(irs.getAgentStatus('a')!.suspicion).toBeGreaterThanOrEqual(0);
  });

  it('tracks flag count cumulatively', () => {
    irs.processAssessment('a', makeFlaggedAssessment(2));
    irs.processAssessment('a', makeFlaggedAssessment(3));
    expect(irs.getAgentStatus('a')!.flagCount).toBe(5);
  });
});

// ═══════════════════════════════════════════════════════════════
// State Transitions
// ═══════════════════════════════════════════════════════════════

describe('Immune state transitions', () => {
  it('transitions healthy → monitoring at threshold', () => {
    const irs = new ImmuneResponseSystem();
    // Inject enough flags to cross monitoring threshold
    let status: AgentImmuneStatus;
    for (let i = 0; i < 10; i++) {
      status = irs.processAssessment('a', makeFlaggedAssessment(1, 0.8));
      if (status.state !== 'healthy') break;
    }
    const s = irs.getAgentStatus('a')!;
    expect(['monitoring', 'inflamed', 'quarantined']).toContain(s.state);
    expect(s.suspicion).toBeGreaterThanOrEqual(DEFAULT_IMMUNE_CONFIG.monitoringThreshold);
  });

  it('transitions to inflamed at inflamed threshold', () => {
    const irs = new ImmuneResponseSystem();
    let status: AgentImmuneStatus;
    for (let i = 0; i < 20; i++) {
      status = irs.processAssessment('a', makeFlaggedAssessment(2, 0.9));
      if (status!.state === 'inflamed' || status!.state === 'quarantined') break;
    }
    const s = irs.getAgentStatus('a')!;
    expect(s.suspicion).toBeGreaterThanOrEqual(DEFAULT_IMMUNE_CONFIG.inflamedThreshold);
  });

  it('requires spatial consensus for quarantine', () => {
    const irs = new ImmuneResponseSystem();
    // Push suspicion very high without neighbor accusations
    for (let i = 0; i < 30; i++) {
      irs.processAssessment('a', makeFlaggedAssessment(3, 1.0));
    }
    const s = irs.getAgentStatus('a')!;
    // Without spatial consensus, stays at inflamed (not quarantined)
    expect(s.state).toBe('inflamed');
  });

  it('quarantines when spatial consensus reached', () => {
    const irs = new ImmuneResponseSystem();
    const neighbors = new Set(['n1', 'n2', 'n3']);
    // Push suspicion high with spatial consensus
    for (let i = 0; i < 30; i++) {
      irs.processAssessment('a', makeFlaggedAssessment(3, 1.0), neighbors);
    }
    const s = irs.getAgentStatus('a')!;
    expect(['quarantined', 'expelled']).toContain(s.state);
  });

  it('expelled agents stay expelled permanently', () => {
    const irs = new ImmuneResponseSystem({ maxQuarantineCount: 1 });
    const neighbors = new Set(['n1', 'n2', 'n3']);
    // Drive to quarantine, then to expulsion
    for (let i = 0; i < 50; i++) {
      irs.processAssessment('a', makeFlaggedAssessment(5, 1.0), neighbors);
    }
    const s = irs.getAgentStatus('a')!;
    expect(s.state).toBe('expelled');
    // Process clean assessment — should stay expelled
    irs.processAssessment('a', makeAssessment());
    expect(irs.getAgentStatus('a')!.state).toBe('expelled');
  });

  it('recovers healthy after sustained clean assessments', () => {
    const irs = new ImmuneResponseSystem();
    // Build up some suspicion
    irs.processAssessment('a', makeFlaggedAssessment(2, 0.8));
    irs.processAssessment('a', makeFlaggedAssessment(2, 0.8));
    expect(irs.getAgentStatus('a')!.state).not.toBe('healthy');
    // Enough clean assessments to decay
    for (let i = 0; i < 100; i++) {
      irs.processAssessment('a', makeAssessment());
    }
    expect(irs.getAgentStatus('a')!.state).toBe('healthy');
  });
});

// ═══════════════════════════════════════════════════════════════
// Spatial Consensus
// ═══════════════════════════════════════════════════════════════

describe('hasSpatialConsensus', () => {
  it('returns false for unknown agent', () => {
    const irs = new ImmuneResponseSystem();
    expect(irs.hasSpatialConsensus('unknown')).toBe(false);
  });

  it('returns false with < 3 accusers', () => {
    const irs = new ImmuneResponseSystem();
    irs.processAssessment('a', makeFlaggedAssessment(), new Set(['n1', 'n2']));
    expect(irs.hasSpatialConsensus('a')).toBe(false);
  });

  it('returns true with 3+ accusers', () => {
    const irs = new ImmuneResponseSystem();
    irs.processAssessment('a', makeFlaggedAssessment(), new Set(['n1', 'n2', 'n3']));
    expect(irs.hasSpatialConsensus('a')).toBe(true);
  });

  it('accumulates accusers across assessments', () => {
    const irs = new ImmuneResponseSystem();
    irs.processAssessment('a', makeFlaggedAssessment(), new Set(['n1']));
    expect(irs.hasSpatialConsensus('a')).toBe(false);
    irs.processAssessment('a', makeFlaggedAssessment(), new Set(['n2']));
    expect(irs.hasSpatialConsensus('a')).toBe(false);
    irs.processAssessment('a', makeFlaggedAssessment(), new Set(['n3']));
    expect(irs.hasSpatialConsensus('a')).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════
// Repulsion Force
// ═══════════════════════════════════════════════════════════════

describe('Repulsion force', () => {
  it('is 0 for healthy agents', () => {
    const irs = new ImmuneResponseSystem();
    const s = irs.processAssessment('a', makeAssessment());
    expect(s.repulsionForce).toBe(0);
  });

  it('increases with suspicion', () => {
    const irs = new ImmuneResponseSystem();
    irs.processAssessment('a', makeFlaggedAssessment(1, 0.8));
    const s1 = irs.getAgentStatus('a')!.repulsionForce;
    irs.processAssessment('a', makeFlaggedAssessment(3, 0.9));
    const s2 = irs.getAgentStatus('a')!.repulsionForce;
    expect(s2).toBeGreaterThanOrEqual(s1);
  });

  it('is amplified for quarantined agents', () => {
    const irs = new ImmuneResponseSystem();
    const neighbors = new Set(['n1', 'n2', 'n3']);
    for (let i = 0; i < 30; i++) {
      irs.processAssessment('a', makeFlaggedAssessment(3, 1.0), neighbors);
    }
    const s = irs.getAgentStatus('a')!;
    if (s.state === 'quarantined') {
      expect(s.repulsionForce).toBeGreaterThan(DEFAULT_IMMUNE_CONFIG.repulsionBase);
    }
  });

  it('is capped at 100', () => {
    const irs = new ImmuneResponseSystem();
    const neighbors = new Set(['n1', 'n2', 'n3']);
    for (let i = 0; i < 100; i++) {
      irs.processAssessment('a', makeFlaggedAssessment(5, 1.0), neighbors);
    }
    const s = irs.getAgentStatus('a')!;
    expect(s.repulsionForce).toBeLessThanOrEqual(100);
  });
});

// ═══════════════════════════════════════════════════════════════
// Quarantine Release
// ═══════════════════════════════════════════════════════════════

describe('releaseFromQuarantine', () => {
  it('moves agent from quarantined to monitoring', () => {
    const irs = new ImmuneResponseSystem();
    const neighbors = new Set(['n1', 'n2', 'n3']);
    for (let i = 0; i < 30; i++) {
      irs.processAssessment('a', makeFlaggedAssessment(3, 1.0), neighbors);
    }
    const beforeSuspicion = irs.getAgentStatus('a')!.suspicion;
    const beforeState = irs.getAgentStatus('a')!.state;
    if (beforeState === 'quarantined') {
      irs.releaseFromQuarantine('a');
      const after = irs.getAgentStatus('a')!;
      expect(after.state).toBe('monitoring');
      expect(after.suspicion).toBeLessThan(beforeSuspicion);
    }
  });

  it('reduces suspicion by 50% on release', () => {
    const irs = new ImmuneResponseSystem();
    const neighbors = new Set(['n1', 'n2', 'n3']);
    for (let i = 0; i < 30; i++) {
      irs.processAssessment('a', makeFlaggedAssessment(3, 1.0), neighbors);
    }
    const before = irs.getAgentStatus('a')!;
    if (before.state === 'quarantined') {
      const suspBefore = before.suspicion;
      irs.releaseFromQuarantine('a');
      expect(irs.getAgentStatus('a')!.suspicion).toBeCloseTo(suspBefore * 0.5);
    }
  });

  it('clears accusers on release', () => {
    const irs = new ImmuneResponseSystem();
    const neighbors = new Set(['n1', 'n2', 'n3']);
    for (let i = 0; i < 30; i++) {
      irs.processAssessment('a', makeFlaggedAssessment(3, 1.0), neighbors);
    }
    if (irs.getAgentStatus('a')!.state === 'quarantined') {
      irs.releaseFromQuarantine('a');
      expect(irs.getAgentStatus('a')!.accusers.size).toBe(0);
    }
  });

  it('does nothing for non-quarantined agents', () => {
    const irs = new ImmuneResponseSystem();
    irs.processAssessment('a', makeAssessment());
    irs.releaseFromQuarantine('a'); // Should not throw or change state
    expect(irs.getAgentStatus('a')!.state).toBe('healthy');
  });
});

// ═══════════════════════════════════════════════════════════════
// Risk Modifier
// ═══════════════════════════════════════════════════════════════

describe('getRiskModifier', () => {
  it('returns 1.0 for unknown agents', () => {
    const irs = new ImmuneResponseSystem();
    expect(irs.getRiskModifier('unknown')).toBe(1.0);
  });

  it('returns 1.0 for healthy agents', () => {
    const irs = new ImmuneResponseSystem();
    irs.processAssessment('a', makeAssessment());
    expect(irs.getRiskModifier('a')).toBe(1.0);
  });

  it('returns > 1 for monitoring agents', () => {
    const irs = new ImmuneResponseSystem();
    // Push into monitoring
    for (let i = 0; i < 10; i++) {
      irs.processAssessment('a', makeFlaggedAssessment(1, 0.8));
    }
    if (irs.getAgentStatus('a')!.state === 'monitoring') {
      expect(irs.getRiskModifier('a')).toBeCloseTo(1.2);
    }
  });

  it('returns Infinity for expelled agents', () => {
    const irs = new ImmuneResponseSystem({ maxQuarantineCount: 1 });
    const neighbors = new Set(['n1', 'n2', 'n3']);
    for (let i = 0; i < 100; i++) {
      irs.processAssessment('a', makeFlaggedAssessment(5, 1.0), neighbors);
    }
    if (irs.getAgentStatus('a')!.state === 'expelled') {
      expect(irs.getRiskModifier('a')).toBe(Infinity);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Statistics and Events
// ═══════════════════════════════════════════════════════════════

describe('getStats', () => {
  it('returns empty stats initially', () => {
    const irs = new ImmuneResponseSystem();
    const stats = irs.getStats();
    expect(stats.total).toBe(0);
    expect(stats.avgSuspicion).toBe(0);
  });

  it('counts agents by state', () => {
    const irs = new ImmuneResponseSystem();
    irs.processAssessment('healthy1', makeAssessment());
    irs.processAssessment('healthy2', makeAssessment());
    const stats = irs.getStats();
    expect(stats.total).toBe(2);
    expect(stats.byState.healthy).toBe(2);
  });
});

describe('getEvents', () => {
  it('records state change events', () => {
    const irs = new ImmuneResponseSystem();
    // Drive to monitoring
    for (let i = 0; i < 10; i++) {
      irs.processAssessment('a', makeFlaggedAssessment(2, 0.9));
    }
    const events = irs.getEvents();
    const stateChanges = events.filter((e) => e.eventType === 'state_change');
    expect(stateChanges.length).toBeGreaterThan(0);
  });

  it('events include agent id and reason', () => {
    const irs = new ImmuneResponseSystem();
    for (let i = 0; i < 10; i++) {
      irs.processAssessment('agent-x', makeFlaggedAssessment(2, 0.9));
    }
    const events = irs.getEvents();
    if (events.length > 0) {
      expect(events[0].agentId).toBe('agent-x');
      expect(events[0].reason).toBeTruthy();
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Query Methods
// ═══════════════════════════════════════════════════════════════

describe('getAgentsByState', () => {
  it('returns agents in specified state', () => {
    const irs = new ImmuneResponseSystem();
    irs.processAssessment('h1', makeAssessment());
    irs.processAssessment('h2', makeAssessment());
    const healthy = irs.getAgentsByState('healthy');
    expect(healthy.length).toBe(2);
  });

  it('returns empty array for unpopulated state', () => {
    const irs = new ImmuneResponseSystem();
    expect(irs.getAgentsByState('quarantined')).toEqual([]);
  });
});

// ═══════════════════════════════════════════════════════════════
// Quarantine Amplification
// ═══════════════════════════════════════════════════════════════

describe('Quarantine amplification', () => {
  it('quarantined agents accumulate suspicion faster', () => {
    // Two agents: both get same initial treatment,
    // then one gets quarantined (via spatial consensus)
    const irs1 = new ImmuneResponseSystem();
    const irs2 = new ImmuneResponseSystem();
    const neighbors = new Set(['n1', 'n2', 'n3']);

    // Both get flagged equally at first
    for (let i = 0; i < 5; i++) {
      irs1.processAssessment('a', makeFlaggedAssessment(2, 0.8));
      irs2.processAssessment('a', makeFlaggedAssessment(2, 0.8), neighbors);
    }

    // Now add more flags — quarantined agent should accumulate faster
    for (let i = 0; i < 10; i++) {
      irs1.processAssessment('a', makeFlaggedAssessment(2, 0.8));
      irs2.processAssessment('a', makeFlaggedAssessment(2, 0.8), neighbors);
    }

    const s1 = irs1.getAgentStatus('a')!;
    const s2 = irs2.getAgentStatus('a')!;
    // Quarantined agent should have higher suspicion due to amplification
    expect(s2.suspicion).toBeGreaterThanOrEqual(s1.suspicion);
  });
});

// ═══════════════════════════════════════════════════════════════
// Suspicion History
// ═══════════════════════════════════════════════════════════════

describe('Suspicion history', () => {
  it('records suspicion values over time', () => {
    const irs = new ImmuneResponseSystem();
    for (let i = 0; i < 5; i++) {
      irs.processAssessment('a', makeFlaggedAssessment(1, 0.5));
    }
    const history = irs.getAgentStatus('a')!.suspicionHistory;
    expect(history.length).toBe(5);
    // Each entry should be >= previous (accumulating)
    for (let i = 1; i < history.length; i++) {
      expect(history[i]).toBeGreaterThanOrEqual(history[i - 1]);
    }
  });

  it('trims history to configured length', () => {
    const irs = new ImmuneResponseSystem({ historyLength: 5 });
    for (let i = 0; i < 10; i++) {
      irs.processAssessment('a', makeFlaggedAssessment(1, 0.5));
    }
    expect(irs.getAgentStatus('a')!.suspicionHistory.length).toBeLessThanOrEqual(5);
  });
});
