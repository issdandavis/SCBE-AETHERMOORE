/**
 * @file symbioticNetwork.ts
 * @module game/symbioticNetwork
 * @layer Layer 5, Layer 9, Layer 10
 * @component Symbiotic Network — Graph Topology for Companion Fleet
 *
 * Companions form a weighted graph. Emergent bonuses come from
 * graph Laplacian spectral properties (λ₂ = algebraic connectivity).
 *
 * Uses NetworkX-equivalent pure-TS implementation (no FAISS — v1 doesn't need it).
 *
 * A4: Symmetry — Hodge dual pairs bond 30% stronger.
 * A5: Composition — pipeline integrity via graph connectivity.
 */

import {
  TongueVector,
  TongueCode,
  TONGUE_CODES,
  HODGE_DUAL_PAIRS,
  tongueDistance,
} from './types.js';
import type { Companion } from './companion.js';

// ---------------------------------------------------------------------------
//  Graph Representation
// ---------------------------------------------------------------------------

interface GraphNode {
  readonly id: string;
  readonly tonguePosition: TongueVector;
}

interface GraphEdge {
  readonly source: string;
  readonly target: string;
  weight: number;
  sharedBattles: number;
}

export class SymbioticNetwork {
  private nodes: Map<string, GraphNode> = new Map();
  private edges: Map<string, GraphEdge> = new Map();
  private adjacency: Map<string, Set<string>> = new Map();

  // -------------------------------------------------------------------------
  //  Node Operations
  // -------------------------------------------------------------------------

  /** Add a companion to the network */
  addCompanion(companion: Companion): void {
    this.nodes.set(companion.id, {
      id: companion.id,
      tonguePosition: [...companion.state.tonguePosition] as TongueVector,
    });
    if (!this.adjacency.has(companion.id)) {
      this.adjacency.set(companion.id, new Set());
    }
  }

  /** Remove a companion from the network */
  removeCompanion(id: string): void {
    // Remove all edges involving this node
    const neighbors = this.adjacency.get(id);
    if (neighbors) {
      for (const neighbor of neighbors) {
        const edgeKey = this.edgeKey(id, neighbor);
        this.edges.delete(edgeKey);
        this.adjacency.get(neighbor)?.delete(id);
      }
    }
    this.nodes.delete(id);
    this.adjacency.delete(id);
  }

  /** Get node count */
  get nodeCount(): number {
    return this.nodes.size;
  }

  /** Get edge count */
  get edgeCount(): number {
    return this.edges.size;
  }

  // -------------------------------------------------------------------------
  //  Edge Operations
  // -------------------------------------------------------------------------

  /** Canonical edge key (alphabetical order) */
  private edgeKey(a: string, b: string): string {
    return a < b ? `${a}::${b}` : `${b}::${a}`;
  }

  /**
   * Add or update a bond between two companions.
   * Weight is computed from tongue similarity + Hodge dual bonus.
   *
   * @param aId - First companion ID
   * @param bId - Second companion ID
   * @param sharedBattles - Number of battles fought together
   */
  addBond(aId: string, bId: string, sharedBattles: number = 0): void {
    const nodeA = this.nodes.get(aId);
    const nodeB = this.nodes.get(bId);
    if (!nodeA || !nodeB) return;

    // Base weight: inverse distance (closer in tongue-space = stronger bond)
    const dist = tongueDistance(nodeA.tonguePosition, nodeB.tonguePosition);
    let weight = 1.0 / (1.0 + dist);

    // Hodge dual bonus: +30% if tongues form a complementary pair
    if (this.isHodgeDualPair(nodeA.tonguePosition, nodeB.tonguePosition)) {
      weight *= 1.3;
    }

    // Shared battle bonus (diminishing returns)
    weight += Math.log1p(sharedBattles) * 0.1;

    const key = this.edgeKey(aId, bId);
    this.edges.set(key, { source: aId, target: bId, weight, sharedBattles });

    // Update adjacency
    this.adjacency.get(aId)?.add(bId);
    this.adjacency.get(bId)?.add(aId);
  }

  /**
   * Check if two tongue vectors form a Hodge dual pair.
   * A pair is "Hodge dual" if their dominant tongues are complementary.
   */
  private isHodgeDualPair(a: TongueVector, b: TongueVector): boolean {
    const domA = this.dominantTongue(a);
    const domB = this.dominantTongue(b);
    return HODGE_DUAL_PAIRS.some(
      ([x, y]) => (domA === x && domB === y) || (domA === y && domB === x)
    );
  }

  private dominantTongue(v: TongueVector): TongueCode {
    let maxIdx = 0;
    for (let i = 1; i < 6; i++) {
      if (v[i] > v[maxIdx]) maxIdx = i;
    }
    return TONGUE_CODES[maxIdx];
  }

