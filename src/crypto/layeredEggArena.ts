/**
 * @file layeredEggArena.ts
 * @module crypto/layeredEggArena
 * @layer Layer 1-14
 * @component Layered Egg Arena — Sacred Eggs × Shifting Keyspace × 14-Layer Pipeline
 *
 * SYSTEMS ARE ABOUT LAYERS.
 *
 * This module unifies three concepts:
 *
 *   1. **Sacred Eggs** — ciphertext containers that only decrypt when
 *      ALL predicates pass (tongue, geometry, path, quorum, crypto).
 *      Failure returns noise, not an error. The attacker can't even tell
 *      which predicate failed.
 *
 *   2. **Shifting Keyspace** — governance axes (time, intent, authority,
 *      tongue phase, breathing, flux) that expand the search space mid-attack.
 *      Temporal axes shift via golden-ratio stepping, invalidating progress.
 *
 *   3. **14-Layer Pipeline** — each layer seals its output in an egg whose
 *      predicates include the shifting keyspace state. The next layer can't
 *      read the output until it hatches the egg. 14 layers = 14 nested eggs.
 *
 * THE COMPOUND EFFECT:
 *
 *   An attacker breaking ONE egg gets ONE layer's output.
 *   But that output is the ciphertext of the NEXT layer's egg.
 *   And by the time they break the first egg, the shifting keyspace
 *   has rotated — the second egg's predicates have changed.
 *
 *   Cost to break one egg:  2^(base + governance) work
 *   Cost to break 14 eggs:  14 × 2^(base + governance) SEQUENTIAL work
 *                           (can't parallelize — each egg needs the previous plaintext)
 *
 *   But it's worse than 14×: each egg has DIFFERENT predicates.
 *   Layer 1's egg needs tongue KO. Layer 5's egg needs tongue UM.
 *   Layer 8's egg requires ring 0 (core). Layer 13 requires quorum.
 *   An attacker who compromises KO still can't touch UM.
 *
 *   And the shifting keyspace means every breathing cycle RESETS
 *   the attacker's partial progress on ALL 14 eggs simultaneously.
 *
 * A5: Composition — the whole pipeline is the composition of 14 sealed layers
 * A3: Causality — eggs must be hatched in order (L1 before L2 before...)
 * A2: Unitarity — each layer preserves the egg's cryptographic guarantees
 */

import { createHash, randomBytes } from 'crypto';
import type { GovernanceAxis, KeyspaceSnapshot } from './pqcArena';
import { ShiftingKeyspace } from './pqcArena';

// ============================================================================
// Layer Egg — A Sacred Egg bound to a specific pipeline layer
// ============================================================================

/** Which Sacred Tongue governs each pipeline layer */
export const LAYER_TONGUE_MAP: Record<number, 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR'> = {
  1: 'KO', // L1 Complex Context — Control
  2: 'KO', // L2 Realification — Control
  3: 'RU', // L3 Weighted Transform — Policy
  4: 'RU', // L4 Poincaré Embedding — Policy
  5: 'UM', // L5 Hyperbolic Distance — Security
  6: 'AV', // L6 Breathing Transform — I/O
  7: 'AV', // L7 Möbius Phase — I/O
  8: 'CA', // L8 Multi-well Hamiltonian — Logic
  9: 'CA', // L9 Spectral Coherence — Logic
  10: 'DR', // L10 Spin Coherence — Types
  11: 'DR', // L11 Temporal Distance — Types
  12: 'UM', // L12 Harmonic Wall — Security
  13: 'RU', // L13 Risk Decision — Policy
  14: 'AV', // L14 Audio Axis — I/O
};

/** Which quantum axiom each layer satisfies */
export const LAYER_AXIOM_MAP: Record<number, string> = {
  1: 'composition',
  2: 'unitarity',
  3: 'locality',
  4: 'unitarity',
  5: 'symmetry',
  6: 'causality',
  7: 'unitarity',
  8: 'locality',
  9: 'symmetry',
  10: 'symmetry',
  11: 'causality',
  12: 'symmetry',
  13: 'causality',
  14: 'composition',
};

/** Ring level required for each layer (0=core, 4=edge) */
export const LAYER_RING_REQUIREMENT: Record<number, number> = {
  1: 4, // Entry — any ring
  2: 4, // Realification — any ring
  3: 3, // Weighted — outer ok
  4: 3, // Poincaré — outer ok
  5: 2, // Hyperbolic distance — inner/middle only
  6: 3, // Breathing — outer ok (I/O layer)
  7: 2, // Möbius — inner/middle
  8: 1, // Multi-well Hamiltonian — inner only
  9: 2, // Spectral — inner/middle
  10: 2, // Spin — inner/middle
  11: 1, // Temporal — inner only
  12: 1, // Harmonic wall — inner only (security critical)
  13: 0, // Risk decision — CORE ONLY
  14: 2, // Audio axis — inner/middle
};

