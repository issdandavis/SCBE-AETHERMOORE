# bin/

Node launchers. `package.json` publishes four commands from here: `geoseal` and `scbe-geoseal` (both `geoseal.cjs`), `scbe-patent`, and `scbe-scan`. `scbe.cjs` and `scbe-system.cjs` are **not** in the `bin` map; they only work from a repo checkout.

| File | Role |
|------|------|
| `scbe.cjs` | 21-line launcher that runs `scbe.py` at the repo root with Python |
| `scbe-system.cjs` | 21-line launcher that runs `scripts/scbe-system-cli.py` with Python |
| `scbe-scan.cjs` | Scan command: loads the built API and prints a decision record |
| `scbe-patent.cjs` | Patent-packet helper (hashing and writing evidence files) |
| `geoseal.cjs` | GeoSeal CLI; the largest file here, with the HTTP client for the `/v1/...` service routes |

None of these files has a header comment. New command logic belongs in `packages/cli/`.

---

Every file in this directory is listed with a one-line description in [`docs/file-index/bin.md`](../docs/file-index/bin.md).
