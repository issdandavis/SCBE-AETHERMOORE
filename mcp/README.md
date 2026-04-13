# mcp/ — moved

This directory was extracted from the monolith and now lives in its own repo:

**→ https://github.com/issdandavis/scbe-agents**

The `scbe-agents` repo contains the former `agents/`, `hydra/`, and `mcp/` trees. The MCP (Model Context Protocol) servers — notion_server, scbe_server, swarm_server, and the scbe-server bundle — ship alongside the agent runtime and HYDRA swarm that consume them.

Install:
```bash
git clone https://github.com/issdandavis/scbe-agents.git
```

The full pre-split state of SCBE-AETHERMOORE is preserved at tag `v-monolith-final` in this repo — checkout with `git checkout v-monolith-final`.
