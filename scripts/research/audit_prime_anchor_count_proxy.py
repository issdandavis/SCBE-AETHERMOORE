"""Audit clustered score peaks as a proxy prime-anchor counting function.

This is not a primality test. It measures whether a score field can be turned
into countable anchor clusters:

    A_hat(range) = number of clustered local score maxima

and compares that count to the verifier's known hidden anchor count.

Two errors are intentionally kept separate:

1. count_error = predicted_clusters - actual_unique_anchors
2. bijection errors: false clusters, missed anchors, duplicate clusters

A small count_error alone is not enough; it can still be wrong anchors.
"""

from __future__ import annotations

import argparse
import bisect
import json
import math
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.research.range_regime_classifier import (  # noqa: E402
    ANCHOR_THRESHOLD,
    COOP_WA,
    COOP_WC,
    COOP_WF,
    D_WA,
    D_WC,
    D_WF,
    DOMINANT_WA,
    DOMINANT_WC,
    DOMINANT_WF,
    HISTORY,
    V6_REGIME_WEIGHTS,
    WINDOW,
    _load_frozen_spec,
    build_range_features,
    dyn_blend,
    predict_regime_v6,
    z_norm,
)
from scripts.research.run_field_branch_gate_search import (
    ensure_dynamic_profiles,
)  # noqa: E402
from scripts.research.run_prime_search_engine_bench import (  # noqa: E402
    DEFAULT_ROW_CACHE_DIR,
    build_or_load_rows,
    fit_centroid_ranker,
    fit_score_normalizer,
    fresh_rows,
    labels,
    linear_scores,
    matrix,
    score_frozen,
    split_ordered_rows,
)

RINGS: dict[str, tuple[int, int]] = {
    "A": (100_000_000, 150_000_000),
    "B": (150_000_000, 200_000_000),
    "C": (200_000_000, 250_000_000),
    "D": (250_000_000, 300_000_000),
    "E": (300_000_000, 350_000_000),
    "F": (350_000_000, 400_000_000),
    "G": (400_000_000, 450_000_000),
    "H": (450_000_000, 500_000_000),
    "I": (500_000_000, 550_000_000),
    "J": (550_000_000, 600_000_000),
    "K": (600_000_000, 650_000_000),
    "L": (650_000_000, 700_000_000),
    "M": (700_000_000, 750_000_000),
    "N": (750_000_000, 800_000_000),
}

SCORE_FAMILIES = (
    "frozen",
    "dominant",
    "magnitude",
    "frozen_coherent",
    "v6",
    "rr_sqrt1_exact",
    "rr_sqrt1_near",
    "rr_sqrt1",
)

RR_SMALL_PRIMES = (3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47)
RR_SQRT1_SHELLS = (
    (3, 5, 7, 11),
    (3, 5, 7, 11, 13),
    (3, 5, 7, 11, 13, 17),
)


@dataclass(frozen=True)
class PeakConfig:
    score_family: str
    percentile: float
    radius: int

    @property
    def config_id(self) -> str:
        pct = str(self.percentile).replace(".", "p")
        return f"{self.score_family}_p{pct}_r{self.radius}"


def anchor_id(row: dict[str, Any]) -> object | None:
    return row.get("first_anchor_idx", row.get("first_anchor_prime"))


def actual_anchor_ids(rows: list[dict[str, Any]]) -> set[object]:
    return {
        anchor_id(row)
        for row in rows
        if row.get("future_anchor") and anchor_id(row) is not None
    }


def crt_pair(a: int, m: int, b: int, n: int) -> int:
    """Chinese-remainder merge for coprime moduli."""
    return (a + m * (((b - a) * pow(m, -1, n)) % n)) % (m * n)


@lru_cache(maxsize=None)
def sqrt1_residues(prime_factors: tuple[int, ...]) -> tuple[int, ...]:
    residues = [0]
    modulus = 1
    for prime in prime_factors:
        next_residues = []
        for residue in residues:
            next_residues.append(crt_pair(residue, modulus, 1, prime))
            next_residues.append(crt_pair(residue, modulus, prime - 1, prime))
        residues = next_residues
        modulus *= prime
    return tuple(sorted(set(residues)))


def circular_residue_distance(
    residue: int, targets: tuple[int, ...], modulus: int
) -> int:
    if not targets:
        return 0
    index = bisect.bisect_left(targets, residue)
    candidates = []
    for candidate_index in (index - 1, index, 0, len(targets) - 1):
        target = targets[candidate_index % len(targets)]
        direct = abs(residue - target)
        candidates.append(min(direct, modulus - direct))
    return min(candidates)


