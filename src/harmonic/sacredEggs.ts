/**
 * @file sacredEggs.ts
 * @module harmonic/sacredEggs
 * @layer Layer 12, Layer 13
 * @component Sacred Eggs - Cryptographic Deferred Authorization
 * @version 3.2.5
 *
 * Sacred Eggs: Ciphertext containers that decrypt IFF a conjunction of predicates holds.
 *
 * PATENTABLE KERNEL:
 * Stateful secret release conditioned on a conjunction of:
 *   - domain membership (tongue)
 *   - geometric state
 *   - monotone path history
 *   - quorum
 *   - cryptographic validity
 * where failure collapses to a uniform response (fail-to-noise).
 *
 * This is NOT RBAC/ABAC. This is cryptographic deferred authorization.
 */

import { hyperbolicDistance, projectEmbeddingToBall } from './hyperbolic';

// ═══════════════════════════════════════════════════════════════
// Types and Constants
// ═══════════════════════════════════════════════════════════════

/** Sacred Tongue identifiers */
export type Tongue = 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';

/** All tongues */
export const ALL_TONGUES: Tongue[] = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];

/** Trust ring levels (0 = core/most trusted, 4 = edge/least trusted) */
export type RingLevel = 0 | 1 | 2 | 3 | 4;

/** Ring boundaries (radii in Poincaré ball) */
export const RING_BOUNDARIES: number[] = [0.2, 0.4, 0.6, 0.8, 0.95];

/** Default tongue weights */
export const DEFAULT_TONGUE_WEIGHTS: Record<Tongue, number> = {
  KO: 1.0, // Kor - nonce
  AV: 1.0, // Ava - AAD
  RU: 1.0, // Run - salt
  CA: 1.0, // Cas - cipher
  UM: 1.0, // Umb - redact
  DR: 1.0, // Dra - tag
};

// ═══════════════════════════════════════════════════════════════
// Sacred Egg Structure
// ═══════════════════════════════════════════════════════════════

/**
 * Policy specification for a Sacred Egg
 */
export interface EggPolicy {
  /** Primary tongue required */
  primaryTongue: Tongue;
  /** Additional tongues for multi-tongue mode (optional) */
  requiredTongues?: Tongue[];
  /** Tongue weights for weighted multi-tongue mode */
  tongueWeights?: Record<Tongue, number>;
  /** Minimum weight sum for multi-tongue mode */
  minWeightSum?: number;
  /** Maximum allowed ring level (0 = core only, 4 = any) */
  maxRing: RingLevel;
  /** Allowed policy cells (discrete state vectors) */
  allowedCells?: number[][];
  /** Required quorum count */
  quorumRequired: number;
  /** Maximum geometric distance to attractors */
  maxGeoDistance?: number;
  /** Attractor points in Poincaré ball */
  attractors?: number[][];
}

/**
 * Sacred Egg: Ciphertext container with policy-gated decryption
 *
 * E := (hdr, C, tag, policy)
 */
export interface SacredEgg {
  /** Header (public metadata) */
  header: {
    /** Egg identifier */
    id: string;
    /** Creation epoch */
    epoch: number;
    /** Policy hash (for verification without revealing policy) */
    policyHash: string;
  };
  /** Ciphertext (encrypted payload) */
  ciphertext: Uint8Array;
  /** Authentication tag */
  tag: Uint8Array;
  /** Policy specification */
  policy: EggPolicy;
  /** Domain separation tag (for key derivation) */
  dst: Uint8Array;
}

/**
 * Verifier state: The observed context at hatch time
 */
export interface VerifierState {
  /** Observed tongue of the request */
  observedTongue: Tongue;
  /** Valid tongues (those that passed MAC/signature verification) */
  validTongues: Set<Tongue>;
  /** Current position in Poincaré ball */
  position: number[];
  /** Current discrete policy cell */
  policyCell: number[];
  /** Ring history (sequence of ring levels, oldest first) */
  ringHistory: RingLevel[];
  /** Approvals presented */
  approvals: Approval[];
  /** Shared secret from PQ KEM */
  sharedSecret: Uint8Array;
}

/**
 * Approval (for quorum predicate)
 */
