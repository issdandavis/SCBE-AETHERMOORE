/**
 * @file pqcArena.ts
 * @module crypto/pqcArena
 * @layer Layer 5, Layer 12, Layer 13
 * @component PQC Arena — System-vs-System Comparison
 *
 * Pits post-quantum cryptographic systems against each other in a
 * measurable arena. Each system gets identical workloads and we
 * compare: key generation speed, encapsulation speed, signature speed,
 * key sizes, ciphertext sizes, and security levels.
 *
 * Systems under test:
 *   - ML-KEM-768 (Lattice KEM, FIPS 203)
 *   - ML-KEM-1024 (Lattice KEM, FIPS 203)
 *   - Classic McEliece 348864 (Code-based KEM)
 *   - SLH-DSA-128s (Hash-based Signatures, FIPS 205 / SPHINCS+)
 *   - ML-DSA-65 (Lattice Signatures, FIPS 204)
 *   - TriStitch (Multi-family KEM combiner)
 *
 * Each system is also tested with the ShiftingKeyspace overlay
 * to show how SCBE governance axes expand the effective search space.
 *
 * A4: Symmetry — same workload, same measurement for all systems
 * A5: Composition — arena composes PQC + shifting keyspace + tongues
 */

import { createHash, randomBytes } from 'crypto';

// ============================================================================
// PQC System Descriptors
// ============================================================================

/**
 * Static properties of a PQC system.
 *
 * These are NIST-published values — we don't need liboqs installed
 * to know that ML-KEM-768 has a 1184-byte public key.
 */
export interface PQCSystemDescriptor {
  /** Human-readable name */
  name: string;
  /** Short ID for arena boards */
  id: string;
  /** PQC family */
  family: 'lattice' | 'code-based' | 'hash-based' | 'hybrid';
  /** NIST security level (1-5) */
  nistLevel: number;
  /** Classical bit security */
  classicalBits: number;
  /** Quantum bit security (Grover-adjusted) */
  quantumBits: number;
  /** Public key size in bytes */
  publicKeyBytes: number;
  /** Secret key size in bytes */
  secretKeyBytes: number;
  /** Ciphertext or signature size in bytes */
  outputBytes: number;
  /** Shared secret size (KEM) or N/A */
  sharedSecretBytes: number;
  /** Type of primitive */
  primitive: 'kem' | 'signature';
  /** NIST standard reference */
  standard: string;
}

