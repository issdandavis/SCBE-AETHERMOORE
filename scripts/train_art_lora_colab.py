#!/usr/bin/env python3
"""
Build a repeatable FLUX art-LoRA training packet for Six Tongues Protocol.

This script does three things locally:

1. audits the art training dataset
2. computes a weighted training plan that emphasizes anchor and hero images
3. writes a Colab notebook plus local report artifacts

It does not spend GPU money or submit remote jobs by itself.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOCAL_DATASET_DIR = ROOT / "training-data" / "art-style-lora"
DEFAULT_NOTEBOOK_PATH = ROOT / "artifacts" / "webtoon" / "six_tongues_lora_training.ipynb"
DEFAULT_PLAN_PATH = ROOT / "artifacts" / "webtoon" / "six_tongues_lora_training_plan.json"
DEFAULT_REPORT_PATH = ROOT / "artifacts" / "webtoon" / "six_tongues_lora_training_report.md"

DEFAULT_QUALITY_WEIGHTS: dict[str, int] = {
    "anchor": 5,
    "hero": 4,
    "good": 3,
    "supplemental": 1,
}

DEFAULT_EVAL_PROMPTS = [
    "manhwa webtoon illustration, over-the-shoulder hacker desk at 3AM, green terminal glow, empty office, lonely exhausted atmosphere",
    "manhwa webtoon illustration, crystal archive corridor, amber light through translucent walls, scholarly fantasy architecture, quiet awe",
    "manhwa webtoon illustration, giant academic raven on a crystal shelf, monochrome feathers with violet sheen, monocle and bowtie, sharp intelligent expression",
    "manhwa webtoon illustration, impossible Aethermoor reveal, floating landmasses, luminescent river, violet-gold aurora sky, painterly atmospheric depth",
]


@dataclass(frozen=True)
class TrainingEntry:
    file_name: str
    text: str
    source: str
    quality: str
    weight: int
    exists: bool

    def resolved_path(self, dataset_dir: Path) -> Path:
        return dataset_dir / self.file_name


def parse_quality_overrides(pairs: list[str]) -> dict[str, int]:
    overrides: dict[str, int] = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(f"quality override must look like quality=weight, got: {pair}")
        quality, raw_weight = pair.split("=", 1)
        quality = quality.strip().lower()
        if not quality:
            raise ValueError(f"quality override missing quality name: {pair}")
        try:
            weight = int(raw_weight)
        except ValueError as exc:
            raise ValueError(f"quality override has non-integer weight: {pair}") from exc
        if weight < 1:
            raise ValueError(f"quality weight must be >= 1, got: {pair}")
        overrides[quality] = weight
    return overrides


def merged_quality_weights(overrides: dict[str, int] | None = None) -> dict[str, int]:
    weights = dict(DEFAULT_QUALITY_WEIGHTS)
    if overrides:
        weights.update(overrides)
    return weights


def load_training_entries(dataset_dir: Path, quality_weights: dict[str, int]) -> list[TrainingEntry]:
    metadata_path = dataset_dir / "metadata.jsonl"
    if not metadata_path.exists():
        raise FileNotFoundError(f"metadata not found: {metadata_path}")

    entries: list[TrainingEntry] = []
    with metadata_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid metadata.jsonl line {line_number}: {exc}") from exc

            file_name = str(payload.get("file_name", "")).strip()
            if not file_name:
                raise ValueError(f"metadata.jsonl line {line_number} missing file_name")
            quality = str(payload.get("quality") or "supplemental").strip().lower()
            weight = int(quality_weights.get(quality, 1))
            resolved_path = dataset_dir / file_name

            entries.append(
                TrainingEntry(
                    file_name=file_name,
                    text=str(payload.get("text", "")).strip(),
                    source=str(payload.get("source", "unknown")).strip(),
                    quality=quality,
                    weight=weight,
                    exists=resolved_path.exists(),
                )
            )
    return entries


def ordered_quality_keys(quality_weights: dict[str, int], observed: set[str]) -> list[str]:
    keys: list[str] = []
    for key in quality_weights:
        if key in observed:
            keys.append(key)
    for key in sorted(observed):
        if key not in keys:
            keys.append(key)
    return keys


def build_training_plan(
    entries: list[TrainingEntry],
    *,
    train_batch_size: int,
    gradient_accumulation_steps: int,
    target_effective_epochs: int,
    quality_weights: dict[str, int],
) -> dict[str, Any]:
    usable_entries = [entry for entry in entries if entry.exists]
    missing_files = [entry.file_name for entry in entries if not entry.exists]

    quality_counts: Counter[str] = Counter()
    weighted_counts: defaultdict[str, int] = defaultdict(int)
    source_counts: Counter[str] = Counter()

    for entry in usable_entries:
        quality_counts[entry.quality] += 1
        weighted_counts[entry.quality] += entry.weight
        source_counts[entry.source] += 1

    observed_qualities = {entry.quality for entry in entries}
    quality_rows: list[dict[str, Any]] = []
    for quality in ordered_quality_keys(quality_weights, observed_qualities):
        quality_rows.append(
            {
                "quality": quality,
                "count": quality_counts.get(quality, 0),
                "weight": int(quality_weights.get(quality, 1)),
                "weighted_examples": int(weighted_counts.get(quality, 0)),
            }
        )

    optimizer_examples_per_step = max(1, train_batch_size * gradient_accumulation_steps)
    weighted_example_count = sum(entry.weight for entry in usable_entries)
    recommended_max_train_steps = (
        math.ceil((weighted_example_count * target_effective_epochs) / optimizer_examples_per_step)
        if weighted_example_count
        else 0
    )
    recommended_save_steps = max(100, recommended_max_train_steps // 4) if recommended_max_train_steps else 0
    estimated_optimizer_epochs = (
        round((recommended_max_train_steps * optimizer_examples_per_step) / weighted_example_count, 2)
        if weighted_example_count
        else 0.0
    )

    recommendations: list[str] = []
    anchor_count = quality_counts.get("anchor", 0)
    hero_count = quality_counts.get("hero", 0)
    if anchor_count < 6:
        recommendations.append("Add more character and environment anchor sheets before large retrains.")
    if hero_count < 8:
        recommendations.append("Collect more hero panels and environment money shots for style lock.")
    if weighted_example_count < 80:
        recommendations.append("Current corpus is still small enough that every approved new image materially matters.")
    if missing_files:
        recommendations.append("Fix missing files before the next training run so the weighting math stays honest.")

    return {
        "entry_count": len(entries),
        "usable_entry_count": len(usable_entries),
        "missing_files": missing_files,
        "quality_breakdown": quality_rows,
        "source_breakdown": dict(sorted(source_counts.items())),
        "weighted_example_count": weighted_example_count,
        "optimizer_examples_per_step": optimizer_examples_per_step,
        "target_effective_epochs": target_effective_epochs,
        "recommended_max_train_steps": recommended_max_train_steps,
        "recommended_save_steps": recommended_save_steps,
        "estimated_optimizer_epochs": estimated_optimizer_epochs,
        "sample_entries": [
            {
                "file_name": entry.file_name,
                "quality": entry.quality,
                "source": entry.source,
                "weight": entry.weight,
                "text": entry.text,
            }
            for entry in usable_entries[:5]
        ],
        "recommendations": recommendations,
    }


def render_report(
    *,
    dataset_dir: Path,
    colab_dataset_dir: str,
    prepared_dataset_dir: str,
    notebook_path: Path,
    plan_path: Path,
    quality_weights: dict[str, int],
    config: dict[str, Any],
    plan: dict[str, Any],
) -> str:
    quality_lines = []
    for row in plan["quality_breakdown"]:
        quality_lines.append(
            f"- `{row['quality']}`: {row['count']} files x weight {row['weight']} -> {row['weighted_examples']} effective examples"
        )

    recommendation_lines = plan["recommendations"] or ["- No urgent dataset warnings."]

    return "\n".join(
        [
            "# Six Tongues Art LoRA Training Report",
            "",
            "## Dataset",
            f"- Local dataset: `{dataset_dir}`",
            f"- Colab upload path: `{colab_dataset_dir}`",
            f"- Weighted training dir inside Colab: `{prepared_dataset_dir}`",
            f"- Entries in metadata: `{plan['entry_count']}`",
            f"- Usable files: `{plan['usable_entry_count']}`",
            f"- Missing files: `{len(plan['missing_files'])}`",
            "",
            "## Weighting",
            f"- Quality weights: `{json.dumps(quality_weights, sort_keys=True)}`",
            *quality_lines,
            "",
            "## Training Plan",
            f"- Base model: `{config['base_model']}`",
            f"- Hub repo: `{config['hub_model_id']}`",
            f"- Trigger word: `{config['trigger_word']}`",
            f"- Weighted example count: `{plan['weighted_example_count']}`",
            f"- Optimizer examples per step: `{plan['optimizer_examples_per_step']}`",
            f"- Target effective epochs: `{plan['target_effective_epochs']}`",
            f"- Recommended max train steps: `{plan['recommended_max_train_steps']}`",
            f"- Recommended save steps: `{config['save_steps']}`",
            f"- Estimated optimizer epochs: `{plan['estimated_optimizer_epochs']}`",
            "",
            "## Notes",
            "- This lane uses a shared trigger prompt plus weighted file repetition.",
            "- The detailed per-image captions remain useful for review, eval prompts, and future caption-aware trainers, but the current DreamBooth command is driven by the shared trigger token.",
            "- Add approved anchor sheets and hero panels first. Then rerun this script before the next training pass.",
            "",
            "## Recommendations",
            *recommendation_lines,
            "",
            "## Outputs",
            f"- Notebook: `{notebook_path}`",
            f"- Plan JSON: `{plan_path}`",
        ]
    )


def make_install_cell() -> str:
    return "\n".join(
        [
            "!pip install -q diffusers transformers accelerate peft bitsandbytes",
            "!pip install -q datasets huggingface_hub safetensors",
            "!pip install -q xformers --index-url https://download.pytorch.org/whl/cu121",
        ]
    )


def make_config_cell(config: dict[str, Any], plan: dict[str, Any]) -> str:
    return f"""
