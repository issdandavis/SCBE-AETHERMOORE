---
name: scbe-doc-maker
description: Build local-first fiction and non-fiction documents from SCBE sources with verifiable citations, structured outlines, and export-ready artifacts. Use when asked to draft, revise, synthesize, or package books, reports, specs, or training corpora from repo/wiki/notes.
---

# SCBE Doc Maker

Use this workflow to produce publishable and auditable documents without external paid tooling.

## Workflow

1. Define target output.
2. Define audience, tone, and acceptance criteria.
3. Build a source manifest with exact file/URL/date for every input.
4. Normalize source structure before drafting.
5. Draft in passes: outline, skeleton, full prose, final tighten.
6. Tag every factual claim with source references.
7. Produce final package and change log.

## Required Outputs

1. `source_manifest.json` with `id`, `path_or_url`, `retrieved_at`, `hash_or_commit`.
2. `outline.md` with chapter or section IDs.
3. `draft.md` or `final.md` with stable heading IDs.
4. `decision_record.json` with material choices and tradeoffs.

## Guardrails

1. Keep generation local-first.
2. Treat remote model calls as optional helpers, not required dependencies.
3. Preserve canon or spec invariants when working on long-running series.
4. Refuse silent source substitution.
5. Mark uncertain content as hypothesis.
