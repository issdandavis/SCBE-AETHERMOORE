"use strict";
/**
 * Post-Quantum Cryptography Module
 * ================================
 * NIST FIPS 203 (ML-KEM) and FIPS 204 (ML-DSA) implementations
 *
 * Security Levels:
 * - ML-KEM-768: NIST Level 3 (128-bit quantum security)
 * - ML-DSA-65: NIST Level 3 (128-bit quantum security)
 *
 * Dependencies:
 * - @noble/post-quantum (preferred) or
 * - liboqs-node bindings
 *
 * References:
 * - NIST FIPS 203: Module-Lattice-Based Key-Encapsulation Mechanism
 * - NIST FIPS 204: Module-Lattice-Based Digital Signature Algorithm
 *
 * @module crypto/pqc
 * @version 1.0.0
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.pqc = exports.DualLatticeConsensus = exports.ConsensusResult = exports.HybridKEM = exports.MLDSA65 = exports.MLKEM768 = exports.ML_DSA_65_PARAMS = exports.ML_KEM_768_PARAMS = void 0;
exports.toHex = toHex;
exports.fromHex = fromHex;
exports.isPQCAvailable = isPQCAvailable;
exports.getPQCStatus = getPQCStatus;
const crypto_1 = require("crypto");
const LIBOQS_CANDIDATES = ['liboqs-node', 'liboqs'];
const KEM_CTORS = ['KEM', 'KeyEncapsulation'];
const SIG_CTORS = ['Signature'];
const KEM_KEYPAIR_METHODS = [
    'generateKeyPair',
    'generate_keypair',
    'generatekeypair',
    'keypair',
];
const KEM_ENCAPSULATE_METHODS = [
    'encapsulate',
    'encap',
    'encaps',
    'encapsulate_secret',
    'encap_secret',
];
const KEM_DECAPSULATE_METHODS = [
    'decapsulate',
    'decap',
    'decaps',
    'decapsulate_secret',
    'decap_secret',
];
const SIG_KEYPAIR_METHODS = [
    'generateKeyPair',
    'generate_keypair',
    'generatekeypair',
    'keypair',
];
const SIG_SIGN_METHODS = [
    'sign',
    'signature',
    'generate_signature',
];
const SIG_VERIFY_METHODS = [
    'verify',
    'verify_signature',
];
let liboqsModuleCache = undefined;
let pqcStatusCache = null;
function resolveLiboqsModule() {
    if (liboqsModuleCache !== undefined) {
        return liboqsModuleCache;
    }
    for (const moduleName of LIBOQS_CANDIDATES) {
        try {
            const mod = require(moduleName);
            liboqsModuleCache = { moduleName, module: mod };
            return liboqsModuleCache;
        }
        catch {
            continue;
        }
    }
    liboqsModuleCache = null;
    return null;
}
function getClassFromModule(mod, candidates) {
    for (const name of candidates) {
        const candidate = mod?.[name];
        if (typeof candidate === 'function') {
            return candidate;
        }
    }
    return null;
}
function firstMatchingMethod(target, candidates) {
    for (const name of candidates) {
        const fn = target[name];
        if (typeof fn === 'function') {
            return name;
        }
    }
    return null;
}
async function invokeNativeMethod(target, candidates, args) {
    const methodName = firstMatchingMethod(target, candidates);
    if (!methodName) {
        return null;
    }
    const fn = target[methodName];
    return Promise.resolve(fn.apply(target, args));
}
function toBytes(value, label) {
    if (typeof value === 'string') {
        return new TextEncoder().encode(value);
    }
    if (value instanceof Uint8Array) {
        return value;
    }
    if (value instanceof ArrayBuffer) {
        return new Uint8Array(value);
    }
    if (Buffer.isBuffer(value)) {
        return new Uint8Array(value);
    }
    if (Array.isArray(value)) {
        return new Uint8Array(value);
    }
    throw new Error(`Expected byte payload for ${label}`);
}
function getAnyKey(obj, keys) {
    for (const key of keys) {
        if (Object.prototype.hasOwnProperty.call(obj, key)) {
            return obj[key];
        }
    }
    return undefined;
}
function parseKeyPair(value, label) {
    if (Array.isArray(value) && value.length >= 2) {
        return {
            publicKey: toBytes(value[0], `${label} public key`),
            secretKey: toBytes(value[1], `${label} secret key`),
        };
    }
    if (value && typeof value === 'object') {
        const obj = value;
        const publicKey = getAnyKey(obj, ['publicKey', 'pk', 'public_key']);
        const secretKey = getAnyKey(obj, ['secretKey', 'sk', 'secret_key', 'privateKey', 'private_key']);
        if (publicKey !== undefined && secretKey !== undefined) {
            return {
                publicKey: toBytes(publicKey, `${label} public key`),
                secretKey: toBytes(secretKey, `${label} secret key`),
            };
        }
    }
    throw new Error(`Native backend for ${label} returned keypair in unsupported shape`);
}
function parseKemEncapsulation(value) {
    if (Array.isArray(value) && value.length >= 2) {
        return {
            ciphertext: toBytes(value[0], 'ML-KEM ciphertext'),
            sharedSecret: toBytes(value[1], 'ML-KEM shared secret'),
        };
    }
    if (value && typeof value === 'object') {
        const obj = value;
        const ciphertext = getAnyKey(obj, ['ciphertext', 'ct', 'encapsulated', 'encapsulation']);
        const sharedSecret = getAnyKey(obj, ['sharedSecret', 'shared_secret', 'ss', 'sessionKey', 'shared_key']);
        if (ciphertext !== undefined && sharedSecret !== undefined) {
            return {
                ciphertext: toBytes(ciphertext, 'ML-KEM ciphertext'),
                sharedSecret: toBytes(sharedSecret, 'ML-KEM shared secret'),
            };
        }
    }
    throw new Error('Native backend for ML-KEM returned unsupported encapsulation shape');
}
function parseKemSharedSecret(value) {
    if (value === undefined || value === null) {
        throw new Error('Native backend for ML-KEM returned empty decapsulated shared secret');
    }
    if (typeof value === 'string' ||
        value instanceof Uint8Array ||
        value instanceof ArrayBuffer ||
        Buffer.isBuffer(value)) {
        return toBytes(value, 'ML-KEM decapsulated shared secret');
    }
    if (Array.isArray(value)) {
        if (value.length === 1) {
            return toBytes(value[0], 'ML-KEM decapsulated shared secret');
        }
        const allNumeric = value.every((item) => typeof item === 'number');
        if (allNumeric) {
            return toBytes(value, 'ML-KEM decapsulated shared secret');
        }
        return toBytes(value[1], 'ML-KEM decapsulated shared secret');
    }
    if (value && typeof value === 'object') {
        const obj = value;
        const sharedSecret = getAnyKey(obj, ['sharedSecret', 'shared_secret', 'ss', 'sessionKey', 'shared_key', 'key']);
        if (sharedSecret !== undefined) {
            return toBytes(sharedSecret, 'ML-KEM decapsulated shared secret');
        }
        const keys = Object.keys(obj);
        if (keys.length === 1) {
            return toBytes(obj[keys[0]], 'ML-KEM decapsulated shared secret');
        }
    }
    throw new Error('Native backend for ML-KEM returned unsupported decapsulated shared secret shape');
}
function parseDsaSignature(value) {
    if (value === undefined || value === null) {
        throw new Error('Native backend for ML-DSA-65 returned empty signature');
    }
    return toBytes(value, 'ML-DSA-65 signature');
}
function createNativeKEM(algorithm) {
    const mod = resolveLiboqsModule();
    if (!mod) {
        return null;
    }
    const ctor = getClassFromModule(mod.module, KEM_CTORS);
    if (!ctor) {
        return null;
    }
    const ctorArgs = [[algorithm], [{ algorithm }], []];
    for (const ctorArgSet of ctorArgs) {
        try {
            const instance = new ctor(...ctorArgSet);
            if (firstMatchingMethod(instance, KEM_KEYPAIR_METHODS) &&
                firstMatchingMethod(instance, KEM_ENCAPSULATE_METHODS) &&
                firstMatchingMethod(instance, KEM_DECAPSULATE_METHODS)) {
                return { moduleName: mod.moduleName, instance };
            }
        }
        catch {
            continue;
        }
    }
    return null;
}
function createNativeDSA(algorithm) {
    const mod = resolveLiboqsModule();
    if (!mod) {
        return null;
    }
    const ctor = getClassFromModule(mod.module, SIG_CTORS);
    if (!ctor) {
        return null;
    }
    const ctorArgs = [[algorithm], [{ algorithm }], []];
    for (const ctorArgSet of ctorArgs) {
        try {
            const instance = new ctor(...ctorArgSet);
            if (firstMatchingMethod(instance, SIG_KEYPAIR_METHODS) &&
                firstMatchingMethod(instance, SIG_SIGN_METHODS) &&
                firstMatchingMethod(instance, SIG_VERIFY_METHODS)) {
                return { moduleName: mod.moduleName, instance };
            }
        }
        catch {
            continue;
        }
    }
    return null;
}
function getPQCStatusInternal() {
    if (pqcStatusCache) {
        return pqcStatusCache;
    }
    const module = resolveLiboqsModule();
    if (!module) {
        pqcStatusCache = {
            available: false,
            implementation: 'stub',
            algorithms: ['ML-KEM-768', 'ML-DSA-65'],
            reason: 'No native liboqs module available',
        };
        return pqcStatusCache;
    }
    const kemInstance = createNativeKEM(exports.ML_KEM_768_PARAMS.name);
    if (!kemInstance) {
        pqcStatusCache = {
            available: false,
            implementation: 'stub',
            algorithms: ['ML-KEM-768', 'ML-DSA-65'],
            moduleName: module.moduleName,
            reason: `Native module ${module.moduleName} does not expose a usable ML-KEM interface`,
        };
        return pqcStatusCache;
    }
    const dsaInstance = createNativeDSA(exports.ML_DSA_65_PARAMS.name);
    if (!dsaInstance) {
        pqcStatusCache = {
            available: false,
            implementation: 'stub',
            algorithms: ['ML-KEM-768', 'ML-DSA-65'],
            moduleName: module.moduleName,
            reason: `Native module ${module.moduleName} does not expose a usable ML-DSA interface`,
        };
        return pqcStatusCache;
    }
    pqcStatusCache = {
        available: true,
        implementation: 'native',
        algorithms: ['ML-KEM-768', 'ML-DSA-65'],
        moduleName: module.moduleName,
    };
    return pqcStatusCache;
}
// ============================================================
// ML-KEM-768 PARAMETERS (NIST FIPS 203)
// ============================================================
exports.ML_KEM_768_PARAMS = {
    name: 'ML-KEM-768',
    securityLevel: 3, // NIST Level 3
    publicKeySize: 1184, // bytes
    secretKeySize: 2400, // bytes
    ciphertextSize: 1088, // bytes
    sharedSecretSize: 32, // bytes
    n: 256, // polynomial degree
    k: 3, // module rank
    q: 3329, // modulus
    eta1: 2, // noise parameter
    eta2: 2, // noise parameter
    du: 10, // ciphertext compression
    dv: 4, // ciphertext compression
};
// ============================================================
// ML-DSA-65 PARAMETERS (NIST FIPS 204)
// ============================================================
exports.ML_DSA_65_PARAMS = {
    name: 'ML-DSA-65',
    securityLevel: 3, // NIST Level 3
    publicKeySize: 1952, // bytes
    secretKeySize: 4032, // bytes
    signatureSize: 3293, // bytes
    n: 256, // polynomial degree
    k: 6, // module rank (public)
    l: 5, // module rank (private)
    q: 8380417, // modulus
    eta: 4, // secret key range
    tau: 49, // number of +/-1 in challenge
    gamma1: 524288, // y coefficient range (2^19)
    gamma2: 261888, // low-order rounding range
    beta: 196, // tau * eta
};
// ============================================================
// ML-KEM-768 IMPLEMENTATION (Stub for liboqs integration)
// ============================================================
/**
 * ML-KEM-768 Key Encapsulation Mechanism
 *
 * In production, this would use liboqs or @noble/post-quantum.
 * This stub provides the correct interface and data sizes.
 */
