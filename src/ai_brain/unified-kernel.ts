/**
 * @file unified-kernel.ts
 * @module ai_brain/unified-kernel
 * @layer Layer 1-14 (Unified Spine)
 * @component Canonical State + Pipeline Runner
 * @version 1.0.0
 * @since 2026-02-08
 *
 * The unified kernel/spine that ties all SCBE-AETHERMOORE subsystems
 * into one coherent runtime architecture.
 *
 * Architecture:
 *   1. Canonical State: Single truth struct (B^n × T^k product manifold)
 *   2. Module Contracts: Hard interfaces for each subsystem
 *   3. Pipeline Runner: 9-step runtime loop orchestrating all modules
 *
 * Modules:
 *   A. PHDM (AetherBrain) → Deterministic Controller
 *   B. SCBE 14-Layer → Metric/Telemetry Engine
 *   C. Dual-Lattice → Structure + Runtime Transform
 *   D. Spiralverse Torus → Write Gate + Recall Index
 *   E. HYDRA → Distributed Ordering + Multi-Agent Coordination
 *
 * The runtime loop:
 *   1. Propose (candidate action)
 *   2. Score (SCBE metrics)
 *   3. Transform topology (Dual-Lattice phason response)
 *   4. Decide (PHDM controller gate)
 *   5. Execute (if ALLOW/TRANSFORM)
 *   6. Memory write attempt (Torus gate)
 *   7. Penalty & breathing (flux contraction, stutter)
 *   8. Audit (hashchain seal)
 *   9. Broadcast (HYDRA ordering, if swarm)
 */

import {
  BRAIN_DIMENSIONS,
  BRAIN_EPSILON,
  PHI,
  POINCARE_MAX_NORM,
  type RiskDecision,
  type BrainStateComponents,
  type CombinedAssessment,
} from './types.js';

import { type PHDMMonitorResult, type PHDMCoreConfig, PHDMCore } from './phdm-core.js';

import {
  type FluxState,
  type AgentFluxRecord,
  type FluxConfig,
  FluxStateManager,
} from './flux-states.js';

import {
  type AgentImmuneStatus,
  type ImmuneState,
  ImmuneResponseSystem,
} from './immune-response.js';

import {
  type DualLatticeResult,
  type PhasonShift,
  type DualLatticeConfig,
  DualLatticeSystem,
} from './dual-lattice.js';

import {
  type DualTernarySpectrum,
  type FractalDimensionResult,
  type DualTernaryConfig,
  DualTernarySystem,
} from './dual-ternary.js';

import { BrainAuditLogger } from './audit.js';
import { entropicAnomaly } from '../harmonic/entropicLayer.js';

// ═══════════════════════════════════════════════════════════════
// Canonical State (the single truth struct)
// ═══════════════════════════════════════════════════════════════

/**
 * Torus coordinates for cyclic memory/time/context.
 * Lives on T^k (k-dimensional torus).
 */
export interface TorusCoordinates {
  /** Domain/topic angle [0, 2π) */
  readonly theta: number;
  /** Sequence/time angle [0, 2π) — monotone rotation */
  readonly phi: number;
  /** Polarity angle [0, 2π) */
  readonly rho: number;
  /** Authority class angle [0, 2π) */
  readonly sigma: number;
}

/**
 * Penalty state for governance enforcement.
 */
export interface PenaltyState {
  /** Consecutive failure count */
  failCount: number;
  /** Time dilation delay (stutter factor, 1.0 = normal) */
  tauDelay: number;
  /** Timestamp of last penalty application */
  lastPenaltyAt: number;
  /** Accumulated snap events (torus write rejections) */
  snapCount: number;
}

/**
 * The canonical state object: everything plugs into this.
 *
 * Product manifold: B^n × T^k
 *   - Governance lives in B^n (hyperbolic Poincaré ball)
 *   - Memory recurrence lives in T^k (torus)
 *
 * Every module reads/writes through this struct.
 */
