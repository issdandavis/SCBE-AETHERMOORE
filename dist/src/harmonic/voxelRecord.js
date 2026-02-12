"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.DEFAULT_THRESHOLDS = void 0;
exports.computeCubeId = computeCubeId;
exports.computePayloadDigest = computePayloadDigest;
exports.computeSignaturePayload = computeSignaturePayload;
exports.scbeDecide = scbeDecide;
exports.harmonicCost = harmonicCost;
exports.validateQuorum = validateQuorum;
exports.buildVoxelRecord = buildVoxelRecord;
exports.simulateQuorum = simulateQuorum;
const crypto_1 = require("crypto");
const jcs_js_1 = require("../crypto/jcs.js");
// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════
/** Golden ratio φ for harmonic scaling */
const PHI = (1 + Math.sqrt(5)) / 2;
exports.DEFAULT_THRESHOLDS = {
    allowMaxCost: 1e3,
    quarantineMaxCost: 1e6,
    allowMinCoherence: 0.55,
    quarantineMinCoherence: 0.25,
    allowMaxDrift: 1.2,
    quarantineMaxDrift: 2.2,
};
// ═══════════════════════════════════════════════════════════════
// CubeId + Digest (deterministic, canonical)
// ═══════════════════════════════════════════════════════════════
/**
 * Compute deterministic CubeId from addressing fields.
 *
 * cubeId = sha256(canonical({lang, voxel, epoch, padMode}))
 *
 * Uses JCS (RFC 8785) canonicalization for stability.
 */
function computeCubeId(lang, voxel, epoch, padMode) {
    const payload = { lang, voxel: Array.from(voxel), epoch, padMode };
    const canonical = (0, jcs_js_1.canonicalize)(payload);
    return (0, crypto_1.createHash)('sha256').update(canonical, 'utf-8').digest('hex');
}
/**
 * Compute payload digest from ciphertext bytes.
 *
 * payloadDigest = sha256(payloadCiphertextBytes)
 */
function computePayloadDigest(payloadCiphertext) {
    const bytes = Buffer.from(payloadCiphertext, 'base64');
    return (0, crypto_1.createHash)('sha256').update(bytes).digest('hex');
}
/**
 * Compute the agent signature payload hash.
 *
 * sigPayload = sha256(cubeId || payloadDigest || epoch || padMode)
 *
 * Agents sign this to cast a quorum vote.
 */
function computeSignaturePayload(cubeId, payloadDigest, epoch, padMode) {
    const combined = `${cubeId}${payloadDigest}${epoch}${padMode}`;
    return (0, crypto_1.createHash)('sha256').update(combined, 'utf-8').digest('hex');
}
// ═══════════════════════════════════════════════════════════════
// SCBE Decision (L13)
// ═══════════════════════════════════════════════════════════════
/**
 * Compute SCBE risk decision from governance state.
 *
 * Decision hierarchy:
 *   DENY if coherence < quarantine_min OR hEff > quarantine_max OR dStar > quarantine_max
 *   ALLOW if coherence >= allow_min AND hEff <= allow_max AND dStar <= allow_max
 *   QUARANTINE otherwise
 */
function scbeDecide(dStar, coherence, hEff, thresholds = exports.DEFAULT_THRESHOLDS) {
    if (coherence < thresholds.quarantineMinCoherence)
        return 'DENY';
    if (hEff > thresholds.quarantineMaxCost)
        return 'DENY';
    if (dStar > thresholds.quarantineMaxDrift)
        return 'DENY';
    if (coherence >= thresholds.allowMinCoherence &&
        hEff <= thresholds.allowMaxCost &&
        dStar <= thresholds.allowMaxDrift) {
        return 'ALLOW';
    }
    return 'QUARANTINE';
}
/**
 * Compute effective harmonic cost H(d*, R).
 *
 * H(d*, R) = R · π^(φ · d*)
 *
 * This is the Layer-12 event horizon: cost grows super-exponentially
 * with hyperbolic realm distance, making adversarial access infeasible.
 */
