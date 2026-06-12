# SCBE-AETHERMOORE — Systems Catalog & Use Guide

**Generated:** 2026-06-10
**Purpose:** Inventory every real, code-backed system in the stack; classify each by what it's *for*; label each for reuse in future projects; compare to the closest industry product; give a short "how you'd actually use it" guide.
**Method:** Four parallel read-only code surveys of `src/`, `packages/`, `agents/`, `hydra/`, `workflows/`, `scripts/research/`, plus the storage inventory of sibling repos. Only systems that exist in code are listed. Maturity and "industry honesty" notes reflect the actual code, not the pitch.

---

## How to read the labels

**Use-category** — what job the system does:
`GOVERNANCE` · `CRYPTO/AUTH` · `ORCHESTRATION` · `SURFACE/PRODUCT` · `RESEARCH` · `SEMANTICS`

**Reuse label** — how ready it is to lift into a new project:
- 🟢 **REUSABLE-LIB** — clean API, tested, drop into a new project today.
- 🔵 **PRODUCT** — a shipping/near-shipping user surface (CLI, service, package).
- 🟡 **WIRED-EXPERIMENT** — works and is wired in, but tied to SCBE internals; lift with care.
- 🟠 **RESEARCH-ONLY** — an instrument/probe; the *findings* are the value, not the runtime.
- ⚪ **SCAFFOLD** — early/MVP or duplicate; treat as a starting point, not a dependency.

**Honesty note** — where the code or our own benchmarks undercut a marketing claim, it's said plainly. (E.g. our own gate data shows Euclidean ≈ or > hyperbolic on the synthetic task — so the sellable edge is the *governed gate + receipts*, not the geometry superlatives.)

---

# 1. Governance & Safety Core — `GOVERNANCE`

The actual product spine: a decision gate that sits between an LLM's intent and a real action, and emits ALLOW / QUARANTINE / ESCALATE / DENY with an auditable cost.

### Runtime Governance Gate — 🟡 WIRED-EXPERIMENT
- **Path:** `src/governance/runtime_gate.py` (+ `tree_of_escalation.py`)
- **Does:** Scores an intent on tongue coordinates + spin vector + harmonic cost, returns a decision and a reason. Cheap for safe ops, expensive for dangerous, ∞ for impossible. This is the load-bearing piece.
- **Industry equivalent:** NVIDIA NeMo Guardrails, Llama Guard 3, Lakera Guard, Protect AI. Those classify text; this returns a *cost-scored, reasoned decision with a receipt* — that's the differentiator worth selling.
- **Honesty note:** The "14-layer hyperbolic" framing is not where the edge lives — our own gate benchmarks show simpler/Euclidean baselines match or beat it on the synthetic task. Sell the **gate + receipt + governance-tongue basis**, drop the geometry superlatives.
- **Use guide:** Call the gate class with an intent string; branch on the returned decision; persist the receipt. This is the thing to wrap in any agent loop you build.

### 14-Layer Harmonic Pipeline — 🟡 WIRED-EXPERIMENT
- **Path:** `src/harmonic/` (TypeScript-canonical), Python reference in `symphonic_cipher/`
- **Does:** The full L1–L14 transform chain (Poincaré embed → hyperbolic distance → breathing/Möbius → harmonic wall `H = 1/(1+φ·d_H+2·pd)`).
- **Industry equivalent:** Bespoke; closest is a feature-extraction pipeline feeding a guardrail classifier.
- **Use guide:** Import `src/harmonic/index.ts`. Most projects only need the harmonic wall scorer (L12) and the gate (L13) — the rest is internal machinery.

### Quantum Axiom Framework — 🟡 WIRED-EXPERIMENT
- **Path:** `symphonic_cipher/scbe_aethermoore/axiom_grouped/`
- **Does:** Maps the 14 layers onto 5 invariants (Unitarity, Locality, Causality, Symmetry, Composition) and runs verification decorators. This is the "why is this safe" audit harness. ~226 cumulative tests.
- **Industry equivalent:** Property-based invariant testing (Hypothesis/fast-check) formalized into a domain framework.
- **Use guide:** Use `verify_all_axioms()` as a CI gate on any pipeline change.

