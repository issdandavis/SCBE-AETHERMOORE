/**
 * L6-ADVERSARIAL Test Index
 *
 * @tier L6
 * @description NSA-level adversarial scenarios, cryptanalysis, formal verification
 * @level Cryptographer / Security Researcher
 *
 * Tests in this tier:
 * - failable-by-design.adversarial.test.ts: Failable-by-design attack simulation
 *
 * Run: npm test -- --testPathPattern="L6-adversarial"
 */

export const tier = 'L6-ADVERSARIAL';
export const level = 'Cryptographer / Security Researcher';
export const description = 'NSA-level adversarial scenarios, cryptanalysis, formal verification';
export const tests = [
  'failable-by-design.adversarial.test.ts'
];
