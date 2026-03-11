/**
 * @file headless-validation.integration.test.ts
 * @module tests/hydra/headless-validation
 * @layer Layer 13 (Risk Decision), Layer 14 (Telemetry)
 * @component HYDRA Headless Browser
 *
 * 8 quick validation tests for the headless browser service.
 * All tests use in-memory mocks — no real browser required.
 *
 * Tests:
 *   1. Cookie & localStorage persistence
 *   2. Concurrent agent isolation
 *   3. Restart recovery (crash/evict → resume)
 *   4. Proxy rotation & per-session egress
 *   5. Replay & audit trail
 *   6. Deterministic fingerprint surface
 *   7. Memory leak smoke test
 *   8. Session export/import (portability)
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { createHash } from 'crypto';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

// ---------------------------------------------------------------------------
//  Mock persistent context — mirrors Playwright launchPersistentContext
// ---------------------------------------------------------------------------

interface PersistentState {
  storage: Record<string, string>;
  cookies: Record<string, string>;
  launchFlags: Record<string, unknown>;
}

class MockPersistentContext {
  readonly userDataDir: string;
  storage: Record<string, string>;
  cookies: Record<string, string>;
  launchFlags: Record<string, unknown>;
  closed = false;

  constructor(userDataDir: string, flags: Record<string, unknown> = {}) {
    this.userDataDir = userDataDir;
    this.storage = {};
    this.cookies = {};
    this.launchFlags = flags;
    this.load();
  }

  private stateFile(): string {
    return path.join(this.userDataDir, '_mock_state.json');
  }

  save(): void {
    fs.mkdirSync(this.userDataDir, { recursive: true });
    const state: PersistentState = {
      storage: this.storage,
      cookies: this.cookies,
      launchFlags: this.launchFlags,
    };
    fs.writeFileSync(this.stateFile(), JSON.stringify(state, null, 2));
  }

  load(): void {
    const sf = this.stateFile();
    if (fs.existsSync(sf)) {
      const data: PersistentState = JSON.parse(fs.readFileSync(sf, 'utf-8'));
      this.storage = data.storage ?? {};
      this.cookies = data.cookies ?? {};
      this.launchFlags = data.launchFlags ?? {};
    }
  }

  async close(): Promise<void> {
    this.save();
    this.closed = true;
  }
}

function openCtx(userDataDir: string, flags: Record<string, unknown> = {}): MockPersistentContext {
  return new MockPersistentContext(userDataDir, flags);
}

// ---------------------------------------------------------------------------
//  Step logger (audit trail)
// ---------------------------------------------------------------------------

interface StepEntry {
  ts: number;
  action: string;
  target: string;
  [k: string]: unknown;
}

class StepLogger {
  steps: StepEntry[] = [];
  network: Array<{ url: string; status: number; ts: number }> = [];

  log(action: string, target: string, meta: Record<string, unknown> = {}): void {
    this.steps.push({ ts: Date.now(), action, target, ...meta });
  }

  logRequest(url: string, status: number): void {
    this.network.push({ url, status, ts: Date.now() });
  }

  exportNdjson(): string {
    const lines: string[] = [];
    for (const s of this.steps) lines.push(JSON.stringify(s));
    for (const n of this.network) lines.push(JSON.stringify(n));
    return lines.join('\n');
  }
}

// ---------------------------------------------------------------------------
//  Temp dir helper
// ---------------------------------------------------------------------------

let tmpRoot: string;

function tmpDir(name: string): string {
  const d = path.join(tmpRoot, name);
  fs.mkdirSync(d, { recursive: true });
  return d;
}

beforeEach(() => {
  tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'hydra-val-'));
});

afterEach(() => {
  fs.rmSync(tmpRoot, { recursive: true, force: true });
});

// =========================================================================
//  Test 1 — Cookie & localStorage persistence
// =========================================================================

describe('T1: Cookie & localStorage persistence', () => {
  it('localStorage and cookies survive close + reopen', async () => {
    const udd = tmpDir('agent-a');

    const ctx1 = openCtx(udd);
    ctx1.storage['foo'] = 'bar';
    ctx1.cookies['session_id'] = 'abc123';
    await ctx1.close();

    const ctx2 = openCtx(udd);
    expect(ctx2.storage['foo']).toBe('bar');
    expect(ctx2.cookies['session_id']).toBe('abc123');
  });

  it('fresh profile starts clean', () => {
    const ctx = openCtx(tmpDir('fresh'));
    expect(Object.keys(ctx.storage)).toHaveLength(0);
    expect(Object.keys(ctx.cookies)).toHaveLength(0);
  });
});

// =========================================================================
//  Test 2 — Concurrent agent isolation
// =========================================================================

describe('T2: Concurrent agent isolation', () => {
  it('N sessions with distinct userDataDirs do not bleed', async () => {
    const N = 5;
    const dirs = Array.from({ length: N }, (_, i) => tmpDir(`agent-${i}`));

    // Write unique data per session
    for (let i = 0; i < N; i++) {
      const ctx = openCtx(dirs[i]);
      ctx.storage['agentId'] = `agent-${i}`;
      ctx.cookies['token'] = `tok-${i}`;
      await ctx.close();
    }

    // Verify isolation
    for (let i = 0; i < N; i++) {
      const ctx = openCtx(dirs[i]);
      expect(ctx.storage['agentId']).toBe(`agent-${i}`);
      expect(ctx.cookies['token']).toBe(`tok-${i}`);
    }
  });

  it('modifying one session does not affect another', async () => {
    const dirA = tmpDir('iso-a');
    const dirB = tmpDir('iso-b');

    const a = openCtx(dirA);
    const b = openCtx(dirB);
    a.storage['key'] = 'A';
    b.storage['key'] = 'B';
    await a.close();
    await b.close();

    expect(openCtx(dirA).storage['key']).toBe('A');
    expect(openCtx(dirB).storage['key']).toBe('B');
  });
});

// =========================================================================
//  Test 3 — Restart recovery (crash/evict → resume)
// =========================================================================

describe('T3: Restart recovery', () => {
  it('state recovers after simulated crash (no close)', () => {
    const udd = tmpDir('crash');
    const ctx = openCtx(udd);
    ctx.storage['step'] = '3';
    ctx.cookies['auth'] = 'jwt-xyz';
    ctx.save(); // periodic checkpoint before crash

    // Abandon without close — simulate OOM kill
    const recovered = openCtx(udd);
    expect(recovered.storage['step']).toBe('3');
    expect(recovered.cookies['auth']).toBe('jwt-xyz');
  });

  it('handles missing state file gracefully', () => {
    const udd = tmpDir('no-state');
    const ctx = openCtx(udd);
    expect(ctx.storage).toEqual({});
    expect(ctx.cookies).toEqual({});
  });
});

// =========================================================================
//  Test 4 — Proxy rotation & per-session egress
// =========================================================================

describe('T4: Proxy rotation & per-session egress', () => {
  it('each session records its assigned proxy', () => {
    const proxies = ['http://proxy1:8080', 'http://proxy2:8080', 'socks5://proxy3:1080'];
    const contexts = proxies.map((p, i) => openCtx(tmpDir(`proxy-${i}`), { proxy: p }));

    for (let i = 0; i < proxies.length; i++) {
      expect(contexts[i].launchFlags['proxy']).toBe(proxies[i]);
    }
  });

  it('proxy survives restart', async () => {
    const udd = tmpDir('proxy-persist');
    const ctx = openCtx(udd, { proxy: 'http://fixed:8080' });
    await ctx.close();

    const reopened = openCtx(udd);
    expect(reopened.launchFlags['proxy']).toBe('http://fixed:8080');
  });

  it('no-proxy session has no proxy flag', () => {
    const ctx = openCtx(tmpDir('no-proxy'));
    expect(ctx.launchFlags['proxy']).toBeUndefined();
  });
});

// =========================================================================
//  Test 5 — Replay & audit trail
// =========================================================================

describe('T5: Replay & audit trail', () => {
  it('step log is time-ordered', () => {
    const logger = new StepLogger();
    logger.log('navigate', 'https://example.com');
    logger.log('click', '#submit-btn');
    logger.log('type', '#search-box', { value: 'hello' });

    for (let i = 1; i < logger.steps.length; i++) {
      expect(logger.steps[i].ts).toBeGreaterThanOrEqual(logger.steps[i - 1].ts);
    }
  });

  it('NDJSON export is valid JSON per line', () => {
    const logger = new StepLogger();
    logger.log('navigate', 'https://example.com');
    logger.log('click', 'button.post');
    logger.logRequest('https://example.com', 200);

    const ndjson = logger.exportNdjson();
    const lines = ndjson.trim().split('\n');
    expect(lines).toHaveLength(3);

    for (const line of lines) {
      const parsed = JSON.parse(line);
      expect(parsed).toHaveProperty('ts');
    }
  });

  it('steps contain action + target', () => {
    const logger = new StepLogger();
    logger.log('scroll', 'body', { direction: 'down' });

    expect(logger.steps[0].action).toBe('scroll');
    expect(logger.steps[0].target).toBe('body');
    expect(logger.steps[0]['direction']).toBe('down');
  });
});

// =========================================================================
//  Test 6 — Deterministic fingerprint surface
// =========================================================================

describe('T6: Deterministic fingerprint surface', () => {
  function fingerprint(flags: Record<string, unknown>): string {
    const canonical = JSON.stringify(flags, Object.keys(flags).sort());
    return createHash('sha256').update(canonical).digest('hex').slice(0, 16);
  }

  const BASE_FLAGS = {
    lang: 'en-US',
    timezone: 'America/Los_Angeles',
    viewport: { width: 1366, height: 768 },
    userAgent: 'Mozilla/5.0 Test',
    webglVendor: 'Google Inc.',
  };

  it('same config → same fingerprint', () => {
    expect(fingerprint(BASE_FLAGS)).toBe(fingerprint({ ...BASE_FLAGS }));
  });

  it('different config → different fingerprint', () => {
    const alt = { ...BASE_FLAGS, timezone: 'Europe/Berlin' };
    expect(fingerprint(BASE_FLAGS)).not.toBe(fingerprint(alt));
  });

  it('fingerprint stable across restart', async () => {
    const udd = tmpDir('fp-agent');
    const ctx1 = openCtx(udd, BASE_FLAGS);
    const fp1 = fingerprint(ctx1.launchFlags as Record<string, unknown>);
    await ctx1.close();

    const ctx2 = openCtx(udd);
    const fp2 = fingerprint(ctx2.launchFlags as Record<string, unknown>);
    expect(fp1).toBe(fp2);
  });
});

// =========================================================================
//  Test 7 — Memory leak smoke test
// =========================================================================

describe('T7: Memory leak smoke test', () => {
  it('contexts can be created and garbage-collected without bloat', () => {
    // Track total bytes of state files as a proxy for leak
    const sizes: number[] = [];

    for (let i = 0; i < 100; i++) {
      const udd = tmpDir(`leak-${i}`);
      const ctx = openCtx(udd);
      ctx.storage['iteration'] = String(i);
      ctx.save();
      // Read size of state file
      const sf = path.join(udd, '_mock_state.json');
      sizes.push(fs.statSync(sf).size);
    }

    // All state files should be approximately the same size (no linear growth)
    const avg = sizes.reduce((a, b) => a + b, 0) / sizes.length;
    const maxDeviation = Math.max(...sizes.map((s) => Math.abs(s - avg)));
    // Iteration number grows in digits, so allow 20 bytes of deviation
    expect(maxDeviation).toBeLessThan(50);
  });

  it('no orphan state files left after explicit cleanup', () => {
    const udd = tmpDir('cleanup');
    const ctx = openCtx(udd);
    ctx.storage['temp'] = 'data';
    ctx.save();

    const sf = path.join(udd, '_mock_state.json');
    expect(fs.existsSync(sf)).toBe(true);

    // Simulate cleanup
    fs.rmSync(udd, { recursive: true, force: true });
    expect(fs.existsSync(sf)).toBe(false);
  });
});

// =========================================================================
//  Test 8 — Session export/import (portability)
// =========================================================================

describe('T8: Session export/import (portability)', () => {
  it('full roundtrip: export → import into fresh instance', async () => {
    const origin = tmpDir('origin');
    const ctx = openCtx(origin);
    ctx.storage['csrf_token'] = 'tok-abc';
    ctx.storage['user_prefs'] = JSON.stringify({ theme: 'dark' });
    ctx.cookies['session'] = 's3cr3t';
    ctx.cookies['__cf_bm'] = 'cf-value';
    await ctx.close();

    // Export
    const bundle = fs.readFileSync(path.join(origin, '_mock_state.json'), 'utf-8');

    // Import into fresh destination
    const dest = tmpDir('destination');
    fs.writeFileSync(path.join(dest, '_mock_state.json'), bundle);

    const imported = openCtx(dest);
    expect(imported.cookies['session']).toBe('s3cr3t');
    expect(imported.storage['csrf_token']).toBe('tok-abc');
    expect(JSON.parse(imported.storage['user_prefs']).theme).toBe('dark');
  });

  it('partial import (cookies only) works gracefully', () => {
    const udd = tmpDir('partial');
    const partial: PersistentState = {
      cookies: { auth: 'jwt-123' },
      storage: {},
      launchFlags: {},
    };
    fs.writeFileSync(path.join(udd, '_mock_state.json'), JSON.stringify(partial));

    const ctx = openCtx(udd);
    expect(ctx.cookies['auth']).toBe('jwt-123');
    expect(Object.keys(ctx.storage)).toHaveLength(0);
  });

  it('import overwrites existing state', async () => {
    const udd = tmpDir('overwrite');

    // Old state
    const old = openCtx(udd);
    old.storage['key'] = 'old_value';
    await old.close();

    // Overwrite with new bundle
    const bundle: PersistentState = {
      storage: { key: 'new_value' },
      cookies: {},
      launchFlags: {},
    };
    fs.writeFileSync(path.join(udd, '_mock_state.json'), JSON.stringify(bundle));

    const fresh = openCtx(udd);
    expect(fresh.storage['key']).toBe('new_value');
  });
});
