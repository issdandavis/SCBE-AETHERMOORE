# Productization Roadmap — SCBE-AETHERMOORE Subcomponents

> Status: living document. Maturity claims below are grounded in the repo as of
> June 2026 — file paths and test counts were verified by running the suites,
> not estimated.

## 1. The honest framing

**A pre-revenue repository has no objective dollar valuation.** Value = market
size × execution × traction, and traction is currently zero: Stripe is wired,
packages are published (npm + PyPI v4.2.1), but there is no evidence of paying
users. Patent-pending status, CAGE code, and SAM registration are *credibility
signals* that shorten enterprise sales conversations — they are not revenue and
no acquirer prices them as such.

Two further honest constraints:

- The repo is a hybrid of production code, research proposals, and
  worldbuilding (by the README's own admission). The sellable surface is a
  **subset**, and buyers will judge the subset, not the whole.
- The hyperbolic-geometry / Sacred Tongues novelty is a **differentiator to
  defend in a technical deep-dive, not the pitch**. The market category with
  actual pull is *AI agent governance / guardrails* — a funded, named category
  (Lakera, Protect AI, Robust Intelligence→Cisco, Guardrails AI, NVIDIA NeMo
  Guardrails). Lead with the problem those buyers already have.

## 2. Candidate inventory (verified)

| Subsystem | What it does | Maturity (verified) | Market analog | Extractability |
|---|---|---|---|---|
| **Governance gate / 14-layer pipeline** | Deterministic ALLOW / QUARANTINE / ESCALATE / DENY decisions over agent behavior, with signed receipts | `src/harmonic/` (50+ files), npm export `scbe-aethermoore/harmonic`; L1–L6 tiered test suites | Guardrails AI, NeMo Guardrails, Lakera Guard | Medium — core is clean; needs a thin, zero-config wrapper |
| **GeoSeal** | Geometric RAG immune system: quarantines adversarial/off-grammar retrievals via Poincaré-ball repulsion + phase discipline | `src/geoseal*.py` + TS ports; **303 tests passing across 8 suites** (v1, v2, routing, cursor, compass, operator-space, CLI); RAG integration (`src/geosealRAG.ts`); now deployment-tunable via `GeoSealConfig` | No direct analog — adjacent: RAG security filters (Lakera RAG, Protect AI) | **High — most self-contained mature piece in the repo** |
| **Agent Bus** | Thin agent coordination spine: routed ops, ML-DSA-65–signed append-only audit log, schema-versioned events, replay/verify CLI, circuit breakers, cost metering + enforced budgets | `agents/agent_bus*.py` (10 modules + CLI); schema 1.1.0; 32 dedicated tests; notes file tracks Tier 1–4 queue | LangSmith/LangFuse (observability), AgentOps | Medium — depends on scraper/browser modules for full ops |
| **code_prism** | Code analysis / IR emitter, multi-language | `src/code_prism/`, PyPI CLI `scbe-code-prism` | Semgrep-lite territory (crowded) | Medium |
| **PQC crypto layer** | ML-KEM-768 / ML-DSA-65 envelopes, spiral seal | `src/crypto/`, npm export, liboqs-backed | Many (PQC libraries are commoditizing) | Low as standalone; high as *feature* of the above |
| **Symphonic/audio, gacha, game, story systems** | Worldbuilding + research | Various | — | Not product candidates; keep out of the pitch |

## 3. Top two candidates

### #1 — "Signed-receipt guardrail" (governance gate, open-core)

The wedge: **a drop-in guardrail that produces a cryptographically signed audit
trail for every AI decision.** This is the dev-tool → compliance bridge: the
same engine serves both buyers.

- Free (MIT, drives adoption): local CLI + library — score/gate prompts and
  outputs, deterministic decisions, local JSONL receipts. Zero config, one
  `npx`/`pipx` command to first result.
- Paid: hosted API, multi-tenant dashboard, **audit retention + receipt
  verification service**, policy management, SSO, SLA. The compliance buyer
  pays for retention and attestation, not for the math.
- Differentiators to hold in reserve for deep-dives: deterministic decisions
  (replayable — auditors care), PQC-signed receipts (ML-DSA-65 — quantum-safe
  audit trail is a real procurement checkbox), exponential cost-scaling of
  adversarial drift (the hyperbolic story, told last).

### #2 — GeoSeal as a focused RAG-security dev tool

Today's audit confirms GeoSeal is the **most extractable mature component**:
dual-language, 300+ passing tests, self-contained math, a working RAG filter
(`filterRetrievals`), and now per-deployment tuning. Position: "an immune
system for your RAG pipeline — quarantines poisoned retrievals before they
reach the context window." RAG poisoning is a named OWASP-LLM risk with no
dominant tooling. Ship as its own small package (the `packages/sixtongues`
pattern already exists for standalone extraction).

## 4. Go-to-market for #1 (first 90 days)

1. **Weeks 1–3 — harden the wedge.** Extract a single package with one
   command: `scbe-gate check <input>` → decision + signed receipt. No config
   required, sane defaults. Kill every import that drags in worldbuilding.
2. **Weeks 3–5 — proof page.** A public benchmark page: detection rates on
   known prompt-injection corpora vs. NeMo Guardrails / Guardrails AI, plus
   "what a signed receipt proves" one-pager. Honest numbers or no page.
3. **Weeks 5–7 — launch.** Show HN / Product Hunt / r/LocalLLaMA with the
   receipt story. Instrument the CLI (opt-in telemetry) to find the retention
   curve.
4. **Weeks 7–13 — convert.** 3–5 design partners from inbound (target: teams
   shipping agents under SOC 2 / EU AI Act pressure). Their audit-retention
   needs define the first paid tier.

**Pricing model (shape, not numbers):** usage-based API tier (per-decision),
seat-based dashboard, enterprise tier keyed to **audit retention duration +
attestation**. Compliance buyers anchor on retention; that's the line item.

## 5. Hardening gaps (from the verified state)

- **Governance gate**: no standalone package yet (the npm export drags the
  full module graph); no zero-config entrypoint; benchmark corpus runs are
  ad-hoc rather than a published page.
- **GeoSeal**: TS/Python parity is manual (config dataclass exists in Python
  only as of this week — mirror `GeoSealConfig` into `geoseal.ts`); the RAG
  filter needs an `embedFn` failure path (currently uncaught).
- **Agent bus**: budget gate only bites once paid rates are configured;
  ledger HMAC (not PQC) under the signed events; browser-module coupling
  blocks slim extraction.
- **Repo-level**: a public-facing repo split (or aggressive README surgery)
  so a buyer's first 10 minutes land on the product subset, not the cosmology.

## 6. What this document deliberately does not do

- Invent a valuation figure.
- Lead with hyperbolic geometry, Sacred Tongues, or lore as the pitch.
- Treat patent filings, CAGE, or SAM as traction.
- Recommend the government/defense channel for this pass (per scope decision).
