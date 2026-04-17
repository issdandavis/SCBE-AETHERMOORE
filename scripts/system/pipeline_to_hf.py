#!/usr/bin/env python3
"""
Push news-pipeline SFT data to HuggingFace dataset.

Converts training-data/news-pipeline/sft/*.jsonl into ChatML-formatted
records and pushes to issdandavis/scbe-aethermoore-training-data.

Usage:
    python scripts/system/pipeline_to_hf.py            # dry run, print stats
    python scripts/system/pipeline_to_hf.py --push     # push to HF
    HF_TOKEN=hf_... python scripts/system/pipeline_to_hf.py --push

The SFT format (instruction / input / output) is converted to ChatML:
    system:  SCBE-AETHERMOORE post-quantum news pipeline assistant.
    user:    {instruction}\n\n{input}          (input omitted if empty)
    assistant: {output}
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SFT_DIR = REPO_ROOT / "training-data" / "news-pipeline" / "sft"
HF_DATASET = "issdandavis/scbe-aethermoore-training-data"
HF_SUBSET = "news-pipeline"

SYSTEM_PROMPT = (
    "You are an SCBE-AETHERMOORE post-quantum news pipeline assistant. "
    "You understand the full 7-stage pipeline: GeoSeal geographic tagging, "
    "Sacred Tongues tokenization (Kor'aelin/Avali/Runethic/Cassisivadan/Umbroth/Draumric), "
    "SHA-256/HMAC hash chains, Sacred Egg envelope creation, "
    "ML-KEM-768 post-quantum encryption, and ML-DSA-65 transport signing. "
    "Respond with precise protocol-correct JSON."
)


def load_sft_pairs() -> list[dict]:
    """Load all SFT JSONL files from the pipeline output directory."""
    pairs = []
    for jsonl_file in sorted(SFT_DIR.glob("*.jsonl")):
        with jsonl_file.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        pairs.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return pairs


def to_chatml(pair: dict) -> dict:
    """Convert Alpaca-style SFT pair to ChatML conversation format."""
    instruction = pair.get("instruction", "")
    inp = pair.get("input", "")
    output = pair.get("output", "")

    user_content = instruction
    if inp and inp not in ("{}", "null", ""):
        user_content = f"{instruction}\n\n{inp}"

    return {
        "id": pair.get("id", ""),
        "pipeline": pair.get("pipeline", "news-pipeline"),
        "version": pair.get("version", "v1"),
        "conversations": [
            {"role": "system",    "content": SYSTEM_PROMPT},
            {"role": "user",      "content": user_content},
            {"role": "assistant", "content": output},
        ],
        # Keep raw fields for filtering / re-use
        "instruction": instruction,
        "input": inp,
        "output": output,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Push pipeline SFT to HuggingFace")
    parser.add_argument("--push", action="store_true", help="Actually push to HF Hub")
    parser.add_argument("--token", default=os.getenv("HF_TOKEN"), help="HF write token")
    args = parser.parse_args()

    pairs = load_sft_pairs()
    if not pairs:
        print("[pipeline_to_hf] No SFT pairs found in", SFT_DIR)
        sys.exit(1)

    chatml = [to_chatml(p) for p in pairs]

    # Stage breakdown
    stages: dict[str, int] = {}
    for p in pairs:
        stage = p.get("id", "").split(":")[1] if ":" in p.get("id", "") else "?"
        stages[stage] = stages.get(stage, 0) + 1

    print(f"[pipeline_to_hf] Loaded {len(pairs)} SFT pairs from {SFT_DIR}")
    print("[pipeline_to_hf] Stage breakdown:")
    for s, n in sorted(stages.items()):
        print(f"  {s}: {n}")

    if not args.push:
        print("\n[pipeline_to_hf] Dry run — pass --push to upload to HuggingFace")
        print(f"[pipeline_to_hf] Target: {HF_DATASET}  subset={HF_SUBSET}")
        print("[pipeline_to_hf] Sample ChatML record:")
        print(json.dumps(chatml[0], indent=2, ensure_ascii=False)[:600], "...\n")
        return

    try:
        from datasets import Dataset  # type: ignore
        from huggingface_hub import HfApi  # type: ignore
    except ImportError:
        print("[pipeline_to_hf] ERROR: pip install datasets huggingface_hub")
        sys.exit(1)

    token = args.token
    if not token:
        print("[pipeline_to_hf] ERROR: set HF_TOKEN env var or pass --token")
        sys.exit(1)

    import tempfile

    dataset = Dataset.from_list(chatml)
    print(f"[pipeline_to_hf] Converting {len(dataset)} records to parquet ...")

    with tempfile.TemporaryDirectory() as tmp:
        pq_path = Path(tmp) / "train.parquet"
        dataset.to_parquet(str(pq_path))
        pq_size = pq_path.stat().st_size

        # Upload directly via HfApi to avoid dataset-card YAML validation
        # conflicts with existing configs that use slash-syntax split names.
        api = HfApi(token=token)
        dest = f"data/{HF_SUBSET}/train-00000-of-00001.parquet"
        print(f"[pipeline_to_hf] Uploading {pq_size:,} bytes -> {HF_DATASET}/{dest}")
        api.upload_file(
            path_or_fileobj=str(pq_path),
            path_in_repo=dest,
            repo_id=HF_DATASET,
            repo_type="dataset",
            commit_message=(
                f"news-pipeline SFT: {len(dataset)} pairs "
                f"(8-stage PQC transport + semantic-atomic braid)"
            ),
        )

    print(f"[pipeline_to_hf] Done. https://huggingface.co/datasets/{HF_DATASET}")


if __name__ == "__main__":
    main()
