from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0.0"
TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")


class PersonaDatasetError(ValueError):
    pass


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise PersonaDatasetError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        if not isinstance(record, dict):
            raise PersonaDatasetError(f"{path}:{line_no}: record must be a JSON object")
        records.append(record)
    return records


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def _require_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PersonaDatasetError(f"{field_name} must be a non-empty string")
    return value.strip()


def _require_list(value: Any, field_name: str) -> list[Any]:
    if not isinstance(value, list) or not value:
        raise PersonaDatasetError(f"{field_name} must be a non-empty list")
    return value


def _normalize_axis(axis: dict[str, Any], field_name: str) -> dict[str, Any]:
    required = ("axis", "framework", "sign", "magnitude", "trend", "confidence")
    missing = [key for key in required if key not in axis]
    if missing:
        raise PersonaDatasetError(f"{field_name} missing required keys: {', '.join(missing)}")

    sign = axis["sign"]
    trend = axis["trend"]
    magnitude = axis["magnitude"]
    confidence = axis["confidence"]

    if sign not in (-1, 0, 1):
        raise PersonaDatasetError(f"{field_name}.sign must be one of -1, 0, 1")
    if trend not in (-1, 0, 1):
        raise PersonaDatasetError(f"{field_name}.trend must be one of -1, 0, 1")
    if not isinstance(magnitude, (int, float)) or not 0 <= float(magnitude) <= 1:
        raise PersonaDatasetError(f"{field_name}.magnitude must be a number in [0,1]")
    if not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
        raise PersonaDatasetError(f"{field_name}.confidence must be a number in [0,1]")

    normalized = {
        "axis": _require_string(axis["axis"], f"{field_name}.axis"),
        "framework": _require_string(axis["framework"], f"{field_name}.framework"),
        "sign": int(sign),
        "magnitude": float(magnitude),
        "trend": int(trend),
        "confidence": float(confidence),
    }
    rationale = axis.get("rationale")
    if rationale is not None:
        normalized["rationale"] = _require_string(rationale, f"{field_name}.rationale")
    return normalized


def _normalize_evidence_span(span: dict[str, Any], field_name: str) -> dict[str, Any]:
    normalized = {
        "source_ref": _require_string(span.get("source_ref"), f"{field_name}.source_ref"),
        "kind": _require_string(span.get("kind"), f"{field_name}.kind"),
        "text": _require_string(span.get("text"), f"{field_name}.text"),
    }
    if "weight" in span:
        weight = span["weight"]
        if not isinstance(weight, (int, float)) or not 0 <= float(weight) <= 1:
            raise PersonaDatasetError(f"{field_name}.weight must be a number in [0,1]")
        normalized["weight"] = float(weight)
    if "tongues" in span:
        tongues = span["tongues"]
        if not isinstance(tongues, list):
            raise PersonaDatasetError(f"{field_name}.tongues must be a list")
        for tongue in tongues:
            if tongue not in TONGUES:
                raise PersonaDatasetError(f"{field_name}.tongues contains unsupported tongue '{tongue}'")
        normalized["tongues"] = tongues
    if "tags" in span:
        tags = span["tags"]
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise PersonaDatasetError(f"{field_name}.tags must be a list of strings")
        normalized["tags"] = tags
    return normalized


def _normalize_reflection_block(block: dict[str, Any], field_name: str) -> dict[str, Any]:
    claims = block.get("claims", [])
    evidence_refs = block.get("evidence_refs", [])
    if not isinstance(claims, list) or not claims or not all(isinstance(item, str) and item.strip() for item in claims):
        raise PersonaDatasetError(f"{field_name}.claims must be a non-empty list of strings")
    if not isinstance(evidence_refs, list) or not evidence_refs or not all(
        isinstance(item, str) and item.strip() for item in evidence_refs
    ):
        raise PersonaDatasetError(f"{field_name}.evidence_refs must be a non-empty list of strings")
    return {
        "lens": _require_string(block.get("lens"), f"{field_name}.lens"),
        "summary": _require_string(block.get("summary"), f"{field_name}.summary"),
        "claims": [item.strip() for item in claims],
        "evidence_refs": [item.strip() for item in evidence_refs],
    }


