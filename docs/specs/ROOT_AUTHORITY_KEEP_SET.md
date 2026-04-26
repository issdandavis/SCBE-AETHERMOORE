# Root Authority Keep Set

This file defines which root-level documents should remain first-class during the consolidation process.

## Keep At Root

These files are allowed to stay prominent at the root because they are entrypoint, canonical, operational, or standard repository surfaces:

- `README.md`
- `START_HERE.md`
- `CANONICAL_SYSTEM_STATE.md`
- `SPEC.md`
- `SECURITY.md`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `AGENTS.md`
- `LICENSE`
- `NOTICE`
- build and package manifests like `package.json`, `pyproject.toml`, `requirements.txt`, and `tsconfig*.json`

## Prefer As Root Shims

These should remain linkable from the root if needed, but should usually defer to `docs/` rather than carrying long-form content at the root:

- architecture overviews
- repo maps
- state summaries
- reports
- audits
- test reports
- product/business strategy notes
- scripts or video copy decks

## Move Out Of The First-Run Path

These do not belong as first-run root surfaces:

- screenshots
- generated reports
- experimental captures
- notebook screenshots
- operator scratch files
- historical exports

Those should move into archive lanes or documentation subtrees.
