/**
 * @file sacredEggs.ts
 * @module harmonic/sacredEggs
 * @layer Layer 5, Layer 7, Layer 8, Layer 13
 * @component Sacred Eggs — Ritual-Based Conditional Secret Distribution
 * @version 3.0.0
 * @since 2026-02-07
 *
 * Predicate-gated AEAD encryption where decryption requires ALL four
 * predicates to be satisfied simultaneously:
 *
 *   P1(tongue):   Correct Sacred Tongue identity
 *   P2(geometry): Correct position in Poincaré ball (L5 metric)
 *   P3(path):     Valid PHDM Hamiltonian path history
 *   P4(quorum):   k-of-n threshold met
 *
 * If ANY predicate fails, the derived key is wrong and AEAD decryption
 * produces an auth failure — no information leaks about WHICH predicate
 * was wrong (fail-to-noise property).
 *
 * Validated by experiments SE-1 (16-case predicate matrix),
 * SE-2 (output collapse), SE-3 (geometry key separation).
 */

import * as crypto from 'crypto';
import { hkdfSha256 } from '../crypto/hkdf.js';
import { hyperbolicDistance, projectToBall } from './hyperbolic.js';
import type { TongueCode } from './sacredTongues.js';

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

/** Phase angles for each Sacred Tongue (60° spacing) */
export const EGG_TONGUE_PHASES: Record<TongueCode, number> = {
  ko: 0,                    // 0°
  av: Math.PI / 3,          // 60°
  ru: (2 * Math.PI) / 3,    // 120°
  ca: Math.PI,              // 180°
  um: (4 * Math.PI) / 3,    // 240°
  dr: (5 * Math.PI) / 3,    // 300°
};

/** A single party's share in the quorum */
export interface QuorumShare {
  partyId: number;
  share: Buffer;  // 32-byte secret share
}

/** Configuration for a Sacred Egg */
export interface SacredEggConfig {
  /** Sacred Tongue code for this egg */
  tongue: TongueCode;
  /** Expected position in Poincaré ball (6D) */
  geometryCenter: number[];
  /** Max hyperbolic distance for geometry match (default 0.5) */
  geometryThreshold?: number;
  /** Quorum threshold (k of n) */
  quorumK: number;
  /** Total quorum parties */
  quorumN: number;
}

/** A sealed Sacred Egg */
export interface SacredEgg {
  /** Encrypted secret (nonce || ciphertext || tag) */
  ciphertext: Buffer;
  /** Authenticated additional data */
  aad: Buffer;
  /** Sacred Tongue code */
  tongue: TongueCode;
  /** Expected geometry center */
  geometryCenter: number[];
  /** Geometry match threshold */
  geometryThreshold: number;
  /** Hash of expected PHDM path */
  pathCommitment: Buffer;
  /** Quorum threshold */
  quorumK: number;
  /** Total quorum parties */
  quorumN: number;
  /** Salt for key derivation */
  salt: Buffer;
}

/** Result of an unseal attempt */
export interface UnsealResult {
  success: boolean;
  secret?: Buffer;
}

// ═══════════════════════════════════════════════════════════════
// Quorum Operations
// ═══════════════════════════════════════════════════════════════

/**
 * Generate quorum shares for n parties with threshold k.
 *
 * Uses deterministic derivation from a seed for reproducibility.
 * In production, use Shamir's Secret Sharing.
 */
export function generateQuorum(
  n: number,
  k: number,
  seed: Buffer
): { shares: QuorumShare[]; combined: Buffer } {
  const shares: QuorumShare[] = [];
  for (let i = 0; i < n; i++) {
    const shareData = Buffer.alloc(4);
    shareData.writeUInt32LE(i);
    const share = crypto
      .createHash('sha256')
      .update(Buffer.concat([seed, shareData]))
      .digest();
    shares.push({ partyId: i, share: Buffer.from(share) });
  }
  const combined = crypto
    .createHash('sha256')
    .update(Buffer.concat([seed, Buffer.from(':quorum-master')]))
    .digest();
  return { shares, combined };
}

