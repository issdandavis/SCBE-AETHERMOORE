# Docker Terminal Operations (No UI Required)

Use this repo script to run all SCBE Docker stacks directly from terminal.

## Script

`scripts/scbe_docker_status.ps1`

## Supported stacks

- `default` -> `docker-compose.yml`
- `api` -> `docker-compose.api.yml`
- `unified` -> `docker-compose.unified.yml`
- `research` -> `docker-compose.research.yml`
- `hydra-remote` -> `docker-compose.hydra-remote.yml`

Each stack is run with an isolated Compose project name:
`scbe-default`, `scbe-api`, `scbe-unified`, `scbe-research`, `scbe-hydra-remote`.

## Core commands

```powershell
# Doctor (config + ports + compose status + health)
.\scripts\scbe_docker_status.ps1 -Action doctor -Stack api

# Bring up a stack with build
.\scripts\scbe_docker_status.ps1 -Action up -Stack api

# Bring down a stack
.\scripts\scbe_docker_status.ps1 -Action down -Stack api

# Tail logs for a stack
.\scripts\scbe_docker_status.ps1 -Action logs -Stack api -LogTail 200 -Follow

# Tail logs for one container
.\scripts\scbe_docker_status.ps1 -Action logs -ContainerName scbe-core -Follow

# Inspect all stacks at once
.\scripts\scbe_docker_status.ps1 -InspectStacks
```

## npm shortcuts (Windows PowerShell)

```powershell
npm run docker:doctor:api
npm run docker:up:api
npm run docker:down:api
npm run docker:doctor:unified
npm run docker:up:unified
npm run docker:down:unified
npm run docker:status:all
```

## Docker MCP (No UI)

Use this helper for Docker MCP Toolkit commands:

`scripts/scbe_mcp_terminal.ps1`

```powershell
# Verify MCP status from terminal
.\scripts\scbe_mcp_terminal.ps1 -Action doctor

# List configured MCP servers and tools
.\scripts\scbe_mcp_terminal.ps1 -Action servers
.\scripts\scbe_mcp_terminal.ps1 -Action tools

# Run gateway in foreground
.\scripts\scbe_mcp_terminal.ps1 -Action gateway
```

`npm` shortcuts:

```powershell
npm run mcp:doctor
npm run mcp:servers
npm run mcp:tools
npm run mcp:gateway
```

## Runtime notes

- `Dockerfile.api` healthcheck uses `/v1/health`.
- `docker-compose.yml` maps `8000:8080` for `scbe-app` (container serves on 8080).
- `docker-compose.unified.yml` sets:
  - `scbe-core` `PORT=8000`
  - `unity-bridge` `PORT=8081`

These keep health checks and host port mappings aligned.
