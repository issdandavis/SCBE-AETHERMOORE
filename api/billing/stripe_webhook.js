'use strict';

// POST /v1/billing/stripe-webhook — receives Stripe events and, when a
// Snapshot ($500 fixed-scope governance review) checkout completes, fires
// a `polly_snapshot_paid` repository_dispatch so the GitHub Actions
// notify workflow can email the buyer the intake checklist + scheduling
// link inside one business day.
//
// Verification: HMAC-SHA256 of `${timestamp}.${raw_body}` against
// STRIPE_WEBHOOK_SECRET, matched in constant time. No `stripe` npm
// package needed; we only consume the JSON shape and the t=/v1= header.
//
// Snapshot detection (any of):
//   - session.payment_link === STRIPE_SNAPSHOT_PAYMENT_LINK_ID
//   - mode='payment' AND amount_total === 50000 AND currency === 'usd'
// Both keep working if the Payment Link is re-created.
//
// Digital package delivery is stricter: Toolkit and Vault are both $29, so
// price alone cannot identify which package to send. They require a pinned
// Payment Link id or explicit checkout metadata.
//
// Always responds 200 after a valid signature so Stripe stops retrying;
// the side-effect dispatch is best-effort and logged on failure.

const crypto = require('crypto');

const SNAPSHOT_AMOUNT_CENTS = 50000;
const HEARTBEAT_AMOUNT_CENTS = 9900;
const LIVE_HEARTBEAT_PAYMENT_LINK_ID = 'plink_1TW71zJTF2SuUODICZLQCCS3';
const DIGITAL_PRODUCT_AMOUNT_CENTS = 2900;
const TOLERANCE_SECONDS = 300; // Stripe default replay window

const DIGITAL_PRODUCTS = {
  toolkit: {
    key: 'toolkit',
    source: 'ai-governance-toolkit',
    displayName: 'SCBE AI Governance Toolkit',
    packageName: 'SCBE_AI_Governance_Toolkit_v1.zip',
    manualUrl: 'https://aethermoore.com/SCBE-AETHERMOORE/product-manual/ai-governance-toolkit.html',
  },
  vault: {
    key: 'vault',
    source: 'ai-security-training-vault',
    displayName: 'SCBE AI Security Training Vault',
    packageName: 'SCBE_AI_Security_Training_Vault_v1.zip',
    manualUrl: 'https://aethermoore.com/SCBE-AETHERMOORE/product-manual/training-vault.html',
  },
};

function setCors(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Stripe-Signature');
}

function sendJson(res, status, payload) {
  setCors(res);
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.status(status).json(payload);
}

function readRawBody(req) {
  return new Promise((resolve, reject) => {
    if (req.rawBody) return resolve(req.rawBody.toString('utf8'));
    let raw = '';
    let total = 0;
    req.on('data', (chunk) => {
      total += chunk.length;
      if (total > 65536) {
        reject(new Error('request body too large'));
        req.destroy();
        return;
      }
      raw += chunk;
    });
    req.on('end', () => resolve(raw));
    req.on('error', reject);
  });
}

function parseSignatureHeader(header) {
  const parts = String(header || '').split(',');
  let timestamp = null;
  const signatures = [];
  for (const part of parts) {
    const eq = part.indexOf('=');
    if (eq < 0) continue;
    const key = part.slice(0, eq).trim();
    const value = part.slice(eq + 1).trim();
    if (key === 't') timestamp = value;
    else if (key === 'v1') signatures.push(value);
  }
  return { timestamp, signatures };
}

