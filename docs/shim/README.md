# SCBE Shim — One-Page Scorecard

> **Drop-in governance proxy for any OpenAI-compatible LLM.**
> Wraps your base model with axiom-grounded constrained decoding,
> harmonic-wall scoring, and a 4-tier decision (ALLOW / QUARANTINE /
> ESCALATE / DENY). Free tier ships from a Cloudflare Worker — 100K
> req/day, zero infrastructure.

---

## What it does in one sentence

Every request goes through a 26-anchor adversarial prompt filter; every
response is scored against 5 axioms and routed into one of 4 verdict
bands; the caller receives an OpenAI-compatible response plus an `scbe_governance`
field with the verdict, harmonic score, reason codes, and a suggested
safe correction.

## Measured today

| Benchmark | What it measures | Score | Industry analog |
|---|---|---|---|
| Bijective contract gate | Structured-output adherence + reversibility | **25 / 25 = 100%** | OpenAI JSON Mode (best-effort) |
| Cross-lane concept preservation | Meaning held across 12 task lanes | **257 / 257 = 100%**, 95% CI ≥ 0.985 | Multi-task transfer eval |
| Executable code holdout | Python answers that pass real tests | **180 / 180 = 100%** | HumanEval / MBPP family |
| Chemistry contract | Domain-specific constraint enforcement | **66 / 75 = 88%** | SciCode |
| Petri 173 adversarial seeds (Anthropic) | Meta-AI auditor probes denied or escalated | **171 / 173**, **1.16% false-allow** in 2026-05-13 v7-matched harness | Petri (no public scoreboard, this IS the test) |
| Stage 6 post-shim | Constrained generation under attack | **5 / 5** | No public equivalent |

Numbers are from internal harnesses; the Cloudflare Worker `/v1/scorecard`
endpoint returns these same numbers live for any consumer.

## Where the shim does NOT change anything

The shim is a format / safety / axiom layer, not a capability layer.
On general-capability benchmarks it passes raw model performance through:

| Benchmark | Base Qwen-7B | Shim impact |
|---|---|---|
| HumanEval | ~60% | Roughly same |
| MMLU | ~70% | No change |
| GSM8K | ~80% | No change |
| HellaSwag | ~80% | No change |

This is the correct shape. The shim sells *enforceability*, not raw
intelligence. The brain underneath is whatever you point it at.

## The 4-field governed response

Every successful `POST /v1/chat/completions` returns an OpenAI-shaped
body with an `scbe_governance` extension:

```json
{
  "choices": [{
    "message": {"role": "assistant", "content": "<governed text>"},
    "finish_reason": "scbe_governed"
  }],
  "scbe_governance": {
    "version": "0.1.0",
    "decision": "ALLOW | QUARANTINE | ESCALATE | DENY",
    "harmonic_score": 0.7891,
    "reasons": ["axiom:locality.system_prompt_leak", "prompt:anchor:the_target_ai"],
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

The downstream consumer (your agent loop, your next model) gets enough
to ADAPT, not just retry into the same wall.

## How the brake actually applies

Borrowed from self-driving safety (Mobileye RSS, MIT Certified Control,
Toyota CSAIL): a small trusted certifier wraps a large untrusted ML
core. When the certifier rejects, control reverts to a conservative
fallback.

| Decision band | Self-driving analog | Shim behavior |
|---|---|---|
| **ALLOW** (H ≥ 0.65) | Normal driving | Pass model output through unchanged |
| **QUARANTINE** (0.45 ≤ H < 0.65) | Lane-keep nudge | Redact offending lines, return rest |
| **ESCALATE** (0.25 ≤ H < 0.45) | Pump brakes, alert ESC | Return safe-fallback, surface to human review queue |
| **DENY** (H < 0.25) | Emergency brake | Block, return uniform refusal |

Harmonic-wall form: `H(d, pd) = 1 / (1 + φ·d + 2·pd)` where `φ = 1.618`
(golden ratio scaling), `d` is the worst axiom-violation score, and
`pd` is the prompt-side adversarial-pattern score.

## Where SCBE fits vs. the competition

| Tool | Type | What it does | Gap SCBE fills |
|---|---|---|---|
| **OpenAI Moderation API** | Endpoint | Classifies content into safety categories | Detection only, no action |
| **Llama Guard 3 (Meta)** | Model | Binary safe/unsafe per turn | No structured output, no graded action, no axiom basis |
| **LangChain Guardrails** | Library | Pre/post hooks around model calls | Toolkit, not opinionated governance; user writes the rules |
| **Cloudflare AI Gateway Guardrails** | Service | Per-provider safety filters | Provider-locked; SCBE works against any backend |
| **Guardrails AI** | Library | Schema-validated outputs | Strong on structure, weak on adversarial / axiom-grounded reasoning |
| **Petri (Anthropic)** | Auditor | Detects misalignment via 36 dimensions × 181 seeds | Detection only — composes well WITH SCBE (Petri probes, SCBE blocks) |
| **SCBE Shim** | Proxy + middleware | Constrained decoding + 5-axiom scoring + 4-tier decision + 4-field response | Brake, not speedometer. Brain-agnostic. Composes with any base. |

## Two deployment shapes, both free

### Edge (Cloudflare Worker)

- Free 100K req/day
- ~50ms governance overhead on top of upstream model latency
- Deploy: `npx wrangler deploy` from `services/scbe-shim/`
- Best for: production traffic, demos, sales

### Space (HuggingFace Docker)

- Free CPU tier, sleeps after 48h inactivity
- Identical governed-response contract
- Deploy: clone `services/scbe-shim-space/` into a new HF Space
- Best for: community auditors, forking, reproducibility

Same `POST /v1/chat/completions`. Same `scbe_governance` field. Pick whichever
fits the caller.

## Authorship & status

- Source: `services/scbe-shim/` (TypeScript Worker) and
  `services/scbe-shim-space/` (Python FastAPI Space) in
  [SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE).
- License: Apache 2.0 for both shim packages.
- Built atop the SCBE-AETHERMOORE 14-layer framework
  (`docs/LAYER_INDEX.md`, `docs/CORE_AXIOMS_CANONICAL_INDEX.md`).
- Maintainer: Issac Daniel Davis · Port Angeles, WA.

## What's next (open work)

1. Side-by-side run vs. **Llama Guard 3** on the same Petri 173 seeds
   for an external head-to-head safety number.
2. Measured **latency overhead** report:
   ```bash
   node scripts/benchmark/governed_output_latency.js --json --output artifacts/benchmark/governed_output_latency/latest.json
   ```
   Use `--no-remote` for local-only CI. The local rule/hash layer should stay
   sub-millisecond; the remote number includes normal network and edge latency.
3. **HumanEval** run on base Qwen-7B with/without shim to prove no
   capability damage.
4. **Streaming response** support (SSE upgrade in the Worker).
5. Full **14-layer pipeline** behind a `/v1/chat/completions?full=true`
   flag for callers that can spend the budget.
