/**
 * @file qrCubeKdf.ts
 * @module harmonic/qrCubeKdf
 * @layer Layer 12, Layer 13
 * @component Holographic QR Cube π^φ Key Derivation
 * @version 1.0.0
 *
 * TypeScript port of the π^φ key derivation function (kdf='pi_phi').
 *
 * Derives cryptographic keys bound to the harmonic geometry of a voxel record.
 * The core innovation is mixing the super-exponential cost scalar π^(φ·d*)
 * into the key material, making key derivation computationally coupled to
 * the agent's position in hyperbolic space.
 *
 * Construction:
 *   1. Validate inputs (reject NaN, Inf, out-of-range coherence)
 *   2. Compute harmonic cost scalar: cost = π^(φ · d*)
 *   3. Build IKM by hashing all inputs with domain-separated prefixes
 *   4. HKDF-Extract: PRK = HMAC-SHA256(salt, IKM)
 *   5. HKDF-Expand: OKM = expand(PRK, context, out_len)
 *
 * Security properties:
 *   - Deterministic for identical inputs
 *   - Input-sensitive: any single-field change → different key
 *   - Domain-separated via context parameter
 *   - NaN/Inf rejection (numeric hygiene)
 *   - HKDF-Expand prefix property: shorter output is prefix of longer
 *
 * Zero npm dependencies — uses only Node.js crypto.
 *
 * Reference: VoxelRecord.seal.kdf = 'pi_phi' (src/harmonic/voxelRecord.ts)
 */

import { createHmac, createHash } from 'crypto';

// =============================================================================
// CONSTANTS
// =============================================================================

const PI = Math.PI;
const PHI = (1 + Math.sqrt(5)) / 2; // Golden ratio ≈ 1.6180339887

const DEFAULT_CONTEXT = Buffer.from('scbe:qr-cube:pi_phi:v1');

// =============================================================================
// HKDF-SHA256 (RFC 5869)
// =============================================================================

function hkdfExtract(salt: Buffer, ikm: Buffer): Buffer {
  const s = salt.length > 0 ? salt : Buffer.alloc(32, 0);
  return Buffer.from(createHmac('sha256', s).update(ikm).digest());
}

function hkdfExpand(prk: Buffer, info: Buffer, length: number): Buffer {
  const parts: Buffer[] = [];
  let t = Buffer.alloc(0);
  let counter = 1;
  let totalLen = 0;
  while (totalLen < length) {
    t = Buffer.from(
      createHmac('sha256', prk)
        .update(Buffer.concat([t, info, Buffer.from([counter])]))
        .digest(),
    );
    parts.push(t);
    totalLen += t.length;
    counter++;
  }
  return Buffer.concat(parts).subarray(0, length);
}

// =============================================================================
// HELPERS
// =============================================================================

/**
 * Compute the harmonic cost scalar: π^(φ · d*).
 *
 * Monotonically increasing with d* (φ > 0, π > 1).
 * At d*=0: returns 1.0
 * At d*=1: returns π^φ ≈ 5.047
 */
export function piPhiScalar(dStar: number): number {
  return PI ** (PHI * dStar);
}

function assertFinite(value: number, name: string): void {
  if (!Number.isFinite(value)) {
    throw new RangeError(`${name} must be finite, got ${value}`);
  }
}

function commitField(domain: string, data: Buffer): Buffer {
  return Buffer.from(
    createHash('sha256')
      .update(Buffer.from(domain))
      .update(data)
      .digest(),
  );
}

/**
 * Pack a float64 as big-endian IEEE 754 bytes (matches Python struct.pack(">d", v)).
 */
function packDouble(value: number): Buffer {
  const buf = Buffer.alloc(8);
  buf.writeDoubleBE(value, 0);
  return buf;
}

// =============================================================================
// TYPES
// =============================================================================

export interface PiPhiKdfParams {
  /** Hyperbolic distance (harmonic drift). Must be finite. */
  dStar: number;
  /** Coherence metric ∈ [0, 1]. Must be finite and in range. */
  coherence: number;
  /** Voxel cube identifier (e.g., "cube-001"). */
  cubeId: string;
  /** Additional authenticated data (e.g., header hash). */
  aad: Buffer;
  /** Per-derivation nonce. */
  nonce: Buffer;
  /** Optional salt for HKDF-Extract (default: empty → 32 zero bytes). */
  salt?: Buffer;
  /** Desired output length in bytes (default: 32). */
  outLen?: number;
  /** Domain separation context for HKDF-Expand info (default: 'scbe:qr-cube:pi_phi:v1'). */
  context?: Buffer;
}

// =============================================================================
// CORE
// =============================================================================

/**
 * Derive a key from the π^φ harmonic cost function bound to voxel geometry.
 *
 * @param params - Key derivation parameters.
 * @returns Derived key of exactly `outLen` bytes.
 * @throws RangeError if dStar or coherence is NaN/Inf, or coherence outside [0,1].
 */
export function derivePiPhiKey(params: PiPhiKdfParams): Buffer {
  const {
    dStar,
    coherence,
    cubeId,
    aad,
    nonce,
    salt = Buffer.alloc(0),
    outLen = 32,
    context = DEFAULT_CONTEXT,
  } = params;

  // 1. Input validation
  assertFinite(dStar, 'dStar');
  assertFinite(coherence, 'coherence');
  if (coherence < 0.0 || coherence > 1.0) {
    throw new RangeError(`coherence must be in range 0..1, got ${coherence}`);
  }

  // 2. Harmonic cost scalar
  const cost = piPhiScalar(dStar);

  // 3. Build IKM from domain-separated field commitments
  const ikm = Buffer.concat([
    commitField('pi_phi:cost:', packDouble(cost)),
    commitField('pi_phi:d_star:', packDouble(dStar)),
    commitField('pi_phi:coherence:', packDouble(coherence)),
    commitField('pi_phi:cube_id:', Buffer.from(cubeId, 'utf-8')),
    commitField('pi_phi:aad:', aad),
    commitField('pi_phi:nonce:', nonce),
  ]);

  // 4. HKDF-Extract
  const prk = hkdfExtract(salt, ikm);

  // 5. HKDF-Expand
  return hkdfExpand(prk, context, outLen);
}
