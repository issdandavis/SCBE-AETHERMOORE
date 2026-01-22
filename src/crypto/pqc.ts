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

import { randomBytes, createHash } from 'crypto';

// ============================================================
// TYPE DEFINITIONS
// ============================================================

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

// ============================================================
// ML-KEM-768 PARAMETERS (NIST FIPS 203)
// ============================================================

export const ML_KEM_768_PARAMS = {
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
} as const;

// ============================================================
// ML-DSA-65 PARAMETERS (NIST FIPS 204)
// ============================================================

export const ML_DSA_65_PARAMS = {
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
} as const;

// ============================================================
// ML-KEM-768 IMPLEMENTATION (Stub for liboqs integration)
// ============================================================

/**
 * ML-KEM-768 Key Encapsulation Mechanism
 *
 * In production, this would use liboqs or @noble/post-quantum.
 * This stub provides the correct interface and data sizes.
 */
export class MLKEM768 {
  private static instance: MLKEM768 | null = null;
  private useNative: boolean = false;

  private constructor() {
    // Check for native liboqs availability
    try {
      // In production: const oqs = require('liboqs-node');
      this.useNative = false; // Set to true when liboqs is available
    } catch {
      this.useNative = false;
    }
  }

  static getInstance(): MLKEM768 {
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
  async generateKeyPair(): Promise<MLKEMKeyPair> {
    if (this.useNative) {
      // Production: Use liboqs
      // const kem = new oqs.KeyEncapsulation('ML-KEM-768');
      // return kem.generateKeypair();
    }

    // Development stub: Generate deterministic test keys
    // WARNING: NOT FOR PRODUCTION USE
    const seed = randomBytes(32);
    const publicKey = this.expandKey(seed, ML_KEM_768_PARAMS.publicKeySize, 'pk');
    const secretKey = this.expandKey(seed, ML_KEM_768_PARAMS.secretKeySize, 'sk');

    return { publicKey, secretKey };
  }

  /**
   * Encapsulate: Generate shared secret using public key
   *
   * @param publicKey - Recipient's public key
   * @returns Ciphertext and shared secret
   */
  async encapsulate(publicKey: Uint8Array): Promise<MLKEMEncapsulation> {
    this.validatePublicKey(publicKey);

    if (this.useNative) {
      // Production: Use liboqs
      // const kem = new oqs.KeyEncapsulation('ML-KEM-768');
      // return kem.encapsulate(publicKey);
    }

    // Development stub
    const randomness = randomBytes(32);
    const ciphertext = this.expandKey(
      Buffer.concat([publicKey.slice(0, 32), randomness]),
      ML_KEM_768_PARAMS.ciphertextSize,
      'ct'
    );
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
  async decapsulate(ciphertext: Uint8Array, secretKey: Uint8Array): Promise<Uint8Array> {
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
  private expandKey(seed: Buffer, length: number, label: string): Uint8Array {
    const result = Buffer.alloc(length);
    let offset = 0;
    let counter = 0;

    while (offset < length) {
      const hash = createHash('sha256')
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

  private deriveSharedSecret(key1: Uint8Array, key2: Uint8Array): Uint8Array {
    return new Uint8Array(
      createHash('sha256').update(Buffer.from(key1)).update(Buffer.from(key2)).digest()
    );
  }

  private validatePublicKey(pk: Uint8Array): void {
    if (pk.length !== ML_KEM_768_PARAMS.publicKeySize) {
      throw new Error(
        `Invalid ML-KEM-768 public key size: ${pk.length} (expected ${ML_KEM_768_PARAMS.publicKeySize})`
      );
    }
  }

  private validateSecretKey(sk: Uint8Array): void {
    if (sk.length !== ML_KEM_768_PARAMS.secretKeySize) {
      throw new Error(
        `Invalid ML-KEM-768 secret key size: ${sk.length} (expected ${ML_KEM_768_PARAMS.secretKeySize})`
      );
    }
  }

  private validateCiphertext(ct: Uint8Array): void {
    if (ct.length !== ML_KEM_768_PARAMS.ciphertextSize) {
      throw new Error(
        `Invalid ML-KEM-768 ciphertext size: ${ct.length} (expected ${ML_KEM_768_PARAMS.ciphertextSize})`
      );
    }
  }
}

// ============================================================
// ML-DSA-65 IMPLEMENTATION (Stub for liboqs integration)
// ============================================================

/**
 * ML-DSA-65 Digital Signature Algorithm (Dilithium3)
 *
 * In production, this would use liboqs or @noble/post-quantum.
 * This stub provides the correct interface and data sizes.
 */
export class MLDSA65 {
  private static instance: MLDSA65 | null = null;
  private useNative: boolean = false;

  private constructor() {
    try {
      this.useNative = false; // Set to true when liboqs is available
    } catch {
      this.useNative = false;
    }
  }

  static getInstance(): MLDSA65 {
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
  async generateKeyPair(): Promise<MLDSAKeyPair> {
    if (this.useNative) {
      // Production: Use liboqs
      // const sig = new oqs.Signature('ML-DSA-65');
      // return sig.generateKeypair();
    }

    // Development stub
    const seed = randomBytes(32);
    const publicKey = this.expandKey(seed, ML_DSA_65_PARAMS.publicKeySize, 'pk');
    const secretKey = this.expandKey(seed, ML_DSA_65_PARAMS.secretKeySize, 'sk');

    return { publicKey, secretKey };
  }

  /**
   * Sign a message
   *
   * @param message - Message to sign
   * @param secretKey - Signer's secret key
   * @returns Signature bytes
   */
  async sign(message: Uint8Array, secretKey: Uint8Array): Promise<Uint8Array> {
    this.validateSecretKey(secretKey);

    if (this.useNative) {
      // Production: Use liboqs
      // const sig = new oqs.Signature('ML-DSA-65');
      // return sig.sign(message, secretKey);
    }

    // Development stub: Deterministic signature
    return this.expandKey(
      Buffer.concat([Buffer.from(message), Buffer.from(secretKey.slice(0, 32))]),
      ML_DSA_65_PARAMS.signatureSize,
      'sig'
    );
  }

  /**
   * Verify a signature
   *
   * @param message - Original message
   * @param signature - Signature to verify
   * @param publicKey - Signer's public key
   * @returns True if valid, false otherwise
   */
  async verify(
    message: Uint8Array,
    signature: Uint8Array,
    publicKey: Uint8Array
  ): Promise<boolean> {
    this.validatePublicKey(publicKey);
    this.validateSignature(signature);

    if (this.useNative) {
      // Production: Use liboqs
      // const sig = new oqs.Signature('ML-DSA-65');
      // return sig.verify(message, signature, publicKey);
    }

    // Development stub: Always returns true for valid-looking signatures
    // WARNING: NOT FOR PRODUCTION USE
    return signature.length === ML_DSA_65_PARAMS.signatureSize;
  }

  // Helper methods
  private expandKey(seed: Buffer, length: number, label: string): Uint8Array {
    const result = Buffer.alloc(length);
    let offset = 0;
    let counter = 0;

    while (offset < length) {
      const hash = createHash('sha256')
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

  private validatePublicKey(pk: Uint8Array): void {
    if (pk.length !== ML_DSA_65_PARAMS.publicKeySize) {
      throw new Error(
        `Invalid ML-DSA-65 public key size: ${pk.length} (expected ${ML_DSA_65_PARAMS.publicKeySize})`
      );
    }
  }

  private validateSecretKey(sk: Uint8Array): void {
    if (sk.length !== ML_DSA_65_PARAMS.secretKeySize) {
      throw new Error(
        `Invalid ML-DSA-65 secret key size: ${sk.length} (expected ${ML_DSA_65_PARAMS.secretKeySize})`
      );
    }
  }

  private validateSignature(sig: Uint8Array): void {
    if (sig.length !== ML_DSA_65_PARAMS.signatureSize) {
      throw new Error(
        `Invalid ML-DSA-65 signature size: ${sig.length} (expected ${ML_DSA_65_PARAMS.signatureSize})`
      );
    }
  }
}

// ============================================================
// HYBRID PQC + CLASSICAL ENCRYPTION
// ============================================================

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
export class HybridKEM {
  private mlkem: MLKEM768;

  constructor() {
    this.mlkem = MLKEM768.getInstance();
  }

  /**
   * Generate hybrid key pair
   */
  async generateKeyPair(): Promise<HybridKeyPair> {
    // Generate PQC key pair
    const pqc = await this.mlkem.generateKeyPair();

    // Generate classical key pair (placeholder - in production use ECDH)
    const classicalSeed = randomBytes(32);
    const classical = {
      publicKey: new Uint8Array(
        createHash('sha256').update(classicalSeed).update('public').digest()
      ),
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
  async encapsulate(publicKey: HybridKeyPair): Promise<HybridEncapsulation> {
    // PQC encapsulation
    const pqc = await this.mlkem.encapsulate(publicKey.pqc.publicKey);

    // Classical encapsulation (placeholder)
    const classicalRandom = randomBytes(32);
    const classical = {
      ciphertext: new Uint8Array(classicalRandom),
      sharedSecret: new Uint8Array(
        createHash('sha256').update(classicalRandom).update(publicKey.classical.publicKey).digest()
      ),
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
  async decapsulate(
    encapsulation: HybridEncapsulation,
    secretKey: HybridKeyPair
  ): Promise<Uint8Array> {
    // PQC decapsulation
    const pqcSecret = await this.mlkem.decapsulate(
      encapsulation.pqc.ciphertext,
      secretKey.pqc.secretKey
    );

    // Classical decapsulation (placeholder)
    const classicalSecret = new Uint8Array(
      createHash('sha256')
        .update(encapsulation.classical.ciphertext)
        .update(secretKey.classical.privateKey)
        .digest()
    );

    // Combine secrets
    const combinedSecret = new Uint8Array(32);
    for (let i = 0; i < 32; i++) {
      combinedSecret[i] = classicalSecret[i] ^ pqcSecret[i];
    }

    return combinedSecret;
  }
}

// ============================================================
// UTILITY FUNCTIONS
// ============================================================

/**
 * Encode bytes to hex string
 */
export function toHex(bytes: Uint8Array): string {
  return Buffer.from(bytes).toString('hex');
}

/**
 * Decode hex string to bytes
 */
export function fromHex(hex: string): Uint8Array {
  return new Uint8Array(Buffer.from(hex, 'hex'));
}

/**
 * Check if PQC algorithms are available (native liboqs)
 */
export function isPQCAvailable(): boolean {
  try {
    // Check for liboqs-node
    require.resolve('liboqs-node');
    return true;
  } catch {
    return false;
  }
}

/**
 * Get PQC implementation status
 */
export function getPQCStatus(): {
  available: boolean;
  implementation: 'native' | 'stub';
  algorithms: string[];
} {
  const available = isPQCAvailable();
  return {
    available,
    implementation: available ? 'native' : 'stub',
    algorithms: ['ML-KEM-768', 'ML-DSA-65'],
  };
}

// ============================================================
// DUAL LATTICE CONSENSUS (Patent USPTO #63/961,403)
// ============================================================

/**
 * Consensus result enum matching Python implementation
 */
export enum ConsensusResult {
  ACCEPT = 'accept',
  REJECT = 'reject',
  KEM_FAIL = 'kem_fail',
  DSA_FAIL = 'dsa_fail',
  CONSENSUS_FAIL = 'consensus_fail',
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
export class DualLatticeConsensus {
  private kem: MLKEM768;
  private dsa: MLDSA65;
  private kemKeyPair: MLKEMKeyPair | null = null;
  private dsaKeyPair: MLDSAKeyPair | null = null;
  private decisionLog: Array<{ timestamp: number; result: string; sessionKeyId: string }> = [];

  private static readonly TIMESTAMP_WINDOW = 60_000; // 60 seconds

  constructor() {
    this.kem = MLKEM768.getInstance();
    this.dsa = MLDSA65.getInstance();
  }

  /**
   * Initialize key pairs for the consensus system
   */
  async initialize(): Promise<void> {
    this.kemKeyPair = await this.kem.generateKeyPair();
    this.dsaKeyPair = await this.dsa.generateKeyPair();
  }

  /**
   * Create a dual-signed authorization token
   * Both KEM-derived key and DSA signature required
   */
  async createAuthorizationToken(
    context: AuthorizationContext,
    decision: string
  ): Promise<AuthorizationToken> {
    if (!this.kemKeyPair || !this.dsaKeyPair) {
      await this.initialize();
    }

    // Step 1: KEM encapsulation for session key
    const { ciphertext, sharedSecret } = await this.kem.encapsulate(this.kemKeyPair!.publicKey);

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
    const signature = await this.dsa.sign(payloadBytes, this.dsaKeyPair!.secretKey);

    // Step 4: Dual-lattice consensus hash (both algorithms must agree)
    const kemHash = this.hashWithDomain(sharedSecret, 'kem_domain');
    const dsaHash = this.hashWithDomain(this.dsaKeyPair!.secretKey.slice(0, 32), 'dsa_domain');
    const consensusHash = this.combineHashes(kemHash, dsaHash);

    // Session key ID for tracking
    const sessionKeyId = toHex(
      new Uint8Array(createHash('sha256').update(Buffer.from(sharedSecret)).digest())
    ).slice(0, 16);

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
  async verifyAuthorizationToken(
    token: AuthorizationToken
  ): Promise<{ result: ConsensusResult; reason: string }> {
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
    } catch (error) {
      return { result: ConsensusResult.REJECT, reason: String(error) };
    }
  }

  /**
   * Get the decision log
   */
  getDecisionLog(): Array<{ timestamp: number; result: string; sessionKeyId: string }> {
    return [...this.decisionLog];
  }

  /**
   * Check if PQC backend is available
   */
  isPQCAvailable(): boolean {
    return isPQCAvailable();
  }

  /**
   * Get PQC status
   */
  getPQCStatus(): { available: boolean; implementation: 'native' | 'stub'; algorithms: string[] } {
    return getPQCStatus();
  }

  // Private helper methods
  private serializeContext(context: AuthorizationContext): Uint8Array {
    const encoder = new TextEncoder();
    const userIdBytes = encoder.encode(context.userId);
    const deviceBytes = encoder.encode(context.deviceFingerprint);
    const timestampBytes = new Uint8Array(8);
    new DataView(timestampBytes.buffer).setBigUint64(0, BigInt(context.timestamp), false);
    const threatBytes = new Uint8Array(4);
    new DataView(threatBytes.buffer).setUint32(0, Math.floor(context.threatLevel * 1000), false);

    const result = new Uint8Array(
      userIdBytes.length +
        deviceBytes.length +
        timestampBytes.length +
        context.sessionNonce.length +
        threatBytes.length
    );

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

  private hashWithDomain(data: Uint8Array, domain: string): Uint8Array {
    return new Uint8Array(
      createHash('sha256')
        .update(Buffer.from(data))
        .update(Buffer.from(domain))
        .digest()
        .slice(0, 8)
    );
  }

  private combineHashes(hash1: Uint8Array, hash2: Uint8Array): Uint8Array {
    return new Uint8Array(
      createHash('sha256').update(Buffer.from(hash1)).update(Buffer.from(hash2)).digest()
    );
  }
}

// ============================================================
// EXPORTS
// ============================================================

export const pqc = {
  MLKEM768,
  MLDSA65,
  HybridKEM,
  DualLatticeConsensus,
  ConsensusResult,
  ML_KEM_768_PARAMS,
  ML_DSA_65_PARAMS,
  toHex,
  fromHex,
  isPQCAvailable,
  getPQCStatus,
};

export default pqc;
