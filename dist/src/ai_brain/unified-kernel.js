"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.UnifiedKernel = exports.DEFAULT_KERNEL_CONFIG = void 0;
exports.torusWriteGate = torusWriteGate;
exports.computeMetrics = computeMetrics;
const types_js_1 = require("./types.js");
const phdm_core_js_1 = require("./phdm-core.js");
const flux_states_js_1 = require("./flux-states.js");
const immune_response_js_1 = require("./immune-response.js");
const dual_lattice_js_1 = require("./dual-lattice.js");
const dual_ternary_js_1 = require("./dual-ternary.js");
const audit_js_1 = require("./audit.js");
exports.DEFAULT_KERNEL_CONFIG = {
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
function torusWriteGate(current, event, threshold) {
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
    const divergence = dTheta * 0.35 + dRho * 0.30 + dSigma * 0.20 + dPhi * 0.15;
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
function angleDiff(a, b) {
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
function computeMetrics(state, phdmResult) {
    // Compute hyperbolic distance from origin
    let normSq = 0;
    for (const v of state)
        normSq += v * v;
    const norm = Math.sqrt(normSq);
    const clampedNorm = Math.min(norm, types_js_1.POINCARE_MAX_NORM);
    const hyperbolicDistance = clampedNorm < 1.0 - types_js_1.BRAIN_EPSILON
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
    const combinedRiskScore = Math.min(1, hyperbolicDistance * 0.3 / 20.0 +
        phaseDeviation * 0.3 +
        (1 - spectralCoherence) * 0.2 +
        driftMagnitude * 0.2);
    // Build minimal assessment
    const assessment = {
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
class UnifiedKernel {
    config;
    phdm;
    fluxManager;
    immune;
    dualLattice;
    dualTernary;
    auditLogger;
    /** Per-agent canonical states */
    states = new Map();
    /** Ordered event log (HYDRA-compatible) */
    orderedLog = [];
    constructor(config = {}) {
        this.config = { ...exports.DEFAULT_KERNEL_CONFIG, ...config };
        this.phdm = new phdm_core_js_1.PHDMCore(this.config.phdm);
        this.fluxManager = new flux_states_js_1.FluxStateManager(this.config.flux);
        this.immune = new immune_response_js_1.ImmuneResponseSystem();
        this.dualLattice = new dual_lattice_js_1.DualLatticeSystem(this.config.dualLattice);
        this.dualTernary = new dual_ternary_js_1.DualTernarySystem(this.config.dualTernary);
        this.auditLogger = new audit_js_1.BrainAuditLogger();
        // Initialize PHDM with a deterministic key (for non-Kyber contexts)
        const masterKey = Buffer.alloc(32);
        for (let i = 0; i < 32; i++)
            masterKey[i] = ((i * 137 + 42) % 256);
        this.phdm.initializeWithKey(masterKey);
        // Initialize static lattice mesh
        this.dualLattice.initializeMesh(3);
    }
    // ─── State Management ───────────────────────────────────────
    /**
     * Initialize canonical state for an agent.
     */
    initializeAgent(agentId, initialState) {
        const hyp = initialState || new Array(types_js_1.BRAIN_DIMENSIONS).fill(0);
        const fluxRecord = this.fluxManager.initializeAgent(agentId, 0.8);
        const state = {
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
    getState(agentId) {
        return this.states.get(agentId);
    }
    // ─── The 9-Step Runtime Loop ────────────────────────────────
    /**
     * Process a proposed action through the full 9-step pipeline.
     *
     * This is the single control loop that uses all parts in the right order.
     */
    processAction(agentId, action, memoryEvent) {
        let state = this.states.get(agentId);
        if (!state) {
            state = this.initializeAgent(agentId, action.stateVector);
        }
        state.step++;
        // Project state vector into Poincaré ball (enforce ||hyp|| < 1)
        const rawNormSq = action.stateVector.reduce((s, v) => s + v * v, 0);
        const rawNorm = Math.sqrt(rawNormSq);
        if (rawNorm >= types_js_1.POINCARE_MAX_NORM) {
            const projScale = (types_js_1.POINCARE_MAX_NORM - types_js_1.BRAIN_EPSILON) / rawNorm;
            state.hyp = action.stateVector.map(v => v * projScale);
        }
        else {
            state.hyp = [...action.stateVector];
        }
        // ═══ Step 1: Propose ═══
        // (action is already the proposal — received as input)
        // ═══ Step 2: Score (SCBE metrics) ═══
        const phdmResult = this.phdm.monitor(action.stateVector, state.step);
        const metrics = computeMetrics(action.stateVector, phdmResult);
        // Process immune response
        const immuneStatus = this.immune.processAssessment(agentId, metrics.assessment);
        state.immuneState = immuneStatus.state;
        // ═══ Step 3: Transform topology (Dual-Lattice runtime) ═══
        const threatPhason = this.dualLattice.createThreatPhason(metrics.combinedRiskScore, findAnomalyDimensions(action.stateVector));
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
        let memoryResult = null;
        if (memoryEvent && (decision === 'ALLOW' || decision === 'TRANSFORM')) {
            memoryResult = torusWriteGate(state.torus, memoryEvent, this.config.snapDivergenceThreshold);
            if (memoryResult.committed) {
                state.torus = memoryResult.newTorus;
            }
        }
        // ═══ Step 7: Penalty & breathing ═══
        const penaltyApplied = this.applyPenalties(state, decision, metrics, memoryResult);
        // Evolve flux state
        const fluxRecord = this.fluxManager.evolve(agentId, 1 - metrics.combinedRiskScore, // trust = inverse of risk
        state.immuneState);
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
        this.auditLogger.logRiskDecision(decision, agentId, `step=${state.step} risk=${metrics.combinedRiskScore.toFixed(4)}`, {
            step: state.step,
            flux: state.flux,
            fluxState: state.fluxState,
            immuneState: state.immuneState,
            latticeCoherence: latticeResult.coherence,
            memorySnap: memoryResult?.snap ?? false,
            penalties: { ...state.penalties },
        });
        const hashChain = this.auditLogger.getHashChain();
        const auditHash = hashChain.length > 0 ? hashChain[hashChain.length - 1] : '';
        state.auditAnchor = auditHash;
        // ═══ Step 9: Broadcast (HYDRA ordering) ═══
        const result = {
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
    gate(state, metrics, latticeResult, phdmResult) {
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
        const effectiveRisk = metrics.combinedRiskScore * 0.4 +
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
    applyPenalties(state, decision, metrics, memoryResult) {
        let penalized = false;
        // Memory snap → penalties (stutter + snap count; flux contraction is
        // applied after fluxManager.evolve() in processAction to persist)
        if (memoryResult?.snap) {
            state.penalties.snapCount++;
            state.penalties.tauDelay = Math.min(state.penalties.tauDelay * this.config.stutterMultiplier, this.config.maxStutterDelay);
            penalized = true;
        }
        // BLOCK decision → penalties
        if (decision === 'BLOCK') {
            state.penalties.failCount++;
            state.penalties.tauDelay = Math.min(state.penalties.tauDelay * 1.2, this.config.maxStutterDelay);
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
    getOrderedLog() {
        return this.orderedLog;
    }
    /** Get all agent states. */
    getAllStates() {
        return new Map(this.states);
    }
    /** Get the audit logger. */
    getAuditLogger() {
        return this.auditLogger;
    }
    /** Get the PHDM core. */
    getPHDM() {
        return this.phdm;
    }
    /** Get the flux manager. */
    getFluxManager() {
        return this.fluxManager;
    }
    /** Get the immune system. */
    getImmuneSystem() {
        return this.immune;
    }
    /** Get the dual lattice system. */
    getDualLattice() {
        return this.dualLattice;
    }
    /** Get the dual ternary system. */
    getDualTernary() {
        return this.dualTernary;
    }
    /**
     * Compute a deterministic state hash for HYDRA convergence verification.
     * All agents processing the same ordered events should arrive at the same hash.
     */
    computeStateHash(agentId) {
        const state = this.states.get(agentId);
        if (!state)
            return '';
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
    reset() {
        this.states.clear();
        this.orderedLog.length = 0;
        this.phdm.resetMonitoring();
    }
}
exports.UnifiedKernel = UnifiedKernel;
// ═══════════════════════════════════════════════════════════════
// Utility Functions
// ═══════════════════════════════════════════════════════════════
/**
 * Find anomaly dimensions: indices where |value| exceeds threshold.
 */
function findAnomalyDimensions(state, threshold = 0.7) {
    const dims = [];
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
function simpleHash(data) {
    let h = 0x811c9dc5; // FNV offset basis
    for (let i = 0; i < data.length; i++) {
        h ^= data.charCodeAt(i);
        h = Math.imul(h, 0x01000193); // FNV prime
    }
    return (h >>> 0).toString(16).padStart(8, '0');
}
//# sourceMappingURL=unified-kernel.js.map