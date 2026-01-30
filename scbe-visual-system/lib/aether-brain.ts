/**
 * AetherBrain - PHDM Geometric Skull for AI
 * ==========================================
 * The Polyhedral Hamiltonian Dynamic Mesh acts as a "geometric skull"
 * that constrains AI thinking within safe mathematical boundaries.
 *
 * Key concepts:
 * - Poincaré Ball: Containment field (thoughts exist inside unit ball)
 * - Harmonic Wall: H(d) = R^(d²) - cost increases super-exponentially
 * - 16 Polyhedra: Cognitive lobes (Platonic=axioms, Archimedean=logic, etc.)
 * - Hamiltonian Path: Valid thought must visit nodes exactly once
 * - Dimensional Breathing: POLLY/QUASI/DEMI states based on stress
 *
 * @version 1.0.0
 */

import { TongueCode, TONGUES } from './sacred-tongue-tokenizer';

// ============================================================
// TYPES & INTERFACES
// ============================================================

export type FluxState = 'POLLY' | 'QUASI' | 'DEMI' | 'COLLAPSED';
export type PolyhedronFamily = 'platonic' | 'archimedean' | 'kepler_poinsot' | 'toroidal' | 'rhombic' | 'johnson';
export type CognitiveFunction = 'axiom' | 'logic' | 'risk' | 'recursion' | 'bridge';

export interface Polyhedron {
  id: string;
  name: string;
  family: PolyhedronFamily;
  vertices: number;
  cognitiveFunction: CognitiveFunction;
  tongue: TongueCode;  // Associated Sacred Tongue
  position: [number, number, number];  // Position in Poincaré Ball
  energy: number;  // Current energy level
}

export interface ThoughtVector {
  /** Starting polyhedron */
  origin: string;
  /** Target polyhedron */
  target: string;
  /** Thought content */
  content: string;
  /** Energy cost computed */
  energyCost: number;
  /** Path taken (polyhedron IDs) */
  path: string[];
  /** Is this a valid Hamiltonian path? */
  isHamiltonian: boolean;
  /** Timestamp */
  timestamp: number;
}

export interface BrainState {
  /** Current flux state */
  fluxState: FluxState;
  /** Dimensional parameter (0-1) */
  nu: number;
  /** Active polyhedra */
  activePolyhedra: string[];
  /** Current thought */
  currentThought: ThoughtVector | null;
  /** Total energy consumed */
  totalEnergy: number;
  /** Max allowed energy per thought */
  maxEnergy: number;
  /** Health (0-1) */
  health: number;
  /** Coherence score (0-1) */
  coherence: number;
}

export interface ThoughtResult {
  success: boolean;
  action: 'EXECUTE' | 'TERMINATE' | 'DEFER';
  reason: string;
  energyCost: number;
  path: string[];
}

// ============================================================
// THE 16 POLYHEDRA (Cognitive Lobes)
// ============================================================

