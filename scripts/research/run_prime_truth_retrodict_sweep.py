"""Retrodict integrity sweep for prime-fog anchor artifacts.

This closes the verifier gap for historical rings: every stored anchor value is
checked by an independent truth layer for both primality and the P(P(n)) index
condition, meaning p is prime and pi(p) is prime.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.research.prime_truth_oracle import (
    AnchorSuperprimeCheck,
    extract_artifact_anchor_values,
    is_prime_u64,
    prime_indices_for_values,
)


OUT_DIR = REPO_ROOT / "artifacts" / "prime_truth_retrodict_sweep"

DEFAULT_ARTIFACTS = (
    REPO_ROOT / "artifacts" / "prime_target_lock" / "target_lock_latest.json",
    REPO_ROOT / "artifacts" / "range_regime_classifier" / "regime_classifier_v2.json",
    REPO_ROOT / "artifacts" / "range_regime_classifier" / "cascade_v5_spec.json",
    REPO_ROOT / "artifacts" / "ring_i_cascade_v4" / "ring_i_results.json",
    REPO_ROOT / "artifacts" / "ring_i_cascade_v4_ip" / "latest_report.json",
    REPO_ROOT / "artifacts" / "ring_j_cascade_v4" / "ring_j_results.json",
    REPO_ROOT / "artifacts" / "ring_k_cascade_v5" / "ring_k_results.json",
)


RANGE_INDEX_RE = re.compile(r"^\$\.ranges\[(\d+)\]")
TARGET_BY_RANGE_RE = re.compile(r"^\$\.targets_by_range\.([A-Z])\b")
RESULTS_RE = re.compile(r"^\$\.(f|g)_results\b")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _infer_ring(path: Path, data: Any, item_path: str) -> str | None:
    if isinstance(data, dict) and isinstance(data.get("ring"), str):
        return data["ring"]
    artifact_name = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    if "/ring_i_" in artifact_name:
        return "I"
    if "/ring_j_" in artifact_name:
        return "J"
    if "/ring_k_" in artifact_name:
        return "K"
    if path.name == "regime_classifier_v2.json":
        match = RESULTS_RE.match(item_path)
        if match:
            return match.group(1).upper()
    if path.name == "target_lock_latest.json" and isinstance(data, dict):
        match = RANGE_INDEX_RE.match(item_path)
        if match:
            ranges = data.get("ranges", [])
            index = int(match.group(1))
            if index < len(ranges):
                ring = ranges[index].get("range")
                if isinstance(ring, str):
                    return ring
        match = TARGET_BY_RANGE_RE.match(item_path)
        if match:
            return match.group(1)
    return None


def _make_check(path: str, value: int, prime_indices: dict[int, int]) -> AnchorSuperprimeCheck:
    is_prime = is_prime_u64(value)
    prime_index = prime_indices.get(value)
    index_is_prime = prime_index is not None and is_prime_u64(prime_index)
    return AnchorSuperprimeCheck(
        path=path,
        value=value,
        is_prime=is_prime,
        prime_index=prime_index,
        index_is_prime=index_is_prime,
        is_superprime=is_prime and index_is_prime,
    )


def build_report(artifact_paths: list[Path]) -> dict[str, Any]:
    artifact_entries: list[dict[str, Any]] = []
    no_anchor_artifacts: list[str] = []

    for path in artifact_paths:
        data = _load_json(path)
        extracted = extract_artifact_anchor_values(path)
        if not extracted:
            no_anchor_artifacts.append(str(path.relative_to(REPO_ROOT)))
        for item_path, value in extracted:
            artifact_entries.append(
                {
                    "artifact": str(path.relative_to(REPO_ROOT)),
                    "item_path": item_path,
                    "ring": _infer_ring(path, data, item_path),
                    "value": value,
                }
            )

    prime_indices = prime_indices_for_values(entry["value"] for entry in artifact_entries)

    artifact_summary: dict[str, dict[str, Any]] = {}
    ring_summary: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []

    for entry in artifact_entries:
        check = _make_check(entry["item_path"], entry["value"], prime_indices)
        artifact = entry["artifact"]
        artifact_bucket = artifact_summary.setdefault(
            artifact,
            {
                "entries_checked": 0,
                "unique_values": set(),
                "failed_entries": 0,
                "failed_values": set(),
            },
        )
        artifact_bucket["entries_checked"] += 1
        artifact_bucket["unique_values"].add(entry["value"])

        ring = entry["ring"] or "unknown"
        ring_bucket = ring_summary.setdefault(
            ring,
            {
                "entries_checked": 0,
                "unique_values": set(),
                "failed_entries": 0,
                "failed_values": set(),
                "artifacts": set(),
            },
        )
        ring_bucket["entries_checked"] += 1
        ring_bucket["unique_values"].add(entry["value"])
        ring_bucket["artifacts"].add(artifact)

        if not check.is_superprime:
            artifact_bucket["failed_entries"] += 1
            artifact_bucket["failed_values"].add(entry["value"])
            ring_bucket["failed_entries"] += 1
            ring_bucket["failed_values"].add(entry["value"])
            failures.append(
                {
                    "artifact": artifact,
                    "ring": entry["ring"],
                    **asdict(check),
                }
            )

    def finalize_bucket(bucket: dict[str, Any]) -> dict[str, Any]:
        return {
            "entries_checked": bucket["entries_checked"],
            "unique_values": len(bucket["unique_values"]),
            "failed_entries": bucket["failed_entries"],
            "failed_unique_values": len(bucket["failed_values"]),
            **({"artifacts": sorted(bucket["artifacts"])} if "artifacts" in bucket else {}),
        }

    artifacts_out = {
        artifact: finalize_bucket(bucket)
        for artifact, bucket in sorted(artifact_summary.items())
    }
    rings_out = {
        ring: finalize_bucket(bucket)
        for ring, bucket in sorted(ring_summary.items())
    }

    unique_values = {entry["value"] for entry in artifact_entries}
    return {
        "schema": "prime_truth_retrodict_sweep_v1",
        "date": datetime.now().isoformat(timespec="seconds"),
        "mode": "superprime",
        "definition": "anchor p is valid when p is prime and pi(p) is prime",
        "artifacts_requested": [str(path.relative_to(REPO_ROOT)) for path in artifact_paths],
        "artifacts_without_anchor_values": no_anchor_artifacts,
        "entry_count": len(artifact_entries),
        "unique_anchor_values": len(unique_values),
        "max_anchor_value": max(unique_values) if unique_values else None,
        "failed_entries": len(failures),
        "failed_unique_values": len({item["value"] for item in failures}),
        "artifact_summary": artifacts_out,
        "ring_summary": rings_out,
        "failures": failures[:100],
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Prime Truth Retrodict Sweep",
        "",
        f"Mode: `{report['mode']}`",
        "",
        f"Definition: {report['definition']}.",
        "",
        "| Scope | Entries | Unique anchors | Failed entries | Failed unique |",
        "| --- | ---: | ---: | ---: | ---: |",
        "| Overall | {entry_count} | {unique_anchor_values} | {failed_entries} | {failed_unique_values} |".format(**report),
        "",
        "## Rings",
        "",
        "| Ring | Entries | Unique anchors | Failed entries | Failed unique |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for ring, item in report["ring_summary"].items():
        lines.append(
            "| {ring} | {entries_checked} | {unique_values} | {failed_entries} | {failed_unique_values} |".format(
                ring=ring,
                **item,
            )
        )

    lines.extend(["", "## Artifacts", "", "| Artifact | Entries | Unique anchors | Failed entries | Failed unique |", "| --- | ---: | ---: | ---: | ---: |"])
    for artifact, item in report["artifact_summary"].items():
        lines.append(
            "| `{artifact}` | {entries_checked} | {unique_values} | {failed_entries} | {failed_unique_values} |".format(
                artifact=artifact,
                **item,
            )
        )

    if report["artifacts_without_anchor_values"]:
        lines.extend(["", "## No Extracted Anchors", ""])
        for artifact in report["artifacts_without_anchor_values"]:
            lines.append(f"- `{artifact}`")

    if report["failures"]:
        lines.extend(["", "## Failures", "", "| Artifact | Ring | Path | Value | Prime | Prime index | Index prime |", "| --- | --- | --- | ---: | --- | ---: | --- |"])
        for failure in report["failures"]:
            lines.append(
                "| `{artifact}` | {ring} | `{path}` | {value} | {is_prime} | {prime_index} | {index_is_prime} |".format(
                    **failure
                )
            )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    artifacts = [path for path in DEFAULT_ARTIFACTS if path.exists()]
    missing = [str(path.relative_to(REPO_ROOT)) for path in DEFAULT_ARTIFACTS if not path.exists()]
    report = build_report(artifacts)
    report["missing_artifacts"] = missing

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "latest_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, OUT_DIR / "RESULTS.md")

    print(json.dumps({
        "entry_count": report["entry_count"],
        "unique_anchor_values": report["unique_anchor_values"],
        "failed_entries": report["failed_entries"],
        "failed_unique_values": report["failed_unique_values"],
        "max_anchor_value": report["max_anchor_value"],
        "out_dir": str(OUT_DIR.relative_to(REPO_ROOT)),
    }, indent=2))
    return 1 if report["failed_entries"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
