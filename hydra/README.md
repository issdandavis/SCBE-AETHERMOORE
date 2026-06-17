# hydra/ — moved

This directory was extracted from the monolith and now lives in its own repo:

**→ https://github.com/issdandavis/scbe-agents**

The `scbe-agents` repo contains the former `agents/`, `hydra/`, and `mcp/` trees. The HYDRA 6-agent swarm coordinator (Kor'aelin, Avali, Runethic, Cassisivadan, Umbroth, Draumric) lives alongside the agent runtime and MCP servers that it drives.

Install:
```bash
git clone https://github.com/issdandavis/scbe-agents.git
```

The full pre-split state of SCBE-AETHERMOORE is preserved at tag `v-monolith-final` in this repo — checkout with `git checkout v-monolith-final`.
