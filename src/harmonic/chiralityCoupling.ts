/**
 * @file chiralityCoupling.ts
 * @module harmonic/chiralityCoupling
 * @layer Layer 5, Layer 9, Layer 10, Layer 12
 * @component Chirality Coupling — Global Handedness Constraints
 * @version 1.0.0
 * @since 2026-03-04
 *
 * Implements GLOBAL parity/handedness constraints on the governance
 * code graph and its allowed automorphisms — the "chirality coupling"
 * half of the BIT_SPIN / CHIRALITY_COUPLING duality.
 *
 * While BitSpin handles local stochastic sampling (no spatial awareness),
 * ChiralityCoupling enforces geometric orientation constraints:
 *
 *   - The governance graph has two SECTORS (left-handed, right-handed)
 *   - Information propagation, defect motion, and allowed transforms
 *     differ depending on global handedness
 *   - Spin-chirality CROSS-TERMS couple local p-bit states to
 *     the global chiral orientation, creating orientation-dependent
 *     transport asymmetry
 *
 * Sacred Tongue chirality mapping:
 *   RIGHT-handed (even index): KO (0), RU (2), UM (4)
 *   LEFT-handed  (odd index):  AV (1), CA (3), DR (5)
 *
 * This mirrors the negabinary polarity where even bit-positions
 * carry positive weight and odd positions carry negative weight.
 *
 * Physical analogy: gauge theory — chirality is an internal symmetry
 * (like "color charge" in QCD) that propagates through the governance
 * mesh. When two agents couple, their chirality sectors must be
 * compatible for constructive interference.
 *
 * References:
 *   [3] Spin-orbit coupling in Chiral-Induced Spin Selectivity (2025)
 *   [4] Chirality coupling in topological magnetic textures (2023)
 *   [6] Chiral Color Codes: 3D Topological Order with Qudit (2024)
 */

import { PHI, BRAIN_EPSILON } from '../ai_brain/types.js';

// ═══════════════════════════════════════════════════════════════
// Constants & Types
// ═══════════════════════════════════════════════════════════════

/** Chiral sectors — left and right handed */
export type ChiralSector = 'left' | 'right';

/** Sacred Tongue names */
const TONGUE_NAMES = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'] as const;
export type TongueName = (typeof TONGUE_NAMES)[number];

/** Phase shifts for each tongue: 60° intervals */
const TONGUE_PHASE_SHIFTS = [0, Math.PI / 3, (2 * Math.PI) / 3, Math.PI, (4 * Math.PI) / 3, (5 * Math.PI) / 3];

/** Sacred Tongue → chirality mapping */
const TONGUE_CHIRALITY: Record<TongueName, ChiralSector> = {
  KO: 'right', // even index 0 → right-handed
  AV: 'left',  // odd index 1 → left-handed
  RU: 'right', // even index 2 → right-handed
  CA: 'left',  // odd index 3 → left-handed
  UM: 'right', // even index 4 → right-handed
  DR: 'left',  // odd index 5 → left-handed
};

/**
 * A node in the chiral governance graph.
 */
export interface ChiralNode {
  /** Node identifier */
  readonly id: string;
  /** Assigned chiral sector */
  sector: ChiralSector;
  /** Associated Sacred Tongue (determines natural sector) */
  tongue: TongueName;
  /** Chiral charge: +1 (right) or -1 (left) */
  charge: 1 | -1;
  /** Local spin state (from BitSpin layer) */
  spinState: 0 | 1;
  /** Chiral phase angle (from tongue phase shift) */
  phase: number;
}

/**
 * A directed edge in the chiral graph with transport asymmetry.
 */
export interface ChiralEdge {
  /** Source node id */
  from: string;
  /** Target node id */
  to: string;
  /** Transport weight (asymmetric: depends on chirality compatibility) */
  weight: number;
  /** Whether this edge crosses chiral sectors */
  crossesSectors: boolean;
  /** Chirality cross-term coupling strength */
  crossTerm: number;
}

/**
 * Result of a chirality compatibility check between two nodes/agents.
 */
export interface ChiralCompatibility {
  /** Whether the two are chirally compatible */
  compatible: boolean;
  /** Interference type */
  interference: 'constructive' | 'destructive' | 'neutral';
  /** Phase difference between the two */
  phaseDifference: number;
  /** Coupling strength (constructive > 0, destructive < 0) */
  couplingStrength: number;
  /** Cross-term contribution from spin × chirality */
  spinChiralCrossTerm: number;
}