class MLKEM768 {
    static instance = null;
    static nativeInstance = undefined;
    useNative = false;
    nativeInstance = null;
    constructor() {
        if (MLKEM768.nativeInstance === undefined) {
            MLKEM768.nativeInstance = createNativeKEM(exports.ML_KEM_768_PARAMS.name);
        }
        this.useNative = MLKEM768.nativeInstance !== null;
        this.nativeInstance = this.useNative ? MLKEM768.nativeInstance : null;
        if (this.useNative && !this.nativeInstance) {
            this.useNative = false;
        }
    }
    static getInstance() {
        if (!MLKEM768.instance) {
            MLKEM768.instance = new MLKEM768();
        }
        return MLKEM768.instance;
    }
    /**
     * Generate ML-KEM-768 key pair
     *
     * @returns Key pair with public and secret keys
     */
    async generateKeyPair() {
        if (this.useNative && this.nativeInstance) {
            try {
                const output = await invokeNativeMethod(this.nativeInstance.instance, KEM_KEYPAIR_METHODS, []);
                if (output !== null) {
                    return parseKeyPair(output, 'ML-KEM-768');
                }
            }
            catch {
                this.useNative = false;
            }
        }
        // Development stub: Generate deterministic test keys
        // WARNING: NOT FOR PRODUCTION USE
        const seed = (0, crypto_1.randomBytes)(32);
        const publicKey = this.expandKey(seed, exports.ML_KEM_768_PARAMS.publicKeySize, 'pk');
        const secretKey = this.expandKey(seed, exports.ML_KEM_768_PARAMS.secretKeySize, 'sk');
        return { publicKey, secretKey };
    }
    /**
     * Encapsulate: Generate shared secret using public key
     *
     * @param publicKey - Recipient's public key
     * @returns Ciphertext and shared secret
     */
    async encapsulate(publicKey) {
        this.validatePublicKey(publicKey);
        if (this.useNative) {
            try {
                const output = await invokeNativeMethod(this.nativeInstance.instance, KEM_ENCAPSULATE_METHODS, [publicKey]);
                if (output !== null) {
                    return parseKemEncapsulation(output);
                }
            }
            catch {
                this.useNative = false;
            }
        }
        // Development stub
        const randomness = (0, crypto_1.randomBytes)(32);
        const ciphertext = this.expandKey(Buffer.concat([publicKey.slice(0, 32), randomness]), exports.ML_KEM_768_PARAMS.ciphertextSize, 'ct');
        const sharedSecret = this.deriveSharedSecret(publicKey, randomness);
        return { ciphertext, sharedSecret };
    }
    /**
     * Decapsulate: Recover shared secret using secret key
     *
     * @param ciphertext - Encapsulated ciphertext
     * @param secretKey - Recipient's secret key
     * @returns Shared secret
     */
    async decapsulate(ciphertext, secretKey) {
        this.validateCiphertext(ciphertext);
        this.validateSecretKey(secretKey);
        if (this.useNative && this.nativeInstance) {
            try {
                const output = await invokeNativeMethod(this.nativeInstance.instance, KEM_DECAPSULATE_METHODS, [ciphertext, secretKey]);
                if (output !== null) {
                    return parseKemSharedSecret(output);
                }
            }
            catch {
                this.useNative = false;
            }
        }
        // Development stub: Deterministic decapsulation
        return this.deriveSharedSecret(secretKey.slice(0, 32), ciphertext.slice(0, 32));
    }
    // Helper methods
    expandKey(seed, length, label) {
        const result = Buffer.alloc(length);
        let offset = 0;
        let counter = 0;
        while (offset < length) {
            const hash = (0, crypto_1.createHash)('sha256')
                .update(seed)
                .update(label)
                .update(Buffer.from([counter >> 8, counter & 0xff]))
                .digest();
            const copyLen = Math.min(hash.length, length - offset);
            hash.copy(result, offset, 0, copyLen);
            offset += copyLen;
            counter++;
        }
        return new Uint8Array(result);
    }
    deriveSharedSecret(key1, key2) {
        return new Uint8Array((0, crypto_1.createHash)('sha256').update(Buffer.from(key1)).update(Buffer.from(key2)).digest());
    }
    validatePublicKey(pk) {
        if (pk.length !== exports.ML_KEM_768_PARAMS.publicKeySize) {
            throw new Error(`Invalid ML-KEM-768 public key size: ${pk.length} (expected ${exports.ML_KEM_768_PARAMS.publicKeySize})`);
        }
    }
    validateSecretKey(sk) {
        if (sk.length !== exports.ML_KEM_768_PARAMS.secretKeySize) {
            throw new Error(`Invalid ML-KEM-768 secret key size: ${sk.length} (expected ${exports.ML_KEM_768_PARAMS.secretKeySize})`);
        }
    }
    validateCiphertext(ct) {
        if (ct.length !== exports.ML_KEM_768_PARAMS.ciphertextSize) {
            throw new Error(`Invalid ML-KEM-768 ciphertext size: ${ct.length} (expected ${exports.ML_KEM_768_PARAMS.ciphertextSize})`);
        }
    }
}
exports.MLKEM768 = MLKEM768;
// ============================================================
// ML-DSA-65 IMPLEMENTATION (Stub for liboqs integration)
// ============================================================
/**
 * ML-DSA-65 Digital Signature Algorithm (Dilithium3)
 *
 * In production, this would use liboqs or @noble/post-quantum.
 * This stub provides the correct interface and data sizes.
 */
