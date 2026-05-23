#!/usr/bin/env python3
"""Run a local/free writing benchmark against Ollama models.

This harness intentionally avoids hosted APIs. It compares locally installed
Ollama models on deterministic writing constraints and saves a JSON receipt.
The score is useful for usability and instruction-following triage; it is not
an automated literary-quality judgment.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "config" / "eval" / "aether_writing_score.v1.json"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "benchmarks" / "aether_writing_score"
DEFAULT_LOCAL_MODELS = (
    "qwen2.5:7b-instruct",
    "openclaw:latest",
    "qwen2.5-coder:1.5b",
    "scbe-geoseal-coder:q8",
)

WORD_RE = re.compile(r"\b[\w'-]+\b", re.UNICODE)


@dataclass
class TaskScore:
    task_id: str
    title: str
    score: float
    passed: bool
    word_count: int
    latency_s: float
    checks: dict[str, Any]
    output: str
    error: str | None = None


@dataclass
class ModelScore:
    model: str
    score: float
    pass_rate: float
    passed_tasks: int
    total_tasks: int
    total_latency_s: float
    tasks: list[TaskScore]


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def list_downloaded_ollama_models() -> set[str]:
    try:
        proc = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=20, check=False)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return set()
    models: set[str] = set()
    for line in proc.stdout.splitlines()[1:]:
        parts = line.split()
        if parts:
            name = parts[0].strip()
            if name and ":cloud" not in name:
                models.add(name)
    return models


def select_models(requested: list[str] | None) -> list[str]:
    downloaded = list_downloaded_ollama_models()
    candidates = requested or list(DEFAULT_LOCAL_MODELS)
    return [model for model in candidates if model in downloaded and ":cloud" not in model]


def call_ollama(
    model: str,
    prompt: str,
    *,
    timeout_s: int = 120,
    num_predict: int = 420,
    temperature: float = 0.2,
) -> tuple[str, str | None, float]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": num_predict,
            "temperature": temperature,
            "top_p": 0.9,
        },
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return str(body.get("response", "")).strip(), None, time.monotonic() - started
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return "", f"{type(exc).__name__}: {exc}", time.monotonic() - started


def word_count(text: str) -> int:
    return len(WORD_RE.findall(text))


def _contains_term(text: str, term: str) -> bool:
    if term.isupper() and len(term) <= 4:
        return term in text
    return term.casefold() in text.casefold()


def _line_prefix_present(text: str, prefix: str) -> bool:
    return any(line.strip().startswith(prefix) for line in text.splitlines())


def _heading_present(text: str, heading: str) -> bool:
    markers = {heading, f"# {heading}", f"## {heading}", f"### {heading}", f"**{heading}**"}
    return any(line.strip().rstrip(":") in markers for line in text.splitlines())


def _extract_json_array(text: str) -> Any:
    fenced = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.IGNORECASE | re.DOTALL)
    if fenced:
        return json.loads(fenced.group(1))
    start = text.find("[")
    end = text.rfind("]")
    if start >= 0 and end > start:
        return json.loads(text[start : end + 1])
    raise ValueError("no JSON array found")


def score_output(task: dict[str, Any], output: str, latency_s: float, error: str | None = None) -> TaskScore:
    checks: dict[str, Any] = {}
    if error:
        return TaskScore(
            task_id=task["task_id"],
            title=task["title"],
            score=0.0,
            passed=False,
            word_count=0,
            latency_s=round(latency_s, 3),
            checks={"runtime_error": error},
            output=output,
            error=error,
        )

    wc = word_count(output)
    min_words = int(task.get("min_words", 0))
    max_words = int(task.get("max_words", 10**9))
    checks["word_count"] = {"value": wc, "min": min_words, "max": max_words, "pass": min_words <= wc <= max_words}

    required_terms = list(task.get("required_terms", []))
    checks["required_terms"] = {term: _contains_term(output, term) for term in required_terms}

    forbidden_terms = list(task.get("forbidden_terms", []))
    checks["forbidden_terms_absent"] = {term: not _contains_term(output, term) for term in forbidden_terms}

    required_headings = list(task.get("required_headings", []))
    if required_headings:
        checks["required_headings"] = {heading: _heading_present(output, heading) for heading in required_headings}

    required_line_prefixes = list(task.get("required_line_prefixes", []))
    if required_line_prefixes:
        checks["required_line_prefixes"] = {
            prefix: _line_prefix_present(output, prefix) for prefix in required_line_prefixes
        }

    exactly_once_terms = list(task.get("exactly_once_terms", []))
    if exactly_once_terms:
        checks["exactly_once_terms"] = {term: output.count(term) == 1 for term in exactly_once_terms}

    if task.get("requires_dialogue"):
        checks["dialogue"] = bool(re.search(r'"[^"]+"|“[^”]+”', output))

    json_fields = list(task.get("required_json_array_fields", []))
    if json_fields:
        try:
            parsed = _extract_json_array(output)
            valid = isinstance(parsed, list) and bool(parsed)
            if valid:
                valid = all(isinstance(item, dict) and all(field in item for field in json_fields) for item in parsed)
            checks["json_array_fields"] = {
                "pass": bool(valid),
                "fields": json_fields,
                "items": len(parsed) if isinstance(parsed, list) else 0,
            }
        except (ValueError, json.JSONDecodeError) as exc:
            checks["json_array_fields"] = {"pass": False, "fields": json_fields, "error": str(exc)}

    leaf_results: list[bool] = []
    for value in checks.values():
        if isinstance(value, bool):
            leaf_results.append(value)
        elif isinstance(value, dict) and "pass" in value:
            leaf_results.append(bool(value["pass"]))
        elif isinstance(value, dict):
            leaf_results.extend(bool(v) for v in value.values() if isinstance(v, bool))

    score = round((sum(leaf_results) / len(leaf_results) * 100.0) if leaf_results else 0.0, 2)
    return TaskScore(
        task_id=task["task_id"],
        title=task["title"],
        score=score,
        passed=score >= 80.0,
        word_count=wc,
        latency_s=round(latency_s, 3),
        checks=checks,
        output=output,
    )


def run_benchmark(
    *,
    config_path: Path = DEFAULT_CONFIG,
    models: list[str] | None = None,
    timeout_s: int = 120,
    num_predict: int = 420,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    config = load_config(config_path)
    selected = select_models(models)
    started_at = datetime.now(timezone.utc).isoformat()
    model_scores: list[ModelScore] = []

    for model in selected:
        task_scores: list[TaskScore] = []
        for task in config["tasks"]:
            output, error, latency = call_ollama(
                model,
                task["prompt"],
                timeout_s=timeout_s,
                num_predict=num_predict,
            )
            task_scores.append(score_output(task, output, latency, error))
        total = len(task_scores)
        passed = sum(1 for task_score in task_scores if task_score.passed)
        avg = round(sum(task_score.score for task_score in task_scores) / total, 2) if total else 0.0
        model_scores.append(
            ModelScore(
                model=model,
                score=avg,
                pass_rate=round(passed / total, 3) if total else 0.0,
                passed_tasks=passed,
                total_tasks=total,
                total_latency_s=round(sum(task_score.latency_s for task_score in task_scores), 3),
                tasks=task_scores,
            )
        )

    ranked = sorted(model_scores, key=lambda item: (item.score, item.pass_rate, -item.total_latency_s), reverse=True)
    report = {
        "schema_version": config["schema_version"],
        "created_at": started_at,
        "policy": config.get("policy", {}),
        "config_path": str(config_path.relative_to(REPO_ROOT)),
        "models_requested": models or list(DEFAULT_LOCAL_MODELS),
        "models_run": [score.model for score in model_scores],
        "ranking": [
            {
                "rank": index + 1,
                "model": score.model,
                "score": score.score,
                "pass_rate": score.pass_rate,
                "passed_tasks": score.passed_tasks,
                "total_tasks": score.total_tasks,
                "total_latency_s": score.total_latency_s,
            }
            for index, score in enumerate(ranked)
        ],
        "results": [asdict(score) for score in model_scores],
    }

    output_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = output_root / f"writing_benchmark_{stamp}.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    report["artifact_path"] = str(out_path.relative_to(REPO_ROOT))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--models", help="comma-separated local Ollama model names")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--num-predict", type=int, default=420)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--json", action="store_true", help="print full JSON report")
    args = parser.parse_args()

    models = [item.strip() for item in args.models.split(",")] if args.models else None
    report = run_benchmark(
        config_path=args.config,
        models=models,
        timeout_s=args.timeout,
        num_predict=args.num_predict,
        output_root=args.out_dir,
    )

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return

    print(f"Aether Writing Score v1 — {report['artifact_path']}")
    print("Policy: local/free Ollama only; hosted_api_allowed=false")
    if not report["models_run"]:
        print("No downloaded local Ollama models matched the requested model list.")
        return
    for row in report["ranking"]:
        print(
            f"{row['rank']}. {row['model']}: {row['score']}/100 "
            f"({row['passed_tasks']}/{row['total_tasks']} pass, {row['total_latency_s']}s)"
        )


if __name__ == "__main__":
    main()