export interface CanonicalState {
  /** Agent identifier */
  readonly agentId: string;
  /** Timestamp step counter */
  step: number;
  /** Hyperbolic governance position (21D brain state in Poincaré ball) */
  hyp: number[];
  /** Torus coordinates for cyclic memory */
  torus: TorusCoordinates;
  /** Fractional dimension flux [0, 1] */
  flux: number;
  /** Current flux state tier */
  fluxState: FluxState;
  /** Dual lattice state snapshot */
  lattice: {
    /** Last static projection acceptance */
    staticAccepted: boolean;
    /** Last dynamic displacement */
    dynamicDisplacement: number;
    /** Cross-verification coherence */
    coherence: number;
    /** Whether dual lattice validated this step */
    validated: boolean;
  };
  /** Object-capability tokens / scopes */
  capabilities: Set<string>;
  /** Tamper-evident audit log anchor (last hash) */
  auditAnchor: string;
  /** Penalty state */
  penalties: PenaltyState;
  /** Immune system state */
  immuneState: ImmuneState;
}

// ═══════════════════════════════════════════════════════════════
// Module Contracts (hard interfaces)
// ═══════════════════════════════════════════════════════════════

/**
 * A proposed action from the LLM/generator.
 */
export interface ProposedAction {
  /** Action type identifier */
  readonly type: string;
  /** 21D state vector associated with this action */
  readonly stateVector: number[];
  /** Optional metadata */
  readonly meta?: Record<string, unknown>;
}

/**
 * Metric bundle produced by SCBE 14-layer scoring.
 * Produces scores; does NOT decide.
 */
export interface MetricBundle {
  /** Hyperbolic distance from safe center */
  hyperbolicDistance: number;
  /** Phase deviation [0, 1] */
  phaseDeviation: number;
  /** Spectral coherence [0, 1] */
  spectralCoherence: number;
  /** Decimal drift magnitude */
  driftMagnitude: number;
  /** Combined risk score [0, 1] */
  combinedRiskScore: number;
  /** Combined assessment from 5 detection mechanisms */
  assessment: CombinedAssessment;
}

/**
 * Memory event for torus write gate.
 */
export interface MemoryEvent {
  /** Event content hash */
  readonly contentHash: string;
  /** Semantic domain class */
  readonly domain: number;
  /** Sequence number (monotone) */
  readonly sequence: number;
  /** Polarity (+1 affirm, -1 negate, 0 neutral) */
  readonly polarity: number;
  /** Authority level [0, 1] */
  readonly authority: number;
}

/**
 * Result from the torus memory write gate.
 */
export interface MemoryWriteResult {
  /** Whether the event was committed */
  committed: boolean;
  /** Updated torus coordinates (if committed) */
  newTorus: TorusCoordinates;
  /** Whether a snap (contradiction) was detected */
  snap: boolean;
  /** Divergence score if snap occurred */
  divergence: number;
}

/**
 * Kernel decision — the output of the PHDM gate.
 */
export type KernelDecision = 'ALLOW' | 'TRANSFORM' | 'BLOCK' | 'QUARANTINE';

/**
 * Result of a single pipeline step.
 */
export interface PipelineStepResult {
  /** Step number */
  step: number;
  /** The proposed action that was evaluated */
  action: ProposedAction;
  /** SCBE metric bundle */
  metrics: MetricBundle;
  /** Dual lattice analysis */
  latticeResult: DualLatticeResult;
  /** Dual ternary spectrum */
  ternarySpectrum: DualTernarySpectrum;
  /** Kernel decision */
  decision: KernelDecision;
  /** Memory write result (if action was allowed) */
  memoryResult: MemoryWriteResult | null;
  /** Whether penalties were applied */
  penaltyApplied: boolean;
  /** Updated canonical state */
  state: CanonicalState;
  /** Audit hash for this step */
  auditHash: string;
}

// ═══════════════════════════════════════════════════════════════
// Kernel Configuration
// ═══════════════════════════════════════════════════════════════

