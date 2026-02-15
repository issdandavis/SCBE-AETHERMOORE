"use strict";
/**
 * @file pqc-strategies.ts
 * @module crypto/pqc-strategies
 * @layer Layer 4, Layer 5, Layer 13
 * @component PQC Strategy Profiles + TriStitch + Geometric Key Binding
 * @version 1.0.0
 *
 * Three capabilities in one module:
 *
 * 1. **Strategy Profiles** — named algorithm combos (balanced-v1, paranoid-v1,
 *    iot-v1, conservative-v1) so governance can pick by risk level, not by
 *    algorithm name. Swappable in one place when NIST updates guidance.
 *
 * 2. **TriStitch Combiner** — run 3 KEMs from different PQC families and XOR
 *    all shared secrets. Attacker must break all three math problems at once.
 *    PQC + PQC + PQC, not just classical + PQC.
 *
 * 3. **Geometric Key Binding** — fuse the PQC shared secret with the 21D brain
 *    state via HKDF. The resulting session key is only valid when both crypto
 *    AND geometry agree. "Valid math but wrong intent" gets rejected.
 *
 * Usage:
 *   const strategy = getStrategy('balanced-v1');
 *   const session = await executeStrategy(strategy, brainState);
 *   // session.boundKey is HKDF(pqcSecret, SHA256(21D state))
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.STRATEGY_CATALOG = void 0;
exports.getStrategy = getStrategy;
exports.registerStrategy = registerStrategy;
exports.listStrategyNames = listStrategyNames;
exports.clearCustomStrategies = clearCustomStrategies;
exports.triStitch = triStitch;
exports.geometricFingerprint = geometricFingerprint;
exports.bindKeyToGeometry = bindKeyToGeometry;
exports.verifyGeometricBinding = verifyGeometricBinding;
exports.executeStrategy = executeStrategy;
exports.signWithStrategy = signWithStrategy;
const crypto_1 = require("crypto");
const quantum_safe_js_1 = require("./quantum-safe.js");
/** Built-in strategy catalog */
exports.STRATEGY_CATALOG = {
    'balanced-v1': {
        name: 'balanced-v1',
        description: 'Lattice KEM + lattice sig + classical hybrid. Standard SCBE default.',
        kemAlgorithms: ['ML-KEM-768'],
        sigAlgorithm: 'ML-DSA-65',
        classicalHybrid: true,
        minNistLevel: 3,
        useCase: 'General-purpose governance, API requests, fleet coordination',
        families: ['lattice'],
    },
    'paranoid-v1': {
        name: 'paranoid-v1',
        description: 'TriStitch: 3-family KEM (lattice + code + lattice-L5) + hash-based sig.',
        kemAlgorithms: ['ML-KEM-768', 'Classic-McEliece-348864', 'ML-KEM-1024'],
        sigAlgorithm: 'SLH-DSA-256s',
        classicalHybrid: true,
        minNistLevel: 5,
        useCase: 'High-value governance decisions, key ceremony, sentinel escalation',
        families: ['lattice', 'code-based', 'hash-based'],
    },
    'conservative-v1': {
        name: 'conservative-v1',
        description: 'Lattice KEM + hash-based sig. Two different math problems.',
        kemAlgorithms: ['ML-KEM-768'],
        sigAlgorithm: 'SLH-DSA-128s',
        classicalHybrid: true,
        minNistLevel: 3,
        useCase: 'Long-term audit records, provenance tracking, compliance',
        families: ['lattice', 'hash-based'],
    },
    'iot-v1': {
        name: 'iot-v1',
        description: 'Lightweight lattice KEM + sig. Minimizes bandwidth and compute.',
        kemAlgorithms: ['ML-KEM-512'],
        sigAlgorithm: 'ML-DSA-44',
        classicalHybrid: false,
        minNistLevel: 1,
        useCase: 'Edge devices, IoT agents, bandwidth-constrained environments',
        families: ['lattice'],
    },
};
// User-defined strategies
const customStrategies = new Map();
/** Get a strategy by name. Checks custom, then built-in catalog. */
function getStrategy(name) {
    const custom = customStrategies.get(name);
    if (custom)
        return custom;
    const builtin = exports.STRATEGY_CATALOG[name];
    if (builtin)
        return builtin;
    throw new Error(`Unknown PQC strategy: ${name}. Available: ${listStrategyNames().join(', ')}`);
}
/** Register a custom strategy profile */
function registerStrategy(strategy) {
    customStrategies.set(strategy.name, strategy);
}
/** List all available strategy names */
function listStrategyNames() {
    return [...Object.keys(exports.STRATEGY_CATALOG), ...customStrategies.keys()];
}
/** Clear custom strategies (for testing) */
function clearCustomStrategies() {
    customStrategies.clear();
}
/**
 * TriStitch: run multiple KEMs from different families and XOR-combine
 * all shared secrets. The combined secret is compromised only if ALL
 * constituent families are broken simultaneously.
 *
 * @param kemNames - Array of KEM algorithm names (1-4)
 * @param classicalHybrid - XOR in 32 random bytes (classical ECDH placeholder)
 * @returns Combined secret + per-KEM audit data
 */
