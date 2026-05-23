# SCBE-AETHERMOORE — one-pager

A single-file overview of the project for partners, contracting officers,
recruiters, and reviewers. Last updated 2026-05-23. Canonical source:
`docs/SCBE_AETHERMOORE_ONE_PAGER.md` in `github.com/issdandavis/SCBE-AETHERMOORE`.

---

## 1. The pitch in one paragraph

SCBE-AETHERMOORE is a **model-agnostic execution board**: any AI model can
propose an action, but actions only execute if they are legal moves inside a
typed workflow space. The board enforces legality — the model does not. This
keeps dispatch control outside the model: even a noisy or adversarial model
cannot advance system state through an illegal move.

The board uses hyperbolic geometry (the Poincaré ball model) to make drift
measurable as distance from trusted state. A 14-layer processing pipeline emits
cryptographic receipts for every gate decision so auditors can replay any
action months later. The receipt mechanism (GeoSeal) plus the local operator
console (AetherDesk) plus the mechanical coding mechanism (compile-CA →
bijective source in Python/TypeScript/Go without an LLM call) together form a
deployable governance overlay that works in front of any LLM API. Author is a
self-taught engineer with active SAM.gov / CAGE registration, two DARPA
submissions on file (CLARA + MATHBAC), and a published prior-art book on KDP
(ASIN B0GSSFQD9G). Repo is open source; the governance overlay and managed-ops
services are the revenue surface.

### 1.1 The GeoBoard execution model

> SCBE turns AI autonomy into board play: models propose moves, but only the
> legal-move matrix can advance the system state.

Every operation passes through a six-stage pipeline before it executes:

```
state → proposed move → legality check → simulation → receipt → dispatch or deny
```

Think of a system as a domino chain. Each domino is a task, tool call, file
change, branch, or decision point. The spacing between dominoes is dependency
distance. The terrain the chain crosses is permissions, tests, latency, cost,
risk, and ownership. A missing domino is a broken dependency; a blocked fall is
a failed precondition; a bad branch is visible before execution because the
chain no longer reaches the target.

The board has six components:

| Component | What it does |
|---|---|
| **Typed state objects** | Files, tools, APIs, branches, scenes, agents, UI nodes, deploy targets — every entity in the system has a type |
| **Legal move catalog** | The complete set of operations the system can perform (edit file, run test, open PR, merge branch, dispatch browser action, invoke coding harness) |
| **Preconditions** | What must be true before a move can be attempted |
| **Effects** | What changes in state after the move succeeds |
| **Constraint terrain** | Permissions, risk budget, cost ceiling, test coverage, ownership, dependency order |
| **Governance receipt** | Structured log of the decision (decision tier, harmonic score, timestamp, requesting origin) emitted before dispatch |

The 14-layer pipeline (L1–L14) is the legality engine. L12's harmonic wall
`H(d, p_d) = 1 / (1 + φ·d_H + 2·p_d)` produces the score; L13 maps it to
ALLOW / QUARANTINE / ESCALATE / DENY. The score is algebraically bounded —
there is no prompt that can argue it past 1.0.

---

## 2. What is actually built

| Layer | What it does | Where it lives |
|---|---|---|
| **L1–L2** Complex Context → Realification | Lifts tokenized input into complex space, then realifies preserving norm | `src/harmonic/pipeline14.ts` |
| **L3** Weighted Transform | Sacred Tongues (KO/AV/RU/CA/UM/DR) apply φ-weighted governance dimensions | `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/langues_metric.py` |
| **L4** Poincaré Embedding | Projects into hyperbolic ball; the boundary is uncrossable | `src/harmonic/pipeline14.ts` |
| **L5** Hyperbolic Distance | `d_H = arcosh(1 + 2‖u−v‖² / ((1−‖u‖²)(1−‖v‖²)))` | `src/harmonic/hyperbolic.ts` |
| **L6–L7** Breathing + Möbius | Temporal modulation + isometric phase rotation | `src/harmonic/hyperbolic.ts`, `adaptiveNavigator.ts` |
| **L8** Hamiltonian CFI (multi-well) | Energy landscape with ALLOW / QUARANTINE / ESCALATE / DENY wells | `src/harmonic/hamiltonianCFI.ts` |
| **L9–L10** Spectral + Spin Coherence | FFT-based anomaly detection, decoherence metrics | `src/spectral/index.ts` |
| **L11** Triadic Temporal Distance | Three-scale intent tracking (immediate / medium / long) | `src/symphonic_cipher/.../causality_axiom.py` |
| **L12** Harmonic Wall | Canonical bounded safety score: `H(d, p_d) = 1 / (1 + φ·d_H + 2·p_d)` ∈ (0, 1] | `src/harmonic/harmonicScaling.ts` |
| **L13** Risk Decision (Swarm Governance) | Maps H to one of four tiers, emits a structured decision record | `src/governance/`, swarm consensus modules |
| **L14** Audio Axis (FFT telemetry) | Encodes the full governance trace as audio for cross-system signaling | `src/harmonic/audioAxis.ts`, `vacuumAcoustics.ts` |

