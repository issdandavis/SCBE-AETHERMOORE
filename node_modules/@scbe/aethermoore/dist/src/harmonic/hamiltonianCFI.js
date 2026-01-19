"use strict";
/**
 * SCBE Hamiltonian CFI (Control Flow Integrity)
 *
 * Topological Control Flow Integrity via spectral embedding and golden path detection.
 * - Valid execution = traversal along Hamiltonian "golden path"
 * - Attack = deviation from linearized manifold in embedded space
 * - Detection = spectral embedding + principal curve projection
 *
 * Key Insight: Many 3D graphs are non-Hamiltonian (e.g., Rhombic Dodecahedron
 * with bipartite imbalance |6-8|=2), but lifting to 4D/6D resolves obstructions.
 *
 * Dirac's Theorem: If deg(v) ≥ |V|/2 for all v, graph is Hamiltonian.
 * Ore's Theorem: If deg(u) + deg(v) ≥ |V| for all non-adjacent u,v, graph is Hamiltonian.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.createVertex = exports.HamiltonianCFI = exports.ControlFlowGraph = void 0;
/**
 * Control Flow Graph
 */
class ControlFlowGraph {
    vertices = new Map();
    edges = new Set();
    adjacency = new Map();
    /**
     * Add a vertex to the graph
     */
    addVertex(vertex) {
        this.vertices.set(vertex.id, vertex);
        if (!this.adjacency.has(vertex.id)) {
            this.adjacency.set(vertex.id, new Set());
        }
    }
    /**
     * Add an edge between two vertices
     */
    addEdge(from, to) {
        const key = `${from}->${to}`;
        this.edges.add(key);
        if (!this.adjacency.has(from)) {
            this.adjacency.set(from, new Set());
        }
        if (!this.adjacency.has(to)) {
            this.adjacency.set(to, new Set());
        }
        this.adjacency.get(from).add(to);
        this.adjacency.get(to).add(from); // Undirected for Hamiltonian analysis
    }
    /**
     * Get vertex by ID
     */
    getVertex(id) {
        return this.vertices.get(id);
    }
    /**
     * Get all vertex IDs
     */
    getVertexIds() {
        return Array.from(this.vertices.keys());
    }
    /**
     * Get neighbors of a vertex
     */
    getNeighbors(id) {
        return Array.from(this.adjacency.get(id) ?? []);
    }
    /**
     * Get degree of a vertex
     */
    degree(id) {
        return this.adjacency.get(id)?.size ?? 0;
    }
    /**
     * Get number of vertices
     */
    get vertexCount() {
        return this.vertices.size;
    }
    /**
     * Get number of edges
     */
    get edgeCount() {
        return this.edges.size;
    }
    /**
     * Check if edge exists
     */
    hasEdge(from, to) {
        return this.adjacency.get(from)?.has(to) ?? false;
    }
    /**
     * Check if graph is bipartite using BFS coloring
     */
    checkBipartite() {
        const color = new Map();
        const setA = [];
        const setB = [];
        let isBipartite = true;
        for (const startId of this.vertices.keys()) {
            if (color.has(startId))
                continue;
            const queue = [startId];
            color.set(startId, 0);
            while (queue.length > 0 && isBipartite) {
                const v = queue.shift();
                const vColor = color.get(v);
                for (const neighbor of this.getNeighbors(v)) {
                    if (!color.has(neighbor)) {
                        color.set(neighbor, 1 - vColor);
                        queue.push(neighbor);
                    }
                    else if (color.get(neighbor) === vColor) {
                        isBipartite = false;
                        break;
                    }
                }
            }
        }
        // Build sets
        for (const [id, c] of color) {
            if (c === 0)
                setA.push(id);
            else
                setB.push(id);
        }
        return {
            isBipartite,
            setA,
            setB,
            imbalance: Math.abs(setA.length - setB.length),
        };
    }
    /**
     * Check Dirac's theorem: deg(v) ≥ |V|/2 for all v
     */
    checkDirac() {
        const n = this.vertexCount;
        if (n < 3)
            return n <= 2;
        const threshold = n / 2;
        for (const id of this.vertices.keys()) {
            if (this.degree(id) < threshold) {
                return false;
            }
        }
        return true;
    }
    /**
     * Check Ore's theorem: deg(u) + deg(v) ≥ |V| for all non-adjacent u,v
     */
    checkOre() {
        const n = this.vertexCount;
        if (n < 3)
            return n <= 2;
        const ids = this.getVertexIds();
        for (let i = 0; i < ids.length; i++) {
            for (let j = i + 1; j < ids.length; j++) {
                const u = ids[i], v = ids[j];
                if (!this.hasEdge(u, v)) {
                    if (this.degree(u) + this.degree(v) < n) {
                        return false;
                    }
                }
            }
        }
        return true;
    }
    /**
     * Comprehensive Hamiltonicity check
     */
    checkHamiltonian() {
        const bipartite = this.checkBipartite();
        const satisfiesDirac = this.checkDirac();
        const satisfiesOre = this.checkOre();
        let minDegree = Infinity;
        for (const id of this.vertices.keys()) {
            minDegree = Math.min(minDegree, this.degree(id));
        }
        if (!isFinite(minDegree))
            minDegree = 0;
        // Likely Hamiltonian if:
        // - Satisfies Dirac or Ore, OR
        // - Is bipartite with |A| = |B|
        const likelyHamiltonian = satisfiesDirac || satisfiesOre ||
            (bipartite.isBipartite && bipartite.imbalance === 0);
        return {
            satisfiesDirac,
            satisfiesOre,
            minDegree,
            likelyHamiltonian,
            bipartite,
        };
    }
}
exports.ControlFlowGraph = ControlFlowGraph;
/**
 * Hamiltonian CFI Monitor
 */
