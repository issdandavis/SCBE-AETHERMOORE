from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def load_drill_rows(path: str | Path) -> list[dict]:
    rows: list[dict] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def holdout_bucket_for_text(text: str, modulo: int) -> int:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % modulo


def split_rows(
    rows: Iterable[dict],
    *,
    split: str,
    holdout_mod: int = 10,
    holdout_bucket: int = 0,
) -> list[dict]:
    if split not in {"all", "train", "holdout"}:
        raise ValueError(f"split must be one of all/train/holdout, got {split!r}")

    selected: list[dict] = []
    for row in rows:
        bucket = holdout_bucket_for_text(row["text"], holdout_mod)
        if split == "all":
            selected.append(row)
        elif split == "holdout" and bucket == holdout_bucket:
            selected.append(row)
        elif split == "train" and bucket != holdout_bucket:
            selected.append(row)
    return selected


def limit_rows_per_cell(rows: Iterable[dict], max_per_cell: int | None) -> list[dict]:
    if not max_per_cell or max_per_cell <= 0:
        return list(rows)
    counts: dict[tuple[str, str, str], int] = defaultdict(int)
    kept: list[dict] = []
    for row in rows:
        key = (row.get("map", ""), row.get("tongue", ""), row.get("kind", ""))
        if counts[key] >= max_per_cell:
            continue
        counts[key] += 1
        kept.append(row)
    return kept


def summarize_losses(scored_rows: Iterable[dict]) -> dict:
    per_map: dict[str, list[float]] = defaultdict(list)
    per_kind: dict[str, list[float]] = defaultdict(list)
    per_tongue: dict[str, list[float]] = defaultdict(list)
    per_map_kind: dict[str, list[float]] = defaultdict(list)

    total = 0
    total_loss = 0.0
    for row in scored_rows:
        loss = float(row["loss"])
        map_name = row.get("map", "unknown")
        kind = row.get("kind", "unknown")
        tongue = row.get("tongue", "unknown")
        total += 1
        total_loss += loss
        per_map[map_name].append(loss)
        per_kind[kind].append(loss)
        per_tongue[tongue].append(loss)
        per_map_kind[f"{map_name}:{kind}"].append(loss)

    def _pack(values: dict[str, list[float]]) -> dict[str, dict[str, float]]:
        packed: dict[str, dict[str, float]] = {}
        for key, losses in sorted(values.items()):
            avg = sum(losses) / len(losses)
            packed[key] = {
                "count": len(losses),
                "avg_loss": avg,
                "perplexity": math.exp(avg),
            }
        return packed

    avg_total = total_loss / total if total else 0.0
    return {
        "_summary": {
            "count": total,
            "avg_loss": avg_total,
            "perplexity": math.exp(avg_total) if total else 1.0,
        },
        "by_map": _pack(per_map),
        "by_kind": _pack(per_kind),
        "by_tongue": _pack(per_tongue),
        "by_map_kind": _pack(per_map_kind),
    }


def verifier_for_row(row: dict) -> str | None:
    map_name = row.get("map", "")
    kind = row.get("kind", "")

    if map_name == "transport_atomic":
        if kind == "transport":
            return "ss2_transport_fields"
        if kind in {"reaction_template", "reaction_predict"}:
            return "chemistry_conservation"
        if kind == "reaction_stability":
            return "chemistry_stability_label"
        if kind == "reaction_capsule":
            return "chemistry_capsule_fields"
    if map_name == "atomic_semantic" and kind == "state":
        return "atomic_state_fields"
    if map_name == "convergence_action" and kind == "packet":
        return "convergence_packet_fields"
    if map_name == "convergence_action" and kind == "anchor":
        return "convergence_anchor_fields"
    if map_name == "cartography_state" and kind == "packet":
        return "cartography_packet_fields"
    if map_name == "cartography_state" and kind == "route":
        return "cartography_route_fields"
    if map_name == "cross_braid_code" and kind in {"pair", "anchor_code", "witness_code"}:
        return "cross_braid_surface"
    if map_name in {
        "paradigm_isomorphism",
        "runtime_emission",
        "spirit_narrative",
        "opcode_runtime",
    } and kind in {"packet", "rationale", "code", "anchor"}:
        return "lane_alignment_fields"
    if map_name == "element_periodic" and kind in {
        "binary_anchor",
        "math_anchor",
        "code_python",
        "code_typescript",
        "code_rust",
        "code_haskell",
        "code_lisp",
        "tongue_binding",
    }:
        return "periodic_table_fields"
    if map_name == "qa_invariance" and kind in {
        "hyperbolic_distance",
        "harmonic_wall",
        "comma_drift",
        "phi_ladder",
        "phase_delta",
    }:
        return "qa_invariance_fields"
    return None