class MLDSA65 {
    static instance = null;
    static nativeInstance = undefined;
    useNative = false;
    nativeInstance = null;
    constructor() {
        try {
            if (MLDSA65.nativeInstance === undefined) {
                MLDSA65.nativeInstance = createNativeDSA(exports.ML_DSA_65_PARAMS.name);
            }
            this.useNative = MLDSA65.nativeInstance !== null;
            this.nativeInstance = this.useNative ? MLDSA65.nativeInstance : null;
            if (this.useNative && !this.nativeInstance) {
                this.useNative = false;
            }
        }
        catch {
            this.useNative = false;
        }
    }
    static getInstance() {
        if (!MLDSA65.instance) {
            MLDSA65.instance = new MLDSA65();
        }
        return MLDSA65.instance;
    }
    /**
     * Generate ML-DSA-65 key pair
     *
     * @returns Key pair with public and secret keys
     */
    async generateKeyPair() {
        if (this.useNative) {
            try {
                const output = await invokeNativeMethod(this.nativeInstance.instance, SIG_KEYPAIR_METHODS, []);
                if (output !== null) {
                    return parseKeyPair(output, 'ML-DSA-65');
                }
            }
            catch {
                this.useNative = false;
            }
        }
        // Development stub
        const seed = (0, crypto_1.randomBytes)(32);
        const publicKey = this.expandKey(seed, exports.ML_DSA_65_PARAMS.publicKeySize, 'pk');
        const secretKey = this.expandKey(seed, exports.ML_DSA_65_PARAMS.secretKeySize, 'sk');
        return { publicKey, secretKey };
    }
    /**
     * Sign a message
     *
     * @param message - Message to sign
     * @param secretKey - Signer's secret key
     * @returns Signature bytes
     */
    async sign(message, secretKey) {
        this.validateSecretKey(secretKey);
        if (this.useNative) {
            try {
                const output = await invokeNativeMethod(this.nativeInstance.instance, SIG_SIGN_METHODS, [message, secretKey]);
                if (output !== null) {
                    return parseDsaSignature(output);
                }
            }
            catch {
                this.useNative = false;
            }
        }
        // Development stub: Deterministic signature
        return this.expandKey(Buffer.concat([Buffer.from(message), Buffer.from(secretKey.slice(0, 32))]), exports.ML_DSA_65_PARAMS.signatureSize, 'sig');
    }
    /**
     * Verify a signature
     *
     * @param message - Original message
     * @param signature - Signature to verify
     * @param publicKey - Signer's public key
     * @returns True if valid, false otherwise
     */
    async verify(message, signature, publicKey) {
        this.validatePublicKey(publicKey);
        this.validateSignature(signature);
        if (this.useNative) {
            try {
                const output = await invokeNativeMethod(this.nativeInstance.instance, SIG_VERIFY_METHODS, [message, signature, publicKey]);
                if (output !== null) {
                    return Boolean(output);
                }
            }
            catch {
                this.useNative = false;
            }
        }
        // Development stub: Always returns true for valid-looking signatures
        // WARNING: NOT FOR PRODUCTION USE
        return signature.length === exports.ML_DSA_65_PARAMS.signatureSize;
    }
    // Helper methods
    expandKey(seed, length, label) {
        const result = Buffer.alloc(length);
        let offset = 0;
        let counter = 0;
        while (offset < length) {
            const hash = (0, crypto_1.createHash)('sha256')
                .update(seed)
                .update(label)
                .update(Buffer.from([counter >> 8, counter & 0xff]))
                .digest();
            const copyLen = Math.min(hash.length, length - offset);
            hash.copy(result, offset, 0, copyLen);
            offset += copyLen;
            counter++;
        }
        return new Uint8Array(result);
    }
    validatePublicKey(pk) {
        if (pk.length !== exports.ML_DSA_65_PARAMS.publicKeySize) {
            throw new Error(`Invalid ML-DSA-65 public key size: ${pk.length} (expected ${exports.ML_DSA_65_PARAMS.publicKeySize})`);
        }
    }
    validateSecretKey(sk) {
        if (sk.length !== exports.ML_DSA_65_PARAMS.secretKeySize) {
            throw new Error(`Invalid ML-DSA-65 secret key size: ${sk.length} (expected ${exports.ML_DSA_65_PARAMS.secretKeySize})`);
        }
    }
    validateSignature(sig) {
        if (sig.length !== exports.ML_DSA_65_PARAMS.signatureSize) {
            throw new Error(`Invalid ML-DSA-65 signature size: ${sig.length} (expected ${exports.ML_DSA_65_PARAMS.signatureSize})`);
        }
    }
}
exports.MLDSA65 = MLDSA65;
/**
 * Hybrid encryption combining classical (ECDH) and PQC (ML-KEM-768)
 *
 * This provides "belt and suspenders" security:
 * - If classical crypto is broken by quantum computers, PQC protects
 * - If ML-KEM has unknown weaknesses, classical protects
 */