/**
 * Configuration for chirality coupling.
 */
export interface ChiralityConfig {
  /** Cross-sector transport penalty (default 0.5 = 50% attenuation) */
  crossSectorPenalty: number;
  /** Spin-chirality coupling constant λ (default 1.0) */
  spinChiralLambda: number;
  /** Minimum compatibility threshold for constructive interference */
  constructiveThreshold: number;
  /** Phase tolerance for alignment detection (radians) */
  phaseTolerance: number;
}

export const DEFAULT_CHIRALITY_CONFIG: ChiralityConfig = {
  crossSectorPenalty: 0.5,
  spinChiralLambda: 1.0,
  constructiveThreshold: 0.5,
  phaseTolerance: Math.PI / 6, // 30 degrees
};

// ═══════════════════════════════════════════════════════════════
// Core Functions
// ═══════════════════════════════════════════════════════════════

/**
 * Get the natural chirality for a Sacred Tongue.
 */
export function tongueSector(tongue: TongueName): ChiralSector {
  return TONGUE_CHIRALITY[tongue];
}

/**
 * Get the chiral charge for a sector: right → +1, left → -1.
 */
export function sectorCharge(sector: ChiralSector): 1 | -1 {
  return sector === 'right' ? 1 : -1;
}

/**
 * Compute the parity operator P that maps left ↔ right.
 *
 * In the governance context, P swaps the roles of even and odd tongues.
 * P(KO) = AV, P(AV) = KO, P(RU) = CA, etc.
 *
 * @param tongue - Input tongue
 * @returns Parity-conjugate tongue
 */
export function parityConjugate(tongue: TongueName): TongueName {
  const idx = TONGUE_NAMES.indexOf(tongue);
  // Swap even ↔ odd by XOR with 1 (within pairs)
  // KO(0)↔AV(1), RU(2)↔CA(3), UM(4)↔DR(5)
  const conjugateIdx = idx ^ 1;
  return TONGUE_NAMES[conjugateIdx];
}

/**
 * Compute chirality compatibility between two nodes.
 *
 * Same sector → constructive interference (aligned charges)
 * Cross sector → destructive interference (opposing charges)
 * Phase alignment further modulates the coupling.
 *
 * The spin-chirality cross-term λ * σ_i * χ_j captures how
 * the local spin state of one node interacts with the global
 * chirality of another — this is what distinguishes chirality
 * coupling from plain spin-spin interaction.
 */
export function computeCompatibility(
  nodeA: ChiralNode,
  nodeB: ChiralNode,
  config: ChiralityConfig = DEFAULT_CHIRALITY_CONFIG
): ChiralCompatibility {
  // Phase difference (modular on [0, 2π])
  const rawDiff = Math.abs(nodeA.phase - nodeB.phase);
  const phaseDifference = Math.min(rawDiff, 2 * Math.PI - rawDiff);

  // Chirality alignment: +1 if same sector, -1 if opposite
  const chiralAlignment = nodeA.charge * nodeB.charge; // +1 or -1

  // Phase alignment factor: cos(Δφ) ∈ [-1, 1]
  const phaseAlignment = Math.cos(phaseDifference);

  // Base coupling: chirality × phase
  const baseCoupling = chiralAlignment * phaseAlignment;

  // Spin-chirality cross-term: λ * (2*s_i - 1) * χ_j
  // Converts spin {0,1} to Ising {-1,+1}, couples with other node's chirality
  const isingA = 2 * nodeA.spinState - 1;
  const isingB = 2 * nodeB.spinState - 1;
  const crossTerm = config.spinChiralLambda * (
    isingA * nodeB.charge + isingB * nodeA.charge
  ) / 2;

  // Total coupling
  const couplingStrength = baseCoupling + crossTerm;

  // Classify interference
  let interference: ChiralCompatibility['interference'];
  if (couplingStrength > config.constructiveThreshold) {
    interference = 'constructive';
  } else if (couplingStrength < -config.constructiveThreshold) {
    interference = 'destructive';
  } else {
    interference = 'neutral';
  }

  return {
    compatible: interference === 'constructive',
    interference,
    phaseDifference,
    couplingStrength,
    spinChiralCrossTerm: crossTerm,
  };
}

