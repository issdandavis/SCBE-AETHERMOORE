---
name: cloud-storage-local-storage-management
description: "Audit, sort, route, and back up large Windows workspaces across local disks and cloud-sync folders without recursive mirror failures. Use when the user wants the filesystem cleaned up, cloud storage organized, backup targets chosen by free space and route quality, or hardware/storage bottlenecks identified before moving data."
---

# Cloud Storage and Local Storage Management

Use this skill when the user says some version of:

- "push everything to cloud storage"
- "my filesystem is messed up"
- "sort my local files"
- "find the best backup route"
- "clean up storage"
- "optimize hardware/storage"

This is a storage-management skill, not a fake security ritual.

- Do **not** hardcode birthdays, names, or simple codes as "admin security".
- Real admin actions should happen through the normal command-escalation flow.
- Default to scans, plans, and dry-run backup routes before destructive cleanup.

## What this skill does

1. Scan the machine layout:
   - local drives
   - cloud roots
   - biggest folders
   - biggest files
   - known cache/problem zones
2. Rank backup routes by:
   - free space
   - whether the cloud root already exists
   - whether the route will recurse into itself
3. Emit a sort plan instead of guessing moves.
4. Run a profile backup with sane excludes when the route is safe.

## Use the bundled scripts in this order

### 1. Scan

```powershell
pwsh -File skills/cloud-storage-local-storage-management/scripts/storage_route_scan.ps1
```

Outputs JSON + Markdown into `artifacts/storage-management/`.

### 2. Build a sort plan

```powershell
pwsh -File skills/cloud-storage-local-storage-management/scripts/storage_sort_plan.ps1
```

This converts the scan into a deterministic cleanup and backup plan.

### 3. Run a backup lane

Dry run first:

```powershell
pwsh -File skills/cloud-storage-local-storage-management/scripts/backup_profile.ps1
```

Apply only after the route is acceptable:

```powershell
pwsh -File skills/cloud-storage-local-storage-management/scripts/backup_profile.ps1 -Apply
```

## Operating rules

- Prefer the smallest safe change that improves structure.
- Never back up a profile into a cloud root without excluding that root itself.
- Treat cloud folders inside the source tree as recursion hazards.
- Treat app caches, temp stores, package caches, and mail-bridge stores as separate from user documents.
- If the target cloud drive is nearly full, stop and reroute instead of forcing the copy.

## Hardware and route logic

The route decision is based on:

- target exists
- target drive free GB
- target path stability
- whether the route is likely to self-nest
- whether the target is a content folder or a sync-engine cache

Good routes:

- `Dropbox\machine-backup\...`
- `Drive\machine-backup\...`
- `OneDrive\machine-backup\...`
- another local disk outside the source tree

Bad routes:

- copying into a folder that is already inside the source without excluding it
- backing up large app caches into a nearly full sync target
- using Creative Cloud or mail stores as generic bulk backup targets

## Admin behavior

If a scan or backup needs higher privileges:

- use the normal escalated command flow
- explain why
- keep the command narrow

Do not simulate "security" with a shared secret embedded in the skill.

## Resources

### scripts/

- `storage_route_scan.ps1`: inspect the current storage layout and emit a ranked route report
- `storage_sort_plan.ps1`: turn the latest scan into a cleanup/backup plan
- `backup_profile.ps1`: dry-run or execute a safe profile backup with recursion and capacity guards
