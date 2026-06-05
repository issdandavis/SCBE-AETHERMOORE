#!/usr/bin/env python3
"""Build a Kaggle-ready public benchmark for SCBE prime-search methods.

The generated public package contains train/test rows and a sample submission.
The hidden-style solution and local scorer are written separately so the same
assets can become either a public Kaggle Dataset or a private Kaggle-style
competition package.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[2]
PROBE_PATH = REPO_ROOT / "scripts" / "research" / "prime_fog_of_war_probe.py"
DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "benchmarks" / "prime_search_kaggle"
SCHEMA_VERSION = "scbe_prime_search_kaggle_benchmark_v1"

FEATURE_COLUMNS = [
    "id",
    "p",
    "q",
    "angle_bin",
    "horizon_jump",
    "combined_gravity_field",
    "gravity_field_normalized",
    "gravity_product_field",
    "field_strength",
    "product_field_strength",
    "phase_alignment",
    "lane_resonance",
    "mesh_ratio",
    "wheel_attraction",
    "mod30_wheel",
    "div_ratio_clearance",
    "riemann_phase_coherence",
    "riemann_zero_wave",
    "phi_mean_zero_wave",
    "digit_last",
    "digit_carry_count",
    "digit_braid_score",
    "shadow_lattice_score",
    "shadow_lattice_hit",
    "shadow_lattice_nearest_gap",
    "path_b_score",
    "path_c_score",
    "path_d_score",
    "path_d_compass_alignment",
]
TRAIN_COLUMNS = [*FEATURE_COLUMNS, "is_twin_prime"]
TEST_COLUMNS = FEATURE_COLUMNS
SOLUTION_COLUMNS = ["id", "is_twin_prime"]
SUBMISSION_COLUMNS = ["id", "score"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def kaggle_owner(kaggle_id: str) -> str:
    return kaggle_id.split("/", 1)[0] if "/" in kaggle_id else kaggle_id


def kaggle_slug(kaggle_id: str) -> str:
    return kaggle_id.split("/", 1)[1] if "/" in kaggle_id else "scbe-prime-search-benchmark"


def load_probe_module() -> Any:
    spec = importlib.util.spec_from_file_location("prime_fog_of_war_probe", PROBE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load probe module from {PROBE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _as_float(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = row.get(key, default)
    if value is None:
        return default
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(result) or math.isinf(result):
        return default
    return result


def _as_int(row: dict[str, Any], key: str, default: int = 0) -> int:
    value = row.get(key, default)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def candidate_id(p: int) -> str:
    return f"p_{p}"


def candidate_record(row: dict[str, Any]) -> dict[str, Any]:
    p = _as_int(row, "p")
    record = {
        "id": candidate_id(p),
        "p": p,
        "q": _as_int(row, "q", p + 2),
        "angle_bin": _as_int(row, "angle_bin"),
        "horizon_jump": _as_float(row, "horizon_jump"),
        "combined_gravity_field": _as_float(row, "combined_gravity_field"),
        "gravity_field_normalized": _as_float(row, "gravity_field_normalized"),
        "gravity_product_field": _as_float(row, "gravity_product_field"),
        "field_strength": _as_float(row, "field_strength"),
        "product_field_strength": _as_float(row, "product_field_strength"),
        "phase_alignment": _as_float(row, "phase_alignment"),
        "lane_resonance": _as_float(row, "lane_resonance"),
        "mesh_ratio": _as_float(row, "mesh_ratio"),
        "wheel_attraction": _as_float(row, "wheel_attraction"),
        "mod30_wheel": _as_float(row, "mod30_wheel"),
        "div_ratio_clearance": _as_float(row, "div_ratio_clearance"),
        "riemann_phase_coherence": _as_float(row, "riemann_phase_coherence"),
        "riemann_zero_wave": _as_float(row, "riemann_zero_wave"),
        "phi_mean_zero_wave": _as_float(row, "phi_mean_zero_wave"),
        "digit_last": _as_int(row, "digit_last"),
        "digit_carry_count": _as_int(row, "digit_carry_count"),
        "digit_braid_score": _as_float(row, "digit_braid_score"),
        "shadow_lattice_score": _as_float(row, "shadow_lattice_score"),
        "shadow_lattice_hit": 1 if bool(row.get("shadow_lattice_hit")) else 0,
        "shadow_lattice_nearest_gap": _as_int(row, "shadow_lattice_nearest_gap"),
        "path_b_score": _as_float(row, "path_b_score"),
        "path_c_score": _as_float(row, "path_c_score"),
        "path_d_score": _as_float(row, "path_d_score"),
        "path_d_compass_alignment": _as_float(row, "path_d_compass_alignment"),
        "is_twin_prime": 1 if bool(row.get("verified")) else 0,
    }
    return record


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _deterministic_random_score(row_id: str) -> float:
    digest = hashlib.sha256(row_id.encode("utf-8")).hexdigest()
    return int(digest[:16], 16) / float(0xFFFFFFFFFFFFFFFF)


def _score_product(row: dict[str, Any], keys: list[str]) -> float:
    score = 1.0
    for key in keys:
        score *= max(0.0, _as_float(row, key))
    return score


def _indicator(condition: bool) -> float:
    return 1.0 if condition else 0.0


def _legal_twin_wheel(p: int) -> float:
    return _indicator(p <= 5 or p % 30 in {11, 17, 29})


def _decimal_gate(p: int) -> float:
    q = p + 2
    p_digit_sum = sum(int(digit) for digit in str(abs(p)))
    q_digit_sum = sum(int(digit) for digit in str(abs(q)))
    last_digit_gate = _indicator(p <= 5 or p % 10 in {1, 7, 9})
    digit_sum_gate = _indicator((p <= 3 or p_digit_sum % 3 != 0) and (q <= 3 or q_digit_sum % 3 != 0))
    return last_digit_gate * digit_sum_gate


def _branch_tree_algebra_score(row: dict[str, Any]) -> float:
    p = _as_int(row, "p")
    path_a = _as_float(row, "combined_gravity_field")
    path_b = _as_float(row, "path_b_score")
    path_c = _as_float(row, "path_c_score")
    path_d = _as_float(row, "path_d_score")
    shadow_clear = 1.0 - _as_float(row, "shadow_lattice_hit")
    algebraic_gate = _legal_twin_wheel(p) * _decimal_gate(p) * shadow_clear
    soft_score = (0.50 * path_a) + (0.18 * path_b) + (0.18 * path_c) + (0.14 * path_d)
    branch_product = max(0.0, path_a) * max(0.0, path_b) * max(0.0, path_c) * max(0.0, path_d)
    return algebraic_gate * (0.65 * soft_score + 0.35 * math.sqrt(max(0.0, branch_product)))


METHODS: dict[str, Callable[[dict[str, Any]], float]] = {
    "random_null": lambda row: _deterministic_random_score(str(row["id"])),
    "path_a_gravity": lambda row: _as_float(row, "combined_gravity_field"),
    "path_b_residue_density": lambda row: _as_float(row, "path_b_score"),
    "path_c_digit_shadow": lambda row: _as_float(row, "path_c_score"),
    "path_d_gap_compass": lambda row: _as_float(row, "path_d_score"),
    "abc_product": lambda row: _score_product(
        row,
        ["combined_gravity_field", "path_b_score", "path_c_score"],
    ),
    "abcd_product": lambda row: _score_product(
        row,
        ["combined_gravity_field", "path_b_score", "path_c_score", "path_d_score"],
    ),
    "branch_tree_algebra": _branch_tree_algebra_score,
}


def submission_for_method(records: list[dict[str, Any]], method: str) -> list[dict[str, Any]]:
    scorer = METHODS[method]
    return [{"id": row["id"], "score": round(float(scorer(row)), 12)} for row in records]


def _coerce_label(value: Any) -> int:
    text = str(value).strip().lower()
    return 1 if text in {"1", "true", "yes"} else 0


def score_submission_rows(
    solution_rows: list[dict[str, Any]],
    submission_rows: list[dict[str, Any]],
    top_ks: tuple[int, ...] = (10, 50, 100),
) -> dict[str, Any]:
    labels = {str(row["id"]): _coerce_label(row["is_twin_prime"]) for row in solution_rows}
    scores: dict[str, float] = {}
    duplicates: list[str] = []
    for row in submission_rows:
        row_id = str(row.get("id", ""))
        if row_id in scores:
            duplicates.append(row_id)
        scores[row_id] = _as_float(row, "score")
    if duplicates:
        raise ValueError(f"duplicate submission ids: {sorted(set(duplicates))[:5]}")

    missing = sorted(set(labels) - set(scores))
    if missing:
        raise ValueError(f"submission missing {len(missing)} ids; first missing id: {missing[0]}")

    extras = sorted(set(scores) - set(labels))
    ranked = sorted(labels, key=lambda row_id: (-scores[row_id], row_id))
    positives = sum(labels.values())
    total = len(ranked)
    base_rate = positives / total if total else 0.0

    hit_count = 0
    precision_sum = 0.0
    for index, row_id in enumerate(ranked, start=1):
        if labels[row_id]:
            hit_count += 1
            precision_sum += hit_count / index
    average_precision = precision_sum / positives if positives else 0.0

    by_k: dict[str, dict[str, float | int]] = {}
    for k in top_ks:
        actual_k = min(k, total)
        top_ids = ranked[:actual_k]
        top_hits = sum(labels[row_id] for row_id in top_ids)
        precision = top_hits / actual_k if actual_k else 0.0
        recall = top_hits / positives if positives else 0.0
        lift = precision / base_rate if base_rate else 0.0
        by_k[f"at_{k}"] = {
            "k": actual_k,
            "hits": top_hits,
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "lift": round(lift, 6),
        }

    return {
        "row_count": total,
        "positive_count": positives,
        "base_rate": round(base_rate, 6),
        "average_precision": round(average_precision, 6),
        "extras_ignored": len(extras),
        "top_k": by_k,
    }


SCORER_SCRIPT = r'''#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def label(value: str) -> int:
    return 1 if str(value).strip().lower() in {"1", "true", "yes"} else 0


def score(solution_path: Path, submission_path: Path) -> dict:
    solution = {row["id"]: label(row["is_twin_prime"]) for row in rows(solution_path)}
    scores = {}
    for row in rows(submission_path):
        row_id = row["id"]
        if row_id in scores:
            raise ValueError(f"duplicate id: {row_id}")
        scores[row_id] = float(row.get("score", 0) or 0)
    missing = sorted(set(solution) - set(scores))
    if missing:
        raise ValueError(f"missing {len(missing)} ids; first missing id: {missing[0]}")
    ranked = sorted(solution, key=lambda row_id: (-scores[row_id], row_id))
    positives = sum(solution.values())
    hits = 0
    precision_sum = 0.0
    for index, row_id in enumerate(ranked, start=1):
        if solution[row_id]:
            hits += 1
            precision_sum += hits / index
    return {
        "average_precision": round(precision_sum / positives if positives else 0.0, 6),
        "row_count": len(ranked),
        "positive_count": positives,
    }


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: score_submission.py <solution.csv> <submission.csv>")
    print(json.dumps(score(Path(sys.argv[1]), Path(sys.argv[2])), indent=2))
'''


def write_public_readme(path: Path, report: dict[str, Any]) -> None:
    text = "\n".join(
        [
            "# SCBE Prime Search Benchmark",
            "",
            "Goal: rank candidate twin-prime starters. A row is positive when both `p` and `p + 2` are prime.",
            "",
            "Files:",
            "",
            "- `train.csv`: labeled examples from the lower range.",
            "- `test.csv`: candidate rows to rank; labels are intentionally omitted.",
            "- `sample_submission.csv`: required submission format, `id,score`; higher scores rank first.",
            "",
            "Recommended Kaggle metric: Average Precision over the full ranked test set.",
            "",
            f"Creator: [{report['kaggle']['owner']}]({report['kaggle']['owner_profile_url']})",
            f"Dataset target: {report['kaggle']['dataset_url']}",
            "",
            "Claim boundary: this is a deterministic ranking benchmark for local prime-search sensors. It does not prove a number-theory theorem and should be interpreted through blind test performance, null controls, and ablations.",
            "",
            f"Generated: {report['generated_at_utc']}",
            f"Range: seed_limit={report['config']['seed_limit']}, limit={report['config']['limit']}, split={report['config']['split']}",
            "",
        ]
    )
    path.write_text(text, encoding="utf-8")


def write_user_profile(path: Path, report: dict[str, Any]) -> None:
    text = "\n".join(
        [
            "# User Profile",
            "",
            f"Kaggle owner: {report['kaggle']['owner']}",
            f"Kaggle profile: {report['kaggle']['owner_profile_url']}",
            f"Dataset target: {report['kaggle']['dataset_url']}",
            "",
            "Public benchmark role: dataset creator and baseline publisher.",
            "",
        ]
    )
    path.write_text(text, encoding="utf-8")


BENCHMARK_STUDIO_TASK = r'''"""Kaggle Benchmark Studio scaffold for the SCBE prime-search benchmark.