function verifySignature(rawBody, header, secret, nowSeconds) {
  if (!header || !secret) return { ok: false, reason: 'missing_signature_or_secret' };
  const { timestamp, signatures } = parseSignatureHeader(header);
  if (!timestamp || signatures.length === 0) {
    return { ok: false, reason: 'malformed_signature_header' };
  }
  const ts = Number(timestamp);
  if (!Number.isFinite(ts)) return { ok: false, reason: 'bad_timestamp' };
  if (Math.abs(nowSeconds - ts) > TOLERANCE_SECONDS) {
    return { ok: false, reason: 'timestamp_outside_tolerance' };
  }
  const signedPayload = `${timestamp}.${rawBody}`;
  const expected = crypto.createHmac('sha256', secret).update(signedPayload, 'utf8').digest('hex');
  const expectedBuf = Buffer.from(expected, 'utf8');
  for (const sig of signatures) {
    let provided;
    try {
      provided = Buffer.from(sig, 'utf8');
    } catch {
      continue;
    }
    if (provided.length !== expectedBuf.length) continue;
    if (crypto.timingSafeEqual(provided, expectedBuf)) return { ok: true };
  }
  return { ok: false, reason: 'signature_mismatch' };
}

function snapshotConfig() {
  return {
    webhookSecret: process.env.STRIPE_WEBHOOK_SECRET || '',
    paymentLinkId: process.env.STRIPE_SNAPSHOT_PAYMENT_LINK_ID || '',
    heartbeatPaymentLinkId:
      process.env.STRIPE_HEARTBEAT_PAYMENT_LINK_ID || LIVE_HEARTBEAT_PAYMENT_LINK_ID,
    toolkitPaymentLinkId:
      process.env.STRIPE_TOOLKIT_PAYMENT_LINK_ID ||
      process.env.SCBE_PAYMENT_LINK_TOOLKIT ||
      '',
    vaultPaymentLinkId:
      process.env.STRIPE_VAULT_PAYMENT_LINK_ID ||
      process.env.SCBE_PAYMENT_LINK_VAULT ||
      '',
    repo: process.env.POLLY_TRAIN_REPO || process.env.GITHUB_REPO || 'issdandavis/SCBE-AETHERMOORE',
    githubToken:
      process.env.POLLY_TRAIN_GITHUB_TOKEN ||
      process.env.GITHUB_TOKEN ||
      process.env.GH_TOKEN ||
      '',
    dispatchEnabled:
      String(process.env.POLLY_SNAPSHOT_DISPATCH_ENABLED || 'true').toLowerCase() !== 'false',
    dispatchTimeoutMs: Math.max(
      500,
      Number(process.env.POLLY_SNAPSHOT_DISPATCH_TIMEOUT_MS || 4000)
    ),
  };
}

function normalizeProductKey(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/^scbe[-_]/, '')
    .replace(/^ai[-_]/, '')
    .replace(/[-_\s]+/g, '_');
}

function sessionProductMetadata(session) {
  const metadata = (session && session.metadata) || {};
  return normalizeProductKey(
    metadata.scbe_product ||
      metadata.product_key ||
      metadata.product ||
      metadata.offer_id ||
      metadata.offer
  );
}

function isSnapshotSession(session, cfg) {
  if (!session || typeof session !== 'object') return false;
  if (cfg.paymentLinkId && session.payment_link === cfg.paymentLinkId) return true;
  // Fall-through identification when the env var isn't pinned to a link id:
  // a one-off USD payment for exactly $500 is the Snapshot product.
  if (
    session.mode === 'payment' &&
    Number(session.amount_total) === SNAPSHOT_AMOUNT_CENTS &&
    String(session.currency || '').toLowerCase() === 'usd'
  ) {
    return true;
  }
  return false;
}

function isHeartbeatSession(session, cfg) {
  if (!session || typeof session !== 'object') return false;
  if (cfg.heartbeatPaymentLinkId && session.payment_link === cfg.heartbeatPaymentLinkId) {
    return true;
  }
  // Fallback: a $99/mo USD subscription signup is the Heartbeat product.
  // amount_total on a subscription checkout reflects the first invoice
  // (the $99 first charge); subsequent invoice.paid events use a different
  // shape and aren't routed here.
  if (
    session.mode === 'subscription' &&
    Number(session.amount_total) === HEARTBEAT_AMOUNT_CENTS &&
    String(session.currency || '').toLowerCase() === 'usd'
  ) {
    return true;
  }
  return false;
}

