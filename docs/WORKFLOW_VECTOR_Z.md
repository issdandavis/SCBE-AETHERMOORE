# Workflow Vector `Z`

Yes: map `Z` directly to workflow actions.

## Definition
Let:
`Z = [z1, z2, z3, z4, z5]`

Action map:
1. `z1` -> `notion_sync`
2. `z2` -> `obsidian_snapshot`
3. `z3` -> `git_commit`
4. `z4` -> `dropbox_backup`
5. `z5` -> `zapier_emit`

Enable rule:
`action_i = 1 if z_i >= theta else 0`

## Example
`Z = [1, 1, 0, 1, 0]` -> notion + obsidian + dropbox only.

## CLI
```powershell
python scripts/system/workflow_vector.py --z 1,1,0,1,0 --threshold 0.5
```

## Why this helps
- deterministic orchestration
- compact state for swarm planning
- easy to hash/sign (`workflow_signature`) for provenance
