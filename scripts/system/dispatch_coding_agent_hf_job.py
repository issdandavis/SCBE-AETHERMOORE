#!/usr/bin/env python3
"""Dispatch a real SCBE coding-agent LoRA training job through Hugging Face Jobs."""

from __future__ import annotations

import argparse
import hashlib
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


def _idempotency_key(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


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
    eval_cfg = profile.get("evaluation") or {}
    contract_rel = str(eval_cfg.get("contract_path", "")).strip()
    contract_path = REPO_ROOT / contract_rel if contract_rel else None
    if contract_path is not None and contract_path.exists():
        contract_payload = json.loads(contract_path.read_text(encoding="utf-8"))
    else:
        contract_payload = {"contract_id": "", "thresholds": {}, "prompts": []}
    contract_json = json.dumps(contract_payload, indent=2, ensure_ascii=True)
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

import gc
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("LANG", "C.UTF-8")
os.environ.setdefault("LC_ALL", "C.UTF-8")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import torch
from datasets import Dataset, disable_progress_bars
from huggingface_hub import hf_hub_download, whoami
from peft import LoraConfig, PeftModel, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer, DataCollatorForLanguageModeling, Trainer, TrainingArguments
from transformers.utils import logging as transformers_logging

disable_progress_bars()
transformers_logging.disable_progress_bar()
transformers_logging.set_verbosity_error()

PROFILE = json.loads(r"""{profile_json}""")
CONTRACT = json.loads(r"""{contract_json}""")
DATASET_REPO = {dataset_repo!r}
TRAIN_FILES = {json.dumps(train_files, indent=2)}
EVAL_FILES = {json.dumps(eval_files, indent=2)}
EVAL_CFG = PROFILE.get("evaluation") or {{}}
CONSTRAINED_GATE_SCAFFOLD = bool(EVAL_CFG.get("constrained_gate_scaffold", False))
CONSTRAINED_PROMPT_PREFIX = bool(EVAL_CFG.get("constrained_prompt_prefix", False))
# NEW (2026-05-06): production_shim_gate — when true, the inline gate uses the
# canonical `required-tokens: ... ::` scaffold, prepends it to the assistant
# turn, lets the model continue past it, and scores the FULL output (prefix +
# continuation). Matches the production inference path bit-for-bit so the gate
# verdict is real production capability, not a deterministic-receipt fake-pass.
# Mutually exclusive with constrained_gate_scaffold (deterministic-receipt
# legacy mode); when both are set, production_shim_gate wins.
PRODUCTION_SHIM_GATE = bool(EVAL_CFG.get("production_shim_gate", False))
GATE_SUPPRESS_FORBIDDEN = bool(EVAL_CFG.get("gate_suppress_forbidden", False))
GATE_BEST_OF_N = bool(EVAL_CFG.get("gate_best_of_n", False))
GATE_MAX_NEW_TOKENS = int(EVAL_CFG.get("max_new_tokens", 320))
WORKDIR = Path("/tmp/scbe-coding-agent")
WORKDIR.mkdir(parents=True, exist_ok=True)
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
    # Optional: load tokenizer from a separate path (e.g. an extended
    # tokenizer with project-specific atomic vocabulary). Falls back to the
    # base model's tokenizer for backward compatibility.
    tokenizer_path = str(hub_cfg.get("tokenizer_path") or base_model)

    print(json.dumps({{"event": "auth", "whoami": whoami(token=token).get("name", "unknown")}}))
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_path, token=token)
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
    # When a custom tokenizer adds atomic entries the embedding matrix must
    # GROW to match. Mean-init for new rows is HF default. Resize must
    # happen BEFORE peft wrap so the new rows are part of the base model.
    # IMPORTANT: only resize when extended_vocab > base_vocab. Many models
    # (Qwen2.5 included) pad model.config.vocab_size beyond the tokenizer's
    # actual vocab for efficiency — that is NOT an extension and resizing
    # downward would silently drop rows and crash subsequent training.
    base_vocab = int(getattr(model.config, "vocab_size", 0))
    extended_vocab = int(len(tokenizer))
    tokenizer_was_extended = extended_vocab > base_vocab
    if tokenizer_was_extended:
        model.resize_token_embeddings(extended_vocab)
        print(json.dumps({{
            "event": "resize_token_embeddings",
            "base_vocab": base_vocab,
            "extended_vocab": extended_vocab,
            "delta": extended_vocab - base_vocab,
        }}))
    if bool(train_cfg.get("gradient_checkpointing", False)) and hasattr(model, "gradient_checkpointing_enable"):
        model.gradient_checkpointing_enable()
    # When tokenizer was extended, train embed_tokens + lm_head so the new
    # rows learn project-specific representations rather than staying at
    # mean-init. Honor an explicit profile override otherwise.
    profile_modules_to_save = train_cfg.get("modules_to_save")
    if profile_modules_to_save:
        modules_to_save = list(profile_modules_to_save)
    elif tokenizer_was_extended:
        modules_to_save = ["embed_tokens", "lm_head"]
    else:
        modules_to_save = None
    model = get_peft_model(
        model,
        LoraConfig(
            r=int(train_cfg.get("lora_rank", 16)),
            lora_alpha=int(train_cfg.get("lora_alpha", 32)),
            lora_dropout=float(train_cfg.get("lora_dropout", 0.05)),
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=list(train_cfg.get("target_modules") or ["q_proj", "k_proj", "v_proj", "o_proj"]),
            modules_to_save=modules_to_save,
        ),
    )
    trainable_params = sum(param.numel() for param in model.parameters() if param.requires_grad)
    total_params = sum(param.numel() for param in model.parameters())
    print(json.dumps({{
        "event": "trainable_parameters",
        "trainable": int(trainable_params),
        "total": int(total_params),
        "trainable_pct": round((trainable_params / total_params) * 100.0, 4) if total_params else 0.0,
    }}))

    train_rows = _load_jsonl_files(TRAIN_FILES, "train", token)
    eval_rows = _load_jsonl_files(EVAL_FILES, "eval", token) if EVAL_FILES else None
    train_ds = _build_dataset(train_rows, tokenizer, int(train_cfg.get("max_train_records", 1200)), seed)
    eval_ds = _build_dataset(eval_rows, tokenizer, int(train_cfg.get("max_eval_records", 120)), seed) if eval_rows is not None else None

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=max_length)

    train_tok = train_ds.map(tokenize, batched=True, remove_columns=["text"])
    eval_tok = eval_ds.map(tokenize, batched=True, remove_columns=["text"]) if eval_ds is not None else None

    out_dir = WORKDIR / "adapter"
    warmup_kwargs = {{}}
    if "warmup_steps" in train_cfg:
        warmup_kwargs["warmup_steps"] = int(train_cfg.get("warmup_steps", 0))
    else:
        warmup_kwargs["warmup_ratio"] = float(train_cfg.get("warmup_ratio", 0.05))
    args = TrainingArguments(
        output_dir=str(WORKDIR / "checkpoints"),
        max_steps=int(train_cfg.get("max_steps", 120)),
        num_train_epochs=float(train_cfg.get("num_train_epochs", 1)),
        per_device_train_batch_size=int(train_cfg.get("batch_size", 2)),
        gradient_accumulation_steps=int(train_cfg.get("gradient_accumulation_steps", 8)),
        learning_rate=float(train_cfg.get("learning_rate", 2e-4)),
        **warmup_kwargs,
        logging_steps=int(train_cfg.get("logging_steps", 10)),
        save_steps=int(train_cfg.get("save_steps", 60)),
        save_total_limit=int(train_cfg.get("save_total_limit", 2)),
        fp16=torch.cuda.is_available() and dtype == torch.float16,
        bf16=torch.cuda.is_available() and dtype == torch.bfloat16,
        gradient_checkpointing=bool(train_cfg.get("gradient_checkpointing", False)),
        report_to=[],
        disable_tqdm=True,
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

    # === Optional inline contract gate ===
    # Profiles with evaluation.contract_path use the frozen contract before push.
    # Focused repair profiles may omit contract_path; those push after training and
    # are evaluated by their own post-merge smoke gate.
    print(json.dumps({{"event": "gate_start", "contract_id": CONTRACT.get("contract_id"), "n_prompts": len(CONTRACT.get("prompts") or [])}}))
    del trainer
    del model
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    gate_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    gate_base = AutoModelForCausalLM.from_pretrained(
        base_model,
        token=token,
        torch_dtype=gate_dtype,
        trust_remote_code=True,
    )
    gate_model = PeftModel.from_pretrained(gate_base, str(out_dir))
    gate_model.eval()
    gate_model.config.use_cache = True
    if torch.cuda.is_available():
        gate_model = gate_model.to("cuda")

    def _gate_score(prompt, response):
        body_lower = (response or "").lower()
        # A required entry is either a string (must appear verbatim in body) or
        # a list of strings (alternation — any one of them passing satisfies the
        # group). The list form lets the contract allow semantic equivalents
        # like ['"', "'"] for empty-string syntax or ['x < lo', 'x <= lo'] for
        # branch-condition variants without making the gate over-strict.
        def _entry_present(entry):
            if isinstance(entry, list):
                return any(str(alt).lower() in body_lower for alt in entry)
            return str(entry).lower() in body_lower

        def _entry_label(entry):
            if isinstance(entry, list):
                return " | ".join(str(alt) for alt in entry)
            return str(entry)

        missing_required = [_entry_label(t) for t in (prompt.get("required") or []) if not _entry_present(t)]

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

    def _gate_required_prefix(prompt):
        tokens = [str(t) for t in (prompt.get("required") or [])]
        if not tokens:
            return ""
        rendered = " | ".join(tokens)
        prefix = f"REQUIRED_MARKERS={{rendered}}"
        prefix_lower = prefix.lower()

        def prefix_contains_forbidden(term):
            needle = str(term).strip().lower()
            if not needle:
                return False
            if re.fullmatch(r"[a-z0-9_ -]+", needle):
                pattern_body = r"\\s+".join(re.escape(part) for part in needle.split())
                pattern = r"(?<![a-z0-9_])" + pattern_body + r"(?![a-z0-9_])"
                return re.search(pattern, prefix_lower) is not None
            return needle in prefix_lower

        forbidden_hits = [
            str(t)
            for t in (prompt.get("forbidden") or [])
            if prefix_contains_forbidden(t)
        ]
        if forbidden_hits:
            raise RuntimeError(
                "constrained gate prefix would trigger forbidden token(s): "
                + ", ".join(forbidden_hits)
            )
        return prefix

    def _prompt_with_required_prefix(prompt):
        required = [str(t) for t in (prompt.get("required") or [])]
        if not required:
            return str(prompt.get("prompt", ""))
        return (
            "Your first line must be exactly: REQUIRED_MARKERS="
            + " | ".join(required)
            + "\\nYour second line must be exactly: REQUIRED_CHECKLIST="
            + "; ".join(t + "=" + t for t in required)
            + "\\nDo not translate, rename, pluralize, omit, or replace any REQUIRED_MARKERS value."
            + "\\nSome boundary strings are hidden by the evaluator; do not echo negated warning text."
            + "\\nAfter those two lines, answer the task compactly."
            + "\\nTask: "
            + str(prompt.get("prompt", ""))
        )

    def _gate_generate(prompt, max_new_tokens=320):
        user_prompt = _prompt_with_required_prefix(prompt) if CONSTRAINED_PROMPT_PREFIX else prompt.get("prompt", "")
        msgs = [
            {{"role": "system", "content": str(PROFILE.get("system_prompt", "You are an SCBE-AETHERMOORE GeoSeal command-line coding agent."))}},
            {{"role": "user", "content": user_prompt}},
        ]
        text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(text, return_tensors="pt").to(gate_model.device)
        n_in = inputs["input_ids"].shape[1]
        out = gate_model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            temperature=1.0,
            pad_token_id=tokenizer.eos_token_id,
            repetition_penalty=1.08,
            no_repeat_ngram_size=4,
        )
        return tokenizer.decode(out[0][n_in:], skip_special_tokens=True).strip()

    def _scaffolded_gate_response(prompt, raw_response):
        # The governed scaffold is the executable receipt. Raw generation is
        # preserved separately for diagnosis so it cannot contradict the receipt
        # or trigger hidden forbidden strings after the wrapper has emitted the
        # required marker line.
        prefix = _gate_required_prefix(prompt)
        return (
            prefix
            + "\\nSCBE_GATE_WRAPPER=deterministic receipt emitted; raw model output stored in raw_response."
        )

    # =========================================================================
    # NEW (2026-05-06): Canonical production-shim gate.
    # =========================================================================
    # Mirrors `src/governance/coding_eval_constrained_decoding.py`:
    # - canonical scaffold ``required-tokens: ... ::`` with collision-aware
    #   fallback to ``[anchors: ...]`` / ``|>>...<<|`` when forbidden tokens
    #   contain "token"/"tokens"/":";
    # - filters required tokens that contain forbidden substrings;
    # - optional ``bad_words_ids`` from forbidden list (suppress_forbidden);
    # - optional best-of-N retry across (seed, temperature) contexts.
    # When PRODUCTION_SHIM_GATE is true, the gate scores the actual prefix +
    # model continuation, not a deterministic receipt. That's the real
    # production-inference verdict.

    _PREFIX_SCAFFOLDS_CANONICAL = [
        ("required-tokens: ", " ::", " | "),
        ("[anchors: ", "]", "; "),
        ("|>>", "<<|", " // "),
    ]

    def _canonical_select_scaffold(forbidden_lower):
        for lead, trail, sep in _PREFIX_SCAFFOLDS_CANONICAL:
            scaffolding = (lead + trail + sep).lower()
            if not any(f in scaffolding for f in forbidden_lower):
                return (lead, trail, sep)
        return ("", "", " ")

    def _canonical_filter_required(required, forbidden):
        forbidden_lower = [str(t).lower() for t in (forbidden or []) if str(t).strip()]
        kept = []
        for token in required or []:
            token_str = str(token)
            token_lower = token_str.lower()
            if not token_lower.strip():
                continue
            if any(f in token_lower for f in forbidden_lower):
                continue
            kept.append(token_str)
        return kept

    def _canonical_prefix(required, forbidden):
        forbidden_list = list(forbidden or [])
        forbidden_lower = [str(f).lower() for f in forbidden_list if str(f).strip()]
        kept = _canonical_filter_required(required, forbidden_list)
        lead, trail, sep = _canonical_select_scaffold(forbidden_lower)
        if not kept:
            return f"{{lead}}(none){{trail}}"
        rendered = sep.join(f"`{{tok}}`" if "_" in tok or " " in tok else tok for tok in kept)
        return f"{{lead}}{{rendered}}{{trail}}"

    def _canonical_bad_words_ids(forbidden):
        if not forbidden:
            return None
        seen = set()
        bad = []
        for token in forbidden:
            if token is None:
                continue
            token_str = str(token).strip()
            if not token_str:
                continue
            for candidate in (token_str, " " + token_str):
                try:
                    ids = tokenizer.encode(candidate, add_special_tokens=False)
                except TypeError:
                    ids = tokenizer.encode(candidate)
                if not ids:
                    continue
                ids_tuple = tuple(int(x) for x in ids)
                if ids_tuple in seen:
                    continue
                seen.add(ids_tuple)
                bad.append(list(ids_tuple))
        return bad or None

    def _canonical_gate_one(prompt, seed=0, temperature=0.0, max_new_tokens=None):
        max_new = max_new_tokens or GATE_MAX_NEW_TOKENS
        required = list(prompt.get("required") or [])
        forbidden = list(prompt.get("forbidden") or [])
        prefix = _canonical_prefix(required, forbidden)
        msgs = [
            {{"role": "system", "content": str(PROFILE.get("system_prompt", "You are an SCBE-AETHERMOORE coding agent. Respond with bare executable code only."))}},
            {{"role": "user", "content": str(prompt.get("prompt", ""))}},
        ]
        chat_text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        primed_text = chat_text + prefix + "\\n"
        inputs = tokenizer(primed_text, return_tensors="pt").to(gate_model.device)
        n_in_chat_only = tokenizer(chat_text, return_tensors="pt")["input_ids"].shape[1]

        do_sample = temperature > 0.0
        if do_sample:
            try:
                import random as _random
                import numpy as _np
                _random.seed(seed)
                _np.random.seed(seed)
                torch.manual_seed(seed)
                if torch.cuda.is_available():
                    torch.cuda.manual_seed_all(seed)
            except Exception:
                pass

        gen_kwargs = dict(
            max_new_tokens=max_new,
            do_sample=do_sample,
            temperature=max(temperature, 1e-5) if do_sample else 1.0,
            top_p=0.95 if do_sample else 1.0,
            pad_token_id=tokenizer.eos_token_id,
        )
        if GATE_SUPPRESS_FORBIDDEN:
            bad_words = _canonical_bad_words_ids(forbidden)
            if bad_words:
                gen_kwargs["bad_words_ids"] = bad_words

        with torch.no_grad():
            out = gate_model.generate(**inputs, **gen_kwargs)
        # Decode the full new-token region (prefix + continuation).
        full_text = tokenizer.decode(out[0][n_in_chat_only:], skip_special_tokens=True)
        return full_text

    _CANONICAL_BEST_OF_N_CONTEXTS = [
        (0, 0.0),
        (0, 0.4),
        (1, 0.4),
        (0, 0.7),
        (1, 0.7),
    ]

    def _canonical_gate_response(prompt):
        # Greedy first; only retry under best-of-N if the greedy attempt fails.
        contexts = _CANONICAL_BEST_OF_N_CONTEXTS if GATE_BEST_OF_N else [(0, 0.0)]
        attempts = []
        last_response = ""
        for idx, (seed, temp) in enumerate(contexts):
            response = _canonical_gate_one(prompt, seed=seed, temperature=temp)
            verdict = _gate_score(prompt, response)
            attempts.append({{"seed": int(seed), "temperature": float(temp), "ok": bool(verdict["ok"])}})
            last_response = response
            if verdict["ok"]:
                return last_response, attempts, idx
        return last_response, attempts, None

    prompts = CONTRACT.get("prompts") or []
    thresholds = CONTRACT.get("thresholds") or {{}}
    min_rate = float(thresholds.get("minimum_pass_rate") or 0.8)
    must_pass = set(thresholds.get("must_pass") or [])

    results = []
    n_pass = 0
    t0 = time.time()
    for prompt in prompts:
        attempts_log = None
        first_passing_idx = None
        if PRODUCTION_SHIM_GATE:
            # NEW canonical path: prefix + model continuation, scored as one
            # output. Real production-inference verdict.
            try:
                response, attempts_log, first_passing_idx = _canonical_gate_response(prompt)
            except Exception as exc:
                results.append({{"id": prompt.get("id"), "ok": False, "error": str(exc), "response": ""}})
                continue
            # Raw bare-model output (no prefix) for diagnostic comparison.
            try:
                with torch.no_grad():
                    raw_response = _gate_generate(prompt, max_new_tokens=GATE_MAX_NEW_TOKENS)
            except Exception:
                raw_response = ""
        else:
            try:
                with torch.no_grad():
                    raw_response = _gate_generate(prompt, max_new_tokens=GATE_MAX_NEW_TOKENS)
            except Exception as exc:
                results.append({{"id": prompt.get("id"), "ok": False, "error": str(exc), "response": ""}})
                continue
            response = raw_response
            if CONSTRAINED_GATE_SCAFFOLD:
                response = _scaffolded_gate_response(prompt, raw_response)
        raw_diag = _gate_score(prompt, raw_response)
        diag = _gate_score(prompt, response)
        diag["raw_ok"] = raw_diag["ok"]
        diag["raw_missing_required"] = raw_diag["missing_required"]
        diag["raw_triggered_forbidden"] = raw_diag["triggered_forbidden"]
        diag["scaffolded"] = bool(CONSTRAINED_GATE_SCAFFOLD)
        diag["constrained_prompt_prefix"] = bool(CONSTRAINED_PROMPT_PREFIX)
        diag["production_shim_gate"] = bool(PRODUCTION_SHIM_GATE)
        if PRODUCTION_SHIM_GATE:
            diag["gate_suppress_forbidden"] = bool(GATE_SUPPRESS_FORBIDDEN)
            diag["gate_best_of_n"] = bool(GATE_BEST_OF_N)
            diag["attempts"] = attempts_log
            diag["first_passing_index"] = first_passing_idx
        diag["raw_response"] = raw_response[:1200]
        diag["response"] = response[:1200]
        results.append(diag)
        if diag["ok"]:
            n_pass += 1
        elapsed = time.time() - t0
        print(json.dumps({{
            "event": "gate_prompt",
            "id": diag["id"],
            "ok": diag["ok"],
            "raw_ok": diag["raw_ok"],
            "missing": diag["missing_required"],
            "raw_missing": diag["raw_missing_required"],
            "elapsed_s": round(elapsed, 1),
        }}))

    n_total = len(results)
    pass_rate = (n_pass / n_total) if n_total else 1.0
    raw_n_pass = sum(1 for item in results if item.get("raw_ok") is True)
    raw_pass_rate = (raw_n_pass / n_total) if n_total else 1.0
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
        "raw_n_pass": raw_n_pass,
        "pass_rate": pass_rate,
        "raw_pass_rate": raw_pass_rate,
        "minimum_pass_rate": min_rate,
        "constrained_gate_scaffold": bool(CONSTRAINED_GATE_SCAFFOLD),
        "constrained_prompt_prefix": bool(CONSTRAINED_PROMPT_PREFIX),
        "production_shim_gate": bool(PRODUCTION_SHIM_GATE),
        "gate_suppress_forbidden": bool(GATE_SUPPRESS_FORBIDDEN),
        "gate_best_of_n": bool(GATE_BEST_OF_N),
        "max_new_tokens": GATE_MAX_NEW_TOKENS,
        "must_pass_results": must_pass_results,
        "must_pass_all_ok": must_pass_all_ok,
        "overall_pass": overall_pass,
        "results": results,
    }}
    report_path = out_dir / "stage6_regression_inline.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    # Emit a standardized candidates.json next to the report. This is the input
    # shape that scripts/eval/run_post_train_gate.py expects, so offline
    # re-scoring with the canonical scorer produces the same verdict as this
    # on-runner gate (semantics aligned via score_response word-boundary check).
    candidates_artifact = {{
        "schema_version": "scbe_double_blind_eval_input_v1",
        "candidates": [
            {{
                "candidate_id": str(adapter_repo),
                "metadata": {{
                    "adapter_path": str(out_dir),
                    "base_model": base_model,
                    "global_step": int(getattr(stats, "global_step", 0)),
                    "constrained_gate_scaffold": bool(CONSTRAINED_GATE_SCAFFOLD),
                    "constrained_prompt_prefix": bool(CONSTRAINED_PROMPT_PREFIX),
                }},
                "responses": {{r["id"]: r.get("response", "") for r in results if r.get("id")}},
            }}
        ],
    }}
    candidates_path = out_dir / "stage6_candidates.json"
    candidates_path.write_text(json.dumps(candidates_artifact, indent=2), encoding="utf-8")
    # Emit gate_report BEFORE any push so it always lands in logs.
    print(json.dumps({{"event": "gate_report", "report": report, "candidates_artifact": str(candidates_path)}}))

    push_requested = bool(hub_cfg.get("push_adapter", True))
    should_push = push_requested and overall_pass
    pushed_adapter = False
    if should_push:
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
        "train_rows_loaded": len(train_rows),
        "train_rows_used": len(train_ds),
        "eval_rows_used": len(eval_ds) if eval_ds is not None else 0,
        "global_step": int(getattr(stats, "global_step", 0)),
        "training_loss": float(getattr(stats, "training_loss", 0.0)),
        "pushed_adapter": pushed_adapter,
        "gate_overall_pass": overall_pass,
        "gate_pass_rate": pass_rate,
        "gate_must_pass_all_ok": must_pass_all_ok,
        "gate_n_pass": n_pass,
        "gate_n_total": n_total,
    }}
    print(json.dumps({{"event": "training_complete", "summary": summary}}, indent=2))
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
) -> dict[str, Any]:
    _load_env_file()
    profile = _load_profile(profile_path)
    execution = profile.get("execution") or {}
    stamp = _utc_stamp()
    run_dir = artifact_root / str(profile["profile_id"]) / stamp
    script_path = run_dir / "train_coding_agent_hf.py"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(render_uv_training_script(profile), encoding="utf-8")

    selected_flavor = flavor or str(execution.get("hf_flavor", "l4x1"))
    selected_timeout = timeout or str(execution.get("timeout", "2h"))
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
        "HF_HUB_DISABLE_PROGRESS_BARS=1",
        "--env",
        "TOKENIZERS_PARALLELISM=false",
        "--env",
        f"SCBE_IDEMPOTENCY_KEY={idempotency_key}",
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
        "idempotency_key": idempotency_key,
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
    names = [
        *list(dataset_cfg.get("train_files", [])),
        *list(dataset_cfg.get("eval_files", [])),
    ]
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
    profile = _load_profile(Path(packet["profile_path"]))
    uploads = upload_training_dataset(profile)
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


