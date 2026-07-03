# SCBE Manaan Permeable Docking Demo

Interactive prototype for the original "Star Wars TOR Manaan doorway" concept:

- Magnetically-confined PFPE/ferrofluid liquid plug
- Differential pumping staircase for standby
- Dartfish trailing edge for minimal film drag-out
- CA conlang commands (Sacred Tongues lane) for docking protocol
- SCBE DockingProtocol / ReentryShield metaphors from `scbe_spaceflight.py`

## Run

```bash
# Python reference
python instrument-wt/demos/scbe-manaan-docking/demo.py

# Open the interactive HTML in any browser
open instrument-wt/demos/scbe-manaan-docking/index.html   # or just double-click
```

## Honesty Firewalls (enforced in source)

- `emitted-to-8 faces` (provenance / polyglot) is **never** claimed as `executed-on-8`.
- Verified = actually ran and agreed (Python + Rust in this case).
- Conlang macros registered level=6 with explicit caveat.
- BOM/UTF issues routed through transference gate at adapter level.
- All caveats live in source + manifests, not just run logs.

See:
- `artifacts/ai_brain/conlang_macros_claim_manifest.json`
- `python/scbe/rosetta.py` (the verified Rosetta mechanism)
- `src/scbe_spaceflight.py` (DockingProtocol, custody, hyperbolic trajectory)
- `python/scbe/language_library_registry.py` (the entry you added)

## Physics

Ported from the earlier `drone_permeable_interface_sim.py`:
- Choked flow for any open annular gap (catastrophic)
- Landau-Levich film thickness using small trailing radius (the dartfish win)
- Capillary number governs drag-out

## Conlang Example

`bip'a draum-sel` → add + clamp → verified core execution.

The paraphrase round-trip is the load-bearing verification step for a non-reader.

## SCBE Mapping

- Liquid plug → ReentryShield / DockingProtocol
- Pumping stages → DelayTolerantBundle custody chain
- Conlang command → CA lane (binds-to core, emits-to faces)
- Gate decision → Governance (ALLOW / QUARANTINE)

This demo keeps the original engineering goal (minimal-loss drone passage) while respecting the project's provenance discipline.