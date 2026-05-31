# Free AI on Rails: No Custom Model Required

> SCBE makes cheap AI useful by moving intelligence out of the model and into
> the governed workspace, legal-move system, and audit chain.

---

## The problem with agent platforms today

Models chat. They don't act safely, remember context, or leave clean audit
trails. Most agent platforms solve this by training a better model. That is
expensive, fragile, and requires you to trust someone else's alignment work.

SCBE solves it differently.

**Don't replace the model. Put it on rails.**

---

## How it works

```
Free AI proposes.
SCBE validates.
The agent bus executes.
Receipts prove what happened.
```

Any LLM can propose an action — which file to ingest, which export to ship,
which task to run. SCBE controls whether that action is a legal move. The model
quality determines how good the suggestions are. The board determines what
actually executes.

---

## 1. No Custom Model Required

SCBE is model-agnostic. You do not need a fine-tuned or specially-aligned model
to get governed behavior. Bring what you already have:

- **Pollinations** — free, no API key
- **Ollama** — local, offline, no account
- **Groq** — fast free-tier inference
- **OpenAI / Claude / Gemini** — BYOK
- **Any OpenAI-compatible endpoint**

Use whatever AI you already have. SCBE sits underneath them as the rules
engine, action bus, audit chain, and workspace memory.

---

## 2. Free/Local First

Pollinations and Ollama can run useful production workflows through SCBE
because the board supplies all the structure the model lacks:

| What the model can't provide | What SCBE provides |
|---|---|
| Memory across runs | Persistent workspace (`00_inbox → 30_exports`) |
| Proof of what happened | Governance receipts (sha256-anchored, replayable) |
| Safe action boundaries | Legal-move catalog (only known verbs execute) |
| Tamper detection | Export + verify chain |
| Compliance trail | Lineage audit (`formation → ingest → export → verify`) |

A free Ollama model calling `workspace ingest → export → verify` produces a
cryptographically-auditable handoff package. The free model did not need to
understand sha256 or tamper detection — SCBE did that.

---

## 3. Model Upgrade Path

Better models improve proposal quality. They do not change the safety or audit
architecture.

| Tier | Model | What changes |
|---|---|---|
| **Free local** | Ollama / Pollinations | Slower, rougher suggestions; same governed execution |
| **Free cloud** | Groq free-tier | Faster suggestions; same governed execution |
| **Paid BYOK** | GPT-4o / Claude / Gemini | Higher-quality proposals; same governed execution |
| **Custom fine-tune** | Your own adapter | Domain-specific suggestions; same governed execution |

The board is the constant. The model is a dial.

Custom model training becomes optional later — useful for narrowing the
suggestion space in a specific domain, not required for the product to have value.

---

## 4. The Agent Bus: Legal Verbs Only

Models interact with SCBE through a fixed verb catalog. They cannot pass raw
shell strings or escalate beyond their permitted scope.

**Workspace verbs:**

| Verb | What it does |
|---|---|
| `workspace new` | Create an auditable working area |
| `workspace ingest` | Pull a file in with provenance receipt |
| `workspace export` | Package work with sha256 manifest |
| `workspace verify` | Re-hash every file, confirm tamper status |
| `workspace import` | Cold-restore from a verified export |
| `workspace lineage` | Read the full chronological audit chain |
| `workspace report` | Dashboard: folder counts, audit health color |

**Event verbs:**

| Verb | What it does |
|---|---|
| `send` | Dispatch one governed task through the harmonic-wall pipeline |
| `batch` | Sequence of governed tasks, stops on first failure by default |
| `health` | Backend liveness check |

The model proposes which verb to call and with what arguments. SCBE validates
that the call is a legal move before it executes. If the proposed move is not in
the catalog or fails a precondition, it does not execute — period.

---

## 5. Why This Sells

**Same buyer category as agent platforms, eval tools, and code-review
assistants — but cheaper to start.**

The pitch to a buyer who already has AI fatigue:

> You have a model. It's already expensive. You don't need a different model.
> You need the thing that makes your model safe to hand tasks to, keeps receipts
> of what it did, and lets your auditors replay any decision without re-running
> the model.

**Competitive positioning:**

| What others sell | What SCBE adds |
|---|---|
| "Better model" | Model-independent execution control |
| "Safer fine-tune" | Tamper-evident audit chain regardless of model |
| "Agent platform" | Governed workspace with legal-move enforcement |
| "Eval harness" | Production enforcement, not just measurement |

**Pricing consequence:** Because Ollama and Pollinations work out of the box,
the entry point is zero compute cost. The buyer proves the workflow is valuable
before spending on a paid model or hosted run. That removes the main objection
("what if this doesn't work for my use case") before any money changes hands.

---

## The one-line version

> SCBE doesn't replace your AI. It tells your AI what it's allowed to do —
> and writes down everything that happened.

---

*See also:*
- `docs/SCBE_AETHERMOORE_ONE_PAGER.md §1.1` — GeoBoard execution model
- `packages/agent-bus/README.md` — full CLI and TypeScript API reference
- `docs/SPEC.md` — canonical governance specification
