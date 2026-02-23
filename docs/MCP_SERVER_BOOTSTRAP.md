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
  "github",
  "scbe",
  "power-cloud-architect-fetch",
  "power-postman-postman"
)
```

## GitHub MCP server (local container)

Workspace `.mcp.json` now includes a `github` MCP entry backed by:

- `ghcr.io/github/github-mcp-server`
- default mode: read-only (`GITHUB_READ_ONLY=1`)
- dynamic toolsets enabled (`GITHUB_DYNAMIC_TOOLSETS=1`)

Set a PAT in your environment before starting MCP hosts:

```powershell
$env:GITHUB_PAT = "<your_github_pat>"
```

Source repo reference: `git@github.com:github/github-mcp-server.git`

## SCBE local MCP server

Workspace `.mcp.json` includes a local `scbe` MCP server:

- command: `node C:\Users\issda\SCBE-AETHERMOORE\mcp\scbe-server\server.mjs`
- tools: tokenizer + map room handoff I/O

If you run from user-level MCP config (`~/.kiro/settings/mcp.json`), add the same server block there or use the command snippet in the Map Room handoff.

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
