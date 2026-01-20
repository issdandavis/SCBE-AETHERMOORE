/**
 * Space-Tor Router
 *
 * Onion routing for space networks with relay node management.
 * Implements path calculation with trust scoring and load balancing.
 */

export interface RelayNode {
  id: string;
  coords: { x: number; y: number; z: number };
  trustScore: number;
  load: number;
  quantumCapable: boolean;
  lastSeen: number;
  bandwidth: number; // Mbps
}

export interface PathConstraints {
  minTrust: number;
  maxLoad?: number;
  requireQuantum?: boolean;
  excludeNodes?: Set<string>;
}

export class SpaceTorRouter {
  private nodes: Map<string, RelayNode> = new Map();
  private readonly minPathLength = 3; // Entry, Middle, Exit

  constructor(initialNodes?: RelayNode[]) {
    if (initialNodes) {
      for (const node of initialNodes) {
        this.nodes.set(node.id, node);
      }
    }
  }

  /**
   * Register a relay node
   */
  public registerNode(node: RelayNode): void {
    this.nodes.set(node.id, node);
  }

  /**
   * Remove a relay node (destroyed/offline)
   */
  public removeNode(nodeId: string): boolean {
    return this.nodes.delete(nodeId);
  }

  /**
   * Get all registered nodes
   */
  public getNodes(): RelayNode[] {
    return Array.from(this.nodes.values());
  }

  /**
   * Get a specific node by ID
   */
  public getNode(nodeId: string): RelayNode | undefined {
    return this.nodes.get(nodeId);
  }

  /**
   * Update node load
   */
  public updateNodeLoad(nodeId: string, load: number): void {
    const node = this.nodes.get(nodeId);
    if (node) {
      node.load = Math.min(1, Math.max(0, load));
    }
  }

  /**
   * Update node trust score
   */
  public updateNodeTrust(nodeId: string, trustScore: number): void {
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
  public calculatePath(
    origin: { x: number; y: number; z: number },
    dest: { x: number; y: number; z: number },
    minTrust: number,
    constraints?: Partial<PathConstraints>
  ): RelayNode[] {
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
  public calculateDisjointPath(
    origin: { x: number; y: number; z: number },
    dest: { x: number; y: number; z: number },
    minTrust: number,
    excludeNodes: Set<string>
  ): RelayNode[] {
    return this.calculatePath(origin, dest, minTrust, { excludeNodes });
  }

  /**
   * Get nodes that meet minimum trust and other constraints
   */
  private getEligibleNodes(
    minTrust: number,
    constraints?: Partial<PathConstraints>
  ): RelayNode[] {
    return Array.from(this.nodes.values()).filter(node => {
      if (node.trustScore < minTrust) return false;
      if (constraints?.maxLoad !== undefined && node.load > constraints.maxLoad) return false;
      if (constraints?.requireQuantum && !node.quantumCapable) return false;
      if (constraints?.excludeNodes?.has(node.id)) return false;
      return true;
    });
  }

  /**
   * Select optimal node based on role and distance
   */
  private selectNode(
    candidates: RelayNode[],
    target: { x: number; y: number; z: number },
    role: 'entry' | 'exit',
    excludeNodes?: Set<string>
  ): RelayNode {
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
  private selectMiddleNode(
    candidates: RelayNode[],
    entry: RelayNode,
    exit: RelayNode,
    excludeNodes?: Set<string>
  ): RelayNode {
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
  private calculateDistance(
    a: { x: number; y: number; z: number },
    b: { x: number; y: number; z: number }
  ): number {
    return Math.sqrt(
      (a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2
    );
  }

  /**
   * Score a node based on trust, distance, and load
   */
  private scoreNode(node: RelayNode, distance: number): number {
    // Higher trust = better, lower distance = better, lower load = better
    return node.trustScore - distance * 10 - node.load * 20;
  }
}