async function triStitch(kemNames, classicalHybrid = true) {
    if (kemNames.length === 0) {
        throw new Error('TriStitch requires at least one KEM algorithm');
    }
    if (kemNames.length > 4) {
        throw new Error('TriStitch supports at most 4 KEM algorithms');
    }
    const kems = kemNames.map((n) => (0, quantum_safe_js_1.getKEM)(n));
    const keyPairs = [];
    const encapsulations = [];
    // Step 1: Generate key pairs and encapsulate for each KEM
    for (const kem of kems) {
        const kp = await kem.generateKeyPair();
        keyPairs.push(kp);
        const enc = await kem.encapsulate(kp.publicKey);
        encapsulations.push(enc);
    }
    // Step 2: XOR all shared secrets together
    const combined = new Uint8Array(32);
    for (const enc of encapsulations) {
        for (let i = 0; i < 32; i++) {
            combined[i] ^= enc.sharedSecret[i];
        }
    }
    // Step 3: Optionally XOR in classical randomness
    let classicalUsed = false;
    if (classicalHybrid) {
        const classicalBytes = new Uint8Array((0, crypto_1.createHash)('sha256').update(Buffer.from(crypto.getRandomValues(new Uint8Array(32)))).digest());
        for (let i = 0; i < 32; i++) {
            combined[i] ^= classicalBytes[i];
        }
        classicalUsed = true;
    }
    // Step 4: Build audit trail
    const families = new Set();
    const kemResults = kems.map((kem, i) => {
        families.add(kem.descriptor.family);
        return {
            algorithm: kem.descriptor.name,
            family: kem.descriptor.family,
            ciphertext: encapsulations[i].ciphertext,
            secretSize: encapsulations[i].sharedSecret.length,
        };
    });
    return {
        result: {
            combinedSecret: combined,
            kemResults,
            familyCount: families.size,
            classicalComponent: classicalUsed,
        },
        keyPairs,
    };
}
// ============================================================
// GEOMETRIC KEY BINDING (21D → Session Key)
// ============================================================
/**
 * HKDF-SHA256: extract-then-expand.
 * Inline to avoid import cycle with hkdf.ts (which imports node:crypto directly).
 */
function hkdf256(ikm, salt, info, len) {
    // Extract
    const prk = (0, crypto_1.createHmac)('sha256', Buffer.from(salt)).update(Buffer.from(ikm)).digest();
    // Expand
    const n = Math.ceil(len / 32);
    let t = Buffer.alloc(0);
    let okm = Buffer.alloc(0);
    for (let i = 0; i < n; i++) {
        t = (0, crypto_1.createHmac)('sha256', prk)
            .update(Buffer.concat([t, Buffer.from(info), Buffer.from([i + 1])]))
            .digest();
        okm = Buffer.concat([okm, t]);
    }
    return new Uint8Array(okm.subarray(0, len));
}
/**
 * Compute the geometric fingerprint of a 21D brain state.
 *
 * SHA-256 over the IEEE 754 double representation of all 21 components,
 * preserving full precision including decimal drift artifacts.
 *
 * @param state - 21D brain state vector
 * @returns 32-byte fingerprint
 */
function geometricFingerprint(state) {
    const buf = Buffer.alloc(state.length * 8);
    for (let i = 0; i < state.length; i++) {
        buf.writeDoubleBE(state[i], i * 8);
    }
    return new Uint8Array((0, crypto_1.createHash)('sha256').update(buf).digest());
}
/**
 * Bind a PQC shared secret to a 21D brain state.
 *
 * boundKey = HKDF-SHA256(
 *   ikm  = pqcSharedSecret,
 *   salt = SHA256(21D state as IEEE 754 doubles),
 *   info = "scbe:geo-bind:v1|norm=X.XXX|phase=N"
 * )
 *
 * The resulting session key is valid only when:
 * 1. The PQC crypto decrypts correctly, AND
 * 2. The geometric state matches what was bound at key creation.
 *
 * "Valid math but wrong intent" → wrong geometric fingerprint → wrong key.
 *
 * @param sharedSecret - PQC shared secret (32 bytes from KEM/TriStitch)
 * @param brainState - 21D state vector [SCBE(6) + nav(6) + cog(3) + sem(3) + swarm(3)]
 * @param config - Optional binding configuration
 * @returns Bound session key + metadata
 */
