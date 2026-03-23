---
date: 2026-03-17
tags:
  - agent-ops
  - browser-first
  - cross-talk
  - obsidian-sync
status: active
---

# 2026-03-17 - Browser Mesh and Vault Sync

## Summary

The vault was behind the repo. This sync pulls the live system state forward.

Main changes now reflected here:

- AetherBrowser is the default operator surface for online work.
- Cross-talk relay is writing into the live Avalon vault again.
- GitHub, Hugging Face, and generic web search now route through repo browser surfaces.
- The phone lane has a real shell layout and telemetry parser.
- The audio gate spectrum experiment is now backed by runnable code.
- Formal axiom coverage is cleaner because legacy Layer 12 wall-law tests and current reference-pipeline tests are split.

## Current browser-first stack

- `agents/aetherbrowse_cli.py`
- `scripts/system/browser_chain_dispatcher.py`
- `scripts/system/playwriter_lane_runner.py`
- `scripts/system/aetherbrowser_search.py`
- `scripts/system/aetherbrowser_huggingface_nav.py`

## Current coordination stack

- `scripts/system/crosstalk_relay.py`
- `Cross Talk.md`
- `artifacts/agent_comm/...`
- `artifacts/agent_comm/github_lanes/cross_talk.jsonl`

## Current device shell stack

- `kindle-app/www/device-shell.html`
- `scripts/system/phone_eye.py`
- `scripts/system/phone_navigation_telemetry.py`

## Current axiom clarification

Do not collapse these into one thing:

- reference Layer 12 score: bounded `1 / (1 + d + 2*phase_deviation)`
- legacy wall-law modules: `H(d,R)=R^(d^2)`

That split is now part of the docs and tests.

## Why this matters

The repo is no longer just a theory archive. The active lanes now line up:

- browser
- relay
- vault
- phone
- audio telemetry
- formal verification

That makes the system easier to operate and easier to explain.