function isDigitalProductSession(session, cfg, productKey) {
  if (!session || typeof session !== 'object') return false;
  const product = DIGITAL_PRODUCTS[productKey];
  if (!product) return false;

  const paymentLinkId =
    productKey === 'toolkit' ? cfg.toolkitPaymentLinkId : cfg.vaultPaymentLinkId;
  if (paymentLinkId && session.payment_link === paymentLinkId) return true;

  const metadataKey = sessionProductMetadata(session);
  if (
    metadataKey === productKey ||
    metadataKey === product.source ||
    metadataKey === normalizeProductKey(product.displayName)
  ) {
    return (
      session.mode === 'payment' &&
      Number(session.amount_total) === DIGITAL_PRODUCT_AMOUNT_CENTS &&
      String(session.currency || '').toLowerCase() === 'usd'
    );
  }

  return false;
}

function isToolkitSession(session, cfg) {
  return isDigitalProductSession(session, cfg, 'toolkit');
}

function isVaultSession(session, cfg) {
  return isDigitalProductSession(session, cfg, 'vault');
}

async function fetchWithTimeout(url, init, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

async function dispatchEvent(eventType, record, cfg) {
  if (!cfg.dispatchEnabled) return { ok: false, reason: 'disabled' };
  if (!cfg.githubToken) return { ok: false, reason: 'no_token' };

  const url = `https://api.github.com/repos/${cfg.repo}/dispatches`;
  const body = JSON.stringify({ event_type: eventType, client_payload: { record } });

  try {
    const response = await fetchWithTimeout(
      url,
      {
        method: 'POST',
        headers: {
          Accept: 'application/vnd.github+json',
          Authorization: `Bearer ${cfg.githubToken}`,
          'Content-Type': 'application/json',
          'X-GitHub-Api-Version': '2022-11-28',
          'User-Agent': 'scbe-stripe-billing-webhook',
        },
        body,
      },
      cfg.dispatchTimeoutMs
    );
    if (!response.ok) {
      const detail = (await response.text()).slice(0, 240);
      return { ok: false, reason: `github_${response.status}`, detail };
    }
    return { ok: true };
  } catch (error) {
    return {
      ok: false,
      reason: 'fetch_error',
      detail: String(error && error.message).slice(0, 240),
    };
  }
}

function buildSessionRecord(session, kind, source) {
  const details = (session && session.customer_details) || {};
  return {
    kind,
    session_id: session && session.id,
    payment_intent: session && session.payment_intent,
    subscription_id: session && session.subscription,
    customer_id: session && session.customer,
    amount_total: session && session.amount_total,
    currency: session && session.currency,
    contact_email: details.email || (session && session.customer_email) || '',
    contact_name: details.name || '',
    contact_phone: details.phone || '',
    created: session && session.created,
    livemode: !!(session && session.livemode),
    payment_link: session && session.payment_link,
    mode: session && session.mode,
    source,
  };
}

function buildProductDeliveryRecord(session, productKey) {
  const product = DIGITAL_PRODUCTS[productKey];
  return {
    ...buildSessionRecord(session, 'product_delivery', product.source),
    product_key: product.key,
    product_name: product.displayName,
    package_name: product.packageName,
    manual_url: product.manualUrl,
  };
}

async function dispatchSnapshotPaid(session, cfg) {
  const record = buildSessionRecord(session, 'snapshot_paid', 'governance-snapshot');
  return dispatchEvent('polly_snapshot_paid', record, cfg);
}

async function dispatchHeartbeatStarted(session, cfg) {
  const record = buildSessionRecord(session, 'heartbeat_started', 'governance-heartbeat');
  return dispatchEvent('polly_heartbeat_started', record, cfg);
}

async function dispatchProductDelivery(session, cfg, productKey) {
  const record = buildProductDeliveryRecord(session, productKey);
  return dispatchEvent('polly_product_delivery', record, cfg);
}

module.exports = async function handler(req, res) {
  if (req.method === 'OPTIONS') {
    setCors(res);
    return res.status(204).end();
  }
  if (req.method !== 'POST') {
    return sendJson(res, 405, { ok: false, error: 'POST only' });
  }

  let raw;
  try {
    raw = await readRawBody(req);
  } catch (error) {
    return sendJson(res, 400, {
      ok: false,
      error: 'invalid body',
      detail: String(error.message || error),
    });
  }

  const cfg = snapshotConfig();
  if (!cfg.webhookSecret) {
    // Refuse to accept anything if the secret isn't configured. This prevents
    // a misconfigured deploy from silently green-checking unsigned events.
    return sendJson(res, 503, { ok: false, error: 'STRIPE_WEBHOOK_SECRET not configured' });
  }

  const sigHeader = req.headers['stripe-signature'];
  const verification = verifySignature(
    raw,
    sigHeader,
    cfg.webhookSecret,
    Math.floor(Date.now() / 1000)
  );
  if (!verification.ok) {
    return sendJson(res, 400, {
      ok: false,
      error: 'signature verification failed',
      reason: verification.reason,
    });
  }

  let event;
  try {
    event = JSON.parse(raw);
  } catch (error) {
    return sendJson(res, 400, {
      ok: false,
      error: 'invalid JSON',
      detail: String(error.message || error),
    });
  }

  // Only act on the one event we care about; everything else is a 200 ack.
  if (event && event.type === 'checkout.session.completed') {
    const session = event.data && event.data.object;
    if (isSnapshotSession(session, cfg)) {
      const dispatch = await dispatchSnapshotPaid(session, cfg);
      return sendJson(res, 200, {
        ok: true,
        handled: 'snapshot_paid',
        session_id: session && session.id,
        dispatch,
      });
    }
    if (isHeartbeatSession(session, cfg)) {
      const dispatch = await dispatchHeartbeatStarted(session, cfg);
      return sendJson(res, 200, {
        ok: true,
        handled: 'heartbeat_started',
        session_id: session && session.id,
        dispatch,
      });
    }
    if (isToolkitSession(session, cfg)) {
      const dispatch = await dispatchProductDelivery(session, cfg, 'toolkit');
      return sendJson(res, 200, {
        ok: true,
        handled: 'product_delivery',
        product_key: 'toolkit',
        session_id: session && session.id,
        dispatch,
      });
    }
    if (isVaultSession(session, cfg)) {
      const dispatch = await dispatchProductDelivery(session, cfg, 'vault');
      return sendJson(res, 200, {
        ok: true,
        handled: 'product_delivery',
        product_key: 'vault',
        session_id: session && session.id,
        dispatch,
      });
    }
    return sendJson(res, 200, {
      ok: true,
      handled: 'checkout_other',
      session_id: session && session.id,
    });
  }

  return sendJson(res, 200, { ok: true, handled: 'ignored', event_type: event && event.type });
};

module.exports._private = {
  parseSignatureHeader,
  verifySignature,
  isSnapshotSession,
  isHeartbeatSession,
  isToolkitSession,
  isVaultSession,
  isDigitalProductSession,
  snapshotConfig,
  buildSessionRecord,
  buildProductDeliveryRecord,
  SNAPSHOT_AMOUNT_CENTS,
  HEARTBEAT_AMOUNT_CENTS,
  DIGITAL_PRODUCT_AMOUNT_CENTS,
  DIGITAL_PRODUCTS,
  TOLERANCE_SECONDS,
};

// Critical: Stripe signature verification MUST see the exact raw request
// bytes. The default @vercel/node body parser would drain the stream and
// leave readRawBody() with `""`, causing every real event to fail HMAC
// match. This config disables that parsing for this single endpoint.
module.exports.config = {
  api: { bodyParser: false },
};
