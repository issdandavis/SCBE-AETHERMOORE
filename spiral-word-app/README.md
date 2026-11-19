# spiral-word-app/

"SpiralWord": a collaborative text editor with SCBE governance, as a FastAPI backend.

- `app.py` — the API server.
- `braid_ledger.py` — the edit ledger.
- `ai_ports.py` — pluggable AI provider ports.

Each module header lists the pipeline layers it touches. The folder name contains a hyphen, so it cannot be imported as `spiral-word-app`; tests in `tests/spiral_word/` load it by path.

---

Every file in this directory is listed with a one-line description in [`docs/file-index/spiral-word-app.md`](../docs/file-index/spiral-word-app.md).
