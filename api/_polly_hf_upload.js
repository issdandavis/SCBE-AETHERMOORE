'use strict';

// Direct upload to a private Hugging Face dataset from the Vercel runtime.
// Bypasses the GitHub repository_dispatch round-trip so capture works as
// long as HF_TOKEN is set on the project — no GitHub PAT required for the
// data path. The dispatch path remains the signal channel for the
// issue + email side effects.

const DEFAULT_DATASET = 'issdandavis/polly-chat-live';
const HF_API_BASE = 'https://huggingface.co/api';

function uploadConfig() {
  return {
    token:
      process.env.HF_TOKEN ||
      process.env.HUGGINGFACE_TOKEN ||
      process.env.HUGGING_FACE_HUB_TOKEN ||
      '',
    repo: process.env.POLLY_HF_DATASET || DEFAULT_DATASET,
    enabled: String(process.env.POLLY_HF_UPLOAD_ENABLED || 'true').toLowerCase() !== 'false',
    timeoutMs: Math.max(2000, Number(process.env.POLLY_HF_UPLOAD_TIMEOUT_MS || 8000)),
  };
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

function stamp(record) {
  const tsSeconds =
    typeof record.ts === 'number' && Number.isFinite(record.ts)
      ? record.ts
      : Math.floor(Date.now() / 1000);
  const date = new Date(tsSeconds * 1000);
  const day = date.toISOString().slice(0, 10);
  const compact = date
    .toISOString()
    .replace(/[-:]/g, '')
    .replace(/\.\d+Z$/, '')
    .replace('T', 'T');
  return { day, compact };
}

function nonceHex(bytes) {
  const out = new Uint8Array(bytes);
  if (typeof globalThis.crypto !== 'undefined' && globalThis.crypto.getRandomValues) {
    globalThis.crypto.getRandomValues(out);
  } else {
    for (let i = 0; i < out.length; i += 1) out[i] = Math.floor(Math.random() * 256);
  }
  return Array.from(out, (b) => b.toString(16).padStart(2, '0')).join('');
}

const KIND_PREFIX = {
  lead: 'polly-leads',
  hosted_run: 'polly-hosted-runs',
  funnel: 'polly-funnel',
  chat: 'polly-chat-live',
};

// Funnel event names are constrained at /v1/polly/funnel to a fixed
// allow-list of [a-z_0-9]+, so prefixing the filename with `${event}__`
// is path-safe and lets /v1/polly/stats?breakdown=event count by event
// in one HF directory listing instead of N file reads.
function safeFunnelEvent(value) {
  if (typeof value !== 'string') return '';
  return value
    .toLowerCase()
    .replace(/[^a-z0-9_]/g, '')
    .slice(0, 60);
}

function pathFor(record) {
  const kind = String(record.kind || 'chat').toLowerCase();
  const prefix = KIND_PREFIX[kind] || 'polly-chat-live';
  const { day, compact } = stamp(record);
  if (kind === 'funnel') {
    const event = safeFunnelEvent(record.event);
    if (event) {
      return `${prefix}/${day}/${event}__${compact}-${nonceHex(3)}.json`;
    }
  }
  return `${prefix}/${day}/${compact}-${nonceHex(3)}.json`;
}

async function ensureRepo(cfg) {
  // Idempotent: returns 200 if exists, 409 if conflict (already exists), or
  // 201 on create. Anything else is propagated up.
  const response = await fetchWithTimeout(
    `${HF_API_BASE}/repos/create`,
    {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        Authorization: `Bearer ${cfg.token}`,
        'Content-Type': 'application/json',
        'User-Agent': 'scbe-polly-hf-upload',
      },
      body: JSON.stringify({
        type: 'dataset',
        name: cfg.repo.split('/').slice(-1)[0],
        organization: cfg.repo.includes('/') ? cfg.repo.split('/')[0] : undefined,
        private: true,
      }),
    },
    cfg.timeoutMs
  );
  if (response.status === 409 || response.ok) return true;
  const detail = (await response.text()).slice(0, 240);
  throw new Error(`hf repo create ${response.status}: ${detail}`);
}

async function commitFile(cfg, pathInRepo, payloadString, summary) {
  const base64 =
    typeof Buffer !== 'undefined'
      ? Buffer.from(payloadString, 'utf-8').toString('base64')
      : btoa(unescape(encodeURIComponent(payloadString)));
  // NDJSON commit body — first line is the header, second line is the file.
  const ndjson =
    JSON.stringify({ key: 'header', value: { summary } }) +
    '\n' +
    JSON.stringify({
      key: 'file',
      value: { path: pathInRepo, encoding: 'base64', content: base64 },
    }) +
    '\n';
  const response = await fetchWithTimeout(
    `${HF_API_BASE}/datasets/${cfg.repo}/commit/main`,
    {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        Authorization: `Bearer ${cfg.token}`,
        'Content-Type': 'application/x-ndjson',
        'User-Agent': 'scbe-polly-hf-upload',
      },
      body: ndjson,
    },
    cfg.timeoutMs
  );
  if (!response.ok) {
    const detail = (await response.text()).slice(0, 240);
    throw new Error(`hf commit ${response.status}: ${detail}`);
  }
  return response.json().catch(() => ({ ok: true }));
}

async function uploadRecord(record) {
  const cfg = uploadConfig();
  if (!cfg.enabled) return { ok: false, reason: 'disabled' };
  if (!cfg.token) return { ok: false, reason: 'no_token' };
  if (!record || typeof record !== 'object') return { ok: false, reason: 'invalid_record' };

  try {
    await ensureRepo(cfg);
    const pathInRepo = pathFor(record);
    const payload = JSON.stringify(record);
    const summary = `chore(polly): ${String(record.kind || 'chat')} ${pathInRepo.split('/').slice(-1)[0]}`;
    const commit = await commitFile(cfg, pathInRepo, payload, summary);
    return { ok: true, repo: cfg.repo, path: pathInRepo, commit };
  } catch (error) {
    return {
      ok: false,
      reason: 'fetch_error',
      detail: String(error.message || error).slice(0, 240),
    };
  }
}

module.exports = {
  uploadConfig,
  uploadRecord,
  pathFor,
};

module.exports._internal = { pathFor, safeFunnelEvent, KIND_PREFIX };
