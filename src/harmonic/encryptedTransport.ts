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

import { createCipheriv, createDecipheriv, randomBytes, createHash } from 'node:crypto';
import { mobiusAdd, projectToBall, hyperbolicDistance } from './hyperbolic.js';

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

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

// ═══════════════════════════════════════════════════════════════
// Base64URL helpers
// ═══════════════════════════════════════════════════════════════

function b64u(buf: Buffer): string {
  return buf.toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

function fromB64u(s: string): Buffer {
  let padded = s.replace(/-/g, '+').replace(/_/g, '/');
  while (padded.length % 4) padded += '=';
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
export function generateTransportKey(domain: string = 'navigation'): VectorTransportKey {
  const key = randomBytes(32);
  const kid = createHash('sha256')
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
function serializeVector(v: number[]): Buffer {
  const buf = Buffer.alloc(v.length * 8);
  for (let i = 0; i < v.length; i++) {
    buf.writeDoubleBE(v[i], i * 8);
  }
  return buf;
}

/**
 * Deserialize a Buffer back to a number[] vector.
 */
function deserializeVector(buf: Buffer, dimension: number): number[] {
  if (buf.length !== dimension * 8) {
    throw new Error(
      `Vector deserialization size mismatch: got ${buf.length} bytes, expected ${dimension * 8}`
    );
  }
  const v: number[] = [];
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
export function encryptVector(
  vector: number[],
  transportKey: VectorTransportKey,
  domain: string = 'poincare-transport'
): EncryptedVector {
  if (!vector || vector.length === 0) {
    throw new Error('Cannot encrypt empty vector');
  }

  // Serialize vector to bytes
  const plaintext = serializeVector(vector);

  // Random 96-bit nonce
  const nonce = randomBytes(12);

  // AAD binds domain + dimension to prevent cross-context attacks
  const aad = Buffer.from(`scbe:vector:${domain}:dim=${vector.length}`);

  // AES-256-GCM encryption
  const cipher = createCipheriv('aes-256-gcm', transportKey.key, nonce);
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
export function decryptVector(
  encrypted: EncryptedVector,
  transportKey: VectorTransportKey,
  validateBall: boolean = true
): number[] {
  const nonce = fromB64u(encrypted.nonce);
  const tag = fromB64u(encrypted.tag);
  const ct = fromB64u(encrypted.ciphertext);
  const aad = Buffer.from(`scbe:vector:${encrypted.domain}:dim=${encrypted.dimension}`);

  if (nonce.length !== 12) {
    throw new Error('Invalid nonce size for vector decryption');
  }

  // AES-256-GCM decryption
  const decipher = createDecipheriv('aes-256-gcm', transportKey.key, nonce);
  decipher.setAAD(aad);
  decipher.setAuthTag(tag);

  let plaintext: Buffer;
  try {
    plaintext = Buffer.concat([decipher.update(ct), decipher.final()]);
  } catch {
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
      throw new Error(
        `Decrypted vector is outside the Poincaré ball: ‖v‖² = ${normSq.toFixed(6)} >= 1`
      );
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
export function secureNavigate(
  currentPosition: number[],
  encryptedStep: EncryptedVector,
  transportKey: VectorTransportKey,
  maxNorm: number = 1 - 1e-10
): SecureNavigationResult {
  // Step 1: Decrypt the step vector (validates ball membership)
  const stepVector = decryptVector(encryptedStep, transportKey, true);

  // Step 2: Dimension check
  if (stepVector.length !== currentPosition.length) {
    throw new Error(
      `Dimension mismatch: position is ${currentPosition.length}D, step is ${stepVector.length}D`
    );
  }

  // Step 3: Möbius addition on PLAINTEXT vectors only
  const newPosition = mobiusAdd(currentPosition, stepVector);

  // Step 4: Project back to ball (safety)
  const safePosition = projectToBall(newPosition, maxNorm);

  // Step 5: Compute distance traveled
  const distanceTraveled = hyperbolicDistance(currentPosition, safePosition);

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
export function secureBatchNavigate(
  startPosition: number[],
  encryptedSteps: EncryptedVector[],
  transportKey: VectorTransportKey,
  maxNorm: number = 1 - 1e-10
): SecureBatchResult {
  let position = [...startPosition];
  let totalDistance = 0;
  let stepsApplied = 0;
  const rejectedSteps: number[] = [];

  for (let i = 0; i < encryptedSteps.length; i++) {
    try {
      const result = secureNavigate(position, encryptedSteps[i], transportKey, maxNorm);
      position = result.position;
      totalDistance += result.distanceTraveled;
      stepsApplied++;
    } catch {
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
export function encryptPosition(
  position: number[],
  transportKey: VectorTransportKey
): EncryptedVector {
  return encryptVector(position, transportKey, 'poincare-position');
}

/**
 * Decrypt a stored position and validate it's still a valid ball point.
 *
 * @param encrypted - Encrypted position from encryptPosition()
 * @param transportKey - Same key used for encryption
 * @returns Validated Poincaré ball position
 */
export function decryptPosition(
  encrypted: EncryptedVector,
  transportKey: VectorTransportKey
): number[] {
  return decryptVector(encrypted, transportKey, true);
}