def rr_sqrt1_exact_score(n: int) -> float:
    """Weighted count of small-prime boundaries n == +/-1 mod p."""
    total = sum(math.log(prime) for prime in RR_SMALL_PRIMES)
    if total <= 0:
        return 0.0
    hit = 0.0
    for prime in RR_SMALL_PRIMES:
        residue = n % prime
        if residue == 1 or residue == prime - 1:
            hit += math.log(prime)
    return hit / total


def rr_sqrt1_near_score(n: int) -> float:
    """Multiscale closeness to CRT sqrt(1) boundary shells."""
    components = []
    for factors in RR_SQRT1_SHELLS:
        modulus = math.prod(factors)
        targets = sqrt1_residues(factors)
        residue = n % modulus
        distance = circular_residue_distance(residue, targets, modulus)
        half_cell = modulus / max(1, 2 * len(targets))
        components.append(1.0 - min(1.0, distance / half_cell))
    return sum(components) / len(components)


def rr_sqrt1_scores(rows: list[dict[str, Any]]) -> dict[str, list[float]]:
    exact = []
    near = []
    for row in rows:
        n = int(row["scan_prime"])
        exact.append(rr_sqrt1_exact_score(n))
        near.append(rr_sqrt1_near_score(n))
    combined = [(0.65 * e) + (0.35 * c) for e, c in zip(exact, near)]
    return {
        "rr_sqrt1_exact": exact,
        "rr_sqrt1_near": near,
        "rr_sqrt1": combined,
    }


def percentile_cutoff(scores: list[float], percentile: float) -> float:
    clean = sorted(score for score in scores if math.isfinite(score))
    if not clean:
        return math.inf
    index = min(len(clean) - 1, max(0, int(math.ceil(percentile * len(clean))) - 1))
    return clean[index]


def local_peak_indices(
    rows: list[dict[str, Any]], scores: list[float], cutoff: float
) -> list[int]:
    out: list[int] = []
    for index, score in enumerate(scores):
        if not math.isfinite(score) or score < cutoff:
            continue
        prev_score = scores[index - 1] if index > 0 else -math.inf
        next_score = scores[index + 1] if index + 1 < len(scores) else -math.inf
        if score >= prev_score and score > next_score:
            out.append(index)
    return out


def non_max_suppress_by_scan_gap(
    rows: list[dict[str, Any]],
    scores: list[float],
    peak_indices: list[int],
    radius: int,
) -> list[int]:
    selected: list[int] = []
    for index in sorted(
        peak_indices, key=lambda item: (-scores[item], rows[item]["scan_idx"])
    ):
        scan_idx = int(rows[index]["scan_idx"])
        if any(
            abs(scan_idx - int(rows[prior]["scan_idx"])) < radius for prior in selected
        ):
            continue
        selected.append(index)
    return sorted(selected, key=lambda item: int(rows[item]["scan_idx"]))


def evaluate_clusters(
    rows: list[dict[str, Any]], scores: list[float], config: PeakConfig
) -> dict[str, Any]:
    cutoff = percentile_cutoff(scores, config.percentile)
    peaks = local_peak_indices(rows, scores, cutoff)
    selected = non_max_suppress_by_scan_gap(rows, scores, peaks, config.radius)

    actual_ids = actual_anchor_ids(rows)
    seen: set[object] = set()
    false_clusters = 0
    duplicate_clusters = 0
    hit_ids: set[object] = set()
    cluster_rows: list[dict[str, Any]] = []

    for rank, index in enumerate(selected, start=1):
        row = rows[index]
        aid = anchor_id(row) if row.get("future_anchor") else None
        if aid is None:
            false_clusters += 1
        elif aid in seen:
            duplicate_clusters += 1
        else:
            hit_ids.add(aid)
            seen.add(aid)
        cluster_rows.append(
            {
                "rank": rank,
                "scan_idx": row.get("scan_idx"),
                "scan_prime": row.get("scan_prime"),
                "score": round(scores[index], 6),
                "future_anchor": bool(row.get("future_anchor")),
                "anchor_idx": row.get("first_anchor_idx"),
                "anchor_prime": row.get("first_anchor_prime"),
                "lead_steps": row.get("lead_steps"),
            }
        )

    predicted = len(selected)
    actual = len(actual_ids)
    unique_hits = len(hit_ids)
    misses = actual - unique_hits
    return {
        "config_id": config.config_id,
        "score_family": config.score_family,
        "percentile": config.percentile,
        "radius": config.radius,
        "cutoff": round(cutoff, 6) if math.isfinite(cutoff) else None,
        "candidate_local_peaks": len(peaks),
        "predicted_clusters": predicted,
        "actual_unique_anchors": actual,
        "count_error": predicted - actual,
        "abs_count_error": abs(predicted - actual),
        "unique_anchor_hits": unique_hits,
        "false_clusters": false_clusters,
        "missed_anchors": misses,
        "duplicate_clusters": duplicate_clusters,
        "precision": round(unique_hits / predicted, 6) if predicted else 0.0,
        "recall": round(unique_hits / actual, 6) if actual else 0.0,
        "hit_anchor_ids": sorted(hit_ids),
        "cluster_rows": cluster_rows[:50],
    }


