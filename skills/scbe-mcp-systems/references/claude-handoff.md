# Claude Handoff

Use this packet when Claude should follow the same SCBE MCP-first workflow that Codex uses.

## Direct handoff text

Use the SCBE MCP service as the first orientation layer for work in `C:\Users\issda\SCBE-AETHERMOORE`.

Order:

1. Call `scbe_tokenizer_health` if MCP health is uncertain.
2. Call `scbe_system_manifest` to identify the repo, command areas, canonical docs, and SCBE MCP tool inventory.
3. Call `scbe_command_catalog` for any command request before inventing shell commands.
4. Call `scbe_reference_lookup` before explaining tokenizer, Sacred Eggs, triadic, harmonic, geometry, training, or 21D state concepts.
5. Only fall back to shell probing or direct file reads when the MCP answer is insufficient.

## Fallback if Claude does not have SCBE MCP mounted

Read these files directly in this order:

1. `skills/scbe-mcp-systems/SKILL.md`
2. `skills/scbe-mcp-systems/references/mcp-first-workflow.md`
3. `mcp/scbe-server/README.md`
4. `docs/map-room/scbe_source_roots.md`
5. `docs/specs/BINARY_FIRST_TRAINING_STACK.md`
6. `docs/research/CANONICAL_TRIADIC_HARMONIC_SYMBOL_REGISTRY.md`
7. `docs/01-architecture/sacred-eggs-systems-model.md`

## Minimal Claude prompt

Use `skills/scbe-mcp-systems` as the workflow. Start with SCBE MCP, not shell guesses. Pull the repo manifest first, then command catalog or reference lookup depending on the task.
