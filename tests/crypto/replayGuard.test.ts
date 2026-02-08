/**
 * ReplayGuard Tests (MEDIUM-001 fix)
 *
 * Tests for both single-process and distributed replay protection.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  ReplayGuard,
  MemoryReplayStore,
  RedisReplayStore,
  type RedisClient,
} from '../../src/crypto/replayGuard.js';

describe('ReplayGuard', () => {
  describe('MemoryReplayStore (single-process)', () => {
    let guard: ReplayGuard;

    beforeEach(() => {
      guard = new ReplayGuard({ ttlSeconds: 1 }); // 1 second TTL for tests
    });

    it('allows first request', () => {
      const result = guard.checkAndSet('provider1', 'request1');
      expect(result).toBe(true);
    });

    it('rejects duplicate request within TTL', () => {
      guard.checkAndSet('provider1', 'request1');
      const result = guard.checkAndSet('provider1', 'request1');
      expect(result).toBe(false);
    });

    it('allows same request after TTL expires', async () => {
      const now = Date.now();
      guard.checkAndSet('provider1', 'request1', now);

      // Simulate TTL expiration (1.1 seconds later)
      const result = guard.checkAndSet('provider1', 'request1', now + 1100);
      expect(result).toBe(true);
    });

    it('allows different request IDs for same provider', () => {
      guard.checkAndSet('provider1', 'request1');
      const result = guard.checkAndSet('provider1', 'request2');
      expect(result).toBe(true);
    });

    it('allows same request ID for different providers', () => {
      guard.checkAndSet('provider1', 'request1');
      const result = guard.checkAndSet('provider2', 'request1');
      expect(result).toBe(true);
    });

    it('handles high volume without memory issues', () => {
      // Create guard with small max size to trigger GC
      const smallGuard = new ReplayGuard({
        ttlSeconds: 600,
        store: new MemoryReplayStore({ maxSize: 100 }),
      });

      // Add 150 entries to trigger garbage collection
      for (let i = 0; i < 150; i++) {
        smallGuard.checkAndSet('provider', `request-${i}`);
      }

      // Should still work
      const result = smallGuard.checkAndSet('provider', 'new-request');
      expect(result).toBe(true);
    });
  });

  describe('MemoryReplayStore async API', () => {
    let store: MemoryReplayStore;

    beforeEach(() => {
      store = new MemoryReplayStore();
    });

    it('async checkAndSet works correctly', async () => {
      const result1 = await store.checkAndSet('key1', 60000, Date.now());
      expect(result1).toBe(true);

      const result2 = await store.checkAndSet('key1', 60000, Date.now());
      expect(result2).toBe(false);
    });

    it('async has works correctly', async () => {
      const now = Date.now();
      await store.set('key1', now);

      const exists = await store.has('key1', 60000, now);
      expect(exists).toBe(true);

      const notExists = await store.has('key2', 60000, now);
      expect(notExists).toBe(false);
    });
  });

  describe('RedisReplayStore (distributed)', () => {
    let mockRedis: RedisClient;
    let store: RedisReplayStore;
    const storage = new Map<string, string>();

    beforeEach(() => {
      storage.clear();

      // Mock Redis client
      mockRedis = {
        get: vi.fn(async (key: string) => storage.get(key) ?? null),
        set: vi.fn(async (key: string, value: string, ...args: (string | number)[]) => {
          // Simulate SET NX behavior
          if (args.includes('NX') && storage.has(key)) {
            return null; // Key exists, NX fails
          }
          storage.set(key, value);
          return 'OK';
        }),
        quit: vi.fn(async () => {}),
      };

      store = new RedisReplayStore(mockRedis, { prefix: 'test:replay:' });
    });

    it('allows first request', async () => {
      const result = await store.checkAndSet('key1', 60000, Date.now());
      expect(result).toBe(true);
      expect(mockRedis.set).toHaveBeenCalledWith(
        'test:replay:key1',
        expect.any(String),
        'EX',
        60,
        'NX'
      );
    });

    it('rejects duplicate request', async () => {
      await store.checkAndSet('key1', 60000, Date.now());
      const result = await store.checkAndSet('key1', 60000, Date.now());
      expect(result).toBe(false);
    });

    it('uses correct key prefix', async () => {
      await store.checkAndSet('mykey', 60000, Date.now());
      expect(mockRedis.set).toHaveBeenCalledWith(
        'test:replay:mykey',
        expect.any(String),
        'EX',
        60,
        'NX'
      );
    });

    it('closes connection on close()', async () => {
      await store.close();
      expect(mockRedis.quit).toHaveBeenCalled();
    });
  });

  describe('ReplayGuard with async store', () => {
    it('checkAndSetAsync works with Redis store', async () => {
      const storage = new Map<string, string>();
      const mockRedis: RedisClient = {
        get: vi.fn(async (key: string) => storage.get(key) ?? null),
        set: vi.fn(async (key: string, value: string, ...args: (string | number)[]) => {
          if (args.includes('NX') && storage.has(key)) return null;
          storage.set(key, value);
          return 'OK';
        }),
      };

      const guard = ReplayGuard.create({ ttlSeconds: 60, redisClient: mockRedis });

      const result1 = await guard.checkAndSetAsync('provider1', 'request1');
      expect(result1).toBe(true);

      const result2 = await guard.checkAndSetAsync('provider1', 'request1');
      expect(result2).toBe(false);
    });

    it('sync checkAndSet fails closed with async store', () => {
      const mockRedis: RedisClient = {
        get: vi.fn(async () => null),
        set: vi.fn(async () => 'OK'),
      };

      const guard = ReplayGuard.create({ ttlSeconds: 60, redisClient: mockRedis });

      // Sync call with async store should fail closed (return false)
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      const result = guard.checkAndSet('provider1', 'request1');
      expect(result).toBe(false);
      expect(consoleSpy).toHaveBeenCalled();
      consoleSpy.mockRestore();
    });
  });

  describe('ReplayGuard.create factory', () => {
    it('creates memory store by default', () => {
      const guard = ReplayGuard.create({ ttlSeconds: 60 });
      // Should work synchronously (memory store)
      const result = guard.checkAndSet('provider1', 'request1');
      expect(result).toBe(true);
    });

    it('creates Redis store when client provided', async () => {
      const storage = new Map<string, string>();
      const mockRedis: RedisClient = {
        get: vi.fn(async (key: string) => storage.get(key) ?? null),
        set: vi.fn(async (key: string, value: string, ...args: (string | number)[]) => {
          if (args.includes('NX') && storage.has(key)) return null;
          storage.set(key, value);
          return 'OK';
        }),
      };

      const guard = ReplayGuard.create({ ttlSeconds: 60, redisClient: mockRedis });

      // Async API should work
      const result = await guard.checkAndSetAsync('provider1', 'request1');
      expect(result).toBe(true);
      expect(mockRedis.set).toHaveBeenCalled();
    });
  });
});
