/**
 * @file redisStore.ts
 * @module api/redisStore
 * @layer Layer 13 (persistence)
 * @component Redis-backed persistence for SCBE Platform API
 *
 * Provides a Redis persistence layer with graceful fallback to in-memory
 * when Redis is unavailable. All session, API key, usage, rate limiting,
 * nonce, and audit data survives process restarts when Redis is connected.
 *
 * Security:
 *   - No raw API keys stored (hash-only)
 *   - All values serialised as JSON with TTL enforcement
 *   - Nonce replay protection with atomic SET NX + TTL
 *   - Rate limiting via Redis MULTI/EXEC for atomicity
 */

import Redis from 'ioredis';

// ============================================================================
// Types
// ============================================================================

/** Redis store configuration */
export interface RedisStoreConfig {
  /** Redis URL (default: redis://localhost:6379) */
  url?: string;
  /** Key prefix for namespacing (default: 'scbe:') */
  prefix?: string;
  /** Enable fallback to in-memory when Redis is unavailable */
  fallbackToMemory?: boolean;
  /** Connection timeout in ms (default: 5000) */
  connectTimeoutMs?: number;
}

/** Rate limit check result */
export interface RateLimitResult {
  allowed: boolean;
  count: number;
  remaining: number;
  resetAt: number;
}

// ============================================================================
// Redis Store
// ============================================================================

/**
 * Redis-backed key-value store with TTL support and graceful degradation.
 *
 * Key namespaces:
 *   scbe:session:{id}    — PlatformSession (TTL: session TTL)
 *   scbe:apikey:{hash}   — ApiKey record (no TTL)
 *   scbe:usage:{ownerId} — OwnerUsage counters (TTL: end of month)
 *   scbe:nonce:{nonce}   — Replay guard (TTL: 5 min)
 *   scbe:rate:{key}      — Rate limit counter (TTL: 60s window)
 *   scbe:audit           — Audit log (Redis list, capped at 10K)
 *   scbe:quarantine:{id} — Quarantine items (TTL: item TTL)
 */
export class RedisStore {
  private redis: Redis | null = null;
  private readonly fallback: Map<string, { value: string; expiresAt: number | null }> = new Map();
  private readonly prefix: string;
  private readonly fallbackToMemory: boolean;
  private connected = false;

  constructor(config?: RedisStoreConfig) {
    this.prefix = config?.prefix ?? 'scbe:';
    this.fallbackToMemory = config?.fallbackToMemory ?? true;

    const url = config?.url ?? process.env.REDIS_URL ?? '';

    if (url) {
      this.redis = new Redis(url, {
        connectTimeout: config?.connectTimeoutMs ?? 5000,
        maxRetriesPerRequest: 3,
        retryStrategy: (times: number) => {
          if (times > 5) return null; // Stop retrying after 5 attempts
          return Math.min(times * 200, 2000);
        },
        lazyConnect: true,
      });

      this.redis.on('connect', () => {
        this.connected = true;
      });

      this.redis.on('error', () => {
        this.connected = false;
      });

      this.redis.on('close', () => {
        this.connected = false;
      });
    }
  }

  /** Connect to Redis. Safe to call multiple times. */
  async connect(): Promise<boolean> {
    if (!this.redis) return false;
    try {
      await this.redis.connect();
      this.connected = true;
      return true;
    } catch {
      this.connected = false;
      if (!this.fallbackToMemory) {
        throw new Error('Redis connection failed and fallback disabled');
      }
      return false;
    }
  }

  /** Disconnect from Redis. */
  async disconnect(): Promise<void> {
    if (this.redis) {
      this.redis.disconnect();
      this.connected = false;
    }
  }

  /** True if Redis is connected. */
  isConnected(): boolean {
    return this.connected;
  }

  // --------------------------------------------------------------------------
  // Core KV Operations
  // --------------------------------------------------------------------------