### Security-Engine (Policy Fields) — 🟢 REUSABLE-LIB
- **Path:** `src/security-engine/` (TypeScript)
- **Does:** Context-coupled decision engine with overlapping policy fields (Safety/Compliance/Resource/Trust/Role/Temporal). Cleaner, more portable than the Python gate.
- **Industry equivalent:** OPA / Cedar (policy-as-code), but context-coupled rather than rule-list.
- **Use guide:** `ContextCoupledSecurityEngine` is the most lift-friendly governance component for a TS project.

---

# 2. Cryptography & Authentication — `CRYPTO/AUTH`

### Aether MFA — 🟢 REUSABLE-LIB
- **Path:** `packages/aether-mfa`
- **Does:** TOTP/HOTP (RFC 6238) + Ed25519 push-approval with action-binding and number-matching. No rolled crypto; RFC test vectors pass.
- **Industry equivalent:** Duo, Authy, Auth0 Guardian. This is "MFA for AI agent actions" — bind approval to a *specific action*, which the consumer products don't do.
- **Use guide:** `import aether_mfa as mfa`. Genuinely the cleanest reusable thing in the stack — ship it as its own package.

### Post-Quantum Crypto — 🟢 REUSABLE-LIB
- **Path:** `src/crypto/` (`pqc.ts`, `pqc_liboqs.py`)
- **Does:** ML-KEM-768 (Kyber) + ML-DSA-65 (Dilithium) via liboqs, with name-fallback for liboqs renames. NIST FIPS 203/204.
- **Industry equivalent:** liboqs, AWS-LC, Cloudflare CIRCL. This is a thin governed wrapper over liboqs, not new crypto — which is correct and honest.
- **Use guide:** Use the `_select_kem_algorithm()` / `_select_dsa_algorithm()` helpers; don't hard-code algorithm names.

### Secret Store / Token Vault — 🟢 REUSABLE-LIB
- **Path:** `src/security/secret_store.py`
- **Does:** env-first secret resolution, text redaction (strips keys/tokens/passwords), PBKDF2 fingerprinting.
- **Industry equivalent:** HashiCorp Vault (lite), `python-dotenv` + a redactor.
- **Use guide:** `get_secret()` / `redact_sensitive_text()` — wire the redactor into any log path.

### SixTongues Encoder — ⚪ SCAFFOLD
- **Path:** `packages/sixtongues`
- **Does:** Bijective byte↔token mapping over 6 tongues (256 tokens each). Reversible encoding, not encryption.
- **Industry equivalent:** A custom base-256 codec; closest framing is a reversible tokenizer.
- **Use guide:** Demo-grade. Useful as a deterministic obfuscation/labeling layer, not a security control.

---

# 3. Multi-Agent Orchestration — `ORCHESTRATION`

The deepest, most novel cluster. If you productize one thing beyond the gate, it's here.

### Agent Bus (TypeScript package) — 🟢 REUSABLE-LIB / 🔵 PRODUCT
- **Path:** `packages/agent-bus` (published npm `scbe-agent-bus` v0.4.2)
- **Does:** Typed, governed multi-agent event routing through the pipeline; multi-bridge (mail/AI/webhook/fs), Zod-validated handoff packets, audit-chain workspaces, 25 built-in tools. ~29 test files — the best-tested system in the repo.
- **Industry equivalent:** LangGraph, CrewAI, AutoGen, OpenAI Swarm. The differentiator: **every handoff is governed + receipted**. None of the mainstream frameworks gate handoffs.
- **Use guide:** Most reusable orchestration layer. `import` the package; define agents; route via the bus. Start here for any new multi-agent project.

### HYDRA — 🟡 WIRED-EXPERIMENT
- **Path:** `hydra/` (40+ Python files; `ledger.py` is the keystone)
- **Does:** Central orchestrator — Spine/Heads/Limbs, BFT consensus, and an HMAC-signed SQLite ledger for cross-session memory/audit (17+ entry types).
- **Industry equivalent:** Temporal/Airflow (durable orchestration) crossed with an audit ledger. The signed ledger is the reusable gem.
- **Use guide:** Lift `hydra/ledger.py` standalone — it's portable and works anywhere Python runs. The full orchestrator is heavier.

