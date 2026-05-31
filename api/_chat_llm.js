'use strict';

// Shared LLM router used by api/agent/chat.js and api/polly/chat.js.
// Extracted to a sibling helper so each Vercel Function can bundle it
// independently (ncc follows relative requires within the function dir's
// dependency tree, but cross-function requires like `../agent/chat`
// from `api/polly/chat.js` are not guaranteed to be hoisted).

const DEFAULT_HF_MODEL = 'Qwen/Qwen2.5-7B-Instruct';
const DEFAULT_HF_CHAT_URL = 'https://router.huggingface.co/v1/chat/completions';
const DEFAULT_OLLAMA_MODEL = 'llama3.2';
const DEFAULT_MAX_TOKENS = 512;
const DEFAULT_TIMEOUT_MS = 25000;

const SYSTEM_PROMPT =
  'You are Polly, the AI assistant for AetherMoore — an AI safety and governance framework ' +
  'using hyperbolic geometry with a 14-layer security pipeline. SCBE means Sacred ' +
  'Circuitry / Symphonic Cipher Boundary Engine in this project context; never invent a ' +
  'different expansion. Be helpful, concise, and accurate. If asked about SCBE, explain ' +
  'the practical product: governed agent behavior with auditable safety decisions, ' +
  'workflow failure analysis, and cheap-first/local-first model routing. For buyer-like ' +
  'questions, point to the $99 AI Agent Workflow Snapshot, $29 toolkit/training vault, ' +
  '$500 Governance Snapshot, or $5+ service credits.';

function cleanBaseUrl(value) {
  return String(value || '')
    .trim()
    .replace(/\/+$/, '');
}

function chatConfig() {
  const hfModel = String(
    process.env.HF_MODEL || process.env.AGENT_HF_MODEL || DEFAULT_HF_MODEL
  ).trim();
  const ollamaModel = String(
    process.env.OLLAMA_MODEL || process.env.AGENT_OLLAMA_MODEL || DEFAULT_OLLAMA_MODEL
  ).trim();
  return {
    hfModel,
    hfToken:
      process.env.HF_TOKEN ||
      process.env.HUGGINGFACE_TOKEN ||
      process.env.HUGGING_FACE_HUB_TOKEN ||
      '',
    hfUrl:
      process.env.HF_CHAT_URL ||
      DEFAULT_HF_CHAT_URL,
    ollamaUrl: cleanBaseUrl(process.env.OLLAMA_URL || process.env.AGENT_OLLAMA_URL || ''),
    ollamaModel,
    providerOrder: String(process.env.AGENT_CHAT_PROVIDER_ORDER || 'ollama,huggingface,offline')
      .split(',')
      .map((item) => item.trim().toLowerCase())
      .filter(Boolean),
    timeoutMs: Math.max(1000, Number(process.env.AGENT_CHAT_TIMEOUT_MS || DEFAULT_TIMEOUT_MS)),
  };
}

function normalizeText(value) {
  if (typeof value === 'string') return value.trim();
  if (Array.isArray(value)) {
    return value.map(normalizeText).filter(Boolean).join('\n').trim();
  }
  if (value && typeof value === 'object') {
    return normalizeText(value.text || value.content || value.generated_text || '');
  }
  return '';
}

function buildMessages(message, history) {
  const messages = [{ role: 'system', content: SYSTEM_PROMPT }];
  if (Array.isArray(history)) {
    history.slice(-6).forEach((row) => {
      const role = row && ['system', 'user', 'assistant'].includes(row.role) ? row.role : '';
      const content = normalizeText(row && row.content);
      if (role && content) messages.push({ role, content });
    });
  }
  messages.push({ role: 'user', content: String(message).trim() });
  return messages;
}

function messagesToPrompt(messages) {
  return messages
    .map((row) => {
      const role =
        row.role === 'assistant' ? 'Assistant' : row.role === 'system' ? 'System' : 'User';
      return `${role}: ${row.content}`;
    })
    .join('\n\n')
    .slice(0, 12000);
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

async function tryOllama(cfg, messages) {
  if (!cfg.ollamaUrl) return null;
  const response = await fetchWithTimeout(
    `${cfg.ollamaUrl}/api/generate`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: cfg.ollamaModel,
        prompt: messagesToPrompt(messages),
        stream: false,
      }),
    },
    cfg.timeoutMs
  );
  if (!response.ok) {
    return {
      ok: false,
      provider: 'ollama',
      model: cfg.ollamaModel,
      error: `Ollama returned ${response.status}`,
      detail: (await response.text()).slice(0, 400),
    };
  }
  const data = await response.json();
  const text = normalizeText(data.response);
  if (!text) {
    return {
      ok: false,
      provider: 'ollama',
      model: cfg.ollamaModel,
      error: 'Ollama returned no text',
    };
  }
  return {
    ok: true,
    text,
    provider: 'ollama',
    model: cfg.ollamaModel,
    tokens_in: Number(data.prompt_eval_count || 0),
    tokens_out: Number(data.eval_count || 0),
  };
}

async function tryHuggingFace(cfg, messages) {
  if (!cfg.hfToken) return null;
  const response = await fetchWithTimeout(
    cfg.hfUrl,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${cfg.hfToken}`,
      },
      body: JSON.stringify({ model: cfg.hfModel, messages, max_tokens: DEFAULT_MAX_TOKENS }),
    },
    cfg.timeoutMs
  );
  if (!response.ok) {
    return {
      ok: false,
      provider: 'huggingface',
      model: cfg.hfModel,
      error: `Hugging Face returned ${response.status}`,
      detail: (await response.text()).slice(0, 400),
    };
  }
  const data = await response.json();
  const text =
    normalizeText(
      data &&
        data.choices &&
        data.choices[0] &&
        data.choices[0].message &&
        data.choices[0].message.content
    ) ||
    normalizeText(data && data.generated_text) ||
    normalizeText(data && data.text) ||
    normalizeText(Array.isArray(data) && data[0]);
  if (!text) {
    return {
      ok: false,
      provider: 'huggingface',
      model: cfg.hfModel,
      error: 'Hugging Face returned no text',
    };
  }
  return { ok: true, text, provider: 'huggingface', model: cfg.hfModel };
}

function offlineReply(message, attempts) {
  return {
    ok: true,
    text:
      '[offline/local-first mode]\n\n' +
      'No configured chat model answered. Start Ollama at home or set HF_TOKEN for the hosted fallback.\n\n' +
      `Your message was received: ${String(message).slice(0, 600)}`,
    provider: 'offline',
    model: 'none',
    attempts,
  };
}

async function routeChat(cfg, message, history) {
  const messages = buildMessages(message, history);
  const attempts = [];
  for (const provider of cfg.providerOrder) {
    try {
      const result =
        provider === 'ollama'
          ? await tryOllama(cfg, messages)
          : provider === 'huggingface'
            ? await tryHuggingFace(cfg, messages)
            : null;
      if (!result) {
        attempts.push({ provider, status: 'skipped', reason: 'not_configured' });
        continue;
      }
      if (result.ok) return { ...result, attempts };
      attempts.push({
        provider,
        status: 'failed',
        model: result.model,
        error: result.error,
        detail: result.detail || '',
      });
    } catch (error) {
      attempts.push({
        provider,
        status: 'failed',
        error: String(error && error.message ? error.message : error).slice(0, 400),
      });
    }
  }
  return offlineReply(message, attempts);
}

module.exports = {
  SYSTEM_PROMPT,
  chatConfig,
  buildMessages,
  messagesToPrompt,
  normalizeText,
  routeChat,
};
