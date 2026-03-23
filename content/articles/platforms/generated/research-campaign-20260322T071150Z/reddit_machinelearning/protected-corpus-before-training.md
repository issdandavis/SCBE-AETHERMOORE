# Do Not Train on Raw Ops Logs: Build a Protected Corpus First

The fastest way to poison a training pipeline is to confuse “useful internal data” with “safe training data.” SCBE’s current privacy lane is important because it stops making that mistake. The repo now draws a hard line: reversible replacement is pseudonymization, not de-identification, and synthetic training should come from the protected layer rather than from raw operational logs.

I am building this in public in one repo, and the claim I care about is simple: the code should exist before the article exists.

Repo-backed references:
- `docs/research/2026-03-21-synthetic-data-privacy-blueprint.md`
- `scripts/build_protected_corpus.py`
- `scripts/privacy_leakage_audit.py`
- `src/security/privacy_token_vault.py`

If you were evaluating this as a workflow/runtime instead of a paper idea, what would you test first?
