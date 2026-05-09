'use strict';

const { readJsonBody, sendJson, setCors } = require('../_agent_common');
const trainCapture = require('../_polly_train_capture');
const hfUpload = require('../_polly_hf_upload');

const PROJECT_TYPES = new Set([
  'audit',
  'custom-overlay',
  'advisory-call',
  'subcontract',
  'training',
  'other',
]);

const BUDGET_RANGES = new Set([
  'under-5k',
  '5k-15k',
  '15k-50k',
  '50k-plus',
  'open',
]);

const TIMELINES = new Set([
  'asap',
  '2-4-weeks',
  '1-3-months',
  'q3',
  'q4',
  'open',
]);

const FIELD_CAPS = {
  contact: 240,
  description: 4000,
  source: 240,
};

function clean(value, max) {
  if (typeof value !== 'string') return '';
  return value.trim().slice(0, max);
}

function validateLead(body) {
  const contact = clean(body && body.contact, FIELD_CAPS.contact);
  if (!contact) return { ok: false, error: 'contact is required (email or phone)' };
  // Either an email or a phone-shaped contact is allowed; we only loosely
  // check the email path because phone formats vary internationally.
  const looksLikeEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contact);
  const looksLikePhone = /^[+()0-9\s.\-]{7,}$/.test(contact);
  if (!looksLikeEmail && !looksLikePhone) {
    return { ok: false, error: 'contact must look like an email or a phone number' };
  }

  const description = clean(body && body.description, FIELD_CAPS.description);
  if (!description || description.length < 10) {
    return { ok: false, error: 'description must be at least 10 characters' };
  }

  const projectType = String((body && body.project_type) || 'other').trim().toLowerCase();
  if (!PROJECT_TYPES.has(projectType)) {
    return {
      ok: false,
      error: `project_type must be one of: ${Array.from(PROJECT_TYPES).join(', ')}`,
    };
  }

  const budget = String((body && body.budget) || 'open').trim().toLowerCase();
  if (!BUDGET_RANGES.has(budget)) {
    return {
      ok: false,
      error: `budget must be one of: ${Array.from(BUDGET_RANGES).join(', ')}`,
    };
  }

  const timeline = String((body && body.timeline) || 'open').trim().toLowerCase();
  if (!TIMELINES.has(timeline)) {
    return {
      ok: false,
      error: `timeline must be one of: ${Array.from(TIMELINES).join(', ')}`,
    };
  }

  const source = clean(body && body.source, FIELD_CAPS.source);
  return {
    ok: true,
    contact,
    description,
    projectType,
    budget,
    timeline,
    source,
  };
}

const LEAD_LOG_PREFIX = 'polly_lead_v1 ';

function logLead(record) {
  try {
    process.stdout.write(LEAD_LOG_PREFIX + JSON.stringify(record) + '\n');
  } catch (_err) {
    /* never raise into the request path */
  }
}

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

  const lead = validateLead(body);
  if (!lead.ok) return sendJson(res, 400, { ok: false, error: lead.error });

  const record = {
    ts: Math.floor(Date.now() / 1000),
    kind: 'lead',
    contact: lead.contact,
    description: lead.description,
    project_type: lead.projectType,
    budget: lead.budget,
    timeline: lead.timeline,
    source: lead.source || 'aethermoore.com/hire',
    transport: 'vercel-polly-lead',
  };

  logLead(record);

  // Two parallel best-effort signal channels, awaited together so the
  // serverless runtime doesn't kill the function before the HF commit
  // completes. allSettled means a transient HF or GitHub blip never
  // poisons the lead response.
  //   1. Direct HF upload using HF_TOKEN — primary durable capture.
  //      Lead lands at polly-leads/{YYYY-MM-DD}/{stamp}-{nonce}.json in
  //      the PRIVATE dataset issdandavis/polly-chat-live.
  //   2. GitHub repository_dispatch — fires the issue + email side
  //      effects when POLLY_TRAIN_GITHUB_TOKEN is also set on Vercel.
  await Promise.allSettled([
    hfUpload.uploadRecord(record),
    trainCapture.dispatchTrainingTurn(record),
  ]);

  return sendJson(res, 200, {
    ok: true,
    message:
      "Got it — Issac will reply within 24 hours. If it's urgent, " +
      'phone (360) 808-0876 is the fastest path.',
    next_steps: [
      'Watch your inbox / phone for a direct reply',
      'In the meantime, browse the open-source work at https://github.com/issdandavis/SCBE-AETHERMOORE',
    ],
  });
};

module.exports._private = {
  PROJECT_TYPES,
  BUDGET_RANGES,
  TIMELINES,
  validateLead,
  logLead,
};
