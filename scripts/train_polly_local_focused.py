# /// script
# dependencies = [
#   "datasets>=3.3.2",
#   "transformers>=4.49.0",
#   "trl>=0.19.1",
#   "peft>=0.14.0",
#   "accelerate>=1.3.0",
# ]
# ///

"""Polly FOCUSED SFT — QLoRA on GTX 1660 Ti (6GB VRAM, Compute 7.5).

Trains on a curated subset of task-specific datasets (governance, sacred eggs,
code patterns, architecture, attention, API, self-correction) while the full
3B model trains on Kaggle.

Runs in fp32 (no AMP) to avoid BF16 grad scaler bugs on Turing GPUs.
Uses 4-bit NF4 base model with LoRA r=16 for VRAM efficiency.
"""

from __future__ import annotations

import os
from pathlib import Path

import torch
from datasets import Dataset, load_dataset
from huggingface_hub import login
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import SFTConfig, SFTTrainer


BASE_MODEL = os.getenv("POLLY_BASE_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
TARGET_MODEL = os.getenv("POLLY_TARGET_MODEL", "issdandavis/polly-focused-qwen-0.5b")
OUTPUT_DIR = os.getenv("POLLY_OUTPUT_DIR", "artifacts/training/polly-focused-0.5b")
PUSH_TO_HUB = os.getenv("POLLY_PUSH_TO_HUB", "0") == "1"

SFT_DIR = Path(__file__).resolve().parents[1] / "training-data" / "sft"

FOCUSED_DATASETS = [
    "governance_deep_v2.jsonl",
    "sacred_eggs_triplets_sft.jsonl",
    "code_brushes_sft.jsonl",
    "code_substrate_l0_sft.jsonl",
    "architecture_explainer_v1.jsonl",
    "attention_residuals_sft.jsonl",
    "api_usage_pairs.jsonl",
    "autocorrection_behavior_sft.jsonl",
]


def load_focused_datasets() -> Dataset:
    """Load and combine all focused JSONL datasets, skipping empty/missing files."""
    all_records: list[dict] = []
    composition: dict[str, int] = {}

    for name in FOCUSED_DATASETS:
        path = SFT_DIR / name
        if not path.exists():
            print(f"  SKIP  {name} (file not found)")
            composition[name] = 0
            continue

        # Check file is non-empty (more than just whitespace/newlines)
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            print(f"  SKIP  {name} (empty file)")
            composition[name] = 0
            continue

        try:
            ds = load_dataset("json", data_files=str(path), split="train")
        except Exception as e:
            print(f"  SKIP  {name} (load error: {e})")
            composition[name] = 0
            continue

        count = len(ds)
        if count == 0:
            print(f"  SKIP  {name} (0 records)")
            composition[name] = 0
            continue

        print(f"  LOAD  {name}: {count} records")
        composition[name] = count
        # Convert instruction/response or instruction/output to messages format
        for row in ds:
            user_text = row.get("instruction", "")
            assistant_text = row.get("response") or row.get("output", "")
            if user_text and assistant_text:
                all_records.append({
                    "messages": [
                        {"role": "user", "content": user_text},
                        {"role": "assistant", "content": assistant_text},
                    ]
                })

    # Print composition summary
    print("\n" + "=" * 60)
    print("DATASET COMPOSITION SUMMARY")
    print("=" * 60)
    total = 0
    for name, count in composition.items():
        status = f"{count:>6d} records" if count > 0 else "  SKIPPED"
        print(f"  {name:<45s} {status}")
        total += count
    print("-" * 60)
    print(f"  {'TOTAL':<45s} {total:>6d} records")
    print("=" * 60 + "\n")

    if total == 0:
        raise RuntimeError("No training records found. Check training-data/sft/ directory.")

    return Dataset.from_list(all_records)


def main() -> None:
    hf_token = os.environ.get("HF_TOKEN", "")
    if hf_token:
        login(token=hf_token)
        print("Authenticated with HuggingFace")

    print("Loading focused training datasets from:", SFT_DIR)
    print()

    dataset = load_focused_datasets()

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, use_fast=True)

    # 4-bit NF4 quantization. GTX 1660 Ti (Turing) has no bf16 — use fp32 compute.
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float32,
            bnb_4bit_use_double_quant=True,
        ),
        torch_dtype=torch.float32,
        device_map="auto",
    )

    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)

    model = get_peft_model(model, LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    ))
    model.print_trainable_parameters()

    # No peft_config — LoRA already applied. No fp16 — avoids BF16 AMP bug on Turing.
    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=dataset,
        args=SFTConfig(
            output_dir=OUTPUT_DIR,
            hub_model_id=TARGET_MODEL,
            push_to_hub=PUSH_TO_HUB,
            learning_rate=2e-4,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=8,
            num_train_epochs=3,
            warmup_ratio=0.05,
            logging_steps=10,
            save_strategy="epoch",
            max_length=512,
            report_to="none",
            fp16=False,
            bf16=False,
            optim="adamw_torch",
            gradient_checkpointing=True,
        ),
    )

    trainer.train()
    trainer.save_model()
    print(f"\nModel saved to {OUTPUT_DIR}")

    if PUSH_TO_HUB:
        trainer.push_to_hub()
        print(f"Pushed to {TARGET_MODEL}")


if __name__ == "__main__":
    main()