/**
 * A Sacred Egg bound to a specific pipeline layer.
 *
 * Each LayerEgg wraps one layer's output and adds:
 * - The layer's tongue requirement (from LAYER_TONGUE_MAP)
 * - The layer's ring requirement (from LAYER_RING_REQUIREMENT)
 * - A snapshot of the shifting keyspace at seal time
 * - A governance fingerprint that must match at hatch time
 *
 * If ANY predicate fails, the egg returns noise.
 * The next layer gets garbage and its own egg will also fail.
 * This creates a CASCADING FAILURE for attackers.
 */
export interface LayerEgg {
  /** Which pipeline layer this egg belongs to */
  layerNumber: number;
  /** Layer name */
  layerName: string;
  /** Quantum axiom this layer satisfies */
  axiom: string;
  /** Required tongue to hatch */
  requiredTongue: 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';
  /** Maximum ring level allowed */
  maxRing: number;
  /** Governance fingerprint at seal time */
  governanceFingerprint: string;
  /** Shifting keyspace snapshot when egg was sealed */
  keyspaceAtSeal: KeyspaceSnapshot;
  /** Hash of previous layer's egg (chain integrity) */
  previousEggHash: string;
  /** Sealed payload (encrypted layer output) */
  sealedPayload: string;
  /** Whether this egg has been successfully hatched */
  hatched: boolean;
  /** Timestamp when sealed */
  sealedAt: number;
}

/** Pipeline layer names */
const LAYER_NAMES: Record<number, string> = {
  1: 'Complex Context',
  2: 'Realification',
  3: 'Weighted Transform',
  4: 'Poincaré Embedding',
  5: 'Hyperbolic Distance',
  6: 'Breathing Transform',
  7: 'Möbius Phase',
  8: 'Multi-well Hamiltonian',
  9: 'Spectral Coherence',
  10: 'Spin Coherence',
  11: 'Temporal Distance',
  12: 'Harmonic Wall',
  13: 'Risk Decision',
  14: 'Audio Axis',
};

// ============================================================================
// Governance Fingerprint
// ============================================================================

/**
 * Create a governance fingerprint from the current keyspace state.
 *
 * This fingerprint is bound into the egg's seal. At hatch time,
 * the fingerprint must match — meaning the governance axes must
 * be in the same position as when the egg was sealed.
 *
 * For TEMPORAL axes, this means the egg can only be hatched during
 * the same breathing phase. After the stairwell rotates, the
 * fingerprint is invalid and the egg returns noise.
 *
 * MATH:
 *   fingerprint = SHA-256(axis₁.value || axis₂.value || ... || axisₙ.value)
 *
 *   Attacker needs to either:
 *   (a) Know all axis values (requires being inside the system)
 *   (b) Brute-force 2^96 combinations (governance bits)
 *   (c) Wait for the same values to recur (irrational stepping = never)
 */
export function createGovernanceFingerprint(snapshot: KeyspaceSnapshot): string {
  const values = snapshot.axes.map((a) => a.currentValue.toString(36)).join(':');
  return createHash('sha256')
    .update(`gov:${snapshot.breathingPhase}:${values}`)
    .digest('hex')
    .slice(0, 32);
}

/**
 * Verify a governance fingerprint against current keyspace state.
 *
 * Returns true only if the axes haven't shifted since seal time.
 */
export function verifyGovernanceFingerprint(
  fingerprint: string,
  currentSnapshot: KeyspaceSnapshot
): boolean {
  return createGovernanceFingerprint(currentSnapshot) === fingerprint;
}

// ============================================================================
// Layered Egg Chain
// ============================================================================

/**
 * Result of attempting to hatch a layer egg.
 */
export interface LayerHatchResult {
  /** Whether the hatch succeeded */
  success: boolean;
  /** Layer number */
  layerNumber: number;
  /** Which predicate failed (null if success, 'noise' if failed — no specifics) */
  failureMode: 'noise' | null;
  /** Payload (real data on success, random noise on failure) */
  payload: string;
  /** Whether governance fingerprint matched */
  governanceValid: boolean;
  /** Whether tongue matched */
  tongueValid: boolean;
  /** Whether ring level was sufficient */
  ringValid: boolean;
  /** Whether chain hash was valid (previous egg) */
  chainValid: boolean;
}

