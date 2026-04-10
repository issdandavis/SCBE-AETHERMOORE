---
name: scbe-document-management
description: Consolidate overlapping docs, classify files by authority, and keep SCBE repo documents aligned with runtime truth. Use when the repo has drift between canonical docs, public docs, proposal notes, research branches, and generated evidence.
---

# SCBE Document Management

Use this skill when documentation is drifting, duplicated, or too mixed to trust quickly.

## Workflow

1. Read `AGENTS.md`.
2. Read `CANONICAL_SYSTEM_STATE.md`.
3. Read `REPO_SURFACE_MAP.md`.
4. Read `docs/operations/DOCUMENT_MANAGEMENT_OPERATING_MODEL.md`.
5. Identify the target topic and classify every relevant file as canonical, operational, public, runtime reference, exploratory, historical, or generated.
6. Consolidate toward the highest-authority valid destination.
7. Leave lower-authority files as pointers, legacy notes, or historical context instead of letting them silently redefine the system.

## Working Rules

- Update canonical docs before public docs.
- Treat runtime code and proving tests as stronger than explanatory notes.
- Do not let generated outputs, corpora, or storage-heavy folders define the repo narrative.
- If one topic has multiple “master” files, reduce it to one authority file and demote the rest.
- Prefer small consolidation passes over giant rewrites.

## River Map Rules

Use the document channels from `references/document-channels.md`:

- main channel = canonical + operational
- side channel = useful support docs
- archive channel = preserved history
- dry channel = exploratory notes
- gated channel = generated evidence and storage-heavy outputs

When in doubt, move the working truth toward the main channel and keep everything else explicitly downstream of it.

## Good Targets

Use this skill for:

- formula drift cleanup
- status-language cleanup
- repo startup map cleanup
- funding / proposal contact consolidation
- converting scattered notes into one operator file
- deciding whether a doc belongs in `docs/`, `notes/`, or a generated path

## Avoid These Mistakes

- Do not treat `README.md` as mathematical authority.
- Do not promote research notes straight into canonical docs without checking runtime/test reality.
- Do not delete historical files just because they are stale; demote them first.
- Do not use storage-heavy folders as the source of truth for process or architecture.

## Optional Future Extension

If a stateful document registry is later built with Cloudflare Agents SDK, keep it as an operator over this manual model:

- stateful registry of document classes
- workflow-based promotion from exploratory → canonical
- audit trail for document authority changes

That future agent should enforce this model, not invent a second one.

## References

- `references/document-authority.md`
- `references/document-channels.md`
- `references/cloudflare-doc-registry-agent.md`