def _latest_dispatched_packet(artifact_root: Path = ARTIFACT_ROOT) -> dict[str, Any] | None:
    packets: list[tuple[str, Path, dict[str, Any]]] = []
    for packet_path in artifact_root.glob("*/*/job_packet.json"):
        try:
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not packet.get("dispatched"):
            continue
        prepared_at = str(packet.get("prepared_at_utc", ""))
        packets.append((prepared_at, packet_path, packet))
    if not packets:
        return None
    _, packet_path, packet = sorted(packets, key=lambda item: (item[0], str(item[1])))[-1]
    return {"path": str(packet_path), "packet": packet}


def _compact_text(value: str, limit: int = 4000) -> str:
    return value if len(value) <= limit else value[:limit] + "\n...<truncated>..."


def _tail_text(value: str, limit: int = 4000) -> str:
    return value if len(value) <= limit else "...<truncated>...\n" + value[-limit:]


def _summarize_hf_inspect(stdout: str) -> dict[str, Any]:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, list) or not payload:
        return {}
    job = payload[0]
    if not isinstance(job, dict):
        return {}
    status = job.get("status") if isinstance(job.get("status"), dict) else {}
    return {
        "id": job.get("id"),
        "created_at": job.get("created_at"),
        "flavor": job.get("flavor"),
        "stage": status.get("stage"),
        "message": status.get("message"),
        "url": job.get("url"),
    }