class ScoreContext:
    def __init__(self, cache_dir: Path) -> None:
        ensure_dynamic_profiles()
        self.cache_dir = cache_dir
        self.frozen_spec = _load_frozen_spec()
        rows_100 = build_or_load_rows(
            100_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, cache_dir, True
        )
        rows_150 = build_or_load_rows(
            150_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, cache_dir, True
        )
        range_a = fresh_rows(rows_100, rows_150)
        fit_a, _ = split_ordered_rows(range_a, 0.60)
        frozen_fit = score_frozen(fit_a, self.frozen_spec)
        self.frozen_mean, self.frozen_scale = fit_score_normalizer(frozen_fit)
        x_fit = matrix(fit_a)
        y_fit = labels(fit_a)
        self.centroid_model = fit_centroid_ranker(x_fit, y_fit)
        centroid_fit = linear_scores(self.centroid_model, x_fit)
        self.centroid_mean, self.centroid_scale = fit_score_normalizer(centroid_fit)

    def load_ring(self, ring: str) -> list[dict[str, Any]]:
        lower, upper = RINGS[ring]
        lower_rows = build_or_load_rows(
            lower, WINDOW, HISTORY, ANCHOR_THRESHOLD, self.cache_dir, True
        )
        upper_rows = build_or_load_rows(
            upper, WINDOW, HISTORY, ANCHOR_THRESHOLD, self.cache_dir, True
        )
        return fresh_rows(lower_rows, upper_rows)

    def scores_for(self, rows: list[dict[str, Any]]) -> dict[str, list[float]]:
        frozen_z = z_norm(
            score_frozen(rows, self.frozen_spec), self.frozen_mean, self.frozen_scale
        )
        centroid_z = z_norm(
            linear_scores(self.centroid_model, matrix(rows)),
            self.centroid_mean,
            self.centroid_scale,
        )
        features = build_range_features(rows, frozen_z, centroid_z)
        regime, fired = predict_regime_v6(features)
        wf, wa, wc = V6_REGIME_WEIGHTS[regime]
        rr_scores = rr_sqrt1_scores(rows)
        return {
            "frozen": frozen_z,
            "dominant": dyn_blend(
                frozen_z, centroid_z, DOMINANT_WF, DOMINANT_WA, DOMINANT_WC
            ),
            "magnitude": dyn_blend(frozen_z, centroid_z, D_WF, D_WA, D_WC),
            "frozen_coherent": dyn_blend(
                frozen_z, centroid_z, COOP_WF, COOP_WA, COOP_WC
            ),
            "v6": dyn_blend(frozen_z, centroid_z, wf, wa, wc),
            **rr_scores,
            "_regime": [regime],  # type: ignore[list-item]
            "_fired": fired,  # type: ignore[dict-item]
        }


def parse_csv_floats(value: str) -> list[float]:
    return [float(part.strip()) for part in value.split(",") if part.strip()]


def parse_csv_ints(value: str) -> list[int]:
    return [int(part.strip()) for part in value.split(",") if part.strip()]


