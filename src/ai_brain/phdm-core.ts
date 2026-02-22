/**
 * @file phdm-core.ts
 * @module ai_brain/phdm-core
 * @layer Layer 6, Layer 8, Layer 11, Layer 13
 * @component Complete PHDM Core Integration
 * @version 1.0.0
 * @since 2026-02-08
 *
 * Integrates the full Polyhedral Hamiltonian Defense Manifold:
 * 1. Hamiltonian path with HMAC-chained keys (harmonic/phdm.ts)
 * 2. Kyber KEM K₀ seed derivation (crypto/pqc.ts + crypto/hkdf.ts)
 * 3. Geodesic monitoring with intrusion detection (snap threshold ε)
 * 4. 6D Langues space decomposition (4D intent + 2D temporal)
 * 5. Langues metric cost computation (exponential cost function)
 * 6. Flux state evolution driven by intrusion results
 *
 * Fills the gaps identified in the architecture review:
 * - K₀ = HKDF(HMAC(ss, intent || epoch), "PHDM-K0-v1", "phdm-hamiltonian-seed")
 * - 6D → (4D intent + 2D temporal) decomposition table
 * - PHDM geodesic monitoring wired into brain-integration pipeline
 * - Numerical intrusion detection with false-positive analysis
 */

import * as crypto from 'crypto';
import {
  PHDMHamiltonianPath,
  PHDMDeviationDetector,
  CANONICAL_POLYHEDRA,
  computeCentroid,
  distance6D,
  type Point6D,
  type IntrusionResult,
  type Polyhedron,
} from '../harmonic/phdm.js';
import { hkdfSha256 } from '../crypto/hkdf.js';
import { FluxStateManager, type AgentFluxRecord } from './flux-states.js';
import { type ImmuneState } from './immune-response.js';
import { PHI } from './types.js';

// ═══════════════════════════════════════════════════════════════
// 6D Langues Space Decomposition
// ═══════════════════════════════════════════════════════════════

/**
 * The 6 Sacred Tongue dimensions mapped to semantic roles.
 *
 * Intent Space (4D):
 *   KO (x1) - Trust boundary: Kor'Aelin, boundaries of truth
 *   AV (x2) - Ethical alignment: Avali, ethical resonance
 *   RU (x3) - Runethic logic: logic gate patterns
 *   CA (x4) - Causal integrity: cause-effect chains
 *
 * Temporal Space (2D):
 *   UM (x5) - Memory/temporal coherence: Umbroth, deep memory
 *   DR (x6) - Predictive state: Draumric, dream/forecast
 */
export interface LanguesDecomposition {
  /** 4D intent subspace [KO, AV, RU, CA] */
  intent: [number, number, number, number];
  /** 2D temporal subspace [UM, DR] */
  temporal: [number, number];
  /** Full 6D vector */
  full: Point6D;
}

export const TONGUE_LABELS = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'] as const;
export const INTENT_TONGUES = ['KO', 'AV', 'RU', 'CA'] as const;
export const TEMPORAL_TONGUES = ['UM', 'DR'] as const;

/**
 * Decompose a 6D Langues space point into intent + temporal subspaces.
 */
export function decomposeLangues(point: Point6D): LanguesDecomposition {
  return {
    intent: [point.x1, point.x2, point.x3, point.x4],
    temporal: [point.x5, point.x6],
    full: point,
  };
}

/**
 * Map 21D brain state vector to 6D Langues space.
 *
 * Uses the SCBE context (first 6D) as Langues coordinates:
 *   x1 (KO) = deviceTrust       (trust boundary)
 *   x2 (AV) = locationTrust     (ethical/spatial alignment)
 *   x3 (RU) = networkTrust      (logical connectivity)
 *   x4 (CA) = behaviorScore     (causal behavior)
 *   x5 (UM) = timeOfDay         (temporal coherence)
 *   x6 (DR) = intentAlignment   (predictive state)
 */
export function brainStateToLangues(state21D: number[]): Point6D {
  if (state21D.length < 6) {
    throw new Error(`Expected at least 6 dimensions, got ${state21D.length}`);
  }
  return {
    x1: state21D[0],
    x2: state21D[1],
    x3: state21D[2],
    x4: state21D[3],
    x5: state21D[4],
    x6: state21D[5],
  };
}

// ═══════════════════════════════════════════════════════════════
// K₀ Derivation from Kyber KEM
// ═══════════════════════════════════════════════════════════════