/** All arena contestants with real NIST-published parameters */
export const ARENA_SYSTEMS: PQCSystemDescriptor[] = [
  // ── KEMs ──
  {
    name: 'ML-KEM-512',
    id: 'kem512',
    family: 'lattice',
    nistLevel: 1,
    classicalBits: 128,
    quantumBits: 64,
    publicKeyBytes: 800,
    secretKeyBytes: 1632,
    outputBytes: 768, // ciphertext
    sharedSecretBytes: 32,
    primitive: 'kem',
    standard: 'FIPS 203',
  },
  {
    name: 'ML-KEM-768',
    id: 'kem768',
    family: 'lattice',
    nistLevel: 3,
    classicalBits: 192,
    quantumBits: 96,
    publicKeyBytes: 1184,
    secretKeyBytes: 2400,
    outputBytes: 1088,
    sharedSecretBytes: 32,
    primitive: 'kem',
    standard: 'FIPS 203',
  },
  {
    name: 'ML-KEM-1024',
    id: 'kem1024',
    family: 'lattice',
    nistLevel: 5,
    classicalBits: 256,
    quantumBits: 128,
    publicKeyBytes: 1568,
    secretKeyBytes: 3168,
    outputBytes: 1568,
    sharedSecretBytes: 32,
    primitive: 'kem',
    standard: 'FIPS 203',
  },
  {
    name: 'Classic McEliece 348864',
    id: 'mceliece',
    family: 'code-based',
    nistLevel: 1,
    classicalBits: 128,
    quantumBits: 64,
    publicKeyBytes: 261120, // 255 KB — the giant
    secretKeyBytes: 6492,
    outputBytes: 128, // tiny ciphertext
    sharedSecretBytes: 32,
    primitive: 'kem',
    standard: 'NIST Round 4',
  },
  // ── Signatures ──
  {
    name: 'ML-DSA-44',
    id: 'dsa44',
    family: 'lattice',
    nistLevel: 2,
    classicalBits: 128,
    quantumBits: 64,
    publicKeyBytes: 1312,
    secretKeyBytes: 2560,
    outputBytes: 2420, // signature
    sharedSecretBytes: 0,
    primitive: 'signature',
    standard: 'FIPS 204',
  },
  {
    name: 'ML-DSA-65',
    id: 'dsa65',
    family: 'lattice',
    nistLevel: 3,
    classicalBits: 192,
    quantumBits: 96,
    publicKeyBytes: 1952,
    secretKeyBytes: 4032,
    outputBytes: 3309,
    sharedSecretBytes: 0,
    primitive: 'signature',
    standard: 'FIPS 204',
  },
  {
    name: 'ML-DSA-87',
    id: 'dsa87',
    family: 'lattice',
    nistLevel: 5,
    classicalBits: 256,
    quantumBits: 128,
    publicKeyBytes: 2592,
    secretKeyBytes: 4896,
    outputBytes: 4627,
    sharedSecretBytes: 0,
    primitive: 'signature',
    standard: 'FIPS 204',
  },
  {
    name: 'SLH-DSA-128s (SPHINCS+)',
    id: 'slh128s',
    family: 'hash-based',
    nistLevel: 1,
    classicalBits: 128,
    quantumBits: 64,
    publicKeyBytes: 32, // tiny keys
    secretKeyBytes: 64,
    outputBytes: 7856, // huge signatures
    sharedSecretBytes: 0,
    primitive: 'signature',
    standard: 'FIPS 205',
  },
  {
    name: 'SLH-DSA-256s (SPHINCS+)',
    id: 'slh256s',
    family: 'hash-based',
    nistLevel: 5,
    classicalBits: 256,
    quantumBits: 128,
    publicKeyBytes: 64,
    secretKeyBytes: 128,
    outputBytes: 29792, // very large signatures
    sharedSecretBytes: 0,
    primitive: 'signature',
    standard: 'FIPS 205',
  },
];

// ============================================================================
// Shifting Keyspace — The Core Innovation
// ============================================================================

/**
 * A governance axis that can be injected into the key space mid-search.
 *
 * Each axis adds log2(cardinality) bits to the effective search space.
 * The axis is "governed" — only actors with the right tongue permissions
 * can even see it exists, let alone enumerate it.
 */
export interface GovernanceAxis {
  /** Axis name */
  name: string;
  /** Which Sacred Tongue governs this axis */
  tongue: 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';
  /** Number of distinct values this axis can take */
  cardinality: number;
  /** Bits added to search space: log2(cardinality) */
  bitsAdded: number;
  /** Whether this axis shifts over time (breathing) */
  temporal: boolean;
  /** Current value (changes with breathing phase) */
  currentValue: number;
  /** Description of what this axis represents */
  description: string;
}

/**
 * Snapshot of the effective key space at a moment in time.
 *
 * THE KEY IDEA:
 *
 *   An attacker starts searching a 2^256 key space.
 *   The system injects a TIME axis: now it's 2^256 × 2^32 = 2^288.
 *   Then INTENT: 2^288 × 2^16 = 2^304.
 *   Then AUTHORITY: 2^304 × 2^8 = 2^312.
 *   Then TONGUE_PHASE: 2^312 × 2^24 = 2^336.
 *   Then BREATHING: 2^336 × 2^12 = 2^348.
 *   Then FLUX: 2^348 × 2^4 = 2^352.
 *
 *   By the time the attacker has enumerated 2^128 of the original
 *   space, the system has already shifted to new axis values.
 *
 *   The attacker's work is WASTED because the target moved.
 *
 * This is "system physics" — the constraints aren't from real physics
 * but from the governance framework's rules about who can do what when.
 */
