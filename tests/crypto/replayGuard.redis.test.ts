/**
 * Redis Replay Guard Integration Tests
 *
 * These tests require a running Redis instance.
 * Skip in CI unless REDIS_URL is set.
 *
 * Run locally:
 *   docker run -d -p 6379:6379 redis:alpine
 *   REDIS_URL=redis://localhost:6379 npm test -- tests/crypto/replayGuard.redis.test.ts
 */

import { describe, it, expect, beforeAll, afterAll, beforeEach } from 'vitest';
import { ReplayGuard, RedisReplayStore, type RedisClient } from '../../src/crypto/replayGuard.js';

// Skip tests if Redis not available
const REDIS_URL = process.env.REDIS_URL;
const describeRedis = REDIS_URL ? describe : describe.skip;

describeRedis('Redis Replay Guard Integration', () => {
  let redis: RedisClient;
  let guard: ReplayGuard;
  const testPrefix = `scbe:test:${Date.now()}:`;

  beforeAll(async () => {
    // Dynamic import to avoid errors when ioredis not installed
    try {
      const Redis = (await import('ioredis')).default;
      redis = new Redis(REDIS_URL!) as unknown as RedisClient;
    } catch (e) {
      console.warn('ioredis not installed, skipping Redis integration tests');
      return;
    }
  });

  afterAll(async () => {
    if (redis?.quit) {
      await redis.quit();
    }
  });

  beforeEach(() => {
    if (!redis) return;
    guard = new ReplayGuard({
      ttlSeconds: 2, // Short TTL for tests
      store: new RedisReplayStore(redis, { prefix: testPrefix }),
    });
  });

  it('allows first request through Redis', async () => {
    if (!redis) return;

    const result = await guard.checkAndSetAsync('provider1', 'request-redis-1');
    expect(result).toBe(true);
  });

  it('rejects duplicate request via Redis', async () => {
    if (!redis) return;

    const requestId = `request-redis-dup-${Date.now()}`;
    const result1 = await guard.checkAndSetAsync('provider1', requestId);
    expect(result1).toBe(true);

    const result2 = await guard.checkAndSetAsync('provider1', requestId);
    expect(result2).toBe(false);
  });

  it('allows request after TTL expires in Redis', async () => {
    if (!redis) return;

    const requestId = `request-redis-ttl-${Date.now()}`;

    // Create guard with very short TTL
    const shortGuard = new ReplayGuard({
      ttlSeconds: 1,
      store: new RedisReplayStore(redis, { prefix: testPrefix }),
    });

    const result1 = await shortGuard.checkAndSetAsync('provider1', requestId);
    expect(result1).toBe(true);

    // Wait for TTL to expire
    await new Promise((resolve) => setTimeout(resolve, 1100));

    const result2 = await shortGuard.checkAndSetAsync('provider1', requestId);
    expect(result2).toBe(true);
  });

  it('isolates different providers in Redis', async () => {
    if (!redis) return;

    const requestId = `request-redis-iso-${Date.now()}`;

    const result1 = await guard.checkAndSetAsync('providerA', requestId);
    expect(result1).toBe(true);

    const result2 = await guard.checkAndSetAsync('providerB', requestId);
    expect(result2).toBe(true);
  });

  it('handles concurrent requests atomically', async () => {
    if (!redis) return;

    const requestId = `request-redis-concurrent-${Date.now()}`;

    // Fire 10 concurrent requests with same ID
    const results = await Promise.all(
      Array.from({ length: 10 }, () =>
        guard.checkAndSetAsync('provider1', requestId)
      )
    );

    // Exactly one should succeed (atomic SET NX)
    const successes = results.filter((r) => r === true);
    expect(successes.length).toBe(1);
  });

  it('uses correct key format', async () => {
    if (!redis) return;

    const requestId = `request-redis-key-${Date.now()}`;
    await guard.checkAndSetAsync('myProvider', requestId);

    // Check key exists in Redis with correct prefix
    const value = await redis.get(`${testPrefix}myProvider::${requestId}`);
    expect(value).not.toBeNull();
  });
});

/**
 * Test helper: Create a mock Redis for unit tests
 */
export function createMockRedis(): RedisClient & { storage: Map<string, { value: string; expireAt: number }> } {
  const storage = new Map<string, { value: string; expireAt: number }>();

  return {
    storage,
    async get(key: string) {
      const entry = storage.get(key);
      if (!entry) return null;
      if (Date.now() > entry.expireAt) {
        storage.delete(key);
        return null;
      }
      return entry.value;
    },
    async set(key: string, value: string, ...args: (string | number)[]) {
      const exIndex = args.indexOf('EX');
      const nxIndex = args.indexOf('NX');

      // Check NX (only set if not exists)
      if (nxIndex !== -1) {
        const existing = storage.get(key);
        if (existing && Date.now() <= existing.expireAt) {
          return null;
        }
      }

      // Get TTL
      let ttlSeconds = 0;
      if (exIndex !== -1 && exIndex + 1 < args.length) {
        ttlSeconds = Number(args[exIndex + 1]);
      }

      storage.set(key, {
        value,
        expireAt: ttlSeconds > 0 ? Date.now() + ttlSeconds * 1000 : Infinity,
      });

      return 'OK';
    },
    async quit() {
      storage.clear();
    },
  };
}

describe('Mock Redis Helper', () => {
  it('mock Redis behaves like real Redis', async () => {
    const mockRedis = createMockRedis();
    const store = new RedisReplayStore(mockRedis, { prefix: 'mock:' });

    // First request allowed
    const r1 = await store.checkAndSet('key1', 60000, Date.now());
    expect(r1).toBe(true);

    // Duplicate blocked
    const r2 = await store.checkAndSet('key1', 60000, Date.now());
    expect(r2).toBe(false);

    // Different key allowed
    const r3 = await store.checkAndSet('key2', 60000, Date.now());
    expect(r3).toBe(true);
  });

  it('mock Redis expires keys', async () => {
    const mockRedis = createMockRedis();
    const store = new RedisReplayStore(mockRedis, { prefix: 'mock:' });

    // Set with 1 second TTL
    const r1 = await store.checkAndSet('expiring', 1000, Date.now());
    expect(r1).toBe(true);

    // Should be blocked immediately
    const r2 = await store.checkAndSet('expiring', 1000, Date.now());
    expect(r2).toBe(false);

    // Wait for expiration
    await new Promise((r) => setTimeout(r, 1100));

    // Should be allowed after TTL
    const r3 = await store.checkAndSet('expiring', 1000, Date.now());
    expect(r3).toBe(true);
  });
});