def _normalize_region_anchor(anchor: dict[str, Any], field_name: str) -> dict[str, Any]:
    weight = anchor.get("weight")
    if not isinstance(weight, (int, float)) or not 0 <= float(weight) <= 1:
        raise PersonaDatasetError(f"{field_name}.weight must be a number in [0,1]")
    normalized = {
        "brain_block": _require_string(anchor.get("brain_block"), f"{field_name}.brain_block"),
        "weight": float(weight),
    }
    polyhedron = anchor.get("polyhedron")
    if polyhedron is not None:
        normalized["polyhedron"] = _require_string(polyhedron, f"{field_name}.polyhedron")
    notes = anchor.get("notes")
    if notes is not None:
        normalized["notes"] = _require_string(notes, f"{field_name}.notes")
    return normalized


def _normalize_costs(costs: dict[str, Any], field_name: str) -> dict[str, dict[str, float]]:
    required = ("self", "user", "system", "attacker", "inaction")
    missing = [key for key in required if key not in costs]
    if missing:
        raise PersonaDatasetError(f"{field_name} missing stakeholder keys: {', '.join(missing)}")

    normalized: dict[str, dict[str, float]] = {}
    for stakeholder in required:
        vector = costs[stakeholder]
        if not isinstance(vector, dict) or not vector:
            raise PersonaDatasetError(f"{field_name}.{stakeholder} must be a non-empty object")
        normalized[stakeholder] = {}
        for channel, value in vector.items():
            if not isinstance(channel, str) or not channel.strip():
                raise PersonaDatasetError(f"{field_name}.{stakeholder} contains an invalid channel name")
            if not isinstance(value, (int, float)) or not 0 <= float(value) <= 1:
                raise PersonaDatasetError(f"{field_name}.{stakeholder}.{channel} must be a number in [0,1]")
            normalized[stakeholder][channel] = float(value)
    return normalized


def _normalize_behavior_eval(item: dict[str, Any], field_name: str) -> dict[str, Any]:
    normalized = {
        "eval_id": _require_string(item.get("eval_id"), f"{field_name}.eval_id"),
        "kind": _require_string(item.get("kind"), f"{field_name}.kind"),
        "prompt": _require_string(item.get("prompt"), f"{field_name}.prompt"),
        "expected_behavior": _require_string(item.get("expected_behavior"), f"{field_name}.expected_behavior"),
    }
    for key in ("must_include", "must_avoid", "stakeholders"):
        value = item.get(key, [])
        if not isinstance(value, list) or not all(isinstance(entry, str) for entry in value):
            raise PersonaDatasetError(f"{field_name}.{key} must be a list of strings")
        normalized[key] = value
    return normalized


def _normalize_dpo_pair(item: dict[str, Any], field_name: str) -> dict[str, Any]:
    normalized = {
        "prompt": _require_string(item.get("prompt"), f"{field_name}.prompt"),
        "chosen": _require_string(item.get("chosen"), f"{field_name}.chosen"),
        "rejected": _require_string(item.get("rejected"), f"{field_name}.rejected"),
    }
    if "dimension" in item and item["dimension"] is not None:
        normalized["dimension"] = _require_string(item["dimension"], f"{field_name}.dimension")
    return normalized


def _normalize_tongue_weights(value: Any) -> dict[str, float]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise PersonaDatasetError("tongue_weights must be an object")
    normalized: dict[str, float] = {}
    for tongue, weight in value.items():
        if tongue not in TONGUES:
            raise PersonaDatasetError(f"tongue_weights contains unsupported tongue '{tongue}'")
        if not isinstance(weight, (int, float)) or not 0 <= float(weight) <= 1:
            raise PersonaDatasetError(f"tongue_weights.{tongue} must be a number in [0,1]")
        normalized[tongue] = float(weight)
    return normalized


