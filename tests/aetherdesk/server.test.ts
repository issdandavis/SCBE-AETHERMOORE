import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';
import * as http from 'http';
import { AddressInfo } from 'net';

// eslint-disable-next-line @typescript-eslint/no-require-imports
const aetherdesk = require('../../aetherdesk/server.js');

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const RECEIPTS_DIR = path.join(REPO_ROOT, 'artifacts', 'aetherdesk_receipts');

let server: http.Server;
let baseUrl: string;

function fetchJson(url: string, init?: RequestInit) {
  return fetch(url, init).then((r) => r.json().then((b) => ({ status: r.status, body: b })));
}

beforeEach(async () => {
  const app = aetherdesk.buildApp();
  await new Promise<void>((resolve) => {
    server = app.listen(0, '127.0.0.1', () => resolve());
  });
  const addr = server.address() as AddressInfo;
  baseUrl = `http://127.0.0.1:${addr.port}`;
});

afterEach(async () => {
  await new Promise<void>((resolve) => server.close(() => resolve()));
});

describe('AetherDesk server — health + introspection', () => {
  it('GET /api/health returns ok', async () => {
    const { status, body } = await fetchJson(`${baseUrl}/api/health`);
    expect(status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.schema).toBe('aetherdesk_health_v0');
  });

  it('GET /api/commands lists all five spec commands', async () => {
    const { status, body } = await fetchJson(`${baseUrl}/api/commands`);
    expect(status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.schema).toBe('aetherdesk_commands_v0');
    const ids = body.commands.map((c: { id: string }) => c.id).sort();
    expect(ids).toEqual([
      'benchmark_cli',
      'benchmark_coding_agents',
      'research_aether_lattice',
      'ts_tests',
      'typecheck',
    ]);
  });

  it('every command surface includes label, npm_script, risk_tier, description', async () => {
    const { body } = await fetchJson(`${baseUrl}/api/commands`);
    for (const c of body.commands) {
      expect(typeof c.label).toBe('string');
      expect(typeof c.npm_script).toBe('string');
      expect(typeof c.risk_tier).toBe('string');
      expect(typeof c.description).toBe('string');
      expect(c.label.length).toBeGreaterThan(0);
    }
  });
});

describe('AetherDesk server — allowlist enforcement (security boundary)', () => {
  it('POST /api/run/<known> resolves to a known command id without spawning', async () => {
    // We don't actually invoke runCommand here (it spawns npm). We verify
    // that the allowlist export contains exactly the spec's five entries.
    const ids = Object.keys(aetherdesk.COMMAND_ALLOWLIST).sort();
    expect(ids).toEqual([
      'benchmark_cli',
      'benchmark_coding_agents',
      'research_aether_lattice',
      'ts_tests',
      'typecheck',
    ]);
  });

  it('POST /api/run/<unknown> rejects with 400 and does not run anything', async () => {
    const { status, body } = await fetchJson(`${baseUrl}/api/run/rm_dash_rf`, { method: 'POST' });
    expect(status).toBe(400);
    expect(body.ok).toBe(false);
    expect(body.error).toMatch(/not allowlisted/i);
    expect(body.command_id).toBe('rm_dash_rf');
  });

  it('POST /api/run/<shell-injection-attempt> rejects with 400', async () => {
    const malicious = encodeURIComponent('typecheck; rm -rf /');
    const { status, body } = await fetchJson(`${baseUrl}/api/run/${malicious}`, { method: 'POST' });
    expect(status).toBe(400);
    expect(body.ok).toBe(false);
  });

  it('POST /api/run/<prototype-pollution-attempt> rejects with 400', async () => {
    // Object.prototype.hasOwnProperty test: __proto__ MUST NOT be treated
    // as an allowlisted command even though it lives on Object.prototype.
    const { status, body } = await fetchJson(`${baseUrl}/api/run/__proto__`, { method: 'POST' });
    expect(status).toBe(400);
    expect(body.ok).toBe(false);
  });
});

