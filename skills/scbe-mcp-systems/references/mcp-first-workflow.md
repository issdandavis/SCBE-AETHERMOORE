# SCBE MCP-First Workflow

Use this note when another agent needs a compact map from common SCBE requests to the local MCP tools.

## Starting pattern

1. Confirm health with `scbe_tokenizer_health` if the server might be down.
2. Pull `scbe_system_manifest` for repo identity, tool inventory, command areas, and canonical docs.
3. Narrow to a command lane with `scbe_command_catalog` or a doc lane with `scbe_reference_lookup`.
4. Move to shell, code inspection, or another SCBE skill only after the MCP answer is insufficient.

## Command areas

- `build` for compile and type-check lanes
- `test` for TypeScript and Python validation lanes
- `mcp` for repo MCP terminal helpers
- `docker` for local Docker health and stack workflows
- `browser` for AetherBrowser service operations
- `system` for connector health, bootstrap, and broader SCBE system control
- `skills` for repo-local skill bridge inspection
- `publish` for npm publishing preparation and checks

## Canonical topic prompts

- `tokenizer`
- `sacred eggs`
- `triadic`
- `harmonic`
- `geometry`
- `training`
- `21d state`
- `source roots`

## Canonical docs currently indexed by the MCP server

- `docs/map-room/scbe_source_roots.md`
- `docs/specs/BINARY_FIRST_TRAINING_STACK.md`
- `docs/research/CANONICAL_TRIADIC_HARMONIC_SYMBOL_REGISTRY.md`
- `docs/01-architecture/sacred-eggs-systems-model.md`

## Escalation rule

If the task changes from orientation into implementation, preserve the MCP outputs in the working notes and then switch to repo code, tests, or another SCBE skill. Do not keep querying the MCP server when the answer now depends on source edits or runtime verification.
