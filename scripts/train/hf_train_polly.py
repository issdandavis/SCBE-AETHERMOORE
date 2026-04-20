"""HF-side SFT training for Polly (SCBE-AETHERMOORE).

Pulls dataset from issdandavis/polly-training-data, trains a LoRA adapter on
Qwen2.5-0.5B (or any compatible CausalLM), and optionally pushes the adapter
to a Hugging Face model repo (default: issdandavis/polly-1).

Designed to run on:
  - Colab Pro+ (T4 / L4 / A100)
    - HF Spaces with a GPU runtime
      - Any local CUDA box

      Usage:
          HF_TOKEN=hf_xxx python scripts/train/hf_train_polly.py \
        --output-repo issdandavis/polly-1 \
        --epochs 3 --batch-size 4 --lr 2e-4 --push

        Notes:
          - max_grad_norm is clipped at 1.0 to fix the 12-15 grad spikes seen during
              Brick 1 LoRA training.
                - Uses 4-bit nf4 quantization via bitsandbytes; falls back to fp16 if bnb
                    is unavailable. Set --no-quant to disable.
                      - Dataset rows are expected in chat format: {"messages": [{"role","content"}, ...]}
                          with optional metadata fields (track, source_type, quality, surface) which
                              are dropped before training.
                              """
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import torch
from datasets import load_dataset
from peft import LoraConfig, TaskType, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTConfig, SFTTrainer


def _build_quant_config(disabled: bool):
      if disabled:
                return None
            try:
                      from transformers import BitsAndBytesConfig

        return BitsAndBytesConfig(
                      load_in_4bit=True,
                      bnb_4bit_quant_type="nf4",
                      bnb_4bit_compute_dtype=torch.float16,
                      bnb_4bit_use_double_quant=True,
        )
except Exception as exc:  # noqa: BLE001
        print(f"[hf_train_polly] bitsandbytes unavailable ({exc}); using fp16 full weights", file=sys.stderr)
        return None


def main() -> int:
      ap = argparse.ArgumentParser()
    ap.add_argument("--base-model", default="Qwen/Qwen2.5-0.5B")
    ap.add_argument("--dataset", default="issdandavis/polly-training-data")
    ap.add_argument("--dataset-split", default="train")
    ap.add_argument("--output-repo", default="issdandavis/polly-1",
                                        help="HF model repo to push the trained adapter to")
    ap.add_argument("--output-dir", default="./out/polly-lora")
    ap.add_argument("--epochs", type=float, default=3.0)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--grad-accum", type=int, default=4)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--max-seq", type=int, default=1024)
    ap.add_argument("--lora-r", type=int, default=16)
    ap.add_argument("--lora-alpha", type=int, default=32)
    ap.add_argument("--lora-dropout", type=float, default=0.05)
    ap.add_argument("--warmup-ratio", type=float, default=0.03)
    ap.add_argument("--max-grad-norm", type=float, default=1.0)
    ap.add_argument("--no-quant", action="store_true", help="disable 4-bit quantization")
    ap.add_argument("--push", action="store_true", help="push adapter to HF on finish")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not token:
              print("[hf_train_polly] ERROR: set HF_TOKEN env var", file=sys.stderr)
              return 2

    print(f"[hf_train_polly] loading dataset {args.dataset}:{args.dataset_split}")
    ds = load_dataset(args.dataset, split=args.dataset_split, token=token)
    keep = {"messages"}
    drop_cols = [c for c in ds.column_names if c not in keep]
    if drop_cols:
              ds = ds.remove_columns(drop_cols)
          print(f"[hf_train_polly] dataset rows: {len(ds)}")

    print(f"[hf_train_polly] loading tokenizer + base model: {args.base_model}")
    tok = AutoTokenizer.from_pretrained(args.base_model, token=token)
    if tok.pad_token is None:
              tok.pad_token = tok.eos_token

    quant = _build_quant_config(args.no_quant)
    model_kwargs = {"token": token, "device_map": "auto"}
    if quant is not None:
              model_kwargs["quantization_config"] = quant
else:
        model_kwargs["torch_dtype"] = torch.float16

    model = AutoModelForCausalLM.from_pretrained(args.base_model, **model_kwargs)

    lora = LoraConfig(
              r=args.lora_r,
              lora_alpha=args.lora_alpha,
              lora_dropout=args.lora_dropout,
              bias="none",
              task_type=TaskType.CAUSAL_LM,
              target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                                                      "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cfg = SFTConfig(
              output_dir=str(output_dir),
              num_train_epochs=args.epochs,
              per_device_train_batch_size=args.batch_size,
              gradient_accumulation_steps=args.grad_accum,
              learning_rate=args.lr,
              lr_scheduler_type="cosine",
              warmup_ratio=args.warmup_ratio,
              max_grad_norm=args.max_grad_norm,
              logging_steps=10,
              save_steps=200,
              save_total_limit=3,
              bf16=False,
              fp16=True,
              max_seq_length=args.max_seq,
              packing=False,
              report_to=[],
              seed=args.seed,
              push_to_hub=args.push,
              hub_model_id=args.output_repo if args.push else None,
              hub_token=token if args.push else None,
              dataset_text_field=None,  # use chat-format messages directly
    )

    trainer = SFTTrainer(
              model=model,
              args=cfg,
              train_dataset=ds,
              processing_class=tok,
    )

    print("[hf_train_polly] starting training")
    trainer.train()

    print(f"[hf_train_polly] saving adapter to {output_dir}")
    trainer.save_model(str(output_dir))
    tok.save_pretrained(str(output_dir))

    if args.push:
              print(f"[hf_train_polly] pushing to hub: {args.output_repo}")
              trainer.push_to_hub()

    print("[hf_train_polly] done")
    return 0


if __name__ == "__main__":
      raise SystemExit(main())
