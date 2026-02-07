/**
 * @file audit.ts
 * @module ai_brain/audit
 * @layer Layer 13, Layer 14
 * @component Unified Audit Logger
 * @version 1.1.0
 *
 * Provides cryptographically auditable event logging for the unified brain manifold.
 * Every state transition, detection alert, boundary violation, and governance decision
 * is recorded with full 21D telemetry.
 */

import * as crypto from 'crypto';

import type { BrainAuditEvent, CombinedAssessment, TrajectoryPoint } from './types.js';

/**
 * Unified Audit Logger for the AI Brain Manifold.
 *
 * Maintains an append-only log of brain events with cryptographic
 * hash chaining for tamper detection. Each event is hashed with
 * the previous event's hash to create an immutable chain.
 */
export class BrainAuditLogger {
  private events: BrainAuditEvent[] = [];
  private hashChain: string[] = [];
  private readonly maxEvents: number;

  /**
   * @param maxEvents - Maximum events to retain in memory (default: 10000)
   */
  constructor(maxEvents: number = 10000) {
    this.maxEvents = maxEvents;
  }

  /**
   * Log a state transition event.
   *
   * @param layer - SCBE layer (1-14) where transition occurred
   * @param oldState - Previous state vector
   * @param newState - New state vector
   * @param metadata - Additional context
   */
  logStateTransition(
    layer: number,
    oldState: number[],
    newState: number[],
    metadata: Record<string, unknown> = {}
  ): void {
    const stateDelta = Math.sqrt(
      oldState.reduce((sum, v, i) => {
        const diff = v - (newState[i] ?? 0);
        return sum + diff * diff;
      }, 0)
    );

    const boundaryDistance = 1 - Math.sqrt(newState.reduce((sum, v) => sum + v * v, 0));

    this.addEvent({
      timestamp: Date.now(),
      layer,
      eventType: 'state_transition',
      stateDelta,
      boundaryDistance,
      metadata: { ...metadata, oldNorm: norm(oldState), newNorm: norm(newState) },
    });
  }

  /**
   * Log a detection alert from the multi-vectored detection system.
   *
   * @param assessment - Combined assessment result
   * @param agentId - Agent identifier
   */
  logDetectionAlert(assessment: CombinedAssessment, agentId: string): void {
    const flaggedMechanisms = assessment.detections
      .filter((d) => d.flagged)
      .map((d) => d.mechanism);

    this.addEvent({
      timestamp: Date.now(),
      layer: 13,
      eventType: 'detection_alert',
      stateDelta: assessment.combinedScore,
      boundaryDistance: 0,
      metadata: {
        agentId,
        decision: assessment.decision,
        combinedScore: assessment.combinedScore,
        flaggedMechanisms,
        flagCount: assessment.flagCount,
      },
    });
  }

  /**
   * Log a boundary violation (agent too close to Poincare ball edge).
   *
   * @param layer - Layer where violation occurred
   * @param point - Trajectory point at violation
   * @param agentId - Agent identifier
   */
  logBoundaryViolation(layer: number, point: TrajectoryPoint, agentId: string): void {
    const boundaryDist = 1 - Math.sqrt(point.embedded.reduce((s, v) => s + v * v, 0));

    this.addEvent({
      timestamp: Date.now(),
      layer,
      eventType: 'boundary_violation',
      stateDelta: point.distance,
      boundaryDistance: boundaryDist,
      metadata: {
        agentId,
        step: point.step,
        distance: point.distance,
        curvature: point.curvature,
      },
    });
  }

  /**
   * Log a risk decision event.
   *
   * @param decision - Risk decision made
   * @param agentId - Agent identifier
   * @param reason - Reason for decision
   */
  logRiskDecision(
    decision: string,
    agentId: string,
    reason: string,
    metadata: Record<string, unknown> = {}
  ): void {
    this.addEvent({
      timestamp: Date.now(),
      layer: 13,
      eventType: 'risk_decision',
      stateDelta: 0,
      boundaryDistance: 0,
      metadata: { ...metadata, decision, agentId, reason },
    });
  }

  /**
   * Get all events
   */
  getEvents(): ReadonlyArray<BrainAuditEvent> {
    return this.events;
  }

  /**
   * Get events filtered by type
   */
  getEventsByType(eventType: BrainAuditEvent['eventType']): BrainAuditEvent[] {
    return this.events.filter((e) => e.eventType === eventType);
  }

  /**
   * Get the hash chain for verification
   */
  getHashChain(): ReadonlyArray<string> {
    return this.hashChain;
  }

  /**
   * Verify hash chain integrity
   */
  verifyChainIntegrity(): boolean {
    for (let i = 0; i < this.events.length; i++) {
      const prevHash = i > 0 ? this.hashChain[i - 1] : '';
      const expectedHash = this.computeEventHash(this.events[i], prevHash);
      if (expectedHash !== this.hashChain[i]) {
        return false;
      }
    }
    return true;
  }

  /**
   * Get event count
   */
  get count(): number {
    return this.events.length;
  }

  // ═══════════════════════════════════════════════════════════════
  // Private Methods
  // ═══════════════════════════════════════════════════════════════

  private addEvent(event: BrainAuditEvent): void {
    // Hash chain: each event's hash includes the previous hash
    const prevHash = this.hashChain.length > 0 ? this.hashChain[this.hashChain.length - 1] : '';
    const eventHash = this.computeEventHash(event, prevHash);

    this.events.push(event);
    this.hashChain.push(eventHash);

    // Trim if over capacity (remove oldest)
    if (this.events.length > this.maxEvents) {
      this.events.shift();
      this.hashChain.shift();
    }
  }

  private computeEventHash(event: BrainAuditEvent, prevHash: string): string {
    const data = JSON.stringify({
      prevHash,
      timestamp: event.timestamp,
      layer: event.layer,
      eventType: event.eventType,
      stateDelta: event.stateDelta,
      boundaryDistance: event.boundaryDistance,
    });
    return crypto.createHash('sha256').update(data).digest('hex');
  }
}

/**
 * Helper: compute vector norm
 */
function norm(v: number[]): number {
  return Math.sqrt(v.reduce((s, x) => s + x * x, 0));
}
