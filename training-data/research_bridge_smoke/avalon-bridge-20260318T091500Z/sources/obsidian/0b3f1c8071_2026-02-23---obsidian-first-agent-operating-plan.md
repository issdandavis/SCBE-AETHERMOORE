---
title: Obsidian-First Agent Operating Plan
date: 2026-02-23
tags: [scbe, obsidian, workflow, agent-ops]
status: active
---

# Obsidian-First Agent Operating Plan

## Objective
Use Obsidian as the private operational memory for all terminal agents so code stays cleaner and process context is preserved.

## Operating Rule
- If it is strategy, analysis, decision rationale, or worklog -> write to Obsidian.
- If it is implementation behavior required for maintainers -> minimal code comments/docs.

## Standard Agent Flow
1. **Context Check**
- Read latest `Agent Ops` index + active work queue.
- Verify repo state before making claims.

2. **Plan Note**
- Create/update plan note with:
  - objective
  - constraints
  - risks
  - explicit execution steps

3. **Execution**
- Run commands/edits.
- Log key evidence in worklog (counts, file paths, commit SHAs).

4. **Results Note**
- Capture outcomes, blockers, deltas, and next actions.

## Folder Contract
- `Agent Ops/` -> live coordination notes
- `Agent Ops/Templates/` -> reusable templates
- `References/` -> long-form source dumps and external inputs

## Mandatory Fields for Every Agent Session
- Scope
- Inputs/Sources
- Actions Taken
- Evidence
- Decision
- Next Step Owner

## Hygiene Rules
- No secrets in Obsidian notes.
- No raw credentials copied anywhere.
- Sensitive architecture/commercial strategy stays in private vault/private repo.

## Weekly Cadence
- Monday: refresh priorities + backlog pruning
- Daily: session logs and execution results
- Friday: one-page weekly outcome summary
