#!/usr/bin/env python3
"""Run the legacy SCBE compliance eval suite against a text-generation model."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVAL_PATH = PROJECT_ROOT / "training-data" / "evals" / "compliance_evals.jsonl"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "artifacts" / "model_evals"
DEFAULT_MODEL_ID = "issdandavis/scbe-pivot-qwen-0.5b"


@dataclass
class EvalRecord:
    id: str
    category: str
    instruction: str
    expected: str
    response_should_contain: list[str]
    difficulty: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalResult:
    record: EvalRecord
    response: str
    matched_terms: list[str]
    missing_terms: list[str]
    term_match_ratio: float
    passed: bool


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or ""))
    normalized = normalized.replace("\u2018", "'").replace("\u2019", "'")
    normalized = normalized.replace("\u201c", '"').replace("\u201d", '"')
    normalized = normalized.replace("\u2212", "-")
    normalized = normalized.casefold()
    return " ".join(normalized.split())


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "").strip())
    slug = re.sub(r"-+", "-", slug).strip("-.")
    return slug or "model"


def load_eval_records(path: Path) -> list[EvalRecord]:
    records: list[EvalRecord] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"{path}:{line_number} must contain JSON objects")
            records.append(
                EvalRecord(
                    id=str(payload.get("id", f"eval-{line_number:03d}")),
                    category=str(payload.get("category", "uncategorized")),
                    instruction=str(payload.get("instruction", "")).strip(),
                    expected=str(payload.get("expected", "")).strip(),
                    response_should_contain=[
                        str(item).strip() for item in payload.get("response_should_contain", []) if str(item).strip()
                    ],
                    difficulty=str(payload.get("difficulty", "")).strip(),
                    metadata=payload.get("metadata", {}) if isinstance(payload.get("metadata", {}), dict) else {},
                )
            )
    return records


def build_prompt(record: EvalRecord) -> str:
    return (
        "You are answering a legacy SCBE evaluation question. "
        "Reply directly and include exact technical terms when you know them.\n\n"
        f"Question: {record.instruction}\n"
        "Answer:"
    )


def score_response(record: EvalRecord, response: str) -> EvalResult:
    normalized_response = _normalize_text(response)
    matched_terms: list[str] = []
    missing_terms: list[str] = []

    for term in record.response_should_contain:
        normalized_term = _normalize_text(term)
        if normalized_term and normalized_term in normalized_response:
            matched_terms.append(term)
        else:
            missing_terms.append(term)

    total_terms = len(record.response_should_contain)
    ratio = len(matched_terms) / total_terms if total_terms else 1.0
    passed = ratio >= 1.0
    return EvalResult(
        record=record,
        response=response,
        matched_terms=matched_terms,
        missing_terms=missing_terms,
        term_match_ratio=ratio,
        passed=passed,
    )


def evaluate_records(
    records: Iterable[EvalRecord],
    generate_fn: Callable[[EvalRecord], str],
) -> list[EvalResult]:
    results: list[EvalResult] = []
    for record in records:
        response = generate_fn(record).strip()
        results.append(score_response(record, response))
    return results


def summarize_results(results: Iterable[EvalResult]) -> dict[str, Any]:
    result_list = list(results)
    total = len(result_list)
    passed = sum(1 for result in result_list if result.passed)
    matched_terms = sum(len(result.matched_terms) for result in result_list)
    required_terms = sum(len(result.matched_terms) + len(result.missing_terms) for result in result_list)
    average_term_match_ratio = sum(result.term_match_ratio for result in result_list) / total if total else 0.0
    partial_hits = sum(1 for result in result_list if result.term_match_ratio > 0.0)
    categories: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "total": 0,
            "passed": 0,
            "partial_hits": 0,
            "matched_terms": 0,
            "required_terms": 0,
            "difficulties": Counter(),
        }
    )

    for result in result_list:
        bucket = categories[result.record.category]
        bucket["total"] += 1
        bucket["passed"] += 1 if result.passed else 0
        bucket["partial_hits"] += 1 if result.term_match_ratio > 0.0 else 0
        bucket["matched_terms"] += len(result.matched_terms)
        bucket["required_terms"] += len(result.matched_terms) + len(result.missing_terms)
        if result.record.difficulty:
            bucket["difficulties"][result.record.difficulty] += 1

    for bucket in categories.values():
        total_bucket = bucket["total"] or 1
        bucket["pass_rate"] = bucket["passed"] / total_bucket
        bucket["global_term_coverage"] = (
            bucket["matched_terms"] / bucket["required_terms"] if bucket["required_terms"] else 0.0
        )
        bucket["difficulties"] = dict(bucket["difficulties"])

    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": passed / total if total else 0.0,
        "average_term_match_ratio": average_term_match_ratio,
        "matched_terms": matched_terms,
        "required_terms": required_terms,
        "global_term_coverage": matched_terms / required_terms if required_terms else 0.0,
        "partial_hits": partial_hits,
        "categories": dict(categories),
    }


def _extract_chat_text(response: Any) -> str:
    choices = getattr(response, "choices", None) or []
    if not choices:
        return str(response)
    message = getattr(choices[0], "message", None)
    content = getattr(message, "content", "")
    if isinstance(content, list):
        text_parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(str(block.get("text", "")))
            elif hasattr(block, "text"):
                text_parts.append(str(block.text))
        return "\n".join(part for part in text_parts if part).strip()
    return str(content).strip()


def _resolve_hf_token(token_env: str) -> str:
    token = os.environ.get(token_env, "").strip()
    if not token:
        token = os.environ.get("HUGGINGFACE_TOKEN", "").strip() or os.environ.get("HUGGINGFACE_API_KEY", "").strip()
    if not token:
        raise RuntimeError("HF_TOKEN (or HUGGINGFACE_TOKEN/HUGGINGFACE_API_KEY) is required for live evaluation")
    return token


def _generate_with_hf_endpoint(
    model_id: str,
    prompt: str,
    *,
    token: str,
    max_new_tokens: int = 220,
    temperature: float = 0.1,
) -> str:
    try:
        from huggingface_hub import InferenceClient  # type: ignore[import-untyped]
    except Exception as exc:  # pragma: no cover - environment-dependent import
        raise RuntimeError("huggingface_hub is not installed") from exc

    client = InferenceClient(model=model_id, token=token)

    try:
        chat_response = client.chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are taking a strict SCBE regression evaluation. "
                        "Answer directly, factually, and include exact domain terms."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_new_tokens,
            temperature=temperature,
        )
        text = _extract_chat_text(chat_response)
        if text:
            return text
    except Exception:
        pass

    text_response = client.text_generation(
        prompt=prompt,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        return_full_text=False,
    )
    return text_response if isinstance(text_response, str) else str(text_response)


def _load_local_adapter_generator(
    model_id: str,
    *,
    token: str,
    max_new_tokens: int,
    temperature: float,
) -> Callable[[str], str]:
    try:
        import torch
        from huggingface_hub import hf_hub_download  # type: ignore[import-untyped]
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except Exception as exc:  # pragma: no cover - environment-dependent import
        raise RuntimeError("Local adapter fallback requires torch, transformers, peft, and huggingface_hub") from exc

    adapter_config_path = hf_hub_download(repo_id=model_id, filename="adapter_config.json", token=token)
    adapter_config = json.loads(Path(adapter_config_path).read_text(encoding="utf-8"))
    configured_base = str(adapter_config.get("base_model_name_or_path", "")).strip()

    base_candidates: list[str] = []
    if configured_base:
        base_candidates.append(configured_base)
    lowered = configured_base.casefold()
    if "qwen2.5-0.5b" in lowered and "qwen/qwen2.5-0.5b-instruct" not in lowered:
        base_candidates.append("Qwen/Qwen2.5-0.5B-Instruct")

    base_errors: list[str] = []
    base_model = None
    selected_base = ""
    for candidate in base_candidates:
        try:
            base_model = AutoModelForCausalLM.from_pretrained(
                candidate,
                token=token,
                torch_dtype="auto",
                low_cpu_mem_usage=True,
            )
            selected_base = candidate
            break
        except Exception as exc:  # pragma: no cover - environment-dependent path
            base_errors.append(f"{candidate}: {exc}")

    if base_model is None:
        joined = " | ".join(base_errors) if base_errors else "no base model candidates were available"
        raise RuntimeError(f"Unable to load a base model for adapter evaluation: {joined}")

    model = PeftModel.from_pretrained(base_model, model_id, token=token)
    model.eval()

    tokenizer = None
    tokenizer_errors: list[str] = []
    for candidate in [model_id, selected_base]:
        if not candidate:
            continue
        try:
            tokenizer = AutoTokenizer.from_pretrained(candidate, token=token)
            break
        except Exception as exc:  # pragma: no cover - environment-dependent path
            tokenizer_errors.append(f"{candidate}: {exc}")

    if tokenizer is None:
        raise RuntimeError(f"Unable to load tokenizer for adapter evaluation: {' | '.join(tokenizer_errors)}")

    if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
        tokenizer.pad_token_id = tokenizer.eos_token_id

    device = next(model.parameters()).device
    do_sample = temperature > 0

    def _generate(prompt: str) -> str:
        if getattr(tokenizer, "chat_template", None):
            inputs = tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}],
                tokenize=True,
                add_generation_prompt=True,
                return_tensors="pt",
            )
        else:
            encoded = tokenizer(prompt, return_tensors="pt")
            inputs = encoded["input_ids"]

        attention_mask = None
        if hasattr(inputs, "shape"):
            input_ids = inputs.to(device)
        else:
            input_ids = inputs["input_ids"].to(device)
            attention_mask = inputs.get("attention_mask")
            if attention_mask is not None:
                attention_mask = attention_mask.to(device)

        with torch.no_grad():
            outputs = model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_new_tokens=max_new_tokens,
                temperature=temperature if do_sample else None,
                do_sample=do_sample,
                pad_token_id=tokenizer.pad_token_id,
            )
        generated = outputs[0][input_ids.shape[-1] :]
        return tokenizer.decode(generated, skip_special_tokens=True).strip()

    return _generate


def make_generate_fn(
    model_id: str,
    *,
    token_env: str = "HF_TOKEN",
    max_new_tokens: int = 220,
    temperature: float = 0.1,
) -> Callable[[EvalRecord], str]:
    token = _resolve_hf_token(token_env)
    local_generator: dict[str, Callable[[str], str]] = {}

    def _generate(record: EvalRecord) -> str:
        prompt = build_prompt(record)
        try:
            return _generate_with_hf_endpoint(
                model_id,
                prompt,
                token=token,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
            )
        except Exception as exc:
            message = str(exc)
            should_fallback = (
                isinstance(exc, StopIteration)
                or "provider" in message.casefold()
                or "inference" in message.casefold()
                or "404" in message
            )
            if not should_fallback:
                raise
            if "local" not in local_generator:
                local_generator["local"] = _load_local_adapter_generator(
                    model_id,
                    token=token,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                )
            return local_generator["local"](prompt)

    return _generate


def write_report(
    output_root: Path,
    model_id: str,
    summary: dict[str, Any],
    results: list[EvalResult],
) -> dict[str, Path]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bundle_dir = output_root / f"{_safe_slug(model_id)}-{stamp}"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    json_path = bundle_dir / "legacy_eval_results.json"
    md_path = bundle_dir / "legacy_eval_report.md"

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_id": model_id,
        "runtime": {
            "python_executable": sys.executable,
            "python_version": sys.version,
        },
        "summary": summary,
        "results": [
            {
                **asdict(result.record),
                "response": result.response,
                "matched_terms": result.matched_terms,
                "missing_terms": result.missing_terms,
                "term_match_ratio": result.term_match_ratio,
                "passed": result.passed,
            }
            for result in results
        ],
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        f"# Legacy Eval Report — {model_id}",
        "",
        f"- generated_at_utc: `{payload['generated_at_utc']}`",
        f"- total_cases: `{summary['total']}`",
        f"- passed: `{summary['passed']}`",
        f"- failed: `{summary['failed']}`",
        f"- pass_rate: `{summary['pass_rate']:.2%}`",
        f"- partial_hits: `{summary['partial_hits']}`",
        f"- average_term_match_ratio: `{summary['average_term_match_ratio']:.2%}`",
        f"- global_term_coverage: `{summary['global_term_coverage']:.2%}`",
        f"- runtime_python: `{payload['runtime']['python_executable']}`",
        "",
        "## Category Breakdown",
        "",
        "| Category | Passed | Total | Pass Rate | Coverage | Partial Hits |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for category, bucket in sorted(summary["categories"].items()):
        lines.append(
            f"| {category} | {bucket['passed']} | {bucket['total']} | {bucket['pass_rate']:.2%} | "
            f"{bucket['global_term_coverage']:.2%} | {bucket['partial_hits']} |"
        )

    failures = [result for result in results if not result.passed]
    if failures:
        lines.extend(["", "## Failed Cases", ""])
        for result in failures[:12]:
            lines.extend(
                [
                    f"### {result.record.id} — {result.record.category}",
                    f"- instruction: {result.record.instruction}",
                    f"- missing_terms: {', '.join(result.missing_terms)}",
                    f"- response_excerpt: {result.response[:500]}",
                    "",
                ]
            )

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID, help="Model repo to evaluate")
    parser.add_argument("--eval-path", type=Path, default=DEFAULT_EVAL_PATH, help="Legacy eval JSONL path")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT, help="Output directory for reports")
    parser.add_argument("--limit", type=int, default=0, help="Optional cap on the number of eval records")
    parser.add_argument("--token-env", default="HF_TOKEN", help="Environment variable holding the HF token")
    parser.add_argument("--max-new-tokens", type=int, default=220)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--json", action="store_true", help="Print the summary payload as JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    records = load_eval_records(args.eval_path)
    if args.limit > 0:
        records = records[: args.limit]

    generate_fn = make_generate_fn(
        args.model_id,
        token_env=args.token_env,
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
    )
    results = evaluate_records(records, generate_fn)
    summary = summarize_results(results)
    paths = write_report(args.output_root, args.model_id, summary, results)

    payload = {
        "model_id": args.model_id,
        "eval_path": str(args.eval_path),
        "summary": summary,
        "report_json": str(paths["json"]),
        "report_markdown": str(paths["markdown"]),
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Model: {args.model_id}")
        print(f"Suite:  {args.eval_path}")
        print(f"Pass:   {summary['passed']}/{summary['total']} ({summary['pass_rate']:.2%})")
        print(f"JSON:   {paths['json']}")
        print(f"MD:     {paths['markdown']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
