/**
 * Governance API - /govern endpoint
 *
 * Implements the AI governance decision engine.
 * All AI actions must pass through this endpoint before execution.
 *
 * @module api/govern
 */
import { TongueCode } from '../tokenizer/ss1.js';
/** Actor making the governance request */
export interface Actor {
    id: string;
    type: 'human' | 'ai' | 'system' | 'external';
    tongue?: TongueCode;
    trust_score?: number;
}
/** Resource being accessed */
export interface Resource {
    type: string;
    id: string;
    classification?: 'public' | 'internal' | 'confidential' | 'restricted';
    value_usd?: number;
    owner?: string;
}
/** Governance request */
export interface GovernanceRequest {
    actor: Actor;
    resource: Resource;
    intent: string;
    context?: Record<string, unknown>;
    nonce: string;
    urgency?: 'low' | 'normal' | 'high' | 'critical';
}
/** Governance decision */
export type Decision = 'ALLOW' | 'DENY' | 'ESCALATE' | 'QUARANTINE';
/** Governance response */
export interface GovernanceResponse {
    decision: Decision;
    request_id: string;
    timestamp: string;
    rationale: string;
    policy_ids: string[];
    risk_score: number;
    harmonic_cost: number;
    conditions?: string[];
    escalation?: {
        required_approvers: string[];
        timeout_seconds: number;
        fallback_decision: 'ALLOW' | 'DENY';
    };
    audit_id: string;
}
/** Policy definition */
export interface Policy {
    id: string;
    name: string;
    description?: string;
    enabled: boolean;
    priority: number;
    tongue?: TongueCode;
    evaluate: (request: GovernanceRequest) => PolicyResult;
}
/** Policy evaluation result */
export interface PolicyResult {
    applies: boolean;
    decision?: Decision;
    risk_modifier?: number;
    rationale?: string;
}
/**
 * Main governance decision function
 */
export declare function govern(request: GovernanceRequest): GovernanceResponse;
/**
 * List active policies
 */
export declare function listPolicies(): Omit<Policy, 'evaluate'>[];
/**
 * Get policy by ID
 */
export declare function getPolicy(id: string): Policy | undefined;
//# sourceMappingURL=govern.d.ts.map