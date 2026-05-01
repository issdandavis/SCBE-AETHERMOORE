# WHY_HERE

These UI roots moved here during the 2026-04 GeoShell consolidation because
they were either empty stubs (only `__init__.py` and empty subdirs) or
superseded by sibling roots.

| Folder | Reason |
|---|---|
| `aetherbrowse/` | Empty stub (4 files, 0MB). The active surface is `src/aetherbrowser/`. The Electron desktop wrapper lives at `desktop/`. |
| `app/` | Generic Express server (5 files: `index.html`, `package.json`, `server.js`, `server.ts`, `tsconfig.json`). Superseded by `desktop/`, `kindle-app/`, and `apps/scbe-github-app/`. |
| `ui/` | 3-file stub (`index.html`, `components/LayerStack.js`, `styles/main.css`). Replaced by the GeoShell shell at `scbe-visual-system/`. |

To restore any of these, `git mv` the folder back to the repo root and add a
test or npm script that exercises it.
