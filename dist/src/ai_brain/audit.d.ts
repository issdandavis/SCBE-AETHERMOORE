/**
 * @file audit.ts
 * @module ai_brain/audit
 * @layer Layer 13, Layer 14
 * @component Unified Audit Logger
 * @version 1.1.0
 * @since 2026-02-07
 *
 * Provides cryptographically auditable event logging for the unified brain manifold.
 * Every state transition, detection alert, boundary violation, and governance decision
 * is recorded with full 21D telemetry.
 */
import type { BrainAuditEvent, CombinedAssessment, TrajectoryPoint } from './types.js';
/**
 * Unified Audit Logger for the AI Brain Manifold.
 *
 * Maintains an append-only log of brain events with cryptographic
 * hash chaining for tamper detection. Each event is hashed with
 * the previous event's hash to create an immutable chain.
 */
export declare class BrainAuditLogger {
    private events;
    private hashChain;
    private readonly maxEvents;
    /**
     * @param maxEvents - Maximum events to retain in memory (default: 10000)
     */
    constructor(maxEvents?: number);
    /**
     * Log a state transition event.
     *
     * @param layer - SCBE layer (1-14) where transition occurred
     * @param oldState - Previous state vector
     * @param newState - New state vector
     * @param metadata - Additional context
     */
    logStateTransition(layer: number, oldState: number[], newState: number[], metadata?: Record<string, unknown>): void;
    /**
     * Log a detection alert from the multi-vectored detection system.
     *
     * @param assessment - Combined assessment result
     * @param agentId - Agent identifier
     */
    logDetectionAlert(assessment: CombinedAssessment, agentId: string): void;
    /**
     * Log a boundary violation (agent too close to Poincare ball edge).
     *
     * @param layer - Layer where violation occurred
     * @param point - Trajectory point at violation
     * @param agentId - Agent identifier
     */
    logBoundaryViolation(layer: number, point: TrajectoryPoint, agentId: string): void;
    /**
     * Log a risk decision event.
     *
     * @param decision - Risk decision made
     * @param agentId - Agent identifier
     * @param reason - Reason for decision
     */
    logRiskDecision(decision: string, agentId: string, reason: string, metadata?: Record<string, unknown>): void;
    /**
     * Get all events
     */
    getEvents(): ReadonlyArray<BrainAuditEvent>;
    /**
     * Get events filtered by type
     */
    getEventsByType(eventType: BrainAuditEvent['eventType']): BrainAuditEvent[];
    /**
     * Get the hash chain for verification
     */
    getHashChain(): ReadonlyArray<string>;
    /**
     * Verify hash chain integrity
     */
    verifyChainIntegrity(): boolean;
    /**
     * Get event count
     */
    get count(): number;
    private addEvent;
    private computeEventHash;
}
//# sourceMappingURL=audit.d.ts.map