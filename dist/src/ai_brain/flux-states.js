"use strict";
/**
 * @file flux-states.ts
 * @module ai_brain/flux-states
 * @layer Layer 6, Layer 8, Layer 13
 * @component PHDM Flux State Management
 * @version 1.0.0
 * @since 2026-02-07
 *
 * Manages PHDM (Polyhedral Hamiltonian Defense Manifold) flux states
 * that control tiered access to the brain manifold.
 *
 * Flux states determine what capabilities an agent has:
 * - POLLY (nu >= 0.8): Full access to all 16 polyhedra, complete cognitive processing
 * - QUASI (0.5 <= nu < 0.8): Partial access, cortex polyhedra restricted
 * - DEMI (0.1 <= nu < 0.5): Minimal access, only core Platonic solids
 * - COLLAPSED (nu < 0.1): Limbic-only, no cognitive processing
 *
 * The flux value (nu) evolves based on agent behavior, trust scores,
 * and immune system state. This creates a dynamic access control system
 * where access rights are earned through demonstrated trustworthiness.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.FluxStateManager = exports.DEFAULT_FLUX_CONFIG = exports.POLYHEDRA = void 0;
/**
 * The 16 canonical polyhedra with their access requirements
 */
exports.POLYHEDRA = [
    // Core (5 Platonic Solids) - accessible at DEMI and above
    { name: 'Tetrahedron', category: 'core', minFlux: 0.1, cognitiveFunction: 'Fundamental truth' },
    { name: 'Cube', category: 'core', minFlux: 0.1, cognitiveFunction: 'Stable facts' },
    { name: 'Octahedron', category: 'core', minFlux: 0.1, cognitiveFunction: 'Binary decisions' },
    { name: 'Dodecahedron', category: 'core', minFlux: 0.15, cognitiveFunction: 'Complex rules' },
    { name: 'Icosahedron', category: 'core', minFlux: 0.2, cognitiveFunction: 'Multi-modal integration' },
    // Cortex (3 Archimedean Solids) - accessible at QUASI and above
    { name: 'Truncated Icosahedron', category: 'cortex', minFlux: 0.5, cognitiveFunction: 'Multi-step planning' },
    { name: 'Rhombicuboctahedron', category: 'cortex', minFlux: 0.55, cognitiveFunction: 'Concept bridging' },
    { name: 'Snub Dodecahedron', category: 'cortex', minFlux: 0.6, cognitiveFunction: 'Creative synthesis' },
    // Subconscious (2 Kepler-Poinsot Stars) - accessible at POLLY only
    { name: 'Small Stellated Dodecahedron', category: 'subconscious', minFlux: 0.8, cognitiveFunction: 'High-risk abstract' },
    { name: 'Great Stellated Dodecahedron', category: 'subconscious', minFlux: 0.85, cognitiveFunction: 'Adversarial detect' },
    // Cerebellum (2 Toroidal) - accessible at POLLY only
    { name: 'Szilassi Polyhedron', category: 'cerebellum', minFlux: 0.8, cognitiveFunction: 'Self-diagnostic loops' },
    { name: 'Csaszar Polyhedron', category: 'cerebellum', minFlux: 0.85, cognitiveFunction: 'Recursive processing' },
    // Connectome (4 Johnson/Rhombic) - accessible at QUASI and above
    { name: 'Pentagonal Bipyramid', category: 'connectome', minFlux: 0.5, cognitiveFunction: 'Space-filling logic' },
    { name: 'Triangular Cupola', category: 'connectome', minFlux: 0.5, cognitiveFunction: 'Pattern matching' },
    { name: 'Rhombic Dodecahedron', category: 'connectome', minFlux: 0.55, cognitiveFunction: 'Spatial tiling' },
    { name: 'Bilinski Dodecahedron', category: 'connectome', minFlux: 0.6, cognitiveFunction: 'Dual-space bridging' },
];
/**
 * Default flux configuration
 */
exports.DEFAULT_FLUX_CONFIG = {
    meanReversionRate: 0.05,
    equilibriumFlux: 0.5,
    oscillationAmplitude: 0.02,
    oscillationFrequency: 0.1,
    immunePenalties: {
        healthy: 0,
        monitoring: 0.05,
        inflamed: 0.15,
        quarantined: 0.4,
        expelled: 1.0,
    },
    trustBoostRate: 0.01,
};
// ═══════════════════════════════════════════════════════════════
// Flux State Manager
// ═══════════════════════════════════════════════════════════════
/**
 * PHDM Flux State Manager
 *
 * Manages the dimensional flux states for all agents in the brain manifold.
 * Flux values evolve dynamically based on:
 * - Mean reversion toward trust-determined equilibrium
 * - Sinusoidal oscillation (breathing dimension flux)
 * - Immune state penalties
 * - Trust score positive reinforcement
 *
 * Flux evolution follows:
 *   dnu/dt = kappa * (nu_bar - nu) + sigma * sin(Omega * t) - penalty
 */
