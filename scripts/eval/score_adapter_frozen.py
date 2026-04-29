"""Frozen-eval scorer for SCBE LoRA adapters.

Computes assistant-token perplexity over a curated holdout corpus, plus
per-source-file metrics so we can compare adapters (v7 + 3 specialty)
against the same fixed sets without needing curated golden phrases.

Output: artifacts/model_evals/frozen/<adapter-slug>-<utc>/{report.json, report.md}
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASE_MODEL = "Qwen/Qwen2.5-Coder-0.5B-Instruct"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "artifacts" / "model_evals" / "frozen"

DEFAULT_EVAL_FILES = [
    "coding_system_full_v1_holdout.sft.jsonl",
    "bijective_codeflow_v1_holdout.sft.jsonl",
    "cross_tongue_dialogue_bijective_v1_holdout.sft.jsonl",
    "drill_langues_full_holdout.sft.jsonl",
    "operator_agent_bus_extracted_v1_eval.sft.jsonl",
    "governance_security_boundary_eval_v1.sft.jsonl",
    "research_bridge_source_grounded_v1_eval.sft.jsonl",
    "aligned_foundations_holdout.sft.jsonl",
    "command_lattice_seed_holdout.sft.jsonl",
    "atomic_workflow_stage6_holdout.sft.jsonl",
    "atomic_workflow_stage6_repair_holdout.sft.jsonl",
]


@dataclass
class FileMetrics:
    name: str
    n_records: int = 0
    n_assistant_tokens: int = 0
    sum_nll: float = 0.0
    skipped: int = 0
    record_losses: list[float] = field(default_factory=list)

    @property
    def mean_nll(self) -> float:
        return (
            self.sum_nll / self.n_assistant_tokens if self.n_assistant_tokens else 0.0
        )

    @property
    def perplexity(self) -> float:
        return math.exp(self.mean_nll) if self.n_assistant_tokens else 0.0


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "").strip())
    return re.sub(r"-+", "-", slug).strip("-.") or "adapter"


def load_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            msgs = payload.get("messages")
            if isinstance(msgs, list) and any(
                m.get("role") == "assistant" for m in msgs
            ):
                records.append({"messages": msgs, "meta": payload.get("meta", {})})
    return records


def build_supervised_inputs(
    tokenizer, messages: list[dict[str, str]], max_length: int
) -> tuple[list[int], list[int]] | None:
    """Returns (input_ids, labels) where non-assistant positions are -100."""
    full_text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=False
    )

    # Split before each assistant turn so we can mask user/system tokens.
    # We rebuild a prefix containing all turns up to (but not including) each
    # assistant turn, tokenize the prefix and the prefix+assistant, and the
    # delta is the assistant's supervised range.
    prefix_messages: list[dict[str, str]] = []
    input_ids: list[int] = []
    labels: list[int] = []

    for msg in messages:
        prefix_text = (
            tokenizer.apply_chat_template(
                prefix_messages, tokenize=False, add_generation_prompt=False
            )
            if prefix_messages
            else ""
        )
        prefix_messages_with = prefix_messages + [msg]
        with_text = tokenizer.apply_chat_template(
            prefix_messages_with, tokenize=False, add_generation_prompt=False
        )

        # Tokenize without special tokens to keep alignment honest; chat
        # template already injects role markers as text.
        prefix_ids = (
            tokenizer(prefix_text, add_special_tokens=False)["input_ids"]
            if prefix_text
            else []
        )
        with_ids = tokenizer(with_text, add_special_tokens=False)["input_ids"]

        if len(with_ids) <= len(prefix_ids):
            prefix_messages = prefix_messages_with
            continue

        delta_ids = with_ids[len(prefix_ids) :]
        input_ids.extend(delta_ids)
        if msg.get("role") == "assistant":
            labels.extend(delta_ids)
        else:
            labels.extend([-100] * len(delta_ids))
        prefix_messages = prefix_messages_with

    if len(input_ids) > max_length:
        input_ids = input_ids[:max_length]
        labels = labels[:max_length]

    if not any(l != -100 for l in labels):
        return None
    return input_ids, labels


def score_file(
    eval_path: Path,
    tokenizer,
    model,
    device,
    max_length: int,
    per_file_limit: int,
) -> FileMetrics:
    metrics = FileMetrics(name=eval_path.name)
    records = load_records(eval_path)
    if per_file_limit > 0:
        records = records[:per_file_limit]

    import torch

    for rec in records:
        prepared = build_supervised_inputs(
            tokenizer, rec["messages"], max_length=max_length
        )
        if prepared is None:
            metrics.skipped += 1
            continue
        input_ids, labels = prepared
        input_tensor = torch.tensor([input_ids], dtype=torch.long, device=device)
        label_tensor = torch.tensor([labels], dtype=torch.long, device=device)
        attn = torch.ones_like(input_tensor)
        with torch.no_grad():
            out = model(
                input_ids=input_tensor, attention_mask=attn, labels=label_tensor
            )
        n_supervised = int((label_tensor != -100).sum().item())
        # HF returns mean loss over supervised positions; multiply back.
        loss_val = float(out.loss.item())
        metrics.n_records += 1
        metrics.n_assistant_tokens += n_supervised
        metrics.sum_nll += loss_val * n_supervised
        metrics.record_losses.append(loss_val)
    return metrics


def load_model_and_tokenizer(
    base_model: str, adapter: str, dtype_arg: str, use_4bit: bool
):
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    cuda_avail = torch.cuda.is_available()
    if dtype_arg == "auto":
        if cuda_avail:
            cap = torch.cuda.get_device_capability(0)
            dtype = torch.bfloat16 if cap[0] >= 8 else torch.float16
        else:
            dtype = torch.float32
    else:
        dtype = {"bf16": torch.bfloat16, "fp16": torch.float16, "fp32": torch.float32}[
            dtype_arg
        ]

    tok = AutoTokenizer.from_pretrained(base_model, use_fast=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    kwargs: dict[str, Any] = {"torch_dtype": dtype, "low_cpu_mem_usage": True}
    if use_4bit and cuda_avail:
        try:
            from transformers import BitsAndBytesConfig

            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=dtype,
                bnb_4bit_use_double_quant=True,
            )
            kwargs["device_map"] = "auto"
        except Exception as exc:
            print(
                f"  WARN bnb 4-bit unavailable, falling back to {dtype}: {exc}",
                file=sys.stderr,
            )
    elif cuda_avail:
        kwargs["device_map"] = "auto"

    base = AutoModelForCausalLM.from_pretrained(base_model, **kwargs)

    if adapter and adapter != "BASE":
        model = PeftModel.from_pretrained(base, adapter)
    else:
        model = base
    model.eval()
    device = next(model.parameters()).device
    return tok, model, device


def write_report(
    output_root: Path,
    adapter: str,
    base_model: str,
    file_metrics: list[FileMetrics],
    elapsed: float,
    runtime_meta: dict[str, Any],
) -> dict[str, Path]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = output_root / f"{safe_slug(adapter)}-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    total_records = sum(m.n_records for m in file_metrics)
    total_tokens = sum(m.n_assistant_tokens for m in file_metrics)
    total_nll = sum(m.sum_nll for m in file_metrics)
    overall_mean_nll = total_nll / total_tokens if total_tokens else 0.0
    overall_ppl = math.exp(overall_mean_nll) if total_tokens else 0.0

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "adapter": adapter,
        "base_model": base_model,
        "elapsed_s": round(elapsed, 1),
        "runtime": runtime_meta,
        "summary": {
            "total_records": total_records,
            "total_assistant_tokens": total_tokens,
            "mean_nll": overall_mean_nll,
            "perplexity": overall_ppl,
            "files_evaluated": len([m for m in file_metrics if m.n_records > 0]),
        },
        "per_file": [
            {
                "name": m.name,
                "n_records": m.n_records,
                "n_assistant_tokens": m.n_assistant_tokens,
                "mean_nll": m.mean_nll,
                "perplexity": m.perplexity,
                "skipped": m.skipped,
            }
            for m in file_metrics
        ],
    }

    json_path = out_dir / "report.json"
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    md_lines = [
        f"# Frozen Eval — {adapter}",
        "",
        f"- generated_at_utc: `{payload['generated_at_utc']}`",
        f"- base_model: `{base_model}`",
        f"- elapsed_s: `{payload['elapsed_s']}`",
        f"- total_records: `{total_records}`",
        f"- total_assistant_tokens: `{total_tokens}`",
        f"- overall_mean_nll: `{overall_mean_nll:.4f}`",
        f"- overall_perplexity: `{overall_ppl:.3f}`",
        "",
        "## Per-file",
        "",
        "| File | Records | Asst Tokens | Mean NLL | Perplexity | Skipped |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for m in file_metrics:
        md_lines.append(
            f"| {m.name} | {m.n_records} | {m.n_assistant_tokens} | "
            f"{m.mean_nll:.4f} | {m.perplexity:.3f} | {m.skipped} |"
        )
    md_path = out_dir / "report.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--adapter",
        required=True,
        help="HF repo id OR local path to adapter; pass BASE to score the un-adapted base model",
    )
    p.add_argument("--base-model", default=DEFAULT_BASE_MODEL)
    p.add_argument(
        "--eval-dir", type=Path, default=PROJECT_ROOT / "training-data" / "sft"
    )
    p.add_argument(
        "--eval-files",
        nargs="*",
        default=DEFAULT_EVAL_FILES,
        help="Filenames inside --eval-dir",
    )
    p.add_argument("--max-length", type=int, default=1024)
    p.add_argument(
        "--per-file-limit",
        type=int,
        default=0,
        help="Cap records per source file (0 = all)",
    )
    p.add_argument("--dtype", choices=["auto", "bf16", "fp16", "fp32"], default="auto")
    p.add_argument(
        "--no-4bit",
        action="store_true",
        help="Disable bnb 4-bit quant (fp16/bf16 only)",
    )
    p.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    eval_paths: list[Path] = []
    for name in args.eval_files:
        candidate = args.eval_dir / name
        if not candidate.exists():
            print(f"  SKIP {name} (not found at {candidate})", file=sys.stderr)
            continue
        eval_paths.append(candidate)
    if not eval_paths:
        print("ERROR: no eval files resolved", file=sys.stderr)
        return 2

    print(f"Loading base={args.base_model} adapter={args.adapter}")
    t0 = time.time()
    tokenizer, model, device = load_model_and_tokenizer(
        args.base_model, args.adapter, args.dtype, use_4bit=not args.no_4bit
    )
    print(f"Loaded in {time.time() - t0:.1f}s on {device}")

    metrics: list[FileMetrics] = []
    eval_t0 = time.time()
    for path in eval_paths:
        f_t0 = time.time()
        m = score_file(
            path,
            tokenizer,
            model,
            device,
            max_length=args.max_length,
            per_file_limit=args.per_file_limit,
        )
        metrics.append(m)
        print(
            f"  {path.name:48s} n={m.n_records:>4d} tok={m.n_assistant_tokens:>6d} "
            f"nll={m.mean_nll:.4f} ppl={m.perplexity:.2f}  ({time.time() - f_t0:.1f}s)"
        )
    elapsed = time.time() - eval_t0

    runtime_meta = {
        "python": sys.version.split()[0],
        "device": str(device),
        "max_length": args.max_length,
        "per_file_limit": args.per_file_limit,
        "use_4bit": not args.no_4bit,
        "dtype": args.dtype,
    }
    paths = write_report(
        args.output_root, args.adapter, args.base_model, metrics, elapsed, runtime_meta
    )

    total_records = sum(m.n_records for m in metrics)
    total_tokens = sum(m.n_assistant_tokens for m in metrics)
    total_nll = sum(m.sum_nll for m in metrics)
    overall = math.exp(total_nll / total_tokens) if total_tokens else 0.0
    print()
    print(f"Total records:   {total_records}")
    print(f"Total tokens:    {total_tokens}")
    print(f"Mean NLL:        {total_nll / total_tokens if total_tokens else 0:.4f}")
    print(f"Perplexity:      {overall:.3f}")
    print(f"Report (JSON):   {paths['json']}")
    print(f"Report (MD):     {paths['markdown']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