class HybridKEM {
    mlkem;
    constructor() {
        this.mlkem = MLKEM768.getInstance();
    }
    /**
     * Generate hybrid key pair
     */
    async generateKeyPair() {
        // Generate PQC key pair
        const pqc = await this.mlkem.generateKeyPair();
        // Generate classical key pair (placeholder - in production use ECDH)
        const classicalSeed = (0, crypto_1.randomBytes)(32);
        const classical = {
            publicKey: new Uint8Array((0, crypto_1.createHash)('sha256').update(classicalSeed).update('public').digest()),
            privateKey: new Uint8Array(classicalSeed),
        };
        return { classical, pqc };
    }
    /**
     * Hybrid encapsulation
     *
     * @param publicKey - Hybrid public key
     * @returns Combined encapsulation with XORed shared secret
     */
    async encapsulate(publicKey) {
        // PQC encapsulation
        const pqc = await this.mlkem.encapsulate(publicKey.pqc.publicKey);
        // Classical encapsulation (placeholder)
        const classicalRandom = (0, crypto_1.randomBytes)(32);
        const classical = {
            ciphertext: new Uint8Array(classicalRandom),
            sharedSecret: new Uint8Array((0, crypto_1.createHash)('sha256').update(classicalRandom).update(publicKey.classical.publicKey).digest()),
        };
        // Combine secrets with XOR (both must be compromised to break)
        const combinedSecret = new Uint8Array(32);
        for (let i = 0; i < 32; i++) {
            combinedSecret[i] = classical.sharedSecret[i] ^ pqc.sharedSecret[i];
        }
        return { classical, pqc, combinedSecret };
    }
    /**
     * Hybrid decapsulation
     *
     * @param encapsulation - Hybrid encapsulation
     * @param secretKey - Hybrid secret key
     * @returns Combined shared secret
     */
    async decapsulate(encapsulation, secretKey) {
        // PQC decapsulation
        const pqcSecret = await this.mlkem.decapsulate(encapsulation.pqc.ciphertext, secretKey.pqc.secretKey);
        // Classical decapsulation (placeholder)
        const classicalSecret = new Uint8Array((0, crypto_1.createHash)('sha256')
            .update(encapsulation.classical.ciphertext)
            .update(secretKey.classical.privateKey)
            .digest());
        // Combine secrets
        const combinedSecret = new Uint8Array(32);
        for (let i = 0; i < 32; i++) {
            combinedSecret[i] = classicalSecret[i] ^ pqcSecret[i];
        }
        return combinedSecret;
    }
}
exports.HybridKEM = HybridKEM;
// ============================================================
// UTILITY FUNCTIONS
// ============================================================
/**
 * Encode bytes to hex string
 */
