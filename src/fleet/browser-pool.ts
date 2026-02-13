/**
 * @file browser-pool.ts
 * @module fleet/browser-pool
 * @layer Layer 5, Layer 13
 * @component Memory-Aware Browser Instance Pool
 * @version 1.0.0
 *
 * Manages a pool of browser instances for multi-AI agent orchestration.
 *
 * Problem: Each browser instance (Playwright/Puppeteer/CDP) consumes
 * 50-200 MB of RAM. When multiple AI agents each need browser access,
 * memory becomes the bottleneck — not CPU or network.
 *
 * Solution: A shared pool with:
 *   - Memory budget enforcement (configurable global limit)
 *   - Per-instance memory tracking
 *   - LRU eviction when budget is exceeded
 *   - Concurrent session limits per AI agent
 *   - Health monitoring and auto-recovery
 *   - Warm instance reuse to reduce startup latency
 *
 * Architecture:
 *
 *   AI Agent 1 ─┐
 *   AI Agent 2 ─┤─→ BrowserPool ─┬→ Instance A (120 MB, active)
 *   AI Agent 3 ─┘                ├→ Instance B (85 MB, idle)
 *                                ├→ Instance C (150 MB, active)
 *                                └→ [evicted when budget exceeded]
 *
 * Integration:
 *   - fleet/crawl-runner.ts → uses pool for browser backends
 *   - browser/agent.ts → BrowserBackend interface compatibility
 *   - ai_brain/detection.ts → trajectory-based anomaly detection per instance
 */

import type { BrowserBackend } from '../browser/agent.js';

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

/** Browser pool configuration */
export interface BrowserPoolConfig {
  /** Maximum total memory budget in MB (default: 2048 = 2 GB) */
  maxMemoryMB: number;
  /** Maximum concurrent instances (default: 8) */
  maxInstances: number;
  /** Maximum instances per AI agent (default: 3) */
  maxPerAgent: number;
  /** Estimated memory per new instance in MB (default: 150) */
  estimatedInstanceMemoryMB: number;
  /** Idle timeout before eviction in ms (default: 300000 = 5 min) */
  idleTimeoutMs: number;
  /** Health check interval in ms (default: 30000 = 30s) */
  healthCheckIntervalMs: number;
  /** Enable warm instance reuse (default: true) */
  warmReuse: boolean;
}

/** Default pool configuration */
export const DEFAULT_POOL_CONFIG: BrowserPoolConfig = {
  maxMemoryMB: 2048,
  maxInstances: 8,
  maxPerAgent: 3,
  estimatedInstanceMemoryMB: 150,
  idleTimeoutMs: 300_000,
  healthCheckIntervalMs: 30_000,
  warmReuse: true,
};

/** Status of a pooled browser instance */
export type InstanceStatus =
  | 'initializing'
  | 'idle'
  | 'active'
  | 'unhealthy'
  | 'evicting';

/** Pooled browser instance descriptor */
export interface PooledInstance {
  /** Unique instance ID */
  readonly id: string;
  /** AI agent that owns this instance */
  readonly agentId: string;
  /** Current status */
  status: InstanceStatus;
  /** Browser backend reference */
  backend: BrowserBackend;
  /** Estimated memory usage in MB */
  memoryMB: number;
  /** Current URL (if navigated) */
  currentUrl: string;
  /** When the instance was created */
  readonly createdAt: number;
  /** Last time the instance was used */
  lastUsedAt: number;
  /** Number of actions executed */
  actionCount: number;
  /** Number of errors encountered */
  errorCount: number;
  /** Tags for warm reuse matching */
  tags: Set<string>;
}

/** Result of an acquire request */
export interface AcquireResult {
  /** Whether acquisition succeeded */
  success: boolean;
  /** The instance if acquired */
  instance?: PooledInstance;
  /** Reason for failure */
  reason?: string;
  /** Whether this was a reused warm instance */
  reused: boolean;
}

/** Pool statistics */
export interface PoolStats {
  /** Total instances in pool */
  totalInstances: number;
  /** Active (in-use) instances */
  activeInstances: number;
  /** Idle instances available for reuse */
  idleInstances: number;
  /** Unhealthy instances */
  unhealthyInstances: number;
  /** Total estimated memory usage in MB */
  totalMemoryMB: number;
  /** Memory budget remaining in MB */
  availableMemoryMB: number;
  /** Memory budget utilization (0-1) */
  memoryUtilization: number;
  /** Total instances created (lifetime) */
  totalCreated: number;
  /** Total instances evicted (lifetime) */
  totalEvicted: number;
  /** Total warm reuses */
  totalReuses: number;
  /** Per-agent instance counts */
  agentCounts: Record<string, number>;
}

