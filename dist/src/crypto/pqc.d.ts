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
export interface MLKEMKeyPair {
    publicKey: Uint8Array;
    secretKey: Uint8Array;
}
export interface MLKEMEncapsulation {
    ciphertext: Uint8Array;
    sharedSecret: Uint8Array;
}
export interface MLDSAKeyPair {
    publicKey: Uint8Array;
    secretKey: Uint8Array;
}
export interface PQCConfig {
    kemAlgorithm: 'ML-KEM-512' | 'ML-KEM-768' | 'ML-KEM-1024';
    dsaAlgorithm: 'ML-DSA-44' | 'ML-DSA-65' | 'ML-DSA-87';
}
export declare const ML_KEM_768_PARAMS: {
    readonly name: "ML-KEM-768";
    readonly securityLevel: 3;
    readonly publicKeySize: 1184;
    readonly secretKeySize: 2400;
    readonly ciphertextSize: 1088;
    readonly sharedSecretSize: 32;
    readonly n: 256;
    readonly k: 3;
    readonly q: 3329;
    readonly eta1: 2;
    readonly eta2: 2;
    readonly du: 10;
    readonly dv: 4;
};
export declare const ML_DSA_65_PARAMS: {
    readonly name: "ML-DSA-65";
    readonly securityLevel: 3;
    readonly publicKeySize: 1952;
    readonly secretKeySize: 4032;
    readonly signatureSize: 3293;
    readonly n: 256;
    readonly k: 6;
    readonly l: 5;
    readonly q: 8380417;
    readonly eta: 4;
    readonly tau: 49;
    readonly gamma1: 524288;
    readonly gamma2: 261888;
    readonly beta: 196;
};
/**
 * ML-KEM-768 Key Encapsulation Mechanism
 *
 * In production, this would use liboqs or @noble/post-quantum.
 * This stub provides the correct interface and data sizes.
 */
export declare class MLKEM768 {
    private static instance;
    private useNative;
    private constructor();
    static getInstance(): MLKEM768;
    /**
     * Generate ML-KEM-768 key pair
     *
     * @returns Key pair with public and secret keys
     */
    generateKeyPair(): Promise<MLKEMKeyPair>;
    /**
     * Encapsulate: Generate shared secret using public key
     *
     * @param publicKey - Recipient's public key
     * @returns Ciphertext and shared secret
     */
    encapsulate(publicKey: Uint8Array): Promise<MLKEMEncapsulation>;
    /**
     * Decapsulate: Recover shared secret using secret key
     *
     * @param ciphertext - Encapsulated ciphertext
     * @param secretKey - Recipient's secret key
     * @returns Shared secret
     */
    decapsulate(ciphertext: Uint8Array, secretKey: Uint8Array): Promise<Uint8Array>;
    private expandKey;
    private deriveSharedSecret;
    private validatePublicKey;
    private validateSecretKey;
    private validateCiphertext;
}
/**
 * ML-DSA-65 Digital Signature Algorithm (Dilithium3)
 *
 * In production, this would use liboqs or @noble/post-quantum.
 * This stub provides the correct interface and data sizes.
 */
export declare class MLDSA65 {
    private static instance;
    private useNative;
    private constructor();
    static getInstance(): MLDSA65;
    /**
     * Generate ML-DSA-65 key pair
     *
     * @returns Key pair with public and secret keys
     */
    generateKeyPair(): Promise<MLDSAKeyPair>;
    /**
     * Sign a message
     *
     * @param message - Message to sign
     * @param secretKey - Signer's secret key
     * @returns Signature bytes
     */
    sign(message: Uint8Array, secretKey: Uint8Array): Promise<Uint8Array>;
    /**
     * Verify a signature
     *
     * @param message - Original message
     * @param signature - Signature to verify
     * @param publicKey - Signer's public key
     * @returns True if valid, false otherwise
     */
    verify(message: Uint8Array, signature: Uint8Array, publicKey: Uint8Array): Promise<boolean>;
    private expandKey;
    private validatePublicKey;
    private validateSecretKey;
    private validateSignature;
}
export interface HybridKeyPair {
    classical: {
        publicKey: Uint8Array;
        privateKey: Uint8Array;
    };
    pqc: MLKEMKeyPair;
}
export interface HybridEncapsulation {
    classical: {
        ciphertext: Uint8Array;
        sharedSecret: Uint8Array;
    };
    pqc: MLKEMEncapsulation;
    combinedSecret: Uint8Array;
}
/**
 * Hybrid encryption combining classical (ECDH) and PQC (ML-KEM-768)
 *
 * This provides "belt and suspenders" security:
 * - If classical crypto is broken by quantum computers, PQC protects
 * - If ML-KEM has unknown weaknesses, classical protects
 */
