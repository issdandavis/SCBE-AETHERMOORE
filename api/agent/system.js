'use strict';

const fs = require('node:fs');
const path = require('node:path');
const {
  ALLOWED_TASKS,
  MAX_QUERY_LENGTH,
  envConfig,
  sendJson,
  setCors,
} = require('../_agent_common');
const { chatConfig } = require('../_chat_llm');
const storage = require('./storage');

const { PROVIDERS, WORKSPACE_FORMATION } = storage._private;

function readPublicJson(name) {
  const target = path.join(process.cwd(), 'docs', name);
  return JSON.parse(fs.readFileSync(target, 'utf8'));
}

function bridgeHealth() {
  const cfg = envConfig();
  const chat = chatConfig();
  return {
    service: 'scbe-agent-vercel-bridge',
    repo: cfg.repo,
    workflow: cfg.workflow,
    ref: cfg.ref,
    dispatch_configured: Boolean(cfg.githubToken),
    dispatch_secret_required: Boolean(cfg.dispatchSecret),
    allowed_tasks: Array.from(ALLOWED_TASKS),
    max_query_length: MAX_QUERY_LENGTH,
    chat: {
      provider_order: chat.providerOrder,
      ollama_configured: Boolean(chat.ollamaUrl),
      huggingface_configured: Boolean(chat.hfToken),
      ollama_model: chat.ollamaModel,
      hf_model: chat.hfModel,
      hf_router: chat.hfUrl,
      cost_policy:
        'prefer local Ollama, then configured Hugging Face, then deterministic offline fallback',
    },
  };
}

function buildSystemContract() {
  const appConfig = readPublicJson('app-config.json');
  const offers = readPublicJson('offers.json');
  const health = bridgeHealth();

  return {
    ok: true,
    schema: 'aethermoor.agent.system_contract.v1',
    generated_at: new Date().toISOString(),
    product: {
      name: appConfig.app?.name || 'Aethermoor Bus',
      package_name: appConfig.app?.package_name || 'io.aethermoor.bus',
      release: appConfig.app?.current_release || 'unknown',
      principle: 'frontend and backend share one agent-bus contract',
    },
    frontend: {
      static_host: appConfig.endpoints?.site_home || '',
      mobile_routes: [
        {
          id: 'home',
          path: './index.html',
          purpose: 'status, offers, storage, and bridge overview',
        },
        { id: 'chat', path: './chat.html', purpose: 'assistant, search, and export thread' },
        { id: 'ops', path: './ops.html', purpose: 'operator diagnostics and backend checks' },
        { id: 'browse', path: './browse.html', purpose: 'web lane entrypoint' },
      ],
      remote_update: appConfig.remote_update || {},
      features: appConfig.features || {},
    },
    backend: {
      base_url: 'https://scbe-agent-bridge-vercel.vercel.app',
      endpoints: {
        health: '/api/agent/health',
        system: '/api/agent/system',
        chat: '/api/agent/chat',
        governed_chat: '/v1/chat/completions',
        hosted_run: '/v1/polly/hosted-run',
        search: '/api/agent/search',
        storage: '/api/agent/storage',
        status: '/api/agent/status',
        offers: '/api/agent/offers',
        app_config: '/api/agent/app-config',
      },
      health,
      governed_output: {
        schema: 'scbe.governed_output.v1',
        openai_compatible_route: '/v1/chat/completions',
        decisions: ['ALLOW', 'QUARANTINE', 'ESCALATE', 'DENY'],
        response_extension: 'scbe_governance',
      },
    },
    bus: {
      workspace_formation: WORKSPACE_FORMATION,
      storage_providers: PROVIDERS,
      data_policy: {
        server_storage: 'none by default',
        export_path: 'local download first; user-owned cloud handoff optional',
        secrets: 'never export secrets by default',
      },
    },
    monetization: {
      offers_schema: offers.schema,
      usage_policy: offers.usage_policy || {},
      live_offers: (offers.offers || [])
        .filter((offer) => offer.status === 'live')
        .map((offer) => ({
          id: offer.id,
          name: offer.name,
          price_label: offer.price_label,
          type: offer.type,
          checkout_url: offer.checkout_url,
          proof_url: offer.proof_url || '',
          intake_url: offer.intake_url || '',
        })),
      primary_offer: appConfig.fallbacks?.primary_offer || '',
    },
  };
}

module.exports = async function handler(req, res) {
  setCors(res);
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'GET') return sendJson(res, 405, { ok: false, error: 'GET required' });

  res.setHeader('Cache-Control', 's-maxage=60, stale-while-revalidate=300');
  return sendJson(res, 200, buildSystemContract());
};

module.exports._private = {
  bridgeHealth,
  buildSystemContract,
};