/** Memory pressure levels */
export type MemoryPressure = 'low' | 'medium' | 'high' | 'critical';

/** Eviction event for listeners */
export interface EvictionEvent {
  instanceId: string;
  agentId: string;
  reason: 'memory' | 'idle' | 'unhealthy' | 'manual';
  memoryFreedMB: number;
  timestamp: number;
}

// ═══════════════════════════════════════════════════════════════
// BrowserPool
// ═══════════════════════════════════════════════════════════════

/**
 * Memory-aware browser instance pool.
 *
 * Manages shared browser instances across multiple AI agents with
 * memory budgeting, LRU eviction, and warm instance reuse.
 *
 * Usage:
 * ```typescript
 * const pool = new BrowserPool({ maxMemoryMB: 1024, maxInstances: 4 });
 *
 * // AI Agent acquires a browser instance
 * const result = pool.acquire('agent-1', backendFactory);
 * if (result.success) {
 *   await result.instance!.backend.navigate('https://example.com');
 *   pool.markActive(result.instance!.id);
 *   // ... use the browser ...
 *   pool.release(result.instance!.id);
 * }
 *
 * // Check memory pressure
 * if (pool.memoryPressure === 'critical') {
 *   pool.evictLRU();
 * }
 * ```
 */
export class BrowserPool {
  private config: BrowserPoolConfig;
  private instances: Map<string, PooledInstance> = new Map();
  private instanceCounter = 0;
  private totalCreated = 0;
  private totalEvicted = 0;
  private totalReuses = 0;
  private evictionListeners: Array<(event: EvictionEvent) => void> = [];

  constructor(config: Partial<BrowserPoolConfig> = {}) {
    this.config = { ...DEFAULT_POOL_CONFIG, ...config };
  }

  // ═══════════════════════════════════════════════════════════
  // Acquisition
  // ═══════════════════════════════════════════════════════════

  /**
   * Acquire a browser instance for an AI agent.
   *
   * 1. Check per-agent limit
   * 2. Try warm reuse (idle instance with matching tags)
   * 3. Check memory budget
   * 4. Evict LRU if needed
   * 5. Create new instance
   *
   * @param agentId - AI agent requesting the instance
   * @param backend - Browser backend to use
   * @param tags - Optional tags for warm reuse matching
   * @returns AcquireResult with instance or failure reason
   */
  acquire(
    agentId: string,
    backend: BrowserBackend,
    tags: string[] = [],
  ): AcquireResult {
    // Check per-agent limit
    const agentInstances = this.getAgentInstances(agentId);
    if (agentInstances.length >= this.config.maxPerAgent) {
      return {
        success: false,
        reason: `Agent ${agentId} at max instances (${this.config.maxPerAgent})`,
        reused: false,
      };
    }

    // Try warm reuse
    if (this.config.warmReuse && tags.length > 0) {
      const warm = this.findWarmInstance(agentId, tags);
      if (warm) {
        warm.status = 'active';
        warm.lastUsedAt = Date.now();
        this.totalReuses++;
        return { success: true, instance: warm, reused: true };
      }
    }

    // Check global instance limit
    if (this.instances.size >= this.config.maxInstances) {
      // Try evicting an idle instance
      const evicted = this.evictLRU();
      if (!evicted) {
        return {
          success: false,
          reason: `Pool at max instances (${this.config.maxInstances}) with no idle instances to evict`,
          reused: false,
        };
      }
    }

    // Check memory budget
    const currentMemory = this.totalMemoryMB;
    if (currentMemory + this.config.estimatedInstanceMemoryMB > this.config.maxMemoryMB) {
      // Try evicting to make room
      const needed = currentMemory + this.config.estimatedInstanceMemoryMB - this.config.maxMemoryMB;
      const freed = this.evictToFree(needed);
      if (freed < needed) {
        return {
          success: false,
          reason: `Insufficient memory: need ${needed.toFixed(0)} MB, freed ${freed.toFixed(0)} MB`,
          reused: false,
        };
      }
    }

    // Create new instance
    const id = `browser-${++this.instanceCounter}`;
    const instance: PooledInstance = {
      id,
      agentId,
      status: 'active',
      backend,
      memoryMB: this.config.estimatedInstanceMemoryMB,
      currentUrl: 'about:blank',
      createdAt: Date.now(),
      lastUsedAt: Date.now(),
      actionCount: 0,
      errorCount: 0,
      tags: new Set(tags),
    };

    this.instances.set(id, instance);
    this.totalCreated++;

    return { success: true, instance, reused: false };
  }

