# services/

Small deployable services.

| Service | Runtime | What it is |
|---------|---------|------------|
| `scbe-shim/` | Cloudflare Worker (TypeScript) | OpenAI-compatible governance proxy. Its own header states that the axiom checks are **surface heuristics, not the full 14-layer pipeline** |
| `scbe-shim-space/` | FastAPI in Docker (Hugging Face Space) | Python mirror of the Worker; `shim/*.py` each mirror one `scbe-shim/src/*.ts` file. Keep both in sync |
| `kernel-runner/` | Node | Sandboxed playground for running the npm kernel package |

Each has its own README; `scbe-shim/DEPLOY.md` covers free-tier deployment.

---

Every file in this directory is listed with a one-line description in [`docs/file-index/services.md`](../docs/file-index/services.md).
