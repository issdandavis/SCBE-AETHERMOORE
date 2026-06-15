import { describe, expect, it, vi } from 'vitest';
import governanceSubmit from '../netlify/functions/governance-submit';
import health from '../netlify/functions/health';
import systemManifest from '../netlify/functions/system-manifest';

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
    expect(body.endpoints.governanceSubmit).toBe('/api/governance/submit');
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
});
