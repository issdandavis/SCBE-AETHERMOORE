#!/usr/bin/env python3
"""Dispatch a real SCBE coding-agent LoRA training job through Hugging Face Jobs."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROFILE = REPO_ROOT / "config" / "model_training" / "coding-agent-qwen-smoke.json"
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "hf_coding_agent_jobs"
ENV_FILE = REPO_ROOT / "config" / "connector_oauth" / ".env.connector.oauth"


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_env_file(path: Path = ENV_FILE) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _load_profile(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("profile must be a JSON object")
    return payload


def _count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _dataset_rows(profile: dict[str, Any], split: str) -> list[dict[str, Any]]:
    dataset = profile.get("dataset") or {}
    root = REPO_ROOT / str(dataset.get("root", "training-data/sft"))
    names = dataset.get("train_files" if split == "train" else "eval_files") or []
    rows = []
    for name in names:
        rel = f"{dataset.get('root', 'training-data/sft')}/{name}".replace("\\", "/")
        path = root / str(name)
        rows.append(
            {
                "name": str(name),
                "path": str(path),
                "exists": path.exists(),
                "row_count": _count_jsonl(path),
                "repo_path": rel,
            }
        )
    return rows


def render_uv_training_script(profile: dict[str, Any]) -> str:
    profile_json = json.dumps(profile, indent=2, ensure_ascii=True)
    dataset = profile.get("dataset") or {}
    hub_cfg = profile.get("hub") or {}
    dataset_repo = str(hub_cfg.get("dataset_repo", "issdandavis/scbe-coding-agent-sft"))
    train_files = [str(name) for name in dataset.get("train_files", [])]
    eval_files = [str(name) for name in dataset.get("eval_files", [])]
    return f'''# /// script
# dependencies = [
#   "accelerate>=0.34.0",
#   "datasets>=2.20.0",
#   "peft>=0.12.0",
#   "torch",
#   "transformers>=4.46.0",
#   "huggingface_hub>=0.25.0"
# ]
# ///
from __future__ import annotations

import json
import os
import random
from pathlib import Path

import torch
from datasets import Dataset
from huggingface_hub import hf_hub_download, whoami
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer, DataCollatorForLanguageModeling, Trainer, TrainingArguments

PROFILE = json.loads(r"""{profile_json}""")
DATASET_REPO = {dataset_repo!r}
TRAIN_FILES = {json.dumps(train_files, indent=2)}
EVAL_FILES = {json.dumps(eval_files, indent=2)}
WORKDIR = Path("/tmp/scbe-coding-agent")
WORKDIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")


def _token() -> str:
    token_env = str((PROFILE.get("hub") or {{}}).get("token_env", "HF_TOKEN"))
    token = os.environ.get(token_env, "").strip() or os.environ.get("HUGGING_FACE_HUB_TOKEN", "").strip()
    if not token:
        raise RuntimeError(f"Missing Hugging Face token in ${{token_env}} or $HUGGING_FACE_HUB_TOKEN")
    os.environ.setdefault("HUGGING_FACE_HUB_TOKEN", token)
    return token


def _load_jsonl_files(files: list[str], split: str, token: str) -> list[dict]:
    rows = []
    for name in files:
        local_path = hf_hub_download(
            repo_id=DATASET_REPO,
            filename=name,
            repo_type="dataset",
            token=token,
            local_dir=WORKDIR / "hub-data",
        )
        with open(local_path, "r", encoding="utf-8") as handle:
            for line in handle:
                raw = line.strip()
                if raw:
                    rows.append(json.loads(raw))
    if not rows:
        raise RuntimeError(f"No {{split}} files configured")
    return rows


def _messages_to_text(row: dict, tokenizer) -> str:
    system_prompt = str(PROFILE.get("system_prompt", "You are a coding assistant."))
    if isinstance(row.get("messages"), list):
        messages = list(row["messages"])
        if not any(item.get("role") == "system" for item in messages if isinstance(item, dict)):
            messages = [{{"role": "system", "content": system_prompt}}, *messages]
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    if "instruction" in row:
        prompt = str(row["instruction"])
        if row.get("input"):
            prompt += "\\n\\n" + str(row["input"])
        messages = [
            {{"role": "system", "content": system_prompt}},
            {{"role": "user", "content": prompt}},
            {{"role": "assistant", "content": str(row.get("output", row.get("response", "")))}},
        ]
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    if "prompt" in row:
        messages = [
            {{"role": "system", "content": system_prompt}},
            {{"role": "user", "content": str(row["prompt"])}},
            {{"role": "assistant", "content": str(row.get("completion", row.get("response", "")))}},
        ]
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    return str(row.get("text", ""))


def _build_dataset(source, tokenizer, limit: int, seed: int) -> Dataset:
    rows = list(source)
    random.Random(seed).shuffle(rows)
    if limit > 0:
        rows = rows[:limit]
    texts = [_messages_to_text(row, tokenizer) for row in rows]
    return Dataset.from_dict({{"text": texts}})


def main() -> None:
    token = _token()
    train_cfg = PROFILE.get("training") or {{}}
    hub_cfg = PROFILE.get("hub") or {{}}
    seed = int(train_cfg.get("seed", 42))
    max_length = int(train_cfg.get("max_seq_length", 1024))
    base_model = str(PROFILE["base_model"])
    adapter_repo = str(hub_cfg["adapter_repo"])

    print(json.dumps({{"event": "auth", "whoami": whoami(token=token).get("name", "unknown")}}))
    tokenizer = AutoTokenizer.from_pretrained(base_model, token=token)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        token=token,
        torch_dtype=dtype if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None,
    )
    model.config.use_cache = False
    if bool(train_cfg.get("gradient_checkpointing", False)) and hasattr(model, "gradient_checkpointing_enable"):
        model.gradient_checkpointing_enable()
    model = get_peft_model(
        model,
        LoraConfig(
            r=int(train_cfg.get("lora_rank", 16)),
            lora_alpha=int(train_cfg.get("lora_alpha", 32)),
            lora_dropout=float(train_cfg.get("lora_dropout", 0.05)),
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=list(train_cfg.get("target_modules") or ["q_proj", "k_proj", "v_proj", "o_proj"]),
        ),
    )
    model.print_trainable_parameters()

    train_rows = _load_jsonl_files(TRAIN_FILES, "train", token)
    eval_rows = _load_jsonl_files(EVAL_FILES, "eval", token) if EVAL_FILES else None
    train_ds = _build_dataset(train_rows, tokenizer, int(train_cfg.get("max_train_records", 1200)), seed)
    eval_ds = _build_dataset(eval_rows, tokenizer, int(train_cfg.get("max_eval_records", 120)), seed) if eval_rows is not None else None

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=max_length)

    train_tok = train_ds.map(tokenize, batched=True, remove_columns=["text"])
    eval_tok = eval_ds.map(tokenize, batched=True, remove_columns=["text"]) if eval_ds is not None else None

    out_dir = WORKDIR / "adapter"
    args = TrainingArguments(
        output_dir=str(WORKDIR / "checkpoints"),
        max_steps=int(train_cfg.get("max_steps", 120)),
        num_train_epochs=float(train_cfg.get("num_train_epochs", 1)),
        per_device_train_batch_size=int(train_cfg.get("batch_size", 2)),
        gradient_accumulation_steps=int(train_cfg.get("gradient_accumulation_steps", 8)),
        learning_rate=float(train_cfg.get("learning_rate", 2e-4)),
        warmup_ratio=float(train_cfg.get("warmup_ratio", 0.05)),
        logging_steps=int(train_cfg.get("logging_steps", 10)),
        save_steps=int(train_cfg.get("save_steps", 60)),
        save_total_limit=int(train_cfg.get("save_total_limit", 2)),
        fp16=torch.cuda.is_available() and dtype == torch.float16,
        bf16=torch.cuda.is_available() and dtype == torch.bfloat16,
        gradient_checkpointing=bool(train_cfg.get("gradient_checkpointing", False)),
        report_to=[],
        remove_unused_columns=False,
        seed=seed,
    )
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_tok,
        eval_dataset=eval_tok,
        data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
    )
    stats = trainer.train()
    model.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)
    if hub_cfg.get("push_adapter", True):
        model.push_to_hub(adapter_repo, token=token)
        tokenizer.push_to_hub(adapter_repo, token=token)
    summary = {{
        "profile_id": PROFILE["profile_id"],
        "base_model": base_model,
        "adapter_repo": adapter_repo,
        "dataset_repo": DATASET_REPO,
        "train_rows_loaded": len(train_rows),
        "train_rows_used": len(train_ds),
        "eval_rows_used": len(eval_ds) if eval_ds is not None else 0,
        "global_step": int(getattr(stats, "global_step", 0)),
        "training_loss": float(getattr(stats, "training_loss", 0.0)),
        "pushed_adapter": bool(hub_cfg.get("push_adapter", True)),
    }}
    print(json.dumps({{"event": "training_complete", "summary": summary}}, indent=2))


if __name__ == "__main__":
    main()
'''


def build_packet(
    *,
    profile_path: Path = DEFAULT_PROFILE,
    artifact_root: Path = ARTIFACT_ROOT,
    flavor: str | None = None,
    timeout: str | None = None,
) -> dict[str, Any]:
    _load_env_file()
    profile = _load_profile(profile_path)
    execution = profile.get("execution") or {}
    stamp = _utc_stamp()
    run_dir = artifact_root / str(profile["profile_id"]) / stamp
    script_path = run_dir / "train_coding_agent_hf.py"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(render_uv_training_script(profile), encoding="utf-8")

    selected_flavor = flavor or str(execution.get("hf_flavor", "t4-small"))
    selected_timeout = timeout or str(execution.get("timeout", "2h"))
    command = [
        "hf",
        "jobs",
        "uv",
        "run",
        "--flavor",
        selected_flavor,
        "--timeout",
        selected_timeout,
        "--env",
        "PYTHONIOENCODING=utf-8",
        "--env",
        "PYTHONUTF8=1",
        "--secrets",
        str((profile.get("hub") or {}).get("token_env", "HF_TOKEN")),
        "--detach",
        str(script_path),
    ]
    packet = {
        "schema_version": "scbe_coding_agent_hf_job_packet_v1",
        "prepared_at_utc": stamp,
        "profile_id": profile["profile_id"],
        "profile_path": str(profile_path),
        "run_dir": str(run_dir),
        "script_path": str(script_path),
        "base_model": profile["base_model"],
        "adapter_repo": (profile.get("hub") or {}).get("adapter_repo", ""),
        "train_datasets": _dataset_rows(profile, "train"),
        "eval_datasets": _dataset_rows(profile, "eval"),
        "hf": {
            "flavor": selected_flavor,
            "timeout": selected_timeout,
            "cli": shutil.which("hf") or "",
            "token_present": bool(os.environ.get(str((profile.get("hub") or {}).get("token_env", "HF_TOKEN")), "")),
        },
        "command": command,
        "dispatched": False,
    }
    _write_json(run_dir / "job_packet.json", packet)
    (run_dir / "RUN.md").write_text(_render_run_note(packet), encoding="utf-8")
    return packet


def _render_run_note(packet: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# Coding Agent HF Job - {packet['profile_id']}",
            "",
            f"- Base model: `{packet['base_model']}`",
            f"- Adapter repo: `{packet['adapter_repo']}`",
            f"- Script: `{packet['script_path']}`",
            f"- Packet: `{Path(packet['run_dir']) / 'job_packet.json'}`",
            "",
            "## Dispatch Command",
            "",
            "```powershell",
            " ".join(packet["command"]),
            "```",
            "",
            "## Monitor",
            "",
            "```powershell",
            "hf jobs ps",
            "hf jobs logs <job-id>",
            "```",
        ]
    )


def upload_training_dataset(profile: dict[str, Any]) -> list[dict[str, Any]]:
    hub_cfg = profile.get("hub") or {}
    dataset_cfg = profile.get("dataset") or {}
    dataset_repo = str(hub_cfg.get("dataset_repo", "")).strip()
    if not dataset_repo:
        raise RuntimeError("hub.dataset_repo is required for HF Jobs training")
    root = REPO_ROOT / str(dataset_cfg.get("root", "training-data/sft"))
    names = [*list(dataset_cfg.get("train_files", [])), *list(dataset_cfg.get("eval_files", []))]
    uploads: list[dict[str, Any]] = []
    for name in names:
        local_path = root / str(name)
        if not local_path.exists():
            raise FileNotFoundError(local_path)
        command = [
            "hf",
            "upload",
            dataset_repo,
            str(local_path),
            str(name),
            "--repo-type",
            "dataset",
            "--private",
            "--commit-message",
            f"Update SCBE coding agent data {name}",
        ]
        result = subprocess.run(command, cwd=str(REPO_ROOT), capture_output=True, text=True, check=False)
        uploads.append(
            {
                "name": str(name),
                "returncode": result.returncode,
                "stdout": result.stdout.strip()[-1000:],
                "stderr": result.stderr.strip()[-1000:],
            }
        )
        if result.returncode != 0:
            raise RuntimeError(f"Dataset upload failed for {name}: {result.stderr.strip()}")
    return uploads


def dispatch_packet(packet: dict[str, Any]) -> dict[str, Any]:
    if not packet["hf"]["cli"]:
        raise RuntimeError("hf CLI is not available")
    if not packet["hf"]["token_present"]:
        raise RuntimeError("HF token is not available in the configured environment")
    profile = _load_profile(Path(packet["profile_path"]))
    uploads = upload_training_dataset(profile)
    result = subprocess.run(packet["command"], cwd=str(REPO_ROOT), capture_output=True, text=True, check=False)
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    job_id = ""
    match = re.search(r"(?:Job ID|ID|job)[^A-Za-z0-9_-]*([A-Za-z0-9_-]{8,})", stdout + "\n" + stderr, re.IGNORECASE)
    if match:
        job_id = match.group(1)
    updated = {
        **packet,
        "dispatched": result.returncode == 0,
        "dispatch": {
            "returncode": result.returncode,
            "stdout": stdout[-4000:],
            "stderr": stderr[-4000:],
            "job_id": job_id,
        },
        "dataset_uploads": uploads,
    }
    _write_json(Path(packet["run_dir"]) / "job_packet.json", updated)
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "dispatch"):
        item = sub.add_parser(name)
        item.add_argument("--profile-path", default=str(DEFAULT_PROFILE))
        item.add_argument("--artifact-root", default=str(ARTIFACT_ROOT))
        item.add_argument("--flavor", default="")
        item.add_argument("--timeout", default="")
        item.add_argument("--json", action="store_true")
    status = sub.add_parser("status")
    status.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.command == "status":
        result = subprocess.run(["hf", "jobs", "ps"], cwd=str(REPO_ROOT), capture_output=True, text=True, check=False)
        payload = {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    else:
        packet = build_packet(
            profile_path=Path(args.profile_path),
            artifact_root=Path(args.artifact_root),
            flavor=args.flavor or None,
            timeout=args.timeout or None,
        )
        payload = dispatch_packet(packet) if args.command == "dispatch" else packet

    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2, ensure_ascii=True))
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
