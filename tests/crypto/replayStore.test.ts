/**
 * @file replayStore.test.ts
 * @module crypto/replayStore
 * @layer L5 Security
 *
 * Tests for MemoryReplayStore, RedisReplayStore, and createReplayStore factory.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  MemoryReplayStore,
  RedisReplayStore,
  createReplayStore,
  type RedisClient,
} from '../../src/crypto/replayStore.js';

describe('MemoryReplayStore', () => {
  let store: MemoryReplayStore;
  const TTL = 5000;

  beforeEach(() => {
    store = new MemoryReplayStore();
  });

  describe('checkAndSet', () => {
    it('returns true for first occurrence of a key', async () => {
      expect(await store.checkAndSet('nonce-1', TTL, 1000)).toBe(true);
    });

    it('returns false for duplicate key within TTL (replay detected)', async () => {
      await store.checkAndSet('nonce-1', TTL, 1000);
      expect(await store.checkAndSet('nonce-1', TTL, 2000)).toBe(false);
    });

    it('returns true after TTL expires (allows reuse)', async () => {
      await store.checkAndSet('nonce-1', TTL, 1000);
      // now = 7000, entry ts = 1000, diff = 6000 > TTL 5000 → expired
      expect(await store.checkAndSet('nonce-1', TTL, 7000)).toBe(true);
    });

    it('handles different keys independently', async () => {
      expect(await store.checkAndSet('a', TTL, 1000)).toBe(true);
      expect(await store.checkAndSet('b', TTL, 1000)).toBe(true);
      expect(await store.checkAndSet('a', TTL, 1500)).toBe(false);
      expect(await store.checkAndSet('b', TTL, 1500)).toBe(false);
    });
  });

  describe('has / set', () => {
    it('returns false for unknown key', async () => {
      expect(await store.has('unknown', TTL, 1000)).toBe(false);
    });

    it('returns true after set within TTL', async () => {
      await store.set('key', 1000);
      expect(await store.has('key', TTL, 3000)).toBe(true);
    });

    it('returns false after TTL expires', async () => {
      await store.set('key', 1000);
      expect(await store.has('key', TTL, 7000)).toBe(false);
    });
  });

  describe('sync variants', () => {
    it('checkAndSetSync works identically to async version', () => {
      expect(store.checkAndSetSync('s1', TTL, 1000)).toBe(true);
      expect(store.checkAndSetSync('s1', TTL, 2000)).toBe(false);
      expect(store.checkAndSetSync('s1', TTL, 7000)).toBe(true);
    });

    it('hasSync / setSync work correctly', () => {
      store.setSync('k', 1000);
      expect(store.hasSync('k', TTL, 2000)).toBe(true);
      expect(store.hasSync('k', TTL, 7000)).toBe(false);
    });
  });

  describe('cleanup', () => {
    it('removes expired entries', async () => {
      await store.set('old', 1000);
      await store.set('recent', 5000);
      await store.cleanup(TTL, 7000);
      expect(await store.has('old', TTL, 7000)).toBe(false);
      expect(await store.has('recent', TTL, 7000)).toBe(true);
    });
  });

  describe('maxSize eviction', () => {
    it('triggers cleanup when maxSize exceeded', () => {
      const small = new MemoryReplayStore({ maxSize: 5 });
      for (let i = 0; i < 10; i++) {
        small.checkAndSetSync(`k-${i}`, TTL, i * 100);
      }
      // Should not throw, store manages itself
      expect(small.checkAndSetSync('new-key', TTL, 2000)).toBe(true);
    });
  });
});

describe('RedisReplayStore', () => {
  function mockRedisClient(): RedisClient & { store: Map<string, { value: string; ttl: number }> } {
    const store = new Map<string, { value: string; ttl: number }>();
    return {
      store,
      get: vi.fn(async (key: string) => {
        const entry = store.get(key);
        return entry ? entry.value : null;
      }),
      set: vi.fn(async (key: string, value: string, ...args: (string | number)[]) => {
        const nx = args.includes('NX');
        if (nx && store.has(key)) return null;
        const exIdx = args.indexOf('EX');
        const ttl = exIdx >= 0 ? (args[exIdx + 1] as number) : 0;
        store.set(key, { value, ttl });
        return 'OK';
      }),
      quit: vi.fn(async () => {}),
    };
  }

  it('checkAndSet returns true on first set (NX succeeds)', async () => {
    const redis = mockRedisClient();
    const store = new RedisReplayStore(redis, { prefix: 'test:' });
    expect(await store.checkAndSet('nonce-1', 5000, 1000)).toBe(true);
  });

  it('checkAndSet returns false on duplicate (NX fails)', async () => {
    const redis = mockRedisClient();
    const store = new RedisReplayStore(redis, { prefix: 'test:' });
    await store.checkAndSet('nonce-1', 5000, 1000);
    expect(await store.checkAndSet('nonce-1', 5000, 2000)).toBe(false);
  });

  it('has returns true when key exists', async () => {
    const redis = mockRedisClient();
    const store = new RedisReplayStore(redis, { prefix: 'test:' });
    await store.set('key', 1000);
    expect(await store.has('key', 5000, 2000)).toBe(true);
  });

  it('has returns false when key does not exist', async () => {
    const redis = mockRedisClient();
    const store = new RedisReplayStore(redis, { prefix: 'test:' });
    expect(await store.has('missing', 5000, 1000)).toBe(false);
  });

  it('uses configured prefix for Redis keys', async () => {
    const redis = mockRedisClient();
    const store = new RedisReplayStore(redis, { prefix: 'myapp:replay:' });
    await store.set('abc', 1000);
    expect(redis.set).toHaveBeenCalledWith(expect.stringContaining('myapp:replay:abc'), '1000');
  });

  it('close calls redis quit', async () => {
    const redis = mockRedisClient();
    const store = new RedisReplayStore(redis);
    await store.close();
    expect(redis.quit).toHaveBeenCalled();
  });

  it('cleanup is a no-op (Redis handles TTL)', async () => {
    const redis = mockRedisClient();
    const store = new RedisReplayStore(redis);
    await expect(store.cleanup(5000, 1000)).resolves.toBeUndefined();
  });
});

describe('createReplayStore', () => {
  it('creates MemoryReplayStore by default', () => {
    const store = createReplayStore();
    expect(store).toBeInstanceOf(MemoryReplayStore);
  });

  it('creates RedisReplayStore when redisClient provided', () => {
    const fakeRedis: RedisClient = {
      get: vi.fn(),
      set: vi.fn(),
    };
    const store = createReplayStore({ redisClient: fakeRedis });
    expect(store).toBeInstanceOf(RedisReplayStore);
  });

  it('passes options to MemoryReplayStore', async () => {
    const store = createReplayStore({ bloomSizeBits: 512, bloomHashes: 2, maxSize: 10 });
    expect(store).toBeInstanceOf(MemoryReplayStore);
    // Verify it works
    expect(await store.checkAndSet('test', 5000, 1000)).toBe(true);
  });
});
