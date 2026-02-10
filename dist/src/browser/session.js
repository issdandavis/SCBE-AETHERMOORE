"use strict";
/**
 * SCBE Browser Session Management
 * =================================
 *
 * Manages browser sessions with:
 * - Session state tracking
 * - Decision history storage (integrated with Hive Memory concepts)
 * - Cross-session learning
 * - Escalation queue management
 *
 * @module browser/session
 * @layer Layer 13 (Hive Memory integration)
 * @version 3.0.0
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.BrowserSession = void 0;
exports.createBrowserSession = createBrowserSession;
exports.defaultSessionConfig = defaultSessionConfig;
const crypto_1 = require("crypto");
const evaluator_js_1 = require("./evaluator.js");
// =============================================================================
// CONSTANTS
// =============================================================================
/** Maximum history entries to keep in hot memory */
const MAX_HOT_HISTORY = 1000;
/** Session timeout (ms) - 30 minutes of inactivity */
const SESSION_TIMEOUT = 30 * 60 * 1000;
/** Risk decay rate per minute */
const RISK_DECAY_RATE = 0.95;
/** Risk increase per DENY decision */
const RISK_INCREMENT_DENY = 0.15;
/** Risk increase per ESCALATE decision */
const RISK_INCREMENT_ESCALATE = 0.08;
/** Risk increase per QUARANTINE decision */
const RISK_INCREMENT_QUARANTINE = 0.03;
// =============================================================================
// SESSION MANAGER
// =============================================================================
/**
 * Manages a single browser session with SCBE governance.
 */
