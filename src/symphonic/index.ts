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
export { Feistel, createFeistel, type FeistelConfig } from './Feistel.js';

// Z-Base-32 encoding
export { ZBase32, getAlphabet } from './ZBase32.js';

// Symphonic Agent (audio synthesis simulation)
export {
  SymphonicAgent,
  createSymphonicAgent,
  type SymphonicAgentConfig,
  type SynthesisResult,
} from './SymphonicAgent.js';

// Hybrid Crypto (main interface)
import { HybridCrypto as HybridCryptoClass } from './HybridCrypto.js';
export {
  HybridCrypto,
  createHybridCrypto,
  signIntent,
  verifyIntent,
  type HarmonicSignature,
  type HybridCryptoConfig,
  type SignedEnvelope,
  type VerificationResult,
} from './HybridCrypto.js';

// Re-export for internal use
const HybridCrypto = HybridCryptoClass;

/**
 * Version of the Symphonic Cipher TypeScript implementation
 */
export const VERSION = '1.0.0';

/**
 * Quick sign function for simple use cases
 */
export function quickSign(intent: string, key: string): string {
  return new HybridCrypto().signCompact(intent, key);
}

/**
 * Quick verify function for simple use cases
 */
export function quickVerify(intent: string, signature: string, key: string): boolean {
  const result = new HybridCrypto().verifyCompact(intent, signature, key);
  return result.valid;
}

// Dual-Channel Consensus (Audio Module)
export * from './audio/index.js';
