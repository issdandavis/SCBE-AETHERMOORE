#!/usr/bin/env python3
"""Merge a PEFT LoRA adapter into its base model locally.

This is the local fallback for remote merge jobs. It is intentionally narrow:
one base model plus one adapter path/repo becomes one full merged model folder.
Use Hugging Face upload tooling after this script if the merged artifact should
be published.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge one PEFT adapter into a full causal-LM model.")
    parser.add_argument("--base-model", required=True, help="Base model id, e.g. Qwen/Qwen2.5-Coder-0.5B-Instruct")
    parser.add_argument("--adapter", required=True, help="Local adapter folder or HF adapter repo id")
    parser.add_argument("--output-dir", required=True, help="Merged model output directory")
    parser.add_argument("--summary", default=None, help="Optional JSON summary path")
    parser.add_argument("--trust-remote-code", action="store_true", help="Pass trust_remote_code=True")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=args.trust_remote_code)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id

    base = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        torch_dtype=torch.float32,
        low_cpu_mem_usage=True,
        trust_remote_code=args.trust_remote_code,
    )
    model = PeftModel.from_pretrained(base, args.adapter, is_trainable=False)
    merged = model.merge_and_unload()
    merged.save_pretrained(str(out_dir), safe_serialization=True)
    tokenizer.save_pretrained(str(out_dir))

    summary = {
        "schema_version": "scbe_local_peft_merge_result_v1",
        "merged_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_model": args.base_model,
        "adapter": args.adapter,
        "output_dir": str(out_dir),
    }
    summary_path = Path(args.summary) if args.summary else out_dir / "scbe_merge_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
