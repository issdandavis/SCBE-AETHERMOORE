'use strict';

const net = require('node:net');

const GOVERNED_TASK_SCHEMA_VERSION = 'scbe.governed-task-run.v1';
const TASK_API_DEFAULT_URL = 'http://127.0.0.1:8766';
const HASH_RE = /^[a-f0-9]{64}$/;
const TERMINAL = new Set(['completed', 'failed', 'cancelled']);
const DISPOSITIONS = new Set([
  'pending',
  'review_required',
  'failed_evidence_check',
  'failed_execution',
  'cancelled',
]);

function isRecord(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function isOwnedIpv4(host) {
  const octets = host.split('.').map(Number);
  if (octets.length !== 4 || octets.some((part) => !Number.isInteger(part))) return false;
  const [first, second] = octets;
  return (
    first === 10 ||
    first === 127 ||
    (first === 169 && second === 254) ||
    (first === 172 && second >= 16 && second <= 31) ||
    (first === 192 && second === 168) ||
    (first === 100 && second >= 64 && second <= 127)
  );
}

function isOwnedTaskApiUrl(value) {
  let parsed;
  try {
    parsed = new URL(value);
  } catch (_) {
    return false;
  }
  if (!['http:', 'https:'].includes(parsed.protocol)) return false;
  const host = parsed.hostname.replace(/^\[|\]$/g, '').toLowerCase();
  if (host === 'localhost') return true;
  const family = net.isIP(host);
  if (family === 4) return isOwnedIpv4(host);
  if (family === 6) {
    return (
      host === '::1' || host.startsWith('fc') || host.startsWith('fd') || host.startsWith('fe80:')
    );
  }
  return false;
}

function normalizeBaseUrl(value, allowPublicNetwork) {
  const parsed = new URL(value);
  if (!isOwnedTaskApiUrl(parsed.toString())) {
    if (!allowPublicNetwork || parsed.protocol !== 'https:') {
      throw new Error('task API URL must be loopback/private/Tailscale, or explicit trusted HTTPS');
    }
  }
  parsed.pathname = parsed.pathname.replace(/\/+$/, '');
  parsed.search = '';
  parsed.hash = '';
  return parsed.toString().replace(/\/$/, '');
}

function validateTaskApiRun(raw) {
  const errors = [];
  if (!isRecord(raw)) return { ok: false, errors: ['task run must be an object'], raw };
  const run = { ...raw, schema_version: GOVERNED_TASK_SCHEMA_VERSION };
  if (run.status === 'cancelled' && run.disposition?.status === 'pending') {
    run.disposition = {
      status: 'cancelled',
      negative_example: true,
      do_not_promote_to_fact: true,
      reason: 'Cancelled runs are not eligible for factual training.',
    };
  }
  if (!run.run_id || !run.interaction_id) errors.push('run and interaction IDs are required');
  if (!['queued', 'running', 'completed', 'failed', 'cancelled'].includes(run.status)) {
    errors.push('invalid task status');
  }
  if (!HASH_RE.test(String(run.input_sha256 || ''))) errors.push('input_sha256 is invalid');
  if (!Array.isArray(run.basis)) errors.push('basis must be an array');
  if (!isRecord(run.disposition)) {
    errors.push('disposition must be an object');
  } else {
    if (!DISPOSITIONS.has(run.disposition.status)) {
      errors.push('disposition status is not recognized');
    }
    if (run.disposition.do_not_promote_to_fact !== true) {
      errors.push('do_not_promote_to_fact must remain true');
    }
    if (typeof run.disposition.negative_example !== 'boolean') {
      errors.push('negative_example must be boolean');
    }
    if (typeof run.disposition.reason !== 'string' || !run.disposition.reason.trim()) {
      errors.push('disposition reason must be non-empty');
    }
  }
  const basis = Array.isArray(run.basis) ? run.basis : [];
  basis.forEach((field, fieldIndex) => {
    if (!isRecord(field)) {
      errors.push('basis[' + fieldIndex + '] must be an object');
      return;
    }
    if (typeof field.field !== 'string' || !field.field.trim()) {
      errors.push('basis[' + fieldIndex + '].field must be non-empty');
    }
    if (
      typeof field.confidence !== 'number' ||
      !Number.isFinite(field.confidence) ||
      field.confidence < 0 ||
      field.confidence > 1
    ) {
      errors.push('basis[' + fieldIndex + '].confidence must be between 0 and 1');
    }
    if (typeof field.reasoning !== 'string' || !field.reasoning.trim()) {
      errors.push('basis[' + fieldIndex + '].reasoning must be non-empty');
    }
    if (!Array.isArray(field.citations)) {
      errors.push('basis[' + fieldIndex + '].citations must be an array');
      return;
    }
    field.citations.forEach((citation, citationIndex) => {
      const path = 'basis[' + fieldIndex + '].citations[' + citationIndex + ']';
      if (!isRecord(citation)) {
        errors.push(path + ' must be an object');
        return;
      }
      if (
        typeof citation.title !== 'string' ||
        !citation.title.trim() ||
        typeof citation.url !== 'string' ||
        !citation.url.trim() ||
        typeof citation.quote !== 'string' ||
        !citation.quote.trim()
      ) {
        errors.push(path + ' is incomplete');
      }
      if (!HASH_RE.test(String(citation.content_sha256 || ''))) {
        errors.push(path + '.content_sha256 is invalid');
      }
    });
  });
  const citations = basis.reduce(
    (count, field) => count + (Array.isArray(field?.citations) ? field.citations.length : 0),
    0
  );
  if (run.status === 'completed') {
    if (!HASH_RE.test(String(run.output_sha256 || '')))
      errors.push('completed run needs output_sha256');
    if (
      citations > 0 &&
      (run.disposition?.status !== 'review_required' || run.disposition?.negative_example !== false)
    ) {
      errors.push('evidence-backed completion must remain review_required');
    }
    if (
      citations === 0 &&
      (run.disposition?.status !== 'failed_evidence_check' ||
        run.disposition?.negative_example !== true)
    ) {
      errors.push('completion without evidence must remain a negative example');
    }
  }
  if (
    run.status === 'failed' &&
    (run.disposition?.status !== 'failed_execution' || run.disposition?.negative_example !== true)
  ) {
    errors.push('failed execution must remain a negative example');
  }
  if (
    run.status === 'cancelled' &&
    (run.disposition?.status !== 'cancelled' || run.disposition?.negative_example !== true)
  ) {
    errors.push('cancelled run must remain non-promotable');
  }
  return errors.length ? { ok: false, errors, raw } : { ok: true, errors: [], data: run };
}

class TaskApiClient {
  constructor(options) {
    const config = options || {};
    this.baseUrl = normalizeBaseUrl(
      config.baseUrl ||
        process.env.POLLY_TASK_API_URL ||
        process.env.SCBE_TASK_API_URL ||
        TASK_API_DEFAULT_URL,
      config.allowPublicNetwork === true
    );
    this.fetchImpl = config.fetchImpl || fetch;
    this.timeoutMs = Math.max(100, Number(config.timeoutMs || 15000));
  }

  async request(pathname, init) {
    const request = init || {};
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);
    try {
      const response = await this.fetchImpl(this.baseUrl + pathname, {
        ...request,
        headers: {
          ...(request.body ? { 'content-type': 'application/json' } : {}),
          ...(request.headers || {}),
        },
        signal: controller.signal,
      });
      const text = await response.text();
      let body = {};
      if (text) {
        try {
          body = JSON.parse(text);
        } catch (_) {
          throw new Error('task API returned non-JSON HTTP ' + response.status);
        }
      }
      if (!response.ok) {
        throw new Error(
          'task API HTTP ' +
            response.status +
            ': ' +
            String(body.message || body.error || response.statusText)
        );
      }
      return body;
    } finally {
      clearTimeout(timer);
    }
  }

  parseRun(raw) {
    const parsed = validateTaskApiRun(raw);
    if (!parsed.ok) throw new Error('invalid task API run: ' + parsed.errors.join('; '));
    return parsed.data;
  }

  async createRun(payload) {
    return this.parseRun(
      await this.request('/v1/tasks/runs', { method: 'POST', body: JSON.stringify(payload) })
    );
  }

  async getRun(runId) {
    return this.parseRun(await this.request('/v1/tasks/runs/' + encodeURIComponent(runId)));
  }

  async waitForRun(runId, options) {
    const config = options || {};
    const timeoutMs = Math.max(100, Number(config.timeoutMs || 60000));
    const pollIntervalMs = Math.max(10, Number(config.pollIntervalMs || 100));
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      const run = await this.getRun(runId);
      if (TERMINAL.has(run.status)) return run;
      await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));
    }
    throw new Error('task run ' + runId + ' did not finish within ' + timeoutMs + 'ms');
  }
}

module.exports = {
  GOVERNED_TASK_SCHEMA_VERSION,
  TASK_API_DEFAULT_URL,
  isOwnedTaskApiUrl,
  validateTaskApiRun,
  TaskApiClient,
};
