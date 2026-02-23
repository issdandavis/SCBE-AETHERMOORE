#!/usr/bin/env python3
"""
Fine-tune Qwen2.5-Coder-1.5B-Instruct on SCBE-AETHERMOORE training data.

Designed to run on Google Colab free tier (T4 GPU, 15GB VRAM).
Uses QLoRA 4-bit quantization via Unsloth for memory efficiency.

Usage (Colab cell):
    !pip install unsloth[colab-new] datasets trl peft accelerate bitsandbytes
    !python scripts/fine_tune_scbe.py

Usage (local with --dry-run for testing):
    python scripts/fine_tune_scbe.py --dry-run

The script:
  1. Loads sft_combined_chat.jsonl (chat format)
  2. Splits into train/eval (holds out ~5% for validation)
  3. Applies QLoRA 4-bit to Qwen2.5-Coder-1.5B-Instruct
  4. Trains with SFTTrainer (TRL)
  5. Pushes adapter + merged model to HuggingFace

Author: Issac Davis
Date: 2026-02-22
Part of SCBE-AETHERMOORE (USPTO #63/961,403)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Auto-load .env from project root so HF_TOKEN is available
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_MODEL = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
OUTPUT_REPO = "issdandavis/scbe-aethermoore-coder-1.5b"
ADAPTER_DIR = "scbe-adapter"
MERGED_DIR = "scbe-merged"

# QLoRA config
LORA_R = 16
LORA_ALPHA = 16
LORA_DROPOUT = 0.0

# Training config
MAX_SEQ_LENGTH = 2048
BATCH_SIZE = 2
GRAD_ACCUM_STEPS = 4  # effective batch = 8
LEARNING_RATE = 2e-4
NUM_EPOCHS = 3
MAX_STEPS = -1  # -1 = use epochs; set to 500 for quick test
WARMUP_RATIO = 0.05
EVAL_STEPS = 50
SAVE_STEPS = 100
LOGGING_STEPS = 10
WEIGHT_DECAY = 0.01

TRAINING_DATA_DIR = Path(__file__).resolve().parent.parent / "training-data"
CHAT_DATA_FILE = TRAINING_DATA_DIR / "sft_combined_chat.jsonl"
EVAL_HOLDOUT_FILE = TRAINING_DATA_DIR / "evals" / "model_eval_holdout.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fine-tune SCBE model with QLoRA")
    parser.add_argument("--dry-run", action="store_true", help="Validate data and config without training")
    parser.add_argument("--max-steps", type=int, default=MAX_STEPS, help="Override max training steps (-1 for epochs)")
    parser.add_argument("--push", action="store_true", help="Push to HuggingFace after training")
    parser.add_argument("--repo-id", default=OUTPUT_REPO, help="HF model repo ID")
    parser.add_argument("--data-file", default=str(CHAT_DATA_FILE), help="Path to chat-format JSONL")
    parser.add_argument("--eval-split", type=float, default=0.05, help="Fraction of data for eval (default: 0.05)")
    parser.add_argument("--resume", default=None, help="Resume from checkpoint directory")
    return parser.parse_args()


def load_chat_data(path: str) -> list[dict]:
    """Load chat-format JSONL and validate structure."""
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                print(f"  WARN: Bad JSON at line {i+1}, skipping", file=sys.stderr)
                continue

            messages = record.get("messages", [])
            if not messages or len(messages) < 2:
                continue

            # Validate message structure
            roles = [m.get("role") for m in messages]
            if "user" not in roles or "assistant" not in roles:
                continue

            # Filter very short responses (< 50 chars)
            assistant_msgs = [m for m in messages if m["role"] == "assistant"]
            if any(len(m.get("content", "")) < 50 for m in assistant_msgs):
                continue

            records.append(record)

    return records


def format_for_training(record: dict) -> str:
    """Format a chat record into the Qwen chat template string."""
    parts = []
    for msg in record["messages"]:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            parts.append(f"<|im_start|>system\n{content}<|im_end|>")
        elif role == "user":
            parts.append(f"<|im_start|>user\n{content}<|im_end|>")
        elif role == "assistant":
            parts.append(f"<|im_start|>assistant\n{content}<|im_end|>")
    return "\n".join(parts)


def main() -> None:
    args = parse_args()

    print("=" * 60)
    print("SCBE-AETHERMOORE QLoRA Fine-Tuning")
    print(f"  Base model:  {BASE_MODEL}")
    print(f"  Output repo: {args.repo_id}")
    print(f"  Data file:   {args.data_file}")
    print("=" * 60)

    # ---- Step 1: Load and validate data ----
    print("\n[1/5] Loading training data...")
    data_path = Path(args.data_file)
    if not data_path.exists():
        print(f"ERROR: Data file not found: {data_path}", file=sys.stderr)
        print("Run `python scripts/daily_training_wave.py` first to generate training data.", file=sys.stderr)
        sys.exit(1)

    records = load_chat_data(str(data_path))
    print(f"  Loaded {len(records)} valid chat records")

    if len(records) < 10:
        print("ERROR: Too few training records. Need at least 10.", file=sys.stderr)
        sys.exit(1)

    # Split into train/eval
    eval_size = max(10, int(len(records) * args.eval_split))
    eval_records = records[:eval_size]
    train_records = records[eval_size:]
    print(f"  Train: {len(train_records)} | Eval: {len(eval_records)}")

    # Format into text
    train_texts = [format_for_training(r) for r in train_records]
    eval_texts = [format_for_training(r) for r in eval_records]

    # Stats
    avg_len = sum(len(t) for t in train_texts) // max(len(train_texts), 1)
    print(f"  Avg training text length: {avg_len} chars")

    if args.dry_run:
        print("\n[DRY RUN] Data validation passed. Exiting without training.")
        print(f"  Would train on {len(train_records)} records")
        print(f"  Would evaluate on {len(eval_records)} records")

        # Show sample
        if train_texts:
            sample = train_texts[0][:500]
            print(f"\n  Sample (first 500 chars):\n  {sample}...")
        return

    # ---- Step 2: Setup model with QLoRA ----
    print("\n[2/5] Loading model with QLoRA 4-bit quantization...")

    try:
        from unsloth import FastLanguageModel
    except ImportError:
        print("ERROR: unsloth not installed.", file=sys.stderr)
        print("Install with: pip install unsloth[colab-new]", file=sys.stderr)
        sys.exit(1)

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=BASE_MODEL,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=None,  # auto-detect
        load_in_4bit=True,
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=LORA_R,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"  Trainable: {trainable_params:,} / {total_params:,} ({100*trainable_params/total_params:.2f}%)")

    # ---- Step 3: Prepare datasets ----
    print("\n[3/5] Preparing datasets...")

    from datasets import Dataset

    train_dataset = Dataset.from_dict({"text": train_texts})
    eval_dataset = Dataset.from_dict({"text": eval_texts})

    print(f"  Train dataset: {len(train_dataset)} examples")
    print(f"  Eval dataset:  {len(eval_dataset)} examples")

    # ---- Step 4: Train ----
    print("\n[4/5] Starting training...")

    from trl import SFTTrainer
    from transformers import TrainingArguments

    training_args = TrainingArguments(
        output_dir=ADAPTER_DIR,
        num_train_epochs=NUM_EPOCHS,
        max_steps=args.max_steps,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRAD_ACCUM_STEPS,
        learning_rate=LEARNING_RATE,
        warmup_ratio=WARMUP_RATIO,
        weight_decay=WEIGHT_DECAY,
        logging_steps=LOGGING_STEPS,
        eval_strategy="steps",
        eval_steps=EVAL_STEPS,
        save_steps=SAVE_STEPS,
        save_total_limit=3,
        fp16=True,
        optim="adamw_8bit",
        lr_scheduler_type="cosine",
        seed=42,
        report_to="none",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        args=training_args,
        max_seq_length=MAX_SEQ_LENGTH,
    )

    if args.resume:
        print(f"  Resuming from checkpoint: {args.resume}")
        trainer.train(resume_from_checkpoint=args.resume)
    else:
        trainer.train()

    # Final eval
    eval_results = trainer.evaluate()
    print(f"\n  Final eval loss: {eval_results.get('eval_loss', 'N/A')}")

    # Save adapter
    model.save_pretrained(ADAPTER_DIR)
    tokenizer.save_pretrained(ADAPTER_DIR)
    print(f"  Adapter saved to: {ADAPTER_DIR}/")

    # ---- Step 5: Merge and optionally push ----
    print("\n[5/5] Merging adapter into base model...")

    model.save_pretrained_merged(
        MERGED_DIR,
        tokenizer,
        save_method="merged_16bit",
    )
    print(f"  Merged model saved to: {MERGED_DIR}/")

    if args.push:
        print(f"\n  Pushing to HuggingFace: {args.repo_id}")

        # Push adapter
        model.push_to_hub(args.repo_id + "-adapter", token=os.environ.get("HF_TOKEN"))
        tokenizer.push_to_hub(args.repo_id + "-adapter", token=os.environ.get("HF_TOKEN"))

        # Push merged model
        model.push_to_hub_merged(
            args.repo_id,
            tokenizer,
            save_method="merged_16bit",
            token=os.environ.get("HF_TOKEN"),
        )

        print(f"  Pushed to: https://huggingface.co/{args.repo_id}")
    else:
        print("  Skipping push (use --push to upload to HuggingFace)")

    print("\n" + "=" * 60)
    print("Training complete!")
    print(f"  Adapter:  {ADAPTER_DIR}/")
    print(f"  Merged:   {MERGED_DIR}/")
    print(f"  Eval loss: {eval_results.get('eval_loss', 'N/A')}")
    print("=" * 60)


if __name__ == "__main__":
    main()