/**
 * Combine k shares into quorum material.
 *
 * If fewer than k shares provided, produces wrong material (fail-to-noise).
 */
export function combineShares(shares: QuorumShare[], k: number): Buffer {
  if (shares.length < k) {
    return Buffer.alloc(32); // insufficient — will produce wrong key
  }
  const sorted = [...shares].sort((a, b) => a.partyId - b.partyId).slice(0, k);
  let combined = Buffer.alloc(32);
  for (const s of sorted) {
    combined = Buffer.from(combined.map((b, i) => b ^ s.share[i]));
  }
  return crypto
    .createHash('sha256')
    .update(Buffer.concat([combined, Buffer.from(':quorum-combined')]))
    .digest();
}

// ═══════════════════════════════════════════════════════════════
// Path Hashing
// ═══════════════════════════════════════════════════════════════

/**
 * Hash a PHDM path (sequence of polyhedron indices).
 */
export function pathHash(pathIndices: number[]): Buffer {
  const data = 'phdm:path:' + pathIndices.join(',');
  return crypto.createHash('sha256').update(data).digest();
}

// ═══════════════════════════════════════════════════════════════
// Key Derivation
// ═══════════════════════════════════════════════════════════════

/**
 * Derive the AEAD key from all four predicates.
 *
 * Each predicate contributes independent key material.
 * The final key is derived from their concatenation via HKDF.
 * If ANY input differs, the derived key is completely different (avalanche).
 */
export function deriveEggKey(
  tongue: TongueCode,
  geometryPoint: number[],
  pathIndices: number[],
  quorumMaterial: Buffer,
  salt: Buffer
): Buffer {
  // P1: Tongue material
  const tonguePhase = EGG_TONGUE_PHASES[tongue] ?? 0;
  const tonguePhaseBytes = Buffer.alloc(8);
  tonguePhaseBytes.writeDoubleBE(tonguePhase);
  const tongueMaterial = crypto
    .createHash('sha256')
    .update(
      Buffer.concat([
        Buffer.from('sacred-egg:tongue:'),
        Buffer.from(tongue),
        tonguePhaseBytes,
      ])
    )
    .digest();

  // P2: Geometry material — point coordinates at full precision
  const geoFloats = Buffer.alloc(geometryPoint.length * 8);
  for (let i = 0; i < geometryPoint.length; i++) {
    geoFloats.writeDoubleBE(geometryPoint[i], i * 8);
  }
  const geometryMaterial = crypto
    .createHash('sha256')
    .update(Buffer.concat([Buffer.from('sacred-egg:geometry:'), geoFloats]))
    .digest();

  // P3: Path material
  const pathMaterial = pathHash(pathIndices);

  // P4: Quorum material
  const quorumMat = crypto
    .createHash('sha256')
    .update(Buffer.concat([Buffer.from('sacred-egg:quorum:'), quorumMaterial]))
    .digest();

  // Combine all four into AEAD key
  const ikm = Buffer.concat([tongueMaterial, geometryMaterial, pathMaterial, quorumMat]);
  const info = Buffer.from('sacred-egg:aead-key:v1');
  return hkdfSha256(ikm, salt, info, 32);
}

// ═══════════════════════════════════════════════════════════════
// AEAD (AES-256-GCM)
// ═══════════════════════════════════════════════════════════════

/**
 * Encrypt with AES-256-GCM AEAD.
 *
 * @returns Buffer containing: nonce(12) || ciphertext || tag(16)
 */
function aeadEncrypt(key: Buffer, plaintext: Buffer, aad: Buffer): Buffer {
  const nonce = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv('aes-256-gcm', key, nonce);
  cipher.setAAD(aad);
  const ct = Buffer.concat([cipher.update(plaintext), cipher.final()]);
  const tag = cipher.getAuthTag();
  return Buffer.concat([nonce, ct, tag]);
}

/**
 * Decrypt with AES-256-GCM AEAD.
 *
 * @returns Plaintext on success, null on auth failure (fail-to-noise)
 */
