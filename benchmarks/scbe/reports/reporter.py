"""Report generator -- JSON report + formatted comparison table.

Produces:
  1. A JSON report with full metrics for all systems.
  2. A printed comparison table (ASCII-safe, no unicode arrows).
  3. Per-class breakdown tables.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from benchmarks.scbe.config import (
    REPORTS_DIR,
    REPORT_VERSION,
    TABLE_COL_WIDTH,
    TARGET_ASR,
    TARGET_DETECTION_RATE,
    TARGET_F1,
    TARGET_FPR,
)
from benchmarks.scbe.runners.core import SystemBenchmarkResult
from benchmarks.scbe.runners.adaptive_runner import AdaptiveSystemResult

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
#  Table formatting
# --------------------------------------------------------------------------- #

def _pad(text: str, width: int) -> str:
    """Pad text to fixed width, truncating if needed."""
    if len(text) > width:
        return text[: width - 2] + ".."
    return text.ljust(width)


def _sep(cols: int, width: int) -> str:
    """Horizontal separator line."""
    return "+" + (("-" * width + "+") * cols)


def format_comparison_table(
    systems: Dict[str, Dict[str, Any]],
) -> str:
    """Format a comparison table of standard metrics across systems.

    Args:
        systems: Dict mapping system_name -> standard metrics dict.

    Returns:
        Multi-line ASCII table string.
    """
    w = TABLE_COL_WIDTH
    headers = ["System", "ASR", "FPR", "Precision", "Recall", "F1", "Accuracy"]
    cols = len(headers)

    lines = []
    lines.append(_sep(cols, w))
    lines.append(
        "|" + "|".join(_pad(h, w) for h in headers) + "|"
    )
    lines.append(_sep(cols, w))

    for sys_name, metrics in systems.items():
        row = [
            sys_name,
            f"{metrics.get('asr', 0):.1%}",
            f"{metrics.get('fpr', 0):.1%}",
            f"{metrics.get('precision', 0):.3f}",
            f"{metrics.get('recall', 0):.3f}",
            f"{metrics.get('f1', 0):.3f}",
            f"{metrics.get('accuracy', 0):.3f}",
        ]
        lines.append("|" + "|".join(_pad(v, w) for v in row) + "|")

    lines.append(_sep(cols, w))
    return "\n".join(lines)


def format_per_class_table(
    system_name: str,
    per_class: Dict[str, Dict[str, Any]],
) -> str:
    """Format a per-class detection breakdown table."""
    w = TABLE_COL_WIDTH
    headers = ["Class", "Total", "Detected", "Rate"]
    cols = len(headers)

    lines = []
    lines.append(f"  {system_name} -- Per-Class Breakdown")
    lines.append(_sep(cols, w))
    lines.append("|" + "|".join(_pad(h, w) for h in headers) + "|")
    lines.append(_sep(cols, w))

    for cls_name in sorted(per_class.keys()):
        data = per_class[cls_name]
        row = [
            cls_name,
            str(data.get("total", 0)),
            str(data.get("detected", 0)),
            f"{data.get('detection_rate', 0):.0%}",
        ]
        lines.append("|" + "|".join(_pad(v, w) for v in row) + "|")

    lines.append(_sep(cols, w))
    return "\n".join(lines)


def format_adaptive_table(
    adaptive_results: Dict[str, Dict[str, Any]],
) -> str:
    """Format adaptive attack results comparison."""
    w = TABLE_COL_WIDTH
    headers = ["System", "Seeds", "Attempts", "Evasions", "Evasion Rate"]
    cols = len(headers)

    lines = []
    lines.append(_sep(cols, w))
    lines.append("|" + "|".join(_pad(h, w) for h in headers) + "|")
    lines.append(_sep(cols, w))

    for sys_name, data in adaptive_results.items():
        row = [
            sys_name,
            str(data.get("total_seeds", 0)),
            str(data.get("total_attempts", 0)),
            str(data.get("total_evasions", 0)),
            f"{data.get('overall_evasion_rate', 0):.1%}",
        ]
        lines.append("|" + "|".join(_pad(v, w) for v in row) + "|")

    lines.append(_sep(cols, w))
    return "\n".join(lines)


def format_target_comparison(
    metrics: Dict[str, Any],
    system_name: str,
) -> str:
    """Compare a system's metrics against target thresholds."""
    lines = []
    lines.append(f"  {system_name} vs. Targets:")

    checks = [
        ("ASR", metrics.get("asr", 1.0), TARGET_ASR, "<="),
        ("FPR", metrics.get("fpr", 1.0), TARGET_FPR, "<="),
        ("F1", metrics.get("f1", 0.0), TARGET_F1, ">="),
        ("Detection Rate", metrics.get("detection_rate", 0.0), TARGET_DETECTION_RATE, ">="),
    ]

    for name, actual, target, op in checks:
        if op == "<=":
            passed = actual <= target
        else:
            passed = actual >= target
        status = "PASS" if passed else "FAIL"
        lines.append(
            f"    {name:<18} actual={actual:.3f}  target{op}{target:.3f}  [{status}]"
        )

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
#  JSON report generation
# --------------------------------------------------------------------------- #

