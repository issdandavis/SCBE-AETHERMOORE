/**
 * Governance API - /govern endpoint
 *
 * Implements the AI governance decision engine.
 * All AI actions must pass through this endpoint before execution.
 *
 * @module api/govern
 */

import { createHash, randomUUID } from 'crypto';
import {
  hyperbolicDistance,
  harmonicWallCost,
  poincareNorm,
  calculateBFTQuorum,
  collectVotes,
  TONGUE_PHASES,
  TONGUE_INDICES,
  GOLDEN_RATIO,
} from '../agent/index.js';
import { TongueCode, TONGUE_CODES } from '../tokenizer/ss1.js';

// ============================================================================
// Types
// ============================================================================

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

// ============================================================================
// Built-in Policies
// ============================================================================

const POLICIES: Policy[] = [
  // High-value transaction policy
  {
    id: 'POL-001',
    name: 'High Value Transaction',
    description: 'Requires approval for transactions over $10,000',
    enabled: true,
    priority: 100,
    tongue: 'CA',
    evaluate: (req) => {
      const value = req.resource.value_usd ?? 0;
      if (value > 50000) {
        return {
          applies: true,
          decision: 'ESCALATE',
          risk_modifier: 0.3,
          rationale: `Transaction value $${value} exceeds $50,000 threshold`,
        };
      }
      if (value > 10000) {
        return {
          applies: true,
          risk_modifier: 0.15,
          rationale: `Transaction value $${value} requires additional scrutiny`,
        };
      }
      return { applies: false };
    },
  },

  // Confidential data access policy
  {
    id: 'POL-002',
    name: 'Confidential Data Access',
    description: 'Controls access to confidential resources',
    enabled: true,
    priority: 95,
    tongue: 'UM',
    evaluate: (req) => {
      if (req.resource.classification === 'restricted') {
        if (req.actor.type === 'ai') {
          return {
            applies: true,
            decision: 'DENY',
            risk_modifier: 0.5,
            rationale: 'AI agents cannot access restricted resources',
          };
        }
        return {
          applies: true,
          decision: 'ESCALATE',
          risk_modifier: 0.4,
          rationale: 'Restricted resource access requires human approval',
        };
      }
      if (req.resource.classification === 'confidential' && req.actor.type === 'ai') {
        return {
          applies: true,
          risk_modifier: 0.2,
          rationale: 'AI accessing confidential data',
        };
      }
      return { applies: false };
    },
  },

  // Auto-approval restrictions
  {
    id: 'POL-003',
    name: 'Auto-Approval Limits',
    description: 'Restricts what AI can auto-approve',
    enabled: true,
    priority: 90,
    tongue: 'RU',
    evaluate: (req) => {
      if (req.intent === 'auto_approve' && req.actor.type === 'ai') {
        const value = req.resource.value_usd ?? 0;
        if (value > 5000) {
          return {
            applies: true,
            decision: 'ESCALATE',
            risk_modifier: 0.25,
            rationale: `AI cannot auto-approve transactions over $5,000 (requested: $${value})`,
          };
        }
        if (req.resource.type === 'contract') {
          return {
            applies: true,
            decision: 'ESCALATE',
            risk_modifier: 0.2,
            rationale: 'Contracts require human approval',
          };
        }
      }
      return { applies: false };
    },
  },

  // Delete operations
  {
    id: 'POL-004',
    name: 'Destructive Operations',
    description: 'Controls delete/destroy operations',
    enabled: true,
    priority: 85,
    tongue: 'DR',
    evaluate: (req) => {
      if (['delete', 'destroy', 'remove', 'purge'].includes(req.intent)) {
        if (req.actor.type === 'ai') {
          return {
            applies: true,
            decision: 'DENY',
            risk_modifier: 0.6,
            rationale: 'AI agents cannot perform destructive operations',
          };
        }
        return {
          applies: true,
          decision: 'ESCALATE',
          risk_modifier: 0.35,
          rationale: 'Destructive operations require confirmation',
        };
      }
      return { applies: false };
    },
  },

  // Trust score check
  {
    id: 'POL-005',
    name: 'Low Trust Actor',
    description: 'Restricts low-trust actors',
    enabled: true,
    priority: 80,
    tongue: 'KO',
    evaluate: (req) => {
      const trust = req.actor.trust_score ?? 0.5;
      if (trust < 0.3) {
        return {
          applies: true,
          decision: 'QUARANTINE',
          risk_modifier: 0.5,
          rationale: `Actor trust score ${trust.toFixed(2)} below threshold`,
        };
      }
      if (trust < 0.5) {
        return {
          applies: true,
          risk_modifier: 0.15,
          rationale: `Actor trust score ${trust.toFixed(2)} is marginal`,
        };
      }
      return { applies: false };
    },
  },
];

// ============================================================================
// Nonce Tracking (Replay Protection)
// ============================================================================

const usedNonces = new Set<string>();
const NONCE_MAX_AGE_MS = 5 * 60 * 1000; // 5 minutes
const nonceTimestamps = new Map<string, number>();

function consumeNonce(nonce: string): boolean {
  // Clean old nonces
  const now = Date.now();
  for (const [n, timestamp] of nonceTimestamps) {
    if (now - timestamp > NONCE_MAX_AGE_MS) {
      usedNonces.delete(n);
      nonceTimestamps.delete(n);
    }
  }

  if (usedNonces.has(nonce)) {
    return false; // Replay detected
  }

  usedNonces.add(nonce);
  nonceTimestamps.set(nonce, now);
  return true;
}

// ============================================================================
// Risk Calculation
// ============================================================================

/**
 * Map actor/resource to position in Poincaré ball
 *
 * Uses hash of identifiers to create deterministic position
 */