/**
 * K₀ derivation parameters
 */
export interface K0DerivationParams {
  /** ML-KEM-768 shared secret (32 bytes) */
  sharedSecret: Uint8Array;
  /** Intent fingerprint (agent-specific identifier) */
  intentFingerprint: string;
  /** Epoch counter for temporal binding */
  epoch: number;
}

/**
 * Derive K₀ from Kyber KEM shared secret.
 *
 * K₀ = HKDF-SHA256(
 *   ikm = HMAC-SHA256(ss, intent_fingerprint || epoch),
 *   salt = "PHDM-K0-v1",
 *   info = "phdm-hamiltonian-seed",
 *   len = 32
 * )
 *
 * Binds the PHDM Hamiltonian path seed to:
 * 1. Post-quantum shared secret (quantum resistance)
 * 2. Agent's intent fingerprint (identity binding)
 * 3. Epoch (temporal freshness)
 */
export function deriveK0(params: K0DerivationParams): Buffer {
  const epochBytes = Buffer.alloc(8);
  epochBytes.writeBigUInt64BE(BigInt(params.epoch));

  const hmac = crypto.createHmac('sha256', Buffer.from(params.sharedSecret));
  hmac.update(Buffer.from(params.intentFingerprint, 'utf-8'));
  hmac.update(epochBytes);
  const ikm = hmac.digest();

  const salt = Buffer.from('PHDM-K0-v1', 'utf-8');
  const info = Buffer.from('phdm-hamiltonian-seed', 'utf-8');

  return hkdfSha256(ikm, salt, info, 32);
}

// ═══════════════════════════════════════════════════════════════
// PHDM Monitor Result
// ═══════════════════════════════════════════════════════════════

/**
 * Result from PHDM monitoring pipeline
 */
export interface PHDMMonitorResult {
  /** Intrusion detection result */
  intrusion: IntrusionResult;
  /** Langues space decomposition */
  langues: LanguesDecomposition;
  /** Langues metric cost */
  languesCost: number;
  /** Langues risk decision */
  languesDecision: 'ALLOW' | 'QUARANTINE' | 'DENY';
  /** Current Hamiltonian path step (which polyhedron) */
  hamiltonianStep: number;
  /** Name of current polyhedron */
  currentPolyhedron: string;
  /** HMAC key fingerprint at current step (first 16 hex chars) */
  keyFingerprint: string;
  /** Whether this state triggers PHDM escalation */
  phdmEscalation: boolean;
  /** Accumulated intrusion count */
  intrusionCount: number;
  /** Running rhythm pattern (last 16 bits) */
  rhythmPattern: string;
}

// ═══════════════════════════════════════════════════════════════
// PHDM Core Configuration
// ═══════════════════════════════════════════════════════════════

export interface PHDMCoreConfig {
  /** Snap threshold for geodesic deviation ε_snap (default: 0.1) */
  snapThreshold: number;
  /** Curvature threshold for intrusion (default: 0.5) */
  curvatureThreshold: number;
  /** Langues metric beta base (default: 1.0) */
  languesBetaBase: number;
  /** Langues metric risk thresholds [low, high] */
  languesRiskThresholds: [number, number];
  /** Maximum intrusions before forced DENY */
  maxIntrusionsBeforeDeny: number;
  /** Intrusion rate threshold for escalation */
  intrusionRateThreshold: number;
  /** Hex-encoded 32-byte master key for PHDM initialization (optional — use initializeWithKey) */
  masterKeyHex?: string;
}

export const DEFAULT_PHDM_CORE_CONFIG: PHDMCoreConfig = {
  snapThreshold: 0.1,
  curvatureThreshold: 0.5,
  languesBetaBase: 1.0,
  languesRiskThresholds: [1.0, 10.0],
  maxIntrusionsBeforeDeny: 5,
  intrusionRateThreshold: 0.3,
};

// ═══════════════════════════════════════════════════════════════
// PHDM Core
// ═══════════════════════════════════════════════════════════════

/**
 * Complete PHDM Core Integration
 *
 * Unifies:
 * 1. Hamiltonian path with HMAC-chained keys through 16 polyhedra
 * 2. Kyber KEM K₀ seed derivation (post-quantum binding)
 * 3. Geodesic monitoring with intrusion detection (snap threshold)
 * 4. 6D Langues space decomposition (4D intent + 2D temporal)
 * 5. Langues metric cost computation (exponential cost scaling)
 * 6. Flux state integration (intrusions penalize flux)
 *
 * The PHDM Core bridges the post-quantum key hierarchy
 * with the topological defense manifold and the Langues cost surface.
 */
