"use strict";
/**
 * Replay Store Interface (MEDIUM-001 fix)
 *
 * Abstracts replay detection storage to support both single-process
 * and distributed deployments.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.RedisReplayStore = exports.MemoryReplayStore = void 0;
exports.createReplayStore = createReplayStore;
/**
 * In-memory replay store (default, single-process).
 * Uses bloom filter for probabilistic fast-path + map for accuracy.
 */
class MemoryReplayStore {
    map = new Map();
    bloomBits;
    bloomHashes;
    maxSize;
    constructor(options = {}) {
        const { bloomSizeBits = 2048, bloomHashes = 4, maxSize = 50000 } = options;
        this.bloomBits = new Uint8Array(bloomSizeBits);
        this.bloomHashes = bloomHashes;
        this.maxSize = maxSize;
    }
    hash(s, n) {
        let h = 0x811c9dc5 ^ n;
        for (let i = 0; i < s.length; i++) {
            h ^= s.charCodeAt(i);
            h = (h * 0x01000193) >>> 0;
        }
        return h % (this.bloomBits.length * 8);
    }
    bloomAdd(key) {
        for (let i = 0; i < this.bloomHashes; i++) {
            const bit = this.hash(key, i);
            const byte = bit >> 3;
            const mask = 1 << (bit & 7);
            this.bloomBits[byte] |= mask;
        }
    }
    bloomMightHave(key) {
        for (let i = 0; i < this.bloomHashes; i++) {
            const bit = this.hash(key, i);
            const byte = bit >> 3;
            const mask = 1 << (bit & 7);
            if ((this.bloomBits[byte] & mask) === 0)
                return false;
        }
        return true;
    }
    async has(key, ttlMs, now) {
        return this.hasSync(key, ttlMs, now);
    }
    hasSync(key, ttlMs, now) {
        const entry = this.map.get(key);
        if (!entry)
            return false;
        return now - entry.ts < ttlMs;
    }
    async set(key, ts) {
        this.setSync(key, ts);
    }
    setSync(key, ts) {
        this.bloomAdd(key);
        this.map.set(key, { ts });
    }
    async checkAndSet(key, ttlMs, now) {
        return this.checkAndSetSync(key, ttlMs, now);
    }
    /**
     * Synchronous version for backward compatibility.
     */
    checkAndSetSync(key, ttlMs, now) {
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
    async cleanup(ttlMs, now) {
        this.cleanupSync(ttlMs, now);
    }
    cleanupSync(ttlMs, now) {
        const cutoff = now - ttlMs;
        for (const [k, v] of this.map) {
            if (v.ts < cutoff) {
                this.map.delete(k);
            }
        }
    }
}
exports.MemoryReplayStore = MemoryReplayStore;
/**
 * Redis-based replay store for distributed deployments.
 * Requires ioredis or compatible Redis client.
 *
 * Usage:
 *   import Redis from 'ioredis';
 *   const redis = new Redis(process.env.REDIS_URL);
 *   const store = new RedisReplayStore(redis, { prefix: 'scbe:replay:' });
 */
class RedisReplayStore {
    client;
    prefix;
    constructor(client, options = {}) {
        this.client = client;
        this.prefix = options.prefix ?? 'scbe:replay:';
    }
    key(k) {
        return `${this.prefix}${k}`;
    }
    async has(key, ttlMs, _now) {
        const val = await this.client.get(this.key(key));
        return val !== null;
    }
    async set(key, ts) {
        // This is a fallback; prefer checkAndSet for atomicity
        await this.client.set(this.key(key), ts.toString());
    }
    async checkAndSet(key, ttlMs, now) {
        const redisKey = this.key(key);
        const ttlSeconds = Math.ceil(ttlMs / 1000);
        // Use SET NX EX for atomic check-and-set with TTL
        // Returns 'OK' if set, null if key already exists
        const result = await this.client.set(redisKey, now.toString(), 'EX', ttlSeconds, 'NX');
        return result === 'OK';
    }
    async cleanup(_ttlMs, _now) {
        // Redis handles TTL automatically via EX option
    }
    async close() {
        if (this.client.quit) {
            await this.client.quit();
        }
    }
}
exports.RedisReplayStore = RedisReplayStore;
/**
 * Factory function to create appropriate replay store based on environment.
 */
function createReplayStore(options = {}) {
    if (options.redisClient) {
        return new RedisReplayStore(options.redisClient, { prefix: options.redisPrefix });
    }
    return new MemoryReplayStore({
        bloomSizeBits: options.bloomSizeBits,
        bloomHashes: options.bloomHashes,
        maxSize: options.maxSize,
    });
}
//# sourceMappingURL=replayStore.js.map