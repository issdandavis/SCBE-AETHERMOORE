#!/usr/bin/env python3
"""Train Polly Chatbot on Kaggle Free GPU
==========================================

Fine-tunes Qwen2.5-3B-Instruct on 92K SCBE SFT pairs using QLoRA.
Designed to run on Kaggle's free T4/P100 GPU (16GB VRAM).

Usage on Kaggle:
  1. Create new notebook
  2. Add dataset: issacizrealdavis/scbe-polly-training-data
  3. Enable GPU accelerator (T4 x2 or P100)
  4. Paste this script and run

Output:
  - LoRA adapter saved to /kaggle/working/polly-lora-adapter/
  - Push to HuggingFace: issdandavis/scbe-polly-chat-v1
"""

# Install dependencies (Kaggle may need these)
import subprocess
subprocess.run(["pip", "install", "-q", "transformers>=4.44", "peft>=0.12",
                "trl>=0.9", "bitsandbytes>=0.43", "accelerate>=0.33",
                "datasets", "huggingface_hub"], check=True)

import json
import os
from pathlib import Path

import torch
from datasets import Dataset
from huggingface_hub import login
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from trl import SFTTrainer

# ============================================================
# Config
# ============================================================
BASE_MODEL = "Qwen/Qwen2.5-3B-Instruct"
OUTPUT_DIR = "/kaggle/working/polly-lora-adapter"
HF_REPO = "issdandavis/scbe-polly-chat-v1"
MAX_SEQ_LENGTH = 1024
EPOCHS = 2
BATCH_SIZE = 4
GRADIENT_ACCUMULATION = 4
LEARNING_RATE = 2e-4
LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05

# ============================================================
# Load data
# ============================================================
print("Loading training data...")

# Try HuggingFace dataset first, then Kaggle input, then local fallback
data_path = None
try:
    from datasets import load_dataset as _ld
    hf_ds = _ld("issdandavis/scbe-aethermoore-training-data",
                data_files="polly_training_merged.jsonl", split="train")
    print(f"Loaded {len(hf_ds):,} rows from HuggingFace")
    USE_HF_DIRECT = True
except Exception:
    USE_HF_DIRECT = False
    data_path = Path("/kaggle/input/scbe-polly-training-data/polly_training_merged.jsonl")
    if not data_path.exists():
        data_path = Path("training-data/polly_training_merged.jsonl")

records = []

if USE_HF_DIRECT:
    # Already loaded from HuggingFace
    for row in hf_ds:
        rec = json.loads(row["text"]) if isinstance(row.get("text"), str) else row
        msgs = rec.get("messages", [])
        text_parts = []
        for m in msgs:
            role = m.get("role", "")
            content = m.get("content", "")
            if role == "system":
                text_parts.append(f"<|im_start|>system\n{content}<|im_end|>")
            elif role == "user":
                text_parts.append(f"<|im_start|>user\n{content}<|im_end|>")
            elif role == "assistant":
                text_parts.append(f"<|im_start|>assistant\n{content}<|im_end|>")
        if text_parts:
            records.append({"text": "\n".join(text_parts)})
else:
    with open(data_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                msgs = rec.get("messages", [])
                # Build chat template string
                text_parts = []
                for m in msgs:
                    role = m.get("role", "")
                    content = m.get("content", "")
                if role == "system":
                    text_parts.append(f"<|im_start|>system\n{content}<|im_end|>")
                elif role == "user":
                    text_parts.append(f"<|im_start|>user\n{content}<|im_end|>")
                elif role == "assistant":
                    text_parts.append(f"<|im_start|>assistant\n{content}<|im_end|>")
                if text_parts:
                    records.append({"text": "\n".join(text_parts)})
            except:
                continue

print(f"Loaded {len(records):,} training records")
dataset = Dataset.from_list(records)

# Shuffle and take a reasonable subset if too large for free GPU
if len(dataset) > 50000:
    dataset = dataset.shuffle(seed=42).select(range(50000))
    print(f"Trimmed to {len(dataset):,} for free GPU constraints")

# ============================================================
# Load model with QLoRA (4-bit quantization)
# ============================================================
print(f"Loading {BASE_MODEL} with 4-bit quantization...")

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
)

model = prepare_model_for_kbit_training(model)

# ============================================================
# Configure LoRA
# ============================================================
print("Configuring LoRA adapter...")

lora_config = LoraConfig(
    r=LORA_R,
    lora_alpha=LORA_ALPHA,
    lora_dropout=LORA_DROPOUT,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                     "gate_proj", "up_proj", "down_proj"],
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

# ============================================================
# Train
# ============================================================
print(f"Starting training: {EPOCHS} epochs, batch={BATCH_SIZE}x{GRADIENT_ACCUMULATION}")

training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=EPOCHS,
    per_device_train_batch_size=BATCH_SIZE,
    gradient_accumulation_steps=GRADIENT_ACCUMULATION,
    learning_rate=LEARNING_RATE,
    weight_decay=0.01,
    warmup_ratio=0.03,
    lr_scheduler_type="cosine",
    logging_steps=25,
    save_strategy="epoch",
    bf16=torch.cuda.is_available() and torch.cuda.get_device_capability()[0] >= 8,
    fp16=torch.cuda.is_available() and torch.cuda.get_device_capability()[0] < 8,
    optim="paged_adamw_8bit",
    gradient_checkpointing=True,
    max_grad_norm=0.3,
    report_to="none",
)

trainer = SFTTrainer(
    model=model,
    args=training_args,
    train_dataset=dataset,
    tokenizer=tokenizer,
    max_seq_length=MAX_SEQ_LENGTH,
    dataset_text_field="text",
    packing=True,
)

trainer.train()

# ============================================================
# Save
# ============================================================
print("Saving LoRA adapter...")
trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

# ============================================================
# Push to HuggingFace
# ============================================================
hf_token = os.environ.get("HF_TOKEN", "")
if hf_token:
    print(f"Pushing to HuggingFace: {HF_REPO}")
    login(token=hf_token)
    model.push_to_hub(HF_REPO, use_auth_token=True)
    tokenizer.push_to_hub(HF_REPO, use_auth_token=True)
    print("Pushed successfully!")
else:
    print("No HF_TOKEN set. Model saved locally only.")
    print(f"To push later: huggingface-cli upload {HF_REPO} {OUTPUT_DIR}")

print("\n" + "=" * 60)
print("  POLLY TRAINING COMPLETE")
print("=" * 60)
print(f"  Records trained: {len(dataset):,}")
print(f"  Epochs: {EPOCHS}")
print(f"  Model: {BASE_MODEL} + LoRA")
print(f"  Adapter saved: {OUTPUT_DIR}")
print("=" * 60)
