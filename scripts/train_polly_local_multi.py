#!/usr/bin/env python3
"""Polly Multi-Round Local SFT — QLoRA on GTX 1660 Ti (6GB VRAM).

Runs multiple training rounds with different dataset configurations.
Each round produces a separate LoRA adapter pushed to HuggingFace.

Usage:
    python scripts/train_polly_local_multi.py --round covenantal
    python scripts/train_polly_local_multi.py --round deep-knowledge
    python scripts/train_polly_local_multi.py --round all
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import torch
from datasets import Dataset, load_dataset
from huggingface_hub import login
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import SFTConfig, SFTTrainer

BASE_MODEL = os.getenv("POLLY_BASE_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
SFT_DIR = Path(__file__).resolve().parents[1] / "training-data" / "sft"

# ============================================================
# Round definitions: name → (datasets, hf_repo, output_dir, epochs)
# ============================================================
ROUNDS: dict[str, dict] = {
    "covenantal": {
        "desc": "Covenantal null-space probes — KO/AV/RU/CA/UM/DR blind spots",
        "datasets": [
            "null_space_confidence_triggers.jsonl",
            "biblical_null_space_probes.jsonl",
            "sacred_eggs_triplets_sft.jsonl",
            "sacred_tongues_sft.jsonl",
            "governance_deep_v2.jsonl",
            "security_structure_deep_v1.jsonl",
            "null_space_dpo_pairs.jsonl",
            "genesis_seed.jsonl",
            "calibration_corpus_sft.jsonl",
        ],
        "hf_repo": "issdandavis/polly-covenantal-qwen-0.5b",
        "output_dir": "artifacts/training/polly-covenantal-0.5b",
        "epochs": 2,
    },
    "deep-knowledge": {
        "desc": "Deep lore, personality, curriculum, frequency bundles",
        "datasets": [
            "polly_personality_deep_sft.jsonl",
            "polly_chat_seed.jsonl",
            "everweave_lore_sft.jsonl",
            "collegiate_curriculum_sft.jsonl",
            "quantum_frequency_bundles_sft.jsonl",
            "sacred_tongues_sft.jsonl",
            "trichromatic_spectrum_sft.jsonl",
            "phi_poincare_sft.jsonl",
            "polly_refusals_sft.jsonl",
        ],
        "hf_repo": "issdandavis/polly-deep-knowledge-qwen-0.5b",
        "output_dir": "artifacts/training/polly-deep-knowledge-0.5b",
        "epochs": 2,
    },
    "code-systems": {
        "desc": "Code patterns, architecture, infrastructure, typescript/python",
        "datasets": [
            "code_brushes_sft.jsonl",
            "code_substrate_l0_sft.jsonl",
            "architecture_explainer_v1.jsonl",
            "infrastructure_sft.jsonl",
            "typescript_docs_sft.jsonl",
            "python_docstrings_sft.jsonl",
            "copilot_replacement_v1.jsonl",
            "universal_code_primitives_sft.jsonl",
            "api_usage_pairs.jsonl",
        ],
        "hf_repo": "issdandavis/polly-code-systems-qwen-0.5b",
        "output_dir": "artifacts/training/polly-code-systems-0.5b",
        "epochs": 2,
    },
    "adversarial": {
        "desc": "Adversarial defense, attack patterns, calibration",
        "datasets": [
            "advanced_adversarial_sft.jsonl",
            "adversarial_candy_sft.jsonl",
            "adversarial_storms_sft.jsonl",
            "entropic_defense_engine_sft.jsonl",
            "calibration_corpus_sft.jsonl",
            "test_behaviors_sft.jsonl",
            "autocorrection_behavior_sft.jsonl",
        ],
        "hf_repo": "issdandavis/polly-adversarial-qwen-0.5b",
        "output_dir": "artifacts/training/polly-adversarial-0.5b",
        "epochs": 2,
    },
}


def load_round_datasets(file_list: list[str]) -> Dataset:
    """Load and combine JSONL datasets, handling both messages and instruction/response formats."""
    all_records: list[dict] = []
    composition: dict[str, int] = {}

    for name in file_list:
        path = SFT_DIR / name
        if not path.exists():
            print(f"  SKIP  {name} (not found)")
            composition[name] = 0
            continue

        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            print(f"  SKIP  {name} (empty)")
            composition[name] = 0
            continue
        if raw.startswith("version https://git-lfs"):
            print(f"  SKIP  {name} (Git LFS pointer — run 'git lfs pull')")
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

        cols = ds.column_names
        for row in ds:
            # Already has messages format
            if "messages" in cols and row.get("messages"):
                all_records.append({"messages": row["messages"]})
            # instruction/response or instruction/output format
            elif "instruction" in cols:
                user_text = row.get("instruction", "")
                assistant_text = row.get("response") or row.get("output") or row.get("positive", "")
                if user_text and assistant_text:
                    all_records.append({
                        "messages": [
                            {"role": "user", "content": user_text},
                            {"role": "assistant", "content": assistant_text},
                        ]
                    })
            # prompt/ideal_contains format (probes)
            elif "prompt" in cols:
                user_text = row.get("prompt", "")
                assistant_text = row.get("ideal_contains") or row.get("response", "")
                if user_text and assistant_text:
                    all_records.append({
                        "messages": [
                            {"role": "user", "content": user_text},
                            {"role": "assistant", "content": str(assistant_text)},
                        ]
                    })

    # Summary
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
    print(f"  {'CONVERTED':<45s} {len(all_records):>6d} messages")
    print("=" * 60 + "\n")

    if not all_records:
        raise RuntimeError("No training records found.")

    return Dataset.from_list(all_records)


def train_round(round_name: str, config: dict) -> None:
    """Run one training round."""
    print(f"\n{'#' * 60}")
    print(f"# ROUND: {round_name}")
    print(f"# {config['desc']}")
    print(f"{'#' * 60}\n")

    dataset = load_round_datasets(config["datasets"])

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

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

    push = os.getenv("POLLY_PUSH_TO_HUB", "0") == "1"
    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=dataset,
        args=SFTConfig(
            output_dir=config["output_dir"],
            hub_model_id=config["hf_repo"],
            push_to_hub=push,
            learning_rate=2e-4,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=8,
            num_train_epochs=config["epochs"],
            warmup_ratio=0.03,
            weight_decay=0.01,
            max_grad_norm=0.3,
            lr_scheduler_type="cosine",
            logging_steps=10,
            save_strategy="epoch",
            save_total_limit=2,
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
    print(f"\nModel saved to {config['output_dir']}")

    if push:
        trainer.push_to_hub()
        print(f"Pushed to {config['hf_repo']}")

    # Clean up GPU memory between rounds
    del trainer, model, tokenizer
    torch.cuda.empty_cache()


def main() -> None:
    parser = argparse.ArgumentParser(description="Polly multi-round local training")
    parser.add_argument("--round", required=True,
                        choices=list(ROUNDS.keys()) + ["all"],
                        help="Which training round to run")
    args = parser.parse_args()

    # Auth
    hf_token = os.environ.get("HF_TOKEN", "")
    if hf_token:
        login(token=hf_token)
    else:
        try:
            login()
        except Exception:
            print("No HF auth — models will be saved locally only")

    if args.round == "all":
        for name, config in ROUNDS.items():
            train_round(name, config)
    else:
        train_round(args.round, ROUNDS[args.round])


if __name__ == "__main__":
    main()