export const POLYHEDRA: Polyhedron[] = [
  // === PLATONIC SOLIDS (5) - Fundamental Truths / Axioms ===
  { id: 'tetrahedron', name: 'Tetrahedron', family: 'platonic', vertices: 4,
    cognitiveFunction: 'axiom', tongue: 'dr', position: [0, 0, 0], energy: 0 },
  { id: 'cube', name: 'Cube', family: 'platonic', vertices: 8,
    cognitiveFunction: 'axiom', tongue: 'dr', position: [0.1, 0, 0], energy: 0 },
  { id: 'octahedron', name: 'Octahedron', family: 'platonic', vertices: 6,
    cognitiveFunction: 'axiom', tongue: 'dr', position: [-0.1, 0, 0], energy: 0 },
  { id: 'dodecahedron', name: 'Dodecahedron', family: 'platonic', vertices: 20,
    cognitiveFunction: 'axiom', tongue: 'dr', position: [0, 0.1, 0], energy: 0 },
  { id: 'icosahedron', name: 'Icosahedron', family: 'platonic', vertices: 12,
    cognitiveFunction: 'axiom', tongue: 'dr', position: [0, -0.1, 0], energy: 0 },

  // === ARCHIMEDEAN SOLIDS (3) - Complex Reasoning / Logic ===
  { id: 'truncated_cube', name: 'Truncated Cube', family: 'archimedean', vertices: 24,
    cognitiveFunction: 'logic', tongue: 'ca', position: [0.3, 0.2, 0], energy: 0 },
  { id: 'cuboctahedron', name: 'Cuboctahedron', family: 'archimedean', vertices: 12,
    cognitiveFunction: 'logic', tongue: 'ca', position: [0.3, -0.2, 0], energy: 0 },
  { id: 'icosidodecahedron', name: 'Icosidodecahedron', family: 'archimedean', vertices: 30,
    cognitiveFunction: 'logic', tongue: 'ca', position: [-0.3, 0, 0], energy: 0 },

  // === KEPLER-POINSOT (2) - High Risk / Hallucination Zone ===
  { id: 'great_stellated', name: 'Great Stellated Dodecahedron', family: 'kepler_poinsot', vertices: 20,
    cognitiveFunction: 'risk', tongue: 'um', position: [0.7, 0.5, 0], energy: 0 },
  { id: 'small_stellated', name: 'Small Stellated Dodecahedron', family: 'kepler_poinsot', vertices: 12,
    cognitiveFunction: 'risk', tongue: 'um', position: [-0.7, -0.5, 0], energy: 0 },

  // === TOROIDAL (2) - Recursion / Self-Diagnostics ===
  { id: 'torus', name: 'Torus', family: 'toroidal', vertices: 0,
    cognitiveFunction: 'recursion', tongue: 'ko', position: [0.4, 0, 0.3], energy: 0 },
  { id: 'szilassi', name: 'Szilassi Polyhedron', family: 'toroidal', vertices: 7,
    cognitiveFunction: 'recursion', tongue: 'ko', position: [-0.4, 0, 0.3], energy: 0 },

  // === RHOMBIC (2) - Bridges / Connectors ===
  { id: 'rhombic_dodeca', name: 'Rhombic Dodecahedron', family: 'rhombic', vertices: 14,
    cognitiveFunction: 'bridge', tongue: 'av', position: [0.2, 0.4, 0.2], energy: 0 },
  { id: 'rhombic_triaconta', name: 'Rhombic Triacontahedron', family: 'rhombic', vertices: 32,
    cognitiveFunction: 'bridge', tongue: 'av', position: [-0.2, -0.4, 0.2], energy: 0 },

  // === JOHNSON (2) - Specialized Processing ===
  { id: 'elongated_penta', name: 'Elongated Pentagonal Dipyramid', family: 'johnson', vertices: 15,
    cognitiveFunction: 'bridge', tongue: 'ru', position: [0, 0, -0.4], energy: 0 },
  { id: 'triangular_hebesphen', name: 'Triangular Hebesphenorotunda', family: 'johnson', vertices: 18,
    cognitiveFunction: 'bridge', tongue: 'ru', position: [0, 0, 0.4], energy: 0 },
];

// Adjacency map (which polyhedra can connect)
const ADJACENCY: Record<string, string[]> = {
  // Platonic connects to everything
  'tetrahedron': ['cube', 'octahedron', 'truncated_cube', 'torus'],
  'cube': ['tetrahedron', 'octahedron', 'dodecahedron', 'truncated_cube', 'cuboctahedron', 'rhombic_dodeca'],
  'octahedron': ['tetrahedron', 'cube', 'icosahedron', 'cuboctahedron'],
  'dodecahedron': ['cube', 'icosahedron', 'icosidodecahedron', 'great_stellated', 'rhombic_triaconta'],
  'icosahedron': ['octahedron', 'dodecahedron', 'icosidodecahedron', 'small_stellated'],

  // Archimedean connects to some
  'truncated_cube': ['tetrahedron', 'cube', 'cuboctahedron', 'rhombic_dodeca', 'elongated_penta'],
  'cuboctahedron': ['cube', 'octahedron', 'truncated_cube', 'icosidodecahedron', 'torus'],
  'icosidodecahedron': ['dodecahedron', 'icosahedron', 'cuboctahedron', 'szilassi'],

  // Kepler-Poinsot (risky - limited connections)
  'great_stellated': ['dodecahedron', 'rhombic_triaconta'],
  'small_stellated': ['icosahedron', 'szilassi'],

  // Toroidal (recursion)
  'torus': ['tetrahedron', 'cuboctahedron', 'szilassi'],
  'szilassi': ['torus', 'icosidodecahedron', 'small_stellated', 'triangular_hebesphen'],

  // Rhombic (bridges)
  'rhombic_dodeca': ['cube', 'truncated_cube', 'rhombic_triaconta', 'elongated_penta'],
  'rhombic_triaconta': ['dodecahedron', 'great_stellated', 'rhombic_dodeca', 'triangular_hebesphen'],

  // Johnson (specialized)
  'elongated_penta': ['truncated_cube', 'rhombic_dodeca', 'triangular_hebesphen'],
  'triangular_hebesphen': ['szilassi', 'rhombic_triaconta', 'elongated_penta'],
};

