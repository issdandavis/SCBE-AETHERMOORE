/**
 * Quantum Lattice Integration for SS1 Tokenizer
 *
 * Implements a dual-lattice security model that combines:
 * 1. SS1 phonetic tokenization (semantic security)
 * 2. Post-quantum lattice cryptography (computational security)
 *
 * The dual-lattice approach provides defense-in-depth:
 * - SS1 tokens prevent semantic confusion attacks
 * - Lattice operations resist quantum computers
 * - Combined: even with quantum advantage, semantic attacks fail
 *
 * @module tokenizer/quantum-lattice
 * @version 1.0.0
 */
import { TongueCode, SS1Envelope } from './ss1';
/** Lattice parameters for different security levels */
export interface LatticeParams {
    n: number;
    q: number;
    sigma: number;
    securityBits: number;
}
/** Dual-lattice encoded data */
export interface DualLatticeEnvelope {
    version: 'DL-SS1-v1';
    ss1: SS1Envelope;
    lattice: {
        publicKey: string;
        ciphertext: string;
        params: 'ML-KEM-512' | 'ML-KEM-768' | 'ML-KEM-1024';
    };
    binding: {
        tongueHash: string;
        latticeHash: string;
        bindingProof: string;
    };
}
/** Tongue-Lattice binding for cross-layer security */
export interface TongueLatticeBinding {
    tongue: TongueCode;
    latticeDimension: number;
    noiseMultiplier: number;
    phaseIntegration: number;
}
/** NIST ML-KEM parameters */
export declare const LATTICE_PARAMS: Record<string, LatticeParams>;
/** Tongue-specific lattice bindings */
export declare const TONGUE_LATTICE_BINDINGS: Record<TongueCode, TongueLatticeBinding>;
/**
 * Generate a lattice keypair (simulated)
 *
 * In production, use liboqs ML-KEM implementation
 */
export declare function generateLatticeKeypair(params: string): {
    publicKey: Buffer;
    secretKey: Buffer;
};
/**
 * Lattice encapsulation (simulated KEM)
 *
 * Returns shared secret and ciphertext
 */
export declare function latticeEncapsulate(publicKey: Buffer, params: string): {
    sharedSecret: Buffer;
    ciphertext: Buffer;
};
/**
 * Lattice decapsulation (simulated)
 */
export declare function latticeDecapsulate(secretKey: Buffer, ciphertext: Buffer, params: string): Buffer;
/**
 * Create dual-lattice envelope
 *
 * Combines SS1 phonetic encoding with lattice-based key encapsulation
 */
export declare function createDualLatticeEnvelope(params: {
    kid: string;
    data: Buffer;
    tongue: TongueCode;
    recipientPublicKey: Buffer;
    latticeParams?: string;
    secretKey?: Buffer;
}): DualLatticeEnvelope;
/**
 * Verify dual-lattice envelope binding
 *
 * Ensures the SS1 layer and lattice layer haven't been tampered with independently
 */
export declare function verifyDualLatticeBinding(envelope: DualLatticeEnvelope, secretKey?: Buffer): boolean;
/**
 * Decrypt dual-lattice envelope
 */
export declare function decryptDualLatticeEnvelope(envelope: DualLatticeEnvelope, recipientSecretKey: Buffer): Buffer;
/**
 * Sign a message with tongue-bound quantum-resistant signature
 *
 * The signature includes the tongue sequence, making it invalid if
 * the phonetic encoding is changed (defense against semantic attacks)
 */
export declare function signWithTongueBinding(message: Buffer, tongue: TongueCode, secretKey: Buffer): {
    signature: string;
    tongueBinding: string;
};
/**
 * Verify tongue-bound signature
 */
export declare function verifyTongueBinding(message: Buffer, tongue: TongueCode, signature: string, tongueBinding: string, publicKey: Buffer): boolean;
export declare const QuantumLattice: {
    LATTICE_PARAMS: Record<string, LatticeParams>;
    TONGUE_LATTICE_BINDINGS: Record<TongueCode, TongueLatticeBinding>;
    generateKeypair: typeof generateLatticeKeypair;
    encapsulate: typeof latticeEncapsulate;
    decapsulate: typeof latticeDecapsulate;
    createEnvelope: typeof createDualLatticeEnvelope;
    verifyBinding: typeof verifyDualLatticeBinding;
    decryptEnvelope: typeof decryptDualLatticeEnvelope;
    sign: typeof signWithTongueBinding;
    verify: typeof verifyTongueBinding;
};
export default QuantumLattice;
//# sourceMappingURL=quantum-lattice.d.ts.map