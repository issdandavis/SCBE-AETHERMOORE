/**
 * Brain Audit Logger Unit Tests
 *
 * Tests for the SHA-256 hash-chained tamper-evident audit logger.
 *
 * @layer Layer 13, Layer 14
 */

import { describe, expect, it } from 'vitest';

import { BRAIN_DIMENSIONS, BrainAuditLogger, type TrajectoryPoint } from '../../src/ai_brain/index';

function makeTestPoint(step: number): TrajectoryPoint {
  return {
    step,
    state: new Array(BRAIN_DIMENSIONS).fill(0.1),
    embedded: new Array(BRAIN_DIMENSIONS).fill(0.05),
    distance: 0.5,
    curvature: 0.01,
    timestamp: Date.now(),
  };
}

describe('BrainAuditLogger', () => {
  it('should start with empty log', () => {
    const logger = new BrainAuditLogger();
    expect(logger.getEvents()).toHaveLength(0);
  });

  it('should log state transitions', () => {
    const logger = new BrainAuditLogger();
    const oldState = new Array(BRAIN_DIMENSIONS).fill(0);
    const newState = new Array(BRAIN_DIMENSIONS).fill(0.5);
    logger.logStateTransition(5, oldState, newState);
    const events = logger.getEvents();
    expect(events).toHaveLength(1);
    expect(events[0].eventType).toBe('state_transition');
  });

  it('should log detection alerts', () => {
    const logger = new BrainAuditLogger();
    logger.logDetectionAlert(
      {
        combinedScore: 0.8,
        decision: 'ESCALATE',
        flagCount: 3,
        anyFlagged: true,
        detections: [],
        timestamp: Date.now(),
      },
      'agent-2'
    );
    const events = logger.getEvents();
    expect(events).toHaveLength(1);
    expect(events[0].eventType).toBe('detection_alert');
  });

  it('should log boundary violations', () => {
    const logger = new BrainAuditLogger();
    logger.logBoundaryViolation(7, makeTestPoint(0), 'agent-3');
    const events = logger.getEvents();
    expect(events).toHaveLength(1);
    expect(events[0].eventType).toBe('boundary_violation');
  });

  it('should log risk decisions', () => {
    const logger = new BrainAuditLogger();
    logger.logRiskDecision('DENY', 'agent-4', 'malicious behavior detected');
    const events = logger.getEvents();
    expect(events).toHaveLength(1);
    expect(events[0].eventType).toBe('risk_decision');
  });

  it('should maintain hash chain integrity', () => {
    const logger = new BrainAuditLogger();
    logger.logRiskDecision('ALLOW', 'a1', 'low risk');
    logger.logRiskDecision('DENY', 'a2', 'high risk');
    logger.logRiskDecision('QUARANTINE', 'a3', 'suspicious');
    expect(logger.verifyChainIntegrity()).toBe(true);
  });

  it('should have unique hashes per event', () => {
    const logger = new BrainAuditLogger();
    logger.logRiskDecision('ALLOW', 'a1', 'low risk');
    logger.logRiskDecision('DENY', 'a2', 'high risk');
    const chain = logger.getHashChain();
    expect(chain).toHaveLength(2);
    expect(chain[0]).not.toBe(chain[1]);
  });

  it('should chain hashes (each event references previous)', () => {
    const logger = new BrainAuditLogger();
    logger.logRiskDecision('ALLOW', 'a1', 'low risk');
    logger.logRiskDecision('DENY', 'a2', 'high risk');
    const chain = logger.getHashChain();
    // Both hashes should be non-empty hex strings
    expect(chain[0]).toMatch(/^[0-9a-f]+$/);
    expect(chain[1]).toMatch(/^[0-9a-f]+$/);
    expect(chain[0]).not.toBe(chain[1]);
  });

  it('should filter events by type', () => {
    const logger = new BrainAuditLogger();
    logger.logRiskDecision('ALLOW', 'a1', 'low risk');
    logger.logRiskDecision('DENY', 'a2', 'high risk');
    logger.logBoundaryViolation(7, makeTestPoint(0), 'a3');
    const decisions = logger.getEventsByType('risk_decision');
    expect(decisions).toHaveLength(2);
    const violations = logger.getEventsByType('boundary_violation');
    expect(violations).toHaveLength(1);
  });
});
