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
export declare const DEFAULT_POOL_CONFIG: BrowserPoolConfig;
/** Status of a pooled browser instance */
export type InstanceStatus = 'initializing' | 'idle' | 'active' | 'unhealthy' | 'evicting';
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
export declare class BrowserPool {
    private config;
    private instances;
    private instanceCounter;
    private totalCreated;
    private totalEvicted;
    private totalReuses;
    private evictionListeners;
    constructor(config?: Partial<BrowserPoolConfig>);
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
    acquire(agentId: string, backend: BrowserBackend, tags?: string[]): AcquireResult;
    /**
     * Release an instance back to idle (available for warm reuse).
     */
    release(instanceId: string): boolean;
    /**
     * Mark an instance as active (in use).
     */
    markActive(instanceId: string): boolean;
    /**
     * Update the memory estimate for an instance.
     */
    updateMemory(instanceId: string, memoryMB: number): boolean;
    /**
     * Update the current URL for an instance.
     */
    updateUrl(instanceId: string, url: string): void;
    /**
     * Record an error on an instance.
     */
    recordError(instanceId: string): void;
    /**
     * Evict the least-recently-used idle instance.
     *
     * @returns true if an instance was evicted
     */
    evictLRU(): boolean;
    /**
     * Evict enough idle instances to free at least `neededMB` of memory.
     *
     * @param neededMB - Memory to free in MB
     * @returns Total memory freed in MB
     */
    evictToFree(neededMB: number): number;
    /**
     * Evict all idle instances that have been idle longer than the timeout.
     *
     * @returns Number of instances evicted
     */
    evictStale(): number;
    /**
     * Evict all unhealthy instances.
     *
     * @returns Number of instances evicted
     */
    evictUnhealthy(): number;
    /**
     * Manually destroy an instance.
     */
    destroy(instanceId: string): boolean;
    /**
     * Get an instance by ID.
     */
    getInstance(instanceId: string): PooledInstance | undefined;
    /**
     * Get all instances for a specific AI agent.
     */
    getAgentInstances(agentId: string): PooledInstance[];
    /**
     * Get all instances.
     */
    getAllInstances(): PooledInstance[];
    /**
     * Get current memory pressure level.
     */
    get memoryPressure(): MemoryPressure;
    /**
     * Get total estimated memory usage.
     */
    get totalMemoryMB(): number;
    /**
     * Get pool size.
     */
    get size(): number;
    /**
     * Get pool statistics.
     */
    getStats(): PoolStats;
    /**
     * Register an eviction event listener.
     */
    onEviction(listener: (event: EvictionEvent) => void): () => void;
    /**
     * Shut down the pool and close all browser instances.
     */
    shutdown(): Promise<number>;
    /**
     * Find a warm idle instance with matching tags.
     */
    private findWarmInstance;
    /**
     * Evict an instance and notify listeners.
     */
    private evict;
}
//# sourceMappingURL=browser-pool.d.ts.map