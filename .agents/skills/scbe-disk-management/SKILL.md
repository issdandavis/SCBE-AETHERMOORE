---
name: scbe-disk-management
description: "Audit disk usage, identify space hogs, and safely clean up caches/temp files across the SCBE-AETHERMOORE repo and user profile. Use when asked about disk space, storage cleanup, finding large files, or freeing space."
---

# SCBE Disk Management

Wraps the three existing PowerShell scripts in `scripts/system/` for disk auditing and safe cleanup.

## Scripts

| Script | Purpose | Output |
|--------|---------|--------|
| `system_disk_audit.ps1` | Audit SCBE repo directory sizes + C: drive free/used | `artifacts/system-audit/disk_audit.json` + `.md` |
| `system_profile_disk_audit.ps1` | Audit entire user profile (`C:\Users\issda`) top-level dirs | `artifacts/system-audit/profile_disk_audit.json` + `.md` |
| `system_cleanup_safe.ps1` | Remove safe-to-delete caches (pytest, hypothesis, pycache) | Console output |

## Operations

### 1. Repo Disk Audit

Scans targeted SCBE directories (src, docs, tests, node_modules, dist, artifacts, training, training-data, .hypothesis, .pytest_cache) plus all top-level children ranked by size.

```bash
powershell -ExecutionPolicy Bypass -File scripts/system/system_disk_audit.ps1
```

Parameters:
- `-RepoPath` — repo root (default: `C:/Users/issda/SCBE-AETHERMOORE`)
- `-TopN` — number of largest children to show (default: 25)
- `-OutDir` — output subdirectory (default: `artifacts/system-audit`)

Reports C: drive used/free GB, targeted path sizes, and largest top-level folders. Writes both JSON and Markdown.

### 2. Profile Disk Audit

Scans all top-level directories under the user profile to find the biggest space consumers system-wide.

```bash
powershell -ExecutionPolicy Bypass -File scripts/system/system_profile_disk_audit.ps1
```

Parameters:
- `-Root` — scan root (default: `C:/Users/issda`)
- `-TopN` — number of results (default: 30)
- `-OutDir` — output subdirectory (default: `artifacts/system-audit`)

### 3. Safe Cleanup (dry-run first)

Removes safe-to-delete cache directories. Always run dry-run first.

```bash
# Dry-run (shows what WOULD be deleted, deletes nothing)
powershell -ExecutionPolicy Bypass -File scripts/system/system_cleanup_safe.ps1

# Actually delete
powershell -ExecutionPolicy Bypass -File scripts/system/system_cleanup_safe.ps1 -Apply
```

**Cleanup targets** (only within the repo):
- `.pytest_cache`
- `.hypothesis/examples`
- `artifacts/pytest_tmp`
- `__pycache__` (root, src, tests)

Parameters:
- `-RepoPath` — repo root (default: `C:/Users/issda/SCBE-AETHERMOORE`)
- `-Apply` — switch to actually delete (omit for dry-run)

## Recommended Workflow

1. **Audit first**: Run repo audit to see current sizes
2. **Profile audit**: If C: drive is low, run profile audit to find what's eating space outside the repo
3. **Dry-run cleanup**: Run cleanup without `-Apply` to review targets
4. **Apply cleanup**: If safe, re-run with `-Apply`
5. **Re-audit**: Confirm space was freed

## Reading Reports

After auditing, reports are at:
- `artifacts/system-audit/disk_audit.json` — repo audit (machine-readable)
- `artifacts/system-audit/disk_audit.md` — repo audit (human-readable)
- `artifacts/system-audit/profile_disk_audit.json` — profile audit (machine-readable)
- `artifacts/system-audit/profile_disk_audit.md` — profile audit (human-readable)

Read the `.md` files for a quick summary, or parse the `.json` for automation.

## Safety Rules

- **Never** delete `node_modules` without confirmation — requires `npm install` to restore
- **Never** delete `training-data/` or `training/` — irreplaceable SFT pairs
- **Never** delete `.git/` — repository history
- **Never** delete `dist/` without rebuilding — breaks npm package
- The cleanup script only targets expendable caches that regenerate automatically
- Always dry-run before applying