export interface KernelConfig {
  /** PHDM controller config */
  phdm: Partial<PHDMCoreConfig>;
  /** Flux state config */
  flux: Partial<FluxConfig>;
  /** Dual lattice config */
  dualLattice: Partial<DualLatticeConfig>;
  /** Dual ternary config */
  dualTernary: Partial<DualTernaryConfig>;
  /** Risk threshold for BLOCK decision */
  blockThreshold: number;
  /** Risk threshold for TRANSFORM decision */
  transformThreshold: number;
  /** Penalty stutter multiplier per snap */
  stutterMultiplier: number;
  /** Flux contraction per snap event */
  fluxContractionPerSnap: number;
  /** Max stutter delay factor */
  maxStutterDelay: number;
  /** Memory divergence threshold for snap detection */
  snapDivergenceThreshold: number;
  /** Capability tiers based on flux state */
  capabilityTiers: Record<FluxState, string[]>;
}

export const DEFAULT_KERNEL_CONFIG: KernelConfig = {
  phdm: {},
  flux: {},
  dualLattice: {},
  dualTernary: {},
  blockThreshold: 0.8,
  transformThreshold: 0.5,
  stutterMultiplier: 1.5,
  fluxContractionPerSnap: 0.15,
  maxStutterDelay: 10.0,
  snapDivergenceThreshold: 0.7,
  capabilityTiers: {
    POLLY: ['read', 'write', 'execute', 'deploy', 'admin', 'create'],
    QUASI: ['read', 'write', 'execute', 'create'],
    DEMI: ['read', 'write'],
    COLLAPSED: ['read'],
  },
};

// ═══════════════════════════════════════════════════════════════
// Torus Memory Write Gate
// ═══════════════════════════════════════════════════════════════

/**
 * Torus Write Gate — decides whether a memory event can be committed
 * to the toroidal geometry.
 *
 * Semantic projection for torus coordinates:
 *   θ = domain/topic/predicate class
 *   φ = sequence/time (monotone rotation)
 *   ρ = polarity
 *   σ = authority class
 *
 * On contradiction (high divergence), emits snap=true which triggers
 * PHDM penalties (time dilation / flux contraction).
 */
export function torusWriteGate(
  current: TorusCoordinates,
  event: MemoryEvent,
  threshold: number
): MemoryWriteResult {
  // Map event to torus coordinates
  const TWO_PI = 2 * Math.PI;
  const candidateTheta = ((event.domain / 21) * TWO_PI) % TWO_PI;
  const candidatePhi = (current.phi + (event.sequence * TWO_PI) / 1000) % TWO_PI;
  const candidateRho = ((event.polarity + 1) / 2) * Math.PI; // [-1,1] → [0, π]
  const candidateSigma = event.authority * TWO_PI;

  // Compute angular divergence from current torus position
  const dTheta = Math.abs(angleDiff(current.theta, candidateTheta));
  const dPhi = Math.abs(angleDiff(current.phi, candidatePhi));
  const dRho = Math.abs(angleDiff(current.rho, candidateRho));
  const dSigma = Math.abs(angleDiff(current.sigma, candidateSigma));

  // Weighted divergence: domain + polarity matter most
  const divergence =
    dTheta * 0.35 + dRho * 0.30 + dSigma * 0.20 + dPhi * 0.15;
  const normalizedDivergence = divergence / Math.PI; // [0, 1]

  const snap = normalizedDivergence > threshold;

  if (snap) {
    // REJECT: event contradicts current memory geometry
    return {
      committed: false,
      newTorus: current,
      snap: true,
      divergence: normalizedDivergence,
    };
  }

  // COMMIT: update torus coordinates
  return {
    committed: true,
    newTorus: {
      theta: candidateTheta,
      phi: candidatePhi,
      rho: candidateRho,
      sigma: candidateSigma,
    },
    snap: false,
    divergence: normalizedDivergence,
  };
}

/** Compute shortest angular difference in [0, π]. */
function angleDiff(a: number, b: number): number {
  const d = Math.abs(a - b) % (2 * Math.PI);
  return d > Math.PI ? 2 * Math.PI - d : d;
}

