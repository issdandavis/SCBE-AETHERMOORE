"""Deterministic dataset export for the Kaprekar mirror topology shadow lane."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from .kaprekar_mirror_topology import KaprekarMirrorTopology

SCHEMA_VERSION = "kaprekar_mirror_auxiliary_view_v1"
OPERATOR_ID = "kaprekar_decimal_fixed_width_v1"
DEFAULT_SPLIT_SEED = 6174

FEATURE_ALLOWLIST = (
    "state",
    "auxiliary_view.mirror_state",
    "auxiliary_view.mirror_pair_id",
    "auxiliary_view.is_mirror_seam",
    "auxiliary_view.primary_depth",
    "auxiliary_view.mirror_depth",
    "auxiliary_view.primary_radial_depth",
    "auxiliary_view.mirror_radial_depth",
    "auxiliary_view.primary_point",
    "auxiliary_view.mirror_point",
)

LABEL_ONLY_FIELDS = (
    "labels.primary_next_state",
    "labels.mirror_next_state",
)

AUDIT_ONLY_FIELDS = (
    "audit.primary_path",
    "audit.mirror_path",
    "audit.primary_cycle",
    "audit.mirror_cycle",
    "audit.palindrome_envelope",
)


def canonical_family_id(state: str) -> str:
    """Group all digit permutations into one leakage-resistant family."""

    return "".join(sorted(state))


def split_for_family(family_id: str, *, split_seed: int = DEFAULT_SPLIT_SEED) -> str:
    """Assign one whole permutation family to a stable 80/10/10 split."""

    digest = hashlib.sha256(f"{split_seed}:{family_id}".encode("ascii")).digest()
    bucket = int.from_bytes(digest[:8], "big") % 10_000
    if bucket < 8_000:
        return "train"
    if bucket < 9_000:
        return "validation"
    return "test"


def build_records(
    *,
    width: int = 4,
    split_seed: int = DEFAULT_SPLIT_SEED,
    include_repdigits: bool = True,
) -> list[dict[str, Any]]:
    """Build records in numeric order without reading labels during splitting."""

    state_count = 10**width
    if state_count > 100_000:
        raise ValueError("dataset export is limited to at most 100,000 states")

    topology = KaprekarMirrorTopology(width=width)
    records: list[dict[str, Any]] = []

    for value in range(state_count):
        pair = topology.pair(value)
        is_repdigit = len(set(pair.state)) == 1
        if is_repdigit and not include_repdigits:
            continue

        family_id = canonical_family_id(pair.state)
        split = split_for_family(family_id, split_seed=split_seed)
        primary_next = topology.kaprekar_step(pair.state)
        mirror_next = topology.mirror_step(pair.mirror_state)
        payload_sha = hashlib.sha256(pair.state.encode("ascii")).hexdigest()
        record_id = hashlib.sha256(
            f"{SCHEMA_VERSION}:{width}:{pair.state}".encode("ascii")
        ).hexdigest()

        records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "record_id": record_id,
                "operator_id": OPERATOR_ID,
                "width": width,
                "state": pair.state,
                "exact_payload_sha256": payload_sha,
                "family_id": family_id,
                "split": split,
                "is_repdigit": is_repdigit,
                "training_role": (
                    "special_zero_basin" if is_repdigit else "synthetic_auxiliary_view"
                ),
                "auxiliary_view": {
                    "mirror_state": pair.mirror_state,
                    "mirror_pair_id": pair.mirror_pair_id,
                    "is_mirror_seam": pair.is_mirror_seam,
                    "primary_depth": pair.primary_trace.depth,
                    "mirror_depth": pair.mirror_trace.depth,
                    "primary_radial_depth": topology.radial_depth(
                        pair.primary_trace.depth
                    ),
                    "mirror_radial_depth": topology.radial_depth(
                        pair.mirror_trace.depth
                    ),
                    "primary_point": list(pair.primary_point),
                    "mirror_point": list(pair.mirror_point),
                    "primary_bottom": pair.primary_bottom,
                    "mirror_bottom": pair.mirror_bottom,
                },
                "labels": {
                    "primary_next_state": primary_next,
                    "mirror_next_state": mirror_next,
                },
                "audit": {
                    "primary_path": list(pair.primary_trace.path),
                    "mirror_path": list(pair.mirror_trace.path),
                    "primary_cycle": list(pair.primary_trace.cycle),
                    "mirror_cycle": list(pair.mirror_trace.cycle),
                    "palindrome_envelope": pair.palindrome_envelope,
                },
                "claim_boundary": (
                    "shadow-only many-to-one topology features; retain the exact payload hash "
                    "and do not use this view for governance or reversible encoding"
                ),
            }
        )

    assert_family_disjoint(records)
    return records


def assert_family_disjoint(records: Iterable[dict[str, Any]]) -> None:
    """Fail if one permutation family appears in more than one split."""

    family_splits: dict[str, set[str]] = {}
    for record in records:
        family_splits.setdefault(str(record["family_id"]), set()).add(
            str(record["split"])
        )

    leaked = {
        family: sorted(splits)
        for family, splits in family_splits.items()
        if len(splits) != 1
    }
    if leaked:
        sample = dict(list(sorted(leaked.items()))[:5])
        raise ValueError(f"permutation families cross splits: {sample}")


def _canonical_json_line(record: dict[str, Any]) -> str:
    return json.dumps(record, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def write_dataset(
    output_path: str | Path,
    manifest_path: str | Path,
    *,
    width: int = 4,
    split_seed: int = DEFAULT_SPLIT_SEED,
    include_repdigits: bool = True,
) -> dict[str, Any]:
    """Write deterministic JSONL plus a deterministic provenance manifest."""

    output = Path(output_path)
    manifest_output = Path(manifest_path)
    records = build_records(
        width=width,
        split_seed=split_seed,
        include_repdigits=include_repdigits,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(_canonical_json_line(record) + "\n")

    output_sha = hashlib.sha256(output.read_bytes()).hexdigest()
    split_counts = Counter(str(record["split"]) for record in records)
    family_counts = Counter(
        (str(record["split"]), str(record["family_id"])) for record in records
    )
    repdigit_count = sum(bool(record["is_repdigit"]) for record in records)
    topology_source = Path(__file__).with_name("kaprekar_mirror_topology.py")

    manifest = {
        "schema_version": "kaprekar_mirror_dataset_manifest_v1",
        "dataset_schema_version": SCHEMA_VERSION,
        "operator_id": OPERATOR_ID,
        "width": width,
        "split_seed": split_seed,
        "split_method": "sha256(seed:sorted_digit_multiset), 80/10/10 thresholds",
        "group_key": "family_id",
        "family_disjoint": True,
        "record_count": len(records),
        "non_repdigit_count": len(records) - repdigit_count,
        "repdigit_count": repdigit_count,
        "split_counts": dict(sorted(split_counts.items())),
        "family_counts": {
            split: sum(1 for family_split, _ in family_counts if family_split == split)
            for split in ("train", "validation", "test")
        },
        "output_file": output.name,
        "output_sha256": output_sha,
        "topology_source_sha256": hashlib.sha256(
            topology_source.read_bytes()
        ).hexdigest(),
        "feature_allowlist": list(FEATURE_ALLOWLIST),
        "label_only_fields": list(LABEL_ONLY_FIELDS),
        "audit_only_fields": list(AUDIT_ONLY_FIELDS),
        "promotion_state": "shadow_only",
        "claim_boundary": (
            "The dataset is synthetic and many-to-one. A benchmark must beat no-feature, "
            "simple-statistic, random-shell, and shuffled-depth controls before Clay intake."
        ),
    }

    manifest_output.parent.mkdir(parents=True, exist_ok=True)
    manifest_output.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Destination JSONL path.")
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--width", type=int, default=4)
    parser.add_argument("--split-seed", type=int, default=DEFAULT_SPLIT_SEED)
    parser.add_argument("--exclude-repdigits", action="store_true")
    args = parser.parse_args()

    manifest_path = args.manifest or args.output.with_suffix(".manifest.json")
    manifest = write_dataset(
        args.output,
        manifest_path,
        width=args.width,
        split_seed=args.split_seed,
        include_repdigits=not args.exclude_repdigits,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