class HamiltonianCFI {
    cfg;
    goldenPath = [];
    currentPosition = 0;
    deviationThreshold;
    constructor(cfg, deviationThreshold = 0.5) {
        this.cfg = cfg;
        this.deviationThreshold = deviationThreshold;
    }
    /**
     * Set the expected "golden path" (valid Hamiltonian traversal)
     */
    setGoldenPath(path) {
        this.goldenPath = path;
        this.currentPosition = 0;
    }
    /**
     * Compute spectral embedding distance (simplified)
     * In production, use proper Laplacian eigenvectors
     */
    spectralDistance(v1, v2) {
        // Simplified: use graph distance as proxy
        const n1 = this.cfg.getNeighbors(v1);
        const n2 = this.cfg.getNeighbors(v2);
        // Jaccard similarity of neighborhoods
        const intersection = n1.filter(x => n2.includes(x)).length;
        const union = new Set([...n1, ...n2]).size;
        if (union === 0)
            return 1.0;
        return 1 - intersection / union;
    }
    /**
     * Check if a state vector represents valid execution
     *
     * @param stateVector - Current execution state [vertex_id, ...]
     * @returns CFI result
     */
    checkState(stateVector) {
        if (stateVector.length === 0) {
            return 'OBSTRUCTION';
        }
        const currentVertex = stateVector[0];
        // Check if vertex exists
        if (!this.cfg.getVertex(currentVertex)) {
            return 'ATTACK';
        }
        // If no golden path set, check graph properties
        if (this.goldenPath.length === 0) {
            const check = this.cfg.checkHamiltonian();
            if (!check.likelyHamiltonian) {
                // Check for bipartite imbalance obstruction
                if (check.bipartite.isBipartite && check.bipartite.imbalance > 1) {
                    return 'OBSTRUCTION';
                }
            }
            return 'VALID';
        }
        // Check against golden path
        const expectedVertex = this.goldenPath[this.currentPosition];
        if (currentVertex === expectedVertex) {
            // On path - advance position
            this.currentPosition = (this.currentPosition + 1) % this.goldenPath.length;
            return 'VALID';
        }
        // Not on expected path - check spectral distance
        const distance = this.spectralDistance(currentVertex, expectedVertex);
        if (distance < this.deviationThreshold) {
            return 'DEVIATION';
        }
        return 'ATTACK';
    }
    /**
     * Reset CFI state
     */
    reset() {
        this.currentPosition = 0;
    }
    /**
     * Get Hamiltonicity analysis of the CFG
     */
    analyzeGraph() {
        return this.cfg.checkHamiltonian();
    }
    /**
     * Attempt to find a Hamiltonian path (brute force for small graphs)
     * Returns null if no path found or graph too large
     */
    findHamiltonianPath(maxVertices = 12) {
        const vertices = this.cfg.getVertexIds();
        if (vertices.length > maxVertices)
            return null;
        if (vertices.length === 0)
            return [];
        if (vertices.length === 1)
            return vertices;
        // Try starting from each vertex
        for (const start of vertices) {
            const path = this.dfsHamiltonian([start], new Set([start]), vertices.length);
            if (path)
                return path;
        }
        return null;
    }
    dfsHamiltonian(path, visited, target) {
        if (path.length === target) {
            return path;
        }
        const current = path[path.length - 1];
        for (const neighbor of this.cfg.getNeighbors(current)) {
            if (!visited.has(neighbor)) {
                visited.add(neighbor);
                path.push(neighbor);
                const result = this.dfsHamiltonian(path, visited, target);
                if (result)
                    return result;
                path.pop();
                visited.delete(neighbor);
            }
        }
        return null;
    }
}
exports.HamiltonianCFI = HamiltonianCFI;
/**
 * Create a CFGVertex helper
 */
function createVertex(id, label, address, metadata) {
    return { id, label, address, metadata };
}
exports.createVertex = createVertex;
//# sourceMappingURL=hamiltonianCFI.js.map