import json
import os
from huggingface_hub import login

CONFIG = {json.dumps(config, indent=4)}
PLAN = {json.dumps(plan, indent=4)}

hf_token = os.environ.get("HF_TOKEN", "")
if not hf_token:
    raise RuntimeError("Set HF_TOKEN in Colab secrets before training.")
login(token=hf_token)

print("Base model:", CONFIG["base_model"])
print("Hub repo:", CONFIG["hub_model_id"])
print("Trigger word:", CONFIG["trigger_word"])
print("Weighted examples:", PLAN["weighted_example_count"])
print("Recommended max train steps:", CONFIG["max_train_steps"])
""".strip()


def make_dataset_prep_cell() -> str:
    return """
import json
import shutil
from pathlib import Path

dataset_dir = Path(CONFIG["dataset_dir"])
prepared_dataset_dir = Path(CONFIG["prepared_dataset_dir"])
metadata_path = dataset_dir / "metadata.jsonl"
if not metadata_path.exists():
    raise FileNotFoundError(f"metadata.jsonl not found in {dataset_dir}")

if prepared_dataset_dir.exists():
    shutil.rmtree(prepared_dataset_dir)
prepared_dataset_dir.mkdir(parents=True, exist_ok=True)

entries = []
with metadata_path.open("r", encoding="utf-8") as handle:
    for raw_line in handle:
        line = raw_line.strip()
        if not line:
            continue
        entries.append(json.loads(line))

