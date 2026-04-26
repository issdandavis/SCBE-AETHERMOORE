"""Polly QLoRA v2 — Optimized for GTX 1660 Ti 6GB.

Fixes from v1: OOM at step 206 due to batch_size=4 + fp32 optimizer.
Changes: batch=1, paged_adamw_8bit, fp16, max_length=512, 3 full epochs.
"""
from __future__ import annotations
import gc
import os
import json
from pathlib import Path
from datetime import datetime

import torch
from datasets import load_dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import SFTConfig, SFTTrainer

# Config
BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
LOCAL_DATASET = str(Path(__file__).resolve().parents[1] / "training-data" / "sft" / "polly_combined_sft.jsonl")
RUN_NAME = f"polly-v2-{datetime.now().strftime('%H%M')}"
OUTPUT_DIR = f"artifacts/training/{RUN_NAME}"

def main():
    # Clear any stale CUDA state
    torch.cuda.empty_cache()
    gc.collect()

    props = torch.cuda.get_device_properties(0)
    free, total = torch.cuda.mem_get_info()
    print(f"GPU: {props.name}, VRAM: {total/1e9:.1f}GB, Free: {free/1e9:.1f}GB")

    # Load data
    dataset = load_dataset("json", data_files=LOCAL_DATASET, split="train")
    print(f"Dataset: {len(dataset)} records")

    # Split 95/5
    split = dataset.train_test_split(test_size=0.05, seed=42)
    print(f"Train: {len(split['train'])}, Eval: {len(split['test'])}")

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, use_fast=True)
    if not tokenizer.pad_token:
        tokenizer.pad_token = tokenizer.eos_token

    # 4-bit NF4 — fp16 compute (not bf16, Turing doesn't support it well)
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        ),
        dtype=torch.float16,
        device_map="auto",
    )
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    model = get_peft_model(model, LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05, bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],
    ))
    model.print_trainable_parameters()

    free2, _ = torch.cuda.mem_get_info()
    print(f"After model load — Free VRAM: {free2/1e9:.1f}GB (model uses {(free-free2)/1e9:.1f}GB)")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=split["train"],
        eval_dataset=split["test"],
        args=SFTConfig(
            output_dir=OUTPUT_DIR,
            num_train_epochs=3,
            # === VRAM-safe settings ===
            per_device_train_batch_size=1,       # was 4 — caused OOM
            per_device_eval_batch_size=1,
            gradient_accumulation_steps=8,        # effective batch = 8
            optim="paged_adamw_8bit",             # was adamw_torch (fp32) — saves ~50% optimizer mem
            fp16=False,                           # AMP broken on Python 3.14 torch (BFloat16 grad scaler bug)
            bf16=False,
            dataloader_pin_memory=False,
            # === Training params ===
            learning_rate=2e-4,
            weight_decay=0.01,
            warmup_ratio=0.05,
            lr_scheduler_type="cosine",
            max_grad_norm=0.3,
            # === Sequence ===
            max_length=384,                       # reduced from 512 — fp32 activations need more VRAM
            packing=True,
            # === Logging & saving ===
            logging_steps=10,
            eval_strategy="steps",
            eval_steps=100,
            save_strategy="epoch",
            save_total_limit=3,
            report_to="none",
            # === Memory ===
            gradient_checkpointing=True,
            gradient_checkpointing_kwargs={"use_reentrant": False},
        ),
    )

    print(f"\nStarting training: {RUN_NAME}")
    print(f"Output: {OUTPUT_DIR}")
    trainer.train()
    print("Training complete!")

    # Save final
    final_dir = os.path.join(OUTPUT_DIR, "final")
    trainer.save_model(final_dir)
    tokenizer.save_pretrained(final_dir)
    print(f"Model saved to {final_dir}")

    # Log final metrics
    logs = trainer.state.log_history
    train_logs = [l for l in logs if "loss" in l and "eval_loss" not in l]
    eval_logs = [l for l in logs if "eval_loss" in l]
    print(f"\n{'='*60}")
    print(f"TRAINING COMPLETE — {RUN_NAME}")
    print(f"{'='*60}")
    print(f"Steps: {trainer.state.global_step}")
    print(f"Final train loss: {train_logs[-1]['loss']:.4f}" if train_logs else "No train logs")
    print(f"Final eval loss: {eval_logs[-1]['eval_loss']:.4f}" if eval_logs else "No eval logs")
    if train_logs and "mean_token_accuracy" in train_logs[-1]:
        print(f"Final token accuracy: {train_logs[-1]['mean_token_accuracy']:.4f}")
    print(f"{'='*60}")

    # Save metrics to JSON
    with open(os.path.join(OUTPUT_DIR, "metrics.json"), "w") as f:
        json.dump({"train": train_logs, "eval": eval_logs}, f, indent=2)


if __name__ == "__main__":
    main()