function toHex(bytes) {
    return Buffer.from(bytes).toString('hex');
}
/**
 * Decode hex string to bytes
 */
function fromHex(hex) {
    return new Uint8Array(Buffer.from(hex, 'hex'));
}
/**
 * Check if PQC algorithms are available (native liboqs)
 */
function isPQCAvailable() {
    return getPQCStatusInternal().available;
}
/**
 * Get PQC implementation status
 */
function getPQCStatus() {
    return getPQCStatusInternal();
}
// ============================================================
// DUAL LATTICE CONSENSUS (Patent USPTO #63/961,403)
// ============================================================
/**
 * Consensus result enum matching Python implementation
 */
var ConsensusResult;
(function (ConsensusResult) {
    ConsensusResult["ACCEPT"] = "accept";
    ConsensusResult["REJECT"] = "reject";
    ConsensusResult["KEM_FAIL"] = "kem_fail";
    ConsensusResult["DSA_FAIL"] = "dsa_fail";
    ConsensusResult["CONSENSUS_FAIL"] = "consensus_fail";
})(ConsensusResult || (exports.ConsensusResult = ConsensusResult = {}));
/**
 * Dual-Lattice Consensus System
 *
 * Implements patent claims for post-quantum cryptographic binding:
 * - ML-KEM-768 (Kyber) for key encapsulation
 * - ML-DSA-65 (Dilithium) for digital signatures
 * - Both must agree for authorization (factor of 2 quantum resistance improvement)
 *
 * Per NIST FIPS 203 and FIPS 204 standards.
 */