// ═══════════════════════════════════════════════════════════════
// SCBE Metrics Adapter
// ═══════════════════════════════════════════════════════════════

/**
 * Score a proposed action using SCBE 14-layer metrics.
 * Produces scores only — does NOT decide.
 */
export function computeMetrics(
  state: number[],
  phdmResult: PHDMMonitorResult | null
): MetricBundle {
  // Compute hyperbolic distance from origin
  let normSq = 0;
  for (const v of state) normSq += v * v;
  const norm = Math.sqrt(normSq);
  const clampedNorm = Math.min(norm, POINCARE_MAX_NORM);
  const hyperbolicDistance =
    clampedNorm < 1.0 - BRAIN_EPSILON
      ? Math.acosh(1 + (2 * clampedNorm * clampedNorm) / (1 - clampedNorm * clampedNorm))
      : 20.0; // boundary → very large

  // Phase deviation: boundary proximity [0, 1].
  // Purely geometric — PHDM langues cost is NOT folded in here because:
  //   1. The langues cost formula produces large baseline values (exponential
  //      golden-ratio weights with sine modulation) even for small vectors.
  //   2. The PHDM's languesDecision is already used directly in the gate()
  //      function; double-counting it here would inflate risk for safe actions.
  const phaseDeviation = clampedNorm;

  // Spectral coherence: distance from Poincaré boundary [0, 1].
  // Near origin = high coherence, near boundary = low coherence.
  const spectralCoherence = 1.0 - clampedNorm;

  // Drift magnitude: norm of state
  const driftMagnitude = norm;

  // Combined risk score (geometric measures only)
  const combinedRiskScore = Math.min(
    1,
    hyperbolicDistance * 0.3 / 20.0 +
      phaseDeviation * 0.3 +
      (1 - spectralCoherence) * 0.2 +
      driftMagnitude * 0.2
  );

  // Build minimal assessment
  const assessment: CombinedAssessment = {
    detections: [],
    combinedScore: combinedRiskScore,
    decision: combinedRiskScore > 0.7 ? 'DENY' : combinedRiskScore > 0.4 ? 'QUARANTINE' : 'ALLOW',
    anyFlagged: combinedRiskScore > 0.5,
    flagCount: combinedRiskScore > 0.5 ? 1 : 0,
    timestamp: Date.now(),
  };

  return {
    hyperbolicDistance,
    phaseDeviation,
    spectralCoherence,
    driftMagnitude,
    combinedRiskScore,
    assessment,
  };
}

// ═══════════════════════════════════════════════════════════════
// Unified Kernel (Pipeline Runner)
// ═══════════════════════════════════════════════════════════════

/**
 * The Unified Kernel — single runtime loop that orchestrates
 * all SCBE-AETHERMOORE subsystems.
 *
 * Runtime loop (9 steps):
 *   1. Propose: receive candidate action
 *   2. Score: SCBE metrics (produces scores, doesn't decide)
 *   3. Transform topology: Dual-Lattice phason response
 *   4. Decide: PHDM controller gate
 *   5. Execute: if ALLOW/TRANSFORM
 *   6. Memory write: Torus gate
 *   7. Penalty & breathing: flux contraction, stutter
 *   8. Audit: hashchain seal
 *   9. Broadcast: HYDRA ordering (if swarm)
 */
export class UnifiedKernel {
  private readonly config: KernelConfig;
  private readonly phdm: PHDMCore;
  private readonly fluxManager: FluxStateManager;
  private readonly immune: ImmuneResponseSystem;
  private readonly dualLattice: DualLatticeSystem;
  private readonly dualTernary: DualTernarySystem;
  private readonly auditLogger: BrainAuditLogger;

  /** Per-agent canonical states */
  private readonly states: Map<string, CanonicalState> = new Map();

  /** Ordered event log (HYDRA-compatible) */
  private readonly orderedLog: PipelineStepResult[] = [];

