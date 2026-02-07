/**
 * Polly Pads - Capability Store
 *
 * Hot-swappable modules that drones can load/unload.
 * Each capability is SCBE-signed and PHDM-validated.
 *
 * @module fleet/polly-pads/capability-store
 */
import { Capability, SacredTongue, DroneClass } from './drone-core.js';
/** Capability category */
export type CapabilityCategory = 'browser' | 'coding' | 'deploy' | 'research' | 'security' | 'utility';
/** Capability manifest in the store */
export interface CapabilityManifest {
    id: string;
    name: string;
    version: string;
    description: string;
    category: CapabilityCategory;
    minTrust: number;
    requiredTongue?: SacredTongue;
    requiredClass?: DroneClass[];
    dependencies: string[];
    entryPoint: string;
    wasmBundle?: string;
    size: number;
    author: string;
    license: string;
    scbeSignature: string;
    phdmHash: string;
    downloads: number;
    rating: number;
    tags: string[];
}
/** Store query options */
export interface StoreQuery {
    category?: CapabilityCategory;
    tongue?: SacredTongue;
    class?: DroneClass;
    maxTrust?: number;
    search?: string;
}
export declare class CapabilityStore {
    private capabilities;
    private signatureKey;
    constructor(signatureKey?: Buffer);
    /**
     * Register a capability in the store
     */
    registerCapability(manifest: CapabilityManifest): void;
    /**
     * Get a capability by ID
     */
    getCapability(id: string): CapabilityManifest | undefined;
    /**
     * Search capabilities
     */
    searchCapabilities(query: StoreQuery): CapabilityManifest[];
    /**
     * Get capabilities compatible with a drone
     */
    getCompatibleCapabilities(tongue: SacredTongue, droneClass: DroneClass, trustRadius: number): CapabilityManifest[];
    /**
     * Convert manifest to loadable Capability
     */
    toCapability(manifest: CapabilityManifest): Capability;
    /**
     * Sign a capability with SCBE
     */
    private signCapability;
    /**
     * Generate PHDM hash for control flow integrity
     */
    private generatePHDMHash;
    /**
     * Verify capability signature
     */
    verifyCapability(manifest: CapabilityManifest): boolean;
    getStats(): {
        total: number;
        byCategory: Record<string, number>;
    };
}
export declare const defaultStore: CapabilityStore;
export default CapabilityStore;
//# sourceMappingURL=capability-store.d.ts.map