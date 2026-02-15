/**
 * @file quantum-safe.ts
 * @module crypto/quantum-safe
 * @layer Layer 4
 * @component Algorithm-Agnostic Post-Quantum Cryptography
 * @version 1.0.0
 *
 * Pluggable PQC abstraction: the governance/geometry stack only needs
 * a shared secret + authenticated identity. Which KEM/signature family
 * provides those is a deployment decision, not an architectural one.
 *
 * Supported families:
 *   - Lattice (ML-KEM-768, ML-DSA-65)          — NIST FIPS 203/204
 *   - Hash-based (SLH-DSA-128s)                 — NIST FIPS 205 (SPHINCS+)
 *   - Code-based (Classic McEliece 348864)       — NIST Round 4
 *   - Isogeny-based (placeholder, some broken)
 *   - Multivariate (placeholder, niche)
 *
 * Design: "SCBE's PQC layer is algorithm-agnostic: today it uses
 * ML-KEM/ML-DSA; we can swap in code-based or hash-based schemes
 * without changing the geometric/governance stack."
 */
/** The five canonical PQC families per NIST taxonomy */
export type PQCFamily = 'lattice' | 'hash-based' | 'code-based' | 'isogeny' | 'multivariate';
/** NIST security levels 1-5 */
export type NISTLevel = 1 | 2 | 3 | 4 | 5;
/** Metadata describing a PQC algorithm (KEM or signature) */
export interface AlgorithmDescriptor {
    /** Algorithm name (e.g., 'ML-KEM-768', 'SLH-DSA-128s') */
    name: string;
    /** PQC family */
    family: PQCFamily;
    /** NIST security level */
    nistLevel: NISTLevel;
    /** NIST standard reference (e.g., 'FIPS 203') */
    standard: string;
    /** Public key size in bytes */
    publicKeySize: number;
    /** Secret/private key size in bytes */
    secretKeySize: number;
    /** Whether a production implementation is available */
    productionReady: boolean;
}
/** KEM-specific descriptor */
export interface KEMDescriptor extends AlgorithmDescriptor {
    kind: 'kem';
    /** Ciphertext size in bytes */
    ciphertextSize: number;
    /** Shared secret size in bytes */
    sharedSecretSize: number;
}
/** Signature-specific descriptor */
export interface SignatureDescriptor extends AlgorithmDescriptor {
    kind: 'signature';
    /** Signature size in bytes */
    signatureSize: number;
}
/** Generic key pair */
export interface QSKeyPair {
    publicKey: Uint8Array;
    secretKey: Uint8Array;
}
/** KEM encapsulation result */
export interface QSEncapsulation {
    ciphertext: Uint8Array;
    sharedSecret: Uint8Array;
}
/**
 * QuantumSafeKEM — algorithm-agnostic key encapsulation mechanism.
 *
 * Governance only needs: generateKeyPair → encapsulate → decapsulate.
 * Which lattice/code/hash scheme backs it is a deployment decision.
 */
export interface QuantumSafeKEM {
    readonly descriptor: KEMDescriptor;
    generateKeyPair(): Promise<QSKeyPair>;
    encapsulate(publicKey: Uint8Array): Promise<QSEncapsulation>;
    decapsulate(ciphertext: Uint8Array, secretKey: Uint8Array): Promise<Uint8Array>;
}
/**
 * QuantumSafeSignature — algorithm-agnostic digital signature.
 *
 * Governance only needs: generateKeyPair → sign → verify.
 */
