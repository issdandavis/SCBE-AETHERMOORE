# GitHub Order And Notes Sync

This checklist keeps local knowledge from being stranded.

## Repository Order

1. Keep `README.md` high-level only.
2. Put executable architecture docs in `docs/`.
3. Keep test-backed systems in `src/` + `tests/`.
4. Keep launch/promotional assets in `content/marketing/`.

## Local Notes To GitHub Flow

1. Build a manifest from local markdown/text notes:

```powershell
python scripts/system/inventory_notes_for_github.py --root . --out artifacts/notes_manifest.json
```

2. Review candidates (size, path, modified date).
3. Promote only high-signal notes into one of:
   - `docs/`
   - `notes/`
   - `training/intake/`
4. Commit promoted notes in focused batches by topic.

## Suggested Priority Buckets

- `P0`: architecture decisions and operating runbooks
- `P1`: validated research notes
- `P2`: rough brainstorms and drafts

## Guardrails

- Never commit secrets/API tokens from local notes.
- Redact personal/sensitive text before push.
- Keep one-topic-per-commit for traceable history.
