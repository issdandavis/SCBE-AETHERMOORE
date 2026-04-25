from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.experiments.atomic_tokenizer_rename_benchmark import (  # noqa: E402
    DEFAULT_INPUT,
    PERIODIC_TABLE,
    Sample,
    _feature_keys_for,
    _l2_features,
    _load_periodic_table,
    _load_samples,
    _normalize_features,
    load_binary_hex_lookup,
    make_atomic_semantic_overlay_feature,
    make_binary_hex_chemistry_feature,
    make_layered_geometry_semantic_feature,
    make_operational_flow_feature,
    combine_feature_heads,
)


DEFAULT_OUTPUT = Path("artifacts") / "mathbac" / "cross_primary_braid_consistency"

PRIMARY_FAMILIES: dict[str, tuple[str, ...]] = {
    "imperative_code": ("KO", "AV", "RU"),
    "symbolic_functional": ("CA", "UM"),
    "prose_bridge": ("DR",),
}


@dataclass(frozen=True)
class CycleResult:
    feature: str
    start_primary: str
    bridge_primary: str
    concept: str
    first_hop_concept: str
    return_concept: str
    first_hop_ok: bool
    closure_ok: bool
    first_hop_distance: float
    return_distance: float


def build_feature_heads(byte_map_mode: str = "hex") -> dict[str, Callable[[str], dict[str, float]]]:
    table = _load_periodic_table(PERIODIC_TABLE)
    hex_lookup = load_binary_hex_lookup()
    chemistry = make_binary_hex_chemistry_feature(table, hex_lookup, mode=byte_map_mode)
    semantic = make_atomic_semantic_overlay_feature()
    flow = make_operational_flow_feature()
    geometry = make_layered_geometry_semantic_feature()
    return {
        f"chemistry_actual_{byte_map_mode}": chemistry,
        "semantic_overlay_current": semantic,
        "flow_reinforcement": flow,
        "layered_geometry_semantic": geometry,
        f"dual_lane_chemistry_semantic_{byte_map_mode}": combine_feature_heads(
            [("chemistry", chemistry, 1.0), ("semantic", semantic, 0.35)]
        ),
        f"reinforced_chemistry_semantic_flow_geometry_{byte_map_mode}": combine_feature_heads(
            [
                ("chemistry", chemistry, 1.0),
                ("semantic", semantic, 0.35),
                ("flow", flow, 0.75),
                ("geometry", geometry, 0.60),
            ]
        ),
    }


def _nearest_index(
    source_index: int,
    candidate_indices: list[int],
    features: list[dict[str, float]],
    keys: list[str],
    *,
    exclude_index: int | None = None,
) -> tuple[int, float]:
    best_index = -1
    best_distance = math.inf
    for candidate_index in candidate_indices:
        if candidate_index == exclude_index:
            continue
        distance = _l2_features(features[source_index], features[candidate_index], keys)
        if distance < best_distance:
            best_distance = distance
            best_index = candidate_index
    return best_index, best_distance


def cross_primary_cycles(
    samples: list[Sample],
    sources: list[str],
    feature_name: str,
    feature_fn: Callable[[str], dict[str, float]],
) -> list[CycleResult]:
    raw_features = [feature_fn(source) for source in sources]
    keys = _feature_keys_for(raw_features)
    features = _normalize_features(raw_features, keys)
    by_primary: dict[str, list[int]] = defaultdict(list)
    for index, sample in enumerate(samples):
        by_primary[sample.primary].append(index)

    results: list[CycleResult] = []
    for start_primary, start_indices in sorted(by_primary.items()):
        for bridge_primary, bridge_indices in sorted(by_primary.items()):
            if start_primary == bridge_primary:
                continue
            for start_index in start_indices:
                start_sample = samples[start_index]
                bridge_index, first_distance = _nearest_index(
                    start_index, bridge_indices, features, keys
                )
                return_index, return_distance = _nearest_index(
                    bridge_index,
                    start_indices,
                    features,
                    keys,
                    exclude_index=None,
                )
                bridge_sample = samples[bridge_index]
                return_sample = samples[return_index]
                results.append(
                    CycleResult(
                        feature=feature_name,
                        start_primary=start_primary,
                        bridge_primary=bridge_primary,
                        concept=start_sample.concept,
                        first_hop_concept=bridge_sample.concept,
                        return_concept=return_sample.concept,
                        first_hop_ok=bridge_sample.concept == start_sample.concept,
                        closure_ok=return_sample.concept == start_sample.concept,
                        first_hop_distance=first_distance,
                        return_distance=return_distance,
                    )
                )
    return results