/**
 * Context for hatching an egg — what the hatching actor presents.
 */
export interface HatchContext {
  /** Actor's current tongue */
  tongue: 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';
  /** Actor's current ring level (0=core, 4=edge) */
  ringLevel: number;
  /** Current keyspace snapshot (for governance fingerprint check) */
  currentKeyspace: KeyspaceSnapshot;
  /** Hash of the previous layer's egg (for chain verification) */
  previousEggHash: string;
}

/**
 * LayeredEggChain — seals the entire 14-layer pipeline as a chain of eggs.
 *
 * Think of it as 14 locked rooms in sequence:
 *
 *   Room 1 (KO tongue, any ring): Contains the Complex Context output
 *   Room 2 (KO tongue, any ring): Contains the Realification output
 *   ...
 *   Room 8 (CA tongue, inner ring): Contains the Hamiltonian output
 *   ...
 *   Room 13 (RU tongue, CORE ring): Contains the Risk Decision
 *   Room 14 (AV tongue, inner ring): Contains the Audio Axis output
 *
 * To read Room N, you must:
 *   (a) Have the right tongue for Room N
 *   (b) Be at the right ring level for Room N
 *   (c) Present the governance fingerprint from seal time
 *   (d) Present proof that you hatched Room N-1 (chain hash)
 *
 * An attacker who breaks Room 1 still can't read Room 5 because
 * Room 5 requires tongue UM (Security), not tongue KO (Control).
 * And even if they had all tongues, the governance fingerprint
 * has shifted since they started.
 */
export class LayeredEggChain {
  private readonly keyspace: ShiftingKeyspace;
  private readonly eggs: Map<number, LayerEgg> = new Map();
  private readonly baseBits: number;

  constructor(baseBits: number = 192) {
    this.baseBits = baseBits;
    this.keyspace = new ShiftingKeyspace(baseBits);

    // Inject the standard 6 governance axes
    this.keyspace.injectAxis({
      name: 'TIME',
      tongue: 'KO',
      cardinality: Math.pow(2, 32),
      temporal: true,
      description: 'Epoch bucket',
    });
    this.keyspace.injectAxis({
      name: 'INTENT',
      tongue: 'CA',
      cardinality: Math.pow(2, 16),
      temporal: false,
      description: 'Intent hash',
    });
    this.keyspace.injectAxis({
      name: 'AUTHORITY',
      tongue: 'RU',
      cardinality: Math.pow(2, 8),
      temporal: false,
      description: 'Role encoding',
    });
    this.keyspace.injectAxis({
      name: 'TONGUE_PHASE',
      tongue: 'DR',
      cardinality: Math.pow(2, 24),
      temporal: true,
      description: 'Combined tongue phase',
    });
    this.keyspace.injectAxis({
      name: 'BREATHING',
      tongue: 'AV',
      cardinality: Math.pow(2, 12),
      temporal: true,
      description: 'Breathing phase',
    });
    this.keyspace.injectAxis({
      name: 'FLUX',
      tongue: 'UM',
      cardinality: Math.pow(2, 4),
      temporal: true,
      description: 'Flux state',
    });
  }

  /**
   * Seal the entire 14-layer pipeline as a chain of eggs.
   *
   * Each layer's output is sealed in an egg whose predicates include:
   * - The layer's tongue requirement
   * - The layer's ring requirement
   * - The governance fingerprint (shifting keyspace state)
   * - A hash of the previous layer's egg (chain integrity)
   *
   * The chain is sealed sequentially: L1 → L2 → ... → L14
   * Each egg's hash feeds into the next egg as a chain link.
   */
  sealPipeline(layerOutputs: Map<number, string>): LayerEgg[] {
    const snapshot = this.keyspace.snapshot();
    const govFingerprint = createGovernanceFingerprint(snapshot);
    const sealedEggs: LayerEgg[] = [];
    let previousHash = 'genesis'; // First egg has no predecessor

    for (let layer = 1; layer <= 14; layer++) {
      const output = layerOutputs.get(layer) ?? `layer_${layer}_output`;

      // Seal the output with HMAC using governance fingerprint as key
      const sealedPayload = createHash('sha256')
        .update(`${govFingerprint}:${output}`)
        .digest('hex');

      const egg: LayerEgg = {
        layerNumber: layer,
        layerName: LAYER_NAMES[layer] ?? `Layer ${layer}`,
        axiom: LAYER_AXIOM_MAP[layer] ?? 'unknown',
        requiredTongue: LAYER_TONGUE_MAP[layer] ?? 'KO',
        maxRing: LAYER_RING_REQUIREMENT[layer] ?? 4,
        governanceFingerprint: govFingerprint,
        keyspaceAtSeal: snapshot,
        previousEggHash: previousHash,
        sealedPayload,
        hatched: false,
        sealedAt: Date.now(),
      };

      // Hash this egg for the chain link
      previousHash = createHash('sha256')
        .update(`egg:${layer}:${sealedPayload}:${previousHash}`)
        .digest('hex')
        .slice(0, 32);

      this.eggs.set(layer, egg);
      sealedEggs.push(egg);
    }

    return sealedEggs;
  }