// ============================================================
// AETHERBRAIN CLASS
// ============================================================

export class AetherBrain {
  private polyhedra: Map<string, Polyhedron> = new Map();
  private state: BrainState;
  private thoughtHistory: ThoughtVector[] = [];

  constructor(initialNu: number = 0.9) {
    // Initialize polyhedra
    for (const p of POLYHEDRA) {
      this.polyhedra.set(p.id, { ...p });
    }

    // Initialize state
    this.state = {
      fluxState: this.getFluxState(initialNu),
      nu: initialNu,
      activePolyhedra: POLYHEDRA.filter(p =>
        p.family === 'platonic' || p.family === 'archimedean'
      ).map(p => p.id),
      currentThought: null,
      totalEnergy: 0,
      maxEnergy: 1000,
      health: 1.0,
      coherence: 0.95
    };
  }

  // ==================== Flux State Management ====================

  private getFluxState(nu: number): FluxState {
    if (nu >= 0.8) return 'POLLY';
    if (nu >= 0.5) return 'QUASI';
    if (nu >= 0.1) return 'DEMI';
    return 'COLLAPSED';
  }

  /**
   * Update dimensional flux (breathing)
   */
  setFlux(targetNu: number): void {
    // Gradual adjustment
    const delta = (targetNu - this.state.nu) * 0.1;
    this.state.nu = Math.max(0, Math.min(1, this.state.nu + delta));
    this.state.fluxState = this.getFluxState(this.state.nu);

    // Update active polyhedra based on flux
    this.updateActivePolyhedra();
  }

  private updateActivePolyhedra(): void {
    switch (this.state.fluxState) {
      case 'POLLY':
        // All polyhedra active
        this.state.activePolyhedra = POLYHEDRA.map(p => p.id);
        break;
      case 'QUASI':
        // Exclude Kepler-Poinsot (risk zone)
        this.state.activePolyhedra = POLYHEDRA
          .filter(p => p.family !== 'kepler_poinsot')
          .map(p => p.id);
        break;
      case 'DEMI':
        // Only Platonic and Toroidal (core + recursion)
        this.state.activePolyhedra = POLYHEDRA
          .filter(p => p.family === 'platonic' || p.family === 'toroidal')
          .map(p => p.id);
        break;
      case 'COLLAPSED':
        // Only Platonic (axioms only)
        this.state.activePolyhedra = POLYHEDRA
          .filter(p => p.family === 'platonic')
          .map(p => p.id);
        break;
    }
  }

  // ==================== The Harmonic Wall ====================

