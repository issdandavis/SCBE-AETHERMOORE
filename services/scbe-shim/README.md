# scbe-shim — Cloudflare Worker

OpenAI-compatible governance proxy. Wraps any base LLM with SCBE
constrained-decoding + axiom checks + 4-tier decision (ALLOW /
QUARANTINE / ESCALATE / DENY).

## What you get

Send an OpenAI-compatible `POST /v1/chat/completions` and receive a
standard OpenAI response **plus** an `scbe_governance` field:

```json
{
  "id": "chatcmpl-scbe-...",
  "object": "chat.completion",
  "model": "Qwen/Qwen2.5-7B-Instruct",
  "choices": [{"index":0,"message":{"role":"assistant","content":"..."},"finish_reason":"scbe_governed"}],
  "usage": {"prompt_tokens":0,"completion_tokens":0,"total_tokens":0},
  "scbe_governance": {
    "version": "0.1.0",
    "decision": "ALLOW",
    "harmonic_score": 0.7891,
    "reasons": [],
    "suggested_correction": null,
    "intervention": null,
    "audit": {
      "input_sha256_16": "0123456789abcdef",
      "output_sha256_16": "fedcba9876543210",
      "provider": "huggingface",
      "model": "Qwen/Qwen2.5-7B-Instruct"
    }
  }
}
```

## Endpoints

| Path | Method | Purpose |
|---|---|---|
| `/v1/chat/completions` | POST | Governed OpenAI-compatible chat |
| `/v1/health` | GET | Service + upstream model check |
| `/v1/scorecard` | GET | Internal benchmark numbers |

## Deploy (free tier, 100K req/day)

```bash
npm install
npx wrangler login
npx wrangler secret put HF_TOKEN   # paste your HuggingFace inference token
npx wrangler deploy
```

You get a `https://scbe-shim.<account>.workers.dev` URL. Point any
OpenAI SDK at it by setting `OPENAI_BASE_URL=https://scbe-shim.<account>.workers.dev/v1`.

## Optional KV cache

To enable response caching (cheaper, faster repeat requests):

```bash
npx wrangler kv:namespace create SHIM_CACHE
# paste returned id into wrangler.toml [[kv_namespaces]] block
npx wrangler deploy
```

## What this MVP includes

- **Petri-173 pre-filter** — 22 deterministic regex anchors that catch
  86% of known meta-AI auditor phrasing on the local Petri corpus.
  Ported from `src/cli/petri_pattern_filter.py`.
- **5 axiom checks on model output** — surface heuristics for
  unitarity / locality / causality / symmetry / composition.
- **Harmonic decision** — `H(d, pd) = 1 / (1 + phi*d + 2*pd)` with
  bands tuned for the four-tier verdict.
- **Redaction in QUARANTINE** — keeps the answer useful, replaces only
  the line(s) that violated locality/symmetry.
- **Refusal fallback in ESCALATE/DENY** — uniform safe response.

## What this MVP does NOT include

- The full 14-layer pipeline (Poincare embedding, Mobius phase,
  spectral coherence). Those live in the main repo's
  `src/harmonic/pipeline14.ts` and need a heavier runtime than a
  50-ms Worker. Either pull select layers in, or call a separate
  HF Space / VPS endpoint for full evaluation when budget allows.
- Streaming responses. SSE upgrade is straightforward but not v0.1.
- Per-user rate limits, billing, tenant isolation. Add via
  Cloudflare API Shield + KV when you go from demo to product.

## Local development

```bash
npm run dev        # starts wrangler dev with hot reload
curl -X POST http://127.0.0.1:8787/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"hello"}]}'
```

## Type check

```bash
npm run typecheck
```
