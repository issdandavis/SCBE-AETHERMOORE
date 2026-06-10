'use strict';

// POST /v1/polly/funnel — operator-only funnel telemetry for /hire and
// /governance-snapshot. Tiny event records like {event:'arrival', page,
// session, meta} land in the same private dataset as leads/chats but
// under polly-funnel/{YYYY-MM-DD}/ so they don't pollute the lead store.
// Counts surface in /v1/polly/stats and the polly-stats dashboard.
//
// Schema (all fields validated):
//   event   string, ALLOWED_EVENTS member
//   page    string, <= 80 chars (e.g. 'hire', 'governance-snapshot')
//   session string, <= 80 chars (client-generated, opaque)
//   meta    object|null, JSON-stringify <= 600 chars after serialization
//
// Honeypot: if `website` is non-empty, return 200 OK and discard.

const { readJsonBody, sendJson, setCors } = require('../_agent_common');
const hfUpload = require('../_polly_hf_upload');
const rateLimit = require('../_polly_rate_limit');

const ALLOWED_EVENTS = new Set([
  'arrival',
  'scroll_50',
  'scroll_90',
  'chat_open',
  'chat_msg',
  'lead_form_focus',
  'lead_submit_attempt',
  'lead_submit_ok',
  'lead_submit_fail',
  'cta_click_buy',
  'cta_click_chat',
  'cta_click_email',
  'snapshot_intake_attempt',
  'snapshot_intake_ok',
  'snapshot_intake_fail',
]);

const FIELD_CAPS = { page: 80, session: 80, meta_serialized: 600 };
const FUNNEL_LOG_PREFIX = 'polly_funnel_v1 ';

function clean(value, max) {
  if (typeof value !== 'string') return '';
  return value.trim().slice(0, max);
}

function validate(body) {
  const event = clean(body && body.event, 60).toLowerCase();
  if (!event) return { ok: false, error: 'event is required' };
  if (!ALLOWED_EVENTS.has(event)) {
    return { ok: false, error: `event must be one of: ${Array.from(ALLOWED_EVENTS).join(', ')}` };
  }
  const page = clean(body && body.page, FIELD_CAPS.page);
  if (!page) return { ok: false, error: 'page is required' };
  const session = clean(body && body.session, FIELD_CAPS.session);
  let meta = body && body.meta;
  if (meta !== undefined && meta !== null && typeof meta !== 'object') {
    return { ok: false, error: 'meta must be an object or omitted' };
  }
  if (meta) {
    const serialized = JSON.stringify(meta);
    if (serialized.length > FIELD_CAPS.meta_serialized) {
      return { ok: false, error: `meta too large (>${FIELD_CAPS.meta_serialized} chars serialized)` };
    }
  }
  return { ok: true, event, page, session, meta: meta || null };
}

function logFunnel(record) {
  try {
    process.stdout.write(FUNNEL_LOG_PREFIX + JSON.stringify(record) + '\n');
  } catch (_err) {
    /* never raise into the request path */
  }
}

module.exports = async function handler(req, res) {
  setCors(res);
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') return sendJson(res, 405, { ok: false, error: 'POST only' });

  const rl = rateLimit.enforce(req, res, 'feedback');
  if (!rl.allowed) {
    return sendJson(res, 429, {
      ok: false,
      error: 'rate limit exceeded',
      retry_after_ms: rl.retryAfterMs,
    });
  }

  let body;
  try {
    body = await readJsonBody(req);
  } catch (error) {
    return sendJson(res, 400, {
      ok: false,
      error: 'invalid JSON body',
      detail: String(error.message || error),
    });
  }

  // Honeypot — bots scraping pages with funnel beacons may try to spam.
  if (body && typeof body.website === 'string' && body.website.trim().length > 0) {
    return sendJson(res, 200, { ok: true, captured: false, reason: 'honeypot' });
  }

  const v = validate(body);
  if (!v.ok) return sendJson(res, 400, { ok: false, error: v.error });

  const record = {
    ts: Math.floor(Date.now() / 1000),
    kind: 'funnel',
    event: v.event,
    page: v.page,
    session: v.session,
    meta: v.meta,
    transport: 'vercel-polly-funnel',
  };

  logFunnel(record);

  // Best-effort capture — never let an HF blip break a beacon. Funnel
  // events are non-blocking telemetry; a 500 on the dataset side
  // shouldn't surface to the user. allSettled avoids that.
  await Promise.allSettled([hfUpload.uploadRecord(record)]);

  return sendJson(res, 200, { ok: true, captured: true, event: v.event });
};

module.exports._private = { ALLOWED_EVENTS, validate, logFunnel };
