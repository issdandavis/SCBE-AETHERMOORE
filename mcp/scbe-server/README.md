# SCBE MCP Server

Local MCP server exposing SCBE tokenizer, Map Room, and Phase 1 state/egg governance tools.

## Tools

- `scbe_tokenize`
- `scbe_detokenize`
- `scbe_detect_tongue`
- `scbe_fetch_url`
- `scbe_decide_offline`
- `scbe_state_emit_21d`
- `scbe_sacred_egg_create`
- `scbe_sacred_egg_hatch`
- `scbe_map_room_read_latest`
- `scbe_map_room_write_latest`
- `scbe_tokenizer_health`

## Runtime

- Entry: `mcp/scbe-server/server.mjs`
- Depends on:
  - `@modelcontextprotocol/sdk`
  - `dist/src/tokenizer/ss1.js`
  - `dist/src/ai_brain/index.js`

## Notes

- This server is local-first and does not require network for tokenizer operations.
- Map Room path is fixed to `docs/map-room/session_handoff_latest.md`.
- `scbe_fetch_url` uses Node `fetch` first and falls back to `curl` on HTTPS issuer-cert trust failures (`UNABLE_TO_GET_ISSUER_CERT_LOCALLY`).
