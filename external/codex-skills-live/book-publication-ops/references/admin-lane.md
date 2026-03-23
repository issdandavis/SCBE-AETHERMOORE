# Admin Lane

## When To Use

Use the admin lane when publication work turns into:

- long-running review loops
- many generated artifacts
- backup-heavy staging
- multi-agent packaging or upload prep

## Artifact Layout

Prefer:

```text
artifacts/publication/
├── audits/
├── previews/
├── review_packets/
├── cover_specs/
├── publish_packets/
└── manifests/
```

## Safety

1. Never delete the canonical manuscript during publication automation.
2. Back up publication packets before pruning local derived artifacts.
3. Keep final upload files checksum-stable once text is locked.

## SCBE Hooks

If the user wants continuous or admin-backed operation, reuse:

- `python scripts/system/ship_verify_prune.py --source <path> --dest <backup1> --dest <backup2> --min-verified-copies 2`
- `python scripts/system/system_hub_sync.py --help`

Use `--delete-source` only when the user explicitly asks for prune behavior.
