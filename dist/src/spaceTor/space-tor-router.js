"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.SpaceTorRouter = void 0;
const trust_manager_1 = require("./trust-manager");
class SpaceTorRouter {
    nodes;
    trustManager;
    constructor(nodes, trustManager) {
        this.nodes = new Map(nodes.map((n) => [n.id, n]));
        this.trustManager = trustManager || new trust_manager_1.TrustManager();
        // Initialize trust manager with node trust vectors
        for (const node of nodes) {
            if (node.trustVector) {
                this.trustManager.computeTrustScore(node.id, node.trustVector);
            }
        }
    }
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
    calculatePath(origin, dest, minTrust = 60) {
        // 1. Filter usable nodes with Layer 3 trust scoring
        const candidates = Array.from(this.nodes.values()).filter((n) => {
            const trust = this.getNodeTrustScore(n);
            return trust >= minTrust && n.load < 0.9;
        });
        if (candidates.length < 3) {
            throw new Error(`Insufficient relay nodes (need 3, have ${candidates.length})`);
        }
        // 2. Entry Node: Prioritize trust (Guard Node) close to origin
        const entryCandidates = candidates.filter((n) => {
            const trust = this.getNodeTrustScore(n);
            return trust > 80;
        });
        if (entryCandidates.length === 0) {
            throw new Error('No high-trust entry nodes available');
        }
        const entry = this.selectWeightedNode(entryCandidates, origin, 0.7); // 70% weight on distance
        // 3. Exit Node: Prioritize exit capabilities close to destination
        const exit = this.selectWeightedNode(candidates, dest, 0.8);
        // 4. Middle Node: Maximum entropy (randomness) to break correlation
        // Must not be Entry or Exit
        const middleCandidates = candidates.filter((n) => n.id !== entry.id && n.id !== exit.id);
        if (middleCandidates.length === 0) {
            throw new Error('No middle node candidates available');
        }
        const middle = middleCandidates[Math.floor(Math.random() * middleCandidates.length)];
        return [entry, middle, exit];
    }
    /**
     * Get node trust score using Layer 3 (Langues Metric Tensor)
     *
     * If trustVector is available, uses TrustManager for advanced scoring.
     * Otherwise, falls back to legacy trustScore (0-100).
     *
     * @param node - Relay node
     * @returns Trust score (0-100)
     */
    getNodeTrustScore(node) {
        if (node.trustVector && node.trustVector.length === 6) {
            // Use Layer 3 (Langues Metric Tensor)
            const score = this.trustManager.computeTrustScore(node.id, node.trustVector);
            // Convert normalized score [0,1] to legacy scale [0,100]
            // Invert because low L = high trust
            return (1 - score.normalized) * 100;
        }
        // Fall back to legacy trust score
        return node.trustScore;
    }
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
    selectWeightedNode(pool, target, distWeight) {
        return pool.reduce((best, current) => {
            const dist = this.distance3D(current.coords, target);
            const trust = this.getNodeTrustScore(current);
            // Cost = (Distance * Weight) - (Trust * InverseWeight)
            const cost = dist * distWeight - trust * (1 - distWeight);
            const bestDist = this.distance3D(best.coords, target);
            const bestTrust = this.getNodeTrustScore(best);
            const bestCost = bestDist * distWeight - bestTrust * (1 - distWeight);
            return cost < bestCost ? current : best;
        });
    }
    /**
     * Calculate 3D Euclidean distance in Astronomical Units
     *
     * @param p1 - First point
     * @param p2 - Second point
     * @returns Distance in AU
     */
    distance3D(p1, p2) {
        return Math.sqrt(Math.pow(p2.x - p1.x, 2) + Math.pow(p2.y - p1.y, 2) + Math.pow(p2.z - p1.z, 2));
    }
    /**
     * Get all nodes
     */
    getNodes() {
        return Array.from(this.nodes.values());
    }
    /**
     * Update node load
     */
    updateNodeLoad(nodeId, load) {
        const node = this.nodes.get(nodeId);
        if (node) {
            node.load = Math.max(0, Math.min(1, load));
        }
    }
    /**
     * Update node trust score (legacy method)
     *
     * For Layer 3 integration, use updateNodeTrustVector instead.
     */
    updateNodeTrust(nodeId, trustScore) {
        const node = this.nodes.get(nodeId);
        if (node) {
            node.trustScore = Math.max(0, Math.min(100, trustScore));
        }
    }
    /**
     * Update node trust vector (Layer 3)
     *
     * Updates the 6D trust vector for Langues Metric Tensor scoring.
     *
     * @param nodeId - Node identifier
     * @param trustVector - 6D trust vector (one per Sacred Tongue)
     */
    updateNodeTrustVector(nodeId, trustVector) {
        const node = this.nodes.get(nodeId);
        if (node) {
            node.trustVector = trustVector;
            this.trustManager.computeTrustScore(nodeId, trustVector);
        }
    }
    /**
     * Get trust manager instance
     */
    getTrustManager() {
        return this.trustManager;
    }
}
exports.SpaceTorRouter = SpaceTorRouter;
//# sourceMappingURL=space-tor-router.js.map