export interface Approval {
  /** Approver identifier */
  approverId: string;
  /** Signature over egg ID + epoch */
  signature: Uint8Array;
  /** Timestamp */
  timestamp: number;
}

/**
 * Hatch result
 */
export type HatchResult =
  | { success: true; plaintext: Uint8Array }
  | { success: false; output: Uint8Array }; // Fail-to-noise: indistinguishable failure

// ═══════════════════════════════════════════════════════════════
// Predicate Functions
// ═══════════════════════════════════════════════════════════════

/**
 * P_tongue: Tongue/domain predicate
 *
 * Solitary mode: τ = τ₀
 * Weighted multi-tongue: Σ w(t) ≥ W_min for t ∈ T_valid
 */
export function predicateTongue(egg: SacredEgg, state: VerifierState): boolean {
  const { policy } = egg;

  // Solitary mode: exact tongue match
  if (!policy.requiredTongues || policy.requiredTongues.length === 0) {
    return state.observedTongue === policy.primaryTongue;
  }

  // Weighted multi-tongue mode
  const weights = policy.tongueWeights || DEFAULT_TONGUE_WEIGHTS;
  const minSum = policy.minWeightSum || 1.0;

  let weightSum = 0;
  for (const tongue of state.validTongues) {
    if (policy.requiredTongues.includes(tongue)) {
      weightSum += weights[tongue] || 0;
    }
  }

  return weightSum >= minSum;
}

/**
 * Get ring level from radius in Poincaré ball
 */
export function getRingLevel(radius: number): RingLevel {
  for (let i = 0; i < RING_BOUNDARIES.length; i++) {
    if (radius < RING_BOUNDARIES[i]) {
      return i as RingLevel;
    }
  }
  return 4 as RingLevel;
}

/**
 * P_geo: Geometric predicate (ring + cell)
 *
 * Checks:
 *   1. ring(u) ≤ ring_max
 *   2. cell ∈ V_allowed (if specified)
 *   3. d*(u) ≤ ε_geo (distance to nearest attractor, if specified)
 */
export function predicateGeo(egg: SacredEgg, state: VerifierState): boolean {
  const { policy } = egg;

  // Use position directly if already in ball; only project real embeddings (norm >= 1)
  const posNorm = Math.sqrt(state.position.reduce((sum, x) => sum + x * x, 0));
  const pos = posNorm >= 1.0 ? projectEmbeddingToBall(state.position) : state.position;
  const radius = Math.sqrt(pos.reduce((sum, x) => sum + x * x, 0));
  const ring = getRingLevel(radius);

  // Check ring constraint
  if (ring > policy.maxRing) {
    return false;
  }

  // Check cell constraint (if specified)
  if (policy.allowedCells && policy.allowedCells.length > 0) {
    const cellMatch = policy.allowedCells.some((allowedCell) =>
      allowedCell.every((v, i) => Math.abs(v - (state.policyCell[i] || 0)) < 0.01)
    );
    if (!cellMatch) {
      return false;
    }
  }

  // Check attractor distance (if specified)
  if (policy.attractors && policy.attractors.length > 0 && policy.maxGeoDistance !== undefined) {
    const minDistance = Math.min(
      ...policy.attractors.map((attractor) => {
        const attractorNorm = Math.sqrt(attractor.reduce((sum, x) => sum + x * x, 0));
        const projectedAttractor = attractorNorm >= 1.0 ? projectEmbeddingToBall(attractor) : attractor;
        return hyperbolicDistance(pos, projectedAttractor);
      })
    );
    if (minDistance > policy.maxGeoDistance) {
      return false;
    }
  }

  return true;
}

/**
 * P_path: Path predicate (monotone ring descent)
 *
 * Checks: ring(u₀) > ring(u₁) > ... > ring(u_K) AND ring(u_K) ≤ r_core
 *
 * This is a STATE EVOLUTION CONSTRAINT - one of the key claim elements.
 */
