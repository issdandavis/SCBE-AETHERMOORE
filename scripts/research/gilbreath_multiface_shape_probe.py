"""Gilbreath multi-face shape probe.

The user's "use the negatives and turn it into a multi-faced shape" maps cleanly
to repeated difference operators on the known-prime line.

Faces:

1. abs_gilbreath  : abs differences, the classical Gilbreath triangle
2. signed_delta   : signed differences, preserving negative motion
3. negative_abs   : mirror of abs_gilbreath, the negative observation face
4. parity_abs     : abs_gilbreath mod 2
5. energy_abs     : log-compressed abs_gilbreath

The useful invariant is the leading seam of the abs face. Gilbreath's conjecture
says the first value of every difference row is 1. This script checks the known
prefix against wheel-admissible random lines of the same length/range.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.research.prime_boundary_spectrum_null import first_n_primes

DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "gilbreath_multiface_shape"
ADMISSIBLE_MOD_30 = (1, 7, 11, 13, 17, 19, 23, 29)
FACE_NAMES = (
    "abs_gilbreath",
    "signed_delta",
    "negative_abs",
    "parity_abs",
    "energy_abs",
)


@dataclass(frozen=True)
class ShapeVertex:
    face: str
    row: int
    col: int
    value: float
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class FaceSummary:
    face: str
    rows: int
    max_abs_value: float
    mean_abs_value: float
    leading_values: tuple[float, ...]


def difference_triangle(
    sequence: Sequence[int | float], depth: int, mode: str = "abs"
) -> list[list[float]]:
    if depth < 1:
        raise ValueError("depth must be at least 1")
    rows: list[list[float]] = [[float(value) for value in sequence]]
    while len(rows) < depth and len(rows[-1]) > 1:
        previous = rows[-1]
        signed = [previous[idx + 1] - previous[idx] for idx in range(len(previous) - 1)]
        if mode == "signed":
            current = signed
        elif mode == "abs":
            current = [abs(value) for value in signed]
        else:
            raise ValueError(f"unknown triangle mode: {mode}")
        rows.append(current)
    return rows


def transform_face(
    abs_rows: Sequence[Sequence[float]],
    signed_rows: Sequence[Sequence[float]],
    face: str,
) -> list[list[float]]:
    if face == "abs_gilbreath":
        return [list(row) for row in abs_rows]
    if face == "signed_delta":
        return [list(row) for row in signed_rows]
    if face == "negative_abs":
        return [[-value for value in row] for row in abs_rows]
    if face == "parity_abs":
        return [[float(int(value) % 2) for value in row] for row in abs_rows]
    if face == "energy_abs":
        return [[math.log1p(abs(value)) for value in row] for row in abs_rows]
    raise ValueError(f"unknown face: {face}")


def leading_values(
    rows: Sequence[Sequence[float]], skip_root: bool = True
) -> tuple[float, ...]:
    start = 1 if skip_root else 0
    return tuple(row[0] for row in rows[start:] if row)


def leading_one_prefix(abs_rows: Sequence[Sequence[float]]) -> int:
    count = 0
    for value in leading_values(abs_rows, skip_root=True):
        if value != 1.0:
            break
        count += 1
    return count


def wheel_admissible_candidates(limit: int) -> list[int]:
    return [value for value in range(7, limit + 1) if value % 30 in ADMISSIBLE_MOD_30]


def random_wheel_line(length: int, max_value: int, rng: random.Random) -> list[int]:
    if length < 4:
        raise ValueError("length must be at least 4")
    candidates = wheel_admissible_candidates(max_value)
    if len(candidates) < length - 3:
        raise ValueError("not enough wheel candidates for requested length")
    sampled = sorted(rng.sample(candidates, length - 3))
    return [2, 3, 5, *sampled]


def random_odd_line(length: int, max_value: int, rng: random.Random) -> list[int]:
    if length < 3:
        raise ValueError("length must be at least 3")
    candidates = list(range(3, max_value + 1, 2))
    if len(candidates) < length - 1:
        raise ValueError("not enough odd candidates for requested length")
    sampled = sorted(rng.sample(candidates, length - 1))
    return [2, *sampled]


def gap_shuffle_line(sequence: Sequence[int], rng: random.Random) -> list[int]:
    if len(sequence) < 2:
        raise ValueError("sequence must have at least two values")
    gaps = [sequence[idx + 1] - sequence[idx] for idx in range(len(sequence) - 1)]
    rng.shuffle(gaps)
    values = [sequence[0]]
    for gap in gaps:
        values.append(values[-1] + gap)
    return values


def prefix_distribution_for_sampler(
    sampler_name: str,
    prime_line: Sequence[int],
    depth: int,
    trials: int,
    seed: int,
) -> list[int]:
    rng = random.Random(seed)
    prefixes: list[int] = []
    for _trial in range(trials):
        if sampler_name == "wheel_line":
            line = random_wheel_line(len(prime_line), prime_line[-1], rng)
        elif sampler_name == "odd_line":
            line = random_odd_line(len(prime_line), prime_line[-1], rng)
        elif sampler_name == "gap_shuffle":
            line = gap_shuffle_line(prime_line, rng)
        else:
            raise ValueError(f"unknown sampler: {sampler_name}")
        abs_rows = difference_triangle(line, depth=depth, mode="abs")
        prefixes.append(leading_one_prefix(abs_rows))
    return prefixes


def null_prefix_distribution(
    length: int,
    max_value: int,
    depth: int,
    trials: int,
    seed: int,
) -> list[int]:
    rng = random.Random(seed)
    prefixes: list[int] = []
    for _trial in range(trials):
        line = random_wheel_line(length, max_value, rng)
        abs_rows = difference_triangle(line, depth=depth, mode="abs")
        prefixes.append(leading_one_prefix(abs_rows))
    return prefixes


def summarize_prefixes(prefixes: Sequence[int], depth: int) -> dict[str, float | int]:
    ordered = sorted(prefixes)
    return {
        "p50": ordered[len(ordered) // 2],
        "p95": ordered[int(math.ceil(0.95 * len(ordered))) - 1],
        "max": max(ordered),
        "full_rate": sum(prefix >= depth - 1 for prefix in ordered) / len(ordered),
    }


def face_summary(face: str, rows: Sequence[Sequence[float]]) -> FaceSummary:
    values = [abs(value) for row in rows for value in row]
    return FaceSummary(
        face=face,
        rows=len(rows),
        max_abs_value=max(values) if values else 0.0,
        mean_abs_value=sum(values) / len(values) if values else 0.0,
        leading_values=leading_values(rows)[:20],
    )


def build_vertices(
    face_rows: dict[str, list[list[float]]], max_rows: int = 80
) -> list[ShapeVertex]:
    vertices: list[ShapeVertex] = []
    face_count = len(face_rows)
    for face_idx, (face, rows) in enumerate(face_rows.items()):
        angle = 2.0 * math.pi * face_idx / face_count
        radial = (math.cos(angle), math.sin(angle))
        tangent = (-math.sin(angle), math.cos(angle))
        for row_idx, row in enumerate(rows[:max_rows]):
            if not row:
                continue
            center = (len(row) - 1) / 2.0
            base_radius = 1.0 + 0.018 * row_idx
            for col_idx, value in enumerate(row):
                lateral = (col_idx - center) * 0.012
                x = base_radius * radial[0] + lateral * tangent[0]
                y = base_radius * radial[1] + lateral * tangent[1]
                z = float(row_idx)
                vertices.append(
                    ShapeVertex(
                        face=face,
                        row=row_idx,
                        col=col_idx,
                        value=float(value),
                        x=x,
                        y=y,
                        z=z,
                    )
                )
    return vertices


def run_probe(
    n_primes: int = 256,
    depth: int = 96,
    null_trials: int = 200,
    seed: int = 53,
    render: bool = False,
    out_dir: Path | None = None,
) -> dict[str, object]:
    primes = first_n_primes(n_primes)
    depth = min(depth, len(primes))
    abs_rows = difference_triangle(primes, depth=depth, mode="abs")
    signed_rows = difference_triangle(primes, depth=depth, mode="signed")
    face_rows = {
        face: transform_face(abs_rows, signed_rows, face) for face in FACE_NAMES
    }

    known_prefix = leading_one_prefix(abs_rows)
    null_summaries = {}
    for offset, sampler_name in enumerate(("odd_line", "wheel_line", "gap_shuffle")):
        prefixes = prefix_distribution_for_sampler(
            sampler_name=sampler_name,
            prime_line=primes,
            depth=depth,
            trials=null_trials,
            seed=seed + 1000 * offset,
        )
        null_summaries[sampler_name] = summarize_prefixes(prefixes, depth)

    max_null_p95 = max(float(summary["p95"]) for summary in null_summaries.values())
    survives_all = known_prefix > max_null_p95
    order_sensitive = known_prefix > float(null_summaries["gap_shuffle"]["p95"])
    wheel_unique = known_prefix > float(null_summaries["wheel_line"]["p95"])
    if survives_all:
        verdict = "GILBREATH_SEAM_SURVIVES_ALL_NULLS"
    elif order_sensitive and not wheel_unique:
        verdict = "ORDER_SIGNAL_WHEEL_NULL_MATCHES"
    else:
        verdict = "GILBREATH_SEAM_COLLAPSES"
    vertices = build_vertices(face_rows, max_rows=depth)

    summary: dict[str, object] = {
        "n_primes": len(primes),
        "depth": depth,
        "face_names": FACE_NAMES,
        "metrics": {
            "known_leading_one_prefix": known_prefix,
            "known_leading_one_rate": known_prefix / max(depth - 1, 1),
            "max_null_prefix_p95": max_null_p95,
            "prefix_margin_vs_max_null": known_prefix - max_null_p95,
            "order_sensitive_vs_gap_shuffle": order_sensitive,
            "unique_vs_wheel_null": wheel_unique,
            "nulls": null_summaries,
        },
        "face_summaries": [
            asdict(face_summary(face, rows)) for face, rows in face_rows.items()
        ],
        "decision_record": {
            "promotion": "QUARANTINE_RESEARCH_ONLY",
            "verdict": verdict,
            "survives_all_nulls": survives_all,
            "order_sensitive_vs_gap_shuffle": order_sensitive,
            "unique_vs_wheel_null": wheel_unique,
            "claim_boundary": (
                "Known-prime finite prefix with odd, wheel, and gap-shuffle nulls only. "
                "Gilbreath's conjecture remains unproven."
            ),
        },
    }
    if out_dir is not None:
        write_artifacts(summary, vertices, out_dir, render=render)
    return summary


def write_artifacts(
    summary: dict[str, object],
    vertices: Sequence[ShapeVertex],
    out_dir: Path,
    render: bool = False,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    with (out_dir / "shape_vertices.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(vertices[0]).keys()))
        writer.writeheader()
        for vertex in vertices:
            writer.writerow(asdict(vertex))
    if render:
        render_shape(vertices, out_dir / "gilbreath_multiface_shape.png")


def render_shape(vertices: Sequence[ShapeVertex], out_path: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return

    faces = list(dict.fromkeys(vertex.face for vertex in vertices))
    fig = plt.figure(figsize=(12, 9), facecolor="#0b0d10")
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("#0b0d10")
    for face_idx, face in enumerate(faces):
        face_vertices = [
            vertex for vertex in vertices if vertex.face == face and vertex.row < 72
        ]
        xs = [vertex.x for vertex in face_vertices]
        ys = [vertex.y for vertex in face_vertices]
        zs = [vertex.z for vertex in face_vertices]
        values = [
            math.copysign(math.log1p(abs(vertex.value)), vertex.value)
            for vertex in face_vertices
        ]
        ax.scatter(
            xs,
            ys,
            zs,
            c=values,
            cmap="coolwarm",
            s=3,
            alpha=0.65,
            label=face if face_idx < 5 else None,
        )
    ax.set_title("Gilbreath Multi-Face Difference Shape", color="white", pad=18)
    ax.set_xlabel("face x", color="white")
    ax.set_ylabel("face y", color="white")
    ax.set_zlabel("difference depth", color="white")
    ax.tick_params(colors="white")
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-primes", type=int, default=256)
    parser.add_argument("--depth", type=int, default=96)
    parser.add_argument("--null-trials", type=int, default=200)
    parser.add_argument("--seed", type=int, default=53)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--render", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_probe(
        n_primes=args.n_primes,
        depth=args.depth,
        null_trials=args.null_trials,
        seed=args.seed,
        render=args.render,
        out_dir=args.out_dir,
    )
    print(json.dumps(summary["metrics"], indent=2, sort_keys=True))
    print(json.dumps(summary["decision_record"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
