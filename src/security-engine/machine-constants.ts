/**
 * @file machine-constants.ts
 * @module security-engine/machine-constants
 * @layer All Layers
 * @component Machine Constants Registry
 *
 * Machine-science invariants used as cross-platform coordination primitives.
 *
 * These are NOT physical constants — they are machine-defined constants that
 * behave like physics-style invariants: stable across heterogeneous systems
 * (x86, ARM, FPGA), deterministic under composition, and tunable by the
 * framework to induce specific simulated behaviors.
 *
 * Categories:
 *   - Geometric: Poincare ball, hyperbolic metric parameters
 *   - Harmonic:  Scaling ratios, golden ratio weights
 *   - Temporal:  Tick rates, decay factors, window sizes
 *   - Trust:     Thresholds, exile bounds, quorum requirements
 *   - Policy:    Field strengths, gradient steepness, coupling constants
 *   - Entropy:   Noise floors, diffusion rates, decoherence thresholds
 */

// ═══════════════════════════════════════════════════════════════
// Q16.16 Fixed-Point Representation
// ═══════════════════════════════════════════════════════════════

/** Scale factor for Q16.16 fixed-point: 2^16 = 65536 */
const Q16_SCALE = 65536;

/** Convert floating-point to Q16.16 fixed-point integer */
export function toQ16(value: number): number {
  return Math.round(value * Q16_SCALE);
}

/** Convert Q16.16 fixed-point integer back to floating-point */
export function fromQ16(fixed: number): number {
  return fixed / Q16_SCALE;
}

/** Multiply two Q16.16 values: (a * b) >> 16 */
export function mulQ16(a: number, b: number): number {
  // Use intermediate 64-bit-safe math (JS numbers are 53-bit mantissa)
  return Math.round((a * b) / Q16_SCALE);
}

/** Divide two Q16.16 values: (a << 16) / b */
export function divQ16(a: number, b: number): number {
  if (b === 0) throw new RangeError('Q16 division by zero');
  return Math.round((a * Q16_SCALE) / b);
}

// ═══════════════════════════════════════════════════════════════
// Constant Categories
// ═══════════════════════════════════════════════════════════════

/** Geometric constants — Poincare ball and hyperbolic metric */
export interface GeometricConstants {
  /** Ball boundary epsilon (clamping distance from ||u|| = 1) */
  readonly poincareEpsilon: number;
  /** Audit epsilon for artanh boundary precision */
  readonly auditEpsilon: number;
  /** Embedding scaling factor alpha for tanh(alpha * ||x||) */
  readonly embeddingAlpha: number;
  /** Breathing transform bounds [min, max] */
  readonly breathingBounds: readonly [number, number];
  /** Dimensions of the Poincare ball embedding */
  readonly ballDimension: number;
}

/** Harmonic constants — scaling ratios and golden-ratio weights */
export interface HarmonicConstants {
  /** Harmonic ratio R (default 1.5 = perfect fifth) */
  readonly harmonicR: number;
  /** Golden ratio phi for tongue weighting */
  readonly phi: number;
  /** Cox constant for ML stability */
  readonly coxConstant: number;
  /** TAHS learning rate bound */
  readonly tahsBound: number;
  /** Number of sacred tongues */
  readonly tongueCount: number;
  /** Tongue weight exponents (phi^k for k = 0..5) */
  readonly tongueWeights: readonly number[];
}

/** Temporal constants — tick rates, decay, windows */
export interface TemporalConstants {
  /** Non-harmonic tick frequency in Hz (avoids grid aliasing) */
  readonly tickFrequencyHz: number;
  /** Tick period in Q16.16 fixed-point microseconds */
  readonly tickPeriodQ16: number;
  /** Intent decay rate per time window */
  readonly intentDecayRate: number;
  /** Intent accumulation window in seconds */
  readonly intentWindowSec: number;
  /** Maximum intent accumulation before hard exile */
  readonly maxIntentAccumulation: number;
  /** Triadic temporal scales: [immediate, medium, long] in seconds */
  readonly triadicScales: readonly [number, number, number];
}

/** Trust constants — thresholds and quorum rules */
export interface TrustConstants {
  /** Omega threshold for ALLOW decision */
  readonly allowThreshold: number;
  /** Omega threshold for QUARANTINE decision */
  readonly quarantineThreshold: number;
  /** Trust score below which exile rounds accumulate */
  readonly exileThreshold: number;
  /** Consecutive low-trust rounds to trigger exile */
  readonly exileRounds: number;
  /** Minimum quorum signatures for critical actions */
  readonly quorumMinSignatures: number;
  /** Role diversity requirement (distinct roles needed in quorum) */
  readonly quorumRoleDiversity: number;
}

