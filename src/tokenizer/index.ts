/**
 * Tokenizer Module Exports
 *
 * Combines SS1 phonetic tokenization with post-quantum lattice cryptography
 * for dual-layer security (semantic + computational).
 *
 * @module tokenizer
 */

// SS1 Phonetic Tokenizer
export {
  // Types
  type TongueCode,
  type TongueInfo,
  type XlateAttestation,
  type BlendPattern,
  type SS1Envelope,

  // Constants
  TONGUES,
  TONGUE_CODES,

  // Core functions
  encode,
  decode,
  encodeByte,
  decodeByte,
  xlate,
  verifyXlateAttestation,
  blend,
  unblend,

  // Envelope functions
  createSS1Envelope,
  parseSS1Envelope,
  serializeSS1Envelope,
  deserializeSS1Envelope,

  // Utility functions
  detectTongue,
  validateTongueConsistency,
  calculateHarmonicWeight,
  getAudioSignature,

  // Class export
  SS1Tokenizer,
} from './ss1.js';

// Quantum Lattice Integration
export {
  // Types
  type LatticeParams,
  type DualLatticeEnvelope,
  type TongueLatticeBinding,

  // Constants
  LATTICE_PARAMS,
  TONGUE_LATTICE_BINDINGS,

  // Key generation
  generateLatticeKeypair,

  // KEM operations
  latticeEncapsulate,
  latticeDecapsulate,

  // Dual-lattice envelope
  createDualLatticeEnvelope,
  verifyDualLatticeBinding,
  decryptDualLatticeEnvelope,

  // Tongue-bound signatures
  signWithTongueBinding,
  verifyTongueBinding,

  // Default export
  QuantumLattice,
} from './quantum-lattice.js';
