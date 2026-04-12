---
title: AetherBrowse Plugin - Governed Browser Stack
type: plugin-note
updated: 2026-04-11
source: plugins\aetherbrowse\.claude-plugin\plugin.json and plugins\aetherbrowse\skills\*
tags:
  - plugins
  - aetherbrowse
  - browser
  - governance
  - electron
  - playwright
---

# AetherBrowse Plugin - Governed Browser Stack

AetherBrowse is the higher-order browser plugin surface. It wraps browser operation in governance, runtime APIs, worker execution, and UI shell layers.

## Current plugin truth

- Plugin name: `aetherbrowse`
- Description: `Full development and operations toolkit for the AetherBrowse governed AI browser`
- Keywords include `playwright`

## Three-process stack

1. Python runtime server
- `plugins\aetherbrowse\aetherbrowse\runtime\server.py`

2. Playwright worker
- `plugins\aetherbrowse\aetherbrowse\worker\browser_worker.py`

3. Electron shell
- `plugins\aetherbrowse\aetherbrowse\electron\main.js`

## Agent loop

- `PERCEIVE`
- `PLAN`
- `GOVERN`
- `EXECUTE`

This makes AetherBrowse more than a browser wrapper. It is a governed browser lane.

## Why it matters

- Playwright is the motor.
- The runtime server is the coordination layer.
- The Electron shell is the operator surface.
- Governance is what turns generic browsing into SCBE browser behavior.

## Related notes

- [[Playwright Plugin - Browser Automation Lane]]
- [[Browser System Fields and Surfaces]]
- [[Plugin Source Snapshot - 2026-04-11]]
