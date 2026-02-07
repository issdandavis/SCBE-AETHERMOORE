"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.createReplayStore = exports.RedisReplayStore = exports.MemoryReplayStore = exports.ReplayGuard = void 0;
const replayStore_js_1 = require("./replayStore.js");
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
class ReplayGuard {
    store;
    ttlMs;
    constructor(options = {}) {
        const { ttlSeconds = 600, sizeBits = 2048, hashes = 4, store } = options;
        this.ttlMs = ttlSeconds * 1000;
        this.store =
            store ??
                new replayStore_js_1.MemoryReplayStore({
                    bloomSizeBits: sizeBits,
                    bloomHashes: hashes,
                });
    }
    /**
     * Factory method to create ReplayGuard with Redis support via URL.
     * Requires ioredis to be installed for Redis support.
     */
    static create(options = {}) {
        const store = (0, replayStore_js_1.createReplayStore)({
            redisClient: options.redisClient,
            bloomSizeBits: options.sizeBits,
            bloomHashes: options.hashes,
        });
        return new ReplayGuard({ ...options, store });
    }
    key(providerId, requestId) {
        return `${providerId}::${requestId}`;
    }
    /**
     * Check if request is a replay and record it if not (synchronous).
     * For distributed stores, use checkAndSetAsync instead.
     * @returns true if OK (not a replay), false if replay detected
     */
    checkAndSet(providerId, requestId, now = Date.now()) {
        const k = this.key(providerId, requestId);
        // For MemoryReplayStore, use synchronous method directly
        if (this.store instanceof replayStore_js_1.MemoryReplayStore) {
            return this.store.checkAndSetSync(k, this.ttlMs, now);
        }
        // For async stores (Redis, etc.), this sync API is not safe
        // Log warning and fail closed (reject as replay) for safety
        console.warn('ReplayGuard: Sync checkAndSet called with async store. ' +
            'Use checkAndSetAsync for distributed deployments.');
        return false; // Fail closed for safety
    }
    /**
     * Async version for distributed stores (MEDIUM-001 fix).
     * Use this method when using Redis or other async stores.
     */
    async checkAndSetAsync(providerId, requestId, now = Date.now()) {
        const k = this.key(providerId, requestId);
        return this.store.checkAndSet(k, this.ttlMs, now);
    }
    /**
     * Close underlying store connections.
     */
    async close() {
        if (this.store.close) {
            await this.store.close();
        }
    }
}
exports.ReplayGuard = ReplayGuard;
// Re-export store types for convenience
var replayStore_js_2 = require("./replayStore.js");
Object.defineProperty(exports, "MemoryReplayStore", { enumerable: true, get: function () { return replayStore_js_2.MemoryReplayStore; } });
Object.defineProperty(exports, "RedisReplayStore", { enumerable: true, get: function () { return replayStore_js_2.RedisReplayStore; } });
Object.defineProperty(exports, "createReplayStore", { enumerable: true, get: function () { return replayStore_js_2.createReplayStore; } });
//# sourceMappingURL=replayGuard.js.map