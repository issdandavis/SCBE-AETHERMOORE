import { ReplayStore, MemoryReplayStore, createReplayStore, RedisClient } from './replayStore.js';

/**
 * ReplayGuard - Prevents replay attacks on envelopes.
 *
 * MEDIUM-001 fix: Now supports pluggable storage backends for distributed deployments.
 *
 * Single-process (default):
 *   const guard = new ReplayGuard({ ttlSeconds: 600 });
 *
 * Distributed (Redis):
 *   import Redis from 'ioredis';
 *   const redis = new Redis(process.env.REDIS_URL);
 *   const guard = new ReplayGuard({ ttlSeconds: 600, store: new RedisReplayStore(redis) });
 *
 * Or via factory:
 *   const guard = ReplayGuard.create({ ttlSeconds: 600, redisUrl: process.env.REDIS_URL });
 */
export class ReplayGuard {
  private store: ReplayStore;
  private ttlMs: number;

  constructor(options: {
    ttlSeconds?: number;
    sizeBits?: number;
    hashes?: number;
    store?: ReplayStore;
  } = {}) {
    const { ttlSeconds = 600, sizeBits = 2048, hashes = 4, store } = options;
    this.ttlMs = ttlSeconds * 1000;
    this.store = store ?? new MemoryReplayStore({
      bloomSizeBits: sizeBits,
      bloomHashes: hashes,
    });
  }

  /**
   * Factory method to create ReplayGuard with Redis support via URL.
   * Requires ioredis to be installed for Redis support.
   */
  static create(options: {
    ttlSeconds?: number;
    sizeBits?: number;
    hashes?: number;
    redisClient?: RedisClient;
  } = {}): ReplayGuard {
    const store = createReplayStore({
      redisClient: options.redisClient,
      bloomSizeBits: options.sizeBits,
      bloomHashes: options.hashes,
    });
    return new ReplayGuard({ ...options, store });
  }

  private key(providerId: string, requestId: string): string {
    return `${providerId}::${requestId}`;
  }

  /**
   * Check if request is a replay and record it if not (synchronous).
   * For distributed stores, use checkAndSetAsync instead.
   * @returns true if OK (not a replay), false if replay detected
   */
  public checkAndSet(providerId: string, requestId: string, now = Date.now()): boolean {
    const k = this.key(providerId, requestId);

    // For MemoryReplayStore, use synchronous method directly
    if (this.store instanceof MemoryReplayStore) {
      return this.store.checkAndSetSync(k, this.ttlMs, now);
    }

    // For async stores (Redis, etc.), this sync API is not safe
    // Log warning and fail closed (reject as replay) for safety
    console.warn(
      'ReplayGuard: Sync checkAndSet called with async store. ' +
      'Use checkAndSetAsync for distributed deployments.'
    );
    return false; // Fail closed for safety
  }

  /**
   * Async version for distributed stores (MEDIUM-001 fix).
   * Use this method when using Redis or other async stores.
   */
  public async checkAndSetAsync(providerId: string, requestId: string, now = Date.now()): Promise<boolean> {
    const k = this.key(providerId, requestId);
    return this.store.checkAndSet(k, this.ttlMs, now);
  }

  /**
   * Close underlying store connections.
   */
  public async close(): Promise<void> {
    if (this.store.close) {
      await this.store.close();
    }
  }
}

// Re-export store types for convenience
export { ReplayStore, MemoryReplayStore, RedisReplayStore, createReplayStore } from './replayStore.js';
export type { RedisClient } from './replayStore.js';