describe('AetherDesk server — receipt schema + listing', () => {
  it('buildReceipt produces an aetherdesk_receipt_v0 with the required fields', () => {
    const r = aetherdesk.buildReceipt({
      commandId: 'typecheck',
      exitCode: 0,
      stdoutTail: 'ok',
      stderrTail: '',
      startedAt: '2026-05-10T12:00:00.000Z',
      finishedAt: '2026-05-10T12:00:01.500Z',
      artifactPath: null,
    });
    expect(r.schema).toBe('aetherdesk_receipt_v0');
    expect(r.command_id).toBe('typecheck');
    expect(r.command).toBe('npm run typecheck');
    expect(r.command_digest).toMatch(/^[a-f0-9]{64}$/);
    expect(r.exit_code).toBe(0);
    expect(r.result).toBe('pass');
    expect(r.duration_ms).toBe(1500);
    expect(r.risk_tier).toBe('read-only');
    expect(r.allowed_paths).toEqual(['<repo-readonly>']);
    expect(r.task_id).toMatch(/_typecheck$/);
  });

  it('non-zero exit code maps to result=fail', () => {
    const r = aetherdesk.buildReceipt({
      commandId: 'typecheck',
      exitCode: 1,
      stdoutTail: '',
      stderrTail: 'TS2322 error',
      startedAt: '2026-05-10T12:00:00.000Z',
      finishedAt: '2026-05-10T12:00:00.500Z',
      artifactPath: null,
    });
    expect(r.exit_code).toBe(1);
    expect(r.result).toBe('fail');
  });

  it('GET /api/receipts returns a list bounded by limit', async () => {
    const { status, body } = await fetchJson(`${baseUrl}/api/receipts?limit=5`);
    expect(status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.schema).toBe('aetherdesk_receipt_list_v0');
    expect(Array.isArray(body.receipts)).toBe(true);
    expect(body.receipts.length).toBeLessThanOrEqual(5);
  });

  it('GET /api/receipts/<traversal-attempt> rejects', async () => {
    const malicious = encodeURIComponent('../../../etc/passwd');
    const { status, body } = await fetchJson(`${baseUrl}/api/receipts/${malicious}`);
    expect(status).toBe(404);
    expect(body.ok).toBe(false);
  });

  it('GET /api/receipts/<bad-name> rejects (no path traversal, only safe chars)', async () => {
    const { status } = await fetchJson(`${baseUrl}/api/receipts/some%2Fnested%2Ffile.json`);
    expect(status).toBe(404);
  });
});

describe('AetherDesk server — receipt round-trip on disk', () => {
  it('writeReceipt + listReceipts + readReceipt round-trips a receipt', () => {
    const r = aetherdesk.buildReceipt({
      commandId: 'typecheck',
      exitCode: 0,
      stdoutTail: 'all good',
      stderrTail: '',
      startedAt: '2026-05-10T12:00:00.000Z',
      finishedAt: '2026-05-10T12:00:00.250Z',
      artifactPath: null,
    });
    const filePath = aetherdesk.writeReceipt(r);
    expect(fs.existsSync(filePath)).toBe(true);

    const list = aetherdesk.listReceipts(50);
    const found = list.find((x: { task_id: string }) => x.task_id === r.task_id);
    expect(found).toBeTruthy();

    const file = path.basename(filePath);
    const readBack = aetherdesk.readReceipt(file);
    expect(readBack).toBeTruthy();
    expect(readBack.task_id).toBe(r.task_id);
    expect(readBack.command_digest).toBe(r.command_digest);

    // Cleanup
    fs.unlinkSync(filePath);
  });

  it('readReceipt rejects names with separators or traversal', () => {
    expect(aetherdesk.readReceipt('../etc/passwd')).toBeNull();
    expect(aetherdesk.readReceipt('foo/bar.json')).toBeNull();
    expect(aetherdesk.readReceipt('foo\\bar.json')).toBeNull();
  });
});

describe('AetherDesk server — output truncation', () => {
  it('tailBytes truncates oversized output and adds a marker', () => {
    const big = 'A'.repeat(20000);
    const tail = aetherdesk._private.tailBytes(big, 8192);
    expect(tail.length).toBeLessThan(big.length);
    expect(tail).toMatch(/truncated/);
    expect(tail.endsWith('A'.repeat(100))).toBe(true);
  });

  it('tailBytes leaves small output untouched', () => {
    const small = 'B'.repeat(100);
    expect(aetherdesk._private.tailBytes(small, 8192)).toBe(small);
  });
});