  /** Set a key with optional TTL (in seconds). */
  async set(key: string, value: unknown, ttlSec?: number): Promise<void> {
    const fullKey = this.prefix + key;
    const serialised = JSON.stringify(value);

    if (this.connected && this.redis) {
      if (ttlSec && ttlSec > 0) {
        await this.redis.setex(fullKey, Math.ceil(ttlSec), serialised);
      } else {
        await this.redis.set(fullKey, serialised);
      }
    } else {
      this.fallback.set(fullKey, {
        value: serialised,
        expiresAt: ttlSec ? Date.now() + ttlSec * 1000 : null,
      });
    }
  }

  /** Get a key, returns null if not found or expired. */
  async get<T = unknown>(key: string): Promise<T | null> {
    const fullKey = this.prefix + key;

    if (this.connected && this.redis) {
      const raw = await this.redis.get(fullKey);
      if (raw === null) return null;
      return JSON.parse(raw) as T;
    } else {
      const entry = this.fallback.get(fullKey);
      if (!entry) return null;
      if (entry.expiresAt && Date.now() > entry.expiresAt) {
        this.fallback.delete(fullKey);
        return null;
      }
      return JSON.parse(entry.value) as T;
    }
  }

  /** Delete a key. Returns true if key existed. */
  async del(key: string): Promise<boolean> {
    const fullKey = this.prefix + key;

    if (this.connected && this.redis) {
      const count = await this.redis.del(fullKey);
      return count > 0;
    } else {
      return this.fallback.delete(fullKey);
    }
  }

  /** Check if a key exists. */
  async exists(key: string): Promise<boolean> {
    const fullKey = this.prefix + key;

    if (this.connected && this.redis) {
      return (await this.redis.exists(fullKey)) === 1;
    } else {
      const entry = this.fallback.get(fullKey);
      if (!entry) return false;
      if (entry.expiresAt && Date.now() > entry.expiresAt) {
        this.fallback.delete(fullKey);
        return false;
      }
      return true;
    }
  }

  // --------------------------------------------------------------------------
  // Nonce Replay Protection (atomic SET NX)
  // --------------------------------------------------------------------------

  /**
   * Consume a nonce atomically. Returns true if the nonce was fresh.
   * Uses SET NX (set-if-not-exists) + TTL for guaranteed single-use.
   */
  async consumeNonce(nonce: string, ttlSec: number = 300): Promise<boolean> {
    const fullKey = this.prefix + 'nonce:' + nonce;

    if (this.connected && this.redis) {
      // SET key value NX EX ttl — atomic: returns 'OK' only if key didn't exist
      const result = await this.redis.set(fullKey, '1', 'EX', ttlSec, 'NX');
      return result === 'OK';
    } else {
      const entry = this.fallback.get(fullKey);
      if (entry) {
        if (entry.expiresAt && Date.now() > entry.expiresAt) {
          this.fallback.delete(fullKey);
          // Fall through to set it
        } else {
          return false; // Nonce already consumed
        }
      }
      this.fallback.set(fullKey, {
        value: '1',
        expiresAt: Date.now() + ttlSec * 1000,
      });
      return true;
    }
  }

  // --------------------------------------------------------------------------
  // Rate Limiting
  // --------------------------------------------------------------------------

