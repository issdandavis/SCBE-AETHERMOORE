/**
 * SCBE Browser Action Evaluator
 * ==============================
 *
 * Evaluates browser actions through the SCBE 14-layer governance pipeline.
 *
 * Pipeline flow:
 * 1. Action → Semantic encoding (Polyglot L1-2)
 * 2. Position encoding (Aethercode L4 Poincaré)
 * 3. Hyperbolic distance metrics (L5)
 * 4. Harmonic scaling (L12)
 * 5. Risk decision (L13 with Hive Memory)
 * 6. 4-tier decision: ALLOW / QUARANTINE / ESCALATE / DENY
 *
 * @module browser/evaluator
 * @layer Layers 1-14 (full pipeline)
 * @version 3.0.0
 */
import { BrowserAction, BrowserObservation, GovernanceResult, DomainRiskCategory } from './types.js';
/** Governance thresholds */
declare const THRESHOLDS: {
    /** Below this: ALLOW */
    allow: number;
    /** Below this: QUARANTINE (with monitoring) */
    quarantine: number;
    /** Below this: ESCALATE (needs human/AI review) */
    escalate: number;
    /** Above this: DENY */
    deny: number;
};
/**
 * Encode a browser action into the semantic space using Polyglot encoding.
 *
 * This implements Layers 1-2:
 * - Layer 1: Complex state (amplitude = sensitivity, phase = action type)
 * - Layer 2: Realification to ℝ^{2D}
 */
declare function encodeActionSemantic(action: BrowserAction, observation: BrowserObservation): {
    complex: {
        real: number[];
        imag: number[];
    };
    realified: number[];
};
/**
 * Encode session state into Poincaré ball position.
 *
 * This represents the agent's "location" in governance space.
 */
declare function encodeSessionPosition(sessionRisk: number, actionCount: number, errorCount: number, domainRisk: number): number[];
/**
 * Classify domain from URL.
 */
declare function classifyDomain(url: string): DomainRiskCategory;
/**
 * Compute combined risk score using 14-layer pipeline.
 */
declare function computeRiskScore(action: BrowserAction, observation: BrowserObservation, sessionState: {
    sessionRisk: number;
    actionCount: number;
    errorCount: number;
}): {
    score: number;
    factors: GovernanceResult['riskFactors'];
    pipelineOutputs: Record<string, unknown>;
};
export interface EvaluatorOptions {
    /** Override thresholds */
    thresholds?: Partial<typeof THRESHOLDS>;
    /** Enable debug pipeline outputs */
    debug?: boolean;
}
/**
 * SCBE Browser Action Evaluator.
 *
 * Processes browser actions through the 14-layer governance pipeline.
 */
export declare class BrowserActionEvaluator {
    private thresholds;
    private debug;
    constructor(options?: EvaluatorOptions);
    /**
     * Evaluate a browser action through the SCBE pipeline.
     *
     * @param action - The action to evaluate
     * @param observation - Current browser observation
     * @param sessionState - Current session state
     * @returns Governance result with decision
     */
    evaluate(action: BrowserAction, observation: BrowserObservation, sessionState: {
        sessionRisk: number;
        actionCount: number;
        errorCount: number;
    }): GovernanceResult;
    /**
     * Batch evaluate multiple actions.
     */
    evaluateBatch(actions: BrowserAction[], observation: BrowserObservation, sessionState: {
        sessionRisk: number;
        actionCount: number;
        errorCount: number;
    }): GovernanceResult[];
    /**
     * Check if a token is valid.
     */
    validateToken(token: string, decisionId: string, action: BrowserAction): boolean;
    /**
     * Generate execution token for allowed actions.
     */
    private generateToken;
}
export { computeRiskScore, classifyDomain, encodeActionSemantic, encodeSessionPosition };
//# sourceMappingURL=evaluator.d.ts.map