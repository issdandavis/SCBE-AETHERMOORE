'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const PROVIDERS = Object.freeze({
  ollama: {
    id: 'ollama',
    label: 'Ollama (local)',
    kind: 'ollama',
    aliases: ['local'],
    baseUrl: 'http://127.0.0.1:11434',
    baseUrlEnv: ['OLLAMA_BASE_URL', 'OLLAMA_HOST'],
    modelEnv: ['OLLAMA_MODEL'],
    defaultModel: 'llama3.2:1b',
    keyEnv: [],
  },
  openai: {
    id: 'openai',
    label: 'OpenAI',
    kind: 'openai',
    aliases: ['chatgpt'],
    baseUrl: 'https://api.openai.com/v1',
    baseUrlEnv: ['OPENAI_BASE_URL'],
    modelEnv: ['OPENAI_MODEL'],
    defaultModel: 'gpt-4o-mini',
    keyEnv: ['OPENAI_API_KEY'],
  },
  xai: {
    id: 'xai',
    label: 'xAI (Grok)',
    kind: 'openai',
    aliases: ['grok'],
    baseUrl: 'https://api.x.ai/v1',
    baseUrlEnv: ['XAI_BASE_URL', 'GROK_BASE_URL'],
    modelEnv: ['XAI_MODEL', 'GROK_MODEL'],
    defaultModel: 'grok-3-mini',
    keyEnv: ['XAI_API_KEY', 'GROK_API_KEY'],
  },
  moonshot: {
    id: 'moonshot',
    label: 'Moonshot (Kimi)',
    kind: 'openai',
    aliases: ['kimi'],
    baseUrl: 'https://api.moonshot.ai/v1',
    baseUrlEnv: ['MOONSHOT_BASE_URL', 'KIMI_BASE_URL'],
    modelEnv: ['MOONSHOT_MODEL', 'KIMI_MODEL'],
    defaultModel: 'kimi-k2.5',
    keyEnv: ['MOONSHOT_API_KEY', 'KIMI_API_KEY'],
  },
  groq: {
    id: 'groq',
    label: 'Groq',
    kind: 'openai',
    aliases: [],
    baseUrl: 'https://api.groq.com/openai/v1',
    baseUrlEnv: ['GROQ_BASE_URL'],
    modelEnv: ['GROQ_MODEL'],
    defaultModel: 'llama-3.3-70b-versatile',
    keyEnv: ['GROQ_API_KEY'],
  },
  cerebras: {
    id: 'cerebras',
    label: 'Cerebras',
    kind: 'openai',
    aliases: [],
    baseUrl: 'https://api.cerebras.ai/v1',
    baseUrlEnv: ['CEREBRAS_BASE_URL'],
    modelEnv: ['CEREBRAS_MODEL'],
    defaultModel: 'llama-3.3-70b',
    keyEnv: ['CEREBRAS_API_KEY'],
  },
  fireworks: {
    id: 'fireworks',
    label: 'Fireworks',
    kind: 'openai',
    aliases: [],
    baseUrl: 'https://api.fireworks.ai/inference/v1',
    baseUrlEnv: ['FIREWORKS_BASE_URL'],
    modelEnv: ['FIREWORKS_MODEL'],
    defaultModel: 'accounts/fireworks/models/kimi-k2p5',
    keyEnv: ['FIREWORKS_API_KEY'],
  },
  anthropic: {
    id: 'anthropic',
    label: 'Anthropic',
    kind: 'anthropic',
    aliases: ['claude'],
    baseUrl: 'https://api.anthropic.com/v1',
    baseUrlEnv: ['ANTHROPIC_BASE_URL'],
    modelEnv: ['ANTHROPIC_MODEL'],
    defaultModel: 'claude-haiku-4-5-20251001',
    keyEnv: ['ANTHROPIC_API_KEY'],
  },
  custom: {
    id: 'custom',
    label: 'Custom OpenAI-compatible',
    kind: 'openai',
    aliases: [],
    baseUrl: 'http://127.0.0.1:8000/v1',
    baseUrlEnv: ['SCBE_BASE_URL'],
    modelEnv: ['SCBE_MODEL'],
    defaultModel: 'default',
    keyEnv: ['SCBE_API_KEY'],
  },
  offline: {
    id: 'offline',
    label: 'Offline',
    kind: 'offline',
    aliases: [],
    baseUrl: '',
    baseUrlEnv: [],
    modelEnv: [],
    defaultModel: 'offline',
    keyEnv: [],
  },
});