class FluxStateManager {
    agents = new Map();
    config;
    constructor(config = {}) {
        this.config = { ...exports.DEFAULT_FLUX_CONFIG, ...config };
    }
    /**
     * Initialize or update an agent's flux state.
     *
     * @param agentId - Agent identifier
     * @param initialNu - Initial flux value (default: 0.5)
     * @returns Flux record
     */
    initializeAgent(agentId, initialNu = 0.5) {
        const nu = Math.max(0, Math.min(1, initialNu));
        const record = {
            agentId,
            nu,
            state: this.nuToState(nu),
            accessiblePolyhedra: this.getAccessiblePolyhedra(nu),
            effectiveDimensionality: this.computeEffectiveDimensionality(nu),
            velocity: 0,
            timeStep: 0,
        };
        this.agents.set(agentId, record);
        return record;
    }
    /**
     * Evolve an agent's flux state by one time step.
     *
     * Implements the ODE:
     *   dnu/dt = kappa * (nu_bar - nu) + sigma * sin(Omega * t) - penalty
     *
     * Where:
     * - kappa = mean reversion rate
     * - nu_bar = equilibrium flux (from trust score)
     * - sigma = oscillation amplitude
     * - Omega = oscillation frequency
     * - penalty = immune state penalty
     *
     * @param agentId - Agent to evolve
     * @param trustScore - Current trust score [0, 1]
     * @param immuneState - Current immune state
     * @param dt - Time step size (default: 1)
     * @returns Updated flux record
     */
    evolve(agentId, trustScore, immuneState, dt = 1) {
        let record = this.agents.get(agentId);
        if (!record) {
            record = this.initializeAgent(agentId, trustScore);
        }
        // Compute equilibrium from trust score
        const nuBar = trustScore;
        // Mean reversion toward equilibrium
        const reversion = this.config.meanReversionRate * (nuBar - record.nu);
        // Sinusoidal oscillation (breathing)
        const oscillation = this.config.oscillationAmplitude *
            Math.sin(this.config.oscillationFrequency * record.timeStep);
        // Immune state penalty
        const penalty = this.config.immunePenalties[immuneState];
        // Trust boost (positive reinforcement for good behavior)
        const trustBoost = trustScore > 0.8 ? this.config.trustBoostRate : 0;
        // Euler integration
        const dnu = (reversion + oscillation - penalty + trustBoost) * dt;
        record.velocity = dnu;
        record.nu = Math.max(0, Math.min(1, record.nu + dnu));
        record.timeStep++;
        // Update derived state
        record.state = this.nuToState(record.nu);
        record.accessiblePolyhedra = this.getAccessiblePolyhedra(record.nu);
        record.effectiveDimensionality = this.computeEffectiveDimensionality(record.nu);
        this.agents.set(agentId, record);
        return record;
    }
    /**
     * Get the current flux record for an agent
     */
    getAgentFlux(agentId) {
        return this.agents.get(agentId);
    }
    /**
     * Get all agents in a specific flux state
     */
    getAgentsByState(state) {
        return Array.from(this.agents.values()).filter((r) => r.state === state);
    }
    /**
     * Check if an agent can access a specific polyhedron
     */
    canAccess(agentId, polyhedronName) {
        const record = this.agents.get(agentId);
        if (!record)
            return false;
        return record.accessiblePolyhedra.includes(polyhedronName);
    }
    /**
     * Get the governance capabilities for a flux state
     */
    getCapabilities(state) {
        switch (state) {
            case 'POLLY':
                return { canProcess: true, canPlan: true, canCreate: true, canSelfDiagnose: true, maxCognitiveLayers: 16 };
            case 'QUASI':
                return { canProcess: true, canPlan: true, canCreate: false, canSelfDiagnose: false, maxCognitiveLayers: 11 };
            case 'DEMI':
                return { canProcess: true, canPlan: false, canCreate: false, canSelfDiagnose: false, maxCognitiveLayers: 5 };
            case 'COLLAPSED':
                return { canProcess: false, canPlan: false, canCreate: false, canSelfDiagnose: false, maxCognitiveLayers: 0 };
        }
    }
    /**
     * Get summary statistics
     */
    getStats() {
        const byState = {
            POLLY: 0,
            QUASI: 0,
            DEMI: 0,
            COLLAPSED: 0,
        };
        let totalFlux = 0;
        let totalDim = 0;
        for (const record of this.agents.values()) {
            byState[record.state]++;
            totalFlux += record.nu;
            totalDim += record.effectiveDimensionality;
        }
        const total = this.agents.size;
        return {
            total,
            byState,
            avgFlux: total > 0 ? totalFlux / total : 0,
            avgDimensionality: total > 0 ? totalDim / total : 0,
        };
    }
    // ═══════════════════════════════════════════════════════════════
    // Private Methods
    // ═══════════════════════════════════════════════════════════════
    nuToState(nu) {
        if (nu >= 0.8)
            return 'POLLY';
        if (nu >= 0.5)
            return 'QUASI';
        if (nu >= 0.1)
            return 'DEMI';
        return 'COLLAPSED';
    }
    getAccessiblePolyhedra(nu) {
        return exports.POLYHEDRA.filter((p) => nu >= p.minFlux).map((p) => p.name);
    }
    computeEffectiveDimensionality(nu) {
        // Count accessible polyhedra, normalized by total
        const accessible = exports.POLYHEDRA.filter((p) => nu >= p.minFlux).length;
        return accessible / exports.POLYHEDRA.length;
    }
}
exports.FluxStateManager = FluxStateManager;
//# sourceMappingURL=flux-states.js.map