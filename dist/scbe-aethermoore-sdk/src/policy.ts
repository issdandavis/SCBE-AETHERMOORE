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

import { PolicyError, PolicyLevel, PolicyMatrix, TongueID } from './types';

/**
 * Default policy matrix
 * 
 * - standard: Any valid signature
 * - strict: Requires RU (Policy) tongue
 * - secret: Requires UM (Security) tongue
 * - critical: Requires RU + UM + DR (Policy + Security + Structure)
 */
export const POLICY_MATRIX: PolicyMatrix = {
  standard: [],                    // Any valid signature
  strict: ['ru'],                  // Requires Policy tongue
  secret: ['um'],                  // Requires Security tongue
  critical: ['ru', 'um', 'dr'],    // Requires Policy + Security + Structure
};

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
export function enforcePolicy(
  validTongues: TongueID[],
  policy: PolicyLevel = 'standard'
): boolean {
  const required = POLICY_MATRIX[policy];
  
  // Standard policy: any valid signature
  if (required.length === 0) {
    if (validTongues.length === 0) {
      throw new PolicyError('No valid signatures found');
    }
    return true;
  }
  
  // Check if all required tongues are present
  const missing = required.filter(t => !validTongues.includes(t));
  
  if (missing.length > 0) {
    throw new PolicyError(
      `Policy '${policy}' requires tongues [${required.join(', ')}], ` +
      `but missing [${missing.join(', ')}]. ` +
      `Valid tongues: [${validTongues.join(', ')}]`
    );
  }
  
  return true;
}

/**
 * Get required tongues for a policy level
 * 
 * @param policy - Policy level
 * @returns Array of required tongue IDs
 */
export function getRequiredTongues(policy: PolicyLevel): TongueID[] {
  return POLICY_MATRIX[policy];
}

/**
 * Check if a set of tongues satisfies a policy (without throwing)
 * 
 * @param validTongues - List of tongues that passed verification
 * @param policy - Policy level to check
 * @returns true if policy is satisfied, false otherwise
 */
export function checkPolicy(
  validTongues: TongueID[],
  policy: PolicyLevel = 'standard'
): boolean {
  try {
    return enforcePolicy(validTongues, policy);
  } catch {
    return false;
  }
}

/**
 * Get policy level description
 * 
 * @param policy - Policy level
 * @returns Human-readable description
 */
export function getPolicyDescription(policy: PolicyLevel): string {
  const descriptions: Record<PolicyLevel, string> = {
    standard: 'Any valid signature',
    strict: 'Requires Policy (RU) tongue signature',
    secret: 'Requires Security (UM) tongue signature',
    critical: 'Requires Policy (RU) + Security (UM) + Structure (DR) signatures',
  };
  return descriptions[policy];
}

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
export function suggestPolicy(operation: string): PolicyLevel {
  const op = operation.toLowerCase();
  
  // Critical operations
  if (op.includes('deploy') || op.includes('grant') || op.includes('revoke') ||
      op.includes('delete_resource') || op.includes('modify_permission')) {
    return 'critical';
  }
  
  // Secret operations
  if (op.includes('delete') || op.includes('secret') || op.includes('credential') ||
      op.includes('key') || op.includes('password')) {
    return 'secret';
  }
  
  // Strict operations
  if (op.includes('write') || op.includes('update') || op.includes('create') ||
      op.includes('modify') || op.includes('config')) {
    return 'strict';
  }
  
  // Standard operations (read, query, list, etc.)
  return 'standard';
}