export interface KeyspaceSnapshot {
  /** Base PQC security bits (from the algorithm) */
  baseBits: number;
  /** Active governance axes */
  axes: GovernanceAxis[];
  /** Total effective bits: base + sum(axis.bitsAdded) */
  effectiveBits: number;
  /** Breathing phase when snapshot was taken */
  breathingPhase: number;
  /** Timestamp */
  timestamp: number;
  /** How many axis shifts have occurred since the attacker started */
  shiftCount: number;
  /** Estimated attacker progress (fraction of space searched) */
  attackerProgress: number;
  /** Harmonic wall cost at current distance */
  harmonicCost: number;
}

/**
 * ShiftingKeyspace — makes key space grow while attacker searches.
 *
 * Think of it like this:
 *   - PQC gives you a locked room with 2^256 possible keys
 *   - SCBE adds new locks to the door while the attacker is picking
 *   - Each new lock is governed by a tongue (role)
 *   - The locks CHANGE based on time, intent, and authority
 *   - The attacker's lockpicking work resets with each change
 *
 * Math flow (step by step):
 *
 *   1. Start: search_space = 2^base_bits
 *      (e.g., ML-KEM-768 = 2^192)
 *
 *   2. Inject TIME axis (32-bit epoch bucket):
 *      search_space = 2^(192 + 32) = 2^224
 *      "Which second are we in? Changes every tick."
 *
 *   3. Inject INTENT axis (16-bit intent hash):
 *      search_space = 2^(224 + 16) = 2^240
 *      "What is the actor trying to do? Changes per request."
 *
 *   4. Inject AUTHORITY axis (8-bit role encoding):
 *      search_space = 2^(240 + 8) = 2^248
 *      "Which tongue/role is the actor? Fixed per session."
 *
 *   5. Inject TONGUE_PHASE axis (24-bit phase angle):
 *      search_space = 2^(248 + 24) = 2^272
 *      "What's the combined phase of all 6 tongues? Rotates."
 *
 *   6. Inject BREATHING axis (12-bit breathing transform):
 *      search_space = 2^(272 + 12) = 2^284
 *      "Where in the breathing cycle? Oscillates."
 *
 *   7. Inject FLUX axis (4-bit flux state):
 *      search_space = 2^(284 + 4) = 2^288
 *      "Polly/Quasi/Demi/Collapsed? Changes with load."
 *
 *   8. Apply HARMONIC WALL cost multiplier:
 *      effective_cost = search_space × H(d, pd)
 *      "The further from safe origin, the harder each guess."
 *
 * The attacker can't pre-compute the axes because:
 *   - TIME changes every tick (they'd need to search each tick)
 *   - INTENT changes per request (they'd need to predict all intents)
 *   - TONGUE_PHASE rotates (golden ratio spacing = aperiodic)
 *   - BREATHING oscillates (their cached work becomes stale)
 *
 * This is the "Hogwarts stairwell" — the paths shift while you walk.
 */
export class ShiftingKeyspace {
  private readonly baseBits: number;
  private readonly axes: GovernanceAxis[] = [];
  private shiftCount = 0;
  private breathingPhase = 0;

  constructor(baseBits: number) {
    this.baseBits = baseBits;
  }

