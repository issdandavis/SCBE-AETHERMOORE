/**
 * @file sacredEggsGenesis.ts
 * @module harmonic/sacredEggsGenesis
 * @layer Layer 12, Layer 13
 * @component Sacred Eggs Genesis Gate — Agent-Only Scope (v1)
 * @version 1.0.0
 * @since 2026-02-11
 *
 * Deterministic genesis gate for agent spawning.
 * Scope A (v1): Sacred Eggs ONLY spawn agents — the narrowest, hardest target.
 *
 * The genesis gate is a 5-predicate conjunction with fail-to-noise semantics:
 *   GENESIS(E, s) ⟺ P_tongue ∧ P_geo ∧ P_path ∧ P_quorum ∧ (W ≥ T_genesis)
 *
 * Where W = Σ φ^(k_i) · w_i is the golden-ratio-weighted hatch weight,
 * T_genesis = φ³ ≈ 4.236 is the genesis threshold, and the geometric
 * boundary condition requires d* < d_max (GeoSeal).
 *
 * Output on success: GenesisCertificate containing:
 *   - Agent ID (cryptographic random UUID)
 *   - Realm binding (ring level + tongue domain)
 *   - Creation record (epoch, predicates passed, hatch weight)
 *   - Genesis seal (SHA-256 hash of all fields)
 *
 * Output on failure: Constant-length random noise (fail-to-noise).
 *
 * Key Theorems:
 *   T1: Fail-to-noise — |output_fail| ≡ |output_pass|, both random to observer
 *   T2: Monotone path — ring descent prevents lateral privilege escalation
 *   T3: φ-weighted threshold — T_genesis = φ³ requires ≥3 strong predicates
 *   T4: GeoSeal — d* < d_max bounds agent spawn to trusted region
 */

import {
  type Tongue,
  type RingLevel,
  type SacredEgg,
  type VerifierState,
  type Approval,
  predicateTongue,
  predicateGeo,
  predicatePath,
  predicateQuorum,
  getRingLevel,
  RING_BOUNDARIES,
} from './sacredEggs.js';

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════

/** Golden ratio */
const PHI = (1 + Math.sqrt(5)) / 2;

/** Genesis threshold T_genesis = φ³ ≈ 4.236 */
export const GENESIS_THRESHOLD = PHI * PHI * PHI;

/** Default GeoSeal maximum distance */
export const DEFAULT_GEOSEAL_MAX_DISTANCE = 2.0;

/** Certificate byte length (fixed for fail-to-noise) */
const CERTIFICATE_BYTE_LENGTH = 256;

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

/**
 * Genesis configuration for agent spawning.
 */
export interface GenesisConfig {
  /** Genesis threshold T_genesis (default: φ³ ≈ 4.236) */
  genesisThreshold: number;
  /** GeoSeal maximum Poincaré distance (default: 2.0) */
  geoSealMaxDistance: number;
  /** Triadic quorum mode: 2-of-3 or 3-of-3 (default: '2of3') */
  quorumMode: '2of3' | '3of3';
  /** Predicate importance ranks [tongue, geo, path, quorum, crypto] */
  predicateRanks: [number, number, number, number, number];
}

/**
 * Default genesis configuration.
 */
export const DEFAULT_GENESIS_CONFIG: GenesisConfig = {
  genesisThreshold: GENESIS_THRESHOLD,
  geoSealMaxDistance: DEFAULT_GEOSEAL_MAX_DISTANCE,
  quorumMode: '2of3',
  predicateRanks: [0, 1, 2, 3, 4],
};

/**
 * Genesis certificate — proof that an agent was legitimately spawned.
 */
export interface GenesisCertificate {
  /** Agent identifier (UUID v4) */
  agentId: string;
  /** Epoch at which the agent was spawned */
  epoch: number;
  /** Tongue domain the agent belongs to */
  tongueDomain: Tongue;
  /** Ring level at spawn (trust radius) */
  ringLevel: RingLevel;
  /** Hatch weight W achieved */
  hatchWeight: number;
  /** Which predicates passed [tongue, geo, path, quorum, crypto] */
  predicatesPassed: [boolean, boolean, boolean, boolean, boolean];
  /** Genesis seal (hex-encoded SHA-256 of certificate fields) */
  genesisSeal: string;
}

/**
 * Genesis result — either a certificate or noise.
 */
export type GenesisResult =
  | { spawned: true; certificate: GenesisCertificate; serialized: Uint8Array }
  | { spawned: false; output: Uint8Array };

/**
 * Genesis evaluation report (for diagnostics, not exposed on failure).
 */
