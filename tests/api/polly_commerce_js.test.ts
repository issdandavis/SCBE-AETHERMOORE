/**
 * @file polly_commerce_js.test.ts
 * Tests the JS Vercel-side port of polly commerce intent classification.
 * Mirrors the Python parity tests in test_polly_commerce.py.
 *
 * Test pollution guard: the lead + chat handlers fire HF upload + GitHub
 * dispatch as side effects of capture. If a developer has HF_TOKEN /
 * GITHUB_TOKEN exported in their shell, those side effects will reach the
 * live private dataset during `npx vitest run`. Strip the env vars at the
 * very top of the module so all subsequent require()s and handler calls
 * see no credentials and short-circuit with no_token.
 */

delete process.env.HF_TOKEN;
delete process.env.HUGGINGFACE_TOKEN;
delete process.env.HUGGING_FACE_HUB_TOKEN;
delete process.env.POLLY_TRAIN_GITHUB_TOKEN;
delete process.env.GITHUB_TOKEN;
delete process.env.GH_TOKEN;

import { describe, it, expect, beforeEach } from 'vitest';
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
// eslint-disable-next-line @typescript-eslint/no-var-requires
const leadHandler = require('../../api/polly/lead.js');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const hostedRunHandler = require('../../api/polly/hosted-run.js');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const hfUpload = require('../../api/_polly_hf_upload.js');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const rateLimit = require('../../api/_polly_rate_limit.js');

