# Project Structure (canonical, 2026-04+)

This file replaces the legacy ``docs/STRUCTURE.md`` shim that pointed at the
old root location. The 2026-04 GeoShell reorg consolidated the repo into a
small set of stable surfaces.

## Top-level surfaces

```
SCBE-AETHERMOORE/
\u251c\u2500 src/                  # Canonical TypeScript + Python product code
\u251c\u2500 api/                  # FastAPI services (geoseal_service, postgres_lite)
\u251c\u2500 tests/                # pytest + vitest contract tests
\u251c\u2500 scripts/              # Operational + reorg + benchmark scripts
\u2502  \u2514\u2500 repo_reorg/        # 2026-04 reorg playbook (plan + apply scripts)
\u251c\u2500 docs/
\u2502  \u251c\u2500 specs/             # Canonical specs (SPEC, ARCHITECTURE, LAYER_INDEX, ...)
\u2502  \u251c\u2500 ops/               # Operational/runbook docs (REPO_REORG_2026-04, RUNBOOK, ...)
\u2502  \u2514\u2500 business/          # Patent / pitch / commercial docs
\u251c\u2500 archive/              # Reversible archive (history preserved via git mv)
\u2502  \u251c\u2500 demos/             # Throwaway demo scripts (use GeoShell tiles instead)
\u2502  \u251c\u2500 ui-graveyard/      # Archived empty UI stubs (aetherbrowse, app, ui)
\u2502  \u251c\u2500 public-pages/      # Old root index.html / product-landing.html
\u2502  \u251c\u2500 data-snapshots/    # Stale JSON dumps
\u2502  \u2514\u2500 manuscripts/       # Long-form text artifacts
\u251c\u2500 runnables/legacy/     # Loose CLIs/scripts no longer wired into CI
\u251c\u2500 artifacts/            # Generated runtime artifacts (gitignored)
\u2514\u2500 ...                   # All other folders below.
```

## Active UI roots (the only ones a human or agent should touch)

| Folder | Role | Status |
|---|---|---|
| `scbe-visual-system/` | **GeoShell** \u2014 React/Vite shell. Tile registry at `apps-registry.json`. App Store at `components/apps/AppStoreApp.tsx`. | **Canonical UI shell.** |
| `kindle-app/` | Capacitor (Android Fire/Kindle) wrapper. **GeoShell deployment target.** Build with `npm run geoshell:build-into-kindle`. | Active. |
| `desktop/` | Electron AetherBrowser standalone (separate desktop product). | Active. |
| `aether-browser/` | Python security layer paired with `src/aetherbrowser/`. | Active. |
| `ai-ide/` | Vite/React coding-assistant IDE; surfaced as a GeoShell service tile (`AI_IDE_URL`, default `:5173`). | Active. |
| `apps/outreach/`, `apps/scbe-github-app/` | Real subprojects with their own README. | Active. |
| `dashboard/` | Two HTML dashboards (`scbe_monitor.html`, `physics-simulator.html`); served as GeoShell service tiles (`SCBE_MONITOR_URL`, `PHYSICS_SIM_URL`). | Active. |
| `prototype/` | `toy_phdm` research surface (Streamlit + visualize). | Active research. |
| `conference-app/` | Real Vite + Vercel app for conferences. | Active. |
| `spiral-word-app/` | FastAPI + WebSocket collaborative editor; surfaced as GeoShell service tile (`SPIRAL_WORD_URL`, default `:8000`). | Active. |

## Archived during 2026-04 reorg

| Folder | Why |
|---|---|
| `archive/ui-graveyard/aetherbrowse/` | Empty stub (4 files, 0MB). |
| `archive/ui-graveyard/app/` | Generic Express server superseded by `desktop/`/`apps/`/`kindle-app/`. |
| `archive/ui-graveyard/ui/` | 3-file stub replaced by `scbe-visual-system/`. |
| `archive/demos/*.py` | Throwaway demos; replaced by GeoShell App Store tiles. |
| `archive/public-pages/{index,product-landing}.html` | Old root marketing pages. |
| `runnables/legacy/*` | Loose CLIs/scripts not wired into CI/tests. |

## Active root entry points

These five Python files **stay at the repo root** because CI workflows, npm
scripts, tests, and `scripts/windows/scbe.bat` reference them directly:

- `scbe.py`, `scbe-cli.py`, `scbe-agent.py`
- `six-tongues-cli.py`
- `enhanced_scbe_cli.py`

## How agents should navigate this repo

1. Start with `README_INDEX.md` (root) for the doc map.
2. Read `docs/specs/SPEC.md` and `docs/specs/LAYER_INDEX.md` for the math.
3. Read this file for the surface map.
4. Read `docs/ops/REPO_REORG_2026-04.md` to understand the current reshape.
5. To add a tile/app to GeoShell: edit `scbe-visual-system/apps-registry.json`
   and run `npm run verify:geoseal-agent && npm run verify:geoshell-registry`.
6. To deploy GeoShell to the Kindle/Fire app: run
   `npm run geoshell:build-into-kindle`.