  /**
   * Check and increment rate limit counter.
   * Uses a sliding window approach with Redis INCR + TTL.
   */
  async checkRateLimit(
    key: string,
    maxRequests: number,
    windowSec: number = 60
  ): Promise<RateLimitResult> {
    const fullKey = this.prefix + 'rate:' + key;
    const now = Date.now();

    if (this.connected && this.redis) {
      const pipeline = this.redis.multi();
      pipeline.incr(fullKey);
      pipeline.ttl(fullKey);
      const results = await pipeline.exec();

      const count = (results?.[0]?.[1] as number) ?? 1;
      const ttl = (results?.[1]?.[1] as number) ?? -1;

      // Set TTL on first request in window
      if (ttl === -1) {
        await this.redis.expire(fullKey, windowSec);
      }

      const resetAt = now + (ttl > 0 ? ttl * 1000 : windowSec * 1000);

      return {
        allowed: count <= maxRequests,
        count,
        remaining: Math.max(0, maxRequests - count),
        resetAt,
      };
    } else {
      // In-memory fallback
      const entry = this.fallback.get(fullKey);
      let count: number;
      let resetAt: number;

      if (!entry || (entry.expiresAt && now > entry.expiresAt)) {
        count = 1;
        resetAt = now + windowSec * 1000;
        this.fallback.set(fullKey, {
          value: JSON.stringify({ count, resetAt }),
          expiresAt: resetAt,
        });
      } else {
        const data = JSON.parse(entry.value) as { count: number; resetAt: number };
        data.count++;
        count = data.count;
        resetAt = data.resetAt;
        entry.value = JSON.stringify(data);
      }

      return {
        allowed: count <= maxRequests,
        count,
        remaining: Math.max(0, maxRequests - count),
        resetAt,
      };
    }
  }

  // --------------------------------------------------------------------------
  // Audit Log (Redis List)
  // --------------------------------------------------------------------------

  /** Push an audit entry to the front of the list. Caps at maxEntries. */
  async pushAudit(entry: unknown, maxEntries: number = 10_000): Promise<void> {
    const fullKey = this.prefix + 'audit';
    const serialised = JSON.stringify(entry);

    if (this.connected && this.redis) {
      await this.redis.lpush(fullKey, serialised);
      await this.redis.ltrim(fullKey, 0, maxEntries - 1);
    } else {
      // Fallback: store in memory list
      const existing = this.fallback.get(fullKey);
      let list: string[];
      if (existing) {
        list = JSON.parse(existing.value) as string[];
      } else {
        list = [];
      }
      list.unshift(serialised);
      if (list.length > maxEntries) list.pop();
      this.fallback.set(fullKey, { value: JSON.stringify(list), expiresAt: null });
    }
  }

  /** Get audit entries with optional offset and limit. */
  async getAudit<T = unknown>(offset: number = 0, limit: number = 100): Promise<T[]> {
    const fullKey = this.prefix + 'audit';

    if (this.connected && this.redis) {
      const entries = await this.redis.lrange(fullKey, offset, offset + limit - 1);
      return entries.map((e) => JSON.parse(e) as T);
    } else {
      const existing = this.fallback.get(fullKey);
      if (!existing) return [];
      const list = JSON.parse(existing.value) as string[];
      return list.slice(offset, offset + limit).map((e) => JSON.parse(e) as T);
    }
  }

  // --------------------------------------------------------------------------
  // Key Scanning (for session enumeration)
  // --------------------------------------------------------------------------

  /** Get all keys matching a pattern. Use sparingly. */
  async keys(pattern: string): Promise<string[]> {
    const fullPattern = this.prefix + pattern;

    if (this.connected && this.redis) {
      const keys = await this.redis.keys(fullPattern);
      return keys.map((k) => k.slice(this.prefix.length));
    } else {
      const matched: string[] = [];
      const regex = new RegExp('^' + fullPattern.replace(/\*/g, '.*') + '$');
      for (const [key] of this.fallback) {
        if (regex.test(key)) {
          const entry = this.fallback.get(key);
          if (entry?.expiresAt && Date.now() > entry.expiresAt) {
            this.fallback.delete(key);
            continue;
          }
          matched.push(key.slice(this.prefix.length));
        }
      }
      return matched;
    }
  }

  // --------------------------------------------------------------------------
  // Atomic Counter (for usage metering)
  // --------------------------------------------------------------------------

