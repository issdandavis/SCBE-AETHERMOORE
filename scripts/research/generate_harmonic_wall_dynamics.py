#!/usr/bin/env python3
"""Generate harmonic wall dynamics plots over N discrete steps.

This separates four related views of the harmonic wall family:
  1. value:      H(n) = R^(n^2 * x)
  2. exponent:   E(n) = n^2 * x
  3. step ratio: H(n+1) / H(n) = R^(x * (2n + 1))
  4. derivative: dH/dn = 2nx ln(R) H(n)

The goal is to make it obvious whether growth is being driven mostly by
the base ratio R, the quadratic exponent n^2 * x, or the derivative blow-up.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import matplotlib.pyplot as plt
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "research"


@dataclass(frozen=True)
class SeriesSpec:
    intent: float
    label: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Graph harmonic wall dynamics over N steps.")
    parser.add_argument("--steps", type=int, default=20, help="Maximum step index N (default: 20).")
    parser.add_argument("--ratio", type=float, default=1.5, help="Base ratio R (default: 1.5).")
    parser.add_argument(
        "--intent-values",
        default="0.5,1.0,3.0",
        help="Comma-separated x values to compare (default: 0.5,1.0,3.0).",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR}).",
    )
    parser.add_argument(
        "--stem",
        default="harmonic_wall_dynamics",
        help="Base filename for generated artifacts.",
    )
    return parser.parse_args()


def parse_intent_values(raw: str) -> List[SeriesSpec]:
    values: List[SeriesSpec] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        x = float(part)
        if x < 0:
            raise ValueError("Intent values must be >= 0.")
        values.append(SeriesSpec(intent=x, label=f"x={x:g}"))
    if not values:
        raise ValueError("At least one intent value is required.")
    return values


def harmonic_value(n: np.ndarray, ratio: float, intent: float) -> np.ndarray:
    return np.exp((n * n * intent) * math.log(ratio))


def exponent_term(n: np.ndarray, intent: float) -> np.ndarray:
    return n * n * intent


def adjacent_ratio(n: np.ndarray, ratio: float, intent: float) -> np.ndarray:
    return np.exp((intent * (2 * n + 1)) * math.log(ratio))


def derivative_term(n: np.ndarray, ratio: float, intent: float) -> np.ndarray:
    values = harmonic_value(n, ratio, intent)
    return 2.0 * n * intent * math.log(ratio) * values


def write_csv(path: Path, steps: int, ratio: float, specs: List[SeriesSpec]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["step", "intent", "exponent", "value", "step_ratio", "derivative"])
        n = np.arange(0, steps + 1, dtype=float)
        for spec in specs:
            exp_term = exponent_term(n, spec.intent)
            values = harmonic_value(n, ratio, spec.intent)
            ratios = adjacent_ratio(n, ratio, spec.intent)
            deriv = derivative_term(n, ratio, spec.intent)
            for idx in range(len(n)):
                writer.writerow(
                    [
                        int(n[idx]),
                        f"{spec.intent:.10g}",
                        f"{exp_term[idx]:.16g}",
                        f"{values[idx]:.16g}",
                        f"{ratios[idx]:.16g}",
                        f"{deriv[idx]:.16g}",
                    ]
                )


def build_plot(steps: int, ratio: float, specs: List[SeriesSpec], output_png: Path) -> None:
    n = np.arange(0, steps + 1, dtype=float)
    fig, axes = plt.subplots(2, 2, figsize=(14, 10), constrained_layout=True)
    (ax_value, ax_exp), (ax_ratio, ax_deriv) = axes

    for spec in specs:
        exp_term = exponent_term(n, spec.intent)
        values = harmonic_value(n, ratio, spec.intent)
        ratios = adjacent_ratio(n, ratio, spec.intent)
        deriv = derivative_term(n, ratio, spec.intent)

        ax_value.plot(n, values, marker="o", label=spec.label)
        ax_exp.plot(n, exp_term, marker="o", label=spec.label)
        ax_ratio.plot(n, ratios, marker="o", label=spec.label)
        ax_deriv.plot(n, deriv, marker="o", label=spec.label)

    ax_value.set_title(f"Wall Value H(n) = R^(n^2 x), R={ratio:g}")
    ax_value.set_xlabel("step n")
    ax_value.set_ylabel("H(n)")
    ax_value.set_yscale("log")
    ax_value.grid(True, alpha=0.3)

    ax_exp.set_title("Exponent Term E(n) = n^2 x")
    ax_exp.set_xlabel("step n")
    ax_exp.set_ylabel("n^2 x")
    ax_exp.grid(True, alpha=0.3)

    ax_ratio.set_title("Adjacent Step Ratio H(n+1) / H(n)")
    ax_ratio.set_xlabel("step n")
    ax_ratio.set_ylabel("ratio")
    ax_ratio.set_yscale("log")
    ax_ratio.grid(True, alpha=0.3)

    ax_deriv.set_title("Continuous Derivative dH/dn")
    ax_deriv.set_xlabel("step n")
    ax_deriv.set_ylabel("dH/dn")
    ax_deriv.set_yscale("log")
    ax_deriv.grid(True, alpha=0.3)

    handles, labels = ax_value.get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=len(specs), frameon=False)
    fig.suptitle("Harmonic Wall Dynamics by Value, Exponent, Ratio, and Derivative", fontsize=16)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=180)
    plt.close(fig)


def write_json(path: Path, steps: int, ratio: float, specs: List[SeriesSpec], png_path: Path, csv_path: Path) -> None:
    n = np.arange(0, steps + 1, dtype=float)
    summary = {}
    for spec in specs:
        values = harmonic_value(n, ratio, spec.intent)
        ratios = adjacent_ratio(n, ratio, spec.intent)
        deriv = derivative_term(n, ratio, spec.intent)
        summary[spec.label] = {
            "max_value": float(values.max()),
            "max_step_ratio": float(ratios.max()),
            "max_derivative": float(deriv.max()),
            "final_exponent": float(exponent_term(n, spec.intent)[-1]),
        }

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "formula": "H(n) = R^(n^2 * x)",
        "steps": steps,
        "ratio": ratio,
        "intent_values": [spec.intent for spec in specs],
        "artifacts": {
            "png": str(png_path.relative_to(REPO_ROOT)).replace("\\", "/"),
            "csv": str(csv_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        },
        "summary": summary,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    if args.steps < 1:
        raise ValueError("--steps must be >= 1")
    if args.ratio <= 1.0:
        raise ValueError("--ratio must be > 1.0")

    specs = parse_intent_values(args.intent_values)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    png_path = output_dir / f"{args.stem}.png"
    csv_path = output_dir / f"{args.stem}.csv"
    json_path = output_dir / f"{args.stem}.json"

    write_csv(csv_path, args.steps, args.ratio, specs)
    build_plot(args.steps, args.ratio, specs, png_path)
    write_json(json_path, args.steps, args.ratio, specs, png_path, csv_path)

    print(
        json.dumps(
            {
                "status": "ok",
                "png": str(png_path),
                "csv": str(csv_path),
                "json": str(json_path),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