  // ═══════════════════════════════════════════════════════════
  // Release & Lifecycle
  // ═══════════════════════════════════════════════════════════

  /**
   * Release an instance back to idle (available for warm reuse).
   */
  release(instanceId: string): boolean {
    const instance = this.instances.get(instanceId);
    if (!instance) return false;

    instance.status = 'idle';
    instance.lastUsedAt = Date.now();
    return true;
  }

  /**
   * Mark an instance as active (in use).
   */
  markActive(instanceId: string): boolean {
    const instance = this.instances.get(instanceId);
    if (!instance) return false;

    instance.status = 'active';
    instance.lastUsedAt = Date.now();
    instance.actionCount++;
    return true;
  }

  /**
   * Update the memory estimate for an instance.
   */
  updateMemory(instanceId: string, memoryMB: number): boolean {
    const instance = this.instances.get(instanceId);
    if (!instance) return false;

    instance.memoryMB = memoryMB;
    return true;
  }

  /**
   * Update the current URL for an instance.
   */
  updateUrl(instanceId: string, url: string): void {
    const instance = this.instances.get(instanceId);
    if (instance) {
      instance.currentUrl = url;
    }
  }

  /**
   * Record an error on an instance.
   */
  recordError(instanceId: string): void {
    const instance = this.instances.get(instanceId);
    if (instance) {
      instance.errorCount++;
      if (instance.errorCount >= 5) {
        instance.status = 'unhealthy';
      }
    }
  }

  // ═══════════════════════════════════════════════════════════
  // Eviction
  // ═══════════════════════════════════════════════════════════

  /**
   * Evict the least-recently-used idle instance.
   *
   * @returns true if an instance was evicted
   */
  evictLRU(): boolean {
    let oldest: PooledInstance | null = null;

    for (const instance of this.instances.values()) {
      if (instance.status !== 'idle') continue;
      if (!oldest || instance.lastUsedAt < oldest.lastUsedAt) {
        oldest = instance;
      }
    }

    if (!oldest) return false;
    return this.evict(oldest.id, 'memory');
  }

  /**
   * Evict enough idle instances to free at least `neededMB` of memory.
   *
   * @param neededMB - Memory to free in MB
   * @returns Total memory freed in MB
   */
  evictToFree(neededMB: number): number {
    let freed = 0;

    // Sort idle instances by lastUsedAt (LRU first)
    const idle = [...this.instances.values()]
      .filter((i) => i.status === 'idle')
      .sort((a, b) => a.lastUsedAt - b.lastUsedAt);

    for (const instance of idle) {
      if (freed >= neededMB) break;
      const mem = instance.memoryMB;
      if (this.evict(instance.id, 'memory')) {
        freed += mem;
      }
    }

    return freed;
  }

  /**
   * Evict all idle instances that have been idle longer than the timeout.
   *
   * @returns Number of instances evicted
   */
  evictStale(): number {
    const now = Date.now();
    let count = 0;

    for (const instance of [...this.instances.values()]) {
      if (instance.status === 'idle' && now - instance.lastUsedAt > this.config.idleTimeoutMs) {
        if (this.evict(instance.id, 'idle')) count++;
      }
    }

    return count;
  }

  /**
   * Evict all unhealthy instances.
   *
   * @returns Number of instances evicted
   */
  evictUnhealthy(): number {
    let count = 0;
    for (const instance of [...this.instances.values()]) {
      if (instance.status === 'unhealthy') {
        if (this.evict(instance.id, 'unhealthy')) count++;
      }
    }
    return count;
  }

  /**
   * Manually destroy an instance.
   */
  destroy(instanceId: string): boolean {
    return this.evict(instanceId, 'manual');
  }

  // ═══════════════════════════════════════════════════════════
  // Queries
  // ═══════════════════════════════════════════════════════════

  /**
   * Get an instance by ID.
   */
  getInstance(instanceId: string): PooledInstance | undefined {
    return this.instances.get(instanceId);
  }

