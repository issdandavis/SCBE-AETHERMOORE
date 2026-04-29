#!/usr/bin/env python3
"""Map agentic coding goals into hyperbolic code-slice command structures.

This is a practical bridge between:
- high-dimensional goal intent,
- low-dimensional code / binary / transport slots,
- tool availability,
- compute lanes,
- attempt history,
- and cross-language stitch points.

The output is a matrix and command-packet set for the harness. It is not a
learned embedding model; it is a deterministic planning substrate that can later
feed training/eval records.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "code_slice_geometry"

LANGUAGE_LENSES = {
    "python": {
        "tongue": "KO",
        "runtime": "pytest",
        "targets": ["python/", "scripts/", "tests/"],
    },
    "typescript": {
        "tongue": "AV",
        "runtime": "vitest",
        "targets": ["src/", "api/", "tests/"],
    },
    "rust": {"tongue": "RU", "runtime": "cargo", "targets": ["rust/"]},
    "c": {"tongue": "CA", "runtime": "native", "targets": ["src/", "include/"]},
    "julia": {
        "tongue": "UM",
        "runtime": "julia",
        "targets": ["notebooks/", "scripts/"],
    },
    "haskell": {
        "tongue": "DR",
        "runtime": "stack",
        "targets": ["training-data/", "docs/"],
    },
    "binary": {
        "tongue": "SS1",
        "runtime": "transport",
        "targets": ["training-data/", "artifacts/"],
    },
}

TOOL_AXES = {
    "search": ["rg", "web_search", "aetherbrowser"],
    "edit": ["apply_patch", "codemod", "format"],
    "test": ["pytest", "vitest", "typecheck"],
    "build": ["npm_build", "docker", "github_actions"],
    "train": ["huggingface", "colab", "kaggle"],
    "dispatch": ["advanced_ai_dispatch", "free_compute_array", "agent_task"],
}

COMPUTE_FACTORS = {
    "local": 0.55,
    "github_actions": 0.78,
    "colab": 0.72,
    "kaggle": 0.69,
    "huggingface_spaces": 0.62,
}

STATUS_FACTORS = {
    "planned": 0.30,
    "in_progress": 0.55,
    "blocked": 0.72,
    "done": 0.18,
}

DESIRED_FLOW = ["discover", "map", "slice", "stitch", "verify", "dispatch", "learn"]


@dataclass(frozen=True)
class CodeSlice:
    slice_id: str
    phase: str
    lens: str
    tongue: str
    status: str
    compute_lane: str
    target_paths: list[str]
    tool_axis: str
    tools: list[str]
    high_dim_goal: str
    low_dim_slot: str
    known_flow: str
    expected_flow: str
    desired_effect: str
    gap_score: float
    hyperbolic_radius: float
    expansion_factor: float
    command_structure: dict[str, Any]
    training_marker: dict[str, Any]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def stable_id(*parts: str) -> str:
    raw = "|".join(parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def tokenize(text: str) -> set[str]:
    return {part for part in re.split(r"[^a-z0-9_]+", text.lower()) if part}


def infer_goal_axes(goal: str) -> dict[str, float]:
    terms = tokenize(goal)
    return {
        "search": 1.0 if terms & {"research", "search", "source", "ground"} else 0.35,
        "edit": (
            1.0
            if terms & {"code", "build", "fix", "implement", "stitch", "slice"}
            else 0.45
        ),
        "test": 1.0 if terms & {"test", "verify", "benchmark", "confirm"} else 0.55,
        "build": 1.0 if terms & {"build", "harness", "system", "matrix"} else 0.45,
        "train": (
            1.0 if terms & {"training", "train", "dataset", "sft", "model"} else 0.35
        ),
        "dispatch": (
            1.0 if terms & {"agent", "agentic", "tool", "calling", "compute"} else 0.50
        ),
    }


def choose_compute(phase: str, lens: str) -> str:
    if phase in {"verify", "dispatch"}:
        return "github_actions"
    if phase == "learn":
        return "colab" if lens in {"python", "binary"} else "kaggle"
    if lens == "binary":
        return "local"
    if lens in {"python", "typescript"}:
        return "github_actions"
    return "local"


def choose_tool_axis(phase: str) -> str:
    return {
        "discover": "search",
        "map": "dispatch",
        "slice": "edit",
        "stitch": "edit",
        "verify": "test",
        "dispatch": "dispatch",
        "learn": "train",
    }.get(phase, "edit")


def hyperbolic_projection(
    *,
    goal_weight: float,
    compute_weight: float,
    status_weight: float,
    attempt_count: int,
    gap_seed: float,
) -> tuple[float, float, float]:
    """Return gap_score, radius, and expansion factor in a bounded Poincare-style ball."""
    attempt_pressure = min(1.0, math.log1p(max(0, attempt_count)) / 3.0)
    gap_score = min(
        1.0,
        0.34 * goal_weight
        + 0.18 * compute_weight
        + 0.18 * status_weight
        + 0.20 * attempt_pressure
        + 0.10 * gap_seed,
    )
    radius = math.tanh(gap_score * 1.85)
    radius = min(radius, 0.97)
    expansion = 1.0 / max(0.03, 1.0 - radius * radius)
    return round(gap_score, 6), round(radius, 6), round(expansion, 6)


def low_dim_slot_for(lens: str, phase: str) -> str:
    if lens == "binary":
        return f"transport_packet::{phase}::source_sha256/token_sha256"
    return f"{lens}::{phase}::function|module|test"


def build_command_structure(
    slice_id: str, phase: str, lens: str, paths: list[str], tools: list[str]
) -> dict[str, Any]:
    return {
        "schema_version": "scbe_code_slice_command_v1",
        "slice_id": slice_id,
        "phase": phase,
        "lens": lens,
        "allowed_paths": paths,
        "tool_chain": tools,
        "commands": {
            "claim": f"python scripts/system/advanced_ai_dispatch.py claim --worker-id code-slice-{slice_id} --capability code.patch",
            "search": f"rg -n \"{phase}|{lens}|TODO|FIXME\" {' '.join(paths)} -S",
            "verify": (
                "npm run typecheck"
                if lens == "typescript"
                else (
                    "pytest tests/ -q"
                    if lens == "python"
                    else "python scripts/benchmark/external_agentic_eval_driver.py --validate-only"
                )
            ),
        },
        "guardrails": [
            "only touch allowed_paths",
            "record before/after command evidence",
            "fallback to binary transport slot only when semantic/code lens is missing",
        ],
    }


def build_slices(
    goal: str, attempts: int, status: str, lenses: list[str] | None = None
) -> list[CodeSlice]:
    if status not in STATUS_FACTORS:
        raise ValueError(f"status must be one of {sorted(STATUS_FACTORS)}")
    axes = infer_goal_axes(goal)
    selected_lenses = lenses or ["python", "typescript", "binary"]
    unknown = sorted(set(selected_lenses) - set(LANGUAGE_LENSES))
    if unknown:
        raise ValueError(f"unknown lenses: {unknown}")

    slices: list[CodeSlice] = []
    for phase_index, phase in enumerate(DESIRED_FLOW, start=1):
        tool_axis = choose_tool_axis(phase)
        tools = TOOL_AXES[tool_axis]
        for lens in selected_lenses:
            lens_meta = LANGUAGE_LENSES[lens]
            compute_lane = choose_compute(phase, lens)
            slice_id = stable_id(goal, phase, lens, str(attempts), status)
            gap_seed = (phase_index / len(DESIRED_FLOW)) * (
                0.8 if lens != "binary" else 1.0
            )
            gap_score, radius, expansion = hyperbolic_projection(
                goal_weight=axes[tool_axis],
                compute_weight=COMPUTE_FACTORS[compute_lane],
                status_weight=STATUS_FACTORS[status],
                attempt_count=attempts,
                gap_seed=gap_seed,
            )
            paths = list(lens_meta["targets"])
            command_structure = build_command_structure(
                slice_id, phase, lens, paths, tools
            )
            training_marker = {
                "record_type": "code_slice_geometry",
                "input_goal": goal,
                "choice": f"{phase}:{lens}",
                "state": status,
                "hyperbolic_radius": radius,
                "expansion_factor": expansion,
                "expected_output": {
                    "command_structure": command_structure,
                    "gap_score": gap_score,
                    "desired_effect": f"{phase} {lens} slice without breaking shared IR",
                },
            }
            slices.append(
                CodeSlice(
                    slice_id=slice_id,
                    phase=phase,
                    lens=lens,
                    tongue=str(lens_meta["tongue"]),
                    status=status,
                    compute_lane=compute_lane,
                    target_paths=paths,
                    tool_axis=tool_axis,
                    tools=tools,
                    high_dim_goal=goal,
                    low_dim_slot=low_dim_slot_for(lens, phase),
                    known_flow=" -> ".join(DESIRED_FLOW[:phase_index]),
                    expected_flow=" -> ".join(DESIRED_FLOW),
                    desired_effect=f"{phase} {lens} slice and stitch into harness",
                    gap_score=gap_score,
                    hyperbolic_radius=radius,
                    expansion_factor=expansion,
                    command_structure=command_structure,
                    training_marker=training_marker,
                )
            )
    return slices


def build_report(
    goal: str, attempts: int, status: str, lenses: list[str] | None = None
) -> dict[str, Any]:
    slices = build_slices(goal, attempts, status, lenses)
    return {
        "schema_version": "scbe_code_slice_geometry_v1",
        "created_at": utc_now(),
        "goal": goal,
        "attempts": attempts,
        "status": status,
        "research_basis": [
            "hyperbolic embeddings for hierarchy/similarity",
            "static/dynamic/conditioned program slicing",
            "ReAct and Toolformer style reasoning-action/tool traces",
            "MLIR/code-property-graph style multi-level code representation",
        ],
        "interpretation": {
            "highest_dimension": "goal intent, desired effect, current/proposed trajectory",
            "lowest_dimension": "function/module/test/transport slots and binary hashes",
            "spaghettification": "expand the goal into many phase/lens slices, then compress each slice into a bounded command packet",
            "code_slice_rule": "when a language lens is missing, fill the structural gap with shared IR or binary transport metadata before generating code",
        },
        "coverage": {
            "slice_count": len(slices),
            "phases": DESIRED_FLOW,
            "lenses": sorted({row.lens for row in slices}),
            "max_expansion_factor": max(
                (row.expansion_factor for row in slices), default=0
            ),
            "high_gap_slices": [
                row.slice_id for row in slices if row.gap_score >= 0.75
            ],
        },
        "slices": [asdict(row) for row in slices],
    }


def write_outputs(report: dict[str, Any], out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "latest_code_slice_geometry.json"
    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    csv_path = out_dir / "latest_code_slice_matrix.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        fields = [
            "slice_id",
            "phase",
            "lens",
            "tongue",
            "status",
            "compute_lane",
            "tool_axis",
            "gap_score",
            "hyperbolic_radius",
            "expansion_factor",
            "low_dim_slot",
            "target_paths",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["slices"]:
            writer.writerow(
                {
                    field: (
                        ";".join(row[field]) if field == "target_paths" else row[field]
                    )
                    for field in fields
                }
            )

    packets_path = out_dir / "latest_command_packets.jsonl"
    with packets_path.open("w", encoding="utf-8") as handle:
        for row in report["slices"]:
            handle.write(json.dumps(row["command_structure"], sort_keys=True) + "\n")

    training_path = out_dir / "latest_training_records.jsonl"
    with training_path.open("w", encoding="utf-8") as handle:
        for row in report["slices"]:
            handle.write(json.dumps(row["training_marker"], sort_keys=True) + "\n")

    md_path = out_dir / "latest_code_slice_geometry.md"
    lines = [
        "# SCBE Code Slice Geometry",
        "",
        f"Goal: {report['goal']}",
        f"Attempts: {report['attempts']}",
        f"Status: `{report['status']}`",
        "",
        "## Model",
        "",
        report["interpretation"]["spaghettification"],
        "",
        "| Phase | Lens | Compute | Gap | Radius | Expansion | Slot |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in report["slices"]:
        lines.append(
            f"| `{row['phase']}` | `{row['lens']}` | `{row['compute_lane']}` | "
            f"{row['gap_score']:.3f} | {row['hyperbolic_radius']:.3f} | "
            f"{row['expansion_factor']:.3f} | `{row['low_dim_slot']}` |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "json": str(json_path),
        "matrix": str(csv_path),
        "command_packets": str(packets_path),
        "training_records": str(training_path),
        "markdown": str(md_path),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--goal", required=True)
    parser.add_argument("--attempts", type=int, default=0)
    parser.add_argument("--status", choices=sorted(STATUS_FACTORS), default="planned")
    parser.add_argument(
        "--lens",
        action="append",
        default=[],
        help="Language/transport lens. Repeatable.",
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--check", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = build_report(args.goal, args.attempts, args.status, args.lens or None)
    if args.check:
        print(
            json.dumps(
                {"ok": True, "slice_count": report["coverage"]["slice_count"]},
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    outputs = write_outputs(report, args.out_dir)
    print(
        json.dumps(
            {
                "ok": True,
                "outputs": outputs,
                "slice_count": report["coverage"]["slice_count"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
