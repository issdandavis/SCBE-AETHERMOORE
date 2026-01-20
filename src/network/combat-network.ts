/**
 * Combat Network (Redundancy Manager)
 *
 * In combat scenarios, single-path routing is vulnerable. Relays get
 * destroyed or jammed ("caked"). This module implements Multipath Routing
 * with disjoint paths for redundancy.
 *
 * Enhancements:
 * - Full path disjointness (no shared nodes between paths)
 * - Path health monitoring with success/failure tracking
 * - Acknowledgment handling with confirmation and retries
 *
 * References:
 * - arXiv:2204.04489 (ShorTor: Multi-hop Overlay Routing)
 * - Quantum Zeitgeist (Multi-path QKD routing)
 */

import { HybridSpaceCrypto } from './hybrid-crypto.js';
import { RelayNode, SpaceTorRouter } from './space-tor-router.js';

// ============================================================================
// Types
// ============================================================================

export interface TransmissionResult {
  success: boolean;
  pathId: string;
  latencyMs: number;
  acknowledged: boolean;
  retries: number;
  error?: string;
}

export interface PathHealth {
  pathId: string;
  successCount: number;
  failureCount: number;
  successRate: number;
  averageLatencyMs: number;
  lastUsed: number;
  nodeIds: string[];
}

export interface AcknowledgmentConfig {
  enabled: boolean;
  timeoutMs: number;
  maxRetries: number;
}

export interface CombatNetworkConfig {
  acknowledgment: AcknowledgmentConfig;
  minDisjointPaths: number;
  healthTrackingWindow: number; // Number of transmissions to track
}

// ============================================================================
// Path Health Monitor
// ============================================================================

class PathHealthMonitor {
  private pathHistory: Map<string, { success: boolean; latencyMs: number; timestamp: number }[]> = new Map();
  private readonly maxHistorySize: number;

  constructor(historySize: number = 100) {
    this.maxHistorySize = historySize;
  }

  /**
   * Record a transmission result
   */
  public record(pathId: string, nodeIds: string[], success: boolean, latencyMs: number): void {
    const key = this.getPathKey(nodeIds);

    if (!this.pathHistory.has(key)) {
      this.pathHistory.set(key, []);
    }

    const history = this.pathHistory.get(key)!;
    history.push({ success, latencyMs, timestamp: Date.now() });

    // Trim to max size
    if (history.length > this.maxHistorySize) {
      history.shift();
    }
  }

  /**
   * Get health statistics for a path
   */
  public getHealth(nodeIds: string[]): PathHealth {
    const key = this.getPathKey(nodeIds);
    const history = this.pathHistory.get(key) || [];

    const successCount = history.filter(h => h.success).length;
    const failureCount = history.filter(h => !h.success).length;
    const totalLatency = history.reduce((sum, h) => sum + h.latencyMs, 0);

    return {
      pathId: key,
      successCount,
      failureCount,
      successRate: history.length > 0 ? successCount / history.length : 1,
      averageLatencyMs: history.length > 0 ? totalLatency / history.length : 0,
      lastUsed: history.length > 0 ? history[history.length - 1].timestamp : 0,
      nodeIds
    };
  }

  /**
   * Get all tracked paths sorted by success rate
   */
  public getAllPaths(): PathHealth[] {
    const paths: PathHealth[] = [];

    for (const [key, history] of this.pathHistory) {
      const nodeIds = key.split('->');
      paths.push(this.getHealth(nodeIds));
    }

    return paths.sort((a, b) => b.successRate - a.successRate);
  }

  /**
   * Check if a path is healthy (success rate above threshold)
   */
  public isHealthy(nodeIds: string[], minSuccessRate: number = 0.7): boolean {
    const health = this.getHealth(nodeIds);
    // New paths are considered healthy
    if (health.successCount + health.failureCount < 3) {
      return true;
    }
    return health.successRate >= minSuccessRate;
  }