export declare class HybridKEM {
    private mlkem;
    constructor();
    /**
     * Generate hybrid key pair
     */
    generateKeyPair(): Promise<HybridKeyPair>;
    /**
     * Hybrid encapsulation
     *
     * @param publicKey - Hybrid public key
     * @returns Combined encapsulation with XORed shared secret
     */
    encapsulate(publicKey: HybridKeyPair): Promise<HybridEncapsulation>;
    /**
     * Hybrid decapsulation
     *
     * @param encapsulation - Hybrid encapsulation
     * @param secretKey - Hybrid secret key
     * @returns Combined shared secret
     */
    decapsulate(encapsulation: HybridEncapsulation, secretKey: HybridKeyPair): Promise<Uint8Array>;
}
/**
 * Encode bytes to hex string
 */
export declare function toHex(bytes: Uint8Array): string;
/**
 * Decode hex string to bytes
 */
export declare function fromHex(hex: string): Uint8Array;
/**
 * Check if PQC algorithms are available (native liboqs)
 */
export declare function isPQCAvailable(): boolean;
/**
 * Get PQC implementation status
 */
export declare function getPQCStatus(): {
    available: boolean;
    implementation: 'native' | 'stub';
    algorithms: string[];
};
/**
 * Consensus result enum matching Python implementation
 */
export declare enum ConsensusResult {
    ACCEPT = "accept",
    REJECT = "reject",
    KEM_FAIL = "kem_fail",
    DSA_FAIL = "dsa_fail",
    CONSENSUS_FAIL = "consensus_fail"
}
/**
 * Authorization context for dual lattice binding
 */
export interface AuthorizationContext {
    userId: string;
    deviceFingerprint: string;
    timestamp: number;
    sessionNonce: Uint8Array;
    threatLevel: number;
}
/**
 * Authorization token structure
 */
export interface AuthorizationToken {
    payload: {
        context: string;
        decision: string;
        timestamp: number;
        kemCiphertext: string;
    };
    signature: string;
    consensusHash: string;
    sessionKeyId: string;
}
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
export declare class DualLatticeConsensus {
    private kem;
    private dsa;
    private kemKeyPair;
    private dsaKeyPair;
    private decisionLog;
    private static readonly TIMESTAMP_WINDOW;
    constructor();
    /**
     * Initialize key pairs for the consensus system
     */
    initialize(): Promise<void>;
    /**
     * Create a dual-signed authorization token
     * Both KEM-derived key and DSA signature required
     */
    createAuthorizationToken(context: AuthorizationContext, decision: string): Promise<AuthorizationToken>;
    /**
     * Verify a dual-signed authorization token
     * Both KEM decapsulation and DSA verification must succeed
     */
    verifyAuthorizationToken(token: AuthorizationToken): Promise<{
        result: ConsensusResult;
        reason: string;
    }>;
    /**
     * Get the decision log
     */
    getDecisionLog(): Array<{
        timestamp: number;
        result: string;
        sessionKeyId: string;
    }>;
    /**
     * Check if PQC backend is available
     */
    isPQCAvailable(): boolean;
    /**
     * Get PQC status
     */
    getPQCStatus(): {
        available: boolean;
        implementation: 'native' | 'stub';
        algorithms: string[];
    };
    private serializeContext;
    private hashWithDomain;
    private combineHashes;
}
export declare const pqc: {
    MLKEM768: typeof MLKEM768;
    MLDSA65: typeof MLDSA65;
    HybridKEM: typeof HybridKEM;
    DualLatticeConsensus: typeof DualLatticeConsensus;
    ConsensusResult: typeof ConsensusResult;
    ML_KEM_768_PARAMS: {
        readonly name: "ML-KEM-768";
        readonly securityLevel: 3;
        readonly publicKeySize: 1184;
        readonly secretKeySize: 2400;
        readonly ciphertextSize: 1088;
        readonly sharedSecretSize: 32;
        readonly n: 256;
        readonly k: 3;
        readonly q: 3329;
        readonly eta1: 2;
        readonly eta2: 2;
        readonly du: 10;
        readonly dv: 4;
    };
    ML_DSA_65_PARAMS: {
        readonly name: "ML-DSA-65";
        readonly securityLevel: 3;
        readonly publicKeySize: 1952;
        readonly secretKeySize: 4032;
        readonly signatureSize: 3293;
        readonly n: 256;
        readonly k: 6;
        readonly l: 5;
        readonly q: 8380417;
        readonly eta: 4;
        readonly tau: 49;
        readonly gamma1: 524288;
        readonly gamma2: 261888;
        readonly beta: 196;
    };
    toHex: typeof toHex;
    fromHex: typeof fromHex;
    isPQCAvailable: typeof isPQCAvailable;
    getPQCStatus: typeof getPQCStatus;
};
export default pqc;
//# sourceMappingURL=pqc.d.ts.map