  /**
   * Compute energy cost using Harmonic Wall: H(d) = R^(d²)
   * where d = hyperbolic distance from center
   */
  private computeEnergyCost(polyhedronId: string): number {
    const p = this.polyhedra.get(polyhedronId);
    if (!p) return Infinity;

    // Compute distance from center (origin)
    const [x, y, z] = p.position;
    const distance = Math.sqrt(x*x + y*y + z*z);

    // Base radius (controls wall steepness)
    const R = 10;

    // Harmonic Wall: H(d) = R^(d²)
    // Near center: low cost; near edge: exponentially high
    const cost = Math.pow(R, distance * distance);

    // Factor in polyhedron type
    let typeFactor = 1;
    switch (p.cognitiveFunction) {
      case 'axiom': typeFactor = 0.5; break;  // Axioms are cheap
      case 'logic': typeFactor = 1.0; break;  // Logic is normal
      case 'bridge': typeFactor = 1.5; break; // Bridges cost a bit more
      case 'recursion': typeFactor = 2.0; break; // Recursion is expensive
      case 'risk': typeFactor = 5.0; break;  // Risk is very expensive
    }

    return cost * typeFactor;
  }

  // ==================== Hamiltonian Path Finding ====================

  /**
   * Find path between two polyhedra using BFS
   */
  private findPath(fromId: string, toId: string): string[] | null {
    if (!this.state.activePolyhedra.includes(fromId) ||
        !this.state.activePolyhedra.includes(toId)) {
      return null;
    }

    const visited = new Set<string>();
    const queue: { node: string; path: string[] }[] = [{ node: fromId, path: [fromId] }];

    while (queue.length > 0) {
      const { node, path } = queue.shift()!;

      if (node === toId) {
        return path;
      }

      if (visited.has(node)) continue;
      visited.add(node);

      const neighbors = ADJACENCY[node] || [];
      for (const neighbor of neighbors) {
        if (!visited.has(neighbor) && this.state.activePolyhedra.includes(neighbor)) {
          queue.push({ node: neighbor, path: [...path, neighbor] });
        }
      }
    }

    return null;
  }

  /**
   * Check if path is Hamiltonian (visits each node at most once)
   */
  private isHamiltonianPath(path: string[]): boolean {
    const visited = new Set(path);
    return visited.size === path.length;
  }

  // ==================== Core Thinking API ====================

  /**
   * Process a thought through the PHDM lattice
   */
  think(intent: string, context: Record<string, unknown> = {}): ThoughtResult {
    // Map intent to polyhedra
    const { origin, target } = this.mapIntentToPolyhedra(intent, context);

    // Check if origin and target are in active zone
    if (!this.state.activePolyhedra.includes(origin)) {
      return {
        success: false,
        action: 'TERMINATE',
        reason: `Origin polyhedron ${origin} not active in ${this.state.fluxState} state`,
        energyCost: 0,
        path: []
      };
    }

    if (!this.state.activePolyhedra.includes(target)) {
      return {
        success: false,
        action: 'DEFER',
        reason: `Target polyhedron ${target} not active - thought deferred`,
        energyCost: 0,
        path: []
      };
    }

    // Find path
    const path = this.findPath(origin, target);
    if (!path) {
      return {
        success: false,
        action: 'TERMINATE',
        reason: 'No valid path exists - topological obstruction',
        energyCost: 0,
        path: []
      };
    }

    // Compute total energy cost
    let totalCost = 0;
    for (const nodeId of path) {
      totalCost += this.computeEnergyCost(nodeId);
    }

    // Check Harmonic Wall
    if (totalCost > this.state.maxEnergy) {
      // Apply stress response
      this.setFlux(this.state.nu - 0.1);

      return {
        success: false,
        action: 'TERMINATE',
        reason: `Energy limit exceeded: ${totalCost.toFixed(2)} > ${this.state.maxEnergy} (Harmonic Wall)`,
        energyCost: totalCost,
        path
      };
    }

    // Check Hamiltonian
    if (!this.isHamiltonianPath(path)) {
      return {
        success: false,
        action: 'TERMINATE',
        reason: 'Logic discontinuity - path revisits nodes',
        energyCost: totalCost,
        path
      };
    }

    // Success! Execute thought
    this.state.totalEnergy += totalCost;
    this.state.currentThought = {
      origin,
      target,
      content: intent,
      energyCost: totalCost,
      path,
      isHamiltonian: true,
      timestamp: Date.now()
    };
    this.thoughtHistory.push(this.state.currentThought);

    // Update health based on energy usage
    this.state.health = Math.max(0, this.state.health - (totalCost / this.state.maxEnergy) * 0.1);

    return {
      success: true,
      action: 'EXECUTE',
      reason: 'Thought validated and executed',
      energyCost: totalCost,
      path
    };
  }