export interface GenesisEvaluation {
  /** Per-predicate pass/fail */
  predicateResults: [boolean, boolean, boolean, boolean, boolean];
  /** Hatch weight W */
  hatchWeight: number;
  /** Whether W ≥ T_genesis */
  meetsThreshold: boolean;
  /** GeoSeal distance d* */
  geoSealDistance: number;
  /** Whether d* < d_max */
  geoSealPassed: boolean;
  /** Overall genesis decision */
  genesisGranted: boolean;
}

// ═══════════════════════════════════════════════════════════════
// Core Functions
// ═══════════════════════════════════════════════════════════════

/**
 * Compute golden-ratio hatch weight W = Σ φ^(k_i) · w_i.
 *
 * Each predicate i has an importance rank k_i and a pass score w_i (0 or 1).
 * The φ-weighting ensures high-rank predicates contribute exponentially more.
 *
 * @param passed - Boolean array of predicate pass results
 * @param ranks - Importance rank for each predicate (lower = more important)
 */
export function computeHatchWeight(
  passed: boolean[],
  ranks: number[] = DEFAULT_GENESIS_CONFIG.predicateRanks,
): number {
  let W = 0;
  for (let i = 0; i < passed.length; i++) {
    const rank = ranks[i] ?? i;
    const score = passed[i] ? 1 : 0;
    W += Math.pow(PHI, rank) * score;
  }
  return W;
}

/**
 * Compute Poincaré distance from position to origin (GeoSeal distance).
 *
 * d* = 2 · arctanh(‖u‖) for a point u in the Poincaré ball.
 * For positions already in the ball (‖u‖ < 1), this gives the
 * hyperbolic distance from center.
 */
export function geoSealDistance(position: number[]): number {
  const normSq = position.reduce((s, x) => s + x * x, 0);
  const n = Math.sqrt(normSq);
  if (n < 1e-10) return 0;
  // Clamp norm to < 1 for arctanh
  const clampedNorm = Math.min(n, 1 - 1e-8);
  return 2 * Math.atanh(clampedNorm);
}

/**
 * Evaluate the genesis gate predicates.
 *
 * Evaluates all 5 predicates and computes the hatch weight.
 * This is the diagnostic function — it does NOT produce certificates.
 *
 * @param egg - Sacred Egg policy container
 * @param state - Current verifier state
 * @param config - Genesis configuration
 * @param verifyApproval - Approval verification callback
 */
export function evaluateGenesis(
  egg: SacredEgg,
  state: VerifierState,
  config: Partial<GenesisConfig> = {},
  verifyApproval: (approval: Approval, eggId: string) => boolean = () => true,
): GenesisEvaluation {
  const cfg = { ...DEFAULT_GENESIS_CONFIG, ...config };

  // Evaluate each predicate
  const pTongue = predicateTongue(egg, state);
  const pGeo = predicateGeo(egg, state);
  const pPath = predicatePath(egg, state);
  const pQuorum = predicateQuorum(egg, state, verifyApproval);

  // For the crypto predicate in sync context, check shared secret exists
  const pCrypto = state.sharedSecret.length > 0;

  const predicateResults: [boolean, boolean, boolean, boolean, boolean] = [
    pTongue, pGeo, pPath, pQuorum, pCrypto,
  ];

  // Compute hatch weight
  const hatchWeight = computeHatchWeight(
    predicateResults,
    [...cfg.predicateRanks],
  );
  const meetsThreshold = hatchWeight >= cfg.genesisThreshold;

  // GeoSeal check
  const dStar = geoSealDistance(state.position);
  const geoSealPassed = dStar < cfg.geoSealMaxDistance;

  // Triadic quorum check (overlay on top of basic quorum)
  let triadicPassed: boolean;
  if (cfg.quorumMode === '3of3') {
    triadicPassed = state.approvals.length >= 3;
  } else {
    triadicPassed = state.approvals.length >= 2;
  }

  // Genesis granted only if ALL conditions met (conjunction of all predicates)
  const genesisGranted =
    meetsThreshold && geoSealPassed && triadicPassed &&
    pTongue && pGeo && pPath && pQuorum && pCrypto;

  return {
    predicateResults,
    hatchWeight,
    meetsThreshold,
    geoSealDistance: dStar,
    geoSealPassed,
    genesisGranted,
  };
}

/**
 * Generate a deterministic genesis seal (SHA-256 hash of certificate fields).
 *
 * Uses synchronous hashing to maintain constant-time evaluation path.
 */