Use this in a Kaggle Community Benchmark task notebook. The deterministic
algorithm path can run directly; the `kaggle_benchmarks` task wrapper is present
when the Kaggle Benchmark Studio runtime provides the SDK.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path


DATA_ROOT = Path("/kaggle/input/scbe-prime-search-benchmark")


def indicator(condition: bool) -> float:
    return 1.0 if condition else 0.0


def if_then_else(condition: bool, when_true: float, when_false: float = 0.0) -> float:
    gate = indicator(condition)
    return gate * when_true + (1.0 - gate) * when_false


def legal_twin_wheel(p: int) -> float:
    return indicator(p <= 5 or p % 30 in {11, 17, 29})


def decimal_gate(p: int) -> float:
    q = p + 2
    last_digit_gate = indicator(p <= 5 or p % 10 in {1, 7, 9})
    digit_sum_gate = indicator((p <= 3 or sum(map(int, str(abs(p)))) % 3 != 0) and (q <= 3 or sum(map(int, str(abs(q)))) % 3 != 0))
    return last_digit_gate * digit_sum_gate


def branch_tree_score(row: dict[str, str]) -> float:
    """Algebraic if-then tree score for candidate ranking.

    A Boolean branch is an indicator variable. Nested if-then logic becomes
    products and sums over branch paths:

        if C then A else B = I(C) * A + (1 - I(C)) * B

    A whole decision tree becomes a sum over leaves:

        score(x) = sum_leaf value(leaf) * product(edge indicators on path)

    This scorer keeps the exact verifier outside the ranker.
    """

    p = int(float(row["p"]))
    path_a = float(row.get("combined_gravity_field", 0) or 0)
    path_b = float(row.get("path_b_score", 0) or 0)
    path_c = float(row.get("path_c_score", 0) or 0)
    path_d = float(row.get("path_d_score", 0) or 0)
    shadow_clear = 1.0 - float(row.get("shadow_lattice_hit", 0) or 0)
    algebraic_gate = legal_twin_wheel(p) * decimal_gate(p) * shadow_clear
    soft_score = (0.50 * path_a) + (0.18 * path_b) + (0.18 * path_c) + (0.14 * path_d)
    branch_product = max(0.0, path_a) * max(0.0, path_b) * max(0.0, path_c) * max(0.0, path_d)
    return algebraic_gate * (0.65 * soft_score + 0.35 * math.sqrt(max(0.0, branch_product)))


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def make_submission(test_csv: Path = DATA_ROOT / "test.csv") -> list[dict[str, float | str]]:
    rows = read_rows(test_csv)
    return [{"id": row["id"], "score": branch_tree_score(row)} for row in rows]


