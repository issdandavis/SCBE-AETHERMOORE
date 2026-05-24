# Cloud RAG Storage Contract

Status: operational storage rule, not a sync-client promise.

The machine has three different storage jobs:

1. Active working set: source code, notes, manuscripts, and files being edited today.
2. Cold archive: bulky generated outputs, snapshots, old runs, videos, audio renders, and cache-like exports.
3. RAG index: small local metadata that lets agents find and reason over cold archive files without keeping every byte hot on `C:`.

Do not treat a folder named `Drive` as cloud storage. A path only counts as an
offload target when it is a mounted cloud or archive root such as `G:\My Drive`,
`H:\My Drive`, `I:\My Drive`, `I:\Shared drives`, a verified external/archive
volume such as `E:\`, or the real OneDrive root when it is configured for
actual online-only/off-device storage.

## Rule

An offload is only complete when all four checks pass:

1. Copy exists at the destination.
2. File count matches.
3. Byte total and SHA-256 hashes match.
4. `C:` free space increases after the local source is removed.

If check 4 does not pass, the file was copied into a local sync cache, not truly offloaded.

## Local Catalog

RAG-visible archive stubs live at:

```text
.scbe/cloud_rag/catalog.jsonl
```

Each row records:

- archive id
- original source root
- cloud destination root
- relative path
- byte size
- SHA-256
- MIME type
- short text preview for text-like files

This lets agents retrieve and reason about the archive without keeping generated media or old snapshots in the active repo.

## Command

Discover mounted cloud roots:

```powershell
python scripts/system/cloud_rag_archive.py discover
```

Rank local archive/offload candidates:

```powershell
python scripts/system/cloud_rag_archive.py inventory --limit 25
```

Plan an offload without copying or deleting:

```powershell
python scripts/system/cloud_rag_archive.py archive `
  --source "C:\path\to\folder" `
  --cloud-root "G:\My Drive" `
  --bucket "SCBE_RAG_ARCHIVE" `
  --lane "generated-media" `
  --delete-source `
  --dry-run
```

Archive, verify, catalog, and preserve the local source:

```powershell
python scripts/system/cloud_rag_archive.py archive `
  --source "C:\path\to\folder" `
  --cloud-root "G:\My Drive" `
  --bucket "SCBE_RAG_ARCHIVE" `
  --lane "generated-media"
```

Archive, verify, catalog, and delete the local source only after verification:

```powershell
python scripts/system/cloud_rag_archive.py archive `
  --source "C:\path\to\folder" `
  --cloud-root "G:\My Drive" `
  --bucket "SCBE_RAG_ARCHIVE" `
  --lane "generated-media" `
  --delete-source
```

If verification completed but Windows blocked source deletion, retry cleanup from
the verified manifest:

```powershell
python scripts/system/cloud_rag_archive.py cleanup-verified `
  --manifest ".scbe\cloud_rag\latest_offload_manifest.json"
```

## Keep Local

- active repo source
- `notes/`
- current manuscripts
- current polished audio stems
- secrets and local-only configuration

## Cold Archive First

- generated videos
- generated audio experiments
- old training runs
- timestamped snapshots
- build outputs
- cache exports
- upload staging folders