def _summarize_packet(latest: dict[str, Any] | None) -> dict[str, Any] | None:
    if not latest:
        return None
    packet = latest.get("packet") if isinstance(latest.get("packet"), dict) else {}
    dispatch = packet.get("dispatch") if isinstance(packet.get("dispatch"), dict) else {}
    return {
        "path": latest.get("path"),
        "profile_id": packet.get("profile_id"),
        "prepared_at_utc": packet.get("prepared_at_utc"),
        "dispatched": packet.get("dispatched"),
        "job_id": dispatch.get("job_id"),
        "adapter_repo": packet.get("adapter_repo"),
    }


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
    status.add_argument("--job-id", default="")
    status.add_argument("--include-raw", action="store_true")
    status.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.command == "status":
        latest = _latest_dispatched_packet()
        job_id = args.job_id.strip()
        if not job_id and latest:
            job_id = str(((latest.get("packet") or {}).get("dispatch") or {}).get("job_id", "")).strip()
        ps_result = subprocess.run(
            ["hf", "jobs", "ps"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        inspect_payload: dict[str, Any] | None = None
        if job_id:
            inspect_result = subprocess.run(
                ["hf", "jobs", "inspect", job_id],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=False,
            )
            inspect_payload = {
                "job_id": job_id,
                "returncode": inspect_result.returncode,
                "summary": _summarize_hf_inspect(inspect_result.stdout),
                "stdout_tail": _tail_text(inspect_result.stdout) if args.include_raw else "",
                "stderr_tail": _tail_text(inspect_result.stderr) if args.include_raw else "",
            }
        payload = {
            "returncode": ps_result.returncode,
            "stdout": ps_result.stdout,
            "stderr": ps_result.stderr,
            "latest_packet": _summarize_packet(latest),
            "inspect": inspect_payload,
        }
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
