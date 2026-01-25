/**
 * L4-PROPERTY Test Index
 *
 * @tier L4
 * @description Property-based testing with random inputs
 * @level Staff Engineer
 * @requires fast-check
 *
 * Tests in this tier:
 * - mathematical-invariants.property.test.ts: Parseval, phase invariance, geometry
 *
 * Run: npm test -- --testPathPattern="L4-property"
 */

export const tier = 'L4-PROPERTY';
export const level = 'Staff Engineer';
export const description = 'Property-based testing with random inputs';
export const tests = [
  'mathematical-invariants.property.test.ts'
];
