/**
 * Polly Pads - Drone Core
 *
 * The identity and base configuration of each AI agent in the fleet.
 * "Same DNA, different specializations" - Clone Trooper doctrine
 *
 * @module fleet/polly-pads/drone-core
 */
/** Sacred Tongue for domain separation */
export type SacredTongue = 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';
/** Drone specialization class */
export type DroneClass = 'RECON' | 'CODER' | 'DEPLOY' | 'RESEARCH' | 'GUARD';
/** Dimensional flux state */
export type FluxState = 'Polly' | 'Quasi' | 'Demi' | 'Collapsed';
/** Trust decision from SCBE */
export type TrustDecision = 'ALLOW' | 'QUARANTINE' | 'DENY';
/** Spectral identity in the Poincaré ball */
export interface SpectralIdentity {
    tongue: SacredTongue;
    phase: number;
    trustRadius: number;
    vector6D: number[];
}
/** Capability that can be loaded into a drone */
export interface Capability {
    id: string;
    name: string;
    version: string;
    minTrust: number;
    requiredTongue?: SacredTongue;
    dependencies: string[];
    entryPoint: string;
    active: boolean;
}
/** Drone core configuration */
export interface DroneCoreConfig {
    id?: string;
    callsign: string;
    class: DroneClass;
    initialTongue?: SacredTongue;
}
export declare class DroneCore {
    readonly id: string;
    readonly callsign: string;
    readonly class: DroneClass;
    readonly maxLoadout: number;
    private _spectralIdentity;
    private _fluxState;
    private _loadout;
    private _missionLog;
    constructor(config: DroneCoreConfig);
    get spectralIdentity(): SpectralIdentity;
    get fluxState(): FluxState;
    get loadout(): Capability[];
    get loadoutCount(): number;
    get trustRadius(): number;
    private generateDroneId;
    private initSpectralIdentity;
    /**
     * Get flux state from trust radius (ν value)
     */
    private calculateFluxState;
    /**
     * Update trust radius based on behavior
     * Moving toward edge = less trusted
     */
    updateTrust(delta: number): void;
    /**
     * H(d, R) = R^(d²)
     * The Harmonic Scaling Law - your invention!
     */
    harmonicScaling(d: number, R?: number): number;
    /**
     * Calculate cost for an action based on trust distance
     */
    calculateActionCost(actionDepth: number): number;
    /**
     * Check if drone can load a capability
     */
    canLoadCapability(capability: Capability): {
        allowed: boolean;
        reason: string;
    };
    /**
     * Load a capability (hot-swap)
     */
    loadCapability(capability: Capability): boolean;
    /**
     * Unload a capability
     */
    unloadCapability(capabilityId: string): boolean;
    /**
     * Check if drone can access a voxel using Chladni mathematics
     *
     * cos(n·π·x)·cos(m·π·y) - cos(m·π·x)·cos(n·π·y) = 0
     *
     * Data readable ONLY at nodal lines (zero points)
     */
    canAccessVoxel(x: number, y: number): boolean;
    private log;
    getMissionLog(): string[];
    toJSON(): object;
    static fromJSON(data: any): DroneCore;
}
/**
 * Create a RECON drone (browser automation specialist)
 */
export declare function createReconDrone(callsign: string): DroneCore;
/**
 * Create a CODER drone (code generation specialist)
 */
export declare function createCoderDrone(callsign: string): DroneCore;
/**
 * Create a DEPLOY drone (infrastructure specialist)
 */
export declare function createDeployDrone(callsign: string): DroneCore;
/**
 * Create a RESEARCH drone (information gathering specialist)
 */
export declare function createResearchDrone(callsign: string): DroneCore;
/**
 * Create a GUARD drone (security specialist)
 */
export declare function createGuardDrone(callsign: string): DroneCore;
export default DroneCore;
//# sourceMappingURL=drone-core.d.ts.map