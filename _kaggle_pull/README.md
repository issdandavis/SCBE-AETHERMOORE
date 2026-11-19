# _kaggle_pull/

Local copies of Kaggle kernels and datasets pulled back from Kaggle, kept so training runs can be reproduced.

- `hftrain/` — notebook for Polly SFT training via the Hugging Face stack on Kaggle, plus its `kernel-metadata.json`.
- `qlora/` — Polly QLoRA training kernel. `polly-qlora-training.py` is a notebook export and **does not parse as Python** (SyntaxError at line 190); treat it as a record, not an importable module.
- `vtc_data/` — the "VTC MBPP Refined Corpus" dataset (161 chat-format records) and its Kaggle metadata.
- `vtc_mbpp_refined.freeze.json` — freeze manifest for that corpus (SHA-256, dedup rule, hidden-test policy).

The same 161-record JSONL is also tracked at `training-data/sft/vtc_mbpp_refined.jsonl`.

---

Every file in this directory is listed with a one-line description in [`docs/file-index/_kaggle_pull.md`](../docs/file-index/_kaggle_pull.md).
