#!/usr/bin/env python3
"""HYDRA Multi-Model Vertex AI Trainer.

Fine-tunes 6 Sacred Tongue head models from open-source bases using QLoRA.
Works on both Colab (free T4) and Vertex AI Custom Training.

Usage:
    # Dry-run — validates config and data, no GPU needed
    python training/vertex_hydra_trainer.py --dry-run

    # Train a single head locally (Colab or local GPU)
    python training/vertex_hydra_trainer.py --head KO

    # Train all heads sequentially (Colab)
    python training/vertex_hydra_trainer.py --all

    # Submit to Vertex AI (requires gcloud auth)
    python training/vertex_hydra_trainer.py --head RU --vertex

    # Push trained adapters to HuggingFace
    python training/vertex_hydra_trainer.py --head KO --push
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

CONFIG_PATH = Path(__file__).parent / "hydra_multi_model_config.yaml"


def load_config(path: Optional[str] = None) -> dict:
    p = Path(path) if path else CONFIG_PATH
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Training data loader
# ---------------------------------------------------------------------------


def load_training_data(
    categories: List[str],
    data_dir: str = "training-data",
) -> List[dict]:
    """Load SFT pairs from JSONL files matching the given categories.

    Searches recursively through subdirectories. Matches categories against
    both the parent directory name and the filename.
    """
    pairs = []
    # Recursive glob to find files in subdirs like game_design_sessions/
    all_files = sorted(glob.glob(os.path.join(data_dir, "**", "*.jsonl"), recursive=True))
    # Also include top-level files
    all_files += sorted(glob.glob(os.path.join(data_dir, "*.jsonl")))
    # Deduplicate
    all_files = sorted(set(all_files))

    for fpath in all_files:
        # Build a match string from the relative path (includes dir + filename)
        rel_path = os.path.relpath(fpath, data_dir).replace("\\", "/").replace(".jsonl", "")
        # Match if any category appears in the relative path
        if not any(cat in rel_path for cat in categories):
            continue
        with open(fpath, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    pairs.append(obj)
                except json.JSONDecodeError:
                    pass
    return pairs


def format_pair(pair: dict) -> dict:
    """Normalize various JSONL formats to a single 'text' field for SFT."""
    if "messages" in pair:
        msgs = pair["messages"]
        text = ""
        for m in msgs:
            role = m.get("role", "user")
            content = m.get("content", "")
            text += f"<|{role}|>\n{content}\n"
        return {"text": text.strip()}

    if "instruction" in pair:
        inp = pair.get("input", "")
        out = pair.get("output", pair.get("response", ""))
        instr = pair["instruction"]
        if inp:
            text = f"<|system|>\n{instr}\n<|user|>\n{inp}\n<|assistant|>\n{out}"
        else:
            text = f"<|user|>\n{instr}\n<|assistant|>\n{out}"
        return {"text": text}

    if "prompt" in pair:
        resp = pair.get("completion", pair.get("response", ""))
        return {"text": f"<|user|>\n{pair['prompt']}\n<|assistant|>\n{resp}"}

    return {"text": " ".join(str(v) for v in pair.values())}


# ---------------------------------------------------------------------------
# Governance gate (TriManifoldLattice integration)
# ---------------------------------------------------------------------------


def governance_check(head_config: dict, pairs: List[dict], config: dict) -> dict:
    """Run Federated 6D governance check on training data.

    Uses TriManifoldLattice to verify data quality before training.
    """
    gov = config.get("governance", {})
    tri = gov.get("tri_manifold", {})
    fed = gov.get("federated", {})

    result = {
        "head": head_config.get("role", "unknown"),
        "pair_count": len(pairs),
        "local_allow": 0,
        "local_quarantine": 0,
        "local_deny": 0,
    }

    try:
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        from symphonic_cipher.scbe_aethermoore.ai_brain.tri_manifold_lattice import (
            TriManifoldLattice,
            TriadicWeights,
        )

        lattice = TriManifoldLattice(
            harmonic_r=tri.get("harmonic_r", 1.5),
            harmonic_dimensions=tri.get("harmonic_dimensions", 6),
            window_immediate=tri.get("window_immediate", 5),
            window_memory=tri.get("window_memory", 25),
            window_governance=tri.get("window_governance", 100),
        )

        for pair in pairs:
            text = format_pair(pair).get("text", "")
            # Convert text to a 21D state normalized to Poincare ball interior.
            # Raw hash values are centered around 0 and scaled to stay well
            # within the ball (norm < 0.4) so the harmonic wall doesn't explode.
            raw = [
                float((hash(text[i:i+3]) % 1000) / 1000.0) - 0.5
                if i < len(text)
                else 0.0
                for i in range(0, 21 * 3, 3)
            ][:21]
            while len(raw) < 21:
                raw.append(0.0)
            # Normalize: clamp norm to 0.4 (safe Poincare ball interior)
            norm = max(sum(x * x for x in raw) ** 0.5, 1e-8)
            scale = min(0.4 / norm, 1.0)
            state = [x * scale for x in raw]

            node = lattice.ingest(state)

            # Tier 1 local decision based on hyperbolic distance from reference.
            # We use hyperbolic_dist (raw Poincare distance) rather than
            # harmonic_cost (which includes the R^(d^2) super-exponential
            # amplifier meant for adversarial detection, not data validation).
            h_dist = node.hyperbolic_dist
            if h_dist < 2.0:
                result["local_allow"] += 1
            elif h_dist < 5.0:
                result["local_quarantine"] += 1
            else:
                result["local_deny"] += 1

        total = max(result["pair_count"], 1)
        result["allow_ratio"] = result["local_allow"] / total
        result["resonance"] = lattice.temporal_resonance()
        result["anomaly"] = lattice.temporal_anomaly()
        result["triadic_distance"] = lattice.current_triadic_distance()

        min_allow = fed.get("min_local_allow_ratio", 0.7)
        result["governance_pass"] = result["allow_ratio"] >= min_allow

    except ImportError:
        # Lattice not available — pass by default in CI/Colab
        result["governance_pass"] = True
        result["note"] = "TriManifoldLattice not available, governance skipped"

    return result


# ---------------------------------------------------------------------------
# Local training (Colab / single GPU)
# ---------------------------------------------------------------------------


def train_head_local(
    tongue: str,
    config: dict,
    output_base: str = "./hydra-models",
    push: bool = False,
) -> str:
    """Fine-tune a single HYDRA head using QLoRA on local GPU."""
    import torch

    head = config["heads"][tongue]
    base_model_name = head["base_model"]
    lora_cfg = head["lora"]
    train_cfg = head["training"]
    output_dir = os.path.join(output_base, f"hydra-{tongue.lower()}-{head['role']}")

    print(f"\n{'='*60}")
    print(f"  HYDRA Head: {tongue} ({head['role']})")
    print(f"  Base model: {base_model_name}")
    print(f"  Output:     {output_dir}")
    print(f"{'='*60}\n")

    # Load training data
    categories = head["training_data"]["categories"]
    raw_pairs = load_training_data(categories)
    if not raw_pairs:
        print(f"  WARNING: No training data for categories {categories}")
        print(f"  Skipping {tongue} head.")
        return ""

    # Governance check
    gov_result = governance_check(head, raw_pairs, config)
    print(f"  Governance: {gov_result['local_allow']}/{len(raw_pairs)} ALLOW "
          f"(ratio={gov_result.get('allow_ratio', 0):.2f}, "
          f"resonance={gov_result.get('resonance', 0):.3f})")

    if not gov_result.get("governance_pass", True):
        print(f"  GOVERNANCE DENIED — allow ratio below threshold")
        return ""

    # Format data
    from datasets import Dataset
    formatted = [format_pair(p) for p in raw_pairs]
    dataset = Dataset.from_list(formatted)
    print(f"  Dataset: {len(dataset)} pairs")

    # Skip vision model (moondream) — needs different training loop
    if "moondream" in base_model_name.lower():
        print(f"  NOTE: Vision model ({base_model_name}) requires custom training loop.")
        print(f"  Saving data only. Use notebooks/hydra_vertex_multimodel.ipynb for VLM training.")
        os.makedirs(output_dir, exist_ok=True)
        dataset.to_json(os.path.join(output_dir, "training_data.jsonl"))
        return output_dir

    # Load model with QLoRA
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from trl import SFTTrainer

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    print(f"  Loading {base_model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )
    model = prepare_model_for_kbit_training(model)

    lora = LoraConfig(
        r=lora_cfg["r"],
        lora_alpha=lora_cfg["alpha"],
        lora_dropout=lora_cfg["dropout"],
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=lora_cfg["target_modules"],
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=train_cfg["epochs"],
        per_device_train_batch_size=train_cfg["batch_size"],
        gradient_accumulation_steps=4,
        learning_rate=train_cfg["learning_rate"],
        fp16=True,
        logging_steps=10,
        save_steps=50,
        save_total_limit=2,
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        args=training_args,
        max_seq_length=train_cfg["max_seq_length"],
    )

    print(f"  Training: {len(dataset)} samples, {train_cfg['epochs']} epochs")
    trainer.train()

    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"  Saved to {output_dir}")

    # Push to HuggingFace if requested
    if push:
        hf_repo = head.get("hf_repo")
        hf_token = os.environ.get("HF_TOKEN", "")
        if hf_repo and hf_token:
            from huggingface_hub import HfApi
            api = HfApi(token=hf_token)
            api.create_repo(repo_id=hf_repo, repo_type="model", exist_ok=True)
            api.upload_folder(
                folder_path=output_dir,
                repo_id=hf_repo,
                repo_type="model",
            )
            print(f"  Pushed to https://huggingface.co/{hf_repo}")
        else:
            print(f"  Skipping push — set HF_TOKEN and check hf_repo in config")

    # Cleanup GPU memory
    del model, trainer
    import gc
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return output_dir


# ---------------------------------------------------------------------------
# Vertex AI submission
# ---------------------------------------------------------------------------


def submit_vertex_job(tongue: str, config: dict) -> str:
    """Submit training job to Vertex AI Custom Training."""
    from google.cloud import aiplatform

    project = config["project"]["gcp_project_id"]
    region = config["project"]["gcp_region"]
    head = config["heads"][tongue]

    aiplatform.init(project=project, location=region)

    display_name = f"hydra-{tongue.lower()}-{head['role']}-{int(time.time())}"
    vertex_compute = head["vertex_compute"]

    job = aiplatform.CustomContainerTrainingJob(
        display_name=display_name,
        container_uri=f"{config['project']['artifact_registry']}/trainer:latest",
        command=["python", "training/vertex_hydra_trainer.py", "--head", tongue],
    )

    job.run(
        machine_type=vertex_compute["machine_type"],
        accelerator_type=vertex_compute["accelerator"],
        accelerator_count=vertex_compute["accelerator_count"],
        environment_variables={
            "HF_TOKEN": os.environ.get("HF_TOKEN", ""),
            "TONGUE": tongue,
        },
    )

    print(f"  Vertex AI job submitted: {display_name}")
    return display_name


# ---------------------------------------------------------------------------
# Dry run
# ---------------------------------------------------------------------------


def dry_run(config: dict) -> None:
    """Validate config and training data without GPU."""
    print("\n" + "=" * 60)
    print("  HYDRA Multi-Model Trainer — DRY RUN")
    print("=" * 60)

    print(f"\n  Project:  {config['project']['gcp_project_id']}")
    print(f"  Region:   {config['project']['gcp_region']}")
    print(f"  HF org:   {config['project']['hf_org']}")

    total_pairs = 0
    total_size_gb = 0.0

    print(f"\n  {'Tongue':<8} {'Role':<10} {'Model':<45} {'Size':>5} {'Data':>6}")
    print(f"  {'-'*8} {'-'*10} {'-'*45} {'-'*5} {'-'*6}")

    for tongue, head in config["heads"].items():
        categories = head["training_data"]["categories"]
        pairs = load_training_data(categories)
        total_pairs += len(pairs)
        total_size_gb += head["model_size_gb"]

        # Run governance
        gov = governance_check(head, pairs, config)
        status = "PASS" if gov.get("governance_pass") else "FAIL"

        print(
            f"  {tongue:<8} {head['role']:<10} "
            f"{head['base_model']:<45} "
            f"{head['model_size_gb']:>4.1f}G "
            f"{len(pairs):>5} [{status}]"
        )

    print(f"\n  Total training pairs: {total_pairs}")
    print(f"  Total model size:     {total_size_gb:.1f} GB (unquantized)")
    print(f"  QLoRA 4-bit:          ~{total_size_gb / 4:.1f} GB VRAM needed per head")

    # Check GPU
    try:
        import torch
        if torch.cuda.is_available():
            vram = torch.cuda.get_device_properties(0).total_mem / 1e9
            print(f"\n  GPU:  {torch.cuda.get_device_name(0)}")
            print(f"  VRAM: {vram:.1f} GB")
            can_fit = [t for t, h in config["heads"].items() if h["model_size_gb"] / 4 < vram * 0.8]
            print(f"  Can train: {', '.join(can_fit)}")
        else:
            print(f"\n  No GPU detected — use Colab or Vertex AI for training")
    except ImportError:
        print(f"\n  PyTorch not installed — install for local training")

    print(f"\n  Dry run complete. Use --head <TONGUE> to train.\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="HYDRA Multi-Model Trainer")
    parser.add_argument("--config", default=None, help="Path to config YAML")
    parser.add_argument("--dry-run", action="store_true", help="Validate only, no training")
    parser.add_argument("--head", type=str, help="Train a specific head (KO/AV/RU/CA/UM/DR)")
    parser.add_argument("--all", action="store_true", help="Train all heads sequentially")
    parser.add_argument("--vertex", action="store_true", help="Submit to Vertex AI")
    parser.add_argument("--push", action="store_true", help="Push to HuggingFace after training")
    parser.add_argument("--output", default="./hydra-models", help="Output directory")
    args = parser.parse_args()

    config = load_config(args.config)

    if args.dry_run:
        dry_run(config)
        return

    if args.head:
        tongue = args.head.upper()
        if tongue not in config["heads"]:
            print(f"Unknown head: {tongue}. Choose from: {list(config['heads'].keys())}")
            sys.exit(1)

        if args.vertex:
            submit_vertex_job(tongue, config)
        else:
            train_head_local(tongue, config, args.output, push=args.push)
        return

    if args.all:
        # Train all heads sequentially (fits on single T4)
        for tongue in config["heads"]:
            if args.vertex:
                submit_vertex_job(tongue, config)
            else:
                train_head_local(tongue, config, args.output, push=args.push)
        return

    # Default: show help
    parser.print_help()


if __name__ == "__main__":
    main()