class BrowserSession {
    sessionId;
    agentId;
    tongue;
    config;
    state;
    evaluator;
    history = [];
    escalationQueue = new Map();
    listeners = new Set();
    riskDecayTimer;
    constructor(config) {
        this.sessionId = config.sessionId;
        this.agentId = config.agentId;
        this.tongue = config.tongue;
        this.config = config;
        this.state = {
            sessionId: this.sessionId,
            status: 'initializing',
            startedAt: Date.now(),
            actionCount: 0,
            decisions: { allow: 0, quarantine: 0, escalate: 0, deny: 0 },
            sessionRisk: 0,
            errorCount: 0,
        };
        this.evaluator = new evaluator_js_1.BrowserActionEvaluator({ debug: false });
    }
    /**
     * Initialize the session.
     */
    async initialize() {
        this.state.status = 'active';
        this.state.startedAt = Date.now();
        // Start risk decay timer (decays risk over time during inactivity)
        this.startRiskDecay();
        this.emit({ type: 'session_start', sessionId: this.sessionId });
    }
    /**
     * Evaluate and potentially execute a browser action.
     */
    async evaluateAction(action, observation) {
        // Update last action time
        this.state.lastActionAt = Date.now();
        this.state.currentUrl = observation.page.url;
        // Evaluate through SCBE pipeline
        const governance = this.evaluator.evaluate(action, observation, {
            sessionRisk: this.state.sessionRisk,
            actionCount: this.state.actionCount,
            errorCount: this.state.errorCount,
        });
        // Update decision counts
        this.updateDecisionCounts(governance.decision);
        // Update session risk
        this.updateSessionRisk(governance);
        // Check if escalation is required
        let escalationRequired;
        if (governance.decision === 'ESCALATE' || governance.requiresRoundtable) {
            escalationRequired = this.createEscalationRequest(action, governance, observation);
        }
        // Determine if action can execute
        const canExecute = governance.decision === 'ALLOW' ||
            (governance.decision === 'QUARANTINE' && !governance.requiresRoundtable);
        // Record in history (before execution)
        const historyEntry = this.createHistoryEntry(action, governance, observation);
        this.addToHistory(historyEntry);
        // Emit event
        this.emit({
            type: 'action_evaluated',
            sessionId: this.sessionId,
            action,
            governance,
            canExecute,
        });
        return { governance, canExecute, escalationRequired };
    }
    /**
     * Record action execution result.
     */
    recordResult(entryId, result, observationAfter) {
        const entry = this.history.find((h) => h.id === entryId);
        if (entry) {
            entry.result = result;
            entry.observationAfter = observationAfter;
        }
        // Update action count
        this.state.actionCount++;
        // Update error count if failed
        if (!result.success) {
            this.state.errorCount++;
        }
        this.emit({
            type: 'action_completed',
            sessionId: this.sessionId,
            entryId,
            success: result.success,
            duration: result.duration,
        });
    }
    /**
     * Handle escalation response.
     */
    async handleEscalationResponse(response) {
        const request = this.escalationQueue.get(response.requestId);
        if (!request) {
            throw new Error(`Unknown escalation request: ${response.requestId}`);
        }
        // Remove from queue
        this.escalationQueue.delete(response.requestId);
        // Determine if can proceed
        const canProceed = response.decision === 'approve' || response.decision === 'modify';
        // Use modified action if provided
        const action = response.modifiedAction ?? request.action;
        // Emit event
        this.emit({
            type: 'escalation_resolved',
            sessionId: this.sessionId,
            requestId: response.requestId,
            decision: response.decision,
            reviewer: response.reviewer,
        });
        // Update risk based on escalation outcome
        if (response.decision === 'deny') {
            this.state.sessionRisk = Math.min(this.state.sessionRisk + RISK_INCREMENT_DENY, 1);
        }
        return { canProceed, action };
    }
    /**
     * Get session statistics.
     */
    getStatistics() {
        const totalDecisions = this.state.decisions.allow +
            this.state.decisions.quarantine +
            this.state.decisions.escalate +
            this.state.decisions.deny;
        return {
            sessionId: this.sessionId,
            status: this.state.status,
            duration: Date.now() - this.state.startedAt,
            actionCount: this.state.actionCount,
            errorCount: this.state.errorCount,
            sessionRisk: this.state.sessionRisk,
            decisions: { ...this.state.decisions },
            rates: totalDecisions > 0
                ? {
                    allowRate: this.state.decisions.allow / totalDecisions,
                    quarantineRate: this.state.decisions.quarantine / totalDecisions,
                    escalateRate: this.state.decisions.escalate / totalDecisions,
                    denyRate: this.state.decisions.deny / totalDecisions,
                }
                : { allowRate: 0, quarantineRate: 0, escalateRate: 0, denyRate: 0 },
            pendingEscalations: this.escalationQueue.size,
            historySize: this.history.length,
        };
    }
    /**
     * Get action history with optional filtering.
     */
    getHistory(options) {
        let filtered = [...this.history];
        if (options?.decision) {
            filtered = filtered.filter((h) => h.governance.decision === options.decision);
        }
        if (options?.actionType) {
            filtered = filtered.filter((h) => h.action.type === options.actionType);
        }
        if (options?.since) {
            filtered = filtered.filter((h) => h.timestamp >= options.since);
        }
        // Sort by timestamp descending (newest first)
        filtered.sort((a, b) => b.timestamp - a.timestamp);
        if (options?.limit) {
            filtered = filtered.slice(0, options.limit);
        }
        return filtered;
    }
    /**
     * Get similar historical actions for learning.
     */
    getSimilarActions(action, limit = 5) {
        // Find actions of same type
        const sameType = this.history.filter((h) => h.action.type === action.type);
        // Sort by recency
        sameType.sort((a, b) => b.timestamp - a.timestamp);
        return sameType.slice(0, limit);
    }
    /**
     * Predict outcome based on historical data.
     */
    predictOutcome(action) {
        const similar = this.getSimilarActions(action, 10);
        if (similar.length < 3) {
            return null;
        }
        // Aggregate decisions
        const decisionCounts = {
            ALLOW: 0,
            QUARANTINE: 0,
            ESCALATE: 0,
            DENY: 0,
        };
        let totalRisk = 0;
        for (const entry of similar) {
            decisionCounts[entry.governance.decision]++;
            totalRisk += entry.governance.riskScore;
        }
        // Find most common decision
        const mostCommon = Object.entries(decisionCounts).reduce((max, [decision, count]) => (count > max[1] ? [decision, count] : max), ['ALLOW', 0]);
        return {
            predictedDecision: mostCommon[0],
            confidence: mostCommon[1] / similar.length,
            avgRiskScore: totalRisk / similar.length,
            sampleSize: similar.length,
            decisionDistribution: decisionCounts,
        };
    }
    /**
     * Pause session.
     */
    pause() {
        this.state.status = 'paused';
        this.stopRiskDecay();
        this.emit({ type: 'session_paused', sessionId: this.sessionId });
    }
    /**
     * Resume session.
     */
    resume() {
        this.state.status = 'active';
        this.startRiskDecay();
        this.emit({ type: 'session_resumed', sessionId: this.sessionId });
    }
    /**
     * Terminate session.
     */
    async terminate() {
        this.state.status = 'terminated';
        this.stopRiskDecay();
        // Generate summary
        const summary = this.generateSummary();
        // Emit event
        this.emit({ type: 'session_end', sessionId: this.sessionId, summary });
        return summary;
    }
    /**
     * Add event listener.
     */
    addEventListener(listener) {
        this.listeners.add(listener);
        return () => this.listeners.delete(listener);
    }
    /**
     * Export session data for Hive Memory storage.
     */
    exportForHiveMemory() {
        return {
            sessionId: this.sessionId,
            agentId: this.agentId,
            tongue: this.tongue,
            state: { ...this.state },
            statistics: this.getStatistics(),
            history: this.history.slice(-500), // Last 500 entries
            exportedAt: Date.now(),
        };
    }
    /**
     * Import historical data for cross-session learning.
     */
    importHistoricalData(data) {
        // Merge historical entries (marked as imported)
        for (const entry of data.history) {
            const importedEntry = {
                ...entry,
                id: `imported-${entry.id}`,
            };
            this.history.unshift(importedEntry);
        }
        // Trim if over limit
        this.trimHistory();
        this.emit({
            type: 'history_imported',
            sessionId: this.sessionId,
            importedCount: data.history.length,
        });
    }
    // ===========================================================================
    // PRIVATE METHODS
    // ===========================================================================
    updateDecisionCounts(decision) {
        switch (decision) {
            case 'ALLOW':
                this.state.decisions.allow++;
                break;
            case 'QUARANTINE':
                this.state.decisions.quarantine++;
                break;
            case 'ESCALATE':
                this.state.decisions.escalate++;
                break;
            case 'DENY':
                this.state.decisions.deny++;
                break;
        }
    }
    updateSessionRisk(governance) {
        // Increase risk based on decision
        let increment = 0;
        switch (governance.decision) {
            case 'DENY':
                increment = RISK_INCREMENT_DENY;
                break;
            case 'ESCALATE':
                increment = RISK_INCREMENT_ESCALATE;
                break;
            case 'QUARANTINE':
                increment = RISK_INCREMENT_QUARANTINE;
                break;
            case 'ALLOW':
                // Small decay on ALLOW
                this.state.sessionRisk *= 0.99;
                return;
        }
        this.state.sessionRisk = Math.min(this.state.sessionRisk + increment, 1);
    }
    createEscalationRequest(action, governance, observation) {
        const request = {
            requestId: (0, crypto_1.randomUUID)(),
            sessionId: this.sessionId,
            action,
            governance,
            observation,
            level: governance.riskScore > 0.8 ? 'human' : 'higher_ai',
            requestedAt: Date.now(),
            deadline: Date.now() + 5 * 60 * 1000, // 5 minute deadline
        };
        this.escalationQueue.set(request.requestId, request);
        return request;
    }
    createHistoryEntry(action, governance, observation) {
        return {
            id: (0, crypto_1.randomUUID)(),
            action,
            governance,
            observationBefore: observation,
            timestamp: Date.now(),
        };
    }
    addToHistory(entry) {
        this.history.push(entry);
        this.trimHistory();
    }
    trimHistory() {
        if (this.history.length > MAX_HOT_HISTORY) {
            // Keep most recent entries
            this.history = this.history.slice(-MAX_HOT_HISTORY);
        }
    }
    startRiskDecay() {
        if (this.riskDecayTimer)
            return;
        this.riskDecayTimer = setInterval(() => {
            // Decay risk over time during inactivity
            const timeSinceLastAction = Date.now() - (this.state.lastActionAt ?? this.state.startedAt);
            if (timeSinceLastAction > 60000) {
                // At least 1 minute of inactivity
                this.state.sessionRisk *= RISK_DECAY_RATE;
            }
        }, 60000); // Check every minute
    }
    stopRiskDecay() {
        if (this.riskDecayTimer) {
            clearInterval(this.riskDecayTimer);
            this.riskDecayTimer = undefined;
        }
    }
    generateSummary() {
        const stats = this.getStatistics();
        const highRiskActions = this.history.filter((h) => h.governance.riskScore > 0.7);
        const deniedActions = this.history.filter((h) => h.governance.decision === 'DENY');
        return {
            sessionId: this.sessionId,
            agentId: this.agentId,
            tongue: this.tongue,
            startedAt: this.state.startedAt,
            endedAt: Date.now(),
            duration: Date.now() - this.state.startedAt,
            statistics: stats,
            highlights: {
                mostCommonAction: this.getMostCommonAction(),
                highRiskActionCount: highRiskActions.length,
                deniedActionCount: deniedActions.length,
                maxRiskScore: Math.max(...this.history.map((h) => h.governance.riskScore), 0),
                uniqueUrls: new Set(this.history.map((h) => h.observationBefore?.page.url).filter(Boolean))
                    .size,
            },
            finalRisk: this.state.sessionRisk,
        };
    }
    getMostCommonAction() {
        const counts = {};
        for (const entry of this.history) {
            counts[entry.action.type] = (counts[entry.action.type] ?? 0) + 1;
        }
        let max = 0;
        let common = 'none';
        for (const [action, count] of Object.entries(counts)) {
            if (count > max) {
                max = count;
                common = action;
            }
        }
        return common;
    }
    emit(event) {
        for (const listener of this.listeners) {
            try {
                listener(event);
            }
            catch (err) {
                console.error('Session event listener error:', err);
            }
        }
    }
}
exports.BrowserSession = BrowserSession;
// =============================================================================
// FACTORY FUNCTION
// =============================================================================
/**
 * Create a new browser session.
 */
function createBrowserSession(config) {
    return new BrowserSession(config);
}
/**
 * Create default session config.
 */
function defaultSessionConfig(agentId, tongue = 'KO') {
    return {
        sessionId: (0, crypto_1.randomUUID)(),
        agentId,
        tongue,
        browserType: 'chromium',
        headless: true,
        viewport: { width: 1280, height: 720 },
        timeout: 30000,
    };
}
//# sourceMappingURL=session.js.map