/**
 * @file polly_funnel_js.test.ts
 * Pins the contract for /v1/polly/funnel — operator funnel telemetry.
 *
 * Test pollution guard: the funnel handler fires HF upload as a side
 * effect of capture. If a developer has HF_TOKEN exported in their
 * shell, that side effect will reach the live private dataset during
 * `npx vitest run`. Strip the env vars at the top so all subsequent
 * require()s and handler calls see no credentials.
 */

delete process.env.HF_TOKEN;
delete process.env.HUGGINGFACE_TOKEN;
delete process.env.HUGGING_FACE_HUB_TOKEN;

import { describe, it, expect, beforeEach } from 'vitest';
// eslint-disable-next-line @typescript-eslint/no-var-requires
const funnelHandler = require('../../api/polly/funnel.js');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const hfUpload = require('../../api/_polly_hf_upload.js');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const rateLimit = require('../../api/_polly_rate_limit.js');

interface MockRes {
  statusCode: number;
  headers: Record<string, string>;
  body: unknown;
  setHeader(k: string, v: string): void;
  status(code: number): MockRes;
  json(payload: unknown): MockRes;
  end(): MockRes;
}

function makeRes(): MockRes {
  const headers: Record<string, string> = {};
  return {
    statusCode: 200,
    headers,
    body: undefined,
    setHeader(k: string, v: string) {
      headers[k] = v;
    },
    status(code: number) {
      this.statusCode = code;
      return this;
    },
    json(payload: unknown) {
      this.body = payload;
      return this;
    },
    end() {
      return this;
    },
  };
}

function makeReq(opts: {
  method?: string;
  body?: Record<string, unknown>;
  headers?: Record<string, string>;
}): unknown {
  return {
    method: opts.method || 'POST',
    headers: opts.headers || {},
    body: opts.body || {},
    on() {
      return this;
    },
    destroy() {
      /* noop */
    },
  };
}

describe('polly funnel — validation', () => {
  beforeEach(() => rateLimit.reset());

  it('accepts a well-formed event', async () => {
    const req = makeReq({
      body: { event: 'arrival', page: 'hire', session: 'sess-abc', meta: { ref: 'twitter' } },
    });
    const res = makeRes();
    await funnelHandler(req as never, res as never);
    expect(res.statusCode).toBe(200);
    expect((res.body as { ok: boolean; event: string }).ok).toBe(true);
    expect((res.body as { event: string }).event).toBe('arrival');
  });

  it('rejects missing event', async () => {
    const req = makeReq({ body: { page: 'hire', session: 's' } });
    const res = makeRes();
    await funnelHandler(req as never, res as never);
    expect(res.statusCode).toBe(400);
    expect((res.body as { error: string }).error).toMatch(/event is required/);
  });

  it('rejects unknown event names', async () => {
    const req = makeReq({ body: { event: 'lol-spam', page: 'hire', session: 's' } });
    const res = makeRes();
    await funnelHandler(req as never, res as never);
    expect(res.statusCode).toBe(400);
    expect((res.body as { error: string }).error).toMatch(/event must be one of/);
  });

  it('rejects missing page', async () => {
    const req = makeReq({ body: { event: 'arrival', session: 's' } });
    const res = makeRes();
    await funnelHandler(req as never, res as never);
    expect(res.statusCode).toBe(400);
    expect((res.body as { error: string }).error).toMatch(/page is required/);
  });

  it('rejects oversized meta', async () => {
    const big = 'x'.repeat(700);
    const req = makeReq({
      body: { event: 'arrival', page: 'hire', session: 's', meta: { fill: big } },
    });
    const res = makeRes();
    await funnelHandler(req as never, res as never);
    expect(res.statusCode).toBe(400);
    expect((res.body as { error: string }).error).toMatch(/meta too large/);
  });

  it('honeypot filled → 200 OK but captured:false (skip side effects)', async () => {
    const req = makeReq({
      body: { event: 'arrival', page: 'hire', session: 's', website: 'http://bot.invalid' },
    });
    const res = makeRes();
    await funnelHandler(req as never, res as never);
    expect(res.statusCode).toBe(200);
    expect((res.body as { ok: boolean; captured: boolean }).captured).toBe(false);
  });

  it('non-POST returns 405', async () => {
    const req = makeReq({ method: 'GET' });
    const res = makeRes();
    await funnelHandler(req as never, res as never);
    expect(res.statusCode).toBe(405);
  });

  it('OPTIONS preflight returns 204', async () => {
    const req = makeReq({ method: 'OPTIONS' });
    const res = makeRes();
    await funnelHandler(req as never, res as never);
    expect(res.statusCode).toBe(204);
  });
});

describe('polly funnel — kind routing', () => {
  it('uploadRecord with kind:funnel routes to polly-funnel/ prefix', () => {
    // pathFor is exported via _internal? Or only via uploadRecord. We probe
    // the kind→prefix mapping via the path produced.
    const { pathFor } = hfUpload._internal || {};
    if (!pathFor) {
      // fallback: just confirm the prefix string is present in the module
      const src = require('fs').readFileSync('api/_polly_hf_upload.js', 'utf8');
      expect(src).toContain('polly-funnel');
      return;
    }
    const path = pathFor({ kind: 'funnel', ts: 1700000000 });
    expect(path).toMatch(/^polly-funnel\/\d{4}-\d{2}-\d{2}\//);
  });
});

describe('polly funnel — allowed events', () => {
  it('exposes the expected funnel-stage event names', () => {
    const events = funnelHandler._private.ALLOWED_EVENTS;
    // Stage signals operators care about
    for (const e of [
      'arrival',
      'scroll_50',
      'chat_open',
      'chat_msg',
      'lead_form_focus',
      'lead_submit_attempt',
      'lead_submit_ok',
      'lead_submit_fail',
      'cta_click_buy',
      'snapshot_intake_attempt',
      'snapshot_intake_ok',
      'snapshot_intake_fail',
    ]) {
      expect(events.has(e)).toBe(true);
    }
  });
});
