# public/

Static site root: HTML pages (the AetherLand pages and product pages), images, PWA icons, and JSON data.

- `data/<topic>/` — per-topic datasets (`dataset.json`, `grid_nodes.json`, `index.json`). Only `ai/` (240 items) and `science/` (160 items) are populated; `culture/`, `data/`, `governance/`, and `security/` are empty arrays.
- `data/open_source_api_library.json`, `data/gamma_landing_sites.json` — connector library and landing-site registry.
- `.well-known/assetlinks.json` — Android Digital Asset Links authorising the package `com.issdandavis.aethercode`. The Trusted Web Activity manifest in `apps/mobile/twa/` declares a different package (`io.aethermoor.bus`) and a placeholder host, so this file does not cover that app.
- `product-manual/` — the service fast-start packet.

---

Every file in this directory is listed with a one-line description in [`docs/file-index/public.md`](../docs/file-index/public.md).
