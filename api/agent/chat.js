'use strict';

const { readJsonBody, sendJson, setCors } = require('../_agent_common');
const llm = require('../_chat_llm');

module.exports = async function handler(req, res) {
  setCors(res);
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') return sendJson(res, 405, { ok: false, error: 'POST only' });

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
  if (!message || !String(message).trim())
    return sendJson(res, 400, { ok: false, error: 'message required' });

  const result = await llm.routeChat(llm.chatConfig(), message, body.history);
  return sendJson(res, 200, {
    ...result,
    cost: result.provider === 'huggingface' ? 'hf-token-or-free-tier' : 'zero-local-or-offline',
  });
};

module.exports._private = {
  buildMessages: llm.buildMessages,
  chatConfig: llm.chatConfig,
  messagesToPrompt: llm.messagesToPrompt,
  normalizeText: llm.normalizeText,
  routeChat: llm.routeChat,
};
