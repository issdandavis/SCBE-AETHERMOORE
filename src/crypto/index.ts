/**
 * @file index.ts
 * @module crypto
 * @component SCBE Cryptographic Module
 *
 * Core encryption and security primitives including:
 * - Post-Quantum Cryptography (ML-KEM-768, ML-DSA-65)
 * - Envelope encryption
 * - Key management
 * - Replay protection
 */

export * from './envelope.js';
export * from './hkdf.js';
export * from './jcs.js';
export * from './kms.js';
export * from './nonceManager.js';
export * from './replayGuard.js';
export * from './bloom.js';
export * from './pqc.js';
export * from './platform.js';
export * from './quantum-safe.js';
export * from './pqc-strategies.js';
export * from './aetherlex-seed.js';
