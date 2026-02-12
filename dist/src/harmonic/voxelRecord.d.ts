/**
 * @file voxelRecord.ts
 * @module harmonic/voxelRecord
 * @layer Layer 1, Layer 12, Layer 13
 * @component Voxel Record Operations
 * @version 3.2.4
 *
 * Deterministic CubeId generation, payload digest computation,
 * quorum validation, and SCBE decision gating for VoxelRecords.
 */
import { type Lang, type PadMode, type Voxel6, type Decision, type VoxelRecord, type QuorumProof } from './scbe_voxel_types.js';
/** Default SCBE governance thresholds */
export interface SCBEThresholds {
    /** Max H_eff for ALLOW (default 1e3) */
    allowMaxCost: number;
    /** Max H_eff for QUARANTINE (default 1e6) */
    quarantineMaxCost: number;
    /** Min coherence for ALLOW (default 0.55) */
    allowMinCoherence: number;
    /** Min coherence for QUARANTINE (default 0.25) */
    quarantineMinCoherence: number;
    /** Max d* for ALLOW (default 1.2) */
    allowMaxDrift: number;
    /** Max d* for QUARANTINE (default 2.2) */
    quarantineMaxDrift: number;
}
export declare const DEFAULT_THRESHOLDS: Readonly<SCBEThresholds>;
/**
 * Compute deterministic CubeId from addressing fields.
 *
 * cubeId = sha256(canonical({lang, voxel, epoch, padMode}))
 *
 * Uses JCS (RFC 8785) canonicalization for stability.
 */
export declare function computeCubeId(lang: Lang, voxel: Voxel6, epoch: number, padMode: PadMode): string;
/**
 * Compute payload digest from ciphertext bytes.
 *
 * payloadDigest = sha256(payloadCiphertextBytes)
 */
export declare function computePayloadDigest(payloadCiphertext: string): string;
/**
 * Compute the agent signature payload hash.
 *
 * sigPayload = sha256(cubeId || payloadDigest || epoch || padMode)
 *
 * Agents sign this to cast a quorum vote.
 */
export declare function computeSignaturePayload(cubeId: string, payloadDigest: string, epoch: number, padMode: PadMode): string;
/**
 * Compute SCBE risk decision from governance state.
 *
 * Decision hierarchy:
 *   DENY if coherence < quarantine_min OR hEff > quarantine_max OR dStar > quarantine_max
 *   ALLOW if coherence >= allow_min AND hEff <= allow_max AND dStar <= allow_max
 *   QUARANTINE otherwise
 */
export declare function scbeDecide(dStar: number, coherence: number, hEff: number, thresholds?: SCBEThresholds): Decision;
/**
 * Compute effective harmonic cost H(d*, R).
 *
 * H(d*, R) = R · π^(φ · d*)
 *
 * This is the Layer-12 event horizon: cost grows super-exponentially
 * with hyperbolic realm distance, making adversarial access infeasible.
 */
export declare function harmonicCost(dStar: number, R?: number): number;
/**
 * Validate a quorum proof against a VoxelRecord.
 *
 * Checks:
 * 1. n=6, f=1, threshold=4
 * 2. ≥threshold votes present
 * 3. All votes reference the same digest
 * 4. All agent IDs are unique
 * 5. All digests match the record's payloadDigest
 */
export declare function validateQuorum(quorum: QuorumProof, expectedDigest: string): {
    valid: boolean;
    matchingVotes: number;
    reason?: string;
};
/** Parameters for building a VoxelRecord */
export interface VoxelRecordParams {
    lang: Lang;
    voxel: Voxel6;
    epoch: number;
    padMode: PadMode;
    coherence: number;
    dStar: number;
    /** Raw plaintext payload (will be "encrypted" as base64) */
    payload: string;
    /** Egg ID for the Sacred Egg seal */
    eggId: string;
    /** Optional tags */
    tags?: string[];
    /** Optional parent cubeIds */
    parents?: string[];
    /** SCBE thresholds override */
    thresholds?: SCBEThresholds;
}
/**
 * Build a complete VoxelRecord from parameters.
 *
 * Computes:
 * - cubeId (deterministic from addressing)
 * - hEff (harmonic cost from dStar)
 * - decision (SCBE L13)
 * - payloadCiphertext (base64 placeholder — real AEAD in production)
 * - payloadDigest (sha256 of ciphertext bytes)
 * - seal (Sacred Egg metadata)
 */
export declare function buildVoxelRecord(params: VoxelRecordParams): VoxelRecord;
/**
 * Create a simulated quorum proof for a record.
 *
 * In production, each agent independently computes and signs.
 * This creates a valid stub for n=6, f=1, threshold=4.
 *
 * @param cubeId - The record's cubeId
 * @param payloadDigest - The record's payloadDigest
 * @param epoch - The record's epoch
 * @param padMode - The record's padMode
 * @param agentCount - Number of agreeing agents (default 4)
 */
export declare function simulateQuorum(cubeId: string, payloadDigest: string, epoch: number, padMode: PadMode, agentCount?: number): QuorumProof;
//# sourceMappingURL=voxelRecord.d.ts.map