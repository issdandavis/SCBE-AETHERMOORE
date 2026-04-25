from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.experiments.atomic_tokenizer_rename_benchmark import (  # noqa: E402
    DEFAULT_INPUT,
    Sample,
    _feature_keys_for,
    _l2_features,
    _load_samples,
    _normalize_features,
)
from scripts.experiments.cross_primary_braid_consistency import (  # noqa: E402
    PRIMARY_FAMILIES,
    build_feature_heads,
)


DEFAULT_OUTPUT = Path("artifacts") / "mathbac" / "binary_branch_braid_router"


@dataclass(frozen=True)
class BranchRoute:
    feature: str
    concept: str
    start_primary: str
    start_family: str
    fingerprint: str
    route_family: str
    bridge_primary: str
    first_hop_concept: str
    return_concept: str
    first_hop_ok: bool
    closure_ok: bool
    first_hop_distance: float
    return_distance: float


def primary_family(primary: str) -> str:
    for family, primaries in PRIMARY_FAMILIES.items():
        if primary in primaries:
            return family
    return "unknown"


def binary_fingerprint(feature: dict[str, float], keys: list[str], bits: int = 16) -> str:
    if bits <= 0:
        raise ValueError("bits must be positive")
    ranked = sorted(keys, key=lambda key: (-abs(feature.get(key, 0.0)), key))[:bits]
    values = [feature.get(key, 0.0) for key in ranked]
    mean = sum(values) / len(values) if values else 0.0
    return "".join("1" if value >= mean else "0" for value in values).ljust(bits, "0")


def route_family_from_pattern(fingerprint: str, start_family: str) -> str:
    """Choose the next branch family from a binary output pattern.

    The route is deterministic and intentionally simple: balanced leading and
    trailing density routes through prose bridge, parity keeps same family,
    high leading density moves to imperative code, and high trailing density
    moves to symbolic/functional.
    """

    ones = fingerprint.count("1")
    leading = fingerprint[: len(fingerprint) // 2].count("1")
    trailing = fingerprint[len(fingerprint) // 2 :].count("1")
    if leading == trailing:
        return "prose_bridge"
    if ones % 2 == 0:
        return start_family
    if leading > trailing:
        return "imperative_code"
    if trailing > leading:
        return "symbolic_functional"
    return "prose_bridge"


def choose_bridge_primary(
    start_primary: str,
    route_family: str,
    candidate_features: list[dict[str, float]],
    sample_features: list[dict[str, float]],
    samples: list[Sample],
    sample_index: int,
    keys: list[str],
) -> tuple[int, float]:
    route_primaries = set(PRIMARY_FAMILIES[route_family])
    candidates = [
        index
        for index, sample in enumerate(samples)
        if sample.primary in route_primaries and sample.primary != start_primary
    ]
    if not candidates:
        candidates = [index for index, sample in enumerate(samples) if sample.primary != start_primary]
    best_index = -1
    best_distance = math.inf
    for index in candidates:
        distance = _l2_features(candidate_features[sample_index], sample_features[index], keys)
        if distance < best_distance:
            best_distance = distance
            best_index = index
    return best_index, best_distance


def choose_return_primary_index(
    start_primary: str,
    bridge_index: int,
    sample_features: list[dict[str, float]],
    samples: list[Sample],
    keys: list[str],
) -> tuple[int, float]:
    candidates = [index for index, sample in enumerate(samples) if sample.primary == start_primary]
    best_index = -1
    best_distance = math.inf
    for index in candidates:
        distance = _l2_features(sample_features[bridge_index], sample_features[index], keys)
        if distance < best_distance:
            best_distance = distance
            best_index = index
    return best_index, best_distance


def route_feature(
    samples: list[Sample],
    sources: list[str],
    feature_name: str,
    feature_fn: Callable[[str], dict[str, float]],
) -> list[BranchRoute]:
    raw_features = [feature_fn(source) for source in sources]
    keys = _feature_keys_for(raw_features)
    normalized = _normalize_features(raw_features, keys)
    routes: list[BranchRoute] = []
    for index, sample in enumerate(samples):
        start_family = primary_family(sample.primary)
        fingerprint = binary_fingerprint(normalized[index], keys)
        route_family = route_family_from_pattern(fingerprint, start_family)
        bridge_index, first_distance = choose_bridge_primary(
            sample.primary,
            route_family,
            normalized,
            normalized,
            samples,
            index,
            keys,
        )
        return_index, return_distance = choose_return_primary_index(
            sample.primary,
            bridge_index,
            normalized,
            samples,
            keys,
        )
        bridge = samples[bridge_index]
        returned = samples[return_index]
        routes.append(
            BranchRoute(
                feature=feature_name,
                concept=sample.concept,
                start_primary=sample.primary,
                start_family=start_family,
                fingerprint=fingerprint,
                route_family=route_family,
                bridge_primary=bridge.primary,
                first_hop_concept=bridge.concept,
                return_concept=returned.concept,
                first_hop_ok=bridge.concept == sample.concept,
                closure_ok=returned.concept == sample.concept,
                first_hop_distance=first_distance,
                return_distance=return_distance,
            )
        )
    return routes


def _rate(values: Iterable[bool]) -> float:
    values = list(values)
    return sum(1 for value in values if value) / len(values) if values else 0.0


def summarize(routes: list[BranchRoute]) -> dict[str, Any]:
    route_counts = Counter(route.route_family for route in routes)
    per_start_family: dict[str, list[BranchRoute]] = defaultdict(list)
    for route in routes:
        per_start_family[route.start_family].append(route)
    return {
        "route_count": len(routes),
        "first_hop_accuracy": _rate(route.first_hop_ok for route in routes),
        "closure_accuracy": _rate(route.closure_ok for route in routes),
        "route_family_counts": dict(sorted(route_counts.items())),
        "per_start_family": {
            family: {
                "route_count": len(bucket),
                "first_hop_accuracy": _rate(route.first_hop_ok for route in bucket),
                "closure_accuracy": _rate(route.closure_ok for route in bucket),
                "route_family_counts": dict(sorted(Counter(route.route_family for route in bucket).items())),
            }
            for family, bucket in sorted(per_start_family.items())
        },
        "fingerprint_hash": sha256("".join(route.fingerprint for route in routes).encode("ascii")).hexdigest(),
        "failures": [asdict(route) for route in routes if not route.closure_ok][:40],
    }


def run(input_dir: Path = DEFAULT_INPUT, output_dir: Path = DEFAULT_OUTPUT, byte_map_mode: str = "hex") -> dict[str, Any]:
    samples = _load_samples(input_dir)
    sources = [sample.source for sample in samples]
    feature_heads = build_feature_heads(byte_map_mode)
    reports = {
        feature_name: summarize(route_feature(samples, sources, feature_name, feature_fn))
        for feature_name, feature_fn in feature_heads.items()
    }
    best = max(reports.items(), key=lambda item: item[1]["closure_accuracy"])
    report = {
        "version": "binary-branch-braid-router-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_dir": str(input_dir),
        "sample_count": len(samples),
        "method": (
            "Derive a deterministic binary fingerprint from each feature vector, choose a branch family from the bit pattern, "
            "route through the nearest sample in that family, then test return closure to the starting primary."
        ),
        "best_feature": best[0],
        "features": reports,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "binary_branch_braid_router.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
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
            print(f"{feature}: closure={feature_report['closure_accuracy']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