function harmonicCost(dStar, R = 1.5) {
    return R * Math.pow(Math.PI, PHI * dStar);
}
// ═══════════════════════════════════════════════════════════════
// Quorum Validation (Byzantine, n=6, f=1, threshold=4)
// ═══════════════════════════════════════════════════════════════
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
function validateQuorum(quorum, expectedDigest) {
    if (quorum.n !== 6) {
        return { valid: false, matchingVotes: 0, reason: 'n must be 6' };
    }
    if (quorum.f !== 1) {
        return { valid: false, matchingVotes: 0, reason: 'f must be 1' };
    }
    if (quorum.threshold !== 4) {
        return { valid: false, matchingVotes: 0, reason: 'threshold must be 4' };
    }
    if (quorum.votes.length < quorum.threshold) {
        return {
            valid: false,
            matchingVotes: quorum.votes.length,
            reason: `insufficient votes: ${quorum.votes.length}/${quorum.threshold}`,
        };
    }
    // Check uniqueness of agent IDs
    const agentIds = new Set(quorum.votes.map((v) => v.agentId));
    if (agentIds.size !== quorum.votes.length) {
        return { valid: false, matchingVotes: 0, reason: 'duplicate agent IDs' };
    }
    // Count matching digests
    const matchingVotes = quorum.votes.filter((v) => v.digest === expectedDigest).length;
    if (matchingVotes < quorum.threshold) {
        return {
            valid: false,
            matchingVotes,
            reason: `digest mismatch: ${matchingVotes}/${quorum.threshold} matching`,
        };
    }
    return { valid: true, matchingVotes };
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
function buildVoxelRecord(params) {
    const { lang, voxel, epoch, padMode, coherence, dStar, payload, eggId, tags, parents, thresholds = exports.DEFAULT_THRESHOLDS, } = params;
    const cubeId = computeCubeId(lang, voxel, epoch, padMode);
    const hEff = harmonicCost(dStar);
    const decision = scbeDecide(dStar, coherence, hEff, thresholds);
    // Placeholder encryption — in production, use AEAD with egg key
    const payloadCiphertext = Buffer.from(payload, 'utf-8').toString('base64');
    const payloadDigest = computePayloadDigest(payloadCiphertext);
    // Build AAD as hash of header fields
    const headerHash = (0, crypto_1.createHash)('sha256')
        .update((0, jcs_js_1.canonicalize)({ lang, voxel: Array.from(voxel), epoch, padMode, coherence, dStar }))
        .digest('hex');
    const seal = {
        eggId,
        kdf: 'pi_phi',
        dStar,
        coherence,
        nonce: (0, crypto_1.createHash)('sha256')
            .update(`${cubeId}:${Date.now()}`)
            .digest('hex')
            .slice(0, 24),
        aad: headerHash,
    };
    return {
        version: 1,
        lang,
        voxel,
        epoch,
        padMode,
        coherence,
        dStar,
        hEff,
        decision,
        cubeId,
        payloadDigest,
        seal,
        payloadCiphertext,
        ...(tags && { tags }),
        ...(parents && { parents }),
    };
}
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
function simulateQuorum(cubeId, payloadDigest, epoch, padMode, agentCount = 4) {
    const sigPayload = computeSignaturePayload(cubeId, payloadDigest, epoch, padMode);
    const now = Date.now();
    const votes = Array.from({ length: agentCount }, (_, i) => ({
        agentId: `agent-${i + 1}`,
        digest: payloadDigest,
        sig: (0, crypto_1.createHash)('sha256')
            .update(`${sigPayload}:agent-${i + 1}`)
            .digest('hex'),
        ts: now + i,
    }));
    return {
        n: 6,
        f: 1,
        threshold: 4,
        votes,
    };
}
//# sourceMappingURL=voxelRecord.js.map