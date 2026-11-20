"""Prepare a sealed VQCC curriculum intake without training or cloud mutation.

The runner is intentionally limited to read-only corpus verification and bounded
local artifacts.  It stages a family split, deterministic train/holdout samples,
and task-construction receipts under a temporary sibling directory.  The caller's
output path appears only after every integrity, coverage, and leakage check passes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

import build_vqcc_split
import findings_task
import vqcc_task
from load_vqcc_corpus import (
    DATASET_ID,
    DATASET_VERSION,
    SampleConfig,
    sample_corpus,
    write_sample,
)


SPEC_SCHEMA = "clay.vqcc-curriculum.campaign-spec.v1"
RECEIPT_SCHEMA = "clay.vqcc-curriculum.readonly-intake.v1"
SHA256_HEX_LENGTH = 64
ROLES = ("train", "holdout")
CAMPAIGN_LANES = frozenset(("public.experimental_findings", "public.gate_count"))
AUTHORITY_FIELDS = (
    "execution_authorized",
    "training_authorized",
    "cloud_mutation_authorized",
    "checkpoint_promotion_authorized",
    "competition_submission_authorized",
)


def _sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _sha256_lines(values: Sequence[str]) -> str:
    payload = "".join(f"{value}\n" for value in sorted(values)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == SHA256_HEX_LENGTH
        and all(character in "0123456789abcdef" for character in value)
    )


def _require_mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


def _require_int(value: object, name: str, *, positive: bool = False) -> int:
    if type(value) is not int or (positive and value <= 0):
        qualifier = "positive " if positive else ""
        raise ValueError(f"{name} must be a {qualifier}integer")
    return value


def _load_and_validate_spec(spec_path: Path, expected_spec_sha256: str) -> tuple[dict[str, Any], str]:
    if not _is_sha256(expected_spec_sha256):
        raise ValueError("expected spec SHA-256 must be 64 lowercase hexadecimal characters")
    raw = spec_path.read_bytes()
    actual_sha256 = hashlib.sha256(raw).hexdigest()
    if actual_sha256 != expected_spec_sha256:
        raise ValueError(
            f"Campaign spec hash differs: expected {expected_spec_sha256}, got {actual_sha256}"
        )
    try:
        spec = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Campaign spec is not valid UTF-8 JSON") from exc
    if not isinstance(spec, dict) or spec.get("schema") != SPEC_SCHEMA:
        raise ValueError(f"Unexpected campaign spec schema: {spec.get('schema')!r}")
    if spec.get("status") != "PREPARED_ONLY":
        raise ValueError("Campaign spec must remain PREPARED_ONLY")
    enabled = [name for name in AUTHORITY_FIELDS if spec.get(name) is not False]
    if enabled:
        raise ValueError(f"Prepared intake rejects authority-bearing fields: {enabled}")

    dataset = _require_mapping(spec.get("dataset"), "dataset")
    if dataset.get("id") != DATASET_ID or dataset.get("version") != DATASET_VERSION:
        raise ValueError("Campaign dataset identity differs from the pinned loader identity")
    if not _is_sha256(dataset.get("manifest_sha256")):
        raise ValueError("dataset.manifest_sha256 must be a lowercase SHA-256")
    counts = _require_mapping(dataset.get("counts"), "dataset.counts")
    if set(counts) != {"train", "holdout", "ordinary", "retention"}:
        raise ValueError("dataset.counts must contain exactly train/holdout/ordinary/retention")
    for name, value in counts.items():
        _require_int(value, f"dataset.counts.{name}")
        if value < 0:
            raise ValueError(f"dataset.counts.{name} must be nonnegative")
    if counts["train"] <= 0:
        raise ValueError("dataset.counts.train must be positive")

    split = _require_mapping(spec.get("campaign_split"), "campaign_split")
    if not isinstance(split.get("seed"), str) or not split["seed"]:
        raise ValueError("campaign_split.seed must be a nonempty string")
    fraction = split.get("holdout_fraction")
    if type(fraction) not in (int, float) or not 0 < float(fraction) < 1:
        raise ValueError("campaign_split.holdout_fraction must lie strictly between zero and one")
    if split.get("unit") != "transitive_source_family":
        raise ValueError("campaign_split.unit must be transitive_source_family")
    if split.get("required_roles") != list(ROLES):
        raise ValueError(f"campaign_split.required_roles must equal {list(ROLES)}")

    sampling = _require_mapping(spec.get("sampling"), "sampling")
    if set(sampling) != {*ROLES, "token_proxy"}:
        raise ValueError("sampling must contain exactly train, holdout, and token_proxy")
    if sampling.get("token_proxy") != "utf8_bytes_plus_3_special_tokens":
        raise ValueError("sampling.token_proxy differs from the implemented loader proxy")
    for role in ROLES:
        config = _require_mapping(sampling.get(role), f"sampling.{role}")
        if set(config) != {
            "seed",
            "lane_caps",
            "max_chars_per_record",
            "max_tokens_per_record",
            "total_token_budget",
        }:
            raise ValueError(f"sampling.{role} contains missing or unknown fields")
        _require_int(config.get("seed"), f"sampling.{role}.seed")
        lanes = _require_mapping(config.get("lane_caps"), f"sampling.{role}.lane_caps")
        if set(lanes) != CAMPAIGN_LANES:
            raise ValueError(f"sampling.{role}.lane_caps must cover exactly {sorted(CAMPAIGN_LANES)}")
        for lane, cap in lanes.items():
            _require_int(cap, f"sampling.{role}.lane_caps.{lane}", positive=True)
        for field in ("max_chars_per_record", "max_tokens_per_record", "total_token_budget"):
            _require_int(config.get(field), f"sampling.{role}.{field}", positive=True)

    builders = _require_mapping(spec.get("task_builders"), "task_builders")
    if set(builders) != {"gate_count", "finding_binding"}:
        raise ValueError("task_builders must contain exactly gate_count and finding_binding")
    gate = _require_mapping(builders.get("gate_count"), "task_builders.gate_count")
    finding = _require_mapping(builders.get("finding_binding"), "task_builders.finding_binding")
    for role in ROLES:
        _require_int(gate.get(f"{role}_seed"), f"task_builders.gate_count.{role}_seed")
        _require_int(finding.get(f"{role}_seed"), f"task_builders.finding_binding.{role}_seed")
    gaps = gate.get("gap_strata")
    if (
        not isinstance(gaps, list)
        or not gaps
        or any(type(gap) is not int or gap <= 0 for gap in gaps)
        or len(set(gaps)) != len(gaps)
    ):
        raise ValueError("task_builders.gate_count.gap_strata must be distinct positive integers")
    if gate.get("balanced_labels") != list(vqcc_task.LABELS):
        raise ValueError("gate-count balanced labels differ from the implemented task")
    if gate.get("natural_prevalence_evaluation") is not True:
        raise ValueError("natural-prevalence gate-count evaluation must remain enabled")
    if finding.get("balanced_labels") != list(findings_task.LABELS):
        raise ValueError("finding balanced labels differ from the implemented task")
    if finding.get("aligned_training_helper") != "findings_task.aligned_findings_training_arms":
        raise ValueError("finding aligned-training helper differs from the implemented helper")
    _require_int(
        finding.get("length_bucket_width"),
        "task_builders.finding_binding.length_bucket_width",
        positive=True,
    )
    required_tasks = finding.get("required_evaluation_tasks")
    if not isinstance(required_tasks, list) or set(required_tasks) != set(findings_task.TASKS):
        raise ValueError("finding required evaluation tasks differ from the implemented task set")
    if len(required_tasks) != len(set(required_tasks)):
        raise ValueError("finding required evaluation tasks contain duplicates")

    training = _require_mapping(spec.get("training"), "training")
    for field in ("runner", "steps", "runtime_cap_seconds"):
        if training.get(field) is not None:
            raise ValueError(f"training.{field} must remain null in a prepared-only intake")
    return spec, actual_sha256


def _sample_config(spec: Mapping[str, Any], role: str) -> SampleConfig:
    raw = spec["sampling"][role]
    return SampleConfig(
        lane_caps=dict(raw["lane_caps"]),
        seed=raw["seed"],
        max_chars_per_record=raw["max_chars_per_record"],
        max_tokens_per_record=raw["max_tokens_per_record"],
        total_token_budget=raw["total_token_budget"],
        campaign_role=role,
    )


def _selected_assignments(
    assignments_path: Path, selected_ids: set[str]
) -> dict[str, dict[str, Any]]:
    assignments: dict[str, dict[str, Any]] = {}
    with assignments_path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid split assignment JSON at line {line_number}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"Non-object split assignment at line {line_number}")
            record_id = row.get("record_id")
            if record_id in selected_ids:
                if record_id in assignments:
                    raise ValueError(f"Duplicate selected split assignment: {record_id}")
                assignments[str(record_id)] = row
    missing = sorted(selected_ids - set(assignments))
    if missing:
        raise ValueError(f"Selected rows lack split assignments: {missing[:5]}")
    return assignments


def _task_id_receipt(ids: Sequence[str]) -> dict[str, Any]:
    return {"rows": len(ids), "ids_sha256": _sha256_lines(ids)}


def _finding_task_receipt(rows: Sequence[findings_task.FindingComparison]) -> dict[str, Any]:
    ids = [row.comparison_id for row in rows]
    return {
        **_task_id_receipt(ids),
        "label_counts": dict(sorted(Counter(row.target for row in rows).items())),
        "task_counts": dict(sorted(Counter(row.task for row in rows).items())),
        "unique_records": len(
            {
                record_id
                for row in rows
                for record_id in (row.question_record_id, row.a_source_id, row.b_source_id)
            }
        ),
        "unique_families": len({family for row in rows for family in row.family_ids}),
    }


def _assert_sample_disjoint(
    samples: Mapping[str, Sequence[Mapping[str, Any]]],
    assignments: Mapping[str, Mapping[str, Any]],
) -> dict[str, int]:
    records: dict[str, set[str]] = {}
    families: dict[str, set[str]] = {}
    for role in ROLES:
        role_records = {str(row["record_id"]) for row in samples[role]}
        role_families: set[str] = set()
        for record_id in role_records:
            assignment = assignments[record_id]
            if assignment.get("split") != role:
                raise ValueError(f"Selected row {record_id} is assigned to {assignment.get('split')!r}, not {role}")
            family = assignment.get("family")
            if not isinstance(family, str) or not family:
                raise ValueError(f"Selected row {record_id} lacks a family")
            role_families.add(family)
        records[role] = role_records
        families[role] = role_families
    record_overlap = records["train"] & records["holdout"]
    family_overlap = families["train"] & families["holdout"]
    if record_overlap or family_overlap:
        raise ValueError(
            "sample train/holdout leakage: "
            f"families={sorted(family_overlap)}, records={sorted(record_overlap)}"
        )
    return {"source_family_overlap": 0, "record_id_overlap": 0}


def run_readonly_intake(
    corpus_root: str | Path,
    output_dir: str | Path,
    *,
    spec_path: str | Path,
    expected_spec_sha256: str,
) -> dict[str, Any]:
    """Build a prepared-only intake atomically under ``output_dir``."""

    corpus_root = Path(corpus_root).resolve(strict=True)
    spec_path = Path(spec_path).resolve(strict=True)
    output_dir = Path(output_dir).resolve()
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite immutable intake output: {output_dir}")
    if output_dir == corpus_root or corpus_root in output_dir.parents:
        raise ValueError("output_dir must not be the corpus root or a descendant of it")
    spec, spec_sha256 = _load_and_validate_spec(spec_path, expected_spec_sha256)
    manifest_sha256 = spec["dataset"]["manifest_sha256"]
    expected_counts = dict(spec["dataset"]["counts"])

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    prefix = f".{output_dir.name}.tmp-"
    staging = Path(tempfile.mkdtemp(prefix=prefix, dir=output_dir.parent)).resolve()
    try:
        split_dir = staging / "campaign-split"
        split_receipt = build_vqcc_split.build_split(
            corpus_root,
            split_dir,
            expected_manifest_sha256=manifest_sha256,
            seed=spec["campaign_split"]["seed"],
            holdout_fraction=float(spec["campaign_split"]["holdout_fraction"]),
        )
        assignments_path = split_dir / "row-assignments.jsonl"
        assignments_sha256 = split_receipt["artifacts"][assignments_path.name]
        if _sha256_file(assignments_path) != assignments_sha256:
            raise ValueError("row-assignment sidecar differs from the split receipt")

        samples: dict[str, Any] = {}
        samples_dir = staging / "samples"
        for role in ROLES:
            result = sample_corpus(
                corpus_root,
                _sample_config(spec, role),
                assignments_path=assignments_path,
                expected_assignments_sha256=assignments_sha256,
                expected_manifest_sha256=manifest_sha256,
                expected_counts=expected_counts,
            )
            write_sample(
                result,
                samples_dir / f"{role}.jsonl",
                samples_dir / f"{role}.receipt.json",
            )
            samples[role] = result

        selected_ids = {
            str(row["record_id"])
            for role in ROLES
            for row in samples[role].rows
        }
        assignments = _selected_assignments(assignments_path, selected_ids)
        sample_invariants = _assert_sample_disjoint(
            {role: samples[role].rows for role in ROLES}, assignments
        )

        gate_examples: dict[str, list[vqcc_task.GateCountExample]] = {}
        finding_examples: dict[str, list[findings_task.FindingExample]] = {}
        for role in ROLES:
            gate_examples[role] = [
                vqcc_task.parse_gate_count_row(
                    row, family_id=str(assignments[str(row["record_id"])]["family"])
                )
                for row in samples[role].rows
                if row["lane"] == "public.gate_count"
            ]
            finding_examples[role] = [
                findings_task.parse_finding_row(
                    row, family_id=str(assignments[str(row["record_id"])]["family"])
                )
                for row in samples[role].rows
                if row["lane"] == "public.experimental_findings"
            ]

        gate_spec = spec["task_builders"]["gate_count"]
        finding_spec = spec["task_builders"]["finding_binding"]
        gate_balanced: dict[str, list[vqcc_task.CostComparison]] = {}
        gate_natural: dict[str, list[vqcc_task.CostComparison]] = {}
        finding_comparisons: dict[str, list[findings_task.FindingComparison]] = {}
        aligned_train, shuffled_train = findings_task.aligned_findings_training_arms(
            finding_examples["train"],
            seed=finding_spec["train_seed"],
            length_bucket_width=finding_spec["length_bucket_width"],
        )
        if [row.record_id for row in aligned_train] != [row.record_id for row in shuffled_train]:
            raise AssertionError("aligned finding training arms differ in retained record order")
        for role in ROLES:
            gate_balanced[role] = vqcc_task.build_balanced_comparisons(
                gate_examples[role],
                seed=gate_spec[f"{role}_seed"],
                gap_strata=tuple(gate_spec["gap_strata"]),
            )
            gate_natural[role] = vqcc_task.build_natural_prevalence_comparisons(
                gate_examples[role], seed=gate_spec[f"{role}_seed"]
            )
            finding_comparisons[role] = findings_task.build_finding_comparisons(
                finding_examples[role],
                seed=finding_spec[f"{role}_seed"],
                length_bucket_width=finding_spec["length_bucket_width"],
            )
            observed_tasks = {row.task for row in finding_comparisons[role]}
            required_tasks = set(finding_spec["required_evaluation_tasks"])
            if observed_tasks != required_tasks:
                raise ValueError(
                    f"{role} finding task coverage differs: "
                    f"expected={sorted(required_tasks)}, observed={sorted(observed_tasks)}"
                )

        vqcc_task.validate_family_disjoint(gate_balanced["train"], gate_balanced["holdout"])
        findings_task.validate_family_disjoint(
            finding_comparisons["train"], finding_comparisons["holdout"]
        )

        sample_receipts = {
            role: {
                "rows_file": f"samples/{role}.jsonl",
                "rows_sha256": _sha256_file(samples_dir / f"{role}.jsonl"),
                "receipt_file": f"samples/{role}.receipt.json",
                "receipt_sha256": _sha256_file(samples_dir / f"{role}.receipt.json"),
                "rows": samples[role].receipt["selection"]["rows"],
                "selected_by_lane": samples[role].receipt["selection"]["selected_by_lane"],
            }
            for role in ROLES
        }
        task_receipts = {
            role: {
                "gate_count": {
                    "parsed_examples": len(gate_examples[role]),
                    "balanced": {
                        **vqcc_task.task_set_report(gate_balanced[role]),
                        "ids_sha256": _sha256_lines(
                            [row.pair_id for row in gate_balanced[role]]
                        ),
                    },
                    "natural_prevalence": {
                        **vqcc_task.task_set_report(gate_natural[role]),
                        "ids_sha256": _sha256_lines(
                            [row.pair_id for row in gate_natural[role]]
                        ),
                    },
                },
                "finding_binding": {
                    "parsed_examples": len(finding_examples[role]),
                    "comparisons": _finding_task_receipt(finding_comparisons[role]),
                },
            }
            for role in ROLES
        }
        task_receipts["train"]["finding_binding"]["aligned_training_arms"] = {
            "retained_records": len(aligned_train),
            "record_ids_sha256": _sha256_lines([row.record_id for row in aligned_train]),
            "shuffled_binding_sha256": _sha256_lines(
                [
                    f"{row.record_id}\t{row.answer_source_id}"
                    for row in shuffled_train
                ]
            ),
        }

        receipt: dict[str, Any] = {
            "schema": RECEIPT_SCHEMA,
            "status": "PASS_PREPARED_ONLY",
            "mode": {
                "training": False,
                "cloud_or_kaggle_execution": False,
                "dataset_mutation": False,
                "competition_submission": False,
            },
            "campaign_spec": {
                "file": spec_path.name,
                "sha256": spec_sha256,
                "schema": spec["schema"],
                "status": spec["status"],
            },
            "dataset": {
                "id": spec["dataset"]["id"],
                "version": spec["dataset"]["version"],
                "manifest_sha256": manifest_sha256,
                "counts": expected_counts,
            },
            "campaign_split": {
                "directory": "campaign-split",
                "manifest_sha256": _sha256_file(split_dir / "SPLIT_MANIFEST.json"),
                "row_assignments_sha256": assignments_sha256,
                "family_assignments_sha256": split_receipt["artifacts"]["family-assignments.jsonl"],
                "counts": split_receipt["counts"],
            },
            "samples": sample_receipts,
            "tasks": task_receipts,
            "invariants": {
                **sample_invariants,
                "gate_task_family_and_record_overlap": 0,
                "finding_task_family_and_record_overlap": 0,
                "required_finding_task_coverage": True,
                "manifest_and_consumed_files_verified": True,
                "failure_atomic_output": True,
            },
            "nonclaims": list(spec.get("nonclaims", [])),
        }
        # JSON round-tripping converts integer histogram keys to their stable
        # on-disk representation before the caller sees the receipt.
        receipt = json.loads(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
        _write_json(staging / "INTAKE_RECEIPT.json", receipt)
        staging.rename(output_dir)
        return receipt
    except BaseException:
        if staging.exists() and staging.parent == output_dir.parent and staging.name.startswith(prefix):
            shutil.rmtree(staging)
        raise


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus_root", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--expected-spec-sha256", required=True)
    args = parser.parse_args(argv)
    receipt = run_readonly_intake(
        args.corpus_root,
        args.output_dir,
        spec_path=args.spec,
        expected_spec_sha256=args.expected_spec_sha256,
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
