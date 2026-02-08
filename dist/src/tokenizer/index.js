"use strict";
/**
 * Tokenizer Module Exports
 *
 * Combines SS1 phonetic tokenization with post-quantum lattice cryptography
 * for dual-layer security (semantic + computational).
 *
 * @module tokenizer
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.QuantumLattice = exports.verifyTongueBinding = exports.signWithTongueBinding = exports.decryptDualLatticeEnvelope = exports.verifyDualLatticeBinding = exports.createDualLatticeEnvelope = exports.latticeDecapsulate = exports.latticeEncapsulate = exports.generateLatticeKeypair = exports.TONGUE_LATTICE_BINDINGS = exports.LATTICE_PARAMS = exports.SS1Tokenizer = exports.getAudioSignature = exports.calculateHarmonicWeight = exports.validateTongueConsistency = exports.detectTongue = exports.deserializeSS1Envelope = exports.serializeSS1Envelope = exports.parseSS1Envelope = exports.createSS1Envelope = exports.unblend = exports.blend = exports.verifyXlateAttestation = exports.xlate = exports.decodeByte = exports.encodeByte = exports.decode = exports.encode = exports.TONGUE_CODES = exports.TONGUES = void 0;
// SS1 Phonetic Tokenizer
var ss1_js_1 = require("./ss1.js");
// Constants
Object.defineProperty(exports, "TONGUES", { enumerable: true, get: function () { return ss1_js_1.TONGUES; } });
Object.defineProperty(exports, "TONGUE_CODES", { enumerable: true, get: function () { return ss1_js_1.TONGUE_CODES; } });
// Core functions
Object.defineProperty(exports, "encode", { enumerable: true, get: function () { return ss1_js_1.encode; } });
Object.defineProperty(exports, "decode", { enumerable: true, get: function () { return ss1_js_1.decode; } });
Object.defineProperty(exports, "encodeByte", { enumerable: true, get: function () { return ss1_js_1.encodeByte; } });
Object.defineProperty(exports, "decodeByte", { enumerable: true, get: function () { return ss1_js_1.decodeByte; } });
Object.defineProperty(exports, "xlate", { enumerable: true, get: function () { return ss1_js_1.xlate; } });
Object.defineProperty(exports, "verifyXlateAttestation", { enumerable: true, get: function () { return ss1_js_1.verifyXlateAttestation; } });
Object.defineProperty(exports, "blend", { enumerable: true, get: function () { return ss1_js_1.blend; } });
Object.defineProperty(exports, "unblend", { enumerable: true, get: function () { return ss1_js_1.unblend; } });
// Envelope functions
Object.defineProperty(exports, "createSS1Envelope", { enumerable: true, get: function () { return ss1_js_1.createSS1Envelope; } });
Object.defineProperty(exports, "parseSS1Envelope", { enumerable: true, get: function () { return ss1_js_1.parseSS1Envelope; } });
Object.defineProperty(exports, "serializeSS1Envelope", { enumerable: true, get: function () { return ss1_js_1.serializeSS1Envelope; } });
Object.defineProperty(exports, "deserializeSS1Envelope", { enumerable: true, get: function () { return ss1_js_1.deserializeSS1Envelope; } });
// Utility functions
Object.defineProperty(exports, "detectTongue", { enumerable: true, get: function () { return ss1_js_1.detectTongue; } });
Object.defineProperty(exports, "validateTongueConsistency", { enumerable: true, get: function () { return ss1_js_1.validateTongueConsistency; } });
Object.defineProperty(exports, "calculateHarmonicWeight", { enumerable: true, get: function () { return ss1_js_1.calculateHarmonicWeight; } });
Object.defineProperty(exports, "getAudioSignature", { enumerable: true, get: function () { return ss1_js_1.getAudioSignature; } });
// Class export
Object.defineProperty(exports, "SS1Tokenizer", { enumerable: true, get: function () { return ss1_js_1.SS1Tokenizer; } });
// Quantum Lattice Integration
var quantum_lattice_js_1 = require("./quantum-lattice.js");
// Constants
Object.defineProperty(exports, "LATTICE_PARAMS", { enumerable: true, get: function () { return quantum_lattice_js_1.LATTICE_PARAMS; } });
Object.defineProperty(exports, "TONGUE_LATTICE_BINDINGS", { enumerable: true, get: function () { return quantum_lattice_js_1.TONGUE_LATTICE_BINDINGS; } });
// Key generation
Object.defineProperty(exports, "generateLatticeKeypair", { enumerable: true, get: function () { return quantum_lattice_js_1.generateLatticeKeypair; } });
// KEM operations
Object.defineProperty(exports, "latticeEncapsulate", { enumerable: true, get: function () { return quantum_lattice_js_1.latticeEncapsulate; } });
Object.defineProperty(exports, "latticeDecapsulate", { enumerable: true, get: function () { return quantum_lattice_js_1.latticeDecapsulate; } });
// Dual-lattice envelope
Object.defineProperty(exports, "createDualLatticeEnvelope", { enumerable: true, get: function () { return quantum_lattice_js_1.createDualLatticeEnvelope; } });
Object.defineProperty(exports, "verifyDualLatticeBinding", { enumerable: true, get: function () { return quantum_lattice_js_1.verifyDualLatticeBinding; } });
Object.defineProperty(exports, "decryptDualLatticeEnvelope", { enumerable: true, get: function () { return quantum_lattice_js_1.decryptDualLatticeEnvelope; } });
// Tongue-bound signatures
Object.defineProperty(exports, "signWithTongueBinding", { enumerable: true, get: function () { return quantum_lattice_js_1.signWithTongueBinding; } });
Object.defineProperty(exports, "verifyTongueBinding", { enumerable: true, get: function () { return quantum_lattice_js_1.verifyTongueBinding; } });
// Default export
Object.defineProperty(exports, "QuantumLattice", { enumerable: true, get: function () { return quantum_lattice_js_1.QuantumLattice; } });
//# sourceMappingURL=index.js.map