"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.CombatNetwork = void 0;
class CombatNetwork {
    router;
    crypto;
    constructor(router, crypto) {
        this.router = router;
        this.crypto = crypto;
    }
    /**
     * Send data with optional combat mode (multipath redundancy)
     *
     * @param data - Data to send
     * @param origin - Origin coordinates (AU)
     * @param dest - Destination coordinates (AU)
     * @param combatMode - Enable multipath redundancy
     * @returns Array of transmission results
     */
    async send(data, origin, dest, combatMode) {
        const payload = Buffer.from(data);
        const results = [];
        if (combatMode) {
            // 1. Generate Disjoint Paths (Paths that don't share middle nodes)
            const pathA = this.router.calculatePath(origin, dest, 70);
            const pathB = this.generateDisjointPath(pathA, origin, dest, 70);
            console.log(`[COMBAT] Routing via Primary: ${pathA.map((n) => n.id).join(' -> ')}`);
            console.log(`[COMBAT] Routing via Backup:  ${pathB.map((n) => n.id).join(' -> ')}`);
            // 2. Encrypt & Send Parallel
            const [onionA, onionB] = await Promise.all([
                this.crypto.buildOnion(payload, pathA),
                this.crypto.buildOnion(payload, pathB),
            ]);
            // 3. Dispatch (Fire and Forget)
            const [resultA, resultB] = await Promise.all([
                this.transmit(pathA[0], onionA, 'PRIMARY'),
                this.transmit(pathB[0], onionB, 'BACKUP'),
            ]);
            results.push(resultA, resultB);
        }
        else {
            // Standard Routing
            const path = this.router.calculatePath(origin, dest, 50);
            console.log(`[STANDARD] Routing via: ${path.map((n) => n.id).join(' -> ')}`);
            const onion = await this.crypto.buildOnion(payload, path);
            const result = await this.transmit(path[0], onion, 'STANDARD');
            results.push(result);
        }
        return results;
    }
    /**
     * Generate a disjoint path that doesn't share middle nodes with primary path
     *
     * @param primaryPath - Primary path to avoid
     * @param origin - Origin coordinates
     * @param dest - Destination coordinates
     * @param minTrust - Minimum trust score
     * @returns Disjoint path
     */
    generateDisjointPath(primaryPath, origin, dest, minTrust) {
        const primaryMiddleId = primaryPath[1].id;
        const maxAttempts = 10;
        for (let attempt = 0; attempt < maxAttempts; attempt++) {
            try {
                const path = this.router.calculatePath(origin, dest, minTrust);
                // Check if middle node is different
                if (path[1].id !== primaryMiddleId) {
                    return path;
                }
            }
            catch (error) {
                // Path calculation failed, try again
                continue;
            }
        }
        // Fallback: return any valid path (better than failing)
        console.warn('[COMBAT] Could not find fully disjoint path, using fallback');
        return this.router.calculatePath(origin, dest, minTrust);
    }
    /**
     * Transmit packet to entry node
     *
     * @param entryNode - Entry relay node
     * @param packet - Encrypted onion packet
     * @param pathId - Path identifier for logging
     * @returns Transmission result
     */
    async transmit(entryNode, packet, pathId) {
        const startTime = Date.now();
        try {
            // Hardware interface mock
            console.log(`[${pathId}] Transmitting ${packet.length} bytes to Entry Node: ${entryNode.id}`);
            // Simulate transmission delay based on distance
            // In production, this would interface with actual radio/laser comm hardware
            const latencyMs = this.calculateTransmissionLatency(entryNode);
            await this.sleep(latencyMs);
            // Update node load
            this.router.updateNodeLoad(entryNode.id, entryNode.load + 0.1);
            return {
                success: true,
                pathId,
                latencyMs: Date.now() - startTime,
            };
        }
        catch (error) {
            return {
                success: false,
                pathId,
                latencyMs: Date.now() - startTime,
                error: error instanceof Error ? error.message : 'Unknown error',
            };
        }
    }
    /**
     * Calculate transmission latency based on node distance
     *
     * @param node - Relay node
     * @returns Latency in milliseconds
     */
    calculateTransmissionLatency(node) {
        // Speed of light: ~300,000 km/s
        // 1 AU ≈ 150 million km
        // Light travel time for 1 AU ≈ 500 seconds = 500,000 ms
        const distance = Math.sqrt(node.coords.x ** 2 + node.coords.y ** 2 + node.coords.z ** 2);
        return distance * 500000; // ms per AU
    }
    /**
     * Sleep utility for simulating delays
     */
    sleep(ms) {
        return new Promise((resolve) => setTimeout(resolve, ms));
    }
    /**
     * Get network statistics
     */
    getNetworkStats() {
        const nodes = this.router.getNodes();
        return {
            totalNodes: nodes.length,
            quantumCapableNodes: nodes.filter((n) => n.quantumCapable).length,
            averageLoad: nodes.reduce((sum, n) => sum + n.load, 0) / nodes.length,
            averageTrust: nodes.reduce((sum, n) => sum + n.trustScore, 0) / nodes.length,
        };
    }
}
exports.CombatNetwork = CombatNetwork;
//# sourceMappingURL=combat-network.js.map