### Fleet (Manager / Dispatcher / Governance / Swarm) — 🟡 WIRED-EXPERIMENT
- **Path:** `src/fleet/` (TypeScript, 50+ files)
- **Does:** Agent registry, capability/trust-scored task dispatch, Sacred-Tongue roundtable consensus, Polly dimensional swarm with flux ODE dynamics, per-node governance kernel with hard invariants.
- **Industry equivalent:** Ray/Dask (dispatch) + a governance layer; `node-kernel.ts` resembles a robotics safety governor (signed policy epochs, hard no-go invariants).
- **Use guide:** `node-kernel.ts` (`evaluateProposal()`) is the standout — a signed, deterministic safety kernel reusable for robotics/embodied agents.

### Juggling Scheduler — 🟡 WIRED-EXPERIMENT
- **Path:** `src/fleet/juggling-scheduler.ts` (+ `hydra/juggling_scheduler.py`)
- **Does:** Models task coordination as physics juggling — TaskCapsules thrown between AgentSlots, catch windows, drop recovery, siteswap patterns.
- **Industry equivalent:** Genuinely novel framing; functionally a deadline-aware scheduler with backpressure.
- **Use guide:** Niche but distinctive. Use when you need deadline-window handoffs with explicit drop/recovery semantics.

### Red/Blue Arena — 🟡 WIRED-EXPERIMENT
- **Path:** `src/security-engine/redblue-arena.ts`
- **Does:** Model-vs-model adversarial sim against the governance pipeline across 5 attack surfaces; provider-agnostic.
- **Industry equivalent:** Microsoft PyRIT, Garak, Lakera red-teaming. This is purpose-built to attack *your* gate.
- **Use guide:** Run it as a continuous adversarial test harness against any gate change.

### Agent Bus (Python) + Swarm/Browser agents — 🟡 WIRED-EXPERIMENT
- **Path:** `agents/agent_bus.py`, `agents/swarm_browser.py`, `agents/browser/phdm_brain.py`, `agents/antivirus_membrane.py`, `agents/kernel_antivirus_gate.py`
- **Does:** Free-tier governed pipeline (search→scrape→free-LLM→gated output) with circuit breaker; BFT 6-tongue browser swarm; Poincaré-radius containment for browser actions; threat-scan membrane; kernel-telemetry policy gate.
- **Industry equivalent:** Browser-Use/Skyvern (automation) + an antivirus/EDR policy layer.
- **Use guide:** `antivirus_membrane.scan_text_for_threats()` and `kernel_antivirus_gate.evaluate_kernel_event()` are clean, reusable deterministic scorers.

---

# 4. Operator Surfaces & Products — `SURFACE/PRODUCT`

### SCBE CLI — 🔵 PRODUCT
- **Path:** `packages/cli` (npm `scbe-aethermoore-cli` v4.4.0)
- **Does:** 30 governed commands — pipeline, tokenizer, PQC receipts, agent bus, governance abacus, conversational shell (`scbe shell --ai`).
- **Industry equivalent:** The `gh`/`stripe` CLI pattern applied to AI governance ops.
- **Use guide:** `scbe <command>`. The flagship operator surface; everything else can be driven from here.

### Polly Pad CLI + OS — 🔵 PRODUCT (CLI) / ⚪ SCAFFOLD (OS)
- **Path:** `packages/polly-pad-cli` (v0.1.0), `packages/polly-pad-os` (React 19 desktop UI, private v0.0.0)
- **Does:** Persistent operator workpad — task state, LLM routing, tool recipes, audit receipts (CLI); 81-app browser desktop the fleet drives via `invoke()` (OS).
- **Industry equivalent:** Warp terminal / a governed mission-control; OS side is a self-hosted agent desktop.
- **Use guide:** `polly` for the terminal workpad. OS is dev-only (`npm run dev`) — a vision surface, not shipped.

### AetherBrowser — 🟡 WIRED-EXPERIMENT
- **Path:** `src/aetherbrowser/`
- **Does:** FastAPI backend for governed web automation via Chrome extension — page→manifest, command planning, provider routing, corridor-atlas.
- **Industry equivalent:** Browser-Use, Skyvern, Multi-on — with a governance gate in front.
- **Use guide:** `uvicorn src.aetherbrowser.serve:app --port 8002`. The tab-manifest (page→534-token summary) is the reusable context-frugal piece.