function loadCommerceWithEnv(env: Record<string, string>) {
  const modulePath = require.resolve('../../api/polly/commerce.js');
  const original: Record<string, string | undefined> = {};
  for (const [key, value] of Object.entries(env)) {
    original[key] = process.env[key];
    process.env[key] = value;
  }
  delete require.cache[modulePath];
  const loaded = require('../../api/polly/commerce.js');
  for (const key of Object.keys(env)) {
    if (original[key] === undefined) {
      delete process.env[key];
    } else {
      process.env[key] = original[key];
    }
  }
  delete require.cache[modulePath];
  require('../../api/polly/commerce.js');
  return loaded;
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

describe('polly rate limiter', () => {
  it('allows requests under the limit and blocks beyond it', () => {
    rateLimit.reset();
    const ip = '203.0.113.42';
    const req = { headers: { 'x-forwarded-for': ip } };
    const res = makeRes();
    // chat default: 30/min — fire 30 requests, 31st should be blocked
    for (let i = 0; i < 30; i += 1) {
      const result = rateLimit.enforce(req, res, 'chat');
      expect(result.allowed).toBe(true);
    }
    const blocked = rateLimit.enforce(req, res, 'chat');
    expect(blocked.allowed).toBe(false);
    expect(blocked.retryAfterMs).toBeGreaterThan(0);
    expect(res.statusCode).toBe(200); // headers set, status not changed by enforce
  });

  it('isolates per-IP buckets so one abuser does not block another', () => {
    rateLimit.reset();
    const abuserReq = { headers: { 'x-forwarded-for': '198.51.100.1' } };
    const cleanReq = { headers: { 'x-forwarded-for': '198.51.100.2' } };
    const res = makeRes();
    for (let i = 0; i < 5; i += 1) rateLimit.enforce(abuserReq, res, 'lead'); // exhaust
    const abuserBlocked = rateLimit.enforce(abuserReq, res, 'lead');
    const cleanAllowed = rateLimit.enforce(cleanReq, res, 'lead');
    expect(abuserBlocked.allowed).toBe(false);
    expect(cleanAllowed.allowed).toBe(true);
  });

  it('extracts the leftmost X-Forwarded-For value', () => {
    expect(
      rateLimit.clientIp({ headers: { 'x-forwarded-for': '203.0.113.5, 10.0.0.1, 10.0.0.2' } })
    ).toBe('203.0.113.5');
  });

  it('falls back to X-Real-IP then unknown', () => {
    expect(rateLimit.clientIp({ headers: { 'x-real-ip': '203.0.113.7' } })).toBe('203.0.113.7');
    expect(rateLimit.clientIp({ headers: {} })).toBe('unknown');
  });
});

describe('polly lead handler — anti-abuse', () => {
  beforeEach(() => rateLimit.reset());

  it('honeypot filled → returns 200 but skips downstream side effects', async () => {
    const req = makeReq({
      body: {
        contact: 'spambot@example.com',
        project_type: 'audit',
        budget: 'open',
        timeline: 'open',
        description: 'this is a spambot scraping the form blindly',
        website: 'https://spambot.example/',
      },
      headers: { 'x-forwarded-for': '203.0.113.99' },
    });
    const res = makeRes();
    await leadHandler(req, res);
    expect(res.statusCode).toBe(200);
    const body = res.body as { ok: boolean; next_steps: string[] };
    expect(body.ok).toBe(true);
    // Honeypot path returns empty next_steps so we can distinguish from real path
    expect(body.next_steps.length).toBe(0);
  });

  it('rate limit kicks in after 5 lead submissions per IP', async () => {
    const headers = { 'x-forwarded-for': '203.0.113.50' };
    const validBody = {
      contact: 'real@example.com',
      project_type: 'audit',
      budget: 'open',
      timeline: 'open',
      description: 'this is a real lead description from a real human',
    };
    for (let i = 0; i < 5; i += 1) {
      const res = makeRes();
      await leadHandler(makeReq({ body: validBody, headers }), res);
      expect(res.statusCode).toBe(200);
    }
    const overRes = makeRes();
    await leadHandler(makeReq({ body: validBody, headers }), overRes);
    expect(overRes.statusCode).toBe(429);
  });
});

describe('polly commerce intent classification', () => {
  it('catalog has live products with valid checkout urls', () => {
    expect(commerce.PRODUCT_CATALOG).toHaveLength(6);
    for (const product of commerce.PRODUCT_CATALOG) {
      expect(product.checkoutUrl).toMatch(/^(https:\/\/(buy\.stripe\.com|ko-fi\.com)|mailto:)/);
      expect(product.keywords.length).toBeGreaterThan(0);
    }
  });

  it('classifies service credits as the pay-as-you-go product', () => {
    const intent = commerce.classifyIntent('I want to buy service credits for hosted routing');
    expect(intent.name).toBe('buy');
    expect(intent.product.sku).toBe('scbe-service-credits');
  });

  it('honors env checkout override for governance heartbeat', () => {
    const loaded = loadCommerceWithEnv({
      SCBE_PAYMENT_LINK_HEARTBEAT: 'https://buy.stripe.com/heartbeat-live-placeholder',
    });
    const product = loaded.PRODUCT_CATALOG.find(
      (p: { sku: string }) => p.sku === 'governance-heartbeat'
    );
    expect(product.checkoutUrl).toBe('https://buy.stripe.com/heartbeat-live-placeholder');
  });

  it('ignores Stripe internal payment link IDs as public checkout overrides', () => {
    const loaded = loadCommerceWithEnv({
      SCBE_PAYMENT_LINK_TOOLKIT: 'plink_1T5t5MJTF2SuUODITNiC7v43',
      SCBE_PAYMENT_LINK_VAULT: 'plink_1TG7QuJTF2SuUODIpeN0DUVw',
    });
    const toolkit = loaded.PRODUCT_CATALOG.find(
      (p: { sku: string }) => p.sku === 'ai-governance-toolkit'
    );
    const vault = loaded.PRODUCT_CATALOG.find(
      (p: { sku: string }) => p.sku === 'ai-security-training-vault'
    );
    expect(toolkit.checkoutUrl).toMatch(/^https:\/\/buy\.stripe\.com\//);
    expect(vault.checkoutUrl).toMatch(/^https:\/\/buy\.stripe\.com\//);
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

  it('classifies governance snapshot as a buyable fixed-scope product', () => {
    const intent = commerce.classifyIntent('Can I get the $500 governance snapshot?');
    expect(intent.name).toBe('buy');
    expect(intent.product.sku).toBe('ai-governance-snapshot');
  });

  it('classifies governance heartbeat as the monthly subscription offer', () => {
    const intent = commerce.classifyIntent('I want the $99 monthly governance heartbeat');
    expect(intent.name).toBe('buy');
    expect(intent.product.sku).toBe('governance-heartbeat');
  });

  it('classifies monthly scan as governance heartbeat without an explicit buy verb', () => {
    const intent = commerce.classifyIntent('Do you have a monthly AI governance scan?');
    expect(intent.name).toBe('buy');
    expect(intent.confidence).toBeCloseTo(0.6, 2);
    expect(intent.product.sku).toBe('governance-heartbeat');
  });

  it('classifies custom intent at 0.85', () => {
    const intent = commerce.classifyIntent('I need a custom audit for my team');
    expect(intent.name).toBe('custom');
    expect(intent.confidence).toBeGreaterThanOrEqual(0.85);
  });

  it('routes hire-Issac and chatbot-safety buyer questions to custom', () => {
    expect(commerce.classifyIntent('How do I hire Issac?').name).toBe('custom');
    expect(commerce.classifyIntent('I need help making my chatbot safer').name).toBe('custom');
  });

  it('classifies membership intent at 0.75', () => {
    const intent = commerce.classifyIntent('How do I subscribe to the newsletter?');
    expect(intent.name).toBe('membership');
  });

  it('classifies research intent at 0.8', () => {
    const intent = commerce.classifyIntent('What is the latest research on the harmonic wall?');
    expect(intent.name).toBe('research');
    expect(intent.confidence).toBeCloseTo(0.8, 2);
  });

  it('classifies "what is the harmonic wall" via topic-key fallback at 0.78', () => {
    const intent = commerce.classifyIntent('What is the harmonic wall in SCBE?');
    expect(intent.name).toBe('research');
    expect(intent.confidence).toBeCloseTo(0.78, 2);
  });

  it('classifies "explain the 14-layer pipeline" via topic-key fallback', () => {
    const intent = commerce.classifyIntent('Explain the 14-layer pipeline please');
    expect(intent.name).toBe('research');
  });

  it('does NOT route question-shaped non-topic prompts to research', () => {
    const intent = commerce.classifyIntent('What time is it?');
    expect(intent.name).toBe('general');
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

  it('renderBuyReply with null lists all products', () => {
    const out = commerce.renderBuyReply(null);
    expect(out.actions).toHaveLength(commerce.PRODUCT_CATALOG.length);
    for (const action of out.actions) {
      expect(action.url).toMatch(/^(https:\/\/|mailto:)/);
    }
  });

  it('renderBuyReply for heartbeat includes immediate signup value', () => {
    const product = commerce.PRODUCT_CATALOG.find(
      (p: { sku: string }) => p.sku === 'governance-heartbeat'
    );
    const out = commerce.renderBuyReply(product);
    expect(out.text).toContain('$99/month');
    expect(out.text).toContain('first scan starts');
    expect(out.actions[0].url).toMatch(/^mailto:/);
  });

  it('renderCustomReply returns mailto with pre-filled context', () => {
    const out = commerce.renderCustomReply('We need governance for our finance LLM');
    const mailtoAction = out.actions.find((a: { url: string }) => a.url.startsWith('mailto:'));
    expect(mailtoAction).toBeDefined();
    expect(mailtoAction!.url).toContain('issdandavis7795@gmail.com');
    expect(mailtoAction!.url).toContain('finance');
    expect(out.actions.some((a: { url: string }) => a.url.includes('service-fast-start'))).toBe(
      true
    );
  });

  it('renderMembershipReply has credits + Ko-fi + GitHub + email actions', () => {
    const out = commerce.renderMembershipReply();
    expect(out.actions).toHaveLength(5);
    expect(out.actions[0].url).toContain('service-credits');
    expect(out.actions[1].url).toContain('Governance%20Heartbeat');
    expect(out.actions[2].url).toContain('ko-fi.com');
    expect(out.actions[3].url).toContain('github.com');
    expect(out.actions[4].url).toContain('mailto:');
    expect(out.text).toContain('2-5%');
    expect(out.text).toContain('$99/month');
  });

  it('renderResearchReply with matching topic returns canonical body + repo links', () => {
    const out = commerce.renderResearchReply('research the harmonic wall formula');
    expect(out.text).toContain('Harmonic wall');
    expect(out.text).toContain('H(d, pd)');
    expect(out.actions.some((a: { url: string }) => a.url.includes('harmonicScaling.ts'))).toBe(
      true
    );
  });

  it('renderResearchReply with no matching topic returns topic index', () => {
    const out = commerce.renderResearchReply('research something completely off-topic xyz');
    expect(out.text).toContain('I can answer research questions');
    expect(out.text).toContain('Harmonic wall');
    expect(out.text).toContain('Sacred Tongues');
  });
});

describe('polly chat handler — research path', () => {
  beforeEach(() => rateLimit.reset());
  it('returns deterministic answer for harmonic wall research question', async () => {
    const req = makeReq({
      body: {
        message: 'What is the latest research on the harmonic wall?',
        consent_to_train: false,
      },
    });
    const res = makeRes();
    await chatHandler(req, res);
    const body = res.body as { intent: string; provider: string; text: string };
    expect(body.intent).toBe('research');
    expect(body.provider).toBe('research');
    expect(body.text).toContain('H(d, pd)');
  });
});

describe('polly chat handler — offline-router fallback', () => {
  beforeEach(() => rateLimit.reset());
  it('replaces dead-end LLM offline message with the four-bucket router', async () => {
    const original = {
      hf: process.env.HF_TOKEN,
      ollama: process.env.OLLAMA_URL,
    };
    delete process.env.HF_TOKEN;
    delete process.env.HUGGINGFACE_TOKEN;
    delete process.env.HUGGING_FACE_HUB_TOKEN;
    delete process.env.OLLAMA_URL;
    try {
      const req = makeReq({
        body: { message: 'tell me a joke about ducks please', consent_to_train: false },
      });
      const res = makeRes();
      await chatHandler(req, res);
      const body = res.body as { provider: string; text: string; actions: { url: string }[] };
      expect(body.provider).toBe('offline-router');
      expect(body.text).toContain('four ways');
      expect(body.actions.length).toBeGreaterThanOrEqual(2);
      expect(body.actions.some((a) => a.url.startsWith('mailto:'))).toBe(true);
    } finally {
      if (original.hf) process.env.HF_TOKEN = original.hf;
      if (original.ollama) process.env.OLLAMA_URL = original.ollama;
    }
  });
});

describe('polly chat handler — commerce path', () => {
  beforeEach(() => rateLimit.reset());
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
    expect(body.actions.some((a) => /aethermoore\.com\/.*hire/.test(a.url))).toBe(true);
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
  beforeEach(() => rateLimit.reset());
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
    expect(body.products).toHaveLength(commerce.PRODUCT_CATALOG.length);
    expect(body.consulting_tiers.length).toBeGreaterThan(0);
  });

  it('rejects POST', async () => {
    const req = makeReq({ method: 'POST' });
    const res = makeRes();
    await catalogHandler(req, res);
    expect(res.statusCode).toBe(405);
  });
});

describe('polly lead handler', () => {
  beforeEach(() => rateLimit.reset());

  const validLead = {
    contact: 'someone@example.com',
    project_type: 'audit',
    budget: '15k-50k',
    timeline: '1-3-months',
    description: 'Need an adversarial audit of our production LLM endpoint.',
  };

  it('accepts a valid lead and returns next-steps', async () => {
    const req = makeReq({ body: validLead });
    const res = makeRes();
    await leadHandler(req, res);
    expect(res.statusCode).toBe(200);
    const body = res.body as {
      ok: boolean;
      message: string;
      next_steps: string[];
      fulfillment_packet: {
        status: string;
        offer: string;
        initial_ai_inspection: string[];
        immediate_value: { url: string }[];
      };
    };
    expect(body.ok).toBe(true);
    expect(body.next_steps.length).toBeGreaterThan(0);
    expect(body.fulfillment_packet.status).toBe('instant-service-intake-v1');
    expect(body.fulfillment_packet.offer).toBe('Adversarial audit');
    expect(body.fulfillment_packet.initial_ai_inspection.length).toBeGreaterThan(0);
    expect(
      body.fulfillment_packet.immediate_value.some((item) =>
        item.url.includes('service-fast-start')
      )
    ).toBe(true);
  });

  it('rejects a lead missing the contact field', async () => {
    const req = makeReq({ body: { ...validLead, contact: '' } });
    const res = makeRes();
    await leadHandler(req, res);
    expect(res.statusCode).toBe(400);
  });

  it('rejects a lead with bogus contact format', async () => {
    const req = makeReq({ body: { ...validLead, contact: 'not-an-email-or-phone' } });
    const res = makeRes();
    await leadHandler(req, res);
    expect(res.statusCode).toBe(400);
  });

  it('rejects a lead with too-short description', async () => {
    const req = makeReq({ body: { ...validLead, description: 'too short' } });
    const res = makeRes();
    await leadHandler(req, res);
    expect(res.statusCode).toBe(400);
  });

  it('rejects a lead with unknown project_type', async () => {
    const req = makeReq({ body: { ...validLead, project_type: 'shouldnt-exist' } });
    const res = makeRes();
    await leadHandler(req, res);
    expect(res.statusCode).toBe(400);
  });

  it('accepts a phone-shaped contact', async () => {
    const req = makeReq({ body: { ...validLead, contact: '+1 (555) 555-5555' } });
    const res = makeRes();
    await leadHandler(req, res);
    expect(res.statusCode).toBe(200);
  });

  it('handles OPTIONS preflight with 204', async () => {
    const req = makeReq({ method: 'OPTIONS' });
    const res = makeRes();
    await leadHandler(req, res);
    expect(res.statusCode).toBe(204);
  });

  it('rejects GET with 405', async () => {
    const req = makeReq({ method: 'GET' });
    const res = makeRes();
    await leadHandler(req, res);
    expect(res.statusCode).toBe(405);
  });
});

describe('polly hosted-run handler', () => {
  beforeEach(() => rateLimit.reset());

  const validHostedRun = {
    contact: 'buyer@example.com',
    run_type: 'governance-scan',
    route: 'ollama-first',
    budget: '5-20',
    task: 'Run a small governed scan and tell me if local Ollama is enough.',
    source: 'test',
  };

  it('accepts a hosted run intake and returns immediate value links', async () => {
    const req = makeReq({ body: validHostedRun });
    const res = makeRes();
    await hostedRunHandler(req, res);
    expect(res.statusCode).toBe(200);
    const body = res.body as {
      ok: boolean;
      next_steps: string[];
      hosted_run_packet: {
        status: string;
        usage_policy: { fee: string };
        immediate_value: { url: string }[];
      };
    };
    expect(body.ok).toBe(true);
    expect(body.next_steps.length).toBeGreaterThan(0);
    expect(body.hosted_run_packet.status).toBe('hosted-run-intake-v1');
    expect(body.hosted_run_packet.usage_policy.fee).toContain('2-5%');
    expect(
      body.hosted_run_packet.immediate_value.some((item) => item.url.includes('service-credits'))
    ).toBe(true);
    expect(
      body.hosted_run_packet.immediate_value.some((item) => item.url.includes('ko-fi.com'))
    ).toBe(true);
  });

  it('rejects hosted run intake without contact', async () => {
    const req = makeReq({ body: { ...validHostedRun, contact: '' } });
    const res = makeRes();
    await hostedRunHandler(req, res);
    expect(res.statusCode).toBe(400);
    const body = res.body as { ok: boolean; error: string };
    expect(body.ok).toBe(false);
    expect(body.error).toContain('contact');
  });

  it('honeypot returns success with no downstream next steps', async () => {
    const req = makeReq({ body: { ...validHostedRun, website: 'https://bot.example' } });
    const res = makeRes();
    await hostedRunHandler(req, res);
    expect(res.statusCode).toBe(200);
    const body = res.body as { ok: boolean; next_steps: string[] };
    expect(body.ok).toBe(true);
    expect(body.next_steps).toHaveLength(0);
  });
});

describe('polly direct HF upload', () => {
  it('returns no_token when HF_TOKEN is unset', async () => {
    const original = {
      hf: process.env.HF_TOKEN,
      hugging: process.env.HUGGINGFACE_TOKEN,
      hub: process.env.HUGGING_FACE_HUB_TOKEN,
    };
    delete process.env.HF_TOKEN;
    delete process.env.HUGGINGFACE_TOKEN;
    delete process.env.HUGGING_FACE_HUB_TOKEN;
    try {
      const result = await hfUpload.uploadRecord({
        ts: 1,
        kind: 'chat',
        user: 'x',
        assistant: 'y',
      });
      expect(result.ok).toBe(false);
      expect(result.reason).toBe('no_token');
    } finally {
      if (original.hf) process.env.HF_TOKEN = original.hf;
      if (original.hugging) process.env.HUGGINGFACE_TOKEN = original.hugging;
      if (original.hub) process.env.HUGGING_FACE_HUB_TOKEN = original.hub;
    }
  });

  it('returns disabled when POLLY_HF_UPLOAD_ENABLED=false', async () => {
    const originalEnabled = process.env.POLLY_HF_UPLOAD_ENABLED;
    const originalToken = process.env.HF_TOKEN;
    process.env.POLLY_HF_UPLOAD_ENABLED = 'false';
    process.env.HF_TOKEN = 'test-token';
    try {
      const result = await hfUpload.uploadRecord({ ts: 1 });
      expect(result.ok).toBe(false);
      expect(result.reason).toBe('disabled');
    } finally {
      if (originalEnabled === undefined) delete process.env.POLLY_HF_UPLOAD_ENABLED;
      else process.env.POLLY_HF_UPLOAD_ENABLED = originalEnabled;
      if (originalToken === undefined) delete process.env.HF_TOKEN;
      else process.env.HF_TOKEN = originalToken;
    }
  });

  it('routes leads under polly-leads/ and chats under polly-chat-live/', () => {
    const leadPath = hfUpload.pathFor({ kind: 'lead', ts: 1715200000 });
    const chatPath = hfUpload.pathFor({ kind: 'chat', ts: 1715200000 });
    expect(leadPath.startsWith('polly-leads/')).toBe(true);
    expect(chatPath.startsWith('polly-chat-live/')).toBe(true);
  });

  it('falls back to chat path when kind is missing', () => {
    const path = hfUpload.pathFor({ ts: 1715200000 });
    expect(path.startsWith('polly-chat-live/')).toBe(true);
  });
});

describe('polly training capture (repository_dispatch)', () => {
  it('defaults to enabled when POLLY_TRAIN_DISPATCH_ENABLED is unset (private destination is wired)', async () => {
    const original = {
      enabled: process.env.POLLY_TRAIN_DISPATCH_ENABLED,
      gh: process.env.GITHUB_TOKEN,
      gh2: process.env.GH_TOKEN,
      polly: process.env.POLLY_TRAIN_GITHUB_TOKEN,
    };
    delete process.env.POLLY_TRAIN_DISPATCH_ENABLED;
    delete process.env.GITHUB_TOKEN;
    delete process.env.GH_TOKEN;
    delete process.env.POLLY_TRAIN_GITHUB_TOKEN;
    try {
      // With env unset and no token, we should hit no_token (proves the
      // disabled gate did NOT short-circuit — i.e. enabled-by-default).
      const result = await trainCapture.dispatchTrainingTurn({ ts: 1 });
      expect(result.ok).toBe(false);
      expect(result.reason).toBe('no_token');
    } finally {
      if (original.enabled === undefined) delete process.env.POLLY_TRAIN_DISPATCH_ENABLED;
      else process.env.POLLY_TRAIN_DISPATCH_ENABLED = original.enabled;
      if (original.gh) process.env.GITHUB_TOKEN = original.gh;
      if (original.gh2) process.env.GH_TOKEN = original.gh2;
      if (original.polly) process.env.POLLY_TRAIN_GITHUB_TOKEN = original.polly;
    }
  });

  it('returns disabled when env opt-out is explicitly set to false', async () => {
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

// eslint-disable-next-line @typescript-eslint/no-var-requires
const statsHandler = require('../../api/polly/stats.js');

describe('polly stats handler', () => {
  beforeEach(() => rateLimit.reset());

  it('returns capture_enabled=false when no HF token is set', async () => {
    // Test pollution guard at top of file already strips HF_TOKEN. So this
    // exercises the no-token branch that the live endpoint hits when the
    // operator has not yet wired HF_TOKEN on Vercel.
    const req = { method: 'GET', headers: {}, query: {} };
    const res = makeRes();
    await statsHandler(req, res);
    expect(res.statusCode).toBe(200);
    const body = res.body as { ok: boolean; capture_enabled: boolean; message?: string };
    expect(body.ok).toBe(true);
    expect(body.capture_enabled).toBe(false);
    expect(typeof body.message).toBe('string');
  });

  it('rejects non-GET methods', async () => {
    const req = { method: 'POST', headers: {}, query: {} };
    const res = makeRes();
    await statsHandler(req, res);
    expect(res.statusCode).toBe(405);
  });

  it('handles OPTIONS preflight with 204 + CORS headers', async () => {
    const req = { method: 'OPTIONS', headers: {}, query: {} };
    const res = makeRes();
    await statsHandler(req, res);
    expect(res.statusCode).toBe(204);
    expect(res.headers['Access-Control-Allow-Origin']).toBe('*');
  });

  it('exposes internal helpers and the date-validation guard', () => {
    const internal = statsHandler._internal;
    expect(internal).toBeDefined();
    expect(internal.isValidDate('2026-05-09')).toBe(true);
    expect(internal.isValidDate('2026-5-9')).toBe(false);
    expect(internal.isValidDate("'); DROP TABLE x;--")).toBe(false);
    expect(internal.isValidDate('')).toBe(false);
    expect(internal.todayUtc()).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});
