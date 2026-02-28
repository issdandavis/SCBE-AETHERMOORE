# Skill Tool GO-TO README

Purpose: convert skill guidance into repeatable tool execution.

## Quick Start

```powershell
npm run skills:bridge
```

## Full Pass

```powershell
npm run skills:bridge:full
```

## What It Runs

1. `obsidian-vault-ops`:
- `python C:\Users\issda\.codex\skills\obsidian-vault-ops\scripts\list_obsidian_vaults.py`

2. `code_prism/code_mesh` validation:
- `pytest tests/code_prism -q`

3. Full mode only:
- `npm run typecheck`
- `npm run mcp:servers`
- `npm run mcp:tools`
- Code Mesh smoke conversion via `scripts/code_mesh_build.py`

## Script Location

- `scripts/system/scbe_skill_tool_bridge.ps1`

## Notes

- The bridge is non-destructive and fail-soft by step (it continues on errors and reports them).
- Open Claw integration is pending a concrete path/reference in vault or repo docs.
