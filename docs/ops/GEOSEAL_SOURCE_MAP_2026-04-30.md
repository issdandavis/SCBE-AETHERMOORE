# GeoSeal Source Map

Date: 2026-04-30

Purpose: preserve the source trail for GeoSeal docs and training surfaces so future agent work can find the original Notion material, the repo implementation, and the current training lanes without guessing.

## Highest-Authority Original Sources Found

### Full Notion export

This is the best original source found. It is the full Notion export, not the short MCP summary.

```text
C:\Users\issda\OneDrive\SCBE-Archives\training_artifacts_2026-04\notion_export_unpacked\Export-d3f8086e-07e0-444f-9291-10b7fe375b22\🛡️ GeoSeal Geometric Access Control Kernel - RAG I 6f1c851a42e54f11bc14ba7ebfb9d559.md
```

Observed metadata:

- size: 17,774 bytes
- last write time: 2026-04-03 00:17 local
- title: `GeoSeal: Geometric Access Control Kernel - RAG Immune System`
- stated status: `Implementation Ready`
- stated version: `1.0.0`
- stated last updated date inside doc: February 10, 2026
- Notion page id in filename: `6f1c851a42e54f11bc14ba7ebfb9d559`

Core source content:

- GeoSeal turns vector RAG into an active immune system.
- It uses hyperbolic geometry plus phase-discipline dynamics.
- Pure hyperbolic distance plus random phase jitter is not enough.
- Load-bearing mechanisms are phase validity amplification, per-neighbor suspicion counters, spatial consensus quarantine, and second-stage force amplification once quarantined.

### Notion MCP ingest summary

This is useful for provenance and quick lookup, but it is only a short summary.

```text
exports\obsidian\notion_mcp_ingest_2026-02-24\GeoSeal_Geometric_Access_Control_Kernel.md
```

Observed metadata:

- source URL: `https://www.notion.so/6f1c851a42e54f11bc14ba7ebfb9d559`
- fetched via MCP: `2026-02-10T09:46:38.376Z`
- size in repo: 864 bytes

Use this file as a pointer, not as the full canonical text.

### Notion ingest bundle index

```text
exports\obsidian\notion_mcp_ingest_2026-02-24\INDEX.md
```

The index confirms the ingest pack was generated on 2026-02-24 from Notion MCP `notion_fetch` and includes:

- `GeoSeal_Geometric_Access_Control_Kernel.md`
- `SS1_Tokenizer_Protocol.md`
- `Six_Tongues_Protocol_Story.md`
- `HYDRA_Complete_Architecture.md`
- related support notes

## Adjacent Original Notion Export Files

These were found in both OneDrive and Dropbox archive copies:

```text
C:\Users\issda\OneDrive\SCBE-Archives\training_artifacts_2026-04\notion_export_unpacked\Export-d3f8086e-07e0-444f-9291-10b7fe375b22\🐍 Six Tongues + GeoSeal CLI - Python Implementatio 8cad7ff3551e49a98900f4c66f3acc98.md
C:\Users\issda\OneDrive\SCBE-Archives\training_artifacts_2026-04\notion_export_unpacked\Export-d3f8086e-07e0-444f-9291-10b7fe375b22\Chapter 5 GeoSeal - Geometric Access Control Kerne 5878bdbc8faf44dabf67f4bda8bd4728.md
C:\Users\issda\OneDrive\SCBE-Archives\training_artifacts_2026-04\notion_export_unpacked\Export-d3f8086e-07e0-444f-9291-10b7fe375b22\Chapter 5 GeoSeal - Geometric Access Control Kerne 857dc65dd6334378b3cfd33dfc351fed.md
C:\Users\issda\OneDrive\SCBE-Archives\training_artifacts_2026-04\notion_export_unpacked\Export-d3f8086e-07e0-444f-9291-10b7fe375b22\GeoSeal Geometric Trust Manifold e98b6184d1024ce99d2134463ff3de1c.md
```

Two OneDrive files returned `The cloud file provider exited unexpectedly` during read attempts. Treat those as found but not locally hydrated. The Dropbox archive has parallel copies under:

```text
C:\Users\issda\Dropbox\SCBE-Archives\training_artifacts_2026-04\notion_export_unpacked\Export-d3f8086e-07e0-444f-9291-10b7fe375b22\
```

## Repository Runtime Sources

Runtime and tests are higher authority than prose when they disagree.

Primary implementation:

```text
src\geoseal.py
src\geoseal.ts
src\geoseal_v2.py
src\geoseal-v2.ts
src\crypto\geo_seal.py
src\geoseal_cli.py
```

Primary tests:

```text
tests\test_geoseal.py
tests\test_geoseal_v2.py
tests\test_geoseal_coding_training_system.py
tests\test_geoseal_agent_routing.py
tests\test_geoseal_cli_tokenizer_atomic.py
```