def summarize_structural_rows(rows: Iterable[dict]) -> dict:
    total = 0
    structural = 0
    by_map_total: Counter[str] = Counter()
    by_map_structural: Counter[str] = Counter()
    by_verifier: Counter[str] = Counter()
    by_map_kind: Counter[str] = Counter()

    for row in rows:
        total += 1
        map_name = row.get("map", "unknown")
        kind = row.get("kind", "unknown")
        verifier = verifier_for_row(row)
        by_map_total[map_name] += 1
        if verifier:
            structural += 1
            by_map_structural[map_name] += 1
            by_verifier[verifier] += 1
            by_map_kind[f"{map_name}:{kind}"] += 1

    by_map: dict[str, dict[str, float]] = {}
    for map_name in sorted(by_map_total):
        total_rows = by_map_total[map_name]
        structural_rows = by_map_structural.get(map_name, 0)
        by_map[map_name] = {
            "count": total_rows,
            "structural_count": structural_rows,
            "structural_ratio": structural_rows / total_rows if total_rows else 0.0,
        }

    return {
        "_summary": {
            "count": total,
            "structural_count": structural,
            "structural_ratio": structural / total if total else 0.0,
        },
        "by_map": by_map,
        "by_verifier": dict(sorted(by_verifier.items())),
        "by_map_kind": dict(sorted(by_map_kind.items())),
    }


def load_model(source: str, device: str = "cuda"):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(source)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model_kwargs = {
        "low_cpu_mem_usage": True,
        "dtype": torch.float16 if device == "cuda" else torch.float32,
    }
    model = AutoModelForCausalLM.from_pretrained(source, **model_kwargs)
    if str(device).lower() != "cpu":
        model = model.to(device)
    model.eval()
    return tokenizer, model


def score_rows(rows: Iterable[dict], tokenizer, model, *, max_length: int = 256) -> list[dict]:
    import torch

    scored: list[dict] = []
    for row in rows:
        encoded = tokenizer(
            row["text"],
            return_tensors="pt",
            truncation=True,
            max_length=max_length,
        ).to(model.device)
        encoded["labels"] = encoded["input_ids"].clone()
        with torch.no_grad():
            out = model(**encoded)
        scored.append(
            {
                "map": row.get("map", "unknown"),
                "kind": row.get("kind", "unknown"),
                "tongue": row.get("tongue", "unknown"),
                "value": row.get("value", ""),
                "loss": float(out.loss.item()),
                "text_preview": row["text"][:120],
            }
        )
    return scored


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_path", type=str, default=None)
    parser.add_argument("--hf_id", type=str, default=None)
    parser.add_argument("--data", type=str, required=True)
    parser.add_argument("--split", choices=["all", "train", "holdout"], default="holdout")
    parser.add_argument("--holdout_mod", type=int, default=10)
    parser.add_argument("--holdout_bucket", type=int, default=0)
    parser.add_argument("--max_per_cell", type=int, default=20)
    parser.add_argument("--max_length", type=int, default=256)
    parser.add_argument("--device", type=str, default="cuda")
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args(argv)

    source = args.model_path or args.hf_id
    if not source:
        print("ERROR: --model_path or --hf_id required", file=sys.stderr)
        return 2

    rows = load_drill_rows(args.data)
    rows = split_rows(
        rows,
        split=args.split,
        holdout_mod=args.holdout_mod,
        holdout_bucket=args.holdout_bucket,
    )
    rows = limit_rows_per_cell(rows, args.max_per_cell)
    structural = summarize_structural_rows(rows)

    print(f"Loading model: {source}")
    tokenizer, model = load_model(source, device=args.device)
    print(f"Scoring {len(rows)} rows from {args.data} [{args.split}]")

    scored = score_rows(rows, tokenizer, model, max_length=args.max_length)
    summary = summarize_losses(scored)
    summary["_config"] = {
        "source": source,
        "data": args.data,
        "split": args.split,
        "holdout_mod": args.holdout_mod,
        "holdout_bucket": args.holdout_bucket,
        "max_per_cell": args.max_per_cell,
        "max_length": args.max_length,
    }
    summary["_structural"] = structural

    print(
        f"DRILL MAP EVAL: {summary['_summary']['count']} rows  "
        f"loss={summary['_summary']['avg_loss']:.4f}  "
        f"ppl={summary['_summary']['perplexity']:.2f}"
    )
    print(
        f"STRUCTURAL COVERAGE: {structural['_summary']['structural_count']}/"
        f"{structural['_summary']['count']} "
        f"= {structural['_summary']['structural_ratio']:.1%}"
    )
    for map_name, stats in summary["by_map"].items():
        print(
            f"  {map_name}: {stats['count']} rows  "
            f"loss={stats['avg_loss']:.4f}  ppl={stats['perplexity']:.2f}"
        )

    if args.output:
        Path(args.output).write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"Wrote: {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