copied = 0
manifest = []
for entry in entries:
    quality = str(entry.get("quality", "supplemental")).strip().lower()
    weight = int(CONFIG["quality_weights"].get(quality, 1))
    image_path = dataset_dir / entry["file_name"]
    if not image_path.exists():
        print("SKIP missing:", image_path)
        continue
    stem = image_path.stem
    suffix = image_path.suffix
    for repeat_index in range(weight):
        target_name = f"{stem}__q{quality}__r{repeat_index + 1:02d}{suffix}"
        target_path = prepared_dataset_dir / target_name
        shutil.copy2(image_path, target_path)
        manifest.append(
            {
                "prepared_file": target_name,
                "source_file": entry["file_name"],
                "quality": quality,
                "weight": weight,
                "text": entry.get("text", ""),
            }
        )
        copied += 1

manifest_path = prepared_dataset_dir / "weighted_manifest.jsonl"
with manifest_path.open("w", encoding="utf-8") as handle:
    for row in manifest:
        handle.write(json.dumps(row, ensure_ascii=True) + "\\n")

print("Prepared weighted dataset:", prepared_dataset_dir)
print("Copied images:", copied)
print("Manifest:", manifest_path)
""".strip()


def make_gpu_check_cell() -> str:
    return """
import torch

device = "cuda" if torch.cuda.is_available() else "cpu"
print("Device:", device)
if device != "cuda":
    raise RuntimeError("GPU is required for FLUX LoRA training.")

