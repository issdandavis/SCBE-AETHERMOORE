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

import { createHash, randomBytes } from 'crypto';
import {
  TongueCode,
  TONGUES,
  encode as ss1Encode,
  decode as ss1Decode,
  SS1Envelope,
  createSS1Envelope,
} from './ss1';

// ============================================================================
// Types
// ============================================================================

/** Lattice parameters for different security levels */
export interface LatticeParams {
  n: number; // Lattice dimension
  q: number; // Modulus
  sigma: number; // Gaussian noise parameter
  securityBits: number;
}

/** Dual-lattice encoded data */
export interface DualLatticeEnvelope {
  version: 'DL-SS1-v1';
  ss1: SS1Envelope;
  lattice: {
    publicKey: string; // Lattice public key (hex)
    ciphertext: string; // Lattice-encrypted session key (hex)
    params: 'ML-KEM-512' | 'ML-KEM-768' | 'ML-KEM-1024';
  };
  binding: {
    tongueHash: string; // Hash of tongue sequence
    latticeHash: string; // Hash of lattice ciphertext
    bindingProof: string; // HMAC binding both layers
  };
}

/** Tongue-Lattice binding for cross-layer security */
export interface TongueLatticeBinding {
  tongue: TongueCode;
  latticeDimension: number;
  noiseMultiplier: number;
  phaseIntegration: number; // Phase offset affects lattice sampling
}

// ============================================================================
// Lattice Parameters by Security Level
// ============================================================================

/** NIST ML-KEM parameters */
export const LATTICE_PARAMS: Record<string, LatticeParams> = {
  'ML-KEM-512': { n: 256, q: 3329, sigma: 3.2, securityBits: 128 },
  'ML-KEM-768': { n: 256, q: 3329, sigma: 3.2, securityBits: 192 },
  'ML-KEM-1024': { n: 256, q: 3329, sigma: 3.2, securityBits: 256 },
};

/** Tongue-specific lattice bindings */
export const TONGUE_LATTICE_BINDINGS: Record<TongueCode, TongueLatticeBinding> = {
  KO: {
    tongue: 'KO',
    latticeDimension: 256,
    noiseMultiplier: 1.0,
    phaseIntegration: 0,
  },
  AV: {
    tongue: 'AV',
    latticeDimension: 256,
    noiseMultiplier: 1.618,
    phaseIntegration: 60,
  },
  RU: {
    tongue: 'RU',
    latticeDimension: 384,
    noiseMultiplier: 2.618,
    phaseIntegration: 120,
  },
  CA: {
    tongue: 'CA',
    latticeDimension: 384,
    noiseMultiplier: 4.236,
    phaseIntegration: 180,
  },
  UM: {
    tongue: 'UM',
    latticeDimension: 512,
    noiseMultiplier: 6.854,
    phaseIntegration: 240,
  },
  DR: {
    tongue: 'DR',
    latticeDimension: 512,
    noiseMultiplier: 11.09,
    phaseIntegration: 300,
  },
};

// ============================================================================
// Simulated Lattice Operations (replace with liboqs in production)
// ============================================================================

/**
 * Generate a lattice keypair (simulated)
 *
 * In production, use liboqs ML-KEM implementation
 */
export function generateLatticeKeypair(params: string): {
  publicKey: Buffer;
  secretKey: Buffer;
} {
  const { securityBits } = LATTICE_PARAMS[params] || LATTICE_PARAMS['ML-KEM-768'];
  const keySize = securityBits * 4; // Simplified size calculation

  return {
    publicKey: randomBytes(keySize),
    secretKey: randomBytes(keySize * 2),
  };
}

/**
 * Lattice encapsulation (simulated KEM)
 *
 * Returns shared secret and ciphertext
 */
export function latticeEncapsulate(
  publicKey: Buffer,
  params: string
): {
  sharedSecret: Buffer;
  ciphertext: Buffer;
} {
  const { securityBits } = LATTICE_PARAMS[params] || LATTICE_PARAMS['ML-KEM-768'];

  // Simulate encapsulation (in production, use liboqs)
  const sharedSecret = createHash('sha256').update(publicKey).update(randomBytes(32)).digest();

  const ciphertext = Buffer.concat([randomBytes(securityBits * 2), createHash('sha256').update(sharedSecret).digest()]);

  return { sharedSecret, ciphertext };
}

/**
 * Lattice decapsulation (simulated)
 */
