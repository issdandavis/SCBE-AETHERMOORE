/**
 * SCBE Post-Quantum Cryptography Module
 *
 * Implements quantum-resistant cryptographic primitives for the SCBE pipeline:
 * - ML-KEM (Kyber) - Key Encapsulation Mechanism (NIST FIPS 203)
 * - ML-DSA (Dilithium) - Digital Signature Algorithm (NIST FIPS 204)
 * - Hybrid classical+quantum schemes
 *
 * This implementation uses @noble/post-quantum for pure TypeScript PQC.
 * For production, consider using liboqs bindings for optimized C implementations.
 *
 * References:
 * - NIST FIPS 203: Module-Lattice-Based Key-Encapsulation Mechanism Standard
 * - NIST FIPS 204: Module-Lattice-Based Digital Signature Standard
 * - Open Quantum Safe: https://openquantumsafe.org/
 */
/**
 * ML-KEM security levels (NIST FIPS 203)
 */
export type MLKEMLevel = 512 | 768 | 1024;
/**
 * ML-DSA security levels (NIST FIPS 204)
 */
export type MLDSALevel = 44 | 65 | 87;
/**
 * Key pair for ML-KEM
 */
export interface MLKEMKeyPair {
    publicKey: Uint8Array;
    secretKey: Uint8Array;
    level: MLKEMLevel;
}
/**
 * Key pair for ML-DSA
 */
export interface MLDSAKeyPair {
    publicKey: Uint8Array;
    secretKey: Uint8Array;
    level: MLDSALevel;
}
/**
 * Encapsulated key result
 */
export interface EncapsulationResult {
    ciphertext: Uint8Array;
    sharedSecret: Uint8Array;
}
/**
 * Hybrid encryption result
 */
export interface HybridEncryptionResult {
    kemCiphertext: Uint8Array;
    aesCiphertext: Uint8Array;
    nonce: Uint8Array;
    tag: Uint8Array;
}
/**
 * PQC configuration
 */
export interface PQCConfig {
    kemLevel?: MLKEMLevel;
    dsaLevel?: MLDSALevel;
    hybridMode?: boolean;
}
/**
 * Number-Theoretic Transform (NTT) for polynomial multiplication
 * Core operation for lattice-based cryptography
 */
export declare function ntt(poly: number[]): number[];
/**
 * Inverse NTT
 */
export declare function invNtt(poly: number[]): number[];
/**
 * Generate cryptographically secure random bytes
 * Uses Web Crypto API when available, falls back to Math.random (NOT SECURE)
 */
export declare function secureRandomBytes(length: number): Uint8Array;
/**
 * SHAKE128 extendable output function (XOF)
 */
export declare function shake128(input: Uint8Array, outputLength: number): Uint8Array;
/**
 * SHAKE256 extendable output function (XOF)
 */
export declare function shake256(input: Uint8Array, outputLength: number): Uint8Array;
/**
 * Generate ML-KEM key pair
 *
 * @param level - Security level (512, 768, or 1024)
 * @returns Key pair with public and secret keys
 */
export declare function mlkemKeyGen(level?: MLKEMLevel): MLKEMKeyPair;
/**
 * ML-KEM encapsulation - generate shared secret and ciphertext
 *
 * @param publicKey - Recipient's public key
 * @param level - Security level
 * @returns Ciphertext and shared secret
 */
export declare function mlkemEncapsulate(publicKey: Uint8Array, level?: MLKEMLevel): EncapsulationResult;
/**
 * ML-KEM decapsulation - recover shared secret from ciphertext
 *
 * @param ciphertext - Encapsulated ciphertext
 * @param secretKey - Recipient's secret key
 * @param level - Security level
 * @returns Shared secret
 */
export declare function mlkemDecapsulate(ciphertext: Uint8Array, secretKey: Uint8Array, level?: MLKEMLevel): Uint8Array;
/**
 * Generate ML-DSA key pair
 *
 * @param level - Security level (44, 65, or 87)
 * @returns Key pair with public and secret keys
 */
export declare function mldsaKeyGen(level?: MLDSALevel): MLDSAKeyPair;
/**
 * ML-DSA sign message
 *
 * @param message - Message to sign
 * @param secretKey - Signer's secret key
 * @param level - Security level
 * @returns Digital signature
 */
export declare function mldsaSign(message: Uint8Array, secretKey: Uint8Array, level?: MLDSALevel): Uint8Array;
/**
 * ML-DSA verify signature
 *
 * @param message - Original message
 * @param signature - Signature to verify
 * @param publicKey - Signer's public key
 * @param level - Security level
 * @returns True if signature is valid
 */
export declare function mldsaVerify(message: Uint8Array, signature: Uint8Array, publicKey: Uint8Array, level?: MLDSALevel): boolean;
/**
 * PQC Provider for SCBE Pipeline
 *
 * Provides quantum-resistant cryptographic operations integrated
 * with the SCBE 14-layer security framework.
 */
export declare class PQCProvider {
    private kemLevel;
    private dsaLevel;
    private hybridMode;
    constructor(config?: PQCConfig);
    /**
     * Generate ML-KEM key pair
     */
    generateKEMKeyPair(): MLKEMKeyPair;
    /**
     * Generate ML-DSA key pair
     */
    generateDSAKeyPair(): MLDSAKeyPair;
    /**
     * Encapsulate a shared secret
     */
    encapsulate(publicKey: Uint8Array): EncapsulationResult;
    /**
     * Decapsulate to recover shared secret
     */
    decapsulate(ciphertext: Uint8Array, secretKey: Uint8Array): Uint8Array;
    /**
     * Sign a message
     */
    sign(message: Uint8Array, secretKey: Uint8Array): Uint8Array;
    /**
     * Verify a signature
     */
    verify(message: Uint8Array, signature: Uint8Array, publicKey: Uint8Array): boolean;
    /**
     * Get security level information
     */
    getSecurityInfo(): {
        kemLevel: MLKEMLevel;
        dsaLevel: MLDSALevel;
        classicalBits: number;
        quantumBits: number;
    };
}
/**
 * Default PQC provider instance
 */
export declare const defaultPQCProvider: PQCProvider;
//# sourceMappingURL=pqc.d.ts.map