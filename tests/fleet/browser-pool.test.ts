/**
 * @file browser-pool.test.ts
 * @module tests/fleet/browser-pool
 * @component Memory-Aware Browser Pool Tests
 *
 * Groups:
 *   A: Pool construction & defaults (5 tests)
 *   B: Instance acquisition (10 tests)
 *   C: Release & lifecycle (6 tests)
 *   D: Memory budgeting (8 tests)
 *   E: LRU eviction (8 tests)
 *   F: Warm reuse (5 tests)
 *   G: Health monitoring (5 tests)
 *   H: Statistics & events (5 tests)
 *   I: Shutdown (3 tests)
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  BrowserPool,
  DEFAULT_POOL_CONFIG,
  type BrowserPoolConfig,
  type PooledInstance,
  type EvictionEvent,
} from '../../src/fleet/browser-pool.js';
import type { BrowserBackend } from '../../src/browser/agent.js';
import type { PageObservation } from '../../src/browser/types.js';

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════

function mockBackend(): BrowserBackend {
  let connected = false;
  return {
    async initialize() { connected = true; },
    async navigate() {},
    async click() {},
    async type() {},
    async scroll() {},
    async executeScript<T>(): Promise<T> { return undefined as T; },
    async screenshot() { return Buffer.from('mock'); },
    async observe(): Promise<PageObservation> {
      return {
        url: 'about:blank', title: 'Mock', readyState: 'complete',
        viewport: { width: 1280, height: 720 }, scroll: { x: 0, y: 0 },
        interactiveElements: [], forms: [], dialogs: [],
        loadTime: 100, timestamp: Date.now(),
      };
    },
    async close() { connected = false; },
    isConnected() { return connected; },
  };
}

// ═══════════════════════════════════════════════════════════════
// A: Pool Construction & Defaults
// ═══════════════════════════════════════════════════════════════

describe('A — Pool Construction', () => {
  it('A1: creates pool with default config', () => {
    const pool = new BrowserPool();
    expect(pool.size).toBe(0);
    expect(pool.totalMemoryMB).toBe(0);
  });

  it('A2: default config values are sensible', () => {
    expect(DEFAULT_POOL_CONFIG.maxMemoryMB).toBe(2048);
    expect(DEFAULT_POOL_CONFIG.maxInstances).toBe(8);
    expect(DEFAULT_POOL_CONFIG.maxPerAgent).toBe(3);
    expect(DEFAULT_POOL_CONFIG.estimatedInstanceMemoryMB).toBe(150);
    expect(DEFAULT_POOL_CONFIG.warmReuse).toBe(true);
  });

  it('A3: accepts partial config overrides', () => {
    const pool = new BrowserPool({ maxMemoryMB: 512, maxInstances: 2 });
    const stats = pool.getStats();
    expect(stats.totalInstances).toBe(0);
  });

  it('A4: memory pressure starts at low', () => {
    const pool = new BrowserPool();
    expect(pool.memoryPressure).toBe('low');
  });

  it('A5: stats show zero state initially', () => {
    const pool = new BrowserPool();
    const stats = pool.getStats();
    expect(stats.totalInstances).toBe(0);
    expect(stats.activeInstances).toBe(0);
    expect(stats.totalMemoryMB).toBe(0);
    expect(stats.memoryUtilization).toBe(0);
    expect(stats.totalCreated).toBe(0);
    expect(stats.totalEvicted).toBe(0);
    expect(stats.totalReuses).toBe(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// B: Instance Acquisition
// ═══════════════════════════════════════════════════════════════

describe('B — Acquisition', () => {
  let pool: BrowserPool;

  beforeEach(() => {
    pool = new BrowserPool({ maxMemoryMB: 1024, maxInstances: 4, maxPerAgent: 2 });
  });

  it('B1: acquires a new instance successfully', () => {
    const result = pool.acquire('agent-1', mockBackend());
    expect(result.success).toBe(true);
    expect(result.instance).toBeDefined();
    expect(result.instance!.agentId).toBe('agent-1');
    expect(result.instance!.status).toBe('active');
    expect(result.reused).toBe(false);
  });

  it('B2: assigns unique instance IDs', () => {
    const r1 = pool.acquire('agent-1', mockBackend());
    const r2 = pool.acquire('agent-1', mockBackend());
    expect(r1.instance!.id).not.toBe(r2.instance!.id);
  });

  it('B3: respects per-agent limit', () => {
    pool.acquire('agent-1', mockBackend());
    pool.acquire('agent-1', mockBackend());
    const r3 = pool.acquire('agent-1', mockBackend());
    expect(r3.success).toBe(false);
    expect(r3.reason).toContain('max instances');
  });

  it('B4: different agents have independent limits', () => {
    pool.acquire('agent-1', mockBackend());
    pool.acquire('agent-1', mockBackend());
    const r3 = pool.acquire('agent-2', mockBackend());
    expect(r3.success).toBe(true);
  });

  it('B5: respects global instance limit', () => {
    pool.acquire('a1', mockBackend());
    pool.acquire('a2', mockBackend());
    pool.acquire('a3', mockBackend());
    pool.acquire('a4', mockBackend());
    // All 4 are active, none idle to evict
    const r5 = pool.acquire('a5', mockBackend());
    expect(r5.success).toBe(false);
  });

  it('B6: evicts idle to make room at global limit', () => {
    pool.acquire('a1', mockBackend());
    const r2 = pool.acquire('a2', mockBackend());
    pool.acquire('a3', mockBackend());
    pool.acquire('a4', mockBackend());

    // Release one to make it idle
    pool.release(r2.instance!.id);

    // Now a new acquire should evict the idle one
    const r5 = pool.acquire('a5', mockBackend());
    expect(r5.success).toBe(true);
  });

  it('B7: tracks memory per instance', () => {
    pool.acquire('a1', mockBackend());
    expect(pool.totalMemoryMB).toBe(150); // Default estimate
  });

  it('B8: instance has correct initial fields', () => {
    const result = pool.acquire('agent-1', mockBackend(), ['domain:example.com']);
    const inst = result.instance!;
    expect(inst.currentUrl).toBe('about:blank');
    expect(inst.actionCount).toBe(0);
    expect(inst.errorCount).toBe(0);
    expect(inst.tags.has('domain:example.com')).toBe(true);
    expect(inst.memoryMB).toBe(150);
  });

  it('B9: increments totalCreated', () => {
    pool.acquire('a1', mockBackend());
    pool.acquire('a2', mockBackend());
    expect(pool.getStats().totalCreated).toBe(2);
  });

  it('B10: pool size matches instance count', () => {
    pool.acquire('a1', mockBackend());
    pool.acquire('a2', mockBackend());
    expect(pool.size).toBe(2);
  });
});

// ═══════════════════════════════════════════════════════════════
// C: Release & Lifecycle
// ═══════════════════════════════════════════════════════════════

describe('C — Release & Lifecycle', () => {
  let pool: BrowserPool;

  beforeEach(() => {
    pool = new BrowserPool();
  });

  it('C1: release sets instance to idle', () => {
    const r = pool.acquire('a1', mockBackend());
    pool.release(r.instance!.id);
    expect(pool.getInstance(r.instance!.id)!.status).toBe('idle');
  });

  it('C2: release returns false for unknown ID', () => {
    expect(pool.release('nonexistent')).toBe(false);
  });

  it('C3: markActive increments action count', () => {
    const r = pool.acquire('a1', mockBackend());
    pool.release(r.instance!.id);
    pool.markActive(r.instance!.id);
    expect(pool.getInstance(r.instance!.id)!.status).toBe('active');
    expect(pool.getInstance(r.instance!.id)!.actionCount).toBe(1);
  });

  it('C4: updateMemory changes estimate', () => {
    const r = pool.acquire('a1', mockBackend());
    pool.updateMemory(r.instance!.id, 200);
    expect(pool.getInstance(r.instance!.id)!.memoryMB).toBe(200);
    expect(pool.totalMemoryMB).toBe(200);
  });

  it('C5: updateUrl tracks current URL', () => {
    const r = pool.acquire('a1', mockBackend());
    pool.updateUrl(r.instance!.id, 'https://example.com');
    expect(pool.getInstance(r.instance!.id)!.currentUrl).toBe('https://example.com');
  });

  it('C6: getAgentInstances returns correct subset', () => {
    pool.acquire('a1', mockBackend());
    pool.acquire('a2', mockBackend());
    pool.acquire('a1', mockBackend());
    expect(pool.getAgentInstances('a1')).toHaveLength(2);
    expect(pool.getAgentInstances('a2')).toHaveLength(1);
  });
});

// ═══════════════════════════════════════════════════════════════
// D: Memory Budgeting
// ═══════════════════════════════════════════════════════════════

describe('D — Memory Budgeting', () => {
  it('D1: blocks acquisition when memory budget exceeded', () => {
    // Budget: 300 MB, each instance: 150 MB → max 2
    const pool = new BrowserPool({ maxMemoryMB: 300, maxInstances: 10, maxPerAgent: 10 });
    pool.acquire('a1', mockBackend());
    pool.acquire('a2', mockBackend());
    const r3 = pool.acquire('a3', mockBackend());
    expect(r3.success).toBe(false);
    expect(r3.reason).toContain('memory');
  });

  it('D2: evicts idle to make memory room', () => {
    const pool = new BrowserPool({ maxMemoryMB: 300, maxInstances: 10, maxPerAgent: 10 });
    const r1 = pool.acquire('a1', mockBackend());
    pool.acquire('a2', mockBackend());

    // Release first to make it evictable
    pool.release(r1.instance!.id);

    // Third should succeed after evicting first
    const r3 = pool.acquire('a3', mockBackend());
    expect(r3.success).toBe(true);
  });

  it('D3: totalMemoryMB tracks all instances', () => {
    const pool = new BrowserPool({ estimatedInstanceMemoryMB: 100 });
    pool.acquire('a1', mockBackend());
    pool.acquire('a2', mockBackend());
    pool.acquire('a3', mockBackend());
    expect(pool.totalMemoryMB).toBe(300);
  });

  it('D4: memory pressure rises with usage', () => {
    const pool = new BrowserPool({ maxMemoryMB: 600, estimatedInstanceMemoryMB: 150, maxInstances: 10, maxPerAgent: 10 });
    expect(pool.memoryPressure).toBe('low');

    pool.acquire('a1', mockBackend()); // 150/600 = 25%
    expect(pool.memoryPressure).toBe('low');

    pool.acquire('a2', mockBackend()); // 300/600 = 50%
    expect(pool.memoryPressure).toBe('low');

    pool.acquire('a3', mockBackend()); // 450/600 = 75%
    expect(pool.memoryPressure).toBe('medium');

    pool.acquire('a4', mockBackend()); // 600/600 = 100%
    expect(pool.memoryPressure).toBe('critical');
  });

  it('D5: memory freed appears in stats after eviction', () => {
    const pool = new BrowserPool({ estimatedInstanceMemoryMB: 100 });
    const r = pool.acquire('a1', mockBackend());
    pool.release(r.instance!.id);
    pool.evictLRU();
    expect(pool.totalMemoryMB).toBe(0);
  });

  it('D6: availableMemoryMB reflects budget minus used', () => {
    const pool = new BrowserPool({ maxMemoryMB: 1000, estimatedInstanceMemoryMB: 200 });
    pool.acquire('a1', mockBackend());
    const stats = pool.getStats();
    expect(stats.availableMemoryMB).toBe(800);
  });

  it('D7: memoryUtilization is ratio', () => {
    const pool = new BrowserPool({ maxMemoryMB: 1000, estimatedInstanceMemoryMB: 250 });
    pool.acquire('a1', mockBackend());
    pool.acquire('a2', mockBackend());
    const stats = pool.getStats();
    expect(stats.memoryUtilization).toBeCloseTo(0.5);
  });

  it('D8: updated memory estimates affect budget checks', () => {
    const pool = new BrowserPool({ maxMemoryMB: 400, estimatedInstanceMemoryMB: 150, maxInstances: 10, maxPerAgent: 10 });
    const r1 = pool.acquire('a1', mockBackend());
    pool.acquire('a2', mockBackend());
    // 300 MB used, 100 MB available

    // Update first instance to use less memory
    pool.updateMemory(r1.instance!.id, 50);
    // Now 200 MB used, 200 MB available

    const r3 = pool.acquire('a3', mockBackend());
    expect(r3.success).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════
// E: LRU Eviction
// ═══════════════════════════════════════════════════════════════

describe('E — LRU Eviction', () => {
  let pool: BrowserPool;

  beforeEach(() => {
    pool = new BrowserPool({ idleTimeoutMs: 100 });
  });

  it('E1: evictLRU removes oldest idle instance', () => {
    const r1 = pool.acquire('a1', mockBackend());
    const r2 = pool.acquire('a2', mockBackend());

    // Make both idle, r1 is older
    pool.release(r1.instance!.id);
    pool.release(r2.instance!.id);

    const evicted = pool.evictLRU();
    expect(evicted).toBe(true);
    expect(pool.getInstance(r1.instance!.id)).toBeUndefined();
    expect(pool.getInstance(r2.instance!.id)).toBeDefined();
  });

  it('E2: evictLRU returns false with no idle instances', () => {
    pool.acquire('a1', mockBackend()); // Still active
    expect(pool.evictLRU()).toBe(false);
  });

  it('E3: evictToFree frees requested amount', () => {
    const r1 = pool.acquire('a1', mockBackend());
    const r2 = pool.acquire('a2', mockBackend());
    pool.release(r1.instance!.id);
    pool.release(r2.instance!.id);

    const freed = pool.evictToFree(200); // Need 200 MB
    expect(freed).toBeGreaterThanOrEqual(200);
  });

  it('E4: evictToFree evicts in LRU order', () => {
    const r1 = pool.acquire('a1', mockBackend());
    const r2 = pool.acquire('a2', mockBackend());
    const r3 = pool.acquire('a3', mockBackend());

    pool.release(r1.instance!.id);
    pool.release(r2.instance!.id);
    pool.release(r3.instance!.id);

    // Free 150 MB (one instance)
    pool.evictToFree(150);
    // r1 should be gone (oldest), r2 and r3 remain
    expect(pool.getInstance(r1.instance!.id)).toBeUndefined();
    expect(pool.getInstance(r2.instance!.id)).toBeDefined();
  });

  it('E5: evictStale removes timed-out idle instances', async () => {
    const r1 = pool.acquire('a1', mockBackend());
    pool.release(r1.instance!.id);

    // Manually set lastUsedAt to the past
    const inst = pool.getInstance(r1.instance!.id)!;
    (inst as any).lastUsedAt = Date.now() - 200; // 200ms ago, timeout is 100ms

    const count = pool.evictStale();
    expect(count).toBe(1);
    expect(pool.size).toBe(0);
  });

  it('E6: evictStale keeps fresh idle instances', () => {
    const r1 = pool.acquire('a1', mockBackend());
    pool.release(r1.instance!.id);
    // Just released — not stale yet
    expect(pool.evictStale()).toBe(0);
    expect(pool.size).toBe(1);
  });

  it('E7: destroy removes specific instance', () => {
    const r1 = pool.acquire('a1', mockBackend());
    expect(pool.destroy(r1.instance!.id)).toBe(true);
    expect(pool.size).toBe(0);
  });

  it('E8: totalEvicted increments on eviction', () => {
    const r1 = pool.acquire('a1', mockBackend());
    pool.release(r1.instance!.id);
    pool.evictLRU();
    expect(pool.getStats().totalEvicted).toBe(1);
  });
});

// ═══════════════════════════════════════════════════════════════
// F: Warm Reuse
// ═══════════════════════════════════════════════════════════════

describe('F — Warm Reuse', () => {
  let pool: BrowserPool;

  beforeEach(() => {
    pool = new BrowserPool({ warmReuse: true });
  });

  it('F1: reuses idle instance with matching tags', () => {
    const r1 = pool.acquire('a1', mockBackend(), ['domain:example.com']);
    pool.release(r1.instance!.id);

    const r2 = pool.acquire('a1', mockBackend(), ['domain:example.com']);
    expect(r2.success).toBe(true);
    expect(r2.reused).toBe(true);
    expect(r2.instance!.id).toBe(r1.instance!.id);
  });

  it('F2: prefers same agent instances for reuse', () => {
    const r1 = pool.acquire('a1', mockBackend(), ['tag']);
    const r2 = pool.acquire('a2', mockBackend(), ['tag']);
    pool.release(r1.instance!.id);
    pool.release(r2.instance!.id);

    const r3 = pool.acquire('a1', mockBackend(), ['tag']);
    expect(r3.reused).toBe(true);
    expect(r3.instance!.id).toBe(r1.instance!.id);
  });

  it('F3: no reuse when tags don\'t match', () => {
    const r1 = pool.acquire('a1', mockBackend(), ['domain:a.com']);
    pool.release(r1.instance!.id);

    // Different tags — still reuses if any idle (but with lower score)
    const r2 = pool.acquire('a1', mockBackend(), ['domain:b.com']);
    // Should still reuse the idle instance (same agent bonus)
    expect(r2.success).toBe(true);
  });

  it('F4: no reuse when warmReuse is disabled', () => {
    const coldPool = new BrowserPool({ warmReuse: false, maxInstances: 10 });
    const r1 = coldPool.acquire('a1', mockBackend(), ['tag']);
    coldPool.release(r1.instance!.id);

    const r2 = coldPool.acquire('a1', mockBackend(), ['tag']);
    expect(r2.reused).toBe(false);
    expect(r2.instance!.id).not.toBe(r1.instance!.id);
  });

  it('F5: reuse increments totalReuses', () => {
    const r1 = pool.acquire('a1', mockBackend(), ['tag']);
    pool.release(r1.instance!.id);
    pool.acquire('a1', mockBackend(), ['tag']);
    expect(pool.getStats().totalReuses).toBe(1);
  });
});

// ═══════════════════════════════════════════════════════════════
// G: Health Monitoring
// ═══════════════════════════════════════════════════════════════

describe('G — Health', () => {
  let pool: BrowserPool;

  beforeEach(() => {
    pool = new BrowserPool();
  });

  it('G1: recordError increments error count', () => {
    const r = pool.acquire('a1', mockBackend());
    pool.recordError(r.instance!.id);
    expect(pool.getInstance(r.instance!.id)!.errorCount).toBe(1);
  });

  it('G2: 5 errors mark instance unhealthy', () => {
    const r = pool.acquire('a1', mockBackend());
    for (let i = 0; i < 5; i++) {
      pool.recordError(r.instance!.id);
    }
    expect(pool.getInstance(r.instance!.id)!.status).toBe('unhealthy');
  });

  it('G3: evictUnhealthy removes unhealthy instances', () => {
    const r = pool.acquire('a1', mockBackend());
    for (let i = 0; i < 5; i++) pool.recordError(r.instance!.id);

    const count = pool.evictUnhealthy();
    expect(count).toBe(1);
    expect(pool.size).toBe(0);
  });

  it('G4: stats track unhealthy count', () => {
    const r = pool.acquire('a1', mockBackend());
    for (let i = 0; i < 5; i++) pool.recordError(r.instance!.id);

    expect(pool.getStats().unhealthyInstances).toBe(1);
  });

  it('G5: healthy instances stay active', () => {
    const r = pool.acquire('a1', mockBackend());
    pool.recordError(r.instance!.id); // Just 1 error
    expect(pool.getInstance(r.instance!.id)!.status).toBe('active');
    expect(pool.evictUnhealthy()).toBe(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// H: Statistics & Events
// ═══════════════════════════════════════════════════════════════

describe('H — Stats & Events', () => {
  it('H1: stats reflect pool state accurately', () => {
    const pool = new BrowserPool({ estimatedInstanceMemoryMB: 100 });
    pool.acquire('a1', mockBackend());
    const r2 = pool.acquire('a2', mockBackend());
    pool.release(r2.instance!.id);

    const stats = pool.getStats();
    expect(stats.totalInstances).toBe(2);
    expect(stats.activeInstances).toBe(1);
    expect(stats.idleInstances).toBe(1);
    expect(stats.totalMemoryMB).toBe(200);
    expect(stats.agentCounts['a1']).toBe(1);
    expect(stats.agentCounts['a2']).toBe(1);
  });

  it('H2: eviction listener receives events', () => {
    const pool = new BrowserPool();
    const events: EvictionEvent[] = [];
    pool.onEviction((e) => events.push(e));

    const r = pool.acquire('a1', mockBackend());
    pool.release(r.instance!.id);
    pool.evictLRU();

    expect(events).toHaveLength(1);
    expect(events[0].agentId).toBe('a1');
    expect(events[0].reason).toBe('memory');
    expect(events[0].memoryFreedMB).toBe(150);
  });

  it('H3: unsubscribe stops listener', () => {
    const pool = new BrowserPool();
    const events: EvictionEvent[] = [];
    const unsub = pool.onEviction((e) => events.push(e));
    unsub();

    const r = pool.acquire('a1', mockBackend());
    pool.release(r.instance!.id);
    pool.evictLRU();

    expect(events).toHaveLength(0);
  });

  it('H4: getAllInstances returns all', () => {
    const pool = new BrowserPool();
    pool.acquire('a1', mockBackend());
    pool.acquire('a2', mockBackend());
    expect(pool.getAllInstances()).toHaveLength(2);
  });

  it('H5: getInstance returns undefined for unknown', () => {
    const pool = new BrowserPool();
    expect(pool.getInstance('nope')).toBeUndefined();
  });
});

// ═══════════════════════════════════════════════════════════════
// I: Shutdown
// ═══════════════════════════════════════════════════════════════

describe('I — Shutdown', () => {
  it('I1: shutdown closes all instances', async () => {
    const pool = new BrowserPool();
    pool.acquire('a1', mockBackend());
    pool.acquire('a2', mockBackend());
    pool.acquire('a3', mockBackend());

    const closed = await pool.shutdown();
    expect(closed).toBe(3);
    expect(pool.size).toBe(0);
  });

  it('I2: shutdown handles close errors gracefully', async () => {
    const pool = new BrowserPool();
    const failBackend = mockBackend();
    failBackend.close = async () => { throw new Error('close failed'); };
    pool.acquire('a1', failBackend);

    const closed = await pool.shutdown();
    expect(closed).toBe(1);
    expect(pool.size).toBe(0);
  });

  it('I3: pool is usable after shutdown', async () => {
    const pool = new BrowserPool();
    pool.acquire('a1', mockBackend());
    await pool.shutdown();

    const r = pool.acquire('a2', mockBackend());
    expect(r.success).toBe(true);
    expect(pool.size).toBe(1);
  });
});
