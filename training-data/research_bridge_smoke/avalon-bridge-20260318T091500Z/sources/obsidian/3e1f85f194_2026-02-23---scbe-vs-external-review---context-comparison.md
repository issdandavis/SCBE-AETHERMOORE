---
title: SCBE vs External Review - Context Comparison
date: 2026-02-23
tags: [scbe, audit, comparison, repo-hygiene]
status: finalized
---

# SCBE vs External Review - Context Comparison

## Goal
Compare the pasted external review against the **actual current system state** before planning changes.

## Sources
- User pasted review text (53 repos, 4,720 files, etc.)
- Local repo audit: `C:\Users\issda\SCBE-AETHERMOORE`
- GitHub inventory: `gh repo list issdandavis --limit 200`
- Grok source note: `C:\Users\issda\OneDrive\Documents\DOCCUMENTS\A follder\Grok Dump.md`
- NotebookLM reference: `https://notebooklm.google.com/notebook/bf1e9a1b-b49c-4343-8f0e-8494546e4f24`

## Reality Snapshot (Current)
- GitHub repos under `issdandavis`: **57**
- Tracked files in main repo (`git ls-files`): **4,994**
- Local working-copy files (includes deps/build/cache): **22,257**
- `src` files: **1,205**
- `docs` files: **490**
- `tests` files: **416**
- `.hypothesis` files present locally: **1,986**
- `.hypothesis` files still tracked in git: **1,201**
- M4 module exists in source: `src/m4mesh/*` (manifest, cvl, geometry, mesh_graph, metrics, pipeline, smear, tie_kb, wave)
- M4 tests exist: `tests/interop/test_m4_*`

## Claim-by-Claim Check (External Review)
1. "53 repos" -> **Outdated** (actual 57).
2. "4,720 files" -> **Close but stale** (tracked 4,994 now; local 22,257 due generated/dependency files).
3. ".hypothesis tracked problem" -> **Correct and still relevant** (1,201 tracked).
4. "No dedicated M4 docs" -> **Mostly correct** (M4 lives in source/tests; no dedicated docs-named M4 markdown).
5. "M4 skeleton is cleaner" -> **Consistent with current code layout** (`src/m4mesh` present with clear module boundaries).
6. "Benchmark claims need reproducibility" -> **Still a valid governance item**; public claims should map to reproducible scripts.
7. "Repo sprawl causes confusion" -> **Still relevant**; multi-repo positioning should be explicit (canonical public + private crown-jewel split).

## High-Value Issues (Confirmed)
- Repo hygiene debt: tracked `.hypothesis` corpus should be untracked from public canonical repo.
- Public/private boundaries must stay explicit (already improved with `SCBE-private`, but needs routine process).
- Messaging and proof artifacts should be organized in private notes so code stays implementation-focused.

## Immediate Recommendation
Adopt Obsidian-first process:
- Planning, research synthesis, and decision logs in private Obsidian vault.
- Code comments limited to implementation-critical context only.
- Public repo gets concise docs; sensitive process/strategy stays private.