props = torch.cuda.get_device_properties(0)
print("GPU:", torch.cuda.get_device_name(0))
print(f"VRAM: {props.total_memory / 1e9:.1f} GB")
""".strip()


def make_train_cell(config: dict[str, Any]) -> str:
    return f"""
from pathlib import Path
import shlex

train_script = Path("train_dreambooth_lora_flux.py")
if not train_script.exists():
    !wget -q -O train_dreambooth_lora_flux.py https://raw.githubusercontent.com/huggingface/diffusers/main/examples/dreambooth/train_dreambooth_lora_flux.py

command_parts = [
    "accelerate launch train_dreambooth_lora_flux.py",
    f"--pretrained_model_name_or_path={{shlex.quote(CONFIG['base_model'])}}",
    f"--instance_data_dir={{shlex.quote(CONFIG['prepared_dataset_dir'])}}",
    f"--instance_prompt={{shlex.quote(CONFIG['trigger_word'])}}",
    f"--output_dir={{shlex.quote(CONFIG['output_dir'])}}",
    f"--resolution={{CONFIG['resolution']}}",
    f"--train_batch_size={{CONFIG['train_batch_size']}}",
    f"--gradient_accumulation_steps={{CONFIG['gradient_accumulation_steps']}}",
    f"--learning_rate={{CONFIG['learning_rate']}}",
    f"--lr_scheduler={{CONFIG['lr_scheduler']}}",
    f"--max_train_steps={{CONFIG['max_train_steps']}}",
    f"--rank={{CONFIG['lora_rank']}}",
    f"--checkpointing_steps={{CONFIG['save_steps']}}",
    "--mixed_precision=fp16",
    f"--seed={{CONFIG['seed']}}",
]

train_command = " ".join(command_parts)
print(train_command)
get_ipython().system(train_command)
""".strip()


def make_push_cell() -> str:
    return """
from pathlib import Path
from huggingface_hub import HfApi

api = HfApi()
output_dir = Path(CONFIG["output_dir"])
if not output_dir.exists():
    raise FileNotFoundError(f"training output missing: {output_dir}")

api.create_repo(repo_id=CONFIG["hub_model_id"], repo_type="model", exist_ok=True)
api.upload_folder(
    folder_path=str(output_dir),
    repo_id=CONFIG["hub_model_id"],
    repo_type="model",
)
print(f"Uploaded LoRA to https://huggingface.co/{CONFIG['hub_model_id']}")
""".strip()


def make_eval_cell() -> str:
    return """
from pathlib import Path

import torch
from diffusers import FluxPipeline