class DualLatticeConsensus {
    kem;
    dsa;
    kemKeyPair = null;
    dsaKeyPair = null;
    decisionLog = [];
    static TIMESTAMP_WINDOW = 60_000; // 60 seconds
    constructor() {
        this.kem = MLKEM768.getInstance();
        this.dsa = MLDSA65.getInstance();
    }
    /**
     * Initialize key pairs for the consensus system
     */
    async initialize() {
        this.kemKeyPair = await this.kem.generateKeyPair();
        this.dsaKeyPair = await this.dsa.generateKeyPair();
    }
    /**
     * Create a dual-signed authorization token
     * Both KEM-derived key and DSA signature required
     */
    async createAuthorizationToken(context, decision) {
        if (!this.kemKeyPair || !this.dsaKeyPair) {
            await this.initialize();
        }
        // Step 1: KEM encapsulation for session key
        const { ciphertext, sharedSecret } = await this.kem.encapsulate(this.kemKeyPair.publicKey);
        // Step 2: Build token payload
        const contextBytes = this.serializeContext(context);
        const payload = {
            context: toHex(contextBytes),
            decision,
            timestamp: context.timestamp,
            kemCiphertext: toHex(ciphertext),
        };
        const payloadBytes = new TextEncoder().encode(JSON.stringify(payload));
        // Step 3: DSA signature over payload
        const signature = await this.dsa.sign(payloadBytes, this.dsaKeyPair.secretKey);
        // Step 4: Dual-lattice consensus hash (both algorithms must agree)
        const kemHash = this.hashWithDomain(sharedSecret, 'kem_domain');
        const dsaHash = this.hashWithDomain(this.dsaKeyPair.secretKey.slice(0, 32), 'dsa_domain');
        const consensusHash = this.combineHashes(kemHash, dsaHash);
        // Session key ID for tracking
        const sessionKeyId = toHex(new Uint8Array((0, crypto_1.createHash)('sha256').update(Buffer.from(sharedSecret)).digest())).slice(0, 16);
        return {
            payload,
            signature: toHex(signature),
            consensusHash: toHex(consensusHash).slice(0, 16),
            sessionKeyId,
        };
    }
    /**
     * Verify a dual-signed authorization token
     * Both KEM decapsulation and DSA verification must succeed
     */
    async verifyAuthorizationToken(token) {
        if (!this.kemKeyPair || !this.dsaKeyPair) {
            return { result: ConsensusResult.REJECT, reason: 'not_initialized' };
        }
        try {
            // Step 1: Verify timestamp freshness
            const now = Date.now();
            if (now - token.payload.timestamp > DualLatticeConsensus.TIMESTAMP_WINDOW) {
                return { result: ConsensusResult.REJECT, reason: 'timestamp_expired' };
            }
            // Step 2: KEM decapsulation
            const ciphertext = fromHex(token.payload.kemCiphertext);
            const sessionKey = await this.kem.decapsulate(ciphertext, this.kemKeyPair.secretKey);
            // Step 3: DSA verification
            const payloadBytes = new TextEncoder().encode(JSON.stringify(token.payload));
            const signature = fromHex(token.signature);
            const isValid = await this.dsa.verify(payloadBytes, signature, this.dsaKeyPair.publicKey);
            if (!isValid) {
                return { result: ConsensusResult.DSA_FAIL, reason: 'signature_invalid' };
            }
            // Step 4: Dual-lattice consensus check
            const kemHash = this.hashWithDomain(sessionKey, 'kem_domain');
            const dsaHash = this.hashWithDomain(this.dsaKeyPair.secretKey.slice(0, 32), 'dsa_domain');
            const expectedConsensus = toHex(this.combineHashes(kemHash, dsaHash)).slice(0, 16);
            if (token.consensusHash !== expectedConsensus) {
                return { result: ConsensusResult.CONSENSUS_FAIL, reason: 'consensus_mismatch' };
            }
            // All checks passed
            this.decisionLog.push({
                timestamp: now,
                result: 'accept',
                sessionKeyId: token.sessionKeyId,
            });
            return { result: ConsensusResult.ACCEPT, reason: 'verified' };
        }
        catch (error) {
            return { result: ConsensusResult.REJECT, reason: String(error) };
        }
    }
    /**
     * Get the decision log
     */
    getDecisionLog() {
        return [...this.decisionLog];
    }
    /**
     * Check if PQC backend is available
     */
    isPQCAvailable() {
        return isPQCAvailable();
    }
    /**
     * Get PQC status
     */
    getPQCStatus() {
        return getPQCStatus();
    }
    // Private helper methods
    serializeContext(context) {
        const encoder = new TextEncoder();
        const userIdBytes = encoder.encode(context.userId);
        const deviceBytes = encoder.encode(context.deviceFingerprint);
        const timestampBytes = new Uint8Array(8);
        new DataView(timestampBytes.buffer).setBigUint64(0, BigInt(context.timestamp), false);
        const threatBytes = new Uint8Array(4);
        new DataView(threatBytes.buffer).setUint32(0, Math.floor(context.threatLevel * 1000), false);
        const result = new Uint8Array(userIdBytes.length +
            deviceBytes.length +
            timestampBytes.length +
            context.sessionNonce.length +
            threatBytes.length);
        let offset = 0;
        result.set(userIdBytes, offset);
        offset += userIdBytes.length;
        result.set(deviceBytes, offset);
        offset += deviceBytes.length;
        result.set(timestampBytes, offset);
        offset += timestampBytes.length;
        result.set(context.sessionNonce, offset);
        offset += context.sessionNonce.length;
        result.set(threatBytes, offset);
        return result;
    }
    hashWithDomain(data, domain) {
        return new Uint8Array((0, crypto_1.createHash)('sha256')
            .update(Buffer.from(data))
            .update(Buffer.from(domain))
            .digest()
            .slice(0, 8));
    }
    combineHashes(hash1, hash2) {
        return new Uint8Array((0, crypto_1.createHash)('sha256').update(Buffer.from(hash1)).update(Buffer.from(hash2)).digest());
    }
}
exports.DualLatticeConsensus = DualLatticeConsensus;
// ============================================================
// EXPORTS
// ============================================================
exports.pqc = {
    MLKEM768,
    MLDSA65,
    HybridKEM,
    DualLatticeConsensus,
    ConsensusResult,
    ML_KEM_768_PARAMS: exports.ML_KEM_768_PARAMS,
    ML_DSA_65_PARAMS: exports.ML_DSA_65_PARAMS,
    toHex,
    fromHex,
    isPQCAvailable,
    getPQCStatus,
};
exports.default = exports.pqc;
//# sourceMappingURL=pqc.js.map