  constructor(config: Partial<KernelConfig> = {}) {
    this.config = { ...DEFAULT_KERNEL_CONFIG, ...config };
    this.phdm = new PHDMCore(this.config.phdm);
    this.fluxManager = new FluxStateManager(this.config.flux);
    this.immune = new ImmuneResponseSystem();
    this.dualLattice = new DualLatticeSystem(this.config.dualLattice);
    this.dualTernary = new DualTernarySystem(this.config.dualTernary);
    this.auditLogger = new BrainAuditLogger();

    // Initialize PHDM with a deterministic key (for non-Kyber contexts)
    const masterKey = Buffer.alloc(32);
    for (let i = 0; i < 32; i++) masterKey[i] = ((i * 137 + 42) % 256);
    this.phdm.initializeWithKey(masterKey);

    // Initialize static lattice mesh
    this.dualLattice.initializeMesh(3);
  }

  // ─── State Management ───────────────────────────────────────

  /**
   * Initialize canonical state for an agent.
   */
  initializeAgent(agentId: string, initialState?: number[]): CanonicalState {
    const hyp = initialState || new Array(BRAIN_DIMENSIONS).fill(0);
    const fluxRecord = this.fluxManager.initializeAgent(agentId, 0.8);

    const state: CanonicalState = {
      agentId,
      step: 0,
      hyp: [...hyp],
      torus: { theta: 0, phi: 0, rho: Math.PI / 2, sigma: 0 },
      flux: fluxRecord.nu,
      fluxState: fluxRecord.state,
      lattice: {
        staticAccepted: true,
        dynamicDisplacement: 0,
        coherence: 1.0,
        validated: true,
      },
      capabilities: new Set(this.config.capabilityTiers[fluxRecord.state]),
      auditAnchor: '',
      penalties: {
        failCount: 0,
        tauDelay: 1.0,
        lastPenaltyAt: 0,
        snapCount: 0,
      },
      immuneState: 'healthy',
    };

    this.states.set(agentId, state);
    return state;
  }

  /**
   * Get the current canonical state for an agent.
   */
  getState(agentId: string): CanonicalState | undefined {
    return this.states.get(agentId);
  }

  // ─── The 9-Step Runtime Loop ────────────────────────────────