Five axioms (Unitarity, Locality, Causality, Symmetry, Composition)
cross-cut these layers and have their own Python implementations in
`src/symphonic_cipher/scbe_aethermoore/axiom_grouped/`. Every axiom has
property-based tests under `tests/L4-property/`.

---

## 3. The three deployable surfaces

### 3.1 GeoSeal — cryptographic receipts

Every gate decision and every operator command writes a structured
receipt (`aetherdesk_receipt_v0` schema) with: task_id, command_digest
(SHA-256), risk_tier, allowed_paths, started/finished_at, duration_ms,
exit_code, result, 8 KB stdout/stderr tails, and (for bench ops)
input_tokens/output_tokens/estimated_cost_usd. Receipts land in
`artifacts/aetherdesk_receipts/`. They are replayable: a reviewer with
the logged `d` and `p_d` can recompute `H` exactly without rerunning
the model.

This is the audit trail other governance vendors lack — Anthropic's
Petri does detection without enforcement; Anthropic's SCONE-bench
(red.anthropic.com/2025/smart-contracts/) measures attacker capability
(frontier models autonomously finding $550M in simulated smart-contract
exploits across 405 benchmark contracts) but does not ship a defensive
gate; PNNL's ALOHA has no governance layer at all. SCBE composes with
all three as the enforcement surface that emits the audit trail. As of
2026-05-14 SCBE ships `scbe contract scan` as a SCONE-class static
prefilter and SCONE-aware anchors in the production governed-output
proxy.

### 3.2 AetherDesk — local operator shell (PR #1640)

Tiny Express server bound to `127.0.0.1:5717`. Static HTML grid:
five known-good commands (typecheck, TS tests, CLI benchmark,
Aether-Lattice sim, coding-agent benchmark) plus a GeoSeal receipt
pane that lists every run and lets the operator click into any
receipt for the full transcript. Allowlist is the security boundary
— the frontend cannot pass raw shell strings, only request command
IDs. 17 tests cover allowlist enforcement, shell-injection rejection,
path-traversal rejection.

Run with `npm run aetherdesk`. v0.1 adds Agent Bus, Diff/Patch, and
Provider Status panes.

### 3.3 Mechanical coding mechanism (PR #1641)

Bijective compile-CA path: 64 tier-1 CA opcodes (+ stack-machine
plumbing like `swap` at 0x40) compile to runnable Python / TypeScript /
Go without any LLM call. Round-trip verified by re-disassembly.

**Benchmark numbers (6 arithmetic tasks, 4 comparator arms):**

| Arm | runs | pass% | mean ms | total cost |
|---|---|---|---|---|
| **mechanical (SCBE)** | 6 | **100.0%** | **677** | **$0.000000** |
| ollama qwen2.5-coder 0.5b | 6 | 100.0% | 3,008 | (local, free) |
| ollama qwen2.5-coder 1.5b | 6 | 100.0% | 3,520 | (local, free) |
| cost_estimate_sonnet | 6 | (passthrough) | n/a | $0.002103 |

Mechanical wins **4.4–5.2× on latency** and reaches the **$0 floor**
on compute cost vs Sonnet's projected $0.0021 across 6 ops. The bench
also surfaced — and the same PR fixed — a real correctness bug in the
foundational opcode table that had been silently returning wrong
values for `abs(a) + abs(b)` under non-symmetric inputs.

Full report at `artifacts/aetherdesk_bench/bench_report_*.json`.

---

## 4. Why this matters now

| Headwind | How SCBE responds |
|---|---|
| AI buyer trust is at floor (77% of "Success" sub-cat Amazon AI books in late 2025 were AI-generated) | The CI-validated runnable-ebook format and the GeoSeal receipts mean every claim ships with a re-runnable proof |
| Governance vendors detect but don't enforce (Petri, ALOHA); attacker-capability benchmarks measure offense but ship no defense (Anthropic SCONE-bench: $550M in simulated smart-contract exploits across 405 benchmark contracts) | SCBE provides the enforcement gate that emits the receipt those tools want to consume; ships `scbe contract scan` SCONE-class static prefilter and SCONE-aware governance anchors |
| Coding-agent compute costs scale with traffic | The mechanical compile-CA path replaces LLM calls for the routine ops that dominate volume (arithmetic, comparison, aggregation) at zero per-call cost |
| Post-quantum migration is forcing the next refactor of every secure system anyway | SCBE is already on ML-DSA-65 / ML-KEM-768 (the renamed Dilithium3 / Kyber768) with fallback handling for older liboqs builds |

---

## 5. Federal contracting status