  /**
   * Clear history for a specific path
   */
  public clearPath(nodeIds: string[]): void {
    const key = this.getPathKey(nodeIds);
    this.pathHistory.delete(key);
  }

  /**
   * Clear all history
   */
  public clearAll(): void {
    this.pathHistory.clear();
  }

  private getPathKey(nodeIds: string[]): string {
    return nodeIds.join('->');
  }
}

// ============================================================================
// Combat Network
// ============================================================================

export class CombatNetwork {
  private readonly healthMonitor: PathHealthMonitor;
  private readonly config: CombatNetworkConfig;
  private pendingAcks: Map<string, { resolve: (ack: boolean) => void; timeout: NodeJS.Timeout }> = new Map();

  constructor(
    private router: SpaceTorRouter,
    private crypto: HybridSpaceCrypto,
    config?: Partial<CombatNetworkConfig>
  ) {
    this.config = {
      acknowledgment: {
        enabled: true,
        timeoutMs: 30000, // 30 seconds default
        maxRetries: 3,
        ...config?.acknowledgment
      },
      minDisjointPaths: 2,
      healthTrackingWindow: 100,
      ...config
    };

    this.healthMonitor = new PathHealthMonitor(this.config.healthTrackingWindow);
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
  public async send(
    data: string,
    origin: { x: number; y: number; z: number },
    dest: { x: number; y: number; z: number },
    combatMode: boolean
  ): Promise<TransmissionResult[]> {
    const payload = Buffer.from(data);
    const results: TransmissionResult[] = [];

    if (combatMode) {
      // Generate fully disjoint paths
      const paths = this.generateDisjointPaths(origin, dest, 70, this.config.minDisjointPaths);

      for (let i = 0; i < paths.length; i++) {
        const pathId = i === 0 ? 'PRIMARY' : `BACKUP-${i}`;
        console.log(`[COMBAT] Routing via ${pathId}: ${paths[i].map(n => n.id).join(' -> ')}`);
      }

      // Encrypt & Send in Parallel
      const onions = await Promise.all(
        paths.map(path => this.crypto.buildOnion(payload, path))
      );

      // Dispatch with acknowledgment handling
      const transmissions = paths.map((path, i) => {
        const pathId = i === 0 ? 'PRIMARY' : `BACKUP-${i}`;
        return this.transmitWithAck(path, onions[i], pathId);
      });

      const pathResults = await Promise.all(transmissions);
      results.push(...pathResults);
    } else {
      // Standard Routing
      const path = this.router.calculatePath(origin, dest, 50);
      console.log(`[STANDARD] Routing via: ${path.map(n => n.id).join(' -> ')}`);

      const onion = await this.crypto.buildOnion(payload, path);
      const result = await this.transmitWithAck(path, onion, 'STANDARD');
      results.push(result);
    }

    return results;
  }

  /**
   * Generate multiple fully disjoint paths
   *
   * Enhancement #2: Full path disjointness - no shared nodes between any paths
   *
   * @param origin - Origin coordinates
   * @param dest - Destination coordinates
   * @param minTrust - Minimum trust score
   * @param numPaths - Number of disjoint paths to generate
   * @returns Array of disjoint paths
   */
  public generateDisjointPaths(
    origin: { x: number; y: number; z: number },
    dest: { x: number; y: number; z: number },
    minTrust: number,
    numPaths: number
  ): RelayNode[][] {
    const paths: RelayNode[][] = [];
    const usedNodes = new Set<string>();

    for (let i = 0; i < numPaths; i++) {
      try {
        // Calculate path excluding all previously used nodes
        const path = this.router.calculateDisjointPath(origin, dest, minTrust, usedNodes);

        // Verify path health before using
        const nodeIds = path.map(n => n.id);
        if (!this.healthMonitor.isHealthy(nodeIds)) {
          console.warn(`[COMBAT] Path ${i + 1} has poor health, attempting alternative`);
          // Try to find healthier alternative
          const altPath = this.findHealthyAlternative(origin, dest, minTrust, usedNodes);
          if (altPath) {
            paths.push(altPath);
            altPath.forEach(n => usedNodes.add(n.id));
            continue;
          }
        }

        paths.push(path);

        // Mark all nodes in this path as used
        path.forEach(node => usedNodes.add(node.id));
      } catch (error) {
        if (i === 0) {
          // Must have at least one path
          throw new Error(`Failed to establish primary path: ${error}`);
        }
        console.warn(`[COMBAT] Could not generate disjoint path ${i + 1}: ${error}`);
        // Continue with fewer paths
        break;
      }
    }

    if (paths.length < numPaths) {
      console.warn(`[COMBAT] Only ${paths.length}/${numPaths} disjoint paths available`);
    }

    return paths;
  }

  /**
   * Find a healthy alternative path
   */
  private findHealthyAlternative(
    origin: { x: number; y: number; z: number },
    dest: { x: number; y: number; z: number },
    minTrust: number,
    excludeNodes: Set<string>
  ): RelayNode[] | null {
    const maxAttempts = 5;

    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        // Lower trust threshold slightly for alternatives
        const adjustedTrust = Math.max(minTrust - attempt * 5, 30);
        const path = this.router.calculateDisjointPath(origin, dest, adjustedTrust, excludeNodes);

        const nodeIds = path.map(n => n.id);
        if (this.healthMonitor.isHealthy(nodeIds)) {
          return path;
        }

        // Add unhealthy path nodes to exclusion for next attempt
        path.forEach(n => excludeNodes.add(n.id));
      } catch {
        continue;
      }
    }

