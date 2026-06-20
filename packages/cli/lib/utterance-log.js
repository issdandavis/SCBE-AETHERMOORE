'use strict';

/**
 * @file utterance-log.js
 * @module cli/lib/utterance-log
 * @component SCBE Compass intent-router durable data hook
 *
 * Privacy-conscious LOCAL log of user utterances + the route they took, so the
 * intent router can graduate from synthetic cold-start data to REAL logged
 * phrasings. Empirically (CLINC150, 2026-06-06) synthetic K=10 examples capture
 * only ~44% of the human-data gain; real logged utterances are the durable lever.
 *
 * Design contract:
 *   - LOCAL ONLY. Never transmitted anywhere. Plain JSONL under the user's home.
 *   - Secret-redacting. Emails, API keys, bearer tokens, long digit runs, and
 *     overlong tokens are scrubbed BEFORE anything is written to disk.
 *   - Fail-open & silent. Logging must never break or slow routing: every public
 *     function swallows its own errors and returns a status instead of throwing.
 *   - Easy opt-out. SCBE_NO_UTTERANCE_LOG=1 disables all writes. Non-interactive
 *     harness modes (agent-json / minimal / CI) should pass { enabled: false }.
 *   - Closes the loop. buildCorpus() turns the log into { tool: [phrasings] } --
 *     the exact shape the few-shot centroid router consumes.
 */

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const SCHEMA_VERSION = 1;
const MAX_UTTERANCE_CHARS = 512;
const MAX_LOG_BYTES = 8 * 1024 * 1024; // rotate past 8 MB so the file never grows unbounded

/** Resolve the log path: env override > <home>/.scbe/utterance-log.jsonl. */
function defaultLogPath() {
  if (process.env.SCBE_UTTERANCE_LOG) {
    return process.env.SCBE_UTTERANCE_LOG;
  }
  const base = process.env.SCBE_HOME || path.join(os.homedir(), '.scbe');
  return path.join(base, 'utterance-log.jsonl');
}

function envTruthy(value) {
  return value !== undefined && value !== '' && value !== '0' && value !== 'false';
}

/** Whether logging is active. Opt-out via SCBE_NO_UTTERANCE_LOG; override via opts.enabled. */
function isEnabled(opts = {}) {
  if (opts.enabled === false) return false;
  if (opts.enabled === true) return true;
  return !envTruthy(process.env.SCBE_NO_UTTERANCE_LOG);
}

const REDACTIONS = [
  // order matters: most specific first
  [/\b[\w.+-]+@[\w-]+\.[\w.-]+\b/g, '[email]'],
  [
    /\b(?:sk|pk|rk|ghp|gho|ghu|ghs|github_pat|xox[baprs]|AKIA|ASIA)[-_][A-Za-z0-9_-]{8,}\b/g,
    '[secret]',
  ],
  [/\bBearer\s+[A-Za-z0-9._-]{8,}\b/gi, '[token]'],
  [/\b[A-Za-z0-9+/_-]{40,}\b/g, '[token]'], // hashes / long opaque tokens (40+ chars never natural words)
  [/\b\d{12,19}\b/g, '[number]'], // card / long account-number shaped runs
];

/** Scrub obvious secrets/PII and bound length. Pure, side-effect free. */
function redact(text) {
  if (typeof text !== 'string') return '';
  let out = text;
  for (const [pattern, replacement] of REDACTIONS) {
    out = out.replace(pattern, replacement);
  }
  out = out.replace(/\s+/g, ' ').trim();
  if (out.length > MAX_UTTERANCE_CHARS) {
    out = out.slice(0, MAX_UTTERANCE_CHARS);
  }
  return out;
}

function rotateIfLarge(logPath) {
  try {
    const stat = fs.statSync(logPath);
    if (stat.size >= MAX_LOG_BYTES) {
      fs.renameSync(logPath, `${logPath}.1`);
    }
  } catch (_err) {
    // no file yet, or rotation failed -- either way, keep going
  }
}

/**
 * Append one routed turn to the local log. Fail-open: returns false on any problem
 * (disabled, empty, write error) and never throws.
 *
 * @param {object} entry
 * @param {string} entry.utterance  raw user text (will be redacted here)
 * @param {string} [entry.tool]     routed tool/intent name (null if refused)
 * @param {number} [entry.score]    router confidence
 * @param {string} [entry.decision] gate decision (ROUTE / CONFIRM / CLARIFY / REFUSE / ...)
 * @param {string} [entry.mode]     shell mode (ai / squad / ...)
 * @param {boolean}[entry.confirmed]true if the user accepted the route (strongest signal)
 * @param {object} [opts]           { enabled, logPath, now }
 * @returns {boolean} whether a line was written
 */
function logUtterance(entry = {}, opts = {}) {
  try {
    if (!isEnabled(opts)) return false;
    const utterance = redact(entry.utterance);
    if (!utterance) return false;
    const logPath = opts.logPath || defaultLogPath();
    fs.mkdirSync(path.dirname(logPath), { recursive: true });
    rotateIfLarge(logPath);
    const now = opts.now || new Date();
    const record = {
      v: SCHEMA_VERSION,
      ts: now.toISOString(),
      utterance,
      tool: entry.tool != null ? String(entry.tool) : null,
      score: typeof entry.score === 'number' ? Number(entry.score.toFixed(4)) : null,
      decision: entry.decision != null ? String(entry.decision) : null,
      mode: entry.mode != null ? String(entry.mode) : null,
      confirmed: entry.confirmed === true,
    };
    fs.appendFileSync(logPath, `${JSON.stringify(record)}\n`, 'utf8');
    return true;
  } catch (_err) {
    return false; // never let logging break the shell
  }
}