const PROVIDER_ALIASES = new Map();
for (const provider of Object.values(PROVIDERS)) {
  PROVIDER_ALIASES.set(provider.id, provider.id);
  for (const alias of provider.aliases) PROVIDER_ALIASES.set(alias, provider.id);
}

function scbeHome(env = process.env, home = os.homedir()) {
  return path.resolve(env.SCBE_HOME || path.join(home, '.scbe'));
}

function shellConfigPath(options = {}) {
  return path.join(scbeHome(options.env, options.home), 'shell.json');
}

function readJson(filePath, fallback = {}) {
  try {
    const value = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    return value && typeof value === 'object' && !Array.isArray(value) ? value : fallback;
  } catch (_error) {
    return fallback;
  }
}

function firstEnv(env, names) {
  for (const name of names || []) {
    if (env[name]) return String(env[name]);
  }
  return '';
}

function normalizeProvider(value) {
  return PROVIDER_ALIASES.get(String(value || '').trim().toLowerCase()) || 'custom';
}

function parseModelSpec(value, currentProvider = 'ollama') {
  const raw = String(value || '').trim();
  if (!raw) return { provider: normalizeProvider(currentProvider), model: '' };

  const spaced = raw.match(/^([^\s]+)\s+(.+)$/);
  if (spaced && PROVIDER_ALIASES.has(spaced[1].toLowerCase())) {
    return { provider: normalizeProvider(spaced[1]), model: spaced[2].trim() };
  }

  const slash = raw.indexOf('/');
  if (slash > 0 && PROVIDER_ALIASES.has(raw.slice(0, slash).toLowerCase())) {
    return {
      provider: normalizeProvider(raw.slice(0, slash)),
      model: raw.slice(slash + 1).trim(),
    };
  }

  if (PROVIDER_ALIASES.has(raw.toLowerCase())) {
    return { provider: normalizeProvider(raw), model: '' };
  }
  return { provider: normalizeProvider(currentProvider), model: raw };
}

