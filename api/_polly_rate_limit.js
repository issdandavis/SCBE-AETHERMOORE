'use strict';

// Per-IP sliding-window rate limiter. In-memory per Vercel function instance,
// so it does not share state across cold starts or instances — a determined
// attacker hitting different invocations can bypass it. The point is not
// fortress-grade abuse prevention, just a defense against single-IP burst
// floods that would otherwise drain Vercel function invocations, HF commits,
// GitHub workflow runs, and (when wired) outbound email.
//
// For real-grade protection, swap the in-memory Map for Vercel KV or Upstash
// Redis and key on user_id where available.

const buckets = new Map();

const DEFAULT_WINDOW_MS = 60_000;
const DEFAULTS = {
  chat: { limit: 30, windowMs: DEFAULT_WINDOW_MS },
  lead: { limit: 5, windowMs: DEFAULT_WINDOW_MS },
  hosted_run: { limit: 8, windowMs: DEFAULT_WINDOW_MS },
  feedback: { limit: 60, windowMs: DEFAULT_WINDOW_MS },
};

function clientIp(req) {
  const forwarded = req && req.headers && req.headers['x-forwarded-for'];
  if (typeof forwarded === 'string' && forwarded.length > 0) {
    return forwarded.split(',')[0].trim();
  }
  const real = req && req.headers && req.headers['x-real-ip'];
  if (typeof real === 'string' && real.length > 0) return real.trim();
  return 'unknown';
}

function envLimit(name, fallback) {
  const upper = name.toUpperCase();
  const limit = Number(process.env[`POLLY_RATE_LIMIT_${upper}`] || fallback.limit);
  const windowMs = Number(process.env[`POLLY_RATE_LIMIT_${upper}_WINDOW_MS`] || fallback.windowMs);
  return {
    limit: Number.isFinite(limit) && limit > 0 ? limit : fallback.limit,
    windowMs: Number.isFinite(windowMs) && windowMs > 0 ? windowMs : fallback.windowMs,
  };
}

function check({ name, ip, now }) {
  const fallback = DEFAULTS[name] || DEFAULTS.chat;
  const cfg = envLimit(name, fallback);
  const key = `${name}:${ip}`;
  const horizon = now - cfg.windowMs;
  const existing = buckets.get(key) || [];
  // Drop timestamps that fell out of the window.
  const recent = existing.filter((t) => t >= horizon);
  if (recent.length >= cfg.limit) {
    const oldest = recent[0];
    const retryAfterMs = Math.max(0, oldest + cfg.windowMs - now);
    return {
      allowed: false,
      remaining: 0,
      limit: cfg.limit,
      windowMs: cfg.windowMs,
      retryAfterMs,
    };
  }
  recent.push(now);
  buckets.set(key, recent);
  // Best-effort GC: evict buckets with no recent activity to bound memory.
  if (buckets.size > 5000) {
    for (const [k, ts] of buckets) {
      if (!ts.length || ts[ts.length - 1] < horizon) buckets.delete(k);
    }
  }
  return {
    allowed: true,
    remaining: cfg.limit - recent.length,
    limit: cfg.limit,
    windowMs: cfg.windowMs,
    retryAfterMs: 0,
  };
}

function enforce(req, res, name) {
  const ip = clientIp(req);
  const result = check({ name, ip, now: Date.now() });
  res.setHeader('X-RateLimit-Limit', String(result.limit));
  res.setHeader('X-RateLimit-Remaining', String(Math.max(0, result.remaining)));
  if (!result.allowed) {
    res.setHeader('Retry-After', String(Math.ceil(result.retryAfterMs / 1000)));
  }
  return result;
}

function reset() {
  buckets.clear();
}

module.exports = {
  enforce,
  check,
  clientIp,
  reset,
  _buckets: buckets,
  DEFAULTS,
};
