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

import { createHash, randomBytes } from 'crypto';

// ============================================================
// PQC FAMILY TAXONOMY
// ============================================================

/** The five canonical PQC families per NIST taxonomy */
export type PQCFamily = 'lattice' | 'hash-based' | 'code-based' | 'isogeny' | 'multivariate';

/** NIST security levels 1-5 */
export type NISTLevel = 1 | 2 | 3 | 4 | 5;

// ============================================================
// ABSTRACT INTERFACES
// ============================================================

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

// ============================================================
// ALGORITHM CATALOG
// ============================================================

/** All known PQC algorithm descriptors */
export const PQC_ALGORITHMS = {
  // ── Lattice KEMs ──
  'ML-KEM-768': {
    kind: 'kem' as const,
    name: 'ML-KEM-768',
    family: 'lattice' as PQCFamily,
    nistLevel: 3 as NISTLevel,
    standard: 'FIPS 203',
    publicKeySize: 1184,
    secretKeySize: 2400,
    ciphertextSize: 1088,
    sharedSecretSize: 32,
    productionReady: true,
  },
  'ML-KEM-512': {
    kind: 'kem' as const,
    name: 'ML-KEM-512',
    family: 'lattice' as PQCFamily,
    nistLevel: 1 as NISTLevel,
    standard: 'FIPS 203',
    publicKeySize: 800,
    secretKeySize: 1632,
    ciphertextSize: 768,
    sharedSecretSize: 32,
    productionReady: true,
  },
  'ML-KEM-1024': {
    kind: 'kem' as const,
    name: 'ML-KEM-1024',
    family: 'lattice' as PQCFamily,
    nistLevel: 5 as NISTLevel,
    standard: 'FIPS 203',
    publicKeySize: 1568,
    secretKeySize: 3168,
    ciphertextSize: 1568,
    sharedSecretSize: 32,
    productionReady: true,
  },

  // ── Code-based KEMs ──
  'Classic-McEliece-348864': {
    kind: 'kem' as const,
    name: 'Classic-McEliece-348864',
    family: 'code-based' as PQCFamily,
    nistLevel: 1 as NISTLevel,
    standard: 'NIST Round 4',
    publicKeySize: 261_120,    // ~255 KB — very large
    secretKeySize: 6_492,
    ciphertextSize: 128,       // very compact
    sharedSecretSize: 32,
    productionReady: false,
  },

  // ── Lattice Signatures ──
  'ML-DSA-65': {
    kind: 'signature' as const,
    name: 'ML-DSA-65',
    family: 'lattice' as PQCFamily,
    nistLevel: 3 as NISTLevel,
    standard: 'FIPS 204',
    publicKeySize: 1952,
    secretKeySize: 4032,
    signatureSize: 3293,
    productionReady: true,
  },
  'ML-DSA-44': {
    kind: 'signature' as const,
    name: 'ML-DSA-44',
    family: 'lattice' as PQCFamily,
    nistLevel: 2 as NISTLevel,
    standard: 'FIPS 204',
    publicKeySize: 1312,
    secretKeySize: 2560,
    signatureSize: 2420,
    productionReady: true,
  },
  'FN-DSA-512': {
    kind: 'signature' as const,
    name: 'FN-DSA-512',
    family: 'lattice' as PQCFamily,
    nistLevel: 1 as NISTLevel,
    standard: 'FIPS 206 (draft)',
    publicKeySize: 897,
    secretKeySize: 1281,
    signatureSize: 666,
    productionReady: false,
  },

  // ── Hash-based Signatures ──
  'SLH-DSA-128s': {
    kind: 'signature' as const,
    name: 'SLH-DSA-128s',
    family: 'hash-based' as PQCFamily,
    nistLevel: 1 as NISTLevel,
    standard: 'FIPS 205',
    publicKeySize: 32,          // very compact
    secretKeySize: 64,
    signatureSize: 7_856,       // large signatures
    productionReady: true,
  },
  'SLH-DSA-256s': {
    kind: 'signature' as const,
    name: 'SLH-DSA-256s',
    family: 'hash-based' as PQCFamily,
    nistLevel: 5 as NISTLevel,
    standard: 'FIPS 205',
    publicKeySize: 64,
    secretKeySize: 128,
    signatureSize: 29_792,
    productionReady: true,
  },
} as const;