try:
    import kaggle_benchmarks as kbench
except Exception:
    kbench = None


if kbench is not None:
    @kbench.task(name="scbe_prime_search_branch_ranker")
    def scbe_prime_search_branch_ranker(llm):
        """Ask a model to explain and improve the algebraic branch ranker."""
        prompt = (
            "You are given a deterministic twin-prime candidate ranking benchmark. "
            "Explain how to convert if-then branches into algebraic indicator gates, "
            "then propose one rank-score formula using the columns path_a, path_b, "
            "path_c, path_d, mod30_wheel, digit gates, and shadow_lattice_hit. "
            "Keep the exact verifier outside the ranker."
        )
        response = llm.prompt(prompt)
        kbench.assertions.assert_contains_regex(
            r"(?i)(indicator|gate|boolean|branch)",
            response,
            expectation="Response should express branch logic as algebraic gates.",
        )
        kbench.assertions.assert_contains_regex(
            r"(?i)(rank|score|precision|average precision|lift)",
            response,
            expectation="Response should define a rank-scoring evaluation surface.",
        )


if __name__ == "__main__":
    submission = make_submission()
    print(f"rows={len(submission)} top_score={max(row['score'] for row in submission):.6f}")
'''


KAGGLE_CODE_RUNNER = r'''#!/usr/bin/env python3
"""Kaggle Code runner for the SCBE Prime Search Benchmark."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path


WORK_ROOT = Path("/kaggle/working") if Path("/kaggle/working").exists() else Path(".")


def resolve_data_root() -> Path:
    candidates = [
        Path("/kaggle/input/scbe-prime-search-benchmark"),
        Path("public_dataset"),
        Path(__file__).resolve().parent,
    ]
    for candidate in candidates:
        if (candidate / "test.csv").exists():
            return candidate
    input_root = Path("/kaggle/input")
    if input_root.exists():
        for test_csv in input_root.rglob("test.csv"):
            return test_csv.parent
    raise FileNotFoundError("could not find test.csv in Kaggle input mounts or bundled kernel files")


DATA_ROOT = resolve_data_root()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    factor = 5
    while factor * factor <= n:
        if n % factor == 0 or n % (factor + 2) == 0:
            return False
        factor += 6
    return True


def label(row: dict[str, str]) -> int:
    p = int(float(row["p"]))
    return 1 if is_prime(p) and is_prime(p + 2) else 0


def f(row: dict[str, str], key: str) -> float:
    try:
        value = float(row.get(key, 0) or 0)
    except ValueError:
        return 0.0
    return 0.0 if math.isnan(value) or math.isinf(value) else value


def indicator(condition: bool) -> float:
    return 1.0 if condition else 0.0


def deterministic_random(row: dict[str, str]) -> float:
    digest = hashlib.sha256(row["id"].encode("utf-8")).hexdigest()
    return int(digest[:16], 16) / float(0xFFFFFFFFFFFFFFFF)


def product(row: dict[str, str], keys: list[str]) -> float:
    score = 1.0
    for key in keys:
        score *= max(0.0, f(row, key))
    return score


def legal_twin_wheel(p: int) -> float:
    return indicator(p <= 5 or p % 30 in {11, 17, 29})


def decimal_gate(p: int) -> float:
    q = p + 2
    p_digit_sum = sum(int(digit) for digit in str(abs(p)))
    q_digit_sum = sum(int(digit) for digit in str(abs(q)))
    last_digit_gate = indicator(p <= 5 or p % 10 in {1, 7, 9})
    digit_sum_gate = indicator((p <= 3 or p_digit_sum % 3 != 0) and (q <= 3 or q_digit_sum % 3 != 0))
    return last_digit_gate * digit_sum_gate


def branch_tree_algebra(row: dict[str, str]) -> float:
    """Tree search as algebraic gates.

    if C then A else B = I(C) * A + (1 - I(C)) * B
    tree(x) = sum_leaf value(leaf) * product(path indicators)
    """
    p = int(float(row["p"]))
    path_a = f(row, "combined_gravity_field")
    path_b = f(row, "path_b_score")
    path_c = f(row, "path_c_score")
    path_d = f(row, "path_d_score")
    shadow_clear = 1.0 - f(row, "shadow_lattice_hit")
    algebraic_gate = legal_twin_wheel(p) * decimal_gate(p) * shadow_clear
    soft_score = (0.50 * path_a) + (0.18 * path_b) + (0.18 * path_c) + (0.14 * path_d)
    branch_product = max(0.0, path_a) * max(0.0, path_b) * max(0.0, path_c) * max(0.0, path_d)
    return algebraic_gate * (0.65 * soft_score + 0.35 * math.sqrt(max(0.0, branch_product)))


METHODS = {
    "random_null": deterministic_random,
    "path_a_gravity": lambda row: f(row, "combined_gravity_field"),
    "path_b_residue_density": lambda row: f(row, "path_b_score"),
    "path_c_digit_shadow": lambda row: f(row, "path_c_score"),
    "path_d_gap_compass": lambda row: f(row, "path_d_score"),
    "abc_product": lambda row: product(row, ["combined_gravity_field", "path_b_score", "path_c_score"]),
    "abcd_product": lambda row: product(row, ["combined_gravity_field", "path_b_score", "path_c_score", "path_d_score"]),
    "branch_tree_algebra": branch_tree_algebra,
}


def score_method(rows: list[dict[str, str]], name: str) -> dict:
    labels = {row["id"]: label(row) for row in rows}
    scores = {row["id"]: float(METHODS[name](row)) for row in rows}
    ranked = sorted(labels, key=lambda row_id: (-scores[row_id], row_id))
    positives = sum(labels.values())
    base_rate = positives / len(ranked) if ranked else 0.0
    hits = 0
    precision_sum = 0.0
    for index, row_id in enumerate(ranked, start=1):
        if labels[row_id]:
            hits += 1
            precision_sum += hits / index
    top_k = {}
    for k in (10, 50, 100):
        top_ids = ranked[: min(k, len(ranked))]
        top_hits = sum(labels[row_id] for row_id in top_ids)
        precision = top_hits / len(top_ids) if top_ids else 0.0
        top_k[f"at_{k}"] = {
            "hits": top_hits,
            "precision": round(precision, 6),
            "lift": round(precision / base_rate if base_rate else 0.0, 6),
        }
    return {
        "average_precision": round(precision_sum / positives if positives else 0.0, 6),
        "positive_count": positives,
        "base_rate": round(base_rate, 6),
        "top_k": top_k,
    }


def main() -> None:
    rows = read_rows(DATA_ROOT / "test.csv")
    baselines = {name: score_method(rows, name) for name in METHODS}
    best = max(baselines, key=lambda name: baselines[name]["average_precision"])
    report = {
        "schema_version": "scbe_prime_search_kaggle_code_run_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data_root": str(DATA_ROOT),
        "row_count": len(rows),
        "best_method": best,
        "best_average_precision": baselines[best]["average_precision"],
        "baselines": baselines,
        "algebraic_branch_identity": "if C then A else B = I(C)*A + (1-I(C))*B",
    }
    (WORK_ROOT / "prime_search_benchmark_latest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# SCBE Prime Search Benchmark Run",
        "",
        f"Generated: {report['generated_at_utc']}",
        f"Rows: {report['row_count']}",
        f"Best: {best} AP={report['best_average_precision']}",
        "",
        "| Method | AP | Precision@100 | Lift@100 |",
        "| --- | ---: | ---: | ---: |",
    ]
    for name, metrics in baselines.items():
        lines.append(
            f"| {name} | {metrics['average_precision']:.6f} | "
            f"{metrics['top_k']['at_100']['precision']:.3f} | "
            f"{metrics['top_k']['at_100']['lift']:.2f} |"
        )
    (WORK_ROOT / "prime_search_benchmark_latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"best_method": best, "best_average_precision": report["best_average_precision"]}, indent=2))


if __name__ == "__main__":
    main()
'''


def write_benchmark_studio_assets(public_dir: Path, report: dict[str, Any]) -> None:
    studio_dir = public_dir / "benchmark_studio"
    studio_dir.mkdir(parents=True, exist_ok=True)
    (studio_dir / "prime_search_branch_ranker_task.py").write_text(BENCHMARK_STUDIO_TASK, encoding="utf-8")
    (studio_dir / "README.md").write_text(
        "\n".join(
            [
                "# Kaggle Benchmark Studio Task",
                "",
                "Open `prime_search_branch_ranker_task.py` inside a Kaggle Benchmark Studio task notebook.",
                "It contains a deterministic branch-tree ranker and a Community Benchmarks task wrapper.",
                "",
                "Studio entry point:",
                "https://www.kaggle.com/benchmarks/tasks/new",
                "",
                f"Dataset target: {report['kaggle']['dataset_url']}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_kaggle_code_assets(out_dir: Path, report: dict[str, Any]) -> None:
    code_dir = out_dir / "kaggle_code"
    code_dir.mkdir(parents=True, exist_ok=True)
    (code_dir / "kernel.py").write_text(KAGGLE_CODE_RUNNER, encoding="utf-8")
    test_csv = out_dir / "public_dataset" / "test.csv"
    if test_csv.exists():
        (code_dir / "test.csv").write_bytes(test_csv.read_bytes())
    metadata = {
        "id": f"{report['kaggle']['owner']}/scbe-prime-search-benchmark-runner",
        "title": "SCBE Prime Search Benchmark Runner",
        "code_file": "kernel.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": False,
        "enable_gpu": False,
        "enable_internet": False,
        "dataset_sources": [report["kaggle"]["dataset_id"]],
        "competition_sources": [],
        "kernel_sources": [],
    }
    (code_dir / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def write_markdown_report(report: dict[str, Any], path: Path) -> None:
    rows = []
    for method, metrics in report["baselines"].items():
        rows.append(
            "| {method} | {ap:.6f} | {p100:.3f} | {lift100:.2f} |".format(
                method=method,
                ap=metrics["average_precision"],
                p100=metrics["top_k"]["at_100"]["precision"],
                lift100=metrics["top_k"]["at_100"]["lift"],
            )
        )
    text = "\n".join(
        [
            "# SCBE Prime Search Kaggle Benchmark",
            "",
            f"Generated: {report['generated_at_utc']}",
            f"Decision: {report['summary']['decision']}",
            f"Kaggle owner: `{report['kaggle']['owner']}`",
            f"Kaggle profile: {report['kaggle']['owner_profile_url']}",
            f"Public package: `{report['paths']['public_dataset']}`",
            f"Local scoring package: `{report['paths']['local_scoring']}`",
            "",
            "| Baseline | Average Precision | Precision@100 | Lift@100 |",
            "| --- | ---: | ---: | ---: |",
            *rows,
            "",
            "Claim boundary: deterministic ranking benchmark for prime-search methods; not a theorem claim.",
            "",
        ]
    )
    path.write_text(text, encoding="utf-8")


def build_assets(
    out_dir: Path,
    seed_limit: int,
    limit: int,
    split: int | None,
    bins: int,
    top: int,
    kaggle_id: str,
    title: str,
    kaggle_profile_url: str | None,
) -> dict[str, Any]:
    if limit <= seed_limit + 10:
        raise ValueError("limit must be meaningfully larger than seed_limit")
    split = split if split is not None else seed_limit + ((limit - seed_limit) // 2)
    if not (seed_limit < split < limit):
        raise ValueError("split must satisfy seed_limit < split < limit")

    probe = load_probe_module()
    payload = probe.run_twin_prime_gravity_search(seed_limit=seed_limit, limit=limit, bins=bins, top=top)
    records = sorted((candidate_record(row) for row in payload["all_candidates"]), key=lambda row: row["p"])
    train = [row for row in records if row["p"] < split]
    test = [row for row in records if row["p"] >= split]
    if not train or not test:
        raise ValueError("train/test split produced an empty side")

    public_dir = out_dir / "public_dataset"
    scoring_dir = out_dir / "local_scoring"
    baseline_dir = scoring_dir / "baselines"
    public_dir.mkdir(parents=True, exist_ok=True)
    scoring_dir.mkdir(parents=True, exist_ok=True)
    baseline_dir.mkdir(parents=True, exist_ok=True)

    solution = [{"id": row["id"], "is_twin_prime": row["is_twin_prime"]} for row in test]
    sample = [{"id": row["id"], "score": 0.0} for row in test]
    write_csv(public_dir / "train.csv", train, TRAIN_COLUMNS)
    write_csv(public_dir / "test.csv", test, TEST_COLUMNS)
    write_csv(public_dir / "sample_submission.csv", sample, SUBMISSION_COLUMNS)
    write_csv(scoring_dir / "solution.csv", solution, SOLUTION_COLUMNS)

    baselines: dict[str, Any] = {}
    for method in METHODS:
        submission = submission_for_method(test, method)
        write_csv(baseline_dir / f"{method}.csv", submission, SUBMISSION_COLUMNS)
        baselines[method] = score_submission_rows(solution, submission)

    best_method = max(baselines, key=lambda method: baselines[method]["average_precision"])
    owner = kaggle_owner(kaggle_id)
    slug = kaggle_slug(kaggle_id)
    owner_profile_url = kaggle_profile_url or f"https://www.kaggle.com/{owner}"
    dataset_url = f"https://www.kaggle.com/datasets/{owner}/{slug}"
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": _utc_now(),
        "summary": {
            "decision": "READY",
            "candidate_count": len(records),
            "train_count": len(train),
            "test_count": len(test),
            "test_positive_count": sum(row["is_twin_prime"] for row in test),
            "test_base_rate": round(sum(row["is_twin_prime"] for row in test) / len(test), 6),
            "best_baseline": best_method,
            "best_average_precision": baselines[best_method]["average_precision"],
        },
        "config": {
            "seed_limit": seed_limit,
            "limit": limit,
            "split": split,
            "bins": bins,
            "top": top,
        },
        "kaggle": {
            "dataset_id": kaggle_id,
            "title": title,
            "owner": owner,
            "owner_profile_url": owner_profile_url,
            "dataset_url": dataset_url,
            "upload_command": f"kaggle datasets create -p {public_dir} --dir-mode zip",
            "note": "Kaggle auth is required locally before upload.",
        },
        "paths": {
            "public_dataset": str(public_dir),
            "local_scoring": str(scoring_dir),
            "kaggle_code": str(out_dir / "kaggle_code"),
            "report_json": str(out_dir / "latest_report.json"),
            "report_markdown": str(out_dir / "LATEST.md"),
        },
        "claim_boundary": (
            "Ranks deterministic candidate p values by whether is_prime(p) and is_prime(p+2); "
            "supports benchmark comparisons only, not theorem claims."
        ),
        "baselines": baselines,
    }

    metadata = {
        "title": title,
        "id": kaggle_id,
        "subtitle": "Deterministic twin-prime candidate ranking benchmark with public baselines",
        "licenses": [{"name": "cc"}],
        "keywords": ["mathematics", "benchmark", "ranking", "primes", "scbe"],
    }
    (public_dir / "dataset-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    (scoring_dir / "score_submission.py").write_text(SCORER_SCRIPT, encoding="utf-8")
    (scoring_dir / "DO_NOT_UPLOAD_PUBLICLY.txt").write_text(
        "Keep solution.csv out of the public Kaggle Dataset. Use it only for local validation or a private competition scorer.\n",
        encoding="utf-8",
    )
    write_public_readme(public_dir / "README.md", report)
    write_user_profile(public_dir / "USER_PROFILE.md", report)
    write_user_profile(public_dir / "PROFILE.md", report)
    write_benchmark_studio_assets(public_dir, report)
    write_kaggle_code_assets(out_dir, report)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "latest_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_markdown_report(report, out_dir / "LATEST.md")
    return report


def score_submission_cli(solution_path: Path, submission_path: Path) -> dict[str, Any]:
    return score_submission_rows(read_csv(solution_path), read_csv(submission_path))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or score the SCBE prime-search Kaggle benchmark.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--seed-limit", type=int, default=1000)
    parser.add_argument("--limit", type=int, default=20000)
    parser.add_argument("--split", type=int)
    parser.add_argument("--bins", type=int, default=72)
    parser.add_argument("--top", type=int, default=100)
    parser.add_argument("--kaggle-id", default="issacizrealdavis/scbe-prime-search-benchmark")
    parser.add_argument("--kaggle-profile-url")
    parser.add_argument("--title", default="SCBE Prime Search Benchmark")
    parser.add_argument("--score-submission")
    parser.add_argument("--solution")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    out_dir = Path(args.out_dir).resolve()
    if args.score_submission:
        solution = Path(args.solution).resolve() if args.solution else out_dir / "local_scoring" / "solution.csv"
        metrics = score_submission_cli(solution, Path(args.score_submission).resolve())
        if args.json:
            print(json.dumps(metrics, indent=2))
        else:
            print(f"average_precision: {metrics['average_precision']:.6f}")
            print(f"rows: {metrics['row_count']} positives: {metrics['positive_count']}")
        return 0

    report = build_assets(
        out_dir=out_dir,
        seed_limit=args.seed_limit,
        limit=args.limit,
        split=args.split,
        bins=args.bins,
        top=args.top,
        kaggle_id=args.kaggle_id,
        title=args.title,
        kaggle_profile_url=args.kaggle_profile_url,
    )
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        summary = report["summary"]
        print(
            "prime-search Kaggle assets: {decision} "
            "train={train_count} test={test_count} positives={test_positive_count} "
            "best={best_baseline} ap={best_average_precision}".format(**summary)
        )
        print(f"public dataset: {report['paths']['public_dataset']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
