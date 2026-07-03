from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from datasets import load_dataset

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.scbe.poly_channel import (
    classify_row,
    format_summary_table,
    normalize_number,
    parse_model_response,
    run_javascript,
    run_python,
    summarize,
)


DEFAULT_OUT = ROOT / "artifacts" / "benchmarks" / "poly_channel"


def gsm8k_gold(answer: str) -> float:
    m = re.search(r"####\s*([-+0-9,./]+)", answer)
    if not m:
        value = normalize_number(answer)
    else:
        value = normalize_number(m.group(1))
    if value is None:
        raise ValueError(f"could not parse GSM8K gold answer: {answer!r}")
    return value


def load_gsm8k_sample(n: int, seed: int) -> list[dict[str, Any]]:
    data = load_dataset("gsm8k", "main", split="test")
    idxs = list(range(len(data)))
    random.Random(seed).shuffle(idxs)
    rows = []
    for idx in idxs[:n]:
        item = data[int(idx)]
        rows.append(
            {
                "dataset": "gsm8k/main/test",
                "dataset_index": int(idx),
                "question": item["question"],
                "answer": item["answer"],
                "gold": gsm8k_gold(item["answer"]),
            }
        )
    return rows


def prompt_for(question: str) -> str:
    return f"""Solve the grade-school math problem.

Return ONLY valid JSON with these keys:
- final_answer: the final numeric answer only
- confidence: a number from 0.0 to 1.0
- python_code: Python code that prints only the numeric answer
- javascript_code: JavaScript code for Node that prints only the numeric answer
- explanation: one short sentence

Problem:
{question}
"""


def ask_ollama(host: str, model: str, prompt: str, timeout: int, seed: int) -> str:
    r = requests.post(
        f"{host.rstrip('/')}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0,
                "seed": seed,
                "num_predict": 700,
            },
        },
        timeout=timeout,
    )
    r.raise_for_status()
    payload = r.json()
    return str(payload.get("response", ""))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def rescore_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rescored = []
    for row in rows:
        parsed = row.get("parsed") or {}
        py = row.get("python") or {}
        js = row.get("javascript") or {}
        if "gold" not in row:
            rescored.append(row)
            continue
        cls = classify_row(
            gold=float(row["gold"]),
            final_value=parsed.get("final_value"),
            py_value=py.get("value"),
            js_value=js.get("value"),
            model_confidence=float(parsed.get("confidence", 0.0)),
        )
        rescored.append({**row, **cls})
    return rescored


def write_report(out_dir: Path, rows: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    rows = rescore_rows(rows)
    summary = summarize(rows, threshold=args.threshold)
    report = {
        "schema": "scbe_poly_channel_benchmark_v1",
        "score_policy": "final_contradiction_blocks_py_js_promotion",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "n": len(rows),
        "seed": args.seed,
        "threshold": args.threshold,
        "summary": summary,
        "claim_boundary": [
            "The JavaScript face is a partially independent execution channel.",
            "It can catch runtime/transcription divergence.",
            "It does not independently reread the word problem, so shared misreads can survive.",
            "Python/JavaScript agreement does not promote trust when the final/prose answer contradicts it.",
        ],
    }
    (out_dir / "summary.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "summary.md").write_text(
        "# Polyglot 3rd-Channel Benchmark\n\n"
        f"Model: `{args.model}`\n\n"
        f"Dataset: GSM8K main/test, seeded sample `{args.seed}`\n\n"
        f"n: `{len(rows)}`\n\n"
        "```text\n"
        + format_summary_table(summary)
        + "\n```\n\n"
        "Boundary: JS execution is a partially independent runtime face, not an independent reading of the problem.\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Measure Python+JavaScript execution-channel trust on GSM8K.")
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--model", default="qwen2.5-coder:1.5b")
    ap.add_argument("--host", default="http://127.0.0.1:11434")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT))
    ap.add_argument("--threshold", type=float, default=0.92)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--limit-new", type=int, default=None, help="debug: process at most this many new rows")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    sample_path = out_dir / "sample.json"
    rows_path = out_dir / "rows.jsonl"

    if sample_path.exists():
        sample = json.loads(sample_path.read_text(encoding="utf-8"))
    else:
        sample = load_gsm8k_sample(args.n, args.seed)
        sample_path.write_text(json.dumps(sample, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    done = {row["dataset_index"] for row in read_jsonl(rows_path)}
    processed = 0
    for i, item in enumerate(sample, 1):
        if item["dataset_index"] in done:
            continue
        if args.limit_new is not None and processed >= args.limit_new:
            break
        print(f"[{i}/{len(sample)}] idx={item['dataset_index']}", flush=True)
        started = time.time()
        raw = ask_ollama(args.host, args.model, prompt_for(item["question"]), args.timeout, args.seed)
        parsed = parse_model_response(raw)
        py = run_python(parsed["python_code"])
        js = run_javascript(parsed["javascript_code"])
        cls = classify_row(
            gold=float(item["gold"]),
            final_value=parsed["final_value"],
            py_value=py.value,
            js_value=js.value,
            model_confidence=float(parsed["confidence"]),
        )
        row = {
            **item,
            "model": args.model,
            "raw_response": raw,
            "parsed": parsed,
            "python": py.__dict__,
            "javascript": js.__dict__,
            **cls,
            "duration_s": round(time.time() - started, 3),
        }
        append_jsonl(rows_path, row)
        processed += 1
        done.add(item["dataset_index"])

    rows = read_jsonl(rows_path)
    rows = [r for r in rows if r.get("dataset_index") in {x["dataset_index"] for x in sample}]
    report = write_report(out_dir, rows, args)
    print(format_summary_table(report["summary"]))
    print(f"wrote {out_dir}")
    return 0 if len(rows) >= len(sample) else 2


if __name__ == "__main__":
    raise SystemExit(main())
