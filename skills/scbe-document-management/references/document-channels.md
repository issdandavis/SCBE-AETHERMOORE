# Document Channels

Use the repo like a river map instead of one flat pile.

## Main channel

Current canonical and operational docs that must stay aligned with runtime truth.

Examples:

- `CANONICAL_SYSTEM_STATE.md`
- `REPO_SURFACE_MAP.md`
- `docs/operations/DOCUMENT_MANAGEMENT_OPERATING_MODEL.md`

## Side channel

Useful support docs that help run a lane but are not primary authority.

Examples:

- proposal checklists
- packaging notes
- release checklists

## Archive channel

Historical docs kept for memory, provenance, or rollback context.

Examples:

- old reports
- old migration notes
- old handoff packets

## Dry channel

Exploratory branches that are still live ideas but not promoted into system truth.

Examples:

- phi / fractal / M4NMM drafts
- speculative proof notes
- forward architecture branches

## Gated channel

Generated evidence, exports, corpora, and storage-heavy outputs.

Examples:

- `artifacts/`
- `training-data/`
- `dist/`
- exports and screenshots

Rule:

If a file changes how the system is explained or operated, it belongs in main or side channel.
If a file mainly stores outputs or history, it belongs downstream.