  /**
   * Get all instances for a specific AI agent.
   */
  getAgentInstances(agentId: string): PooledInstance[] {
    return [...this.instances.values()].filter((i) => i.agentId === agentId);
  }

  /**
   * Get all instances.
   */
  getAllInstances(): PooledInstance[] {
    return [...this.instances.values()];
  }

  /**
   * Get current memory pressure level.
   */
  get memoryPressure(): MemoryPressure {
    const utilization = this.totalMemoryMB / this.config.maxMemoryMB;
    if (utilization >= 0.95) return 'critical';
    if (utilization >= 0.80) return 'high';
    if (utilization >= 0.60) return 'medium';
    return 'low';
  }

  /**
   * Get total estimated memory usage.
   */
  get totalMemoryMB(): number {
    let total = 0;
    for (const instance of this.instances.values()) {
      total += instance.memoryMB;
    }
    return total;
  }

  /**
   * Get pool size.
   */
  get size(): number {
    return this.instances.size;
  }

  /**
   * Get pool statistics.
   */
  getStats(): PoolStats {
    const instances = [...this.instances.values()];
    const totalMem = instances.reduce((s, i) => s + i.memoryMB, 0);

    const agentCounts: Record<string, number> = {};
    for (const inst of instances) {
      agentCounts[inst.agentId] = (agentCounts[inst.agentId] ?? 0) + 1;
    }

    return {
      totalInstances: instances.length,
      activeInstances: instances.filter((i) => i.status === 'active').length,
      idleInstances: instances.filter((i) => i.status === 'idle').length,
      unhealthyInstances: instances.filter((i) => i.status === 'unhealthy').length,
      totalMemoryMB: totalMem,
      availableMemoryMB: this.config.maxMemoryMB - totalMem,
      memoryUtilization: this.config.maxMemoryMB > 0 ? totalMem / this.config.maxMemoryMB : 0,
      totalCreated: this.totalCreated,
      totalEvicted: this.totalEvicted,
      totalReuses: this.totalReuses,
      agentCounts,
    };
  }

  // ═══════════════════════════════════════════════════════════
  // Event Listeners
  // ═══════════════════════════════════════════════════════════

  /**
   * Register an eviction event listener.
   */
  onEviction(listener: (event: EvictionEvent) => void): () => void {
    this.evictionListeners.push(listener);
    return () => {
      this.evictionListeners = this.evictionListeners.filter((l) => l !== listener);
    };
  }

  // ═══════════════════════════════════════════════════════════
  // Shutdown
  // ═══════════════════════════════════════════════════════════

  /**
   * Shut down the pool and close all browser instances.
   */
  async shutdown(): Promise<number> {
    let closed = 0;
    for (const instance of [...this.instances.values()]) {
      try {
        await instance.backend.close();
      } catch {
        // Ignore close errors during shutdown
      }
      this.instances.delete(instance.id);
      closed++;
    }
    return closed;
  }

  // ═══════════════════════════════════════════════════════════
  // Private
  // ═══════════════════════════════════════════════════════════

  /**
   * Find a warm idle instance with matching tags.
   */
  private findWarmInstance(agentId: string, tags: string[]): PooledInstance | null {
    let best: PooledInstance | null = null;
    let bestScore = -1;

    for (const instance of this.instances.values()) {
      if (instance.status !== 'idle') continue;
      // Prefer same agent's instances for cache locality
      const sameAgent = instance.agentId === agentId ? 1 : 0;

      // Count matching tags
      let matchCount = 0;
      for (const tag of tags) {
        if (instance.tags.has(tag)) matchCount++;
      }

      const score = sameAgent * 10 + matchCount;
      if (score > bestScore) {
        bestScore = score;
        best = instance;
      }
    }

    return best;
  }

  /**
   * Evict an instance and notify listeners.
   */
  private evict(instanceId: string, reason: EvictionEvent['reason']): boolean {
    const instance = this.instances.get(instanceId);
    if (!instance) return false;

    const event: EvictionEvent = {
      instanceId,
      agentId: instance.agentId,
      reason,
      memoryFreedMB: instance.memoryMB,
      timestamp: Date.now(),
    };

    this.instances.delete(instanceId);
    this.totalEvicted++;

    // Notify listeners
    for (const listener of this.evictionListeners) {
      try {
        listener(event);
      } catch {
        // Don't let listener errors break eviction
      }
    }

    return true;
  }
}