### API / Gateway — 🟡 WIRED-EXPERIMENT
- **Path:** `src/api/` (FastAPI), `src/gateway/unified-api.ts` (Hono)
- **Does:** HTTP surface — auth, rate limiting, compute, free-LLM, geoseal bridge, billing/commerce.
- **Industry equivalent:** Any API gateway (Kong) + an LLM router (LiteLLM).
- **Use guide:** `uvicorn src.api.main:app` for the Python surface; the Hono gateway ships in `Dockerfile.gateway`.

### MCP Server — 🟡 WIRED-EXPERIMENT
- **Path:** `src/mcp_server/`
- **Does:** Model Context Protocol server exposing SCBE to Claude/MCP editors.
- **Industry equivalent:** Any MCP server; this one fronts the governance stack.
- **Use guide:** Wire via `.mcp.json`. The path to exposing the gate to other AI tools.

### n8n Workflow Bridge — 🔵 PRODUCT (M5 substrate)
- **Path:** `workflows/n8n/scbe_n8n_bridge.py`
- **Does:** FastAPI bridge (`/v1/governance/scan`, `/v1/tongue/encode`, `/v1/training/ingest`, …) + 7 verified workflows. This is the M5 Mesh Foundry revenue substrate.
- **Industry equivalent:** n8n/Zapier/Make + a governance step.
- **Use guide:** `uvicorn workflows.n8n.scbe_n8n_bridge:app --port 8001`. The actual "sell it now" product surface.

---

# 5. Research Instruments — `RESEARCH`

The *findings* are the deliverable; treat runtimes as probes, not dependencies. All are null-gated (real-vs-scrambled), which is their real value.

### Optical Transistor Sim — 🟠 RESEARCH-ONLY (well-built)
- **Path:** `src/physics_sim/optical_transistor.py`
- **Does:** Bistable optical-element model (saturable gain+absorber); cascade logic-restoration; β-survival curve; null/collapse metric on every result; `--regimes` grounds knobs in cited materials.
- **Use guide:** `python src/physics_sim/optical_transistor.py --regimes` (~9s) for the grounding table; full run ~110s.

### Measurement Rulers — 🟠 RESEARCH-ONLY
- **Paths:** `scripts/research/{nature_ruler,prime_ruler,ratio_caliper,hyperbolic_ruler,nested_integer_ruler}.py`
- **Does:** Family of ratio/proportion instruments with a built-in trust-glow significance test against a pre-fixed null. Nature's Ruler is the standalone "point at anything, read interpretable ratios" device.
- **Honesty note (from null tests):** prime *lengths* are decorative (= coprimality); Fermat *angles* are load-bearing (constructibility). Nested-integer + RNS is the real home of the exactness instinct.
- **Use guide:** Each is a `python … .py` CLI that prints measurements + a glow/significance verdict.

### Fermat RNS / NTT — 🟠 RESEARCH-ONLY
- **Paths:** `scripts/research/{fermat_rns,fermat_ntt_readout}.py`
- **Does:** Carry-free parallel integer arithmetic over Fermat-prime moduli; NTT shown decorative for accuracy, load-bearing for exactness (zero float error).
- **Use guide:** `PYTHONPATH=. python scripts/research/fermat_rns.py`.

### Tensor Foam / Prime-Rationed Lattice — 🟠 RESEARCH-ONLY
- **Paths:** `scripts/research/{tensor_foam_reservoir,prime_rationed_lattice}.py`
- **Does:** Reservoir-computing and moving-geometry probes. Findings: foam *computes* but prime coupling is decorative (= random); Fermat angles load-bearing.

### Code Prism — 🟢 REUSABLE-LIB
- **Path:** `src/code_prism/`
- **Does:** IR-based polyglot transpiler (Python/TS → TS/Go/C/Haskell) with round-trip tests. CLI entry `scbe-code-prism`.
- **Industry equivalent:** Tree-sitter + a transpiler; narrower but governed/tongue-routed.
- **Use guide:** `python src/code_prism/cli.py --input F --source-lang python --targets typescript,go --out-dir D`.

