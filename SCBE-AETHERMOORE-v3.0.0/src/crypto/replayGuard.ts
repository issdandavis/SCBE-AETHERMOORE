import { BloomFilter } from './bloom.js';

type Entry = { ts: number };

export class ReplayGuard {
  private bloom: BloomFilter;
  private ttlMs: number;
  private map = new Map<string, Entry>();

  constructor({ ttlSeconds = 600, sizeBits = 2048, hashes = 4 } = {}) {
    this.ttlMs = ttlSeconds * 1000;
    this.bloom = new BloomFilter(sizeBits, hashes);
  }

  private key(providerId: string, requestId: string) {
    return `${providerId}::${requestId}`;
  }

  public checkAndSet(providerId: string, requestId: string, now = Date.now()): boolean {
    const k = this.key(providerId, requestId);
    const seenBloom = this.bloom.mightHave(k);
    const ent = this.map.get(k);
    if (ent && now - ent.ts < this.ttlMs) return false;
    if (seenBloom && ent) return false;
    this.bloom.add(k);
    this.map.set(k, { ts: now });
    // Garbage collect occasionally
    if (this.map.size > 50000) {
      const cutoff = now - this.ttlMs;
      for (const [kk, v] of this.map) if (v.ts < cutoff) this.map.delete(kk);
    }
    return true;
  }
}