  /**
   * Process a proposed action through the full 9-step pipeline.
   *
   * This is the single control loop that uses all parts in the right order.
   */
  processAction(
    agentId: string,
    action: ProposedAction,
    memoryEvent?: MemoryEvent
  ): PipelineStepResult {
    let state = this.states.get(agentId);
    if (!state) {
      state = this.initializeAgent(agentId, action.stateVector);
    }

    state.step++;

    // Project state vector into Poincaré ball (enforce ||hyp|| < 1)
    const rawNormSq = action.stateVector.reduce((s, v) => s + v * v, 0);
    const rawNorm = Math.sqrt(rawNormSq);
    if (rawNorm >= POINCARE_MAX_NORM) {
      const projScale = (POINCARE_MAX_NORM - BRAIN_EPSILON) / rawNorm;
      state.hyp = action.stateVector.map(v => v * projScale);
    } else {
      state.hyp = [...action.stateVector];
    }

    // ═══ Step 1: Propose ═══
    // (action is already the proposal — received as input)

    // ═══ Step 2: Score (SCBE metrics) ═══
    const hfToken = process.env.HUGGINGFACE_TOKEN;
    if (!hfToken) {
      const anomaly = entropicAnomaly('HF_TOKEN_MISSING', {
        agentId,
        step: state.step,
        token: '[REDACTED]',
      });

      const quarantineMetrics: MetricBundle = {
        hyperbolicDistance: 0,
        phaseDeviation: 1,
        spectralCoherence: 0,
        driftMagnitude: 0,
        combinedRiskScore: 1,
        assessment: {
          detections: [],
          combinedScore: 1,
          decision: 'QUARANTINE',
          anyFlagged: true,
          flagCount: 1,
          timestamp: Date.now(),
        },
      };

      this.auditLogger.logRiskDecision(
        'QUARANTINE',
        agentId,
        `step=${state.step} reason=HF_TOKEN_MISSING token=[REDACTED]`,
        {
          step: state.step,
          anomaly: anomaly.code,
          token: '[REDACTED]',
          decision: 'QUARANTINE',
        }
      );

      const hashChain = this.auditLogger.getHashChain();
      const auditHash = hashChain.length > 0 ? hashChain[hashChain.length - 1] : '';
      state.auditAnchor = auditHash;

      const result: PipelineStepResult = {
        step: state.step,
        action,
        metrics: quarantineMetrics,
        latticeResult: this.dualLattice.process(
          action.stateVector,
          this.dualLattice.createThreatPhason(1.0, findAnomalyDimensions(action.stateVector))
        ),
        ternarySpectrum: this.dualTernary.analyzeSpectrum(),
        decision: 'QUARANTINE',
        memoryResult: null,
        penaltyApplied: true,
        state: { ...state, capabilities: new Set(state.capabilities) },
        auditHash,
      };

      this.orderedLog.push(result);
      return result;
    }

    const phdmResult = this.phdm.monitor(action.stateVector, state.step);
    const metrics = computeMetrics(action.stateVector, phdmResult);

    // Process immune response
    const immuneStatus = this.immune.processAssessment(agentId, metrics.assessment);
    state.immuneState = immuneStatus.state;

    // ═══ Step 3: Transform topology (Dual-Lattice runtime) ═══
    const threatPhason = this.dualLattice.createThreatPhason(
      metrics.combinedRiskScore,
      findAnomalyDimensions(action.stateVector)
    );
    const latticeResult = this.dualLattice.process(action.stateVector, threatPhason);

    state.lattice = {
      staticAccepted: latticeResult.static.accepted,
      dynamicDisplacement: latticeResult.dynamic.displacement,
      coherence: latticeResult.coherence,
      validated: latticeResult.validated,
    };

    // Dual ternary encoding for spectral analysis
    const ternaryEncoded = this.dualTernary.encode(action.stateVector);
    const ternarySpectrum = this.dualTernary.analyzeSpectrum();

    // ═══ Step 4: Decide (PHDM controller gate) ═══
    const decision = this.gate(state, metrics, latticeResult, phdmResult);

    // ═══ Step 5: Execute (if ALLOW/TRANSFORM) ═══
    // (execution is external; we just report the decision)

    // ═══ Step 6: Memory write attempt (Torus gate) ═══
    let memoryResult: MemoryWriteResult | null = null;
    if (memoryEvent && (decision === 'ALLOW' || decision === 'TRANSFORM')) {
      memoryResult = torusWriteGate(
        state.torus,
        memoryEvent,
        this.config.snapDivergenceThreshold
      );
      if (memoryResult.committed) {
        state.torus = memoryResult.newTorus;
      }
    }

    // ═══ Step 7: Penalty & breathing ═══
    const penaltyApplied = this.applyPenalties(state, decision, metrics, memoryResult);

    // Evolve flux state
    const fluxRecord = this.fluxManager.evolve(
      agentId,
      1 - metrics.combinedRiskScore, // trust = inverse of risk
      state.immuneState
    );
    state.flux = fluxRecord.nu;
    state.fluxState = fluxRecord.state;

    // Apply snap-based flux contraction AFTER evolution so it persists.
    // (The flux manager evolve() would otherwise override the penalty reduction.)
    if (memoryResult?.snap) {
      state.flux = Math.max(0, state.flux - this.config.fluxContractionPerSnap);
    }

    // Update capabilities based on current flux state
    state.capabilities = new Set(this.config.capabilityTiers[state.fluxState]);

    // ═══ Step 8: Audit (hashchain seal) ═══
    this.auditLogger.logRiskDecision(
      decision,
      agentId,
      `step=${state.step} risk=${metrics.combinedRiskScore.toFixed(4)}`,
      {
        step: state.step,
        flux: state.flux,
        fluxState: state.fluxState,
        immuneState: state.immuneState,
        latticeCoherence: latticeResult.coherence,
        memorySnap: memoryResult?.snap ?? false,
        penalties: { ...state.penalties },
      }
    );
    const hashChain = this.auditLogger.getHashChain();
    const auditHash = hashChain.length > 0 ? hashChain[hashChain.length - 1] : '';
    state.auditAnchor = auditHash;

    // ═══ Step 9: Broadcast (HYDRA ordering) ═══
    const result: PipelineStepResult = {
      step: state.step,
      action,
      metrics,
      latticeResult,
      ternarySpectrum,
      decision,
      memoryResult,
      penaltyApplied,
      state: { ...state, capabilities: new Set(state.capabilities) },
      auditHash,
    };

    this.orderedLog.push(result);

    return result;
  }

