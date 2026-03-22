---
name: scbe-claim-to-code-evidence
description: Map SCBE Notion technical claims, proof pages, and patent-facing architecture notes to concrete repository evidence such as code paths, tests, demos, and docs. Use when Codex needs to build a due-diligence packet, claim-to-code audit, implementation crosswalk, patent support note, or proof summary from local Notion exports and repo artifacts.
---

# SCBE Claim To Code Evidence

## Overview

Use this skill to turn SCBE Notion material into repo-backed evidence instead of vague positioning. Start with the local Notion corpus and existing repo manifests, then map each important page or claim to code, tests, and demo surfaces.

## Quick Start

1. Build the starter evidence packet:

```powershell
python skills/scbe-claim-to-code-evidence/scripts/build_evidence_packet.py --repo-root .
```

2. Read the generated outputs:
- `artifacts/notion_claim_evidence/starter_manifest.json`
- `artifacts/notion_claim_evidence/starter_manifest.md`

3. For deeper matching, run the repo-wide comparator:

```powershell
python scripts/compare_notion_to_codebase.py
```

## Workflow

1. Start from the local inventory, not live search.
- Read `docs/notion/NOTION_USEFUL_PAGES_SHORTLIST_2026-03-15.md`.
- Read `docs/notion/NOTION_TECH_CORPUS_INVENTORY_2026-03-15.md`.
- Use `training-data/notion_raw_clean.jsonl` as the main page-text source.

2. Reuse existing repo mappings first.
- Read `docs/notion_pages_manifest.json` before doing new search work.
- Treat existing `verification_state` and `code_paths` as the fastest first pass.

3. Build evidence rows per page or claim.
- `claim_or_page`
- `notion_id`
- `source_url`
- `repo_code_paths`
- `repo_test_paths`
- `demo_or_api_paths`
- `state`: `implemented|tested|partial|unmapped`
- `notes`

4. Search only where the manifest is weak.
- Prefer `rg` across `src`, `api`, `scripts`, `docs`, and `tests`.
- Search by component nouns, not marketing phrases.
- If a page is mostly architectural, map it to the narrowest concrete runtime surface available.

5. Keep proof and aspiration separate.
- If a page claims something the repo does not show, mark it `partial` or `unmapped`.
- Do not upgrade a claim to `implemented` without at least one concrete repo path.
- Prefer explicit test linkage whenever possible.

6. Produce deterministic artifacts.
- JSON manifest for machine reuse
- Markdown brief for humans
- short missing-proof list for next work

## Evidence Rules

- Favor pages in `references/priority_pages.json` first.
- Favor already-mapped pages in `docs/notion_pages_manifest.json` before new manual crosswalks.
- Use `scripts/compare_notion_to_codebase.py` when the page title is known but the implementation path is not.
- When a page is patent-facing, look for both code and tests before claiming reduction to practice.

## Output Contract

Return:
- concise summary of strongest proven pages
- list of weak or unmapped pages
- artifact paths for JSON and markdown outputs
- explicit next mapping targets

## Resources

- `references/priority_pages.json`: top Notion pages to map first
- `references/evidence_schema.md`: field contract for evidence rows
- `scripts/build_evidence_packet.py`: generate a starter evidence manifest from the repo shortlist and existing page manifest
