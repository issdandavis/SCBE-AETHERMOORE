"use strict";
/**
 * Polly Pads - Drone Core
 *
 * The identity and base configuration of each AI agent in the fleet.
 * "Same DNA, different specializations" - Clone Trooper doctrine
 *
 * @module fleet/polly-pads/drone-core
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.DroneCore = void 0;
exports.createReconDrone = createReconDrone;
exports.createCoderDrone = createCoderDrone;
exports.createDeployDrone = createDeployDrone;
exports.createResearchDrone = createResearchDrone;
exports.createGuardDrone = createGuardDrone;
const crypto_1 = require("crypto");
// ============================================================================
// Constants
// ============================================================================
/** Golden ratio for harmonic calculations */
const PHI = 1.618033988749895;
/** Perfect fifth ratio for H(d,R) */
const R_PERFECT_FIFTH = 1.5;
/** Tongue phase offsets (60° intervals) */
const TONGUE_PHASES = {
    KO: 0, // Kor'aelin - Intent/Nonce
    AV: 60, // Avali - Context
    RU: 120, // Runethic - Binding
    CA: 180, // Cassisivadan - Ciphertext
    UM: 240, // Umbroth - Redaction
    DR: 300, // Draumric - Structure
};
/** Class configurations */
const CLASS_CONFIG = {
    RECON: { maxLoadout: 4, defaultTongue: 'KO', designation: 'CT-7567' },
    CODER: { maxLoadout: 6, defaultTongue: 'AV', designation: 'CT-5555' },
    DEPLOY: { maxLoadout: 5, defaultTongue: 'RU', designation: 'CT-21-0408' },
    RESEARCH: { maxLoadout: 8, defaultTongue: 'CA', designation: 'CT-27-5555' },
    GUARD: { maxLoadout: 3, defaultTongue: 'DR', designation: 'CT-99' },
};
// ============================================================================
// Drone Core Class
// ============================================================================
class DroneCore {
    id;
    callsign;
    class;
    maxLoadout;
    _spectralIdentity;
    _fluxState = 'Polly';
    _loadout = new Map();
    _missionLog = [];
    constructor(config) {
        const classConfig = CLASS_CONFIG[config.class];
        this.id = config.id || this.generateDroneId(classConfig.designation);
        this.callsign = config.callsign;
        this.class = config.class;
        this.maxLoadout = classConfig.maxLoadout;
        const tongue = config.initialTongue || classConfig.defaultTongue;
        this._spectralIdentity = this.initSpectralIdentity(tongue);
        this.log(`Drone ${this.id} "${this.callsign}" initialized`);
        this.log(`Class: ${this.class}, Tongue: ${tongue}, Max Loadout: ${this.maxLoadout}`);
    }
    // --------------------------------------------------------------------------
    // Getters
    // --------------------------------------------------------------------------
    get spectralIdentity() {
        return { ...this._spectralIdentity };
    }
    get fluxState() {
        return this._fluxState;
    }
    get loadout() {
        return Array.from(this._loadout.values());
    }
    get loadoutCount() {
        return this._loadout.size;
    }
    get trustRadius() {
        return this._spectralIdentity.trustRadius;
    }
    // --------------------------------------------------------------------------
    // Identity & Trust
    // --------------------------------------------------------------------------
    generateDroneId(designation) {
        const suffix = (0, crypto_1.randomBytes)(2).toString('hex').toUpperCase();
        return `${designation}-${suffix}`;
    }
    initSpectralIdentity(tongue) {
        const phase = TONGUE_PHASES[tongue];
        const tongueIndex = Object.keys(TONGUE_PHASES).indexOf(tongue);
        // Initialize at center of Poincaré ball (trusted)
        const trustRadius = 0.1;
        // 6D vector based on tongue
        const vector6D = Array(6)
            .fill(0)
            .map((_, i) => {
            if (i === tongueIndex)
                return trustRadius;
            return 0;
        });
        return { tongue, phase, trustRadius, vector6D };
    }
    /**
     * Get flux state from trust radius (ν value)
     */
    calculateFluxState(nu) {
        if (nu >= 0.9)
            return 'Polly';
        if (nu >= 0.5)
            return 'Quasi';
        if (nu >= 0.1)
            return 'Demi';
        return 'Collapsed';
    }
    /**
     * Update trust radius based on behavior
     * Moving toward edge = less trusted
     */
    updateTrust(delta) {
        const newRadius = Math.max(0, Math.min(1, this._spectralIdentity.trustRadius + delta));
        this._spectralIdentity.trustRadius = newRadius;
        // Recalculate flux state (inverse of trust - higher trust = higher ν)
        const nu = 1 - newRadius;
        this._fluxState = this.calculateFluxState(nu);
        this.log(`Trust updated: radius=${newRadius.toFixed(3)}, flux=${this._fluxState}`);
    }
    // --------------------------------------------------------------------------
    // Harmonic Scaling (Your IP!)
    // --------------------------------------------------------------------------
    /**
     * score = 1 / (1 + d_H + 2 * phaseDeviation)
     * The Harmonic Scaling Law - bounded risk scoring.
     */
    harmonicScaling(d, phaseDeviation = 0) {
        return 1 / (1 + d + 2 * phaseDeviation);
    }
    /**
     * Calculate cost for an action based on trust distance
     */
    calculateActionCost(actionDepth) {
        // Further from center = higher cost
        const distanceFromCenter = this._spectralIdentity.trustRadius;
        const effectiveDepth = actionDepth * (1 + distanceFromCenter * 5);
        return this.harmonicScaling(effectiveDepth);
    }
    // --------------------------------------------------------------------------
    // Capability Management (Hot-Swap)
    // --------------------------------------------------------------------------
    /**
     * Check if drone can load a capability
     */
    canLoadCapability(capability) {
        // Check loadout limit
        if (this._loadout.size >= this.maxLoadout) {
            return { allowed: false, reason: 'Loadout full' };
        }
        // Check trust requirement
        if (this._spectralIdentity.trustRadius > 1 - capability.minTrust) {
            return {
                allowed: false,
                reason: `Insufficient trust: ${this._spectralIdentity.trustRadius.toFixed(2)} > ${(1 - capability.minTrust).toFixed(2)} max`,
            };
        }
        // Check tongue compatibility
        if (capability.requiredTongue && capability.requiredTongue !== this._spectralIdentity.tongue) {
            return {
                allowed: false,
                reason: `Wrong tongue: requires ${capability.requiredTongue}, have ${this._spectralIdentity.tongue}`,
            };
        }
        // Check dependencies
        for (const dep of capability.dependencies) {
            if (!this._loadout.has(dep)) {
                return { allowed: false, reason: `Missing dependency: ${dep}` };
            }
        }
        return { allowed: true, reason: 'OK' };
    }
    /**
     * Load a capability (hot-swap)
     */
    loadCapability(capability) {
        const check = this.canLoadCapability(capability);
        if (!check.allowed) {
            this.log(`Failed to load ${capability.name}: ${check.reason}`);
            return false;
        }
        // Calculate cost using Harmonic Scaling
        const cost = this.calculateActionCost(2); // Loading = depth 2
        this.log(`Loading ${capability.name} v${capability.version} (cost: ${cost.toFixed(2)} units)`);
        capability.active = true;
        this._loadout.set(capability.id, capability);
        this.log(`✓ Capability ${capability.name} activated`);
        return true;
    }
    /**
     * Unload a capability
     */
    unloadCapability(capabilityId) {
        const capability = this._loadout.get(capabilityId);
        if (!capability) {
            this.log(`Capability ${capabilityId} not found`);
            return false;
        }
        // Check if other capabilities depend on this one
        for (const [id, cap] of this._loadout) {
            if (cap.dependencies.includes(capabilityId)) {
                this.log(`Cannot unload ${capabilityId}: ${id} depends on it`);
                return false;
            }
        }
        this._loadout.delete(capabilityId);
        this.log(`✓ Capability ${capability.name} unloaded`);
        return true;
    }
    // --------------------------------------------------------------------------
    // Cymatic Voxel Storage (Your IP!)
    // --------------------------------------------------------------------------
    /**
     * Check if drone can access a voxel using Chladni mathematics
     *
     * cos(n·π·x)·cos(m·π·y) - cos(m·π·x)·cos(n·π·y) = 0
     *
     * Data readable ONLY at nodal lines (zero points)
     */
    canAccessVoxel(x, y) {
        const n = this._spectralIdentity.phase / 60; // velocity mode
        const m = this._spectralIdentity.trustRadius * 6; // security mode
        const chladni = Math.cos(n * Math.PI * x) * Math.cos(m * Math.PI * y) -
            Math.cos(m * Math.PI * x) * Math.cos(n * Math.PI * y);
        // Access granted at nodal lines (within epsilon)
        return Math.abs(chladni) < 0.001;
    }
    // --------------------------------------------------------------------------
    // Logging
    // --------------------------------------------------------------------------
    log(message) {
        const timestamp = new Date().toISOString();
        const entry = `[${timestamp}] [${this.id}] ${message}`;
        this._missionLog.push(entry);
        // Keep log size manageable
        if (this._missionLog.length > 1000) {
            this._missionLog = this._missionLog.slice(-500);
        }
    }
    getMissionLog() {
        return [...this._missionLog];
    }
    // --------------------------------------------------------------------------
    // Serialization
    // --------------------------------------------------------------------------
    toJSON() {
        return {
            id: this.id,
            callsign: this.callsign,
            class: this.class,
            spectralIdentity: this._spectralIdentity,
            fluxState: this._fluxState,
            loadout: Array.from(this._loadout.values()),
            maxLoadout: this.maxLoadout,
        };
    }
    static fromJSON(data) {
        const drone = new DroneCore({
            id: data.id,
            callsign: data.callsign,
            class: data.class,
            initialTongue: data.spectralIdentity?.tongue,
        });
        // Restore state
        drone._spectralIdentity = data.spectralIdentity;
        drone._fluxState = data.fluxState;
        // Restore loadout
        for (const cap of data.loadout || []) {
            drone._loadout.set(cap.id, cap);
        }
        return drone;
    }
}
exports.DroneCore = DroneCore;
// ============================================================================
// Factory Functions
// ============================================================================
/**
 * Create a RECON drone (browser automation specialist)
 */
function createReconDrone(callsign) {
    return new DroneCore({ callsign, class: 'RECON' });
}
/**
 * Create a CODER drone (code generation specialist)
 */
function createCoderDrone(callsign) {
    return new DroneCore({ callsign, class: 'CODER' });
}
/**
 * Create a DEPLOY drone (infrastructure specialist)
 */
function createDeployDrone(callsign) {
    return new DroneCore({ callsign, class: 'DEPLOY' });
}
/**
 * Create a RESEARCH drone (information gathering specialist)
 */
function createResearchDrone(callsign) {
    return new DroneCore({ callsign, class: 'RESEARCH' });
}
/**
 * Create a GUARD drone (security specialist)
 */
function createGuardDrone(callsign) {
    return new DroneCore({ callsign, class: 'GUARD' });
}
// ============================================================================
// Exports
// ============================================================================
exports.default = DroneCore;
//# sourceMappingURL=drone-core.js.map