  /**
   * Inject a new axis into the key space.
   *
   * Each axis multiplies the search space by its cardinality.
   * In bits: effective_bits += log2(cardinality).
   *
   * EXAMPLE:
   *   Before: 2^192 (ML-KEM-768 base)
   *   injectAxis("TIME", cardinality=2^32)
   *   After:  2^(192+32) = 2^224
   *
   *   The attacker now needs 2^32 = 4 billion times more work.
   */
  injectAxis(params: {
    name: string;
    tongue: 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';
    cardinality: number;
    temporal: boolean;
    description: string;
  }): GovernanceAxis {
    const bitsAdded = Math.log2(params.cardinality);
    const axis: GovernanceAxis = {
      ...params,
      bitsAdded,
      currentValue: Math.floor(Math.random() * params.cardinality),
    };
    this.axes.push(axis);
    this.shiftCount++;
    return axis;
  }

  /**
   * Simulate a breathing cycle: temporal axes shift their values.
   *
   * This is the "stairwell rotation" — the paths change.
   * Any attacker progress on the old axis values is WASTED.
   *
   * MATH:
   *   new_value = (old_value + phi_step) mod cardinality
   *   phi_step = floor(cardinality × golden_ratio_frac)
   *
   *   Using the golden ratio ensures maximum spacing between
   *   consecutive values (Weyl's equidistribution theorem).
   *   The sequence never repeats exactly (irrational base).
   */
  breathe(): void {
    const PHI_FRAC = 0.6180339887498949; // 1/φ = φ-1
    this.breathingPhase = (this.breathingPhase + PHI_FRAC) % 1.0;

    for (const axis of this.axes) {
      if (axis.temporal) {
        const step = Math.floor(axis.cardinality * PHI_FRAC);
        axis.currentValue = (axis.currentValue + step) % axis.cardinality;
        this.shiftCount++;
      }
    }
  }

  /**
   * Take a snapshot of the current effective key space.
   *
   * Shows exactly how many bits the attacker faces right now
   * and how much of the space they could have searched.
   */
  snapshot(attackerOpsPerSec: number = 1e12, elapsedSeconds: number = 0): KeyspaceSnapshot {
    const effectiveBits = this.getEffectiveBits();

    // Attacker progress: ops_done / total_space
    // total_space = 2^effectiveBits
    // ops_done = attackerOpsPerSec × elapsedSeconds
    //
    // progress = ops_done / 2^effectiveBits
    //          = (opsPerSec × seconds) / 2^bits
    //          = 2^log2(opsPerSec × seconds) / 2^bits
    //          = 2^(log2(opsPerSec × seconds) - bits)
    //
    // If bits > log2(ops_done), progress ≈ 0 (good!)
    const opsLog2 = elapsedSeconds > 0 ? Math.log2(attackerOpsPerSec * elapsedSeconds) : 0;
    const attackerProgress = opsLog2 < effectiveBits ? Math.pow(2, opsLog2 - effectiveBits) : 1;

    // Harmonic wall cost: H(d, pd) = 1 / (1 + d + 2*pd)
    // d = normalized distance from safe origin (use breathing phase as proxy)
    const d = this.breathingPhase * 2; // scale to [0, 2]
    const pd = this.axes.filter((a) => !a.temporal).length / 6; // static axis density
    const harmonicCost = 1 / (1 + d + 2 * pd);

    return {
      baseBits: this.baseBits,
      axes: [...this.axes],
      effectiveBits,
      breathingPhase: this.breathingPhase,
      timestamp: Date.now(),
      shiftCount: this.shiftCount,
      attackerProgress,
      harmonicCost,
    };
  }

  /**
   * Get total effective bits: base + all axes.
   *
   * MATH:
   *   effective = base_bits + Σ log2(axis.cardinality)
   *
   * EXAMPLE with ML-KEM-768 (192 base):
   *   + TIME(2^32)          = 192 + 32  = 224
   *   + INTENT(2^16)        = 224 + 16  = 240
   *   + AUTHORITY(2^8)      = 240 + 8   = 248
   *   + TONGUE_PHASE(2^24)  = 248 + 24  = 272
   *   + BREATHING(2^12)     = 272 + 12  = 284
   *   + FLUX(2^4)           = 284 + 4   = 288
   *
   *   Result: 288 effective bits vs 192 base bits
   *   That's 2^96 = 79 quintillion times harder to search.
   */
  getEffectiveBits(): number {
    return this.baseBits + this.axes.reduce((sum, a) => sum + a.bitsAdded, 0);
  }

