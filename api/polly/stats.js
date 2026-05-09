'use strict';

// GET /v1/polly/stats — public counts of consented chat turns and lead
// submissions captured to the private HF dataset, so the operator can see
// activity without browsing the dataset directly.
//
// Returns counts only (no record contents, no contact info, no message
// bodies), so it's safe to leave public. Counts come from listing the
// dataset's per-day directories via the HF tree API:
//
//   polly-chat-live/{YYYY-MM-DD}/*.json   → chat turns that day
//   polly-leads/{YYYY-MM-DD}/*.json       → leads submitted that day
//
// Cached for 60s in-memory per Vercel instance to avoid hammering HF on
// dashboard refreshes. Rate-limited under the `feedback` bucket (60/min).

const { sendJson, setCors } = require('../_agent_common');
const { uploadConfig } = require('../_polly_hf_upload');
const rateLimit = require('../_polly_rate_limit');

const HF_API_BASE = 'https://huggingface.co/api';
const CACHE_TTL_MS = 60_000;

// In-memory cache. Key: `${date}|${repo}`.
const cache = new Map();

function pad(n) {
  return n < 10 ? `0${n}` : String(n);
}

function todayUtc() {
  const d = new Date();
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}`;
}

function isValidDate(s) {
  return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s);
}

async function listFolder(repo, token, prefix, dateDir, timeoutMs) {
  // HF tree API: GET /api/datasets/{repo}/tree/main/{path}?recursive=false
  const path = `${prefix}/${dateDir}`;
  const url = `${HF_API_BASE}/datasets/${repo}/tree/main/${encodeURI(path)}?recursive=false`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    const response = await fetch(url, { method: 'GET', headers, signal: controller.signal });
    if (response.status === 404) return { count: 0, exists: false };
    if (!response.ok) {
      return { count: 0, exists: false, error: `hf list ${response.status}` };
    }
    const data = await response.json();
    if (!Array.isArray(data)) return { count: 0, exists: false };
    const fileCount = data.filter(
      (entry) => entry && entry.type === 'file' && /\.json$/i.test(entry.path || '')
    ).length;
    return { count: fileCount, exists: true };
  } catch (error) {
    return {
      count: 0,
      exists: false,
      error: String((error && error.message) || error).slice(0, 120),
    };
  } finally {
    clearTimeout(timer);
  }
}

async function gather(repo, token, dateDir, timeoutMs) {
  const [chats, leads] = await Promise.all([
    listFolder(repo, token, 'polly-chat-live', dateDir, timeoutMs),
    listFolder(repo, token, 'polly-leads', dateDir, timeoutMs),
  ]);
  return {
    date: dateDir,
    chats: chats.count,
    leads: leads.count,
    chats_dir_exists: chats.exists,
    leads_dir_exists: leads.exists,
    errors: [chats.error, leads.error].filter(Boolean),
  };
}

module.exports = async function handler(req, res) {
  setCors(res);
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'GET') {
    return sendJson(res, 405, { ok: false, error: 'GET only' });
  }

  const limited = rateLimit.enforce(req, res, 'feedback');
  if (!limited.allowed) {
    return sendJson(res, 429, { ok: false, error: 'rate limited' });
  }

  const cfg = uploadConfig();
  if (!cfg.enabled) {
    return sendJson(res, 200, {
      ok: true,
      capture_enabled: false,
      message: 'capture is disabled (POLLY_HF_UPLOAD_ENABLED=false)',
    });
  }
  if (!cfg.token) {
    return sendJson(res, 200, {
      ok: true,
      capture_enabled: false,
      message: 'HF_TOKEN not set on Vercel — capture and counts unavailable',
    });
  }

  const queryDate =
    (req.query && (req.query.date || (req.query.date === '' ? '' : null))) || '';
  const dateDir = isValidDate(queryDate) ? queryDate : todayUtc();
  const cacheKey = `${dateDir}|${cfg.repo}`;
  const cached = cache.get(cacheKey);
  const now = Date.now();
  if (cached && now - cached.at < CACHE_TTL_MS) {
    return sendJson(res, 200, { ...cached.payload, cached: true });
  }

  const stats = await gather(cfg.repo, cfg.token, dateDir, cfg.timeoutMs);
  const payload = {
    ok: true,
    capture_enabled: true,
    repo: cfg.repo,
    ...stats,
  };
  cache.set(cacheKey, { at: now, payload });
  return sendJson(res, 200, payload);
};

module.exports._internal = { todayUtc, isValidDate, gather };
