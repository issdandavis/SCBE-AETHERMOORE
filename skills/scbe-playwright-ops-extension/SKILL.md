---
name: scbe-playwright-ops-extension
description: Command-line Playwright extension that combines deterministic HYDRA terminal browsing evidence, Playwright capture, cross-talk packet emission, and handoff packaging with speed-line lane outputs.
---

# SCBE Playwright Ops Extension

Use this when you want one command to run a useful browser ops packet with governance artifacts.

This skill composes:
- `playwright` for browser capture
- `hydra-node-terminal-browsing` for deterministic evidence JSON
- `agent-handoff-packager` for resume-ready handoff docs
- `speed-line-delivery` for lane-based one-line execution
- `hydra-clawbot-synthesis` and `scbe-universal-synthesis` alignment via artifact contracts

## Command

Run from repo root:

```powershell
python skills/scbe-playwright-ops-extension/scripts/playwright_extension_runner.py --url "https://example.com" --task-id "PWX-001" --summary "Capture and package browser evidence"
```

## What It Produces

- `artifacts/playwright_extension/terminal_browse.json`
- `artifacts/playwright_extension/playwright_capture/*.json`
- `artifacts/playwright_extension/handoff.md`
- `artifacts/playwright_extension/speed_lines.txt`
- `artifacts/playwright_extension/run_report.json`

## Behavior

1. Attempts deterministic node browse using:
- `C:\Users\issda\.codex\skills\hydra-node-terminal-browsing\scripts\hydra_terminal_browse.mjs`

2. Runs Playwright capture using repo tool:
- `scripts/agentic_web_tool.py --engine playwright capture`

3. Emits cross-talk packet using required fields:
- `scripts/system/crosstalk_relay.py emit --sender --recipient --task-id --summary ...`

4. Writes handoff markdown with the standard structure for agent resume.

5. Writes lane-based speed commands in `speed_lines.txt`.

6. Optional Notion payload export (`--emit-notion-payload`) for API-first page creation.

## Options

- `--skip-node-browse` to bypass node evidence capture
- `--skip-crosstalk` to bypass relay emission
- `--engine auto|playwright|http` for capture backend
- `--sender`, `--recipient`, `--intent` for cross-talk routing

## Safety

- Never place secrets in summaries or proof fields.
- Cross-talk uses append-only packet lanes.
- All outputs are artifact-first for deterministic audits.