    return null;
  }

  /**
   * Transmit with acknowledgment handling
   *
   * Enhancement #4: Acknowledgment handling with confirmation and retries
   */
  private async transmitWithAck(
    path: RelayNode[],
    packet: Buffer,
    pathId: string
  ): Promise<TransmissionResult> {
    const nodeIds = path.map(n => n.id);
    let retries = 0;
    let lastError: string | undefined;

    while (retries <= this.config.acknowledgment.maxRetries) {
      const result = await this.transmit(path[0], packet, pathId);

      if (result.success) {
        if (this.config.acknowledgment.enabled) {
          // Wait for acknowledgment
          const acknowledged = await this.waitForAck(pathId, this.config.acknowledgment.timeoutMs);

          // Record health
          this.healthMonitor.record(pathId, nodeIds, acknowledged, result.latencyMs);

          return {
            ...result,
            acknowledged,
            retries
          };
        }

        // No ack required
        this.healthMonitor.record(pathId, nodeIds, true, result.latencyMs);
        return { ...result, acknowledged: true, retries };
      }

      // Transmission failed
      lastError = result.error;
      retries++;

      if (retries <= this.config.acknowledgment.maxRetries) {
        console.log(`[${pathId}] Retry ${retries}/${this.config.acknowledgment.maxRetries}`);
        // Exponential backoff
        await this.sleep(Math.min(1000 * Math.pow(2, retries), 10000));
      }
    }

    // All retries exhausted
    this.healthMonitor.record(pathId, nodeIds, false, 0);

    return {
      success: false,
      pathId,
      latencyMs: 0,
      acknowledged: false,
      retries,
      error: lastError || 'Max retries exceeded'
    };
  }

  /**
   * Transmit packet to entry node
   */
  private async transmit(
    entryNode: RelayNode,
    packet: Buffer,
    pathId: string
  ): Promise<TransmissionResult> {
    const startTime = Date.now();

    try {
      console.log(`[${pathId}] Transmitting ${packet.length} bytes to Entry Node: ${entryNode.id}`);

      // Simulate transmission delay based on distance
      const latencyMs = this.calculateTransmissionLatency(entryNode);

      // Cap simulation delay for testing (real delay would be actual light-speed)
      const simulatedDelay = Math.min(latencyMs, 100);
      await this.sleep(simulatedDelay);

      // Update node load
      this.router.updateNodeLoad(entryNode.id, entryNode.load + 0.1);

      return {
        success: true,
        pathId,
        latencyMs: Date.now() - startTime,
        acknowledged: false,
        retries: 0
      };
    } catch (error) {
      return {
        success: false,
        pathId,
        latencyMs: Date.now() - startTime,
        acknowledged: false,
        retries: 0,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  /**
   * Wait for acknowledgment from destination
   */
  private waitForAck(pathId: string, timeoutMs: number): Promise<boolean> {
    return new Promise(resolve => {
      const timeout = setTimeout(() => {
        this.pendingAcks.delete(pathId);
        resolve(false); // Timeout - no ack received
      }, timeoutMs);

      this.pendingAcks.set(pathId, { resolve, timeout });

      // Simulate acknowledgment for testing (80% success rate)
      setTimeout(() => {
        if (this.pendingAcks.has(pathId)) {
          const ackSuccess = Math.random() > 0.2;
          this.receiveAck(pathId, ackSuccess);
        }
      }, Math.random() * 50 + 10);
    });
  }

  /**
   * Receive acknowledgment (called by network layer)
   */
  public receiveAck(pathId: string, success: boolean): void {
    const pending = this.pendingAcks.get(pathId);
    if (pending) {
      clearTimeout(pending.timeout);
      this.pendingAcks.delete(pathId);
      pending.resolve(success);
    }
  }

  /**
   * Calculate transmission latency based on node distance
   */
  private calculateTransmissionLatency(node: RelayNode): number {
    // Speed of light: ~300,000 km/s
    // 1 AU ≈ 150 million km
    // Light travel time for 1 AU ≈ 500 seconds = 500,000 ms
    const distance = Math.sqrt(
      node.coords.x ** 2 + node.coords.y ** 2 + node.coords.z ** 2
    );
    return distance * 500000; // ms per AU
  }

  /**
   * Sleep utility
   */
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // ============================================================================
  // Statistics & Monitoring (Enhancement #3)
  // ============================================================================

  /**
   * Get network statistics
   */
  public getNetworkStats(): {
    totalNodes: number;
    quantumCapableNodes: number;
    averageLoad: number;
    averageTrust: number;
  } {
    const nodes = this.router.getNodes();

    if (nodes.length === 0) {
      return {
        totalNodes: 0,
        quantumCapableNodes: 0,
        averageLoad: 0,
        averageTrust: 0
      };
    }

    return {
      totalNodes: nodes.length,
      quantumCapableNodes: nodes.filter(n => n.quantumCapable).length,
      averageLoad: nodes.reduce((sum, n) => sum + n.load, 0) / nodes.length,
      averageTrust: nodes.reduce((sum, n) => sum + n.trustScore, 0) / nodes.length
    };
  }

  /**
   * Get path health statistics
   */
  public getPathHealthStats(): PathHealth[] {
    return this.healthMonitor.getAllPaths();
  }

  /**
   * Get health for a specific path
   */
  public getPathHealth(nodeIds: string[]): PathHealth {
    return this.healthMonitor.getHealth(nodeIds);
  }

  /**
   * Check if network has sufficient healthy paths
   */
  public hasHealthyRedundancy(
    origin: { x: number; y: number; z: number },
    dest: { x: number; y: number; z: number },
    minTrust: number,
    requiredPaths: number = 2
  ): boolean {
    try {
      const paths = this.generateDisjointPaths(origin, dest, minTrust, requiredPaths);
      return paths.length >= requiredPaths;
    } catch {
      return false;
    }
  }

  /**
   * Clear all health history
   */
  public clearHealthHistory(): void {
    this.healthMonitor.clearAll();
  }
}