Runtime summary:

- `src\geoseal.py` is the compact Python reference implementation for the original geometric access control kernel.
- `src\geoseal_v2.py` extends the kernel into a mixed-curvature product manifold: hyperbolic hierarchy/trust, spherical tongue phase, and Euclidean uncertainty.
- `src\crypto\geo_seal.py` is the broader crypto/harmonic implementation with context vectors, hyperbolic containment, phase-distance scoring, and temporal phase scoring.
- `src\geoseal_cli.py` is the current user-facing command surface.

## Current Live Repo GeoSeal Doc

```text
docs\specs\GEOSEAL_MARS_MISSION_COMPASS_v1.md
```

This is not the original GeoSeal kernel doc. It is a newer Mars mission substrate scaffold that applies GeoSeal to mission packets, terrain mapping, coding fixes, fault recovery, navigation home, and handoff.

## Archived Repo Docs Found Outside Active Docs

These are not currently present in the active repo `docs\` tree, but were found in OneDrive/Dropbox offload snapshots:

```text
...\notes_snapshot\notes\System Library\Repository Mirror\docs\GEOSEAL_ACCESS_CONTROL.md
...\notes_snapshot\notes\System Library\Repository Mirror\docs\08-reference\archive\GEOSEAL_CONCEPT.md
...\notes_snapshot\notes\System Library\Repository Mirror\docs\guides\GEOSEAL_AND_TONGUES.md
```

OneDrive examples:

```text
C:\Users\issda\OneDrive\Backups\SCBE_Verified_Offload\SCBE-AETHERMOORE_2026-04-22_separation\notes_snapshot\notes\System Library\Repository Mirror\docs\GEOSEAL_ACCESS_CONTROL.md
C:\Users\issda\OneDrive\Backups\SCBE_Verified_Offload\SCBE-AETHERMOORE_2026-04-22_separation\notes_snapshot\notes\System Library\Repository Mirror\docs\08-reference\archive\GEOSEAL_CONCEPT.md
C:\Users\issda\OneDrive\Backups\SCBE_Verified_Offload\SCBE-AETHERMOORE_2026-04-22_separation\notes_snapshot\notes\System Library\Repository Mirror\docs\guides\GEOSEAL_AND_TONGUES.md
```

## Training State Checked

Latest local cloud sync:

```text
training\runs\local_cloud_sync\20260501T002643Z\run_summary.json
training\runs\local_cloud_sync\20260501T002643Z\manifest.json
```

Observed state:

- status: `ok`
- indexed files: 51,673
- changed files: 2
- shipped to Dropbox: ok
- shipped to Google Drive: ok
- delta changed only the MC/DC doc and command planner test from the previous turn

Current Colab training worker:

```text
artifacts\colab_workers\colab-training-live\worker-colab-00-long2\
```

Observed active process:

- PowerShell PID: 27196
- Python PID: 3908
- started: 2026-04-30 16:46 local
- no completion JSON had landed when checked

GeoSeal training config:

```text
config\model_training\geoseal_coding_training_manifest.json
```

Current manifest includes staged profiles from smoke through full coding system and CA/GeoSeal repair passes. Promotion is explicitly gated by pass rate and required smoke prompts, not loss alone.

Latest relevant SFT files:

```text
training-data\sft\coding_system_full_v1_train.sft.jsonl
training-data\sft\coding_system_full_v1_holdout.sft.jsonl
training-data\sft\ca_geoseal_combined_repair_v3_train.sft.jsonl
training-data\sft\ca_geoseal_smoke_repair_v1_train.sft.jsonl
training-data\sft\geoseal_command_recall_v1.sft.jsonl
training-data\sft\geoseal_command_harmony_v1.sft.jsonl
```

## Recommended Authority Order

Use this order for future GeoSeal work:

1. Full Notion export kernel doc from `SCBE-Archives\training_artifacts_2026-04`.
2. Runtime implementations and tests in `src\` and `tests\`.
3. Notion MCP ingest summary as provenance pointer.
4. Current applied docs such as `GEOSEAL_MARS_MISSION_COMPASS_v1.md`.
5. Training SFT files and model manifests as downstream derived material.

## Immediate Fix Recommendation

Do not train future GeoSeal models from only the 864-byte MCP summary. Use the full 17,774-byte Notion export plus runtime/test examples as the source bundle, then generate derived SFT from that bundle with provenance fields:

```json
{
  "source_family": "geoseal",
  "source_authority": "notion_export_full",
  "source_notion_id": "6f1c851a42e54f11bc14ba7ebfb9d559",
  "runtime_anchor": "src/geoseal.py",
  "test_anchor": "tests/test_geoseal.py"
}
```
