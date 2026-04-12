---
title: Playwright Plugin - Browser Automation Lane
type: plugin-note
updated: 2026-04-11
source: C:\Users\issda\.codex\skills\playwright\SKILL.md
tags:
  - plugins
  - playwright
  - browser
  - automation
  - lane
---

# Playwright Plugin - Browser Automation Lane

The Playwright lane is the terminal-first browser automation surface. Its job is direct browser control: open pages, snapshot DOM state, click, fill, press keys, capture screenshots, and debug UI flows from the shell.

## Role in the browser system

- Acts as the low-level execution lane for browser tasks.
- Prefers CLI-driven interaction over test-spec generation.
- Uses snapshots as the stable reference surface for actions.
- Fits under the governed browser system rather than replacing it.

## Core behavior

- Open a page.
- Snapshot the page.
- Act on stable element references from the latest snapshot.
- Re-snapshot after navigation or large DOM changes.
- Capture evidence when needed.

## Source surfaces

- Skill definition: `C:\Users\issda\.codex\skills\playwright\SKILL.md`
- Wrapper script family: `$CODEX_HOME/skills/playwright/scripts/`

## Relationship to AetherBrowse

Playwright is the execution lane that AetherBrowse can call into or mirror. It is not the full browser system by itself.

- For the full governed browser stack, see [[AetherBrowse Plugin - Governed Browser Stack]].
- For shared browser fields and UI surfaces, see [[Browser System Fields and Surfaces]].
- For the dated source map, see [[Plugin Source Snapshot - 2026-04-11]].