function aeadDecrypt(key: Buffer, ciphertext: Buffer, aad: Buffer): Buffer | null {
  if (ciphertext.length < 28) return null; // nonce(12) + tag(16) minimum

  const nonce = ciphertext.subarray(0, 12);
  const tag = ciphertext.subarray(ciphertext.length - 16);
  const ct = ciphertext.subarray(12, ciphertext.length - 16);

  try {
    const decipher = crypto.createDecipheriv('aes-256-gcm', key, nonce);
    decipher.setAAD(aad);
    decipher.setAuthTag(tag);
    return Buffer.concat([decipher.update(ct), decipher.final()]);
  } catch {
    return null; // Auth failed — fail-to-noise
  }
}

// ═══════════════════════════════════════════════════════════════
// Sacred Egg Operations
// ═══════════════════════════════════════════════════════════════

/**
 * Seal a secret into a Sacred Egg.
 *
 * The secret will only be recoverable if ALL four predicates
 * are presented correctly during unseal.
 *
 * @param secret - The secret to protect
 * @param config - Egg configuration (tongue, geometry, quorum params)
 * @param geometryPoint - Sealer's position in Poincaré ball
 * @param pathIndices - PHDM Hamiltonian path history
 * @param quorumShares - Available quorum shares (must have >= k)
 * @returns Sealed Sacred Egg
 */
export function sealEgg(
  secret: Buffer,
  config: SacredEggConfig,
  geometryPoint: number[],
  pathIndices: number[],
  quorumShares: QuorumShare[]
): SacredEgg {
  const salt = crypto.randomBytes(32);
  const quorumMaterial = combineShares(quorumShares, config.quorumK);

  const key = deriveEggKey(config.tongue, geometryPoint, pathIndices, quorumMaterial, salt);

  const aad = Buffer.from(
    JSON.stringify({
      type: 'sacred-egg',
      version: 'v1',
      tongue: config.tongue,
      quorum_k: config.quorumK,
      quorum_n: config.quorumN,
    })
  );

  const ciphertext = aeadEncrypt(key, secret, aad);

  return {
    ciphertext,
    aad,
    tongue: config.tongue,
    geometryCenter: [...geometryPoint],
    geometryThreshold: config.geometryThreshold ?? 0.5,
    pathCommitment: pathHash(pathIndices),
    quorumK: config.quorumK,
    quorumN: config.quorumN,
    salt,
  };
}

/**
 * Attempt to unseal a Sacred Egg.
 *
 * ALL four predicates must match for decryption to succeed.
 * On failure, returns { success: false } with no information
 * about which predicate was wrong (fail-to-noise).
 *
 * @param egg - The Sacred Egg to unseal
 * @param tongue - Claimed tongue code
 * @param geometryPoint - Claimer's position in Poincaré ball
 * @param pathIndices - Claimed PHDM path history
 * @param quorumShares - Available quorum shares
 * @returns UnsealResult with secret on success, nothing on failure
 */
export function unsealEgg(
  egg: SacredEgg,
  tongue: TongueCode,
  geometryPoint: number[],
  pathIndices: number[],
  quorumShares: QuorumShare[]
): UnsealResult {
  const quorumMaterial = combineShares(quorumShares, egg.quorumK);

  const key = deriveEggKey(tongue, geometryPoint, pathIndices, quorumMaterial, egg.salt);

  const result = aeadDecrypt(key, egg.ciphertext, egg.aad);

  if (result !== null) {
    return { success: true, secret: result };
  }
  return { success: false };
}

/**
 * Check if a geometry point is within the egg's threshold.
 *
 * This is an OPTIONAL pre-check — the real gating happens in key derivation.
 * Use this for UX (show distance feedback) but NEVER skip AEAD verification.
 */
export function checkGeometryProximity(
  egg: SacredEgg,
  candidatePoint: number[]
): { withinThreshold: boolean; distance: number } {
  const a = projectToBall(egg.geometryCenter);
  const b = projectToBall(candidatePoint);
  const distance = hyperbolicDistance(a, b);
  return {
    withinThreshold: distance <= egg.geometryThreshold,
    distance,
  };
}