export interface QuantumSafeSignature {
    readonly descriptor: SignatureDescriptor;
    generateKeyPair(): Promise<QSKeyPair>;
    sign(message: Uint8Array, secretKey: Uint8Array): Promise<Uint8Array>;
    verify(message: Uint8Array, signature: Uint8Array, publicKey: Uint8Array): Promise<boolean>;
}
/** All known PQC algorithm descriptors */
export declare const PQC_ALGORITHMS: {
    readonly 'ML-KEM-768': {
        readonly kind: "kem";
        readonly name: "ML-KEM-768";
        readonly family: PQCFamily;
        readonly nistLevel: NISTLevel;
        readonly standard: "FIPS 203";
        readonly publicKeySize: 1184;
        readonly secretKeySize: 2400;
        readonly ciphertextSize: 1088;
        readonly sharedSecretSize: 32;
        readonly productionReady: true;
    };
    readonly 'ML-KEM-512': {
        readonly kind: "kem";
        readonly name: "ML-KEM-512";
        readonly family: PQCFamily;
        readonly nistLevel: NISTLevel;
        readonly standard: "FIPS 203";
        readonly publicKeySize: 800;
        readonly secretKeySize: 1632;
        readonly ciphertextSize: 768;
        readonly sharedSecretSize: 32;
        readonly productionReady: true;
    };
    readonly 'ML-KEM-1024': {
        readonly kind: "kem";
        readonly name: "ML-KEM-1024";
        readonly family: PQCFamily;
        readonly nistLevel: NISTLevel;
        readonly standard: "FIPS 203";
        readonly publicKeySize: 1568;
        readonly secretKeySize: 3168;
        readonly ciphertextSize: 1568;
        readonly sharedSecretSize: 32;
        readonly productionReady: true;
    };
    readonly 'Classic-McEliece-348864': {
        readonly kind: "kem";
        readonly name: "Classic-McEliece-348864";
        readonly family: PQCFamily;
        readonly nistLevel: NISTLevel;
        readonly standard: "NIST Round 4";
        readonly publicKeySize: 261120;
        readonly secretKeySize: 6492;
        readonly ciphertextSize: 128;
        readonly sharedSecretSize: 32;
        readonly productionReady: false;
    };
    readonly 'ML-DSA-65': {
        readonly kind: "signature";
        readonly name: "ML-DSA-65";
        readonly family: PQCFamily;
        readonly nistLevel: NISTLevel;
        readonly standard: "FIPS 204";
        readonly publicKeySize: 1952;
        readonly secretKeySize: 4032;
        readonly signatureSize: 3293;
        readonly productionReady: true;
    };
    readonly 'ML-DSA-44': {
        readonly kind: "signature";
        readonly name: "ML-DSA-44";
        readonly family: PQCFamily;
        readonly nistLevel: NISTLevel;
        readonly standard: "FIPS 204";
        readonly publicKeySize: 1312;
        readonly secretKeySize: 2560;
        readonly signatureSize: 2420;
        readonly productionReady: true;
    };
    readonly 'FN-DSA-512': {
        readonly kind: "signature";
        readonly name: "FN-DSA-512";
        readonly family: PQCFamily;
        readonly nistLevel: NISTLevel;
        readonly standard: "FIPS 206 (draft)";
        readonly publicKeySize: 897;
        readonly secretKeySize: 1281;
        readonly signatureSize: 666;
        readonly productionReady: false;
    };
    readonly 'SLH-DSA-128s': {
        readonly kind: "signature";
        readonly name: "SLH-DSA-128s";
        readonly family: PQCFamily;
        readonly nistLevel: NISTLevel;
        readonly standard: "FIPS 205";
        readonly publicKeySize: 32;
        readonly secretKeySize: 64;
        readonly signatureSize: 7856;
        readonly productionReady: true;
    };
    readonly 'SLH-DSA-256s': {
        readonly kind: "signature";
        readonly name: "SLH-DSA-256s";
        readonly family: PQCFamily;
        readonly nistLevel: NISTLevel;
        readonly standard: "FIPS 205";
        readonly publicKeySize: 64;
        readonly secretKeySize: 128;
        readonly signatureSize: 29792;
        readonly productionReady: true;
    };
};
export type PQCAlgorithmName = keyof typeof PQC_ALGORITHMS;
/**
 * Generic stub KEM — generates deterministic test keys/ciphertext.
 * Works for any descriptor; swap for native liboqs in production.
 */
export declare class StubKEM implements QuantumSafeKEM {
    readonly descriptor: KEMDescriptor;
    constructor(desc: KEMDescriptor);
    generateKeyPair(): Promise<QSKeyPair>;
    encapsulate(publicKey: Uint8Array): Promise<QSEncapsulation>;
    decapsulate(ciphertext: Uint8Array, secretKey: Uint8Array): Promise<Uint8Array>;
}
/**
 * Generic stub Signature — deterministic test signatures.
 */
export declare class StubSignature implements QuantumSafeSignature {
    readonly descriptor: SignatureDescriptor;
    constructor(desc: SignatureDescriptor);
    generateKeyPair(): Promise<QSKeyPair>;
    sign(message: Uint8Array, secretKey: Uint8Array): Promise<Uint8Array>;
    verify(message: Uint8Array, signature: Uint8Array, publicKey: Uint8Array): Promise<boolean>;
}
/**
 * Register a custom KEM implementation (e.g., native liboqs wrapper).
 * Replaces any existing registration for the same name.
 */
export declare function registerKEM(kem: QuantumSafeKEM): void;
/**
 * Register a custom signature implementation.
 */
export declare function registerSignature(sig: QuantumSafeSignature): void;
/**
 * Get a KEM by algorithm name. Returns stub if no native registered.
 */
export declare function getKEM(name: string): QuantumSafeKEM;
/**
 * Get a signature scheme by algorithm name. Returns stub if no native registered.
 */
export declare function getSignature(name: string): QuantumSafeSignature;
/**
 * List all registered algorithms with their status.
 */
