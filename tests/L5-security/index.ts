/**
 * L5-SECURITY Test Index
 *
 * @tier L5
 * @description Security boundaries, compliance, cryptographic correctness
 * @level Security Engineer
 *
 * Tests in this tier:
 * - crypto-boundaries.security.test.ts: Cryptographic boundary enforcement
 *
 * Run: npm test -- --testPathPattern="L5-security"
 */

export const tier = 'L5-SECURITY';
export const level = 'Security Engineer';
export const description = 'Security boundaries, compliance, cryptographic correctness';
export const tests = [
  'crypto-boundaries.security.test.ts'
];
