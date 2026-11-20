"""Canonical, fail-closed task artifacts for the Clay VQCC curriculum.

The corpus intake used to retain only aggregate task receipts.  This module
stores the exact comparisons and training-control occurrences that a later
runner may consume.  It performs no training, network access, or provider
mutation.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import findings_task
import vqcc_task


COST_ROW_SCHEMA = "clay.vqcc-task.cost-comparison.v1"
FINDING_ROW_SCHEMA = "clay.vqcc-task.finding-comparison.v1"
FINDING_TRAINING_ROW_SCHEMA = "clay.vqcc-task.finding-training-occurrence.v1"
MANIFEST_SCHEMA = "clay.vqcc-task-manifest.v1"
ROLES = frozenset(("train", "holdout"))
BINDINGS = frozenset(("intact", "shuffled_binding"))

_ROW_FIELDS = frozenset(
    (
        "schema",
        "task_kind",
        "dataset_role",
        "population",
        "binding",
        "source_item_id",
        "payload",
        "prompt",
        "payload_sha256",
        "occurrence_id",
    )
)
_COST_FIELDS = frozenset(
    (
        "pair_id",
        "a_record_id",
        "b_record_id",
        "family_ids",
        "a_opcodes",
        "b_opcodes",
        "a_count",
        "b_count",
        "target",
        "target_source_id",
    )
)
_FINDING_FIELDS = frozenset(
    (
        "comparison_id",
        "question_record_id",
        "family_ids",
        "task",
        "question",
        "a_answer",
        "b_answer",
        "a_source_id",
        "b_source_id",
        "target",
    )
)
_FINDING_TRAINING_FIELDS = frozenset(
    (
        "occurrence_id",
        "arm",
        "base_comparison_id",
        "question_record_id",
        "family_ids",
        "task",
        "question",
        "a_answer",
        "b_answer",
        "a_source_id",
        "b_source_id",
        "a_source_family_id",
        "b_source_family_id",
        "a_bound_record_id",
        "b_bound_record_id",
        "supervision_target",
        "binding_mode",
        "evaluation_eligible",
    )
)


def canonical_json_bytes(value: object, *, newline: bool = False) -> bytes:
    suffix = "\n" if newline else ""
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + suffix
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_lines(values: Iterable[str]) -> str:
    return _sha256("".join(f"{value}\n" for value in sorted(values)).encode("utf-8"))


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant is forbidden: {value}")


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _require_exact_fields(value: Mapping[str, Any], expected: frozenset[str], name: str) -> None:
    observed = set(value)
    if observed != expected:
        raise ValueError(
            f"{name} fields differ: missing={sorted(expected - observed)}, "
            f"extra={sorted(observed - expected)}"
        )


def _require_string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _require_string_list(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"{name} must be a non-empty string array")
    return tuple(value)


def _require_int(value: object, name: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{name} must be an integer")
    return value


def _load_canonical_jsonl(path: Path) -> list[dict[str, Any]]:
    raw = path.read_bytes()
    if not raw or raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw or not raw.endswith(b"\n"):
        raise ValueError(f"task artifact is not canonical LF JSONL: {path}")
    result: list[dict[str, Any]] = []
    for line_number, line in enumerate(raw.splitlines(keepends=True), 1):
        if line == b"\n":
            raise ValueError(f"blank task row at line {line_number}")
        try:
            text = line[:-1].decode("utf-8", errors="strict")
            value = json.loads(
                text,
                object_pairs_hook=_pairs_no_duplicates,
                parse_constant=_reject_constant,
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid task row at line {line_number}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"task row {line_number} is not an object")
        if canonical_json_bytes(value, newline=True) != line:
            raise ValueError(f"task row {line_number} is not canonical JSON")
        result.append(value)
    occurrence_ids = [str(row.get("occurrence_id", "")) for row in result]
    if occurrence_ids != sorted(occurrence_ids) or len(set(occurrence_ids)) != len(occurrence_ids):
        raise ValueError("task occurrence IDs must be unique and strictly sorted")
    return result


def _cost_payload(row: vqcc_task.CostComparison) -> dict[str, Any]:
    return {
        "pair_id": row.pair_id,
        "a_record_id": row.a_record_id,
        "b_record_id": row.b_record_id,
        "family_ids": list(row.family_ids),
        "a_opcodes": list(row.a_opcodes),
        "b_opcodes": list(row.b_opcodes),
        "a_count": row.a_count,
        "b_count": row.b_count,
        "target": row.target,
        "target_source_id": row.target_source_id,
    }


def _finding_payload(row: findings_task.FindingComparison) -> dict[str, Any]:
    return {
        "comparison_id": row.comparison_id,
        "question_record_id": row.question_record_id,
        "family_ids": list(row.family_ids),
        "task": row.task,
        "question": row.question,
        "a_answer": row.a_answer,
        "b_answer": row.b_answer,
        "a_source_id": row.a_source_id,
        "b_source_id": row.b_source_id,
        "target": row.target,
    }


def _finding_training_payload(row: findings_task.FindingTrainingOccurrence) -> dict[str, Any]:
    return {
        "occurrence_id": row.occurrence_id,
        "arm": row.arm,
        "base_comparison_id": row.base_comparison_id,
        "question_record_id": row.question_record_id,
        "family_ids": list(row.family_ids),
        "task": row.task,
        "question": row.question,
        "a_answer": row.a_answer,
        "b_answer": row.b_answer,
        "a_source_id": row.a_source_id,
        "b_source_id": row.b_source_id,
        "a_source_family_id": row.a_source_family_id,
        "b_source_family_id": row.b_source_family_id,
        "a_bound_record_id": row.a_bound_record_id,
        "b_bound_record_id": row.b_bound_record_id,
        "supervision_target": row.supervision_target,
        "binding_mode": row.binding_mode,
        "evaluation_eligible": row.evaluation_eligible,
    }


def _materialized_row(
    *,
    schema: str,
    task_kind: str,
    dataset_role: str,
    population: str,
    binding: str,
    source_item_id: str,
    payload: Mapping[str, Any],
    prompt: str,
) -> dict[str, Any]:
    if dataset_role not in ROLES:
        raise ValueError(f"unsupported dataset role: {dataset_role}")
    if binding not in BINDINGS:
        raise ValueError(f"unsupported task binding: {binding}")
    payload_sha256 = _sha256(canonical_json_bytes({"payload": payload, "prompt": prompt}))
    occurrence_id = _sha256(
        canonical_json_bytes(
            [
                "clay-vqcc-task-occurrence-v1",
                task_kind,
                dataset_role,
                population,
                binding,
                source_item_id,
                payload_sha256,
            ]
        )
    )
    return {
        "schema": schema,
        "task_kind": task_kind,
        "dataset_role": dataset_role,
        "population": population,
        "binding": binding,
        "source_item_id": source_item_id,
        "payload": dict(payload),
        "prompt": prompt,
        "payload_sha256": payload_sha256,
        "occurrence_id": occurrence_id,
    }


def _write_rows(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    ordered = sorted(rows, key=lambda row: str(row["occurrence_id"]))
    if len({str(row["occurrence_id"]) for row in ordered}) != len(ordered):
        raise ValueError("task occurrence IDs must be unique")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        for row in ordered:
            stream.write(canonical_json_bytes(row, newline=True))


def _artifact_receipt(
    path: Path,
    rows: Sequence[Mapping[str, Any]],
    *,
    relative_path: str,
    label_values: Sequence[str],
    task_values: Sequence[str] = (),
    record_values: Sequence[str] = (),
    family_values: Sequence[str] = (),
) -> dict[str, Any]:
    return {
        "relative_path": relative_path,
        "task_schema": rows[0]["schema"],
        "task_kind": rows[0]["task_kind"],
        "dataset_role": rows[0]["dataset_role"],
        "population": rows[0]["population"],
        "binding": rows[0]["binding"],
        "rows": len(rows),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "occurrence_ids_sha256": _sha256_lines(str(row["occurrence_id"]) for row in rows),
        "source_item_ids_sha256": _sha256_lines(str(row["source_item_id"]) for row in rows),
        "payloads_sha256": _sha256_lines(str(row["payload_sha256"]) for row in rows),
        "label_counts": dict(sorted(Counter(label_values).items())),
        "task_counts": dict(sorted(Counter(task_values).items())),
        "unique_records": len(set(record_values)),
        "unique_families": len(set(family_values)),
    }


def write_cost_artifact(
    path: Path,
    rows: Sequence[vqcc_task.CostComparison],
    *,
    relative_path: str,
    dataset_role: str,
    population: str,
    binding: str,
) -> dict[str, Any]:
    require_true = binding == "intact"
    require_balanced = population == "balanced"
    if population not in {"balanced", "natural_prevalence"}:
        raise ValueError(f"unsupported cost population: {population}")
    if population == "natural_prevalence" and binding != "intact":
        raise ValueError("natural-prevalence cost rows must keep intact bindings")
    vqcc_task.validate_task_set(
        rows,
        require_balanced=require_balanced,
        max_record_reuse=1,
        require_true_target=require_true,
    )
    materialized = [
        _materialized_row(
            schema=COST_ROW_SCHEMA,
            task_kind="gate_count",
            dataset_role=dataset_role,
            population=population,
            binding=binding,
            source_item_id=row.pair_id,
            payload=_cost_payload(row),
            prompt=row.prompt,
        )
        for row in rows
    ]
    _write_rows(path, materialized)
    return _artifact_receipt(
        path,
        materialized,
        relative_path=relative_path,
        label_values=[row.target for row in rows],
        record_values=[record for row in rows for record in (row.a_record_id, row.b_record_id)],
        family_values=[family for row in rows for family in row.family_ids],
    )


def write_finding_artifact(
    path: Path,
    rows: Sequence[findings_task.FindingComparison],
    *,
    relative_path: str,
    dataset_role: str,
) -> dict[str, Any]:
    findings_task.validate_finding_comparisons(rows)
    materialized = [
        _materialized_row(
            schema=FINDING_ROW_SCHEMA,
            task_kind="finding_binding",
            dataset_role=dataset_role,
            population="paired_symmetric",
            binding="intact",
            source_item_id=row.comparison_id,
            payload=_finding_payload(row),
            prompt=row.prompt,
        )
        for row in rows
    ]
    _write_rows(path, materialized)
    return _artifact_receipt(
        path,
        materialized,
        relative_path=relative_path,
        label_values=[row.target for row in rows],
        task_values=[row.task for row in rows],
        record_values=[
            record
            for row in rows
            for record in (row.question_record_id, row.a_source_id, row.b_source_id)
        ],
        family_values=[family for row in rows for family in row.family_ids],
    )


def write_finding_training_artifact(
    path: Path,
    rows: Sequence[findings_task.FindingTrainingOccurrence],
    *,
    relative_path: str,
    dataset_role: str,
    binding: str,
) -> dict[str, Any]:
    if dataset_role != "train":
        raise ValueError("finding training occurrences are train-only")
    expected_arm = "candidate" if binding == "intact" else "shuffled_binding"
    if {row.arm for row in rows} != {expected_arm}:
        raise ValueError("finding training arm differs from artifact binding")
    materialized = [
        _materialized_row(
            schema=FINDING_TRAINING_ROW_SCHEMA,
            task_kind="finding_binding",
            dataset_role=dataset_role,
            population="paired_symmetric_training",
            binding=binding,
            source_item_id=row.base_comparison_id,
            payload=_finding_training_payload(row),
            prompt=row.prompt,
        )
        for row in rows
    ]
    _write_rows(path, materialized)
    return _artifact_receipt(
        path,
        materialized,
        relative_path=relative_path,
        label_values=[row.supervision_target for row in rows],
        task_values=[row.task for row in rows],
        record_values=[
            record
            for row in rows
            for record in (
                row.question_record_id,
                row.a_source_id,
                row.b_source_id,
                row.a_bound_record_id,
                row.b_bound_record_id,
            )
        ],
        family_values=[
            family
            for row in rows
            for family in (*row.family_ids, row.a_source_family_id, row.b_source_family_id)
        ],
    )


def _verify_materialized_row(
    row: Mapping[str, Any],
    *,
    schema: str,
    task_kind: str,
    dataset_role: str,
    population: str,
    binding: str,
) -> Mapping[str, Any]:
    _require_exact_fields(row, _ROW_FIELDS, "task row")
    expected = {
        "schema": schema,
        "task_kind": task_kind,
        "dataset_role": dataset_role,
        "population": population,
        "binding": binding,
    }
    if any(row.get(key) != value for key, value in expected.items()):
        raise ValueError(f"task row metadata differs from artifact contract: {row.get('occurrence_id')}")
    source_item_id = _require_string(row.get("source_item_id"), "source_item_id")
    prompt = _require_string(row.get("prompt"), "prompt")
    payload = row.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("task payload must be an object")
    payload_sha256 = _sha256(canonical_json_bytes({"payload": payload, "prompt": prompt}))
    if row.get("payload_sha256") != payload_sha256:
        raise ValueError("task payload SHA-256 differs")
    expected_id = _materialized_row(
        schema=schema,
        task_kind=task_kind,
        dataset_role=dataset_role,
        population=population,
        binding=binding,
        source_item_id=source_item_id,
        payload=payload,
        prompt=prompt,
    )["occurrence_id"]
    if row.get("occurrence_id") != expected_id:
        raise ValueError("task occurrence identity differs")
    return payload


def load_cost_artifact(
    path: Path,
    *,
    dataset_role: str,
    population: str,
    binding: str,
) -> list[vqcc_task.CostComparison]:
    result: list[vqcc_task.CostComparison] = []
    for materialized in _load_canonical_jsonl(path):
        payload = _verify_materialized_row(
            materialized,
            schema=COST_ROW_SCHEMA,
            task_kind="gate_count",
            dataset_role=dataset_role,
            population=population,
            binding=binding,
        )
        _require_exact_fields(payload, _COST_FIELDS, "cost payload")
        opcodes_a = payload["a_opcodes"]
        opcodes_b = payload["b_opcodes"]
        if (
            not isinstance(opcodes_a, list)
            or not isinstance(opcodes_b, list)
            or any(type(value) is not int for value in (*opcodes_a, *opcodes_b))
        ):
            raise ValueError("cost opcodes must be integer arrays")
        row = vqcc_task.CostComparison(
            pair_id=_require_string(payload["pair_id"], "pair_id"),
            a_record_id=_require_string(payload["a_record_id"], "a_record_id"),
            b_record_id=_require_string(payload["b_record_id"], "b_record_id"),
            family_ids=_require_string_list(payload["family_ids"], "family_ids"),
            a_opcodes=tuple(opcodes_a),
            b_opcodes=tuple(opcodes_b),
            a_count=_require_int(payload["a_count"], "a_count"),
            b_count=_require_int(payload["b_count"], "b_count"),
            target=_require_string(payload["target"], "target"),
            target_source_id=_require_string(payload["target_source_id"], "target_source_id"),
        )
        if materialized["source_item_id"] != row.pair_id or materialized["prompt"] != row.prompt:
            raise ValueError("cost source identity or prompt differs")
        result.append(row)
    vqcc_task.validate_task_set(
        result,
        require_balanced=population == "balanced",
        max_record_reuse=1,
        require_true_target=binding == "intact",
    )
    return result


def load_finding_artifact(path: Path, *, dataset_role: str) -> list[findings_task.FindingComparison]:
    result: list[findings_task.FindingComparison] = []
    for materialized in _load_canonical_jsonl(path):
        payload = _verify_materialized_row(
            materialized,
            schema=FINDING_ROW_SCHEMA,
            task_kind="finding_binding",
            dataset_role=dataset_role,
            population="paired_symmetric",
            binding="intact",
        )
        _require_exact_fields(payload, _FINDING_FIELDS, "finding payload")
        row = findings_task.FindingComparison(
            comparison_id=_require_string(payload["comparison_id"], "comparison_id"),
            question_record_id=_require_string(payload["question_record_id"], "question_record_id"),
            family_ids=_require_string_list(payload["family_ids"], "family_ids"),
            task=_require_string(payload["task"], "task"),
            question=_require_string(payload["question"], "question"),
            a_answer=_require_string(payload["a_answer"], "a_answer"),
            b_answer=_require_string(payload["b_answer"], "b_answer"),
            a_source_id=_require_string(payload["a_source_id"], "a_source_id"),
            b_source_id=_require_string(payload["b_source_id"], "b_source_id"),
            target=_require_string(payload["target"], "target"),
        )
        if materialized["source_item_id"] != row.comparison_id or materialized["prompt"] != row.prompt:
            raise ValueError("finding source identity or prompt differs")
        matched = findings_task._QUESTION.fullmatch(row.question)
        if matched is None or matched.group("task") != row.task:
            raise ValueError("finding question task differs from its payload")
        result.append(row)
    findings_task.validate_finding_comparisons(result)
    return result


def load_finding_training_artifact(
    path: Path,
    *,
    dataset_role: str,
    binding: str,
    comparisons: Sequence[findings_task.FindingComparison],
    examples: Sequence[findings_task.FindingExample],
    length_bucket_width: int,
) -> list[findings_task.FindingTrainingOccurrence]:
    result: list[findings_task.FindingTrainingOccurrence] = []
    for materialized in _load_canonical_jsonl(path):
        payload = _verify_materialized_row(
            materialized,
            schema=FINDING_TRAINING_ROW_SCHEMA,
            task_kind="finding_binding",
            dataset_role=dataset_role,
            population="paired_symmetric_training",
            binding=binding,
        )
        _require_exact_fields(payload, _FINDING_TRAINING_FIELDS, "finding training payload")
        if type(payload["evaluation_eligible"]) is not bool:
            raise ValueError("evaluation_eligible must be boolean")
        row = findings_task.FindingTrainingOccurrence(
            occurrence_id=_require_string(payload["occurrence_id"], "occurrence_id"),
            arm=_require_string(payload["arm"], "arm"),
            base_comparison_id=_require_string(payload["base_comparison_id"], "base_comparison_id"),
            question_record_id=_require_string(payload["question_record_id"], "question_record_id"),
            family_ids=_require_string_list(payload["family_ids"], "family_ids"),
            task=_require_string(payload["task"], "task"),
            question=_require_string(payload["question"], "question"),
            a_answer=_require_string(payload["a_answer"], "a_answer"),
            b_answer=_require_string(payload["b_answer"], "b_answer"),
            a_source_id=_require_string(payload["a_source_id"], "a_source_id"),
            b_source_id=_require_string(payload["b_source_id"], "b_source_id"),
            a_source_family_id=_require_string(payload["a_source_family_id"], "a_source_family_id"),
            b_source_family_id=_require_string(payload["b_source_family_id"], "b_source_family_id"),
            a_bound_record_id=_require_string(payload["a_bound_record_id"], "a_bound_record_id"),
            b_bound_record_id=_require_string(payload["b_bound_record_id"], "b_bound_record_id"),
            supervision_target=_require_string(payload["supervision_target"], "supervision_target"),
            binding_mode=_require_string(payload["binding_mode"], "binding_mode"),
            evaluation_eligible=payload["evaluation_eligible"],
        )
        if materialized["source_item_id"] != row.base_comparison_id or materialized["prompt"] != row.prompt:
            raise ValueError("finding training source identity or prompt differs")
        result.append(row)
    findings_task.validate_finding_training_occurrences(
        result,
        comparisons=comparisons,
        examples=examples,
        length_bucket_width=length_bucket_width,
    )
    return result


def write_task_manifest(
    tasks_dir: Path,
    artifacts: Sequence[Mapping[str, Any]],
    *,
    authorities: Mapping[str, Any],
) -> dict[str, Any]:
    manifest_path = tasks_dir / "TASK_MANIFEST.json"
    if manifest_path.exists():
        raise FileExistsError(f"refusing to overwrite task manifest: {manifest_path}")
    ordered = sorted((dict(item) for item in artifacts), key=lambda item: item["relative_path"])
    relative_paths = [str(item["relative_path"]) for item in ordered]
    if len(set(relative_paths)) != len(relative_paths):
        raise ValueError("task artifact paths must be unique")
    for relative in relative_paths:
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != relative:
            raise ValueError(f"unsafe task artifact path: {relative}")
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "status": "MATERIALIZED_PREPARED_ONLY",
        "authorities": dict(authorities),
        "artifacts": ordered,
        "content_set_sha256": _sha256(canonical_json_bytes(ordered)),
    }
    tasks_dir.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("xb") as stream:
        stream.write(canonical_json_bytes(manifest, newline=True))
    verify_task_manifest(tasks_dir)
    return manifest


def verify_task_manifest(tasks_dir: Path) -> dict[str, Any]:
    manifest_path = tasks_dir / "TASK_MANIFEST.json"
    rows = _load_canonical_jsonl(manifest_path)
    if len(rows) != 1:
        raise ValueError("task manifest must contain exactly one JSON object")
    manifest = rows[0]
    expected_fields = frozenset(("schema", "status", "authorities", "artifacts", "content_set_sha256"))
    _require_exact_fields(manifest, expected_fields, "task manifest")
    if manifest["schema"] != MANIFEST_SCHEMA or manifest["status"] != "MATERIALIZED_PREPARED_ONLY":
        raise ValueError("task manifest schema or status differs")
    artifacts = manifest["artifacts"]
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("task manifest artifacts must be a non-empty array")
    if manifest["content_set_sha256"] != _sha256(canonical_json_bytes(artifacts)):
        raise ValueError("task manifest content-set hash differs")
    expected_files = {"TASK_MANIFEST.json"}
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise ValueError("task manifest artifact is not an object")
        relative = _require_string(artifact.get("relative_path"), "relative_path")
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != relative:
            raise ValueError(f"unsafe task artifact path: {relative}")
        actual = tasks_dir / path
        expected_files.add(relative)
        if (
            not actual.is_file()
            or actual.stat().st_size != artifact.get("bytes")
            or sha256_file(actual) != artifact.get("sha256")
        ):
            raise ValueError(f"task artifact differs from manifest: {relative}")
        loaded = _load_canonical_jsonl(actual)
        if len(loaded) != artifact.get("rows"):
            raise ValueError(f"task artifact row count differs: {relative}")
        if _sha256_lines(str(row["occurrence_id"]) for row in loaded) != artifact.get(
            "occurrence_ids_sha256"
        ):
            raise ValueError(f"task artifact occurrence IDs differ: {relative}")
    observed_files = {
        path.relative_to(tasks_dir).as_posix() for path in tasks_dir.rglob("*") if path.is_file()
    }
    if observed_files != expected_files:
        raise ValueError(
            f"task artifact inventory differs: missing={sorted(expected_files - observed_files)}, "
            f"extra={sorted(observed_files - expected_files)}"
        )
    return manifest