  // -------------------------------------------------------------------------
  //  Laplacian Computation
  // -------------------------------------------------------------------------

  /**
   * Compute the weighted graph Laplacian matrix L = D - A.
   * Returns as a flat 2D array indexed by node order.
   */
  computeLaplacian(): { matrix: number[][]; nodeOrder: string[] } {
    const nodeOrder = Array.from(this.nodes.keys()).sort();
    const n = nodeOrder.length;
    const idxMap = new Map(nodeOrder.map((id, i) => [id, i]));

    // Initialize L as zeros
    const L: number[][] = Array.from({ length: n }, () => Array(n).fill(0));

    // Fill from edges
    for (const edge of this.edges.values()) {
      const i = idxMap.get(edge.source);
      const j = idxMap.get(edge.target);
      if (i === undefined || j === undefined) continue;

      L[i][j] = -edge.weight;
      L[j][i] = -edge.weight;
      L[i][i] += edge.weight;
      L[j][j] += edge.weight;
    }

    return { matrix: L, nodeOrder };
  }

  /**
   * Compute algebraic connectivity (λ₂ = second smallest eigenvalue of L).
   * Uses power iteration on (L - λ₁I) to find λ₂.
   * Pure TS — no numpy needed.
   */
  getAlgebraicConnectivity(): number {
    if (this.nodes.size < 2) return 0;

    const { matrix } = this.computeLaplacian();
    const eigenvalues = this.computeEigenvalues(matrix);

    // Sort ascending
    eigenvalues.sort((a, b) => a - b);

    // λ₂ is the second smallest (first should be ~0)
    return eigenvalues.length > 1 ? Math.max(0, eigenvalues[1]) : 0;
  }

  /**
   * Compute eigenvalues of a symmetric matrix using QR iteration.
   * Simplified for small matrices (companion fleet is typically 3-8 nodes).
   */
  private computeEigenvalues(matrix: number[][]): number[] {
    const n = matrix.length;
    if (n === 0) return [];
    if (n === 1) return [matrix[0][0]];
    if (n === 2) {
      // Analytical 2x2 eigenvalues
      const a = matrix[0][0],
        b = matrix[0][1];
      const c = matrix[1][0],
        d = matrix[1][1];
      const trace = a + d;
      const det = a * d - b * c;
      const disc = Math.sqrt(Math.max(0, trace * trace - 4 * det));
      return [(trace + disc) / 2, (trace - disc) / 2];
    }

    // For larger matrices: Jacobi eigenvalue algorithm
    // (suitable for symmetric matrices, which the Laplacian always is)
    return this.jacobiEigenvalues(matrix);
  }

  /**
   * Jacobi eigenvalue algorithm for symmetric matrices.
   * Iteratively applies Givens rotations to diagonalize.
   */
  private jacobiEigenvalues(matrix: number[][]): number[] {
    const n = matrix.length;
    const A: number[][] = matrix.map((row) => [...row]);
    const maxIter = 100 * n * n;
    const epsilon = 1e-10;

    for (let iter = 0; iter < maxIter; iter++) {
      // Find largest off-diagonal element
      let maxVal = 0;
      let p = 0,
        q = 1;
      for (let i = 0; i < n; i++) {
        for (let j = i + 1; j < n; j++) {
          if (Math.abs(A[i][j]) > maxVal) {
            maxVal = Math.abs(A[i][j]);
            p = i;
            q = j;
          }
        }
      }

      if (maxVal < epsilon) break;

      // Compute rotation angle
      const theta =
        Math.abs(A[p][p] - A[q][q]) < epsilon
          ? Math.PI / 4
          : 0.5 * Math.atan2(2 * A[p][q], A[p][p] - A[q][q]);

      const c = Math.cos(theta);
      const s = Math.sin(theta);

      // Apply Givens rotation
      for (let i = 0; i < n; i++) {
        if (i !== p && i !== q) {
          const aip = A[i][p];
          const aiq = A[i][q];
          A[i][p] = c * aip + s * aiq;
          A[p][i] = A[i][p];
          A[i][q] = -s * aip + c * aiq;
          A[q][i] = A[i][q];
        }
      }

      const app = A[p][p];
      const aqq = A[q][q];
      const apq = A[p][q];
      A[p][p] = c * c * app + 2 * s * c * apq + s * s * aqq;
      A[q][q] = s * s * app - 2 * s * c * apq + c * c * aqq;
      A[p][q] = 0;
      A[q][p] = 0;
    }

    // Diagonal elements are eigenvalues
    return Array.from({ length: n }, (_, i) => A[i][i]);
  }

