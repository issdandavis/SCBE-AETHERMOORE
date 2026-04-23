# Programmatic Hugging Face Training Needs a Governed Staging Lane

The biggest practical improvement in the SCBE training lane is not a new model. It is the fact that the repo now has a governed programmatic path from local training records to a package that can be audited, split, and optionally pushed to Hugging Face. That is what turns “we have data everywhere” into an actual training system.

I am building this in public in one repo, and the claim I care about is simple: the code should exist before the article exists.

Repo-backed references:
- `scripts/programmatic_hf_training.py`
- `scripts/build_offload_sft_records.py`
- `src/training/auto_ledger.py`
- `training/ledgered/sft_ledgered_clean.jsonl`

If you were evaluating this as a workflow/runtime instead of a paper idea, what would you test first?
