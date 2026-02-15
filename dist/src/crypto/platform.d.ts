/**
 * @file platform.ts
 * @module crypto/platform
 * @layer Layer 4
 * @component Platform-Agnostic Cryptographic Primitives
 * @version 1.0.0
 *
 * Provides secure random generation and hashing that works across:
 *   - Node.js (uses node:crypto)
 *   - Browsers (uses Web Crypto API / globalThis.crypto)
 *   - Edge runtimes (Cloudflare Workers, Deno, Bun)
 *
 * This resolves the platform mismatch identified in the architecture
 * audit: src/browser/ files imported Node's crypto.randomUUID() which
 * fails in browser contexts.
 *
 * All functions detect the runtime environment and select the best
 * available implementation, with no external dependencies.
 */
/** Current runtime environment */
export type CryptoRuntime = 'web' | 'node' | 'none';
/**
 * Detect the current crypto runtime.
 */
export declare function detectRuntime(): CryptoRuntime;
/**
 * Generate a cryptographically random UUID v4.
 *
 * Priority: globalThis.crypto.randomUUID → Node crypto.randomUUID → manual
 *
 * @returns UUID v4 string (e.g., "550e8400-e29b-41d4-a716-446655440000")
 */
export declare function platformRandomUUID(): string;
/**
 * Generate cryptographically secure random bytes.
 *
 * Priority: Web Crypto getRandomValues → Node crypto.randomBytes → Error
 *
 * @param length - Number of bytes to generate
 * @returns Uint8Array of random bytes
 * @throws Error if no secure random source is available
 */
export declare function platformRandomBytes(length: number): Uint8Array;
/**
 * Compute SHA-256 hash synchronously.
 *
 * Uses Node.js crypto.createHash when available.
 * For browser-only async hashing, use platformSHA256Async.
 *
 * @param data - Data to hash (string or Uint8Array)
 * @returns Hex-encoded SHA-256 hash
 * @throws Error if synchronous hashing is not available
 */
export declare function platformSHA256(data: string | Uint8Array): string;
/**
 * Compute SHA-256 hash asynchronously.
 *
 * Works in all environments: Web Crypto API (browser) and Node.js.
 *
 * @param data - Data to hash (string or Uint8Array)
 * @returns Hex-encoded SHA-256 hash
 */
export declare function platformSHA256Async(data: string | Uint8Array): Promise<string>;
/**
 * Constant-time comparison of two byte arrays.
 * Prevents timing attacks when comparing secrets.
 *
 * @param a - First array
 * @param b - Second array
 * @returns true if arrays are equal
 */
export declare function constantTimeEqual(a: Uint8Array, b: Uint8Array): boolean;
//# sourceMappingURL=platform.d.ts.map