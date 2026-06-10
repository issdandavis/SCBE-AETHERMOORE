#!/usr/bin/env python3
"""Dispatch a real SCBE aligned-foundations LoRA training job through Hugging Face Jobs.

Mirrors ``dispatch_coding_agent_hf_job.py`` but specializes for the
``aligned_foundations`` bucket:

  * 4-bit QLoRA over Qwen2.5-7B-Instruct with the profile's 7-module target list.
  * Inline post-training cross-lane concept-preservation gate against the
    ``drill_langues_full_holdout`` records (the only holdout in the blend that
    carries multi-tongue concept groups).
  * Push adapter to ``hub.adapter_repo`` only if ``push_adapter AND
    overall_pass``; otherwise emit ``push_skipped`` and ``sys.exit(1)``.
  * Distribute ``src/governance/aligned_foundations_cross_lane.py`` to the HF
    Jobs container by uploading it alongside the SFT files into the private
    dataset repo, then downloading + dynamically importing inside the wrapper.

This file is the *file-only* dispatcher build. It does not spend HF Jobs
compute; ``main`` only writes a packet unless ``dispatch`` is called.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROFILE = REPO_ROOT / "config" / "model_training" / "aligned-foundations-qwen-primary.json"
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "hf_aligned_foundations_jobs"
ENV_FILE = REPO_ROOT / "config" / "connector_oauth" / ".env.connector.oauth"
CROSS_LANE_SRC = REPO_ROOT / "src" / "governance" / "aligned_foundations_cross_lane.py"
CROSS_LANE_FILENAME = "aligned_foundations_cross_lane.py"
DEFAULT_DATASET_REPO = "issdandavis/scbe-aligned-foundations-sft"
DEFAULT_GATE_HOLDOUT = "drill_langues_full_holdout.sft.jsonl"


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


def render_uv_training_script(
    profile: dict[str, Any],
    *,
    dataset_repo: str,
    push_adapter_override: bool | None,
    gate_holdout: str,
    gate_max_new_tokens: int,
    gate_min_packet: float,
    gate_min_invariance: float,
    gate_limit: int,
) -> str:
    profile_json = json.dumps(profile, indent=2, ensure_ascii=True)
    dataset = profile.get("dataset") or {}
    train_files = [str(name) for name in dataset.get("train_files", [])]
    eval_files = [str(name) for name in dataset.get("eval_files", [])]
    return f'''# /// script
# dependencies = [
#   "accelerate>=0.34.0,<1.2",
#   "datasets>=2.20.0,<3.2",
#   "peft>=0.12.0,<0.14",
#   "torch",
#   "transformers>=4.46.0,<4.48",
#   "huggingface_hub>=0.25.0",
#   "bitsandbytes>=0.43.0",
#   "trl==0.12.1"
# ]
# ///
from __future__ import annotations

import gc
import importlib.util
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import torch
from datasets import Dataset, concatenate_datasets
from huggingface_hub import hf_hub_download, whoami
from peft import LoraConfig, PeftModel, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from trl import SFTTrainer, SFTConfig

PROFILE = json.loads(r"""{profile_json}""")
DATASET_REPO = {dataset_repo!r}
TRAIN_FILES = {json.dumps(train_files, indent=2)}
EVAL_FILES = {json.dumps(eval_files, indent=2)}
GATE_HOLDOUT = {gate_holdout!r}
GATE_MAX_NEW_TOKENS = {gate_max_new_tokens}
GATE_MIN_PACKET = {gate_min_packet!r}
GATE_MIN_INVARIANCE = {gate_min_invariance!r}
GATE_LIMIT = {gate_limit}
PUSH_ADAPTER_OVERRIDE = {push_adapter_override!r}
CROSS_LANE_FILENAME = {CROSS_LANE_FILENAME!r}
WORKDIR = Path("/tmp/scbe-aligned-foundations")
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


def _download_dataset_file(name: str, token: str) -> Path:
    local_path = hf_hub_download(
        repo_id=DATASET_REPO,
        filename=name,
        repo_type="dataset",
        token=token,
        local_dir=str(WORKDIR / "hub-data"),
    )
    return Path(local_path)


def _load_jsonl_path(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            raw = line.strip()
            if raw:
                rows.append(json.loads(raw))
    return rows


def _load_jsonl_files(files: list[str], split: str, token: str) -> list[dict]:
    rows: list[dict] = []
    for name in files:
        local_path = _download_dataset_file(name, token)
        rows.extend(_load_jsonl_path(local_path))
    if not rows:
        raise RuntimeError(f"No {{split}} rows loaded from DATASET_REPO={{DATASET_REPO}}")
    return rows


def _import_cross_lane(token: str):
    local_path = _download_dataset_file(CROSS_LANE_FILENAME, token)
    spec = importlib.util.spec_from_file_location("scbe_aligned_foundations_cross_lane", str(local_path))
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load cross-lane primitives from dataset repo")
    module = importlib.util.module_from_spec(spec)
    sys.modules["scbe_aligned_foundations_cross_lane"] = module
    spec.loader.exec_module(module)
    return module


def _format_text(row: dict, tokenizer) -> str:
    system_prompt = str(PROFILE.get("system_prompt", ""))
    if isinstance(row.get("messages"), list):
        messages = list(row["messages"])
        if system_prompt and not any(item.get("role") == "system" for item in messages if isinstance(item, dict)):
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
    if "question" in row:
        messages = [
            {{"role": "system", "content": system_prompt}},
            {{"role": "user", "content": str(row["question"])}},
            {{"role": "assistant", "content": str(row.get("answer", ""))}},
        ]
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    return str(row.get("text", ""))


def _build_dataset(rows: list[dict], tokenizer) -> Dataset:
    texts = [_format_text(row, tokenizer) for row in rows]
    texts = [t for t in texts if t]
    return Dataset.from_dict({{"text": texts}})


def main() -> None:
    token = _token()
    train_cfg = PROFILE.get("training") or {{}}
    hub_cfg = PROFILE.get("hub") or {{}}
    seed = int(train_cfg.get("seed", 42))
    max_length = int(train_cfg.get("max_seq_length", 4096))
    base_model = str(PROFILE["base_model"])
    adapter_repo = str(hub_cfg.get("adapter_repo", "")).strip()
    push_requested = (
        bool(hub_cfg.get("push_adapter", False))
        if PUSH_ADAPTER_OVERRIDE is None
        else bool(PUSH_ADAPTER_OVERRIDE)
    )

    print(json.dumps({{"event": "auth", "whoami": whoami(token=token).get("name", "unknown")}}))

    cross_lane = _import_cross_lane(token)

    tokenizer = AutoTokenizer.from_pretrained(base_model, token=token, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    use_4bit = bool(train_cfg.get("load_in_4bit", True))
    bnb_cfg = None
    if use_4bit and torch.cuda.is_available():
        bnb_cfg = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
            bnb_4bit_use_double_quant=True,
        )

    dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        token=token,
        torch_dtype=dtype if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None,
        quantization_config=bnb_cfg,
        trust_remote_code=True,
    )
    model.config.use_cache = False
    if hasattr(model, "gradient_checkpointing_enable"):
        model.gradient_checkpointing_enable()
    if use_4bit and torch.cuda.is_available():
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    model = get_peft_model(
        model,
        LoraConfig(
            r=int(train_cfg.get("lora_rank", 32)),
            lora_alpha=int(train_cfg.get("lora_alpha", 64)),
            lora_dropout=float(train_cfg.get("lora_dropout", 0.05)),
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=list(
                train_cfg.get("target_modules")
                or ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
            ),
        ),
    )
    model.print_trainable_parameters()

    train_rows = _load_jsonl_files(TRAIN_FILES, "train", token)
    eval_rows = _load_jsonl_files(EVAL_FILES, "eval", token) if EVAL_FILES else None
    train_ds = _build_dataset(train_rows, tokenizer)
    eval_ds = _build_dataset(eval_rows, tokenizer) if eval_rows is not None else None
    print(json.dumps({{"event": "datasets_built", "train_rows": len(train_ds), "eval_rows": len(eval_ds) if eval_ds is not None else 0}}))

    out_dir = WORKDIR / "adapter"
    sft_args = SFTConfig(
        output_dir=str(WORKDIR / "checkpoints"),
        num_train_epochs=float(train_cfg.get("num_train_epochs", 1)),
        max_steps=int(train_cfg.get("max_steps", -1)),
        per_device_train_batch_size=int(train_cfg.get("batch_size", 2)),
        gradient_accumulation_steps=int(train_cfg.get("gradient_accumulation_steps", 8)),
        learning_rate=float(train_cfg.get("learning_rate", 2e-4)),
        warmup_ratio=float(train_cfg.get("warmup_ratio", 0.05)),
        logging_steps=int(train_cfg.get("logging_steps", 25)),
        save_strategy=str(train_cfg.get("save_strategy", "steps")),
        save_steps=int(train_cfg.get("save_steps", 100)),
        save_total_limit=int(train_cfg.get("save_total_limit", 2)),
        optim=str(train_cfg.get("optim", "adamw_8bit")),
        weight_decay=float(train_cfg.get("weight_decay", 0.01)),
        lr_scheduler_type=str(train_cfg.get("lr_scheduler_type", "cosine")),
        bf16=torch.cuda.is_available() and dtype == torch.bfloat16,
        fp16=torch.cuda.is_available() and dtype == torch.float16,
        gradient_checkpointing=True,
        report_to="none",
        seed=seed,
        max_seq_length=max_length,
        packing=bool(train_cfg.get("packing", True)),
        dataset_text_field="text",
        dataloader_num_workers=int(train_cfg.get("dataloader_num_workers", 2)),
    )
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        args=sft_args,
    )
    stats = trainer.train()
    model.save_pretrained(str(out_dir))
    tokenizer.save_pretrained(str(out_dir))
    print(json.dumps({{"event": "training_saved", "adapter_dir": str(out_dir), "global_step": int(getattr(stats, "global_step", 0)), "training_loss": float(getattr(stats, "training_loss", 0.0))}}))

    # === Inline cross-lane concept-preservation gate ===
    print(json.dumps({{"event": "gate_start", "holdout": GATE_HOLDOUT, "min_packet": GATE_MIN_PACKET, "min_invariance": GATE_MIN_INVARIANCE}}))
    del trainer
    del model
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # Reload base + adapter for evaluation in inference dtype.
    gate_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    gate_base = AutoModelForCausalLM.from_pretrained(
        base_model,
        token=token,
        torch_dtype=gate_dtype,
        device_map="auto" if torch.cuda.is_available() else None,
        quantization_config=bnb_cfg,
        trust_remote_code=True,
    )
    gate_model = PeftModel.from_pretrained(gate_base, str(out_dir))
    gate_model.eval()
    gate_model.config.use_cache = True

    holdout_path = _download_dataset_file(GATE_HOLDOUT, token)
    holdout_rows = _load_jsonl_path(holdout_path)
    if GATE_LIMIT and GATE_LIMIT > 0:
        holdout_rows = holdout_rows[:GATE_LIMIT]
    print(json.dumps({{"event": "gate_holdout_loaded", "n_records": len(holdout_rows)}}))

    def _gate_generate(record):
        sys_text = cross_lane.system_prompt_text(record)
        user_text = cross_lane.user_prompt_text(record)
        msgs = []
        if sys_text:
            msgs.append({{"role": "system", "content": sys_text}})
        msgs.append({{"role": "user", "content": user_text}})
        text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(text, return_tensors="pt").to(gate_model.device)
        n_in = inputs["input_ids"].shape[1]
        out = gate_model.generate(
            **inputs,
            max_new_tokens=GATE_MAX_NEW_TOKENS,
            do_sample=False,
            temperature=1.0,
            pad_token_id=tokenizer.eos_token_id,
        )
        return tokenizer.decode(out[0][n_in:], skip_special_tokens=True)

    per_record_results = []
    records_with_responses = []
    n_compliant = 0
    n_unmapped = 0
    unmapped_kinds: Counter = Counter()
    t0 = time.time()
    for i, rec in enumerate(holdout_rows, 1):
        try:
            with torch.no_grad():
                response = _gate_generate(rec)
        except Exception as exc:  # noqa: BLE001
            meta = rec.get("meta") or {{}}
            entry = {{
                "meta": {{
                    "map": str(meta.get("map", "")),
                    "kind": str(meta.get("kind", "")),
                    "tongue": str(meta.get("tongue", "")),
                    "value": str(meta.get("value", "")),
                }},
                "ok": False,
                "error": str(exc),
                "response": "",
                "reference": cross_lane.reference_assistant_text(rec)[:1500],
            }}
            per_record_results.append(entry)
            records_with_responses.append((rec, ""))
            print(json.dumps({{"event": "gate_record_error", "i": i, "n": len(holdout_rows), "meta": entry["meta"], "error": str(exc)}}))
            continue
        meta = rec.get("meta") or {{}}
        map_name = str(meta.get("map", ""))
        kind = str(meta.get("kind", ""))
        tongue = str(meta.get("tongue", ""))
        value = str(meta.get("value", ""))
        reference = cross_lane.reference_assistant_text(rec)
        diag = cross_lane.score_packet_compliance(map_name, kind, response, reference)
        entry = {{
            "meta": {{"map": map_name, "kind": kind, "tongue": tongue, "value": value}},
            "ok": diag["ok"],
            "error": diag.get("error"),
            "diffs": diag.get("diffs"),
            "actual_signature": diag.get("actual_signature"),
            "expected_signature": diag.get("expected_signature"),
            "response": response[:1500],
            "reference": reference[:1500],
        }}
        per_record_results.append(entry)
        records_with_responses.append((rec, response))
        if entry.get("error") == "not_implemented":
            n_unmapped += 1
            unmapped_kinds[(map_name, kind)] += 1
        elif entry["ok"]:
            n_compliant += 1
        elapsed = time.time() - t0
        print(json.dumps({{"event": "gate_record", "i": i, "n": len(holdout_rows), "ok": entry["ok"], "meta": entry["meta"], "elapsed_s": round(elapsed, 1)}}))

    by_concept = {{}}
    for rec, resp in records_with_responses:
        meta = rec.get("meta") or {{}}
        key = (str(meta.get("map", "")), str(meta.get("kind", "")), str(meta.get("value", "")))
        by_concept.setdefault(key, []).append((rec, resp))

    concept_verdicts = []
    for (map_name, kind, value), pairs in sorted(by_concept.items()):
        per_tongue_responses = {{}}
        per_tongue_references = {{}}
        for rec, resp in pairs:
            meta = rec.get("meta") or {{}}
            tongue = str(meta.get("tongue", ""))
            per_tongue_responses[tongue] = resp
            per_tongue_references[tongue] = cross_lane.reference_assistant_text(rec)
        verdict = cross_lane.aligned_foundations_concept_verdict(
            map_name, kind, value, per_tongue_responses, per_tongue_references
        )
        concept_verdicts.append(verdict)

    n_concepts = len(concept_verdicts)
    multi_tongue = [c for c in concept_verdicts if c.get("n_tongues", 0) >= 2 and "error" not in c]
    n_multi_tongue = len(multi_tongue)
    n_invariant = sum(1 for c in multi_tongue if c.get("invariance_ok", False))
    n_records = len(per_record_results)
    pass_rate_packet = (n_compliant / n_records) if n_records else 0.0
    pass_rate_invariance = (n_invariant / n_multi_tongue) if n_multi_tongue else 1.0
    summary = {{
        "n_records": n_records,
        "n_compliant": n_compliant,
        "pass_rate_packet_compliance": pass_rate_packet,
        "n_concepts": n_concepts,
        "n_multi_tongue_concepts": n_multi_tongue,
        "n_invariant_multi_tongue_concepts": n_invariant,
        "pass_rate_concept_invariance": pass_rate_invariance,
        "n_unmapped_kinds_seen": n_unmapped,
    }}
    overall_pass = (
        n_unmapped == 0
        and pass_rate_packet >= GATE_MIN_PACKET
        and pass_rate_invariance >= GATE_MIN_INVARIANCE
    )

    report = {{
        "schema": "scbe_aligned_foundations_cross_lane_report_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "base_model": base_model,
        "adapter": str(out_dir),
        "holdout": str(holdout_path),
        "tag": f"hf_jobs_{{PROFILE['profile_id']}}",
        "thresholds": {{
            "min_packet_rate": GATE_MIN_PACKET,
            "min_invariance_rate": GATE_MIN_INVARIANCE,
        }},
        "summary": summary,
        "unmapped_kinds": [{{"map": k[0], "kind": k[1], "n": n}} for k, n in unmapped_kinds.most_common()],
        "overall_pass": overall_pass,
        "concept_verdicts": concept_verdicts,
        "per_record_results": per_record_results,
    }}
    report_path = out_dir / "aligned_foundations_cross_lane_inline.json"
    # default=str so frozensets / non-primitive types in concept_verdicts don't crash the dump
    # (job 69f2c151d70108f37ace1989 ERRORed here: TypeError frozenset is not JSON serializable)
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    # Emit gate_report BEFORE any push so it always lands in logs.
    print(json.dumps({{"event": "gate_report", "report_summary": summary, "overall_pass": overall_pass, "unmapped": n_unmapped}}))

    should_push = push_requested and overall_pass and adapter_repo
    pushed_adapter = False
    if should_push:
        print(json.dumps({{"event": "push_attempt", "adapter_repo": adapter_repo}}))
        gate_model.push_to_hub(adapter_repo, token=token)
        tokenizer.push_to_hub(adapter_repo, token=token)
        pushed_adapter = True
    else:
        if not adapter_repo:
            reason = "no_adapter_repo_configured"
        elif not push_requested:
            reason = "push_disabled"
        else:
            reason = "gate_failed"
        print(json.dumps({{"event": "push_skipped", "reason": reason, "overall_pass": overall_pass, "push_requested": push_requested}}))

    final_summary = {{
        "profile_id": PROFILE["profile_id"],
        "base_model": base_model,
        "adapter_repo": adapter_repo,
        "dataset_repo": DATASET_REPO,
        "train_rows_loaded": len(train_rows),
        "eval_rows_loaded": len(eval_rows) if eval_rows is not None else 0,
        "global_step": int(getattr(stats, "global_step", 0)),
        "training_loss": float(getattr(stats, "training_loss", 0.0)),
        "pushed_adapter": pushed_adapter,
        "gate_overall_pass": overall_pass,
        "gate_pass_rate_packet": pass_rate_packet,
        "gate_pass_rate_invariance": pass_rate_invariance,
        "gate_n_unmapped_kinds_seen": n_unmapped,
        "gate_n_records": n_records,
        "gate_n_concepts": n_concepts,
        "gate_n_multi_tongue_concepts": n_multi_tongue,
    }}
    print(json.dumps({{"event": "training_complete", "summary": final_summary}}, indent=2))
    if not overall_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()
'''


def build_packet(
    *,
    profile_path: Path = DEFAULT_PROFILE,
    artifact_root: Path = ARTIFACT_ROOT,
    flavor: str | None = None,
    timeout: str | None = None,
    dataset_repo: str | None = None,
    push_adapter_override: bool | None = None,
    gate_holdout: str = DEFAULT_GATE_HOLDOUT,
    gate_max_new_tokens: int = 320,
    gate_min_packet: float = 0.80,
    gate_min_invariance: float = 0.80,
    gate_limit: int = 0,
) -> dict[str, Any]:
    _load_env_file()
    profile = _load_profile(profile_path)
    execution = profile.get("execution") or {}
    hub_cfg = profile.get("hub") or {}
    resolved_dataset_repo = dataset_repo or str(hub_cfg.get("dataset_repo", "")).strip() or DEFAULT_DATASET_REPO
    stamp = _utc_stamp()
    run_dir = artifact_root / str(profile["profile_id"]) / stamp
    script_path = run_dir / "train_aligned_foundations_hf.py"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(
        render_uv_training_script(
            profile,
            dataset_repo=resolved_dataset_repo,
            push_adapter_override=push_adapter_override,
            gate_holdout=gate_holdout,
            gate_max_new_tokens=gate_max_new_tokens,
            gate_min_packet=gate_min_packet,
            gate_min_invariance=gate_min_invariance,
            gate_limit=gate_limit,
        ),
        encoding="utf-8",
    )

    selected_flavor = flavor or str(execution.get("hf_flavor", "l4x1"))
    selected_timeout = timeout or str(execution.get("timeout", "4h"))
    token_env = str((profile.get("hub") or {}).get("token_env", "HF_TOKEN"))
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
        token_env,
        "--detach",
        str(script_path),
    ]
    packet = {
        "schema_version": "scbe_aligned_foundations_hf_job_packet_v1",
        "prepared_at_utc": stamp,
        "profile_id": profile["profile_id"],
        "profile_path": str(profile_path),
        "run_dir": str(run_dir),
        "script_path": str(script_path),
        "base_model": profile["base_model"],
        "adapter_repo": (profile.get("hub") or {}).get("adapter_repo", ""),
        "dataset_repo": resolved_dataset_repo,
        "cross_lane_module": str(CROSS_LANE_SRC),
        "cross_lane_filename": CROSS_LANE_FILENAME,
        "train_datasets": _dataset_rows(profile, "train"),
        "eval_datasets": _dataset_rows(profile, "eval"),
        "gate": {
            "holdout": gate_holdout,
            "max_new_tokens": gate_max_new_tokens,
            "min_packet_rate": gate_min_packet,
            "min_invariance_rate": gate_min_invariance,
            "limit": gate_limit,
        },
        "push_adapter_override": push_adapter_override,
        "hf": {
            "flavor": selected_flavor,
            "timeout": selected_timeout,
            "cli": shutil.which("hf") or "",
            "token_present": bool(os.environ.get(token_env, "")),
            "token_env": token_env,
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
            f"# Aligned Foundations HF Job - {packet['profile_id']}",
            "",
            f"- Base model: `{packet['base_model']}`",
            f"- Adapter repo: `{packet['adapter_repo']}`",
            f"- Dataset repo: `{packet['dataset_repo']}`",
            f"- Cross-lane module: `{packet['cross_lane_module']}` (uploaded as `{packet['cross_lane_filename']}` in dataset repo)",
            f"- Script: `{packet['script_path']}`",
            f"- Packet: `{Path(packet['run_dir']) / 'job_packet.json'}`",
            "",
            "## Gate",
            "",
            f"- Holdout: `{packet['gate']['holdout']}`",
            f"- min_packet_rate: {packet['gate']['min_packet_rate']}",
            f"- min_invariance_rate: {packet['gate']['min_invariance_rate']}",
            f"- limit: {packet['gate']['limit']} (0 = all)",
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


def upload_training_dataset(profile: dict[str, Any], dataset_repo: str) -> list[dict[str, Any]]:
    if not dataset_repo:
        raise RuntimeError("dataset_repo is required for HF Jobs training")
    dataset_cfg = profile.get("dataset") or {}
    root = REPO_ROOT / str(dataset_cfg.get("root", "training-data/sft"))
    names = [
        *list(dataset_cfg.get("train_files", [])),
        *list(dataset_cfg.get("eval_files", [])),
    ]
    uploads: list[dict[str, Any]] = []
    # First upload the SFT files.
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
            f"Update SCBE aligned-foundations data {name}",
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
    # Then upload the cross-lane primitives module as a companion file.
    if not CROSS_LANE_SRC.exists():
        raise FileNotFoundError(CROSS_LANE_SRC)
    command = [
        "hf",
        "upload",
        dataset_repo,
        str(CROSS_LANE_SRC),
        CROSS_LANE_FILENAME,
        "--repo-type",
        "dataset",
        "--private",
        "--commit-message",
        "Update SCBE aligned-foundations cross-lane primitives",
    ]
    result = subprocess.run(command, cwd=str(REPO_ROOT), capture_output=True, text=True, check=False)
    uploads.append(
        {
            "name": CROSS_LANE_FILENAME,
            "returncode": result.returncode,
            "stdout": result.stdout.strip()[-1000:],
            "stderr": result.stderr.strip()[-1000:],
        }
    )
    if result.returncode != 0:
        raise RuntimeError(f"Cross-lane primitives upload failed: {result.stderr.strip()}")
    return uploads


def dispatch_packet(packet: dict[str, Any]) -> dict[str, Any]:
    if not packet["hf"]["cli"]:
        raise RuntimeError("hf CLI is not available")
    if not packet["hf"]["token_present"]:
        raise RuntimeError("HF token is not available in the configured environment")
    profile = _load_profile(Path(packet["profile_path"]))
    uploads = upload_training_dataset(profile, packet["dataset_repo"])
    result = subprocess.run(
        packet["command"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    job_id = ""
    match = re.search(
        r"(?:Job ID|ID|job)[^A-Za-z0-9_-]*([A-Za-z0-9_-]{8,})",
        stdout + "\n" + stderr,
        re.IGNORECASE,
    )
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


def _add_common_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--profile-path", default=str(DEFAULT_PROFILE))
    parser.add_argument("--artifact-root", default=str(ARTIFACT_ROOT))
    parser.add_argument("--flavor", default="")
    parser.add_argument("--timeout", default="")
    parser.add_argument("--dataset-repo", default="")
    parser.add_argument(
        "--push-adapter",
        choices=("default", "true", "false"),
        default="default",
        help="Override profile hub.push_adapter (default = honor profile)",
    )
    parser.add_argument("--gate-holdout", default=DEFAULT_GATE_HOLDOUT)
    parser.add_argument("--gate-max-new-tokens", type=int, default=320)
    parser.add_argument("--gate-min-packet", type=float, default=0.80)
    parser.add_argument("--gate-min-invariance", type=float, default=0.80)
    parser.add_argument("--gate-limit", type=int, default=0)
    parser.add_argument("--json", action="store_true")


def _resolve_push_override(value: str) -> bool | None:
    if value == "true":
        return True
    if value == "false":
        return False
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "dispatch"):
        item = sub.add_parser(name)
        _add_common_flags(item)
    status = sub.add_parser("status")
    status.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.command == "status":
        result = subprocess.run(
            ["hf", "jobs", "ps"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        payload = {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    else:
        packet = build_packet(
            profile_path=Path(args.profile_path),
            artifact_root=Path(args.artifact_root),
            flavor=args.flavor or None,
            timeout=args.timeout or None,
            dataset_repo=args.dataset_repo or None,
            push_adapter_override=_resolve_push_override(args.push_adapter),
            gate_holdout=args.gate_holdout,
            gate_max_new_tokens=args.gate_max_new_tokens,
            gate_min_packet=args.gate_min_packet,
            gate_min_invariance=args.gate_min_invariance,
            gate_limit=args.gate_limit,
        )
        payload = dispatch_packet(packet) if args.command == "dispatch" else packet

    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2, ensure_ascii=True))
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