function bindKeyToGeometry(sharedSecret, brainState, config = {}) {
    const domain = config.domain ?? 'scbe:geo-bind:v1';
    const includeNorm = config.includeNorm ?? true;
    const includePhase = config.includePhase ?? true;
    // Step 1: Compute geometric fingerprint (salt)
    const geoFingerprint = geometricFingerprint(brainState);
    // Step 2: Compute Poincaré norm of the state
    let normSq = 0;
    for (const x of brainState)
        normSq += x * x;
    const stateNorm = Math.sqrt(normSq);
    // Step 3: Build domain-separated info string
    let info = domain;
    if (includeNorm) {
        info += `|norm=${stateNorm.toFixed(6)}`;
    }
    if (includePhase) {
        // Phase index: which Sacred Tongue has maximum weight (first 6 components)
        let maxIdx = 0;
        let maxVal = -Infinity;
        const phaseLen = Math.min(6, brainState.length);
        for (let i = 0; i < phaseLen; i++) {
            if (Math.abs(brainState[i]) > maxVal) {
                maxVal = Math.abs(brainState[i]);
                maxIdx = i;
            }
        }
        info += `|phase=${maxIdx}`;
    }
    const infoBytes = new TextEncoder().encode(info);
    // Step 4: HKDF derive the bound key
    const boundKey = hkdf256(sharedSecret, geoFingerprint, infoBytes, 32);
    // Step 5: Compute key ID for audit trail
    const keyId = (0, crypto_1.createHash)('sha256').update(Buffer.from(boundKey)).digest('hex').slice(0, 16);
    return { boundKey, geoFingerprint, keyId, stateNorm };
}
/**
 * Verify that a key binding matches an expected geometric state.
 *
 * Re-derives the bound key from the same inputs and compares.
 * Uses constant-time comparison to prevent timing attacks.
 *
 * @param boundKey - Previously derived bound key
 * @param sharedSecret - Original PQC shared secret
 * @param brainState - Current 21D state to verify against
 * @param config - Same config used during binding
 * @returns true if geometric state matches
 */
function verifyGeometricBinding(boundKey, sharedSecret, brainState, config = {}) {
    const rederived = bindKeyToGeometry(sharedSecret, brainState, config);
    // Constant-time comparison
    if (boundKey.length !== rederived.boundKey.length)
        return false;
    let diff = 0;
    for (let i = 0; i < boundKey.length; i++) {
        diff |= boundKey[i] ^ rederived.boundKey[i];
    }
    return diff === 0;
}
/**
 * Execute a complete PQC strategy with geometric binding.
 *
 * This is the top-level API for governance:
 *   1. Resolve strategy → algorithm combos
 *   2. TriStitch KEMs → combined shared secret
 *   3. Bind to 21D geometric state → session key
 *   4. Generate signature key pair for decision signing
 *
 * @param strategyName - Strategy profile name (e.g., 'balanced-v1')
 * @param brainState - Current 21D brain state for geometric binding
 * @param geoConfig - Optional geometric binding config
 * @returns Complete execution result with bound key + signing capability
 */
async function executeStrategy(strategyName, brainState, geoConfig) {
    const strategy = getStrategy(strategyName);
    // Step 1: TriStitch KEMs
    const { result: triStitchResult } = await triStitch(strategy.kemAlgorithms, strategy.classicalHybrid);
    // Step 2: Geometric binding
    const boundKey = bindKeyToGeometry(triStitchResult.combinedSecret, brainState, geoConfig);
    // Step 3: Signature key pair
    const sig = (0, quantum_safe_js_1.getSignature)(strategy.sigAlgorithm);
    const sigKeyPair = await sig.generateKeyPair();
    return {
        strategyName: strategy.name,
        boundKey,
        triStitch: triStitchResult,
        sigKeyPair,
        sigAlgorithm: strategy.sigAlgorithm,
        families: strategy.families,
        timestamp: Date.now(),
    };
}
/**
 * Sign a governance decision using a strategy execution result.
 *
 * @param message - The governance decision payload
 * @param execution - Result from executeStrategy()
 * @returns Signature bytes
 */
async function signWithStrategy(message, execution) {
    const sig = (0, quantum_safe_js_1.getSignature)(execution.sigAlgorithm);
    return sig.sign(message, execution.sigKeyPair.secretKey);
}
//# sourceMappingURL=pqc-strategies.js.map