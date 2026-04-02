# The First Agent Product Surface Is a Local MCP

Most agent failures do not start with bad model weights. They start with bad orientation.

The useful SCBE shift this week is small but practical: repo orientation is moving into a local MCP surface with explicit tools for:

- health checks
- repo and tool manifest lookup
- command catalog lookup
- canonical document lookup

That matters because large system repos break down when agents rely on prompt memory instead of grounded operator surfaces.

The pattern I think is actually shippable is:

- MCP for orientation
- CLI for execution

SCBE already documents the CLI side in `docs/TERMINAL_OPS_QUICKSTART.md`, and the new MCP side is documented in `mcp/scbe-server/README.md`.

The result is not “AI magic.” It is a smaller claim:

- identity is queryable
- commands are queryable
- canonical docs are queryable
- health is queryable

That is a better product boundary for multi-agent systems than vague repo familiarity.

Code-backed references:

- `mcp/scbe-server/README.md`
- `mcp/scbe-server/server.mjs`
- `docs/map-room/scbe_source_roots.md`
- `docs/TERMINAL_OPS_QUICKSTART.md`
- `skills/scbe-mcp-systems/SKILL.md`
- `CLAUDE.md`
