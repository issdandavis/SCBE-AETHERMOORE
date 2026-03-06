# SCBE Cymatic Voxel MCP App

This MCP App is a cymatic voxel variant of the basic MCP App pattern:

- Tool: `cymatic-voxel-layout`
- UI resource: `ui://cymatic-voxel/mcp-app.html`
- Graph rules:
  - spectral channels isolate flows,
  - intersections are allowed only at designated merge nodes,
  - hyperbolic proximity checks flag near-collisions.
- 6D explicit voxel dimensions:
  - `x,y,z` + `spectral` + `authority` + `intent`
- 1 implied dimension:
  - `timestamp` (temporal slicing via `atUnixMs` + `windowMs`)

It was shaped from your Notion notes around:

- Cymatic voxel / Chladni storage,
- Poincare metric invariance,
- quasi-periodic and phason shift concepts.

## Run

```bash
npm install
npm run build
npm run serve
```

Server endpoint:

- `http://localhost:3001/mcp`

## MCP host test

Use any MCP Apps-capable host and connect to the endpoint above.  
Call `cymatic-voxel-layout` with optional args:

```json
{
  "flowCount": 10,
  "mode": "quasi",
  "atUnixMs": 1770000000000,
  "windowMs": 120000
}
```

`mode` values:

- `default`
- `quasi`
- `dense`

## Notes

- UI is bundled into a single file via `vite-plugin-singlefile`.
- Graph and voxel logic lives in `src/spectralGraph.ts`.
