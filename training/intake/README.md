# Production Intake Folder

Place raw exports from operational systems here.

## Cold Archive Note

The largest raw export buckets were moved to cold archive on 2026-04-11:

- `grok_export` -> `C:\Users\issda\OneDrive\SCBE-Archives\training_cold_2026-04-11\grok_export`
- `claude_export` -> `C:\Users\issda\OneDrive\SCBE-Archives\training_cold_2026-04-11\claude_export`

Reason:

- these are raw upstream archives
- they are useful for reference and recovery but do not need to occupy the active repo hot path

See:

- `docs/operations/TRAINING_STORAGE_CLASSIFICATION_2026-04-11.md`
- `docs/operations/REPO_ARCHIVE_OFFLOAD_2026-04-11.md`

## Supported Inputs

- `airtable/*.jsonl`
- `asana/*.jsonl`
- `protonmail/*.jsonl`
- `gumroad/*.jsonl`
- `google_business/*.jsonl`
- `zapier/*.jsonl`
- Any nested `*.json` under `training/intake/`

## Minimal Record Shape

JSONL or JSON object/list with at least one text-bearing field:

- `text`, `content`, `body`, `description`, `notes`, `message`, `title`, or `summary`

Optional provenance fields:

- `id`
- `source_system` / `tool` / `app`
- `event_type`
- `created_at` / `timestamp`
- `category`

## Example JSONL row

```json
{"source_system":"asana","id":"task-123","event_type":"task_update","created_at":"2026-02-19T00:00:00Z","title":"Kernel triage","notes":"Refine source filters and publish verified dataset batch.","category":"ops"}
```

