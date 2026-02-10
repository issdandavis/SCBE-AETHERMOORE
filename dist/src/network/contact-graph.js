"use strict";
/**
 * Contact Graph - Graph-based routing for SpaceTor swarm networks
 *
 * Implements Contact Graph Routing (CGR) from DTN research for
 * predictive circuit paths through satellite swarms.
 *
 * @module network/contact-graph
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.ContactGraph = void 0;
exports.computeContactGraph = computeContactGraph;
/**
 * Generate a UUID v4 without external dependency
 */
function uuidv4() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
        const r = (Math.random() * 16) | 0;
        const v = c === 'x' ? r : (r & 0x3) | 0x8;
        return v.toString(16);
    });
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
class ContactGraph {
    nodes = new Map();
    edges = new Map();
    adjacency = new Map(); // nodeId -> Set<edgeId>
    /**
     * Add a node to the graph
     */
    addNode(node) {
        this.nodes.set(node.id, node);
        if (!this.adjacency.has(node.id)) {
            this.adjacency.set(node.id, new Set());
        }
    }
    /**
     * Remove a node and all its edges
     */
    removeNode(nodeId) {
        if (!this.nodes.has(nodeId))
            return false;
        // Remove all edges connected to this node
        const edgeIds = this.adjacency.get(nodeId) || new Set();
        for (const edgeId of edgeIds) {
            this.edges.delete(edgeId);
        }
        // Remove from other nodes' adjacency lists
        for (const [, adjSet] of this.adjacency) {
            for (const edgeId of adjSet) {
                const edge = this.edges.get(edgeId);
                if (edge && (edge.source === nodeId || edge.target === nodeId)) {
                    adjSet.delete(edgeId);
                }
            }
        }
        this.adjacency.delete(nodeId);
        this.nodes.delete(nodeId);
        return true;
    }
    /**
     * Add a contact edge between nodes
     */
    addEdge(edge) {
        const fullEdge = {
            ...edge,
            id: edge.id || uuidv4(),
        };
        // Ensure nodes exist
        if (!this.nodes.has(fullEdge.source)) {
            throw new Error(`Source node ${fullEdge.source} not found`);
        }
        if (!this.nodes.has(fullEdge.target)) {
            throw new Error(`Target node ${fullEdge.target} not found`);
        }
        this.edges.set(fullEdge.id, fullEdge);
        // Update adjacency (bidirectional for undirected graph)
        this.adjacency.get(fullEdge.source)?.add(fullEdge.id);
        this.adjacency.get(fullEdge.target)?.add(fullEdge.id);
        return fullEdge;
    }
    /**
     * Remove an edge
     */
    removeEdge(edgeId) {
        const edge = this.edges.get(edgeId);
        if (!edge)
            return false;
        this.adjacency.get(edge.source)?.delete(edgeId);
        this.adjacency.get(edge.target)?.delete(edgeId);
        this.edges.delete(edgeId);
        return true;
    }
    /**
     * Get node by ID
     */
    getNode(nodeId) {
        return this.nodes.get(nodeId);
    }
    /**
     * Get edge by ID
     */
    getEdge(edgeId) {
        return this.edges.get(edgeId);
    }
    /**
     * Get all edges between two nodes
     */
    getEdgesBetween(nodeA, nodeB) {
        const results = [];
        const edgeIds = this.adjacency.get(nodeA) || new Set();
        for (const edgeId of edgeIds) {
            const edge = this.edges.get(edgeId);
            if (edge &&
                ((edge.source === nodeA && edge.target === nodeB) ||
                    (edge.source === nodeB && edge.target === nodeA))) {
                results.push(edge);
            }
        }
        return results;
    }
    /**
     * Get neighbors of a node
     */
    getNeighbors(nodeId) {
        const neighbors = new Set();
        const edgeIds = this.adjacency.get(nodeId) || new Set();
        for (const edgeId of edgeIds) {
            const edge = this.edges.get(edgeId);
            if (edge) {
                if (edge.source === nodeId)
                    neighbors.add(edge.target);
                if (edge.target === nodeId)
                    neighbors.add(edge.source);
            }
        }
        return Array.from(neighbors);
    }
    /**
     * Dijkstra's algorithm for shortest path by latency
     */
    dijkstra(source) {
        const distances = new Map();
        const visited = new Set();
        const queue = [];
        // Initialize
        for (const nodeId of this.nodes.keys()) {
            distances.set(nodeId, { distance: Infinity, previous: null });
        }
        distances.set(source, { distance: 0, previous: null });
        queue.push({ node: source, distance: 0 });
        while (queue.length > 0) {
            // Sort by distance and get minimum
            queue.sort((a, b) => a.distance - b.distance);
            const current = queue.shift();
            if (visited.has(current.node))
                continue;
            visited.add(current.node);
            // Check all neighbors
            for (const neighbor of this.getNeighbors(current.node)) {
                if (visited.has(neighbor))
                    continue;
                const edges = this.getEdgesBetween(current.node, neighbor);
                if (edges.length === 0)
                    continue;
                // Use edge with lowest latency
                const bestEdge = edges.reduce((a, b) => (a.latency < b.latency ? a : b));
                const newDistance = current.distance + bestEdge.latency;
                const currentBest = distances.get(neighbor);
                if (newDistance < currentBest.distance) {
                    distances.set(neighbor, { distance: newDistance, previous: current.node });
                    queue.push({ node: neighbor, distance: newDistance });
                }
            }
        }
        return distances;
    }
    /**
     * Find shortest path between two nodes
     */
    findShortestPath(source, target) {
        const dijkstraResult = this.dijkstra(source);
        const targetResult = dijkstraResult.get(target);
        if (!targetResult || targetResult.distance === Infinity) {
            return null;
        }
        // Reconstruct path
        const nodes = [];
        let current = target;
        while (current !== null) {
            nodes.unshift(current);
            current = dijkstraResult.get(current)?.previous || null;
        }
        // Collect edges
        const edges = [];
        let totalCapacity = Infinity;
        let reliability = 1.0;
        for (let i = 0; i < nodes.length - 1; i++) {
            const edgesBetween = this.getEdgesBetween(nodes[i], nodes[i + 1]);
            if (edgesBetween.length > 0) {
                const bestEdge = edgesBetween.reduce((a, b) => (a.latency < b.latency ? a : b));
                edges.push(bestEdge);
                totalCapacity = Math.min(totalCapacity, bestEdge.capacity);
                reliability *= bestEdge.confidence;
            }
        }
        return {
            nodes,
            edges,
            totalLatency: targetResult.distance,
            totalCapacity,
            reliability,
            score: this.scorePath({
                nodes,
                edges,
                totalLatency: targetResult.distance,
                totalCapacity,
                reliability,
            }),
        };
    }
    /**
     * Multi-objective path scoring
     *
     * Balances:
     * - Latency (lower is better)
     * - Reliability (higher is better)
     * - Trust (higher is better)
     * - Capacity (higher is better)
     */
    scorePath(path) {
        // Latency score (normalized, 1s = 0.5 score)
        const latencyScore = 1.0 / (1.0 + path.totalLatency / 1000.0);
        // Reliability score (already 0-1)
        const reliabilityScore = path.reliability;
        // Trust score (average of node trust scores)
        let trustSum = 0;
        for (const nodeId of path.nodes) {
            const node = this.nodes.get(nodeId);
            trustSum += node?.trustScore || 0.5;
        }
        const trustScore = trustSum / path.nodes.length;
        // Capacity score (normalized to 1Mbps)
        const capacityScore = Math.min(1.0, path.totalCapacity / 1_000_000);
        // Weighted combination
        const weights = {
            latency: 0.3,
            reliability: 0.3,
            trust: 0.25,
            capacity: 0.15,
        };
        return (weights.latency * latencyScore +
            weights.reliability * reliabilityScore +
            weights.trust * trustScore +
            weights.capacity * capacityScore);
    }
    /**
     * Find k-best disjoint paths for redundancy
     */
    findDisjointPaths(source, target, k = 3) {
        const paths = [];
        const usedNodes = new Set();
        // Always allow source and target
        usedNodes.delete(source);
        usedNodes.delete(target);
        for (let i = 0; i < k; i++) {
            // Create filtered graph excluding used intermediate nodes
            const path = this.findPathExcluding(source, target, usedNodes);
            if (!path)
                break;
            paths.push(path);
            // Mark intermediate nodes as used
            for (const nodeId of path.nodes.slice(1, -1)) {
                usedNodes.add(nodeId);
            }
        }
        return paths;
    }
    /**
     * Find path excluding certain nodes
     */
    findPathExcluding(source, target, excludeNodes) {
        // Modified Dijkstra that skips excluded nodes
        const distances = new Map();
        const visited = new Set();
        const queue = [];
        for (const nodeId of this.nodes.keys()) {
            distances.set(nodeId, { distance: Infinity, previous: null });
        }
        distances.set(source, { distance: 0, previous: null });
        queue.push({ node: source, distance: 0 });
        while (queue.length > 0) {
            queue.sort((a, b) => a.distance - b.distance);
            const current = queue.shift();
            if (visited.has(current.node))
                continue;
            visited.add(current.node);
            for (const neighbor of this.getNeighbors(current.node)) {
                // Skip excluded nodes (unless it's the target)
                if (excludeNodes.has(neighbor) && neighbor !== target)
                    continue;
                if (visited.has(neighbor))
                    continue;
                const edges = this.getEdgesBetween(current.node, neighbor);
                if (edges.length === 0)
                    continue;
                const bestEdge = edges.reduce((a, b) => (a.latency < b.latency ? a : b));
                const newDistance = current.distance + bestEdge.latency;
                const currentBest = distances.get(neighbor);
                if (newDistance < currentBest.distance) {
                    distances.set(neighbor, { distance: newDistance, previous: current.node });
                    queue.push({ node: neighbor, distance: newDistance });
                }
            }
        }
        const targetResult = distances.get(target);
        if (!targetResult || targetResult.distance === Infinity) {
            return null;
        }
        // Reconstruct path
        const nodes = [];
        let currentNode = target;
        while (currentNode !== null) {
            nodes.unshift(currentNode);
            currentNode = distances.get(currentNode)?.previous || null;
        }
        const edges = [];
        let totalCapacity = Infinity;
        let reliability = 1.0;
        for (let i = 0; i < nodes.length - 1; i++) {
            const edgesBetween = this.getEdgesBetween(nodes[i], nodes[i + 1]);
            if (edgesBetween.length > 0) {
                const bestEdge = edgesBetween.reduce((a, b) => (a.latency < b.latency ? a : b));
                edges.push(bestEdge);
                totalCapacity = Math.min(totalCapacity, bestEdge.capacity);
                reliability *= bestEdge.confidence;
            }
        }
        return {
            nodes,
            edges,
            totalLatency: targetResult.distance,
            totalCapacity,
            reliability,
            score: this.scorePath({
                nodes,
                edges,
                totalLatency: targetResult.distance,
                totalCapacity,
                reliability,
            }),
        };
    }
    /**
     * Get active contact windows at a given time
     */
    getActiveContacts(timestamp = Date.now()) {
        const active = [];
        for (const edge of this.edges.values()) {
            if (edge.startTime <= timestamp && edge.endTime >= timestamp) {
                active.push(edge);
            }
        }
        return active;
    }
    /**
     * Get upcoming contact windows within horizon
     */
    getUpcomingContacts(horizon = 3600000) {
        const now = Date.now();
        const cutoff = now + horizon;
        const upcoming = [];
        for (const edge of this.edges.values()) {
            if (edge.startTime > now && edge.startTime <= cutoff) {
                upcoming.push(edge);
            }
        }
        return upcoming.sort((a, b) => a.startTime - b.startTime);
    }
    /**
     * Prune expired contact windows
     */
    pruneExpired(timestamp = Date.now()) {
        let pruned = 0;
        for (const [edgeId, edge] of this.edges) {
            if (edge.endTime < timestamp) {
                this.removeEdge(edgeId);
                pruned++;
            }
        }
        return pruned;
    }
    /**
     * Get graph statistics
     */
    getStats() {
        const nodeCount = this.nodes.size;
        const edgeCount = this.edges.size;
        let totalLatency = 0;
        let totalCapacity = 0;
        for (const edge of this.edges.values()) {
            totalLatency += edge.latency;
            totalCapacity += edge.capacity;
        }
        const maxPossibleEdges = nodeCount * (nodeCount - 1);
        const density = maxPossibleEdges > 0 ? edgeCount / maxPossibleEdges : 0;
        // Count connected components using BFS
        const visited = new Set();
        let components = 0;
        for (const nodeId of this.nodes.keys()) {
            if (!visited.has(nodeId)) {
                components++;
                const queue = [nodeId];
                while (queue.length > 0) {
                    const current = queue.shift();
                    if (visited.has(current))
                        continue;
                    visited.add(current);
                    for (const neighbor of this.getNeighbors(current)) {
                        if (!visited.has(neighbor))
                            queue.push(neighbor);
                    }
                }
            }
        }
        return {
            nodeCount,
            edgeCount,
            averageLatency: edgeCount > 0 ? totalLatency / edgeCount : 0,
            averageCapacity: edgeCount > 0 ? totalCapacity / edgeCount : 0,
            density,
            connectedComponents: components,
        };
    }
    /**
     * Export graph data for visualization
     */
    toVisualizationData() {
        const nodes = Array.from(this.nodes.values()).map((n) => ({
            id: n.id,
            type: n.type,
            position: n.position6D.slice(0, 3), // Project to 3D
            trust: n.trustScore,
        }));
        const edges = Array.from(this.edges.values()).map((e) => ({
            source: e.source,
            target: e.target,
            latency: e.latency,
            capacity: e.capacity,
        }));
        return { nodes, edges };
    }
    /**
     * Import from JSON
     */
    static fromJSON(data) {
        const graph = new ContactGraph();
        for (const node of data.nodes) {
            graph.addNode(node);
        }
        for (const edge of data.edges) {
            graph.addEdge(edge);
        }
        return graph;
    }
    /**
     * Export to JSON
     */
    toJSON() {
        return {
            nodes: Array.from(this.nodes.values()),
            edges: Array.from(this.edges.values()),
        };
    }
}
exports.ContactGraph = ContactGraph;
/**
 * Build contact graph from swarm nodes over planning horizon
 */
