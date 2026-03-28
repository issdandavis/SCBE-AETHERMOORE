# Free Open Mapping Stack Research

## Decision
For SCBE demos, the best free and most usable stack is:

- Renderer: `MapLibre GL JS`
- Free hosted base map for fast start: `OpenFreeMap`
- Custom static map data and overlays: `PMTiles` via `Protomaps`
- Search control: `@maplibre/maplibre-gl-geocoder`
- Routing when needed: `OSRM`
- Dynamic serving or PostGIS-backed growth: `Martin`

This is the fastest path to demos that look professional without depending on Mapbox.

## Why this stack wins

### 1. MapLibre is the correct frontend base
MapLibre GL JS is an open-source TypeScript/WebGL map renderer with MapLibre Native for Android and iOS.
It supports:
- vector tiles
- globe/terrain
- fog/sky styling
- custom WebGL layers
- custom 3D layers and external engines such as Three.js

That makes it suitable for SCBE surfaces like:
- GeoSeal overlays
- Hydra movement tracks
- quarantine halos
- route collapse visuals
- premium terrain-backed demos instead of flat debug panels

### 2. OpenFreeMap is the best zero-friction hosted start
OpenFreeMap’s public instance is currently:
- free
- no registration
- no API keys
- no cookies
- commercial use allowed
- offers ready MapLibre style URLs
- includes a `3D` style option

This makes it the simplest replacement for “just get a good-looking map on screen.”

Tradeoff:
- public instance is provided as-is
- no SLA guarantees
- if the project becomes important, self-hosting or migration is still the right long-term path

### 3. Protomaps + PMTiles is the best static/custom data lane
Protomaps gives you:
- an open source mapping system
- `PMTiles`, a single-file tile archive format
- low-maintenance hosting over normal HTTP range requests
- direct browser use with MapLibre

This is ideal for SCBE-specific overlays and map packs:
- restricted corridors
- threat regions
- mission areas
- terrain masks
- world-state overlays
- demo bundles that can be shipped as files instead of databases

### 4. Martin is the growth path, not the starting requirement
Martin can serve:
- PostGIS tables/functions
- PMTiles
- MBTiles
- mixed sources

Use Martin only when one of these becomes true:
- data needs real-time updates
- multiple map sources must be merged dynamically
- PostGIS is already part of the system
- public traffic or complexity justifies a server

### 5. Search is where many “free map” stacks get weak
Do not treat search and map tiles as the same problem.

Best choices:
- small/modest early use: Nominatim through a proxy with strict caching
- real autocomplete or larger usage: Photon or Pelias

Important constraint:
- the public OSM Nominatim policy forbids client-side autocomplete and sets a hard usage cap
- so Nominatim is acceptable for light user-triggered search, not for a polished high-traffic public autocomplete product

### 6. Routing is easiest with OSRM
OSRM is the easiest open routing lane to stand up for:
- fastest route calculation
- route geometry
- step output
- matching/trip/table services

If routing becomes more advanced later, Valhalla is another option, but OSRM is the simpler first move.

## Recommended SCBE build order

### Phase 1: demo quality now
Use:
- `MapLibre GL JS`
- `OpenFreeMap` style URL
- local `GeoJSON` overlays

This gets to a polished demo quickly.

Build these first:
- terrain-backed map view
- risk/quarantine zone layers
- animated agent track layer
- route tension or seal-integrity glow
- operator status panel beside the map

### Phase 2: own the custom layers
Use:
- `Tippecanoe` to build vector tiles for your own data
- `pmtiles` CLI to package them
- host `.pmtiles` over normal HTTP

This gives you:
- reusable SCBE map packs
- offline or low-infra deployment
- better performance than raw giant GeoJSON files

### Phase 3: add search and routing
Use:
- `@maplibre/maplibre-gl-geocoder`
- proxy-backed `Nominatim` for very light use or internal tools
- self-hosted `Photon` or `Pelias` for real autocomplete/search
- `OSRM` for routing

### Phase 4: move to dynamic serving only if needed
Use:
- `Martin`
- `PostGIS`
- PMTiles + database composite sources

Only do this when the product really needs live data and server-side composition.

## Practical automation plan

### A. Free demo lane
1. Load a MapLibre map with an OpenFreeMap style.
2. Inject SCBE overlays from local GeoJSON.
3. Use custom layers for premium effects:
   - hazard bloom
   - signal fog
   - corridor glow
   - agent pulse
4. Export snapshots or recordings for the site/demo pages.

### B. Static data lane
1. Convert SCBE geospatial data to GeoJSON.
2. Build vector tiles with `tippecanoe`.
3. Convert or package to PMTiles.
4. Serve the `.pmtiles` file from static hosting.
5. Load it in MapLibre.

### C. Search lane
1. Add `@maplibre/maplibre-gl-geocoder`.
2. Start with a proxy-backed endpoint.
3. Cache aggressively.
4. Replace with Photon or Pelias when autocomplete and volume matter.

### D. Routing lane
1. Stand up `OSRM`.
2. Query routes from the demo or app.
3. Render route geometry as SCBE paths.
4. Add policy overlays on top of the route, not just plain directions.

## What not to do
- Do not use the public OpenStreetMap tile servers as a production map backend.
- Do not build a whole “Mapbox replacement company” first.
- Do not start with Pelias if you only need a nice-looking demo map.
- Do not depend on public Nominatim for client-side autocomplete.

## Final recommendation

If the goal is:
- free
- polished
- usable now
- code you control

then the default stack should be:

- `MapLibre GL JS`
- `OpenFreeMap` for immediate basemaps
- `PMTiles`/`Protomaps` for SCBE-owned overlays and map packs
- `OSRM` when routing matters
- `Martin` only when the system grows into dynamic server-side map composition

That stack is the best balance of:
- visual quality
- zero-cost starting point
- open-source control
- future scale path

## Primary sources
- MapLibre GL JS docs: https://maplibre.org/maplibre-gl-js/docs
- MapLibre Native: https://maplibre.org/projects/native/
- MapLibre examples: https://maplibre.org/maplibre-gl-js/docs/examples/
- MapLibre custom layers: https://maplibre.org/maplibre-gl-js/docs/API/interfaces/CustomLayerInterface/
- OpenFreeMap home: https://openfreemap.org/
- OpenFreeMap quick start: https://openfreemap.org/quick_start/
- OpenFreeMap terms: https://openfreemap.org/tos/
- Protomaps docs: https://docs.protomaps.com/
- Protomaps getting started: https://docs.protomaps.com/guide/getting-started
- PMTiles concepts: https://docs.protomaps.com/pmtiles/
- PMTiles creation: https://docs.protomaps.com/pmtiles/create
- PMTiles CLI: https://docs.protomaps.com/pmtiles/cli
- Martin docs: https://maplibre.org/martin/
- Martin tile sources: https://maplibre.org/martin/sources-tiles.html
- Nominatim usage policy: https://operations.osmfoundation.org/policies/nominatim/
- Nominatim site/docs: https://nominatim.org/
- Pelias: https://pelias.io/
- MapLibre geocoder control: https://maplibre.org/maplibre-gl-geocoder/
- OSRM API docs: https://project-osrm.org/docs/v5.24.0/api/
