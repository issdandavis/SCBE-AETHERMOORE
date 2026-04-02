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
  "huggingface",
  "kaggle",
  "scbe",
  "power-cloud-architect-fetch",
  "power-postman-postman"
)
```

## GitHub MCP server

Workspace `.mcp.json` now includes a `github` MCP entry backed by:

- `@modelcontextprotocol/server-github`
- launched via explicit Windows `cmd.exe` + `npx.cmd` paths to avoid `program not found` startup errors

Set a PAT in your environment before starting MCP hosts:

```powershell
$env:GITHUB_PAT = "<your_github_pat>"
```

## Hugging Face MCP server

Workspace `.mcp.json` now includes a `huggingface` MCP entry backed by:

- `mcp-remote`
- remote endpoint: `https://huggingface.co/mcp`
- auth header: `Authorization: Bearer ${HF_TOKEN}`

For Codex specifically, the live user config should prefer the native HTTP MCP URL:

- `https://huggingface.co/mcp?login`

That matches the installed Hugging Face plugin metadata and avoids the handshake issue seen with the `mcp-remote` wrapper in this host.

Set a token in your environment before starting MCP hosts:

```powershell
$env:HF_TOKEN = "<your_huggingface_token>"
```

## Kaggle MCP server

Workspace `.mcp.json` includes a `kaggle` MCP entry backed by:

- `mcp-remote`
- remote endpoint: `https://www.kaggle.com/mcp`
- auth header: `Authorization: Bearer ${KAGGLE_API_TOKEN}`

Set a token in your environment before starting MCP hosts:

```powershell
$env:KAGGLE_API_TOKEN = "<your_kaggle_api_token>"
```

Direct probe note: the Kaggle remote MCP endpoint completed proxy establishment successfully with this launcher shape.

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