def normalize_source_record(record: dict[str, Any]) -> dict[str, Any]:
    body_axes = [_normalize_axis(item, f"body_axes[{idx}]") for idx, item in enumerate(_require_list(record.get("body_axes"), "body_axes"))]
    mind_axes = [_normalize_axis(item, f"mind_axes[{idx}]") for idx, item in enumerate(_require_list(record.get("mind_axes"), "mind_axes"))]
    evidence_spans = [
        _normalize_evidence_span(item, f"evidence_spans[{idx}]")
        for idx, item in enumerate(_require_list(record.get("evidence_spans"), "evidence_spans"))
    ]
    behavior_eval_items = [
        _normalize_behavior_eval(item, f"behavior_eval_items[{idx}]")
        for idx, item in enumerate(_require_list(record.get("behavior_eval_items"), "behavior_eval_items"))
    ]

    metadata = record.get("metadata", {})
    if metadata is not None and not isinstance(metadata, dict):
        raise PersonaDatasetError("metadata must be an object when provided")

    normalized = {
        "subject_id": _require_string(record.get("subject_id"), "subject_id"),
        "display_name": _require_string(record.get("display_name"), "display_name"),
        "canon_role": _require_string(record.get("canon_role"), "canon_role"),
        "source_type": _require_string(record.get("source_type"), "source_type"),
        "body_axes": body_axes,
        "mind_axes": mind_axes,
        "evidence_spans": evidence_spans,
        "stakeholder_costs": _normalize_costs(record.get("stakeholder_costs"), "stakeholder_costs"),
        "behavior_eval_items": behavior_eval_items,
        "tongue_weights": _normalize_tongue_weights(record.get("tongue_weights")),
        "metadata": metadata or {},
    }

    for optional_key in ("canon_status", "summary"):
        if optional_key in record and record[optional_key] is not None:
            normalized[optional_key] = _require_string(record[optional_key], optional_key)

    reflection_blocks = record.get("reflection_blocks", [])
    if reflection_blocks:
        if not isinstance(reflection_blocks, list):
            raise PersonaDatasetError("reflection_blocks must be a list")
        normalized["reflection_blocks"] = [
            _normalize_reflection_block(item, f"reflection_blocks[{idx}]") for idx, item in enumerate(reflection_blocks)
        ]

    region_anchors = record.get("region_anchors", [])
    if region_anchors:
        if not isinstance(region_anchors, list):
            raise PersonaDatasetError("region_anchors must be a list")
        normalized["region_anchors"] = [
            _normalize_region_anchor(item, f"region_anchors[{idx}]") for idx, item in enumerate(region_anchors)
        ]

    state_vector = record.get("state_vector_21d")
    if state_vector is not None:
        if not isinstance(state_vector, list) or len(state_vector) != 21 or not all(
            isinstance(item, (int, float)) for item in state_vector
        ):
            raise PersonaDatasetError("state_vector_21d must be a list of 21 numbers")
        normalized["state_vector_21d"] = [float(item) for item in state_vector]

    conflict_rules = record.get("conflict_rules", [])
    if conflict_rules:
        if not isinstance(conflict_rules, list) or not all(isinstance(item, str) for item in conflict_rules):
            raise PersonaDatasetError("conflict_rules must be a list of strings")
        normalized["conflict_rules"] = conflict_rules

    dpo_pairs = record.get("dpo_pairs", [])
    if dpo_pairs:
        if not isinstance(dpo_pairs, list):
            raise PersonaDatasetError("dpo_pairs must be a list")
        normalized["dpo_pairs"] = [_normalize_dpo_pair(item, f"dpo_pairs[{idx}]") for idx, item in enumerate(dpo_pairs)]

    return normalized


def dominant_tongue(weights: dict[str, float]) -> str | None:
    if not weights:
        return None
    return max(weights.items(), key=lambda item: item[1])[0]


def build_profile_record(source: dict[str, Any], matrix_version: str = SCHEMA_VERSION) -> dict[str, Any]:
    profile_id = f"persona-{source['subject_id']}-v1"
    source_refs = list(source.get("metadata", {}).get("source_refs", []))
    derived_views = ["evidence", "behavior"]
    if source.get("reflection_blocks"):
        derived_views.append("reflection")
    if source.get("dpo_pairs"):
        derived_views.append("dpo")
    if source.get("state_vector_21d") is not None:
        derived_views.append("21d")

    body = {
        "axes": source["body_axes"],
        "tongue_weights": source.get("tongue_weights", {}),
    }
    if source.get("state_vector_21d") is not None:
        body["state_vector_21d"] = source["state_vector_21d"]

    mind = {
        "axes": source["mind_axes"],
    }
    if source.get("region_anchors"):
        mind["region_anchors"] = source["region_anchors"]
    if source.get("conflict_rules"):
        mind["conflict_rules"] = source["conflict_rules"]

    profile = {
        "profile_id": profile_id,
        "subject_id": source["subject_id"],
        "display_name": source["display_name"],
        "canon_role": source["canon_role"],
        "source_type": source["source_type"],
        "matrix_version": matrix_version,
        "body": body,
        "mind": mind,
        "spirit": {
            "stakeholder_costs": source["stakeholder_costs"],
        },
        "evidence_spans": source["evidence_spans"],
        "derived": {
            "evidence_count": len(source["evidence_spans"]),
            "body_axis_count": len(source["body_axes"]),
            "mind_axis_count": len(source["mind_axes"]),
            "behavior_eval_count": len(source["behavior_eval_items"]),
            "dpo_pair_count": len(source.get("dpo_pairs", [])),
            "available_views": derived_views,
        },
        "metadata": {
            "track": "persona_profile",
            "source_refs": source_refs,
            "owner": source.get("metadata", {}).get("owner"),
            "split": source.get("metadata", {}).get("split", "train"),
            "tags": source.get("metadata", {}).get("tags", []),
        },
    }

    if source.get("canon_status"):
        profile["canon_status"] = source["canon_status"]
    if source.get("summary"):
        profile["summary"] = source["summary"]
    if source.get("reflection_blocks"):
        profile["reflection_blocks"] = source["reflection_blocks"]

    tongue = dominant_tongue(source.get("tongue_weights", {}))
    if tongue is not None:
        profile["derived"]["dominant_tongue"] = tongue

    return profile


