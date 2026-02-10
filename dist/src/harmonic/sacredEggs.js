"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.DEFAULT_TONGUE_WEIGHTS = exports.RING_BOUNDARIES = exports.ALL_TONGUES = void 0;
exports.predicateTongue = predicateTongue;
exports.getRingLevel = getRingLevel;
exports.predicateGeo = predicateGeo;
exports.predicatePath = predicatePath;
exports.predicateQuorum = predicateQuorum;
exports.deriveKey = deriveKey;
exports.predicateCrypto = predicateCrypto;
exports.hatch = hatch;
exports.createEgg = createEgg;
const hyperbolic_1 = require("./hyperbolic");
/** All tongues */
exports.ALL_TONGUES = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
/** Ring boundaries (radii in Poincaré ball) */
exports.RING_BOUNDARIES = [0.2, 0.4, 0.6, 0.8, 0.95];
/** Default tongue weights */
exports.DEFAULT_TONGUE_WEIGHTS = {
    KO: 1.0, // Kor - nonce
    AV: 1.0, // Ava - AAD
    RU: 1.0, // Run - salt
    CA: 1.0, // Cas - cipher
    UM: 1.0, // Umb - redact
    DR: 1.0, // Dra - tag
};
// ═══════════════════════════════════════════════════════════════
// Predicate Functions
// ═══════════════════════════════════════════════════════════════
/**
 * P_tongue: Tongue/domain predicate
 *
 * Solitary mode: τ = τ₀
 * Weighted multi-tongue: Σ w(t) ≥ W_min for t ∈ T_valid
 */
function predicateTongue(egg, state) {
    const { policy } = egg;
    // Solitary mode: exact tongue match
    if (!policy.requiredTongues || policy.requiredTongues.length === 0) {
        return state.observedTongue === policy.primaryTongue;
    }
    // Weighted multi-tongue mode
    const weights = policy.tongueWeights || exports.DEFAULT_TONGUE_WEIGHTS;
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
function getRingLevel(radius) {
    for (let i = 0; i < exports.RING_BOUNDARIES.length; i++) {
        if (radius < exports.RING_BOUNDARIES[i]) {
            return i;
        }
    }
    return 4;
}
/**
 * P_geo: Geometric predicate (ring + cell)
 *
 * Checks:
 *   1. ring(u) ≤ ring_max
 *   2. cell ∈ V_allowed (if specified)
 *   3. d*(u) ≤ ε_geo (distance to nearest attractor, if specified)
 */
function predicateGeo(egg, state) {
    const { policy } = egg;
    // Use position directly if already in ball; only project real embeddings (norm >= 1)
    const posNorm = Math.sqrt(state.position.reduce((sum, x) => sum + x * x, 0));
    const pos = posNorm >= 1.0 ? (0, hyperbolic_1.projectEmbeddingToBall)(state.position) : state.position;
    const radius = Math.sqrt(pos.reduce((sum, x) => sum + x * x, 0));
    const ring = getRingLevel(radius);
    // Check ring constraint
    if (ring > policy.maxRing) {
        return false;
    }
    // Check cell constraint (if specified)
    if (policy.allowedCells && policy.allowedCells.length > 0) {
        const cellMatch = policy.allowedCells.some((allowedCell) => allowedCell.every((v, i) => Math.abs(v - (state.policyCell[i] || 0)) < 0.01));
        if (!cellMatch) {
            return false;
        }
    }
    // Check attractor distance (if specified)
    if (policy.attractors && policy.attractors.length > 0 && policy.maxGeoDistance !== undefined) {
        const minDistance = Math.min(...policy.attractors.map((attractor) => {
            const attractorNorm = Math.sqrt(attractor.reduce((sum, x) => sum + x * x, 0));
            const projectedAttractor = attractorNorm >= 1.0 ? (0, hyperbolic_1.projectEmbeddingToBall)(attractor) : attractor;
            return (0, hyperbolic_1.hyperbolicDistance)(pos, projectedAttractor);
        }));
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
function predicatePath(egg, state) {
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
function predicateQuorum(egg, state, verifyApproval) {
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
async function deriveKey(sharedSecret, egg, state) {
    // Build domain separation tag
    const encoder = new TextEncoder();
    const tongueBytes = encoder.encode(egg.policy.primaryTongue);
    // Use position directly if already in ball; only project real embeddings (norm >= 1)
    const posNorm = Math.sqrt(state.position.reduce((sum, x) => sum + x * x, 0));
    const pos = posNorm >= 1.0 ? (0, hyperbolic_1.projectEmbeddingToBall)(state.position) : state.position;
    const radius = Math.sqrt(pos.reduce((sum, x) => sum + x * x, 0));
    const ring = getRingLevel(radius);
    const ringBytes = new Uint8Array([ring]);
    const cellBytes = new Uint8Array(state.policyCell.map((x) => Math.floor(x * 255)));
    const epochBytes = new Uint8Array(new BigUint64Array([BigInt(egg.header.epoch)]).buffer);
    // Path digest: hash of ring history
    const pathBytes = new Uint8Array(state.ringHistory);
    // Concatenate DST components
    const dst = new Uint8Array(tongueBytes.length + ringBytes.length + cellBytes.length + pathBytes.length + epochBytes.length);
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
    const derivedBits = await crypto.subtle.deriveBits({
        name: 'HKDF',
        hash: 'SHA-256',
        salt: dst,
        info: new Uint8Array(0),
    }, cryptoKey, 256);
    return new Uint8Array(derivedBits);
}
/**
 * P_crypto: Cryptographic predicate (AEAD decryption)
 *
 * Returns plaintext if successful, null if failed
 */
async function predicateCrypto(egg, state) {
    try {
        const key = await deriveKey(state.sharedSecret, egg, state);
        // Import key for AES-GCM
        const aesKey = await crypto.subtle.importKey('raw', key, { name: 'AES-GCM' }, false, [
            'decrypt',
        ]);
        // Decrypt
        const plaintext = await crypto.subtle.decrypt({
            name: 'AES-GCM',
            iv: egg.tag.slice(0, 12), // First 12 bytes as IV
            tagLength: 128,
        }, aesKey, egg.ciphertext);
        return new Uint8Array(plaintext);
    }
    catch {
        return null;
    }
}
// ═══════════════════════════════════════════════════════════════
// HATCH: Main Decision Function
// ═══════════════════════════════════════════════════════════════
/**
 * Generate fail-to-noise output (indistinguishable failure response)
 */
function generateFailureOutput(length) {
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
async function hatch(egg, state, verifyApproval = () => true) {
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
async function createEgg(plaintext, policy, sharedSecret, expectedState) {
    const id = crypto.randomUUID();
    const epoch = Date.now();
    // Create egg structure (needed for key derivation)
    const partialEgg = {
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
    const ciphertext = await crypto.subtle.encrypt({
        name: 'AES-GCM',
        iv,
        tagLength: 128,
    }, aesKey, plaintext);
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
//# sourceMappingURL=sacredEggs.js.map