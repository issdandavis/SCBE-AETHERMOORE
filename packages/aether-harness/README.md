# aether-harness

A governed agent harness — the Claude-Code/Hermes-style experience under our
control, with **every tool call routed through the SCBE governance gate and
sealed with a GeoSeal receipt**.

Status: **Slice 1 (governed core), in progress.** Design:
`docs/superpowers/specs/2026-06-10-aether-harness-slice1-design.md`. Study that
chose the approach: `docs/superpowers/specs/2026-06-10-governed-harness-study.md`.

## What's here now

- `governance_seam.py` — engine-agnostic core. `GovernanceSeam.govern(tool, args)`
  evaluates an action through the repo's `RuntimeGate` (+ GeoSeal command
  scanner for shell/code tools), returns a `SeamDecision` (ALLOW/REVIEW/
  QUARANTINE/ESCALATE/DENY), and emits a GeoSeal receipt per call to
  `.scbe/aether/receipts.jsonl`. Policy: deny-beats-bypass; DENY blocks, the
  reason is fed back to the model.
- `scbe_governance_plugin.py` — thin Hermes adapter: registers a `pre_tool_call`
  hook (Hermes' native, intended seam) that calls the governance seam and blocks
  on DENY. Vendor-friendly; no monkeypatching.
- `test_governance_seam.py` — offline unit tests (real light gate + a fake gate).

## Plan

The engine is a vendored, stripped Hermes fork (MIT). The seam is wired via the
plugin's `pre_tool_call` hook. Slice 1 success: `aether "task"` runs in
PowerShell, completes on a real model, and produces a GeoSeal audit chain with
one receipt per tool call — and a known-bad action is DENIED with a receipt.

Later slices: streaming + AskUserQuestion buttons + notes surface; nested
if-then workflows; multi-agent intercom; Polly Pad GUI.
