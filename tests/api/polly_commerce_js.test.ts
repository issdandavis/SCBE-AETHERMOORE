/**
 * @file polly_commerce_js.test.ts
 * Tests the JS Vercel-side port of polly commerce intent classification.
 * Mirrors the Python parity tests in test_polly_commerce.py.
 */

import { describe, it, expect } from 'vitest';
// eslint-disable-next-line @typescript-eslint/no-var-requires
const commerce = require('../../api/polly/commerce.js');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const chatHandler = require('../../api/polly/chat.js');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const feedbackHandler = require('../../api/polly/feedback.js');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const catalogHandler = require('../../api/polly/catalog.js');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const trainCapture = require('../../api/_polly_train_capture.js');

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
  const res: MockRes = {
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
  return res;
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

describe('polly commerce intent classification', () => {
  it('catalog has three live products with valid stripe/kofi urls', () => {
    expect(commerce.PRODUCT_CATALOG).toHaveLength(3);
    for (const product of commerce.PRODUCT_CATALOG) {
      expect(product.checkoutUrl).toMatch(/^https:\/\/(buy\.stripe\.com|ko-fi\.com)/);
      expect(product.keywords.length).toBeGreaterThan(0);
    }
  });

  it('classifies "buy" verb with bound product at 0.95 confidence', () => {
    const intent = commerce.classifyIntent('I want to buy the AI governance toolkit');
    expect(intent.name).toBe('buy');
    expect(intent.confidence).toBeGreaterThanOrEqual(0.95);
    expect(intent.product).not.toBeNull();
    expect(intent.product.sku).toBe('ai-governance-toolkit');
  });

  it('classifies bare product keyword as buy at 0.6', () => {
    const intent = commerce.classifyIntent('Tell me about the training vault');
    expect(intent.name).toBe('buy');
    expect(intent.confidence).toBeCloseTo(0.6, 2);
    expect(intent.product.sku).toBe('ai-security-training-vault');
  });

  it('classifies custom intent at 0.85', () => {
    const intent = commerce.classifyIntent('I need a custom audit for my team');
    expect(intent.name).toBe('custom');
    expect(intent.confidence).toBeGreaterThanOrEqual(0.85);
  });

  it('classifies membership intent at 0.75', () => {
    const intent = commerce.classifyIntent('How do I subscribe to the newsletter?');
    expect(intent.name).toBe('membership');
  });

  it('returns general intent when nothing matches', () => {
    const intent = commerce.classifyIntent('What is the weather today?');
    expect(intent.name).toBe('general');
    expect(intent.confidence).toBe(0);
  });

  it('handles empty input safely', () => {
    expect(commerce.classifyIntent('').name).toBe('general');
    expect(commerce.classifyIntent(null as unknown as string).name).toBe('general');
  });
});

describe('polly commerce reply rendering', () => {
  it('renderBuyReply with product returns checkout url in actions', () => {
    const product = commerce.PRODUCT_CATALOG[0];
    const out = commerce.renderBuyReply(product);
    expect(out.text).toContain(product.name);
    expect(out.text).toContain(product.checkoutUrl);
    expect(out.actions[0].url).toBe(product.checkoutUrl);
  });

  it('renderBuyReply with null lists all 3 products', () => {
    const out = commerce.renderBuyReply(null);
    expect(out.actions).toHaveLength(3);
    for (const action of out.actions) {
      expect(action.url).toMatch(/^https:\/\//);
    }
  });

  it('renderCustomReply returns mailto with pre-filled context', () => {
    const out = commerce.renderCustomReply('We need governance for our finance LLM');
    const mailtoAction = out.actions.find((a: { url: string }) => a.url.startsWith('mailto:'));
    expect(mailtoAction).toBeDefined();
    expect(mailtoAction!.url).toContain('issdandavis7795@gmail.com');
    expect(mailtoAction!.url).toContain('finance');
  });

  it('renderMembershipReply has Ko-fi + GitHub + email actions', () => {
    const out = commerce.renderMembershipReply();
    expect(out.actions).toHaveLength(3);
    expect(out.actions[0].url).toContain('ko-fi.com');
    expect(out.actions[1].url).toContain('github.com');
    expect(out.actions[2].url).toContain('mailto:');
  });
});

describe('polly chat handler — commerce path', () => {
  it('returns Stripe link when buy intent + product matches', async () => {
    const req = makeReq({
      body: { message: 'I want to buy the AI governance toolkit', consent_to_train: false },
    });
    const res = makeRes();
    await chatHandler(req, res);
    expect(res.statusCode).toBe(200);
    const body = res.body as {
      ok: boolean;
      provider: string;
      intent: string;
      actions: { url: string }[];
    };
    expect(body.ok).toBe(true);
    expect(body.provider).toBe('commerce');
    expect(body.intent).toBe('buy');
    expect(body.actions[0].url).toContain('buy.stripe.com');
  });

  it('returns mailto + hire url for custom intent', async () => {
    const req = makeReq({
      body: {
        message: 'I need a custom governance overlay for my company',
        consent_to_train: false,
      },
    });
    const res = makeRes();
    await chatHandler(req, res);
    const body = res.body as { intent: string; actions: { url: string }[] };
    expect(body.intent).toBe('custom');
    expect(body.actions.some((a) => a.url.startsWith('mailto:'))).toBe(true);
    expect(body.actions.some((a) => a.url.includes('aethermoore.com/hire'))).toBe(true);
  });

  it('rejects POST without message', async () => {
    const req = makeReq({ body: {} });
    const res = makeRes();
    await chatHandler(req, res);
    expect(res.statusCode).toBe(400);
  });

  it('rejects non-POST methods', async () => {
    const req = makeReq({ method: 'GET' });
    const res = makeRes();
    await chatHandler(req, res);
    expect(res.statusCode).toBe(405);
  });

  it('handles OPTIONS for CORS preflight', async () => {
    const req = makeReq({ method: 'OPTIONS' });
    const res = makeRes();
    await chatHandler(req, res);
    expect(res.statusCode).toBe(204);
  });
});

describe('polly feedback handler', () => {
  it('captures up rating', async () => {
    const req = makeReq({
      body: { rating: 'up', user_message: 'hi', assistant_reply: 'hello', session_id: 'test-1' },
    });
    const res = makeRes();
    await feedbackHandler(req, res);
    expect(res.statusCode).toBe(200);
    const body = res.body as { ok: boolean; rating: string };
    expect(body.ok).toBe(true);
    expect(body.rating).toBe('up');
  });

  it('rejects invalid rating', async () => {
    const req = makeReq({ body: { rating: 'maybe' } });
    const res = makeRes();
    await feedbackHandler(req, res);
    expect(res.statusCode).toBe(400);
  });
});

describe('polly catalog handler', () => {
  it('returns the product catalog over GET', async () => {
    const req = makeReq({ method: 'GET' });
    const res = makeRes();
    await catalogHandler(req, res);
    expect(res.statusCode).toBe(200);
    const body = res.body as { ok: boolean; products: unknown[]; consulting_tiers: unknown[] };
    expect(body.ok).toBe(true);
    expect(body.products).toHaveLength(3);
    expect(body.consulting_tiers.length).toBeGreaterThan(0);
  });

  it('rejects POST', async () => {
    const req = makeReq({ method: 'POST' });
    const res = makeRes();
    await catalogHandler(req, res);
    expect(res.statusCode).toBe(405);
  });
});

describe('polly training capture (repository_dispatch)', () => {
  it('returns no_token when GITHUB_TOKEN not set', async () => {
    const original = {
      gh: process.env.GITHUB_TOKEN,
      gh2: process.env.GH_TOKEN,
      polly: process.env.POLLY_TRAIN_GITHUB_TOKEN,
    };
    delete process.env.GITHUB_TOKEN;
    delete process.env.GH_TOKEN;
    delete process.env.POLLY_TRAIN_GITHUB_TOKEN;
    try {
      const result = await trainCapture.dispatchTrainingTurn({ ts: 1, user: 'x', assistant: 'y' });
      expect(result.ok).toBe(false);
      expect(result.reason).toBe('no_token');
    } finally {
      if (original.gh) process.env.GITHUB_TOKEN = original.gh;
      if (original.gh2) process.env.GH_TOKEN = original.gh2;
      if (original.polly) process.env.POLLY_TRAIN_GITHUB_TOKEN = original.polly;
    }
  });

  it('returns disabled when env opt-out is set', async () => {
    const originalDisable = process.env.POLLY_TRAIN_DISPATCH_ENABLED;
    process.env.POLLY_TRAIN_DISPATCH_ENABLED = 'false';
    try {
      const result = await trainCapture.dispatchTrainingTurn({ ts: 1 });
      expect(result.ok).toBe(false);
      expect(result.reason).toBe('disabled');
    } finally {
      if (originalDisable === undefined) delete process.env.POLLY_TRAIN_DISPATCH_ENABLED;
      else process.env.POLLY_TRAIN_DISPATCH_ENABLED = originalDisable;
    }
  });

  it('exports the canonical event type so the workflow listens correctly', () => {
    expect(trainCapture.EVENT_TYPE).toBe('polly_training_turn');
  });
});
