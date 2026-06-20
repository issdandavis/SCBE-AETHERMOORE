'use strict';

const { readJsonBody, sendJson, setCors } = require('../_agent_common');
const trainCapture = require('../_polly_train_capture');
const hfUpload = require('../_polly_hf_upload');
const rateLimit = require('../_polly_rate_limit');

const HOSTED_RUN_PAGE = 'https://aethermoore.com/SCBE-AETHERMOORE/hosted-run.html';
const SERVICE_CREDITS_PAGE = 'https://aethermoore.com/SCBE-AETHERMOORE/service-credits.html';
const SERVICE_CREDITS_CHECKOUT = 'https://ko-fi.com/izdandavis';

const RUN_TYPES = new Set([
  'governance-scan',
  'agent-routing',
  'report',
  'benchmark',
  'training-capture',
  'other',
]);

const ROUTES = new Set(['local-first', 'ollama-first', 'hosted-ok', 'hosted-required']);
const BUDGETS = new Set(['credits-on-file', '5-20', '20-100', '100-plus', 'open']);

const FIELD_CAPS = {
  contact: 240,
  task: 4000,
  source: 240,
  repo_url: 400,
  artifact_url: 400,
};

function clean(value, max) {
  if (typeof value !== 'string') return '';
  return value.trim().slice(0, max);
}

function enumValue(value, allowed, fallback) {
  const normalized = String(value || fallback)
    .trim()
    .toLowerCase();
  return allowed.has(normalized) ? normalized : null;
}

function validateHostedRun(body) {
  const contact = clean(body && body.contact, FIELD_CAPS.contact);
  if (!contact) return { ok: false, error: 'contact is required (email or phone)' };
  const looksLikeEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contact);
  const looksLikePhone = /^[+()0-9\s.\-]{7,}$/.test(contact);
  if (!looksLikeEmail && !looksLikePhone) {
    return { ok: false, error: 'contact must look like an email or a phone number' };
  }

  const task = clean(body && body.task, FIELD_CAPS.task);
  if (!task || task.length < 10) {
    return { ok: false, error: 'task must be at least 10 characters' };
  }

  const runType = enumValue(body && body.run_type, RUN_TYPES, 'other');
  if (!runType) {
    return { ok: false, error: `run_type must be one of: ${Array.from(RUN_TYPES).join(', ')}` };
  }

  const route = enumValue(body && body.route, ROUTES, 'local-first');
  if (!route) {
    return { ok: false, error: `route must be one of: ${Array.from(ROUTES).join(', ')}` };
  }

  const budget = enumValue(body && body.budget, BUDGETS, 'open');
  if (!budget) {
    return { ok: false, error: `budget must be one of: ${Array.from(BUDGETS).join(', ')}` };
  }

  return {
    ok: true,
    contact,
    task,
    runType,
    route,
    budget,
    source: clean(body && body.source, FIELD_CAPS.source),
    repoUrl: clean(body && body.repo_url, FIELD_CAPS.repo_url),
    artifactUrl: clean(body && body.artifact_url, FIELD_CAPS.artifact_url),
    allowTrainingCapture: body && body.allow_training_capture === true,
  };
}

const HOSTED_RUN_LOG_PREFIX = 'polly_hosted_run_v1 ';

function logHostedRun(record) {
  try {
    process.stdout.write(HOSTED_RUN_LOG_PREFIX + JSON.stringify(record) + '\n');
  } catch (_err) {
    /* never raise into the request path */
  }
}

function buildHostedRunPacket(run) {
  return {
    status: 'hosted-run-intake-v1',
    offer: 'SCBE hosted run',
    run_type: run.runType,
    requested_route: run.route,
    budget: run.budget,
    usage_policy: {
      default: 'local/Ollama/deterministic harness first',
      billable_when:
        'hosted capacity, report delivery, storage, or paid provider/model usage is needed',
      fee: 'actual provider/model cost plus a 2-5% SCBE coordination fee',
      checkout_url: SERVICE_CREDITS_CHECKOUT,
    },
    order_recap: [
      `Requested run type: ${run.runType}`,
      `Route preference: ${run.route}`,
      `Budget/credit signal: ${run.budget}`,
      'Payment status: not charged by this form; credits/top-up are confirmed before billable hosted work.',
    ],
    initial_ai_inspection: [
      'Contact format validated.',
      'Run type, route preference, and budget signal normalized.',
      'No secrets are required at intake.',
      run.allowTrainingCapture
        ? 'Training capture consent was provided for this intake.'
        : 'Training capture consent was not provided; use private review only.',
    ],
    immediate_value: [
      {
        label: 'How SCBE Service Credits work',
        url: SERVICE_CREDITS_PAGE,
        why: 'Explains the free-first routing policy and 2-5% coordination fee.',
      },
      {
        label: 'Top up service credits',
        url: SERVICE_CREDITS_CHECKOUT,
        why: 'Use $5+ credits for small hosted runs without a large subscription.',
      },
      {
        label: 'Hosted run intake page',
        url: HOSTED_RUN_PAGE,
        why: 'Return here to submit another scoped run request.',
      },
      {
        label: 'Public SCBE repository',
        url: 'https://github.com/issdandavis/SCBE-AETHERMOORE',
        why: 'Inspect the open-source engine before paying for hosted work.',
      },
    ],
    follow_up_steps: [
      'The request is stored for private review.',
      'If it can run locally/free-first, the reply points to the local command or npm package path.',
      'If hosted capacity is needed, the reply confirms expected credit use before running.',
      'After a hosted run, buyer receives the result, a short receipt, and the next recommended command or report step.',
    ],
  };
}

module.exports = async function handler(req, res) {
  setCors(res);
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') return sendJson(res, 405, { ok: false, error: 'POST only' });

  const rl = rateLimit.enforce(req, res, 'hosted_run');
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

  // Honeypot: real users never see or fill `website`.
  if (body && typeof body.website === 'string' && body.website.trim().length > 0) {
    return sendJson(res, 200, {
      ok: true,
      message: 'Hosted run request received.',
      next_steps: [],
    });
  }

  const run = validateHostedRun(body);
  if (!run.ok) return sendJson(res, 400, { ok: false, error: run.error });

  const record = {
    ts: Math.floor(Date.now() / 1000),
    kind: 'hosted_run',
    contact: run.contact,
    task: run.task,
    run_type: run.runType,
    route: run.route,
    budget: run.budget,
    repo_url: run.repoUrl,
    artifact_url: run.artifactUrl,
    allow_training_capture: run.allowTrainingCapture,
    source: run.source || 'aethermoore.com/hosted-run',
    transport: 'vercel-polly-hosted-run',
  };

  logHostedRun(record);

  await Promise.allSettled([
    hfUpload.uploadRecord(record),
    trainCapture.dispatchTrainingTurn(record),
  ]);

  const hostedRunPacket = buildHostedRunPacket(run);

  return sendJson(res, 200, {
    ok: true,
    message:
      'Hosted run request received. If credits are needed, usage will be confirmed before billable work runs.',
    next_steps: [...hostedRunPacket.order_recap, ...hostedRunPacket.follow_up_steps],
    hosted_run_packet: hostedRunPacket,
  });
};

module.exports._private = {
  RUN_TYPES,
  ROUTES,
  BUDGETS,
  validateHostedRun,
  buildHostedRunPacket,
  logHostedRun,
};
