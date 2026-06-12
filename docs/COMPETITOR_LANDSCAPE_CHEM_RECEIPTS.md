# Competitor Landscape: Chemistry Lane, Units Engine, Signed Receipts, Agentic CLIs

Date: 2026-06-12. Method: 5-lane adversarially-verified market research (8 agents;
3 uniqueness claims stress-tested, 2 refuted — corrections are folded in below).
Companion to `COMPETITOR_GAP_OPENCLAW_MOLTBOT.md`.

## TL;DR positioning

Sell the **PQC-signed receipt around a verified result** — not the gate, not the
chemistry math, not the unit math, not even "signed receipts" alone:

- Governance gates on agent tool calls are **table stakes** (Claude Code, Gemini
  CLI, Codex, Goose, Warp, Q/Kiro all ship allow/deny machinery).
- Reaction balancing is **commodity math** (ChemPy, Wolfram, ChemEquations.jl).
- Exact unit arithmetic is **not unique** (Frink, SymPy, Pint's Fraction mode).
- Per-result signed receipts now **exist as add-on products** (Asqav ships
  ML-DSA-65 bilateral receipts; IETF ACTA draft even recommends ML-DSA-65).

What no one else does: **sign a *verified computational result*** — exact
rational mass+charge conservation, dimensional analysis, lossiness
classification (BIJECTIVE/LOSSY_*), explicit claim boundaries, hazard flags —
natively in the CLI, with real liboqs ML-DSA-65, hash-chained, verifiable
offline. Every competitor attests that an *action happened*; we attest that a
*result is correct, classified, and bounded*.

## Lane 1 — Stoichiometry / balancing software

| Product | Balancing | Hazard flags | Audit artifact | License |
|---|---|---|---|---|
| **ChemPy** (closest peer) | Exact symbolic (SymPy), charge + electrons, parametric underdetermined | none | bare dict | BSD-2 |
| **Wolfram ReactionBalance / W\|A** | Exact, best failure semantics, NL input, thermo attached | none | none | Proprietary ($9.99/mo Pro) |
| **pymatgen** | Float-tolerance least-squares (not exact), no charge row; adds DFT reaction *energetics* | none | none | MIT |
| **ChemEquations.jl** | Same nullspace algorithm as ours | none | none | MIT |
| **RDKit / Open Babel** | No balancing at all (transforms / format interop) | n/a | n/a | BSD / GPL-2 |
| **ChemDraw (Revvity)** | Stoichiometry grid on drawn reactions (quantities, not symbolic balance) | none | ELN audit at platform level | Subscription-only since 2025 |
| **scbe react balance** | Exact rational nullspace, charge row, named failure diagnostics | **yes (lexical species screen + deny patterns)** | **SHA-256 chained + ML-DSA-65 signed packet** | — |

**Verified claim (held under adversarial search):** no mainstream balancer
attaches hazard warnings to balanced equations at the API/CLI level. That is
genuinely ours.

**They're stronger:** ChemPy's parametric handling of underdetermined systems;
Wolfram's pedagogy + curated data; pymatgen's real thermodynamics. Our line
stays "conservation/identity engine; thermo defers to Cantera/NASA CEA."

## Lane 2 — Units / dimensional analysis

Mature, crowded, all-free lane. **There is no money in unit math; the envelope
is the product.**

- Every serious runtime library catches dimension mismatches (Pint, astropy,
  unyt). SymPy units is the weak outlier (silent symbolic `meter+second`);
  F# units-of-measure is the strong outlier (compile-time, but erased at
  runtime — useless for agent-supplied values).
- **REFUTED claim — do not say "we're exact, they're float":** Pint has a
  first-class `Fraction` mode (`non_int_type`, bit-exact round-trips verified
  on 0.25.3); Frink does exact arbitrary-size rationals over a 20-year unit
  catalog; Unitful.jl uses exact rationals by default. Honest claim: **"exact
  by default in a governed pipeline"** (astropy *is* float-scale; Pint's
  *default* is float).
- Nobody in the lane signs, chains, governs, or claim-classifies a result, and
  none ship an agent-facing MCP contract.
- Cheap credibility moves: emit **QUDT unit URIs** (NASA-pedigree ontology,
  CC BY 4.0) in packets; audit our dimension vectors against **NISTIR 8289**'s
  documented library pathologies. Keep Pint as the cross-check backend.

## Lane 3 — LLM chemistry agents / safety governance

The dual-use screening standard of care is **ahead of our lexical table**:

- **ChemCrow** (MIT): auto-invoked `ControlledChemicalCheck` — CAS lookup
  against **OPCW Schedules 1–3 + Australia Group** lists, plus Tanimoto >0.35
  structural similarity to catch unlisted analogues; ExplosiveCheck (GHS);
  hard-stops execution.
