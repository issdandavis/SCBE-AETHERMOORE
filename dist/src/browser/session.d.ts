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
import { TongueCode } from '../tokenizer/ss1.js';
import { BrowserAction, BrowserObservation, BrowserSessionConfig, BrowserSessionState, ActionHistoryEntry, GovernanceResult, ActionResult, EscalationRequest, EscalationResponse, BrowserDecision } from './types.js';
/**
 * Manages a single browser session with SCBE governance.
 */
export declare class BrowserSession {
    readonly sessionId: string;
    readonly agentId: string;
    readonly tongue: TongueCode;
    readonly config: BrowserSessionConfig;
    private state;
    private evaluator;
    private history;
    private escalationQueue;
    private listeners;
    private riskDecayTimer?;
    constructor(config: BrowserSessionConfig);
    /**
     * Initialize the session.
     */
    initialize(): Promise<void>;
    /**
     * Evaluate and potentially execute a browser action.
     */
    evaluateAction(action: BrowserAction, observation: BrowserObservation): Promise<{
        governance: GovernanceResult;
        canExecute: boolean;
        escalationRequired?: EscalationRequest;
    }>;
    /**
     * Record action execution result.
     */
    recordResult(entryId: string, result: ActionResult, observationAfter?: BrowserObservation): void;
    /**
     * Handle escalation response.
     */
    handleEscalationResponse(response: EscalationResponse): Promise<{
        canProceed: boolean;
        action: BrowserAction;
    }>;
    /**
     * Get session statistics.
     */
    getStatistics(): SessionStatistics;
    /**
     * Get action history with optional filtering.
     */
    getHistory(options?: {
        limit?: number;
        decision?: BrowserDecision;
        actionType?: string;
        since?: number;
    }): ActionHistoryEntry[];
    /**
     * Get similar historical actions for learning.
     */
    getSimilarActions(action: BrowserAction, limit?: number): ActionHistoryEntry[];
    /**
     * Predict outcome based on historical data.
     */
    predictOutcome(action: BrowserAction): PredictedOutcome | null;
    /**
     * Pause session.
     */
    pause(): void;
    /**
     * Resume session.
     */
    resume(): void;
    /**
     * Terminate session.
     */
    terminate(): Promise<SessionSummary>;
    /**
     * Add event listener.
     */
    addEventListener(listener: SessionEventListener): () => void;
    /**
     * Export session data for Hive Memory storage.
     */
    exportForHiveMemory(): HiveMemoryExport;
    /**
     * Import historical data for cross-session learning.
     */
    importHistoricalData(data: HiveMemoryExport): void;
    private updateDecisionCounts;
    private updateSessionRisk;
    private createEscalationRequest;
    private createHistoryEntry;
    private addToHistory;
    private trimHistory;
    private startRiskDecay;
    private stopRiskDecay;
    private generateSummary;
    private getMostCommonAction;
    private emit;
}
export interface SessionStatistics {
    sessionId: string;
    status: BrowserSessionState['status'];
    duration: number;
    actionCount: number;
    errorCount: number;
    sessionRisk: number;
    decisions: BrowserSessionState['decisions'];
    rates: {
        allowRate: number;
        quarantineRate: number;
        escalateRate: number;
        denyRate: number;
    };
    pendingEscalations: number;
    historySize: number;
}
export interface PredictedOutcome {
    predictedDecision: BrowserDecision;
    confidence: number;
    avgRiskScore: number;
    sampleSize: number;
    decisionDistribution: Record<BrowserDecision, number>;
}
export interface SessionSummary {
    sessionId: string;
    agentId: string;
    tongue: TongueCode;
    startedAt: number;
    endedAt: number;
    duration: number;
    statistics: SessionStatistics;
    highlights: {
        mostCommonAction: string;
        highRiskActionCount: number;
        deniedActionCount: number;
        maxRiskScore: number;
        uniqueUrls: number;
    };
    finalRisk: number;
}
export interface HiveMemoryExport {
    sessionId: string;
    agentId: string;
    tongue: TongueCode;
    state: BrowserSessionState;
    statistics: SessionStatistics;
    history: ActionHistoryEntry[];
    exportedAt: number;
}
export type SessionEvent = {
    type: 'session_start';
    sessionId: string;
} | {
    type: 'session_paused';
    sessionId: string;
} | {
    type: 'session_resumed';
    sessionId: string;
} | {
    type: 'session_end';
    sessionId: string;
    summary: SessionSummary;
} | {
    type: 'action_evaluated';
    sessionId: string;
    action: BrowserAction;
    governance: GovernanceResult;
    canExecute: boolean;
} | {
    type: 'action_completed';
    sessionId: string;
    entryId: string;
    success: boolean;
    duration: number;
} | {
    type: 'escalation_resolved';
    sessionId: string;
    requestId: string;
    decision: string;
    reviewer: string;
} | {
    type: 'history_imported';
    sessionId: string;
    importedCount: number;
};
export type SessionEventListener = (event: SessionEvent) => void;
/**
 * Create a new browser session.
 */
export declare function createBrowserSession(config: BrowserSessionConfig): BrowserSession;
/**
 * Create default session config.
 */
export declare function defaultSessionConfig(agentId: string, tongue?: TongueCode): BrowserSessionConfig;
//# sourceMappingURL=session.d.ts.map