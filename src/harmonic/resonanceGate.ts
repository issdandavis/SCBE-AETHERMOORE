/**
 * Re-export the canonical resonance gate from the kernel package.
 *
 * This keeps the public src/ import path stable while ensuring Layer 12 and
 * Layer 14 integrations use a single implementation.
 */

export * from '../../packages/kernel/src/resonanceGate.js';