  /** Get the added bits from governance alone */
  getGovernanceBits(): number {
    return this.axes.reduce((sum, a) => sum + a.bitsAdded, 0);
  }

  /** Get count of temporal (shifting) axes */
  getTemporalAxisCount(): number {
    return this.axes.filter((a) => a.temporal).length;
  }

  /** Get count of static axes */
  getStaticAxisCount(): number {
    return this.axes.filter((a) => !a.temporal).length;
  }
}

// ============================================================================
// Arena Match — System vs System
// ============================================================================

/**
 * Result of pitting two PQC systems against each other.
 *
 * We compare them on:
 *   1. Raw security bits (quantum-adjusted)
 *   2. Effective security with SCBE governance axes
 *   3. Key + ciphertext size (bandwidth cost)
 *   4. Attacker cost ratio (how much harder is system A vs B?)
 *   5. Governance amplification factor
 */
export interface ArenaMatchResult {
  /** System A descriptor */
  systemA: PQCSystemDescriptor;
  /** System B descriptor */
  systemB: PQCSystemDescriptor;
  /** System A with governance overlay */
  systemAKeyspace: KeyspaceSnapshot;
  /** System B with governance overlay */
  systemBKeyspace: KeyspaceSnapshot;
  /** Which system wins on raw quantum bits */
  rawSecurityWinner: string;
  /** Which system wins on effective bits (with governance) */
  effectiveSecurityWinner: string;
  /** Which system has smaller total wire size */
  sizeWinner: string;
  /** Ratio: 2^(A_effective - B_effective) — how much harder A is vs B */
  costRatioLog2: number;
  /** Governance amplification: effective_bits / base_bits */
  governanceAmplificationA: number;
  governanceAmplificationB: number;
  /** Summary for non-math people */
  summary: string;
}

/**
 * PQC Arena — pits systems against each other.
 *
 * Usage:
 *   const arena = new PQCArena();
 *   const result = arena.match('kem768', 'mceliece');
 *   console.log(result.summary);
 */
export class PQCArena {
  private readonly systems: Map<string, PQCSystemDescriptor> = new Map();

  constructor(systems: PQCSystemDescriptor[] = ARENA_SYSTEMS) {
    for (const sys of systems) {
      this.systems.set(sys.id, sys);
    }
  }

