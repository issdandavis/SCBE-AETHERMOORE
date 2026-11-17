import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// eslint-disable-next-line @typescript-eslint/no-var-requires
const download = require('../../api/agent/download.js');

const TOOLKIT_LINK_ID = 'plink_toolkit_test';

interface MockRes {
  statusCode: number;
  headers: Record<string, string>;
  body: unknown;
  setHeader(key: string, value: string): void;
  status(code: number): MockRes;
  json(payload: unknown): MockRes;
  send(payload: unknown): MockRes;
  end(): MockRes;
}

function makeRes(): MockRes {
  return {
    statusCode: 200,
    headers: {},
    body: undefined,
    setHeader(key, value) {
      this.headers[key] = value;
    },
    status(code) {
      this.statusCode = code;
      return this;
    },
    json(payload) {
      this.body = payload;
      return this;
    },
    send(payload) {
      this.body = payload;
      return this;
    },
    end() {
      return this;
    },
  };
}

function makeReq(url: string, method = 'GET') {
  return { method, url, headers: {} };
}

function paidSession(overrides: Record<string, unknown> = {}) {
  return {
    id: 'cs_test_paid123',
    object: 'checkout.session',
    mode: 'payment',
    status: 'complete',
    payment_status: 'paid',
    payment_link: TOOLKIT_LINK_ID,
    metadata: { scbe_product: 'toolkit' },
    ...overrides,
  };
}

function setEnv(): void {
  process.env.STRIPE_DELIVERY_RESTRICTED_KEY = 'rk_test_delivery';
  process.env.STRIPE_TOOLKIT_PAYMENT_LINK_ID = TOOLKIT_LINK_ID;
  process.env.SCBE_TOOLKIT_BLOB_URL = 'https://blob.example/toolkit.zip';
  process.env.BLOB_READ_WRITE_TOKEN = 'blob_test_token';
}

function clearEnv(): void {
  delete process.env.STRIPE_DELIVERY_RESTRICTED_KEY;
  delete process.env.STRIPE_SECRET_KEY;
  delete process.env.STRIPE_TOOLKIT_PAYMENT_LINK_ID;
  delete process.env.STRIPE_VAULT_PAYMENT_LINK_ID;
  delete process.env.STRIPE_MAKING_OF_PAYMENT_LINK_ID;
  delete process.env.SCBE_TOOLKIT_BLOB_URL;
  delete process.env.SCBE_VAULT_BLOB_URL;
  delete process.env.SCBE_MAKING_OF_BLOB_URL;
  delete process.env.BLOB_READ_WRITE_TOKEN;
}

describe('paid digital download', () => {
  beforeEach(setEnv);
  afterEach(() => {
    clearEnv();
    vi.restoreAllMocks();
  });

  it('rejects a request without a checkout session', async () => {
    const fetchSpy = vi.spyOn(global, 'fetch');
    const res = makeRes();
    await download(makeReq('/api/agent/download?product=toolkit') as never, res as never);
    expect(res.statusCode).toBe(400);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('fails closed when Stripe verification is not configured', async () => {
    delete process.env.STRIPE_DELIVERY_RESTRICTED_KEY;
    const res = makeRes();
    await download(
      makeReq('/api/agent/download?session_id=cs_test_paid123') as never,
      res as never
    );
    expect(res.statusCode).toBe(503);
  });

  it('rejects an unknown checkout session', async () => {
    vi.spyOn(global, 'fetch').mockResolvedValue(new Response('{}', { status: 404 }));
    const res = makeRes();
    await download(
      makeReq('/api/agent/download?session_id=cs_test_missing123') as never,
      res as never
    );
    expect(res.statusCode).toBe(401);
  });

  it('rejects a complete session whose payment is still unpaid', async () => {
    const fetchSpy = vi
      .spyOn(global, 'fetch')
      .mockResolvedValueOnce(
        Response.json(paidSession({ payment_status: 'unpaid' }), { status: 200 })
      );
    const res = makeRes();
    await download(
      makeReq('/api/agent/download?session_id=cs_test_unpaid123') as never,
      res as never
    );
    expect(res.statusCode).toBe(402);
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it('rejects a paid checkout for a different requested product', async () => {
    const fetchSpy = vi
      .spyOn(global, 'fetch')
      .mockResolvedValueOnce(Response.json(paidSession(), { status: 200 }));
    const res = makeRes();
    await download(
      makeReq('/api/agent/download?session_id=cs_test_paid123&product=vault') as never,
      res as never
    );
    expect(res.statusCode).toBe(403);
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it('rejects a paid checkout that is not mapped to a digital product', async () => {
    const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValueOnce(
      Response.json(paidSession({ payment_link: 'plink_unrelated', metadata: {} }), {
        status: 200,
      })
    );
    const res = makeRes();
    await download(
      makeReq('/api/agent/download?session_id=cs_test_paid123') as never,
      res as never
    );
    expect(res.statusCode).toBe(403);
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it('streams only the product attached to a paid checkout session', async () => {
    const fetchSpy = vi
      .spyOn(global, 'fetch')
      .mockResolvedValueOnce(Response.json(paidSession(), { status: 200 }))
      .mockResolvedValueOnce(
        new Response(Buffer.from('zip-bytes'), {
          status: 200,
          headers: { 'content-type': 'application/zip' },
        })
      );
    const res = makeRes();
    await download(
      makeReq('/api/agent/download?session_id=cs_test_paid123&product=toolkit') as never,
      res as never
    );

    expect(res.statusCode).toBe(200);
    expect(fetchSpy).toHaveBeenCalledTimes(2);
    expect(String(fetchSpy.mock.calls[0][0])).toContain('/checkout/sessions/cs_test_paid123');
    expect(fetchSpy.mock.calls[1][0]).toBe('https://blob.example/toolkit.zip');
    expect(res.headers['Content-Disposition']).toContain('SCBE_AI_Governance_Toolkit_v1.zip');
    expect(res.headers['Cache-Control']).toBe('private, no-store');
    expect(res.headers['Referrer-Policy']).toBe('no-referrer');
    expect(Buffer.isBuffer(res.body)).toBe(true);
  });
});