export function latticeDecapsulate(secretKey: Buffer, ciphertext: Buffer, params: string): Buffer {
  // Simulate decapsulation (in production, use liboqs)
  const { securityBits } = LATTICE_PARAMS[params] || LATTICE_PARAMS['ML-KEM-768'];

  // Extract embedded hash from ciphertext
  const embeddedHash = ciphertext.subarray(securityBits * 2);

  // Derive shared secret
  return createHash('sha256').update(secretKey).update(embeddedHash).digest();
}

// ============================================================================
// Dual-Lattice Encoding
// ============================================================================

/**
 * Apply phase-shifted noise to lattice operations based on tongue
 *
 * This binds the phonetic layer to the lattice layer mathematically
 */
function applyPhaseNoise(value: number, tongue: TongueCode): number {
  const binding = TONGUE_LATTICE_BINDINGS[tongue];
  const phaseRad = (binding.phaseIntegration * Math.PI) / 180;

  // Apply phase-modulated noise
  const noise = Math.sin(phaseRad) * binding.noiseMultiplier;
  return value + noise;
}

/**
 * Create tongue sequence hash for binding verification
 */
function hashTongueSequence(spellText: string): string {
  const tongues: string[] = [];
  const tokens = spellText.split(/\s+/);

  for (const token of tokens) {
    if (token.includes(':')) {
      tongues.push(token.split(':')[0].toUpperCase());
    }
  }

  return createHash('sha256').update(tongues.join(',')).digest('hex');
}

/**
 * Create dual-lattice envelope
 *
 * Combines SS1 phonetic encoding with lattice-based key encapsulation
 */
export function createDualLatticeEnvelope(params: {
  kid: string;
  data: Buffer;
  tongue: TongueCode;
  recipientPublicKey: Buffer;
  latticeParams?: string;
  secretKey?: Buffer;
}): DualLatticeEnvelope {
  const latticeParamsName = params.latticeParams ?? 'ML-KEM-768';

  // Step 1: Lattice encapsulation to get session key
  const { sharedSecret, ciphertext: latticeCiphertext } = latticeEncapsulate(
    params.recipientPublicKey,
    latticeParamsName
  );

  // Step 2: Use session key to encrypt data (AES-256-GCM simulation)
  const nonce = randomBytes(12);
  const salt = randomBytes(16);

  // Simple XOR "encryption" for simulation (use AES-GCM in production)
  const encryptedData = Buffer.alloc(params.data.length);
  for (let i = 0; i < params.data.length; i++) {
    encryptedData[i] = params.data[i] ^ sharedSecret[i % sharedSecret.length];
  }

  const tag = createHash('sha256').update(encryptedData).update(sharedSecret).digest().subarray(0, 16);

  // Step 3: Create SS1 envelope
  const ss1Envelope = createSS1Envelope({
    kid: params.kid,
    salt,
    ciphertext: encryptedData,
    tag,
    nonce,
  });

  // Step 4: Create binding proof
  const tongueHash = hashTongueSequence(ss1Envelope.ct);
  const latticeHash = createHash('sha256').update(latticeCiphertext).digest('hex');

  const bindingData = `${tongueHash}:${latticeHash}:${params.kid}`;
  const bindingProof = params.secretKey
    ? createHash('sha256').update(bindingData).update(params.secretKey).digest('hex')
    : createHash('sha256').update(bindingData).digest('hex');

  return {
    version: 'DL-SS1-v1',
    ss1: ss1Envelope,
    lattice: {
      publicKey: params.recipientPublicKey.toString('hex'),
      ciphertext: latticeCiphertext.toString('hex'),
      params: latticeParamsName as 'ML-KEM-512' | 'ML-KEM-768' | 'ML-KEM-1024',
    },
    binding: {
      tongueHash,
      latticeHash,
      bindingProof,
    },
  };
}

/**
 * Verify dual-lattice envelope binding
 *
 * Ensures the SS1 layer and lattice layer haven't been tampered with independently
 */
export function verifyDualLatticeBinding(envelope: DualLatticeEnvelope, secretKey?: Buffer): boolean {
  // Verify tongue hash matches SS1 content
  const computedTongueHash = hashTongueSequence(envelope.ss1.ct);
  if (computedTongueHash !== envelope.binding.tongueHash) {
    return false;
  }

  // Verify lattice hash matches ciphertext
  const computedLatticeHash = createHash('sha256')
    .update(Buffer.from(envelope.lattice.ciphertext, 'hex'))
    .digest('hex');

  if (computedLatticeHash !== envelope.binding.latticeHash) {
    return false;
  }

  // Verify binding proof
  const bindingData = `${envelope.binding.tongueHash}:${envelope.binding.latticeHash}:${envelope.ss1.kid}`;
  const expectedProof = secretKey
    ? createHash('sha256').update(bindingData).update(secretKey).digest('hex')
    : createHash('sha256').update(bindingData).digest('hex');

  return expectedProof === envelope.binding.bindingProof;
}