def choose_best(results: list[dict[str, Any]]) -> dict[str, Any]:
    return min(
        results,
        key=lambda item: (
            item["abs_count_error"],
            item["false_clusters"]
            + item["missed_anchors"]
            + item["duplicate_clusters"],
            -item["precision"],
            -item["recall"],
            item["config_id"],
        ),
    )


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Prime Anchor Count Proxy Audit",
        "",
        "Counts clustered local score maxima and compares them to known hidden anchor counts.",
        "Count error is separate from false/missed/duplicate anchor errors.",
        "",
        "## Best Per Ring",
        "",
        (
            "| Ring | Best config | Predicted clusters | Actual anchors | Count error | "
            "Precision | Recall | False | Missed | Duplicates |"
        ),
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for ring, item in report["best_per_ring"].items():
        lines.append(
            "| {ring} | {config_id} | {predicted_clusters} | {actual_unique_anchors} | {count_error:+d} | "
            "{precision:.1%} | {recall:.1%} | {false_clusters} | {missed_anchors} | {duplicate_clusters} |".format(
                ring=ring,
                **item,
            )
        )
    lines.extend(["", "## Fixed Config Evaluation", ""])
    fixed = report.get("fixed_config")
    if fixed:
        lines.append(f"Fixed from `{fixed['fit_ring']}`: `{fixed['config_id']}`")
        lines.extend(
            [
                "",
                (
                    "| Ring | Predicted clusters | Actual anchors | Count error | "
                    "Precision | Recall | False | Missed | Duplicates |"
                ),
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for ring, item in fixed["results"].items():
            lines.append(
                "| {ring} | {predicted_clusters} | {actual_unique_anchors} | {count_error:+d} | "
                "{precision:.1%} | {recall:.1%} | {false_clusters} | {missed_anchors} | {duplicate_clusters} |".format(
                    ring=ring,
                    **item,
                )
            )
    lines.extend(
        [
            "",
            "## Caveat",
            "",
            (
                "A low count error does not prove a prime-counting method unless false clusters, "
                "misses, and duplicates are also controlled."
            ),
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rings", default="K,L,M,N")
    parser.add_argument(
        "--percentiles", default="0.50,0.55,0.60,0.65,0.70,0.75,0.80,0.85,0.90"
    )
    parser.add_argument("--radii", default="6,12,18,24,36")
    parser.add_argument(
        "--families", default="frozen,dominant,magnitude,frozen_coherent,v6,rr_sqrt1"
    )
    parser.add_argument("--fit-ring", default="M")
    parser.add_argument("--out-dir", default="artifacts/prime_anchor_count_proxy")
    parser.add_argument("--cache-dir", default=str(DEFAULT_ROW_CACHE_DIR))
    args = parser.parse_args()

    rings = [ring.strip().upper() for ring in args.rings.split(",") if ring.strip()]
    families = [name.strip() for name in args.families.split(",") if name.strip()]
    unknown = sorted(set(rings) - set(RINGS))
    if unknown:
        raise SystemExit(f"unknown rings: {unknown}")
    unknown_families = sorted(set(families) - set(SCORE_FAMILIES))
    if unknown_families:
        raise SystemExit(f"unknown score families: {unknown_families}")

    configs = [
        PeakConfig(score_family=family, percentile=percentile, radius=radius)
        for family in families
        for percentile in parse_csv_floats(args.percentiles)
        for radius in parse_csv_ints(args.radii)
    ]

    ctx = ScoreContext(Path(args.cache_dir))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_results: dict[str, list[dict[str, Any]]] = {}
    best_per_ring: dict[str, dict[str, Any]] = {}
    ring_meta: dict[str, dict[str, Any]] = {}

    for ring in rings:
        rows = ctx.load_ring(ring)
        score_map = ctx.scores_for(rows)
        ring_meta[ring] = {
            "row_count": len(rows),
            "actual_unique_anchors": len(actual_anchor_ids(rows)),
            "v6_regime": score_map["_regime"][0],
            "v6_fired": score_map["_fired"],
        }
        ring_results: list[dict[str, Any]] = []
        for config in configs:
            scores = score_map[config.score_family]
            ring_results.append(evaluate_clusters(rows, scores, config))
        all_results[ring] = sorted(ring_results, key=lambda item: item["config_id"])
        best_per_ring[ring] = choose_best(ring_results)

    fixed_config = None
    fit_ring = args.fit_ring.upper()
    if fit_ring in all_results:
        chosen = choose_best(all_results[fit_ring])
        config = PeakConfig(
            chosen["score_family"], chosen["percentile"], chosen["radius"]
        )
        fixed_results = {}
        for ring in rings:
            match = next(
                item
                for item in all_results[ring]
                if item["config_id"] == config.config_id
            )
            fixed_results[ring] = match
        fixed_config = {
            "fit_ring": fit_ring,
            "config_id": config.config_id,
            "score_family": config.score_family,
            "percentile": config.percentile,
            "radius": config.radius,
            "results": fixed_results,
        }

    report = {
        "schema": "prime_anchor_count_proxy_audit_v1",
        "rings": rings,
        "configs": [config.__dict__ for config in configs],
        "ring_meta": ring_meta,
        "best_per_ring": best_per_ring,
        "fixed_config": fixed_config,
        "all_results": all_results,
    }
    (out_dir / "latest_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    write_markdown(report, out_dir / "RESULTS.md")

    print("Prime anchor count proxy audit")
    print(f"  rings: {', '.join(rings)}")
    print(f"  configs: {len(configs)}")
    print(f"  wrote: {out_dir / 'RESULTS.md'}")
    print("\nBest per ring:")
    for ring, item in best_per_ring.items():
        print(
            f"  {ring}: {item['config_id']} clusters={item['predicted_clusters']} "
            f"actual={item['actual_unique_anchors']} error={item['count_error']:+d} "
            f"precision={item['precision']:.1%} recall={item['recall']:.1%}"
        )
    if fixed_config:
        print(f"\nFixed from {fit_ring}: {fixed_config['config_id']}")
        for ring, item in fixed_config["results"].items():
            print(
                f"  {ring}: clusters={item['predicted_clusters']} "
                f"actual={item['actual_unique_anchors']} error={item['count_error']:+d} "
                f"precision={item['precision']:.1%} recall={item['recall']:.1%}"
            )


if __name__ == "__main__":
    main()
