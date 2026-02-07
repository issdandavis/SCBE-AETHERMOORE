"use strict";
/**
 * @file encryptedTransport.ts
 * @module harmonic/encryptedTransport
 * @layer Layer 5, Layer 12, Layer 13
 * @component Encrypted Vector Transport
 * @version 1.0.0
 * @since 2026-02-07
 *
 * Separates encryption from navigation in the Poincaré ball.
 *
 * CRITICAL DESIGN PRINCIPLE:
 * Encrypted vectors are opaque ciphertext — NOT valid Poincaré ball points.
 * You CANNOT perform Möbius addition on ciphertext because encryption destroys
 * the geometric structure (‖p‖ < 1, gyrovector algebra, etc.).
 *
 * Correct pattern:
 *   1. Encrypt vectors for transport/storage (ciphertext is opaque bytes)
 *   2. Decrypt back to plaintext vectors before any geometric operations
 *   3. Perform Möbius addition / hyperbolic distance on plaintext only
 *   4. Re-encrypt result if it needs to travel again
 *
 * This module provides the encrypt-transport-decrypt-navigate pipeline.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.generateTransportKey = generateTransportKey;
exports.encryptVector = encryptVector;
exports.decryptVector = decryptVector;
exports.secureNavigate = secureNavigate;
exports.secureBatchNavigate = secureBatchNavigate;
exports.encryptPosition = encryptPosition;
exports.decryptPosition = decryptPosition;
const node_crypto_1 = require("node:crypto");
const hyperbolic_js_1 = require("./hyperbolic.js");
// ═══════════════════════════════════════════════════════════════
// Base64URL helpers
// ═══════════════════════════════════════════════════════════════
function b64u(buf) {
    return buf.toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}
function fromB64u(s) {
    let padded = s.replace(/-/g, '+').replace(/_/g, '/');
    while (padded.length % 4)
        padded += '=';
    return Buffer.from(padded, 'base64');
}
// ═══════════════════════════════════════════════════════════════
// Key Management
// ═══════════════════════════════════════════════════════════════
/**
 * Generate a transport key for encrypting Poincaré ball vectors.
 *
 * @param domain - Domain label for key separation (e.g., 'navigation', 'storage')
 * @returns A VectorTransportKey with a random 256-bit AES key
 */
function generateTransportKey(domain = 'navigation') {
    const key = (0, node_crypto_1.randomBytes)(32);
    const kid = (0, node_crypto_1.createHash)('sha256')
        .update(key)
        .update(domain)
        .digest('hex')
        .slice(0, 16);
    return {
        key,
        kid,
        createdAt: Date.now(),
    };
}
// ═══════════════════════════════════════════════════════════════
// Vector Serialization
// ═══════════════════════════════════════════════════════════════
/**
 * Serialize a number[] vector to a Buffer using Float64 encoding.
 * This preserves full double-precision floating point accuracy.
 */
function serializeVector(v) {
    const buf = Buffer.alloc(v.length * 8);
    for (let i = 0; i < v.length; i++) {
        buf.writeDoubleBE(v[i], i * 8);
    }
    return buf;
}
/**
 * Deserialize a Buffer back to a number[] vector.
 */
function deserializeVector(buf, dimension) {
    if (buf.length !== dimension * 8) {
        throw new Error(`Vector deserialization size mismatch: got ${buf.length} bytes, expected ${dimension * 8}`);
    }
    const v = [];
    for (let i = 0; i < dimension; i++) {
        v.push(buf.readDoubleBE(i * 8));
    }
    return v;
}
// ═══════════════════════════════════════════════════════════════
// Encrypt / Decrypt
// ═══════════════════════════════════════════════════════════════
/**
 * Encrypt a Poincaré ball vector for transport.
 *
 * The resulting EncryptedVector is opaque ciphertext — it is NOT a valid
 * Poincaré ball point. Do NOT pass it to mobiusAdd, hyperbolicDistance,
 * or any geometric operation.
 *
 * @param vector - Plaintext vector in the Poincaré ball (‖v‖ < 1)
 * @param transportKey - Symmetric key for encryption
 * @param domain - Domain label bound into the AAD
 * @returns Opaque EncryptedVector
 */
function encryptVector(vector, transportKey, domain = 'poincare-transport') {
    if (!vector || vector.length === 0) {
        throw new Error('Cannot encrypt empty vector');
    }
    // Serialize vector to bytes
    const plaintext = serializeVector(vector);
    // Random 96-bit nonce
    const nonce = (0, node_crypto_1.randomBytes)(12);
    // AAD binds domain + dimension to prevent cross-context attacks
    const aad = Buffer.from(`scbe:vector:${domain}:dim=${vector.length}`);
    // AES-256-GCM encryption
    const cipher = (0, node_crypto_1.createCipheriv)('aes-256-gcm', transportKey.key, nonce);
    cipher.setAAD(aad);
    const ct = Buffer.concat([cipher.update(plaintext), cipher.final()]);
    const tag = cipher.getAuthTag();
    return {
        ciphertext: b64u(ct),
        nonce: b64u(nonce),
        tag: b64u(tag),
        dimension: vector.length,
        domain,
    };
}
/**
 * Decrypt an EncryptedVector back to a plaintext Poincaré ball vector.
 *
 * Validates that the decrypted vector has finite components and is inside
 * the Poincaré ball (‖v‖ < 1). Throws on auth failure, corruption, or
 * if the decrypted vector is not a valid ball point.
 *
 * @param encrypted - Opaque EncryptedVector from encryptVector()
 * @param transportKey - Same symmetric key used for encryption
 * @param validateBall - If true (default), verify ‖v‖ < 1
 * @returns Plaintext vector suitable for Möbius operations
 */