function objectRecord(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function providerSettings(raw, provider) {
  const providers = objectRecord(raw.providers);
  for (const [name, value] of Object.entries(providers)) {
    if (normalizeProvider(name) === provider) return objectRecord(value);
  }
  return {};
}

function legacySettingsMatch(raw, provider, options = {}) {
  const savedProvider = String(raw.provider || '').trim();
  if (savedProvider) return normalizeProvider(savedProvider) === provider;
  return options.allowUnscoped === true;
}

function legacyModelForProvider(raw, provider) {
  if (!raw.model) return '';
  const parsed = parseModelSpec(raw.model, provider);
  return parsed.provider === provider ? parsed.model : '';
}

function cleanBaseUrl(value) {
  return String(value || '').replace(/\/+$/, '');
}

function isConfigured(definition, provider, apiKey) {
  return (
    definition.kind === 'offline' ||
    definition.kind === 'ollama' ||
    Boolean(apiKey) ||
    provider === 'custom'
  );
}

function resolveAgentConfig(options = {}) {
  const env = options.env || process.env;
  const raw = readJson(shellConfigPath({ ...options, env }), {});
  let provider = normalizeProvider(env.SCBE_PROVIDER || raw.provider || 'ollama');
  let environmentModel = '';
  let savedModel = '';

  if (env.SCBE_MODEL) {
    const parsed = parseModelSpec(env.SCBE_MODEL, provider);
    provider = parsed.provider;
    environmentModel = parsed.model;
  } else if (!env.SCBE_PROVIDER && raw.model) {
    const parsed = parseModelSpec(raw.model, provider);
    provider = parsed.provider;
    savedModel = parsed.model;
  }

  const definition = PROVIDERS[provider] || PROVIDERS.custom;
  const scoped = providerSettings(raw, provider);
  const allowLegacy = legacySettingsMatch(raw, provider, {
    allowUnscoped: !env.SCBE_PROVIDER && !env.SCBE_MODEL,
  });
  const model =
    environmentModel ||
    firstEnv(env, definition.modelEnv) ||
    scoped.model ||
    savedModel ||
    (allowLegacy ? legacyModelForProvider(raw, provider) : '') ||
    definition.defaultModel;
  const baseUrl = cleanBaseUrl(
    env.SCBE_BASE_URL ||
      firstEnv(env, definition.baseUrlEnv) ||
      scoped.base_url ||
      scoped.url ||
      (allowLegacy ? raw.base_url || raw.openai_base_url || raw.url : '') ||
      definition.baseUrl
  );
  const configuredKeyEnv = String(
    scoped.api_key_env || (allowLegacy ? raw.api_key_env : '') || ''
  ).trim();
  const apiKey =
    env.SCBE_API_KEY ||
    (configuredKeyEnv ? env[configuredKeyEnv] : '') ||
    firstEnv(env, definition.keyEnv) ||
    scoped.api_key ||
    (allowLegacy ? raw.api_key : '') ||
    '';
  const timeoutMs = Number(env.SCBE_TIMEOUT_MS || raw.timeout_ms || 120000);
  const maxToolRounds = Number(env.SCBE_MAX_TOOL_ROUNDS || raw.max_tool_rounds || 8);

  return {
    provider,
    providerLabel: definition.label,
    kind: definition.kind,
    model,
    baseUrl,
    apiKey,
    apiKeyEnv: configuredKeyEnv || definition.keyEnv.find((name) => Boolean(env[name])) || null,
    configured: isConfigured(definition, provider, apiKey),
    timeoutMs: Number.isFinite(timeoutMs) && timeoutMs > 0 ? timeoutMs : 120000,
    maxToolRounds:
      Number.isFinite(maxToolRounds) && maxToolRounds > 0
        ? Math.min(20, Math.floor(maxToolRounds))
        : 8,
    permissionMode: String(env.SCBE_PERMISSION_MODE || raw.permission_mode || 'ask'),
    temperature: Number(scoped.temperature ?? raw.temperature ?? 0.2),
    configPath: shellConfigPath({ ...options, env }),
  };
}

function selectAgentConfig(current, spec, options = {}) {
  const env = options.env || process.env;
  const raw = readJson(shellConfigPath({ ...options, env }), {});
  const parsed = parseModelSpec(spec, current.provider);
  const provider = parsed.provider;
  const definition = PROVIDERS[provider] || PROVIDERS.custom;
  const scoped = providerSettings(raw, provider);
  const allowLegacy = legacySettingsMatch(raw, provider);
  const sameProvider = current.provider === provider;
  const configuredKeyEnv = String(
    scoped.api_key_env ||
      (sameProvider ? current.apiKeyEnv : '') ||
      (allowLegacy ? raw.api_key_env : '') ||
      ''
  ).trim();
  const model =
    parsed.model ||
    firstEnv(env, definition.modelEnv) ||
    (sameProvider ? current.model : '') ||
    scoped.model ||
    (allowLegacy ? legacyModelForProvider(raw, provider) : '') ||
    definition.defaultModel;
  const baseUrl = cleanBaseUrl(
    env.SCBE_BASE_URL ||
      firstEnv(env, definition.baseUrlEnv) ||
      (sameProvider ? current.baseUrl : '') ||
      scoped.base_url ||
      scoped.url ||
      (allowLegacy ? raw.base_url || raw.openai_base_url || raw.url : '') ||
      definition.baseUrl
  );
  const apiKey =
    env.SCBE_API_KEY ||
    (configuredKeyEnv ? env[configuredKeyEnv] : '') ||
    firstEnv(env, definition.keyEnv) ||
    (sameProvider ? current.apiKey : '') ||
    scoped.api_key ||
    (allowLegacy ? raw.api_key : '') ||
    '';

  return {
    ...current,
    provider,
    providerLabel: definition.label,
    kind: definition.kind,
    model,
    baseUrl,
    apiKey,
    apiKeyEnv: configuredKeyEnv || definition.keyEnv.find((name) => Boolean(env[name])) || null,
    configured: isConfigured(definition, provider, apiKey),
  };
}

function saveAgentConfig(patch, options = {}) {
  const configPath = shellConfigPath(options);
  const current = readJson(configPath, {});
  const safePatch = { ...patch };
  delete safePatch.apiKey;
  delete safePatch.api_key;
  if (safePatch.providers && typeof safePatch.providers === 'object') {
    const mergedProviders = {};
    for (const [provider, settings] of Object.entries(objectRecord(current.providers))) {
      const sanitized = { ...objectRecord(settings) };
      delete sanitized.apiKey;
      delete sanitized.api_key;
      mergedProviders[provider] = sanitized;
    }
    for (const [provider, settings] of Object.entries(objectRecord(safePatch.providers))) {
      const safeSettings = { ...objectRecord(settings) };
      delete safeSettings.apiKey;
      delete safeSettings.api_key;
      mergedProviders[provider] = {
        ...objectRecord(mergedProviders[provider]),
        ...safeSettings,
      };
    }
    safePatch.providers = mergedProviders;
  }
  const next = { ...current, ...safePatch };
  delete next.apiKey;
  delete next.api_key;
  fs.mkdirSync(path.dirname(configPath), { recursive: true });
  const temporary = `${configPath}.${process.pid}.tmp`;
  fs.writeFileSync(temporary, `${JSON.stringify(next, null, 2)}\n`, 'utf8');
  fs.renameSync(temporary, configPath);
  return next;
}

function listProviders(options = {}) {
  const env = options.env || process.env;
  return Object.values(PROVIDERS).map((provider) => ({
    id: provider.id,
    label: provider.label,
    kind: provider.kind,
    defaultModel: provider.defaultModel,
    configured:
      provider.kind === 'offline' ||
      provider.kind === 'ollama' ||
      provider.id === 'custom' ||
      Boolean(firstEnv(env, provider.keyEnv)),
    keyEnv: provider.keyEnv.slice(),
  }));
}

function asOpenAiTools(tools) {
  return (tools || []).map((tool) => ({
    type: 'function',
    function: {
      name: tool.name,
      description: tool.description,
      parameters: tool.inputSchema || { type: 'object', properties: {} },
    },
  }));
}

function normalizeToolCalls(toolCalls) {
  return (toolCalls || []).map((call, index) => {
    const fn = call.function || call;
    const args = fn.arguments ?? call.arguments ?? {};
    return {
      id: String(call.id || `tool-${Date.now()}-${index + 1}`),
      name: String(fn.name || call.name || ''),
      arguments: typeof args === 'string' ? args : JSON.stringify(args || {}),
    };
  });
}

function compactErrorBody(text) {
  return String(text || '')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 500);
}

