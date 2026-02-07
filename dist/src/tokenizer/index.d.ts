/**
 * Tokenizer Module Exports
 *
 * Combines SS1 phonetic tokenization with post-quantum lattice cryptography
 * for dual-layer security (semantic + computational).
 *
 * @module tokenizer
 */
export { type TongueCode, type TongueInfo, type XlateAttestation, type BlendPattern, type SS1Envelope, TONGUES, TONGUE_CODES, encode, decode, encodeByte, decodeByte, xlate, verifyXlateAttestation, blend, unblend, createSS1Envelope, parseSS1Envelope, serializeSS1Envelope, deserializeSS1Envelope, detectTongue, validateTongueConsistency, calculateHarmonicWeight, getAudioSignature, SS1Tokenizer, } from './ss1.js';
export { type LatticeParams, type DualLatticeEnvelope, type TongueLatticeBinding, LATTICE_PARAMS, TONGUE_LATTICE_BINDINGS, generateLatticeKeypair, latticeEncapsulate, latticeDecapsulate, createDualLatticeEnvelope, verifyDualLatticeBinding, decryptDualLatticeEnvelope, signWithTongueBinding, verifyTongueBinding, QuantumLattice, } from './quantum-lattice.js';
//# sourceMappingURL=index.d.ts.map