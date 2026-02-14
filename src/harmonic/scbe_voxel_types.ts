/**
 * @file scbe_voxel_types.ts
 * @module harmonic/scbe_voxel_types
 * @layer Layer 1, Layer 12, Layer 13, Layer 14
 * @component Voxel Record Schema
 * @version 3.2.4
 *
 * Canonical payload envelope stored at a voxel address [X,Y,Z,V,P,S] per tongue.
 * Fits QR Cubes + Sacred Eggs + Polly Pads + Byzantine quorum.
 *
 * Addressing: cubeId = sha256(canonical({lang, voxel, epoch, padMode}))
 * Content:    payloadDigest = sha256(payloadCiphertextBytes)
 * Quorum:     ≥4/6 votes on same (cubeId, payloadDigest) to commit
 */

/** Sacred Tongue identifiers (6 tongues) */
export type Lang = 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';

/** All valid tongue codes */
export const LANGS: readonly Lang[] = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'] as const;

/** Polly Pad operational modes — one per tongue-function */
export type PadMode =
  | 'ENGINEERING'
  | 'NAVIGATION'
  | 'SYSTEMS'
  | 'SCIENCE'
  | 'COMMS'
  | 'MISSION';

/** All valid pad modes */
export const PAD_MODES: readonly PadMode[] = [
  'ENGINEERING',
  'NAVIGATION',
  'SYSTEMS',
  'SCIENCE',
  'COMMS',
  'MISSION',
] as const;

/** SCBE risk decision tiers (L13) */
export type Decision = 'ALLOW' | 'QUARANTINE' | 'DENY';

/** 6D voxel address: [X, Y, Z, V, P, S] */
export type Voxel6 = [number, number, number, number, number, number];

/**
 * Byzantine quorum proof — ≥4/6 matching votes to commit.
 * n=6, f=1, threshold=4 (BFT: 3f+1 = 4).
 */
export interface QuorumProof {
  /** Total agents in quorum (always 6) */
  n: number;
  /** Max tolerated faults (always 1) */
  f: number;
  /** Required matching votes (always 4) */
  threshold: number;
  /** Individual agent votes */
  votes: QuorumVote[];
}

/** Single agent vote in a quorum */
export interface QuorumVote {
  /** Which of 6 agents cast this vote */
  agentId: string;
  /** sha256(payloadCiphertext) */
  digest: string;
  /** Sign(agentPriv, sha256(cubeId || digest || epoch || padMode)) */
  sig: string;
  /** Timestamp in ms since epoch */
  ts: number;
}

/**
 * Sacred Egg seal — encryption + authenticity metadata.
 * Binds the π^(φ*d*) key derivation to the envelope.
 */
export interface SacredEggSeal {
  /** Egg ritual / container identifier */
  eggId: string;
  /** Key derivation family: pi_phi → key = π^(φ*d*) */
  kdf: 'pi_phi';
  /** Hyperbolic realm distance used in π^(φ*d*) */
  dStar: number;
  /** NK coherence at commit time */
  coherence: number;
  /** Nonce for AEAD encryption */
  nonce: string;
  /** Additional authenticated data: hash of the record header */
  aad: string;
}

/**
 * Canonical Voxel Record — the fundamental storage unit.
 *
 * QR Cube  = lang + voxel + epoch + padMode (native addressing)
 * Sacred Egg = seal + payloadCiphertext (encryption + authenticity)
 * Byzantine  = quorum proof (auditable consensus)
 */
export interface VoxelRecord {
  /** Schema version */
  version: 1;

  // ── Addressing ──────────────────────────────────────────
  /** Sacred Tongue for this record */
  lang: Lang;
  /** 6D voxel coordinate [X, Y, Z, V, P, S] */
  voxel: Voxel6;
  /** Epoch counter (0-based) */
  epoch: number;
  /** Polly Pad operational mode */
  padMode: PadMode;

  // ── Governance snapshot at write time ───────────────────
  /** NK coherence ∈ [0, 1] */
  coherence: number;
  /** Hyperbolic realm distance d* */
  dStar: number;
  /** Effective harmonic cost H_eff */
  hEff: number;
  /** Risk decision at write time */
  decision: Decision;

  // ── Content-addressing ─────────────────────────────────
  /** Deterministic cubeId = sha256(canonical({lang, voxel, epoch, padMode})) */
  cubeId: string;
  /** payloadDigest = sha256(payloadCiphertextBytes) */
  payloadDigest: string;

  // ── Sacred Egg envelope ────────────────────────────────
  /** AEAD seal metadata */
  seal: SacredEggSeal;
  /** base64(AEAD_encrypt(eggKey, plaintext)) */
  payloadCiphertext: string;

  // ── Byzantine proof ────────────────────────────────────
  /** Quorum proof (optional — may be pending) */
  quorum?: QuorumProof;

  // ── Optional indexing ──────────────────────────────────
  /** Indexing tags (e.g. ["tool:browser", "topic:crypto", "trace"]) */
  tags?: string[];
  /** Parent cubeIds — graph edges for DAG traversal */
  parents?: string[];
}

/** Pad mode to tongue mapping */
export const PAD_MODE_TONGUE: Record<PadMode, Lang> = {
  ENGINEERING: 'CA',
  NAVIGATION: 'AV',
  SYSTEMS: 'DR',
  SCIENCE: 'UM',
  COMMS: 'KO',
  MISSION: 'RU',
};

/** Tongue semantic impedance roles */
export const TONGUE_ROLES: Record<Lang, string> = {
  KO: 'flow_orientation',
  AV: 'boundary_condition',
  RU: 'constraint_field',
  CA: 'active_operator',
  DR: 'structural_tensor',
  UM: 'entropic_sink',
};
