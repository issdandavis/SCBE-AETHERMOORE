# MCP Server Bootstrap for SCBE Agents

## Current session capability check

- This workspace currently exposes no active MCP resources through the Codex tooling (`list_mcp_resources` returned empty).
- That is normal for session-level capability.
- MCP availability for future agents is controlled by your local MCP configuration files.

## What was prepared

Added helper:

- `scripts/enable_mcp_servers.ps1`

This script enables MCP server entries in:

- `~/.kiro/settings/mcp.json`

It is non-destructive by default and only flips `disabled` flags on known entries.

## How to use now (recommended)

1. Enable baseline web/fetch MCP entries:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\enable_mcp_servers.ps1
```

2. Optional: enable extra servers by name:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\enable_mcp_servers.ps1 -Servers @(
  "fetch",
  "power-cloud-architect-fetch",
  "power-postman-postman"
)
```

3. Do a dry run first if you want:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\enable_mcp_servers.ps1 -DryRun
```

## Recommended follow-up for future agents

- Keep this file in place so every new agent can run the same bootstrap step.
- Add required credentials per server before enabling providers that need tokens/keys (Postman, Figma, AWS, etc.).
- Document server choices in your onboarding notes so team agents do not each have to re-learn setup.

## Known constraints

- Enabling a server in config does not guarantee external network/service credentials are valid.
- Some MCP servers require runtime packages (`uvx`, `npx`) and external auth.
- After changing MCP config, restart the host app/client that loads MCP servers.
