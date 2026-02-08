/**
 * Contact Graph - Graph-based routing for SpaceTor swarm networks
 *
 * Implements Contact Graph Routing (CGR) from DTN research for
 * predictive circuit paths through satellite swarms.
 *
 * @module network/contact-graph
 */
/**
 * Represents a contact window between two nodes
 */
export interface ContactEdge {
    id: string;
    source: string;
    target: string;
    startTime: number;
    endTime: number;
    capacity: number;
    latency: number;
    confidence: number;
    metadata?: Record<string, unknown>;
}
/**
 * Node in the contact graph
 */
export interface ContactNode {
    id: string;
    type: 'LEO' | 'MEO' | 'GEO' | 'LUNAR' | 'GROUND';
    position6D: number[];
    trustScore: number;
    lastSeen: number;
    metadata?: Record<string, unknown>;
}
/**
 * Path through the contact graph
 */
export interface ContactPath {
    nodes: string[];
    edges: ContactEdge[];
    totalLatency: number;
    totalCapacity: number;
    reliability: number;
    score: number;
}
/**
 * Graph statistics
 */
export interface GraphStats {
    nodeCount: number;
    edgeCount: number;
    averageLatency: number;
    averageCapacity: number;
    density: number;
    connectedComponents: number;
}
/**
 * Contact Graph - Core data structure for swarm routing
 *
 * Provides:
 * - Node/edge management
 * - Dijkstra shortest path
 * - Multi-objective path scoring
 * - Temporal contact window queries
 * - Graph visualization data export
 */
export declare class ContactGraph {
    private nodes;
    private edges;
    private adjacency;
    /**
     * Add a node to the graph
     */
    addNode(node: ContactNode): void;
    /**
     * Remove a node and all its edges
     */
    removeNode(nodeId: string): boolean;
    /**
     * Add a contact edge between nodes
     */
    addEdge(edge: Omit<ContactEdge, 'id'> & {
        id?: string;
    }): ContactEdge;
    /**
     * Remove an edge
     */
    removeEdge(edgeId: string): boolean;
    /**
     * Get node by ID
     */
    getNode(nodeId: string): ContactNode | undefined;
    /**
     * Get edge by ID
     */
    getEdge(edgeId: string): ContactEdge | undefined;
    /**
     * Get all edges between two nodes
     */
    getEdgesBetween(nodeA: string, nodeB: string): ContactEdge[];
    /**
     * Get neighbors of a node
     */
    getNeighbors(nodeId: string): string[];
    /**
     * Dijkstra's algorithm for shortest path by latency
     */
    dijkstra(source: string): Map<string, {
        distance: number;
        previous: string | null;
    }>;
    /**
     * Find shortest path between two nodes
     */
    findShortestPath(source: string, target: string): ContactPath | null;
    /**
     * Multi-objective path scoring
     *
     * Balances:
     * - Latency (lower is better)
     * - Reliability (higher is better)
     * - Trust (higher is better)
     * - Capacity (higher is better)
     */
    scorePath(path: Omit<ContactPath, 'score'>): number;
    /**
     * Find k-best disjoint paths for redundancy
     */
    findDisjointPaths(source: string, target: string, k?: number): ContactPath[];
    /**
     * Find path excluding certain nodes
     */
    private findPathExcluding;
    /**
     * Get active contact windows at a given time
     */
    getActiveContacts(timestamp?: number): ContactEdge[];
    /**
     * Get upcoming contact windows within horizon
     */
    getUpcomingContacts(horizon?: number): ContactEdge[];
    /**
     * Prune expired contact windows
     */
    pruneExpired(timestamp?: number): number;
    /**
     * Get graph statistics
     */
    getStats(): GraphStats;
    /**
     * Export graph data for visualization
     */
    toVisualizationData(): {
        nodes: Array<{
            id: string;
            type: string;
            position: number[];
            trust: number;
        }>;
        edges: Array<{
            source: string;
            target: string;
            latency: number;
            capacity: number;
        }>;
    };
    /**
     * Import from JSON
     */
    static fromJSON(data: {
        nodes: ContactNode[];
        edges: Array<Omit<ContactEdge, 'id'> & {
            id?: string;
        }>;
    }): ContactGraph;
    /**
     * Export to JSON
     */
    toJSON(): {
        nodes: ContactNode[];
        edges: ContactEdge[];
    };
}
/**
 * Build contact graph from swarm nodes over planning horizon
 */
export declare function computeContactGraph(nodes: Array<{
    id: string;
    type: ContactNode['type'];
    position6D: number[];
    trustScore: number;
}>, horizonMs?: number, // 1 hour default
estimateContact?: (nodeA: {
    id: string;
    position6D: number[];
}, nodeB: {
    id: string;
    position6D: number[];
}) => {
    latency: number;
    capacity: number;
    confidence: number;
} | null): ContactGraph;
export default ContactGraph;
//# sourceMappingURL=contact-graph.d.ts.map