/** Read all valid JSONL records (silently skips corrupt lines and missing files). */
function readLog(logPath = defaultLogPath()) {
  const out = [];
  let raw;
  try {
    raw = fs.readFileSync(logPath, 'utf8');
  } catch (_err) {
    return out;
  }
  for (const line of raw.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    try {
      out.push(JSON.parse(trimmed));
    } catch (_err) {
      // skip the bad line, keep the rest
    }
  }
  return out;
}

const ROUTE_DECISIONS = new Set(['ROUTE', 'ROUTE_CONFIRM', 'ALLOW', 'CONFIRM']);

/**
 * Turn the log into a per-tool training corpus: { tool: [unique phrasings] }.
 * This is the exact shape the few-shot centroid router / synthesis experiment use,
 * so logged real utterances drop straight into centroid building.
 *
 * @param {object} [options]
 * @param {string} [options.logPath]
 * @param {number} [options.minScore=0]      keep only routes at/above this confidence
 * @param {boolean}[options.confirmedOnly=false] keep only user-accepted routes
 * @param {boolean}[options.routedOnly=true]  drop refused/clarify turns (no clean label)
 * @param {number} [options.maxPerTool=Infinity] cap phrasings per tool (most-recent kept)
 * @returns {Object<string,string[]>}
 */
function buildCorpus(options = {}) {
  const {
    logPath = defaultLogPath(),
    minScore = 0,
    confirmedOnly = false,
    routedOnly = true,
    maxPerTool = Infinity,
  } = options;
  const records = readLog(logPath);
  const seen = new Map(); // tool -> Set(lowercased) for dedup
  const corpus = {};
  for (const r of records) {
    if (!r.tool) continue;
    if (routedOnly && r.decision && !ROUTE_DECISIONS.has(r.decision)) continue;
    if (confirmedOnly && r.confirmed !== true) continue;
    if (typeof r.score === 'number' && r.score < minScore) continue;
    const text = (r.utterance || '').trim();
    if (!text) continue;
    const key = text.toLowerCase();
    if (!seen.has(r.tool)) {
      seen.set(r.tool, new Set());
      corpus[r.tool] = [];
    }
    const dedup = seen.get(r.tool);
    if (dedup.has(key)) continue;
    dedup.add(key);
    corpus[r.tool].push(text);
    if (corpus[r.tool].length > maxPerTool) {
      corpus[r.tool].shift(); // keep most recent
    }
  }
  return corpus;
}

/** Quick health summary for `stats` / monitoring. */
function stats(logPath = defaultLogPath()) {
  const records = readLog(logPath);
  const perTool = {};
  let routed = 0;
  let refused = 0;
  let first = null;
  let last = null;
  for (const r of records) {
    if (r.tool) {
      perTool[r.tool] = (perTool[r.tool] || 0) + 1;
      routed += 1;
    } else {
      refused += 1;
    }
    if (r.ts) {
      if (!first || r.ts < first) first = r.ts;
      if (!last || r.ts > last) last = r.ts;
    }
  }
  return {
    total: records.length,
    routed,
    refused,
    tools: Object.keys(perTool).length,
    perTool,
    first,
    last,
  };
}

module.exports = {
  SCHEMA_VERSION,
  defaultLogPath,
  isEnabled,
  redact,
  logUtterance,
  readLog,
  buildCorpus,
  stats,
};

// ---------------------------------------------------------------------------
// Standalone CLI so the log is usable TODAY without touching the (mid-rewrite)
// shell:  node lib/utterance-log.js <path|stats|export> [--min N] [--confirmed]
// ---------------------------------------------------------------------------
if (require.main === module) {
  const [cmd, ...rest] = process.argv.slice(2);
  const flag = (name) => rest.includes(name);
  const opt = (name, def) => {
    const i = rest.indexOf(name);
    return i >= 0 && rest[i + 1] ? rest[i + 1] : def;
  };
  if (cmd === 'path') {
    process.stdout.write(`${defaultLogPath()}\n`);
  } else if (cmd === 'stats') {
    process.stdout.write(`${JSON.stringify(stats(), null, 2)}\n`);
  } else if (cmd === 'export') {
    const corpus = buildCorpus({
      minScore: Number(opt('--min', '0')),
      confirmedOnly: flag('--confirmed'),
    });
    process.stdout.write(`${JSON.stringify(corpus, null, 1)}\n`);
  } else {
    process.stderr.write(
      'usage: node lib/utterance-log.js <path|stats|export> [--min N] [--confirmed]\n' +
        '  path    print the local log file location\n' +
        '  stats   per-tool counts + date range\n' +
        '  export  emit { tool: [phrasings] } corpus for few-shot centroids\n'
    );
    process.exitCode = 2;
  }
}
