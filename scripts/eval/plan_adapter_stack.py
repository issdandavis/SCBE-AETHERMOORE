"""Build a route-first adapter stack plan from frozen-eval reports.

Kaggle stacking works because each model earns a place in the stack on
out-of-fold validation. For SCBE LoRA adapters, the safer analogue is routing:
pick the adapter that improves each frozen holdout slice, keep BASE where no
adapter earns the lane, and block merge if aggregate regressions are visible.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "adapter_registry" / "stack_plans"


def resolve_report(path: Path) -> Path:
    if path.is_dir():
        candidate = path / "report.json"
        if candidate.exists():
            return candidate
    return path


def load_report(path: Path) -> dict[str, Any]:
    report_path = resolve_report(path)
    data = json.loads(report_path.read_text(encoding="utf-8"))
    data["_report_path"] = str(report_path)
    return data


def per_file_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["name"]: row for row in report.get("per_file", []) if "name" in row}


def finite_ppl(row: dict[str, Any] | None) -> float | None:
    if not row:
        return None
    value = row.get("perplexity")
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def summarize_adapter(
    base: dict[str, Any],
    adapter: dict[str, Any],
    *,
    regression_tolerance: float,
) -> dict[str, Any]:
    base_files = per_file_map(base)
    adapter_files = per_file_map(adapter)
    rows = []
    wins = 0
    regressions = 0
    comparable = 0
    for name, base_row in sorted(base_files.items()):
        base_ppl = finite_ppl(base_row)
        adapter_ppl = finite_ppl(adapter_files.get(name))
        if base_ppl is None or adapter_ppl is None:
            continue
        comparable += 1
        ratio = adapter_ppl / base_ppl if base_ppl else float("inf")
        improvement_pct = (1.0 - ratio) * 100.0
        won = adapter_ppl < base_ppl
        regressed = adapter_ppl > base_ppl * (1.0 + regression_tolerance)
        wins += int(won)
        regressions += int(regressed)
        rows.append(
            {
                "file": name,
                "base_perplexity": base_ppl,
                "adapter_perplexity": adapter_ppl,
                "ratio_vs_base": ratio,
                "improvement_pct": improvement_pct,
                "won": won,
                "regressed": regressed,
            }
        )

    base_total = float(base.get("summary", {}).get("perplexity", float("inf")))
    adapter_total = float(adapter.get("summary", {}).get("perplexity", float("inf")))
    aggregate_ratio = adapter_total / base_total if base_total else float("inf")
    return {
        "adapter": adapter.get("adapter", "UNKNOWN"),
        "report_path": adapter.get("_report_path"),
        "overall_perplexity": adapter_total,
        "base_overall_perplexity": base_total,
        "overall_ratio_vs_base": aggregate_ratio,
        "overall_improvement_pct": (1.0 - aggregate_ratio) * 100.0,
        "comparable_files": comparable,
        "wins": wins,
        "regressions": regressions,
        "per_file": rows,
        "promotion_hint": (
            "route_candidate"
            if adapter_total <= base_total and regressions == 0 and wins > 0
            else "evaluate_or_quarantine"
        ),
    }


def build_route_map(
    base: dict[str, Any],
    adapter_summaries: list[dict[str, Any]],
    *,
    regression_tolerance: float,
) -> list[dict[str, Any]]:
    base_files = per_file_map(base)
    route_rows = []
    for name, base_row in sorted(base_files.items()):
        base_ppl = finite_ppl(base_row)
        if base_ppl is None:
            continue
        best = {"adapter": "BASE", "perplexity": base_ppl, "improvement_pct": 0.0}
        for summary in adapter_summaries:
            for row in summary["per_file"]:
                if row["file"] != name:
                    continue
                if row["adapter_perplexity"] <= base_ppl * (1.0 + regression_tolerance):
                    if row["adapter_perplexity"] < best["perplexity"]:
                        best = {
                            "adapter": summary["adapter"],
                            "perplexity": row["adapter_perplexity"],
                            "improvement_pct": row["improvement_pct"],
                        }
        route_rows.append(
            {
                "file": name,
                "base_perplexity": base_ppl,
                "route_adapter": best["adapter"],
                "route_perplexity": best["perplexity"],
                "route_improvement_pct": best["improvement_pct"],
            }
        )
    return route_rows


def write_markdown(path: Path, plan: dict[str, Any]) -> None:
    lines = [
        "# Adapter Stack Plan",
        "",
        f"Generated: `{plan['generated_at_utc']}`",
        f"Base report: `{plan['base_report']}`",
        "",
        "## Adapter Summary",
        "",
        "| Adapter | Overall PPL | Ratio vs Base | Wins | Regressions | Hint |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in plan["adapters"]:
        lines.append(
            f"| `{row['adapter']}` | {row['overall_perplexity']:.4g} | "
            f"{row['overall_ratio_vs_base']:.3f} | {row['wins']} | "
            f"{row['regressions']} | `{row['promotion_hint']}` |"
        )
    lines.extend(
        [
            "",
            "## Route Map",
            "",
            "| Holdout File | Route Adapter | Base PPL | Route PPL | Improvement |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    for row in plan["route_map"]:
        lines.append(
            f"| `{row['file']}` | `{row['route_adapter']}` | "
            f"{row['base_perplexity']:.4g} | {row['route_perplexity']:.4g} | "
            f"{row['route_improvement_pct']:.2f}% |"
        )
    lines.extend(
        [
            "",
            "## Rule",
            "",
            "Route before merge. An adapter earns a lane only on frozen validation; "
            "training loss and token accuracy are not promotion evidence.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-report", type=Path, required=True)
    parser.add_argument("--adapter-report", type=Path, action="append", required=True)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--label", default="latest")
    parser.add_argument("--regression-tolerance", type=float, default=0.05)
    args = parser.parse_args()

    base = load_report(args.base_report)
    adapters = [load_report(path) for path in args.adapter_report]
    summaries = [
        summarize_adapter(base, adapter, regression_tolerance=args.regression_tolerance)
        for adapter in adapters
    ]
    route_map = build_route_map(base, summaries, regression_tolerance=args.regression_tolerance)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    plan = {
        "schema_version": "scbe_adapter_stack_plan_v1",
        "generated_at_utc": generated,
        "base_report": str(resolve_report(args.base_report)),
        "regression_tolerance": args.regression_tolerance,
        "adapters": summaries,
        "route_map": route_map,
    }

    out_dir = args.out_dir / args.label
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "stack_plan.json"
    md_path = out_dir / "stack_plan.md"
    json_path.write_text(json.dumps(plan, indent=2, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(md_path, plan)
    print(json.dumps({"json": str(json_path), "markdown": str(md_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
