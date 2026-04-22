#!/usr/bin/env python3
"""Universal cloud bootstrap — one script, any free GPU VM.

Copy-paste this onto Kaggle, Colab, Lightning, Paperspace, Saturn, or any VM:

    !curl -sL https://raw.githubusercontent.com/issdandavis/SCBE-AETHERMOORE/main/scripts/cloud_bootstrap_train.py | python3 - --round deep-knowledge

Or upload and run:
    python cloud_bootstrap_train.py --round covenantal --push

Handles: deps install, HF auth, dataset pull, GPU detection, batch size auto-tuning,
training, and optional push back to HuggingFace.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


# ============================================================
# STEP 1: AUTO-INSTALL DEPS
# ============================================================

REQUIRED = [
    "torch",
    "transformers>=4.49.0",
    "trl>=0.19.1",
    "peft>=0.14.0",
    "accelerate>=1.3.0",
    "datasets>=3.3.2",
    "bitsandbytes",
    "huggingface_hub",
]

def ensure_deps():
    """Install missing packages without restarting kernel."""
    for pkg in REQUIRED:
        name = pkg.split(">=")[0].split(">")[0]
        try:
            __import__(name)
        except ImportError:
            print(f"Installing {pkg}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg])


ensure_deps()

import torch
from datasets import Dataset, load_dataset
from huggingface_hub import login, hf_hub_download, HfApi
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import SFTConfig, SFTTrainer


# ============================================================
# CONFIG
# ============================================================

HF_DATASET = "issdandavis/scbe-aethermoore-training-data"
BASE_MODEL = os.getenv("POLLY_BASE_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")

ROUNDS: dict[str, dict] = {
    "covenantal": {
        "desc": "Covenantal null-space probes — KO/AV/RU/CA/UM/DR blind spots",
        "files": [
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
        "epochs": 2,
    },
    "deep-knowledge": {
        "desc": "Deep lore, personality, curriculum, frequency bundles",
        "files": [
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
        "epochs": 2,
    },
    "code-systems": {
        "desc": "Code patterns, architecture, typescript/python",
        "files": [
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
        "epochs": 2,
    },
    "adversarial": {
        "desc": "Adversarial defense, attack patterns, calibration",
        "files": [
            "advanced_adversarial_sft.jsonl",
            "adversarial_candy_sft.jsonl",
            "adversarial_storms_sft.jsonl",
            "entropic_defense_engine_sft.jsonl",
            "calibration_corpus_sft.jsonl",
            "test_behaviors_sft.jsonl",
            "autocorrection_behavior_sft.jsonl",
        ],
        "hf_repo": "issdandavis/polly-adversarial-qwen-0.5b",
        "epochs": 2,
    },
    "all-in-one": {
        "desc": "Every SFT file we have — big unified run",
        "files": "__ALL__",
        "hf_repo": "issdandavis/polly-unified-qwen-0.5b",
        "epochs": 2,
    },
}


# ============================================================
# STEP 2: GPU DETECTION + AUTO-TUNING
# ============================================================

def detect_gpu() -> dict:
    """Detect GPU and set optimal training params."""
    if not torch.cuda.is_available():
        print("WARNING: No GPU detected — training will be very slow on CPU")
        return {
            "batch_size": 1,
            "grad_accum": 16,
            "max_length": 256,
            "use_4bit": False,
            "compute_dtype": torch.float32,
            "bf16": False,
            "fp16": False,
            "device_map": "cpu",
            "gpu_name": "CPU",
            "vram_gb": 0,
        }

    gpu_name = torch.cuda.get_device_name(0)
    vram = torch.cuda.get_device_properties(0).total_mem / (1024**3)
    compute_cap = torch.cuda.get_device_capability(0)

    # BF16 support: Ampere+ (compute >= 8.0)
    has_bf16 = compute_cap[0] >= 8

    print(f"GPU: {gpu_name}")
    print(f"VRAM: {vram:.1f} GB")
    print(f"Compute: {compute_cap[0]}.{compute_cap[1]}")
    print(f"BF16: {'yes' if has_bf16 else 'no'}")

    # Auto-tune based on VRAM
    if vram >= 40:       # A100-40GB, A6000
        batch_size, grad_accum, max_len = 8, 4, 1024
    elif vram >= 24:     # A10G, 3090, 4090
        batch_size, grad_accum, max_len = 4, 4, 768
    elif vram >= 15:     # T4 (Kaggle/Colab), A4000
        batch_size, grad_accum, max_len = 4, 4, 512
    elif vram >= 8:      # 3060, 2080
        batch_size, grad_accum, max_len = 2, 8, 512
    elif vram >= 6:      # 1660 Ti, 2060
        batch_size, grad_accum, max_len = 2, 8, 512
    else:                # 4GB cards
        batch_size, grad_accum, max_len = 1, 16, 256

    return {
        "batch_size": batch_size,
        "grad_accum": grad_accum,
        "max_length": max_len,
        "use_4bit": True,
        "compute_dtype": torch.bfloat16 if has_bf16 else torch.float32,
        "bf16": has_bf16,
        "fp16": False,  # 4-bit + fp16 is buggy, avoid
        "device_map": "auto",
        "gpu_name": gpu_name,
        "vram_gb": vram,
    }


# ============================================================
# STEP 3: DATA LOADING (local files OR HuggingFace pull)
# ============================================================

def find_local_sft_dir() -> Path | None:
    """Try to find SFT data locally (for when repo is cloned)."""
    candidates = [
        Path("training-data/sft"),
        Path("../training-data/sft"),
        Path("/kaggle/input/scbe-sft/sft"),
        Path("/content/training-data/sft"),
    ]
    for p in candidates:
        if p.exists() and any(p.glob("*.jsonl")):
            return p
    return None


def load_from_hf(file_list: list[str]) -> list[dict]:
    """Pull JSONL files from HuggingFace dataset repo."""
    records = []
    api = HfApi()

    print(f"\nPulling data from {HF_DATASET}...")

    # List available files
    try:
        repo_files = [f.rfilename for f in api.list_repo_tree(HF_DATASET, repo_type="dataset")]
    except Exception:
        repo_files = []

    for name in file_list:
        # Try with and without sft/ prefix
        candidates = [name, f"sft/{name}", f"training-data/sft/{name}"]
        found = None
        for c in candidates:
            if c in repo_files:
                found = c
                break

        if not found:
            print(f"  SKIP  {name} (not in HF repo)")
            continue

        try:
            local_path = hf_hub_download(
                repo_id=HF_DATASET,
                filename=found,
                repo_type="dataset",
            )
            ds = load_dataset("json", data_files=local_path, split="train")
            print(f"  PULL  {name}: {len(ds)} records")

            for row in ds:
                rec = convert_row(row, ds.column_names)
                if rec:
                    records.append(rec)
        except Exception as e:
            print(f"  SKIP  {name} ({e})")

    return records


def load_from_local(sft_dir: Path, file_list: list[str]) -> list[dict]:
    """Load JSONL files from local directory."""
    records = []

    for name in file_list:
        path = sft_dir / name
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
        for row in ds:
            rec = convert_row(row, ds.column_names)
            if rec:
                records.append(rec)
                count += 1

        print(f"  LOAD  {name}: {count} records")

    return records


def convert_row(row: dict, cols: list[str]) -> dict | None:
    """Convert any SFT format to messages."""
    if "messages" in cols and row.get("messages"):
        return {"messages": row["messages"]}

    if "instruction" in cols:
        user = row.get("instruction", "")
        asst = row.get("response") or row.get("output") or row.get("positive", "")
        if user and asst:
            return {"messages": [
                {"role": "user", "content": user},
                {"role": "assistant", "content": asst},
            ]}

    if "prompt" in cols:
        user = row.get("prompt", "")
        asst = row.get("ideal_contains") or row.get("response", "")
        if user and asst:
            return {"messages": [
                {"role": "user", "content": user},
                {"role": "assistant", "content": str(asst)},
            ]}

    return None


def load_round_data(round_config: dict) -> Dataset:
    """Load data for a training round, trying local first, then HF."""
    file_list = round_config["files"]

    # Handle "all" mode
    if file_list == "__ALL__":
        local_dir = find_local_sft_dir()
        if local_dir:
            file_list = [f.name for f in local_dir.glob("*.jsonl")]
        else:
            print("Cannot discover files for all-in-one without local dir")
            sys.exit(1)

    local_dir = find_local_sft_dir()
    if local_dir:
        print(f"Using local data: {local_dir}")
        records = load_from_local(local_dir, file_list)
    else:
        records = load_from_hf(file_list)

    if not records:
        print("ERROR: No training records loaded!")
        sys.exit(1)

    print(f"\nTotal: {len(records)} training records")
    return Dataset.from_list(records)


# ============================================================
# STEP 4: TRAIN
# ============================================================

def train(round_name: str, round_config: dict, gpu: dict, push: bool) -> None:
    print(f"\n{'#' * 60}")
    print(f"# ROUND: {round_name}")
    print(f"# {round_config['desc']}")
    print(f"# GPU: {gpu['gpu_name']} ({gpu['vram_gb']:.0f}GB)")
    print(f"# Batch: {gpu['batch_size']} × {gpu['grad_accum']} accum = {gpu['batch_size'] * gpu['grad_accum']} effective")
    print(f"{'#' * 60}\n")

    dataset = load_round_data(round_config)

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    quant_config = None
    if gpu["use_4bit"]:
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=gpu["compute_dtype"],
            bnb_4bit_use_double_quant=True,
        )

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=quant_config,
        torch_dtype=gpu["compute_dtype"],
        device_map=gpu["device_map"],
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

    output_dir = f"polly-{round_name}"

    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=dataset,
        args=SFTConfig(
            output_dir=output_dir,
            hub_model_id=round_config["hf_repo"],
            push_to_hub=push,
            learning_rate=2e-4,
            per_device_train_batch_size=gpu["batch_size"],
            gradient_accumulation_steps=gpu["grad_accum"],
            num_train_epochs=round_config["epochs"],
            warmup_ratio=0.03,
            weight_decay=0.01,
            max_grad_norm=0.3,
            lr_scheduler_type="cosine",
            logging_steps=10,
            save_strategy="epoch",
            save_total_limit=2,
            max_length=gpu["max_length"],
            report_to="none",
            fp16=gpu["fp16"],
            bf16=gpu["bf16"],
            optim="adamw_torch",
            gradient_checkpointing=True,
        ),
    )

    trainer.train()
    trainer.save_model()
    print(f"\nSaved to {output_dir}")

    if push:
        trainer.push_to_hub()
        print(f"Pushed to {round_config['hf_repo']}")


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Universal Polly training — any GPU, any platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cloud_bootstrap_train.py --round covenantal --push
  python cloud_bootstrap_train.py --round deep-knowledge
  python cloud_bootstrap_train.py --round all-in-one --push
  python cloud_bootstrap_train.py --round adversarial --base-model Qwen/Qwen2.5-3B-Instruct
        """,
    )
    parser.add_argument("--round", required=True, choices=list(ROUNDS.keys()))
    parser.add_argument("--push", action="store_true", help="Push to HuggingFace after training")
    parser.add_argument("--base-model", default=None, help="Override base model")
    parser.add_argument("--hf-token", default=None, help="HuggingFace token (or set HF_TOKEN env)")
    args = parser.parse_args()

    if args.base_model:
        global BASE_MODEL
        BASE_MODEL = args.base_model

    # Auth
    token = args.hf_token or os.environ.get("HF_TOKEN", "")
    if token:
        login(token=token)
    else:
        try:
            login()
        except Exception:
            if args.push:
                print("ERROR: --push requires HF auth. Set HF_TOKEN or run `huggingface-cli login`")
                sys.exit(1)
            print("No HF auth — local only")

    # Detect GPU
    gpu = detect_gpu()

    # Train
    train(args.round, ROUNDS[args.round], gpu, args.push)

    print("\nDone.")


if __name__ == "__main__":
    main()