  // -------------------------------------------------------------------------
  //  Emergent Bonuses
  // -------------------------------------------------------------------------

  /**
   * Compute all emergent bonuses from network topology.
   * These are NOT hardcoded — they emerge from graph spectral properties.
   */
  computeNetworkBonuses(): NetworkBonuses {
    const lambda2 = this.getAlgebraicConnectivity();
    const density = this.computeDensity();
    const totalBond = this.computeTotalBondWeight();
    const uniqueTongues = this.countUniqueDominantTongues();

    return {
      xpMultiplier: 1 + lambda2 * 0.5,
      insightBonus: density * 0.3,
      resilience: Math.min(1, lambda2 * 0.2),
      governanceWeight: Math.min(2, totalBond * 0.1 + 1),
      diversityBonus: uniqueTongues / 6,
      algebraicConnectivity: lambda2,
      density,
    };
  }

  /** Graph density: |E| / (|V| choose 2) */
  private computeDensity(): number {
    const n = this.nodes.size;
    if (n < 2) return 0;
    const maxEdges = (n * (n - 1)) / 2;
    return this.edges.size / maxEdges;
  }

  /** Sum of all edge weights */
  private computeTotalBondWeight(): number {
    let total = 0;
    for (const edge of this.edges.values()) {
      total += edge.weight;
    }
    return total;
  }

  /** Count unique dominant tongues across all nodes */
  private countUniqueDominantTongues(): number {
    const tongues = new Set<TongueCode>();
    for (const node of this.nodes.values()) {
      tongues.add(this.dominantTongue(node.tonguePosition));
    }
    return tongues.size;
  }

  // -------------------------------------------------------------------------
  //  Artifact Governance (Layer 12 gate)
  // -------------------------------------------------------------------------

  /**
   * Submit an artifact through the network governance gate.
   * Rejects if the state divergence from network centroid exceeds threshold.
   *
   * @param state - The canonical state of the submitting entity
   * @param threshold - Maximum allowed ds² distance (default: 5.0)
   * @returns 'approved' | 'quarantined'
   */
  submitArtifact(state: TongueVector, threshold: number = 5.0): 'approved' | 'quarantined' {
    if (this.nodes.size === 0) return 'approved';

    const centroid = this.computeCentroid();
    const ds2 = tongueDistance(state, centroid) ** 2;

    return ds2 <= threshold ? 'approved' : 'quarantined';
  }

  /** Compute centroid of all node tongue positions */
  private computeCentroid(): TongueVector {
    const n = this.nodes.size;
    if (n === 0) return [0, 0, 0, 0, 0, 0];

    const sum: TongueVector = [0, 0, 0, 0, 0, 0];
    for (const node of this.nodes.values()) {
      for (let i = 0; i < 6; i++) {
        sum[i] += node.tonguePosition[i];
      }
    }
    return sum.map((v) => v / n) as TongueVector;
  }

  // -------------------------------------------------------------------------
  //  Serialization
  // -------------------------------------------------------------------------

  /** Serialize the network to a plain object */
  toJSON(): { nodes: GraphNode[]; edges: GraphEdge[] } {
    return {
      nodes: Array.from(this.nodes.values()),
      edges: Array.from(this.edges.values()),
    };
  }

  /** Deserialize from a plain object */
  static fromJSON(data: { nodes: GraphNode[]; edges: GraphEdge[] }): SymbioticNetwork {
    const net = new SymbioticNetwork();
    for (const node of data.nodes) {
      net.nodes.set(node.id, node);
      net.adjacency.set(node.id, new Set());
    }
    for (const edge of data.edges) {
      const key = net.edgeKey(edge.source, edge.target);
      net.edges.set(key, edge);
      net.adjacency.get(edge.source)?.add(edge.target);
      net.adjacency.get(edge.target)?.add(edge.source);
    }
    return net;
  }
}

// ---------------------------------------------------------------------------
//  Network Bonus Interface
// ---------------------------------------------------------------------------

export interface NetworkBonuses {
  /** XP multiplier: 1 + λ₂ × 0.5 */
  readonly xpMultiplier: number;
  /** Insight bonus: density × 0.3 */
  readonly insightBonus: number;
  /** Resilience: min(1, λ₂ × 0.2) */
  readonly resilience: number;
  /** Governance weight: min(2, total_bond × 0.1 + 1) */
  readonly governanceWeight: number;
  /** Diversity bonus: unique_tongues / 6 */
  readonly diversityBonus: number;
  /** Raw algebraic connectivity */
  readonly algebraicConnectivity: number;
  /** Raw graph density */
  readonly density: number;
}
