---
name: skill-synthesis
description: Compose multiple installed skills into one coordinated execution stack with ordered packets, minimal context load, and deterministic handoff artifacts. Use when tasks span multiple domains (for example HYDRA + browser + training + deploy) and you need a single combined workflow instead of invoking skills one-by-one.
---

# Skill Synthesis

## Overview
Use this skill to fuse multiple installed skills into one execution loop with clear ordering, packet boundaries, and artifacts.

## Quick Start

1. Build a stack from a task prompt.
```powershell
python C:\Users\issda\.codex\skills\skill-synthesis\scripts\compose_skill_stack.py --task "Build gamma funnels and deploy" --top 8
```

2. Run the resulting packets in order from highest leverage to lowest risk.

## Workflow

### 1) Select Minimal Stack
- Pick one **primary** skill (owns outcome).
- Pick up to four **support** skills (execution lanes).
- Do not load the whole skill catalog unless explicitly requested.

### 2) Build Ordered Packets
- Packet A: discovery/research
- Packet B: implementation
- Packet C: validation/smoke
- Packet D: publish/deploy
- Packet E: evidence + vault notes

### 3) Execute with Context Discipline
- Keep live context to only the active packet.
- Move long notes to artifacts or vault docs.
- Keep source links and proofs in packet output.

### 4) Output Contract
- stack plan JSON
- ordered packet list
- execution report (what ran, what passed, what is blocked)

## Built-in Stack Profiles

### `hydra-library-wing`
- `hydra-clawbot-synthesis`
- `aetherbrowser-arxiv-nav`
- `aetherbrowser-github-nav`
- `hugging-face-model-trainer`
- `notion`

Use for deep research + dataset handoff + multi-agent synthesis.

### `revenue-gamma-funnel`
- `living-codex-browser-builder`
- `article-posting-ops`
- `scbe-shopify-money-flow`
- `aetherbrowser-shopify-nav`
- `vercel-deploy`

Use for landing pages, conversion flow, and web deployment.

### `platform-release`
- `development-flow-loop`
- `playwright`
- `scbe-connector-health-check`
- `vercel-deploy`

Use for implementation -> smoke -> deploy.

## Rules
- Favor official docs and primary sources for unstable facts.
- Keep stack size small unless user explicitly asks for full-spectrum mode.
- Prefer deterministic scripts and repeatable packets over ad-hoc chat instructions.
- Record evidence paths for every packet.

## Resources

### scripts/
- `compose_skill_stack.py`: Generate ranked skill stacks and packet plans from a task description.

### references/
- `stack-profiles.md`: Reusable profile templates and packet recipes.
