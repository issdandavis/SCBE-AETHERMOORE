"use strict";
/**
 * Space-Tor Router
 *
 * Onion routing for space networks with relay node management.
 * Implements path calculation with trust scoring and load balancing.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.SpaceTorRouter = void 0;
class SpaceTorRouter {
    nodes = new Map();
    minPathLength = 3; // Entry, Middle, Exit
    constructor(initialNodes) {
        if (initialNodes) {
            for (const node of initialNodes) {
                this.nodes.set(node.id, node);
            }
        }
    }
    /**
     * Register a relay node
     */
    registerNode(node) {
        this.nodes.set(node.id, node);
    }
    /**
     * Remove a relay node (destroyed/offline)
     */
    removeNode(nodeId) {
        return this.nodes.delete(nodeId);
    }
    /**
     * Get all registered nodes
     */
    getNodes() {
        return Array.from(this.nodes.values());
    }
    /**
     * Get a specific node by ID
     */
    getNode(nodeId) {
        return this.nodes.get(nodeId);
    }
    /**
     * Update node load
     */
    updateNodeLoad(nodeId, load) {
        const node = this.nodes.get(nodeId);
        if (node) {
            node.load = Math.min(1, Math.max(0, load));
        }
    }
    /**
     * Update node trust score
     */
    updateNodeTrust(nodeId, trustScore) {
        const node = this.nodes.get(nodeId);
        if (node) {
            node.trustScore = Math.min(100, Math.max(0, trustScore));
        }
    }
    /**
     * Calculate optimal path from origin to destination
     *
     * @param origin - Origin coordinates (AU)
     * @param dest - Destination coordinates (AU)
     * @param minTrust - Minimum trust score for nodes
     * @param constraints - Additional path constraints
     * @returns Array of relay nodes forming the path
     */
    calculatePath(origin, dest, minTrust, constraints) {
        const eligibleNodes = this.getEligibleNodes(minTrust, constraints);
        if (eligibleNodes.length < this.minPathLength) {
            throw new Error(`Insufficient eligible nodes: ${eligibleNodes.length} < ${this.minPathLength}`);
        }
        // Select Entry Node (closest to origin with good trust)
        const entryNode = this.selectNode(eligibleNodes, origin, 'entry', constraints?.excludeNodes);
        // Select Exit Node (closest to destination)
        const remainingForExit = eligibleNodes.filter(n => n.id !== entryNode.id);
        const exitNode = this.selectNode(remainingForExit, dest, 'exit', constraints?.excludeNodes);
        // Select Middle Node (balanced between entry and exit, highest trust)
        const remainingForMiddle = remainingForExit.filter(n => n.id !== exitNode.id);
        const middleNode = this.selectMiddleNode(remainingForMiddle, entryNode, exitNode, constraints?.excludeNodes);
        return [entryNode, middleNode, exitNode];
    }
    /**
     * Calculate path with specific node exclusions (for disjoint paths)
     */
    calculateDisjointPath(origin, dest, minTrust, excludeNodes) {
        return this.calculatePath(origin, dest, minTrust, { excludeNodes });
    }
    /**
     * Get nodes that meet minimum trust and other constraints
     */
    getEligibleNodes(minTrust, constraints) {
        return Array.from(this.nodes.values()).filter(node => {
            if (node.trustScore < minTrust)
                return false;
            if (constraints?.maxLoad !== undefined && node.load > constraints.maxLoad)
                return false;
            if (constraints?.requireQuantum && !node.quantumCapable)
                return false;
            if (constraints?.excludeNodes?.has(node.id))
                return false;
            return true;
        });
    }
    /**
     * Select optimal node based on role and distance
     */
    selectNode(candidates, target, role, excludeNodes) {
        const filtered = excludeNodes
            ? candidates.filter(n => !excludeNodes.has(n.id))
            : candidates;
        if (filtered.length === 0) {
            throw new Error(`No eligible nodes for ${role} role`);
        }
        // Score based on distance, trust, and load
        return filtered.reduce((best, node) => {
            const distance = this.calculateDistance(node.coords, target);
            const nodeScore = this.scoreNode(node, distance);
            const bestDistance = this.calculateDistance(best.coords, target);
            const bestScore = this.scoreNode(best, bestDistance);
            return nodeScore > bestScore ? node : best;
        });
    }
    /**
     * Select middle node optimized for security and balance
     */
    selectMiddleNode(candidates, entry, exit, excludeNodes) {
        const filtered = excludeNodes
            ? candidates.filter(n => !excludeNodes.has(n.id))
            : candidates;
        if (filtered.length === 0) {
            throw new Error('No eligible nodes for middle role');
        }
        // Middle node should be somewhat equidistant and have high trust
        const midpoint = {
            x: (entry.coords.x + exit.coords.x) / 2,
            y: (entry.coords.y + exit.coords.y) / 2,
            z: (entry.coords.z + exit.coords.z) / 2
        };
        return filtered.reduce((best, node) => {
            const distance = this.calculateDistance(node.coords, midpoint);
            // Prioritize trust for middle node (security critical)
            const nodeScore = node.trustScore * 2 - distance * 0.5 - node.load * 10;
            const bestDistance = this.calculateDistance(best.coords, midpoint);
            const bestScore = best.trustScore * 2 - bestDistance * 0.5 - best.load * 10;
            return nodeScore > bestScore ? node : best;
        });
    }
    /**
     * Calculate distance between two points (AU)
     */
    calculateDistance(a, b) {
        return Math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2);
    }
    /**
     * Score a node based on trust, distance, and load
     */
    scoreNode(node, distance) {
        // Higher trust = better, lower distance = better, lower load = better
        return node.trustScore - distance * 10 - node.load * 20;
    }
}
exports.SpaceTorRouter = SpaceTorRouter;
//# sourceMappingURL=space-tor-router.js.map