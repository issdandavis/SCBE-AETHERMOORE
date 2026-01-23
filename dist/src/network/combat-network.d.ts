/**
 * Combat Network (Redundancy Manager)
 *
 * In combat scenarios, single-path routing is vulnerable. Relays get
 * destroyed or jammed ("caked"). This module implements Multipath Routing
 * with disjoint paths for redundancy.
 *
 * Enhancements:
 * - Full path disjointness (no shared nodes between paths)
 * - Path health monitoring with success/failure tracking
 * - Acknowledgment handling with confirmation and retries
 *
 * References:
 * - arXiv:2204.04489 (ShorTor: Multi-hop Overlay Routing)
 * - Quantum Zeitgeist (Multi-path QKD routing)
 */
import { HybridSpaceCrypto } from './hybrid-crypto.js';
import { RelayNode, SpaceTorRouter } from './space-tor-router.js';
export interface TransmissionResult {
    success: boolean;
    pathId: string;
    latencyMs: number;
    acknowledged: boolean;
    retries: number;
    error?: string;
}
export interface PathHealth {
    pathId: string;
    successCount: number;
    failureCount: number;
    successRate: number;
    averageLatencyMs: number;
    lastUsed: number;
    nodeIds: string[];
}
export interface AcknowledgmentConfig {
    enabled: boolean;
    timeoutMs: number;
    maxRetries: number;
}
export interface CombatNetworkConfig {
    acknowledgment: AcknowledgmentConfig;
    minDisjointPaths: number;
    healthTrackingWindow: number;
}
export declare class CombatNetwork {
    private router;
    private crypto;
    private readonly healthMonitor;
    private readonly config;
    private pendingAcks;
    constructor(router: SpaceTorRouter, crypto: HybridSpaceCrypto, config?: Partial<CombatNetworkConfig>);
    /**
     * Send data with optional combat mode (multipath redundancy)
     *
     * @param data - Data to send
     * @param origin - Origin coordinates (AU)
     * @param dest - Destination coordinates (AU)
     * @param combatMode - Enable multipath redundancy
     * @returns Array of transmission results
     */
    send(data: string, origin: {
        x: number;
        y: number;
        z: number;
    }, dest: {
        x: number;
        y: number;
        z: number;
    }, combatMode: boolean): Promise<TransmissionResult[]>;
    /**
     * Generate multiple fully disjoint paths
     *
     * Enhancement #2: Full path disjointness - no shared nodes between any paths
     *
     * @param origin - Origin coordinates
     * @param dest - Destination coordinates
     * @param minTrust - Minimum trust score
     * @param numPaths - Number of disjoint paths to generate
     * @returns Array of disjoint paths
     */
    generateDisjointPaths(origin: {
        x: number;
        y: number;
        z: number;
    }, dest: {
        x: number;
        y: number;
        z: number;
    }, minTrust: number, numPaths: number): RelayNode[][];
    /**
     * Find a healthy alternative path
     */
    private findHealthyAlternative;
    /**
     * Transmit with acknowledgment handling
     *
     * Enhancement #4: Acknowledgment handling with confirmation and retries
     */
    private transmitWithAck;
    /**
     * Transmit packet to entry node
     */
    private transmit;
    /**
     * Wait for acknowledgment from destination
     */
    private waitForAck;
    /**
     * Receive acknowledgment (called by network layer)
     */
    receiveAck(pathId: string, success: boolean): void;
    /**
     * Calculate transmission latency based on node distance
     */
    private calculateTransmissionLatency;
    /**
     * Sleep utility
     */
    private sleep;
    /**
     * Get network statistics
     */
    getNetworkStats(): {
        totalNodes: number;
        quantumCapableNodes: number;
        averageLoad: number;
        averageTrust: number;
    };
    /**
     * Get path health statistics
     */
    getPathHealthStats(): PathHealth[];
    /**
     * Get health for a specific path
     */
    getPathHealth(nodeIds: string[]): PathHealth;
    /**
     * Check if network has sufficient healthy paths
     */
    hasHealthyRedundancy(origin: {
        x: number;
        y: number;
        z: number;
    }, dest: {
        x: number;
        y: number;
        z: number;
    }, minTrust: number, requiredPaths?: number): boolean;
    /**
     * Clear all health history
     */
    clearHealthHistory(): void;
}
//# sourceMappingURL=combat-network.d.ts.map