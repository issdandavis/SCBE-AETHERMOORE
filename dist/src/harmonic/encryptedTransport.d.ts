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
/** Opaque encrypted vector — NOT a valid Poincaré ball point */
export interface EncryptedVector {
    /** AES-256-GCM ciphertext (base64url) */
    ciphertext: string;
    /** 96-bit nonce (base64url) */
    nonce: string;
    /** 128-bit auth tag (base64url) */
    tag: string;
    /** Dimension of the original vector */
    dimension: number;
    /** Domain label for key separation */
    domain: string;
}
/** Symmetric key for vector transport encryption */
export interface VectorTransportKey {
    /** 256-bit AES key */
    key: Buffer;
    /** Key identifier */
    kid: string;
    /** Creation timestamp */
    createdAt: number;
}
/** Result of a secure navigation step */
export interface SecureNavigationResult {
    /** New position after Möbius addition (plaintext) */
    position: number[];
    /** Hyperbolic distance traveled */
    distanceTraveled: number;
    /** Whether the step vector was validated as inside the ball */
    vectorValidated: boolean;
}
/** Result of a secure batch navigation */
export interface SecureBatchResult {
    /** Final position after all steps */
    position: number[];
    /** Total hyperbolic distance traveled */
    totalDistance: number;
    /** Number of steps applied */
    stepsApplied: number;
    /** Steps that were rejected (out of ball, corrupted, etc.) */
    rejectedSteps: number[];
}
/**
 * Generate a transport key for encrypting Poincaré ball vectors.
 *
 * @param domain - Domain label for key separation (e.g., 'navigation', 'storage')
 * @returns A VectorTransportKey with a random 256-bit AES key
 */
export declare function generateTransportKey(domain?: string): VectorTransportKey;
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
export declare function encryptVector(vector: number[], transportKey: VectorTransportKey, domain?: string): EncryptedVector;
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
export declare function decryptVector(encrypted: EncryptedVector, transportKey: VectorTransportKey, validateBall?: boolean): number[];
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
export declare function secureNavigate(currentPosition: number[], encryptedStep: EncryptedVector, transportKey: VectorTransportKey, maxNorm?: number): SecureNavigationResult;
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
export declare function secureBatchNavigate(startPosition: number[], encryptedSteps: EncryptedVector[], transportKey: VectorTransportKey, maxNorm?: number): SecureBatchResult;
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
export declare function encryptPosition(position: number[], transportKey: VectorTransportKey): EncryptedVector;
/**
 * Decrypt a stored position and validate it's still a valid ball point.
 *
 * @param encrypted - Encrypted position from encryptPosition()
 * @param transportKey - Same key used for encryption
 * @returns Validated Poincaré ball position
 */
export declare function decryptPosition(encrypted: EncryptedVector, transportKey: VectorTransportKey): number[];
//# sourceMappingURL=encryptedTransport.d.ts.map