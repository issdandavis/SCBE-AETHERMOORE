# Research Roadmap Index

Generated: 2026-05-02

Purpose: treat research outputs as roadmaps. The root JSON research captures are not final source files; they are lane scouts that point to build tasks, validation gates, and discard rules.

## Rule

Research becomes useful when it is converted into one of these:

1. A repo issue or roadmap lane.
2. A testable implementation slice.
3. A benchmark or evaluation gate.
4. A short source-backed note under `docs/research/`.
5. A training-data improvement with a manifest and holdout.

Loose research JSON files should stay temporary unless a downstream lane consumes them.

## Promotion Ladder

Use this ladder for every research capture:

| Stage | Output | Promotion gate |
|---|---|---|
| 0. Research capture | Raw source bundle, source URLs, excerpts, and a short hypothesis. | Source is attributable and relevant to an active SCBE lane. |
| 1. Roadmap digestion | Compact lane entry in this file or a focused `docs/research/` note. | The capture has a build target, reject list, and test idea. |
| 2. Test design | Deterministic tests, eval contract, benchmark spec, or fixture plan. | The expected behavior can fail before implementation. |
| 3. Implementation slice | Small code path wired into an existing module or CLI surface. | Targeted tests pass and no unrelated behavior changes. |
| 4. Integration | Connected to GeoSeal, training profiles, harness providers, docs, or release surfaces. | Cross-module tests pass and metadata is routeable. |
| 5. Full deploy testing | Local smoke, harness readiness, Kaggle/Hugging Face eval, npm/PyPI dry run, or service health check. | Results are captured under artifacts with a clear pass/fail report. |
| 6. Release or promotion | Package publish, adapter promotion, docs publication, or manifest freeze. | Rollback path exists and generated churn is quarantined. |

Short form:

```text
research -> roadmap -> tests -> implementation -> integration -> deploy testing -> release/promotion
```

Research that cannot reach Stage 2 should stay as notes, not implementation pressure.

## Active Roadmap Seeds

| Research capture | Roadmap lane | Useful signal | Do not import |
|---|---|---|---|
| `hf-bijective-coding-research.json` | Hugging Face training hardening | Hugging Face Transformers, TRL SFT/DPO, PEFT/QLoRA, adapter push workflow, tool-calling dataset shape. | Generic beginner tutorial structure unless it maps to the existing dispatcher/profile system. |
| `bijective-coding-focused.json` | Bijective reasoning and coding | Reversible programming, bijective numeration, reversible logic, inverse interpretation, deterministic round-trip constraints. | Claims that bijective coding alone makes code semantically correct. It only proves invertibility or uniqueness unless paired with tests. |
| `geoseal-cli-tech-stack-research.json` | GeoSeal geospatial/tool-stack extension | GDAL, PROJ, PostGIS azimuth/project primitives, coordinate transforms, CLI-friendly geospatial operations. | Heavy GIS server dependencies until a minimal CLI adapter proves value. |
| `geoseal-h3-s2-research.json` | GeoSeal spatial indexing and route grids | H3 hierarchical cell indexes, S2 spherical geometry, resolution hierarchy, approximate coverings. | Treating H3/S2 as interchangeable. H3 is hex hierarchy; S2 is sphere cell geometry. |
| `geoseal-cli-survival-toolkit-research.json` | Terminal-game and analog-action training | Map, compass, triangulation, dead reckoning, back bearings, skill drills. Good source for analog action primitives. | Survival-course marketing as doctrine. Extract task structure, not brand language. |
| `land-nav-doctrine-research.json` | Land-navigation doctrine adapter | Map reading, land navigation, terrain association, azimuth/back azimuth, route planning. Good fit for agent route verification metaphors and tests. | Unsafe tactical framing. Keep it as navigation, geometry, route-checking, and training-drill structure. |

## Conversion Plan

### 1. Hugging Face Training Hardening

Build target:

- Make the Stage 5 and Stage 6 training paths easier to repeat and compare.
- Add a results sheet that links job id, adapter repo, gate pass rate, eval rows, and digest residue.
- Keep `scripts/system/dispatch_coding_agent_hf_job.py` as the main dispatch surface.

Gate:

- Existing profile parses.
- Generated training script compiles.
- Gate report contains `gate_overall_pass`, `gate_pass_rate`, `n_pass`, `n_total`.
- Digest script emits residue chains and next-lane decision.

### 2. Bijective Coding

Build target:

- Treat bijective coding as a first-class contract: source code to packet to source code must round-trip exactly.
- Extend from code transport into semantic checks only when tests exist.
- Keep code-language lanes as first-class routing labels.

Gate:

- Exact byte round-trip.
- Source SHA-256 and token SHA-256 both present.
- Invalid packet fails closed.
- Generated code still passes language-specific tests.

### 3. GeoSeal Geospatial Tool Stack

Build target:

- Add a narrow `geoseal nav` or `geoseal geo` lane before any broad GIS dependency.
- Implement local math first: bearing, back bearing, project point, route segment, route error.
- Only then evaluate GDAL/PROJ/PostGIS adapters.

Gate:

- Pure-Python deterministic tests for bearing/back-bearing.
- No network or database required for the base lane.
- Optional adapters skip cleanly when dependency is unavailable.

### 4. H3 / S2 Spatial Indexing

Build target:

- Use H3/S2 as route-grid backends for agent movement, lane switching, and terminal-game training maps.
- Keep backend choice explicit in packet metadata.

Gate:

- Same input coordinate produces deterministic cell id.
- Parent/child resolution tests pass.
- Route compression preserves start, end, and checkpoint cells.

### 5. Terminal-Game Analog Actions

Build target:

- Convert map/compass drills into analog action primitives already exposed by GeoSeal:
  - `observe-room`
  - `move-lane`
  - `inspect-object`
  - `solve-checkpoint`
  - `verify-evidence`
  - `reset-run`
- Use simple navigation tasks as training games for agentic CLI behavior.

Gate:

- Agent must signal lane change before switching route.
- Agent must verify evidence before marking checkpoint solved.
- Reset must produce a clean replayable state.

## Cleanup Rule

After a research capture is converted:

1. Keep the compact roadmap entry here.
2. Move or regenerate raw JSON under `artifacts/parallelism_system/` or a dated `artifacts/research/` folder.
3. Commit only the roadmap, implementation, tests, and small manifests needed for reproducibility.