function computeContactGraph(nodes, horizonMs = 3600000, // 1 hour default
estimateContact) {
    const graph = new ContactGraph();
    const now = Date.now();
    // Add all nodes
    for (const node of nodes) {
        graph.addNode({
            id: node.id,
            type: node.type,
            position6D: node.position6D,
            trustScore: node.trustScore,
            lastSeen: now,
        });
    }
    // Default contact estimator based on 6D distance
    const defaultEstimator = (nodeA, nodeB) => {
        // Calculate 6D Euclidean distance
        let distSq = 0;
        for (let i = 0; i < 6; i++) {
            const diff = (nodeA.position6D[i] || 0) - (nodeB.position6D[i] || 0);
            distSq += diff * diff;
        }
        const distance = Math.sqrt(distSq);
        // No contact if too far (threshold: 100 units)
        if (distance > 100)
            return null;
        // Latency proportional to distance (speed of light approximation)
        const latency = Math.max(1, distance * 3.33); // ~3.33ms per unit
        // Capacity inversely proportional to distance
        const capacity = Math.max(10000, 1_000_000 / (1 + distance));
        // Confidence based on distance
        const confidence = Math.max(0.1, 1 - distance / 100);
        return { latency, capacity, confidence };
    };
    const contactEstimator = estimateContact || defaultEstimator;
    // Add edges between all pairs that can contact
    for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
            const contact = contactEstimator(nodes[i], nodes[j]);
            if (contact) {
                graph.addEdge({
                    source: nodes[i].id,
                    target: nodes[j].id,
                    startTime: now,
                    endTime: now + horizonMs,
                    latency: contact.latency,
                    capacity: contact.capacity,
                    confidence: contact.confidence,
                });
            }
        }
    }
    return graph;
}
exports.default = ContactGraph;
//# sourceMappingURL=contact-graph.js.map