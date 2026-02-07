/**
 * Combat Network (Redundancy Manager)
 *
 * In combat scenarios, single-path routing is vulnerable. Relays get
 * destroyed or jammed ("caked"). This module implements Multipath Routing
 * with disjoint paths for redundancy.
 *
 * References:
 * - arXiv:2204.04489 (ShorTor: Multi-hop Overlay Routing)
 * - Quantum Zeitgeist (Multi-path QKD routing)
 */
import { HybridSpaceCrypto } from './hybrid-crypto';
import { SpaceTorRouter } from './space-tor-router';
export interface TransmissionResult {
    success: boolean;
    pathId: string;
    latencyMs: number;
    error?: string;
}
export declare class CombatNetwork {
    private router;
    private crypto;
    constructor(router: SpaceTorRouter, crypto: HybridSpaceCrypto);
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
     * Generate a disjoint path that doesn't share middle nodes with primary path
     *
     * @param primaryPath - Primary path to avoid
     * @param origin - Origin coordinates
     * @param dest - Destination coordinates
     * @param minTrust - Minimum trust score
     * @returns Disjoint path
     */
    private generateDisjointPath;
    /**
     * Transmit packet to entry node
     *
     * @param entryNode - Entry relay node
     * @param packet - Encrypted onion packet
     * @param pathId - Path identifier for logging
     * @returns Transmission result
     */
    private transmit;
    /**
     * Calculate transmission latency based on node distance
     *
     * @param node - Relay node
     * @returns Latency in milliseconds
     */
    private calculateTransmissionLatency;
    /**
     * Sleep utility for simulating delays
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
}
//# sourceMappingURL=combat-network.d.ts.map