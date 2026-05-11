#!/usr/bin/env python3
"""Parallel batch augmenter for SFT JSONL files.

Wraps `augment_sft_with_dense_bundle` in a multiprocessing pool so a
whole directory of SFT files gets the dense_bundle treatment in
parallel. The bash-loop version processed files serially; this one
uses every available core.

Usage:
    python scripts/encoding/parallel_augment_sft.py \\
        --input-dir artifacts/kaggle_datasets/scbe-coding-agent-stage6-repair-v7/ \\
        --output-dir training-data/kaggle/dense_bundle_augmented/ \\
        --workers 8

Defaults: workers = number of CPUs - 1, glob = *.sft.jsonl.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

# Local import — keep relative to repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.encoding.dense_bundle import (  # noqa: E402
    DenseBundle,
    bundle_intent_profile,
    route_lane_for_bundle,
)


@dataclass
class JobResult:
    input_path: str
    output_path: str
    records_in: int
    records_out: int
    bundles_added: int
    elapsed_s: float
    error: str | None = None


def _augment_one_record(record: dict, target: str, default_view: str) -> dict:
    """Pure record augmentation. Identical semantics to augment_record in
    the sequential script — duplicated here so the worker process
    doesn't need to import the script module (which would be brittle
    across multiprocessing process boundaries).
    """
    messages = record.get("messages") or []
    content: str | None = None
    for msg in messages:
        if msg.get("role") == target:
            value = msg.get("content")
            if isinstance(value, str):
                content = value
            elif isinstance(value, list):
                content = "".join(p.get("text", "") for p in value if isinstance(p, dict))
            break
    if content is None or content == "":
        return record
    bundle = DenseBundle.from_text(content)
    return {
        **record,
        "dense_bundle": {
            "target": target,
            "default_view": default_view,
            "route_lane": route_lane_for_bundle(default_view, bundle),
            "intent_profile": bundle_intent_profile(bundle),
            "byte_length": bundle.byte_length,
            "density_ratio": bundle.density_ratio(),
            "views": {
                "hex": bundle.hex,
                "binary": bundle.binary,
                "base64": bundle.base64,
                "ternary": bundle.ternary,
            },
            "intent": list(bundle.intent),
        },
    }


def _augment_file(args: tuple[str, str, str, str]) -> JobResult:
    """Worker entry: augment one input file -> one output file."""
    input_path, output_path, target, default_view = args
    start = time.perf_counter()
    in_p = Path(input_path)
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    records_in = 0
    records_out = 0
    bundles_added = 0
    try:
        with in_p.open("r", encoding="utf-8") as fin, out_p.open("w", encoding="utf-8") as fout:
            for raw in fin:
                raw = raw.strip()
                if not raw:
                    continue
                records_in += 1
                try:
                    record = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                augmented = _augment_one_record(record, target=target, default_view=default_view)
                if "dense_bundle" in augmented:
                    bundles_added += 1
                fout.write(json.dumps(augmented, ensure_ascii=False))
                fout.write("\n")
                records_out += 1
    except Exception as err:  # surface, don't crash the pool
        return JobResult(
            input_path=input_path,
            output_path=output_path,
            records_in=records_in,
            records_out=records_out,
            bundles_added=bundles_added,
            elapsed_s=time.perf_counter() - start,
            error=f"{type(err).__name__}: {err}",
        )
    return JobResult(
        input_path=input_path,
        output_path=output_path,
        records_in=records_in,
        records_out=records_out,
        bundles_added=bundles_added,
        elapsed_s=time.perf_counter() - start,
    )


def _discover_inputs(input_dir: Path, pattern: str) -> list[Path]:
    return sorted(input_dir.glob(pattern))


def _output_path_for(input_path: Path, input_dir: Path, output_dir: Path, suffix: str) -> Path:
    rel = input_path.relative_to(input_dir)
    base = rel.name
    if base.endswith(".sft.jsonl"):
        new_name = base[: -len(".sft.jsonl")] + suffix
    elif base.endswith(".jsonl"):
        new_name = base[: -len(".jsonl")] + suffix
    else:
        new_name = base + suffix
    return output_dir / rel.parent / new_name


def run(
    input_dir: Path,
    output_dir: Path,
    pattern: str = "*.sft.jsonl",
    workers: int | None = None,
    target: str = "user",
    default_view: str = "hex",
    suffix: str = ".dense.jsonl",
) -> tuple[list[JobResult], dict]:
    """Run the parallel pool. Returns per-file results + aggregate stats."""
    inputs = _discover_inputs(input_dir, pattern)
    if not inputs:
        return [], {"files": 0, "records_in": 0, "records_out": 0, "bundles_added": 0, "elapsed_s": 0.0}

    workers = workers or max(1, (os.cpu_count() or 2) - 1)
    workers = min(workers, len(inputs))

    jobs = [(str(p), str(_output_path_for(p, input_dir, output_dir, suffix)), target, default_view) for p in inputs]

    started = time.perf_counter()
    if workers == 1:
        results = [_augment_file(job) for job in jobs]
    else:
        with mp.Pool(processes=workers) as pool:
            results = pool.map(_augment_file, jobs)
    elapsed = time.perf_counter() - started

    summary = {
        "files": len(results),
        "records_in": sum(r.records_in for r in results),
        "records_out": sum(r.records_out for r in results),
        "bundles_added": sum(r.bundles_added for r in results),
        "elapsed_s": elapsed,
        "workers": workers,
        "errors": sum(1 for r in results if r.error),
    }
    return results, summary


def _print_summary(results: Iterable[JobResult], summary: dict) -> None:
    for r in results:
        flag = f"  ERROR: {r.error}" if r.error else ""
        print(
            f"[{r.elapsed_s:6.2f}s] {Path(r.input_path).name}: "
            f"{r.records_in} in -> {r.records_out} out, +{r.bundles_added} bundles{flag}"
        )
    print("---")
    print(
        f"DONE: {summary['files']} files, {summary['records_in']} records, "
        f"+{summary['bundles_added']} bundles, {summary['elapsed_s']:.2f}s "
        f"using {summary['workers']} workers, {summary['errors']} errors"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parallel SFT dense-bundle augmenter.")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--pattern", default="*.sft.jsonl")
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--target", default="user", choices=["user", "system", "assistant"])
    parser.add_argument("--default-view", default="hex", choices=["hex", "binary", "base64", "ternary"])
    parser.add_argument("--suffix", default=".dense.jsonl")
    parser.add_argument("--quiet", action="store_true", help="Skip per-file lines, only print summary.")
    args = parser.parse_args(argv)

    if not args.input_dir.is_dir():
        print(f"[error] input dir not found: {args.input_dir}", file=sys.stderr)
        return 2

    results, summary = run(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        pattern=args.pattern,
        workers=args.workers,
        target=args.target,
        default_view=args.default_view,
        suffix=args.suffix,
    )
    if args.quiet:
        print(
            f"DONE: {summary['files']} files, {summary['records_in']} records, "
            f"+{summary['bundles_added']} bundles, {summary['elapsed_s']:.2f}s, "
            f"{summary['errors']} errors"
        )
    else:
        _print_summary(results, summary)
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
