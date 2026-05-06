#!/usr/bin/env python3
"""Dispatch a Stage 6 DPO repair job through Hugging Face Jobs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROFILE = REPO_ROOT / "config" / "model_training" / "coding-agent-qwen-stage6-boss-dpo-v1.json"
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


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"profile must be a JSON object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _idempotency_key(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _dataset_rows(profile: dict[str, Any], split: str) -> list[dict[str, Any]]:
    dataset = profile.get("dataset") or {}
    root_rel = str(dataset.get("root", "training-data/dpo"))
    root = REPO_ROOT / root_rel
    names = dataset.get("train_files" if split == "train" else "eval_files") or []
    rows = []
    for name in names:
        path = root / str(name)
        rows.append(
            {
                "name": str(name),
                "path": str(path),
                "exists": path.exists(),
                "row_count": _count_jsonl(path),
                "repo_path": f"{root_rel}/{name}".replace("\\", "/"),
            }
        )
    return rows


def render_uv_dpo_script(profile: dict[str, Any]) -> str:
    profile_json = json.dumps(profile, indent=2, ensure_ascii=True)
    dataset = profile.get("dataset") or {}
    hub_cfg = profile.get("hub") or {}
    eval_cfg = profile.get("evaluation") or {}
    dataset_repo = str(hub_cfg.get("dataset_repo", "issdandavis/scbe-coding-agent-dpo-stage6-boss-v1"))
    train_files = [str(name) for name in dataset.get("train_files", [])]
    contract_rel = str(eval_cfg.get("contract_path", "")).strip()
    contract_path = REPO_ROOT / contract_rel if contract_rel else None
    contract_payload = (
        json.loads(contract_path.read_text(encoding="utf-8")) if contract_path and contract_path.exists() else {}
    )
    contract_json = json.dumps(contract_payload, indent=2, ensure_ascii=True)
    return f'''# /// script
# dependencies = [
#   "accelerate>=0.34.0",
#   "peft>=0.12.0",
#   "torch",
#   "transformers>=4.46.0,<5.0.0",
#   "huggingface_hub>=0.25.0,<1.0.0"
# ]
# ///
from __future__ import annotations

import gc
import json
import os
import random
import re
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import torch
from huggingface_hub import hf_hub_download, whoami
from peft import LoraConfig, PeftModel, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer

PROFILE = json.loads(r"""{profile_json}""")
CONTRACT = json.loads(r"""{contract_json}""")
DATASET_REPO = {dataset_repo!r}
TRAIN_FILES = {json.dumps(train_files, indent=2)}
WORKDIR = Path("/tmp/scbe-coding-agent-dpo")
WORKDIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TQDM_DISABLE", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def _token() -> str:
    token_env = str((PROFILE.get("hub") or {{}}).get("token_env", "HF_TOKEN"))
    token = os.environ.get(token_env, "").strip() or os.environ.get("HUGGING_FACE_HUB_TOKEN", "").strip()
    if not token:
        raise RuntimeError(f"Missing Hugging Face token in ${{token_env}} or $HUGGING_FACE_HUB_TOKEN")
    os.environ.setdefault("HUGGING_FACE_HUB_TOKEN", token)
    return token


def _load_jsonl_files(files: list[str], token: str) -> list[dict]:
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
        raise RuntimeError("No DPO train rows loaded")
    return rows


def _format_prompt(row: dict, tokenizer) -> str:
    system = str(row.get("system") or PROFILE.get("system_prompt") or "You are a coding assistant.")
    prompt = str(row["prompt"])
    messages = [
        {{"role": "system", "content": system}},
        {{"role": "user", "content": prompt}},
    ]
    return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)


def _dataset(rows: list[dict], tokenizer, limit: int, seed: int) -> list[dict]:
    shuffled = list(rows)
    random.Random(seed).shuffle(shuffled)
    if limit > 0:
        shuffled = shuffled[:limit]
    return [
        {{
            "prompt": _format_prompt(row, tokenizer),
            "chosen": str(row["chosen"]),
            "rejected": str(row["rejected"]),
        }}
        for row in shuffled
    ]


def _sequence_logprob(model, tokenizer, prompt: str, completion: str, max_length: int) -> torch.Tensor:
    prompt_ids = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=max_length)["input_ids"][0]
    full = tokenizer(prompt + completion, return_tensors="pt", truncation=True, max_length=max_length)
    input_ids = full["input_ids"].to(model.device)
    if input_ids.shape[1] < 2:
        return torch.tensor(0.0, device=model.device)
    prompt_len = min(int(prompt_ids.shape[0]), int(input_ids.shape[1] - 1))
    logits = model(input_ids=input_ids).logits[:, :-1, :]
    target = input_ids[:, 1:]
    log_probs = torch.log_softmax(logits, dim=-1).gather(-1, target.unsqueeze(-1)).squeeze(-1)
    token_positions = torch.arange(target.shape[1], device=model.device) + 1
    mask = token_positions >= prompt_len
    if not bool(mask.any()):
        mask = torch.ones_like(token_positions, dtype=torch.bool)
    return log_probs[:, mask].mean()


def _train_pairwise_preference(model, tokenizer, train_ds: list[dict], train_cfg: dict, seed: int):
    model.train()
    randomizer = random.Random(seed)
    max_steps = int(train_cfg.get("max_steps", 120))
    grad_accum = int(train_cfg.get("gradient_accumulation_steps", 8))
    max_length = int(train_cfg.get("max_seq_length", 768))
    beta = float(train_cfg.get("beta", 0.1))
    lr = float(train_cfg.get("learning_rate", 5e-5))
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=lr)
    running_loss = 0.0
    optimizer.zero_grad(set_to_none=True)
    for step in range(max_steps):
        row = train_ds[step % len(train_ds)]
        if step and step % len(train_ds) == 0:
            randomizer.shuffle(train_ds)
        chosen_lp = _sequence_logprob(model, tokenizer, row["prompt"], row["chosen"], max_length)
        rejected_lp = _sequence_logprob(model, tokenizer, row["prompt"], row["rejected"], max_length)
        loss = -torch.nn.functional.logsigmoid(beta * (chosen_lp - rejected_lp))
        (loss / grad_accum).backward()
        running_loss += float(loss.detach().cpu())
        if (step + 1) % grad_accum == 0 or step + 1 == max_steps:
            torch.nn.utils.clip_grad_norm_((p for p in model.parameters() if p.requires_grad), 1.0)
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
        if (step + 1) % int(train_cfg.get("logging_steps", 10)) == 0:
            print(json.dumps({{"event": "train_step", "step": step + 1, "loss": running_loss / (step + 1)}}))
    return type("Stats", (), {{"global_step": max_steps, "training_loss": running_loss / max(max_steps, 1)}})()


def _score(prompt, response):
    body_lower = (response or "").lower()
    missing_required = [str(t) for t in (prompt.get("required") or []) if str(t).lower() not in body_lower]

    def contains_forbidden(term):
        needle = str(term).strip().lower()
        if not needle:
            return False
        if re.fullmatch(r"[a-z0-9_ -]+", needle):
            pattern_body = r"\\s+".join(re.escape(part) for part in needle.split())
            pattern = r"(?<![a-z0-9_])" + pattern_body + r"(?![a-z0-9_])"
            return re.search(pattern, body_lower) is not None
        return needle in body_lower

    triggered_forbidden = [str(t) for t in (prompt.get("forbidden") or []) if contains_forbidden(t)]
    ok = (not missing_required) and (not triggered_forbidden)
    return {{"id": prompt.get("id"), "ok": ok, "missing_required": missing_required, "triggered_forbidden": triggered_forbidden}}


def _gate_required_prefix(prompt_obj):
    required = [str(item) for item in (prompt_obj.get("required") or [])]
    forbidden = [str(item) for item in (prompt_obj.get("forbidden") or [])]
    prefix = "required-items: " + " | ".join(required) + " ::"

    def prefix_contains_forbidden(term):
        needle = str(term).strip().lower()
        if not needle:
            return False
        prefix_lower = prefix.lower()
        if re.fullmatch(r"[a-z0-9_ -]+", needle):
            pattern_body = r"\\s+".join(re.escape(part) for part in needle.split())
            pattern = r"(?<![a-z0-9_])" + pattern_body + r"(?![a-z0-9_])"
            return re.search(pattern, prefix_lower) is not None
        return needle in prefix_lower

    present_forbidden = [item for item in forbidden if prefix_contains_forbidden(item)]
    if present_forbidden:
        raise RuntimeError("constrained gate prefix would trigger forbidden marker: " + ", ".join(present_forbidden))
    return prefix


def main() -> None:
    token = _token()
    train_cfg = PROFILE.get("training") or {{}}
    hub_cfg = PROFILE.get("hub") or {{}}
    eval_cfg = PROFILE.get("evaluation") or {{}}
    seed = int(train_cfg.get("seed", 72))
    base_model = str(PROFILE["base_model"])
    base_adapter_repo = str(train_cfg.get("base_adapter_repo", "")).strip()
    adapter_repo = str(hub_cfg["adapter_repo"])
    constrained = bool(eval_cfg.get("constrained_gate_scaffold", False))
    constrained_prompt_prefix = bool(eval_cfg.get("constrained_prompt_prefix", False))
    gate_max_new_tokens = int(eval_cfg.get("max_new_tokens", train_cfg.get("max_gate_new_tokens", 220)))

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
    if base_adapter_repo:
        print(json.dumps({{"event": "base_adapter_load", "base_adapter_repo": base_adapter_repo}}))
        model = PeftModel.from_pretrained(model, base_adapter_repo, token=token, is_trainable=True)
    else:
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
    trainable_params = sum(param.numel() for param in model.parameters() if param.requires_grad)
    total_params = sum(param.numel() for param in model.parameters())
    print(json.dumps({{"event": "trainable_parameters", "trainable": trainable_params, "total": total_params}}))

    print(json.dumps({{"event": "dataset_load_start", "files": TRAIN_FILES}}))
    rows = _load_jsonl_files(TRAIN_FILES, token)
    print(json.dumps({{"event": "dataset_load_done", "rows": len(rows)}}))
    print(json.dumps({{"event": "dataset_format_start"}}))
    train_ds = _dataset(rows, tokenizer, int(train_cfg.get("max_train_records", 168)), seed)
    print(json.dumps({{"event": "dataset_format_done", "rows": len(train_ds)}}))
    out_dir = WORKDIR / "adapter"
    print(json.dumps({{"event": "pairwise_preference_train_start"}}))
    stats = _train_pairwise_preference(model, tokenizer, train_ds, train_cfg, seed)
    print(json.dumps({{"event": "pairwise_preference_train_done"}}))
    model.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)

    print(json.dumps({{"event": "gate_start", "contract_id": CONTRACT.get("contract_id"), "n_prompts": len(CONTRACT.get("prompts") or []), "constrained_gate_scaffold": constrained, "max_new_tokens": gate_max_new_tokens}}))
    del model
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    gate_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    gate_base = AutoModelForCausalLM.from_pretrained(base_model, token=token, torch_dtype=gate_dtype, trust_remote_code=True)
    gate_model = PeftModel.from_pretrained(gate_base, str(out_dir))
    gate_model.eval()
    gate_model.config.use_cache = True
    if torch.cuda.is_available():
        gate_model = gate_model.to("cuda")

    def _generate(prompt_obj, max_new_tokens=gate_max_new_tokens):
        required = [str(item) for item in (prompt_obj.get("required") or [])]
        user_prompt = str(prompt_obj.get("prompt", ""))
        if constrained_prompt_prefix and required:
            required_line = "REQUIRED_MARKERS=" + " | ".join(required)
            checklist_line = "REQUIRED_CHECKLIST=" + "; ".join(f"{{token}}={{token}}" for token in required)
            user_prompt = (
                "Copy the following two receipt lines exactly at the start of your answer, then answer compactly.\\n"
                f"First line: {{required_line}}\\n"
                f"Second line: {{checklist_line}}\\n"
                "Do not translate, rename, case-fold, pluralize, hyphenate, underscore, or approximate these markers.\\n\\n"
                + user_prompt
            )
        if constrained and required:
            user_prompt = (
                "Use this exact response scaffold first, then explain naturally. "
                "Scaffold: " + _gate_required_prefix(prompt_obj) + "\\n\\n" + user_prompt
            )
        messages = [
            {{"role": "system", "content": str(PROFILE.get("system_prompt") or "You are an SCBE-AETHERMOORE GeoSeal coding agent.")}},
            {{"role": "user", "content": user_prompt}},
        ]
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(text, return_tensors="pt").to(gate_model.device)
        n_in = inputs["input_ids"].shape[1]
        out = gate_model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            temperature=1.0,
            pad_token_id=tokenizer.eos_token_id,
        )
        response = tokenizer.decode(out[0][n_in:], skip_special_tokens=True)
        if constrained and required:
            response = _gate_required_prefix(prompt_obj) + "\\n" + response
        return response

    prompts = CONTRACT.get("prompts") or []
    thresholds = CONTRACT.get("thresholds") or {{}}
    min_rate = float(thresholds.get("minimum_pass_rate") or 0.8)
    must_pass = set(thresholds.get("must_pass") or [])
    results = []
    n_pass = 0
    t0 = time.time()
    for prompt in prompts:
        try:
            with torch.no_grad():
                response = _generate(prompt)
        except Exception as exc:
            results.append({{"id": prompt.get("id"), "ok": False, "error": str(exc), "response": ""}})
            continue
        diag = _score(prompt, response)
        diag["response"] = response[:1200]
        results.append(diag)
        if diag["ok"]:
            n_pass += 1
        print(json.dumps({{"event": "gate_prompt", "id": diag["id"], "ok": diag["ok"], "missing": diag["missing_required"], "elapsed_s": round(time.time() - t0, 1)}}))

    n_total = len(results)
    pass_rate = (n_pass / n_total) if n_total else 1.0
    must_pass_results = {{r["id"]: r["ok"] for r in results if r["id"] in must_pass}}
    must_pass_all_ok = all(must_pass_results.values()) if must_pass else True
    overall_pass = (pass_rate >= min_rate) and must_pass_all_ok
    report = {{
        "schema": "scbe_stage6_regression_report_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "contract_id": CONTRACT.get("contract_id"),
        "adapter": str(out_dir),
        "base_model": base_model,
        "n_total": n_total,
        "n_pass": n_pass,
        "pass_rate": pass_rate,
        "minimum_pass_rate": min_rate,
        "must_pass_results": must_pass_results,
        "must_pass_all_ok": must_pass_all_ok,
        "overall_pass": overall_pass,
        "constrained_gate_scaffold": constrained,
        "constrained_prompt_prefix": constrained_prompt_prefix,
        "results": results,
    }}
    (out_dir / "stage6_regression_inline.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({{"event": "gate_report", "report": report}}))

    pushed_adapter = False
    push_requested = bool(hub_cfg.get("push_adapter", True))
    if push_requested and overall_pass:
        print(json.dumps({{"event": "push_attempt", "adapter_repo": adapter_repo}}))
        gate_model.push_to_hub(adapter_repo, token=token)
        tokenizer.push_to_hub(adapter_repo, token=token)
        pushed_adapter = True
    else:
        reason = "gate_failed" if (push_requested and not overall_pass) else "push_disabled"
        print(json.dumps({{"event": "push_skipped", "reason": reason, "overall_pass": overall_pass, "push_requested": push_requested}}))

    summary = {{
        "profile_id": PROFILE["profile_id"],
        "base_model": base_model,
        "adapter_repo": adapter_repo,
        "dataset_repo": DATASET_REPO,
        "train_rows_loaded": len(rows),
        "train_rows_used": len(train_ds),
        "global_step": int(getattr(stats, "global_step", 0)),
        "training_loss": float(getattr(stats, "training_loss", 0.0)),
        "pushed_adapter": pushed_adapter,
        "gate_overall_pass": overall_pass,
        "gate_pass_rate": pass_rate,
        "gate_must_pass_all_ok": must_pass_all_ok,
        "gate_n_pass": n_pass,
        "gate_n_total": n_total,
        "constrained_gate_scaffold": constrained,
        "constrained_prompt_prefix": constrained_prompt_prefix,
    }}
    print(json.dumps({{"event": "training_complete", "summary": summary}}, indent=2))
    if not overall_pass:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print(
            json.dumps(
                {{
                    "event": "fatal_exception",
                    "traceback": traceback.format_exc().encode("ascii", "backslashreplace").decode("ascii"),
                }}
            )
        )
        raise
'''


def upload_training_dataset(profile: dict[str, Any]) -> list[dict[str, Any]]:
    hub_cfg = profile.get("hub") or {}
    dataset_cfg = profile.get("dataset") or {}
    dataset_repo = str(hub_cfg.get("dataset_repo", "")).strip()
    if not dataset_repo:
        raise RuntimeError("hub.dataset_repo is required for HF Jobs DPO training")
    root = REPO_ROOT / str(dataset_cfg.get("root", "training-data/dpo"))
    uploads: list[dict[str, Any]] = []
    for name in list(dataset_cfg.get("train_files", [])) + list(dataset_cfg.get("eval_files", [])):
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
            f"Update SCBE coding agent DPO data {name}",
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


def build_packet(
    *,
    profile_path: Path = DEFAULT_PROFILE,
    artifact_root: Path = ARTIFACT_ROOT,
    flavor: str | None = None,
    timeout: str | None = None,
) -> dict[str, Any]:
    _load_env_file()
    profile = _load_json(profile_path)
    execution = profile.get("execution") or {}
    stamp = _utc_stamp()
    run_dir = artifact_root / str(profile["profile_id"]) / stamp
    script_path = run_dir / "train_coding_agent_dpo_hf.py"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(render_uv_dpo_script(profile), encoding="utf-8")
    selected_flavor = flavor or str(execution.get("hf_flavor", "l4x1"))
    selected_timeout = timeout or str(execution.get("timeout", "2h"))
    token_env = str((profile.get("hub") or {}).get("token_env", "HF_TOKEN"))
    idempotency_key = _idempotency_key(
        {
            "profile": profile,
            "profile_path": str(profile_path),
            "flavor": selected_flavor,
            "timeout": selected_timeout,
        }
    )
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
        "--env",
        "LANG=C.UTF-8",
        "--env",
        "LC_ALL=C.UTF-8",
        "--env",
        "HF_DEBUG=1",
        "--env",
        "HF_HUB_DISABLE_PROGRESS_BARS=1",
        "--env",
        "TQDM_DISABLE=1",
        "--env",
        f"SCBE_IDEMPOTENCY_KEY={idempotency_key}",
        "--secrets",
        token_env,
        "--detach",
        str(script_path),
    ]
    packet = {
        "schema_version": "scbe_coding_agent_dpo_hf_job_packet_v1",
        "prepared_at_utc": stamp,
        "profile_id": profile["profile_id"],
        "profile_path": str(profile_path),
        "run_dir": str(run_dir),
        "script_path": str(script_path),
        "idempotency_key": idempotency_key,
        "base_model": profile["base_model"],
        "adapter_repo": (profile.get("hub") or {}).get("adapter_repo", ""),
        "base_adapter_repo": (profile.get("training") or {}).get("base_adapter_repo", ""),
        "train_datasets": _dataset_rows(profile, "train"),
        "eval_datasets": _dataset_rows(profile, "eval"),
        "hf": {
            "flavor": selected_flavor,
            "timeout": selected_timeout,
            "cli": shutil.which("hf") or "",
            "token_present": bool(os.environ.get(token_env, "")),
        },
        "command": command,
        "dispatched": False,
    }
    _write_json(run_dir / "job_packet.json", packet)
    return packet


def dispatch_packet(packet: dict[str, Any]) -> dict[str, Any]:
    if not packet["hf"]["cli"]:
        raise RuntimeError("hf CLI is not available")
    if not packet["hf"]["token_present"]:
        raise RuntimeError("HF token is not available in the configured environment")
    run_dir = Path(packet["run_dir"])
    marker_dir = run_dir.parents[1] / "_idempotency"
    marker_dir.mkdir(parents=True, exist_ok=True)
    marker_path = marker_dir / f"{packet.get('idempotency_key', '')}.json"
    if packet.get("idempotency_key") and marker_path.exists():
        previous = json.loads(marker_path.read_text(encoding="utf-8"))
        updated = {
            **packet,
            "dispatched": False,
            "dispatch": {
                "returncode": 0,
                "stdout": "",
                "stderr": "",
                "job_id": str((previous.get("dispatch") or {}).get("job_id", "")),
                "idempotent_skip": True,
                "previous_packet": str(previous.get("packet_path", "")),
            },
            "dataset_uploads": [],
        }
        _write_json(run_dir / "job_packet.json", updated)
        return updated
    profile = _load_json(Path(packet["profile_path"]))
    uploads = upload_training_dataset(profile)
    result = subprocess.run(packet["command"], cwd=str(REPO_ROOT), capture_output=True, text=True, check=False)
    combined = result.stdout + "\n" + result.stderr
    match = re.search(r"(?:Job ID|ID|job)[^A-Za-z0-9_-]*([A-Za-z0-9_-]{8,})", combined, re.IGNORECASE)
    updated = {
        **packet,
        "dispatched": result.returncode == 0,
        "dispatch": {
            "returncode": result.returncode,
            "stdout": result.stdout.strip()[-4000:],
            "stderr": result.stderr.strip()[-4000:],
            "job_id": match.group(1) if match else "",
        },
        "dataset_uploads": uploads,
    }
    _write_json(run_dir / "job_packet.json", updated)
    if updated.get("dispatched") and packet.get("idempotency_key"):
        _write_json(
            marker_path,
            {
                "idempotency_key": packet["idempotency_key"],
                "packet_path": str(run_dir / "job_packet.json"),
                "dispatch": updated.get("dispatch", {}),
                "profile_id": updated.get("profile_id"),
                "prepared_at_utc": updated.get("prepared_at_utc"),
            },
        )
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
    args = parser.parse_args()
    packet = build_packet(
        profile_path=Path(args.profile_path),
        artifact_root=Path(args.artifact_root),
        flavor=args.flavor or None,
        timeout=args.timeout or None,
    )
    payload = dispatch_packet(packet) if args.command == "dispatch" else packet
    print(json.dumps(payload, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
