# root/ vs src/ package trees — they are VARIANTS, not duplicates

Audited 2026-07-27. **Do not "deduplicate" these by deleting one side.** An earlier pass of
this audit concluded `src/` was authoritative and root was a stale shadow. That was wrong,
and the correction is the most important thing on this page.

## They implement different mathematics, on purpose

```
symphonic_cipher/__init__.py:18       # Variant tag: ROOT package uses exponential cost
                                      # formula H(d,R) = R^(d²)
symphonic_cipher/__init__.py:21       _VARIANT = "root"

src/symphonic_cipher/__init__.py:18   # Variant tag: SRC package uses bounded safety score
                                      # H(d,pd) = 1/(1+d+2*pd) ∈ (0,1]
src/symphonic_cipher/__init__.py:21   _VARIANT = "src"
```

This mirrors the split the package itself documents: a **bounded decision score** used by
the 14-layer profiles, and a **separately named exponential distance-cost helper**
(`harmonic_wall`, whose docstring says it "is separate from the bounded score"). Deleting
either tree deletes a deliberate implementation, not a copy.

**Both are live.** 198 of the last 200 commits touch the root tree; root's last commit was
2026-07-24, src's 2026-07-27. Root is not abandoned.

## Which one you get depends on your working directory

This is the real defect — not the existence of two variants, but that the choice is
implicit.

Bare `from symphonic_cipher...` resolves to **root** for anything with cwd = repo root.
Confirmed live callers that get the ROOT variant:

- `scbe-cli.py:51,274,1140`
- `api/validation.py:24`
- `spiral-word-app/braid_ledger.py:35`
- `runnables/legacy/scbe-geo.py:55,60`

Tests get **src**, but only because `tests/conftest.py` fights for it:

```python
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_SRC_ROOT))      # src must come first
for _k in list(sys.modules):             # purge so the src/ variant is cleanly imported
    if _k == "symphonic_cipher" or _k.startswith("symphonic_cipher."):
        del sys.modules[_k]
```

`tests/test_negative_tongue_lattice.py:36` re-asserts the variant, and `setup.py` names the
collision outright: *"A single find rooted at '.' would name-collide with the duplicate root
packages."*

So a scan-heavy caller and a test can be running **different safety formulas** with no
signal at the call site.

## Measurement

| | files |
|---|---:|
| in both trees, different | 90 |
| in both trees, identical | 6 |
| root-only | 7 |
| src-only | 151 |

Where the two differ, `src/` is usually tidier — of nine files where root looked newer or
larger, **every apparent "root advantage" was an unused import** `src/` had already removed
(`pqc_harmonic.py` imports six names — `PHI`, `R_FIFTH`, `DEFAULT_BASE_BITS`,
`security_level`, `EncapsulationResult`, `derive_hybrid_key` — that appear *only* in the
import statement). That makes `src/` the better-maintained copy. It does **not** make root
redundant, because root computes something else.

## Blocker on any consolidation

`symphonic_cipher/geoseal/` (2 files) exists **only** in the root tree, is imported by
`scbe-cli.py:274` and `examples/symphonic_cipher_geoseal_manifold.py:6`, and is explicitly
excluded from packaging (`setup.py` `SRC_EXCLUDE` → `symphonic_cipher.geoseal*`). Removing
the root tree breaks the CLI.

Also root-only and live: `physics_sim/patrol.py` (542 LOC, 2 importers),
`physics_sim/test_bugfixes_and_patrol.py` (432), `training/federated_orchestrator.py` (202,
13 references by name), `training/doc_verifier.py` (136, 17 references by name).

## What was actually fixed

`src/symphonic_cipher/core.py` (27,578 bytes) — deleted. That directory held **both**
`core.py` and a `core/` package; Python resolves the package, so the file was unreachable
dead weight. It also broke `examples/python-basic.py`, whose `try/except` printed the
resulting `ImportError` as a tidy "Error:" line, so the documented example had never once
worked. Verified after: wheel gate green, 162 tests pass.

## The right fix, when someone takes it on

Not deletion. **Make the variant selection explicit** so no caller picks a safety formula by
accident:

1. Give the two variants distinct import names, or a single façade that takes the variant as
   a parameter and defaults deliberately.
2. Relocate the root-only live modules (`geoseal/`, `patrol.py`, the two `training/` ones) so
   neither tree is load-bearing by accident.
3. Only then can `tests/conftest.py` drop its `sys.modules` surgery — that workaround is the
   symptom, and it should be the last thing removed, not the first.

Until then, **keep both trees** and treat `_VARIANT` as the thing to check when two callers
disagree about a score.
