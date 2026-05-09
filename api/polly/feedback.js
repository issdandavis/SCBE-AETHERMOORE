'use strict';

const { readJsonBody, sendJson, setCors } = require('../_agent_common');
const rateLimit = require('../_polly_rate_limit');

const VALID_RATINGS = new Set(['up', 'down']);
const FEEDBACK_LOG_PREFIX = 'polly_feedback_v1 ';

function logFeedback(record) {
  try {
    process.stdout.write(FEEDBACK_LOG_PREFIX + JSON.stringify(record) + '\n');
  } catch (_err) {
    /* never raise */
  }
}

module.exports = async function handler(req, res) {
  setCors(res);
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') {
    return sendJson(res, 405, { ok: false, error: 'POST only' });
  }

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

  const rating = String((body && body.rating) || '').toLowerCase();
  if (!VALID_RATINGS.has(rating)) {
    return sendJson(res, 400, { ok: false, error: "rating must be 'up' or 'down'" });
  }

  const userMessage = typeof body.user_message === 'string' ? body.user_message.slice(0, 4096) : '';
  const assistantReply =
    typeof body.assistant_reply === 'string' ? body.assistant_reply.slice(0, 8192) : '';

  logFeedback({
    ts: Math.floor(Date.now() / 1000),
    session_id: (body && body.session_id) || '',
    rating,
    intent: (body && body.intent) || '',
    user: userMessage,
    assistant: assistantReply,
    page_context: typeof body.page_context === 'string' ? body.page_context.slice(0, 512) : '',
    transport: 'vercel-polly-feedback',
  });

  return sendJson(res, 200, { ok: true, captured: true, rating });
};

module.exports._private = { logFeedback, VALID_RATINGS };
