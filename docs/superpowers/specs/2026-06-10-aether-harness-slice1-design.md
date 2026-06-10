# Aether Harness — Slice 1 Design Spec (Governed Core, Terminal-First)

_2026-06-10. Approved design. Builds on docs/superpowers/specs/2026-06-10-governed-harness-study.md._

## Goal

A custom, governed agent harness that replaces the terminal: a **vendored, stripped Hermes fork** that runs in PowerShell as `aether "task"`, where **every tool call passes through the SCBE governance gate and emits a GeoSeal receipt**. Slice 1 is the spine every later slice (buttons/notes surface, if-then workflows, multi-agent, Polly GUI) builds on.

## Decisions (locked)

- **Fork strategy:** vendor a stripped Hermes fork into `packages/aether-harness/` (we own + edit it). MIT — retain LICENSE + attribution.
- **Surface:** terminal-first (CLI). GUI (Polly Pad) is a later slice.
- **Engine:** Hermes Agent v0.16.0 (real harness loop, tool registry, providers, memory, skills, local browser).

## Architecture

```
aether "task"
  → Hermes one-shot loop (cli.py --query)
     → model (≥64K ctx, reasoning-aware provider)
        → tool_call
           → [GOVERNANCE SEAM]  ← src/governance/runtime_gate + anchor_wall
                ALLOW    → execute, receipt
                QUARANTINE/ESCALATE → pause, prompt approve/changes/deny, receipt
                DENY     → block, deny-reason fed back to model, receipt
           → tool result → loop
  → done (audit chain of GeoSeal receipts)
```

## Components

1. **`packages/aether-harness/`** — vendored Hermes. Keep: `agent/` (loop), `tools/` (registry, file, execute_code, browser, delegate, clarify), `providers/`, `cli.py`, memory, skills, `model_tools.py`. Strip (later-allowed, not blocking): `gateway/` (messaging platforms), media-gen tools (image/video/tts), cloud browser backends, `acp_adapter/`, non-coding integration tools. Retain `LICENSE` + a `VENDORED.md` noting source commit + our modifications.

2. **`governance_seam.py`** (the one load-bearing module) — wraps the single tool-dispatch point (`tools/registry.py::handle_function_call`, confirmed cleanest seam). Interface:
   - `govern(tool_name: str, tool_args: dict, ctx) -> GovernDecision` where `GovernDecision ∈ {ALLOW, QUARANTINE, ESCALATE, DENY}` + reason + receipt.
   - Builds an action descriptor (tool name + compact args summary), calls the repo's `RuntimeGate.evaluate(action_text, tool_name)` (single source of truth — import from `src/governance/`, no copy) and optionally `FixedAnchorWall.step`.
   - Emits a **GeoSeal receipt** per call (audit_id, tool, args-sha256, decision, cost, signals, timestamp) to an append-only audit log + renders the stamp inline. Reuse the existing GeoSeal stamp util.
   - "Hooks-first, deny-beats-bypass": the seam runs before dispatch and a DENY blocks regardless of mode. DENY returns a structured tool error (deny-with-reason) so the model adapts instead of dead-ending.

3. **Provider fix** — normalize assistant `reasoning_content`: strip it before re-sending on the OpenAI-compatible (`custom`) path so reasoning models (gpt-oss, GLM) complete multi-turn. (Measured bug: both Cerebras models break on turn 3 without this.)

4. **Model/provider config** — a configurable **≥64K default**. Cred reality: Anthropic key has no API balance, Groq key stale, Cerebras key valid (gpt-oss-120b / zai-glm-4.7, both reasoning → need the fix). Slice 1 default: Cerebras gpt-oss-120b WITH the reasoning fix, overridable; document how to point at a local ≥64K model or a live key.

5. **`aether` entry point** — PowerShell-friendly wrapper (`packages/aether-harness/bin/aether` + npm/py script): `aether "task"` runs the governed harness; streaming output; GeoSeal receipts inline; reuses Hermes' diff-review + `clarify` for the approve/changes/deny prompt on QUARANTINE/ESCALATE.

## Data / control flow

User → `aether` CLI → Hermes loop → model → tool_call → **seam.govern()** → (execute | block) → receipt appended → result → loop → final audit chain.

## Testing

- **Unit (seam, mocked gate+tool):** ALLOW dispatches the tool; DENY blocks + returns the reason and does NOT dispatch; QUARANTINE/ESCALATE pauses; exactly one receipt emitted per call; receipt fields populated.
- **Provider unit:** an assistant message carrying `reasoning_content` is stripped before re-send; a normal message is untouched.
- **Integration (real model):** palindrome task end-to-end through the governed harness → files created, `pytest` green, AND a receipt exists per tool call.
- **Adversarial integration:** a tool call that is destructive/exfil (e.g., delete outside workdir, read a secret) → seam returns DENY, tool not executed, receipt records DENY.

## Boundaries / isolation

The seam is one module with a single clean function; vendored Hermes is otherwise unmodified except (a) the one dispatch hook, (b) the strip, (c) the reasoning_content fix. Governance logic stays in `src/governance/` (one source of truth); the seam adapts Hermes ↔ gate.

## Out of scope (later slices)

Full AskUserQuestion button polish; notes-on-decisions persistence + re-injection; nested if-then workflows; multi-agent intercom; Polly Pad GUI; aggressive dependency strip beyond what's needed to run.

## Success criterion for Slice 1

`aether "write + test a small function"` runs in PowerShell, completes the task on a real model, and produces a GeoSeal audit chain with one receipt per tool call — and a known-bad action is DENIED with a receipt.
