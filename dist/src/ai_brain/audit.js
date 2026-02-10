"use strict";
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
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.BrainAuditLogger = void 0;
const crypto = __importStar(require("crypto"));
/**
 * Unified Audit Logger for the AI Brain Manifold.
 *
 * Maintains an append-only log of brain events with cryptographic
 * hash chaining for tamper detection. Each event is hashed with
 * the previous event's hash to create an immutable chain.
 */
class BrainAuditLogger {
    events = [];
    hashChain = [];
    maxEvents;
    /**
     * @param maxEvents - Maximum events to retain in memory (default: 10000)
     */
    constructor(maxEvents = 10000) {
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
    logStateTransition(layer, oldState, newState, metadata = {}) {
        const stateDelta = Math.sqrt(oldState.reduce((sum, v, i) => {
            const diff = v - (newState[i] ?? 0);
            return sum + diff * diff;
        }, 0));
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
    logDetectionAlert(assessment, agentId) {
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
    logBoundaryViolation(layer, point, agentId) {
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
    logRiskDecision(decision, agentId, reason, metadata = {}) {
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
    getEvents() {
        return this.events;
    }
    /**
     * Get events filtered by type
     */
    getEventsByType(eventType) {
        return this.events.filter((e) => e.eventType === eventType);
    }
    /**
     * Get the hash chain for verification
     */
    getHashChain() {
        return this.hashChain;
    }
    /**
     * Verify hash chain integrity
     */
    verifyChainIntegrity() {
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
    get count() {
        return this.events.length;
    }
    // ═══════════════════════════════════════════════════════════════
    // Private Methods
    // ═══════════════════════════════════════════════════════════════
    addEvent(event) {
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
    computeEventHash(event, prevHash) {
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
exports.BrainAuditLogger = BrainAuditLogger;
/**
 * Helper: compute vector norm
 */
function norm(v) {
    return Math.sqrt(v.reduce((s, x) => s + x * x, 0));
}
//# sourceMappingURL=audit.js.map