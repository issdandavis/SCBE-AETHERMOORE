/**
 * Replay Store Interface (MEDIUM-001 fix)
 *
 * Abstracts replay detection storage to support both single-process
 * and distributed deployments.
 */
export interface ReplayEntry {
    ts: number;
}
/**
 * Interface for replay detection storage backends.
 * Implementations must be safe for concurrent access.
 */
export interface ReplayStore {
    /**
     * Check if a key exists and is within TTL.
     * @returns true if key exists and is not expired
     */
    has(key: string, ttlMs: number, now: number): Promise<boolean>;
    /**
     * Set a key with timestamp. Should be atomic with has() check.
     */
    set(key: string, ts: number): Promise<void>;
    /**
     * Check and set atomically. Returns false if already exists (replay detected).
     * This is the primary method for replay detection.
     */
    checkAndSet(key: string, ttlMs: number, now: number): Promise<boolean>;
    /**
     * Optional cleanup of expired entries.
     */
    cleanup?(ttlMs: number, now: number): Promise<void>;
    /**
     * Close connections (for distributed stores).
     */
    close?(): Promise<void>;
}
/**
 * In-memory replay store (default, single-process).
 * Uses bloom filter for probabilistic fast-path + map for accuracy.
 */
export declare class MemoryReplayStore implements ReplayStore {
    private map;
    private bloomBits;
    private bloomHashes;
    private maxSize;
    constructor(options?: {
        bloomSizeBits?: number;
        bloomHashes?: number;
        maxSize?: number;
    });
    private hash;
    private bloomAdd;
    private bloomMightHave;
    has(key: string, ttlMs: number, now: number): Promise<boolean>;
    hasSync(key: string, ttlMs: number, now: number): boolean;
    set(key: string, ts: number): Promise<void>;
    setSync(key: string, ts: number): void;
    checkAndSet(key: string, ttlMs: number, now: number): Promise<boolean>;
    /**
     * Synchronous version for backward compatibility.
     */
    checkAndSetSync(key: string, ttlMs: number, now: number): boolean;
    cleanup(ttlMs: number, now: number): Promise<void>;
    cleanupSync(ttlMs: number, now: number): void;
}
/**
 * Redis-based replay store for distributed deployments.
 * Requires ioredis or compatible Redis client.
 *
 * Usage:
 *   import Redis from 'ioredis';
 *   const redis = new Redis(process.env.REDIS_URL);
 *   const store = new RedisReplayStore(redis, { prefix: 'scbe:replay:' });
 */
export declare class RedisReplayStore implements ReplayStore {
    private client;
    private prefix;
    constructor(client: RedisClient, options?: {
        prefix?: string;
    });
    private key;
    has(key: string, ttlMs: number, _now: number): Promise<boolean>;
    set(key: string, ts: number): Promise<void>;
    checkAndSet(key: string, ttlMs: number, now: number): Promise<boolean>;
    cleanup(_ttlMs: number, _now: number): Promise<void>;
    close(): Promise<void>;
}
/**
 * Minimal Redis client interface (compatible with ioredis).
 */
export interface RedisClient {
    get(key: string): Promise<string | null>;
    set(key: string, value: string, ...args: (string | number)[]): Promise<string | null>;
    quit?(): Promise<void>;
}
/**
 * Factory function to create appropriate replay store based on environment.
 */
export declare function createReplayStore(options?: {
    redisClient?: RedisClient;
    redisPrefix?: string;
    bloomSizeBits?: number;
    bloomHashes?: number;
    maxSize?: number;
}): ReplayStore;
//# sourceMappingURL=replayStore.d.ts.map