import { ReplayStore, RedisClient } from './replayStore.js';
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
export declare class ReplayGuard {
    private store;
    private ttlMs;
    constructor(options?: {
        ttlSeconds?: number;
        sizeBits?: number;
        hashes?: number;
        store?: ReplayStore;
    });
    /**
     * Factory method to create ReplayGuard with Redis support via URL.
     * Requires ioredis to be installed for Redis support.
     */
    static create(options?: {
        ttlSeconds?: number;
        sizeBits?: number;
        hashes?: number;
        redisClient?: RedisClient;
    }): ReplayGuard;
    private key;
    /**
     * Check if request is a replay and record it if not (synchronous).
     * For distributed stores, use checkAndSetAsync instead.
     * @returns true if OK (not a replay), false if replay detected
     */
    checkAndSet(providerId: string, requestId: string, now?: number): boolean;
    /**
     * Async version for distributed stores (MEDIUM-001 fix).
     * Use this method when using Redis or other async stores.
     */
    checkAndSetAsync(providerId: string, requestId: string, now?: number): Promise<boolean>;
    /**
     * Close underlying store connections.
     */
    close(): Promise<void>;
}
export { ReplayStore, MemoryReplayStore, RedisReplayStore, createReplayStore, } from './replayStore.js';
export type { RedisClient } from './replayStore.js';
//# sourceMappingURL=replayGuard.d.ts.map