export class PHDMCore {
  private readonly config: PHDMCoreConfig;
  private readonly hamiltonianPath: PHDMHamiltonianPath;
  private readonly detector: PHDMDeviationDetector;
  private pathKeys: Buffer[] = [];
  private k0: Buffer | null = null;
  private currentStep: number = 0;
  private totalSteps: number = 0;
  private intrusionCount: number = 0;
  private rhythmBits: string[] = [];

  private readonly languesWeights: number[];
  private readonly languesPhases: number[];
  private readonly languesBetas: number[];

  constructor(config: Partial<PHDMCoreConfig> = {}) {
    this.config = { ...DEFAULT_PHDM_CORE_CONFIG, ...config };
    this.hamiltonianPath = new PHDMHamiltonianPath(CANONICAL_POLYHEDRA);
    this.detector = new PHDMDeviationDetector(
      CANONICAL_POLYHEDRA,
      this.config.snapThreshold,
      this.config.curvatureThreshold
    );

    // Langues metric parameters (matching languesMetric.ts)
    this.languesWeights = Array.from({ length: 6 }, (_, i) => Math.pow(PHI, i));
    this.languesPhases = Array.from({ length: 6 }, (_, i) => (2 * Math.PI * i) / 6);
    this.languesBetas = Array.from(
      { length: 6 },
      (_, i) => this.config.languesBetaBase * Math.pow(PHI, i * 0.5)
    );
  }

  /**
   * Initialize from Kyber KEM shared secret.
   * Derives K₀ and computes the full Hamiltonian path.
   */
  initializeFromKyber(params: K0DerivationParams): void {
    this.k0 = deriveK0(params);
    this.pathKeys = this.hamiltonianPath.computePath(this.k0);
    this.resetMonitoring();
  }

  /**
   * Initialize with a raw master key (testing or non-Kyber contexts).
   */
  initializeWithKey(masterKey: Buffer): void {
    this.k0 = masterKey;
    this.pathKeys = this.hamiltonianPath.computePath(masterKey);
    this.resetMonitoring();
  }

  /** Get the derived K₀ */
  getK0(): Buffer | null {
    return this.k0;
  }

  /** Get path key at a specific step */
  getPathKey(step: number): Buffer | null {
    return this.hamiltonianPath.getKey(step);
  }

  /** Verify HMAC chain integrity */
  verifyChainIntegrity(): boolean {
    if (!this.k0 || this.pathKeys.length === 0) return false;
    const finalKey = this.pathKeys[this.pathKeys.length - 1];
    return this.hamiltonianPath.verifyPath(this.k0, finalKey);
  }

  /**
   * Monitor an agent's state through the PHDM geodesic.
   *
   * Takes a 21D brain state, maps to 6D Langues space,
   * checks geodesic deviation, computes Langues cost.
   *
   * @param state21D - 21D brain state vector
   * @param t - Normalized time parameter [0, 1]
   */
  monitor(state21D: number[], t: number): PHDMMonitorResult {
    if (!this.k0) {
      throw new Error(
        'PHDM Core not initialized. Call initializeFromKyber() or initializeWithKey() first.'
      );
    }

    // Map 21D → 6D Langues space
    const langues6D = brainStateToLangues(state21D);
    const decomposition = decomposeLangues(langues6D);

    // Geodesic intrusion detection
    const intrusion = this.detector.detect(langues6D, t);

    // Track intrusions
    this.totalSteps++;
    if (intrusion.isIntrusion) {
      this.intrusionCount++;
    }
    this.rhythmBits.push(intrusion.rhythmPattern);
    if (this.rhythmBits.length > 16) {
      this.rhythmBits.shift();
    }

    // Langues metric cost
    const languesCost = this.computeLanguesCost(langues6D, t);
    const languesDecision = this.evaluateLanguesRisk(languesCost);

    // Hamiltonian step (which polyhedron)
    const hamiltonianStep = Math.min(
      Math.floor(t * CANONICAL_POLYHEDRA.length),
      CANONICAL_POLYHEDRA.length - 1
    );
    this.currentStep = hamiltonianStep;

    // Key fingerprint for audit
    const stepKey = this.pathKeys[hamiltonianStep + 1] || this.pathKeys[0];
    const keyFingerprint = stepKey.toString('hex').slice(0, 16);

    // PHDM escalation check
    const intrusionRate =
      this.totalSteps > 0 ? this.intrusionCount / this.totalSteps : 0;
    const phdmEscalation =
      this.intrusionCount >= this.config.maxIntrusionsBeforeDeny ||
      (this.totalSteps >= 5 && intrusionRate > this.config.intrusionRateThreshold);

    return {
      intrusion,
      langues: decomposition,
      languesCost,
      languesDecision,
      hamiltonianStep,
      currentPolyhedron: CANONICAL_POLYHEDRA[hamiltonianStep]?.name ?? 'unknown',
      keyFingerprint,
      phdmEscalation,
      intrusionCount: this.intrusionCount,
      rhythmPattern: this.rhythmBits.join(''),
    };
  }

