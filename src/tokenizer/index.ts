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

// SS2 Semantic Atom Layer
// NOTE: SemanticWorkflowThread is intentionally NOT re-exported from
// semantic-atom.js here. The name is claimed by the richer
// semantic-workflow-thread.ts module below (schema 'scbe-workflow-thread-v1').
// Callers that need the simpler SemanticWorkflowThread from semantic-atom.ts
// can import it directly from './semantic-atom.js'.
export {
  SEMANTIC_ATOMS,
  getSemanticAtom,
  buildRelationTree,
  embedSemanticAtom,
  tokenizeSemanticAtoms,
  buildSemanticLedgerEntry,
  buildSemanticWorkflowThread,
  type SemanticDomain,
  type SemanticRelationKind,
  type SemanticWorkflowChannel,
  type SemanticNucleus,
  type SemanticOrbital,
  type SemanticBond,
  type SemanticIsotope,
  type SemanticCodeRelations,
  type AtomicProxy,
  type SemanticAtom,
  type SemanticToken,
  type SemanticLedgerEntry,
  type SemanticWorkflowNode,
  type SemanticWorkflowEdge,
} from './semantic-atom.js';

// SS3 Semantic Workflow Thread — multi-lane highway model
export {
  // Builder class
  WorkflowThreadBuilder,

  // Factory and utilities
  createWorkflowThread,
  serializeThread,
  validateThread,

  // Types
  type ThreadEdgeKind,
  type ThreadNode,
  type ThreadEdge,
  type TunnelSegment,
  type WorkflowThreadReceipt,
  type SemanticWorkflowThread,
} from './semantic-workflow-thread.js';

// SS4 NSM Prime Anchors — Wierzbicka semantic primes + phi-extrapolation
export {
  NSM_PRIMES,
  PHI,
  TONGUE_ORDER,
  TONGUE_PHASE,
  TONGUE_WEIGHT,
  getPrime,
  primesForTongue,
  coverageReport,
  gridIndex,
  primeGridIndex,
  gridPositionForTongue,
  phiExtrapolate,
  phiExtrapolateAll,
  findEmptyLatticeSites,
  generateSubprimeAnchors,
  type NSMPrime,
  type PrimeSpan,
  type PhiExtrapolation,
  type SubPrimeAnchor,
  type CoverageReport,
} from './nsmPrimes.js';

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