| Item | Value | Status |
|---|---|---|
| SAM.gov UEI | J4NXHM6N5F59 | **ACTIVE** through 2026-04-13 |
| CAGE Code | 1EXD5 | Assigned |
| Entity type | Sole proprietor, minority-owned | Registered |
| APEX Accelerator | Port Angeles, WA | Engaged |
| DARPA CLARA (FP-033) | DARPA-PA-25-07-02 | **SUBMITTED**; award decision 2026-06-16 |
| DARPA MATHBAC abstract v1 | DARPA-SN-26-59 | **SUBMITTED 2026-04-27** |
| MATHBAC full proposal | (joint w/ Collin Hoag / DAVA) | Due 2026-06-16; spine drafted |

Direct contracting channels: APEX Accelerator (free gov contracting
help, 338 W First St, (360) 457-7793) and DIBBS / DLA via DAVA
teaming. Subcontract rates: $150–$250/hour.

---

## 6. Prior art and publication

- **Six Tongues Protocol Book** — Amazon KDP, ASIN B0GSSFQD9G — timestamped
  prior art for the Sacred Tongues system, prior to any DARPA submission.
- **AI Governance Fundamentals** (in progress, chapters 1–4 shipped) —
  runnable-ebook format: every code block is extracted and executed by
  `tests/book/_runner.py` on every push. Code does not rot. Chapters
  cover the harmonic wall, the four-tier risk decision, decision records,
  and Sacred Tongues weighting. See PRs #1630 and #1635.
- **`docs/specs/AETHERDESK_OPERATOR_SHELL_v0.md`** — implementation spec
  for the operator shell (PR #1637).
- **`docs/research/TERAX_AI_TERMINAL_REFERENCE.md`** — competitive
  analysis vs the Terax AI terminal, establishing SCBE's wedge
  (governed agent workbench vs AI terminal).

---

## 7. Where to look first (key files)

| For | Read |
|---|---|
| Architecture overview | `docs/LAYER_INDEX.md`, `docs/SYSTEM_ARCHITECTURE.md` |
| Canonical spec | `docs/SPEC.md` |
| 14-layer pipeline (TypeScript canon) | `src/harmonic/pipeline14.ts` |
| Harmonic wall implementation | `src/harmonic/harmonicScaling.ts` |
| Sacred Tongues (Python reference) | `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/langues_metric.py` |
| Mechanical coding CLI | `scripts/agents/scbe_code.py` |
| AetherDesk operator shell | `aetherdesk/server.js`, `aetherdesk/public/index.html` |
| Mechanical-coding benchmark | `scripts/benchmark/aetherdesk_mechanical_coding_bench.py` |
| Runnable book chapters | `book/ai-governance-fundamentals/chapter-*.md` |
| Federal docs (MATHBAC, CLARA) | `docs/contracting/`, `docs/specs/ta1_mathematical_challenges_v1.md` |

---

## 8. Revenue surface (what's for sale)

| SKU | Price | What you get |
|---|---|---|
| SCBE Service Credits | $5+ pay-as-you-go | Hosted governance scans, governed runs, reports, provider/model usage with 2–5% coordination fee |
| AI Governance Snapshot | $500 one-time | Fixed-scope assessment of one AI workflow: 2-page findings memo, three prioritized fixes, evidence checklist |
| Governance Heartbeat | $99/month | Monthly governance scan for one AI workflow with delta report and recommended actions |
| AI Governance Toolkit | $29 one-time | Templates + decision records + setup guidance, downloadable ZIP |
| AI Security Training Vault | $29 one-time | Training data + projector weights + benchmark suite + notebooks |
| Adversarial audit | $5,000 – $15,000 / 1–3 weeks | Production LLM endpoint or agent audit vs the SCBE governance harness |
| Custom governance overlay | $25,000 – $80,000 / 4–10 weeks | Deployable governance layer in front of your model API |
| Federal subcontract | $150 – $250 / hour | AI safety / LLM evaluation on a prime's contract |

---

## 9. Contact

- **Issac Davis** — Port Angeles, WA
- Email: `issdandavis7795@gmail.com`
- Repo: `github.com/issdandavis/SCBE-AETHERMOORE`
- Hire page: `https://aethermoore.com/SCBE-AETHERMOORE/hire.html`
- Tip jar / supporter sub: `https://ko-fi.com/izdandavis`

---

## 10. Note on how this document was made

Human-authored. AI-assisted in the editing pass. The git history for
this file is public; specifics of the human / AI division are
auditable via `git log -p docs/SCBE_AETHERMOORE_ONE_PAGER.md`. The
numbers in section 3.3 are computed, not estimated — see the bench
report under `artifacts/aetherdesk_bench/`.

This is one of two single-file shareables. The companion file
(`scripts/bootstrap/aethermoore.pyz`, planned next PR) is the
double-click launcher; this file is the read-once briefing.
