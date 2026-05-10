/**
 * @file stripe_webhook_js.test.ts
 * Pins the contract for /v1/billing/stripe-webhook — Stripe receives
 * checkout.session.completed events here and a successful Snapshot
 * purchase fans out a polly_snapshot_paid repository_dispatch.
 *
 * The handler verifies HMAC-SHA256 of `${timestamp}.${raw_body}` against
 * STRIPE_WEBHOOK_SECRET. Tests construct that signature directly so we
 * never need the real `stripe` npm package as a dev dependency.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createHmac } from 'crypto';
import { EventEmitter } from 'events';

// eslint-disable-next-line @typescript-eslint/no-var-requires
const stripeWebhook = require('../../api/billing/stripe_webhook.js');

const TEST_SECRET = 'whsec_test_secret_xyz';
const SNAPSHOT_LINK_ID = 'plink_snapshot_test_42';

function setEnv(): void {
  process.env.STRIPE_WEBHOOK_SECRET = TEST_SECRET;
  process.env.STRIPE_SNAPSHOT_PAYMENT_LINK_ID = SNAPSHOT_LINK_ID;
  process.env.GITHUB_TOKEN = 'ghp_test_token';
  process.env.GITHUB_REPO = 'test-org/test-repo';
  process.env.POLLY_SNAPSHOT_DISPATCH_ENABLED = 'true';
}

function clearEnv(): void {
  delete process.env.STRIPE_WEBHOOK_SECRET;
  delete process.env.STRIPE_SNAPSHOT_PAYMENT_LINK_ID;
  delete process.env.GITHUB_TOKEN;
  delete process.env.GH_TOKEN;
  delete process.env.POLLY_TRAIN_GITHUB_TOKEN;
  delete process.env.GITHUB_REPO;
  delete process.env.POLLY_SNAPSHOT_DISPATCH_ENABLED;
}

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
    setHeader(k, v) {
      headers[k] = v;
    },
    status(code) {
      this.statusCode = code;
      return this;
    },
    json(payload) {
      this.body = payload;
      return this;
    },
    end() {
      return this;
    },
  };
}

interface MockReqOpts {
  method?: string;
  rawBody?: string;
  headers?: Record<string, string>;
}

function makeReq(opts: MockReqOpts): EventEmitter & {
  method: string;
  headers: Record<string, string>;
  destroy: () => void;
} {
  const req = new EventEmitter() as EventEmitter & {
    method: string;
    headers: Record<string, string>;
    destroy: () => void;
  };
  req.method = opts.method || 'POST';
  req.headers = opts.headers || {};
  req.destroy = () => undefined;
  // Schedule the body emit on next tick so the handler can attach listeners.
  if (opts.rawBody !== undefined) {
    setImmediate(() => {
      req.emit('data', Buffer.from(opts.rawBody as string, 'utf8'));
      req.emit('end');
    });
  } else if (opts.method !== 'OPTIONS' && opts.method !== 'GET') {
    setImmediate(() => req.emit('end'));
  }
  return req;
}

function signPayload(payload: string, secret: string, timestamp?: number): string {
  const ts = timestamp ?? Math.floor(Date.now() / 1000);
  const signedPayload = `${ts}.${payload}`;
  const sig = createHmac('sha256', secret).update(signedPayload, 'utf8').digest('hex');
  return `t=${ts},v1=${sig}`;
}

function snapshotEvent(overrides: Record<string, unknown> = {}): string {
  return JSON.stringify({
    id: 'evt_test_1',
    type: 'checkout.session.completed',
    data: {
      object: {
        id: 'cs_test_session_42',
        object: 'checkout.session',
        mode: 'payment',
        amount_total: 50000,
        currency: 'usd',
        payment_link: SNAPSHOT_LINK_ID,
        payment_intent: 'pi_test_42',
        customer: 'cus_test_42',
        customer_email: 'buyer@example.com',
        customer_details: {
          email: 'buyer@example.com',
          name: 'Buyer Name',
          phone: null,
        },
        livemode: false,
        created: 1715200000,
        ...overrides,
      },
    },
  });
}

describe('stripe webhook — signature verification', () => {
  beforeEach(() => {
    setEnv();
  });
  afterEach(() => {
    clearEnv();
    vi.restoreAllMocks();
  });

  it('valid signature → 200 and dispatch attempted', async () => {
    const fetchSpy = vi
      .spyOn(global, 'fetch')
      .mockResolvedValue(new Response('{}', { status: 200 }));
    const raw = snapshotEvent();
    const sig = signPayload(raw, TEST_SECRET);
    const req = makeReq({ rawBody: raw, headers: { 'stripe-signature': sig } });
    const res = makeRes();
    await stripeWebhook(req as never, res as never);
    expect(res.statusCode).toBe(200);
    const body = res.body as { ok: boolean; handled: string; dispatch: { ok: boolean } };
    expect(body.ok).toBe(true);
    expect(body.handled).toBe('snapshot_paid');
    expect(body.dispatch.ok).toBe(true);
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it('mismatched signature → 400', async () => {
    const raw = snapshotEvent();
    const badSig = signPayload(raw, 'wrong_secret');
    const req = makeReq({ rawBody: raw, headers: { 'stripe-signature': badSig } });
    const res = makeRes();
    await stripeWebhook(req as never, res as never);
    expect(res.statusCode).toBe(400);
    expect((res.body as { reason: string }).reason).toBe('signature_mismatch');
  });

  it('missing signature header → 400', async () => {
    const raw = snapshotEvent();
    const req = makeReq({ rawBody: raw, headers: {} });
    const res = makeRes();
    await stripeWebhook(req as never, res as never);
    expect(res.statusCode).toBe(400);
    expect((res.body as { reason: string }).reason).toMatch(/missing|malformed/);
  });

  it('replay-old timestamp → 400', async () => {
    const raw = snapshotEvent();
    const oldTs = Math.floor(Date.now() / 1000) - 600; // 10min ago, > 5min tolerance
    const sig = signPayload(raw, TEST_SECRET, oldTs);
    const req = makeReq({ rawBody: raw, headers: { 'stripe-signature': sig } });
    const res = makeRes();
    await stripeWebhook(req as never, res as never);
    expect(res.statusCode).toBe(400);
    expect((res.body as { reason: string }).reason).toBe('timestamp_outside_tolerance');
  });

  it('malformed signature header → 400', async () => {
    const raw = snapshotEvent();
    const req = makeReq({ rawBody: raw, headers: { 'stripe-signature': 'garbage' } });
    const res = makeRes();
    await stripeWebhook(req as never, res as never);
    expect(res.statusCode).toBe(400);
    expect((res.body as { reason: string }).reason).toMatch(/malformed/);
  });
});

describe('stripe webhook — drained stream regression', () => {
  // Vercel's @vercel/node body parser may drain the request stream before
  // the handler attaches data listeners. If that ever happens, raw becomes
  // "" and every signature would fail. We pin the contract: the handler
  // exports `config.api.bodyParser = false` so Vercel leaves the stream
  // alone. Without that flag, this scenario would produce silent prod
  // failures while the happy-path tests still pass.
  it('handler exports bodyParser:false to prevent silent stream drainage', () => {
    expect(stripeWebhook.config).toBeDefined();
    expect(stripeWebhook.config.api).toBeDefined();
    expect(stripeWebhook.config.api.bodyParser).toBe(false);
  });

  it('drained stream (no data, only end) → signature_mismatch (not silent 200)', async () => {
    setEnv();
    try {
      // Simulate the failure mode: Vercel parsed the body, drained the
      // stream, our raw read returns "". HMAC would then be over `${ts}.`
      // and never match a real Stripe signature.
      const realRaw = snapshotEvent();
      const realSig = signPayload(realRaw, TEST_SECRET);
      const req = makeReq({ headers: { 'stripe-signature': realSig } });
      // No rawBody — just method:POST. The makeReq helper for that case
      // emits 'end' with zero data chunks, mimicking the drained state.
      const res = makeRes();
      await stripeWebhook(req as never, res as never);
      // Must FAIL signature verification (not silently succeed). This is
      // the safety net — even if bodyParser:false is bypassed somehow,
      // we never accept a payload we can't verify.
      expect(res.statusCode).toBe(400);
      expect((res.body as { reason: string }).reason).toBe('signature_mismatch');
    } finally {
      clearEnv();
    }
  });
});

describe('stripe webhook — env guard', () => {
  beforeEach(() => clearEnv());
  afterEach(() => {
    clearEnv();
    vi.restoreAllMocks();
  });

  it('missing STRIPE_WEBHOOK_SECRET → 503 (refuse to silently accept)', async () => {
    const raw = snapshotEvent();
    // Without secret, the verify path can't even be exercised; the handler
    // must refuse rather than green-check unsigned events.
    const req = makeReq({ rawBody: raw, headers: { 'stripe-signature': 't=1,v1=x' } });
    const res = makeRes();
    await stripeWebhook(req as never, res as never);
    expect(res.statusCode).toBe(503);
  });
});

describe('stripe webhook — snapshot detection', () => {
  beforeEach(() => setEnv());
  afterEach(() => {
    clearEnv();
    vi.restoreAllMocks();
  });

  it('matches by payment_link id', () => {
    const { isSnapshotSession, snapshotConfig } = stripeWebhook._private;
    const cfg = snapshotConfig();
    expect(isSnapshotSession({ payment_link: SNAPSHOT_LINK_ID }, cfg)).toBe(true);
  });

  it('matches by amount + mode + currency when no payment_link match', () => {
    const { isSnapshotSession, snapshotConfig } = stripeWebhook._private;
    const cfg = snapshotConfig();
    expect(
      isSnapshotSession(
        { mode: 'payment', amount_total: 50000, currency: 'usd', payment_link: 'plink_other' },
        cfg
      )
    ).toBe(true);
  });

  it('rejects subscription mode even with $500 total', () => {
    const { isSnapshotSession, snapshotConfig } = stripeWebhook._private;
    const cfg = snapshotConfig();
    expect(
      isSnapshotSession({ mode: 'subscription', amount_total: 50000, currency: 'usd' }, cfg)
    ).toBe(false);
  });

  it('rejects mismatched amount', () => {
    const { isSnapshotSession, snapshotConfig } = stripeWebhook._private;
    const cfg = snapshotConfig();
    expect(isSnapshotSession({ mode: 'payment', amount_total: 12900, currency: 'usd' }, cfg)).toBe(
      false
    );
  });
});

describe('stripe webhook — event routing', () => {
  beforeEach(() => setEnv());
  afterEach(() => {
    clearEnv();
    vi.restoreAllMocks();
  });

  it('non-snapshot checkout completes → 200, no dispatch', async () => {
    const fetchSpy = vi
      .spyOn(global, 'fetch')
      .mockResolvedValue(new Response('{}', { status: 200 }));
    const raw = snapshotEvent({
      payment_link: 'plink_unrelated',
      amount_total: 12900,
      mode: 'payment',
    });
    const sig = signPayload(raw, TEST_SECRET);
    const req = makeReq({ rawBody: raw, headers: { 'stripe-signature': sig } });
    const res = makeRes();
    await stripeWebhook(req as never, res as never);
    expect(res.statusCode).toBe(200);
    expect((res.body as { handled: string }).handled).toBe('checkout_other');
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('unrelated event type → 200 ignored, no dispatch', async () => {
    const fetchSpy = vi
      .spyOn(global, 'fetch')
      .mockResolvedValue(new Response('{}', { status: 200 }));
    const raw = JSON.stringify({
      id: 'evt_test_2',
      type: 'invoice.paid',
      data: { object: {} },
    });
    const sig = signPayload(raw, TEST_SECRET);
    const req = makeReq({ rawBody: raw, headers: { 'stripe-signature': sig } });
    const res = makeRes();
    await stripeWebhook(req as never, res as never);
    expect(res.statusCode).toBe(200);
    expect((res.body as { handled: string }).handled).toBe('ignored');
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('GET → 405', async () => {
    const req = makeReq({ method: 'GET' });
    const res = makeRes();
    await stripeWebhook(req as never, res as never);
    expect(res.statusCode).toBe(405);
  });

  it('OPTIONS → 204', async () => {
    const req = makeReq({ method: 'OPTIONS' });
    const res = makeRes();
    await stripeWebhook(req as never, res as never);
    expect(res.statusCode).toBe(204);
  });

  it('dispatch payload contains buyer email + session id + snapshot source tag', async () => {
    let capturedBody: string | undefined;
    vi.spyOn(global, 'fetch').mockImplementation(async (_url, init) => {
      capturedBody = (init as { body: string }).body;
      return new Response('{}', { status: 200 });
    });
    const raw = snapshotEvent();
    const sig = signPayload(raw, TEST_SECRET);
    const req = makeReq({ rawBody: raw, headers: { 'stripe-signature': sig } });
    const res = makeRes();
    await stripeWebhook(req as never, res as never);
    expect(capturedBody).toBeDefined();
    const dispatched = JSON.parse(capturedBody as string);
    expect(dispatched.event_type).toBe('polly_snapshot_paid');
    const rec = dispatched.client_payload.record;
    expect(rec.session_id).toBe('cs_test_session_42');
    expect(rec.contact_email).toBe('buyer@example.com');
    expect(rec.amount_total).toBe(50000);
    expect(rec.source).toBe('governance-snapshot');
  });
});