  /** Increment a counter field. Returns the new value. */
  async incr(key: string, field?: string, amount: number = 1): Promise<number> {
    const fullKey = this.prefix + key;

    if (this.connected && this.redis) {
      if (field) {
        return this.redis.hincrby(fullKey, field, amount);
      }
      return this.redis.incrby(fullKey, amount);
    } else {
      if (field) {
        const entry = this.fallback.get(fullKey);
        let data: Record<string, number> = {};
        if (entry) {
          data = JSON.parse(entry.value) as Record<string, number>;
        }
        data[field] = (data[field] ?? 0) + amount;
        this.fallback.set(fullKey, {
          value: JSON.stringify(data),
          expiresAt: entry?.expiresAt ?? null,
        });
        return data[field];
      } else {
        const entry = this.fallback.get(fullKey);
        const current = entry ? parseInt(entry.value, 10) || 0 : 0;
        const next = current + amount;
        this.fallback.set(fullKey, {
          value: String(next),
          expiresAt: entry?.expiresAt ?? null,
        });
        return next;
      }
    }
  }

  /** Set a hash field. */
  async hset(key: string, field: string, value: unknown): Promise<void> {
    const fullKey = this.prefix + key;

    if (this.connected && this.redis) {
      await this.redis.hset(fullKey, field, JSON.stringify(value));
    } else {
      const entry = this.fallback.get(fullKey);
      let data: Record<string, string> = {};
      if (entry) {
        data = JSON.parse(entry.value) as Record<string, string>;
      }
      data[field] = JSON.stringify(value);
      this.fallback.set(fullKey, {
        value: JSON.stringify(data),
        expiresAt: entry?.expiresAt ?? null,
      });
    }
  }

  /** Get a hash field. */
  async hget<T = unknown>(key: string, field: string): Promise<T | null> {
    const fullKey = this.prefix + key;

    if (this.connected && this.redis) {
      const raw = await this.redis.hget(fullKey, field);
      if (raw === null) return null;
      return JSON.parse(raw) as T;
    } else {
      const entry = this.fallback.get(fullKey);
      if (!entry) return null;
      const data = JSON.parse(entry.value) as Record<string, string>;
      if (!(field in data)) return null;
      return JSON.parse(data[field]) as T;
    }
  }

  /** Get all hash fields. */
  async hgetall<T = unknown>(key: string): Promise<Record<string, T> | null> {
    const fullKey = this.prefix + key;

    if (this.connected && this.redis) {
      const raw = await this.redis.hgetall(fullKey);
      if (!raw || Object.keys(raw).length === 0) return null;
      const result: Record<string, T> = {};
      for (const [k, v] of Object.entries(raw)) {
        result[k] = JSON.parse(v) as T;
      }
      return result;
    } else {
      const entry = this.fallback.get(fullKey);
      if (!entry) return null;
      const data = JSON.parse(entry.value) as Record<string, string>;
      const result: Record<string, T> = {};
      for (const [k, v] of Object.entries(data)) {
        result[k] = JSON.parse(v) as T;
      }
      return result;
    }
  }

  /** Add a member to a set. */
  async sadd(key: string, member: string): Promise<void> {
    const fullKey = this.prefix + key;

    if (this.connected && this.redis) {
      await this.redis.sadd(fullKey, member);
    } else {
      const entry = this.fallback.get(fullKey);
      let members: string[] = [];
      if (entry) {
        members = JSON.parse(entry.value) as string[];
      }
      if (!members.includes(member)) {
        members.push(member);
      }
      this.fallback.set(fullKey, {
        value: JSON.stringify(members),
        expiresAt: entry?.expiresAt ?? null,
      });
    }
  }

  /** Get set size. */
  async scard(key: string): Promise<number> {
    const fullKey = this.prefix + key;

    if (this.connected && this.redis) {
      return this.redis.scard(fullKey);
    } else {
      const entry = this.fallback.get(fullKey);
      if (!entry) return 0;
      return (JSON.parse(entry.value) as string[]).length;
    }
  }
}

// ============================================================================
// Singleton
// ============================================================================

let _instance: RedisStore | null = null;

/** Get or create the singleton RedisStore. */
export function getRedisStore(config?: RedisStoreConfig): RedisStore {
  if (!_instance) {
    _instance = new RedisStore(config);
  }
  return _instance;
}

/** Reset the singleton (for testing). */
export function resetRedisStore(): void {
  if (_instance) {
    _instance.disconnect().catch(() => {});
    _instance = null;
  }
}