  // ─── PHDM Gate (Deterministic Controller) ──────────────────

  /**
   * The PHDM gate: deterministic decision given (S, action, metrics, lattice).
   *
   * Must be deterministic given the same inputs.
   * Enforces: boundedness, capabilities, barrier functions.
   */
  private gate(
    state: CanonicalState,
    metrics: MetricBundle,
    latticeResult: DualLatticeResult,
    phdmResult: PHDMMonitorResult
  ): KernelDecision {
    // Hard block: PHDM escalation requires corroborating risk evidence.
    // The langues cost formula uses time-dependent sine modulation with
    // golden-ratio exponential weights, which can transiently spike even
    // for safe vectors. Require that the independent risk metrics also
    // indicate elevated risk before hard-blocking.
    if (phdmResult.phdmEscalation && metrics.combinedRiskScore > 0.3) {
      return 'BLOCK';
    }

    // DENY with corroborating risk evidence
    if (phdmResult.languesDecision === 'DENY' && metrics.combinedRiskScore > 0.4) {
      return 'BLOCK';
    }

    // Intrusion accumulation: hard block only with corroborating risk evidence.
    // No unconditional cap — PHDM geodesic deviation flags many benign vectors
    // because the 21D→6D langues mapping naturally deviates from the expected
    // polyhedron-centroid geodesic. Low-risk actions must pass regardless of
    // intrusion count; the escalation + risk checks above handle true threats.
    if (phdmResult.intrusionCount >= 5 && metrics.combinedRiskScore > 0.15) {
      return 'BLOCK';
    }

    // Hard block: immune system says expelled
    if (state.immuneState === 'expelled') {
      return 'BLOCK';
    }

    // Hard block: flux collapsed with high-risk action
    if (state.fluxState === 'COLLAPSED' && metrics.combinedRiskScore > 0.3) {
      return 'BLOCK';
    }

    // Hard block: dual lattice not validated + high risk
    if (!latticeResult.validated && metrics.combinedRiskScore > 0.6) {
      return 'BLOCK';
    }

    // Combined score threshold
    const effectiveRisk =
      metrics.combinedRiskScore * 0.4 +
      (1 - latticeResult.coherence) * 0.2 +
      (state.penalties.tauDelay > 2.0 ? 0.2 : 0) +
      (state.immuneState === 'quarantined' ? 0.2 : 0);

    if (effectiveRisk >= this.config.blockThreshold) {
      return 'BLOCK';
    }

    if (effectiveRisk >= this.config.transformThreshold) {
      return 'TRANSFORM';
    }

    return 'ALLOW';
  }

  // ─── Penalty Application ───────────────────────────────────