/**
 * Compute the transport weight for an edge between two chiral nodes.
 *
 * Same-sector edges have full transport weight.
 * Cross-sector edges are attenuated by the penalty factor.
 * The spin-chirality cross-term can partially restore or further
 * suppress cross-sector transport.
 */
export function computeTransportWeight(
  from: ChiralNode,
  to: ChiralNode,
  baseWeight: number = 1.0,
  config: ChiralityConfig = DEFAULT_CHIRALITY_CONFIG
): ChiralEdge {
  const crossesSectors = from.sector !== to.sector;
  const compat = computeCompatibility(from, to, config);

  let weight = baseWeight;
  if (crossesSectors) {
    // Cross-sector penalty
    weight *= config.crossSectorPenalty;
    // Cross-term can partially restore transport (if spins align favorably)
    weight *= Math.max(0, 1 + compat.spinChiralCrossTerm * 0.5);
  } else {
    // Same-sector boost from constructive interference
    weight *= 1 + Math.max(0, compat.couplingStrength) * 0.2;
  }

  return {
    from: from.id,
    to: to.id,
    weight: Math.max(0, weight),
    crossesSectors,
    crossTerm: compat.spinChiralCrossTerm,
  };
}

// ═══════════════════════════════════════════════════════════════
// Chiral Graph
// ═══════════════════════════════════════════════════════════════

/**
 * Chirality-aware governance graph.
 *
 * Enforces global handedness constraints on the governance mesh:
 * - Nodes are assigned to left or right chiral sectors
 * - Edges have asymmetric transport weights
 * - Automorphisms must preserve chirality (no parity-violating transforms)
 * - Defect propagation follows chiral transport rules
 *
 * The graph acts as a "gauge field" where chirality is the internal
 * symmetry. When connected to BitSpin, the local spin fluctuations
 * become chirality-aware through the cross-term coupling.
 */
export class ChiralGraph {
  private nodes: Map<string, ChiralNode> = new Map();
  private edges: ChiralEdge[] = [];
  private readonly config: ChiralityConfig;

  constructor(config: Partial<ChiralityConfig> = {}) {
    this.config = { ...DEFAULT_CHIRALITY_CONFIG, ...config };
  }

  /**
   * Add a chiral node.
   */
  addNode(id: string, tongue: TongueName, spinState: 0 | 1 = 0): ChiralNode {
    const sector = tongueSector(tongue);
    const tongueIdx = TONGUE_NAMES.indexOf(tongue);
    const node: ChiralNode = {
      id,
      sector,
      tongue,
      charge: sectorCharge(sector),
      spinState,
      phase: TONGUE_PHASE_SHIFTS[tongueIdx],
    };
    this.nodes.set(id, node);
    return node;
  }

  /**
   * Connect two nodes with chirality-aware transport.
   */
  connect(fromId: string, toId: string, baseWeight: number = 1.0): ChiralEdge | null {
    const from = this.nodes.get(fromId);
    const to = this.nodes.get(toId);
    if (!from || !to) return null;

    const edge = computeTransportWeight(from, to, baseWeight, this.config);
    this.edges.push(edge);
    return edge;
  }

  /**
   * Build the full Sacred Tongue hexagonal chiral graph.
   *
   * Creates 6 nodes (one per tongue) with chirality assignments,
   * then connects nearest neighbors and cross-diagonals with
   * chirality-dependent transport weights.
   */
  buildTongueHexagon(baseWeight: number = 1.0): void {
    // Create nodes
    for (const tongue of TONGUE_NAMES) {
      this.addNode(tongue, tongue);
    }

    // Nearest-neighbor ring
    for (let i = 0; i < 6; i++) {
      const next = (i + 1) % 6;
      this.connect(TONGUE_NAMES[i], TONGUE_NAMES[next], baseWeight);
      // Bidirectional
      this.connect(TONGUE_NAMES[next], TONGUE_NAMES[i], baseWeight);
    }

    // Cross-diagonals (φ-attenuated)
    this.connect('KO', 'CA', baseWeight / PHI);
    this.connect('CA', 'KO', baseWeight / PHI);
    this.connect('AV', 'UM', baseWeight / PHI);
    this.connect('UM', 'AV', baseWeight / PHI);
    this.connect('RU', 'DR', baseWeight / PHI);
    this.connect('DR', 'RU', baseWeight / PHI);
  }