// Smoke marker: confirm the receipts dir is created on demand under artifacts/
describe('AetherDesk server — receipts directory', () => {
  it('RECEIPTS_DIR resolves under artifacts/', () => {
    expect(aetherdesk.RECEIPTS_DIR.replace(/\\/g, '/')).toMatch(/artifacts\/aetherdesk_receipts$/);
    expect(aetherdesk.RECEIPTS_DIR.startsWith(REPO_ROOT)).toBe(true);
    expect(RECEIPTS_DIR).toBe(aetherdesk.RECEIPTS_DIR);
  });
});

describe('AetherDesk server — Provider Status (v0.1)', () => {
  it('PROVIDER_DEFS includes the spec providers (ollama, lmstudio, hf, anthropic, openai)', () => {
    const ids = aetherdesk.PROVIDER_DEFS.map((p: { id: string }) => p.id);
    expect(ids).toEqual(
      expect.arrayContaining(['ollama', 'lmstudio', 'huggingface', 'anthropic', 'openai'])
    );
  });

  it('GET /api/providers returns the v0 schema and a result per provider', async () => {
    const { status, body } = await fetchJson(`${baseUrl}/api/providers`);
    expect(status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.schema).toBe('aetherdesk_providers_v0');
    expect(body.generated_at).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    expect(Array.isArray(body.providers)).toBe(true);
    expect(body.providers.length).toBe(aetherdesk.PROVIDER_DEFS.length);
    for (const p of body.providers) {
      expect(typeof p.id).toBe('string');
      expect(typeof p.label).toBe('string');
      expect(['local-http', 'env-var']).toContain(p.kind);
    }
  }, 10000);

  it('local-http providers report reachable + latency_ms (or an error)', async () => {
    const { body } = await fetchJson(`${baseUrl}/api/providers`);
    const httpProviders = body.providers.filter((p: { kind: string }) => p.kind === 'local-http');
    expect(httpProviders.length).toBeGreaterThan(0);
    for (const p of httpProviders) {
      expect(typeof p.reachable).toBe('boolean');
      expect(typeof p.latency_ms).toBe('number');
      expect(p.url).toMatch(/^http/);
      // We don't assert true/false reachable — depends on what's running locally.
    }
  }, 10000);

  it('env-var providers never expose secret values, only presence + name', async () => {
    const { body } = await fetchJson(`${baseUrl}/api/providers`);
    const envProviders = body.providers.filter((p: { kind: string }) => p.kind === 'env-var');
    expect(envProviders.length).toBeGreaterThan(0);
    for (const p of envProviders) {
      expect(typeof p.has_secret).toBe('boolean');
      expect(Array.isArray(p.env_vars_checked)).toBe(true);
      // The env_vars_checked is just NAMES, not values:
      for (const name of p.env_vars_checked) {
        expect(typeof name).toBe('string');
        // Sanity: shouldn't look like an API key
        expect(name).not.toMatch(/^sk-/);
        expect(name).not.toMatch(/^hf_/);
      }
      // secret_env_var is the matched name (or null), never the value
      if (p.has_secret) {
        expect(p.env_vars_checked).toContain(p.secret_env_var);
      } else {
        expect(p.secret_env_var).toBeNull();
      }
    }
  }, 10000);

  it('probeEnv detects truthy env vars and returns the matched name', () => {
    const KEY = '__AETHERDESK_TEST_KEY_' + Math.random().toString(36).slice(2);
    expect(aetherdesk.probeEnv([KEY])).toEqual({ has_secret: false, secret_env_var: null });
    process.env[KEY] = 'sentinel-value';
    try {
      const r = aetherdesk.probeEnv([KEY, 'OTHER_NAME']);
      expect(r.has_secret).toBe(true);
      expect(r.secret_env_var).toBe(KEY);
    } finally {
      delete process.env[KEY];
    }
  });

  it('probeEnv treats empty string as not-set', () => {
    const KEY = '__AETHERDESK_EMPTY_' + Math.random().toString(36).slice(2);
    process.env[KEY] = '';
    try {
      const r = aetherdesk.probeEnv([KEY]);
      expect(r.has_secret).toBe(false);
      expect(r.secret_env_var).toBeNull();
    } finally {
      delete process.env[KEY];
    }
  });
});