export function predicatePath(egg: SacredEgg, state: VerifierState): boolean {
  const history = state.ringHistory;

  // Empty history = no path constraint (pass)
  if (history.length === 0) {
    return true;
  }

  // Check strict monotone descent
  for (let i = 1; i < history.length; i++) {
    if (history[i] >= history[i - 1]) {
      // Not strictly descending
      return false;
    }
  }

  // Check final ring is at core level (0) or acceptable
  const finalRing = history[history.length - 1];
  return finalRing <= 1; // Must reach core or inner ring
}

/**
 * P_quorum: Quorum predicate
 *
 * Checks: |A| ≥ q AND all approvals verify
 */
export function predicateQuorum(
  egg: SacredEgg,
  state: VerifierState,
  verifyApproval: (approval: Approval, eggId: string) => boolean
): boolean {
  const { policy } = egg;

  if (state.approvals.length < policy.quorumRequired) {
    return false;
  }

  // Verify all approvals
  for (const approval of state.approvals) {
    if (!verifyApproval(approval, egg.header.id)) {
      return false;
    }
  }

  return true;
}

/**
 * Derive key from shared secret and domain separation tag
 *
 * K := HKDF(ss, DST, ℓ)
 * DST := Enc(τ₀) || Enc(ring) || Enc(cell) || Enc(pathDigest) || Enc(epoch)
 */
export async function deriveKey(
  sharedSecret: Uint8Array,
  egg: SacredEgg,
  state: VerifierState
): Promise<Uint8Array> {
  // Build domain separation tag
  const encoder = new TextEncoder();
  const tongueBytes = encoder.encode(egg.policy.primaryTongue);

  // Use position directly if already in ball; only project real embeddings (norm >= 1)
  const posNorm = Math.sqrt(state.position.reduce((sum, x) => sum + x * x, 0));
  const pos = posNorm >= 1.0 ? projectEmbeddingToBall(state.position) : state.position;
  const radius = Math.sqrt(pos.reduce((sum, x) => sum + x * x, 0));
  const ring = getRingLevel(radius);

  const ringBytes = new Uint8Array([ring]);
  const cellBytes = new Uint8Array(state.policyCell.map((x) => Math.floor(x * 255)));
  const epochBytes = new Uint8Array(new BigUint64Array([BigInt(egg.header.epoch)]).buffer);

  // Path digest: hash of ring history
  const pathBytes = new Uint8Array(state.ringHistory);

  // Concatenate DST components
  const dst = new Uint8Array(
    tongueBytes.length + ringBytes.length + cellBytes.length + pathBytes.length + epochBytes.length
  );
  let offset = 0;
  dst.set(tongueBytes, offset);
  offset += tongueBytes.length;
  dst.set(ringBytes, offset);
  offset += ringBytes.length;
  dst.set(cellBytes, offset);
  offset += cellBytes.length;
  dst.set(pathBytes, offset);
  offset += pathBytes.length;
  dst.set(epochBytes, offset);

  // HKDF (simplified - in production use proper HKDF)
  const keyMaterial = new Uint8Array(sharedSecret.length + dst.length);
  keyMaterial.set(sharedSecret, 0);
  keyMaterial.set(dst, sharedSecret.length);

  // Use SubtleCrypto for proper key derivation
  const cryptoKey = await crypto.subtle.importKey('raw', keyMaterial, 'HKDF', false, [
    'deriveBits',
  ]);

  const derivedBits = await crypto.subtle.deriveBits(
    {
      name: 'HKDF',
      hash: 'SHA-256',
      salt: dst,
      info: new Uint8Array(0),
    },
    cryptoKey,
    256
  );

  return new Uint8Array(derivedBits);
}

/**
 * P_crypto: Cryptographic predicate (AEAD decryption)
 *
 * Returns plaintext if successful, null if failed
 */
export async function predicateCrypto(
  egg: SacredEgg,
  state: VerifierState
): Promise<Uint8Array | null> {
  try {
    const key = await deriveKey(state.sharedSecret, egg, state);

    // Import key for AES-GCM
    const aesKey = await crypto.subtle.importKey('raw', key, { name: 'AES-GCM' }, false, [
      'decrypt',
    ]);

    // Decrypt
    const plaintext = await crypto.subtle.decrypt(
      {
        name: 'AES-GCM',
        iv: egg.tag.slice(0, 12), // First 12 bytes as IV
        tagLength: 128,
      },
      aesKey,
      egg.ciphertext
    );

    return new Uint8Array(plaintext);
  } catch {
    return null;
  }
}

