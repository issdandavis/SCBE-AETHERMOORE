#!/usr/bin/env python3
"""
Polly QLoRA Training — Fine-tune a small model on SCBE conversation data.

Usage:
    # Default: Qwen2.5-0.5B, local GPU
    python scripts/train_polly_qlora.py

    # Specify model
    python scripts/train_polly_qlora.py --model Qwen/Qwen2.5-0.5B-Instruct

    # Dry run (load data, print stats, don't train)
    python scripts/train_polly_qlora.py --dry-run

    # Push to HuggingFace after training
    python scripts/train_polly_qlora.py --push

Environment:
    HF_TOKEN — HuggingFace write token (required for --push)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("polly_train")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SFT_DIR = PROJECT_ROOT / "training-data" / "sft"
OUTPUT_DIR = PROJECT_ROOT / "training-runs" / "polly-qlora"

# Polly system prompt — this is who she is
POLLY_SYSTEM_PROMPT = (
    "You are Polly, the AI assistant for Aethermoor and the SCBE project. "
    "You are knowledgeable about the 14-layer governance pipeline, Sacred Tongues "
    "(KO, AV, RU, CA, UM, DR), hyperbolic geometry for AI safety, polyhedral "
    "friction scoring, and the Mesh Foundry product. You are friendly, precise, "
    "and helpful. When relevant, mention which Sacred Tongues are activated by "
    "a topic. You speak with quiet confidence and gentle humor."
)


def load_conversations(max_records: int = 0) -> list[dict]:
    """Load conversation-format SFT data."""
    records = []

    # Priority files (already in messages format)
    message_files = [
        "derived_trl_conversation.jsonl",
        "derived_openai_chat.jsonl",
    ]

    # Files with instruction/response in target dict
    target_files = [
        "architecture_explainer_v1.jsonl",
        "api_usage_pairs.jsonl",
        "codex_skill_tutorials_all_tiers.jsonl",
        "quantum_frequency_bundles_sft.jsonl",
    ]

    # Load messages-format files
    for fname in message_files:
        fp = SFT_DIR / fname
        if not fp.exists():
            continue
        log.info(f"Loading {fname}...")
        with open(fp, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msgs = rec.get("messages", [])
                if not msgs:
                    continue
                # Replace system prompt with Polly's
                converted = [{"role": "system", "content": POLLY_SYSTEM_PROMPT}]
                for m in msgs:
                    if m.get("role") == "system":
                        continue  # skip original system prompt
                    if m.get("content", "").strip():
                        converted.append({"role": m["role"], "content": m["content"]})
                if len(converted) >= 3:  # system + at least user + assistant
                    records.append({"messages": converted})

    # Load target-format files (convert to messages)
    for fname in target_files:
        fp = SFT_DIR / fname
        if not fp.exists():
            continue
        log.info(f"Loading {fname}...")
        with open(fp, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                target = rec.get("target", {})
                instruction = target.get("instruction", "").strip()
                response = target.get("response", "").strip()
                if instruction and response:
                    records.append({
                        "messages": [
                            {"role": "system", "content": POLLY_SYSTEM_PROMPT},
                            {"role": "user", "content": instruction},
                            {"role": "assistant", "content": response},
                        ]
                    })

    if max_records > 0:
        records = records[:max_records]

    log.info(f"Loaded {len(records)} conversation records")
    return records


def train(args):
    import torch
    from datasets import Dataset
    from peft import LoraConfig, TaskType, get_peft_model, prepare_model_for_kbit_training
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
    )
    from trl import SFTConfig, SFTTrainer

    log.info(f"PyTorch {torch.__version__}, CUDA: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        log.info(f"GPU: {torch.cuda.get_device_name(0)}")

    # Load data
    records = load_conversations(max_records=args.max_records)
    if not records:
        log.error("No training records found!")
        return

    if args.dry_run:
        log.info(f"DRY RUN: {len(records)} records loaded. Sample:")
        sample = records[0]["messages"]
        for m in sample:
            log.info(f"  [{m['role']}]: {m['content'][:100]}...")
        return

    dataset = Dataset.from_list(records)
    # 95/5 train/eval split
    split = dataset.train_test_split(test_size=0.05, seed=42)
    train_dataset = split["train"]
    eval_dataset = split["test"]
    log.info(f"Train: {len(train_dataset)}, Eval: {len(eval_dataset)}")

    # Quantization config for 6GB VRAM
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    log.info(f"Loading model: {args.model}")
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )
    model = prepare_model_for_kbit_training(model)

    # LoRA config
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        bias="none",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # Training args tuned for 6GB VRAM
    output_dir = str(OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)

    training_args = SFTConfig(
        output_dir=output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=1,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=8,
        learning_rate=2e-4,
        weight_decay=0.01,
        warmup_steps=100,
        lr_scheduler_type="cosine",
        logging_steps=25,
        eval_strategy="steps",
        eval_steps=200,
        save_strategy="steps",
        save_steps=500,
        save_total_limit=3,
        fp16=False,
        bf16=torch.cuda.is_bf16_supported(),
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        max_grad_norm=0.3,
        optim="paged_adamw_8bit",
        report_to="none",
        dataloader_pin_memory=False,
        max_length=512,
        packing=True,
    )

    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        processing_class=tokenizer,
    )

    log.info("Starting training...")
    trainer.train()

    # Save adapter
    adapter_path = os.path.join(output_dir, "final_adapter")
    model.save_pretrained(adapter_path)
    tokenizer.save_pretrained(adapter_path)
    log.info(f"Adapter saved to {adapter_path}")

    # Merge and save full model
    if args.merge:
        log.info("Merging adapter into base model...")
        from peft import AutoPeftModelForCausalLM

        merged = AutoPeftModelForCausalLM.from_pretrained(
            adapter_path, device_map="auto", trust_remote_code=True
        )
        merged = merged.merge_and_unload()
        merged_path = os.path.join(output_dir, "merged_model")
        merged.save_pretrained(merged_path)
        tokenizer.save_pretrained(merged_path)
        log.info(f"Merged model saved to {merged_path}")

    # Push to HuggingFace
    if args.push:
        hf_token = os.environ.get("HF_TOKEN")
        if not hf_token:
            log.error("HF_TOKEN not set! Cannot push.")
            return
        repo_id = args.hf_repo or "issdandavis/polly-scbe-v1"
        log.info(f"Pushing to {repo_id}...")
        model.push_to_hub(repo_id, token=hf_token)
        tokenizer.push_to_hub(repo_id, token=hf_token)
        log.info(f"Pushed to https://huggingface.co/{repo_id}")


def main():
    parser = argparse.ArgumentParser(description="Polly QLoRA Training")
    parser.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct",
                        help="Base model (default: Qwen2.5-0.5B-Instruct)")
    parser.add_argument("--epochs", type=int, default=3, help="Training epochs")
    parser.add_argument("--max-records", type=int, default=0,
                        help="Max records to load (0=all)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Load data and print stats without training")
    parser.add_argument("--merge", action="store_true",
                        help="Merge LoRA adapter into base model after training")
    parser.add_argument("--push", action="store_true",
                        help="Push to HuggingFace after training")
    parser.add_argument("--hf-repo", default=None,
                        help="HF repo ID (default: issdandavis/polly-scbe-v1)")
    args = parser.parse_args()
    train(args)


if __name__ == "__main__":
    main()