  /**
   * Compute the Langues metric cost at a 6D point.
   * L(x,t) = Σ wₗ exp(βₗ · (dₗ + sin(ωₗt + φₗ)))
   */
  computeLanguesCost(point: Point6D, t: number): number {
    const arr = [point.x1, point.x2, point.x3, point.x4, point.x5, point.x6];
    let L = 0;
    for (let i = 0; i < 6; i++) {
      const omega = i + 1;
      const sinTerm = Math.sin(omega * t + this.languesPhases[i]);
      const exponent = this.languesBetas[i] * (arr[i] + sinTerm);
      L += this.languesWeights[i] * Math.exp(exponent);
    }
    return L;
  }

  /** Evaluate Langues risk decision from cost value */
  evaluateLanguesRisk(cost: number): 'ALLOW' | 'QUARANTINE' | 'DENY' {
    const [low, high] = this.config.languesRiskThresholds;
    if (cost < low) return 'ALLOW';
    if (cost < high) return 'QUARANTINE';
    return 'DENY';
  }

  /** Get intrusion statistics */
  getStats(): {
    totalSteps: number;
    intrusionCount: number;
    intrusionRate: number;
    currentHamiltonianStep: number;
    currentPolyhedron: string;
    rhythmPattern: string;
    chainIntact: boolean;
  } {
    return {
      totalSteps: this.totalSteps,
      intrusionCount: this.intrusionCount,
      intrusionRate: this.totalSteps > 0 ? this.intrusionCount / this.totalSteps : 0,
      currentHamiltonianStep: this.currentStep,
      currentPolyhedron: CANONICAL_POLYHEDRA[this.currentStep]?.name ?? 'unknown',
      rhythmPattern: this.rhythmBits.join(''),
      chainIntact: this.verifyChainIntegrity(),
    };
  }

  /** Reset monitoring state (keeps keys) */
  resetMonitoring(): void {
    this.currentStep = 0;
    this.totalSteps = 0;
    this.intrusionCount = 0;
    this.rhythmBits = [];
  }

  /** Get the 16 canonical polyhedra */
  getPolyhedra(): Polyhedron[] {
    return [...CANONICAL_POLYHEDRA];
  }

  /**
   * Apply PHDM monitoring result to flux state evolution.
   *
   * Intrusions penalize flux value → agent loses access to higher polyhedra.
   * Creates feedback loop: deviation → intrusion → flux penalty → reduced access.
   */
  applyToFlux(
    fluxManager: FluxStateManager,
    agentId: string,
    monitorResult: PHDMMonitorResult,
    immuneState: ImmuneState
  ): AgentFluxRecord {
    // Use deviation-only logic for flux trust (not isIntrusion which includes curvature).
    // Curvature measures the geodesic's own shape; deviation measures the agent's
    // distance FROM the geodesic. Only deviation is actionable for trust scoring.
    const deviation = monitorResult.intrusion.deviation;
    let phdmTrust: number;
    if (deviation > this.config.snapThreshold) {
      // Agent is OFF the geodesic → penalize proportionally
      const normalizedDeviation = Math.min(
        deviation / (this.config.snapThreshold * 10),
        1
      );
      phdmTrust = Math.max(0, 0.3 * (1 - normalizedDeviation));
    } else {
      // Agent is ON the geodesic → high trust
      const normalizedDeviation = deviation / this.config.snapThreshold;
      phdmTrust = 0.8 + 0.2 * (1 - Math.min(normalizedDeviation, 1));
    }

    if (monitorResult.phdmEscalation) {
      phdmTrust = 0;
    }

    return fluxManager.evolve(agentId, phdmTrust, immuneState);
  }
}
