import { beforeEach, describe, expect, it, vi } from 'vitest';
import governanceReceipt from '../netlify/functions/governance-receipt';
import governanceRollup from '../netlify/functions/governance-rollup';
import governanceSubmit from '../netlify/functions/governance-submit';
import governanceSelftest from '../netlify/functions/governance-selftest';
import governanceWorker from '../netlify/functions/governance-worker-background';
import health from '../netlify/functions/health';
import systemManifest from '../netlify/functions/system-manifest';

const blobMock = vi.hoisted(() => {
  const data = new Map<string, { value: unknown; metadata?: Record<string, string> }>();
  const store = {
    setJSON: vi.fn(
      async (key: string, value: unknown, options?: { metadata?: Record<string, string> }) => {
        data.set(key, { value, metadata: options?.metadata });
      }
    ),
    get: vi.fn(async (key: string, options?: { type?: string }) => {
      const record = data.get(key);
      if (!record) {
        return null;
      }
      return options?.type === 'json' ? record.value : JSON.stringify(record.value);
    }),
    list: vi.fn(async (options?: { prefix?: string }) => ({
      blobs: Array.from(data.keys())
        .filter((key) => !options?.prefix || key.startsWith(options.prefix))
        .sort()
        .map((key) => ({ key, etag: `etag-${key}` })),
      directories: [],
    })),
    delete: vi.fn(async (key: string) => {
      data.delete(key);
    }),
  };

  return {
    data,
    getStore: vi.fn(() => store),
  };
});

vi.mock('@netlify/blobs', () => ({
  getStore: blobMock.getStore,
}));

const context = {
  requestId: 'req_test',
  waitUntil: vi.fn(),
  deploy: { context: 'dev', id: 'deploy_test', published: false },
  site: { id: 'site_test', name: 'scbe-test', url: 'https://example.netlify.app' },
  geo: {
    city: 'Test City',
    country: { code: 'US', name: 'United States' },
    timezone: 'America/Los_Angeles',
  },
} as any;

describe('Netlify functions', () => {
  beforeEach(() => {
    blobMock.data.clear();
    vi.clearAllMocks();
  });

  it('returns API health', async () => {
    const res = await health(new Request('https://example.com/api/health'), context);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.service).toBe('scbe-aethermoore');
  });

  it('returns a system manifest', async () => {
    const res = await systemManifest(
      new Request('https://example.com/api/system/manifest'),
      context
    );
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.capabilities).toContain('governance-submit');
    expect(body.capabilities).toContain('governance-receipts');
    expect(body.endpoints.governanceSubmit).toBe('/api/governance/submit');
    expect(body.endpoints.governanceReceipt).toBe('/api/governance/receipts/:receipt');
    expect(body.endpoints.governanceSelftest).toBe('/api/governance/selftest');
    expect(body.endpoints.governanceWorker).toBe('/api/governance/process');
  });

  it('accepts governance submissions with deterministic receipts', async () => {
    const req = new Request('https://example.com/api/governance/submit', {
      method: 'POST',
      body: JSON.stringify({
        intent: 'run chemistry tokenizer preflight',
        source: 'test',
        metadata: { b: 2, a: 1 },
      }),
    });

    const first = await governanceSubmit(req, context);
    const firstBody = await first.json();
    const second = await governanceSubmit(
      new Request('https://example.com/api/governance/submit', {
        method: 'POST',
        body: JSON.stringify({
          metadata: { a: 1, b: 2 },
          source: 'test',
          intent: 'run chemistry tokenizer preflight',
        }),
      }),
      context
    );
    const secondBody = await second.json();

    expect(first.status).toBe(202);
    expect(firstBody.decision).toBe('queued');
    expect(firstBody.receipt).toMatch(/^[a-f0-9]{64}$/);
    expect(firstBody.receipt).toBe(secondBody.receipt);
    expect(firstBody.storageKey).toMatch(
      new RegExp(`^receipts/\\d{4}-\\d{2}-\\d{2}/${firstBody.receipt}\\.json$`)
    );
  });

  it('stores and returns a governance receipt record', async () => {
    const submit = await governanceSubmit(
      new Request('https://example.com/api/governance/submit', {
        method: 'POST',
        body: JSON.stringify({
          intent: 'persist receipt in blobs',
          source: 'vitest',
          metadata: { subsystem: 'netlify' },
        }),
      }),
      context
    );
    const submitBody = await submit.json();

    const res = await governanceReceipt(
      new Request(`https://example.com/api/governance/receipts/${submitBody.receipt}`)
    );
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.record.receipt).toBe(submitBody.receipt);
    expect(body.record.status).toBe('queued');
    expect(body.record.payload.intent).toBe('persist receipt in blobs');
    expect(body.record.netlify.siteId).toBe('site_test');
  });

  it('returns 404 for missing governance receipts', async () => {
    const res = await governanceReceipt(
      new Request(
        'https://example.com/api/governance/receipts/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
      )
    );
    const body = await res.json();

    expect(res.status).toBe(404);
    expect(body.error).toBe('receipt_not_found');
  });

  it('rejects empty governance submissions', async () => {
    const res = await governanceSubmit(
      new Request('https://example.com/api/governance/submit', {
        method: 'POST',
        body: JSON.stringify({ intent: '' }),
      }),
      context
    );
    const body = await res.json();

    expect(res.status).toBe(422);
    expect(body.error).toBe('invalid_payload');
  });

  it('runs a governance selftest', async () => {
    const res = await governanceSelftest(
      new Request('https://example.com/api/governance/selftest'),
      context
    );
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.checks.receiptHex64).toBe(true);
    expect(body.receipt).toMatch(/^[a-f0-9]{64}$/);
  });

  it('writes a daily governance rollup from stored receipts', async () => {
    const log = vi.spyOn(console, 'log').mockImplementation(() => undefined);
    const submitted = await governanceSubmit(
      new Request('https://example.com/api/governance/submit', {
        method: 'POST',
        body: JSON.stringify({ intent: 'daily rollup receipt', source: 'test' }),
      }),
      context
    );
    const submitBody = await submitted.json();

    const res = await governanceRollup(
      new Request('https://example.com/.netlify/functions/governance-rollup'),
      context
    );

    expect(res).toBeUndefined();
    expect(log).toHaveBeenCalledWith(
      'governance_rollup_written',
      expect.objectContaining({
        requestId: 'req_test',
        receiptCount: 1,
      })
    );
    expect(
      Array.from(blobMock.data.values()).some((record) => {
        const value = record.value as { receipts?: string[] };
        return value.receipts?.includes(submitBody.receipt);
      })
    ).toBe(true);
    log.mockRestore();
  });

  it('processes background governance payloads without returning a body', async () => {
    const log = vi.spyOn(console, 'log').mockImplementation(() => undefined);
    const res = await governanceWorker(
      new Request('https://example.com/api/governance/process', {
        method: 'POST',
        body: JSON.stringify({ intent: 'background receipt test', source: 'test' }),
      }),
      context
    );

    expect(res).toBeUndefined();
    expect(log).toHaveBeenCalledWith(
      'governance_worker_processed',
      expect.objectContaining({
        requestId: 'req_test',
        source: 'test',
      })
    );
    log.mockRestore();
  });
});
