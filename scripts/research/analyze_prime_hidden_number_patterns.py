"""Contrastive analysis for discovered versus undiscovered hidden prime anchors.

The benchmark verifier defines hidden numbers by future gap-ratio events, but
the searcher only sees local pre-event channels. This script treats each hidden
anchor as one unit, then asks which local features separate anchors found by the
frozen gate from anchors the current methods missed.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.research.run_field_gate_oos_validate import spec_from_report  # noqa: E402
from scripts.research.run_field_gate_threshold_sensitivity import fresh_rows  # noqa: E402
from scripts.research.run_prime_search_engine_bench import (  # noqa: E402
    FEATURE_NAMES,
    feature_vector,
    row_cache_path,
    score_frozen,
)


DEFAULT_REPORT = Path("artifacts/prime_search_engine_bench_100_200_hidden_numbers/latest_report.json")
DEFAULT_ROW_CACHE_DIR = Path("artifacts/prime_fog_row_cache")
DEFAULT_OUT_DIR = Path("artifacts/prime_hidden_number_patterns")


def safe_mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def safe_stdev(values: list[float]) -> float:
    return statistics.pstdev(values) if len(values) > 1 else 0.0


def load_rows(cache_dir: Path, limit: int, window: int, history: int, anchor_threshold: float) -> list[dict[str, Any]]:
    path = row_cache_path(cache_dir, limit, window, history, anchor_threshold)
    if not path.exists():
        raise FileNotFoundError(f"missing row cache: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def anchor_id(row: dict[str, Any]) -> object | None:
    return row.get("first_anchor_idx", row.get("first_anchor_prime"))


def hidden_id(number: dict[str, Any]) -> object | None:
    return number.get("anchor_idx", number.get("anchor_prime"))


def method_found_sets(report: dict[str, Any]) -> dict[str, set[object]]:
    out: dict[str, set[object]] = {}
    for method, hidden_numbers in report.get("hidden_number_maps", {}).items():
        out[method] = {hidden_id(number) for number in hidden_numbers if hidden_id(number) is not None}
    return out


def top_row_duplicate_ghosts(method: dict[str, Any]) -> list[dict[str, Any]]:
    seen: set[object] = set()
    ghosts: list[dict[str, Any]] = []
    for row in method["range_b"].get("top_rows", []):
        aid = anchor_id(row)
        if not row.get("future_anchor") or aid is None:
            continue
        if aid in seen:
            ghosts.append(
                {
                    "rank": row.get("rank"),
                    "anchor_idx": row.get("first_anchor_idx"),
                    "anchor_prime": row.get("first_anchor_prime"),
                    "scan_idx": row.get("scan_idx"),
                    "lead_steps": row.get("lead_steps"),
                    "score": row.get("score"),
                }
            )
        seen.add(aid)
    return ghosts


def build_anchor_records(
    range_b_rows: list[dict[str, Any]],
    catalog: list[dict[str, Any]],
    frozen_scores: list[float],
    found_sets: dict[str, set[object]],
) -> list[dict[str, Any]]:
    rows_by_anchor: dict[object, list[tuple[dict[str, Any], float]]] = defaultdict(list)
    for row, score in zip(range_b_rows, frozen_scores):
        if not row.get("future_anchor"):
            continue
        aid = anchor_id(row)
        if aid is not None:
            rows_by_anchor[aid].append((row, score))

    records: list[dict[str, Any]] = []
    for item in catalog:
        aid = item.get("anchor_idx", item.get("anchor_prime"))
        candidates = rows_by_anchor.get(aid, [])
        if not candidates:
            continue
        best_row, best_score = max(candidates, key=lambda pair: (pair[1], -pair[0].get("lead_steps", 10**9)))
        features = dict(zip(FEATURE_NAMES, feature_vector(best_row)))
        found_by = [method for method, found in found_sets.items() if aid in found]
        records.append(
            {
                "anchor_idx": item.get("anchor_idx"),
                "anchor_prime": item.get("anchor_prime"),
                "anchor_ratio": item.get("anchor_ratio"),
                "abs_anchor_ratio": abs(float(item.get("anchor_ratio") or 0.0)),
                "candidate_rows": item.get("candidate_rows"),
                "min_lead_steps": item.get("min_lead_steps"),
                "max_lead_steps": item.get("max_lead_steps"),
                "representative_scan_idx": best_row.get("scan_idx"),
                "representative_scan_prime": best_row.get("scan_prime"),
                "representative_lead_steps": best_row.get("lead_steps"),
                "frozen_score": best_score,
                "found_by": found_by,
                "frozen_found": "frozen_gate" in found_by,
                "selected_found": "best_selected_on_range_a" in found_by,
                "oracle_found": "best_oracle_on_range_b" in found_by,
                "any_found": bool(found_by),
                "features": features,
            }
        )
    return records


def standardized_deltas(records: list[dict[str, Any]], positive_key: str) -> list[dict[str, Any]]:
    positives = [record for record in records if record[positive_key]]
    negatives = [record for record in records if not record[positive_key]]
    out = []
    for feature in FEATURE_NAMES:
        pos_values = [float(record["features"][feature]) for record in positives]
        neg_values = [float(record["features"][feature]) for record in negatives]
        pos_mean = safe_mean(pos_values)
        neg_mean = safe_mean(neg_values)
        pooled = math.sqrt((safe_stdev(pos_values) ** 2 + safe_stdev(neg_values) ** 2) / 2.0) or 1.0
        out.append(
            {
                "feature": feature,
                "positive_mean": round(pos_mean, 6),
                "negative_mean": round(neg_mean, 6),
                "delta": round(pos_mean - neg_mean, 6),
                "standardized_delta": round((pos_mean - neg_mean) / pooled, 6),
            }
        )
    return sorted(out, key=lambda item: abs(item["standardized_delta"]), reverse=True)


def threshold_candidates(values: list[float], max_candidates: int = 24) -> list[float]:
    unique = sorted(set(values))
    if len(unique) <= max_candidates:
        return unique
    thresholds = []
    for index in range(1, max_candidates + 1):
        q = index / (max_candidates + 1)
        thresholds.append(unique[min(len(unique) - 1, max(0, round((len(unique) - 1) * q)))])
    return sorted(set(thresholds))


def threshold_rules(records: list[dict[str, Any]], positive_key: str) -> list[dict[str, Any]]:
    total_pos = sum(1 for record in records if record[positive_key])
    total_neg = len(records) - total_pos
    rules = []
    for feature in FEATURE_NAMES:
        values = [float(record["features"][feature]) for record in records]
        for threshold in threshold_candidates(values):
            for op in (">=", "<="):
                selected = [
                    record
                    for record in records
                    if (float(record["features"][feature]) >= threshold if op == ">=" else float(record["features"][feature]) <= threshold)
                ]
                if not selected:
                    continue
                tp = sum(1 for record in selected if record[positive_key])
                fp = len(selected) - tp
                fn = total_pos - tp
                tn = total_neg - fp
                precision = tp / (tp + fp) if tp + fp else 0.0
                recall = tp / total_pos if total_pos else 0.0
                specificity = tn / total_neg if total_neg else 0.0
                balanced_accuracy = 0.5 * (recall + specificity)
                f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
                rules.append(
                    {
                        "feature": feature,
                        "op": op,
                        "threshold": round(threshold, 6),
                        "selected": len(selected),
                        "tp": tp,
                        "fp": fp,
                        "precision": round(precision, 6),
                        "recall": round(recall, 6),
                        "specificity": round(specificity, 6),
                        "balanced_accuracy": round(balanced_accuracy, 6),
                        "f1": round(f1, 6),
                    }
                )
    return sorted(rules, key=lambda item: (-item["balanced_accuracy"], -item["f1"], item["feature"]))[:40]


def method_overlap(found_sets: dict[str, set[object]]) -> dict[str, Any]:
    all_ids = sorted(set().union(*found_sets.values())) if found_sets else []
    counts = Counter()
    for aid in all_ids:
        key = "+".join(method for method, found in found_sets.items() if aid in found)
        counts[key or "unfound"] += 1
    return {
        "found_union": len(all_ids),
        "set_sizes": {method: len(found) for method, found in found_sets.items()},
        "intersections": dict(sorted(counts.items())),
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Prime Hidden Number Pattern Analysis",
        "",
        f"Source benchmark: `{report['source_report']}`",
        f"Hidden anchors analyzed: {report['summary']['record_count']}",
        f"Frozen-found anchors: {report['summary']['frozen_found']}",
        f"Unfound by all tracked methods: {report['summary']['unfound_by_all']}",
        "",
        "## Method Overlap",
        "",
        "| Method | Unique hidden numbers |",
        "| --- | ---: |",
    ]
    for method, count in report["method_overlap"]["set_sizes"].items():
        lines.append(f"| {method} | {count} |")
    lines.extend(["", "## Strongest Frozen-Found Feature Deltas", "", "| Feature | Found mean | Unfound mean | Std delta |", "| --- | ---: | ---: | ---: |"])
    for item in report["frozen_vs_unfound_deltas"][:20]:
        lines.append(
            "| {feature} | {positive_mean} | {negative_mean} | {standardized_delta} |".format(**item)
        )
    lines.extend(["", "## Best One-Rule Shadows", "", "| Rule | Selected | TP | FP | Precision | Recall | Balanced acc |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"])
    for rule in report["frozen_vs_unfound_threshold_rules"][:20]:
        lines.append(
            "| {feature} {op} {threshold} | {selected} | {tp} | {fp} | {precision} | {recall} | {balanced_accuracy} |".format(
                **rule
            )
        )
    lines.extend(["", "## Frozen-Found Hidden Numbers", "", "| Anchor prime | Ratio | Lead | Frozen score | Found by |", "| ---: | ---: | ---: | ---: | --- |"])
    for record in report["frozen_found_records"]:
        lines.append(
            "| {anchor_prime} | {anchor_ratio} | {representative_lead_steps} | {frozen_score} | {found_by} |".format(
                anchor_prime=record["anchor_prime"],
                anchor_ratio=record["anchor_ratio"],
                representative_lead_steps=record["representative_lead_steps"],
                frozen_score=round(record["frozen_score"], 6),
                found_by=", ".join(record["found_by"]),
            )
        )
    lines.extend(["", "## Duplicate Ghosts", ""])
    for method, ghosts in report["duplicate_ghosts"].items():
        lines.append(f"- `{method}` duplicate anchor rows: {len(ghosts)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    source_report = Path(args.report)
    benchmark = json.loads(source_report.read_text(encoding="utf-8"))
    config = benchmark["config"]
    cache_dir = Path(args.row_cache_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    boundary_rows = load_rows(
        cache_dir,
        config["limit_a_test"],
        config["window"],
        config["history"],
        config["anchor_threshold"],
    )
    test_rows = load_rows(
        cache_dir,
        config["limit_b_test"],
        config["window"],
        config["history"],
        config["anchor_threshold"],
    )
    range_b = fresh_rows(boundary_rows, test_rows)
    frozen_spec = spec_from_report(Path(config.get("source_report", args.gate_report)), args.selector)
    frozen_scores = score_frozen(range_b, frozen_spec)
    catalog = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
    found_sets = method_found_sets(benchmark)
    records = build_anchor_records(range_b, catalog, frozen_scores, found_sets)

    frozen_found = [record for record in records if record["frozen_found"]]
    unfound_by_all = [record for record in records if not record["any_found"]]
    report = {
        "schema_version": "prime_hidden_number_pattern_analysis_v1",
        "source_report": str(source_report),
        "summary": {
            "record_count": len(records),
            "frozen_found": len(frozen_found),
            "unfound_by_all": len(unfound_by_all),
            "range_b_rows": len(range_b),
        },
        "method_overlap": method_overlap(found_sets),
        "frozen_vs_unfound_deltas": standardized_deltas(
            [*frozen_found, *unfound_by_all],
            "frozen_found",
        ),
        "frozen_vs_unfound_threshold_rules": threshold_rules(
            [*frozen_found, *unfound_by_all],
            "frozen_found",
        ),
        "any_found_vs_unfound_deltas": standardized_deltas(records, "any_found"),
        "duplicate_ghosts": {
            "frozen_gate": top_row_duplicate_ghosts(benchmark["frozen_gate"]),
            "best_selected_on_range_a": top_row_duplicate_ghosts(benchmark["best_selected_on_range_a"]),
            "best_oracle_on_range_b": top_row_duplicate_ghosts(benchmark["best_oracle_on_range_b"]),
        },
        "frozen_found_records": [
            {
                key: record[key]
                for key in (
                    "anchor_idx",
                    "anchor_prime",
                    "anchor_ratio",
                    "representative_scan_idx",
                    "representative_scan_prime",
                    "representative_lead_steps",
                    "frozen_score",
                    "found_by",
                    "features",
                )
            }
            for record in frozen_found
        ],
        "records": records if args.include_records else [],
    }
    (out_dir / "latest_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, out_dir / "LATEST.md")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--catalog", default="artifacts/prime_search_engine_bench_100_200_hidden_numbers/known_unknown_catalog_latest.json")
    parser.add_argument("--gate-report", default="artifacts/prime_fog_branch_gate/latest_report.json")
    parser.add_argument("--selector", choices=["holdout", "train", "full"], default="holdout")
    parser.add_argument("--row-cache-dir", default=str(DEFAULT_ROW_CACHE_DIR))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--include-records", action="store_true")
    args = parser.parse_args()
    report = run(args)
    print(
        "hidden_pattern_analysis records={records} frozen_found={found} unfound={unfound}".format(
            records=report["summary"]["record_count"],
            found=report["summary"]["frozen_found"],
            unfound=report["summary"]["unfound_by_all"],
        )
    )
    print(Path(args.out_dir) / "LATEST.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
