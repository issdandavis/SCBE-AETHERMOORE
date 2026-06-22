# %% [code]
# %% [code]
#!/usr/bin/env python3
"""Train Polly on Kaggle Free GPU
==================================

Fine-tunes Qwen2.5-3B-Instruct on 116K SCBE SFT pairs using QLoRA.
Works on both P100 (compute 6.0) and T4 (compute 7.5).

Data loading priority:
  1. HuggingFace dataset (issdandavis/scbe-aethermoore-training-data)
  2. Kaggle dataset input (/kaggle/input/scbe-polly-training-data/)
  3. Local fallback (training-data/sft/polly_combined_sft.jsonl)
"""

import subprocess
import sys

subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q",
     "transformers>=4.49", "peft>=0.14", "trl>=0.19",
     "bitsandbytes>=0.45", "accelerate>=1.3", "datasets>=3.3",
     "huggingface_hub>=0.28"],
    check=True,
)

import json
import os
from pathlib import Path

import torch
from datasets import Dataset, load_dataset
from huggingface_hub import login
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import SFTConfig, SFTTrainer

# ============================================================
# Authenticate HF early (before model download)
# ============================================================
hf_token = os.environ.get("HF_TOKEN", "")
if not hf_token:
    try:
        from kaggle_secrets import UserSecretsClient
        hf_token = UserSecretsClient().get_secret("HF_TOKEN")
    except Exception:
        pass

if hf_token:
    login(token=hf_token)
    print("HuggingFace authenticated")
else:
    print("WARNING: No HF_TOKEN found. Model will be saved locally only.")

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
# Detect GPU capability
# ============================================================
if torch.cuda.is_available():
    gpu_name = torch.cuda.get_device_name(0)
    gpu_count = torch.cuda.device_count()
    cc_major, cc_minor = torch.cuda.get_device_capability(0)
    compute_cap = cc_major + cc_minor / 10
    print(f"GPU: {gpu_name} x {gpu_count} (compute {cc_major}.{cc_minor})")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
else:
    raise RuntimeError("No CUDA GPU available")

# bitsandbytes requires compute >= 7.0 (Volta+)
# P100 is compute 6.0 -- skip quantization entirely, load fp16
USE_4BIT = compute_cap >= 7.0
USE_QUANT = compute_cap >= 7.0  # bitsandbytes segfaults on P100
if USE_4BIT:
    print("Using 4-bit NF4 quantization (compute >= 7.0)")
elif USE_QUANT:
    print("Using 8-bit quantization")
else:
    print(f"Compute {compute_cap} < 7.0 -- loading fp16 without quantization (bitsandbytes incompatible)")

# ============================================================
# Load data
# ============================================================
print("Loading training data...")

dataset = None

# Strategy 1: HuggingFace dataset
try:
    dataset = load_dataset(
        "issdandavis/scbe-aethermoore-training-data",
        data_files="polly_training_merged.jsonl",
        split="train",
    )
    print(f"Loaded {len(dataset):,} rows from HuggingFace")
except Exception as e:
    print(f"HF load failed: {e}")

# Strategy 2: Kaggle input directory
if dataset is None:
    kaggle_path = Path("/kaggle/input/scbe-polly-training-data/polly_training_merged.jsonl")
    if kaggle_path.exists():
        dataset = load_dataset("json", data_files=str(kaggle_path), split="train")
        print(f"Loaded {len(dataset):,} rows from Kaggle input")

# Strategy 3: Local fallback
if dataset is None:
    local_paths = [
        Path("training-data/polly_training_merged.jsonl"),
        Path("training-data/sft/polly_combined_sft.jsonl"),
    ]
    for p in local_paths:
        if p.exists():
            dataset = load_dataset("json", data_files=str(p), split="train")
            print(f"Loaded {len(dataset):,} rows from {p}")
            break

if dataset is None:
    raise FileNotFoundError("No training data found. Upload polly_training_merged.jsonl as a Kaggle dataset.")

if "messages" not in dataset.column_names:
    raise ValueError(f"Dataset missing 'messages' column. Found: {dataset.column_names}")

print(f"Training on {len(dataset):,} records")

# ============================================================
# Load model with quantization
# ============================================================
print(f"Loading {BASE_MODEL}...")

tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, use_fast=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

if USE_4BIT:
    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=quant_config,
        torch_dtype=torch.float16,
        device_map="auto",
    )
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
elif USE_QUANT:
    quant_config = BitsAndBytesConfig(load_in_8bit=True)
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=quant_config,
        torch_dtype=torch.float16,
        device_map="auto",
    )
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
else:
    # P100 path: no bitsandbytes, pure fp16 (3B model = ~6GB, fits in 16GB)
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float16,
        device_map="auto",
    )
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()

model = get_peft_model(model, LoraConfig(
    r=LORA_R,
    lora_alpha=LORA_ALPHA,
    lora_dropout=LORA_DROPOUT,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                     "gate_proj", "up_proj", "down_proj"],
))
=False,z=False, #(c)zzmodel.print_trainable_parameters()
.p()

# ============================================================
# Train
# ============================================================
effective_batch = BATCH_SIZE * GRADIENT_ACCUMULATION
print(f"Starting training: {EPOCHS} epochs, batch={BATCH_SIZE}x{GRADIENT_ACCUMULATION}={effective_batch}")
print(f"GPU: {gpu_name} x {gpu_count}")

# Adjust batch size and optimizer for GPU capability
if USE_QUANT:
    # T4+: can use paged_adamw_8bit (bitsandbytes)
    OPTIM = "paged_adamw_8bit"
else:
    # P100: no bitsandbytes, use standard adamw, reduce batch for fp16 full model
    OPTIM = "adamw_torch"
    BATCH_SIZE = 2
    GRADIENT_ACCUMULATION = 8
    print(f"P100 mode: batch={BATCH_SIZE}x{GRADIENT_ACCUMULATION}, optim={OPTIM}")

trainer = SFTTrainer(
    model=model,
    processing_class=tokenizer,
    train_dataset=dataset,
    args=SFTConfig(
        output_dir=OUTPUT_DIR,
        num_train_epochs=EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION,
        learning_rate=LEARNING_RATE,
        weight_decay=0.01,
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        logging_steps=25,
        save_strategy="steps",
        save_steps=500,
        max_length=MAX_SEQ_LENGTH,
        fp16=True,
        bf16=False,
        optim=OPTIM,
        gradient_checkpointing=True,
        max_grad_norm=0.3,
        report_to="none",
    ),
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
if hf_token:
    print(f"Pushing to HuggingFace: {HF_REPO}")
    model.push_to_hub(HF_REPO)
    tokenizer.push_to_hub(HF_REPO)
    print("Pushed successfully!")
else:
    print("No HF_TOKEN found. Model saved locally only.")
    print(f"To push later: huggingface-cli upload {HF_REPO} {OUTPUT_DIR}")

print("\n" + "=" * 60)f
print("  POLLY TRAINING COMPLETE")
print("=" * 60)
print(f"  Records trained: {len(dataset):,}")
print(f"  Epochs: {EPOCHS}")
print(f"  Model: {BASE_MODEL} + LoRA r={LORA_R}")
print(f"  Quantization: {'4-bit NF4' if USE_4BIT else '8-bit' if USE_QUANT else 'none (fp16)'}")
print(f"  Adapter saved: {OUTPUT_DIR}")
print(f"  HF repo: {HF_REPO}")
print("=" * 60)
