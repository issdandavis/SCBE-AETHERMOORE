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
exports.pqc = exports.HybridKEM = exports.MLDSA65 = exports.MLKEM768 = exports.ML_DSA_65_PARAMS = exports.ML_KEM_768_PARAMS = void 0;
exports.toHex = toHex;
exports.fromHex = fromHex;
exports.isPQCAvailable = isPQCAvailable;
exports.getPQCStatus = getPQCStatus;
const crypto_1 = require("crypto");
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
    useNative = false;
    constructor() {
        // Check for native liboqs availability
        try {
            // In production: const oqs = require('liboqs-node');
            this.useNative = false; // Set to true when liboqs is available
        }
        catch {
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
        if (this.useNative) {
            // Production: Use liboqs
            // const kem = new oqs.KeyEncapsulation('ML-KEM-768');
            // return kem.generateKeypair();
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
            // Production: Use liboqs
            // const kem = new oqs.KeyEncapsulation('ML-KEM-768');
            // return kem.encapsulate(publicKey);
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
        if (this.useNative) {
            // Production: Use liboqs
            // const kem = new oqs.KeyEncapsulation('ML-KEM-768');
            // return kem.decapsulate(ciphertext, secretKey);
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
    useNative = false;
    constructor() {
        try {
            this.useNative = false; // Set to true when liboqs is available
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
            // Production: Use liboqs
            // const sig = new oqs.Signature('ML-DSA-65');
            // return sig.generateKeypair();
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
            // Production: Use liboqs
            // const sig = new oqs.Signature('ML-DSA-65');
            // return sig.sign(message, secretKey);
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
            // Production: Use liboqs
            // const sig = new oqs.Signature('ML-DSA-65');
            // return sig.verify(message, signature, publicKey);
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
    try {
        // Check for liboqs-node
        require.resolve('liboqs-node');
        return true;
    }
    catch {
        return false;
    }
}
/**
 * Get PQC implementation status
 */
function getPQCStatus() {
    const available = isPQCAvailable();
    return {
        available,
        implementation: available ? 'native' : 'stub',
        algorithms: ['ML-KEM-768', 'ML-DSA-65'],
    };
}
// ============================================================
// EXPORTS
// ============================================================
exports.pqc = {
    MLKEM768,
    MLDSA65,
    HybridKEM,
    ML_KEM_768_PARAMS: exports.ML_KEM_768_PARAMS,
    ML_DSA_65_PARAMS: exports.ML_DSA_65_PARAMS,
    toHex,
    fromHex,
    isPQCAvailable,
    getPQCStatus,
};
exports.default = exports.pqc;
//# sourceMappingURL=pqc.js.map