# boundary marker — this directory is the TOKENIZER role

`src/tokenizer/` is the Six-Tongues **byte↔token encoding** (e.g. `ss1.ts`,
the 16×16 bijective vocabulary — patent claims 26–28). It is **not** the typed
routing IR.

- Encoding / tokenizer role → here, `src/crypto/sacred_tongues.py`, `packages/sixtongues/`
- Routing / typing **IR** role → `src/coding_spine/` (`shared_ir.py`, `router.py`), `src/cli/cross_build_ir.py`

Full disambiguation and the keep-apart rule: **`docs/BOUNDARIES.md` §1**.