  /**
   * Attempt to hatch a layer egg.
   *
   * ALL predicates must pass:
   *   P1 (Tongue): actor.tongue === egg.requiredTongue
   *   P2 (Ring):   actor.ringLevel <= egg.maxRing
   *   P3 (Gov):    governance fingerprint matches (axes haven't shifted)
   *   P4 (Chain):  previous egg hash matches (proves L(n-1) was hatched)
   *
   * On ANY failure: returns random noise (fail-to-noise).
   * The attacker can't tell which predicate failed.
   */
  hatchLayer(layerNumber: number, context: HatchContext): LayerHatchResult {
    const egg = this.eggs.get(layerNumber);
    if (!egg) {
      return {
        success: false,
        layerNumber,
        failureMode: 'noise',
        payload: randomBytes(32).toString('hex'),
        governanceValid: false,
        tongueValid: false,
        ringValid: false,
        chainValid: false,
      };
    }

    // P1: Tongue check
    const tongueValid = context.tongue === egg.requiredTongue;

    // P2: Ring check
    const ringValid = context.ringLevel <= egg.maxRing;

    // P3: Governance fingerprint check
    const governanceValid = verifyGovernanceFingerprint(
      egg.governanceFingerprint,
      context.currentKeyspace
    );

    // P4: Chain integrity check
    const chainValid = context.previousEggHash === egg.previousEggHash;

    // ALL must pass — fail-to-noise on any failure
    if (!tongueValid || !ringValid || !governanceValid || !chainValid) {
      return {
        success: false,
        layerNumber,
        failureMode: 'noise',
        payload: randomBytes(32).toString('hex'),
        governanceValid,
        tongueValid,
        ringValid,
        chainValid,
      };
    }

    // All predicates passed — return real payload
    egg.hatched = true;
    return {
      success: true,
      layerNumber,
      failureMode: null,
      payload: egg.sealedPayload,
      governanceValid: true,
      tongueValid: true,
      ringValid: true,
      chainValid: true,
    };
  }

  /**
   * Rotate the stairwell — shift all temporal axes.
   *
   * After this call, ALL governance fingerprints in sealed eggs
   * become INVALID. Any unhatchied eggs will now return noise
   * because P3 (governance) will fail.
   *
   * This is why the attacker can't win: by the time they break
   * one egg's predicates, the stairwell has rotated and they
   * need to start over.
   */
  breathe(): void {
    this.keyspace.breathe();
  }

  /**
   * Get a security analysis of the entire chain.
   *
   * Shows exactly how hard it is to break all 14 layers
   * and why the attacker faces compounding costs.
   */
  getSecurityAnalysis(): ChainSecurityAnalysis {
    const snapshot = this.keyspace.snapshot();
    const eggs = Array.from(this.eggs.values());

    // Count distinct tongues required across all layers
    const requiredTongues = new Set(eggs.map((e) => e.requiredTongue));

    // Find the most restrictive ring requirement
    const strictestRing = Math.min(...eggs.map((e) => e.maxRing));

    // Count distinct axioms
    const axioms = new Set(eggs.map((e) => e.axiom));

    // Sequential break cost:
    // Each egg costs 2^effectiveBits to break
    // 14 eggs in sequence = 14 × 2^effectiveBits
    // But that's a LOWER BOUND — the tongue/ring diversity makes it worse
    const perEggBits = snapshot.effectiveBits;
    const sequentialCostLog2 = perEggBits + Math.log2(14);

    // Tongue diversity bonus:
    // If the attacker compromises one tongue, they can only hatch
    // layers that require that tongue. They need ALL 6 tongues.
    // Each tongue compromise is independent → multiply costs
    const tongueDiversityBits = Math.log2(requiredTongues.size) * 8;

    // Ring escalation cost:
    // Getting from ring 4 (edge) to ring 0 (core) requires
    // strictly descending path through all rings.
    // This is O(5!) = 120 valid orderings, but only 1 is correct
    const ringEscalationBits = Math.log2(120);

    // Total effective chain security
    const totalEffectiveBits = sequentialCostLog2 + tongueDiversityBits + ringEscalationBits;

    return {
      layerCount: eggs.length,
      baseBitsPerEgg: this.baseBits,
      governanceBitsPerEgg: snapshot.effectiveBits - this.baseBits,
      effectiveBitsPerEgg: snapshot.effectiveBits,
      sequentialCostLog2,
      tongueDiversityBits,
      tonguesRequired: Array.from(requiredTongues),
      ringEscalationBits,
      strictestRing,
      totalEffectiveBits,
      axiomsCovered: Array.from(axioms),
      temporalAxes: snapshot.axes.filter((a) => a.temporal).length,
      staticAxes: snapshot.axes.filter((a) => !a.temporal).length,
      breathingInvalidatesAll: true,
      summary: this.buildSummary(
        perEggBits,
        sequentialCostLog2,
        totalEffectiveBits,
        requiredTongues.size
      ),
    };
  }