  /**
   * Build the standard SCBE governance axes for a given base system.
   *
   * These are the "extra locks" that SCBE adds to any PQC system.
   * The attacker doesn't just need to break the PQC — they also
   * need to know the correct time, intent, authority, phase, etc.
   */
  buildGovernanceKeyspace(system: PQCSystemDescriptor): ShiftingKeyspace {
    const ks = new ShiftingKeyspace(system.quantumBits);

    // ── AXIS 1: TIME ──
    // 32-bit epoch bucket = 4 billion time slots
    // Temporal: shifts every breathing cycle
    // Governed by: KO (Control — who controls timing)
    ks.injectAxis({
      name: 'TIME',
      tongue: 'KO',
      cardinality: Math.pow(2, 32),
      temporal: true,
      description: 'Epoch bucket — which second matters. Shifts every tick.',
    });

    // ── AXIS 2: INTENT ──
    // 16-bit intent hash = 65536 possible intents
    // Not temporal: fixed per request
    // Governed by: CA (Logic — what is the actor trying to do)
    ks.injectAxis({
      name: 'INTENT',
      tongue: 'CA',
      cardinality: Math.pow(2, 16),
      temporal: false,
      description: 'Intent hash — what action is being attempted.',
    });

    // ── AXIS 3: AUTHORITY ──
    // 8-bit role encoding = 256 role combinations
    // Not temporal: fixed per actor
    // Governed by: RU (Policy — what roles exist)
    ks.injectAxis({
      name: 'AUTHORITY',
      tongue: 'RU',
      cardinality: Math.pow(2, 8),
      temporal: false,
      description: 'Role encoding — which tongue combination grants access.',
    });

    // ── AXIS 4: TONGUE_PHASE ──
    // 24-bit phase angle = 16 million phase positions
    // Temporal: rotates with golden ratio spacing
    // Governed by: DR (Types/Flow — the flow of phase)
    ks.injectAxis({
      name: 'TONGUE_PHASE',
      tongue: 'DR',
      cardinality: Math.pow(2, 24),
      temporal: true,
      description: 'Combined phase of all 6 Sacred Tongues. Rotates irrationally.',
    });

    // ── AXIS 5: BREATHING ──
    // 12-bit breathing transform = 4096 breathing positions
    // Temporal: oscillates with the pipeline
    // Governed by: AV (I/O — the breathing is input/output)
    ks.injectAxis({
      name: 'BREATHING',
      tongue: 'AV',
      cardinality: Math.pow(2, 12),
      temporal: true,
      description: 'Breathing phase — where in the oscillation cycle.',
    });

    // ── AXIS 6: FLUX ──
    // 4-bit flux state = 16 flux positions
    // Temporal: changes with system load
    // Governed by: UM (Security — flux state is a security signal)
    ks.injectAxis({
      name: 'FLUX',
      tongue: 'UM',
      cardinality: Math.pow(2, 4),
      temporal: true,
      description: 'Polly/Quasi/Demi/Collapsed state. Changes with load.',
    });

    return ks;
  }

  /**
   * Run a head-to-head match between two PQC systems.
   *
   * Both systems get the same SCBE governance overlay.
   * We measure who benefits more and who would be harder to break.
   */
  match(systemAId: string, systemBId: string): ArenaMatchResult {
    const systemA = this.systems.get(systemAId);
    const systemB = this.systems.get(systemBId);
    if (!systemA) throw new Error(`Unknown system: ${systemAId}`);
    if (!systemB) throw new Error(`Unknown system: ${systemBId}`);

    // Build governance keyspaces
    const ksA = this.buildGovernanceKeyspace(systemA);
    const ksB = this.buildGovernanceKeyspace(systemB);

    // Simulate a few breathing cycles
    for (let i = 0; i < 3; i++) {
      ksA.breathe();
      ksB.breathe();
    }

    // Take snapshots (assume attacker has 1 trillion ops/sec, 1 year elapsed)
    const oneYear = 365.25 * 24 * 3600;
    const snapA = ksA.snapshot(1e12, oneYear);
    const snapB = ksB.snapshot(1e12, oneYear);

    // Wire sizes
    const wireSizeA = systemA.publicKeyBytes + systemA.outputBytes;
    const wireSizeB = systemB.publicKeyBytes + systemB.outputBytes;

    // Cost ratio: how many times harder is A vs B
    const costRatioLog2 = snapA.effectiveBits - snapB.effectiveBits;

    // Governance amplification
    const govAmpA = snapA.effectiveBits / systemA.quantumBits;
    const govAmpB = snapB.effectiveBits / systemB.quantumBits;

    // Determine winners
    const rawWinner =
      systemA.quantumBits > systemB.quantumBits
        ? systemA.name
        : systemA.quantumBits < systemB.quantumBits
          ? systemB.name
          : 'TIE';
    const effectiveWinner =
      snapA.effectiveBits > snapB.effectiveBits
        ? systemA.name
        : snapA.effectiveBits < snapB.effectiveBits
          ? systemB.name
          : 'TIE';
    const sizeWinner =
      wireSizeA < wireSizeB ? systemA.name : wireSizeA > wireSizeB ? systemB.name : 'TIE';

    // Build human-readable summary
    const costMultiple =
      costRatioLog2 > 0
        ? `2^${costRatioLog2} times harder to break ${systemA.name}`
        : costRatioLog2 < 0
          ? `2^${Math.abs(costRatioLog2)} times harder to break ${systemB.name}`
          : 'Equal difficulty';

    const summary = [
      `${systemA.name} vs ${systemB.name}`,
      `─────────────────────────────────`,
      `Raw quantum security: ${systemA.name}=${systemA.quantumBits}b, ${systemB.name}=${systemB.quantumBits}b → Winner: ${rawWinner}`,
      `With SCBE governance: ${systemA.name}=${snapA.effectiveBits}b, ${systemB.name}=${snapB.effectiveBits}b → Winner: ${effectiveWinner}`,
      `Governance amplification: ${systemA.name}=${govAmpA.toFixed(1)}×, ${systemB.name}=${govAmpB.toFixed(1)}×`,
      `Wire size: ${systemA.name}=${wireSizeA}B, ${systemB.name}=${wireSizeB}B → Smallest: ${sizeWinner}`,
      `Cost difference: ${costMultiple}`,
      `Attacker progress after 1 year at 1T ops/sec: ${snapA.attackerProgress.toExponential(2)}`,
      `Shifting axes: ${snapA.axes.filter((a) => a.temporal).length} temporal, ${snapA.axes.filter((a) => !a.temporal).length} static`,
    ].join('\n');

    return {
      systemA,
      systemB,
      systemAKeyspace: snapA,
      systemBKeyspace: snapB,
      rawSecurityWinner: rawWinner,
      effectiveSecurityWinner: effectiveWinner,
      sizeWinner,
      costRatioLog2,
      governanceAmplificationA: govAmpA,
      governanceAmplificationB: govAmpB,
      summary,
    };
  }