// ═══════════════════════════════════════════════════════════════
// HATCH: Main Decision Function
// ═══════════════════════════════════════════════════════════════

/**
 * Generate fail-to-noise output (indistinguishable failure response)
 */
function generateFailureOutput(length: number): Uint8Array {
  const output = new Uint8Array(length);
  crypto.getRandomValues(output);
  return output;
}

/**
 * HATCH: Open a Sacred Egg
 *
 * HATCH(E, s) ⟺ P_tongue ∧ P_geo ∧ P_path ∧ P_quorum ∧ P_crypto
 *
 * Decision rule:
 *   Open(E, s) = { M, if HATCH = true
 *                { ⊥, if HATCH = false  (fail-to-noise)
 *
 * @param egg - Sacred Egg to open
 * @param state - Verifier's observed state
 * @param verifyApproval - Function to verify approvals
 * @returns HatchResult with plaintext on success, noise on failure
 */
export async function hatch(
  egg: SacredEgg,
  state: VerifierState,
  verifyApproval: (approval: Approval, eggId: string) => boolean = () => true
): Promise<HatchResult> {
  // Default failure output length (matches expected plaintext size or fixed)
  const failureLength = egg.ciphertext.length;

  // P_tongue: Domain membership check
  if (!predicateTongue(egg, state)) {
    return { success: false, output: generateFailureOutput(failureLength) };
  }

  // P_geo: Geometric state check
  if (!predicateGeo(egg, state)) {
    return { success: false, output: generateFailureOutput(failureLength) };
  }

  // P_path: Monotone path history check
  if (!predicatePath(egg, state)) {
    return { success: false, output: generateFailureOutput(failureLength) };
  }

  // P_quorum: Quorum check
  if (!predicateQuorum(egg, state, verifyApproval)) {
    return { success: false, output: generateFailureOutput(failureLength) };
  }

  // P_crypto: Cryptographic decryption
  const plaintext = await predicateCrypto(egg, state);
  if (plaintext === null) {
    return { success: false, output: generateFailureOutput(failureLength) };
  }

  // All predicates passed
  return { success: true, plaintext };
}

// ═══════════════════════════════════════════════════════════════
// Egg Creation (for testing and production use)
// ═══════════════════════════════════════════════════════════════

/**
 * Create a Sacred Egg (encrypt plaintext with policy)
 */
export async function createEgg(
  plaintext: Uint8Array,
  policy: EggPolicy,
  sharedSecret: Uint8Array,
  expectedState: VerifierState
): Promise<SacredEgg> {
  const id = crypto.randomUUID();
  const epoch = Date.now();

  // Create egg structure (needed for key derivation)
  const partialEgg: SacredEgg = {
    header: {
      id,
      epoch,
      policyHash: '', // Will compute after
    },
    ciphertext: new Uint8Array(0),
    tag: new Uint8Array(16),
    policy,
    dst: new Uint8Array(0),
  };

  // Generate IV
  const iv = new Uint8Array(12);
  crypto.getRandomValues(iv);
  partialEgg.tag.set(iv, 0);

  // Derive key using expected state
  const key = await deriveKey(sharedSecret, partialEgg, expectedState);

  // Import key for AES-GCM
  const aesKey = await crypto.subtle.importKey('raw', key, { name: 'AES-GCM' }, false, ['encrypt']);

  // Encrypt
  const ciphertext = await crypto.subtle.encrypt(
    {
      name: 'AES-GCM',
      iv,
      tagLength: 128,
    },
    aesKey,
    plaintext
  );

  partialEgg.ciphertext = new Uint8Array(ciphertext);

  // Compute policy hash
  const policyStr = JSON.stringify(policy);
  const policyBytes = new TextEncoder().encode(policyStr);
  const hashBuffer = await crypto.subtle.digest('SHA-256', policyBytes);
  partialEgg.header.policyHash = Array.from(new Uint8Array(hashBuffer))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');

  return partialEgg;
}