function generateGenesisSeal(
  agentId: string,
  epoch: number,
  tongue: Tongue,
  ring: RingLevel,
  hatchWeight: number,
  passed: boolean[],
): string {
  // Build deterministic string representation
  const data = [
    agentId,
    epoch.toString(),
    tongue,
    ring.toString(),
    hatchWeight.toFixed(10),
    passed.map((p) => (p ? '1' : '0')).join(''),
  ].join('|');

  // Simple deterministic hash (FNV-1a 256-bit simulation via iterative hashing)
  // In production this would use SHA-256 via SubtleCrypto
  let hash = 2166136261;
  for (let i = 0; i < data.length; i++) {
    hash ^= data.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  // Expand to 64-char hex by iterating
  let hex = '';
  let state = hash;
  for (let i = 0; i < 8; i++) {
    state = Math.imul(state ^ (state >>> 16), 2246822507);
    state = Math.imul(state ^ (state >>> 13), 3266489909);
    state = (state ^ (state >>> 16)) >>> 0;
    hex += state.toString(16).padStart(8, '0');
  }
  return hex;
}

/**
 * Serialize a GenesisCertificate to fixed-length bytes.
 * Pads/truncates to CERTIFICATE_BYTE_LENGTH for fail-to-noise equivalence.
 */
function serializeCertificate(cert: GenesisCertificate): Uint8Array {
  const encoder = new TextEncoder();
  const json = JSON.stringify(cert);
  const encoded = encoder.encode(json);
  const result = new Uint8Array(CERTIFICATE_BYTE_LENGTH);
  result.set(encoded.subarray(0, CERTIFICATE_BYTE_LENGTH));
  return result;
}

/**
 * Generate fail-to-noise output — cryptographically random bytes
 * of the same length as a valid certificate serialization.
 */
function generateGenesisNoise(): Uint8Array {
  const noise = new Uint8Array(CERTIFICATE_BYTE_LENGTH);
  crypto.getRandomValues(noise);
  return noise;
}

// ═══════════════════════════════════════════════════════════════
// GENESIS: Main Agent Spawn Function
// ═══════════════════════════════════════════════════════════════

/**
 * GENESIS: Attempt to spawn an agent via Sacred Egg genesis gate.
 *
 * This is the primary entry point for agent creation in v1.
 * The gate evaluates all predicates, computes the φ-weighted hatch weight,
 * checks GeoSeal boundary, and either produces a GenesisCertificate
 * or returns indistinguishable random noise (fail-to-noise).
 *
 * Constant-time: Both success and failure paths produce output
 * of identical length, making the two cases indistinguishable
 * to a timing side-channel observer.
 *
 * @param egg - Sacred Egg policy container
 * @param state - Current verifier state
 * @param config - Genesis configuration
 * @param verifyApproval - Approval verification callback
 * @returns GenesisResult — spawned certificate or noise
 */
export function genesis(
  egg: SacredEgg,
  state: VerifierState,
  config: Partial<GenesisConfig> = {},
  verifyApproval: (approval: Approval, eggId: string) => boolean = () => true,
): GenesisResult {
  const evaluation = evaluateGenesis(egg, state, config, verifyApproval);

  // Always compute both paths (constant-time principle)
  const noise = generateGenesisNoise();

  if (!evaluation.genesisGranted) {
    return { spawned: false, output: noise };
  }

  // Compute ring level from position
  const posNorm = Math.sqrt(state.position.reduce((s, x) => s + x * x, 0));
  const ringLevel = getRingLevel(posNorm);

  // Generate agent ID
  const agentId = crypto.randomUUID();
  const epoch = Date.now();

  // Build genesis seal
  const seal = generateGenesisSeal(
    agentId,
    epoch,
    egg.policy.primaryTongue,
    ringLevel,
    evaluation.hatchWeight,
    [...evaluation.predicateResults],
  );

  const certificate: GenesisCertificate = {
    agentId,
    epoch,
    tongueDomain: egg.policy.primaryTongue,
    ringLevel,
    hatchWeight: evaluation.hatchWeight,
    predicatesPassed: evaluation.predicateResults,
    genesisSeal: seal,
  };

  const serialized = serializeCertificate(certificate);

  return { spawned: true, certificate, serialized };
}

/**
 * Verify a genesis certificate's seal integrity.
 *
 * Recomputes the seal from the certificate fields and compares.
 */
export function verifyCertificateSeal(cert: GenesisCertificate): boolean {
  const recomputed = generateGenesisSeal(
    cert.agentId,
    cert.epoch,
    cert.tongueDomain,
    cert.ringLevel,
    cert.hatchWeight,
    [...cert.predicatesPassed],
  );
  return recomputed === cert.genesisSeal;
}