/** Policy field constants — gradient strengths and coupling */
export interface PolicyConstants {
  /** Safety field strength (higher = steeper gradient for unsafe behavior) */
  readonly safetyFieldStrength: number;
  /** Compliance field coupling constant */
  readonly complianceFieldCoupling: number;
  /** Resource field decay rate (how fast resource constraints relax) */
  readonly resourceFieldDecay: number;
  /** Trust field viscosity (resistance to rapid trust changes) */
  readonly trustFieldViscosity: number;
  /** Role field coupling radius */
  readonly roleFieldRadius: number;
  /** Maximum simultaneous active policy fields */
  readonly maxActivePolicies: number;
}

/** Entropy constants — noise, diffusion, decoherence */
export interface EntropyConstants {
  /** Spectral noise floor for coherence checks */
  readonly spectralNoiseFloor: number;
  /** Diffusion rate for chaos-based spectral spreading */
  readonly diffusionRate: number;
  /** Decoherence threshold for quantum state validity */
  readonly decoherenceThreshold: number;
  /** Ornstein-Uhlenbeck mean reversion rate */
  readonly ouMeanReversion: number;
  /** Ornstein-Uhlenbeck volatility */
  readonly ouVolatility: number;
}

// ═══════════════════════════════════════════════════════════════
// Machine Constants Bundle
// ═══════════════════════════════════════════════════════════════

/** Complete machine constants configuration */
export interface MachineConstants {
  readonly geometric: GeometricConstants;
  readonly harmonic: HarmonicConstants;
  readonly temporal: TemporalConstants;
  readonly trust: TrustConstants;
  readonly policy: PolicyConstants;
  readonly entropy: EntropyConstants;
  /** Version string for this constant set (for audit/replay) */
  readonly version: string;
  /** SHA-256 hash of canonical JSON (computed at seal time) */
  readonly hash?: string;
}

// ═══════════════════════════════════════════════════════════════
// Default Constants (The "Physics" of Normal Operation)
// ═══════════════════════════════════════════════════════════════

const PHI = 1.618033988749895;
const TICK_HZ = 144.72; // Non-harmonic: avoids 50/60Hz grid aliasing

export const DEFAULT_GEOMETRIC: GeometricConstants = {
  poincareEpsilon: 0.01,
  auditEpsilon: 1e-15,
  embeddingAlpha: 1.0,
  breathingBounds: [0.5, 2.0] as const,
  ballDimension: 12, // 6 tongues * 2 (real/imag)
};

export const DEFAULT_HARMONIC: HarmonicConstants = {
  harmonicR: 1.5,
  phi: PHI,
  coxConstant: 0.4616321449683624, // Cox-de Boor constant
  tahsBound: 0.01,
  tongueCount: 6,
  tongueWeights: [
    1.0, // KO
    PHI, // AV  ≈ 1.618
    PHI * PHI, // RU  ≈ 2.618
    PHI ** 3, // CA  ≈ 4.236
    PHI ** 4, // UM  ≈ 6.854
    PHI ** 5, // DR  ≈ 11.090
  ] as const,
};

export const DEFAULT_TEMPORAL: TemporalConstants = {
  tickFrequencyHz: TICK_HZ,
  tickPeriodQ16: toQ16(1_000_000 / TICK_HZ), // ~6910 microseconds in Q16.16
  intentDecayRate: 0.95,
  intentWindowSec: 1.0,
  maxIntentAccumulation: 10.0,
  triadicScales: [0.1, 1.0, 10.0] as const, // 100ms, 1s, 10s
};

export const DEFAULT_TRUST: TrustConstants = {
  allowThreshold: 0.85,
  quarantineThreshold: 0.4,
  exileThreshold: 0.3,
  exileRounds: 10,
  quorumMinSignatures: 3,
  quorumRoleDiversity: 2,
};

export const DEFAULT_POLICY: PolicyConstants = {
  safetyFieldStrength: 2.0,
  complianceFieldCoupling: 1.5,
  resourceFieldDecay: 0.9,
  trustFieldViscosity: 0.8,
  roleFieldRadius: 0.5,
  maxActivePolicies: 8,
};

