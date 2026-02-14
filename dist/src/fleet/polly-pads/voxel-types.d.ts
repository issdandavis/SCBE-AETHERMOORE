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
/** Sacred Tongue language code (uppercase for voxel addressing) */
export type Lang = 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';
/** Polly Pad operational mode */
export type PadMode = 'ENGINEERING' | 'NAVIGATION' | 'SYSTEMS' | 'SCIENCE' | 'COMMS' | 'MISSION';
/** SCBE Layer-13 three-tier risk decision */
export type Decision = 'ALLOW' | 'QUARANTINE' | 'DENY';
/** 6D voxel address: [X, Y, Z, V, P, S] */
export type Voxel6 = [number, number, number, number, number, number];
/** Voxel record scope */
export type VoxelScope = 'unit' | 'squad';
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
/** Canonical payload envelope at 6D voxel address */
export interface VoxelRecord {
    version: 1;
    /** Unit-local or squad-shared */
    scope: VoxelScope;
    /** Unit ID (present when scope == "unit") */
    unitId?: string;
    /** Squad ID (present when scope == "squad") */
    squadId?: string;
    /** Sacred Tongue language dimension */
    lang: Lang;
    /** 6D voxel coordinate [X, Y, Z, V, P, S] */
    voxel: Voxel6;
    /** Epoch counter */
    epoch: number;
    /** Pad mode at write time */
    padMode: PadMode;
    /** NK coherence score */
    coherence: number;
    /** Hyperbolic drift */
    dStar: number;
    /** Effective Hamiltonian cost */
    hEff: number;
    /** SCBE risk decision */
    decision: Decision;
    /** sha256(scope|unitId|squadId|lang|voxel|epoch|padMode) */
    cubeId: string;
    /** sha256(payloadCiphertext) */
    payloadDigest: string;
    seal: SacredEggSeal;
    /** base64(AEAD_encrypt(eggKey, plaintext)) */
    payloadCiphertext: string;
    quorum?: QuorumProof;
    /** e.g., ["tool:ide", "topic:proximity"] */
    tags?: string[];
    /** Parent cubeIds for graph edges */
    parents?: string[];
}
/** Map uppercase Lang to lowercase TongueCode */
export declare function langToTongueCode(lang: Lang): TongueCode;
/** Map lowercase TongueCode to uppercase Lang */
export declare function tongueCodeToLang(code: TongueCode): Lang;
/** Validate a VoxelRecord has required fields for its scope */
export declare function validateVoxelRecord(record: VoxelRecord): void;
//# sourceMappingURL=voxel-types.d.ts.map