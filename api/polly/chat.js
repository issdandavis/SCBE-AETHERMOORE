'use strict';

const { readJsonBody, sendJson, setCors } = require('../_agent_common');
const {
  classifyIntent,
  renderBuyReply,
  renderCustomReply,
  renderMembershipReply,
} = require('./commerce');
const agentChat = require('../agent/chat');

const COMMERCE_INTENTS = new Set(['buy', 'custom', 'membership']);
const COMMERCE_CONFIDENCE_FLOOR = 0.6;
const TRAIN_LOG_PREFIX = 'polly_train_v1 ';

function logTrainingTurn(record) {
  try {
    process.stdout.write(TRAIN_LOG_PREFIX + JSON.stringify(record) + '\n');
  } catch (_err) {
    /* never raise into the chat path */
  }
}

function captureIfConsented({ req, message, reply, intent, sessionId, pageContext, provider }) {
  if (!req || req.consent_to_train !== true) return;
  if (typeof message !== 'string' || !message.trim()) return;
  if (typeof reply !== 'string' || !reply.trim()) return;
  logTrainingTurn({
    ts: Math.floor(Date.now() / 1000),
    session_id: sessionId || '',
    intent,
    provider: provider || 'commerce',
    user: message.slice(0, 4096),
    assistant: reply.slice(0, 8192),
    page_context: pageContext ? String(pageContext).slice(0, 512) : '',
    transport: 'vercel-polly-chat',
  });
}

async function llmFallback(message, history) {
  const cfg = agentChat._private.chatConfig();
  return agentChat._private.routeChat(cfg, message, history);
}

module.exports = async function handler(req, res) {
  setCors(res);
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') {
    return sendJson(res, 405, { ok: false, error: 'POST only' });
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

  const message = body && body.message;
  if (!message || typeof message !== 'string' || !message.trim()) {
    return sendJson(res, 400, { ok: false, error: 'message required' });
  }

  const history = Array.isArray(body.history) ? body.history : [];
  const sessionId = body.session_id || '';
  const pageContext = body.page_context || '';

  const intent = classifyIntent(message);

  if (intent.confidence >= COMMERCE_CONFIDENCE_FLOOR && COMMERCE_INTENTS.has(intent.name)) {
    let rendered;
    if (intent.name === 'buy') {
      rendered = renderBuyReply(intent.product);
    } else if (intent.name === 'custom') {
      rendered = renderCustomReply(message);
    } else {
      rendered = renderMembershipReply();
    }

    captureIfConsented({
      req: body,
      message,
      reply: rendered.text,
      intent: intent.name,
      sessionId,
      pageContext,
      provider: 'commerce',
    });

    return sendJson(res, 200, {
      ok: true,
      text: rendered.text,
      provider: 'commerce',
      model: 'intent-classifier-v1',
      intent: intent.name,
      confidence: intent.confidence,
      actions: rendered.actions,
      cost: 'zero-deterministic',
    });
  }

  let llm;
  try {
    llm = await llmFallback(message, history);
  } catch (error) {
    llm = {
      ok: false,
      text: `[error] LLM call failed: ${String(error.message || error).slice(0, 240)}`,
      provider: 'error',
      model: 'none',
    };
  }

  captureIfConsented({
    req: body,
    message,
    reply: llm && llm.text,
    intent: intent.name,
    sessionId,
    pageContext,
    provider: llm && llm.provider,
  });

  return sendJson(res, 200, {
    ok: !!(llm && llm.ok !== false),
    text: (llm && llm.text) || '',
    provider: (llm && llm.provider) || 'offline',
    model: (llm && llm.model) || 'none',
    attempts: (llm && llm.attempts) || [],
    intent: intent.name,
    confidence: intent.confidence,
    actions: [],
    cost: llm && llm.provider === 'huggingface' ? 'hf-token-or-free-tier' : 'zero-local-or-offline',
  });
};

module.exports._private = {
  COMMERCE_INTENTS,
  COMMERCE_CONFIDENCE_FLOOR,
  llmFallback,
  logTrainingTurn,
  captureIfConsented,
};