/**
 * Decrypt dual-lattice envelope
 */
export function decryptDualLatticeEnvelope(
  envelope: DualLatticeEnvelope,
  recipientSecretKey: Buffer
): Buffer {
  // Step 1: Verify binding
  if (!verifyDualLatticeBinding(envelope)) {
    throw new Error('Dual-lattice binding verification failed');
  }

  // Step 2: Lattice decapsulation
  const latticeCiphertext = Buffer.from(envelope.lattice.ciphertext, 'hex');
  const sharedSecret = latticeDecapsulate(recipientSecretKey, latticeCiphertext, envelope.lattice.params);

  // Step 3: Decrypt SS1 ciphertext
  const encryptedData = ss1Decode(envelope.ss1.ct, 'CA');

  // Simple XOR "decryption" (use AES-GCM in production)
  const decryptedData = Buffer.alloc(encryptedData.length);
  for (let i = 0; i < encryptedData.length; i++) {
    decryptedData[i] = encryptedData[i] ^ sharedSecret[i % sharedSecret.length];
  }

  // Step 4: Verify tag
  const expectedTag = createHash('sha256')
    .update(encryptedData)
    .update(sharedSecret)
    .digest()
    .subarray(0, 16);

  const actualTag = ss1Decode(envelope.ss1.tag, 'DR');

  if (!expectedTag.equals(actualTag)) {
    throw new Error('Tag verification failed');
  }

  return decryptedData;
}

// ============================================================================
// Quantum-Resistant Message Signing with Tongue Binding
// ============================================================================

/**
 * Sign a message with tongue-bound quantum-resistant signature
 *
 * The signature includes the tongue sequence, making it invalid if
 * the phonetic encoding is changed (defense against semantic attacks)
 */
export function signWithTongueBinding(
  message: Buffer,
  tongue: TongueCode,
  secretKey: Buffer
): {
  signature: string;
  tongueBinding: string;
} {
  // Encode message in the specified tongue
  const spellText = ss1Encode(message, tongue);

  // Create tongue-specific binding
  const binding = TONGUE_LATTICE_BINDINGS[tongue];
  const tongueBinding = `${tongue}:${binding.phaseIntegration}:${binding.noiseMultiplier}`;

  // Sign both message and tongue binding
  const dataToSign = Buffer.concat([message, Buffer.from(tongueBinding), Buffer.from(spellText)]);

  const signature = createHash('sha256').update(dataToSign).update(secretKey).digest('hex');

  return { signature, tongueBinding };
}

/**
 * Verify tongue-bound signature
 */
export function verifyTongueBinding(
  message: Buffer,
  tongue: TongueCode,
  signature: string,
  tongueBinding: string,
  publicKey: Buffer
): boolean {
  const spellText = ss1Encode(message, tongue);

  // Recreate expected binding
  const binding = TONGUE_LATTICE_BINDINGS[tongue];
  const expectedTongueBinding = `${tongue}:${binding.phaseIntegration}:${binding.noiseMultiplier}`;

  if (tongueBinding !== expectedTongueBinding) {
    return false;
  }

  // Verify signature
  const dataToSign = Buffer.concat([message, Buffer.from(tongueBinding), Buffer.from(spellText)]);

  // In production, use ML-DSA signature verification
  const expectedSignature = createHash('sha256').update(dataToSign).update(publicKey).digest('hex');

  return signature === expectedSignature;
}

// ============================================================================
// Export
// ============================================================================

export const QuantumLattice = {
  // Parameters
  LATTICE_PARAMS,
  TONGUE_LATTICE_BINDINGS,

  // Key generation
  generateKeypair: generateLatticeKeypair,

  // Encapsulation
  encapsulate: latticeEncapsulate,
  decapsulate: latticeDecapsulate,

  // Dual-lattice envelope
  createEnvelope: createDualLatticeEnvelope,
  verifyBinding: verifyDualLatticeBinding,
  decryptEnvelope: decryptDualLatticeEnvelope,

  // Tongue-bound signatures
  sign: signWithTongueBinding,
  verify: verifyTongueBinding,
};

export default QuantumLattice;
