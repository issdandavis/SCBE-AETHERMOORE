---
title: Claude-Codex Cross-Talk Handoff
date: 2026-03-17
status: active
---

# Claude-Codex Cross-Talk Handoff

## Canonical coordination channels

Live vault root:

`C:\Users\issda\Documents\Avalon Files`

Canonical handoff note:

- `Cross Talk.md`

Canonical repo lanes:

- `artifacts/agent_comm/<date>/...json`
- `artifacts/agent_comm/github_lanes/cross_talk.jsonl`
- `scripts/system/crosstalk_relay.py`

The older OneDrive/Dropbox AI Workspace path is not the canonical lane anymore.

## Current operating rule

When either agent finishes meaningful work:

1. emit a cross-talk packet
2. verify it landed on repo lanes
3. verify it landed in `Cross Talk.md`
4. keep proof paths in the packet summary

## Current shared state as of 2026-03-17

- browser-first AetherBrowser lane is active
- Hugging Face browser navigation and unified search wrappers exist
- cross-talk relay is repaired against the live Avalon vault
- phone lane has a device shell plus telemetry parser
- audio gate spectrum reporting is live
- formal axiom coverage now distinguishes legacy wall-law tests from current reference-pipeline tests

## Useful packet subjects

- browser surface changes
- vault path changes
- model training pushes
- phone/emulator state changes
- formal axiom/test changes
- publishing and revenue lane status

## Current rule for stale docs

If repo reality changes, update both:

- the repo doc or test proving the change
- the vault note that humans will actually read later

The handoff is not complete until both are updated.
