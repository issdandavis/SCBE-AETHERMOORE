/**
 * @file voxel-types.ts
 * @module fleet/polly-pads/voxel-types
 * @layer Layer 12, Layer 13
 * @version 1.0.0
 *
 * VoxelRecord schema - canonical payload envelope at 6D voxel address.
 *
 * Each record is content-addressed via deterministic cubeId and sealed
 * with a SacredEggSeal envelope. Squad-scoped commits require Byzantine
 * 4/6 quorum proof.
 *
 * Addressing: [X, Y, Z, V, P, S] per Sacred Tongue dimension.
 */

import type { TongueCode } from '../../harmonic/sacredTongues.js';

// ---------------------------------------------------------------------------
// Core types
// ---------------------------------------------------------------------------

/** Sacred Tongue language code (uppercase for voxel addressing) */
export type Lang = 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';

/** Polly Pad operational mode */
export type PadMode =
  | 'ENGINEERING'
  | 'NAVIGATION'
  | 'SYSTEMS'
  | 'SCIENCE'
  | 'COMMS'
  | 'MISSION';

/** SCBE Layer-13 three-tier risk decision */
export type Decision = 'ALLOW' | 'QUARANTINE' | 'DENY';

/** 6D voxel address: [X, Y, Z, V, P, S] */
export type Voxel6 = [number, number, number, number, number, number];

/** Voxel record scope */
export type VoxelScope = 'unit' | 'squad';

// ---------------------------------------------------------------------------
// Byzantine quorum proof
// ---------------------------------------------------------------------------

/** Individual agent vote in a quorum */
export interface QuorumVote {
  /** Agent identifier (e.g., "unit-1-pad-eng") */
  agentId: string;
  /** sha256(payloadCiphertext) */
  digest: string;
  /** Signature over (cubeId || digest || epoch || padMode) */
  sig: string;
  /** Millisecond timestamp */
  ts: number;
  /** Serialized tri-directional path trace (proof of governance) */
  pathTrace?: string;
}

/** Byzantine 4/6 quorum proof for voxel commits */
export interface QuorumProof {
  /** Total agents (e.g., 6) */
  n: number;
  /** Fault tolerance (e.g., 1) */
  f: number;
  /** Required votes (e.g., 4) */
  threshold: number;
  /** Individual agent votes */
  votes: QuorumVote[];
}

// ---------------------------------------------------------------------------
// Sacred Egg seal
// ---------------------------------------------------------------------------

/** Encryption envelope with pi^(phi*d*) key derivation */
export interface SacredEggSeal {
  /** Ritual/container ID */
  eggId: string;
  /** Key derivation family */
  kdf: 'pi_phi';
  /** Hyperbolic drift used in pi^(phi*d*) */
  dStar: number;
  /** NK coherence at commit time */
  coherence: number;
  /** AEAD nonce */
  nonce: string;
  /** Additional authenticated data (hash of header) */
  aad: string;
}

// ---------------------------------------------------------------------------
// Voxel record
// ---------------------------------------------------------------------------

/** Canonical payload envelope at 6D voxel address */
export interface VoxelRecord {
  version: 1;

  // -- Scoping --
  /** Unit-local or squad-shared */
  scope: VoxelScope;
  /** Unit ID (present when scope == "unit") */
  unitId?: string;
  /** Squad ID (present when scope == "squad") */
  squadId?: string;

  // -- 6D addressing --
  /** Sacred Tongue language dimension */
  lang: Lang;
  /** 6D voxel coordinate [X, Y, Z, V, P, S] */
  voxel: Voxel6;
  /** Epoch counter */
  epoch: number;
  /** Pad mode at write time */
  padMode: PadMode;

  // -- Governance snapshot (Layer 12-13) --
  /** NK coherence score */
  coherence: number;
  /** Hyperbolic drift */
  dStar: number;
  /** Effective Hamiltonian cost */
  hEff: number;
  /** SCBE risk decision */
  decision: Decision;

  // -- Content-addressing --
  /** sha256(scope|unitId|squadId|lang|voxel|epoch|padMode) */
  cubeId: string;
  /** sha256(payloadCiphertext) */
  payloadDigest: string;

  // -- Sacred Egg envelope --
  seal: SacredEggSeal;
  /** base64(AEAD_encrypt(eggKey, plaintext)) */
  payloadCiphertext: string;

  // -- Byzantine proof (required for squad scope) --
  quorum?: QuorumProof;

  // -- Optional indexing --
  /** e.g., ["tool:ide", "topic:proximity"] */
  tags?: string[];
  /** Parent cubeIds for graph edges */
  parents?: string[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Map uppercase Lang to lowercase TongueCode */
export function langToTongueCode(lang: Lang): TongueCode {
  return lang.toLowerCase() as TongueCode;
}

/** Map lowercase TongueCode to uppercase Lang */
export function tongueCodeToLang(code: TongueCode): Lang {
  return code.toUpperCase() as Lang;
}

/** Validate a VoxelRecord has required fields for its scope */
export function validateVoxelRecord(record: VoxelRecord): void {
  if (record.version !== 1) {
    throw new Error(`Unsupported VoxelRecord version: ${record.version}`);
  }
  if (record.scope === 'unit' && !record.unitId) {
    throw new Error('Unit-scoped VoxelRecord requires unitId');
  }
  if (record.scope === 'squad' && !record.squadId) {
    throw new Error('Squad-scoped VoxelRecord requires squadId');
  }
  if (record.scope === 'squad' && !record.quorum) {
    throw new Error('Squad-scoped VoxelRecord requires quorum proof');
  }
  if (record.voxel.length !== 6) {
    throw new Error(`Voxel must be 6D, got ${record.voxel.length}D`);
  }
}