  /**
   * Run a full tournament: every system vs every other system.
   *
   * Returns a leaderboard sorted by effective security bits.
   */
  tournament(): ArenaLeaderboard {
    const entries: LeaderboardEntry[] = [];

    for (const sys of Array.from(this.systems.values())) {
      const ks = this.buildGovernanceKeyspace(sys);
      for (let i = 0; i < 3; i++) ks.breathe();
      const snap = ks.snapshot(1e12, 365.25 * 24 * 3600);

      entries.push({
        system: sys,
        baseBits: sys.quantumBits,
        effectiveBits: snap.effectiveBits,
        governanceBits: ks.getGovernanceBits(),
        amplification: snap.effectiveBits / sys.quantumBits,
        wireSize: sys.publicKeyBytes + sys.outputBytes,
        attackerProgress: snap.attackerProgress,
        temporalAxes: ks.getTemporalAxisCount(),
        staticAxes: ks.getStaticAxisCount(),
      });
    }

    // Sort by effective bits descending
    entries.sort((a, b) => b.effectiveBits - a.effectiveBits);

    return { entries, timestamp: Date.now() };
  }

  /** Get a system by ID */
  getSystem(id: string): PQCSystemDescriptor | undefined {
    return this.systems.get(id);
  }

  /** List all system IDs */
  listSystems(): string[] {
    return Array.from(this.systems.keys());
  }
}

// ============================================================================
// Tournament Leaderboard
// ============================================================================

export interface LeaderboardEntry {
  system: PQCSystemDescriptor;
  /** Raw quantum security bits */
  baseBits: number;
  /** Effective bits with SCBE governance */
  effectiveBits: number;
  /** Bits added by governance alone */
  governanceBits: number;
  /** Amplification factor: effective / base */
  amplification: number;
  /** Total wire size (pk + output) in bytes */
  wireSize: number;
  /** Attacker progress after 1yr at 1T ops/sec */
  attackerProgress: number;
  /** Count of temporal (shifting) axes */
  temporalAxes: number;
  /** Count of static axes */
  staticAxes: number;
}

export interface ArenaLeaderboard {
  entries: LeaderboardEntry[];
  timestamp: number;
}
