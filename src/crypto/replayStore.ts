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
export class MemoryReplayStore implements ReplayStore {
  private map = new Map<string, ReplayEntry>();
  private bloomBits: Uint8Array;
  private bloomHashes: number;
  private maxSize: number;

  constructor(options: { bloomSizeBits?: number; bloomHashes?: number; maxSize?: number } = {}) {
    const { bloomSizeBits = 2048, bloomHashes = 4, maxSize = 50000 } = options;
    this.bloomBits = new Uint8Array(bloomSizeBits);
    this.bloomHashes = bloomHashes;
    this.maxSize = maxSize;
  }

  private hash(s: string, n: number): number {
    let h = 0x811c9dc5 ^ n;
    for (let i = 0; i < s.length; i++) {
      h ^= s.charCodeAt(i);
      h = (h * 0x01000193) >>> 0;
    }
    return h % (this.bloomBits.length * 8);
  }

  private bloomAdd(key: string): void {
    for (let i = 0; i < this.bloomHashes; i++) {
      const bit = this.hash(key, i);
      const byte = bit >> 3;
      const mask = 1 << (bit & 7);
      this.bloomBits[byte] |= mask;
    }
  }

  private bloomMightHave(key: string): boolean {
    for (let i = 0; i < this.bloomHashes; i++) {
      const bit = this.hash(key, i);
      const byte = bit >> 3;
      const mask = 1 << (bit & 7);
      if ((this.bloomBits[byte] & mask) === 0) return false;
    }
    return true;
  }

  async has(key: string, ttlMs: number, now: number): Promise<boolean> {
    return this.hasSync(key, ttlMs, now);
  }

  hasSync(key: string, ttlMs: number, now: number): boolean {
    const entry = this.map.get(key);
    if (!entry) return false;
    return now - entry.ts < ttlMs;
  }

  async set(key: string, ts: number): Promise<void> {
    this.setSync(key, ts);
  }

  setSync(key: string, ts: number): void {
    this.bloomAdd(key);
    this.map.set(key, { ts });
  }

  async checkAndSet(key: string, ttlMs: number, now: number): Promise<boolean> {
    return this.checkAndSetSync(key, ttlMs, now);
  }

  /**
   * Synchronous version for backward compatibility.
   */
  checkAndSetSync(key: string, ttlMs: number, now: number): boolean {
    // Check map for definitive answer with TTL
    const entry = this.map.get(key);
    if (entry && now - entry.ts < ttlMs) {
      return false; // Replay detected - entry exists and not expired
    }

    // Entry either doesn't exist or is expired
    // Fast path: if bloom filter says definitely not seen, we're good
    // If bloom says "might have" but entry is expired/missing, allow it
    // (Bloom filters can't be cleared, so we rely on map TTL for expiration)

    // Not a replay (or expired), record it
    this.bloomAdd(key);
    this.map.set(key, { ts: now });

    // Garbage collect if needed
    if (this.map.size > this.maxSize) {
      this.cleanupSync(ttlMs, now);
    }

    return true; // OK, not a replay
  }

  async cleanup(ttlMs: number, now: number): Promise<void> {
    this.cleanupSync(ttlMs, now);
  }

  cleanupSync(ttlMs: number, now: number): void {
    const cutoff = now - ttlMs;
    for (const [k, v] of this.map) {
      if (v.ts < cutoff) {
        this.map.delete(k);
      }
    }
  }
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
export class RedisReplayStore implements ReplayStore {
  private client: RedisClient;
  private prefix: string;

  constructor(client: RedisClient, options: { prefix?: string } = {}) {
    this.client = client;
    this.prefix = options.prefix ?? 'scbe:replay:';
  }

  private key(k: string): string {
    return `${this.prefix}${k}`;
  }

  async has(key: string, ttlMs: number, _now: number): Promise<boolean> {
    const val = await this.client.get(this.key(key));
    return val !== null;
  }

  async set(key: string, ts: number): Promise<void> {
    // This is a fallback; prefer checkAndSet for atomicity
    await this.client.set(this.key(key), ts.toString());
  }

  async checkAndSet(key: string, ttlMs: number, now: number): Promise<boolean> {
    const redisKey = this.key(key);
    const ttlSeconds = Math.ceil(ttlMs / 1000);

    // Use SET NX EX for atomic check-and-set with TTL
    // Returns 'OK' if set, null if key already exists
    const result = await this.client.set(redisKey, now.toString(), 'EX', ttlSeconds, 'NX');

    return result === 'OK';
  }

  async cleanup(_ttlMs: number, _now: number): Promise<void> {
    // Redis handles TTL automatically via EX option
  }

  async close(): Promise<void> {
    if (this.client.quit) {
      await this.client.quit();
    }
  }
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
export function createReplayStore(
  options: {
    redisClient?: RedisClient;
    redisPrefix?: string;
    bloomSizeBits?: number;
    bloomHashes?: number;
    maxSize?: number;
  } = {}
): ReplayStore {
  if (options.redisClient) {
    return new RedisReplayStore(options.redisClient, { prefix: options.redisPrefix });
  }
  return new MemoryReplayStore({
    bloomSizeBits: options.bloomSizeBits,
    bloomHashes: options.bloomHashes,
    maxSize: options.maxSize,
  });
}