export type PQCAlgorithmName = keyof typeof PQC_ALGORITHMS;

// ============================================================
// STUB KEM IMPLEMENTATION (dev/test, expandable)
// ============================================================

/** Helper: expand seed to fixed-length deterministic bytes */
function expandSeed(seed: Buffer, length: number, label: string): Uint8Array {
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

/** Helper: derive shared secret from two byte arrays */
function deriveSecret(a: Uint8Array, b: Uint8Array): Uint8Array {
  return new Uint8Array(
    createHash('sha256').update(Buffer.from(a)).update(Buffer.from(b)).digest()
  );
}

/**
 * Generic stub KEM — generates deterministic test keys/ciphertext.
 * Works for any descriptor; swap for native liboqs in production.
 */
export class StubKEM implements QuantumSafeKEM {
  readonly descriptor: KEMDescriptor;

  constructor(desc: KEMDescriptor) {
    this.descriptor = desc;
  }

  async generateKeyPair(): Promise<QSKeyPair> {
    const seed = randomBytes(32);
    return {
      publicKey: expandSeed(seed, this.descriptor.publicKeySize, `${this.descriptor.name}:pk`),
      secretKey: expandSeed(seed, this.descriptor.secretKeySize, `${this.descriptor.name}:sk`),
    };
  }

  async encapsulate(publicKey: Uint8Array): Promise<QSEncapsulation> {
    if (publicKey.length !== this.descriptor.publicKeySize) {
      throw new Error(
        `${this.descriptor.name}: invalid public key size ${publicKey.length} ` +
        `(expected ${this.descriptor.publicKeySize})`
      );
    }
    const rand = randomBytes(32);
    const ciphertext = expandSeed(
      Buffer.concat([publicKey.subarray(0, 32), rand]),
      this.descriptor.ciphertextSize,
      `${this.descriptor.name}:ct`
    );
    const sharedSecret = deriveSecret(publicKey.subarray(0, 32), rand);
    return { ciphertext, sharedSecret };
  }

  async decapsulate(ciphertext: Uint8Array, secretKey: Uint8Array): Promise<Uint8Array> {
    if (ciphertext.length !== this.descriptor.ciphertextSize) {
      throw new Error(
        `${this.descriptor.name}: invalid ciphertext size ${ciphertext.length} ` +
        `(expected ${this.descriptor.ciphertextSize})`
      );
    }
    if (secretKey.length !== this.descriptor.secretKeySize) {
      throw new Error(
        `${this.descriptor.name}: invalid secret key size ${secretKey.length} ` +
        `(expected ${this.descriptor.secretKeySize})`
      );
    }
    return deriveSecret(secretKey.subarray(0, 32), ciphertext.subarray(0, 32));
  }
}

/**
 * Generic stub Signature — deterministic test signatures.
 */
export class StubSignature implements QuantumSafeSignature {
  readonly descriptor: SignatureDescriptor;

  constructor(desc: SignatureDescriptor) {
    this.descriptor = desc;
  }

  async generateKeyPair(): Promise<QSKeyPair> {
    const seed = randomBytes(32);
    return {
      publicKey: expandSeed(seed, this.descriptor.publicKeySize, `${this.descriptor.name}:pk`),
      secretKey: expandSeed(seed, this.descriptor.secretKeySize, `${this.descriptor.name}:sk`),
    };
  }

  async sign(message: Uint8Array, secretKey: Uint8Array): Promise<Uint8Array> {
    if (secretKey.length !== this.descriptor.secretKeySize) {
      throw new Error(
        `${this.descriptor.name}: invalid secret key size ${secretKey.length} ` +
        `(expected ${this.descriptor.secretKeySize})`
      );
    }
    return expandSeed(
      Buffer.concat([Buffer.from(message), Buffer.from(secretKey.subarray(0, 32))]),
      this.descriptor.signatureSize,
      `${this.descriptor.name}:sig`
    );
  }

  async verify(
    message: Uint8Array,
    signature: Uint8Array,
    publicKey: Uint8Array
  ): Promise<boolean> {
    if (publicKey.length !== this.descriptor.publicKeySize) {
      throw new Error(
        `${this.descriptor.name}: invalid public key size ${publicKey.length} ` +
        `(expected ${this.descriptor.publicKeySize})`
      );
    }
    if (signature.length !== this.descriptor.signatureSize) {
      throw new Error(
        `${this.descriptor.name}: invalid signature size ${signature.length} ` +
        `(expected ${this.descriptor.signatureSize})`
      );
    }
    // Stub: size-only check. NOT secure — production uses liboqs.
    return signature.length === this.descriptor.signatureSize;
  }
}

// ============================================================
// ALGORITHM REGISTRY
// ============================================================

/** Registry of instantiated KEM/Signature providers, keyed by algorithm name */
const kemRegistry = new Map<string, QuantumSafeKEM>();
const sigRegistry = new Map<string, QuantumSafeSignature>();

/**
 * Register a custom KEM implementation (e.g., native liboqs wrapper).
 * Replaces any existing registration for the same name.
 */
export function registerKEM(kem: QuantumSafeKEM): void {
  kemRegistry.set(kem.descriptor.name, kem);
}

/**
 * Register a custom signature implementation.
 */
export function registerSignature(sig: QuantumSafeSignature): void {
  sigRegistry.set(sig.descriptor.name, sig);
}

/**
 * Get a KEM by algorithm name. Returns stub if no native registered.
 */
export function getKEM(name: string): QuantumSafeKEM {
  const existing = kemRegistry.get(name);
  if (existing) return existing;

  // Look up in catalog and create stub
  const desc = Object.values(PQC_ALGORITHMS).find(
    (a) => a.kind === 'kem' && a.name === name
  ) as KEMDescriptor | undefined;
  if (!desc) {
    throw new Error(`Unknown KEM algorithm: ${name}`);
  }

  const stub = new StubKEM(desc);
  kemRegistry.set(name, stub);
  return stub;
}

/**
 * Get a signature scheme by algorithm name. Returns stub if no native registered.
 */
export function getSignature(name: string): QuantumSafeSignature {
  const existing = sigRegistry.get(name);
  if (existing) return existing;

  const desc = Object.values(PQC_ALGORITHMS).find(
    (a) => a.kind === 'signature' && a.name === name
  ) as SignatureDescriptor | undefined;
  if (!desc) {
    throw new Error(`Unknown signature algorithm: ${name}`);
  }

  const stub = new StubSignature(desc);
  sigRegistry.set(name, stub);
  return stub;
}

/**
 * List all registered algorithms with their status.
 */
export function listAlgorithms(): Array<{
  name: string;
  kind: 'kem' | 'signature';
  family: PQCFamily;
  nistLevel: NISTLevel;
  registered: boolean;
  productionReady: boolean;
}> {
  return Object.values(PQC_ALGORITHMS).map((desc) => ({
    name: desc.name,
    kind: desc.kind,
    family: desc.family,
    nistLevel: desc.nistLevel,
    registered: desc.kind === 'kem'
      ? kemRegistry.has(desc.name)
      : sigRegistry.has(desc.name),
    productionReady: desc.productionReady,
  }));
}

/** Clear all registered implementations (for testing) */
export function clearRegistry(): void {
  kemRegistry.clear();
  sigRegistry.clear();
}

// ============================================================
// HYBRID QUANTUM-SAFE ENVELOPE
// ============================================================

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

export const DEFAULT_QS_ENVELOPE_CONFIG: QSEnvelopeConfig = {
  kemAlgorithm: 'ML-KEM-768',
  sigAlgorithm: 'ML-DSA-65',
  hybridMode: true,
};

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
    kem: { name: string; family: PQCFamily; nistLevel: NISTLevel };
    sig: { name: string; family: PQCFamily; nistLevel: NISTLevel };
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
export class QuantumSafeEnvelope {
  private readonly config: QSEnvelopeConfig;
  private kem: QuantumSafeKEM;
  private sig: QuantumSafeSignature;
  private kemKeyPair: QSKeyPair | null = null;
  private sigKeyPair: QSKeyPair | null = null;
  private classicalSecret: Uint8Array | null = null;

  constructor(config: Partial<QSEnvelopeConfig> = {}) {
    this.config = { ...DEFAULT_QS_ENVELOPE_CONFIG, ...config };
    this.kem = getKEM(this.config.kemAlgorithm);
    this.sig = getSignature(this.config.sigAlgorithm);
  }

  /** Generate key pairs. Must be called before establish/verify. */
  async initialize(): Promise<void> {
    this.kemKeyPair = await this.kem.generateKeyPair();
    this.sigKeyPair = await this.sig.generateKeyPair();

    if (this.config.hybridMode) {
      // Classical component: random 32 bytes (in prod: ECDH ephemeral)
      this.classicalSecret = new Uint8Array(randomBytes(32));
    }
  }

  /** Check if initialized */
  get isInitialized(): boolean {
    return this.kemKeyPair !== null && this.sigKeyPair !== null;
  }

  /** Get algorithm descriptors */
  get algorithms(): { kem: KEMDescriptor; sig: SignatureDescriptor } {
    return {
      kem: this.kem.descriptor,
      sig: this.sig.descriptor,
    };
  }

  /**
   * Establish: encapsulate + sign. Returns everything the governance
   * layer needs: shared secret, identity proof, and binding hash.
   */
  async establish(): Promise<QSEstablishment> {
    if (!this.kemKeyPair || !this.sigKeyPair) {
      throw new Error('QuantumSafeEnvelope not initialized — call initialize() first');
    }

    // Step 1: KEM encapsulation
    const { ciphertext, sharedSecret } = await this.kem.encapsulate(this.kemKeyPair.publicKey);

    // Step 2: Hybrid mixing (if enabled)
    let finalSecret: Uint8Array;
    if (this.config.hybridMode && this.classicalSecret) {
      finalSecret = new Uint8Array(32);
      for (let i = 0; i < 32; i++) {
        finalSecret[i] = sharedSecret[i] ^ this.classicalSecret[i];
      }
    } else {
      finalSecret = sharedSecret;
    }

    // Step 3: Build binding data for signature
    const bindingData = this.buildBindingData(finalSecret);

    // Step 4: Sign binding data
    const signature = await this.sig.sign(bindingData, this.sigKeyPair.secretKey);

    // Step 5: Compute binding hash
    const bindingHash = createHash('sha256').update(Buffer.from(bindingData)).digest('hex');

    return {
      sharedSecret: finalSecret,
      kemCiphertext: ciphertext,
      signature,
      bindingHash,
      algorithms: {
        kem: {
          name: this.kem.descriptor.name,
          family: this.kem.descriptor.family,
          nistLevel: this.kem.descriptor.nistLevel,
        },
        sig: {
          name: this.sig.descriptor.name,
          family: this.sig.descriptor.family,
          nistLevel: this.sig.descriptor.nistLevel,
        },
      },
      hybrid: this.config.hybridMode ?? false,
    };
  }

  /**
   * Verify: check a signature over binding data using the signer's public key.
   */
  async verify(
    bindingData: Uint8Array,
    signature: Uint8Array,
    signerPublicKey: Uint8Array
  ): Promise<boolean> {
    return this.sig.verify(bindingData, signature, signerPublicKey);
  }

  /**
   * Decapsulate: recover shared secret from ciphertext.
   */
  async decapsulate(ciphertext: Uint8Array): Promise<Uint8Array> {
    if (!this.kemKeyPair) {
      throw new Error('QuantumSafeEnvelope not initialized');
    }

    const raw = await this.kem.decapsulate(ciphertext, this.kemKeyPair.secretKey);

    if (this.config.hybridMode && this.classicalSecret) {
      const mixed = new Uint8Array(32);
      for (let i = 0; i < 32; i++) {
        mixed[i] = raw[i] ^ this.classicalSecret[i];
      }
      return mixed;
    }

    return raw;
  }

  /**
   * Get the signer's public key (for verification by counterpart).
   */
  getSignerPublicKey(): Uint8Array {
    if (!this.sigKeyPair) throw new Error('Not initialized');
    return this.sigKeyPair.publicKey;
  }

  /**
   * Get the KEM public key (for encapsulation by counterpart).
   */
  getKEMPublicKey(): Uint8Array {
    if (!this.kemKeyPair) throw new Error('Not initialized');
    return this.kemKeyPair.publicKey;
  }

  /** Build canonical binding data: kemAlg ‖ sigAlg ‖ secret ‖ JSON(tags) */
  private buildBindingData(secret: Uint8Array): Uint8Array {
    const encoder = new TextEncoder();
    const parts = [
      encoder.encode(this.config.kemAlgorithm),
      encoder.encode(':'),
      encoder.encode(this.config.sigAlgorithm),
      encoder.encode(':'),
      secret,
    ];

    if (this.config.tags && Object.keys(this.config.tags).length > 0) {
      // Sort keys for canonical ordering
      const sorted = Object.keys(this.config.tags).sort();
      const tagStr = sorted.map((k) => `${k}=${this.config.tags![k]}`).join(',');
      parts.push(encoder.encode(':'));
      parts.push(encoder.encode(tagStr));
    }

    const totalLen = parts.reduce((s, p) => s + p.length, 0);
    const result = new Uint8Array(totalLen);
    let offset = 0;
    for (const p of parts) {
      result.set(p, offset);
      offset += p.length;
    }
    return result;
  }
}

// ============================================================
// PQC FAMILY COMPARISON TABLE
// ============================================================

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
export const PQC_FAMILY_TRADEOFFS: Record<PQCFamily, {
  keySize: string;
  outputSize: string;
  speed: string;
  maturity: string;
  scbeRecommendation: string;
}> = {
  lattice: {
    keySize: 'Medium (1-3 KB)',
    outputSize: 'Medium (1-3 KB)',
    speed: 'Fast',
    maturity: 'NIST FIPS standardized',
    scbeRecommendation: 'Primary — default for all SCBE deployments',
  },
  'hash-based': {
    keySize: 'Tiny (32-128 B)',
    outputSize: 'Large (8-30 KB signatures)',
    speed: 'Slow signing, fast verify',
    maturity: 'NIST FIPS 205 standardized',
    scbeRecommendation: 'Conservative backup — when lattice assumptions are questioned',
  },
  'code-based': {
    keySize: 'Very large (255+ KB public key)',
    outputSize: 'Tiny (128 B ciphertext)',
    speed: 'Fast',
    maturity: 'NIST Round 4 candidate',
    scbeRecommendation: 'Long-term KEM — when bandwidth is cheap but storage is not',
  },
  isogeny: {
    keySize: 'Tiny',
    outputSize: 'Tiny',
    speed: 'Very slow',
    maturity: 'Partially broken (SIDH); active research',
    scbeRecommendation: 'Not recommended — wait for next-gen (CSIDH variants)',
  },
  multivariate: {
    keySize: 'Large',
    outputSize: 'Tiny',
    speed: 'Fast verify',
    maturity: 'Niche, some schemes broken',
    scbeRecommendation: 'Experimental only — do not use in production governance',
  },
};
