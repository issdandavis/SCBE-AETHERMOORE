"use strict";
/**
 * Swarm Coordination System
 *
 * Manages Polly dimensional swarm coordination between agent pads.
 * Implements coherence tracking, synchronization, and flux ODE dynamics.
 *
 * Dimensional States:
 * - POLLY (ν ≈ 1.0): Full swarm participation
 * - QUASI (0.5 < ν < 1): Partial sync
 * - DEMI (0 < ν < 0.5): Minimal connection
 * - COLLAPSED (ν ≈ 0): Disconnected
 *
 * @module fleet/swarm
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.SwarmCoordinator = exports.DEFAULT_FLUX_ODE = void 0;
const types_1 = require("./types");
/**
 * Default flux ODE parameters
 */
exports.DEFAULT_FLUX_ODE = {
    alpha: 0.1,
    beta: 0.01,
    gamma: 0.05,
    dt: 1.0,
};
/**
 * Swarm Coordinator
 *
 * Manages dimensional flux coordination across agent pads.
 */
class SwarmCoordinator {
    swarms = new Map();
    swarmPads = new Map(); // swarmId -> padIds
    padManager;
    fluxParams;
    syncIntervals = new Map();
    constructor(padManager, fluxParams = exports.DEFAULT_FLUX_ODE) {
        this.padManager = padManager;
        this.fluxParams = fluxParams;
    }
    /**
     * Create a new swarm
     */
    createSwarm(config) {
        const id = config.id || `swarm-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 6)}`;
        const swarm = {
            id,
            name: config.name,
            minCoherence: config.minCoherence ?? 0.5,
            fluxDecayRate: config.fluxDecayRate ?? 0.01,
            syncIntervalMs: config.syncIntervalMs ?? 5000,
            maxPads: config.maxPads ?? 10,
        };
        this.swarms.set(id, swarm);
        this.swarmPads.set(id, new Set());
        return swarm;
    }
    /**
     * Get swarm by ID
     */
    getSwarm(id) {
        return this.swarms.get(id);
    }
    /**
     * Get all swarms
     */
    getAllSwarms() {
        return Array.from(this.swarms.values());
    }
    /**
     * Add pad to swarm
     */
    addPadToSwarm(swarmId, padId) {
        const swarm = this.swarms.get(swarmId);
        const pads = this.swarmPads.get(swarmId);
        if (!swarm || !pads)
            return false;
        if (pads.size >= swarm.maxPads)
            return false;
        const pad = this.padManager.getPad(padId);
        if (!pad)
            return false;
        // Remove from previous swarm if any
        if (pad.swarmId) {
            this.removePadFromSwarm(pad.swarmId, padId);
        }
        pads.add(padId);
        // Update pad's swarm reference
        pad.swarmId = swarmId;
        pad.lastSwarmSync = Date.now();
        return true;
    }
    /**
     * Remove pad from swarm
     */
    removePadFromSwarm(swarmId, padId) {
        const pads = this.swarmPads.get(swarmId);
        if (!pads)
            return false;
        const removed = pads.delete(padId);
        if (removed) {
            const pad = this.padManager.getPad(padId);
            if (pad) {
                pad.swarmId = undefined;
                pad.coherenceScore = 1.0; // Reset to self-coherent
            }
        }
        return removed;
    }
    /**
     * Get pads in swarm
     */
    getSwarmPads(swarmId) {
        const padIds = this.swarmPads.get(swarmId);
        if (!padIds)
            return [];
        return Array.from(padIds)
            .map((id) => this.padManager.getPad(id))
            .filter((p) => p !== undefined);
    }
    /**
     * Get swarm state snapshot
     */
    getSwarmState(swarmId) {
        const swarm = this.swarms.get(swarmId);
        const padIds = this.swarmPads.get(swarmId);
        if (!swarm || !padIds)
            return undefined;
        const pads = this.getSwarmPads(swarmId);
        if (pads.length === 0) {
            return {
                id: swarmId,
                name: swarm.name,
                padIds: [],
                avgNu: 0,
                coherence: 0,
                dominantState: 'COLLAPSED',
                lastSync: Date.now(),
                activePads: 0,
                collapsedPads: 0,
            };
        }
        // Calculate average flux
        const avgNu = pads.reduce((sum, p) => sum + p.nu, 0) / pads.length;
        // Calculate coherence (variance-based)
        const variance = pads.reduce((sum, p) => sum + Math.pow(p.nu - avgNu, 2), 0) / pads.length;
        const coherence = Math.max(0, 1 - Math.sqrt(variance) * 2);
        // Count states
        const stateCounts = {
            POLLY: 0,
            QUASI: 0,
            DEMI: 0,
            COLLAPSED: 0,
        };
        for (const pad of pads) {
            stateCounts[pad.dimensionalState]++;
        }
        // Find dominant state
        let dominantState = 'COLLAPSED';
        let maxCount = 0;
        for (const [state, count] of Object.entries(stateCounts)) {
            if (count > maxCount) {
                maxCount = count;
                dominantState = state;
            }
        }
        return {
            id: swarmId,
            name: swarm.name,
            padIds: Array.from(padIds),
            avgNu,
            coherence,
            dominantState,
            lastSync: Date.now(),
            activePads: stateCounts.POLLY + stateCounts.QUASI,
            collapsedPads: stateCounts.COLLAPSED,
        };
    }
    /**
     * Synchronize swarm - update coherence scores
     */
    syncSwarm(swarmId) {
        const state = this.getSwarmState(swarmId);
        if (!state)
            return;
        const pads = this.getSwarmPads(swarmId);
        for (const pad of pads) {
            // Update coherence based on distance from swarm average
            const distance = Math.abs(pad.nu - state.avgNu);
            pad.coherenceScore = Math.max(0, 1 - distance);
            pad.lastSwarmSync = Date.now();
        }
    }
    /**
     * Step flux dynamics using ODE
     * dν/dt = α(ν_target - ν) - β*decay + γ*coherence_boost
     */
    stepFluxODE(swarmId) {
        const swarm = this.swarms.get(swarmId);
        const state = this.getSwarmState(swarmId);
        if (!swarm || !state)
            return;
        const pads = this.getSwarmPads(swarmId);
        const { alpha, beta, gamma, dt } = this.fluxParams;
        for (const pad of pads) {
            // Target is swarm average (attraction to consensus)
            const nuTarget = pad.targetNu ?? state.avgNu;
            // ODE: dν/dt = α(ν_target - ν) - β*decay + γ*coherence
            const attraction = alpha * (nuTarget - pad.nu);
            const decay = beta * swarm.fluxDecayRate;
            const coherenceBoost = gamma * state.coherence * (pad.coherenceScore > 0.5 ? 1 : -1);
            const dNu = (attraction - decay + coherenceBoost) * dt;
            // Update flux
            pad.nu = Math.max(0, Math.min(1, pad.nu + dNu));
            pad.dimensionalState = (0, types_1.getDimensionalState)(pad.nu);
            pad.fluxRate = Math.abs(dNu);
        }
    }
    /**
     * Boost pad flux (e.g., after successful task)
     */
    boostPadFlux(padId, amount = 0.1) {
        const pad = this.padManager.getPad(padId);
        if (!pad)
            return;
        pad.nu = Math.min(1, pad.nu + amount);
        pad.dimensionalState = (0, types_1.getDimensionalState)(pad.nu);
    }
    /**
     * Decay pad flux (e.g., after failure or inactivity)
     */
    decayPadFlux(padId, amount = 0.05) {
        const pad = this.padManager.getPad(padId);
        if (!pad)
            return;
        pad.nu = Math.max(0, pad.nu - amount);
        pad.dimensionalState = (0, types_1.getDimensionalState)(pad.nu);
    }
    /**
     * Collapse pad (set to COLLAPSED state)
     */
    collapsePad(padId) {
        const pad = this.padManager.getPad(padId);
        if (!pad)
            return;
        pad.nu = 0;
        pad.dimensionalState = 'COLLAPSED';
        pad.fluxRate = 0;
        pad.targetNu = undefined;
    }
    /**
     * Revive collapsed pad
     */
    revivePad(padId, targetNu = 0.5) {
        const pad = this.padManager.getPad(padId);
        if (!pad)
            return;
        pad.nu = 0.1; // Start at DEMI
        pad.targetNu = targetNu;
        pad.fluxRate = 0.02;
        pad.dimensionalState = 'DEMI';
    }
    /**
     * Start automatic sync for swarm
     */
    startAutoSync(swarmId) {
        const swarm = this.swarms.get(swarmId);
        if (!swarm)
            return;
        // Clear existing interval
        this.stopAutoSync(swarmId);
        const interval = setInterval(() => {
            this.syncSwarm(swarmId);
            this.stepFluxODE(swarmId);
        }, swarm.syncIntervalMs);
        this.syncIntervals.set(swarmId, interval);
    }
    /**
     * Stop automatic sync for swarm
     */
    stopAutoSync(swarmId) {
        const interval = this.syncIntervals.get(swarmId);
        if (interval) {
            clearInterval(interval);
            this.syncIntervals.delete(swarmId);
        }
    }
    /**
     * Get swarm statistics
     */
    getSwarmStats(swarmId) {
        const pads = this.getSwarmPads(swarmId);
        if (pads.length === 0)
            return undefined;
        const byState = {
            POLLY: 0,
            QUASI: 0,
            DEMI: 0,
            COLLAPSED: 0,
        };
        const byTier = {
            KO: 0,
            AV: 0,
            RU: 0,
            CA: 0,
            UM: 0,
            DR: 0,
        };
        let totalCoherence = 0;
        let totalNu = 0;
        for (const pad of pads) {
            byState[pad.dimensionalState]++;
            byTier[pad.tier]++;
            totalCoherence += pad.coherenceScore;
            totalNu += pad.nu;
        }
        const avgCoherence = totalCoherence / pads.length;
        const avgNu = totalNu / pads.length;
        // Health score: weighted combination
        const healthScore = avgCoherence * 0.3 +
            avgNu * 0.3 +
            (byState.POLLY / pads.length) * 0.2 +
            (1 - byState.COLLAPSED / pads.length) * 0.2;
        return {
            totalPads: pads.length,
            byState,
            byTier,
            avgCoherence,
            avgNu,
            healthScore,
        };
    }
    /**
     * Shutdown coordinator
     */
    shutdown() {
        for (const swarmId of this.syncIntervals.keys()) {
            this.stopAutoSync(swarmId);
        }
    }
}
exports.SwarmCoordinator = SwarmCoordinator;
//# sourceMappingURL=swarm.js.map