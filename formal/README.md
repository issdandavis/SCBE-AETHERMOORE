# formal/

Machine-checked mathematics.

`lean/` is a Lean 4 project stating SCBE's mathematical contracts as theorems. Modules under `lean/SCBE/` cover geometry (exact real arithmetic; the headers note IEEE-754 rounding is not modelled), the harmonic cost function, routing, composition of decisions, codecs, and tongue vocabularies. `lean/evidence/` holds JSON records of proof-check runs (Lean version, theorem count, axioms used).

Read `lean/README.md` for scope and build steps.

---

Every file in this directory is listed with a one-line description in [`docs/file-index/formal.md`](../docs/file-index/formal.md).
