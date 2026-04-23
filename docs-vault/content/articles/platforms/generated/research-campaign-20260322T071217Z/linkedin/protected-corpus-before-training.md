# Do Not Train on Raw Ops Logs: Build a Protected Corpus First

The fastest way to poison a training pipeline is to confuse “useful internal data” with “safe training data.” SCBE’s current privacy lane is important because it stops making that mistake. The repo now draws a hard line: reversible replacement is pseudonymization, not de-identification, and synthetic training should come from the protected layer rather than from raw operational logs.

Why this matters:
- SCBE is moving from planning docs to executable operator surfaces.
- The work is tied to real commands, guides, and tests already in the repo.
- The point is governed execution, not vague agent theater.

Code refs: `docs/research/2026-03-21-synthetic-data-privacy-blueprint.md`, `scripts/build_protected_corpus.py`, `scripts/privacy_leakage_audit.py`

If you are building bounded multi-agent systems, this is the shape I think is actually shippable.
