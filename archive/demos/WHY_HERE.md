# WHY_HERE

These demo scripts moved here from the repo root ``demos/`` folder during the
2026-04 GeoShell consolidation. Their content is preserved for history.

**Industry-grade replacement:** every demo that needs to be runnable lives
as a tile inside the GeoShell App Store
(`scbe-visual-system/apps-registry.json`). To resurrect any of these as a
nested service, point a tile's ``service.envUrl`` at a uvicorn process
serving the equivalent FastAPI surface and remove the file from this archive.
