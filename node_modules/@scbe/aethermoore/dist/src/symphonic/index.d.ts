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
export { Complex } from './Complex.js';
export { FFT, type FFTResult } from './FFT.js';
export { Feistel, createFeistel, type FeistelConfig, } from './Feistel.js';
export { ZBase32, getAlphabet } from './ZBase32.js';
export { SymphonicAgent, createSymphonicAgent, type SynthesisResult, type SymphonicAgentConfig, } from './SymphonicAgent.js';
export { HybridCrypto, createHybridCrypto, signIntent, verifyIntent, type HarmonicSignature, type SignedEnvelope, type VerificationResult, type HybridCryptoConfig, } from './HybridCrypto.js';
/**
 * Version of the Symphonic Cipher TypeScript implementation
 */
export declare const VERSION = "1.0.0";
/**
 * Quick sign function for simple use cases
 */
export declare function quickSign(intent: string, key: string): string;
/**
 * Quick verify function for simple use cases
 */
export declare function quickVerify(intent: string, signature: string, key: string): boolean;
//# sourceMappingURL=index.d.ts.map