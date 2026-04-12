---
title: Browser System Fields and Surfaces
type: plugin-fields
updated: 2026-04-11
source: plugin skills, docs, and browser API surfaces
tags:
  - browser-system
  - fields
  - rooms
  - vault
  - ops
---

# Browser System Fields and Surfaces

This note tracks the browser-side fields that show up repeatedly across the AetherBrowse system. It is the note to use when asking what the browser lane is actually composed of.

## Operational fields

- Perceive
- Plan
- Govern
- Execute

These are the control fields of the governed browser loop.

## User-facing surfaces

- Browse
- Chat
- Rooms
- Vault
- Ops

These are the visible browser surfaces referenced by the mobile and API-backed browser system.

## Structural meaning

- `Browse` is direct page navigation.
- `Chat` is the assistant interaction surface.
- `Rooms` is local context or grouped workspace state.
- `Vault` is the note or memory surface.
- `Ops` is diagnostics, orchestration, and control.

## Relationship to plugins

- [[Playwright Plugin - Browser Automation Lane]] operates the page-level automation lane.
- [[AetherBrowse Plugin - Governed Browser Stack]] binds those fields into one governed browser system.

## Tracking use

This note is intended for graph linkage and snapshot comparison. It should be treated as a stable field map, not a mutable runtime spec.
