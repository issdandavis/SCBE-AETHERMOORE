#!/usr/bin/env python3
"""
SmolLM2-360M SCBE Assistant — Kaggle/Colab Training Script
============================================================
Fine-tunes SmolLM2-360M-Instruct into an SCBE-aware assistant.
Designed for Kaggle (free T4 16GB) or Colab.

Upload this script + your SCBE training data to Kaggle as a dataset,
then run in a notebook with GPU T4 accelerator.

Usage (Kaggle notebook cell):
    !pip install transformers trl peft bitsandbytes datasets accelerate
    %run train_smollm2_kaggle.py

Usage (local):
    python scripts/train_smollm2_kaggle.py --local
    python scripts/train_smollm2_kaggle.py --local --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("smollm2_train")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL_ID = "HuggingFaceTB/SmolLM2-360M-Instruct"
MODEL_NAME = "scbe-twin-360m"  # One of Izack's twins

# Detect environment
IS_KAGGLE = os.path.exists("/kaggle/input")
IS_COLAB = os.path.exists("/content")

if IS_KAGGLE:
    DATA_ROOT = Path("/kaggle/input/scbe-training-data")
    OUTPUT_DIR = Path("/kaggle/working") / MODEL_NAME
elif IS_COLAB:
    DATA_ROOT = Path("/content/drive/MyDrive/scbe-training-data")
    OUTPUT_DIR = Path("/content") / MODEL_NAME
else:
    DATA_ROOT = Path(__file__).resolve().parent.parent / "training-data" / "sft"
    OUTPUT_DIR = Path(__file__).resolve().parent.parent / "training-runs" / MODEL_NAME

# SCBE training files — upload these to your Kaggle dataset
TRAINING_FILES = [
    "phase0_baby_babble_sft.jsonl",
    "kids_group_physics_sft.jsonl",
    "baby_babble_phase0.jsonl",
    "kids_math_games_sft.jsonl",
    "tongue_primer_sft.jsonl",
    "book_six_tongues_sft.jsonl",
    "tongue_curriculum_v2.jsonl",
]

# QLoRA config
LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
LORA_TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]

# Training config
EPOCHS = 3
BATCH_SIZE = 4
GRAD_ACCUM = 4
LR = 2e-4
MAX_SEQ_LEN = 512
WARMUP_RATIO = 0.05
WEIGHT_DECAY = 0.01

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_training_data(data_root: Path, max_records: int = 0) -> list[dict]:
    """Load messages-format JSONL files."""
    records = []
    for fname in TRAINING_FILES:
        fpath = data_root / fname
        if not fpath.exists():
            log.warning(f"  Skipping {fname} (not found at {fpath})")
            continue
        log.info(f"  Loading {fname}...")
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                msgs = obj.get("messages", [])
                if not msgs:
                    continue
                records.append({"messages": msgs})
        log.info(f"    -> {len(records)} records so far")

    if max_records > 0:
        records = records[:max_records]
    log.info(f"  Total: {len(records)} records")
    return records


def format_for_sft(record: dict, tokenizer) -> str:
    """Format a messages record into a single string using the chat template."""
    return tokenizer.apply_chat_template(record["messages"], tokenize=False, add_generation_prompt=False)

# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train(dry_run: bool = False, max_records: int = 0):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from trl import SFTConfig, SFTTrainer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    log.info(f"Device: {device}")
    if device == "cuda":
        log.info(f"GPU: {torch.cuda.get_device_name(0)}")
        log.info(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

    # Load data
    log.info("Loading SCBE training data...")
    records = load_training_data(DATA_ROOT, max_records)
    if not records:
        log.error("No training data found! Upload JSONL files to your dataset.")
        sys.exit(1)

    # Split train/eval
    eval_size = min(500, len(records) // 20)
    train_records = records[:-eval_size] if eval_size > 0 else records
    eval_records = records[-eval_size:] if eval_size > 0 else []

    log.info(f"Train: {len(train_records)}, Eval: {len(eval_records)}")

    if dry_run:
        log.info("DRY RUN — would train on %d records for %d epochs", len(train_records), EPOCHS)
        return

    # Load tokenizer
    log.info(f"Loading tokenizer: {MODEL_ID}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Quantization config
    use_4bit = device == "cuda"
    if use_4bit:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
            bnb_4bit_use_double_quant=True,
        )
    else:
        bnb_config = None

    # Load model
    log.info(f"Loading model: {MODEL_ID}")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=bnb_config,
        device_map="auto" if device == "cuda" else None,
        trust_remote_code=True,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
    )

    if use_4bit:
        model = prepare_model_for_kbit_training(model)

    # LoRA config
    lora_config = LoraConfig(
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        target_modules=LORA_TARGETS,
        bias="none",
        task_type="CAUSAL_LM",
    )

    model = get_peft_model(model, lora_config)
    trainable, total = model.get_nb_trainable_parameters()
    log.info(f"Trainable: {trainable:,} / {total:,} ({100*trainable/total:.2f}%)")

    # Format data
    from datasets import Dataset

    def format_record(example):
        text = tokenizer.apply_chat_template(example["messages"], tokenize=False, add_generation_prompt=False)
        return {"text": text}

    train_ds = Dataset.from_list(train_records).map(format_record, remove_columns=["messages"])
    eval_ds = Dataset.from_list(eval_records).map(format_record, remove_columns=["messages"]) if eval_records else None

    # Training args
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    training_args = SFTConfig(
        output_dir=str(OUTPUT_DIR),
        num_train_epochs=EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRAD_ACCUM,
        learning_rate=LR,
        lr_scheduler_type="cosine",
        warmup_ratio=WARMUP_RATIO,
        weight_decay=WEIGHT_DECAY,
        max_seq_length=MAX_SEQ_LEN,
        logging_steps=25,
        save_steps=500,
        eval_strategy="steps" if eval_ds else "no",
        eval_steps=500 if eval_ds else None,
        save_total_limit=3,
        bf16=torch.cuda.is_bf16_supported() if device == "cuda" else False,
        fp16=not torch.cuda.is_bf16_supported() if device == "cuda" else False,
        optim="paged_adamw_8bit" if device == "cuda" else "adamw_torch",
        report_to="none",
        dataset_text_field="text",
        packing=True,
        seed=137,
    )

    # Train
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        processing_class=tokenizer,
    )

    log.info("Starting training...")
    t0 = time.time()
    trainer.train()
    elapsed = time.time() - t0
    log.info(f"Training complete in {elapsed/60:.1f} minutes")

    # Save
    final_dir = OUTPUT_DIR / "final_adapter"
    trainer.save_model(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))
    log.info(f"Adapter saved to: {final_dir}")

    # Quick eval
    log.info("Running quick generation test...")
    model.eval()
    test_prompts = [
        "What are the Sacred Tongues?",
        "Explain the harmonic wall formula.",
        "Who is Polly?",
        "What is the difference between ALLOW and QUARANTINE?",
        "Say something in Kor'aelin.",
    ]
    for prompt in test_prompts:
        msgs = [{"role": "user", "content": prompt}]
        input_text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(input_text, return_tensors="pt").to(model.device)
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=100, temperature=0.7, do_sample=True)
        response = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        log.info(f"\n  Q: {prompt}\n  A: {response[:200]}")

    # Push to HF if token available
    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if hf_token:
        repo_id = f"issdandavis/{MODEL_NAME}"
        log.info(f"Pushing to HuggingFace: {repo_id}")
        try:
            model.push_to_hub(repo_id, token=hf_token)
            tokenizer.push_to_hub(repo_id, token=hf_token)
            log.info(f"Pushed successfully to {repo_id}")
        except Exception as e:
            log.warning(f"HF push failed: {e}")
    else:
        log.info("No HF_TOKEN found — skipping push. Set HF_TOKEN to auto-push.")

    log.info("Done! Your SCBE twin is ready.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train SmolLM2-360M SCBE Assistant")
    parser.add_argument("--dry-run", action="store_true", help="Load data only, don't train")
    parser.add_argument("--local", action="store_true", help="Force local paths")
    parser.add_argument("--max-records", type=int, default=0, help="Limit records (0=all)")
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    args = parser.parse_args()

    if args.local:
        DATA_ROOT = Path(__file__).resolve().parent.parent / "training-data" / "sft"
        OUTPUT_DIR = Path(__file__).resolve().parent.parent / "training-runs" / MODEL_NAME

    if args.epochs != EPOCHS:
        EPOCHS = args.epochs

    train(dry_run=args.dry_run, max_records=args.max_records)
