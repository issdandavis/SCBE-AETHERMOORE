'use strict';

const { sendJson, setCors } = require('../_agent_common');

const STRIPE_API_BASE = 'https://api.stripe.com/v1';
const STRIPE_TIMEOUT_MS = 5000;

const PRODUCTS = {
  toolkit: {
    envUrl: 'SCBE_TOOLKIT_BLOB_URL',
    envPaymentLink: 'STRIPE_TOOLKIT_PAYMENT_LINK_ID',
    fallbackPaymentLink: 'plink_1T5t5MJTF2SuUODITNiC7v43',
    filename: 'SCBE_AI_Governance_Toolkit_v1.zip',
  },
  vault: {
    envUrl: 'SCBE_VAULT_BLOB_URL',
    envPaymentLink: 'STRIPE_VAULT_PAYMENT_LINK_ID',
    fallbackPaymentLink: 'plink_1TG7QuJTF2SuUODIpeN0DUVw',
    filename: 'SCBE_AI_Security_Training_Vault_v1.zip',
  },
  making_of: {
    envUrl: 'SCBE_MAKING_OF_BLOB_URL',
    envPaymentLink: 'STRIPE_MAKING_OF_PAYMENT_LINK_ID',
    fallbackPaymentLink: 'plink_1TXo24JTF2SuUODIoRc6T3DD',
    filename: 'AetherMoore_Behind_The_Scenes_Writing_Process_Pack_v1.zip',
  },
};

function requestUrl(req) {
  return new URL(req.url || '/api/agent/download', 'https://scbe-agent-bridge-vercel.vercel.app');
}

function normalizeProductKey(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/^scbe[-_]/, '')
    .replace(/^ai[-_]/, '')
    .replace(/[-_\s]+/g, '_');
}

function requestedProduct(req) {
  return normalizeProductKey(requestUrl(req).searchParams.get('product'));
}

function requestedSessionId(req) {
  return String(requestUrl(req).searchParams.get('session_id') || '').trim();
}

function paymentLinkId(value) {
  if (value && typeof value === 'object') return String(value.id || '');
  return String(value || '');
}

function productPaymentLink(product) {
  return String(process.env[product.envPaymentLink] || product.fallbackPaymentLink || '').trim();
}

function sessionProduct(session) {
  const linkId = paymentLinkId(session && session.payment_link);
  for (const [key, product] of Object.entries(PRODUCTS)) {
    if (linkId && linkId === productPaymentLink(product)) return key;
  }

  const metadata = (session && session.metadata) || {};
  const metadataKey = normalizeProductKey(
    metadata.scbe_product || metadata.product_key || metadata.product || metadata.offer_id
  );
  return PRODUCTS[metadataKey] ? metadataKey : '';
}

function isPaidCompleteSession(session) {
  return !!(
    session &&
    session.object === 'checkout.session' &&
    session.mode === 'payment' &&
    session.status === 'complete' &&
    session.payment_status === 'paid'
  );
}

async function fetchWithTimeout(url, init, timeoutMs = STRIPE_TIMEOUT_MS) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

async function retrieveCheckoutSession(sessionId, restrictedKey) {
  const response = await fetchWithTimeout(
    `${STRIPE_API_BASE}/checkout/sessions/${encodeURIComponent(sessionId)}`,
    {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${restrictedKey}`,
        'Stripe-Version': '2025-02-24.acacia',
      },
    }
  );
  if (!response.ok) return { ok: false, status: response.status };
  return { ok: true, session: await response.json() };
}

module.exports = async function handler(req, res) {
  setCors(res);
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    return sendJson(res, 405, { status: 'error', error: 'GET required' });
  }

  const restrictedKey = String(
    process.env.STRIPE_DELIVERY_RESTRICTED_KEY || process.env.STRIPE_SECRET_KEY || ''
  ).trim();
  if (!restrictedKey) {
    return sendJson(res, 503, { status: 'error', error: 'payment verification is not configured' });
  }

  const sessionId = requestedSessionId(req);
  if (!/^cs_(?:test_|live_)?[A-Za-z0-9]+$/.test(sessionId)) {
    return sendJson(res, 400, { status: 'error', error: 'valid session_id required' });
  }

  let verified;
  try {
    verified = await retrieveCheckoutSession(sessionId, restrictedKey);
  } catch {
    return sendJson(res, 502, { status: 'error', error: 'payment verification unavailable' });
  }
  if (!verified.ok) {
    return sendJson(res, 401, { status: 'error', error: 'checkout session not verified' });
  }

  const session = verified.session;
  if (!isPaidCompleteSession(session)) {
    return sendJson(res, 402, { status: 'error', error: 'payment is not complete' });
  }

  const productKey = sessionProduct(session);
  const product = PRODUCTS[productKey];
  if (!product) {
    return sendJson(res, 403, {
      status: 'error',
      error: 'checkout is not eligible for a download',
    });
  }

  const requested = requestedProduct(req);
  if (requested && requested !== productKey) {
    return sendJson(res, 403, {
      status: 'error',
      error: 'checkout does not match requested product',
    });
  }

  const blobUrl = String(process.env[product.envUrl] || '').trim();
  const blobToken = String(process.env.BLOB_READ_WRITE_TOKEN || '').trim();
  if (!blobUrl || !blobToken) {
    return sendJson(res, 503, { status: 'error', error: 'blob delivery is not configured' });
  }

  let upstream;
  try {
    upstream = await fetchWithTimeout(blobUrl, {
      method: req.method,
      headers: { Authorization: `Bearer ${blobToken}` },
    });
  } catch {
    return sendJson(res, 502, { status: 'error', error: 'blob delivery unavailable' });
  }
  if (!upstream.ok) {
    return sendJson(res, upstream.status, { status: 'error', error: 'blob fetch failed' });
  }

  res.setHeader('Content-Type', upstream.headers.get('content-type') || 'application/zip');
  res.setHeader('Content-Disposition', `attachment; filename="${product.filename}"`);
  res.setHeader('Cache-Control', 'private, no-store');
  res.setHeader('Referrer-Policy', 'no-referrer');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  if (req.method === 'HEAD') return res.status(200).end();

  const body = Buffer.from(await upstream.arrayBuffer());
  return res.status(200).send(body);
};

module.exports._private = {
  PRODUCTS,
  isPaidCompleteSession,
  normalizeProductKey,
  requestedProduct,
  requestedSessionId,
  retrieveCheckoutSession,
  sessionProduct,
};
