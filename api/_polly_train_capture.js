'use strict';

// Best-effort durable capture of consented Polly chat turns.
// Strategy: fire a GitHub repository_dispatch event whose payload is the
// training record. A workflow listens for the `polly_training_turn` event
// type and appends the record to training-data/polly-chat-live/{YYYY-MM}.jsonl
// in main, then commits.
//
// All paths are non-blocking and never raise into the chat path.

const DEFAULT_REPO = 'issdandavis/SCBE-AETHERMOORE';
const EVENT_TYPE = 'polly_training_turn';

function trainConfig() {
  return {
    token:
      process.env.POLLY_TRAIN_GITHUB_TOKEN ||
      process.env.GITHUB_TOKEN ||
      process.env.GH_TOKEN ||
      '',
    repo: process.env.POLLY_TRAIN_REPO || process.env.GITHUB_REPO || DEFAULT_REPO,
    // Dispatch defaults to ON — the workflow pushes to a PRIVATE Hugging Face
    // dataset (issdandavis/polly-chat-live), so always-on capture is the
    // intended state. Set POLLY_TRAIN_DISPATCH_ENABLED='false' on Vercel to
    // explicitly opt out per-deploy.
    enabled: String(process.env.POLLY_TRAIN_DISPATCH_ENABLED || 'true').toLowerCase() !== 'false',
    timeoutMs: Math.max(500, Number(process.env.POLLY_TRAIN_DISPATCH_TIMEOUT_MS || 4000)),
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

async function dispatchTrainingTurn(record) {
  const cfg = trainConfig();
  if (!cfg.enabled) return { ok: false, reason: 'disabled' };
  if (!cfg.token) return { ok: false, reason: 'no_token' };
  if (!record || typeof record !== 'object') return { ok: false, reason: 'invalid_record' };

  const url = `https://api.github.com/repos/${cfg.repo}/dispatches`;
  const body = JSON.stringify({
    event_type: EVENT_TYPE,
    client_payload: { record },
  });

  try {
    const response = await fetchWithTimeout(
      url,
      {
        method: 'POST',
        headers: {
          Accept: 'application/vnd.github+json',
          Authorization: `Bearer ${cfg.token}`,
          'Content-Type': 'application/json',
          'X-GitHub-Api-Version': '2022-11-28',
          'User-Agent': 'scbe-polly-train-capture',
        },
        body,
      },
      cfg.timeoutMs
    );
    if (!response.ok) {
      return {
        ok: false,
        reason: `github_${response.status}`,
        detail: (await response.text()).slice(0, 240),
      };
    }
    return { ok: true };
  } catch (error) {
    return {
      ok: false,
      reason: 'fetch_error',
      detail: String(error && error.message).slice(0, 240),
    };
  }
}

module.exports = {
  EVENT_TYPE,
  trainConfig,
  dispatchTrainingTurn,
};
