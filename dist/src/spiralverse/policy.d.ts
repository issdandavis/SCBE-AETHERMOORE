/**
 * RWP v2.1 Policy Matrix
 * ======================
 *
 * Policy enforcement for multi-signature envelopes.
 *
 * @module spiralverse/policy
 * @version 2.1.0
 * @since 2026-01-18
 */
import { PolicyLevel, PolicyMatrix, TongueID } from './types';
/**
 * Default policy matrix
 *
 * - standard: Any valid signature
 * - strict: Requires RU (Policy) tongue
 * - secret: Requires UM (Security) tongue
 * - critical: Requires RU + UM + DR (Policy + Security + Structure)
 */
export declare const POLICY_MATRIX: PolicyMatrix;
/**
 * Check if valid tongues satisfy a policy level
 *
 * @param validTongues - List of tongues that passed verification
 * @param policy - Policy level to enforce
 * @returns true if policy is satisfied
 * @throws PolicyError if policy is not satisfied
 *
 * @example
 * ```typescript
 * enforcePolicy(['ko', 'av'], 'standard');  // OK - any valid signature
 * enforcePolicy(['ru', 'um'], 'strict');    // OK - has RU
 * enforcePolicy(['ko', 'av'], 'strict');    // Error - missing RU
 * enforcePolicy(['ru', 'um', 'dr'], 'critical');  // OK - has all three
 * ```
 */
export declare function enforcePolicy(validTongues: TongueID[], policy?: PolicyLevel): boolean;
/**
 * Get required tongues for a policy level
 *
 * @param policy - Policy level
 * @returns Array of required tongue IDs
 */
export declare function getRequiredTongues(policy: PolicyLevel): TongueID[];
/**
 * Check if a set of tongues satisfies a policy (without throwing)
 *
 * @param validTongues - List of tongues that passed verification
 * @param policy - Policy level to check
 * @returns true if policy is satisfied, false otherwise
 */
export declare function checkPolicy(validTongues: TongueID[], policy?: PolicyLevel): boolean;
/**
 * Get policy level description
 *
 * @param policy - Policy level
 * @returns Human-readable description
 */
export declare function getPolicyDescription(policy: PolicyLevel): string;
/**
 * Suggest appropriate policy level based on operation type
 *
 * @param operation - Type of operation
 * @returns Recommended policy level
 *
 * @example
 * ```typescript
 * suggestPolicy('read');        // 'standard'
 * suggestPolicy('write');       // 'strict'
 * suggestPolicy('delete');      // 'secret'
 * suggestPolicy('deploy');      // 'critical'
 * suggestPolicy('grant_access'); // 'critical'
 * ```
 */
export declare function suggestPolicy(operation: string): PolicyLevel;
//# sourceMappingURL=policy.d.ts.map