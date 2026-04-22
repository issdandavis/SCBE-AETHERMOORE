#!/usr/bin/env python3
"""Sacred Tongues Tokenizer Training — BOTH approaches.

Approach 1 (--mode replace):
    Replace Qwen's tokenizer entirely with Sacred Tongues (1,548 vocab).
    Retrains embeddings + LM head from scratch. Pure Sacred Tongue model.

Approach 2 (--mode bridge):
    Keep Qwen's transformer frozen/LoRA'd. Learn a bridge layer that maps
    Sacred Tongue tokens into Qwen's embedding space.

Both run on GTX 1660 Ti (6GB VRAM) with QLoRA where applicable.

Usage:
    python scripts/train_polly_sacred_tongues.py --mode replace
    python scripts/train_polly_sacred_tongues.py --mode bridge
    python scripts/train_polly_sacred_tongues.py --mode both
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import torch
from torch.utils.data import DataLoader, Dataset as TorchDataset
from datasets import load_dataset
from huggingface_hub import login
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

# Add src/ to path for Sacred Tongues imports
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from tokenizer.sacred_tongues_hf import (
    SacredTonguesHFTokenizer,
    SacredTongueBridge,
    BridgedModel,
    replace_model_tokenizer,
    TOTAL_VOCAB,
)

BASE_MODEL = os.getenv("POLLY_BASE_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
SFT_DIR = REPO_ROOT / "training-data" / "sft"

# Datasets that work best with Sacred Tongues training
SACRED_DATASETS = [
    "sacred_tongues_sft.jsonl",
    "sacred_eggs_triplets_sft.jsonl",
    "governance_deep_v2.jsonl",
    "calibration_corpus_sft.jsonl",
    "null_space_confidence_triggers.jsonl",
    "biblical_null_space_probes.jsonl",
    "polly_personality_deep_sft.jsonl",
]


# ============================================================
# DATA LOADING
# ============================================================

def load_sft_texts(file_list: list[str]) -> list[str]:
    """Load SFT datasets and extract plain text for tokenizer training."""
    texts: list[str] = []

    for name in file_list:
        path = SFT_DIR / name
        if not path.exists():
            print(f"  SKIP  {name} (not found)")
            continue

        raw = path.read_text(encoding="utf-8").strip()
        if not raw or raw.startswith("version https://git-lfs"):
            print(f"  SKIP  {name} (empty or LFS pointer)")
            continue

        try:
            ds = load_dataset("json", data_files=str(path), split="train")
        except Exception as e:
            print(f"  SKIP  {name} ({e})")
            continue

        count = 0
        cols = ds.column_names
        for row in ds:
            # Extract text from various formats
            if "messages" in cols and row.get("messages"):
                for msg in row["messages"]:
                    if msg.get("content"):
                        texts.append(msg["content"])
                        count += 1
            elif "instruction" in cols:
                if row.get("instruction"):
                    texts.append(row["instruction"])
                    count += 1
                resp = row.get("response") or row.get("output") or row.get("positive", "")
                if resp:
                    texts.append(resp)
                    count += 1
            elif "prompt" in cols:
                if row.get("prompt"):
                    texts.append(row["prompt"])
                    count += 1
                resp = row.get("ideal_contains") or row.get("response", "")
                if resp:
                    texts.append(str(resp))
                    count += 1

        print(f"  LOAD  {name}: {count} texts")

    print(f"\nTotal texts: {len(texts)}")
    return texts


class SacredTongueDataset(TorchDataset):
    """Dataset that tokenizes text with Sacred Tongues tokenizer."""

    def __init__(
        self,
        texts: list[str],
        tokenizer: SacredTonguesHFTokenizer,
        max_length: int = 256,
        tongue: str = "ko",
    ):
        self.texts = texts
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.tongue = tongue
        # Cycle through tongues for multi-tongue training
        self.tongue_cycle = ["ko", "av", "ru", "ca", "um", "dr"]

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        # Rotate tongues so model sees all six
        tongue = self.tongue_cycle[idx % 6]
        ids = self.tokenizer.encode(self.texts[idx], tongue=tongue)

        # Truncate
        if len(ids) > self.max_length:
            ids = ids[: self.max_length - 1] + [self.tokenizer.eos_token_id]

        # Pad
        pad_len = self.max_length - len(ids)
        attention_mask = [1] * len(ids) + [0] * pad_len
        ids = ids + [self.tokenizer.pad_token_id] * pad_len

        # Labels = input_ids (causal LM), ignore padding
        labels = [i if m == 1 else -100 for i, m in zip(ids, attention_mask)]

        return {
            "input_ids": torch.tensor(ids, dtype=torch.long),
            "attention_mask": torch.tensor(attention_mask, dtype=torch.long),
            "labels": torch.tensor(labels, dtype=torch.long),
        }


# ============================================================
# APPROACH 1: VOCAB REPLACEMENT
# ============================================================

def train_vocab_replacement(texts: list[str]) -> None:
    """Replace Qwen tokenizer entirely with Sacred Tongues."""
    print("\n" + "=" * 70)
    print("APPROACH 1: VOCAB REPLACEMENT")
    print("Replacing Qwen's 151,936-token vocab with 1,548 Sacred Tongue tokens")
    print("=" * 70)

    output_dir = "artifacts/training/polly-sacred-replace"
    os.makedirs(output_dir, exist_ok=True)

    # Sacred Tongues tokenizer
    st_tokenizer = SacredTonguesHFTokenizer(default_tongue="ko")

    # Load base model (4-bit quantized)
    print("Loading base model...")
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

    # Replace embeddings + LM head
    print(f"Replacing vocab: {model.config.vocab_size} → {TOTAL_VOCAB}")
    model = replace_model_tokenizer(model, old_vocab_size=model.config.vocab_size)

    # Only train new embeddings + LM head (freeze transformer)
    for name, param in model.named_parameters():
        if "embed_tokens" in name or "lm_head" in name:
            param.requires_grad = True
        else:
            param.requires_grad = False

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"Trainable: {trainable:,} / {total:,} ({100*trainable/total:.2f}%)")

    # Dataset
    dataset = SacredTongueDataset(texts, st_tokenizer, max_length=256)
    loader = DataLoader(dataset, batch_size=4, shuffle=True, num_workers=0)

    # Optimizer — only for trainable params
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=5e-4,
        weight_decay=0.01,
    )

    # Training loop
    device = next(model.parameters()).device
    model.train()
    num_epochs = 3

    for epoch in range(num_epochs):
        total_loss = 0.0
        steps = 0

        for batch in loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels,
            )

            loss = outputs.loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 0.3)
            optimizer.step()
            optimizer.zero_grad()

            total_loss += loss.item()
            steps += 1

            if steps % 50 == 0:
                avg = total_loss / steps
                print(f"  Epoch {epoch+1}/{num_epochs} | Step {steps} | Loss {avg:.4f}")

        avg_loss = total_loss / max(steps, 1)
        print(f"Epoch {epoch+1} complete — Avg Loss: {avg_loss:.4f}")

    # Save
    st_tokenizer.save_pretrained(output_dir)
    torch.save(model.state_dict(), os.path.join(output_dir, "model.pt"))
    print(f"\nSaved to {output_dir}")
    print("  - tokenizer_config.json, vocab.json (Sacred Tongues tokenizer)")
    print("  - model.pt (retrained embeddings + LM head)")

    # Cleanup
    del model, optimizer
    torch.cuda.empty_cache()


# ============================================================
# APPROACH 2: BRIDGE LAYER
# ============================================================

def train_bridge(texts: list[str]) -> None:
    """Train a bridge layer: Sacred Tongues → Qwen embedding space."""
    print("\n" + "=" * 70)
    print("APPROACH 2: SACRED TONGUE BRIDGE")
    print("Learning projection: Sacred Tongue tokens → Qwen embedding space")
    print("=" * 70)

    output_dir = "artifacts/training/polly-sacred-bridge"
    os.makedirs(output_dir, exist_ok=True)

    # Sacred Tongues tokenizer
    st_tokenizer = SacredTonguesHFTokenizer(default_tongue="ko")

    # Load base model (4-bit quantized)
    print("Loading base model...")
    base_model = AutoModelForCausalLM.from_pretrained(
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

    # Get model dimension from config
    model_dim = base_model.config.hidden_size  # 896 for Qwen2.5-0.5B

    # Create bridge
    bridge = SacredTongueBridge(
        sacred_vocab_size=TOTAL_VOCAB,
        bridge_dim=256,
        model_dim=model_dim,
        dropout=0.1,
    )

    # Move bridge to same device as model
    device = next(base_model.parameters()).device
    bridge = bridge.to(device).to(torch.float32)

    # Wrap model with bridge
    bridged = BridgedModel(base_model, bridge)

    # Apply LoRA to transformer layers (bridge is fully trainable)
    base_model = prepare_model_for_kbit_training(base_model, use_gradient_checkpointing=True)
    base_model = get_peft_model(base_model, LoraConfig(
        r=8,  # Smaller r — bridge carries most adaptation load
        lora_alpha=16,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    ))

    # Count params
    bridge_params = sum(p.numel() for p in bridge.parameters())
    lora_params = sum(p.numel() for p in base_model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in bridged.parameters())
    print(f"Bridge params: {bridge_params:,}")
    print(f"LoRA params:   {lora_params:,}")
    print(f"Total params:  {total_params:,}")
    print(f"Trainable:     {bridge_params + lora_params:,} ({100*(bridge_params+lora_params)/total_params:.2f}%)")

    # Dataset
    dataset = SacredTongueDataset(texts, st_tokenizer, max_length=256)
    loader = DataLoader(dataset, batch_size=2, shuffle=True, num_workers=0)

    # Optimizer — bridge (full LR) + LoRA (lower LR)
    optimizer = torch.optim.AdamW([
        {"params": bridge.parameters(), "lr": 1e-3},
        {"params": [p for p in base_model.parameters() if p.requires_grad], "lr": 2e-4},
    ], weight_decay=0.01)

    # Training loop
    bridged.train()
    num_epochs = 3

    for epoch in range(num_epochs):
        total_loss = 0.0
        steps = 0

        for batch in loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            outputs = bridged(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels,
            )

            loss = outputs.loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(bridged.parameters(), 0.3)
            optimizer.step()
            optimizer.zero_grad()

            total_loss += loss.item()
            steps += 1

            if steps % 50 == 0:
                avg = total_loss / steps
                print(f"  Epoch {epoch+1}/{num_epochs} | Step {steps} | Loss {avg:.4f}")

        avg_loss = total_loss / max(steps, 1)
        print(f"Epoch {epoch+1} complete — Avg Loss: {avg_loss:.4f}")

    # Save bridge weights + tokenizer
    st_tokenizer.save_pretrained(output_dir)
    torch.save(bridge.state_dict(), os.path.join(output_dir, "bridge.pt"))
    base_model.save_pretrained(os.path.join(output_dir, "lora_adapter"))
    print(f"\nSaved to {output_dir}")
    print("  - tokenizer_config.json, vocab.json (Sacred Tongues tokenizer)")
    print("  - bridge.pt (bridge projection weights)")
    print("  - lora_adapter/ (LoRA adapter for Qwen transformer)")

    # Cleanup
    del bridged, base_model, bridge, optimizer
    torch.cuda.empty_cache()


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Sacred Tongues tokenizer training")
    parser.add_argument(
        "--mode",
        required=True,
        choices=["replace", "bridge", "both"],
        help="Training mode: replace (vocab swap), bridge (learned projection), or both",
    )
    args = parser.parse_args()

    # HF auth
    hf_token = os.environ.get("HF_TOKEN", "")
    if hf_token:
        login(token=hf_token)
    else:
        try:
            login()
        except Exception:
            print("No HF auth — local only")

    # Load data
    print("Loading Sacred Tongues training data...")
    texts = load_sft_texts(SACRED_DATASETS)

    if not texts:
        print("ERROR: No training texts found. Check training-data/sft/ directory.")
        sys.exit(1)

    if args.mode in ("replace", "both"):
        train_vocab_replacement(texts)

    if args.mode in ("bridge", "both"):
        train_bridge(texts)

    print("\n" + "=" * 70)
    print("SACRED TONGUES TRAINING COMPLETE")
    if args.mode == "both":
        print("  Approach 1 (replace): artifacts/training/polly-sacred-replace/")
        print("  Approach 2 (bridge):  artifacts/training/polly-sacred-bridge/")
    print("=" * 70)


if __name__ == "__main__":
    main()
