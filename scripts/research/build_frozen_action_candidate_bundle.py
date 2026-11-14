"""Build a non-launchable four-lane frozen-action candidate bundle.

The bundle uses a candidate-only schema, keeps every review and training flag
false, and never loads a model or starts an optimizer.  It converts previously
audited arithmetic rows into exact compiler-frame targets, checks the recovered
parent's sequence bound, and binds all four lanes to replayable source spans.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Iterable

CANDIDATE_MANIFEST_SCHEMA = "clay.full-system-action-dataset-candidate.v1"
CANDIDATE_AUTHORITY_SCHEMA = "clay.full-system-action-source-authorities-candidate.v1"
ACCEPTED_CAMPAIGN_SCHEMA = "clay.full-system-action-dataset.v1"
LANES = ("train", "holdout", "ordinary", "retention")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_bytes(_canonical_json(value).encode("utf-8"))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def _jsonl(rows: Iterable[dict[str, Any]]) -> str:
    return "".join(_canonical_json(row) + "\n" for row in rows)


def _descriptor(path: Path, records: int) -> dict[str, Any]:
    return {
        "bytes": path.stat().st_size,
        "path": path.name,
        "records": records,
        "sha256": _sha256_file(path),
    }


def _authority(
    *,
    source_id: str,
    source_family: str,
    lane: str,
    locator: str,
    artifact_sha256: str,
    artifact_bytes: int,
    span: dict[str, Any],
    excerpt_sha256: str,
) -> dict[str, Any]:
    unsigned = {
        "artifact_bytes": artifact_bytes,
        "artifact_sha256": artifact_sha256,
        "excerpt_sha256": excerpt_sha256,
        "lane": lane,
        "locator": locator,
        "source_family": source_family,
        "source_id": source_id,
        "source_kind": "published_source",
        "span": span,
    }
    return {**unsigned, "receipt_sha256": _sha256_json(unsigned)}


def _load_external(root: Path) -> tuple[Any, Any]:
    experiment_root = root.resolve(strict=True)
    if str(experiment_root) not in sys.path:
        sys.path.insert(0, str(experiment_root))
    action = importlib.import_module("action_compiler")
    campaign = importlib.import_module("full_system_action_campaign")
    return action, campaign


def _action_candidate(
    *,
    action: Any,
    campaign: Any,
    compiler: Any,
    record_id: str,
    lane: str,
    source_id: str,
    excerpt_sha256: str,
    prompt: str,
    expression: str,
    block_size: int,
) -> tuple[dict[str, Any] | None, str | None]:
    frame = action.ActionFrame(0, expression, None)
    compiled = compiler.compile_frame(frame)
    compiled_frame = compiled["frame"]
    canonical = f"{compiled_frame['family']} :: {compiled_frame['method']} :: " f"{compiled_frame['payload']}"
    record = campaign.ActionRecord(
        record_id=record_id,
        split=lane,
        source_id=source_id,
        source_sha256=excerpt_sha256,
        source_kind="published_source",
        prompt=prompt,
        canonical=canonical,
        family_token_id=int(compiled_frame["family_token_id"]),
        method_token_id=compiled_frame["method_token_id"],
        payload=str(compiled_frame["payload"]),
        action_receipt_sha256=str(compiled["receipt_sha256"]),
    )
    try:
        campaign.prepare_example(record, block_size=block_size)
    except campaign.DatasetAdmissionError as error:
        return None, str(error)
    return (
        {
            "id": record.record_id,
            "input": record.prompt,
            "review_status": "NOT_REVIEWED",
            "source_id": record.source_id,
            "source_kind": record.source_kind,
            "source_sha256": record.source_sha256,
            "split": lane,
            "target": {
                "action_receipt_sha256": record.action_receipt_sha256,
                "canonical": record.canonical,
                "family_token_id": record.family_token_id,
                "method_token_id": record.method_token_id,
                "payload": record.payload,
            },
            "training_eligible": False,
        },
        None,
    )


def _source_locator(metadata: dict[str, Any], suffix: str) -> str:
    return f"{metadata['repository']}@{metadata['commit']}:" f"{metadata['artifact']}#{suffix}"


def _build_action_lanes(
    *,
    source_receipt: dict[str, Any],
    math_rows: list[dict[str, Any]],
    gsm8k_path: Path,
    svamp_path: Path,
    action: Any,
    campaign: Any,
    block_size: int,
    limit_per_source: int | None,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]], dict[str, Any]]:
    accepted = {(str(row["source"]), int(row["source_index"])): row for row in math_rows if row["accepted"]}
    compiler = action.ActionCompiler()
    records: dict[str, list[dict[str, Any]]] = {"train": [], "holdout": []}
    authorities: list[dict[str, Any]] = []
    rejected_for_length: dict[str, list[str]] = {"train": [], "holdout": []}

    gsm_meta = source_receipt["sources"]["openai-gsm8k"]
    gsm_lines = gsm8k_path.read_text(encoding="utf-8").splitlines(keepends=True)
    for index, line in enumerate(gsm_lines):
        audit = accepted.get(("openai-gsm8k", index))
        if audit is None:
            continue
        if limit_per_source is not None and len(records["train"]) >= limit_per_source:
            break
        raw = json.loads(line)
        excerpt_sha256 = _sha256_bytes(line.encode("utf-8"))
        source_id = f"openai-gsm8k:train:{index:05d}"
        record, error = _action_candidate(
            action=action,
            campaign=campaign,
            compiler=compiler,
            record_id=f"action-{source_id}",
            lane="train",
            source_id=source_id,
            excerpt_sha256=excerpt_sha256,
            prompt=str(raw["question"]),
            expression=str(audit["normalized_expression"]),
            block_size=block_size,
        )
        if record is None:
            rejected_for_length["train"].append(str(audit["source_row_id"]))
            continue
        records["train"].append(record)
        authorities.append(
            _authority(
                source_id=source_id,
                source_family="openai-gsm8k",
                lane="train",
                locator=_source_locator(gsm_meta, f"line={index}:{index + 1}"),
                artifact_sha256=str(gsm_meta["sha256"]),
                artifact_bytes=int(gsm_meta["bytes"]),
                span={"end": index + 1, "start": index, "unit": "line"},
                excerpt_sha256=excerpt_sha256,
            )
        )

    svamp_meta = source_receipt["sources"]["arkilpatel-svamp"]
    svamp_rows = json.loads(svamp_path.read_text(encoding="utf-8"))
    for index, raw in enumerate(svamp_rows):
        audit = accepted.get(("arkilpatel-svamp", index))
        if audit is None:
            continue
        if limit_per_source is not None and len(records["holdout"]) >= limit_per_source:
            break
        excerpt = _canonical_json(raw)
        excerpt_sha256 = _sha256_bytes(excerpt.encode("utf-8"))
        source_id = f"arkilpatel-svamp:holdout:{raw['ID']}"
        prompt = f"{str(raw['Body']).strip()} {str(raw['Question']).strip()}".strip()
        record, error = _action_candidate(
            action=action,
            campaign=campaign,
            compiler=compiler,
            record_id=f"action-{source_id}",
            lane="holdout",
            source_id=source_id,
            excerpt_sha256=excerpt_sha256,
            prompt=prompt,
            expression=str(audit["normalized_expression"]),
            block_size=block_size,
        )
        if record is None:
            rejected_for_length["holdout"].append(str(audit["source_row_id"]))
            continue
        records["holdout"].append(record)
        authorities.append(
            _authority(
                source_id=source_id,
                source_family="arkilpatel-svamp",
                lane="holdout",
                locator=_source_locator(svamp_meta, f"record={index}:{index + 1}"),
                artifact_sha256=str(svamp_meta["sha256"]),
                artifact_bytes=int(svamp_meta["bytes"]),
                span={"end": index + 1, "start": index, "unit": "record"},
                excerpt_sha256=excerpt_sha256,
            )
        )

    return (
        records,
        authorities,
        {
            "rejected_for_parent_sequence_bound": {lane: len(values) for lane, values in rejected_for_length.items()},
            "rejected_row_ids": rejected_for_length,
        },
    )


def _build_text_lanes(
    *,
    source_receipt: dict[str, Any],
    text_rows: list[dict[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    records: dict[str, list[dict[str, Any]]] = {"ordinary": [], "retention": []}
    authorities: list[dict[str, Any]] = []
    metadata_by_source = {
        "python-cpython-controlflow": source_receipt["sources"]["python-cpython-controlflow"],
        "rust-lang-book-control-flow": source_receipt["sources"]["rust-lang-book-control-flow"],
    }
    for row in text_rows:
        lane = str(row["lane"])
        if lane not in records:
            raise ValueError(f"unexpected text lane: {lane}")
        if row["review_status"] != "NOT_REVIEWED" or row["training_eligible"] is not False:
            raise ValueError("text candidate unexpectedly carries review/training authority")
        source_id = str(row["source_id"])
        record = {
            "id": f"text-{source_id}",
            "input": str(row["prompt"]),
            "review_status": "NOT_REVIEWED",
            "source_id": source_id,
            "source_kind": "published_source",
            "source_sha256": str(row["excerpt_sha256"]),
            "split": lane,
            "training_eligible": False,
        }
        records[lane].append(record)
        metadata = metadata_by_source[str(row["source"])]
        span = dict(row["span"])
        authorities.append(
            _authority(
                source_id=source_id,
                source_family=str(row["source_family"]),
                lane=lane,
                locator=_source_locator(metadata, f"lines={span['start']}:{span['end']}"),
                artifact_sha256=str(metadata["sha256"]),
                artifact_bytes=int(metadata["bytes"]),
                span=span,
                excerpt_sha256=str(row["excerpt_sha256"]),
            )
        )
    return records, authorities


def _validate_bundle(records: dict[str, list[dict[str, Any]]], authorities: list[dict[str, Any]]) -> dict[str, Any]:
    if set(records) != set(LANES) or any(not records[lane] for lane in LANES):
        raise ValueError("candidate bundle must contain all four nonempty lanes")
    source_ids = [row["source_id"] for lane in LANES for row in records[lane]]
    record_ids = [row["id"] for lane in LANES for row in records[lane]]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("candidate source IDs are not unique")
    if len(record_ids) != len(set(record_ids)):
        raise ValueError("candidate record IDs are not unique")
    by_id = {row["source_id"]: row for row in authorities}
    if set(by_id) != set(source_ids):
        raise ValueError("candidate authority coverage differs from records")
    families: dict[str, set[str]] = {}
    prompts: dict[str, set[str]] = {}
    for lane in LANES:
        families[lane] = {by_id[row["source_id"]]["source_family"] for row in records[lane]}
        prompts[lane] = {str(row["input"]) for row in records[lane]}
        for row in records[lane]:
            authority = by_id[row["source_id"]]
            if authority["lane"] != lane:
                raise ValueError("candidate authority lane differs from record")
            if authority["excerpt_sha256"] != row["source_sha256"]:
                raise ValueError("candidate excerpt hash differs from record")
            unsigned = dict(authority)
            receipt = unsigned.pop("receipt_sha256")
            if _sha256_json(unsigned) != receipt:
                raise ValueError("candidate authority receipt does not replay")
            if row["review_status"] != "NOT_REVIEWED" or row["training_eligible"] is not False:
                raise ValueError("candidate row unexpectedly carries authority")
    for index, left in enumerate(LANES):
        for right in LANES[index + 1 :]:
            if families[left] & families[right]:
                raise ValueError(f"source families overlap: {left}/{right}")
            if prompts[left] & prompts[right]:
                raise ValueError(f"exact prompts overlap: {left}/{right}")
    return {
        "exact_prompt_disjoint": True,
        "record_count": len(source_ids),
        "source_family_disjoint": True,
        "source_families": {lane: sorted(families[lane]) for lane in LANES},
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-audit-receipt", required=True, type=Path)
    parser.add_argument("--math-audit-ledger", required=True, type=Path)
    parser.add_argument("--text-audit-ledger", required=True, type=Path)
    parser.add_argument("--gsm8k", required=True, type=Path)
    parser.add_argument("--svamp", required=True, type=Path)
    parser.add_argument("--action-experiment-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--block-size", type=int, default=512)
    parser.add_argument("--limit-per-action-source", type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.block_size <= 0:
        raise ValueError("--block-size must be positive")
    if args.limit_per_action_source is not None and args.limit_per_action_source <= 0:
        raise ValueError("--limit-per-action-source must be positive")
    output_dir = args.output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"candidate output directory is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    source_receipt_path = args.source_audit_receipt.resolve(strict=True)
    source_receipt = json.loads(source_receipt_path.read_text(encoding="utf-8"))
    math_ledger_path = args.math_audit_ledger.resolve(strict=True)
    text_ledger_path = args.text_audit_ledger.resolve(strict=True)
    math_rows = [json.loads(line) for line in math_ledger_path.read_text(encoding="utf-8").splitlines() if line]
    text_rows = [json.loads(line) for line in text_ledger_path.read_text(encoding="utf-8").splitlines() if line]
    gsm8k = args.gsm8k.resolve(strict=True)
    svamp = args.svamp.resolve(strict=True)
    if _sha256_file(gsm8k) != source_receipt["sources"]["openai-gsm8k"]["sha256"]:
        raise ValueError("GSM8K artifact differs from source receipt")
    if _sha256_file(svamp) != source_receipt["sources"]["arkilpatel-svamp"]["sha256"]:
        raise ValueError("SVAMP artifact differs from source receipt")

    action, campaign = _load_external(args.action_experiment_root)
    action_records, action_authorities, action_summary = _build_action_lanes(
        source_receipt=source_receipt,
        math_rows=math_rows,
        gsm8k_path=gsm8k,
        svamp_path=svamp,
        action=action,
        campaign=campaign,
        block_size=args.block_size,
        limit_per_source=args.limit_per_action_source,
    )
    text_records, text_authorities = _build_text_lanes(
        source_receipt=source_receipt,
        text_rows=text_rows,
    )
    records = {**action_records, **text_records}
    authorities = action_authorities + text_authorities
    validation = _validate_bundle(records, authorities)

    files: dict[str, dict[str, Any]] = {}
    for lane in LANES:
        path = output_dir / f"{lane}.candidate.jsonl"
        _atomic_text(path, _jsonl(records[lane]))
        files[lane] = _descriptor(path, len(records[lane]))

    authority_payload = {
        "schema": CANDIDATE_AUTHORITY_SCHEMA,
        "authorities": authorities,
        "review_status": "NOT_REVIEWED",
        "training_authorized": False,
        "claim_boundary": "Candidate authority receipts only; not accepted by the campaign loader.",
    }
    authority_path = output_dir / "SOURCE_AUTHORITIES.candidate.json"
    _atomic_text(authority_path, json.dumps(authority_payload, indent=2, sort_keys=True) + "\n")
    authority_descriptor = _descriptor(authority_path, len(authorities))

    manifest = {
        "schema": CANDIDATE_MANIFEST_SCHEMA,
        "accepted_campaign_schema": ACCEPTED_CAMPAIGN_SCHEMA,
        "accepted_by_campaign_loader": False,
        "block_size": args.block_size,
        "files": files,
        "material_evidence_authorized": False,
        "review_status": "NOT_REVIEWED",
        "source_authorities": authority_descriptor,
        "source_disjoint": True,
        "training_authorized": False,
    }
    manifest_path = output_dir / "CANDIDATE_MANIFEST.json"
    _atomic_text(manifest_path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    receipt = {
        "schema": "clay.full-system-action-candidate-build-receipt.v1",
        "status": "COMPLETE_NOT_ADMITTED",
        "authority": {
            "dataset_admission": "NONE",
            "launch": "NONE",
            "partial_unfreeze": "NONE",
            "promotion": "NONE",
            "tool_dispatch": "DISABLED",
        },
        "action_summary": action_summary,
        "inputs": {
            "math_audit_ledger_sha256": _sha256_file(math_ledger_path),
            "source_audit_receipt_sha256": _sha256_file(source_receipt_path),
            "text_audit_ledger_sha256": _sha256_file(text_ledger_path),
        },
        "manifest": {
            "bytes": manifest_path.stat().st_size,
            "path": str(manifest_path),
            "sha256": _sha256_file(manifest_path),
        },
        "outputs": {**files, "source_authorities": authority_descriptor},
        "validation": validation,
        "claim_boundary": (
            "This bundle proves deterministic candidate construction and source-span "
            "coverage only. Its schema is intentionally rejected by the material "
            "campaign loader, all rows are unreviewed/ineligible, and it authorizes "
            "no training, execution, promotion, or partial unfreeze."
        ),
    }
    receipt_path = output_dir / "BUILD_RECEIPT.json"
    _atomic_text(receipt_path, json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(
        _canonical_json(
            {
                "manifest_sha256": receipt["manifest"]["sha256"],
                "output": str(output_dir),
                "records": validation["record_count"],
                "status": receipt["status"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
