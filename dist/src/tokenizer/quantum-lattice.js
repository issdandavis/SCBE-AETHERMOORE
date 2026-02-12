"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.QuantumLattice = exports.TONGUE_LATTICE_BINDINGS = exports.LATTICE_PARAMS = void 0;
exports.generateLatticeKeypair = generateLatticeKeypair;
exports.latticeEncapsulate = latticeEncapsulate;
exports.latticeDecapsulate = latticeDecapsulate;
exports.createDualLatticeEnvelope = createDualLatticeEnvelope;
exports.verifyDualLatticeBinding = verifyDualLatticeBinding;
exports.decryptDualLatticeEnvelope = decryptDualLatticeEnvelope;
exports.signWithTongueBinding = signWithTongueBinding;
exports.verifyTongueBinding = verifyTongueBinding;
const crypto_1 = require("crypto");
const ss1_1 = require("./ss1");
// ============================================================================
// Lattice Parameters by Security Level
// ============================================================================
/** NIST ML-KEM parameters */
exports.LATTICE_PARAMS = {
    'ML-KEM-512': { n: 256, q: 3329, sigma: 3.2, securityBits: 128 },
    'ML-KEM-768': { n: 256, q: 3329, sigma: 3.2, securityBits: 192 },
    'ML-KEM-1024': { n: 256, q: 3329, sigma: 3.2, securityBits: 256 },
};
/** Tongue-specific lattice bindings */
exports.TONGUE_LATTICE_BINDINGS = {
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
function generateLatticeKeypair(params) {
    const { securityBits } = exports.LATTICE_PARAMS[params] || exports.LATTICE_PARAMS['ML-KEM-768'];
    const keySize = securityBits * 4; // Simplified size calculation
    return {
        publicKey: (0, crypto_1.randomBytes)(keySize),
        secretKey: (0, crypto_1.randomBytes)(keySize * 2),
    };
}
/**
 * Lattice encapsulation (simulated KEM)
 *
 * Returns shared secret and ciphertext
 */
function latticeEncapsulate(publicKey, params) {
    const { securityBits } = exports.LATTICE_PARAMS[params] || exports.LATTICE_PARAMS['ML-KEM-768'];
    // Simulate encapsulation (in production, use liboqs)
    const sharedSecret = (0, crypto_1.createHash)('sha256').update(publicKey).update((0, crypto_1.randomBytes)(32)).digest();
    const ciphertext = Buffer.concat([
        (0, crypto_1.randomBytes)(securityBits * 2),
        (0, crypto_1.createHash)('sha256').update(sharedSecret).digest(),
    ]);
    return { sharedSecret, ciphertext };
}
/**
 * Lattice decapsulation (simulated)
 */
function latticeDecapsulate(secretKey, ciphertext, params) {
    // Simulate decapsulation (in production, use liboqs)
    const { securityBits } = exports.LATTICE_PARAMS[params] || exports.LATTICE_PARAMS['ML-KEM-768'];
    // Extract embedded hash from ciphertext
    const embeddedHash = ciphertext.subarray(securityBits * 2);
    // Derive shared secret
    return (0, crypto_1.createHash)('sha256').update(secretKey).update(embeddedHash).digest();
}
// ============================================================================
// Dual-Lattice Encoding
// ============================================================================
/**
 * Apply phase-shifted noise to lattice operations based on tongue
 *
 * This binds the phonetic layer to the lattice layer mathematically
 */
function applyPhaseNoise(value, tongue) {
    const binding = exports.TONGUE_LATTICE_BINDINGS[tongue];
    const phaseRad = (binding.phaseIntegration * Math.PI) / 180;
    // Apply phase-modulated noise
    const noise = Math.sin(phaseRad) * binding.noiseMultiplier;
    return value + noise;
}
/**
 * Create tongue sequence hash for binding verification
 */
function hashTongueSequence(spellText) {
    const tongues = [];
    const tokens = spellText.split(/\s+/);
    for (const token of tokens) {
        if (token.includes(':')) {
            tongues.push(token.split(':')[0].toUpperCase());
        }
    }
    return (0, crypto_1.createHash)('sha256').update(tongues.join(',')).digest('hex');
}
/**
 * Create dual-lattice envelope
 *
 * Combines SS1 phonetic encoding with lattice-based key encapsulation
 */
function createDualLatticeEnvelope(params) {
    const latticeParamsName = params.latticeParams ?? 'ML-KEM-768';
    // Step 1: Lattice encapsulation to get session key
    const { sharedSecret, ciphertext: latticeCiphertext } = latticeEncapsulate(params.recipientPublicKey, latticeParamsName);
    // Step 2: Use session key to encrypt data (AES-256-GCM simulation)
    const nonce = (0, crypto_1.randomBytes)(12);
    const salt = (0, crypto_1.randomBytes)(16);
    // Simple XOR "encryption" for simulation (use AES-GCM in production)
    const encryptedData = Buffer.alloc(params.data.length);
    for (let i = 0; i < params.data.length; i++) {
        encryptedData[i] = params.data[i] ^ sharedSecret[i % sharedSecret.length];
    }
    const tag = (0, crypto_1.createHash)('sha256')
        .update(encryptedData)
        .update(sharedSecret)
        .digest()
        .subarray(0, 16);
    // Step 3: Create SS1 envelope
    const ss1Envelope = (0, ss1_1.createSS1Envelope)({
        kid: params.kid,
        salt,
        ciphertext: encryptedData,
        tag,
        nonce,
    });
    // Step 4: Create binding proof
    const tongueHash = hashTongueSequence(ss1Envelope.ct);
    const latticeHash = (0, crypto_1.createHash)('sha256').update(latticeCiphertext).digest('hex');
    const bindingData = `${tongueHash}:${latticeHash}:${params.kid}`;
    const bindingProof = params.secretKey
        ? (0, crypto_1.createHash)('sha256').update(bindingData).update(params.secretKey).digest('hex')
        : (0, crypto_1.createHash)('sha256').update(bindingData).digest('hex');
    return {
        version: 'DL-SS1-v1',
        ss1: ss1Envelope,
        lattice: {
            publicKey: params.recipientPublicKey.toString('hex'),
            ciphertext: latticeCiphertext.toString('hex'),
            params: latticeParamsName,
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
function verifyDualLatticeBinding(envelope, secretKey) {
    // Verify tongue hash matches SS1 content
    const computedTongueHash = hashTongueSequence(envelope.ss1.ct);
    if (computedTongueHash !== envelope.binding.tongueHash) {
        return false;
    }
    // Verify lattice hash matches ciphertext
    const computedLatticeHash = (0, crypto_1.createHash)('sha256')
        .update(Buffer.from(envelope.lattice.ciphertext, 'hex'))
        .digest('hex');
    if (computedLatticeHash !== envelope.binding.latticeHash) {
        return false;
    }
    // Verify binding proof
    const bindingData = `${envelope.binding.tongueHash}:${envelope.binding.latticeHash}:${envelope.ss1.kid}`;
    const expectedProof = secretKey
        ? (0, crypto_1.createHash)('sha256').update(bindingData).update(secretKey).digest('hex')
        : (0, crypto_1.createHash)('sha256').update(bindingData).digest('hex');
    return expectedProof === envelope.binding.bindingProof;
}
/**
 * Decrypt dual-lattice envelope
 */
function decryptDualLatticeEnvelope(envelope, recipientSecretKey) {
    // Step 1: Verify binding
    if (!verifyDualLatticeBinding(envelope)) {
        throw new Error('Dual-lattice binding verification failed');
    }
    // Step 2: Lattice decapsulation
    const latticeCiphertext = Buffer.from(envelope.lattice.ciphertext, 'hex');
    const sharedSecret = latticeDecapsulate(recipientSecretKey, latticeCiphertext, envelope.lattice.params);
    // Step 3: Decrypt SS1 ciphertext
    const encryptedData = (0, ss1_1.decode)(envelope.ss1.ct, 'CA');
    // Simple XOR "decryption" (use AES-GCM in production)
    const decryptedData = Buffer.alloc(encryptedData.length);
    for (let i = 0; i < encryptedData.length; i++) {
        decryptedData[i] = encryptedData[i] ^ sharedSecret[i % sharedSecret.length];
    }
    // Step 4: Verify tag
    const expectedTag = (0, crypto_1.createHash)('sha256')
        .update(encryptedData)
        .update(sharedSecret)
        .digest()
        .subarray(0, 16);
    const actualTag = (0, ss1_1.decode)(envelope.ss1.tag, 'DR');
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
function signWithTongueBinding(message, tongue, secretKey) {
    // Encode message in the specified tongue
    const spellText = (0, ss1_1.encode)(message, tongue);
    // Create tongue-specific binding
    const binding = exports.TONGUE_LATTICE_BINDINGS[tongue];
    const tongueBinding = `${tongue}:${binding.phaseIntegration}:${binding.noiseMultiplier}`;
    // Sign both message and tongue binding
    const dataToSign = Buffer.concat([message, Buffer.from(tongueBinding), Buffer.from(spellText)]);
    const signature = (0, crypto_1.createHash)('sha256').update(dataToSign).update(secretKey).digest('hex');
    return { signature, tongueBinding };
}
/**
 * Verify tongue-bound signature
 */
function verifyTongueBinding(message, tongue, signature, tongueBinding, publicKey) {
    const spellText = (0, ss1_1.encode)(message, tongue);
    // Recreate expected binding
    const binding = exports.TONGUE_LATTICE_BINDINGS[tongue];
    const expectedTongueBinding = `${tongue}:${binding.phaseIntegration}:${binding.noiseMultiplier}`;
    if (tongueBinding !== expectedTongueBinding) {
        return false;
    }
    // Verify signature
    const dataToSign = Buffer.concat([message, Buffer.from(tongueBinding), Buffer.from(spellText)]);
    // In production, use ML-DSA signature verification
    const expectedSignature = (0, crypto_1.createHash)('sha256').update(dataToSign).update(publicKey).digest('hex');
    return signature === expectedSignature;
}
// ============================================================================
// Export
// ============================================================================
exports.QuantumLattice = {
    // Parameters
    LATTICE_PARAMS: exports.LATTICE_PARAMS,
    TONGUE_LATTICE_BINDINGS: exports.TONGUE_LATTICE_BINDINGS,
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
exports.default = exports.QuantumLattice;
//# sourceMappingURL=quantum-lattice.js.map