def build_behavior_eval_records(source: dict[str, Any], profile_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    split = source.get("metadata", {}).get("split", "train")
    for item in source["behavior_eval_items"]:
        rows.append(
            {
                "eval_id": item["eval_id"],
                "subject_id": source["subject_id"],
                "profile_id": profile_id,
                "kind": item["kind"],
                "prompt": item["prompt"],
                "expected_behavior": item["expected_behavior"],
                "rubric": {
                    "must_include": item.get("must_include", []),
                    "must_avoid": item.get("must_avoid", []),
                    "stakeholders": item.get("stakeholders", []),
                },
                "metadata": {
                    "track": "persona_behavior_eval",
                    "source_type": source["source_type"],
                    "subject_id": source["subject_id"],
                    "split": split,
                },
            }
        )
    return rows


def build_dpo_records(source: dict[str, Any], profile_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    split = source.get("metadata", {}).get("split", "train")
    for item in source.get("dpo_pairs", []):
        rows.append(
            {
                "prompt": item["prompt"],
                "chosen": item["chosen"],
                "rejected": item["rejected"],
                "metadata": {
                    "track": "persona_dpo",
                    "subject_id": source["subject_id"],
                    "profile_id": profile_id,
                    "source_type": source["source_type"],
                    "split": split,
                    "dimension": item.get("dimension"),
                },
            }
        )
    return rows


def compile_persona_dataset(input_path: Path, output_dir: Path) -> dict[str, Any]:
    source_rows = [normalize_source_record(record) for record in read_jsonl(input_path)]

    profile_rows: list[dict[str, Any]] = []
    eval_rows: list[dict[str, Any]] = []
    dpo_rows: list[dict[str, Any]] = []

    for source in source_rows:
        profile = build_profile_record(source)
        profile_rows.append(profile)
        eval_rows.extend(build_behavior_eval_records(source, profile["profile_id"]))
        dpo_rows.extend(build_dpo_records(source, profile["profile_id"]))

    output_dir.mkdir(parents=True, exist_ok=True)
    profiles_path = output_dir / "persona_profiles.jsonl"
    evals_path = output_dir / "persona_behavior_eval.jsonl"
    dpo_path = output_dir / "persona_dpo.jsonl"
    manifest_path = output_dir / "manifest.json"

    write_jsonl(profiles_path, profile_rows)
    write_jsonl(evals_path, eval_rows)
    write_jsonl(dpo_path, dpo_rows)

    manifest = {
        "input_path": str(input_path),
        "output_dir": str(output_dir),
        "schema_version": SCHEMA_VERSION,
        "profile_count": len(profile_rows),
        "behavior_eval_count": len(eval_rows),
        "dpo_count": len(dpo_rows),
        "outputs": {
            "persona_profiles": str(profiles_path),
            "persona_behavior_eval": str(evals_path),
            "persona_dpo": str(dpo_path),
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compile persona source packets into SCBE profile/eval/DPO lanes.")
    parser.add_argument("--input", required=True, help="Path to persona source JSONL")
    parser.add_argument("--output-dir", required=True, help="Output directory for compiled JSONL lanes")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    manifest = compile_persona_dataset(Path(args.input), Path(args.output_dir))
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