export const DEFAULT_ENTROPY: EntropyConstants = {
  spectralNoiseFloor: 1e-6,
  diffusionRate: 0.1,
  decoherenceThreshold: 0.01,
  ouMeanReversion: 0.15,
  ouVolatility: 0.05,
};

/** Default machine constants — the "physics" of normal, cooperative operation */
export const DEFAULT_MACHINE_CONSTANTS: MachineConstants = {
  geometric: DEFAULT_GEOMETRIC,
  harmonic: DEFAULT_HARMONIC,
  temporal: DEFAULT_TEMPORAL,
  trust: DEFAULT_TRUST,
  policy: DEFAULT_POLICY,
  entropy: DEFAULT_ENTROPY,
  version: '1.0.0',
};

// ═══════════════════════════════════════════════════════════════
// Machine Constants Registry (Mutable Singleton)
// ═══════════════════════════════════════════════════════════════

/**
 * Registry that holds the active machine constants.
 * Constants can be swapped atomically to induce different simulated behaviors.
 * All components read from this registry, ensuring cross-system consistency.
 */
export class MachineConstantsRegistry {
  private _active: MachineConstants;
  private _history: Array<{ constants: MachineConstants; timestamp: number }> = [];
  private _listeners: Array<(constants: MachineConstants) => void> = [];

  constructor(initial?: MachineConstants) {
    this._active = initial ?? { ...DEFAULT_MACHINE_CONSTANTS };
    this._history.push({ constants: this._active, timestamp: Date.now() });
  }

  /** Get the currently active constants */
  get active(): MachineConstants {
    return this._active;
  }

  /** Get Q16.16 fixed-point version of a numeric constant */
  getQ16(category: keyof MachineConstants, key: string): number {
    const cat = this._active[category];
    if (typeof cat === 'object' && cat !== null && key in cat) {
      const val = (cat as unknown as Record<string, unknown>)[key];
      if (typeof val === 'number') return toQ16(val);
    }
    throw new RangeError(`Unknown constant: ${String(category)}.${key}`);
  }

  /**
   * Atomically swap to a new set of constants.
   * This is how the framework "rewrites the physics" for different regimes.
   */
  swap(next: MachineConstants): void {
    this._active = next;
    this._history.push({ constants: next, timestamp: Date.now() });
    // Cap history at 100 entries
    if (this._history.length > 100) {
      this._history = this._history.slice(-100);
    }
    for (const listener of this._listeners) {
      listener(next);
    }
  }

  /**
   * Apply a partial override to active constants (merge).
   * Useful for tuning individual parameters without replacing everything.
   */
  tune(
    overrides: Partial<{
      geometric: Partial<GeometricConstants>;
      harmonic: Partial<HarmonicConstants>;
      temporal: Partial<TemporalConstants>;
      trust: Partial<TrustConstants>;
      policy: Partial<PolicyConstants>;
      entropy: Partial<EntropyConstants>;
    }>
  ): void {
    const merged: MachineConstants = {
      geometric: { ...this._active.geometric, ...(overrides.geometric ?? {}) },
      harmonic: { ...this._active.harmonic, ...(overrides.harmonic ?? {}) },
      temporal: { ...this._active.temporal, ...(overrides.temporal ?? {}) },
      trust: { ...this._active.trust, ...(overrides.trust ?? {}) },
      policy: { ...this._active.policy, ...(overrides.policy ?? {}) },
      entropy: { ...this._active.entropy, ...(overrides.entropy ?? {}) },
      version: this._active.version,
    };
    this.swap(merged);
  }

  /** Subscribe to constant changes */
  onSwap(listener: (constants: MachineConstants) => void): () => void {
    this._listeners.push(listener);
    return () => {
      this._listeners = this._listeners.filter((l) => l !== listener);
    };
  }

  /** Get change history (for audit trail) */
  history(): ReadonlyArray<{ constants: MachineConstants; timestamp: number }> {
    return this._history;
  }

  /** Reset to defaults */
  reset(): void {
    this.swap({ ...DEFAULT_MACHINE_CONSTANTS });
  }
}

/** Global singleton registry */
let _globalRegistry: MachineConstantsRegistry | null = null;

export function getGlobalRegistry(): MachineConstantsRegistry {
  if (!_globalRegistry) {
    _globalRegistry = new MachineConstantsRegistry();
  }
  return _globalRegistry;
}

/** Reset global registry (for testing) */
export function resetGlobalRegistry(): void {
  _globalRegistry = null;
}
