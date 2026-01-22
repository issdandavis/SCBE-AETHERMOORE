/**
 * Space-Tor Router
 *
 * Onion routing for space networks with relay node management.
 * Implements path calculation with trust scoring and load balancing.
 */
export interface RelayNode {
    id: string;
    coords: {
        x: number;
        y: number;
        z: number;
    };
    trustScore: number;
    load: number;
    quantumCapable: boolean;
    lastSeen: number;
    bandwidth: number;
}
export interface PathConstraints {
    minTrust: number;
    maxLoad?: number;
    requireQuantum?: boolean;
    excludeNodes?: Set<string>;
}
export declare class SpaceTorRouter {
    private nodes;
    private readonly minPathLength;
    constructor(initialNodes?: RelayNode[]);
    /**
     * Register a relay node
     */
    registerNode(node: RelayNode): void;
    /**
     * Remove a relay node (destroyed/offline)
     */
    removeNode(nodeId: string): boolean;
    /**
     * Get all registered nodes
     */
    getNodes(): RelayNode[];
    /**
     * Get a specific node by ID
     */
    getNode(nodeId: string): RelayNode | undefined;
    /**
     * Update node load
     */
    updateNodeLoad(nodeId: string, load: number): void;
    /**
     * Update node trust score
     */
    updateNodeTrust(nodeId: string, trustScore: number): void;
    /**
     * Calculate optimal path from origin to destination
     *
     * @param origin - Origin coordinates (AU)
     * @param dest - Destination coordinates (AU)
     * @param minTrust - Minimum trust score for nodes
     * @param constraints - Additional path constraints
     * @returns Array of relay nodes forming the path
     */
    calculatePath(origin: {
        x: number;
        y: number;
        z: number;
    }, dest: {
        x: number;
        y: number;
        z: number;
    }, minTrust: number, constraints?: Partial<PathConstraints>): RelayNode[];
    /**
     * Calculate path with specific node exclusions (for disjoint paths)
     */
    calculateDisjointPath(origin: {
        x: number;
        y: number;
        z: number;
    }, dest: {
        x: number;
        y: number;
        z: number;
    }, minTrust: number, excludeNodes: Set<string>): RelayNode[];
    /**
     * Get nodes that meet minimum trust and other constraints
     */
    private getEligibleNodes;
    /**
     * Select optimal node based on role and distance
     */
    private selectNode;
    /**
     * Select middle node optimized for security and balance
     */
    private selectMiddleNode;
    /**
     * Calculate distance between two points (AU)
     */
    private calculateDistance;
    /**
     * Score a node based on trust, distance, and load
     */
    private scoreNode;
}
//# sourceMappingURL=space-tor-router.d.ts.map