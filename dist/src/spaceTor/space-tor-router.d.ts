/**
 * Space Tor Router - 3D Spatial Pathfinding
 *
 * Standard Tor selects nodes randomly. In space, light lag is the enemy.
 * This router uses weighted selection: balances anonymity (randomness)
 * against latency (physical distance) and trust.
 *
 * Integrates with Trust Manager (Layer 3) for Langues Weighting System
 * trust scoring across Six Sacred Tongues.
 *
 * References:
 * - arXiv:2508.17651 (Path Selection Strategies in Tor)
 * - arXiv:2406.15055 (SaTor: Satellite Routing)
 */
import { TrustManager } from './trust-manager';
export interface RelayNode {
    id: string;
    coords: {
        x: number;
        y: number;
        z: number;
    };
    trustScore: number;
    trustVector?: number[];
    quantumCapable: boolean;
    load: number;
}
export declare class SpaceTorRouter {
    private nodes;
    private trustManager;
    constructor(nodes: RelayNode[], trustManager?: TrustManager);
    /**
     * Core Logic: Select a 3-hop path balancing Latency vs. Trust
     *
     * Uses Layer 3 (Langues Metric Tensor) for advanced trust scoring
     * when trustVector is available, falls back to legacy trustScore.
     *
     * @param origin - Origin coordinates (AU from Sol)
     * @param dest - Destination coordinates (AU from Sol)
     * @param minTrust - Minimum trust score threshold (default 60)
     * @returns Array of 3 RelayNodes [entry, middle, exit]
     */
    calculatePath(origin: {
        x: number;
        y: number;
        z: number;
    }, dest: {
        x: number;
        y: number;
        z: number;
    }, minTrust?: number): RelayNode[];
    /**
     * Get node trust score using Layer 3 (Langues Metric Tensor)
     *
     * If trustVector is available, uses TrustManager for advanced scoring.
     * Otherwise, falls back to legacy trustScore (0-100).
     *
     * @param node - Relay node
     * @returns Trust score (0-100)
     */
    private getNodeTrustScore;
    /**
     * Weight Calculation: Lower score is better
     *
     * Cost = (Distance * Weight) - (Trust * InverseWeight)
     *
     * Uses Layer 3 trust scoring when available.
     *
     * @param pool - Candidate nodes
     * @param target - Target coordinates
     * @param distWeight - Weight for distance (0.0-1.0)
     * @returns Best node based on weighted cost
     */
    private selectWeightedNode;
    /**
     * Calculate 3D Euclidean distance in Astronomical Units
     *
     * @param p1 - First point
     * @param p2 - Second point
     * @returns Distance in AU
     */
    private distance3D;
    /**
     * Get all nodes
     */
    getNodes(): RelayNode[];
    /**
     * Update node load
     */
    updateNodeLoad(nodeId: string, load: number): void;
    /**
     * Update node trust score (legacy method)
     *
     * For Layer 3 integration, use updateNodeTrustVector instead.
     */
    updateNodeTrust(nodeId: string, trustScore: number): void;
    /**
     * Update node trust vector (Layer 3)
     *
     * Updates the 6D trust vector for Langues Metric Tensor scoring.
     *
     * @param nodeId - Node identifier
     * @param trustVector - 6D trust vector (one per Sacred Tongue)
     */
    updateNodeTrustVector(nodeId: string, trustVector: number[]): void;
    /**
     * Get trust manager instance
     */
    getTrustManager(): TrustManager;
}
//# sourceMappingURL=space-tor-router.d.ts.map