async function fetchJson(url, init, timeoutMs, fetchImpl = globalThis.fetch) {
  if (typeof fetchImpl !== 'function') throw new Error('fetch unavailable; SCBE requires Node 20+');
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetchImpl(url, { ...init, signal: controller.signal });
    const text = await response.text();
    if (!response.ok) {
      throw new Error(`model HTTP ${response.status}: ${compactErrorBody(text) || response.statusText}`);
    }
    try {
      return JSON.parse(text || '{}');
    } catch (_error) {
      throw new Error(`model returned invalid JSON: ${compactErrorBody(text)}`);
    }
  } catch (error) {
    if (error && error.name === 'AbortError') {
      throw new Error(`model request timed out after ${timeoutMs}ms`);
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

function anthropicMessages(messages) {
  const system = messages
    .filter((message) => message.role === 'system')
    .map((message) => String(message.content || ''))
    .join('\n\n');
  const out = [];
  for (const message of messages) {
    if (message.role === 'system') continue;
    if (message.role === 'assistant' && message.tool_calls?.length) {
      const content = [];
      if (message.content) content.push({ type: 'text', text: String(message.content) });
      for (const call of message.tool_calls) {
        let input = {};
        try {
          input = JSON.parse(call.function?.arguments || call.arguments || '{}');
        } catch (_error) {
          input = {};
        }
        content.push({
          type: 'tool_use',
          id: call.id,
          name: call.function?.name || call.name,
          input,
        });
      }
      out.push({ role: 'assistant', content });
      continue;
    }
    if (message.role === 'tool') {
      out.push({
        role: 'user',
        content: [
          {
            type: 'tool_result',
            tool_use_id: message.tool_call_id,
            content: String(message.content || ''),
          },
        ],
      });
      continue;
    }
    out.push({ role: message.role, content: String(message.content || '') });
  }
  return { system, messages: out };
}

async function requestAnthropic(config, messages, tools, options) {
  const converted = anthropicMessages(messages);
  const body = {
    model: config.model,
    max_tokens: Number(options.maxTokens || 4096),
    temperature: config.temperature,
    system: converted.system,
    messages: converted.messages,
    tools: (tools || []).map((tool) => ({
      name: tool.name,
      description: tool.description,
      input_schema: tool.inputSchema || { type: 'object', properties: {} },
    })),
  };
  if (!body.tools.length) delete body.tools;
  const payload = await fetchJson(
    `${config.baseUrl}/messages`,
    {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'x-api-key': config.apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify(body),
    },
    config.timeoutMs,
    options.fetchImpl
  );
  const content = (payload.content || [])
    .filter((block) => block.type === 'text')
    .map((block) => block.text || '')
    .join('');
  const toolCalls = (payload.content || [])
    .filter((block) => block.type === 'tool_use')
    .map((block) => ({
      id: block.id,
      name: block.name,
      arguments: JSON.stringify(block.input || {}),
    }));
  return { content, toolCalls, usage: payload.usage || null, raw: payload };
}

async function requestOpenAiLike(config, messages, tools, options) {
  const body = {
    model: config.model,
    messages,
    temperature: config.temperature,
    stream: false,
    tools: asOpenAiTools(tools),
    tool_choice: 'auto',
  };
  if (!body.tools.length) {
    delete body.tools;
    delete body.tool_choice;
  }
  const headers = { 'content-type': 'application/json' };
  if (config.apiKey) headers.authorization = `Bearer ${config.apiKey}`;

  let payload;
  try {
    payload = await fetchJson(
      `${config.baseUrl}/chat/completions`,
      { method: 'POST', headers, body: JSON.stringify(body) },
      config.timeoutMs,
      options.fetchImpl
    );
  } catch (error) {
    if (!body.tools || !/tool|function|schema/i.test(String(error.message || ''))) throw error;
    delete body.tools;
    delete body.tool_choice;
    payload = await fetchJson(
      `${config.baseUrl}/chat/completions`,
      { method: 'POST', headers, body: JSON.stringify(body) },
      config.timeoutMs,
      options.fetchImpl
    );
  }
  const message = payload.choices?.[0]?.message || {};
  return {
    content: String(message.content || ''),
    toolCalls: normalizeToolCalls(message.tool_calls),
    usage: payload.usage || null,
    raw: payload,
  };
}

async function requestOllama(config, messages, tools, options) {
  const body = {
    model: config.model,
    messages,
    stream: false,
    options: { temperature: config.temperature },
    tools: asOpenAiTools(tools),
  };
  if (!body.tools.length) delete body.tools;
  const headers = { 'content-type': 'application/json' };
  if (config.apiKey) headers.authorization = `Bearer ${config.apiKey}`;
  let payload;
  try {
    payload = await fetchJson(
      `${config.baseUrl.replace(/\/api$/, '')}/api/chat`,
      { method: 'POST', headers, body: JSON.stringify(body) },
      config.timeoutMs,
      options.fetchImpl
    );
  } catch (error) {
    if (!body.tools || !/tool|function|schema/i.test(String(error.message || ''))) throw error;
    delete body.tools;
    payload = await fetchJson(
      `${config.baseUrl.replace(/\/api$/, '')}/api/chat`,
      { method: 'POST', headers, body: JSON.stringify(body) },
      config.timeoutMs,
      options.fetchImpl
    );
  }
  const message = payload.message || {};
  return {
    content: String(message.content || ''),
    toolCalls: normalizeToolCalls(message.tool_calls),
    usage: {
      prompt_tokens: payload.prompt_eval_count,
      completion_tokens: payload.eval_count,
    },
    raw: payload,
  };
}

async function requestModel(config, messages, tools = [], options = {}) {
  if (options.transport) return options.transport({ config, messages, tools });
  if (config.kind === 'offline') {
    const last = [...messages].reverse().find((message) => message.role === 'user');
    return {
      content:
        `[offline] I saved your message${last?.content ? `: ${String(last.content).slice(0, 120)}` : ''}. ` +
        'Use /model to select Ollama, Kimi, Grok, ChatGPT, or another compatible provider.',
      toolCalls: [],
      usage: null,
      raw: null,
    };
  }
  if (!config.configured) {
    const definition = PROVIDERS[config.provider] || PROVIDERS.custom;
    throw new Error(
      `${definition.label} is not configured. Set ${definition.keyEnv.join(' or ') || 'an API key'} or use /model ollama.`
    );
  }
  if (config.kind === 'anthropic') {
    return requestAnthropic(config, messages, tools, options);
  }
  if (config.kind === 'ollama') {
    return requestOllama(config, messages, tools, options);
  }
  return requestOpenAiLike(config, messages, tools, options);
}

module.exports = {
  PROVIDERS,
  normalizeProvider,
  parseModelSpec,
  resolveAgentConfig,
  selectAgentConfig,
  saveAgentConfig,
  listProviders,
  requestModel,
  scbeHome,
  shellConfigPath,
};