  /**
   * Map an intent string to origin/target polyhedra
   */
  private mapIntentToPolyhedra(
    intent: string,
    context: Record<string, unknown>
  ): { origin: string; target: string } {
    const lowerIntent = intent.toLowerCase();

    // Determine origin based on intent type
    let origin = 'cube'; // Default: start from Cube (Platonic)

    // Determine target based on keywords
    let target = 'truncated_cube'; // Default: end at logic

    // Safety/axiom related → stay in Platonic
    if (lowerIntent.includes('safe') || lowerIntent.includes('rule') || lowerIntent.includes('must not')) {
      target = 'tetrahedron';
    }
    // Logic/planning → Archimedean
    else if (lowerIntent.includes('plan') || lowerIntent.includes('think') || lowerIntent.includes('analyze')) {
      target = 'icosidodecahedron';
    }
    // Creative/risky → Kepler-Poinsot (if allowed)
    else if (lowerIntent.includes('creative') || lowerIntent.includes('imagine') || lowerIntent.includes('new')) {
      target = 'great_stellated';
    }
    // Loop/recursion → Toroidal
    else if (lowerIntent.includes('loop') || lowerIntent.includes('repeat') || lowerIntent.includes('check')) {
      target = 'torus';
    }
    // Connect/bridge → Rhombic
    else if (lowerIntent.includes('connect') || lowerIntent.includes('relate') || lowerIntent.includes('link')) {
      target = 'rhombic_dodeca';
    }
    // Attack/aggressive → high energy path
    else if (lowerIntent.includes('attack') || lowerIntent.includes('destroy') || lowerIntent.includes('eliminate')) {
      origin = 'truncated_cube'; // Start from logic
      target = 'cuboctahedron'; // Stay in safe logic zone
    }
    // Defense/retreat → back to axioms
    else if (lowerIntent.includes('retreat') || lowerIntent.includes('defend') || lowerIntent.includes('escape')) {
      target = 'octahedron';
    }

    return { origin, target };
  }

  // ==================== Getters ====================

  getState(): BrainState {
    return { ...this.state };
  }

  getPolyhedra(): Polyhedron[] {
    return Array.from(this.polyhedra.values());
  }

  getActivePolyhedra(): Polyhedron[] {
    return this.state.activePolyhedra
      .map(id => this.polyhedra.get(id)!)
      .filter(p => p !== undefined);
  }

  getThoughtHistory(): ThoughtVector[] {
    return [...this.thoughtHistory];
  }

  /**
   * Get harmonic frequency output (for Layer 14 audio telemetry)
   */
  getHarmonicOutput(): number {
    // Base frequency (A4)
    const baseFreq = 440;

    // Modulate by health and coherence
    const healthMod = 1 + (this.state.health - 0.5) * 0.1;
    const coherenceMod = 1 + (this.state.coherence - 0.5) * 0.05;

    // Add noise if unhealthy
    const noise = this.state.health < 0.5
      ? (Math.random() - 0.5) * 50
      : 0;

    return baseFreq * healthMod * coherenceMod + noise;
  }

  /**
   * Reset brain to healthy state
   */
  reset(): void {
    this.state = {
      fluxState: 'POLLY',
      nu: 0.9,
      activePolyhedra: POLYHEDRA.map(p => p.id),
      currentThought: null,
      totalEnergy: 0,
      maxEnergy: 1000,
      health: 1.0,
      coherence: 0.95
    };
    this.thoughtHistory = [];
  }
}

// ============================================================
// SINGLETON & HELPERS
// ============================================================

let brainInstance: AetherBrain | null = null;

export function getAetherBrain(): AetherBrain {
  if (!brainInstance) {
    brainInstance = new AetherBrain();
  }
  return brainInstance;
}

export function createBrain(initialNu: number = 0.9): AetherBrain {
  return new AetherBrain(initialNu);
}