function decryptVector(encrypted, transportKey, validateBall = true) {
    const nonce = fromB64u(encrypted.nonce);
    const tag = fromB64u(encrypted.tag);
    const ct = fromB64u(encrypted.ciphertext);
    const aad = Buffer.from(`scbe:vector:${encrypted.domain}:dim=${encrypted.dimension}`);
    if (nonce.length !== 12) {
        throw new Error('Invalid nonce size for vector decryption');
    }
    // AES-256-GCM decryption
    const decipher = (0, node_crypto_1.createDecipheriv)('aes-256-gcm', transportKey.key, nonce);
    decipher.setAAD(aad);
    decipher.setAuthTag(tag);
    let plaintext;
    try {
        plaintext = Buffer.concat([decipher.update(ct), decipher.final()]);
    }
    catch {
        throw new Error('Vector decryption auth failed: ciphertext tampered or wrong key');
    }
    // Deserialize
    const vector = deserializeVector(plaintext, encrypted.dimension);
    // Validate finiteness
    for (let i = 0; i < vector.length; i++) {
        if (!isFinite(vector[i])) {
            throw new Error(`Decrypted vector component ${i} is not finite`);
        }
    }
    // Validate ball membership
    if (validateBall) {
        const normSq = vector.reduce((sum, x) => sum + x * x, 0);
        if (normSq >= 1) {
            throw new Error(`Decrypted vector is outside the Poincaré ball: ‖v‖² = ${normSq.toFixed(6)} >= 1`);
        }
    }
    return vector;
}
// ═══════════════════════════════════════════════════════════════
// Secure Navigation (decrypt-then-navigate)
// ═══════════════════════════════════════════════════════════════
/**
 * Decrypt an encrypted step vector, then apply Möbius addition to navigate.
 *
 * This is the CORRECT way to combine encryption with hyperbolic navigation:
 *   1. Decrypt the step vector from its encrypted transport form
 *   2. Validate it's a proper Poincaré ball vector
 *   3. Apply Möbius addition: new_position = position ⊕ step
 *   4. Project result back into the ball (safety clamp)
 *
 * @param currentPosition - Current position in the Poincaré ball (plaintext)
 * @param encryptedStep - Encrypted navigation step vector
 * @param transportKey - Symmetric key for decryption
 * @param maxNorm - Maximum allowed norm after navigation (default 1 - ε)
 * @returns Navigation result with new position
 */
function secureNavigate(currentPosition, encryptedStep, transportKey, maxNorm = 1 - 1e-10) {
    // Step 1: Decrypt the step vector (validates ball membership)
    const stepVector = decryptVector(encryptedStep, transportKey, true);
    // Step 2: Dimension check
    if (stepVector.length !== currentPosition.length) {
        throw new Error(`Dimension mismatch: position is ${currentPosition.length}D, step is ${stepVector.length}D`);
    }
    // Step 3: Möbius addition on PLAINTEXT vectors only
    const newPosition = (0, hyperbolic_js_1.mobiusAdd)(currentPosition, stepVector);
    // Step 4: Project back to ball (safety)
    const safePosition = (0, hyperbolic_js_1.projectToBall)(newPosition, maxNorm);
    // Step 5: Compute distance traveled
    const distanceTraveled = (0, hyperbolic_js_1.hyperbolicDistance)(currentPosition, safePosition);
    return {
        position: safePosition,
        distanceTraveled,
        vectorValidated: true,
    };
}
/**
 * Navigate through a batch of encrypted steps, decrypting each before
 * applying Möbius addition sequentially.
 *
 * Rejected steps (auth failure, out-of-ball, dimension mismatch) are
 * skipped and their indices recorded.
 *
 * @param startPosition - Starting position in the Poincaré ball
 * @param encryptedSteps - Array of encrypted step vectors
 * @param transportKey - Symmetric key for decryption
 * @param maxNorm - Maximum allowed norm (default 1 - ε)
 * @returns Batch navigation result
 */
function secureBatchNavigate(startPosition, encryptedSteps, transportKey, maxNorm = 1 - 1e-10) {
    let position = [...startPosition];
    let totalDistance = 0;
    let stepsApplied = 0;
    const rejectedSteps = [];
    for (let i = 0; i < encryptedSteps.length; i++) {
        try {
            const result = secureNavigate(position, encryptedSteps[i], transportKey, maxNorm);
            position = result.position;
            totalDistance += result.distanceTraveled;
            stepsApplied++;
        }
        catch {
            rejectedSteps.push(i);
        }
    }
    return {
        position,
        totalDistance,
        stepsApplied,
        rejectedSteps,
    };
}
/**
 * Encrypt a position vector for storage or transmission, then later
 * decrypt it to resume navigation.
 *
 * Use this to persist navigator state securely between sessions.
 *
 * @param position - Current Poincaré ball position
 * @param transportKey - Key for encryption
 * @returns Encrypted position
 */
function encryptPosition(position, transportKey) {
    return encryptVector(position, transportKey, 'poincare-position');
}
/**
 * Decrypt a stored position and validate it's still a valid ball point.
 *
 * @param encrypted - Encrypted position from encryptPosition()
 * @param transportKey - Same key used for encryption
 * @returns Validated Poincaré ball position
 */
function decryptPosition(encrypted, transportKey) {
    return decryptVector(encrypted, transportKey, true);
}
//# sourceMappingURL=encryptedTransport.js.map