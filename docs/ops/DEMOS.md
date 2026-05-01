# Demos \u2014 location guide

Demos in this repo now live in three places, depending on shape:

## 1. Interactive demos \u2014 GeoShell App Store

Interactive demos (the ones a user clicks on) live as **tiles in the
GeoShell App Store**, defined by:

- `scbe-visual-system/apps-registry.json` (registry)
- `scbe-visual-system/components/apps/AppStoreApp.tsx` (UI)
- `scbe-visual-system/components/apps/ServiceApp.tsx` (HTTP service tiles, e.g. Spiral Word, GeoSeal)

Add a tile by editing the registry JSON; no React change needed for
service-style tiles. Set the relevant env var (e.g. `SPIRAL_WORD_URL`,
`GEOSEAL_SERVICE_URL`) to override the default localhost URL.

## 2. Long-form catalog

The narrative demo catalog (attack scenarios, case studies, marketing copy)
lives at `docs/DEMOS.md`.

## 3. Archived throwaway scripts

The old throwaway pitch scripts that lived under the repo-root `demos/`
folder were moved to `archive/demos/` during the 2026-04 reorg
(see `docs/ops/REPO_REORG_2026-04.md` and `archive/demos/WHY_HERE.md`).

If you want to resurrect one as a real interactive demo, wrap it in a
small FastAPI app, point a registry tile's `service.envUrl` at the
running uvicorn process, and remove the file from the archive.