function actorToPosition(actor: Actor): { x: number; y: number; z: number } {
  const hash = createHash('sha256').update(actor.id).update(actor.type).digest();

  // Map hash bytes to position in ball (radius < 0.9)
  const x = ((hash[0] / 255) * 2 - 1) * 0.7;
  const y = ((hash[1] / 255) * 2 - 1) * 0.7;
  const z = ((hash[2] / 255) * 2 - 1) * 0.7;

  return { x, y, z };
}

function resourceToPosition(resource: Resource): { x: number; y: number; z: number } {
  const hash = createHash('sha256').update(resource.type).update(resource.id).digest();

  // Resources closer to boundary = higher risk
  const classification = resource.classification ?? 'internal';
  const radiusMultiplier = {
    public: 0.3,
    internal: 0.5,
    confidential: 0.7,
    restricted: 0.85,
  }[classification];

  const x = ((hash[0] / 255) * 2 - 1) * radiusMultiplier;
  const y = ((hash[1] / 255) * 2 - 1) * radiusMultiplier;
  const z = ((hash[2] / 255) * 2 - 1) * radiusMultiplier;

  return { x, y, z };
}

/**
 * Calculate risk score using hyperbolic geometry
 */
function calculateRisk(request: GovernanceRequest, policyRiskModifier: number): number {
  const actorPos = actorToPosition(request.actor);
  const resourcePos = resourceToPosition(request.resource);

  // Hyperbolic distance between actor and resource
  const distance = hyperbolicDistance(actorPos, resourcePos);

  // Base risk from distance
  let risk = Math.min(1, distance / 3);

  // Adjust for actor trust
  const trust = request.actor.trust_score ?? 0.5;
  risk = risk * (1.5 - trust);

  // Adjust for urgency (high urgency = slightly higher risk)
  const urgencyMultiplier = {
    low: 0.9,
    normal: 1.0,
    high: 1.1,
    critical: 1.2,
  }[request.urgency ?? 'normal'];

  risk = risk * urgencyMultiplier;

  // Add policy-based risk
  risk = Math.min(1, risk + policyRiskModifier);

  return risk;
}

// ============================================================================
// Governance Engine
// ============================================================================

/**
 * Main governance decision function
 */
export function govern(request: GovernanceRequest): GovernanceResponse {
  const requestId = randomUUID();
  const auditId = randomUUID();
  const timestamp = new Date().toISOString();

  // Replay protection
  if (!consumeNonce(request.nonce)) {
    return {
      decision: 'DENY',
      request_id: requestId,
      timestamp,
      rationale: 'Nonce already used (replay attack detected)',
      policy_ids: [],
      risk_score: 1.0,
      harmonic_cost: Infinity,
      audit_id: auditId,
    };
  }

  // Evaluate policies
  const appliedPolicies: string[] = [];
  let policyDecision: Decision | null = null;
  let totalRiskModifier = 0;
  const rationales: string[] = [];
  let escalationRequired = false;

  for (const policy of POLICIES.filter((p) => p.enabled).sort((a, b) => b.priority - a.priority)) {
    const result = policy.evaluate(request);

    if (result.applies) {
      appliedPolicies.push(policy.id);

      if (result.risk_modifier) {
        totalRiskModifier += result.risk_modifier;
      }

      if (result.rationale) {
        rationales.push(`[${policy.id}] ${result.rationale}`);
      }

      // Higher priority policies override decision
      if (result.decision && !policyDecision) {
        policyDecision = result.decision;
        if (result.decision === 'ESCALATE') {
          escalationRequired = true;
        }
      }
    }
  }

  // Calculate risk score
  const riskScore = calculateRisk(request, totalRiskModifier);

  // Calculate harmonic wall cost
  const harmonicCost = harmonicWallCost(riskScore * 3); // Scale for meaningful cost

  // Determine final decision
  let finalDecision: Decision;
  if (policyDecision) {
    finalDecision = policyDecision;
  } else if (riskScore > 0.8) {
    finalDecision = 'DENY';
    rationales.push(`Risk score ${riskScore.toFixed(3)} exceeds threshold`);
  } else if (riskScore > 0.6) {
    finalDecision = 'ESCALATE';
    escalationRequired = true;
    rationales.push(`Risk score ${riskScore.toFixed(3)} requires review`);
  } else if (riskScore > 0.4) {
    finalDecision = 'ALLOW';
    rationales.push(`Risk score ${riskScore.toFixed(3)} acceptable with monitoring`);
  } else {
    finalDecision = 'ALLOW';
    rationales.push(`Risk score ${riskScore.toFixed(3)} within safe bounds`);
  }

  // Build response
  const response: GovernanceResponse = {
    decision: finalDecision,
    request_id: requestId,
    timestamp,
    rationale: rationales.join('; '),
    policy_ids: appliedPolicies,
    risk_score: riskScore,
    harmonic_cost: harmonicCost,
    audit_id: auditId,
  };

  // Add escalation details if needed
  if (escalationRequired && finalDecision === 'ESCALATE') {
    response.escalation = {
      required_approvers: ['security-team', 'manager'],
      timeout_seconds: 3600,
      fallback_decision: 'DENY',
    };
  }

  // Add conditions for conditional allows
  if (finalDecision === 'ALLOW' && riskScore > 0.3) {
    response.conditions = ['Action will be logged', 'Subject to audit review'];
  }

  return response;
}

/**
 * List active policies
 */
export function listPolicies(): Omit<Policy, 'evaluate'>[] {
  return POLICIES.map(({ evaluate, ...rest }) => rest);
}

/**
 * Get policy by ID
 */
export function getPolicy(id: string): Policy | undefined {
  return POLICIES.find((p) => p.id === id);
}