### Self-Healing Orchestrator — 🟢 REUSABLE-LIB
- **Path:** `src/selfHealing/selfHealingOrchestrator.py`
- **Does:** Circuit breaker + exponential backoff + multi-level healing (RETRY/FALLBACK/CIRCUIT_BREAK/ESCALATE/QUARANTINE), audit logging. Cites NIST 800-53 SI-13.
- **Industry equivalent:** resilience4j / Polly (.NET) / Hystrix.
- **Use guide:** Class API; wrap any flaky external call.

### Task Manager Core — 🟢 REUSABLE-LIB
- **Path:** `tools/taskmgr_core.py`
- **Does:** Headless process/agent monitor (psutil), classifies SCBE/ollama/claude-code/geoseal agents, `--json`.
- **Use guide:** `python -m tools.taskmgr_core {procs|agents|system|scbe|sample|kill} [--json]`.

---

# 6. Semantics & Tokenizer — `SEMANTICS`

### Sacred Tongues Tokenizer / NSM Primes — 🟡 WIRED-EXPERIMENT
- **Path:** `src/tokenizer/` (`nsmPrimes.ts` / `nsm_primes.py`, `semantic-atom.ts`)
- **Does:** 6-tongue encoding (Kor'aelin/Avali/Runethic/Cassisivadan/Umbroth/Draumric, 256 tokens each, φ-weighted) + NSM sememe primes for semantic atoms; feeds the governance basis.
- **Honesty note (home-turf test):** on a governance corpus the 6 tongues hit 0.91 (2× random, 92% of learned ceiling) — they're a genuinely well-chosen *governance* basis, not arbitrary. Off-domain they look random; on-domain they're load-bearing.
- **Use guide:** This is the basis the gate scores against. Reuse it *as the governance feature space*, not as a general-purpose tokenizer.

### GeoSeed — 🟡 WIRED-EXPERIMENT (M6 R&D)
- **Path:** `src/geoseed/`
- **Does:** Prime-orbital models, Fermat rulers, bit-dressing, semantic abacus — the geometric substrate for the M6 multi-nodal network.
- **Use guide:** Research substrate for M6; not a product surface.

---

# 7. Sibling Repos (workspace-level, future-project seeds)

From the storage inventory — independent repos that are products/seeds in their own right:

| Repo | Likely use-category | Note |
|---|---|---|
| `aetherbrowser`, `chrome-devtools-mcp`, `obsidian-local-rest-api` | SURFACE | browser/editor integration seeds |
| `aethermoore-creator-os`, `aethermoore-root-site`, `issdandavis.github.io` | SURFACE | public web surfaces |
| `aethermoore-youtube-automation`, `Shopify-Command-Center-src`, `gumroad-automation` | PRODUCT | monetization/ops automation |
| `phdm-21d-embedding`, `hyperbolica`, `scbe-research-staging`, `scbe-gate-town` | RESEARCH | geometry/gate research |
| `devoted-novel`, `aethromoor-novel-ci-cleanup`, `watershed-cultivation`, `writing-books-fieldbook`, `book-workshop`, `visual-computer-kindle-ai` | (writing) | the fiction/KDP track — separate domain |
| `Entropicdefenseengineproposal`, `Mava` | RESEARCH | external proposals/forks |
| `stripe-cli-fork`, `obs-studio-inspect`, `sysmon-config` | tooling | forks/configs, low priority |

---

# Where to start for a *new* project

1. **Need a safety gate around an agent?** → Runtime Governance Gate (`src/governance`) or Security-Engine (TS). Wrap every action; persist receipts.
2. **Building multi-agent?** → `packages/agent-bus` (best-tested) + `hydra/ledger.py` for audit.
3. **Need MFA / PQC / secret handling?** → `packages/aether-mfa`, `src/crypto`, `src/security/secret_store.py` — all 🟢 lift-ready.
4. **Need resilience / transpile / process-monitor utilities?** → self-healing orchestrator, code_prism, taskmgr_core.
5. **Selling something now?** → the n8n bridge (M5 Mesh Foundry) is the revenue substrate; the SCBE CLI is the operator face.

**The honest one-line positioning:** the defensible, sellable assets are the **governed gate + signed receipts/ledger + governed multi-agent bus + MFA/PQC libs** — not the "hyperbolic / 14-layer" geometry superlatives, which our own benchmarks don't support.