export declare function listAlgorithms(): Array<{
    name: string;
    kind: 'kem' | 'signature';
    family: PQCFamily;
    nistLevel: NISTLevel;
    registered: boolean;
    productionReady: boolean;
}>;
/** Clear all registered implementations (for testing) */
export declare function clearRegistry(): void;
/** Configuration for a QuantumSafeEnvelope */
export interface QSEnvelopeConfig {
    /** KEM algorithm name (e.g., 'ML-KEM-768', 'Classic-McEliece-348864') */
    kemAlgorithm: string;
    /** Signature algorithm name (e.g., 'ML-DSA-65', 'SLH-DSA-128s') */
    sigAlgorithm: string;
    /** Enable hybrid mode: combine PQC with classical ECDH/ECDSA (belt + suspenders) */
    hybridMode?: boolean;
    /** Semantic tags for governance binding */
    tags?: Record<string, string>;
}
export declare const DEFAULT_QS_ENVELOPE_CONFIG: QSEnvelopeConfig;
/** Result of envelope establishment (key agreement + identity proof) */
export interface QSEstablishment {
    /** Shared secret (32 bytes), possibly XOR'd with classical component */
    sharedSecret: Uint8Array;
    /** KEM ciphertext for recipient */
    kemCiphertext: Uint8Array;
    /** Signature over binding data */
    signature: Uint8Array;
    /** Binding hash: SHA-256(kemAlg ‖ sigAlg ‖ sharedSecret ‖ tags) */
    bindingHash: string;
    /** Algorithm metadata */
    algorithms: {
        kem: {
            name: string;
            family: PQCFamily;
            nistLevel: NISTLevel;
        };
        sig: {
            name: string;
            family: PQCFamily;
            nistLevel: NISTLevel;
        };
    };
    /** Whether classical hybrid was applied */
    hybrid: boolean;
}
/**
 * QuantumSafeEnvelope — the governance-facing abstraction.
 *
 * The geometric/consensus stack calls establish() and verify().
 * Which KEM/signature family backs it is fully pluggable.
 *
 * Usage:
 *   const env = new QuantumSafeEnvelope({ kemAlgorithm: 'ML-KEM-768', sigAlgorithm: 'SLH-DSA-128s' });
 *   await env.initialize();
 *   const est = await env.establish();  // → sharedSecret + signature + binding
 */
export declare class QuantumSafeEnvelope {
    private readonly config;
    private kem;
    private sig;
    private kemKeyPair;
    private sigKeyPair;
    private classicalSecret;
    constructor(config?: Partial<QSEnvelopeConfig>);
    /** Generate key pairs. Must be called before establish/verify. */
    initialize(): Promise<void>;
    /** Check if initialized */
    get isInitialized(): boolean;
    /** Get algorithm descriptors */
    get algorithms(): {
        kem: KEMDescriptor;
        sig: SignatureDescriptor;
    };
    /**
     * Establish: encapsulate + sign. Returns everything the governance
     * layer needs: shared secret, identity proof, and binding hash.
     */
    establish(): Promise<QSEstablishment>;
    /**
     * Verify: check a signature over binding data using the signer's public key.
     */
    verify(bindingData: Uint8Array, signature: Uint8Array, signerPublicKey: Uint8Array): Promise<boolean>;
    /**
     * Decapsulate: recover shared secret from ciphertext.
     */
    decapsulate(ciphertext: Uint8Array): Promise<Uint8Array>;
    /**
     * Get the signer's public key (for verification by counterpart).
     */
    getSignerPublicKey(): Uint8Array;
    /**
     * Get the KEM public key (for encapsulation by counterpart).
     */
    getKEMPublicKey(): Uint8Array;
    /** Build canonical binding data: kemAlg ‖ sigAlg ‖ secret ‖ JSON(tags) */
    private buildBindingData;
}
/**
 * Performance/security trade-off table for architecture documentation.
 *
 * Family           | Key Size     | Sig/CT Size  | Speed      | Maturity
 * -----------------+--------------+--------------+------------+---------
 * Lattice          | Medium       | Medium       | Fast       | NIST std
 * Hash-based       | Tiny (32B)   | Large (8-30K)| Slow sign  | NIST std
 * Code-based       | Huge (255K+) | Tiny (128B)  | Fast       | Round 4
 * Isogeny          | Tiny         | Tiny         | Very slow  | Broken?
 * Multivariate     | Large        | Tiny         | Fast verify| Niche
 */
export declare const PQC_FAMILY_TRADEOFFS: Record<PQCFamily, {
    keySize: string;
    outputSize: string;
    speed: string;
    maturity: string;
    scbeRecommendation: string;
}>;
//# sourceMappingURL=quantum-safe.d.ts.map