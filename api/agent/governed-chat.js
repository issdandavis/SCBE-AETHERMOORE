'use strict';

const { readJsonBody, sendJson, setCors } = require('../_agent_common');
const llm = require('../_chat_llm');
const governed = require('../_governed_output');

module.exports = async function handler(req, res) {
  setCors(res);
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') return sendJson(res, 405, { ok: false, error: 'POST only' });

  let body;
  try {
    body = await readJsonBody(req, 64 * 1024);
  } catch (error) {
    return sendJson(res, 400, {
      ok: false,
      error: 'invalid JSON body',
      detail: String(error.message || error),
    });
  }

  const { inputText, history } = governed.extractMessagesPayload(body);
  if (!inputText) return sendJson(res, 400, { ok: false, error: 'messages or message required' });

  const id = `chatcmpl-scbe-${Date.now().toString(36)}`;
  const preBlock = governed.shouldPreBlock(inputText);
  if (preBlock.blocked) {
    const governance = {
      decision: preBlock.decision,
      reasons: preBlock.reasons,
      suggested_correction: preBlock.suggested_correction,
      intervention: 'refusal_injection',
      audit: {
        input_sha256_16: require('node:crypto').createHash('sha256').update(inputText).digest('hex').slice(0, 16),
        output_sha256_16: require('node:crypto').createHash('sha256').update(preBlock.output).digest('hex').slice(0, 16),
        provider: 'scbe-preflight',
        model: 'scbe-governed-output-v1',
      },
    };
    return sendJson(
      res,
      200,
      governed.openAiResponse({
        id,
        model: body.model || 'scbe-governed-output-v1',
        output: preBlock.output,
        governance,
        provider: 'scbe-preflight',
        attempts: [],
      })
    );
  }

  const result = await llm.routeChat(llm.chatConfig(), inputText, history);
  const output = String(result.text || '').trim();
  const governance = governed.buildGovernanceRecord({
    inputText,
    outputText: output,
    provider: result.provider,
    model: result.model,
    attempts: result.attempts,
  });
  const governedOutput = governed.applyOutputBrake(output, governance);

  return sendJson(
    res,
    200,
    governed.openAiResponse({
      id,
      model: body.model || result.model || 'scbe-governed-output-v1',
      output: governedOutput,
      governance,
      provider: result.provider,
      attempts: result.attempts,
    })
  );
};

module.exports._private = {
  ...governed,
};