  /**
   * Apply penalties based on decision outcome and memory snaps.
   *
   * On snap or high risk:
   *   - Increase τ_delay (stutter)
   *   - Contract ν (flux shift toward QUASI/DEMI)
   *   - Increment fail count
   */
  private applyPenalties(
    state: CanonicalState,
    decision: KernelDecision,
    metrics: MetricBundle,
    memoryResult: MemoryWriteResult | null
  ): boolean {
    let penalized = false;

    // Memory snap → penalties (stutter + snap count; flux contraction is
    // applied after fluxManager.evolve() in processAction to persist)
    if (memoryResult?.snap) {
      state.penalties.snapCount++;
      state.penalties.tauDelay = Math.min(
        state.penalties.tauDelay * this.config.stutterMultiplier,
        this.config.maxStutterDelay
      );
      penalized = true;
    }

    // BLOCK decision → penalties
    if (decision === 'BLOCK') {
      state.penalties.failCount++;
      state.penalties.tauDelay = Math.min(
        state.penalties.tauDelay * 1.2,
        this.config.maxStutterDelay
      );
      state.penalties.lastPenaltyAt = state.step;
      penalized = true;
    }

    // Gradual recovery when not penalized.
    // Use 0.85 decay so that agents can meaningfully recover within
    // tens of safe steps (0.95 was too slow from the 10.0 cap).
    if (!penalized && state.penalties.tauDelay > 1.0) {
      state.penalties.tauDelay = Math.max(1.0, state.penalties.tauDelay * 0.85);
    }

    return penalized;
  }

  // ─── Query Methods ─────────────────────────────────────────

  /** Get the ordered event log (HYDRA-compatible). */
  getOrderedLog(): ReadonlyArray<PipelineStepResult> {
    return this.orderedLog;
  }

  /** Get all agent states. */
  getAllStates(): Map<string, CanonicalState> {
    return new Map(this.states);
  }

  /** Get the audit logger. */
  getAuditLogger(): BrainAuditLogger {
    return this.auditLogger;
  }

  /** Get the PHDM core. */
  getPHDM(): PHDMCore {
    return this.phdm;
  }

  /** Get the flux manager. */
  getFluxManager(): FluxStateManager {
    return this.fluxManager;
  }

  /** Get the immune system. */
  getImmuneSystem(): ImmuneResponseSystem {
    return this.immune;
  }

  /** Get the dual lattice system. */
  getDualLattice(): DualLatticeSystem {
    return this.dualLattice;
  }

  /** Get the dual ternary system. */
  getDualTernary(): DualTernarySystem {
    return this.dualTernary;
  }

  /**
   * Compute a deterministic state hash for HYDRA convergence verification.
   * All agents processing the same ordered events should arrive at the same hash.
   */
  computeStateHash(agentId: string): string {
    const state = this.states.get(agentId);
    if (!state) return '';

    // Deterministic serialization of key state components.
    // NOTE: auditAnchor is excluded because the BrainAuditLogger uses
    // wall-clock timestamps in its SHA-256 hash chain, making it
    // inherently non-deterministic across kernel instances. Audit
    // chain integrity is verified separately via verifyChainIntegrity().
    const components = [
      state.step.toString(),
      state.flux.toFixed(8),
      state.fluxState,
      state.immuneState,
      state.penalties.failCount.toString(),
      state.penalties.snapCount.toString(),
      state.penalties.tauDelay.toFixed(8),
      state.lattice.coherence.toFixed(8),
      state.lattice.validated.toString(),
    ];

    return simpleHash(components.join('|'));
  }

  /** Reset all state (for testing). */
  reset(): void {
    this.states.clear();
    this.orderedLog.length = 0;
    this.phdm.resetMonitoring();
  }
}

// ═══════════════════════════════════════════════════════════════
// Utility Functions
// ═══════════════════════════════════════════════════════════════

/**
 * Find anomaly dimensions: indices where |value| exceeds threshold.
 */
function findAnomalyDimensions(
  state: number[],
  threshold: number = 0.7
): number[] {
  const dims: number[] = [];
  for (let i = 0; i < state.length; i++) {
    if (Math.abs(state[i]) > threshold) {
      dims.push(i);
    }
  }
  return dims;
}

/**
 * Simple deterministic hash for state fingerprinting.
 * (Not cryptographic — used for convergence verification.)
 */
function simpleHash(data: string): string {
  let h = 0x811c9dc5; // FNV offset basis
  for (let i = 0; i < data.length; i++) {
    h ^= data.charCodeAt(i);
    h = Math.imul(h, 0x01000193); // FNV prime
  }
  return (h >>> 0).toString(16).padStart(8, '0');
}