- **FutureHouse ether0/Phoenix**: refusal RL-trained into model weights on
  OPCW Schedules 1&2 (~80% refusal — i.e., ~20% leak; probabilistic).
- **Coscientist** (Nature): published red-team — pure-LLM refusal was
  jailbroken 4/11 times. Deterministic gates beat LLM judgment here.
- Three public yardsticks we have **no score against**: ChemBench (safety
  category; finding: LLMs overconfident on safety), ChemSafetyBench (30K
  samples incl. jailbreaks + legality), SciMT-Safety.

**None of them emit a signed receipt or exact conservation math.** Their
safety decisions are LLM-mediated and unverifiable after the fact; ours is
deterministic and signed.

**Roadmap that falls out:** (1) adopt OPCW/Australia-Group CAS lists as the
screen's source of truth (ChemCrow's approach is MIT — wrap, don't reinvent);
(2) add structural-similarity flagging for analogue evasion; (3) publish a
ChemSafetyBench score so the safety claim is benchmarked, not asserted.

## Lane 4 — Signed / auditable agent execution

The category crystallized in late 2025/2026 — **"we sign receipts" is
commoditizing**:

- **REFUTED claim — per-result PQC receipts are no longer unique:**
  **Asqav** (`asqav-mcp`, PyPI/npm, May 2026) signs each tool call's request
  *and* response with ML-DSA-65 and hash-chains per-result; installs into
  Claude Code via `claude mcp add`. **Rubric Protocol** signs agent actions
  with ML-DSA-65 (Merkle-batch anchoring). **IETF draft-farley-acta-signed-
  receipts-01** specifies signed decision receipts with `previousReceiptHash`
  and *recommends ML-DSA-65*. Ed25519 implementations: Attested Intelligence
  (+ Merkle inclusion proofs), Signet, ScopeBlind, Microsoft's Agent
  Governance Toolkit. Surviving narrower claim: **no major agentic CLI ships
  this natively** — it's all bolt-on.
- Observability incumbents (LangSmith/Langfuse) own the budget line but sign
  nothing — their own forum asks for an "execution evidence layer."
  MCP gateways (Lasso, mcp-scan/Snyk) hash tool *definitions*, not results.
  Sigstore/C2PA sign *artifacts/media*, not tool executions (and C2PA has no
  PQC).
- **Their honest advantages over us:** Merkle inclusion proofs beat a linear
  chain on omission-resistance; the field converged on **RFC 8785 JCS**
  canonicalization (interop gap for us); Rekor-style transparency logs beat
  self-attested chains; OPAQUE sells hardware-TEE attestation into the **EU AI
  Act enforcement date (Aug 2, 2026)**.
- **Roadmap:** JCS canonicalization + ACTA-compatible fields (cheap interop);
  Merkle checkpointing; optional Rekor anchoring; consider hybrid
  Ed25519+ML-DSA-65.

## Lane 5 — Agentic CLIs (the direct competitors)

Verified June 2026 across Claude Code, Codex, Gemini CLI, Aider, OpenHands,
Goose, Warp, Amazon Q/Kiro:

- **Domain-science tools: 0 of 8.** No built-in chemistry or units anywhere;
  only conversational RDKit MCP wrappers with no exactness, hazards, or
  receipts. `scbe react` + the units engine is unoccupied territory.
- **Governance gates: crowded — not our differentiator.** Claude Code
  (deny→ask→allow + hooks + MDM-managed settings + OTel/SIEM), Gemini CLI
  (Policy Engine + Trusted Folders), Codex (OS sandbox + Starlark execpolicy),
  Goose (Smart Approval + MCP-install allowlist), Warp (deny-precedence
  regex), Q/Kiro (allowedTools JSON). Ours stands out only via the risk-tier
  taxonomy (ALLOW/QUARANTINE/ESCALATE/DENY vs everyone's binary) and
  domain-aware deny patterns. Notable: Gemini CLI's gate has a documented hole
  in headless auto-edit mode (#20469) — exactly where ours binds.
- **Cryptographic receipts: 0 of 8 natively.** Closest: OpenHands' replayable
  (unsigned) event stream, Aider's git DAG (file edits only), Claude Code's
  OTel events (tamper-evidence delegated to your SIEM).
- **They're flatly stronger on:** OS-enforced sandboxing (Codex), enterprise
  policy distribution + observability plumbing (Claude Code), operator UX
  (Warp), distribution (all big three), replayable execution (OpenHands).

## Demand signals

EU AI Act high-risk logging obligations land **August 2, 2026**; five-government
guidance (CISA/NSA/NCSC-UK/ASD/CCCS/NCSC-NZ) names cryptographic attestation
for agentic AI; Microsoft's agent-security curriculum teaches signed receipts;
IETF standards motion (ACTA, Authproof). The window where "receipts" alone
differentiates is closing — "receipts over verified results" is the durable
position.
