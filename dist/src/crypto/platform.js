"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.detectRuntime = detectRuntime;
exports.platformRandomUUID = platformRandomUUID;
exports.platformRandomBytes = platformRandomBytes;
exports.platformSHA256 = platformSHA256;
exports.platformSHA256Async = platformSHA256Async;
exports.constantTimeEqual = constantTimeEqual;
// ═══════════════════════════════════════════════════════════════
// Runtime Detection
// ═══════════════════════════════════════════════════════════════
/** Detect if Web Crypto API is available */
function hasWebCrypto() {
    return (typeof globalThis !== 'undefined' &&
        typeof globalThis.crypto !== 'undefined' &&
        typeof globalThis.crypto.getRandomValues === 'function');
}
/** Detect if Node.js crypto module is available */
function hasNodeCrypto() {
    try {
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        return typeof require !== 'undefined' && typeof require('crypto') !== 'undefined';
    }
    catch {
        return false;
    }
}
/**
 * Detect the current crypto runtime.
 */
function detectRuntime() {
    if (hasWebCrypto())
        return 'web';
    if (hasNodeCrypto())
        return 'node';
    return 'none';
}
// ═══════════════════════════════════════════════════════════════
// UUID Generation
// ═══════════════════════════════════════════════════════════════
/**
 * Generate a cryptographically random UUID v4.
 *
 * Priority: globalThis.crypto.randomUUID → Node crypto.randomUUID → manual
 *
 * @returns UUID v4 string (e.g., "550e8400-e29b-41d4-a716-446655440000")
 */
function platformRandomUUID() {
    // Web Crypto API (Chrome 92+, Firefox 95+, Node 19+)
    if (typeof globalThis !== 'undefined' &&
        typeof globalThis.crypto !== 'undefined' &&
        typeof globalThis.crypto.randomUUID === 'function') {
        return globalThis.crypto.randomUUID();
    }
    // Node.js crypto module
    if (hasNodeCrypto()) {
        try {
            // eslint-disable-next-line @typescript-eslint/no-require-imports
            const nodeCrypto = require('crypto');
            if (typeof nodeCrypto.randomUUID === 'function') {
                return nodeCrypto.randomUUID();
            }
        }
        catch {
            // Fall through to manual generation
        }
    }
    // Manual UUID v4 generation using available randomness
    const bytes = platformRandomBytes(16);
    // Set version (4) and variant (10xx) bits per RFC 4122
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    const hex = Array.from(bytes)
        .map((b) => b.toString(16).padStart(2, '0'))
        .join('');
    return [
        hex.slice(0, 8),
        hex.slice(8, 12),
        hex.slice(12, 16),
        hex.slice(16, 20),
        hex.slice(20, 32),
    ].join('-');
}
// ═══════════════════════════════════════════════════════════════
// Secure Random Bytes
// ═══════════════════════════════════════════════════════════════
/**
 * Generate cryptographically secure random bytes.
 *
 * Priority: Web Crypto getRandomValues → Node crypto.randomBytes → Error
 *
 * @param length - Number of bytes to generate
 * @returns Uint8Array of random bytes
 * @throws Error if no secure random source is available
 */
function platformRandomBytes(length) {
    if (length <= 0)
        return new Uint8Array(0);
    // Web Crypto API
    if (hasWebCrypto()) {
        const buffer = new Uint8Array(length);
        // getRandomValues has a 65536-byte limit; chunk if needed
        for (let offset = 0; offset < length; offset += 65536) {
            const chunkSize = Math.min(65536, length - offset);
            globalThis.crypto.getRandomValues(buffer.subarray(offset, offset + chunkSize));
        }
        return buffer;
    }
    // Node.js crypto
    if (hasNodeCrypto()) {
        try {
            // eslint-disable-next-line @typescript-eslint/no-require-imports
            const nodeCrypto = require('crypto');
            const buf = nodeCrypto.randomBytes(length);
            return new Uint8Array(buf.buffer, buf.byteOffset, buf.byteLength);
        }
        catch {
            // Fall through
        }
    }
    throw new Error('No secure random source available. ' +
        'Requires Web Crypto API (browser) or Node.js crypto module.');
}
// ═══════════════════════════════════════════════════════════════
// SHA-256 Hashing
// ═══════════════════════════════════════════════════════════════
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
function platformSHA256(data) {
    if (hasNodeCrypto()) {
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const nodeCrypto = require('crypto');
        const hash = nodeCrypto.createHash('sha256');
        hash.update(typeof data === 'string' ? data : Buffer.from(data));
        return hash.digest('hex');
    }
    throw new Error('Synchronous SHA-256 not available in this runtime. Use platformSHA256Async instead.');
}
/**
 * Compute SHA-256 hash asynchronously.
 *
 * Works in all environments: Web Crypto API (browser) and Node.js.
 *
 * @param data - Data to hash (string or Uint8Array)
 * @returns Hex-encoded SHA-256 hash
 */
async function platformSHA256Async(data) {
    const bytes = typeof data === 'string' ? new TextEncoder().encode(data) : data;
    // Web Crypto API (async)
    if (typeof globalThis !== 'undefined' &&
        typeof globalThis.crypto !== 'undefined' &&
        typeof globalThis.crypto.subtle !== 'undefined') {
        const hashBuffer = await globalThis.crypto.subtle.digest('SHA-256', bytes);
        return Array.from(new Uint8Array(hashBuffer))
            .map((b) => b.toString(16).padStart(2, '0'))
            .join('');
    }
    // Node.js fallback
    if (hasNodeCrypto()) {
        return platformSHA256(data);
    }
    throw new Error('No SHA-256 implementation available.');
}
// ═══════════════════════════════════════════════════════════════
// Constant-Time Comparison
// ═══════════════════════════════════════════════════════════════
/**
 * Constant-time comparison of two byte arrays.
 * Prevents timing attacks when comparing secrets.
 *
 * @param a - First array
 * @param b - Second array
 * @returns true if arrays are equal
 */
function constantTimeEqual(a, b) {
    if (a.length !== b.length)
        return false;
    // Node.js timingSafeEqual
    if (hasNodeCrypto()) {
        try {
            // eslint-disable-next-line @typescript-eslint/no-require-imports
            const nodeCrypto = require('crypto');
            return nodeCrypto.timingSafeEqual(Buffer.from(a), Buffer.from(b));
        }
        catch {
            // Fall through to manual implementation
        }
    }
    // Manual constant-time comparison
    let result = 0;
    for (let i = 0; i < a.length; i++) {
        result |= a[i] ^ b[i];
    }
    return result === 0;
}
//# sourceMappingURL=platform.js.map