'use strict';

const { readJsonBody, sendJson, setCors } = require('../_agent_common');
const {
  classifyIntent,
  renderAgentTaskReply,
  renderBuyReply,
  renderCustomReply,
  renderGuideReply,
  renderMembershipReply,
  renderResearchReply,
  HIRE_EMAIL,
  CONSULTING_LANDING_URL,
} = require('./commerce');
const llm = require('../_chat_llm');
const hfUpload = require('../_polly_hf_upload');
const rateLimit = require('../_polly_rate_limit');

const COMMERCE_INTENTS = new Set([
  'agent_task',
  'buy',
  'custom',
  'guide',
  'membership',
  'research',
]);
const COMMERCE_CONFIDENCE_FLOOR = 0.6;
const TRAIN_LOG_PREFIX = 'polly_train_v1 ';

function logTrainingTurn(record) {
  try {
    process.stdout.write(TRAIN_LOG_PREFIX + JSON.stringify(record) + '\n');
  } catch (_err) {
    /* never raise into the chat path */
  }
}

async function captureIfConsented({
  req,
  message,
  reply,
  intent,
  sessionId,
  pageContext,
  provider,
}) {
  if (!req || req.consent_to_train !== true) return;
  if (typeof message !== 'string' || !message.trim()) return;
  if (typeof reply !== 'string' || !reply.trim()) return;
  const record = {
    ts: Math.floor(Date.now() / 1000),
    session_id: sessionId || '',
    intent,
    provider: provider || 'commerce',
    user: message.slice(0, 4096),
    assistant: reply.slice(0, 8192),
    page_context: pageContext ? String(pageContext).slice(0, 512) : '',
    transport: 'vercel-polly-chat',
  };
  logTrainingTurn(record);
  // Direct HF upload only for chat turns. The repository_dispatch path
  // exists for the lead-notification side effects (GitHub issue + SMTP
  // email) and isn't needed for chat — dispatching for chats would
  // trigger an empty workflow run per turn and burn CI minutes.
  // Awaited so the serverless runtime doesn't kill the function before
  // the HF commit returns.
  await hfUpload.uploadRecord(record).catch(() => {
    /* never raise into the chat path */
  });
}

async function llmFallback(message, history) {
  return llm.routeChat(llm.chatConfig(), message, history);
}

module.exports = async function handler(req, res) {
  setCors(res);
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') {
    return sendJson(res, 405, { ok: false, error: 'POST only' });
  }

  const rl = rateLimit.enforce(req, res, 'chat');
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
    } else if (intent.name === 'guide') {
      rendered = renderGuideReply();
    } else if (intent.name === 'research') {
      rendered = renderResearchReply(message);
    } else if (intent.name === 'agent_task') {
      rendered = renderAgentTaskReply(message);
    } else {
      rendered = renderMembershipReply();
    }

    const provider =
      intent.name === 'research'
        ? 'research'
        : intent.name === 'agent_task'
        ? 'agent_task'
        : 'commerce';

    await captureIfConsented({
      req: body,
      message,
      reply: rendered.text,
      intent: intent.name,
      sessionId,
      pageContext,
      provider,
    });

    return sendJson(res, 200, {
      ok: true,
      text: rendered.text,
      provider,
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

  // If the LLM router returns the offline placeholder, replace the dead-end
  // message with a useful four-bucket router so the user always has a next
  // step. Real LLM responses (provider in ollama|huggingface) pass through.
  if (!llm || llm.provider === 'offline' || llm.provider === 'error') {
    const fallback = renderOfflineRouter(message);
    await captureIfConsented({
      req: body,
      message,
      reply: fallback.text,
      intent: intent.name,
      sessionId,
      pageContext,
      provider: 'offline-router',
    });
    return sendJson(res, 200, {
      ok: true,
      text: fallback.text,
      provider: 'offline-router',
      model: 'fallback-router-v1',
      attempts: (llm && llm.attempts) || [],
      intent: intent.name,
      confidence: intent.confidence,
      actions: fallback.actions,
      cost: 'zero-deterministic',
    });
  }

  await captureIfConsented({
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

function renderOfflineRouter(message) {
  const trimmed = String(message || '').slice(0, 300);
  const subject = 'Polly conversation — direct follow-up';
  const body =
    `Hi Issac,\n\n` +
    `I asked Polly: "${trimmed}"\n\n` +
    `It didn't match a stock answer — could you reply directly? My context:\n\n`;
  const mailto = `mailto:${HIRE_EMAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  const text =
    "I don't have a stock answer for that one — but here are the four ways " +
    'I can actually help right now:\n\n' +
    '- **Buy** a $29 toolkit (governance or training vault)\n' +
    '- **Custom** scope: audit, advisory, or governance overlay\n' +
    '- **Research**: ask about the harmonic wall, the 14-layer pipeline, ' +
    'Sacred Tongues, axiom mesh, Petri composition, or DARPA work\n' +
    '- **Stay close**: tip the work or watch the GitHub repo\n\n' +
    'Or email me directly with your question — same-day reply where I can.';
  const actions = [
    { label: 'See products', url: CONSULTING_LANDING_URL },
    { label: 'Email Issac with this question', url: mailto },
    {
      label: 'Browse the repo',
      url: 'https://github.com/issdandavis/SCBE-AETHERMOORE',
    },
  ];
  return { text, actions };
}

module.exports._private = {
  COMMERCE_INTENTS,
  COMMERCE_CONFIDENCE_FLOOR,
  llmFallback,
  logTrainingTurn,
  captureIfConsented,
  renderOfflineRouter,
};
