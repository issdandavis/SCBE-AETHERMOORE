"""One-shot: upload Brick 0 adapter + drill data to HuggingFace for Colab access.

Creates:
  - model repo  issdandavis/tongue-table-lora-brick0-v5  (adapter weights, private=False)
  - dataset repo issdandavis/scbe-drill-langues-full     (drill_langues_full.jsonl)
"""
from __future__ import annotations

from pathlib import Path

from huggingface_hub import HfApi

REPO_ROOT = Path(__file__).resolve().parent.parent
ADAPTER_DIR = REPO_ROOT / "artifacts" / "tongue-table-lora-brick0-v5" / "lora_final"
DRILL_FILE = REPO_ROOT / "data" / "tongue_drill" / "drill_langues_full.jsonl"

MODEL_REPO = "issdandavis/tongue-table-lora-brick0-v5"
DATA_REPO = "issdandavis/scbe-drill-langues-full"


def main() -> int:
    api = HfApi()

    print(f"[HF] creating model repo: {MODEL_REPO}")
    api.create_repo(repo_id=MODEL_REPO, repo_type="model", exist_ok=True, private=False)
    print(f"[HF] uploading adapter folder: {ADAPTER_DIR}")
    api.upload_folder(
        folder_path=str(ADAPTER_DIR),
        repo_id=MODEL_REPO,
        repo_type="model",
        commit_message="Brick 0 v5 LoRA adapter (warm-start for Brick 1)",
    )
    print(f"[HF] model upload complete: https://huggingface.co/{MODEL_REPO}")

    print(f"[HF] creating dataset repo: {DATA_REPO}")
    api.create_repo(repo_id=DATA_REPO, repo_type="dataset", exist_ok=True, private=False)
    print(f"[HF] uploading drill file: {DRILL_FILE}")
    api.upload_file(
        path_or_fileobj=str(DRILL_FILE),
        path_in_repo="drill_langues_full.jsonl",
        repo_id=DATA_REPO,
        repo_type="dataset",
        commit_message="Brick 0/1 drill dataset (2630 rows)",
    )
    print(f"[HF] dataset upload complete: https://huggingface.co/datasets/{DATA_REPO}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
