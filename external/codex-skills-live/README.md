## Codex Skills Live Mirror

This directory is a repository-tracked mirror of the live local Codex skills tree from `C:\Users\issda\.codex\skills`.

Purpose:
- preserve the full local skill library on GitHub
- keep the backup separate from active repo skill loaders
- allow later diff and consolidation work without changing runtime behavior

Rules:
- treat this as an archival mirror first, not the canonical runtime skill path for this repo
- preserve upstream folder names from the live local tree
- reconcile duplicates into `skills/`, `.claude/skills/`, or plugin skill packs in later passes
