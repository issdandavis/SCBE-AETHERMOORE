# Agentic coding: execution, review, and temporal reliance layers

This document closes the loop between (1) Polly Pad / L11 / bijective transport,
(2) industry practice (NASA, SpaceX-style discipline), and (3) concrete SCBE
surfaces: GeoSeal harness, Stage 6, and verification commands.

## 1. Clarifications (load-bearing)

### 1.1 Layer 11 is not one formula today

Multiple scalar aggregations of triadic distances exist in-repo (φ-linear
combination, φ-power mean in `src/polly_pads_runtime.py`, triangle-inequality
residual in `src/crypto/dual_lattice_integration.py`, Euclidean root-sum-square
in `src/symphonic_cipher/scbe_aethermoore/layers_9_12.py`). They are **not**
equivalent on arbitrary inputs: they emphasize worst-trace deviation, weighted
average inconsistency, or metric coherence differently.

**Until one aggregation is declared canonical and others are explicitly
deprecated or mapped to diagnostic-only roles, “L11 objective” is
underspecified** for proofs and for patent/DARPA language that treats L11 as
fixed.

**Candidate canonical choice (geometry-aligned):** the φ-power mean in
`triadic_temporal_distance()` — it penalizes the largest directional deviation
in a way that composes with “harmonic wall” intuition (single bad trace dominates
the scalar). **This is a design decision, not yet enforced repo-wide.** Follow-up
work: pick one, add cross-module tests, and mark alternates as `legacy_*` or
`diagnostic_*`.

### 1.2 “Bijective” has a strict domain

- **SS1 payload bijection** (`src/crypto/sacred_tongue_payload_bijection.py`):
  bytes ↔ tongue tokens on the tokenizer’s image.
- **STIB** (`python/scbe/tongue_isa_binary.py`): canonical binary for CA opcode
  programs with integrity hash.
- **ISA round-trip** (`compile` → `disassemble`): holds on **lawful** opcode
  programs.

Autoregressive **generation** is not in that image. The bridge from noisy LM
output to a lawful artifact is **Stage 6 constrained decoding**
(`src/governance/stage6_constrained_decoding.py`): forced-prefix / substring
gates and eval contract — i.e. **commit-time** enforcement, not token-stream
bijection.

## 2. Three-way split (stable mental model)

| Concern | Nature | Primary surfaces |
|--------|--------|------------------|
| Polly Pad governance | Discrete trust / tier / audit | `src/fleet/polly-pad.ts`, Polly Pad runtime |
| L11 triadic cost | Continuous scalar(s) — **needs canonical pick** | `polly_pads_runtime.py`, layers_9_12, dual_lattice |
| Bijective transport + generation gate | Strict maps + commit gate | SS1, STIB, ISA, Stage 6 |

## 3. Research basis: NASA / SpaceX / agentic coding

### 3.1 NASA NPR 7150–style separation

NPR 7150.2 and the NASA Software Engineering Handbook emphasize **recorded
verification**, **independent verification and validation (IV&V)** where
required, and **peer reviews / inspections** with tracked actions to closure.
See NASA SWE Handbook — Book B (requirements), SWE-141 (IV&V), and peer-review
requirements (e.g. SWE-073 / inspection themes in handbook editions).

**Mapping:** our **review layer** is the IV&V analog: tests, ladder, and human
checkpoints are **not** optional substitutes for each other; they address
different failure modes.

### 3.2 SpaceX-style execution discipline

Public summaries of SpaceX flight-software practice stress **continuous
integration**, **simulation on every change**, **hardware-in-the-loop** where
affordable, and **multi-path checking** (e.g. redundant compute with
compare/vote patterns on Falcon-class systems). See e.g. Stack Overflow blog
(2021) on SpaceX testing culture; industry writeups on Actor–Judge / redundancy.

**Mapping:** our **execution layer** is bounded, repeatable commands with
evidence artifacts — not ad-hoc model prose. **Temporal reliance** covers
delayed execution when upstream simulation (or task) state is stale.

### 3.3 Agentic coding (2024–2026)

Codex CLI, Claude Code hooks/MCP, OpenHands, and Aider converge on: **explicit
permission profiles**, **tool manifests**, **replayable trajectories**, and
**pre-tool policy**. SCBE encodes these in `build_agent_harness_manifest_v1`
plus the stack below.

## 4. The three new layers (execution / review / temporal reliance)

These layers are emitted in the agent harness as `agent_execution_stack_v1`
(see `src/coding_spine/agent_tool_bridge.py` and
`src/coding_spine/agent_temporal_reliance.py`).

### 4.1 Execution layer

**Purpose:** Run only **approved**, **bounded** commands; produce **artifacts**
 suitable for audit.

Includes:

- GeoSeal routes: `code-packet`, `testing-cli`, `project-scaffold` (as allowed by profile).
- **Stage 6** as the **generation→commit** gate for merged coding models.
- Optional: `scbe_code` apply path only after static + harness checks pass.

### 4.2 Review layer

**Purpose:** **Independent** verification — not the same model that wrote the patch.

Includes:

- `testing-cli`, `agentic_ladder`, CI-equivalent scripts.
- **Peer / human** step for high-risk tool classes (`destructive_filesystem`,
  `secrets_or_credentials`).
- Explicit **forbidden:** “model self-signoff” as sole verification for
  workspace-write or above.

### 4.3 Temporal reliance layer

**Purpose:** Tasks that **execute later** must **re-anchor** to facts that may
have changed: merges, rebases, remote CI, or another agent’s completion.

Primitives:

- `task_id`, `upstream_task_ids`, `anchor_state`: `PROVEN` | `ASSUMED` | `UNKNOWN`.
- **Re-anchor protocol** (ordered):
  1. Refresh evidence (git status, test output hash, manifest digest).
  2. If upstream `UNKNOWN` or stale TTL: downgrade to `observe` or block writes.
  3. Re-run minimal **review layer** slice (smoke + targeted tests).
  4. Log decision to history/replay envelope.

This is the agentic analog of **re-baselining** simulation state before a
delayed command upload in aerospace workflows.

## 5. Next engineering steps

1. **Canonicalize L11** — one scalar in production; document migration for others.
2. **Wire pre-tool policy** — manifest `tool_contracts` → enforced gate before spawn.
3. **MCP export** — expose `agent_execution_stack_v1` as resources/tools for hosts.
4. **Stage 6 + STIB** — document explicit pipeline: generate → Stage6 gate → STIB/ISA verify → commit.

## References (external)

- NASA Software Engineering Handbook / NPR 7150.2 — verification, IV&V, peer reviews: https://swehb.nasa.gov/display/7150/Book+B.+7150+Requirements+Guidance and SWE-141 IV&V pages.
- SpaceX / flight-software testing culture (secondary): e.g. https://stackoverflow.blog/2021/05/11/testing-software-so-its-reliable-enough-for-space
- Agentic CLI patterns: OpenAI Codex README, Claude Code MCP/hooks, MCP spec, OpenHands, Aider (as cited in `docs/ops/AGENTIC_CLI_HARNESS_RESEARCH_2026-04-29.md`).
