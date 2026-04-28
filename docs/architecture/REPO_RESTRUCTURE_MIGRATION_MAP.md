# Repo Restructure Migration Map

This map tracks every move and compatibility adapter through the restructure rollout.

## Usage

- Add rows before performing any move.
- Keep adapter ownership explicit.
- Do not remove old-path adapters until the listed removal phase is complete and verified.

## Legend

- Compatibility adapter examples: wrapper script, alias, symlink/junction, forwarding config.
- Removal phase values: `phase2-batch1`, `phase2-batch2`, `phase3-cutover`.

## Move Table

| old path | new path | compatibility adapter | owner script/config | removal phase |
| --- | --- | --- | --- | --- |
| `artifacts/` (disposable) | `generated/artifacts/runtime/` | path alias in launch scripts | `scripts/system/scbe_paths.py` | `phase3-cutover` |
| `artifacts/` (evidence) | `artifacts/evidence/` (no move in phase 0/1) | none | `docs/architecture/REPO_RESTRUCTURE_GENERATED_DATA_POLICY.md` | `phase3-cutover` |
| `deploy/` | `infra/deploy/` | wrapper paths in ops scripts | `scripts/system/repo_path_reference_scan.py` | `phase2-batch2` |
| `k8s/` | `infra/k8s/` | wrapper paths in ops scripts | `scripts/system/repo_path_reference_scan.py` | `phase2-batch2` |
| `scripts/` | `ops/scripts/` (planned, blocked in phase 0/1) | command wrappers in `package.json` | `package.json` | `phase3-cutover` |
| `docs/` | `docs/` (canonical, no move in phase 0/1) | none | `scripts/system/check_markdown_links.py` | `n/a` |
| `training-data/` (non-canonical subsets only) | `training/data/local/` | dataset manifest redirects | `config/training/*` | `phase2-batch3` |

## Notes

- This map is intentionally conservative in Phase 0/1 and records planned moves without executing them.
- Runtime roots (`src/`, `python/`, `api/`, `tests/`, `packages/`) remain frozen until Phase 2 authorization.
