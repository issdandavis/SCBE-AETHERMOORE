#!/usr/bin/env python3
"""Config-backed SCBE model training lane helpers."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_PROFILE_DIR = Path("config") / "model_training"
DEFAULT_PROFILE_ID = "coder-qwen-local"


def _ensure_dict(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _coerce_string(value: Any, fallback: str = "") -> str:
    if isinstance(value, str):
        return value
    return fallback


def _coerce_str_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(item) for item in values if str(item).strip()]


def profile_dir(repo_root: Path, raw_dir: str | None = None) -> Path:
    candidate = Path(raw_dir) if raw_dir else DEFAULT_PROFILE_DIR
    return candidate if candidate.is_absolute() else (repo_root / candidate).resolve()


def resolve_profile_path(
    repo_root: Path,
    *,
    profile: str | None = None,
    profile_path: str | None = None,
    raw_profile_dir: str | None = None,
) -> Path:
    if profile_path:
        candidate = Path(profile_path)
        return candidate if candidate.is_absolute() else (repo_root / candidate).resolve()
    profile_id = (profile or DEFAULT_PROFILE_ID).strip() or DEFAULT_PROFILE_ID
    return profile_dir(repo_root, raw_profile_dir) / f"{profile_id}.json"


def list_profiles(repo_root: Path, raw_dir: str | None = None) -> list[dict[str, str]]:
    root = profile_dir(repo_root, raw_dir)
    if not root.exists():
        return []
    items: list[dict[str, str]] = []
    for path in sorted(root.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        items.append(
            {
                "profile_id": _coerce_string(payload.get("profile_id"), path.stem),
                "title": _coerce_string(payload.get("title"), path.stem),
                "path": str(path),
            }
        )
    return items


def load_profile(profile_path: Path) -> dict[str, Any]:
    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    payload = _ensure_dict(payload, label="model profile")
    dataset = _ensure_dict(payload.get("dataset") or {}, label="dataset")
    training = _ensure_dict(payload.get("training") or {}, label="training")
    execution = _ensure_dict(payload.get("execution") or {}, label="execution")
    hub = _ensure_dict(payload.get("hub") or {}, label="hub")
    payload["dataset"] = dataset
    payload["training"] = training
    payload["execution"] = execution
    payload["hub"] = hub
    payload.setdefault("schema_version", "scbe_model_training_profile_v1")
    payload.setdefault("profile_id", profile_path.stem)
    payload.setdefault("title", payload["profile_id"])
    payload.setdefault("description", "")
    payload.setdefault("backend", "unsloth-qlora")
    payload.setdefault("base_model", "Qwen/Qwen2.5-Coder-7B-Instruct")
    payload.setdefault("system_prompt", "You are a coding assistant.")
    dataset.setdefault("root", "training-data")
    dataset.setdefault("train_files", [])
    dataset.setdefault("eval_files", [])
    training.setdefault("output_dir", f"training/runs/{payload['profile_id']}")
    execution.setdefault("default_emit_path", f"artifacts/model_training/{payload['profile_id']}-train.py")
    hub.setdefault("token_env", "HF_TOKEN")
    hub.setdefault("push_adapter", False)
    hub.setdefault("adapter_repo", "")
    hub.setdefault("push_merged", False)
    return payload


def _resolve_data_root(repo_root: Path, profile_path: Path, raw_root: str) -> Path:
    root = Path(raw_root)
    if root.is_absolute():
        return root
    return (repo_root / root).resolve() if profile_path.parent == repo_root / DEFAULT_PROFILE_DIR else (profile_path.parent / root).resolve()


def _count_jsonl_rows(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                count += 1
    return count


def _sample_jsonl_keys(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            raw = line.strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                return []
            if isinstance(payload, dict):
                return sorted(str(key) for key in payload.keys())
            return []
    return []


def _dataset_rows(data_root: Path, files: list[str], *, split: str) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    total = 0
    for name in files:
        path = data_root / name if not Path(name).is_absolute() else Path(name)
        exists = path.exists()
        row_count = _count_jsonl_rows(path) if exists else 0
        sample_keys = _sample_jsonl_keys(path) if exists else []
        total += row_count
        rows.append(
            {
                "split": split,
                "name": name,
                "path": str(path),
                "exists": exists,
                "row_count": row_count,
                "sample_keys": sample_keys,
            }
        )
    return rows, total


def build_training_plan(repo_root: Path, profile_path: Path) -> dict[str, Any]:
    profile = load_profile(profile_path)
    dataset_cfg = profile["dataset"]
    data_root = _resolve_data_root(repo_root, profile_path, _coerce_string(dataset_cfg.get("root"), "training-data"))
    train_rows, total_train_rows = _dataset_rows(data_root, _coerce_str_list(dataset_cfg.get("train_files")), split="train")
    eval_rows, total_eval_rows = _dataset_rows(data_root, _coerce_str_list(dataset_cfg.get("eval_files")), split="eval")
    all_rows = train_rows + eval_rows
    missing = [row["name"] for row in all_rows if not row["exists"]]
    output_dir = Path(_coerce_string(profile["training"].get("output_dir"), f"training/runs/{profile['profile_id']}"))
    if not output_dir.is_absolute():
        output_dir = (repo_root / output_dir).resolve()
    emit_path = Path(_coerce_string(profile["execution"].get("default_emit_path"), f"artifacts/model_training/{profile['profile_id']}-train.py"))
    if not emit_path.is_absolute():
        emit_path = (repo_root / emit_path).resolve()
    return {
        "schema_version": "scbe_model_training_plan_v1",
        "ready": not missing and bool(train_rows),
        "profile_id": profile["profile_id"],
        "title": profile["title"],
        "description": profile["description"],
        "profile_path": str(profile_path),
        "backend": profile["backend"],
        "base_model": profile["base_model"],
        "data_root": str(data_root),
        "train_datasets": train_rows,
        "eval_datasets": eval_rows,
        "train_file_count": len(train_rows),
        "eval_file_count": len(eval_rows),
        "total_train_rows": total_train_rows,
        "total_eval_rows": total_eval_rows,
        "missing_files": missing,
        "output_dir": str(output_dir),
        "default_emit_path": str(emit_path),
        "training": profile["training"],
        "hub": profile["hub"],
        "system_prompt": profile["system_prompt"],
    }


def _dependency_status(name: str) -> dict[str, Any]:
    spec = importlib.util.find_spec(name)
    return {
        "name": name,
        "available": spec is not None,
    }


def _inspect_torch_runtime() -> dict[str, Any]:
    try:
        import torch  # type: ignore
    except Exception as exc:  # pragma: no cover - import failure depends on environment
        return {
            "available": False,
            "error": str(exc),
            "cuda_available": False,
            "device_count": 0,
            "devices": [],
            "total_vram_mb": 0,
        }

    cuda_available = bool(torch.cuda.is_available())
    devices: list[dict[str, Any]] = []
    total_vram_mb = 0
    if cuda_available:
        for idx in range(int(torch.cuda.device_count())):
            props = torch.cuda.get_device_properties(idx)
            total_mb = int(props.total_memory // (1024 * 1024))
            total_vram_mb += total_mb
            devices.append(
                {
                    "index": idx,
                    "name": str(props.name),
                    "total_vram_mb": total_mb,
                }
            )
    return {
        "available": True,
        "version": getattr(torch, "__version__", "unknown"),
        "cuda_available": cuda_available,
        "device_count": int(torch.cuda.device_count()) if cuda_available else 0,
        "devices": devices,
        "total_vram_mb": total_vram_mb,
    }


def _inspect_nvidia_smi() -> dict[str, Any]:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return {"available": False, "devices": []}
    try:
        result = subprocess.run(
            [exe, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except Exception as exc:  # pragma: no cover - environment dependent
        return {"available": True, "error": str(exc), "devices": []}
    if result.returncode != 0:
        return {
            "available": True,
            "returncode": result.returncode,
            "stderr": result.stderr.strip(),
            "devices": [],
        }
    devices: list[dict[str, Any]] = []
    for idx, line in enumerate(result.stdout.splitlines()):
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 3:
            continue
        name, total_mem, driver_version = parts[:3]
        total_vram_mb = int(total_mem) if total_mem.isdigit() else 0
        devices.append(
            {
                "index": idx,
                "name": name,
                "total_vram_mb": total_vram_mb,
                "driver_version": driver_version,
            }
        )
    return {
        "available": True,
        "devices": devices,
        "total_vram_mb": sum(device.get("total_vram_mb", 0) for device in devices),
    }


def _estimated_min_local_vram_mb(profile: dict[str, Any]) -> int:
    execution_cfg = profile.get("execution") or {}
    explicit = execution_cfg.get("minimum_local_vram_mb")
    if isinstance(explicit, int) and explicit > 0:
        return explicit
    model_name = _coerce_string(profile.get("base_model"), "")
    match = re.search(r"(\d+(?:\.\d+)?)\s*[bB]", model_name)
    billions = float(match.group(1)) if match else 7.0
    if billions <= 3:
        base = 6144
    elif billions <= 7:
        base = 8192
    elif billions <= 14:
        base = 16384
    else:
        base = 24576
    load_in_4bit = bool((profile.get("training") or {}).get("load_in_4bit", True))
    if not load_in_4bit:
        base = int(base * 1.75)
    return base


def _recommended_actions(
    repo_root: Path,
    profile_path: Path,
    plan: dict[str, Any],
    execution_target: str,
) -> list[dict[str, Any]]:
    cli_script = (repo_root / "scripts" / "scbe-system-cli.py").resolve()
    emit_path = Path(plan["default_emit_path"])
    if not emit_path.is_absolute():
        emit_path = (repo_root / emit_path).resolve()

    actions: list[dict[str, Any]] = [
        {
            "kind": "emit-script",
            "description": "Emit the runnable training script for this profile.",
            "command": [
                sys.executable,
                str(cli_script),
                "model",
                "train",
                "--profile-path",
                str(profile_path),
                "--emit-script",
                str(emit_path),
                "--json",
            ],
        }
    ]

    if execution_target == "local":
        actions.append(
            {
                "kind": "run-local",
                "description": "Run the emitted training script on the current machine.",
                "command": [sys.executable, str(emit_path)],
            }
        )
    elif execution_target == "colab":
        actions.append(
            {
                "kind": "colab-notebook",
                "description": "Resolve the repo's QLoRA Colab notebook lane for remote training.",
                "command": [
                    sys.executable,
                    str((repo_root / "scripts" / "system" / "colab_workflow_catalog.py").resolve()),
                    "show",
                    "qlora",
                    "--json",
                ],
            }
        )
    elif execution_target == "hf-jobs":
        actions.append(
            {
                "kind": "hf-host-inventory",
                "description": "Check the configured Hugging Face host route before dispatching the emitted script.",
                "command": [
                    "powershell",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str((repo_root / "scripts" / "system" / "model_host_quickcall.ps1").resolve()),
                    "-Action",
                    "inventory-hf",
                ],
            }
        )
    return actions


def _toolchain_status(
    repo_root: Path,
    profile_path: Path,
    profile: dict[str, Any],
    plan: dict[str, Any],
    execution_target: str,
) -> dict[str, Any]:
    emit_path = Path(plan["default_emit_path"])
    if not emit_path.is_absolute():
        emit_path = (repo_root / emit_path).resolve()

    catalog_path = (repo_root / "scripts" / "system" / "colab_workflow_catalog.py").resolve()
    host_quickcall_path = (repo_root / "scripts" / "system" / "model_host_quickcall.ps1").resolve()
    hf_loop_path = (repo_root / "scripts" / "hf_training_loop.py").resolve()
    cloud_bootstrap_path = (repo_root / "scripts" / "cloud_bootstrap_train.py").resolve()
    hf_cli = shutil.which("hf")
    ollama_cli = shutil.which("ollama")

    toolchain: dict[str, Any] = {
        "target": execution_target,
        "python": {
            "available": bool(sys.executable),
            "path": sys.executable,
        },
        "profile": {
            "path": str(profile_path),
            "exists": profile_path.exists(),
        },
        "emit_script": {
            "path": str(emit_path),
            "parent_exists": emit_path.parent.exists(),
        },
        "colab_catalog": {
            "path": str(catalog_path),
            "exists": catalog_path.exists(),
        },
        "model_host_quickcall": {
            "path": str(host_quickcall_path),
            "exists": host_quickcall_path.exists(),
        },
        "hf_training_loop": {
            "path": str(hf_loop_path),
            "exists": hf_loop_path.exists(),
        },
        "cloud_bootstrap_train": {
            "path": str(cloud_bootstrap_path),
            "exists": cloud_bootstrap_path.exists(),
        },
        "hf_cli": {
            "available": hf_cli is not None,
            "path": hf_cli or "",
        },
        "ollama": {
            "available": ollama_cli is not None,
            "path": ollama_cli or "",
        },
    }

    runtime = profile.get("runtime") or {}
    if isinstance(runtime, dict) and runtime:
        toolchain["runtime"] = {
            "provider": _coerce_string(runtime.get("provider"), ""),
            "model": _coerce_string(runtime.get("model"), ""),
            "base_url": _coerce_string(runtime.get("base_url"), ""),
        }

    if execution_target == "colab":
        qlora_notebook = (repo_root / "notebooks" / "colab_qlora_training.ipynb").resolve()
        finetune_notebook = (repo_root / "notebooks" / "scbe_finetune_colab.ipynb").resolve()
        toolchain["colab_notebooks"] = {
            "qlora": {
                "path": str(qlora_notebook),
                "exists": qlora_notebook.exists(),
            },
            "finetune": {
                "path": str(finetune_notebook),
                "exists": finetune_notebook.exists(),
            },
        }

    return toolchain


def build_training_preflight(repo_root: Path, profile_path: Path) -> dict[str, Any]:
    profile = load_profile(profile_path)
    plan = build_training_plan(repo_root, profile_path)

    dependencies = {
        name: _dependency_status(name)
        for name in ("datasets", "transformers", "trl", "unsloth")
    }
    torch_runtime = _inspect_torch_runtime()
    nvidia_smi = _inspect_nvidia_smi()
    token_env = _coerce_string(profile["hub"].get("token_env"), "HF_TOKEN")
    token_present = bool(os.environ.get(token_env, ""))
    minimum_local_vram_mb = _estimated_min_local_vram_mb(profile)

    local_blockers: list[str] = []
    if plan["missing_files"]:
        local_blockers.append("dataset-missing")
    missing_deps = [name for name, status in dependencies.items() if not status["available"]]
    if missing_deps:
        local_blockers.extend(f"missing-dependency:{name}" for name in missing_deps)
    if not torch_runtime.get("available", False):
        local_blockers.append("torch-unavailable")
    elif not torch_runtime.get("cuda_available", False):
        local_blockers.append("cuda-unavailable")
    detected_vram = int(torch_runtime.get("total_vram_mb") or nvidia_smi.get("total_vram_mb") or 0)
    if detected_vram and detected_vram < minimum_local_vram_mb:
        local_blockers.append(f"insufficient-vram:{detected_vram}<{minimum_local_vram_mb}")
    elif not detected_vram:
        local_blockers.append("vram-unknown")

    local_ready = not local_blockers
    hf_ready = bool(token_present and plan["ready"])
    recommended_target = _coerce_string(profile["execution"].get("recommended_target"), "local")
    recommended_target_key = recommended_target.lower()
    prefers_hf = "hf" in recommended_target_key or "huggingface" in recommended_target_key
    prefers_colab = "colab" in recommended_target_key
    execution_target = "local"
    rationale: list[str] = []
    if local_ready:
        execution_target = "local"
        rationale.append("local-environment-meets-profile-requirements")
    elif prefers_hf and hf_ready:
        execution_target = "hf-jobs"
        rationale.append("profile-prefers-hf-and-token-is-present")
    elif prefers_colab or "local" in recommended_target_key:
        execution_target = "colab"
        rationale.append("local-environment-is-underpowered-for-profile")
    elif hf_ready:
        execution_target = "hf-jobs"
        rationale.append("hf-token-present-and-local-environment-not-ready")
    else:
        execution_target = "emit-only"
        rationale.append("profile-can-emit-script-but-runtime-target-is-not-ready")
    if local_blockers:
        rationale.extend(local_blockers)
    if not token_present:
        rationale.append(f"missing-env:{token_env}")

    return {
        "schema_version": "scbe_model_preflight_v1",
        "profile_id": profile["profile_id"],
        "profile_path": str(profile_path),
        "backend": profile["backend"],
        "base_model": profile["base_model"],
        "plan_ready": plan["ready"],
        "recommended_target": recommended_target,
        "minimum_local_vram_mb": minimum_local_vram_mb,
        "dependencies": dependencies,
        "torch": torch_runtime,
        "nvidia_smi": nvidia_smi,
        "hub": {
            "token_env": token_env,
            "token_present": token_present,
        },
        "local": {
            "ready": local_ready,
            "detected_vram_mb": detected_vram,
            "blockers": local_blockers,
        },
        "decision": {
            "execution_target": execution_target,
            "rationale": rationale,
        },
        "toolchain": _toolchain_status(repo_root, profile_path, profile, plan, execution_target),
        "next_steps": _recommended_actions(repo_root, profile_path, plan, execution_target),
        "plan": plan,
    }

def _render_training_script(profile: dict[str, Any], plan: dict[str, Any]) -> str:
    profile_json = json.dumps(profile, indent=2, ensure_ascii=True)
    train_files_json = json.dumps([row["path"] for row in plan["train_datasets"] if row["exists"]], indent=2, ensure_ascii=True)
    eval_files_json = json.dumps([row["path"] for row in plan["eval_datasets"] if row["exists"]], indent=2, ensure_ascii=True)
    output_dir_literal = repr(plan["output_dir"])
    return f'''#!/usr/bin/env python3
"""Generated SCBE model training script."""

from __future__ import annotations

import json
import os
from pathlib import Path

PROFILE = json.loads(r"""{profile_json}""")
TRAIN_FILES = json.loads(r"""{train_files_json}""")
EVAL_FILES = json.loads(r"""{eval_files_json}""")
OUTPUT_DIR = Path({output_dir_literal})


def _load_chat_datasets():
    from datasets import concatenate_datasets, load_dataset

    def load_many(paths):
        bundles = [load_dataset("json", data_files=path, split="train") for path in paths]
        if not bundles:
            return None
        if len(bundles) == 1:
            return bundles[0]
        return concatenate_datasets(bundles)

    train_dataset = load_many(TRAIN_FILES)
    eval_dataset = load_many(EVAL_FILES)
    if train_dataset is None:
        raise RuntimeError("No training files were resolved for this profile.")
    return train_dataset, eval_dataset


def _format_records(dataset, tokenizer):
    system_prompt = PROFILE["system_prompt"]

    def convert(example):
        if "messages" in example and isinstance(example["messages"], list):
            messages = example["messages"]
            if not any(message.get("role") == "system" for message in messages):
                messages = [{{"role": "system", "content": system_prompt}}, *messages]
            return {{"text": tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)}}
        if "instruction" in example:
            user_content = str(example["instruction"])
            if example.get("input"):
                user_content += "\\n\\n" + str(example["input"])
            messages = [
                {{"role": "system", "content": system_prompt}},
                {{"role": "user", "content": user_content}},
                {{"role": "assistant", "content": str(example.get("output", example.get("response", "")))}} ,
            ]
            return {{"text": tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)}}
        if "prompt" in example:
            messages = [
                {{"role": "system", "content": system_prompt}},
                {{"role": "user", "content": str(example["prompt"])}},
                {{"role": "assistant", "content": str(example.get("completion", example.get("response", "")))}} ,
            ]
            return {{"text": tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)}}
        if "question" in example:
            messages = [
                {{"role": "system", "content": system_prompt}},
                {{"role": "user", "content": str(example["question"])}},
                {{"role": "assistant", "content": str(example.get("answer", ""))}},
            ]
            return {{"text": tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)}}
        if "text" in example:
            return {{"text": str(example["text"])}}
        raise ValueError(f"Unsupported record shape: {{list(example.keys())}}")

    return dataset.map(convert, remove_columns=dataset.column_names)


def main() -> int:
    from transformers import TrainingArguments
    from trl import SFTTrainer
    from unsloth import FastLanguageModel

    train_cfg = PROFILE["training"]
    hub_cfg = PROFILE["hub"]
    token_env = hub_cfg.get("token_env", "HF_TOKEN")
    hf_token = os.environ.get(token_env, "")

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=PROFILE["base_model"],
        max_seq_length=int(train_cfg.get("max_seq_length", 4096)),
        dtype=None,
        load_in_4bit=bool(train_cfg.get("load_in_4bit", True)),
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=int(train_cfg.get("lora_rank", 32)),
        lora_alpha=int(train_cfg.get("lora_alpha", 64)),
        lora_dropout=float(train_cfg.get("lora_dropout", 0.0)),
        target_modules=list(train_cfg.get("target_modules") or ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]),
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    train_dataset, eval_dataset = _load_chat_datasets()
    train_dataset = _format_records(train_dataset, tokenizer)
    if eval_dataset is not None:
        eval_dataset = _format_records(eval_dataset, tokenizer)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        dataset_text_field="text",
        max_seq_length=int(train_cfg.get("max_seq_length", 4096)),
        packing=bool(train_cfg.get("packing", True)),
        args=TrainingArguments(
            output_dir=str(OUTPUT_DIR),
            report_to="none",
            num_train_epochs=float(train_cfg.get("num_train_epochs", 1)),
            max_steps=int(train_cfg.get("max_steps", -1)),
            warmup_ratio=float(train_cfg.get("warmup_ratio", 0.05)),
            per_device_train_batch_size=int(train_cfg.get("batch_size", 2)),
            gradient_accumulation_steps=int(train_cfg.get("gradient_accumulation_steps", 8)),
            learning_rate=float(train_cfg.get("learning_rate", 2e-4)),
            optim=str(train_cfg.get("optim", "adamw_8bit")),
            weight_decay=float(train_cfg.get("weight_decay", 0.01)),
            lr_scheduler_type=str(train_cfg.get("lr_scheduler_type", "cosine")),
            logging_steps=int(train_cfg.get("logging_steps", 25)),
            save_strategy=str(train_cfg.get("save_strategy", "steps")),
            save_steps=int(train_cfg.get("save_steps", 500)),
            save_total_limit=int(train_cfg.get("save_total_limit", 2)),
            gradient_checkpointing=True,
            dataloader_num_workers=int(train_cfg.get("dataloader_num_workers", 2)),
            seed=int(train_cfg.get("seed", 42)),
        ),
    )
    stats = trainer.train()
    lora_dir = OUTPUT_DIR / "lora"
    model.save_pretrained(str(lora_dir))
    tokenizer.save_pretrained(str(lora_dir))

    if hub_cfg.get("push_adapter") and hub_cfg.get("adapter_repo") and hf_token:
        model.push_to_hub(str(hub_cfg["adapter_repo"]), token=hf_token)
        tokenizer.push_to_hub(str(hub_cfg["adapter_repo"]), token=hf_token)

    summary = {{
        "profile_id": PROFILE["profile_id"],
        "base_model": PROFILE["base_model"],
        "train_rows": len(train_dataset),
        "eval_rows": len(eval_dataset) if eval_dataset is not None else 0,
        "output_dir": str(OUTPUT_DIR),
        "global_step": int(getattr(stats, "global_step", 0)),
        "training_loss": float(getattr(stats, "training_loss", 0.0)),
    }}
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def emit_training_script(repo_root: Path, profile_path: Path, output_path: Path | None = None) -> tuple[Path, dict[str, Any]]:
    profile = load_profile(profile_path)
    plan = build_training_plan(repo_root, profile_path)
    target = output_path or Path(plan["default_emit_path"])
    if not target.is_absolute():
        target = (repo_root / target).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_render_training_script(profile, plan), encoding="utf-8")
    return target, plan


