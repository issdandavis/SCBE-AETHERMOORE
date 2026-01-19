/**
 * SCBE Symphonic Cipher - TypeScript Implementation
 *
 * A complete port of the Python Symphonic Cipher to TypeScript,
 * providing feature parity for web and Node.js developers.
 *
 * Components:
 * - Complex: Complex number arithmetic for FFT
 * - FFT: Cooley-Tukey radix-2 Fast Fourier Transform
 * - Feistel: Balanced Feistel network for intent modulation
 * - ZBase32: Human-friendly encoding (Phil Zimmermann)
 * - SymphonicAgent: Audio synthesis simulation
 * - HybridCrypto: Unified signing/verification interface
 *
 * @module symphonic
 * @version 1.0.0
 */

// Complex number class
export { Complex } from './Complex.js';

// Fast Fourier Transform
export { FFT, type FFTResult } from './FFT.js';

// Feistel Network cipher
export {
  Feistel,
  createFeistel,
  type FeistelConfig,
} from './Feistel.js';

// Z-Base-32 encoding
export { ZBase32, getAlphabet } from './ZBase32.js';

// Symphonic Agent (audio synthesis simulation)
export {
  SymphonicAgent,
  createSymphonicAgent,
  type SynthesisResult,
  type SymphonicAgentConfig,
} from './SymphonicAgent.js';

// Hybrid Crypto (main interface)
export {
  HybridCrypto,
  createHybridCrypto,
  signIntent,
  verifyIntent,
  type HarmonicSignature,
  type SignedEnvelope,
  type VerificationResult,
  type HybridCryptoConfig,
} from './HybridCrypto.js';

/**
 * Version of the Symphonic Cipher TypeScript implementation
 */
export const VERSION = '1.0.0';

/**
 * Quick sign function for simple use cases
 */
export function quickSign(intent: string, key: string): string {
  const { HybridCrypto } = require('./HybridCrypto.js');
  return new HybridCrypto().signCompact(intent, key);
}

/**
 * Quick verify function for simple use cases
 */
export function quickVerify(intent: string, signature: string, key: string): boolean {
  const { HybridCrypto } = require('./HybridCrypto.js');
  const result = new HybridCrypto().verifyCompact(intent, signature, key);
  return result.valid;
}
