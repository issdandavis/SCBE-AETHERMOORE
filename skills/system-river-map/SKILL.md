---
name: system-river-map
description: Build and use a river-style machine map for SCBE cleanup, storage routing, and path-risk decisions on Windows. Use when a task needs a machine topology view before deleting, moving, offloading, or deduplicating data across local disks, sync roots, offload mirrors, junctions, and archive surfaces.
---

# System River Map

Use this skill before broad cleanup.

The goal is to map the machine like a watershed so cleanup work follows channels instead of guessing at folders.

This skill produces a topological reachability map for cleanup routing. It is not meant to replace a full file inventory.

## What this skill does

1. Scans reachable storage roots and mounted drives
2. Identifies canonical channels, sync edges, archive basins, and offload lanes
3. Resolves top-level reparse points that can hide path drift
4. Marks reparse targets as reachable, dry, or unresolved
5. Emits a machine-readable and human-readable map
6. Uses the map to route cleanup decisions safely

## Use this skill when

- the user wants a system map before cleanup
- storage feels duplicated across Dropbox, Drive, OneDrive, or external disks
- folders might be junctions, placeholders, or broken relocated paths
- a cleanup task spans repo work, cloud mirrors, and local drives
- you need to decide what is canonical before moving or deleting

## Default workflow

### 1. Generate a fresh scan

Run:

```powershell
pwsh -File skills/system-river-map/scripts/system_river_scan.ps1
```

This writes outputs into `artifacts/system-river-map/`.

### 2. Read the current machine map

Use the generated markdown report first.

If repo-specific context matters, also read:

- `docs/map-room/system_reachability_river_map.md`

### 3. Classify the target path

Every target should be placed into one of these buckets:

- main channel
- side channel
- archive basin
- dry channel
- gated channel

Do not mutate anything until the path has a bucket.

### 4. Apply cleanup routing

- Prefer canonical channels for preserved state
- prefer archive or offload basins for cold data
- treat sync edges as volatile until compared against the canonical path
- treat broken relocation targets as dry channels
- stop before destructive cleanup when the route is still ambiguous

## Operating rules

- Resolve reparse points before assuming path ownership
- Prefer verified duplicates over guess-based deletion
- Prefer canonical ledgers over sync-engine wrappers
- Treat current Dropbox edges as volatile
- Treat archive mirrors as read-mostly comparison basins
- Treat external drives as cold-storage targets, not live working roots

## Known SCBE channel model

The default SCBE channel order is:

1. live repo
2. canonical Drive storage
3. old archive mirror
4. current sync edge
5. OneDrive offload shell-folder layer
6. external cold-storage drives

See `docs/map-room/system_reachability_river_map.md` for the machine-specific version.

## Outputs

The scan script emits:

- `artifacts/system-river-map/latest.json`
- `artifacts/system-river-map/latest.md`

Use these as the current cleanup routing source of truth for the session.