def generate_report(
    benchmark_results: Dict[str, SystemBenchmarkResult],
    standard_metrics: Dict[str, Dict[str, Any]],
    scbe_metrics: Optional[Dict[str, Any]] = None,
    adaptive_results: Optional[Dict[str, Any]] = None,
    dataset_info: Optional[Dict[str, Any]] = None,
    output_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Generate a full JSON benchmark report.

    Args:
        benchmark_results: System name -> SystemBenchmarkResult.
        standard_metrics: System name -> standard metrics dict.
        scbe_metrics: SCBE-specific metrics (optional).
        adaptive_results: Adaptive attack results per system (optional).
        dataset_info: Info about the dataset used.
        output_path: Where to write the JSON report. Defaults to reports dir.

    Returns:
        The full report as a dict.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    report: Dict[str, Any] = {
        "version": REPORT_VERSION,
        "timestamp": timestamp,
        "dataset": dataset_info or {},
        "systems": {},
        "comparison": {},
    }

    # Per-system results
    for sys_name, bench_result in benchmark_results.items():
        sys_report: Dict[str, Any] = bench_result.to_dict()
        sys_report["standard_metrics"] = standard_metrics.get(sys_name, {})
        report["systems"][sys_name] = sys_report

    # SCBE-specific metrics
    if scbe_metrics:
        report["scbe_metrics"] = scbe_metrics

    # Adaptive results
    if adaptive_results:
        report["adaptive"] = adaptive_results

    # Comparison summary (side by side)
    report["comparison"] = {
        sys_name: {
            "asr": m.get("asr", 0),
            "fpr": m.get("fpr", 0),
            "f1": m.get("f1", 0),
            "detection_rate": m.get("detection_rate", 0),
        }
        for sys_name, m in standard_metrics.items()
    }

    # Write to file
    if output_path is None:
        output_path = REPORTS_DIR / f"benchmark_{timestamp.replace(':', '-')}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    logger.info("Report written to: %s", output_path)
    return report


# --------------------------------------------------------------------------- #
#  Console printer
# --------------------------------------------------------------------------- #

def print_full_report(
    standard_metrics: Dict[str, Dict[str, Any]],
    benchmark_results: Dict[str, SystemBenchmarkResult],
    scbe_metrics: Optional[Dict[str, Any]] = None,
    adaptive_results: Optional[Dict[str, Any]] = None,
) -> None:
    """Print a formatted benchmark report to stdout.

    Uses only ASCII-safe characters (no unicode arrows or fancy symbols).
    """
    print("")
    print("=" * 78)
    print("  SCBE BENCHMARK REPORT")
    print("=" * 78)
    print("")

    # Comparison table
    print("  STANDARD METRICS COMPARISON")
    print("")
    print(format_comparison_table(standard_metrics))
    print("")

    # Per-system details
    for sys_name, bench_result in benchmark_results.items():
        per_class = bench_result.per_class_results
        if per_class:
            print(format_per_class_table(sys_name, per_class))
            print("")

    # Target comparison for SCBE
    if "scbe_system" in standard_metrics:
        print(format_target_comparison(
            standard_metrics["scbe_system"], "scbe_system"
        ))
        print("")

    # SCBE-specific metrics
    if scbe_metrics:
        print("  SCBE-SPECIFIC METRICS")
        print("  " + "-" * 40)
        for key, value in scbe_metrics.items():
            if key in ("signal_frequency", "totals"):
                continue
            print(f"    {key:<35} {value}")
        if "signal_frequency" in scbe_metrics:
            print("")
            print("  Signal Frequency:")
            for sig, count in scbe_metrics["signal_frequency"].items():
                print(f"    {sig:<30} {count}")
        print("")

    # Adaptive results
    if adaptive_results:
        print("  ADAPTIVE ATTACK RESULTS")
        print("")
        print(format_adaptive_table(adaptive_results))
        print("")

        # Strategy effectiveness
        for sys_name, data in adaptive_results.items():
            scores = data.get("strategy_scores", {})
            if scores:
                print(f"  {sys_name} -- Strategy Effectiveness:")
                for strat, score in sorted(
                    scores.items(), key=lambda x: -x[1]
                ):
                    print(f"    {strat:<20} {score:.3f}")
                print("")

    print("=" * 78)
    print("")
