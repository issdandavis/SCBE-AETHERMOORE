/**
 * Space Tor Router - 3D Spatial Pathfinding
 * 
 * Standard Tor selects nodes randomly. In space, light lag is the enemy.
 * This router uses weighted selection: balances anonymity (randomness) 
 * against latency (physical distance) and trust.
 * 
 * References:
 * - arXiv:2508.17651 (Path Selection Strategies in Tor)
 * - arXiv:2406.15055 (SaTor: Satellite Routing)
 */

export interface RelayNode {
  id: string;
  coords: { x: number; y: number; z: number }; // AU from Sol
  trustScore: number; // 0-100
  quantumCapable: boolean;
  load: number; // Current packet load (0.0-1.0)
}

export class SpaceTorRouter {
  private nodes: Map<string, RelayNode>;

  constructor(nodes: RelayNode[]) {
    this.nodes = new Map(nodes.map(n => [n.id, n]));
  }

  /**
   * Core Logic: Select a 3-hop path balancing Latency vs. Trust
   * 
   * @param origin - Origin coordinates (AU from Sol)
   * @param dest - Destination coordinates (AU from Sol)
   * @param minTrust - Minimum trust score threshold (default 60)
   * @returns Array of 3 RelayNodes [entry, middle, exit]
   */
  public calculatePath(
    origin: { x: number; y: number; z: number },
    dest: { x: number; y: number; z: number },
    minTrust: number = 60
  ): RelayNode[] {
    // 1. Filter usable nodes
    const candidates = Array.from(this.nodes.values()).filter(
      n => n.trustScore >= minTrust && n.load < 0.9
    );

    if (candidates.length < 3) {
      throw new Error(`Insufficient relay nodes (need 3, have ${candidates.length})`);
    }

    // 2. Entry Node: Prioritize trust (Guard Node) close to origin
    const entryCandidates = candidates.filter(n => n.trustScore > 80);
    if (entryCandidates.length === 0) {
      throw new Error('No high-trust entry nodes available');
    }
    const entry = this.selectWeightedNode(entryCandidates, origin, 0.7); // 70% weight on distance

    // 3. Exit Node: Prioritize exit capabilities close to destination
    const exit = this.selectWeightedNode(candidates, dest, 0.8);

    // 4. Middle Node: Maximum entropy (randomness) to break correlation
    // Must not be Entry or Exit
    const middleCandidates = candidates.filter(
      n => n.id !== entry.id && n.id !== exit.id
    );
    
    if (middleCandidates.length === 0) {
      throw new Error('No middle node candidates available');
    }

    const middle = middleCandidates[Math.floor(Math.random() * middleCandidates.length)];

    return [entry, middle, exit];
  }

  /**
   * Weight Calculation: Lower score is better
   * 
   * Cost = (Distance * Weight) - (Trust * InverseWeight)
   * 
   * @param pool - Candidate nodes
   * @param target - Target coordinates
   * @param distWeight - Weight for distance (0.0-1.0)
   * @returns Best node based on weighted cost
   */
  private selectWeightedNode(
    pool: RelayNode[],
    target: { x: number; y: number; z: number },
    distWeight: number
  ): RelayNode {
    return pool.reduce((best, current) => {
      const dist = this.distance3D(current.coords, target);
      // Cost = (Distance * Weight) - (Trust * InverseWeight)
      const cost = (dist * distWeight) - (current.trustScore * (1 - distWeight));

      const bestDist = this.distance3D(best.coords, target);
      const bestCost = (bestDist * distWeight) - (best.trustScore * (1 - distWeight));

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
  private distance3D(
    p1: { x: number; y: number; z: number },
    p2: { x: number; y: number; z: number }
  ): number {
    return Math.sqrt(
      Math.pow(p2.x - p1.x, 2) +
      Math.pow(p2.y - p1.y, 2) +
      Math.pow(p2.z - p1.z, 2)
    );
  }

  /**
   * Get all nodes
   */
  public getNodes(): RelayNode[] {
    return Array.from(this.nodes.values());
  }

  /**
   * Update node load
   */
  public updateNodeLoad(nodeId: string, load: number): void {
    const node = this.nodes.get(nodeId);
    if (node) {
      node.load = Math.max(0, Math.min(1, load));
    }
  }

  /**
   * Update node trust score
   */
  public updateNodeTrust(nodeId: string, trustScore: number): void {
    const node = this.nodes.get(nodeId);
    if (node) {
      node.trustScore = Math.max(0, Math.min(100, trustScore));
    }
  }
}
