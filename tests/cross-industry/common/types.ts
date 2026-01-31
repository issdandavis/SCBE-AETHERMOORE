/**
 * @file types.ts
 * @module tests/cross-industry/common
 * @description Shared types for cross-industry governance testing
 */

/**
 * Governance decision outcomes
 */
export type GovernanceDecision = 'ALLOW' | 'QUARANTINE' | 'DENY';

/**
 * Industry domains supported by the test suite
 */
export type Industry =
  | 'bank'
  | 'healthcare'
  | 'manufacturing'
  | 'autonomous-vehicle'
  | 'mlops'
  | 'public-sector';

/**
 * Attack types for red-team testing
 */
export type AttackType =
  | 'none'
  | 'replay'
  | 'tamper'
  | 'entropy'
  | 'time'
  | 'topology'
  | 'injection'
  | 'privilege-escalation';

/**
 * 6D context state vector
 */
export interface Context6D {
  identity: number[];      // Identity embedding
  intentPhase: number;     // Intent phase angle
  trajectory: number[];    // Trajectory coherence vector
  timestamp: number;       // Unix timestamp
  commitment: number;      // Commitment strength [0,1]
  signatureFlag: boolean;  // Has valid signature
}

/**
 * Extended 9D state vector
 */
export interface Context9D extends Context6D {
  timeFlow: number;        // Time flow rate deviation
  entropyDelta: number;    // Entropy change rate
  quantumState: number[];  // Quantum coherence vector
}

/**
 * Policy realm definition
 */
export interface PolicyRealm {
  id: string;
  center: number[];        // Hyperbolic center point
  radius: number;          // Trust radius in hyperbolic space
  allowedActions: string[];
  riskThreshold: number;
  requiresMultiSig: boolean;
  multiSigThreshold?: number;
}

/**
 * Sealed envelope structure
 */
export interface SealedEnvelope {
  version: string;
  nonce: string;
  timestamp: number;
  aad: Record<string, unknown>;
  ciphertext: string;
  tag: string;
  hmacChain: string;
  signatures: Record<string, string>;
}

/**
 * Governance test case definition
 */
export interface GovernanceTestCase {
  name: string;
  description: string;
  industry: Industry;
  context: Context6D | Context9D;
  policyRealm: PolicyRealm;
  envelope: Partial<SealedEnvelope>;
  expectedDecision: GovernanceDecision;
  expectedReasonContains: string[];
  attackLabel: AttackType;
}

/**
 * Governance result from the 14-layer pipeline
 */
export interface GovernanceResult {
  decision: GovernanceDecision;
  reason: string;
  riskScore: number;
  layerBreakdown: LayerResult[];
  timestamp: number;
}

/**
 * Individual layer processing result
 */
export interface LayerResult {
  layer: number;
  name: string;
  passed: boolean;
  score: number;
  details?: string;
}

/**
 * Test suite configuration
 */
export interface TestSuiteConfig {
  industry: Industry;
  strictMode: boolean;
  verbose: boolean;
  realms: PolicyRealm[];
}