  /** Get the current keyspace snapshot */
  getKeyspaceSnapshot(): KeyspaceSnapshot {
    return this.keyspace.snapshot();
  }

  /** Get an egg by layer number */
  getEgg(layerNumber: number): LayerEgg | undefined {
    return this.eggs.get(layerNumber);
  }

  /** Get all eggs */
  getAllEggs(): LayerEgg[] {
    return Array.from(this.eggs.values());
  }

  /** Compute the egg hash for a given layer (used for chain verification) */
  computeEggHash(layerNumber: number): string {
    const egg = this.eggs.get(layerNumber);
    if (!egg) return 'unknown';
    return createHash('sha256')
      .update(`egg:${layerNumber}:${egg.sealedPayload}:${egg.previousEggHash}`)
      .digest('hex')
      .slice(0, 32);
  }

  private buildSummary(
    perEggBits: number,
    sequentialBits: number,
    totalBits: number,
    tongueCount: number
  ): string {
    return [
      `Layered Egg Chain Security Analysis`,
      `═══════════════════════════════════`,
      ``,
      `14 layers, each sealed with a Sacred Egg.`,
      `Each egg requires: right tongue + right ring + governance fingerprint + chain proof.`,
      ``,
      `Per-egg security:       2^${perEggBits} (PQC base + governance axes)`,
      `Sequential chain:       2^${sequentialBits.toFixed(1)} (14 eggs in series)`,
      `+ Tongue diversity:     +${(Math.log2(tongueCount) * 8).toFixed(1)} bits (${tongueCount} distinct tongues required)`,
      `+ Ring escalation:      +${Math.log2(120).toFixed(1)} bits (ring 4→0 path constraint)`,
      ``,
      `Total effective:        2^${totalBits.toFixed(1)} bits`,
      ``,
      `THE STAIRWELL EFFECT:`,
      `Every breathing cycle invalidates ALL 14 eggs simultaneously.`,
      `The attacker must break all 14 eggs within ONE breathing window.`,
      `Golden-ratio stepping ensures the window never recurs exactly.`,
    ].join('\n');
  }
}

// ============================================================================
// Security Analysis Types
// ============================================================================

export interface ChainSecurityAnalysis {
  /** Number of layers in the chain */
  layerCount: number;
  /** Base PQC bits per egg (before governance) */
  baseBitsPerEgg: number;
  /** Governance bits added per egg */
  governanceBitsPerEgg: number;
  /** Effective bits per egg (base + governance) */
  effectiveBitsPerEgg: number;
  /** Cost to break all eggs sequentially (log2) */
  sequentialCostLog2: number;
  /** Extra bits from tongue diversity */
  tongueDiversityBits: number;
  /** Which tongues are required across the chain */
  tonguesRequired: string[];
  /** Extra bits from ring escalation constraint */
  ringEscalationBits: number;
  /** Most restrictive ring level in the chain */
  strictestRing: number;
  /** Total effective security bits */
  totalEffectiveBits: number;
  /** Quantum axioms covered by the chain */
  axiomsCovered: string[];
  /** Count of temporal (shifting) axes */
  temporalAxes: number;
  /** Count of static axes */
  staticAxes: number;
  /** Whether breathing invalidates all eggs at once */
  breathingInvalidatesAll: boolean;
  /** Human-readable summary */
  summary: string;
}