  /**
   * Check if a graph automorphism preserves chirality.
   *
   * An automorphism π: V → V is chirality-preserving iff
   * for all nodes v: sector(π(v)) = sector(v).
   *
   * This constrains the symmetry group of the governance graph
   * to the subgroup that respects handedness.
   *
   * @param permutation - Map from node id to permuted node id
   * @returns Whether the permutation preserves chirality
   */
  isChiralityPreserving(permutation: Map<string, string>): boolean {
    for (const [nodeId, targetId] of permutation) {
      const node = this.nodes.get(nodeId);
      const target = this.nodes.get(targetId);
      if (!node || !target) return false;
      if (node.sector !== target.sector) return false;
    }
    return true;
  }

  /**
   * Compute the total chiral charge of a subgraph.
   *
   * Q = Σ χ_i where χ_i = +1 (right) or -1 (left)
   *
   * Charge conservation: the total charge of the full graph
   * should be 0 for a balanced governance system (3 right + 3 left).
   */
  totalCharge(nodeIds?: string[]): number {
    const ids = nodeIds ?? Array.from(this.nodes.keys());
    let charge = 0;
    for (const id of ids) {
      const node = this.nodes.get(id);
      if (node) charge += node.charge;
    }
    return charge;
  }

  /**
   * Compute transport asymmetry between two sectors.
   *
   * Measures how different the total edge weight is from
   * right→left vs left→right. A perfectly symmetric system
   * has asymmetry = 0. Chirality coupling creates natural
   * asymmetry that serves as a security invariant.
   */
  transportAsymmetry(): number {
    let rightToLeft = 0;
    let leftToRight = 0;

    for (const edge of this.edges) {
      const from = this.nodes.get(edge.from);
      const to = this.nodes.get(edge.to);
      if (!from || !to || !edge.crossesSectors) continue;

      if (from.sector === 'right' && to.sector === 'left') {
        rightToLeft += edge.weight;
      } else {
        leftToRight += edge.weight;
      }
    }

    const total = rightToLeft + leftToRight;
    if (total < BRAIN_EPSILON) return 0;

    return Math.abs(rightToLeft - leftToRight) / total;
  }

  /**
   * Update spin states from an external BitSpin field.
   * Recalculates edge weights to reflect spin-chirality coupling.
   */
  updateSpins(spinStates: ReadonlyMap<string, 0 | 1>): void {
    for (const [id, state] of spinStates) {
      const node = this.nodes.get(id);
      if (node) {
        // Create new node with updated spinState (readonly property workaround)
        const updated: ChiralNode = { ...node, spinState: state };
        this.nodes.set(id, updated);
      }
    }

    // Recompute edge weights with updated spin states
    this.recalculateEdges();
  }

  /**
   * Get the graph's chirality-aware adjacency matrix.
   * Entry (i,j) = transport weight from node i to node j.
   * Asymmetric in general due to chirality coupling.
   */
  adjacencyMatrix(): { ids: string[]; matrix: number[][] } {
    const ids = Array.from(this.nodes.keys());
    const n = ids.length;
    const matrix: number[][] = Array.from({ length: n }, () => new Array(n).fill(0));

    for (const edge of this.edges) {
      const i = ids.indexOf(edge.from);
      const j = ids.indexOf(edge.to);
      if (i >= 0 && j >= 0) {
        matrix[i][j] = edge.weight;
      }
    }

    return { ids, matrix };
  }

  /**
   * Get a node by id.
   */
  getNode(id: string): ChiralNode | undefined {
    return this.nodes.get(id);
  }

  /**
   * Get all nodes.
   */
  getAllNodes(): ChiralNode[] {
    return Array.from(this.nodes.values());
  }

  /**
   * Get all edges.
   */
  getAllEdges(): readonly ChiralEdge[] {
    return this.edges;
  }

  // ═══════════════════════════════════════════════════════════════
  // Private
  // ═══════════════════════════════════════════════════════════════

  /**
   * Recalculate all edge weights based on current node states.
   */
  private recalculateEdges(): void {
    const newEdges: ChiralEdge[] = [];
    for (const edge of this.edges) {
      const from = this.nodes.get(edge.from);
      const to = this.nodes.get(edge.to);
      if (!from || !to) continue;

      // Recover approximate base weight (remove chirality effects)
      const baseWeight = edge.crossesSectors
        ? edge.weight / Math.max(BRAIN_EPSILON, this.config.crossSectorPenalty)
        : edge.weight;

      newEdges.push(computeTransportWeight(from, to, baseWeight, this.config));
    }
    this.edges = newEdges;
  }
}