def _rate(values: list[bool]) -> float:
    return sum(1 for value in values if value) / len(values) if values else 0.0


def summarize_cycles(results: list[CycleResult]) -> dict[str, Any]:
    pair_buckets: dict[str, list[CycleResult]] = defaultdict(list)
    family_buckets: dict[str, list[CycleResult]] = defaultdict(list)
    for result in results:
        pair_buckets[f"{result.start_primary}->{result.bridge_primary}->{result.start_primary}"].append(result)
        start_family = next(
            (name for name, primaries in PRIMARY_FAMILIES.items() if result.start_primary in primaries),
            "unknown",
        )
        bridge_family = next(
            (name for name, primaries in PRIMARY_FAMILIES.items() if result.bridge_primary in primaries),
            "unknown",
        )
        family_buckets[f"{start_family}->{bridge_family}->{start_family}"].append(result)

    return {
        "overall": {
            "cycle_count": len(results),
            "first_hop_accuracy": _rate([result.first_hop_ok for result in results]),
            "closure_accuracy": _rate([result.closure_ok for result in results]),
            "mean_first_hop_distance": sum(result.first_hop_distance for result in results) / len(results),
            "mean_return_distance": sum(result.return_distance for result in results) / len(results),
        },
        "per_pair": {
            pair: {
                "cycle_count": len(bucket),
                "first_hop_accuracy": _rate([result.first_hop_ok for result in bucket]),
                "closure_accuracy": _rate([result.closure_ok for result in bucket]),
            }
            for pair, bucket in sorted(pair_buckets.items())
        },
        "per_family": {
            family: {
                "cycle_count": len(bucket),
                "first_hop_accuracy": _rate([result.first_hop_ok for result in bucket]),
                "closure_accuracy": _rate([result.closure_ok for result in bucket]),
            }
            for family, bucket in sorted(family_buckets.items())
        },
        "failures": [
            asdict(result)
            for result in results
            if not result.closure_ok
        ][:40],
    }


def run(
    input_dir: Path = DEFAULT_INPUT,
    output_dir: Path = DEFAULT_OUTPUT,
    byte_map_mode: str = "hex",
) -> dict[str, Any]:
    samples = _load_samples(input_dir)
    sources = [sample.source for sample in samples]
    feature_heads = build_feature_heads(byte_map_mode)
    feature_reports: dict[str, Any] = {}
    for feature_name, feature_fn in feature_heads.items():
        cycles = cross_primary_cycles(samples, sources, feature_name, feature_fn)
        feature_reports[feature_name] = summarize_cycles(cycles)

    best_closure = max(
        feature_reports.items(),
        key=lambda item: item[1]["overall"]["closure_accuracy"],
    )
    report = {
        "version": "cross-primary-braid-consistency-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_dir": str(input_dir),
        "sample_count": len(samples),
        "primary_families": PRIMARY_FAMILIES,
        "method": (
            "For each concept in primary A, find nearest same-feature sample in primary B, "
            "then hop back to primary A. A->B->A closure is consistent when the returned concept matches the start concept."
        ),
        "best_closure_feature": best_closure[0],
        "features": feature_reports,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "cross_primary_braid_consistency.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--byte-map-mode", choices=["mod", "stride", "hex", "hash"], default="hex")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    report = run(args.input_dir, args.output_dir, args.byte_map_mode)
    if args.json:
        print(json.dumps(report["features"], indent=2))
    else:
        for feature, feature_report in report["features"].items():
            overall = feature_report["overall"]
            print(
                f"{feature}: first_hop={overall['first_hop_accuracy']:.3f} "
                f"closure={overall['closure_accuracy']:.3f}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
