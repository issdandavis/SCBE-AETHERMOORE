# apps/

Standalone applications that consume SCBE but ship separately from the npm/PyPI packages.

| App | Stack | What it is |
|-----|-------|------------|
| `aether-desktop/` | FastAPI backend + Vite/React shell, Fly.io config | Desktop workspace: a tool bus with chat and tool-console windows, API-key auth, and an audit writer. Backend tests live in `backend/tests/`, shell tests in `shell/tests/` |
| `mobile/` | React PWA (`pwa/`) + Trusted Web Activity manifest (`twa/`) | "Aethermoor Bus" phone client: login gate, agent list, and bus feed. Has its own README |
| `outreach/` | FastAPI + SQLAlchemy + static front-end | "Aethermoor Outreach": civic and business workflow engine (intent classification, document generation). Has its own README; start with `python apps/outreach/run.py` |
| `scbe-github-app/` | GitHub App manifest | "SCBE Repo Manager" app definition. Has its own README |

Most `aether-desktop` Python modules have no docstring; the file index lists their classes and functions.

---

Every file in this directory is listed with a one-line description in [`docs/file-index/apps.md`](../docs/file-index/apps.md).
