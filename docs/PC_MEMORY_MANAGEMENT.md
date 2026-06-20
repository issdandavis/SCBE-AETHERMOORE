# PC Memory Management

Updated: 2026-06-15

## Purpose

SCBE users need local machine health checks before large agent runs, repo scans, PQC builds, browser automation, backups, or cloud recovery. "Memory management" here means both RAM pressure and storage headroom. A system can fail from either one.

## Local Health Check

Preferred CLI:

```powershell
python scbe.py system health
python scbe.py system health --json
python scbe.py health --json
```

Detailed Windows report:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\system\pc_memory_health.ps1
```

The script writes JSON and Markdown reports to:

```text
artifacts/pc-memory/
```

It checks:

- total, used, and free RAM;
- pagefile allocation and usage;
- free disk space by drive;
- top memory-heavy processes;
- cloud-sync roots such as OneDrive;
- common cache hotspots;
- warnings and safe recommendations.

## Current Machine Findings

Latest local run:

- OneDrive is using about 2 GB RAM.
- `D:\` has low headroom, about 8 GB free.
- `C:\` has usable but not generous headroom.

For long builds or recovery scans, pause OneDrive sync first. Do not run deep recursive scans while RAM is already above 85% used.

## User-Facing Policy

Before expensive tasks, SCBE should run a preflight:

1. Warn if RAM use is above 85%.
2. Warn if any target drive has less than 25 GB free.
3. Warn if OneDrive/Dropbox/Drive is consuming more than 1 GB RAM.
4. Prefer shallow scans first.
5. Require explicit user confirmation before deleting, moving, or cache-clearing files.

## Safe Actions

Safe by default:

- report memory pressure;
- list top processes;
- identify cache hotspots;
- identify cloud recursion hazards;
- write Markdown/JSON reports.

Not automatic:

- killing processes;
- emptying Recycle Bin;
- deleting caches;
- moving user documents;
- changing pagefile settings;
- pausing cloud sync.

## Product Hook

Add this check before:

- `geoseal` PQC/liboqs builds;
- full GitHub inventory scans;
- backup/recovery runs;
- browser swarm runs;
- local model training;
- large RAG indexing jobs.

The product-facing command is:

```powershell
scbe system health
scbe system health --json
scbe health --json
```

The Python CLI gives the fast cross-command preflight. The PowerShell script remains the detailed Windows report generator.