pipe = FluxPipeline.from_pretrained(
    CONFIG["base_model"],
    torch_dtype=torch.float16,
)
pipe.load_lora_weights(CONFIG["output_dir"])
pipe.to("cuda")

eval_dir = Path("lora_eval_outputs")
eval_dir.mkdir(parents=True, exist_ok=True)

for index, prompt in enumerate(CONFIG["eval_prompts"], start=1):
    full_prompt = f"{CONFIG['trigger_word']}, {prompt}"
    image = pipe(
        prompt=full_prompt,
        num_inference_steps=CONFIG["eval_num_inference_steps"],
        guidance_scale=CONFIG["eval_guidance_scale"],
    ).images[0]
    output_path = eval_dir / f"eval_{index:02d}.png"
    image.save(output_path)
    print(output_path, "->", full_prompt)
""".strip()


def build_notebook_cells(config: dict[str, Any], plan: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        (
            "markdown",
            "\n".join(
                [
                    "# Six Tongues Protocol Art LoRA Training",
                    "",
                    "This notebook trains a FLUX LoRA for the Six Tongues visual lane.",
                    "",
                    "Key idea:",
                    "- lock the trigger token",
                    "- upweight anchor and hero images",
                    "- retrain after each new approved dataset wave",
                    "",
                    f"Weighted examples in this packet: `{plan['weighted_example_count']}`",
                    f"Recommended max train steps: `{config['max_train_steps']}`",
                ]
            ),
        ),
        ("code", make_install_cell()),
        ("markdown", "## Config"),
        ("code", make_config_cell(config, plan)),
        ("markdown", "## Dataset Prep"),
        ("code", make_dataset_prep_cell()),
        ("markdown", "## GPU Check"),
        ("code", make_gpu_check_cell()),
        ("markdown", "## Train"),
        ("code", make_train_cell(config)),
        ("markdown", "## Push To Hugging Face"),
        ("code", make_push_cell()),
        ("markdown", "## Eval Prompts"),
        ("code", make_eval_cell()),
    ]


def build_notebook(path: Path, *, config: dict[str, Any], plan: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    cells = build_notebook_cells(config, plan)
    notebook = {
        "nbformat": 4,
        "nbformat_minor": 0,
        "metadata": {
            "colab": {"provenance": [], "gpuType": "T4"},
            "kernelspec": {"name": "python3", "display_name": "Python 3"},
            "accelerator": "GPU",
        },
        "cells": [],
    }
    for cell_type, source in cells:
        notebook["cells"].append(
            {
                "cell_type": cell_type,
                "metadata": {},
                "source": source.splitlines(keepends=True),
                **({"outputs": [], "execution_count": None} if cell_type == "code" else {}),
            }
        )
    path.write_text(json.dumps(notebook, indent=2), encoding="utf-8")
    return path


def write_plan_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_config(args: argparse.Namespace, plan: dict[str, Any], quality_weights: dict[str, int]) -> dict[str, Any]:
    max_train_steps = args.max_train_steps or int(plan["recommended_max_train_steps"])
    save_steps = args.save_steps or int(plan["recommended_save_steps"] or max(100, max_train_steps // 4 or 100))
    return {
        "base_model": args.base_model,
        "dataset_dir": args.colab_dataset_dir,
        "prepared_dataset_dir": args.prepared_dataset_dir,
        "output_dir": args.output_dir,
        "hub_model_id": args.hub_model_id,
        "trigger_word": args.trigger_word,
        "quality_weights": quality_weights,
        "lora_rank": args.lora_rank,
        "lora_alpha": args.lora_alpha,
        "learning_rate": args.learning_rate,
        "lr_scheduler": args.lr_scheduler,
        "train_batch_size": args.train_batch_size,
        "gradient_accumulation_steps": args.gradient_accumulation_steps,
        "max_train_steps": max_train_steps,
        "save_steps": save_steps,
        "resolution": args.resolution,
        "seed": args.seed,
        "eval_prompts": list(DEFAULT_EVAL_PROMPTS),
        "eval_num_inference_steps": args.eval_num_inference_steps,
        "eval_guidance_scale": args.eval_guidance_scale,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a weighted art-LoRA training notebook and dataset report.")
    parser.add_argument("--dataset-dir", default=str(DEFAULT_LOCAL_DATASET_DIR), help="Local dataset path used for audit.")
    parser.add_argument(
        "--colab-dataset-dir",
        default="training-data/art-style-lora",
        help="Dataset path as it will exist inside Colab after upload.",
    )
    parser.add_argument(
        "--prepared-dataset-dir",
        default="training-data/art-style-lora-weighted",
        help="Weighted dataset directory created inside Colab before training.",
    )
    parser.add_argument("--base-model", default="black-forest-labs/FLUX.1-schnell")
    parser.add_argument("--hub-model-id", default="issdandavis/six-tongues-art-lora")
    parser.add_argument("--output-dir", default="six-tongues-lora-output")
    parser.add_argument("--trigger-word", default="sixtongues_style")
    parser.add_argument("--lora-rank", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--lr-scheduler", default="constant")
    parser.add_argument("--train-batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=4)
    parser.add_argument("--resolution", type=int, default=1024)
    parser.add_argument("--target-effective-epochs", type=int, default=60)
    parser.add_argument("--max-train-steps", type=int, default=None, help="Override the derived training-step recommendation.")
    parser.add_argument("--save-steps", type=int, default=None, help="Override checkpoint frequency.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--eval-num-inference-steps", type=int, default=4)
    parser.add_argument("--eval-guidance-scale", type=float, default=0.0)
    parser.add_argument(
        "--quality-weight",
        action="append",
        default=[],
        help="Override quality weights, for example --quality-weight anchor=6",
    )
    parser.add_argument("--notebook-path", default=str(DEFAULT_NOTEBOOK_PATH))
    parser.add_argument("--plan-path", default=str(DEFAULT_PLAN_PATH))
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_dir = Path(args.dataset_dir).resolve()
    notebook_path = Path(args.notebook_path).resolve()
    plan_path = Path(args.plan_path).resolve()
    report_path = Path(args.report_path).resolve()

    quality_weights = merged_quality_weights(parse_quality_overrides(args.quality_weight))
    entries = load_training_entries(dataset_dir, quality_weights)
    plan = build_training_plan(
        entries,
        train_batch_size=args.train_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        target_effective_epochs=args.target_effective_epochs,
        quality_weights=quality_weights,
    )
    config = build_config(args, plan, quality_weights)

    notebook = build_notebook(notebook_path, config=config, plan=plan)
    write_plan_json(plan_path, {"dataset_dir": str(dataset_dir), "config": config, "plan": plan})
    report = render_report(
        dataset_dir=dataset_dir,
        colab_dataset_dir=args.colab_dataset_dir,
        prepared_dataset_dir=args.prepared_dataset_dir,
        notebook_path=notebook,
        plan_path=plan_path,
        quality_weights=quality_weights,
        config=config,
        plan=plan,
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")

    print(f"Notebook written: {notebook}")
    print(f"Plan written: {plan_path}")
    print(f"Report written: {report_path}")
    print()
    print("Training summary")
    print(f"  usable files: {plan['usable_entry_count']}/{plan['entry_count']}")
    print(f"  weighted examples: {plan['weighted_example_count']}")
    print(f"  recommended max train steps: {config['max_train_steps']}")
    print(f"  trigger word: {config['trigger_word']}")
    if plan["missing_files"]:
        print(f"  missing files: {', '.join(plan['missing_files'])}")
    print()
    print("Next step")
    print(f"  1. Upload {notebook} to Colab")
    print(f"  2. Upload {args.colab_dataset_dir}/ with metadata.jsonl and images")
    print("  3. Set HF_TOKEN in Colab secrets")
    print("  4. Run all notebook cells")


if __name__ == "__main__":
    main()
