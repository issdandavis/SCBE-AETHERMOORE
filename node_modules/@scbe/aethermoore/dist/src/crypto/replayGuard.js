"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ReplayGuard = void 0;
const bloom_js_1 = require("./bloom.js");
class ReplayGuard {
    bloom;
    ttlMs;
    map = new Map();
    constructor({ ttlSeconds = 600, sizeBits = 2048, hashes = 4 } = {}) {
        this.ttlMs = ttlSeconds * 1000;
        this.bloom = new bloom_js_1.BloomFilter(sizeBits, hashes);
    }
    key(providerId, requestId) {
        return `${providerId}::${requestId}`;
    }
    checkAndSet(providerId, requestId, now = Date.now()) {
        const k = this.key(providerId, requestId);
        const seenBloom = this.bloom.mightHave(k);
        const ent = this.map.get(k);
        if (ent && now - ent.ts < this.ttlMs)
            return false;
        if (seenBloom && ent)
            return false;
        this.bloom.add(k);
        this.map.set(k, { ts: now });
        // Garbage collect occasionally
        if (this.map.size > 50000) {
            const cutoff = now - this.ttlMs;
            for (const [kk, v] of this.map)
                if (v.ts < cutoff)
                    this.map.delete(kk);
        }
        return true;
    }
}
exports.ReplayGuard = ReplayGuard;
//# sourceMappingURL=replayGuard.js.map