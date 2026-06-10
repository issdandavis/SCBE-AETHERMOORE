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
- `hermes_plugin/` — the installable Hermes plugin (manifest + bridge +
  `config.example.yaml`). Bootstrap copies it into the engine's `plugins/`.
- `vendor/hermes/` — the engine, vendored **by reference**: pinned upstream
  commit + our patch + `bootstrap_hermes.ps1`. See `vendor/hermes/VENDORED.md`.
- `patches/0001-strip-reasoning-content-on-replay.patch` — the one upstream fix
  (Cerebras/custom endpoints reject replayed `reasoning_content`).
- `test_governance_seam.py` — offline unit tests (real light gate + a fake gate).

## Slice 1 status: governed core PROVEN

Both halves of the Slice-1 success criterion are demonstrated against the real
engine on a real model (Cerebras `gpt-oss-120b`):

- **Governed live run** — task: write `is_palindrome` + run it on three inputs.
  The model drove 3 tool calls (2 `write_file`, 1 `execute_code`); every call
  was routed through the seam and stamped (`⊟ GeoSeal ✓ ALLOW …`); 3 receipts
  landed in `.scbe/aether/receipts.jsonl`; output was correct
  (`racecar`→True, `A man a plan a canal Panama`→True, `hello`→False).
- **DENY proven through the engine's real dispatch path** —
  `hermes_cli.plugins.get_pre_tool_call_block_message` (the exact function
  `model_tools.py:1035` calls before *every* tool) returns our block directive
  for `rm -rf / --no-preserve-root` and `None` for a benign write. On a block,
  `model_tools.py:1048` aborts the tool and feeds the reason back to the model.

### Honesty note: what catches the bad command

In these runs the DENY came from the **GeoSeal command scanner**, not the
hyperbolic gate — the gate reported `calibrating` and did not itself flag the
command. The seam takes the worst verdict across {gate, GeoSeal scan}, so
shell-command safety is carried by the scanner today; the gate contributes
governance signals + the receipt chain. This matches the repo's own
decorative-geometry finding: don't read the demo as the geometry catching
attacks.

## Plan

The engine is a vendored-by-reference Hermes fork (MIT) — pin + patch +
bootstrap, not a 127 MB source dump (keeps this public repo lean). The seam is
wired via the plugin's `pre_tool_call` hook.

Later slices: streaming + AskUserQuestion buttons + notes surface; nested
if-then workflows; multi-agent intercom; Polly Pad GUI.
