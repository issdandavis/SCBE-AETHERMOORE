'use strict';

const {
  ALLOWED_TASKS,
  MAX_QUERY_LENGTH,
  envConfig,
  sendJson,
  setCors,
} = require('../_agent_common');

module.exports = async function handler(req, res) {
  setCors(res);
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'GET') return sendJson(res, 405, { ok: false, error: 'GET required' });

  const cfg = envConfig();
  return sendJson(res, 200, {
    ok: true,
    service: 'scbe-agent-vercel-bridge',
    repo: cfg.repo,
    workflow: cfg.workflow,
    ref: cfg.ref,
    dispatch_configured: Boolean(cfg.githubToken),
    dispatch_secret_required: Boolean(cfg.dispatchSecret),
    allowed_tasks: Array.from(ALLOWED_TASKS),
    max_query_length: MAX_QUERY_LENGTH,
    chat: {
      provider_order: String(process.env.AGENT_CHAT_PROVIDER_ORDER || 'ollama,huggingface,offline'),
      ollama_configured: Boolean(process.env.OLLAMA_URL || process.env.AGENT_OLLAMA_URL),
      huggingface_configured: Boolean(
        process.env.HF_TOKEN || process.env.HUGGINGFACE_TOKEN || process.env.HUGGING_FACE_HUB_TOKEN
      ),
      ollama_model: process.env.OLLAMA_MODEL || process.env.AGENT_OLLAMA_MODEL || 'llama3.2',
      hf_model: process.env.HF_MODEL || process.env.AGENT_HF_MODEL || 'Qwen/Qwen2.5-7B-Instruct',
      cost_policy:
        'prefer local Ollama, then configured Hugging Face, then deterministic offline fallback',
    },
    storage: {
      endpoint: '/api/agent/storage',
      default_provider: 'local_download',
      cost_policy:
        'zero server storage by default; local download/browser storage first, optional user-owned cloud handoff',
      providers: ['local_download', 'browser_local', 'github', 'dropbox', 'onedrive', 'gdrive'],
    },
  });
};
