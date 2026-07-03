# SCBE Worktree Garden

Generated: `2026-07-02T13:15:14+00:00`
Digest: `736f4e7443a6b1e1`

This is the local worktree garden map. Plots are workspaces or storage lanes. Agents attach by lease.

## Capacity

- Plots: `5/12`
- Active leases: `1`
- Missing plots: `0`
- Over plot capacity: `False`

## Zones

| Zone | Label | Plots | Max | Purpose |
| --- | --- | ---: | ---: | --- |
| `house` | House | 1 | 2 | Daily-driver repo surfaces that should stay close, visible, and actively tended. |
| `homestead` | Homestead | 2 | 6 | Adjacent local products, workspaces, and satellite repos. |
| `outsource_storage` | Outsource Storage | 2 | 4 | Storage lanes for offload, cloud sync, backups, and large generated material. |

## Plots

| Plot | Zone | Health | Agents | Branch | Dirty | Path |
| --- | --- | --- | ---: | --- | ---: | --- |
| `house-scbe` | `house` | `growing-dirty` | 1 | `lane/tool-trajectory-harvester` | 177 | `C:\Users\issda\SCBE-AETHERMOORE` |
| `homestead-aetherdesk` | `homestead` | `growing-dirty` | 0 | `main` | 47 | `C:\Users\issda\AetherDesk` |
| `homestead-local-apps` | `homestead` | `ready` | 0 | `` |  | `C:\Users\issda\LocalOnly\Apps` |
| `outsource-onedrive` | `outsource_storage` | `cloud-storage` | 0 | `` |  | `C:\Users\issda\OneDrive` |
| `outsource-localonly` | `outsource_storage` | `ready` | 0 | `` |  | `C:\Users\issda\LocalOnly` |

## Active Agent Leases

- `codex` on `house-scbe` as `work` until `2026-07-02T17:30:27+00:00`: build worktree garden tracker

## Agent Commands

```powershell
npm run worktree:garden -- status
npm run worktree:garden -- attach --agent codex --plot house-scbe --task "describe work"
npm run worktree:garden -- release --agent codex --plot house-scbe
```

## Safety Notes

- Attachment is metadata only; it does not run a shell command or start a background worker.
- Cloud-backed storage plots should be verify-first before move/delete work.
- A dirty git plot is treated as growing work, not trash.
