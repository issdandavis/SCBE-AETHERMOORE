# System Reachability River Map

This map treats the machine like a watershed.

- Headwaters are physical or mounted roots.
- Main channels carry active work.
- Side channels are sync, archive, or offload mirrors.
- Dry channels are broken junctions or stale paths.
- Dams are permission, lock, or tool-boundary constraints.
- This is a topological reachability map, not a full file-by-file inventory.

## 1. Water Sources

### Primary basin

- `C:\Users\issda`
- Active repo: `C:\Users\issda\SCBE-AETHERMOORE`
- Canonical SCBE storage root: `C:\Users\issda\Drive\SCBE`

### Mounted tributaries

- `C:\` main system volume, about 25 GB free at scan time
- `E:\` dossier/archive lane
- `F:\` offload lane
- `S:\` mounted but gated; root listing returned access denied

## 2. Main Channel

This is the path to prefer for live SCBE cleanup and state decisions.

1. `C:\Users\issda\SCBE-AETHERMOORE`
2. `C:\Users\issda\Drive\SCBE`
3. `C:\Users\issda\Drive\SCBE\local-workspace-sync`

Observed canonical SCBE contents under `Drive\SCBE`:

- `Knowledge_Library`
- `local-workspace-sync`

Interpretation:

- `SCBE-AETHERMOORE` is the live working tree.
- `Drive\SCBE\local-workspace-sync` is the canonical sync-history ledger.
- Cleanup work should check this channel first before touching Dropbox copies.

## 3. Side Channels

### Current Dropbox lane

- `C:\Users\issda\Dropbox`
- Top-level state is placeholder-heavy and sync-engine driven.
- Recent SCBE selective-sync conflicts appeared as reparse-point wrappers, not stable local folders.

Current notable items:

- `_PC_Inventory`
- `.dropbox.cache`
- `_sync_summary.txt`
- stale or placeholder `SCBE (Selective Sync Conflict N)` entries may appear and disappear as Dropbox settles

Operational meaning:

- Treat current Dropbox as a volatile sync edge, not the canonical SCBE store.
- Delete or merge only after checking whether the same run already exists under `Drive\SCBE\local-workspace-sync`.

### Old Dropbox lane

- `C:\Users\issda\Dropbox (Old)`
- `SCBE` exists here as a linked archive surface
- `SCBE\local-workspace-sync` contains older run folders from `20260329...` through `20260330...`
- `SCBE\backup-2026-03-30` also exists

Operational meaning:

- This is an archive basin.
- Good for recovery and comparison.
- Bad as a default write target.

### OneDrive offload lane

- `C:\Users\issda\OneDrive`
- visible roots:
  - `Documents`
  - `Dropbox`
  - `Offload`
  - `Pictures`
  - `Proton_Sync`
  - `Videos`

Observed offload structure:

- `C:\Users\issda\OneDrive\Offload\CrossDevice`
- `C:\Users\issda\OneDrive\Offload\Pictures`

High-value shell-folder redirects:

- `C:\Users\issda\Documents -> C:\Users\issda\OneDrive\Offload\Documents`
- `C:\Users\issda\Pictures -> C:\Users\issda\OneDrive\Offload\Pictures`
- `C:\Users\issda\workspace -> C:\Users\issda\OneDrive\Offload\workspace`

Operational meaning:

- This lane is part live shell-folder routing, part cold storage.
- Cleanup tasks must resolve junction targets before moving user files.

### External/offload drives

`E:\`

- `SCBE_DOSSIER_RUNS`

`F:\`

- `SCBE_Offload`
- `2T5CY.docx`

Operational meaning:

- `E:\` and `F:\` are low-cost overflow basins.
- Favor them for cold archives, bulky exports, and validated backups.

## 4. Dry Channels

Top-level user-profile junctions show a relocation pattern into `D:\Relocated\...`, but `D:\` is not currently mounted as a filesystem drive in this session.

Confirmed dry targets:

- `C:\Users\issda\source -> D:\Relocated\source`
- `C:\Users\issda\SCBE-AETHERMOORE-BEST -> D:\Relocated\AI_SCBE\SCBE-AETHERMOORE-BEST`

`D:\` checks at scan time:

- `D:\` does not exist
- `D:\Relocated\source` does not exist
- `D:\Relocated\AI_SCBE\SCBE-AETHERMOORE-BEST` does not exist

Operational meaning:

- These are dry riverbeds.
- Any cleanup or move plan that trusts these junctions without checking target existence will misroute data.

## 5. Dams And Gates

### Permission dams

- `S:\` root access denied

### Sync dams

- Dropbox conflict wrappers can be locked by the sync process while cleanup is running
- placeholder reparse points can reappear during a delete pass

### Tool-boundary dams

- Repo-native write lane without escalation is the current repo plus `.codex\memories`
- broad local inspection is available through shell commands
- remote Dropbox inspection is available through the Dropbox connector, but mutation support is limited here

Operational meaning:

- Use shell for broad discovery
- use repo files for durable maps/runbooks
- use escalation only when mutating paths outside the repo or when deleting locked sync surfaces

## 6. Cleanup Routing Rules

Use this order for complex cleaning work:

1. Identify the channel
   - live repo
   - canonical Drive store
   - current Dropbox edge
   - old Dropbox archive
   - OneDrive offload
   - external/offload drive
2. Resolve reparse points before acting
3. Check whether the same state already exists in `Drive\SCBE\local-workspace-sync`
4. Preserve canonical history first, then remove duplicate wrappers
5. Treat `D:\Relocated\...` targets as suspect until proven mounted
6. Treat `S:\` as gated until an explicit access path is available

## 7. Current High-Value Map For SCBE Cleanup

- Live code channel: `C:\Users\issda\SCBE-AETHERMOORE`
- Canonical sync ledger: `C:\Users\issda\Drive\SCBE\local-workspace-sync`
- Archive mirror: `C:\Users\issda\Dropbox (Old)\SCBE\local-workspace-sync`
- Volatile sync edge: `C:\Users\issda\Dropbox`
- Offload shell-folder layer: `C:\Users\issda\OneDrive\Offload`
- Cold archive drives: `E:\SCBE_DOSSIER_RUNS`, `F:\SCBE_Offload`
- Broken relocation scheme to verify before use: `D:\Relocated\...`

## 8. Immediate Use

When the next cleanup task arrives:

- start from this map
- classify the target path into a channel
- check for junctions or placeholders
- route duplicates toward `Drive\SCBE\local-workspace-sync`
- route bulky cold data toward `E:\` or `F:\`
- do not trust Dropbox edge state as canonical without comparison
